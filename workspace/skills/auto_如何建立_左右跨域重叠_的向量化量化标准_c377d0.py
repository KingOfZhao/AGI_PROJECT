"""
Module: auto_如何建立_左右跨域重叠_的向量化量化标准_c377d0
Description: 建立'左右跨域重叠'的向量化量化标准，以发现潜在的新'真实节点'。
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    节点数据结构。
    
    Attributes:
        id (str): 节点的唯一标识符。
        domain (str): 节点所属的领域（如 'biology', 'engineering'）。
        semantic_vector (np.ndarray): 语义嵌入向量。
        structural_features (np.ndarray): 结构化特征向量（如图拓扑特征、逻辑依赖特征）。
    """
    id: str
    domain: str
    semantic_vector: np.ndarray
    structural_features: np.ndarray

class CrossDomainResonanceAnalyzer:
    """
    分析跨域节点之间的结构共振与重叠。
    
    该类实现了一种非欧几里得距离的度量算法，旨在识别描述不同（语义距离远）
    但底层逻辑结构高度相似（结构距离近）的节点对。
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.5, gamma: float = 0.1):
        """
        初始化分析器。
        
        Args:
            alpha (float): 结构相似度的权重。
            beta (float): 语义差异度的奖励权重（用于确保跨域）。
            gamma (float): 曼哈顿距离在结构计算中的混合比例。
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self._validate_parameters()
        logger.info("CrossDomainResonanceAnalyzer initialized with alpha=%.2f, beta=%.2f", alpha, beta)

    def _validate_parameters(self) -> None:
        """验证初始化参数的合法性。"""
        if not (0.0 <= self.alpha <= 1.0 and 0.0 <= self.beta <= 1.0):
            raise ValueError("Weights alpha and beta must be between 0 and 1.")
        if not (0.0 <= self.gamma <= 1.0):
            raise ValueError("Mixture ratio gamma must be between 0 and 1.")

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """
        辅助函数：对特征进行标准化处理。
        
        Args:
            features (np.ndarray): 原始特征矩阵 (N, D)。
            
        Returns:
            np.ndarray: 标准化后的特征矩阵。
        """
        if features.size == 0:
            raise ValueError("Input features cannot be empty.")
        scaler = StandardScaler()
        return scaler.fit_transform(features)

    def calculate_structural_geometry(self, vector: np.ndarray) -> Tuple[float, float, float]:
        """
        计算单个向量在超维空间中的几何特征（非欧氏特征提取）。
        
        这是一个辅助函数，用于提取向量的内在几何属性，而非相对于其他点的距离。
        
        Args:
            vector (np.ndarray): 节点的结构特征向量。
            
        Returns:
            Tuple[float, float, float]: 包含 (范数能量, 熵复杂度, 稀疏度) 的元组。
        """
        # 1. 范数能量
        norm_l2 = np.linalg.norm(vector)
        
        # 2. 熵复杂度 - 基于分量的概率分布
        abs_vec = np.abs(vector) + 1e-9  # 避免log(0)
        prob = abs_vec / np.sum(abs_vec)
        entropy = -np.sum(prob * np.log2(prob))
        
        # 3. 稀疏度
        k = np.sqrt(len(vector))
        threshold = np.sort(np.abs(vector))[int(len(vector) - k)]
        sparsity = np.sum(np.abs(vector) > threshold) / len(vector)
        
        return norm_l2, entropy, sparsity

    def compute_resonance_matrix(self, nodes: List[Node]) -> np.ndarray:
        """
        核心函数：计算所有节点对之间的'结构重合度'分数矩阵。
        
        算法逻辑：
        1. 提取并标准化结构特征。
        2. 计算混合距离矩阵 (1-gamma)*Cosine + gamma*Manhattan。
        3. 将距离转换为相似度。
        4. 结合语义距离和结构相似度计算最终共振分数。
        
        Args:
            nodes (List[Node]): 包含777个节点的列表。
            
        Returns:
            np.ndarray: NxN 的共振分数矩阵。
        """
        if not nodes:
            raise ValueError("Node list is empty.")
        
        n = len(nodes)
        if n != 777:
            logger.warning(f"Expected 777 nodes, but got {n}. Proceeding with current data.")
        
        logger.info(f"Processing {n} nodes for structural resonance...")
        
        # 数据提取与验证
        try:
            struct_features = np.array([node.structural_features for node in nodes])
            semantic_vectors = np.array([node.semantic_vector for node in nodes])
            domains = np.array([node.domain for node in nodes])
        except AttributeError as e:
            logger.error("Invalid node structure: missing attributes.")
            raise e

        # 1. 结构特征工程
        # 标准化结构特征以消除量纲影响
        struct_norm = self._normalize_features(struct_features)
        
        # 2. 计算非欧几里得混合距离
        # Cosine距离 (关注角度，忽略模长)
        dist_cosine = pairwise_distances(struct_norm, metric='cosine')
        # 曼哈顿距离 (关注网格结构，模拟城市街区/逻辑路径)
        dist_manhattan = pairwise_distances(struct_norm, metric='manhattan')
        # 归一化曼哈顿距离到 [0, 1] 以便混合
        dist_manhattan_norm = dist_manhattan / (np.max(dist_manhattan) + 1e-9)
        
        # 混合距离: 结合角度对齐与路径差异
        hybrid_distance = (1 - self.gamma) * dist_cosine + self.gamma * dist_manhattan_norm
        
        # 3. 转换为结构相似度
        struct_similarity = 1 - hybrid_distance
        
        # 4. 计算语义距离
        # 我们希望找到语义不同但结构相似的，所以这里计算距离
        semantic_dist = pairwise_distances(semantic_vectors, metric='cosine')
        
        # 5. 计算跨域奖励
        # 如果节点属于不同领域，给予额外奖励
        domain_bonus = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if domains[i] != domains[j]:
                    domain_bonus[i, j] = 1.0
        
        # 6. 综合共振分数公式
        # Score = α * (结构相似度) + β * (语义距离 * 跨域奖励)
        # 这意味着：高结构相似 + 不同语义 + 不同领域 = 高分
        resonance_matrix = (self.alpha * struct_similarity) + \
                           (self.beta * semantic_dist * domain_bonus)
        
        # 移除自比较 (对角线设为0)
        np.fill_diagonal(resonance_matrix, 0.0)
        
        logger.info("Resonance matrix computation complete.")
        return resonance_matrix

    def discover_potential_nodes(self, nodes: List[Node], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        核心函数：基于共振矩阵发现潜在的新'真实节点'。
        
        Args:
            nodes (List[Node]): 节点列表。
            top_k (int): 返回得分最高的前K个节点对。
            
        Returns:
            List[Dict]: 包含潜在创新节点对信息的字典列表，按分数降序排列。
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive.")

        matrix = self.compute_resonance_matrix(nodes)
        
        # 获取平铺后的索引
        flat_indices = np.argsort(matrix.flatten())[::-1]
        
        results = []
        count = 0
        
        for idx in flat_indices:
            if count >= top_k:
                break
            
            i, j = divmod(idx, len(nodes))
            
            # 确保只处理上三角矩阵，避免重复 (i < j)
            if i >= j:
                continue

            score = matrix[i, j]
            node_a = nodes[i]
            node_b = nodes[j]
            
            # 简单的边界检查，确保分数有意义
            if score <= 0:
                continue
                
            result_entry = {
                "pair": (node_a.id, node_b.id),
                "domains": (node_a.domain, node_b.domain),
                "resonance_score": float(score),
                "interpretation": f"High structural overlap between '{node_a.domain}' and '{node_b.domain}'. "
                                  f"Potential for new concept synthesis."
            }
            results.append(result_entry)
            count += 1
            
        logger.info(f"Discovered {len(results)} potential node pairs.")
        return results

# --- Usage Example ---
if __name__ == "__main__":
    # 模拟数据生成
    def generate_mock_nodes(num_nodes: int = 777) -> List[Node]:
        np.random.seed(42)
        nodes = []
        domains = ['biology', 'engineering', 'sociology', 'physics']
        for i in range(num_nodes):
            # 随机生成语义向量和结构向量
            # 语义向量：普通正态分布
            sem_vec = np.random.rand(128)
            # 结构向量：模拟某些特定逻辑模式 (例如周期性或稀疏性)
            struc_vec = np.random.rand(64)
            
            # 故意制造一些跨域重叠：
            # 让某些biology节点的结构向量与engineering节点非常相似
            if i < 20:
                struc_vec = np.ones(64) * 0.5 # 特定模式
            elif i >= 100 and i < 120:
                struc_vec = np.ones(64) * 0.5 # 相同模式，不同ID和域
            
            node = Node(
                id=f"node_{i:04d}",
                domain=domains[i % len(domains)],
                semantic_vector=sem_vec,
                structural_features=struc_vec
            )
            nodes.append(node)
        return nodes

    try:
        # 1. 初始化
        analyzer = CrossDomainResonanceAnalyzer(alpha=0.6, beta=0.4)
        
        # 2. 准备数据
        mock_nodes = generate_mock_nodes()
        
        # 3. 执行发现
        potential_innovations = analyzer.discover_potential_nodes(mock_nodes, top_k=5)
        
        # 4. 输出结果
        print("\n--- Top Potential Innovations (Structural Resonance) ---")
        for item in potential_innovations:
            print(f"Pair: {item['pair']}")
            print(f"Domains: {item['domains']}")
            print(f"Score: {item['resonance_score']:.4f}")
            print(f"Insight: {item['interpretation']}")
            print("-" * 40)
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)