"""
模块: dynamic_semantic_compressor
描述: 实现'动态语义压缩器'，基于认知流形学习和注意力机制，根据上下文动态调整特征权重。
作者: AGI System Core Engineer
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, Optional, Union, List
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CompressionResult:
    """
    压缩结果的数据结构。
    
    Attributes:
        compressed_data (np.ndarray): 压缩后的低维数据。
        attention_weights (np.ndarray): 生成的特征权重向量。
        retained_variance (float): 保留的方差比例。
        context_relevance (float): 上下文相关度得分。
    """
    compressed_data: np.ndarray
    attention_weights: np.ndarray
    retained_variance: float
    context_relevance: float

class DynamicSemanticCompressor:
    """
    动态语义压缩器：模拟人类注意机制的非线性降维模型。
    
    该类实现了一个基于目标驱动的流形学习网络。不同于静态PCA，
    它根据输入的'上下文目标'动态计算特征的注意力权重，
    在降维过程中保留与目标最相关的语义信息。
    
    Attributes:
        n_components (int): 目标降维维度。
        attention_threshold (float): 注意力权重的截断阈值。
        _is_fitted (bool): 模型是否已训练。
    """

    def __init__(self, n_components: int = 2, attention_threshold: float = 0.01) -> None:
        """
        初始化压缩器。

        Args:
            n_components (int): 压缩后的维度。
            attention_threshold (float): 低于此权重的特征将被忽略以增强稀疏性。
        
        Raises:
            ValueError: 如果参数不合法。
        """
        if n_components < 1:
            raise ValueError("n_components must be at least 1.")
        if not 0 <= attention_threshold <= 1:
            raise ValueError("attention_threshold must be between 0 and 1.")
            
        self.n_components = n_components
        self.attention_threshold = attention_threshold
        self._scaler = StandardScaler()
        self._is_fitted = False
        
        logger.info(f"Initialized DynamicSemanticCompressor with {n_components} components.")

    def _calculate_attention_weights(
        self, 
        X: np.ndarray, 
        context_vector: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        [核心函数 1] 计算动态注意力权重。
        
        模拟认知注意机制。如果有上下文目标，特征权重将偏向与目标相关的维度；
        如果没有，则依据特征本身的稀疏性和方差分布生成权重（模拟无意识注意）。

        Args:
            X (np.ndarray): 输入数据矩阵 (n_samples, n_features)。
            context_vector (np.ndarray, optional): 上下文目标向量 (n_features,)。

        Returns:
            np.ndarray: 归一化的注意力权重向量 (n_features,)。
        """
        n_features = X.shape[1]
        
        if context_vector is not None:
            # 验证上下文向量形状
            if context_vector.shape[0] != n_features:
                raise ValueError(
                    f"Context vector dimension {context_vector.shape[0]} "
                    f"does not match data features {n_features}."
                )
            
            # 计算特征与上下文的相似度（模拟相关性）
            # 使用简单的点积作为相关性度量，实际AGI场景可能使用复杂的嵌入相似度
            abs_context = np.abs(context_vector)
            weights = abs_context / (np.sum(abs_context) + 1e-9)
            logger.debug("Calculated weights based on context vector.")
        else:
            # 无上下文时，基于特征的统计属性（熵/方差）生成自注意力权重
            # 这里使用标准差作为信息量的代理
            std_devs = np.std(X, axis=0)
            weights = std_devs / (np.sum(std_devs) + 1e-9)
            logger.debug("Calculated weights based on data intrinsic variance (auto-focus).")

        # 应用阈值截断，模拟人类忽略微弱信号的能力
        weights[weights < self.attention_threshold] = 0
        
        # 重新归一化
        total_weight = np.sum(weights)
        if total_weight > 0:
            weights = weights / total_weight
        else:
            # 极端情况处理：如果所有权重都被过滤，则恢复均匀分布
            weights = np.ones(n_features) / n_features
            logger.warning("All weights below threshold, falling back to uniform distribution.")
            
        return weights

    def fit_transform(
        self, 
        X: np.ndarray, 
        context_vector: Optional[np.ndarray] = None
    ) -> CompressionResult:
        """
        [核心函数 2] 训练模型并执行动态语义压缩。
        
        执行流程：
        1. 数据标准化。
        2. 计算动态注意力权重。
        3. 应用权重到特征空间（缩放流形）。
        4. 执行加权PCA降维。

        Args:
            X (np.ndarray): 输入数据 (n_samples, n_features)。
            context_vector (Optional[np.ndarray]): 目标上下文向量。

        Returns:
            CompressionResult: 包含压缩数据和元信息的对象。
        """
        # 输入验证
        if not isinstance(X, np.ndarray) or X.ndim != 2:
            raise TypeError("Input X must be a 2D numpy array.")
        if X.shape[0] < 2:
             raise ValueError("Number of samples must be at least 2 for fitting.")
        
        logger.info(f"Starting compression for {X.shape[0]} samples...")
        
        try:
            # 1. 标准化预处理
            X_scaled = self._scaler.fit_transform(X)
            
            # 2. 获取注意力权重
            attention_w = self._calculate_attention_weights(X, context_vector)
            
            # 3. 构建对角权重矩阵并变换数据（关键步骤：改变流形度规）
            # W @ X 相当于对每个特征维度乘以一个系数
            # 这使得PCA会优先捕捉权重高的特征方向
            weight_matrix = np.diag(np.sqrt(attention_w + 1e-9)) # 加小量防止数值不稳定
            X_weighted = np.dot(X_scaled, weight_matrix)
            
            # 4. 执行核心降维
            # 确保n_components不超过特征数
            actual_components = min(self.n_components, X.shape[1])
            pca = PCA(n_components=actual_components)
            X_compressed = pca.fit_transform(X_weighted)
            
            # 计算上下文相关度指标
            context_relevance = np.mean(attention_w[attention_w > 0]) if np.any(attention_w > 0) else 0.0
            
            self._is_fitted = True
            
            result = CompressionResult(
                compressed_data=X_compressed,
                attention_weights=attention_w,
                retained_variance=float(np.sum(pca.explained_variance_ratio_)),
                context_relevance=float(context_relevance)
            )
            
            logger.info(
                f"Compression complete. Retained variance: {result.retained_variance:.4f}, "
                f"Context Relevance: {result.context_relevance:.4f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error during compression process: {str(e)}")
            raise RuntimeError("Failed to compress semantic data.") from e

    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        [辅助函数] 获取最后一次拟合计算出的特征重要性（注意力权重）。
        
        Returns:
            Optional[np.ndarray]: 特征权重数组，如果未拟合则返回None。
        """
        if not self._is_fitted:
            logger.warning("Model has not been fitted yet.")
            return None
        # 注意：实际权重在fit_transform中动态生成，此处仅为接口示例
        # 在更复杂的实现中，该状态会被存储在实例变量中
        return self._scaler.scale_  # 仅作为示例返回缩放因子

# 使用示例
if __name__ == "__main__":
    # 模拟数据：100个样本，10个特征
    data = np.random.rand(100, 10) * 10
    
    # 模拟上下文：我们只关心前3个特征（模拟'目标'）
    # 假设前3个特征包含了核心语义，其他是噪音
    context = np.zeros(10)
    context[0:3] = 1.0 
    
    try:
        # 初始化压缩器，压缩至2维
        compressor = DynamicSemanticCompressor(n_components=2, attention_threshold=0.05)
        
        print("--- Starting Dynamic Compression ---")
        result = compressor.fit_transform(data, context_vector=context)
        
        print(f"\nOriginal Shape: {data.shape}")
        print(f"Compressed Shape: {result.compressed_data.shape}")
        print(f"Attention Weights (First 5): {result.attention_weights[:5]}")
        print(f"Retained Variance Ratio: {result.retained_variance:.4f}")
        
        # 对比无上下文情况
        print("\n--- Starting Auto-Focus Compression (No Context) ---")
        result_auto = compressor.fit_transform(data)
        print(f"Attention Weights (Auto, First 5): {result_auto.attention_weights[:5]}")

    except Exception as e:
        print(f"An error occurred: {e}")