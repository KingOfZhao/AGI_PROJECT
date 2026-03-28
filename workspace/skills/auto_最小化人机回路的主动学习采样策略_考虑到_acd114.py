"""
主动学习采样策略模块 - 最小化人机回路
本模块实现基于不确定性的主动学习采样策略，专注于最小化人类专家的参与成本，
通过计算信息增益和熵值，仅推送处于决策边界的样本进行人工验证。
"""

import math
import logging
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
from scipy.stats import entropy

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    节点数据结构，包含模型预测概率和当前状态
    
    Attributes:
        node_id: 节点唯一标识符
        features: 节点特征向量
        predicted_proba: 模型预测的概率分布 (正类概率)
        true_label: 真实标签 (None表示未标注)
        confidence: 当前模型的置信度
    """
    node_id: str
    features: np.ndarray
    predicted_proba: float
    true_label: Optional[int] = None
    confidence: float = 0.0

class ActiveLearningSampler:
    """
    主动学习采样器，实现基于不确定性的采样策略
    
    该类提供多种主动学习采样方法，包括:
    - 熵值采样
    - 最小置信度采样
    - 边缘采样
    - 信息密度采样
    
    所有方法都旨在最小化人类专家的参与成本，同时最大化模型性能提升。
    """
    
    def __init__(self, uncertainty_threshold: float = 0.2, min_confidence: float = 0.8):
        """
        初始化主动学习采样器
        
        Args:
            uncertainty_threshold: 不确定性阈值，用于确定决策边界
            min_confidence: 最小置信度阈值，低于此值的样本将被考虑
        
        Raises:
            ValueError: 如果参数不在有效范围内
        """
        self._validate_init_params(uncertainty_threshold, min_confidence)
        self.uncertainty_threshold = uncertainty_threshold
        self.min_confidence = min_confidence
        self.sampled_count = 0
        logger.info("ActiveLearningSampler initialized with uncertainty_threshold=%.2f, min_confidence=%.2f",
                   uncertainty_threshold, min_confidence)
    
    def _validate_init_params(self, uncertainty_threshold: float, min_confidence: float) -> None:
        """验证初始化参数的有效性"""
        if not 0 <= uncertainty_threshold <= 1:
            raise ValueError("uncertainty_threshold must be between 0 and 1")
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
    
    def calculate_entropy(self, probability: float) -> float:
        """
        计算二分类熵值
        
        Args:
            probability: 正类的预测概率
            
        Returns:
            计算得到的熵值 (0到1之间)
            
        Raises:
            ValueError: 如果概率不在[0,1]范围内
        """
        if not 0 <= probability <= 1:
            raise ValueError(f"Probability must be between 0 and 1, got {probability}")
        
        if probability == 0 or probability == 1:
            return 0.0
        
        # 二分类熵计算: -p*log2(p) - (1-p)*log2(1-p)
        return -probability * math.log2(probability) - (1 - probability) * math.log2(1 - probability)
    
    def uncertainty_sampling(self, nodes: List[Node], strategy: str = 'entropy') -> List[Node]:
        """
        基于不确定性的主动学习采样策略
        
        Args:
            nodes: 节点列表
            strategy: 采样策略 ('entropy', 'least_confident', 'margin')
            
        Returns:
            按不确定性排序的节点列表，最不确定的排在最前面
            
        Raises:
            ValueError: 如果策略名称无效
        """
        if not nodes:
            logger.warning("Empty node list provided to uncertainty_sampling")
            return []
        
        valid_strategies = ['entropy', 'least_confident', 'margin']
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{strategy}'. Valid strategies are: {valid_strategies}")
        
        sampled_nodes = []
        for node in nodes:
            if node.true_label is not None:
                continue  # 跳过已标注节点
                
            try:
                if strategy == 'entropy':
                    score = self.calculate_entropy(node.predicted_proba)
                elif strategy == 'least_confident':
                    score = 1 - max(node.predicted_proba, 1 - node.predicted_proba)
                elif strategy == 'margin':
                    score = min(node.predicted_proba, 1 - node.predicted_proba)
                
                node.confidence = score
                sampled_nodes.append(node)
            except Exception as e:
                logger.error(f"Error calculating uncertainty for node {node.node_id}: {str(e)}")
                continue
        
        # 按不确定性降序排序
        sampled_nodes.sort(key=lambda x: x.confidence, reverse=True)
        self.sampled_count += len(sampled_nodes)
        
        logger.info("Uncertainty sampling completed. Sampled %d nodes using %s strategy", 
                   len(sampled_nodes), strategy)
        return sampled_nodes
    
    def get_boundary_nodes(self, nodes: List[Node], top_k: int = 10) -> List[Node]:
        """
        获取处于决策边界的节点 (即系统无法确信的样本)
        
        Args:
            nodes: 节点列表
            top_k: 返回的最多节点数量
            
        Returns:
            处于决策边界的节点列表
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive")
            
        uncertain_nodes = self.uncertainty_sampling(nodes)
        boundary_nodes = []
        
        for node in uncertain_nodes:
            if (0.5 - self.uncertainty_threshold) <= node.predicted_proba <= (0.5 + self.uncertainty_threshold):
                boundary_nodes.append(node)
                if len(boundary_nodes) >= top_k:
                    break
        
        logger.info("Found %d boundary nodes (uncertainty threshold=%.2f)", 
                   len(boundary_nodes), self.uncertainty_threshold)
        return boundary_nodes
    
    def information_density_sampling(self, nodes: List[Node], similarity_matrix: np.ndarray, 
                                    beta: float = 0.5) -> List[Node]:
        """
        基于信息密度的采样策略，考虑样本的不确定性和代表性
        
        Args:
            nodes: 节点列表
            similarity_matrix: 节点间的相似度矩阵
            beta: 平衡不确定性和代表性的权重 (0-1)
            
        Returns:
            按信息密度排序的节点列表
            
        Raises:
            ValueError: 如果相似度矩阵维度不匹配或beta值无效
        """
        if not nodes:
            return []
            
        if len(nodes) != similarity_matrix.shape[0]:
            raise ValueError("Similarity matrix dimensions must match number of nodes")
            
        if not 0 <= beta <= 1:
            raise ValueError("Beta must be between 0 and 1")
        
        uncertain_nodes = self.uncertainty_sampling(nodes)
        if not uncertain_nodes:
            return []
            
        # 计算每个节点的平均相似度 (代表性)
        avg_similarities = np.mean(similarity_matrix, axis=1)
        
        # 归一化不确定性和代表性
        uncertainties = np.array([node.confidence for node in uncertain_nodes])
        uncertainties = (uncertainties - np.min(uncertainties)) / (np.max(uncertainties) - np.min(uncertainties) + 1e-10)
        
        # 计算信息密度
        information_density = beta * uncertainties + (1 - beta) * avg_similarities
        
        # 按信息密度排序
        for i, node in enumerate(uncertain_nodes):
            node.confidence = information_density[i]
        
        uncertain_nodes.sort(key=lambda x: x.confidence, reverse=True)
        self.sampled_count += len(uncertain_nodes)
        
        logger.info("Information density sampling completed. Sampled %d nodes with beta=%.2f", 
                   len(uncertain_nodes), beta)
        return uncertain_nodes

    def update_model(self, labeled_nodes: List[Node]) -> None:
        """
        模拟模型更新过程 (实际应用中应替换为真实模型更新)
        
        Args:
            labeled_nodes: 已标注的节点列表
        """
        # 在实际应用中，这里应该重新训练或更新模型
        logger.info("Model updated with %d labeled nodes", len(labeled_nodes))

