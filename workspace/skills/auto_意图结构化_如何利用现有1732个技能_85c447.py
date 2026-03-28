"""
模块: auto_意图结构化_如何利用现有1732个技能_85c447
描述: 实现基于图神经网络（GNN）和拓扑结构匹配的意图结构化模块。
      该模块利用现有的技能节点作为语义锚点，通过计算节点间的语义相似度
      与图拓扑结构的匹配度，解决自然语言中的歧义问题，映射出Top-K技能组合。
作者: AGI System Architect
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import heapq
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 技能唯一标识符。
        name (str): 技能名称。
        embedding (np.ndarray): 技能的语义向量表示 (e.g., 768-dim vector)。
        neighbors (Set[str]): 图中相邻节点的ID集合，用于表示拓扑结构。
    """
    id: str
    name: str
    embedding: Optional[np.ndarray] = None
    neighbors: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.embedding is not None and not isinstance(self.embedding, np.ndarray):
            try:
                self.embedding = np.array(self.embedding)
            except Exception as e:
                logger.error(f"Failed to convert embedding to np.ndarray for skill {self.id}: {e}")
                self.embedding = None

@dataclass
class IntentContext:
    """
    意图上下文数据结构。
    
    Attributes:
        raw_text (str): 原始自然语言输入。
        embedding (np.ndarray): 意图的语义向量。
        mentioned_entities (List[str]): 用户明确提到的实体或技能名称（弱监督信号）。
    """
    raw_text: str
    embedding: np.ndarray
    mentioned_entities: List[str] = field(default_factory=list)

@dataclass
class MatchedSkill:
    """
    匹配结果数据结构。
    
    Attributes:
        skill_id (str): 匹配到的技能ID。
        score (float): 综合得分 (语义 + 拓扑)。
        reasoning (str): 解释为何匹配该技能。
    """
    skill_id: str
    score: float
    reasoning: str

class GraphTopologyMatcher:
    """
    核心类：意图结构化与图拓扑匹配器。
    
    该类维护技能图谱，并实现将模糊意图映射到特定技能组合的逻辑。
    它不仅仅是向量搜索，而是结合了图结构信息来消除歧义。
    """

    def __init__(self, skill_nodes: List[SkillNode], embedding_dim: int = 768):
        """
        初始化匹配器。
        
        Args:
            skill_nodes (List[SkillNode]): 现有的技能节点列表。
            embedding_dim (int): 向量维度，用于验证。
        """
        self.embedding_dim = embedding_dim
        self.skill_graph: Dict[str, SkillNode] = {}
        self._load_skills(skill_nodes)
        logger.info(f"GraphTopologyMatcher initialized with {len(self.skill_graph)} skills.")

    def _load_skills(self, skill_nodes: List[SkillNode]) -> None:
        """加载技能节点并构建图索引。"""
        for node in skill_nodes:
            if not node.id or not node.name:
                logger.warning(f"Skipping invalid node with missing id or name.")
                continue
            
            # 数据验证：检查向量维度
            if node.embedding is not None:
                if node.embedding.shape[0] != self.embedding_dim:
                    logger.warning(f"Skill {node.id} has incorrect embedding dim. Expected {self.embedding_dim}, got {node.embedding.shape[0]}. Skipping.")
                    continue
            
            self.skill_graph[node.id] = node

    def _calculate_semantic_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        辅助函数：计算余弦相似度。
        
        Args:
            vec_a (np.ndarray): 向量A
            vec_b (np.ndarray): 向量B
            
        Returns:
            float: 相似度得分 [-1, 1]
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_b == 0 or norm_a == 0:
            return 0.0
        return np.dot(vec_a, vec_b) / (norm_a * norm_b)

    def _calculate_topology_score(self, candidate_id: str, context: IntentContext, initial_candidates: Dict[str, float]) -> float:
        """
        核心算法：计算拓扑结构匹配度。
        
        逻辑：
        如果一个候选节点的邻居节点也在 'initial_candidates' (初步语义匹配列表) 中，
        或者与上下文中的 'mentioned_entities' 相连，则增加其得分。
        这解决了“一词多义”问题——正确的含义通常在图中聚集在一起。
        
        Args:
            candidate_id (str): 当前候选节点ID。
            context (IntentContext): 意图上下文。
            initial_candidates (Dict[str, float]): 初步语义相似度较高的节点集合 {id: score}.
            
        Returns:
            float: 拓扑加成分数。
        """
        if candidate_id not in self.skill_graph:
            return 0.0
        
        node = self.skill_graph[candidate_id]
        topology_score = 0.0
        
        # 1. 检查邻居是否也在高置信度候选列表中
        # 这利用了图的局部聚集特性
        neighbor_hit_count = 0
        for neighbor_id in node.neighbors:
            if neighbor_id in initial_candidates:
                # 如果邻居也是高相关节点，说明这是一个强相关的子图
                neighbor_hit_count += 1
        
        if neighbor_hit_count > 0:
            # 使用对数缩放防止数值过大，并归一化
            topology_score += np.log1p(neighbor_hit_count) * 0.5
        
        # 2. 检查是否连接到用户明确提到的实体
        for entity in context.mentioned_entities:
            if entity in node.neighbors:
                topology_score += 1.0  # 强信号
                
        return topology_score

    def map_intent_to_skills(
        self, 
        context: IntentContext, 
        top_k: int = 5, 
        semantic_weight: float = 0.6, 
        topology_weight: float = 0.4
    ) -> List[MatchedSkill]:
        """
        核心函数：将意图映射为Top-K技能组合。
        
        Args:
            context (IntentContext): 包含向量和元数据的意图上下文。
            top_k (int): 返回的最佳匹配数量。
            semantic_weight (float): 语义相似度的权重。
            topology_weight (float): 拓扑结构匹配度的权重。
            
        Returns:
            List[MatchedSkill]: 排序后的匹配结果列表。
            
        Raises:
            ValueError: 如果输入向量为空或维度不匹配。
        """
        # 1. 数据验证
        if context.embedding is None:
            raise ValueError("Intent embedding cannot be None.")
        if context.embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"Intent embedding dim mismatch. Expected {self.embedding_dim}, got {context.embedding.shape[0]}.")

        logger.info(f"Processing intent: '{context.raw_text}'")
        
        # 2. 第一阶段：全局语义搜索
        # 计算意图向量与所有技能节点的原始相似度
        semantic_scores: Dict[str, float] = {}
        for skill_id, node in self.skill_graph.items():
            if node.embedding is not None:
                score = self._calculate_semantic_similarity(context.embedding, node.embedding)
                semantic_scores[skill_id] = score
        
        if not semantic_scores:
            return []

        # 3. 第二阶段：拓扑结构增强
        # 选取初步候选集（例如前50个）用于构建拓扑上下文
        preliminary_candidates = dict(
            sorted(semantic_scores.items(), key=lambda item: item[1], reverse=True)[:50]
        )
        
        final_scores: List[Tuple[float, str, str]] = [] # (score, id, reasoning)
        
        for skill_id, sem_score in semantic_scores.items():
            # 计算拓扑加成
            topo_score = self._calculate_topology_score(skill_id, context, preliminary_candidates)
            
            # 综合评分归一化
            # 注意：这里假设语义分在[-1, 1]，拓扑分需要根据实际情况归一化，这里简化处理
            # 使用加权和
            combined_score = (sem_score * semantic_weight) + (topo_score * topology_weight)
            
            # 简单的推理生成
            reasoning = f"Sem: {sem_score:.2f}, Topo: {topo_score:.2f}"
            
            final_scores.append((combined_score, skill_id, reasoning))
            
        # 4. 排序并选取 Top-K
        # 使用堆排序处理大量数据效率更高，这里为了清晰直接排序
        final_scores.sort(key=lambda x: x[0], reverse=True)
        
        results: List[MatchedSkill] = []
        for i, (score, skill_id, reasoning) in enumerate(final_scores[:top_k]):
            results.append(MatchedSkill(
                skill_id=skill_id,
                score=float(score),
                reasoning=f"Ranked #{i+1}. {reasoning}. Matched node: {self.skill_graph[skill_id].name}"
            ))
            
        logger.info(f"Mapped intent to {len(results)} skills.")
        return results

