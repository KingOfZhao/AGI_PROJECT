"""
高维重叠特征提取器模块

该模块实现了一个针对'四向碰撞'场景的特征提取器，专门用于检测和处理'左右跨域重叠'问题。
通过计算潜在语义空间中节点间的欧氏距离或余弦相似度，当检测到距离小于阈值但领域标签不同时，
自动触发'融合提案'机制。

主要功能：
1. 计算高维特征空间中的节点相似度
2. 检测跨域重叠节点对
3. 自动生成融合提案

输入格式：
- 节点特征：形状为(N, D)的numpy数组或类似结构，N为节点数，D为特征维度
- 领域标签：长度为N的列表或数组，表示每个节点的领域归属

输出格式：
- 重叠节点对列表：包含节点索引和相似度得分的元组列表
- 融合提案：包含节点对信息和融合建议的字典列表

使用示例：
>>> features = np.random.rand(100, 128)  # 100个节点，每个128维特征
>>> labels = ['domain_a'] * 50 + ['domain_b'] * 50  # 两个领域各50个节点
>>> extractor = HighDimOverlapExtractor(distance_threshold=0.5, similarity_threshold=0.8)
>>> overlaps = extractor.detect_cross_domain_overlaps(features, labels)
>>> proposals = extractor.generate_fusion_proposals(overlaps)
"""

import numpy as np
from typing import List, Tuple, Dict, Union, Optional
import logging
from dataclasses import dataclass
from scipy.spatial.distance import cdist

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OverlapPair:
    """表示一对跨域重叠节点的数据类"""
    node1_idx: int
    node2_idx: int
    similarity: float
    domain1: str
    domain2: str


