"""
Module: auto_决策层_跨域迁移_不同工业场景_9b98a1
Description: 【决策层：跨域迁移】构建跨域同构映射器，识别化工反应釜与水泥回转窑之间的
             结构相似性，将已验证的控制策略进行参数化变形并迁移，降低新场景试错成本。
Domain: Transfer Learning / Industrial Control
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossDomainMapper")


@dataclass
class IndustrialProcessProfile:
    """
    工业场景的标准化配置文件。
    
    Attributes:
        name (str): 场景名称
        thermal_inertia (float): 热惯性系数 (0.0-1.0)，表示系统对热量变化的响应速度
        delay_factor (float): 纯滞后时间因子
        nonlinearity_index (float): 非线性指数 (0.0-1.0)
        control_constraints (Dict[str, Tuple[float, float]]): 控制变量的上下限
    """
    name: str
    thermal_inertia: float
    delay_factor: float
    nonlinearity_index: float
    control_constraints: Dict[str, Tuple[float, float]]

    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.thermal_inertia <= 1.0):
            raise ValueError(f"thermal_inertia must be in [0, 1], got {self.thermal_inertia}")
        if self.delay_factor < 0:
            raise ValueError(f"delay_factor cannot be negative, got {self.delay_factor}")
        if not (0.0 <= self.nonlinearity_index <= 1.0):
            raise ValueError(f"nonlinearity_index must be in [0, 1], got {self.nonlinearity_index}")


class CrossDomainIsomorphicMapper:
    """
    跨域同构映射器。
    
    用于识别不同工业场景（源域与目标域）之间的结构相似性，
    并基于物理参数差异对控制策略进行参数化变形。
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化映射器。
        
        Args:
            similarity_threshold (float): 判定场景可迁移性的相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self._mapping_cache: Dict[str, Any] = {}
        logger.info("CrossDomainIsomorphicMapper initialized with threshold %.2f", similarity_threshold)

    def _validate_inputs(self, source: IndustrialProcessProfile, target: IndustrialProcessProfile) -> None:
        """
        辅助函数：验证输入的场景配置是否有效。
        
        Args:
            source: 源领域配置
            target: 目标领域配置
            
        Raises:
            ValueError: 如果配置无效
        """
        if not isinstance(source, IndustrialProcessProfile) or not isinstance(target, IndustrialProcessProfile):
            raise TypeError("Source and Target must be IndustrialProcessProfile instances")
        logger.debug("Input profiles validated: %s -> %s", source.name, target.name)

    def calculate_structural_similarity(self, source: IndustrialProcessProfile, target: IndustrialProcessProfile) -> Tuple[float, Dict[str, float]]:
        """
        核心函数 1: 计算源领域与目标领域的结构相似度。
        
        基于热惯性、滞后因子和非线性指数的欧氏距离计算相似度。
        相似度越高，代表控制逻辑的同构性越强。
        
        Args:
            source: 源领域配置（如：化工反应釜）
            target: 目标领域配置（如：水泥回转窑）
            
        Returns:
            Tuple[float, Dict[str, float]]: 
                - 综合相似度得分 (0.0-1.0)
                - 各维度的特征差异字典
        """
        self._validate_inputs(source, target)
        
        # 提取特征向量
        vec_src = np.array([source.thermal_inertia, source.delay_factor, source.nonlinearity_index])
        vec_tgt = np.array([target.thermal_inertia, target.delay_factor, target.nonlinearity_index])
        
        # 归一化差异计算 (假设特征已归一化到0-1)
        delta = vec_src - vec_tgt
        distance = np.linalg.norm(delta)
        
        # 转换为相似度 (0-1范围，距离0为相似度1)
        max_possible_dist = np.sqrt(3) # 3维单位向量的最大距离
        similarity = 1.0 - (distance / max_possible_dist)
        
        feature_deltas = {
            "thermal_inertia_diff": float(target.thermal_inertia - source.thermal_inertia),
            "delay_factor_diff": float(target.delay_factor - source.delay_factor),
            "nonlinearity_diff": float(target.nonlinearity_index - source.nonlinearity_index)
        }
        
        logger.info(f"Similarity calculation: {source.name} vs {target.name} = {similarity:.4f}")
        
        if similarity < self.similarity_threshold:
            logger.warning(f"Low structural similarity ({similarity:.2f}). Migration may be risky.")
            
        return float(similarity), feature_deltas

    def transfer_strategy_parameters(self, source_params: Dict[str, float], feature_deltas: Dict[str, float], target: IndustrialProcessProfile) -> Dict[str, float]:
        """
        核心函数 2: 迁移并变形控制策略参数。
        
        根据物理特征的差异（delta），对源领域的PID参数或控制增益进行变形。
        规则：
        1. 热惯性增加 -> 降低积分作用，防止超调
        2. 滞后增加 -> 降低比例增益，增加微分作用
        
        Args:
            source_params: 源领域的控制参数 (e.g., {'kp': 1.0, 'ki': 0.1, 'kd': 0.01})
            feature_deltas: _calculate_structural_similarity 返回的特征差异
            target: 目标领域配置（用于边界检查）
            
        Returns:
            Dict[str, float]: 变形后的目标领域控制参数
        """
        if not source_params:
            raise ValueError("Source parameters cannot be empty")

        transferred_params = source_params.copy()
        
        try:
            # 1. 处理热惯性差异 (影响积分系数 Ki)
            # 如果目标惯性大，系统反应慢，需要减小Ki防止累积过大
            inertia_shift = feature_deltas.get('thermal_inertia_diff', 0.0)
            if 'ki' in transferred_params:
                transferred_params['ki'] *= (1.0 - inertia_shift * 0.8) # 经验系数0.8
            
            # 2. 处理滞后差异 (影响比例和微分)
            # 如果目标滞后大，需要减小Kp防止震荡，增加Kd抑制滞后
            delay_shift = feature_deltas.get('delay_factor_diff', 0.0)
            if 'kp' in transferred_params:
                transferred_params['kp'] *= np.exp(-delay_shift) # 指数衰减
            if 'kd' in transferred_params:
                transferred_params['kd'] *= (1.0 + delay_shift * 1.2)

            # 3. 边界检查
            for param, value in transferred_params.items():
                if param in target.control_constraints:
                    min_val, max_val = target.control_constraints[param]
                    if not (min_val <= value <= max_val):
                        logger.warning(f"Param {param} out of bounds [{min_val}, {max_val}]. Clamping.")
                        transferred_params[param] = np.clip(value, min_val, max_val)
                        
            logger.info(f"Parameters transferred successfully: {transferred_params}")
            
        except Exception as e:
            logger.error(f"Error during parameter transformation: {str(e)}")
            raise RuntimeError("Parameter transformation failed") from e

        return transferred_params

