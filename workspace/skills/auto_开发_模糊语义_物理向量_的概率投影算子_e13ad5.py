"""
模块名称: fuzzy_semantic_vector_projector
描述: 开发'模糊语义-物理向量'的概率投影算子，建立不确定性的标准化度量衡。
      本模块实现将高维模糊语义概念映射到低维物理向量空间的算法，同时保留
      概率分布特性以量化语义不确定性。

核心功能:
1. 语义向量编码与解码
2. 模糊边界处理
3. 概率投影计算
4. 不确定性度量评估
"""

import logging
import numpy as np
from typing import Tuple, Dict, Union, Optional
from dataclasses import dataclass
from enum import Enum
from scipy.special import softmax
from scipy.spatial.distance import cosine

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectionMethod(Enum):
    """投影方法枚举"""
    LINEAR = "linear"
    NONLINEAR = "nonlinear"
    HYBRID = "hybrid"

@dataclass
class ProjectionResult:
    """投影结果数据结构"""
    physical_vector: np.ndarray
    uncertainty_metrics: Dict[str, float]
    projection_quality: float
    method_used: ProjectionMethod

def validate_input_vector(vector: np.ndarray, 
                         expected_dim: Optional[int] = None) -> bool:
    """
    验证输入向量的有效性
    
    参数:
        vector: 输入向量
        expected_dim: 期望的维度 (可选)
        
    返回:
        bool: 验证是否通过
        
    异常:
        ValueError: 当输入不符合要求时
    """
    if not isinstance(vector, np.ndarray):
        raise ValueError("输入必须是numpy数组")
        
    if vector.ndim != 1:
        raise ValueError("输入向量必须是一维数组")
        
    if expected_dim is not None and vector.shape[0] != expected_dim:
        raise ValueError(f"输入向量维度应为 {expected_dim}, 实际为 {vector.shape[0]}")
        
    if not np.all(np.isfinite(vector)):
        raise ValueError("输入向量包含非有限值 (inf或nan)")
        
    return True

def fuzzy_boundary_handler(vector: np.ndarray, 
                          threshold: float = 0.8) -> np.ndarray:
    """
    处理模糊边界，应用平滑函数增强边界区域
    
    参数:
        vector: 输入语义向量
        threshold: 边界阈值 (0-1)
        
    返回:
        np.ndarray: 处理后的向量
    """
    logger.debug(f"应用模糊边界处理，阈值: {threshold}")
    sigmoid = 1 / (1 + np.exp(-10 * (vector - threshold)))
    return vector * sigmoid