class HighDimOverlapExtractor:
    """
    高维重叠特征提取器，用于检测和处理四向碰撞中的左右跨域重叠问题。
    
    参数:
        distance_threshold (float): 欧氏距离阈值，小于此值视为重叠
        similarity_threshold (float): 余弦相似度阈值，大于此值视为重叠
        metric (str): 相似度计算方法，'euclidean'或'cosine'
        verbose (bool): 是否输出详细日志信息
    """
    
    def __init__(
        self,
        distance_threshold: float = 0.5,
        similarity_threshold: float = 0.8,
        metric: str = 'cosine',
        verbose: bool = False
    ):
        self.distance_threshold = distance_threshold
        self.similarity_threshold = similarity_threshold
        self.metric = metric
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性"""
        if self.distance_threshold <= 0:
            raise ValueError("距离阈值必须为正数")
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("相似度阈值必须在0到1之间")
        if self.metric not in ['euclidean', 'cosine']:
            raise ValueError("度量方法必须是'euclidean'或'cosine'")
    
    def compute_similarity_matrix(
        self,
        features: np.ndarray
    ) -> np.ndarray:
        """
        计算特征矩阵中所有节点对之间的相似度矩阵。
        
        参数:
            features (np.ndarray): 形状为(N, D)的特征矩阵，N为节点数，D为特征维度
            
        返回:
            np.ndarray: 形状为(N, N)的相似度矩阵
            
        异常:
            ValueError: 如果输入特征不是2维数组或为空
        """
        if not isinstance(features, np.ndarray) or features.ndim != 2:
            raise ValueError("输入特征必须是2维numpy数组")
        if features.size == 0:
            raise ValueError("输入特征矩阵不能为空")
            
        logger.debug(f"计算相似度矩阵，特征形状: {features.shape}")
        
        if self.metric == 'euclidean':
            dist_matrix = cdist(features, features, 'euclidean')
            similarity_matrix = 1 / (1 + dist_matrix)  # 将距离转换为相似度
        else:  # cosine
            similarity_matrix = 1 - cdist(features, features, 'cosine')
            
        return similarity_matrix
    
    def detect_cross_domain_overlaps(
        self,
        features: np.ndarray,
        domain_labels: List[str],
        min_samples: int = 1
    ) -> List[OverlapPair]:
        """
        检测跨域重叠的节点对。
        
        参数:
            features (np.ndarray): 形状为(N, D)的特征矩阵
            domain_labels (List[str]): 长度为N的领域标签列表
            min_samples (int): 每个领域至少包含的样本数
            
        返回:
            List[OverlapPair]: 跨域重叠节点对列表
            
        异常:
            ValueError: 如果输入维度不匹配或标签无效
        """
        self._validate_input(features, domain_labels)
        
        if min_samples < 1:
            raise ValueError("min_samples必须至少为1")
            
        # 检查领域标签的唯一性
        unique_domains = set(domain_labels)
        if len(unique_domains) < 2:
            logger.warning("只检测到一个领域标签，无法检测跨域重叠")
            return []
            
        # 计算相似度矩阵
        similarity_matrix = self.compute_similarity_matrix(features)
        
        overlaps = []
        n_nodes = features.shape[0]
        
        # 遍历所有节点对
        for i in range(n_nodes):
            for j in range(i+1, n_nodes):
                if domain_labels[i] != domain_labels[j]:
                    similarity = similarity_matrix[i, j]
                    
                    # 根据度量方法检查阈值
                    is_overlap = False
                    if self.metric == 'euclidean' and similarity > (1 / (1 + self.distance_threshold)):
                        is_overlap = True
                    elif self.metric == 'cosine' and similarity > self.similarity_threshold:
                        is_overlap = True
                        
                    if is_overlap:
                        overlaps.append(OverlapPair(
                            node1_idx=i,
                            node2_idx=j,
                            similarity=similarity,
                            domain1=domain_labels[i],
                            domain2=domain_labels[j]
                        ))
                        logger.debug(
                            f"发现跨域重叠: 节点{i}({domain_labels[i]})和节点{j}({domain_labels[j]}), "
                            f"相似度: {similarity:.4f}"
                        )
        
        logger.info(f"检测到{len(overlaps)}对跨域重叠节点")
        return overlaps
    
    def generate_fusion_proposals(
        self,
        overlaps: List[OverlapPair],
        min_confidence: float = 0.7
    ) -> List[Dict[str, Union[int, float, str]]]:
        """
        根据检测到的跨域重叠生成融合提案。
        
        参数:
            overlaps (List[OverlapPair]): 跨域重叠节点对列表
            min_confidence (float): 生成提案的最小置信度阈值
            
        返回:
            List[Dict]: 融合提案列表，每个提案包含节点对信息和融合建议
            
        异常:
            ValueError: 如果min_confidence不在0到1之间
        """
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence必须在0到1之间")
            
        proposals = []
        
        for overlap in overlaps:
            if overlap.similarity >= min_confidence:
                proposal = {
                    'node1_idx': overlap.node1_idx,
                    'node2_idx': overlap.node2_idx,
                    'domain1': overlap.domain1,
                    'domain2': overlap.domain2,
                    'similarity': overlap.similarity,
                    'fusion_suggestion': self._generate_fusion_suggestion(overlap),
                    'timestamp': np.datetime64('now').astype(str)
                }
                proposals.append(proposal)
                logger.debug(
                    f"生成融合提案: 节点{overlap.node1_idx}和{overlap.node2_idx}, "
                    f"相似度: {overlap.similarity:.4f}"
                )
        
        logger.info(f"生成{len(proposals)}个融合提案")
        return proposals
    
    def _generate_fusion_suggestion(
        self,
        overlap: OverlapPair
    ) -> str:
        """
        根据重叠节点对生成融合建议。
        
        参数:
            overlap (OverlapPair): 跨域重叠节点对
            
        返回:
            str: 融合建议文本
        """
        if overlap.similarity > 0.95:
            return "强建议融合: 高度相似的跨域节点对，建议立即合并"
        elif overlap.similarity > 0.85:
            return "建议融合: 中等相似度的跨域节点对，建议考虑合并"
        else:
            return "可能融合: 低相似度的跨域节点对，建议进一步分析"
    
    def _validate_input(
        self,
        features: np.ndarray,
        domain_labels: List[str]
    ) -> None:
        """验证输入数据的完整性和一致性"""
        if not isinstance(features, np.ndarray):
            raise ValueError("特征必须是numpy数组")
        if features.ndim != 2:
            raise ValueError("特征矩阵必须是2维数组")
        if len(domain_labels) != features.shape[0]:
            raise ValueError("领域标签数量与特征矩阵行数不匹配")
        if not all(isinstance(label, str) for label in domain_labels):
            raise ValueError("所有领域标签必须是字符串")


# 示例用法
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    num_nodes = 100
    feature_dim = 128
    
    # 创建两个领域的特征，有一些重叠
    domain_a_features = np.random.randn(num_nodes//2, feature_dim)
    domain_b_features = np.random.randn(num_nodes//2, feature_dim)
    
    # 添加一些跨域重叠
    overlap_indices = np.random.choice(num_nodes//2, size=10, replace=False)
    domain_b_features[overlap_indices] = domain_a_features[overlap_indices] + np.random.normal(0, 0.1, (10, feature_dim))
    
    # 合并特征和创建标签
    features = np.vstack([domain_a_features, domain_b_features])
    labels = ['domain_a'] * (num_nodes//2) + ['domain_b'] * (num_nodes//2)
    
    # 创建并使用特征提取器
    extractor = HighDimOverlapExtractor(
        distance_threshold=0.5,
        similarity_threshold=0.8,
        metric='cosine',
        verbose=True
    )
    
    # 检测跨域重叠
    overlaps = extractor.detect_cross_domain_overlaps(features, labels)
    
    # 生成融合提案
    proposals = extractor.generate_fusion_proposals(overlaps, min_confidence=0.75)
    
    # 打印部分结果
    print(f"\n检测到{len(overlaps)}对跨域重叠节点")
    print(f"生成{len(proposals)}个融合提案\n")
    
    if proposals:
        print("示例融合提案:")
        print(proposals[0])