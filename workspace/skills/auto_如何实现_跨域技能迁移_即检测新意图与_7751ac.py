"""
模块名称: cross_domain_skill_transfer
功能描述: 实现AGI系统中的跨域技能迁移。通过计算新意图与现有SKILL节点拓扑的
         语义与逻辑重叠度，决策是复用现有架构还是触发归纳构建流程。
         
核心逻辑:
1. 计算语义向量距离。
2. 计算逻辑结构（拓扑）重叠度。
3. 综合评估：若 > 0.7 复用，< 0.3 构建，中间状态由外部策略决定。

作者: Senior Python Engineer
创建时间: 2023-10-27
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TransferDecision(Enum):
    """迁移决策枚举类"""
    REUSE = "REUSE_ARCHITECTURE"      # 复用现有架构
    CONSTRUCT = "INDUCTIVE_BUILD"     # 归纳构建
    UNCERTAIN = "REVIEW_REQUIRED"     # 需人工或更复杂策略复核

@dataclass
class SkillNode:
    """
    现有技能节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识符。
        embedding (np.ndarray): 技能的语义向量表示 (e.g., 768-dim vector)。
        logical_tags (Set[str]): 逻辑结构标签，用于拓扑匹配 (如 'loop', 'api_call', 'io')。
        metadata (Dict[str, Any]): 其他元数据。
    """
    id: str
    embedding: np.ndarray
    logical_tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

class CrossDomainTransferManager:
    """
    管理跨域技能迁移的核心类。
    负责处理新意图与现有技能库的匹配与决策。
    """
    
    def __init__(self, skill_database: List[SkillNode], semantic_weight: float = 0.6):
        """
        初始化迁移管理器。
        
        Args:
            skill_database (List[SkillNode]): 现有的技能节点数据库。
            semantic_weight (float): 语义相似度在综合评分中的权重 (0.0-1.0)。
                                     逻辑结构权重则为 (1 - semantic_weight)。
        """
        if not skill_database:
            logger.warning("初始化技能数据库为空，所有新意图将触发构建流程。")
        
        self.skill_database = skill_database
        self.semantic_weight = semantic_weight
        logger.info(f"CrossDomainTransferManager initialized with {len(skill_database)} skills.")

    def _calculate_semantic_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        辅助函数：计算两个向量之间的余弦相似度。
        
        Args:
            vec_a (np.ndarray): 向量A。
            vec_b (np.ndarray): 向量B。
            
        Returns:
            float: 余弦相似度得分 (0.0 到 1.0)。
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        score = np.dot(vec_a, vec_b) / (norm_a * norm_b)
        # 修正浮点误差，确保范围在 [0, 1]
        return float(np.clip(score, 0.0, 1.0))

    def _calculate_logical_overlap(self, tags_a: Set[str], tags_b: Set[str]) -> float:
        """
        辅助函数：计算逻辑标签集合的Jaccard相似系数。
        
        Args:
            tags_a (Set[str]): 标签集合A。
            tags_b (Set[str]): 标签集合B。
            
        Returns:
            float: Jaccard相似度 (0.0 到 1.0)。
        """
        if not tags_a and not tags_b:
            return 1.0 # 如果两者都为空，视为逻辑结构一致（无结构）
        if not tags_a or not tags_b:
            return 0.0
            
        intersection = len(tags_a.intersection(tags_b))
        union = len(tags_a.union(tags_b))
        
        return intersection / union if union > 0 else 0.0

    def evaluate_transfer_potential(
        self, 
        new_intent_embedding: np.ndarray, 
        new_intent_tags: Set[str],
        top_k: int = 5
    ) -> Tuple[TransferDecision, Optional[SkillNode], float]:
        """
        核心函数：评估新意图的迁移潜力。
        
        流程:
        1. 遍历(或检索)现有技能节点。
        2. 分别计算语义距离和逻辑重叠度。
        3. 加权融合得到最终重叠度。
        4. 根据阈值(>0.7, <0.3)做出决策。
        
        Args:
            new_intent_embedding (np.ndarray): 新意图的向量。
            new_intent_tags (Set[str]): 新意图的逻辑标签。
            top_k (int): 返回最匹配的候选节点数量（日志用）。
            
        Returns:
            Tuple[TransferDecision, Optional[SkillNode], float]: 
                决策结果, 最佳匹配节点(如果复用), 最高重叠度分数。
        """
        # 数据验证
        if not isinstance(new_intent_embedding, np.ndarray):
            raise TypeError("输入必须是numpy数组")
        if new_intent_embedding.size == 0:
            raise ValueError("意图向量不能为空")

        if not self.skill_database:
            return TransferDecision.CONSTRUCT, None, 0.0

        max_score = -1.0
        best_match: Optional[SkillNode] = None

        # 在实际生产中，此处应使用向量数据库(如Milvus/Faiss)进行ANN检索
        # 这里为了演示算法逻辑，进行全量计算
        for skill in self.skill_database:
            # 1. 语义对齐
            sem_sim = self._calculate_semantic_similarity(new_intent_embedding, skill.embedding)
            
            # 2. 逻辑结构对齐
            logic_sim = self._calculate_logical_overlap(new_intent_tags, skill.logical_tags)
            
            # 3. 综合评估 (加权平均)
            # 语义捕捉"做什么"，逻辑捕捉"怎么做"的结构
            combined_score = (self.semantic_weight * sem_sim) + ((1 - self.semantic_weight) * logic_sim)
            
            if combined_score > max_score:
                max_score = combined_score
                best_match = skill

        # 决策逻辑
        decision = TransferDecision.UNCERTAIN
        
        if max_score > 0.7:
            decision = TransferDecision.REUSE
            logger.info(f"Decision: REUSE. Score: {max_score:.4f}. Matched Skill: {best_match.id if best_match else None}")
        elif max_score < 0.3:
            decision = TransferDecision.CONSTRUCT
            logger.info(f"Decision: CONSTRUCT. Score: {max_score:.4f}. No suitable architecture found.")
        else:
            decision = TransferDecision.UNCERTAIN
            logger.warning(f"Decision: UNCERTAIN. Score: {max_score:.4f}. Requires further strategy.")

        return decision, best_match, max_score

def mock_embedding_generator(dim: int = 128) -> np.ndarray:
    """生成模拟的归一化向量"""
    vec = np.random.rand(dim)
    return vec / np.linalg.norm(vec)

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 构造模拟的现有技能库
    # 包含 id, 向量, 逻辑标签
    existing_skills = [
        SkillNode(
            id="skill_001_data_cleaning",
            embedding=mock_embedding_generator(),
            logical_tags={"pandas", "loop", "io", "exception_handling"}
        ),
        SkillNode(
            id="skill_002_web_scraping",
            embedding=mock_embedding_generator(),
            logical_tags={"requests", "html_parsing", "loop"}
        ),
        SkillNode(
            id="skill_003_api_integration",
            embedding=mock_embedding_generator(),
            logical_tags={"requests", "json", "authentication"}
        )
    ]

    # 2. 初始化管理器
    manager = CrossDomainTransferManager(existing_skills)

    # 3. 场景 A: 尝试迁移一个高度相关的技能 (修改现有Web爬虫)
    # 假设新意图是爬取特定API数据，逻辑相似，向量我们手动调整得接近一点 skill_002
    print("\n--- Scenario A: High Overlap ---")
    new_intent_vec_a = existing_skills[1].embedding * 0.9 + mock_embedding_generator() * 0.1
    new_intent_tags_a = {"requests", "html_parsing", "new_feature"}
    
    decision_a, match_a, score_a = manager.evaluate_transfer_potential(
        new_intent_embedding=new_intent_vec_a,
        new_intent_tags=new_intent_tags_a
    )
    print(f"Result A: {decision_a.value}, Matched: {match_a.id if match_a else 'None'}, Score: {score_a:.4f}")

    # 4. 场景 B: 全新领域 (比如控制无人机，与现有数据处理技能无关)
    print("\n--- Scenario B: Low Overlap ---")
    new_intent_vec_b = mock_embedding_generator() # 随机向量，大概率距离很远
    new_intent_tags_b = {"drone_control", "hardware_io", "real_time"}
    
    decision_b, match_b, score_b = manager.evaluate_transfer_potential(
        new_intent_embedding=new_intent_vec_b,
        new_intent_tags=new_intent_tags_b
    )
    print(f"Result B: {decision_b.value}, Matched: {match_b.id if match_b else 'None'}, Score: {score_b:.4f}")

    # 5. 边界检查示例
    print("\n--- Scenario C: Invalid Input ---")
    try:
        manager.evaluate_transfer_potential(np.array([]), set())
    except ValueError as e:
        print(f"Caught expected error: {e}")