def semantic_to_physical_projection(
    semantic_vector: np.ndarray,
    physical_dim: int = 3,
    method: ProjectionMethod = ProjectionMethod.HYBRID,
    uncertainty_weight: float = 0.1
) -> ProjectionResult:
    """
    核心函数1: 将模糊语义向量投影到物理向量空间
    
    参数:
        semantic_vector: 输入的语义向量 (高维)
        physical_dim: 目标物理向量维度
        method: 使用的投影方法
        uncertainty_weight: 不确定性权重因子
        
    返回:
        ProjectionResult: 包含投影结果和元数据
        
    示例:
        >>> semantic_vec = np.random.rand(128)
        >>> result = semantic_to_physical_projection(semantic_vec)
        >>> print(result.physical_vector)
    """
    # 输入验证
    try:
        validate_input_vector(semantic_vector)
    except ValueError as e:
        logger.error(f"输入验证失败: {str(e)}")
        raise
        
    logger.info(f"开始语义到物理投影，方法: {method.value}")
    
    # 应用模糊边界处理
    processed_vector = fuzzy_boundary_handler(semantic_vector)
    
    # 计算不确定性度量
    entropy = -np.sum(processed_vector * np.log2(processed_vector + 1e-10))
    variance = np.var(processed_vector)
    
    # 根据方法选择投影策略
    if method == ProjectionMethod.LINEAR:
        # 线性投影 (PCA风格)
        projection_matrix = np.random.randn(len(processed_vector), physical_dim)
        physical_vector = np.dot(processed_vector, projection_matrix)
    elif method == ProjectionMethod.NONLINEAR:
        # 非线性投影 (使用softmax和随机权重)
        weights = np.random.randn(len(processed_vector), physical_dim)
        physical_vector = softmax(np.dot(processed_vector, weights))
    else:
        # 混合方法
        linear_part = np.dot(processed_vector, 
                           np.random.randn(len(processed_vector), physical_dim//2))
        nonlinear_part = softmax(np.dot(processed_vector, 
                                      np.random.randn(len(processed_vector), physical_dim//2)))
        physical_vector = np.concatenate([linear_part, nonlinear_part])
    
    # 添加不确定性噪声
    noise = np.random.normal(0, uncertainty_weight, physical_dim)
    physical_vector += noise
    
    # 计算投影质量 (使用余弦相似度)
    original_reconstruction = np.dot(physical_vector[:len(processed_vector)], 
                                   np.linalg.pinv(physical_vector[:len(processed_vector)].reshape(-1, 1)))
    quality = 1 - cosine(processed_vector, original_reconstruction.flatten())
    
    # 准备不确定性指标
    uncertainty_metrics = {
        'entropy': float(entropy),
        'variance': float(variance),
        'noise_level': float(uncertainty_weight),
        'reconstruction_error': float(1 - quality)
    }
    
    logger.info(f"投影完成，质量评分: {quality:.3f}")
    
    return ProjectionResult(
        physical_vector=physical_vector,
        uncertainty_metrics=uncertainty_metrics,
        projection_quality=float(quality),
        method_used=method
    )

def inverse_physical_to_semantic(
    physical_vector: np.ndarray,
    original_semantic_dim: int,
    projection_matrix: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    核心函数2: 从物理向量重建语义向量 (逆投影)
    
    参数:
        physical_vector: 物理空间中的向量
        original_semantic_dim: 原始语义空间维度
        projection_matrix: 可选的投影矩阵 (如果已知)
        
    返回:
        Tuple[np.ndarray, Dict[str, float]]: 
            - 重建的语义向量
            - 重建误差指标
            
    示例:
        >>> physical_vec = np.array([0.1, 0.2, 0.3])
        >>> semantic_vec, errors = inverse_physical_to_semantic(physical_vec, 128)
    """
    # 输入验证
    try:
        validate_input_vector(physical_vector)
    except ValueError as e:
        logger.error(f"输入验证失败: {str(e)}")
        raise
        
    logger.info("开始物理到语义的逆投影")
    
    # 如果没有提供投影矩阵，使用随机初始化
    if projection_matrix is None:
        projection_matrix = np.random.randn(original_semantic_dim, len(physical_vector))
        logger.warning("使用随机投影矩阵，重建质量可能较差")
    
    # 计算伪逆重建
    pseudo_inverse = np.linalg.pinv(projection_matrix)
    reconstructed_semantic = np.dot(physical_vector, pseudo_inverse.T)
    
    # 计算重建误差
    reconstruction_error = np.linalg.norm(reconstructed_semantic - 
                                        np.dot(reconstructed_semantic, 
                                              np.dot(projection_matrix, pseudo_inverse)))
    
    # 应用模糊边界处理
    reconstructed_semantic = fuzzy_boundary_handler(reconstructed_semantic)
    
    # 准备误差指标
    error_metrics = {
        'reconstruction_error': float(reconstruction_error),
        'relative_error': float(reconstruction_error / (np.linalg.norm(reconstructed_semantic) + 1e-10)),
        'condition_number': float(np.linalg.cond(projection_matrix))
    }
    
    logger.info(f"逆投影完成，相对误差: {error_metrics['relative_error']:.3f}")
    
    return reconstructed_semantic, error_metrics

def calculate_uncertainty_index(
    semantic_vector: np.ndarray,
    physical_vector: np.ndarray,
    projection_quality: float
) -> float:
    """
    辅助函数: 计算综合不确定性指数
    
    参数:
        semantic_vector: 原始语义向量
        physical_vector: 投影后的物理向量
        projection_quality: 投影质量评分
        
    返回:
        float: 综合不确定性指数 (0-1)
        
    示例:
        >>> sem_vec = np.random.rand(128)
        >>> phys_vec = np.random.rand(3)
        >>> index = calculate_uncertainty_index(sem_vec, phys_vec, 0.8)
    """
    # 计算语义熵
    semantic_entropy = -np.sum(semantic_vector * np.log2(semantic_vector + 1e-10))
    
    # 计算物理空间分布
    phys_variance = np.var(physical_vector)
    
    # 综合计算
    uncertainty_index = (0.4 * semantic_entropy + 
                         0.3 * phys_variance + 
                         0.3 * (1 - projection_quality))
    
    # 标准化到0-1范围
    uncertainty_index = np.clip(uncertainty_index, 0, 1)
    
    logger.debug(f"计算不确定性指数: {uncertainty_index:.3f}")
    return float(uncertainty_index)

# 使用示例
if __name__ == "__main__":
    try:
        # 生成随机语义向量 (模拟高维语义空间)
        semantic_vector = np.random.rand(128)
        semantic_vector = semantic_vector / np.sum(semantic_vector)  # 归一化为概率分布
        
        # 执行投影
        result = semantic_to_physical_projection(
            semantic_vector,
            physical_dim=3,
            method=ProjectionMethod.HYBRID,
            uncertainty_weight=0.05
        )
        
        print(f"投影结果向量: {result.physical_vector}")
        print(f"不确定性指标: {result.uncertainty_metrics}")
        print(f"投影质量: {result.projection_quality:.3f}")
        
        # 计算不确定性指数
        uncertainty_idx = calculate_uncertainty_index(
            semantic_vector,
            result.physical_vector,
            result.projection_quality
        )
        print(f"综合不确定性指数: {uncertainty_idx:.3f}")
        
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}", exc_info=True)