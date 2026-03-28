"""
模块名称: auto_跨域迁移的_最小碰撞面积_量化_针对左右_5e4229
描述: 实现跨域概念迁移中的"最小碰撞面积"量化算法。
      用于判断两个看似无关的领域节点（如'生物进化'与'代码重构'）
      是否存在值得构建的深层语义连接，防止无效噪音连接。
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AnalogyResult:
    """
    类比验证结果的数据结构。
    
    Attributes:
        is_valid (bool): 连接是否有效（是否通过最小碰撞面积测试）。
        angle_degrees (float): 语义向量夹角（度）。
        distance_diff_percent (float): 差异度百分比（基于向量模长或空间距离）。
        overlap_score (float): 综合重叠得分。
        message (str): 诊断信息。
    """
    is_valid: bool
    angle_degrees: float
    distance_diff_percent: float
    overlap_score: float
    message: str

def _vector_operations(vec1: List[float], vec2: List[float]) -> Tuple[float, float, float]:
    """
    辅助函数：计算两个向量的夹角（度）和模长差异百分比。
    
    Args:
        vec1 (List[float]): 向量1
        vec2 (List[float]): 向量2
        
    Returns:
        Tuple[float, float, float]: (夹角度数, 模长差异百分比, 点积)
        
    Raises:
        ValueError: 如果向量维度不匹配或包含非法数值。
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"向量维度不匹配: {len(vec1)} vs {len(vec2)}")
    
    if not vec1 or not vec2:
        raise ValueError("向量不能为空")

    # 计算点积
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # 计算模长
    norm1 = math.sqrt(sum(a**2 for a in vec1))
    norm2 = math.sqrt(sum(b**2 for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        raise ValueError("向量模长不能为0")

    # 计算夹角 (Cosine Similarity -> Angle)
    cos_theta = max(-1.0, min(1.0, dot_product / (norm1 * norm2)))  # 防止浮点误差
    angle_rad = math.acos(cos_theta)
    angle_deg = math.degrees(angle_rad)
    
    # 计算模长差异百分比
    # 使用差异相对于较大模长的比例
    max_norm = max(norm1, norm2)
    diff_percent = abs(norm1 - norm2) / max_norm * 100 if max_norm > 0 else 0.0
    
    return angle_deg, diff_percent, dot_product

def calculate_semantic_overlap(
    node_a_vec: List[float], 
    node_b_vec: List[float], 
    angle_threshold: float = 30.0, 
    diff_threshold: float = 20.0
) -> AnalogyResult:
    """
    核心函数：计算两个跨域节点的语义重叠度，并验证是否构成有效类比。
    
    逻辑基于"最小碰撞面积"假设：
    1. 向量夹角必须足够小（< angle_threshold），代表语义方向高度相关。
    2. 向量模长（代表概念规模/强度）必须存在显著差异（> diff_threshold），
       或者根据具体业务逻辑调整（此处示例为差异度检测，防止完全相同的冗余连接）。
    
    Args:
        node_a_vec (List[float]): 源节点语义向量（如'生物进化'的特征向量）。
        node_b_vec (List[float]): 目标节点语义向量（如'代码重构'的特征向量）。
        angle_threshold (float): 允许的最大语义偏移角度（默认30度）。
        diff_threshold (float): 要求的最小结构差异度（默认20%）。
        
    Returns:
        AnalogyResult: 包含验证结果和详细指标的对象。
        
    Example:
        >>> v1 = [0.8, 0.2, 0.1] # 抽象特征：持续迭代
        >>> v2 = [0.7, 0.3, 0.1] # 抽象特征：代码优化
        >>> result = calculate_semantic_overlap(v1, v2)
        >>> print(result.is_valid)
    """
    try:
        logger.info("开始计算语义重叠...")
        
        # 数据验证
        if not isinstance(node_a_vec, list) or not isinstance(node_b_vec, list):
            raise TypeError("输入必须是列表类型")
            
        angle, diff_pct, dot = _vector_operations(node_a_vec, node_b_vec)
        
        logger.debug(f"计算结果 - 夹角: {angle:.2f}°, 差异度: {diff_pct:.2f}%")
        
        # 验证逻辑
        # 1. 角度检查：必须小于阈值（方向一致）
        is_angle_valid = angle < angle_threshold
        
        # 2. 差异度检查：必须大于阈值（避免同义反复，确保是跨域映射）
        is_diff_valid = diff_pct > diff_threshold
        
        # 综合判定
        is_valid = is_angle_valid and is_diff_valid
        
        # 计算重叠得分 (示例算法：夹角越小得分越高，差异度适中得分高)
        # 这里简化为夹角的余弦值作为重叠得分基础
        overlap_score = math.cos(math.radians(angle)) if is_valid else 0.0
        
        msg = (f"验证完成。角度匹配: {is_angle_valid}, 差异匹配: {is_diff_valid}. "
               f"Angle: {angle:.1f}° < {angle_threshold}° | Diff: {diff_pct:.1f}% > {diff_threshold}%")
        
        if is_valid:
            logger.info(f"有效类比连接! {msg}")
        else:
            logger.warning(f"无效噪音过滤. {msg}")
            
        return AnalogyResult(
            is_valid=is_valid,
            angle_degrees=angle,
            distance_diff_percent=diff_pct,
            overlap_score=overlap_score,
            message=msg
        )

    except Exception as e:
        logger.error(f"计算过程中发生错误: {str(e)}")
        return AnalogyResult(
            is_valid=False, 
            angle_degrees=180.0, 
            distance_diff_percent=0.0, 
            overlap_score=0.0, 
            message=f"Error: {str(e)}"
        )

def batch_validate_migration_candidates(
    candidates: List[Tuple[str, str, List[float], List[float]]], 
    config: Optional[dict] = None
) -> List[Tuple[str, str, bool]]:
    """
    核心函数：批量验证潜在的跨域迁移候选项。
    
    针对大量潜在的节点对进行过滤，筛选出值得构建'类比连接'的配对。
    
    Args:
        candidates (List[Tuple]): 候选项列表，格式为 
            [('源节点ID', '目标节点ID', 源向量, 目标向量), ...]
        config (Optional[dict]): 配置参数，覆盖默认的角度和差异阈值。
        
    Returns:
        List[Tuple[str, str, bool]]: 验证结果列表，包含节点ID和是否有效。
        
    Example:
        >>> data = [
        ...     ("bio_evo", "code_refactor", [1, 0], [0.9, 0.1]),
        ...     ("coffee", "blockchain", [1, 0], [0, 1])
        ... ]
        >>> results = batch_validate_migration_candidates(data)
    """
    if config is None:
        config = {}
        
    angle_th = config.get("angle_threshold", 30.0)
    diff_th = config.get("diff_threshold", 20.0)
    
    results = []
    
    logger.info(f"开始批量验证 {len(candidates)} 个候选项...")
    
    for src_id, dst_id, s_vec, d_vec in candidates:
        try:
            # 边界检查：确保向量非空
            if not s_vec or not d_vec:
                logger.warning(f"跳过空向量对: {src_id} -> {dst_id}")
                results.append((src_id, dst_id, False))
                continue
                
            res = calculate_semantic_overlap(s_vec, d_vec, angle_th, diff_th)
            results.append((src_id, dst_id, res.is_valid))
            
        except Exception as e:
            logger.error(f"处理对 {src_id}-{dst_id} 时出错: {e}")
            results.append((src_id, dst_id, False))
            
    valid_count = sum(1 for item in results if item[2])
    logger.info(f"批量验证完成。有效连接数: {valid_count}/{len(candidates)}")
    
    return results

# ==========================================
# 使用示例 / 单元测试入口
# ==========================================
if __name__ == "__main__":
    # 示例数据：模拟AGI系统中的概念节点
    # 假设我们有一个3维语义空间：[时间持续性, 结构复杂性, 目的性]
    
    # 案例 1: 生物进化 vs 代码重构
    # 预期：方向相似（都有时间持续和目的），但规模/性质有差异
    bio_evolution = [0.9, 0.8, 0.7]  # 持续时间长，结构极其复杂
    code_refactor = [0.85, 0.6, 0.75] # 持续，结构中等复杂
    
    # 案例 2: 喝咖啡 vs 区块链
    # 预期：语义空间正交，无关联
    drinking_coffee = [0.1, 0.1, 0.2]
    blockchain = [0.8, 0.9, 0.1]
    
    # 案例 3: 完全相同的节点 (噪音/冗余)
    node_self = [0.5, 0.5, 0.5]
    
    print("--- 单个测试 ---")
    res1 = calculate_semantic_overlap(bio_evolution, code_refactor)
    print(f"结果 1 (Bio vs Code): Valid={res1.is_valid}, Score={res1.overlap_score:.4f}")
    print(f"Details: {res1.message}\n")
    
    res2 = calculate_semantic_overlap(drinking_coffee, blockchain)
    print(f"结果 2 (Coffee vs Chain): Valid={res2.is_valid}, Score={res2.overlap_score:.4f}")
    print(f"Details: {res2.message}\n")
    
    # 批量测试
    print("--- 批量测试 ---")
    batch_data = [
        ("bio", "code", bio_evolution, code_refactor),
        ("coffee", "chain", drinking_coffee, blockchain),
        ("self", "self", node_self, node_self) # 应该失败（差异度低）
    ]
    
    batch_results = batch_validate_migration_candidates(batch_data)
    for src, dst, valid in batch_results:
        print(f"Connection: {src} -> {dst} | Valid: {valid}")