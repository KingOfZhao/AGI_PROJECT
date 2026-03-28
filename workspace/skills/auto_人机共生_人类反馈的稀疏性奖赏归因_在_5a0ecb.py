"""
Module: auto_人机共生_人类反馈的稀疏性奖赏归因_在_5a0ecb
Description: 【人机共生】人类反馈的稀疏性奖赏归因模块。
             在'AI梳理清单→人类实践'的闭环中，针对人类仅提供二元反馈（成/败）的情况，
             本模块利用反事实推理，通过扰动分析识别导致结果的关键SKILL节点，
             实现对节点权重的精准更新，解决信用分配问题。
Domain: cognitive_science
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillNode:
    """
    表示AGI系统中的一个SKILL节点或动作步骤。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        name (str): 节点名称/描述。
        weight (float): 当前权重，表示该节点对成功贡献的先验信念。范围建议 [0.0, 1.0]。
    """
    node_id: str
    name: str
    weight: float = 0.5

    def __post_init__(self):
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")


class SparseRewardAttributor:
    """
    处理稀疏二元反馈的反事实归因引擎。
    
    核心逻辑：
    1. 接收执行轨迹（SKILL节点序列）和最终二元结果。
    2. 使用内部预测模型模拟“反事实”场景（即移除某个节点后的预测结果）。
    3. 比较实际结果与反事实预测的差异，计算归因分数。
    4. 根据归因分数更新节点权重。
    """

    def __init__(self, learning_rate: float = 0.1):
        """
        初始化归因器。

        Args:
            learning_rate (float): 权重更新的步长。默认 0.1。
        """
        self.learning_rate = learning_rate
        logger.info(f"SparseRewardAttributor initialized with learning_rate={learning_rate}")

    def _validate_input(self, trace: List[SkillNode], result: bool) -> None:
        """
        辅助函数：验证输入数据的完整性和合法性。

        Args:
            trace (List[SkillNode]): 执行轨迹。
            result (bool): 人类反馈的二元结果。

        Raises:
            ValueError: 如果输入数据无效。
        """
        if not trace:
            raise ValueError("Execution trace cannot be empty.")
        if not isinstance(result, bool):
            raise ValueError(f"Result must be boolean (True/False), got {type(result)}.")
        
        for node in trace:
            if not isinstance(node, SkillNode):
                raise ValueError(f"Trace must contain SkillNode objects, found {type(node)}.")

    def _predict_outcome(self, trace: List[SkillNode]) -> float:
        """
        辅助函数：模拟内部世界模型，预测给定轨迹成功的概率。
        
        这里使用简化的Sigmoid函数作为代理模型：
        P(success) = sigmoid(sum(weights) - bias)
        
        Args:
            trace (List[SkillNode]): 待评估的节点序列。

        Returns:
            float: 预测的成功概率 [0.0, 1.0]。
        """
        # 简单的线性聚合：假设节点越多、权重越高，成功概率越大
        # 在实际AGI系统中，这里可以替换为神经网络或其他复杂模型
        total_score = sum(node.weight for node in trace)
        
        # 设定一个动态阈值，假设平均每个节点贡献0.5分，需要一定量才能成功
        threshold = len(trace) * 0.4 
        
        # 使用Sigmoid将分数映射到概率
        try:
            probability = 1.0 / (1.0 + math.exp(-(total_score - threshold)))
        except OverflowError:
            probability = 0.0 if total_score - threshold < 0 else 1.0
            
        return probability

    def compute_attribution(self, trace: List[SkillNode], result: bool) -> Dict[str, float]:
        """
        核心函数：计算反事实归因分数。
        
        通过逐一“屏蔽”节点，观察预测结果的变化量。变化量越大，说明该节点对结果越关键。
        
        Input Format:
            trace: List[SkillNode], 例如 [Node(A, 0.5), Node(B, 0.8)]
            result: bool, True 表示成功，False 表示失败
        
        Output Format:
            Dict[str, float]: 键为 node_id，值为归因分数。
                              分数为正表示促进了成功，为负表示导致了失败。

        Args:
            trace (List[SkillNode]): 实际执行的SKILL节点序列。
            result (bool): 最终的二元反馈结果。

        Returns:
            Dict[str, float]: 每个节点的归因分数。
        """
        self._validate_input(trace, result)
        
        # 1. 计算基准预测（基于当前权重的模型预测）
        # 注意：这里我们结合实际结果和模型预测来计算“惊讶度”或“必要性”
        baseline_prob = self._predict_outcome(trace)
        baseline_value = 1.0 if result else 0.0
        
        attribution_scores = {}
        
        logger.info(f"Starting attribution analysis. Result: {result}, Baseline Prob: {baseline_prob:.4f}")

        # 2. 遍历每个节点进行反事实推理
        for i, target_node in enumerate(trace):
            # 创建反事实轨迹：移除当前节点
            counterfactual_trace = trace[:i] + trace[i+1:]
            
            if not counterfactual_trace:
                # 如果移除后为空，假设基准失败概率为0
                cf_prob = 0.0
            else:
                cf_prob = self._predict_outcome(counterfactual_trace)
            
            # 3. 计算归因：实际结果与反事实预测的差异
            # 如果结果是成功(1)，且移除节点后预测概率大幅下降，则该节点贡献为正
            # 如果结果是失败(0)，且移除节点后预测概率大幅上升（即该节点导致了失败），则该节点贡献为负
            # 公式：Attribution = (Actual - Counterfactual_Prediction) * Sign(Actual - Baseline_Prediction)
            # 简化版：直接看移除该节点对“符合结果”方向的影响
            
            # 这里采用更直观的Shapley Value简化思路：
            # 节点的重要性 = (包含该节点的预测值 - 不包含该节点的预测值)
            # 我们需要将实际结果映射为数值 1.0 或 0.0
            delta = baseline_value - cf_prob
            
            # 归一化处理（可选，视具体需求而定）
            attribution_scores[target_node.node_id] = delta
            
            logger.debug(f"Node {target_node.node_id}: CF_Prob={cf_prob:.4f}, Attribution={delta:.4f}")

        return attribution_scores

    def update_weights(self, trace: List[SkillNode], attribution_scores: Dict[str, float]) -> List[SkillNode]:
        """
        核心函数：根据归因分数更新SKILL节点的权重。
        
        更新规则：
        weight_new = weight_old + learning_rate * attribution_score
        
        Args:
            trace (List[SkillNode]): 原始执行轨迹。
            attribution_scores (Dict[str, float]): compute_attribution 计算出的分数。

        Returns:
            List[SkillNode]: 更新权重后的节点列表。
        """
        updated_trace = []
        
        for node in trace:
            score = attribution_scores.get(node.node_id, 0.0)
            
            # 计算新权重
            new_weight = node.weight + (self.learning_rate * score)
            
            # 边界检查：确保权重在 [0.0, 1.0] 之间
            new_weight = max(0.0, min(1.0, new_weight))
            
            # 更新节点
            updated_node = SkillNode(node_id=node.node_id, name=node.name, weight=new_weight)
            updated_trace.append(updated_node)
            
            logger.info(f"Updated Node {node.node_id}: {node.weight:.4f} -> {new_weight:.4f} (Score: {score:.4f})")
            
        return updated_trace


# 使用示例
if __name__ == "__main__":
    # 模拟场景：AI生成了一份包含3个步骤的清单，人类执行后反馈“成功”
    # 我们想知道哪个步骤最关键，以便下次强化它
    
    # 1. 定义SKILL节点
    step1 = SkillNode(node_id="skill_001", name="数据收集", weight=0.4)
    step2 = SkillNode(node_id="skill_002", name="特征工程", weight=0.6)
    step3 = SkillNode(node_id="skill_003", name="模型训练", weight=0.5)
    
    execution_trace = [step1, step2, step3]
    human_feedback = True  # 成功
    
    # 2. 初始化归因器
    attributor = SparseRewardAttributor(learning_rate=0.2)
    
    print("--- 开始反事实归因分析 ---")
    # 3. 计算归因
    scores = attributor.compute_attribution(execution_trace, human_feedback)
    
    print("\n--- 归因分数 ---")
    for nid, score in scores.items():
        print(f"{nid}: {score:.4f}")
        
    # 4. 更新权重
    print("\n--- 更新权重 ---")
    new_trace = attributor.update_weights(execution_trace, scores)
    
    print("\n--- 最终结果 ---")
    for node in new_trace:
        print(f"Node: {node.name}, New Weight: {node.weight:.4f}")