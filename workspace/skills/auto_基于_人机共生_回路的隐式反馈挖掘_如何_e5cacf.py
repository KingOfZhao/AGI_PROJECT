"""
Module: implicit_feedback_mining.py
Description: 基于'人机共生'回路的隐式反馈挖掘模块。
             通过计算用户的'实践证伪'行为（如重写代码、回溯操作）的编辑距离与时间特征，
             将其转化为对特定SKILL节点的'置信度惩罚值'。
Author: Senior Python Engineer (AGI System)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义数据结构
@dataclass
class SkillNode:
    """代表AGI系统中的一个技能节点"""
    node_id: str
    current_confidence: float = 1.0  # 范围 [0.0, 1.0]
    penalty_history: list = field(default_factory=list)

    def update_confidence(self, penalty: float):
        """应用惩罚值并确保置信度在有效范围内"""
        self.current_confidence = max(0.0, self.current_confidence - penalty)
        self.penalty_history.append(penalty)

@dataclass
class UserAction:
    """代表用户的一次隐式反馈行为"""
    action_id: str
    node_id: str
    original_content: str
    modified_content: str
    action_duration_ms: int  # 操作耗时（毫秒），用于判断犹豫程度
    is_rollback: bool = False  # 是否为回溯/撤销操作

class ImplicitFeedbackMiner:
    """
    基于'人机共生'回路的隐式反馈挖掘器。
    
    该类负责将人类用户对AI生成内容的隐性修正行为转化为数值化的惩罚信号，
    用于降低特定SKILL节点的置信度，从而实现无需显式打分的模型自我修正。
    """

    def __init__(self, 
                 distance_weight: float = 0.6, 
                 hesitation_weight: float = 0.4,
                 max_penalty_threshold: float = 0.8):
        """
        初始化挖掘器。

        Args:
            distance_weight (float): 编辑距离在惩罚计算中的权重.
            hesitation_weight (float): 犹豫时间在惩罚计算中的权重.
            max_penalty_threshold (float): 单次操作允许的最大惩罚值上限.
        """
        if not (0.0 <= distance_weight <= 1.0) or not (0.0 <= hesitation_weight <= 1.0):
            raise ValueError("Weights must be between 0.0 and 1.0")
        if distance_weight + hesitation_weight > 1.0:
            logger.warning("Sum of weights exceeds 1.0, behavior might be skewed.")

        self.distance_weight = distance_weight
        self.hesitation_weight = hesitation_weight
        self.max_penalty = max_penalty_threshold
        self.nodes: Dict[str, SkillNode] = {}
        
        logger.info("ImplicitFeedbackMiner initialized with weights: d=%f, h=%f", 
                    distance_weight, hesitation_weight)

    def _calculate_levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        计算两个字符串之间的Levenshtein编辑距离。
        辅助函数：用于量化修改幅度。

        Args:
            s1 (str): 原始字符串.
            s2 (str): 修改后字符串.

        Returns:
            int: 编辑距离.
        """
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _normalize_metrics(self, 
                          raw_distance: int, 
                          max_len: int, 
                          duration_ms: int) -> Tuple[float, float]:
        """
        归一化编辑距离和犹豫时间。
        辅助函数：将不同量纲的数据转化为 [0, 1] 的数值。

        Args:
            raw_distance (int): 原始编辑距离.
            max_len (int): 原始文本长度用于归一化.
            duration_ms (int): 操作耗时.

        Returns:
            Tuple[float, float]: (归一化距离分数, 归一化犹豫分数)
        """
        # 1. 归一化距离 (0.0 到 1.0)
        # 避免除以0
        norm_dist = raw_distance / max_len if max_len > 0 else 0.0
        
        # 2. 归一化犹豫度
        # 假设超过2000ms(2秒)被视为高犹豫，使用Sigmoid-like函数平滑
        # 这里简化为线性截断，实际应用可用更复杂的心理模型
        hesitation_score = min(1.0, duration_ms / 3000.0) 
        
        return norm_dist, hesitation_score

    def process_user_action(self, action: UserAction) -> float:
        """
        核心函数：处理用户行为并计算惩罚值。
        
        逻辑流程：
        1. 验证数据有效性。
        2. 如果是'回溯'行为，给予基础高惩罚。
        3. 如果是'编辑'行为，计算编辑距离和操作耗时。
        4. 加权融合指标生成最终惩罚值。
        5. 更新对应的SkillNode。

        Args:
            action (UserAction): 包含修改细节的用户行为对象.

        Returns:
            float: 计算出的惩罚值 (0.0 to 1.0).
            
        Raises:
            ValueError: 如果node_id不存在或数据无效.
        """
        if not action.node_id:
            logger.error("Action missing node_id")
            raise ValueError("Invalid action data: node_id required")

        # 确保节点存在
        if action.node_id not in self.nodes:
            self.nodes[action.node_id] = SkillNode(node_id=action.node_id)
            logger.info("Created new SkillNode: %s", action.node_id)

        node = self.nodes[action.node_id]
        
        # 边界检查
        if not isinstance(action.original_content, str) or not isinstance(action.modified_content, str):
            logger.warning("Invalid content types for action %s", action.action_id)
            return 0.0

        penalty = 0.0

        if action.is_rollback:
            # 回溯操作被视为强烈的负反馈
            penalty = 0.75  # 固定高惩罚
            logger.info("Rollback detected for node %s. Assigning fixed penalty.", action.node_id)
        else:
            # 计算编辑距离
            dist = self._calculate_levenshtein_distance(action.original_content, action.modified_content)
            max_len = max(len(action.original_content), len(action.modified_content))
            
            if max_len == 0:
                # 内容为空且无修改
                return 0.0

            # 归一化指标
            norm_dist, norm_hesitation = self._normalize_metrics(
                dist, max_len, action.action_duration_ms
            )

            # 算法核心：加权惩罚计算
            # 如果编辑距离大且犹豫时间长，惩罚高
            # 如果只是微小的拼写修正（距离小），惩罚低
            raw_penalty = (norm_dist * self.distance_weight) + \
                          (norm_hesitation * self.hesitation_weight)
            
            # 应用非线性放大（可选，使大改动惩罚更明显）
            penalty = math.pow(raw_penalty, 1.5)

        # 应用最大阈值限制
        final_penalty = min(penalty, self.max_penalty)
        
        # 更新节点
        node.update_confidence(final_penalty)
        logger.info("Applied penalty %.4f to node %s. New confidence: %.4f", 
                    final_penalty, action.node_id, node.current_confidence)

        return final_penalty

    def get_node_confidence(self, node_id: str) -> Optional[float]:
        """
        核心函数：获取特定节点的当前置信度。
        
        Args:
            node_id (str): 节点ID.

        Returns:
            Optional[float]: 置信度，如果节点不存在则返回None.
        """
        if node_id in self.nodes:
            return self.nodes[node_id].current_confidence
        return None

