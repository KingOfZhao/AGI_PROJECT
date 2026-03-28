"""
高级技能发现模块：基于结构同构性的动态权重图算法。

该模块实现了一个用于AGI认知架构的算法，旨在从大量已有的技能节点中
自动发现并推荐具有高“结构同构性”的跨域技能对。

核心思想：
通过提取技能节点的多维特征（入度、出度、聚类系数、抽象层级等），
构建归一化的拓扑特征向量。利用余弦相似度结合语义嵌入，计算跨域节点
间的“同构分数”，从而识别出例如“代码重构”与“文章润色”这类隐性连接。
"""

import logging
import random
import numpy as np
from typing import List, Tuple, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 唯一标识符
        domain (str): 所属领域 (e.g., 'Coding', 'Writing')
        description (str): 技能描述
        in_edges (Set[str]): 入度节点ID集合
        out_edges (Set[str]): 出度节点ID集合
        embedding (Optional[np.ndarray]): 语义嵌入向量
    """
    id: str
    domain: str
    description: str
    in_edges: Set[str] = field(default_factory=set)
    out_edges: Set[str] = field(default_factory=set)
    embedding: Optional[np.ndarray] = None

    def __post_init__(self):
        if not isinstance(self.in_edges, set):
            self.in_edges = set(self.in_edges)
        if not isinstance(self.out_edges, set):
            self.out_edges = set(self.out_edges)

class SkillGraphIsomorphismAnalyzer:
    """
    基于结构同构性的技能图分析器。
    
    该类负责构建动态权重图，计算节点的拓扑特征，
    并推荐具有高结构相似性的跨域技能对。
    """
    
    def __init__(self, min_samples: int = 10, top_k: int = 5, alpha: float = 0.6):
        """
        初始化分析器。
        
        Args:
            min_samples (int): 进行分析所需的最小节点数。
            top_k (int): 返回的Top K推荐数量。
            alpha (float): 结构权重与语义权重的混合系数 (0.0-1.0)。
                           1.0 表示纯结构，0.0 表示纯语义。
        """
        self.min_samples = min_samples
        self.top_k = top_k
        self.alpha = alpha
        self._validate_params()
        logger.info(f"SkillGraphIsomorphismAnalyzer initialized with alpha={alpha}")

    def _validate_params(self) -> None:
        """验证初始化参数。"""
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")

    def _extract_topological_features(self, nodes: List[SkillNode]) -> np.ndarray:
        """
        辅助函数：提取并归一化节点的拓扑特征。
        
        Features:
            1. in_degree (入度)
            2. out_degree (出度)
            3. degree_product (度数积)
            4. abstract_level (抽象层级估计，基于出度/入度比)
            
        Args:
            nodes (List[SkillNode]): 节点列表。
            
        Returns:
            np.ndarray: 归一化后的特征矩阵 (N, 4)。
        """
        logger.debug("Extracting topological features...")
        features = []
        for node in nodes:
            in_deg = len(node.in_edges)
            out_deg = len(node.out_edges)
            
            # 估计抽象层级：输出多/输入少通常代表抽象概念或工具
            ratio = (out_deg + 1) / (in_deg + 1) # 加1防止除零
            
            feature_vec = [
                float(in_deg),
                float(out_deg),
                float(in_deg * out_deg),
                np.log1p(ratio) # 使用对数平滑
            ]
            features.append(feature_vec)
            
        matrix = np.array(features)
        
        # 标准化特征
        scaler = StandardScaler()
        try:
            normalized_matrix = scaler.fit_transform(matrix)
        except ValueError as e:
            logger.error(f"Feature scaling failed: {e}")
            return matrix # Fallback to unscaled if scaling fails
            
        return normalized_matrix

    def _calculate_semantic_similarity(self, nodes: List[SkillNode]) -> np.ndarray:
        """
        计算语义相似度矩阵（基于预存的Embedding）。
        如果节点没有Embedding，则返回零矩阵。
        """
        embeddings = []
        for node in nodes:
            if node.embedding is not None:
                embeddings.append(node.embedding)
            else:
                # 如果缺少embedding，用零向量占位，实际应用中应抛出警告或进行encode
                logger.warning(f"Node {node.id} missing embedding, using zero vector.")
                embeddings.append(np.zeros(10)) # 假设维度
                
        if not embeddings:
            return np.zeros((len(nodes), len(nodes)))
            
        emb_matrix = np.array(embeddings)
        return cosine_similarity(emb_matrix)

    def discover_isomorphic_pairs(self, nodes: List[SkillNode]) -> List[Dict[str, Any]]:
        """
        核心函数：发现并推荐跨域技能对。
        
        算法步骤：
        1. 数据验证与清洗。
        2. 计算拓扑特征向量。
        3. 计算语义相似度。
        4. 融合分数：Final_Score = alpha * Structural_Sim + (1-alpha) * Semantic_Sim。
        5. 过滤同域对，排序返回。
        
        Args:
            nodes (List[SkillNode]): 待分析的技能节点列表。
            
        Returns:
            List[Dict[str, Any]]: 推荐列表，包含节点对ID、分数及域信息。
        """
        if len(nodes) < self.min_samples:
            logger.warning(f"Insufficient data: {len(nodes)} nodes provided, need {self.min_samples}.")
            return []

        logger.info(f"Starting analysis for {len(nodes)} nodes...")
        
        # 1. 提取特征
        topo_features = self._extract_topological_features(nodes)
        
        # 2. 计算结构相似度
        struct_sim_matrix = cosine_similarity(topo_features)
        
        # 3. 计算语义相似度
        sem_sim_matrix = self._calculate_semantic_similarity(nodes)
        
        # 4. 融合分数
        final_sim_matrix = (self.alpha * struct_sim_matrix) + ((1 - self.alpha) * sem_sim_matrix)
        
        # 5. 提取跨域高分配
        recommendations = []
        n = len(nodes)
        # 阈值过滤，避免计算量过大
        threshold = 0.7 
        
        for i in range(n):
            for j in range(i + 1, n):
                node_a = nodes[i]
                node_b = nodes[j]
                
                # 必须是跨域
                if node_a.domain == node_b.domain:
                    continue
                    
                score = final_sim_matrix[i, j]
                
                if score > threshold:
                    recommendations.append({
                        "source_id": node_a.id,
                        "source_domain": node_a.domain,
                        "target_id": node_b.id,
                        "target_domain": node_b.domain,
                        "isomorphism_score": float(score),
                        "reason": "High structural and semantic overlap"
                    })
        
        # 排序并截取Top K
        recommendations.sort(key=lambda x: x["isomorphism_score"], reverse=True)
        logger.info(f"Found {len(recommendations)} potential pairs. Returning top {self.top_k}.")
        
        return recommendations[:self.top_k]

# ==========================================
# 使用示例 / Usage Example
# ==========================================

def _generate_mock_data(count: int = 310) -> List[SkillNode]:
    """生成模拟的310个技能节点数据用于测试"""
    domains = ["Software_Engineering", "Creative_Writing", "Data_Science", "Project_Management"]
    nodes = []
    
    for i in range(count):
        domain = random.choice(domains)
        # 模拟特征：代码重构通常有高入度和高出度（中间节点）
        if i == 0:
            node = SkillNode(
                id="skill_code_refactor",
                domain="Software_Engineering",
                description="Refactoring code structure without changing behavior",
                in_edges={"skill_debug", "skill_review"},
                out_edges={"skill_optimize", "skill_clean_arch"},
                embedding=np.random.rand(10) + 0.5 # 随机模拟embedding
            )
        # 模拟特征：文章润色也是中间节点
        elif i == 1:
            node = SkillNode(
                id="skill_text_polishing",
                domain="Creative_Writing",
                description="Polishing text for better readability",
                in_edges={"skill_draft", "skill_proofread"},
                out_edges={"skill_publish", "skill_style_adjust"},
                embedding=np.random.rand(10) + 0.5 # 模拟相似的embedding
            )
        else:
            node = SkillNode(
                id=f"skill_{i}",
                domain=domain,
                description=f"Mock skill number {i}",
                in_edges=set(random.sample(range(1000), random.randint(0, 5))),
                out_edges=set(random.sample(range(1000), random.randint(0, 5))),
                embedding=np.random.rand(10)
            )
        nodes.append(node)
    return nodes

if __name__ == "__main__":
    # 1. 初始化分析器
    analyzer = SkillGraphIsomorphismAnalyzer(alpha=0.7, top_k=3)
    
    # 2. 准备数据 (模拟310个节点)
    skill_nodes = _generate_mock_data(310)
    
    # 3. 执行发现算法
    try:
        pairs = analyzer.discover_isomorphic_pairs(skill_nodes)
        
        print("\n--- Discovered Isomorphic Skill Pairs ---")
        for p in pairs:
            print(f"[{p['isomorphism_score']:.4f}] {p['source_id']} ({p['source_domain']}) <--> {p['target_id']} ({p['target_domain']})")
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")