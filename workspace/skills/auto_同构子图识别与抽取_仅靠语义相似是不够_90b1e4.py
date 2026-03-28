"""
高级AGI技能模块：跨域同构子图识别与抽取

本模块实现了基于结构一致性的图同构识别算法，超越了简单的语义相似度匹配。
核心思想是：即使节点语义完全不同（如"狼-羊"与"微软-初创公司"），只要其
在拓扑结构中的角色（度中心性、聚类系数、路径位置）一致，即判定为同构。

算法流程：
1. 结构指纹提取：计算源图和目标图中每个节点的多维结构特征向量
2. 拓扑对齐：通过匈牙利算法寻找最优的节点映射关系
3. 同构概率计算：基于结构相似度和映射一致性计算概率分数

作者: AGI Systems
版本: 2.1.0
创建日期: 2024-03-15
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
import networkx as nx

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """图节点数据结构"""
    node_id: str
    domain: str  # 领域标签（如'biology', 'business'）
    semantic_label: str  # 语义标签（如'predator', 'company'）
    features: Optional[np.ndarray] = None


@dataclass
class MetaStructure:
    """元结构定义：抽象的拓扑模式"""
    structure_id: str
    nodes: List[str]  # 角色标签（如['alpha', 'beta', 'gamma']）
    edges: List[Tuple[str, str]]  # 角色之间的连接关系
    description: str


class StructuralFingerprintExtractor:
    """
    结构指纹提取器
    
    计算图中每个节点的多维结构特征，包括：
    - 度中心性
    - 聚类系数
    - 平均邻居度
    - 结构孔洞指数
    - k-core值
    """
    
    def __init__(self, feature_dims: int = 5):
        """
        初始化指纹提取器
        
        Args:
            feature_dims: 特征维度数量
        """
        self.feature_dims = feature_dims
        logger.info(f"初始化结构指纹提取器，特征维度: {feature_dims}")
    
    def compute_fingerprint(self, graph: nx.Graph, node_id: str) -> np.ndarray:
        """
        计算单个节点的结构指纹
        
        Args:
            graph: NetworkX图对象
            node_id: 目标节点ID
            
        Returns:
            结构指纹向量（归一化后的特征数组）
            
        Raises:
            ValueError: 当节点不存在于图中时
        """
        if node_id not in graph:
            error_msg = f"节点 {node_id} 不存在于图中"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # 计算度中心性（归一化）
            degree = nx.degree_centrality(graph)[node_id]
            
            # 计算聚类系数
            clustering = nx.clustering(graph, node_id)
            
            # 计算平均邻居度
            neighbors = list(graph.neighbors(node_id))
            if neighbors:
                neighbor_degrees = [graph.degree(n) for n in neighbors]
                avg_neighbor_degree = np.mean(neighbor_degrees) / (len(graph) - 1)
            else:
                avg_neighbor_degree = 0.0
            
            # 计算结构孔洞指数（约束系数的补数）
            constraint = nx.constraint(graph, [node_id]).get(node_id, 1.0)
            structural_hole = 1.0 - constraint
            
            # 计算k-core值（归一化）
            core_numbers = nx.core_number(graph)
            max_core = max(core_numbers.values()) if core_numbers else 1
            k_core = core_numbers.get(node_id, 0) / max_core if max_core > 0 else 0
            
            fingerprint = np.array([
                degree,
                clustering,
                avg_neighbor_degree,
                structural_hole,
                k_core
            ], dtype=np.float32)
            
            # 确保没有NaN或Inf值
            fingerprint = np.nan_to_num(fingerprint, nan=0.0, posinf=1.0, neginf=0.0)
            
            logger.debug(f"节点 {node_id} 的结构指纹: {fingerprint}")
            return fingerprint
            
        except Exception as e:
            logger.error(f"计算节点 {node_id} 结构指纹时出错: {str(e)}")
            raise
    
    def compute_all_fingerprints(self, graph: nx.Graph) -> Dict[str, np.ndarray]:
        """
        计算图中所有节点的结构指纹
        
        Args:
            graph: NetworkX图对象
            
        Returns:
            节点ID到结构指纹的映射字典
        """
        fingerprints = {}
        for node in graph.nodes():
            try:
                fingerprints[node] = self.compute_fingerprint(graph, node)
            except ValueError as e:
                logger.warning(f"跳过节点 {node}: {str(e)}")
                continue
        
        logger.info(f"成功计算 {len(fingerprints)} 个节点的结构指纹")
        return fingerprints


def compute_structural_similarity(
    fp1: np.ndarray,
    fp2: np.ndarray,
    metric: str = 'cosine'
) -> float:
    """
    计算两个结构指纹之间的相似度
    
    Args:
        fp1: 第一个结构指纹向量
        fp2: 第二个结构指纹向量
        metric: 相似度度量方法 ('cosine', 'euclidean', 'correlation')
        
    Returns:
        相似度分数 [0, 1]
        
    Raises:
        ValueError: 当输入向量维度不匹配时
    """
    if fp1.shape != fp2.shape:
        raise ValueError(f"指纹维度不匹配: {fp1.shape} vs {fp2.shape}")
    
    if metric == 'cosine':
        norm1 = np.linalg.norm(fp1)
        norm2 = np.linalg.norm(fp2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        similarity = np.dot(fp1, fp2) / (norm1 * norm2)
    elif metric == 'euclidean':
        distance = np.linalg.norm(fp1 - fp2)
        similarity = 1.0 / (1.0 + distance)
    elif metric == 'correlation':
        if np.std(fp1) == 0 or np.std(fp2) == 0:
            return 0.0
        similarity = (np.corrcoef(fp1, fp2)[0, 1] + 1) / 2  # 归一化到[0,1]
    else:
        raise ValueError(f"不支持的相似度度量: {metric}")
    
    # 确保结果在[0, 1]范围内
    return float(np.clip(similarity, 0.0, 1.0))


class IsomorphicSubgraphRecognizer:
    """
    同构子图识别器
    
    识别跨领域的结构同构性，例如：
    - 生物界"捕食者-猎物"模型 ↔ 商界"寡头-长尾"竞争模型
    - 神经网络结构 ↔ 社交网络传播模型
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化同构识别器
        
        Args:
            similarity_threshold: 结构相似度阈值，用于判定同构性
        """
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("相似度阈值必须在 [0, 1] 范围内")
        
        self.similarity_threshold = similarity_threshold
        self.fingerprint_extractor = StructuralFingerprintExtractor()
        logger.info(f"初始化同构子图识别器，相似度阈值: {similarity_threshold}")
    
    def extract_meta_structure(
        self,
        graph: nx.Graph,
        node_roles: Optional[Dict[str, str]] = None
    ) -> MetaStructure:
        """
        从具体图中提取抽象的元结构
        
        Args:
            graph: NetworkX图对象
            node_roles: 可选的节点角色映射（node_id -> role_name）
            
        Returns:
            提取的元结构对象
            
        Example:
            >>> G = nx.karate_club_graph()
            >>> recognizer = IsomorphicSubgraphRecognizer()
            >>> meta = recognizer.extract_meta_structure(G)
            >>> print(meta.description)
        """
        if not graph.nodes():
            raise ValueError("输入图不能为空")
        
        logger.info(f"开始从 {len(graph)} 个节点的图中提取元结构")
        
        # 如果没有提供角色映射，使用聚类算法自动分配角色
        if node_roles is None:
            node_roles = self._auto_assign_roles(graph)
        
        # 提取抽象结构
        unique_roles = list(set(node_roles.values()))
        role_connections = set()
        
        for u, v in graph.edges():
            role_u = node_roles.get(u, 'unknown')
            role_v = node_roles.get(v, 'unknown')
            role_connections.add((role_u, role_v))
        
        # 生成描述
        description = self._generate_structure_description(
            unique_roles, list(role_connections)
        )
        
        meta_struct = MetaStructure(
            structure_id=f"meta_{hash(frozenset(role_connections)) & 0xFFFFFFFF}",
            nodes=unique_roles,
            edges=list(role_connections),
            description=description
        )
        
        logger.info(f"成功提取元结构: {meta_struct.structure_id}")
        return meta_struct
    
    def _auto_assign_roles(self, graph: nx.Graph) -> Dict[str, str]:
        """
        基于结构特征自动为节点分配角色
        
        Args:
            graph: NetworkX图对象
            
        Returns:
            节点ID到角色标签的映射
        """
        fingerprints = self.fingerprint_extractor.compute_all_fingerprints(graph)
        
        # 简单的k-means聚类分配角色
        from sklearn.cluster import KMeans
        
        n_clusters = min(5, len(fingerprints))  # 最多5种角色
        if n_clusters < 2:
            return {node: 'role_0' for node in fingerprints}
        
        features = np.array(list(fingerprints.values()))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features)
        
        role_mapping = {}
        for (node, _), label in zip(fingerprints.items(), labels):
            role_mapping[node] = f'role_{label}'
        
        logger.debug(f"自动分配了 {n_clusters} 种角色")
        return role_mapping
    
    def _generate_structure_description(
        self,
        roles: List[str],
        connections: List[Tuple[str, str]]
    ) -> str:
        """生成元结构的自然语言描述"""
        role_count = len(roles)
        connection_count = len(connections)
        
        # 识别常见模式
        if role_count == 2 and connection_count == 2:
            return "二元对立结构（如：捕食者-猎物、寡头-长尾）"
        elif role_count == 3 and connection_count >= 3:
            return "三元闭环结构（如：食物链、供应链三角）"
        elif any(role in ['hub', 'role_0'] for role in roles):
            return "中心辐射结构（如：星型网络、平台生态）"
        else:
            return f"复杂网络结构（{role_count}种角色，{connection_count}种连接）"
    
    def compute_isomorphism_probability(
        self,
        source_graph: nx.Graph,
        target_graph: nx.Graph,
        source_meta: Optional[MetaStructure] = None,
        target_meta: Optional[MetaStructure] = None
    ) -> Tuple[float, Dict[str, str]]:
        """
        计算两个图之间的同构概率
        
        Args:
            source_graph: 源图（如生物学网络）
            target_graph: 目标图（如商业网络）
            source_meta: 可选的源图元结构（若未提供则自动提取）
            target_meta: 可选的目标图元结构（若未提供则自动提取）
            
        Returns:
            (同构概率, 最优节点映射)
            
        Example:
            >>> bio_graph = nx.DiGraph([('wolf', 'sheep'), ('sheep', 'grass')])
            >>> biz_graph = nx.DiGraph(['google', 'startup'], ['startup', 'user'])
            >>> prob, mapping = recognizer.compute_isomorphism_probability(
            ...     bio_graph, biz_graph
            ... )
            >>> print(f"同构概率: {prob:.2%}")
        """
        # 输入验证
        if not source_graph.nodes() or not target_graph.nodes():
            logger.error("输入图不能为空")
            return 0.0, {}
        
        logger.info(f"开始计算同构概率: 源图{len(source_graph)}节点, 目标图{len(target_graph)}节点")
        
        # 提取元结构（如果未提供）
        if source_meta is None:
            source_meta = self.extract_meta_structure(source_graph)
        if target_meta is None:
            target_meta = self.extract_meta_structure(target_graph)
        
        # 检查角色数量是否匹配
        if len(source_meta.nodes) != len(target_meta.nodes):
            logger.warning(
                f"角色数量不匹配: 源{len(source_meta.nodes)} vs 目标{len(target_meta.nodes)}"
            )
            return 0.0, {}
        
        # 计算结构指纹
        source_fps = self.fingerprint_extractor.compute_all_fingerprints(source_graph)
        target_fps = self.fingerprint_extractor.compute_all_fingerprints(target_graph)
        
        # 构建成本矩阵（用于匈牙利算法）
        source_nodes = list(source_fps.keys())
        target_nodes = list(target_fps.keys())
        
        cost_matrix = np.zeros((len(source_nodes), len(target_nodes)))
        
        for i, s_node in enumerate(source_nodes):
            for j, t_node in enumerate(target_nodes):
                similarity = compute_structural_similarity(
                    source_fps[s_node],
                    target_fps[t_node],
                    metric='cosine'
                )
                # 匈牙利算法求最小化，所以用1 - similarity作为成本
                cost_matrix[i, j] = 1.0 - similarity
        
        # 使用匈牙利算法找到最优映射
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # 计算整体同构概率
        total_similarity = 0.0
        node_mapping = {}
        
        for i, j in zip(row_ind, col_ind):
            s_node = source_nodes[i]
            t_node = target_nodes[j]
            similarity = 1.0 - cost_matrix[i, j]
            
            if similarity >= self.similarity_threshold:
                node_mapping[s_node] = t_node
                total_similarity += similarity
        
        # 归一化概率
        if len(row_ind) > 0:
            isomorphism_prob = total_similarity / len(row_ind)
        else:
            isomorphism_prob = 0.0
        
        logger.info(f"同构概率计算完成: {isomorphism_prob:.2%}, 映射节点数: {len(node_mapping)}")
        
        return float(isomorphism_prob), node_mapping
    
    def find_isomorphic_subgraphs(
        self,
        knowledge_graph: nx.Graph,
        query_pattern: MetaStructure,
        min_probability: float = 0.6
    ) -> List[Tuple[nx.Graph, float]]:
        """
        在大型知识图谱中查找与查询模式同构的子图
        
        Args:
            knowledge_graph: 大型知识图谱（如2532个节点的AGI知识库）
            query_pattern: 查询的元结构模式
            min_probability: 最小同构概率阈值
            
        Returns:
            匹配的子图列表及其同构概率
            
        Raises:
            ValueError: 当知识图谱节点数超过处理能力时
        """
        max_nodes = 5000  # 设置处理上限
        if len(knowledge_graph) > max_nodes:
            logger.warning(f"知识图谱节点数 {len(knowledge_graph)} 超过上限 {max_nodes}")
            raise ValueError(f"知识图谱节点数超过处理上限 {max_nodes}")
        
        logger.info(f"开始在 {len(knowledge_graph)} 节点的知识图谱中搜索同构子图")
        
        # 基于query_pattern的角色数量，提取相应大小的候选子图
        pattern_size = len(query_pattern.nodes)
        candidate_subgraphs = self._extract_candidate_subgraphs(
            knowledge_graph, pattern_size
        )
        
        results = []
        for subgraph in candidate_subgraphs:
            try:
                prob, _ = self.compute_isomorphism_probability(
                    subgraph,
                    nx.Graph(query_pattern.edges)  # 将pattern转为图
                )
                
                if prob >= min_probability:
                    results.append((subgraph, prob))
                    logger.debug(f"发现同构子图，概率: {prob:.2%}")
            
            except Exception as e:
                logger.warning(f"处理候选子图时出错: {str(e)}")
                continue
        
        # 按概率降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"找到 {len(results)} 个同构子图")
        return results
    
    def _extract_candidate_subgraphs(
        self,
        graph: nx.Graph,
        size: int
    ) -> List[nx.Graph]:
        """
        从大图中提取候选子图
        
        使用 ego_graph 和社区检测算法提取语义相关的子图区域
        """
        candidates = []
        
        # 策略1: 基于高度中心节点的ego网络
        degree_centrality = nx.degree_centrality(graph)
        top_hubs = sorted(degree_centrality, key=degree_centrality.get, reverse=True)[:20]
        
        for hub in top_hubs:
            ego = nx.ego_graph(graph, hub, radius=2)
            if len(ego) >= size:
                # 随机采样子图到合适大小
                nodes_sample = list(ego.nodes())[:size * 2]
                subgraph = graph.subgraph(nodes_sample)
                candidates.append(subgraph)
        
        # 策略2: 基于连通分量
        for component in nx.connected_components(graph):
            if len(component) >= size and len(component) <= size * 3:
                candidates.append(graph.subgraph(component))
        
        logger.debug(f"提取了 {len(candidates)} 个候选子图")
        return candidates[:50]  # 限制候选数量以提高效率


# 使用示例
if __name__ == "__main__":
    """完整使用示例：跨领域同构结构识别"""
    
    print("=" * 60)
    print("AGI同构子图识别系统 - 跨领域结构映射演示")
    print("=" * 60)
    
    # 示例1: 构建生物学"捕食者-猎物"网络
    bio_graph = nx.DiGraph()
    bio_graph.add_edges_from([
        ("wolf", "sheep"),
        ("lion", "gazelle"),
        ("eagle", "rabbit"),
        ("sheep", "grass"),
        ("gazelle", "grass"),
        ("rabbit", "clover")
    ])
    
    # 添加节点属性
    for node in bio_graph.nodes():
        if node in ["wolf", "lion", "eagle"]:
            bio_graph.nodes[node]["role"] = "predator"
            bio_graph.nodes[node]["domain"] = "biology"
        elif node in ["grass", "clover"]:
            bio_graph.nodes[node]["role"] = "producer"
            bio_graph.nodes[node]["domain"] = "biology"
        else:
            bio_graph.nodes[node]["role"] = "prey"
            bio_graph.nodes[node]["domain"] = "biology"
    
    # 示例2: 构建商业"寡头-长尾"网络
    biz_graph = nx.DiGraph()
    biz_graph.add_edges_from([
        ("google", "startup_A"),
        ("microsoft", "startup_B"),
        ("amazon", "startup_C"),
        ("startup_A", "user_segment_1"),
        ("startup_B", "user_segment_2"),
        ("startup_C", "user_segment_3")
    ])
    
    for node in biz_graph.nodes():
        if node in ["google", "microsoft", "amazon"]:
            biz_graph.nodes[node]["role"] = "oligarch"
            biz_graph.nodes[node]["domain"] = "business"
        elif "startup" in node:
            biz_graph.nodes[node]["role"] = "challenger"
            biz_graph.nodes[node]["domain"] = "business"
        else:
            biz_graph.nodes[node]["role"] = "market"
            biz_graph.nodes[node]["domain"] = "business"
    
    # 初始化识别器
    recognizer = IsomorphicSubgraphRecognizer(similarity_threshold=0.65)
    
    # 提取元结构
    print("\n[步骤1] 提取生物学网络元结构...")
    bio_meta = recognizer.extract_meta_structure(bio_graph)
    print(f"元结构ID: {bio_meta.structure_id}")
    print(f"角色: {bio_meta.nodes}")
    print(f"描述: {bio_meta.description}")
    
    print("\n[步骤2] 提取商业网络元结构...")
    biz_meta = recognizer.extract_meta_structure(biz_graph)
    print(f"元结构ID: {biz_meta.structure_id}")
    print(f"角色: {biz_meta.nodes}")
    print(f"描述: {biz_meta.description}")
    
    # 计算同构概率
    print("\n[步骤3] 计算跨领域同构概率...")
    prob, mapping = recognizer.compute_isomorphism_probability(
        bio_graph, biz_graph
    )
    
    print(f"\n{'='*40}")
    print(f"同构概率: {prob:.2%}")
    print(f"节点映射关系:")
    for src, tgt in mapping.items():
        src_role = bio_graph.nodes[src].get("role", "unknown")
        tgt_role = biz_graph.nodes[tgt].get("role", "unknown")
        print(f"  {src}({src_role}) ↔ {tgt}({tgt_role})")
    
    print(f"\n{'='*40}")
    print("结论: 生物界'捕食者-猎物'模型与商界'寡头-长尾'模型")
    print(f"      在拓扑结构上具有 {prob:.0%} 的同构性")
    print("      这揭示了跨领域竞争关系的普遍规律")
    
    # 示例3: 在大型知识图谱中搜索
    print("\n[高级功能] 在大型知识图谱中搜索同构模式...")
    
    # 模拟一个较大的知识图谱
    large_kg = nx.barabasi_albert_graph(100, 3, seed=42)
    # 转换为字符串节点ID以模拟真实场景
    large_kg = nx.relabel_nodes(
        large_kg, 
        {i: f"concept_{i}" for i in range(100)}
    )
    
    # 添加随机边以增加复杂度
    for _ in range(50):
        u, v = np.random.randint(0, 100, 2)
        large_kg.add_edge(f"concept_{u}", f"concept_{v}")
    
    print(f"知识图谱规模: {len(large_kg)} 节点, {large_kg.number_of_edges()} 边")
    
    # 搜索与生物网络同构的子图
    matches = recognizer.find_isomorphic_subgraphs(
        large_kg,
        bio_meta,
        min_probability=0.5
    )
    
    print(f"发现 {len(matches)} 个同构子图")
    if matches:
        best_match, best_prob = matches[0]
        print(f"最佳匹配: {len(best_match)} 节点, 同构概率 {best_prob:.2%}")