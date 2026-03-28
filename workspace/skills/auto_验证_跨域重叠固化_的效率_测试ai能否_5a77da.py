"""
模块名称: auto_验证_跨域重叠固化_的效率_测试ai能否_5a77da
描述: 验证'跨域重叠固化'的效率。测试AI能否识别两个看似无关领域的深层同构性。
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator
from functools import wraps
import time
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 类型别名定义
Vector = Union[List[float], np.ndarray]
Matrix = Union[List[List[float]], np.ndarray]

class DomainModelSchema(BaseModel):
    """域模型数据验证模式"""
    domain_name: str = Field(..., min_length=1, max_length=100)
    parameters: Dict[str, float] = Field(..., min_items=1)
    evolution_matrix: List[List[float]] = Field(..., min_items=1)
    initial_state: List[float] = Field(..., min_items=1)
    
    @validator('evolution_matrix')
    def validate_matrix(cls, v):
        if not all(len(row) == len(v[0]) for row in v):
            raise ValueError("矩阵必须具有相同的行和列长度")
        return v
    
    @validator('initial_state')
    def validate_state(cls, v, values):
        if 'evolution_matrix' in values and len(v) != len(values['evolution_matrix'][0]):
            raise ValueError("初始状态向量必须与矩阵维度匹配")
        return v

@dataclass
class IsomorphismResult:
    """同构性检测结果"""
    is_isomorphic: bool
    similarity_score: float
    shared_kernel: Optional[str] = None
    parameter_mapping: Optional[Dict[str, str]] = None
    error: Optional[str] = None

def timing_decorator(func):
    """计时装饰器，用于测量函数执行时间"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        logger.info(f"函数 {func.__name__} 执行耗时: {elapsed:.6f} 秒")
        return result
    return wrapper

def normalize_vector(vector: Vector) -> np.ndarray:
    """
    归一化向量到单位长度
    
    参数:
        vector: 输入向量
        
    返回:
        np.ndarray: 归一化后的向量
        
    示例:
        >>> normalize_vector([3, 4])
        array([0.6, 0.8])
    """
    try:
        vec = np.asarray(vector, dtype=np.float64)
        norm = np.linalg.norm(vec)
        if norm == 0:
            logger.warning("遇到零向量，返回原向量")
            return vec
        return vec / norm
    except Exception as e:
        logger.error(f"向量归一化失败: {str(e)}")
        raise ValueError(f"向量归一化失败: {str(e)}")

@timing_decorator
def detect_mathematical_isomorphism(
    domain_a: DomainModelSchema, 
    domain_b: DomainModelSchema,
    similarity_threshold: float = 0.85
) -> IsomorphismResult:
    """
    检测两个域模型之间的数学同构性
    
    参数:
        domain_a: 第一个域模型
        domain_b: 第二个域模型
        similarity_threshold: 相似度阈值
        
    返回:
        IsomorphismResult: 包含同构性检测结果的dataclass
        
    示例:
        >>> model_a = DomainModelSchema(
        ...     domain_name="Biological Virus",
        ...     parameters={"beta": 0.3, "gamma": 0.1},
        ...     evolution_matrix=[[0.9, 0.1], [0.05, 0.95]],
        ...     initial_state=[0.99, 0.01]
        ... )
        >>> model_b = DomainModelSchema(
        ...     domain_name="Computer Virus",
        ...     parameters={"infection_rate": 0.35, "recovery_rate": 0.12},
        ...     evolution_matrix=[[0.88, 0.12], [0.04, 0.96]],
        ...     initial_state=[0.98, 0.02]
        ... )
        >>> result = detect_mathematical_isomorphism(model_a, model_b)
    """
    try:
        # 验证输入
        if similarity_threshold <= 0 or similarity_threshold > 1:
            raise ValueError("相似度阈值必须在(0, 1]范围内")
            
        # 检查矩阵维度是否匹配
        if len(domain_a.evolution_matrix) != len(domain_b.evolution_matrix):
            return IsomorphismResult(
                is_isomorphic=False,
                similarity_score=0.0,
                error="矩阵维度不匹配"
            )
            
        # 计算矩阵相似度
        matrix_a = np.array(domain_a.evolution_matrix)
        matrix_b = np.array(domain_b.evolution_matrix)
        
        # 归一化矩阵以便比较
        norm_a = matrix_a / np.linalg.norm(matrix_a)
        norm_b = matrix_b / np.linalg.norm(matrix_b)
        
        # 计算Frobenius内积作为相似度度量
        similarity = np.sum(norm_a * norm_b) / np.sqrt(np.sum(norm_a**2) * np.sum(norm_b**2))
        
        # 检测参数映射
        param_mapping = _detect_parameter_mapping(
            domain_a.parameters, 
            domain_b.parameters,
            threshold=similarity_threshold
        )
        
        # 确定是否同构
        is_iso = similarity >= similarity_threshold and param_mapping is not None
        
        # 推断可能的共享内核
        shared_kernel = None
        if is_iso:
            if _is_sir_model_like(matrix_a, domain_a.parameters):
                shared_kernel = "SIR_Model_Kernel"
            elif _is_random_walk_like(matrix_a):
                shared_kernel = "Random_Walk_Kernel"
            else:
                shared_kernel = "Generic_Dynamical_System"
                
        logger.info(f"检测到相似度: {similarity:.4f}, 同构性: {is_iso}")
        
        return IsomorphismResult(
            is_isomorphic=is_iso,
            similarity_score=float(similarity),
            shared_kernel=shared_kernel,
            parameter_mapping=param_mapping
        )
        
    except Exception as e:
        logger.error(f"同构性检测失败: {str(e)}")
        return IsomorphismResult(
            is_isomorphic=False,
            similarity_score=0.0,
            error=str(e)
        )

