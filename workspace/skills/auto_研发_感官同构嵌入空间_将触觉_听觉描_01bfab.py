"""
Module: sensory_isomorphic_embedding.py
Description: 研发‘感官同构嵌入空间’，将触觉、听觉描述映射到同一高维向量空间进行聚类验证。
Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SensoryInput:
    """
    感官输入数据结构。
    
    Attributes:
        modality (str): 感官模态，支持 'tactile' (触觉) 或 'auditory' (听觉)
        description (str): 感官描述文本
        intensity (float): 感官强度，范围 [0.0, 1.0]
        duration (Optional[float]): 持续时间（秒），仅对听觉有效
    """
    modality: str
    description: str
    intensity: float = 0.5
    duration: Optional[float] = None
    
    def __post_init__(self):
        """数据验证和边界检查"""
        self._validate()
        
    def _validate(self):
        """验证输入数据的有效性"""
        if self.modality not in ['tactile', 'auditory']:
            raise ValueError(f"不支持的感官模态: {self.modality}. 必须是 'tactile' 或 'auditory'")
            
        if not isinstance(self.description, str) or len(self.description.strip()) == 0:
            raise ValueError("描述文本不能为空")
            
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"强度值必须在[0.0, 1.0]范围内，当前值: {self.intensity}")
            
        if self.modality == 'auditory' and self.duration is not None and self.duration <= 0:
            raise ValueError("听觉持续时间必须为正数")


class SensoryIsomorphicEmbedding:
    """
    感官同构嵌入空间实现类。
    
    该类提供将触觉和听觉描述映射到同一高维向量空间的功能，
    并支持在该空间中进行聚类分析和验证。
    
    Attributes:
        embedding_dim (int): 嵌入空间的维度
        random_state (int): 随机种子
        embeddings (np.ndarray): 存储的嵌入向量
        metadata (List[Dict]): 存储的元数据
    
    Example:
        >>> model = SensoryIsomorphicEmbedding(embedding_dim=128)
        >>> inputs = [
        ...     SensoryInput(modality='tactile', description='粗糙的表面', intensity=0.7),
        ...     SensoryInput(modality='auditory', description='高频尖啸声', intensity=0.9, duration=2.5)
        ... ]
        >>> model.fit(inputs)
        >>> cluster_labels = model.cluster(n_clusters=2)
    """
    
    def __init__(self, embedding_dim: int = 64, random_state: int = 42):
        """
        初始化感官同构嵌入空间。
        
        Args:
            embedding_dim (int): 嵌入空间的维度，必须大于0
            random_state (int): 随机种子，用于可重复性
        """
        if embedding_dim <= 0:
            raise ValueError("嵌入维度必须为正整数")
            
        self.embedding_dim = embedding_dim
        self.random_state = random_state
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: List[Dict] = []
        
        logger.info(f"初始化感官同构嵌入空间，维度: {embedding_dim}")
        
    def _hash_description(self, description: str) -> np.ndarray:
        """
        辅助函数：使用哈希技术将文本描述转换为固定维度的向量。
        
        这是一个简化的嵌入方法，实际应用中应替换为预训练的文本嵌入模型。
        
        Args:
            description (str): 输入的文本描述
            
        Returns:
            np.ndarray: 生成的嵌入向量
        """
        # 使用多个哈希函数生成特征向量
        vector = np.zeros(self.embedding_dim)
        
        for i, char in enumerate(description):
            # 使用字符的Unicode编码和位置信息生成特征
            hash_val = hash(f"{char}_{i}_{description[:i+1]}")
            idx = abs(hash_val) % self.embedding_dim
            vector[idx] += 1.0
            
        # 添加描述长度的归一化特征
        if len(description) > 0:
            vector[-1] = min(len(description) / 100.0, 1.0)
            
        # L2归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def _encode_modality(self, modality: str) -> np.ndarray:
        """
        辅助函数：将感官模态编码为向量特征。
        
        Args:
            modality (str): 感官模态 ('tactile' 或 'auditory')
            
        Returns:
            np.ndarray: 模态特征向量
        """
        # 在嵌入空间中保留前10维用于模态特征
        modality_features = np.zeros(10)
        
        if modality == 'tactile':
            modality_features[:5] = 1.0
        else:  # auditory
            modality_features[5:] = 1.0
            
        return modality_features
    
    def embed(self, inputs: List[SensoryInput]) -> np.ndarray:
        """
        核心函数1：将感官输入列表映射到嵌入空间。
        
        Args:
            inputs (List[SensoryInput]): 感官输入列表
            
        Returns:
            np.ndarray: 嵌入向量矩阵，形状为 (n_samples, embedding_dim)
            
        Raises:
            ValueError: 如果输入列表为空
        """
        if not inputs:
            raise ValueError("输入列表不能为空")
            
        logger.info(f"开始处理 {len(inputs)} 个感官输入样本...")
        
        embeddings = []
        self.metadata = []
        
        for i, sensory_input in enumerate(inputs):
            try:
                # 生成描述嵌入
                desc_embedding = self._hash_description(sensory_input.description)
                
                # 生成模态特征
                modality_features = self._encode_modality(sensory_input.modality)
                
                # 组合特征 (在描述嵌入的基础上叠加模态特征)
                combined = desc_embedding.copy()
                combined[:10] += modality_features * sensory_input.intensity
                
                # 添加强度特征
                combined[-2] = sensory_input.intensity
                
                # 添加持续时间特征 (仅对听觉)
                if sensory_input.modality == 'auditory' and sensory_input.duration is not None:
                    combined[-3] = min(sensory_input.duration / 10.0, 1.0)
                
                # L2归一化最终向量
                combined = normalize(combined.reshape(1, -1), norm='l2').flatten()
                
                embeddings.append(combined)
                
                # 存储元数据
                self.metadata.append({
                    'index': i,
                    'modality': sensory_input.modality,
                    'description': sensory_input.description,
                    'intensity': sensory_input.intensity,
                    'duration': sensory_input.duration
                })
                
            except Exception as e:
                logger.error(f"处理样本 {i} 时出错: {str(e)}")
                continue
                
        if not embeddings:
            raise RuntimeError("没有成功处理任何样本")
            
        self.embeddings = np.vstack(embeddings)
        logger.info(f"成功生成嵌入矩阵，形状: {self.embeddings.shape}")
        
        return self.embeddings
    
    def cluster_and_validate(self, n_clusters: int = 2) -> Tuple[np.ndarray, float]:
        """
        核心函数2：在嵌入空间中进行聚类并验证效果。
        
        Args:
            n_clusters (int): 聚类数量
            
        Returns:
            Tuple[np.ndarray, float]: (聚类标签数组, 轮廓系数)
            
        Raises:
            ValueError: 如果尚未调用embed()方法
        """
        if self.embeddings is None:
            raise ValueError("必须先调用embed()方法生成嵌入向量")
            
        if n_clusters < 2:
            raise ValueError("聚类数量必须至少为2")
            
        if len(self.embeddings) < n_clusters:
            raise ValueError(f"样本数量({len(self.embeddings)})少于聚类数量({n_clusters})")
            
        logger.info(f"开始聚类分析，聚类数: {n_clusters}")
        
        try:
            # 使用K-Means聚类
            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=self.random_state,
                n_init=10,
                max_iter=300
            )
            
            cluster_labels = kmeans.fit_predict(self.embeddings)
            
            # 计算轮廓系数评估聚类质量
            if len(np.unique(cluster_labels)) > 1:
                silhouette_avg = silhouette_score(self.embeddings, cluster_labels)
            else:
                silhouette_avg = 0.0
                logger.warning("所有样本被分配到同一聚类，无法计算轮廓系数")
                
            logger.info(f"聚类完成，平均轮廓系数: {silhouette_avg:.4f}")
            
            # 分析聚类中的模态分布
            self._analyze_cluster_modality(cluster_labels)
            
            return cluster_labels, silhouette_avg
            
        except Exception as e:
            logger.error(f"聚类过程中发生错误: {str(e)}")
            raise
            
    def _analyze_cluster_modality(self, labels: np.ndarray) -> None:
        """
        辅助函数：分析各聚类中的模态分布。
        
        Args:
            labels (np.ndarray): 聚类标签数组
        """
        cluster_modality_count = {}
        
        for i, label in enumerate(labels):
            if label not in cluster_modality_count:
                cluster_modality_count[label] = {'tactile': 0, 'auditory': 0}
                
            modality = self.metadata[i]['modality']
            cluster_modality_count[label][modality] += 1
            
        logger.info("聚类模态分布:")
        for cluster_id, counts in cluster_modality_count.items():
            total = counts['tactile'] + counts['auditory']
            tactile_ratio = counts['tactile'] / total if total > 0 else 0
            auditory_ratio = counts['auditory'] / total if total > 0 else 0
            logger.info(
                f"  聚类 {cluster_id}: "
                f"触觉 {counts['tactile']} ({tactile_ratio:.1%}), "
                f"听觉 {counts['auditory']} ({auditory_ratio:.1%})"
            )


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    sensory_data = [
        # 触觉样本
        SensoryInput(modality='tactile', description='粗糙的砂纸表面', intensity=0.8),
        SensoryInput(modality='tactile', description='丝滑的布料', intensity=0.3),
        SensoryInput(modality='tactile', description='冰冷的金属', intensity=0.6),
        SensoryInput(modality='tactile', description='尖锐的针尖', intensity=0.95),
        
        # 听觉样本
        SensoryInput(modality='auditory', description='低沉的鼓声', intensity=0.7, duration=1.5),
        SensoryInput(modality='auditory', description='高频的哨声', intensity=0.9, duration=3.0),
        SensoryInput(modality='auditory', description='柔和的小提琴旋律', intensity=0.4, duration=5.2),
        SensoryInput(modality='auditory', description='刺耳的电钻声', intensity=0.85, duration=0.8),
    ]
    
    try:
        # 初始化模型
        model = SensoryIsomorphicEmbedding(embedding_dim=64, random_state=42)
        
        # 生成嵌入
        embeddings = model.embed(sensory_data)
        print(f"\n生成的嵌入矩阵形状: {embeddings.shape}")
        
        # 聚类验证
        labels, score = model.cluster_and_validate(n_clusters=2)
        print(f"\n聚类标签: {labels}")
        print(f"轮廓系数: {score:.4f}")
        
        # 输出聚类结果
        print("\n聚类结果详情:")
        for i, (label, meta) in enumerate(zip(labels, model.metadata)):
            print(f"样本 {i} [{meta['modality']:8}]: '{meta['description']}' -> 聚类 {label}")
            
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")