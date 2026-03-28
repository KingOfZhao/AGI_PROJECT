"""
上下文记忆层模块：多轮对话中的意图漂移检测与锁定机制。

该模块实现了'意图漂移检测与锁定机制'，用于在多轮代码生成对话中跟踪用户意图。
它区分“意图修改”（硬重置）和“信息补充”（软更新），防止代码生成逻辑因
对话中的“碰撞”（用户改变主意）而陷入混乱。
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentChangeType(Enum):
    """意图变化类型的枚举。"""
    NEW_INTENT = "NEW_INTENT"         # 全新意图
    MODIFICATION = "MODIFICATION"     # 意图修改（碰撞/重置）
    SUPPLEMENT = "SUPPLEMENT"         # 信息补充
    IRRELEVANT = "IRRELEVANT"         # 无关噪声

@dataclass
class IntentState:
    """
    当前意图状态的数据结构。
    
    Attributes:
        main_intent (str): 核心意图描述（如："编写一个爬虫"）。
        constraints (List[str]): 意图的限制条件或具体参数。
        state_vector (np.ndarray): 意图的向量表示，用于计算相似度。
        turn_count (int): 当前意图持续的轮次。
    """
    main_intent: str
    constraints: List[str] = field(default_factory=list)
    state_vector: Optional[np.ndarray] = None
    turn_count: int = 0

class ContextMemoryLayer:
    """
    管理对话上下文并检测意图漂移的核心类。
    
    该类维护一个'当前意图状态向量'，并使用语义相似度来判断
    新的用户输入是对当前任务的修改、补充还是全新的开始。
    """

    def __init__(self, drift_threshold: float = 0.45, supplement_threshold: float = 0.75):
        """
        初始化上下文记忆层。
        
        Args:
            drift_threshold (float): 判定为'意图漂移/修改'的相似度阈值。
                                     低于此值通常意味着话题改变或大幅修改。
            supplement_threshold (float): 判定为'补充'的相似度阈值。
                                          高于此值意味着紧密相关的补充信息。
        """
        if not 0.0 <= drift_threshold <= 1.0:
            raise ValueError("drift_threshold must be between 0 and 1")
        if not 0.0 <= supplement_threshold <= 1.0:
            raise ValueError("supplement_threshold must be between 0 and 1")
            
        self.drift_threshold = drift_threshold
        self.supplement_threshold = supplement_threshold
        self.current_state: Optional[IntentState] = None
        self.history: List[Dict] = [] # 保存历史记录以便回溯
        
        logger.info("ContextMemoryLayer initialized with drift=%.2f, supplement=%.2f", 
                    drift_threshold, supplement_threshold)

    def _mock_embedding_model(self, text: str) -> np.ndarray:
        """
        [辅助函数] 模拟文本嵌入模型。
        
        在实际生产环境中，这会调用 OpenAI Embedding 或 BERT 等模型。
        这里使用简单的哈希向量模拟，仅供演示逻辑。
        
        Args:
            text (str): 输入文本。
            
        Returns:
            np.ndarray: 归一化的模拟向量。
        """
        if not isinstance(text, str):
            raise TypeError("Input for embedding must be a string.")
        
        # 基于文本哈希生成确定性随机向量
        seed = sum(ord(c) for c in text)
        rng = np.random.default_rng(seed)
        vector = rng.random(128) # 128维向量
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _calculate_cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        [辅助函数] 计算两个向量的余弦相似度。
        
        Args:
            vec_a (np.ndarray): 向量A。
            vec_b (np.ndarray): 向量B。
            
        Returns:
            float: 相似度得分 (0.0 到 1.0)。
        """
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))

    def process_user_input(self, user_input: str) -> Tuple[IntentChangeType, IntentState]:
        """
        处理用户输入并更新上下文状态。
        
        这是核心函数，负责检测意图漂移、修改或补充。
        
        Args:
            user_input (str): 当前轮次用户的输入字符串。
            
        Returns:
            Tuple[IntentChangeType, IntentState]: 返回变化的类型和更新后的意图状态。
        
        Raises:
            ValueError: 如果输入为空。
        """
        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")
            
        logger.info(f"Processing input: '{user_input}'")
        
        # 1. 获取当前输入的向量表示
        input_vector = self._mock_embedding_model(user_input)
        
        # 2. 如果没有历史状态，直接创建新状态
        if self.current_state is None:
            logger.info("No existing intent found. Creating new intent.")
            new_state = IntentState(
                main_intent=user_input,
                state_vector=input_vector,
                turn_count=1
            )
            self.current_state = new_state
            self.history.append({"type": IntentChangeType.NEW_INTENT, "content": user_input})
            return IntentChangeType.NEW_INTENT, new_state

        # 3. 计算与当前意图状态向量的相似度
        # 注意：为了简化，我们这里比较的是整句向量与意图核心向量的相似度
        current_vector = self.current_state.state_vector
        similarity = self._calculate_cosine_similarity(input_vector, current_vector)
        
        logger.debug(f"Similarity score: {similarity:.4f}")
        
        # 4. 核心逻辑：意图漂移检测与锁定机制
        # 检测关键词逻辑 (简化版，实际应使用NLP分类器)
        is_explicit_change = any(kw in user_input for kw in ["不", "重写", "改成", "错了", "换"])
        
        change_type: IntentChangeType
        
        if is_explicit_change or similarity < self.drift_threshold:
            # 情况 A: 意图漂移 (Drift) / 碰撞
            # 用户可能修改了目标，或者开启了一个新任务。
            # 系统需要决定是覆盖还是新建。这里采用“锁定并重置”策略。
            logger.warning("Intent Drift detected! Resetting context.")
            self.current_state = IntentState(
                main_intent=user_input,
                state_vector=input_vector,
                turn_count=1
            )
            change_type = IntentChangeType.MODIFICATION
            
        elif similarity >= self.supplement_threshold:
            # 情况 B: 信息补充 (Supplement)
            # 用户在当前意图上增加细节。
            logger.info("Input recognized as supplement to current intent.")
            self.current_state.constraints.append(user_input)
            self.current_state.turn_count += 1
            # 融合向量：更新状态向量以包含新信息
            self._update_state_vector(input_vector)
            change_type = IntentChangeType.SUPPLEMENT
            
        else:
            # 情况 C: 模糊地带或无关信息
            # 可能是闲聊或轻微的指令修正。暂时标记为无关，不改变核心状态。
            logger.info("Input irrelevant or ambiguous. Maintaining current intent.")
            change_type = IntentChangeType.IRRELEVANT

        self.history.append({"type": change_type, "content": user_input})
        return change_type, self.current_state

    def _update_state_vector(self, new_vector: np.ndarray, alpha: float = 0.3):
        """
        [内部方法] 更新当前状态向量，融合新的语义信息。
        
        Args:
            new_vector (np.ndarray): 新输入的向量。
            alpha (float): 新信息的权重。
        """
        if self.current_state is None:
            return
            
        old_vector = self.current_state.state_vector
        updated_vector = (1 - alpha) * old_vector + alpha * new_vector
        
        # 重新归一化
        norm = np.linalg.norm(updated_vector)
        if norm > 0:
            updated_vector = updated_vector / norm
            
        self.current_state.state_vector = updated_vector

    def get_current_context_for_prompt(self) -> str:
        """
        获取用于代码生成的格式化上下文字符串。
        
        Returns:
            str: 包含核心意图和限制条件的格式化字符串。
        """
        if not self.current_state:
            return "无上下文信息。"
            
        constraints_text = "\n".join([f"- {c}" for c in self.current_state.constraints])
        return (
            f"【当前核心任务】: {self.current_state.main_intent}\n"
            f"【已确认的细节/限制】:\n{constraints_text}\n"
            f"【已持续轮次】: {self.current_state.turn_count}"
        )

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化系统
    memory = ContextMemoryLayer(drift_threshold=0.4, supplement_threshold=0.7)
    
    print("--- 轮次 1: 初始意图 ---")
    intent_type, state = memory.process_user_input("请帮我写一个Python函数来计算斐波那契数列")
    print(f"类型: {intent_type.value}")
    print(f"状态: {state.main_intent}")
    print("-" * 30)

    print("\n--- 轮次 2: 补充信息 ---")
    # 这里的语义应该高度相关，被识别为 SUPPLEMENT
    intent_type, state = memory.process_user_input("请确保使用迭代法而不是递归，防止栈溢出")
    print(f"类型: {intent_type.value}")
    print(f"状态: {state.main_intent}")
    print(f"限制: {state.constraints}")
    print("-" * 30)

    print("\n--- 轮次 3: 意图漂移/修改 (碰撞) ---")
    # 这里语义发生剧烈变化，或者包含否定词，被识别为 MODIFICATION
    # 系统锁定了新的意图，丢弃了斐波那契数列的逻辑，防止生成的代码混乱
    intent_type, state = memory.process_user_input("算了，斐波那契太简单，帮我写一个快速排序算法")
    print(f"类型: {intent_type.value}")
    print(f"状态: {state.main_intent}")
    print(f"限制: {state.constraints}") # 应该为空，因为是重置
    print("-" * 30)
    
    print("\n--- 最终生成提示词上下文 ---")
    print(memory.get_current_context_for_prompt())