def _detect_parameter_mapping(
    params_a: Dict[str, float],
    params_b: Dict[str, float],
    threshold: float = 0.9
) -> Optional[Dict[str, str]]:
    """
    辅助函数: 检测两个参数集之间的可能映射
    
    参数:
        params_a: 第一个参数集
        params_b: 第二个参数集
        threshold: 参数值相似度阈值
        
    返回:
        Optional[Dict[str, str]]: 参数映射字典，如果没有找到足够相似的映射则返回None
    """
    mapping = {}
    used_b_keys = set()
    
    # 归一化参数值以便比较
    norm_a = {k: v / max(params_a.values()) for k, v in params_a.items()}
    norm_b = {k: v / max(params_b.values()) for k, v in params_b.items()}
    
    for a_key, a_val in norm_a.items():
        best_match = None
        best_sim = 0.0
        
        for b_key, b_val in norm_b.items():
            if b_key in used_b_keys:
                continue
                
            # 计算参数相似度 (使用相对差异)
            similarity = 1.0 - abs(a_val - b_val) / max(a_val, b_val)
            
            if similarity > best_sim and similarity >= threshold:
                best_sim = similarity
                best_match = b_key
                
        if best_match:
            mapping[a_key] = best_match
            used_b_keys.add(best_match)
    
    return mapping if len(mapping) == min(len(params_a), len(params_b)) else None

def _is_sir_model_like(matrix: np.ndarray, params: Dict[str, float]) -> bool:
    """
    辅助函数: 判断矩阵是否类似于SIR模型
    
    参数:
        matrix: 演化矩阵
        params: 参数字典
        
    返回:
        bool: 如果矩阵结构类似于SIR模型则返回True
    """
    # SIR模型通常有转移概率和恢复概率参数
    sir_keywords = {'beta', 'gamma', 'infection', 'recovery', 'transmission'}
    params_lower = {k.lower() for k in params.keys()}
    
    if not sir_keywords.intersection(params_lower):
        return False
        
    # 检查矩阵结构 (简化检测)
    if matrix.shape[0] >= 2 and matrix.shape[1] >= 2:
        # 检查是否有对角占优特性
        if np.allclose(matrix, np.diag(np.diag(matrix)), atol=0.2):
            return True
            
    return False

def _is_random_walk_like(matrix: np.ndarray) -> bool:
    """
    辅助函数: 判断矩阵是否类似于随机游走模型
    
    参数:
        matrix: 演化矩阵
        
    返回:
        bool: 如果矩阵结构类似于随机游走则返回True
    """
    # 随机游走矩阵通常是行随机矩阵
    if matrix.shape[0] == matrix.shape[1]:
        row_sums = np.sum(matrix, axis=1)
        if np.allclose(row_sums, np.ones_like(row_sums), atol=0.1):
            return True
    return False

