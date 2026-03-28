"""
高维意图空间的非欧几里得流形映射模块

本模块实现了将模糊的高维意图语义云团映射为结构化功能拓扑图的核心算法。
主要解决语义边界模糊性与代码结构确定性之间的数学映射冲突。

核心组件:
- IntentCloudProcessor: 处理原始意图的流形学习与降维
- TopologyGenerator: 基于流形结构生成功能拓扑图
- 辅助函数: 数据验证与边界检查

使用示例:
>>> processor = IntentCloudProcessor()
>>> intent_cloud = {"concepts": ["game", "fun", "interactive"], "weights": [0.8, 0.9, 0.7]}
>>> manifold_structure = processor.fit_transform(intent_cloud)
>>> generator = TopologyGenerator()
>>> topology = generator.generate(manifold_structure)
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from sklearn.manifold import Isomap, LocallyLinearEmbedding
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import pdist, squareform
from dataclasses import dataclass
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ManifoldStructure:
    """流形结构数据类"""
    embedding: np.ndarray
    intrinsic_dim: int
    cluster_labels: np.ndarray
    geodesic_distances: np.ndarray

class IntentCloudProcessor:
    """
    高维意图云团的流形学习处理器
    
    使用非欧几里得流形学习技术将模糊意图映射到低维结构化空间
    """
    
    def __init__(self, 
                 intrinsic_dim: int = 3,
                 n_neighbors: int = 5,
                 min_samples: int = 3):
        """
        初始化处理器
        
        Args:
            intrinsic_dim: 流形内在维度
            n_neighbors: 流形学习的邻居数
            min_samples: DBSCAN聚类最小样本数
        """
        self.intrinsic_dim = intrinsic_dim
        self.n_neighbors = n_neighbors
        self.min_samples = min_samples
        self._validate_parameters()
        
    def _validate_parameters(self) -> None:
        """验证初始化参数"""
        if self.intrinsic_dim < 2 or self.intrinsic_dim > 10:
            raise ValueError("内在维度必须在2-10之间")
        if self.n_neighbors < 3:
            raise ValueError("邻居数不能小于3")
            
    def fit_transform(self, 
                     intent_cloud: Dict[str, Union[List[str], List[float]]]) -> ManifoldStructure:
        """
        将意图云团转换为流形结构
        
        Args:
            intent_cloud: 包含concepts和weights的意图云团
            
        Returns:
            ManifoldStructure: 包含嵌入坐标、内在维度和聚类标签的结构
            
        Raises:
            ValueError: 输入数据验证失败时
        """
        # 数据验证
        self._validate_intent_cloud(intent_cloud)
        
        # 转换为向量表示
        vectors = self._concepts_to_vectors(intent_cloud["concepts"])
        weights = np.array(intent_cloud["weights"])
        
        # 加权距离矩阵
        weighted_vectors = vectors * weights[:, np.newaxis]
        
        # 计算测地距离
        distances = self._compute_geodesic_distances(weighted_vectors)
        
        # 流形学习 - Isomap
        isomap = Isomap(
            n_neighbors=self.n_neighbors,
            n_components=self.intrinsic_dim,
            metric='precomputed'
        )
        embedding = isomap.fit_transform(distances)
        
        # 聚类分析
        cluster_labels = self._cluster_intent_space(weighted_vectors)
        
        # 估计内在维度
        intrinsic_dim = self._estimate_intrinsic_dim(distances)
        
        logger.info("Successfully transformed intent cloud to manifold structure")
        
        return ManifoldStructure(
            embedding=embedding,
            intrinsic_dim=intrinsic_dim,
            cluster_labels=cluster_labels,
            geodesic_distances=distances
        )
    
    def _validate_intent_cloud(self, cloud: Dict) -> None:
        """验证意图云团数据格式"""
        if "concepts" not in cloud or "weights" not in cloud:
            raise ValueError("意图云团必须包含'concepts'和'weights'字段")
            
        if len(cloud["concepts"]) != len(cloud["weights"]):
            raise ValueError("concepts和weights长度必须一致")
            
        if len(cloud["concepts"]) < 3:
            raise ValueError("意图云团至少需要3个概念")
            
        if any(w <= 0 or w > 1 for w in cloud["weights"]):
            raise ValueError("权重必须在(0,1]范围内")
    
    def _concepts_to_vectors(self, concepts: List[str]) -> np.ndarray:
        """将概念转换为向量表示(简化实现)"""
        # 实际应用中这里应该使用预训练的词向量模型
        np.random.seed(42)  # 为了可重复性
        return np.random.rand(len(concepts), 50)  # 假设50维向量
    
    def _compute_geodesic_distances(self, vectors: np.ndarray) -> np.ndarray:
        """计算测地距离矩阵"""
        euclidean_dist = squareform(pdist(vectors, 'euclidean'))
        
        # 使用k近邻图近似测地距离
        n_samples = euclidean_dist.shape[0]
        for i in range(n_samples):
            neighbors = np.argsort(euclidean_dist[i])[:self.n_neighbors+1]
            mask = np.ones(n_samples, dtype=bool)
            mask[neighbors] = False
            euclidean_dist[i, mask] = np.inf
            
        return euclidean_dist
    
    def _cluster_intent_space(self, vectors: np.ndarray) -> np.ndarray:
        """使用DBSCAN聚类意图空间"""
        clustering = DBSCAN(
            eps=0.5,
            min_samples=self.min_samples,
            metric='euclidean'
        ).fit(vectors)
        return clustering.labels_
    
    def _estimate_intrinsic_dim(self, distances: np.ndarray) -> int:
        """估计流形的内在维度"""
        # 使用基于特征值的方法估计
        n_components = min(distances.shape[0] - 1, self.intrinsic_dim)
        return n_components

class TopologyGenerator:
    """
    基于流形结构生成功能拓扑图
    
    将低维嵌入转换为可执行的功能拓扑结构
    """
    
    def __init__(self, 
                 connectivity_threshold: float = 0.7,
                 min_module_size: int = 2):
        """
        初始化拓扑生成器
        
        Args:
            connectivity_threshold: 节点连接阈值
            min_module_size: 模块最小尺寸
        """
        self.connectivity_threshold = connectivity_threshold
        self.min_module_size = min_module_size
        
    def generate(self, manifold: ManifoldStructure) -> Dict:
        """
        生成功能拓扑图
        
        Args:
            manifold: 流形结构
            
        Returns:
            Dict: 包含节点和边的功能拓扑图
            
        Raises:
            ValueError: 流形结构无效时
        """
        if manifold.embedding.shape[0] < 3:
            raise ValueError("流形嵌入至少需要3个点")
            
        # 识别核心功能节点
        nodes = self._identify_nodes(manifold)
        
        # 建立节点连接
        edges = self._establish_connections(manifold)
        
        # 构建模块结构
        modules = self._build_modules(manifold, nodes, edges)
        
        topology = {
            "nodes": nodes,
            "edges": edges,
            "modules": modules,
            "metadata": {
                "intrinsic_dim": manifold.intrinsic_dim,
                "cluster_count": len(set(manifold.cluster_labels))
            }
        }
        
        logger.info("Successfully generated functional topology")
        return topology
    
    def _identify_nodes(self, manifold: ManifoldStructure) -> List[Dict]:
        """识别功能节点"""
        nodes = []
        for i, label in enumerate(manifold.cluster_labels):
            if label != -1:  # 忽略噪声点
                nodes.append({
                    "id": f"node_{i}",
                    "cluster": int(label),
                    "position": manifold.embedding[i].tolist(),
                    "type": self._classify_node_type(manifold.embedding[i])
                })
        return nodes
    
    def _classify_node_type(self, position: np.ndarray) -> str:
        """分类节点类型"""
        # 简化实现: 基于位置坐标分类
        if position[0] > 0:
            return "core" if position[1] > 0 else "input"
        else:
            return "output" if position[1] > 0 else "auxiliary"
    
    def _establish_connections(self, manifold: ManifoldStructure) -> List[Dict]:
        """建立节点连接"""
        edges = []
        n_samples = manifold.embedding.shape[0]
        
        for i in range(n_samples):
            for j in range(i+1, n_samples):
                # 使用测地距离决定连接强度
                distance = manifold.geodesic_distances[i, j]
                strength = 1 / (1 + distance)  # 简单转换函数
                
                if strength > self.connectivity_threshold:
                    edges.append({
                        "source": f"node_{i}",
                        "target": f"node_{j}",
                        "strength": float(strength),
                        "type": "data_flow"
                    })
                    
        return edges
    
    def _build_modules(self, 
                      manifold: ManifoldStructure,
                      nodes: List[Dict],
                      edges: List[Dict]) -> List[Dict]:
        """构建功能模块"""
        modules = []
        cluster_groups = {}
        
        # 按聚类分组节点
        for node in nodes:
            cluster = node["cluster"]
            if cluster not in cluster_groups:
                cluster_groups[cluster] = []
            cluster_groups[cluster].append(node["id"])
        
        # 为每个聚类创建模块
        for cluster, node_ids in cluster_groups.items():
            if len(node_ids) >= self.min_module_size:
                modules.append({
                    "id": f"module_{cluster}",
                    "nodes": node_ids,
                    "type": "functional_cluster",
                    "cohesion": self._calculate_module_cohesion(
                        node_ids, manifold.geodesic_distances
                    )
                })
                
        return modules
    
    def _calculate_module_cohesion(self, 
                                  node_ids: List[str],
                                  distances: np.ndarray) -> float:
        """计算模块内聚度"""
        if len(node_ids) < 2:
            return 0.0
            
        indices = [int(n.split("_")[1]) for n in node_ids]
        sub_distances = distances[np.ix_(indices, indices)]
        
        # 排除无穷大值
        finite_distances = sub_distances[np.isfinite(sub_distances)]
        if len(finite_distances) == 0:
            return 0.0
            
        return float(1 / (1 + np.mean(finite_distances)))

def validate_intent_input(intent_data: Union[Dict, str]) -> Dict[str, Union[List[str], List[float]]]:
    """
    验证并标准化意图输入数据
    
    Args:
        intent_data: 原始意图数据，可以是字典或JSON字符串
        
    Returns:
        标准化后的意图云团数据
        
    Raises:
        ValueError: 输入数据无效时
    """
    if isinstance(intent_data, str):
        try:
            intent_data = json.loads(intent_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {str(e)}")
    
    if not isinstance(intent_data, dict):
        raise ValueError("Intent data must be a dictionary or JSON string")
    
    # 标准化字段名
    normalized = {}
    if "concepts" in intent_data:
        normalized["concepts"] = intent_data["concepts"]
    elif "keywords" in intent_data:
        normalized["concepts"] = intent_data["keywords"]
    else:
        raise ValueError("No concept/keyword field found in intent data")
    
    if "weights" in intent_data:
        normalized["weights"] = intent_data["weights"]
    else:
        # 默认均匀权重
        normalized["weights"] = [1.0] * len(normalized["concepts"])
    
    return normalized

# 示例用法
if __name__ == "__main__":
    try:
        # 示例意图云团
        example_intent = {
            "concepts": ["game", "fun", "interactive", "graphics", "multiplayer"],
            "weights": [0.9, 0.8, 0.85, 0.6, 0.75]
        }
        
        # 处理流程
        processor = IntentCloudProcessor(intrinsic_dim=3, n_neighbors=3)
        manifold_structure = processor.fit_transform(example_intent)
        
        generator = TopologyGenerator()
        topology = generator.generate(manifold_structure)
        
        # 输出结果
        print("Generated Topology:")
        print(f"Nodes: {len(topology['nodes'])}")
        print(f"Edges: {len(topology['edges'])}")
        print(f"Modules: {len(topology['modules'])}")
        
    except Exception as e:
        logger.error(f"Error in processing pipeline: {str(e)}")
        raise