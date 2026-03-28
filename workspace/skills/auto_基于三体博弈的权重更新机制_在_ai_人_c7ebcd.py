"""
名称: auto_基于三体博弈的权重更新机制_在_ai_人_c7ebcd
描述: 基于三体博弈的权重更新机制：在'AI-人类-环境'共生系统中，如何量化人类反馈的权威权重？
     并非所有人类反馈都是正确的（人类也会犯错）。如何设计算法，根据反馈来源的历史可靠性、
     反馈内容的逻辑强度以及与现有稳固节点的冲突程度，动态调整知识更新的步长？
领域: human_computer_interaction
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FeedbackSignal:
    """
    反馈信号数据结构。
    
    Attributes:
        source_id (str): 反馈来源的唯一标识符（如用户ID）。
        logic_strength (float): 反馈内容的逻辑强度 (0.0 到 1.0)。
        content_vector (np.ndarray): 反馈内容的向量表示。
        confidence (float): 反馈者自身的自信程度 (0.0 到 1.0)。
    """
    source_id: str
    logic_strength: float
    content_vector: np.ndarray
    confidence: float

class ThreeBodyGameWeighting:
    """
    基于三体博弈（AI-人类-环境）的权重更新机制。
    
    该类实现了在共生系统中，根据历史可靠性、逻辑强度和冲突程度，
    动态计算人类反馈的权威权重，从而调整知识更新的步长。
    
    Attributes:
        base_lr (float): 基础学习率。
        momentum (float): 动量因子，用于平滑更新。
        reliability_history (Dict[str, float]): 记录各来源的历史可靠性。
        knowledge_graph (np.ndarray): 当前AI系统的稳固知识节点向量。
    """
    
    def __init__(self, 
                 base_lr: float = 0.01, 
                 momentum: float = 0.9,
                 initial_knowledge_dim: int = 128):
        """
        初始化三体博弈权重更新机制。
        
        Args:
            base_lr: 基础学习率。
            momentum: 优化器动量。
            initial_knowledge_dim: 知识向量的维度。
        """
        self.base_lr = base_lr
        self.momentum = momentum
        self.reliability_history: Dict[str, float] = {}
        # 模拟环境/知识库状态
        self.knowledge_graph = np.random.rand(initial_knowledge_dim)
        self._velocity = np.zeros_like(self.knowledge_graph)
        
        logger.info("ThreeBodyGameWeighting initialized with base_lr=%.4f", base_lr)

    def _calculate_conflict_score(self, feedback_vector: np.ndarray) -> float:
        """
        辅助函数：计算反馈与现有稳固知识节点的冲突程度。
        
        使用余弦相似度，值越低（负值）表示冲突越大。
        将相似度映射到 [0, 1] 的冲突分数，1表示完全冲突，0表示完全一致。
        
        Args:
            feedback_vector: 反馈内容的向量。
            
        Returns:
            float: 冲突分数 (0.0 到 1.0)。
        """
        if np.linalg.norm(feedback_vector) == 0 or np.linalg.norm(self.knowledge_graph) == 0:
            return 0.5  # 默认中等冲突
        
        # 计算余弦相似度 [-1, 1]
        similarity = np.dot(feedback_vector, self.knowledge_graph) / (
            np.linalg.norm(feedback_vector) * np.linalg.norm(self.knowledge_graph)
        )
        
        # 归一化到 [0, 1] 冲突区间: conflict = (1 - similarity) / 2
        conflict = (1.0 - similarity) / 2.0
        
        # 数据边界检查
        conflict = np.clip(conflict, 0.0, 1.0)
        return float(conflict)

    def update_reliability(self, source_id: str, reward_signal: float) -> None:
        """
        根据环境反馈更新来源的历史可靠性。
        
        这是'环境'作为第三体对'人类'反馈质量的校准。
        
        Args:
            source_id: 反馈来源ID。
            reward_signal: 环境给出的奖励信号 (-1.0 到 1.0)。
        """
        if not -1.0 <= reward_signal <= 1.0:
            logger.error("Invalid reward signal: %f. Must be between -1 and 1.", reward_signal)
            raise ValueError("Reward signal must be between -1.0 and 1.0")
            
        current_rel = self.reliability_history.get(source_id, 0.5)
        
        # 使用移动平均更新可靠性
        alpha = 0.1  # 更新速率
        new_rel = current_rel + alpha * (reward_signal - current_rel)
        
        # 确保可靠性在 [0, 1] 之间
        self.reliability_history[source_id] = np.clip(new_rel, 0.0, 1.0)
        logger.debug("Updated reliability for %s: %.4f -> %.4f", source_id, current_rel, new_rel)

    def calculate_authority_weight(self, feedback: FeedbackSignal) -> float:
        """
        核心函数1：计算当前反馈的权威权重。
        
        权重 = Sigmoid(历史可靠性 + 逻辑强度 - 冲突惩罚因子)
        这是一个非线性的博弈平衡过程。
        
        Args:
            feedback: 包含来源、逻辑强度和内容的反馈对象。
            
        Returns:
            float: 动态计算出的权威权重 (0.0 到 1.0)。
        """
        # 1. 获取历史可靠性 (Default 0.5 if unknown)
        r_hist = self.reliability_history.get(feedback.source_id, 0.5)
        
        # 2. 获取逻辑强度
        l_strength = feedback.logic_strength
        
        # 3. 计算冲突程度
        conflict = self._calculate_conflict_score(feedback.content_vector)
        
        # 博弈计算：
        # 如果冲突很大，我们需要更谨慎（降低权重），除非历史可靠性极高。
        # 权重公式：w = 1 / (1 + exp(-(r_hist + l_strength - 2*conflict)))
        # 这里简化为线性加权组合以演示，实际可用更复杂网络
        
        logit = (r_hist * 0.4) + (l_strength * 0.3) + ((1 - conflict) * 0.3)
        
        # Sigmoid 归一化
        weight = 1 / (1 + np.exp(-5 * (logit - 0.5)))
        
        logger.info("Calculated weight for %s: %.4f (Rel: %.2f, Logic: %.2f, Conflict: %.2f)",
                    feedback.source_id, weight, r_hist, l_strength, conflict)
        
        return float(np.clip(weight, 0.0, 1.0))

    def apply_knowledge_update(self, feedback: FeedbackSignal) -> Tuple[np.ndarray, float]:
        """
        核心函数2：根据计算出的权重更新内部知识（模拟权重更新步长）。
        
        结合当前的AI状态、环境约束和人类反馈进行梯度下降式的更新。
        
        Args:
            feedback: 反馈信号对象。
            
        Returns:
            Tuple[np.ndarray, float]: 更新后的知识向量和实际使用的有效学习率。
        """
        try:
            # 1. 计算权威权重
            authority_weight = self.calculate_authority_weight(feedback)
            
            # 2. 计算动态步长 (Learning Rate)
            # 有效学习率 = 基础学习率 * 权重 * 反馈置信度
            effective_lr = self.base_lr * authority_weight * feedback.confidence
            
            # 3. 计算更新向量 (模拟梯度)
            # 目标是将 knowledge 向 feedback 拉近，但受步长控制
            # gradient = (target - current)
            gradient = feedback.content_vector - self.knowledge_graph
            
            # 4. 应用动量更新
            self._velocity = (self.momentum * self._velocity) + (effective_lr * gradient)
            self.knowledge_graph += self._velocity
            
            # 5. 归一化知识向量，防止数值爆炸
            norm = np.linalg.norm(self.knowledge_graph)
            if norm > 1e-6:
                self.knowledge_graph = self.knowledge_graph / norm
            
            logger.info("Knowledge updated. Effective LR: %.6f", effective_lr)
            return self.knowledge_graph.copy(), effective_lr
            
        except Exception as e:
            logger.error("Error during knowledge update: %s", str(e))
            raise RuntimeError("Failed to apply knowledge update") from e

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 初始化系统
    system = ThreeBodyGameWeighting(base_lr=0.1, initial_knowledge_dim=10)
    
    # 2. 模拟反馈数据
    # 场景A：来自一个新用户，逻辑中等，冲突中等
    user_a_id = "user_123"
    vec_a = np.random.rand(10)
    feedback_a = FeedbackSignal(
        source_id=user_a_id,
        logic_strength=0.5,
        content_vector=vec_a,
        confidence=0.8
    )
    
    # 第一次更新
    print("--- Feedback A (First time user) ---")
    _, lr_a = system.apply_knowledge_update(feedback_a)
    print(f"Effective LR: {lr_a:.4f} (Should be moderate)")

    # 3. 模拟环境反馈（证明该用户之前的反馈是错误的）
    print("\n--- Environment Penalizes User A ---")
    system.update_reliability(user_a_id, -0.8)  # 给予负奖励
    
    # 4. 场景B：同一个用户再次反馈，这次逻辑很强，但历史可靠性低
    vec_b = np.random.rand(10)
    feedback_b = FeedbackSignal(
        source_id=user_a_id,
        logic_strength=0.9, # High logic
        content_vector=vec_b,
        confidence=0.9
    )
    
    print("\n--- Feedback B (User A after penalty) ---")
    _, lr_b = system.apply_knowledge_update(feedback_b)
    print(f"Effective LR: {lr_b:.4f} (Should be lower due to bad history despite high logic)")
    
    # 5. 边界测试
    try:
        system.update_reliability(user_a_id, 2.0) # Invalid
    except ValueError as e:
        print(f"\nCaught expected error: {e}")