# 使用示例
if __name__ == "__main__":
    # 1. 初始化挖掘器
    miner = ImplicitFeedbackMiner(distance_weight=0.7, hesitation_weight=0.3)

    # 2. 模拟场景：AI生成了代码，用户进行了大幅度重写 (隐式负反馈)
    ai_generated_code = "def hello():\n    print('world')"
    user_rewritten_code = "def greet_user(name):\n    # Fixed logic\n    print(f'Hello {name}')"
    
    action_1 = UserAction(
        action_id="act_001",
        node_id="skill_python_codegen_01",
        original_content=ai_generated_code,
        modified_content=user_rewritten_code,
        action_duration_ms=4500,  # 用户思考并修改了4.5秒
        is_rollback=False
    )

    # 3. 处理反馈
    penalty = miner.process_user_action(action_1)
    print(f"Calculated Penalty: {penalty:.4f}")
    print(f"Node Confidence: {miner.get_node_confidence('skill_python_codegen_01'):.4f}")

    # 4. 模拟场景：用户执行了撤销操作
    action_2 = UserAction(
        action_id="act_002",
        node_id="skill_python_codegen_02",
        original_content="some code",
        modified_content="",  # Empty for rollback context
        action_duration_ms=200,
        is_rollback=True
    )
    
    miner.process_user_action(action_2)
    print(f"Node Confidence after rollback: {miner.get_node_confidence('skill_python_codegen_02'):.4f}")