# 使用示例
if __name__ == "__main__":
    try:
        # 创建模拟节点数据
        nodes = [
            Node(node_id="n1", features=np.array([0.1, 0.2]), predicted_proba=0.9),
            Node(node_id="n2", features=np.array([0.4, 0.5]), predicted_proba=0.55),
            Node(node_id="n3", features=np.array([0.7, 0.8]), predicted_proba=0.3),
            Node(node_id="n4", features=np.array([0.2, 0.3]), predicted_proba=0.48),
            Node(node_id="n5", features=np.array([0.9, 0.1]), predicted_proba=0.1),
            Node(node_id="n6", features=np.array([0.5, 0.5]), predicted_proba=0.5),
        ]
        
        # 创建模拟相似度矩阵
        similarity_matrix = np.array([
            [1.0, 0.2, 0.1, 0.3, 0.4, 0.5],
            [0.2, 1.0, 0.5, 0.6, 0.3, 0.7],
            [0.1, 0.5, 1.0, 0.4, 0.2, 0.6],
            [0.3, 0.6, 0.4, 1.0, 0.5, 0.8],
            [0.4, 0.3, 0.2, 0.5, 1.0, 0.3],
            [0.5, 0.7, 0.6, 0.8, 0.3, 1.0]
        ])
        
        # 初始化采样器
        sampler = ActiveLearningSampler(uncertainty_threshold=0.15, min_confidence=0.7)
        
        # 1. 使用不确定性采样
        print("\n=== Uncertainty Sampling ===")
        sampled_nodes = sampler.uncertainty_sampling(nodes, strategy='entropy')
        for node in sampled_nodes[:3]:
            print(f"Node {node.node_id}: proba={node.predicted_proba:.2f}, entropy={node.confidence:.3f}")
        
        # 2. 获取边界节点
        print("\n=== Boundary Nodes ===")
        boundary_nodes = sampler.get_boundary_nodes(nodes, top_k=3)
        for node in boundary_nodes:
            print(f"Node {node.node_id}: proba={node.predicted_proba:.2f}")
        
        # 3. 使用信息密度采样
        print("\n=== Information Density Sampling ===")
        dense_nodes = sampler.information_density_sampling(nodes, similarity_matrix, beta=0.6)
        for node in dense_nodes[:3]:
            print(f"Node {node.node_id}: proba={node.predicted_proba:.2f}, info_density={node.confidence:.3f}")
        
        print(f"\nTotal sampled nodes: {sampler.sampled_count}")
        
    except Exception as e:
        logger.error("Error in example usage: %s", str(e))
        raise