# ============================================================
# Usage Example
# ============================================================

if __name__ == "__main__":
    # 1. 定义源领域：化工反应釜
    # 特点：热惯性较小，滞后中等，非线性强
    source_reactor = IndustrialProcessProfile(
        name="Chemical_Reactor_A",
        thermal_inertia=0.3,
        delay_factor=0.2,
        nonlinearity_index=0.8,
        control_constraints={"kp": (0.1, 5.0), "ki": (0.01, 1.0), "kd": (0.0, 0.5)}
    )

    # 2. 定义目标领域：水泥回转窑
    # 特点：热惯性极大，滞后大，非线性中等
    target_kiln = IndustrialProcessProfile(
        name="Cement_Kiln_B",
        thermal_inertia=0.85,
        delay_factor=0.6,
        nonlinearity_index=0.5,
        control_constraints={"kp": (0.1, 5.0), "ki": (0.01, 1.0), "kd": (0.0, 0.5)}
    )

    # 3. 源领域的已验证控制参数
    verified_pid_params = {
        "kp": 2.5,
        "ki": 0.8,
        "kd": 0.05
    }

    # 4. 初始化映射器
    mapper = CrossDomainIsomorphicMapper(similarity_threshold=0.5)

    try:
        # 5. 计算相似度
        similarity_score, deltas = mapper.calculate_structural_similarity(source_reactor, target_kiln)
        print(f"\nStructural Similarity: {similarity_score:.4f}")
        print(f"Feature Deltas: {deltas}")

        # 6. 迁移参数
        new_params = mapper.transfer_strategy_parameters(verified_pid_params, deltas, target_kiln)
        
        print("\n=== Migration Result ===")
        print(f"Source Params: {verified_pid_params}")
        print(f"Target Params: {new_params}")
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")