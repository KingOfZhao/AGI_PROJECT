"""
模块: auto_人机共生_意图对齐_当人类通过手把手_c21570
描述: 实现基于人类示教/修正的实时价值函数更新与策略验证系统。
      该模块模拟了一个“人在环”的学习过程，当人类对AI的动作进行修正时，
      系统不仅记录轨迹，还实时更新内部的Q函数，并验证在相似情境下的泛化能力。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class State:
    """
    环境状态表示类。
    用于封装机器人在某一时刻的感知信息。
    """
    features: np.ndarray  # 状态的特征向量
    
    def to_vector(self) -> np.ndarray:
        return self.features
    
    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        return np.array_equal(self.features, other.features)

@dataclass
class Action:
    """
    动作表示类。
    """
    action_id: int
    action_vector: np.ndarray
    
    def to_vector(self) -> np.ndarray:
        return self.action_vector

@dataclass
class ExperienceBuffer:
    """
    经验回放缓冲区，用于存储人类修正的数据。
    """
    buffer_size: int = 1000
    data: deque = field(default_factory=lambda: deque(maxlen=buffer_size))
    
    def add(self, state: State, action: Action, reward: float, next_state: State):
        self.data.append((state, action, reward, next_state))

class HumanGuidedPolicyLearner:
    """
    核心类：基于人类引导的策略学习器。
    
    实现了基于人类修正信号的实时策略更新机制。包含价值函数更新、
    相似度计算和泛化能力测试等功能。
    """
    
    def __init__(self, 
                 state_dim: int = 10, 
                 action_dim: int = 5,
                 learning_rate: float = 0.01,
                 gamma: float = 0.95,
                 similarity_threshold: float = 0.85):
        """
        初始化学习器。
        
        Args:
            state_dim: 状态空间维度
            action_dim: 动作空间维度
            learning_rate: 学习率
            gamma: 折扣因子
            similarity_threshold: 状态相似度阈值，用于泛化测试
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = learning_rate
        self.gamma = gamma
        self.similarity_threshold = similarity_threshold
        
        # 初始化Q函数参数 (简单的线性逼近器用于演示)
        self.q_weights = np.random.randn(state_dim, action_dim) * 0.01
        
        # 经验缓冲区
        self.experience_buffer = ExperienceBuffer()
        
        # 记录人类修正的案例用于验证
        self.correction_cases: List[Dict[str, Any]] = []
        
        logger.info(f"初始化HumanGuidedPolicyLearner: state_dim={state_dim}, action_dim={action_dim}")

    def _validate_inputs(self, state: State, action: Optional[Action] = None):
        """数据验证和边界检查"""
        if state.features.shape[0] != self.state_dim:
            raise ValueError(f"状态维度不匹配: 期望 {self.state_dim}, 实际 {state.features.shape[0]}")
        
        if action is not None:
            if action.action_vector.shape[0] != self.action_dim:
                raise ValueError(f"动作维度不匹配: 期望 {self.action_dim}, 实际 {action.action_vector.shape[0]}")

    def get_ai_action(self, state: State) -> Action:
        """
        [核心函数1] 根据当前价值函数获取AI建议的动作。
        
        Args:
            state: 当前环境状态
            
        Returns:
            Action: AI选择的动作
        """
        try:
            self._validate_inputs(state)
            
            state_vec = state.to_vector()
            # 计算Q值: Q(s, a) = state @ W
            q_values = state_vec @ self.q_weights
            
            # 选择最大Q值的动作
            best_action_id = np.argmax(q_values)
            
            # 生成动作向量 (这里简单使用One-hot编码作为动作表示)
            action_vec = np.zeros(self.action_dim)
            action_vec[best_action_id] = 1.0
            
            logger.debug(f"AI选择动作: {best_action_id}, Q值: {q_values[best_action_id]:.4f}")
            
            return Action(action_id=best_action_id, action_vector=action_vec)
            
        except Exception as e:
            logger.error(f"获取AI动作时发生错误: {str(e)}")
            raise

    def process_human_correction(self, 
                                 state: State, 
                                 corrected_action: Action, 
                                 ai_suggested_action: Action):
        """
        [核心函数2] 处理人类修正，更新内部价值函数。
        
        这是“意图对齐”的关键步骤。当人类修正动作时，我们需要告诉算法：
        在状态S下，动作Corrected_Action比AI_Suggested_Action更好。
        
        Args:
            state: 发生修正时的状态
            corrected_action: 人类提供的修正动作
            ai_suggested_action: AI原本建议的动作
        """
        try:
            self._validate_inputs(state, corrected_action)
            
            state_vec = state.to_vector()
            
            # 1. 计算当前Q值
            current_q_values = state_vec @ self.q_weights
            
            # 2. 定义训练目标
            # 我们提高修正动作的Q值，降低原建议动作的Q值
            # 这里使用一个模拟的奖励差值
            correction_reward = 1.0  # 正向激励修正动作
            target_q = current_q_values.copy()
            
            # 增强修正动作的价值
            target_q[corrected_action.action_id] += self.lr * correction_reward
            
            # 如果AI建议的动作与修正不同，则抑制
            if corrected_action.action_id != ai_suggested_action.action_id:
                target_q[ai_suggested_action.action_id] -= self.lr * correction_reward
            
            # 3. 更新权重 (梯度下降)
            # Loss = (Q_pred - Q_target)^2
            # dL/dW = 2 * (Q_pred - Q_target) * state
            error = (current_q_values - target_q)
            gradient = np.outer(state_vec, error)
            
            self.q_weights -= self.lr * gradient
            
            # 4. 记录修正案例用于验证
            self._record_correction_case(state, corrected_action, ai_suggested_action)
            
            logger.info(f"已处理人类修正: 状态哈希{hash(state.features.tobyps())//10000}, "
                       f"AI动作{ai_suggested_action.action_id} -> 人类动作{corrected_action.action_id}")
            
        except Exception as e:
            logger.error(f"处理人类修正时发生错误: {str(e)}")
            raise

    def _record_correction_case(self, state: State, corrected: Action, original: Action):
        """辅助函数：记录修正案例"""
        self.correction_cases.append({
            "state": state.features.tolist(),
            "corrected_id": corrected.action_id,
            "original_id": original.action_id
        })

    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        [辅助函数] 计算两个状态向量的余弦相似度。
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        cosine_sim = np.dot(vec1, vec2) / (norm1 * norm2)
        # 归一化到 [0, 1]
        return (cosine_sim + 1) / 2

    def verify_generalization(self, 
                              test_state: State, 
                              top_k: int = 3) -> Dict[str, Any]:
        """
        验证在相似情境下的泛化能力。
        
        检查对于与之前修正案例相似的新状态，AI是否选择了正确的动作。
        
        Args:
            test_state: 用于测试的新状态
            top_k: 检索最相似的K个历史修正案例
            
        Returns:
            包含验证结果的字典: {
                'is_aligned': bool, 
                'similarity_score': float, 
                'chosen_action': int,
                'expected_action': int
            }
        """
        if not self.correction_cases:
            logger.warning("没有历史修正案例可供验证泛化能力")
            return {'is_aligned': False, 'error': 'No history'}
            
        try:
            self._validate_inputs(test_state)
            test_vec = test_state.to_vector()
            
            # 寻找最相似的历史修正状态
            max_sim = 0.0
            best_match_case = None
            
            for case in self.correction_cases:
                hist_vec = np.array(case['state'])
                sim = self._calculate_similarity(test_vec, hist_vec)
                if sim > max_sim:
                    max_sim = sim
                    best_match_case = case
            
            # 如果没有足够相似的案例，则无法验证意图对齐
            if max_sim < self.similarity_threshold:
                return {
                    'is_aligned': True, # 默认为真，因为没有参照
                    'note': 'No similar context found to verify alignment',
                    'similarity': max_sim
                }
            
            # 获取当前策略对该测试状态的动作
            current_action = self.get_ai_action(test_state)
            
            # 检查是否与当时人类修正的意图一致
            is_aligned = (current_action.action_id == best_match_case['corrected_id'])
            
            result = {
                'is_aligned': is_aligned,
                'similarity_score': max_sim,
                'chosen_action': current_action.action_id,
                'expected_action': best_match_case['corrected_id'],
                'reference_original': best_match_case['original_id']
            }
            
            logger.info(f"泛化验证: 相似度 {max_sim:.2f}, 对齐状态 {is_aligned}, "
                       f"期望动作 {best_match_case['corrected_id']}, 实际动作 {current_action.action_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"验证泛化能力时发生错误: {str(e)}")
            raise

# 使用示例
if __name__ == "__main__":
    # 1. 初始化系统
    learner = HumanGuidedPolicyLearner(state_dim=4, action_dim=3)
    
    # 2. 模拟一个特定情境 (例如: 障碍物在左边)
    # 状态特征: [距离左边, 距离右边, 速度, 传感器噪声]
    critical_state = State(features=np.array([0.1, 5.0, 1.0, 0.0])) # 左边很近
    
    # 3. AI 做出判断 (初始可能是随机的或错误的)
    ai_action = learner.get_ai_action(critical_state)
    print(f"AI初始建议动作: {ai_action.action_id}")
    
    # 4. 人类介入修正 (假设动作1是"向右转"，人类强制执行动作1)
    human_action = Action(action_id=1, action_vector=np.array([0, 1, 0]))
    
    # 5. 系统处理修正，更新价值函数
    learner.process_human_correction(critical_state, human_action, ai_action)
    
    # 6. 测试泛化能力
    # 创建一个相似但不同的状态 (障碍物依然在左边，但距离稍微变了)
    similar_state = State(features=np.array([0.15, 4.8, 1.1, 0.1]))
    
    # 验证系统是否学会了在相似情况下向右转
    verification = learner.verify_generalization(similar_state)
    
    print("-" * 30)
    print("验证结果:")
    print(json.dumps(verification, indent=2))
    print("-" * 30)
    
    # 7. 再次获取AI动作，确认是否改变
    new_ai_action = learner.get_ai_action(critical_state)
    print(f"修正后AI对原状态的动作: {new_ai_action.action_id}")
    print(f"修正后AI对新状态的动作: {learner.get_ai_action(similar_state).action_id}")