@timing_decorator
def create_unified_kernel(
    domain_models: List[DomainModelSchema],
    force_unify: bool = False
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    从多个域模型创建统一的数学内核
    
    参数:
        domain_models: 域模型列表
        force_unify: 是否强制统一（即使相似度不高）
        
    返回:
        Tuple[np.ndarray, Dict[str, Any]]: (统一内核矩阵, 元数据字典)
        
    示例:
        >>> models = [model_a, model_b, model_c]
        >>> kernel, meta = create_unified_kernel(models)
    """
    if not domain_models:
        raise ValueError("至少需要一个域模型")
        
    if len(domain_models) == 1:
        logger.warning("只有一个模型，返回其演化矩阵作为内核")
        return np.array(domain_models[0].evolution_matrix), {
            'source_models': [domain_models[0].domain_name],
            'unification_score': 1.0,
            'is_forced': False
        }
    
    # 收集所有演化矩阵
    matrices = [np.array(m.evolution_matrix) for m in domain_models]
    ref_shape = matrices[0].shape
    
    # 验证矩阵形状一致性
    for i, mat in enumerate(matrices[1:], 1):
        if mat.shape != ref_shape:
            raise ValueError(f"模型 {i} 的矩阵形状 {mat.shape} 与参考形状 {ref_shape} 不匹配")
    
    # 计算成对相似度
    similarity_scores = []
    for i in range(len(matrices)):
        for j in range(i+1, len(matrices)):
            result = detect_mathematical_isomorphism(
                domain_models[i], domain_models[j]
            )
            similarity_scores.append(result.similarity_score)
    
    avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.0
    min_similarity = np.min(similarity_scores) if similarity_scores else 0.0
    
    # 决定是否统一
    if not force_unify and min_similarity < 0.7:
        raise ValueError(f"模型间相似度太低 (最小: {min_similarity:.2f})，无法创建统一内核")
    
    # 创建统一内核（矩阵平均）
    unified_kernel = np.mean(matrices, axis=0)
    
    # 收集元数据
    metadata = {
        'source_models': [m.domain_name for m in domain_models],
        'unification_score': float(avg_similarity),
        'min_similarity': float(min_similarity),
        'is_forced': force_unify,
        'kernel_type': 'average'
    }
    
    logger.info(f"创建统一内核，平均相似度: {avg_similarity:.4f}")
    return unified_kernel, metadata

def example_usage():
    """使用示例函数"""
    # 创建两个域模型（生物病毒和计算机病毒）
    bio_virus = DomainModelSchema(
        domain_name="Biological_Virus_Transmission",
        parameters={"beta": 0.3, "gamma": 0.1, "mu": 0.01},
        evolution_matrix=[
            [0.9, 0.08, 0.02],
            [0.05, 0.9, 0.05],
            [0.01, 0.01, 0.98]
        ],
        initial_state=[0.99, 0.01, 0.0]
    )
    
    comp_virus = DomainModelSchema(
        domain_name="Computer_Virus_Propagation",
        parameters={"infection_rate": 0.32, "recovery_rate": 0.11, "mutation_rate": 0.015},
        evolution_matrix=[
            [0.88, 0.10, 0.02],
            [0.06, 0.88, 0.06],
            [0.02, 0.02, 0.96]
        ],
        initial_state=[0.98, 0.02, 0.0]
    )
    
    # 第三种不相关的模型
    market_model = DomainModelSchema(
        domain_name="Market_Dynamics",
        parameters={"volatility": 0.2, "trend": 0.05},
        evolution_matrix=[
            [0.7, 0.3],
            [0.2, 0.8]
        ],
        initial_state=[0.5, 0.5]
    )
    
    # 检测生物病毒和计算机病毒之间的同构性
    print("=== 检测生物病毒和计算机病毒之间的同构性 ===")
    result = detect_mathematical_isomorphism(bio_virus, comp_virus)
    print(f"是否同构: {result.is_isomorphic}")
    print(f"相似度分数: {result.similarity_score:.4f}")
    print(f"共享内核: {result.shared_kernel}")
    print(f"参数映射: {result.parameter_mapping}")
    
    # 尝试创建统一内核
    print("\n=== 创建统一内核 ===")
    try:
        kernel, meta = create_unified_kernel([bio_virus, comp_virus])
        print("统一内核矩阵:")
        print(kernel)
        print("\n元数据:")
        for k, v in meta.items():
            print(f"{k}: {v}")
    except ValueError as e:
        print(f"无法创建统一内核: {str(e)}")
    
    # 尝试混合不相似的模型
    print("\n=== 尝试混合不相似的模型 ===")
    try:
        kernel, meta = create_unified_kernel([bio_virus, market_model])
    except ValueError as e:
        print(f"预期中的错误: {str(e)}")

if __name__ == "__main__":
    example_usage()