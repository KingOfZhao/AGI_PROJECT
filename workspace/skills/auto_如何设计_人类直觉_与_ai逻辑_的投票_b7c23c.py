"""
Module: dynamic_confidence_voting.py
Description: 实现基于贝叶斯更新的动态置信度投票机制，用于解决AGI系统中人类直觉与AI逻辑的冲突。
             核心思想是利用任务的"可证伪性强度"来动态分配决策权重。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DecisionSource(Enum):
    """决策来源枚举"""
    HUMAN = "human_intuition"
    AI = "ai_logic"
    CONSENSUS = "consensus"

@dataclass
class TaskContext:
    """
    任务上下文数据类
    
    Attributes:
        task_id (str): 任务唯一标识符
        falsifiability_score (float): 可证伪性强度评分 [0.0, 1.0]
            1.0 代表高度可证伪（如数学证明、代码编译），AI应具有高权重
            0.0 代表极度模糊（如艺术审美、情感判断），人类应具有高权重
        description (str): 任务描述
        metadata (Dict): 额外元数据
    """
    task_id: str
    falsifiability_score: float
    description: str = ""
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.falsifiability_score <= 1.0:
            logger.error(f"Invalid falsifiability_score: {self.falsifiability_score}")
            raise ValueError("falsifiability_score must be between 0.0 and 1.0")
        if not self.task_id:
            raise ValueError("task_id cannot be empty")

@dataclass
class AgentVote:
    """
    智能体投票数据类
    
    Attributes:
        agent_id (str): 智能体ID
        decision (bool): 决策结果 (True=同意/肯定, False=拒绝/否定)
        confidence (float): 初始置信度 [0.0, 1.0]
        prior_success_rate (float): 历史先验成功率 [0.0, 1.0]
    """
    agent_id: str
    decision: bool
    confidence: float
    prior_success_rate: float = 0.5

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence {self.confidence} out of bounds for agent {self.agent_id}")
        if not 0.0 <= self.prior_success_rate <= 1.0:
            raise ValueError(f"Prior rate {self.prior_success_rate} out of bounds for agent {self.agent_id}")

def _calculate_bayesian_weight(prior_rate: float, observed_confidence: float) -> float:
    """
    [Helper] 辅助函数：基于简化的贝叶斯模型计算最终权重因子。
    
    使用 Beta 分布共轭先验的近似逻辑：
    权重 ∝ (先验 * 似然度) / 不确定性
    
    Args:
        prior_rate (float): 历史基线成功率
        observed_confidence (float): 当前决策的置信度
    
    Returns:
        float: 调整后的权重系数
    
    Raises:
        ValueError: 如果输入参数不在 [0, 1] 范围内
    """
    # 边界检查
    if not (0.0 <= prior_rate <= 1.0 and 0.0 <= observed_confidence <= 1.0):
        raise ValueError("Inputs must be between 0 and 1")

    # 避免除零错误，设置最小不确定性
    epsilon = 1e-5
    
    # 计算后验概率的强度
    # 这里的逻辑是：如果历史成功率高，且当前置信度高，权重应显著增加
    # 使用对数逻辑防止数值溢出并平滑差异
    log_odds = math.log((prior_rate + epsilon) / (1 - prior_rate + epsilon))
    adjusted_weight = observed_confidence * (1 + log_odds)
    
    # 归一化处理，确保权重在合理范围内 (0.1 到 2.0 之间，防止极端值)
    final_weight = max(0.1, min(2.0, adjusted_weight))
    
    logger.debug(f"Bayesian update: Prior={prior_rate}, Conf={observed_confidence}, Weight={final_weight}")
    return final_weight

def calculate_dynamic_weights(task: TaskContext) -> Dict[str, float]:
    """
    核心函数 1: 根据任务的可证伪性计算人类与AI的基础投票权重。
    
    逻辑说明：
    - 高可证伪性 (Score -> 1): 领域逻辑严密，客观性强，AI权重增加。
    - 低可证伪性 (Score -> 0): 领域模糊，主观性强，人类直觉权重增加。
    
    Args:
        task (TaskContext): 包含可证伪性评分的任务对象
        
    Returns:
        Dict[str, float]: 包含 'human_weight' 和 'ai_weight' 的字典
        
    Example:
        >>> task = TaskContext("task_123", 0.9, "Code Review")
        >>> weights = calculate_dynamic_weights(task)
        >>> print(weights)
        {'human_weight': 0.1, 'ai_weight': 0.9}
    """
    if not isinstance(task, TaskContext):
        raise TypeError("Input must be a TaskContext instance")
        
    score = task.falsifiability_score
    
    # Sigmoid-like 映射或简单线性映射
    # 这里使用简单的线性分配，但保留阈值逻辑
    # AI权重 = 可证伪性分数
    # 人类权重 = 1 - 可证伪性分数
    # 可以引入非线性函数增强特定区间的敏感度
    
    # 增强 S 型函数，使得在中间地带权重变化更剧烈
    # k=5 控制陡峭度
    k = 5.0 
    ai_weight = 1 / (1 + math.exp(-k * (score - 0.5)))
    human_weight = 1.0 - ai_weight
    
    logger.info(f"Task {task.task_id} Weights -> AI: {ai_weight:.4f}, Human: {human_weight:.4f} (F-Score: {score})")
    
    return {
        "human_weight": human_weight,
        "ai_weight": ai_weight
    }

def resolve_conflict(
    task: TaskContext, 
    human_vote: AgentVote, 
    ai_vote: AgentVote
) -> Tuple[bool, float, DecisionSource]:
    """
    核心函数 2: 解决冲突并输出最终决策。
    
    综合考虑：
    1. 任务的静态权重（基于可证伪性）
    2. 智能体的动态置信度（基于贝叶斯更新）
    
    Args:
        task (TaskContext): 任务上下文
        human_vote (AgentVote): 人类的投票数据
        ai_vote (AgentVote): AI的投票数据
        
    Returns:
        Tuple[bool, float, DecisionSource]: 
            - 最终决策
            - 最终置信度 (0.0-1.0)
            - 决策主导者
    
    Example:
        >>> ctx = TaskContext("t1", 0.8, "Math Problem")
        >>> h_vote = AgentVote("human_1", False, 0.6) # 人类直觉说错了
        >>> a_vote = AgentVote("ai_1", True, 0.95)    # AI逻辑说对了
        >>> result, conf, owner = resolve_conflict(ctx, h_vote, a_vote)
        >>> print(result)
        True
    """
    try:
        # 1. 获取基础动态权重
        base_weights = calculate_dynamic_weights(task)
        
        # 2. 计算贝叶斯调整后的实际权重
        # 人类权重 = 基础权重 * (历史表现因子 * 当前置信度)
        # 这里使用辅助函数计算加权系数
        human_adj_factor = _calculate_bayesian_weight(
            human_vote.prior_success_rate, 
            human_vote.confidence
        )
        ai_adj_factor = _calculate_bayesian_weight(
            ai_vote.prior_success_rate, 
            ai_vote.confidence
        )
        
        effective_human_weight = base_weights['human_weight'] * human_adj_factor
        effective_ai_weight = base_weights['ai_weight'] * ai_adj_factor
        
        total_weight = effective_human_weight + effective_ai_weight
        
        if total_weight == 0:
            logger.warning("Total weight is zero, defaulting to consensus fallback.")
            return False, 0.5, DecisionSource.CONSENSUS

        # 3. 计票
        # 如果决策一致
        if human_vote.decision == ai_vote.decision:
            final_conf = (effective_human_weight + effective_ai_weight) / total_weight
            logger.info(f"Consensus reached for {task.task_id}.")
            return human_vote.decision, min(final_conf, 1.0), DecisionSource.CONSENSUS
        
        # 如果决策冲突，进行加权投票
        # 计算支持 True 的总权重
        score_true = 0.0
        if human_vote.decision:
            score_true += effective_human_weight
        if ai_vote.decision:
            score_true += effective_ai_weight
            
        final_decision = score_true > (total_weight / 2)
        
        # 4. 确定最终置信度和主导者
        # 归一化胜出者的权重作为置信度
        winner_weight = score_true if final_decision else (total_weight - score_true)
        final_confidence = winner_weight / total_weight
        
        # 确定主导者
        if final_decision == human_vote.decision and effective_human_weight >= effective_ai_weight:
            dominant = DecisionSource.HUMAN
        elif final_decision == ai_vote.decision and effective_ai_weight >= effective_human_weight:
            dominant = DecisionSource.AI
        else:
            # 如果权重相近或复杂情况
            dominant = DecisionSource.HUMAN if base_weights['human_weight'] > base_weights['ai_weight'] else DecisionSource.AI
            
        logger.info(
            f"Conflict in {task.task_id}: Human({human_vote.decision}) vs AI({ai_vote.decision}). "
            f"Winner: {dominant.value}, Decision: {final_decision}, Conf: {final_confidence:.2f}"
        )
        
        return final_decision, final_confidence, dominant

    except Exception as e:
        logger.error(f"Error during conflict resolution for {task.task_id}: {e}")
        # 故障安全机制：在出错时倾向于人类直觉（安全第一原则）
        return human_vote.decision, human_vote.confidence, DecisionSource.HUMAN

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 场景 1: 高可证伪性任务 (例如：代码语法检查)
    # AI 应该占主导，即使人类有些许怀疑
    print("--- Scenario 1: Code Syntax Check (High Falsifiability) ---")
    code_task = TaskContext(
        task_id="code_001",
        falsifiability_score=0.95, # 高度客观
        description="Check if Python syntax is valid"
    )
    
    # AI 非常确信代码是对的，历史准确率 99%
    ai_vote_1 = AgentVote("ai_model_v2", decision=True, confidence=0.99, prior_success_rate=0.99)
    # 人类直觉觉得代码有问题（可能是错觉），历史准确率一般
    human_vote_1 = AgentVote("expert_01", decision=False, confidence=0.6, prior_success_rate=0.6)
    
    decision, conf, source = resolve_conflict(code_task, human_vote_1, ai_vote_1)
    print(f"Final Decision: {decision} (Source: {source.value}, Confidence: {conf:.2f})")
    # 预期结果: True (AI胜出)

    # 场景 2: 低可证伪性任务 (例如：UI 配色审美)
    # 人类应占主导
    print("\n--- Scenario 2: UI Color Aesthetics (Low Falsifiability) ---")
    design_task = TaskContext(
        task_id="design_045",
        falsifiability_score=0.10, # 高度主观
        description="Decide if the blue button looks better"
    )
    
    # AI 根据数据觉得红色好，置信度很高
    ai_vote_2 = AgentVote("ai_model_v2", decision=False, confidence=0.95, prior_success_rate=0.7)
    # 人类直觉觉得蓝色好，置信度中等
    human_vote_2 = AgentVote("expert_01", decision=True, confidence=0.7, prior_success_rate=0.8)
    
    decision, conf, source = resolve_conflict(design_task, human_vote_2, ai_vote_2)
    print(f"Final Decision: {decision} (Source: {source.value}, Confidence: {conf:.2f})")
    # 预期结果: True (Human胜出)