# --- 使用示例与测试 ---

def _generate_mock_data(num_skills: int = 100) -> List[SkillNode]:
    """辅助函数：生成模拟技能图谱数据用于测试。"""
    skills = []
    for i in range(num_skills):
        # 生成随机向量，模拟 Embedding
        emb = np.random.rand(768).astype(np.float32)
        
        # 模拟图连接 (环形连接 + 随机连接)
        neighbors = set()
        if i > 0: neighbors.add(str(i-1))
        if i < num_skills - 1: neighbors.add(str(i+1))
        if i > 5: neighbors.add(str(i-5)) # 跨层连接
            
        skills.append(SkillNode(
            id=str(i),
            name=f"skill_{i}",
            embedding=emb,
            neighbors=neighbors
        ))
    return skills

if __name__ == "__main__":
    # 1. 准备环境
    logger.info("Starting demonstration of Intent Structuring...")
    
    # 生成 1732 个技能节点 (模拟真实规模)
    all_skills = _generate_mock_data(1732)
    
    # 假设 'skill_10' 是生成海报的技能
    # 修改其向量，使其与我们将要查询的向量非常接近
    target_skill_idx = 10
    target_vector = np.random.rand(768).astype(np.float32)
    
    # 设置特定技能的向量以便验证结果
    all_skills[target_skill_idx].embedding = target_vector + np.random.normal(0, 0.1, 768) # 加一点噪声
    all_skills[target_skill_idx].name = "generate_poster_v2"
    
    # 设置其邻居 (拓扑结构)
    # 假设 skill_9 是 "image_filter", skill_11 是 "text_layout"
    all_skills[9].name = "image_filter"
    all_skills[11].name = "text_layout"
    
    # 2. 初始化匹配器
    matcher = GraphTopologyMatcher(skill_nodes=all_skills, embedding_dim=768)
    
    # 3. 创建意图上下文
    # 用户意图："帮我搞个像那样的海报" -> 向量应该接近 target_vector
    # 假设用户提到了 "image_filter" 这个实体 (mentioned_entities)
    user_intent = IntentContext(
        raw_text="帮我搞个像那样的海报",
        embedding=target_vector, # 模拟相同的意图
        mentioned_entities=["9"] # 明确提到了ID为9的技能 (image_filter)
    )
    
    # 4. 执行映射
    try:
        matched_results = matcher.map_intent_to_skills(
            context=user_intent,
            top_k=3,
            semantic_weight=0.7,
            topology_weight=0.3
        )
        
        print("\n--- Top-K Matched Skills ---")
        for res in matched_results:
            print(f"Skill ID: {res.skill_id}")
            print(f"Name: {matcher.skill_graph[res.skill_id].name}")
            print(f"Score: {res.score:.4f}")
            print(f"Reasoning: {res.reasoning}")
            print("-" * 30)
            
    except ValueError as e:
        logger.error(f"Error during mapping: {e}")