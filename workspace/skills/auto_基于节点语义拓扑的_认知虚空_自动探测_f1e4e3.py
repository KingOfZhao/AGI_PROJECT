"""
高级认知虚空探测模块

该模块实现了基于节点语义拓扑的‘认知虚空’自动探测算法。
通过构建高维语义向量空间并计算空间中的‘低密度空洞’，
识别出既未被现有技能覆盖，又位于高价值区域附近的‘未知空间’。

典型用法:
    >>> detector = CognitiveVoidDetector()
    >>> nodes = [Node(id="n1", vector=[0.1, 0.2], connections=5)]
    >>> voids = detector.detect_voids(nodes)
    >>> print(voids[0].centroid)
    [0.15, 0.25]
"""

import logging
import math
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from scipy.spatial import KDTree, Voronoi
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Node:
    """表示认知网络中的一个节点"""
    id: str
    vector: List[float]
    connections: int
    metadata: Optional[Dict] = None


@dataclass
class CognitiveVoid:
    """表示检测到的认知虚空"""
    centroid: List[float]
    radius: float
    nearby_high_value_nodes: List[str]
    density_score: float
    exploration_priority: float


class CognitiveVoidDetector:
    """
    基于节点语义拓扑的认知虚空检测器
    
    该类实现了以下核心功能：
    1. 构建高维语义向量空间
    2. 计算空间中的低密度空洞
    3. 识别高价值区域附近的未知空间
    4. 生成待探索的新概念候选项
    """
    
    def __init__(self, 
                 min_density_threshold: float = 0.2,
                 high_value_threshold: float = 0.8,
                 exploration_radius: float = 0.5):
        """
        初始化检测器
        
        Args:
            min_density_threshold: 密度阈值，低于此值的区域被视为虚空
            high_value_threshold: 高价值节点阈值（连接数归一化后）
            exploration_radius: 探索半径，控制虚空检测的精度
        """
        self.min_density_threshold = min_density_threshold
        self.high_value_threshold = high_value_threshold
        self.exploration_radius = exploration_radius
        self._validate_parameters()
        
    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性"""
        if not 0 < self.min_density_threshold < 1:
            raise ValueError("min_density_threshold must be between 0 and 1")
        if not 0 < self.high_value_threshold < 1:
            raise ValueError("high_value_threshold must be between 0 and 1")
        if self.exploration_radius <= 0:
            raise ValueError("exploration_radius must be positive")
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """归一化向量到单位球面"""
        return normalize(vectors, norm='l2')
    
    def _compute_local_density(self, 
                              point: np.ndarray, 
                              kd_tree: KDTree, 
                              radius: float) -> float:
        """
        计算给定点周围半径范围内的局部密度
        
        Args:
            point: 要计算密度的点
            kd_tree: 用于快速邻居搜索的KD树
            radius: 计算密度的半径范围
            
        Returns:
            局部密度值（邻居数量 / 最大可能邻居数量）
        """
        neighbors = kd_tree.query_ball_point(point, radius)
        max_neighbors = min(100, len(kd_tree.data))  # 避免极端值
        return len(neighbors) / max_neighbors if max_neighbors > 0 else 0.0
    
    def _find_high_value_nodes(self, nodes: List[Node]) -> Set[str]:
        """
        识别高价值节点（高连接数或高流量）
        
        Args:
            nodes: 节点列表
            
        Returns:
            高价值节点ID的集合
        """
        if not nodes:
            return set()
            
        # 计算连接数的百分位数
        connections = np.array([n.connections for n in nodes])
        threshold = np.percentile(connections, 
                                self.high_value_threshold * 100)
        
        return {n.id for n in nodes 
               if n.connections >= threshold}
    
    def _generate_candidate_points(self, 
                                  kd_tree: KDTree, 
                                  high_value_indices: List[int],
                                  n_candidates: int = 1000) -> np.ndarray:
        """
        在高价值节点附近生成候选探测点
        
        Args:
            kd_tree: 包含所有节点的KD树
            high_value_indices: 高价值节点的索引列表
            n_candidates: 要生成的候选点数量
            
        Returns:
            候选点数组，形状为(n_candidates, n_dimensions)
        """
        if not high_value_indices:
            return np.array([])
            
        # 获取高价值节点的向量
        high_value_vectors = kd_tree.data[high_value_indices]
        
        # 使用Voronoi图生成候选点（在高价值节点之间）
        try:
            vor = Voronoi(high_value_vectors)
            candidates = vor.vertices
        except Exception as e:
            logger.warning(f"Voronoi generation failed: {e}. Using fallback method.")
            # 回退方法：在高价值节点周围随机采样
            candidates = self._random_sampling_around_points(
                high_value_vectors, n_candidates
            )
            
        return candidates
    
    def _random_sampling_around_points(self, 
                                      points: np.ndarray, 
                                      n_samples: int) -> np.ndarray:
        """
        在给定点周围随机采样
        
        Args:
            points: 中心点数组
            n_samples: 要采样的点数量
            
        Returns:
            采样点数组
        """
        n_points, n_dim = points.shape
        samples = np.zeros((n_samples, n_dim))
        
        for i in range(n_samples):
            # 随机选择一个中心点
            center = points[np.random.randint(n_points)]
            # 添加随机偏移
            offset = np.random.normal(0, self.exploration_radius/2, n_dim)
            samples[i] = center + offset
            
        return samples
    
    def detect_voids(self, nodes: List[Node]) -> List[CognitiveVoid]:
        """
        检测认知虚空的主函数
        
        Args:
            nodes: 节点列表，每个节点包含ID、向量表示和连接数
            
        Returns:
            检测到的认知虚空列表，按探索优先级排序
            
        Raises:
            ValueError: 如果输入节点列表为空或格式无效
        """
        # 输入验证
        if not nodes:
            raise ValueError("Input node list cannot be empty")
            
        try:
            # 准备数据
            vectors = np.array([n.vector for n in nodes])
            vectors = self._normalize_vectors(vectors)
            node_ids = [n.id for n in nodes]
            
            # 构建KD树用于快速空间查询
            kd_tree = KDTree(vectors)
            
            # 识别高价值节点
            high_value_ids = self._find_high_value_nodes(nodes)
            high_value_indices = [i for i, n in enumerate(nodes) 
                                 if n.id in high_value_ids]
            
            if not high_value_indices:
                logger.warning("No high-value nodes found. Results may be suboptimal.")
                high_value_indices = range(len(nodes))  # 使用所有节点作为回退
            
            # 生成候选探测点
            candidates = self._generate_candidate_points(
                kd_tree, high_value_indices
            )
            
            # 计算每个候选点的局部密度
            voids = []
            for candidate in candidates:
                density = self._compute_local_density(
                    candidate, kd_tree, self.exploration_radius
                )
                
                # 如果密度低于阈值，则认为是虚空
                if density < self.min_density_threshold:
                    # 找到附近的高价值节点
                    nearby_indices = kd_tree.query_ball_point(
                        candidate, self.exploration_radius * 2
                    )
                    nearby_ids = [node_ids[i] for i in nearby_indices]
                    high_value_nearby = [id for id in nearby_ids 
                                       if id in high_value_ids]
                    
                    # 计算探索优先级
                    # 优先级 = (1 - density) * log(1 + high_value_connections)
                    high_value_connections = sum(
                        nodes[i].connections for i in nearby_indices 
                        if node_ids[i] in high_value_ids
                    )
                    priority = (1 - density) * math.log(1 + high_value_connections)
                    
                    voids.append(CognitiveVoid(
                        centroid=candidate.tolist(),
                        radius=self.exploration_radius,
                        nearby_high_value_nodes=high_value_nearby,
                        density_score=density,
                        exploration_priority=priority
                    ))
            
            # 按探索优先级排序
            voids.sort(key=lambda x: x.exploration_priority, reverse=True)
            
            logger.info(f"Detected {len(voids)} cognitive voids. "
                       f"Top priority: {voids[0].centroid if voids else 'None'}")
            
            return voids
            
        except Exception as e:
            logger.error(f"Error during void detection: {str(e)}")
            raise RuntimeError(f"Void detection failed: {str(e)}") from e


# 示例用法
if __name__ == "__main__":
    # 生成示例数据
    np.random.seed(42)
    nodes = []
    
    # 创建一些高连接中心节点
    for i in range(10):
        center = np.random.rand(10)  # 10维向量
        nodes.append(Node(
            id=f"center_{i}",
            vector=center.tolist(),
            connections=np.random.randint(50, 100)
        ))
        
        # 添加一些周围节点
        for j in range(10):
            offset = np.random.normal(0, 0.2, 10)
            nodes.append(Node(
                id=f"surround_{i}_{j}",
                vector=(center + offset).tolist(),
                connections=np.random.randint(1, 20)
            ))
    
    # 创建一些孤立节点（潜在虚空）
    for i in range(5):
        nodes.append(Node(
            id=f"isolated_{i}",
            vector=np.random.rand(10).tolist(),
            connections=np.random.randint(0, 5)
        ))
    
    # 检测认知虚空
    detector = CognitiveVoidDetector(
        min_density_threshold=0.15,
        high_value_threshold=0.9,
        exploration_radius=0.3
    )
    
    try:
        voids = detector.detect_voids(nodes)
        print(f"Detected {len(voids)} cognitive voids")
        
        if voids:
            print("\nTop 3 voids by exploration priority:")
            for i, void in enumerate(voids[:3]):
                print(f"\nVoid #{i+1}:")
                print(f"Centroid: {void.centroid[:3]}... (truncated)")
                print(f"Nearby high-value nodes: {void.nearby_high_value_nodes}")
                print(f"Density score: {void.density_score:.3f}")
                print(f"Exploration priority: {void.exploration_priority:.3f}")
                
    except Exception as e:
        print(f"Error: {str(e)}")