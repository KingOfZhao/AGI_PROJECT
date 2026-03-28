"""
高级技能映射与动态路由器模块

该模块实现了基于IR结构的动态技能路由系统，用于从大规模技能库中精准定位最匹配的技能组合。
若不存在直接匹配，系统会基于图拓扑结构推荐最接近的技能簇作为参考模板。

核心功能：
1. 基于语义相似度和结构匹配的技能检索
2. 动态技能组合优化
3. 拓扑相似度计算与最近邻推荐

依赖库：
- numpy
- networkx
- scipy

作者: AGI架构组
版本: 1.0.0
"""

import logging
import numpy as np
import networkx as nx
from scipy.spatial import distance
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Skill:
    """技能数据结构"""
    id: str
    name: str
    embedding: np.ndarray
    dependencies: Set[str]
    category: str
    complexity: float

@dataclass
class IRNode:
    """中间表示节点结构"""
    id: str
    type: str
    attributes: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class DynamicSkillRouter:
    """
    动态技能路由器，根据输入IR结构从技能库中匹配最佳技能组合
    
    特性：
    - 支持语义和结构双重匹配
    - 自动处理不完整匹配情况
    - 提供拓扑相似度计算
    
    示例:
        >>> router = DynamicSkillRouter(skill_db)
        >>> ir_graph = ...  # 从Q1生成的IR结构
        >>> best_match = router.find_best_skill_combination(ir_graph)
        >>> if not best_match:
        >>>     similar_clusters = router.find_nearest_skill_clusters(ir_graph)
    """
    
    def __init__(self, skill_database: Dict[str, Skill]):
        """
        初始化路由器
        
        Args:
            skill_database: 技能字典，key为技能ID，value为Skill对象
        """
        self.skill_db = skill_database
        self.skill_graph = self._build_skill_dependency_graph()
        self.embedding_matrix, self.skill_ids = self._prepare_embedding_matrix()
        
        logger.info(f"Initialized router with {len(skill_database)} skills")
    
    def _build_skill_dependency_graph(self) -> nx.DiGraph:
        """
        构建技能依赖关系图
        
        Returns:
            NetworkX有向图表示技能依赖关系
        """
        graph = nx.DiGraph()
        
        for skill_id, skill in self.skill_db.items():
            graph.add_node(skill_id, **skill.__dict__)
            
        for skill_id, skill in self.skill_db.items():
            for dep_id in skill.dependencies:
                if dep_id in self.skill_db:
                    graph.add_edge(skill_id, dep_id)
        
        logger.debug(f"Built skill dependency graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def _prepare_embedding_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        准备技能嵌入矩阵用于快速相似度计算
        
        Returns:
            Tuple of (embedding_matrix, skill_id_list)
        """
        skill_ids = list(self.skill_db.keys())
        embeddings = [self.skill_db[skill_id].embedding for skill_id in skill_ids]
        return np.vstack(embeddings), skill_ids
    
    def find_best_skill_combination(
        self, 
        ir_graph: nx.DiGraph,
        min_similarity: float = 0.85,
        max_complexity: float = 1.0
    ) -> Optional[Dict[str, float]]:
        """
        根据IR图查找最佳技能组合
        
        Args:
            ir_graph: 输入IR结构的有向图
            min_similarity: 最小相似度阈值
            max_complexity: 允许的最大技能复杂度
            
        Returns:
            匹配的技能组合及其得分，格式为 {skill_id: similarity_score}
            如果没有足够好的匹配则返回None
        """
        if not isinstance(ir_graph, nx.DiGraph):
            logger.error("Input must be a NetworkX DiGraph")
            raise ValueError("Input must be a NetworkX DiGraph")
            
        ir_nodes = list(ir_graph.nodes(data=True))
        if not ir_nodes:
            logger.warning("Empty IR graph provided")
            return None
            
        # 计算IR节点的平均嵌入
        ir_embeddings = [attrs.get('embedding') for _, attrs in ir_nodes if 'embedding' in attrs]
        if not ir_embeddings:
            logger.warning("No embeddings found in IR nodes")
            return None
            
        ir_avg_embedding = np.mean(ir_embeddings, axis=0)
        
        # 计算与所有技能的相似度
        similarities = 1 - distance.cdist(
            [ir_avg_embedding], 
            self.embedding_matrix, 
            'cosine'
        )[0]
        
        # 筛选符合条件的技能
        candidate_skills = {
            self.skill_ids[i]: similarities[i]
            for i in range(len(similarities))
            if similarities[i] >= min_similarity and 
               self.skill_db[self.skill_ids[i]].complexity <= max_complexity
        }
        
        if not candidate_skills:
            logger.info("No skills met the similarity and complexity thresholds")
            return None
            
        # 检查技能依赖是否满足
        valid_skills = self._validate_skill_dependencies(candidate_skills)
        
        if not valid_skills:
            logger.info("No valid skill combination found after dependency check")
            return None
            
        logger.info(f"Found {len(valid_skills)} valid skill combinations")
        return valid_skills
    
    def find_nearest_skill_clusters(
        self, 
        ir_graph: nx.DiGraph,
        top_n: int = 3,
        cluster_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找与IR图拓扑最接近的技能簇
        
        Args:
            ir_graph: 输入IR结构的有向图
            top_n: 返回的最佳匹配数量
            cluster_size: 每个簇的大小
            
        Returns:
            技能簇列表，每个包含:
            - skills: 技能ID列表
            - similarity: 整体相似度得分
            - structural_match: 结构匹配得分
        """
        if not isinstance(ir_graph, nx.DiGraph):
            logger.error("Input must be a NetworkX DiGraph")
            raise ValueError("Input must be a NetworkX DiGraph")
            
        # 获取IR图的基本特征
        ir_features = self._extract_graph_features(ir_graph)
        
        # 计算与所有技能簇的相似度
        cluster_scores = []
        
        # 这里简化为使用技能图的社区检测
        communities = nx.community.greedy_modularity_communities(self.skill_graph)
        
        for community in communities[:10]:  # 只检查前10个最大的社区
            if len(community) < cluster_size:
                continue
                
            # 从社区中随机采样技能
            sampled_skills = np.random.choice(
                list(community), 
                size=min(cluster_size, len(community)), 
                replace=False
            )
            
            # 计算特征相似度
            subgraph = self.skill_graph.subgraph(sampled_skills)
            skill_features = self._extract_graph_features(subgraph)
            
            feature_sim = 1 - distance.cosine(ir_features, skill_features)
            structural_sim = self._calculate_structural_similarity(ir_graph, subgraph)
            
            total_score = 0.6 * feature_sim + 0.4 * structural_sim
            
            cluster_scores.append({
                'skills': list(sampled_skills),
                'similarity': total_score,
                'structural_match': structural_sim
            })
        
        # 返回得分最高的簇
        top_clusters = sorted(cluster_scores, key=lambda x: x['similarity'], reverse=True)[:top_n]
        
        logger.info(f"Found {len(top_clusters)} nearest skill clusters")
        return top_clusters
    
    def _validate_skill_dependencies(self, skill_candidates: Dict[str, float]) -> Dict[str, float]:
        """
        验证技能组合的依赖关系是否可满足
        
        Args:
            skill_candidates: 候选技能及其得分
            
        Returns:
            验证通过的技能及其得分
        """
        valid_skills = {}
        
        for skill_id, score in skill_candidates.items():
            skill = self.skill_db[skill_id]
            missing_deps = skill.dependencies - set(self.skill_db.keys())
            
            if not missing_deps:
                valid_skills[skill_id] = score
            else:
                logger.debug(f"Skill {skill_id} has missing dependencies: {missing_deps}")
        
        return valid_skills
    
    def _extract_graph_features(self, graph: nx.DiGraph) -> np.ndarray:
        """
        提取图特征向量
        
        Args:
            graph: 输入图
            
        Returns:
            特征向量
        """
        features = [
            graph.number_of_nodes(),
            graph.number_of_edges(),
            nx.density(graph),
            nx.average_clustering(graph.to_undirected()) if graph.number_of_nodes() > 1 else 0,
            len(list(nx.connected_components(graph.to_undirected())))
        ]
        
        return np.array(features)
    
    def _calculate_structural_similarity(
        self, 
        graph1: nx.DiGraph, 
        graph2: nx.DiGraph
    ) -> float:
        """
        计算两个图的结构相似度
        
        Args:
            graph1: 第一个图
            graph2: 第二个图
            
        Returns:
            结构相似度得分 [0, 1]
        """
        # 简化的结构相似度计算
        node_diff = abs(graph1.number_of_nodes() - graph2.number_of_nodes())
        edge_diff = abs(graph1.number_of_edges() - graph2.number_of_edges())
        
        max_possible = max(
            graph1.number_of_nodes() + graph1.number_of_edges(),
            graph2.number_of_nodes() + graph2.number_of_edges()
        )
        
        if max_possible == 0:
            return 1.0
            
        return 1.0 - (node_diff + edge_diff) / (2 * max_possible)

# 示例用法
if __name__ == "__main__":
    # 创建示例技能数据库
    skill_db = {
        "skill1": Skill(
            id="skill1",
            name="数据预处理",
            embedding=np.random.rand(128),
            dependencies=set(),
            category="数据处理",
            complexity=0.5
        ),
        "skill2": Skill(
            id="skill2",
            name="特征工程",
            embedding=np.random.rand(128),
            dependencies={"skill1"},
            category="数据处理",
            complexity=0.7
        ),
        "skill3": Skill(
            id="skill3",
            name="模型训练",
            embedding=np.random.rand(128),
            dependencies={"skill2"},
            category="机器学习",
            complexity=0.9
        )
    }
    
    # 初始化路由器
    router = DynamicSkillRouter(skill_db)
    
    # 创建示例IR图
    ir_graph = nx.DiGraph()
    ir_graph.add_node("node1", type="data_input", embedding=np.random.rand(128))
    ir_graph.add_node("node2", type="feature_extraction", embedding=np.random.rand(128))
    ir_graph.add_edge("node1", "node2")
    
    # 查找最佳技能组合
    best_match = router.find_best_skill_combination(ir_graph)
    print("Best skill match:", best_match)
    
    # 如果没有直接匹配，查找最近的技能簇
    if not best_match:
        nearest_clusters = router.find_nearest_skill_clusters(ir_graph)
        print("Nearest skill clusters:", nearest_clusters)