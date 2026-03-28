"""
模块名称: adaptive_entropy_protocol.py
描述: 实现基于信息熵的动态提示词协议，用于人机共生系统的接口层。
      该模块根据用户实时反馈（修正频率、犹豫时间）动态调整认知颗粒度，
      并通过语义向量聚类将高层意图拆解为特定的技能组合。

核心功能:
1. 计算用户交互过程中的实时信息熵。
2. 基于熵值动态调整系统的认知颗粒度。
3. 利用语义向量相似度将意图映射到现有的技能节点。

作者: AGI System Architect
版本: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveGranularity(Enum):
    """定义系统的认知颗粒度等级"""
    MACRO = 0      # 宏观：处理模糊意图，宽泛搜索
    MESO = 1       # 中观：平衡模式，常规交互
    MICRO = 2      # 微观：高精度模式，处理复杂或修正较多的任务

@dataclass
class UserFeedback:
    """用户实时反馈数据结构"""
    hesitation_time_ms: float = 0.0  # 犹豫时间
    corrections_count: int = 0       # 修正次数
    scroll_events: int = 0           # 滚动/查看细节事件
    explicit_rating: Optional[int] = None # 显式评分 (1-5)

@dataclass
class SkillNode:
    """技能节点数据结构"""
    id: str
    name: str
    description: str
    embedding: Optional[np.ndarray] = None

class EntropyProtocolEngine:
    """
    基于信息熵的动态协议引擎。
    负责监测用户状态，计算认知负荷，并调度技能节点。
    """

    def __init__(self, skill_nodes: List[SkillNode], config: Optional[Dict] = None):
        """
        初始化引擎。

        Args:
            skill_nodes (List[SkillNode]): 系统当前拥有的技能节点列表（如374个节点）。
            config (Optional[Dict]): 配置参数，包含熵的阈值等。
        """
        self.skill_nodes = skill_nodes
        self.config = config or {
            'hesitation_threshold_high': 3000.0,  # ms
            'hesitation_threshold_low': 500.0,
            'correction_weight': 0.4,
            'hesitation_weight': 0.6,
            'similarity_threshold': 0.75
        }
        self._validate_skill_nodes()
        logger.info(f"EntropyProtocolEngine initialized with {len(skill_nodes)} skills.")

    def _validate_skill_nodes(self) -> None:
        """验证技能节点的完整性和维度"""
        if not self.skill_nodes:
            raise ValueError("Skill nodes list cannot be empty.")
        
        # 检查向量维度一致性 (模拟检查，假设embedding不为空)
        first_dim = self.skill_nodes[0].embedding.shape[0] if self.skill_nodes[0].embedding is not None else 0
        for node in self.skill_nodes:
            if node.embedding is None:
                logger.warning(f"Skill {node.id} has no embedding.")
            elif node.embedding.shape[0] != first_dim:
                raise ValueError(f"Embedding dimension mismatch for skill {node.id}.")

    def calculate_cognitive_entropy(self, feedback: UserFeedback) -> float:
        """
        核心函数 1: 计算当前的认知信息熵。
        
        基于用户的犹豫时间和修正次数，映射到一个标准化的熵值 [0, 1]。
        高熵值意味着用户困惑或任务复杂，需要系统提供更细致（微观）的响应。

        Args:
            feedback (UserFeedback): 用户实时反馈对象。

        Returns:
            float: 标准化的认知熵值 (0.0 到 1.0)。
        """
        try:
            # 1. 处理犹豫时间成分 (非线性映射)
            h_time = feedback.hesitation_time_ms
            if h_time < self.config['hesitation_threshold_low']:
                time_score = 0.0
            elif h_time > self.config['hesitation_threshold_high']:
                time_score = 1.0
            else:
                # Sigmoid-like scaling
                range_val = self.config['hesitation_threshold_high'] - self.config['hesitation_threshold_low']
                time_score = (h_time - self.config['hesitation_threshold_low']) / range_val
            
            # 2. 处理修正次数成分 (对数增长)
            # 假设5次以上修正视为高熵
            correction_score = min(1.0, np.log1p(feedback.corrections_count) / np.log1p(5))
            
            # 3. 加权融合
            entropy = (
                time_score * self.config['hesitation_weight'] + 
                correction_score * self.config['correction_weight']
            )
            
            logger.debug(f"Calculated Entropy: {entropy:.4f} (Time: {time_score:.2f}, Corr: {correction_score:.2f})")
            return np.clip(entropy, 0.0, 1.0)

        except Exception as e:
            logger.error(f"Error calculating entropy: {e}")
            return 0.5  # 返回中间值作为故障安全

    def map_intent_to_skills(
        self, 
        intent_vector: np.ndarray, 
        current_entropy: float
    ) -> Tuple[CognitiveGranularity, List[SkillNode]]:
        """
        核心函数 2: 将高层意图映射到具体的技能组合。
        
        根据当前的熵值决定聚类的颗粒度（阈值）。
        高熵 -> 降低阈值，选择更少、更精准的技能 (Micro)。
        低熵 -> 提高阈值，选择更广泛、关联性弱的技能组合。

        Args:
            intent_vector (np.ndarray): 用户意图的语义向量。
            current_entropy (float): 当前计算出的认知熵。

        Returns:
            Tuple[CognitiveGranularity, List[SkillNode]]: 
                建议的认知模式 和 激活的技能节点列表。
        """
        if intent_vector is None or intent_vector.size == 0:
            raise ValueError("Intent vector cannot be empty.")

        # 1. 确定认知颗粒度
        granularity = self._determine_granularity(current_entropy)
        
        # 2. 动态调整相似度阈值
        # 熵越高，我们越需要精确匹配 (高阈值)；熵越低，我们可以探索性匹配 (低阈值)?
        # 这里采用反向策略：高熵(困惑) -> 需要更聚焦的技能 (高阈值，只选最相关的)
        # 低熵(流畅) -> 可以进行更宽泛的联想 (低阈值，多选几个背景技能)
        # 但如果是为了解决困惑，我们需要Micro级别的精确。
        # 此处逻辑：高熵 = 困惑 = 需要高精度 = 高阈值 (只保留最相似的)
        
        base_threshold = self.config['similarity_threshold']
        if granularity == CognitiveGranularity.MICRO:
            dynamic_threshold = base_threshold + 0.10  # 0.85, 更严格
        elif granularity == CognitiveGranularity.MACRO:
            dynamic_threshold = base_threshold - 0.15  # 0.60, 更宽泛
        else:
            dynamic_threshold = base_threshold

        logger.info(f"Mode: {granularity.name}, Dynamic Threshold: {dynamic_threshold}")

        # 3. 语义匹配 (替代复杂的聚类，此处使用余弦相似度进行Top-K筛选)
        activated_skills = []
        try:
            for node in self.skill_nodes:
                if node.embedding is None:
                    continue
                
                # 辅助函数计算相似度
                similarity = self._cosine_similarity(intent_vector, node.embedding)
                
                if similarity >= dynamic_threshold:
                    activated_skills.append(node)
            
            # 边界检查：如果没有匹配到任何技能，返回最相似的一个
            if not activated_skills:
                logger.warning("No skills matched dynamic threshold. Falling back to best match.")
                best_node = max(
                    self.skill_nodes, 
                    key=lambda n: self._cosine_similarity(intent_vector, n.embedding) if n.embedding is not None else 0
                )
                activated_skills.append(best_node)

            return granularity, activated_skills

        except Exception as e:
            logger.error(f"Error during skill mapping: {e}")
            raise RuntimeError("Skill mapping failed.") from e

    def _determine_granularity(self, entropy: float) -> CognitiveGranularity:
        """辅助函数: 根据熵值确定认知颗粒度"""
        if entropy > 0.75:
            return CognitiveGranularity.MICRO
        elif entropy < 0.35:
            return CognitiveGranularity.MACRO
        else:
            return CognitiveGranularity.MESO

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """辅助函数: 计算余弦相似度"""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(vec_a, vec_b) / (norm_a * norm_b)

# ==========================================
# 使用示例与模拟运行
# ==========================================
if __name__ == "__main__":
    # 1. 模拟生成374个技能节点 (维度设为128)
    NUM_SKILLS = 374
    VECTOR_DIM = 128
    mock_skills = []
    
    print("Initializing mock skill database...")
    for i in range(NUM_SKILLS):
        # 生成随机向量并归一化
        vec = np.random.randn(VECTOR_DIM)
        vec = vec / np.linalg.norm(vec)
        
        mock_skills.append(SkillNode(
            id=f"skill_{i:03d}",
            name=f"Capability_Node_{i}",
            description="Autogenerated mock skill",
            embedding=vec
        ))

    # 2. 初始化引擎
    engine = EntropyProtocolEngine(skill_nodes=mock_skills)

    # 3. 模拟场景 A: 用户非常犹豫且频繁修改 (高熵)
    print("\n--- Scenario A: Confused User (High Entropy) ---")
    feedback_confused = UserFeedback(hesitation_time_ms=4500, corrections_count=3)
    
    # 计算熵
    entropy = engine.calculate_cognitive_entropy(feedback_confused)
    
    # 模拟意图向量 (随机生成)
    user_intent_vec = np.random.randn(VECTOR_DIM)
    
    # 映射技能
    granularity, skills = engine.map_intent_to_skills(user_intent_vec, entropy)
    
    print(f"User Entropy: {entropy:.2f}")
    print(f"System Response Granularity: {granularity.name}")
    print(f"Activated Skills Count: {len(skills)}")
    print(f"Top Skill ID: {skills[0].id}")

    # 4. 模拟场景 B: 用户非常流畅 (低熵)
    print("\n--- Scenario B: Expert User (Low Entropy) ---")
    feedback_expert = UserFeedback(hesitation_time_ms=200, corrections_count=0)
    
    entropy_low = engine.calculate_cognitive_entropy(feedback_expert)
    granularity_low, skills_low = engine.map_intent_to_skills(user_intent_vec, entropy_low)
    
    print(f"User Entropy: {entropy_low:.2f}")
    print(f"System Response Granularity: {granularity_low.name}")
    print(f"Activated Skills Count: {len(skills_low)} (Should be higher/more inclusive)")