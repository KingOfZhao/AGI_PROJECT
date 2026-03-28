"""
名称: auto_现象学触觉感知滤波器_该能力通过算法_悬_ea8623
描述: 现象学触觉感知滤波器。该能力通过算法'悬置'高层语义标签，迫使AI在底层感知层直接处理原始流。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PhenomenologicalTactileFilter")


class PerceptionMode(Enum):
    """感知模式枚举"""
    SEMANTIC = "semantic"  # 语义模式（包含标签）
    RAW_PHENOMENOLOGICAL = "raw"  # 现象学模式（悬置标签）


@dataclass
class TactileSample:
    """触觉样本数据结构"""
    timestamp: float
    force_vector: np.ndarray  # [Fx, Fy, Fz]
    torque_vector: np.ndarray  # [Tx, Ty, Tz]
    pressure_distribution: np.ndarray  # 压力分布矩阵
    semantic_label: Optional[str] = None  # 可选的高层语义标签
    
    def validate(self) -> bool:
        """验证数据有效性"""
        if self.timestamp < 0:
            raise ValueError("Timestamp cannot be negative")
        if self.force_vector.shape != (3,):
            raise ValueError("Force vector must be 3-dimensional")
        if self.torque_vector.shape != (3,):
            raise ValueError("Torque vector must be 3-dimensional")
        if self.pressure_distribution.ndim != 2:
            raise ValueError("Pressure distribution must be a 2D matrix")
        return True


@dataclass
class PerceptionState:
    """感知状态跟踪"""
    mode: PerceptionMode = PerceptionMode.SEMANTIC
    suspension_level: float = 0.0  # 悬置级别 (0.0 - 1.0)
    raw_buffer: List[TactileSample] = field(default_factory=list)
    semantic_memory: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.raw_buffer = []
        self.semantic_memory = {}


class PhenomenologicalTactileFilter:
    """
    现象学触觉感知滤波器
    
    通过算法实现'悬置'(Epoché)机制，在需要精细操作时暂时屏蔽高层语义标签，
    直接处理底层力觉流的时间序列特征，实现指尖级别的直觉反应。
    
    Attributes:
        buffer_size (int): 原始数据缓冲区大小
        suspension_threshold (float): 触发悬置的力变化阈值
        smoothing_factor (float): 信号平滑因子
        
    Example:
        >>> filter = PhenomenologicalTactileFilter()
        >>> sample = TactileSample(
        ...     timestamp=0.0,
        ...     force_vector=np.array([0.1, 0.2, 5.0]),
        ...     torque_vector=np.array([0.01, 0.02, 0.03]),
        ...     pressure_distribution=np.random.rand(10, 10),
        ...     semantic_label="metal_surface"
        ... )
        >>> processed = filter.process_sample(sample)
    """
    
    def __init__(
        self,
        buffer_size: int = 100,
        suspension_threshold: float = 2.0,
        smoothing_factor: float = 0.3
    ):
        """
        初始化现象学触觉感知滤波器
        
        Args:
            buffer_size: 原始数据缓冲区大小
            suspension_threshold: 触发悬置模式的力变化阈值
            smoothing_factor: 信号平滑因子 (0.0-1.0)
        """
        self.buffer_size = buffer_size
        self.suspension_threshold = suspension_threshold
        self.smoothing_factor = smoothing_factor
        self._state = PerceptionState()
        self._prev_force_magnitude = 0.0
        
        # 边界检查
        if not 0 < buffer_size <= 10000:
            raise ValueError("Buffer size must be between 1 and 10000")
        if not 0.0 <= smoothing_factor <= 1.0:
            raise ValueError("Smoothing factor must be between 0.0 and 1.0")
            
        logger.info("PhenomenologicalTactileFilter initialized with buffer_size=%d", buffer_size)
    
    def _calculate_force_magnitude(self, force_vector: np.ndarray) -> float:
        """
        计算力向量的大小
        
        Args:
            force_vector: 三维力向量
            
        Returns:
            力的大小标量值
        """
        return float(np.linalg.norm(force_vector))
    
    def _detect_instability(self, current_magnitude: float) -> bool:
        """
        检测力觉流的不稳定性（用于决定是否进入悬置模式）
        
        Args:
            current_magnitude: 当前力的大小
            
        Returns:
            是否检测到不稳定性
        """
        delta = abs(current_magnitude - self._prev_force_magnitude)
        self._prev_force_magnitude = current_magnitude
        return delta > self.suspension_threshold
    
    def suspend_semantic_labels(self, level: float = 1.0) -> None:
        """
        主动进入悬置模式，屏蔽语义标签
        
        Args:
            level: 悬置级别 (0.0 - 1.0)，1.0表示完全屏蔽
        """
        if not 0.0 <= level <= 1.0:
            raise ValueError("Suspension level must be between 0.0 and 1.0")
        
        self._state.mode = PerceptionMode.RAW_PHENOMENOLOGICAL
        self._state.suspension_level = level
        logger.info("Entered phenomenological mode with suspension level %.2f", level)
    
    def restore_semantic_perception(self) -> None:
        """恢复语义感知模式"""
        self._state.mode = PerceptionMode.SEMANTIC
        self._state.suspension_level = 0.0
        logger.info("Restored semantic perception mode")
    
    def process_sample(self, sample: TactileSample) -> Dict[str, Any]:
        """
        处理单个触觉样本
        
        根据当前感知模式处理样本，在悬置模式下屏蔽语义标签，
        只保留原始力觉流特征。
        
        Args:
            sample: 输入的触觉样本
            
        Returns:
            处理后的感知字典，包含:
            - timestamp: 时间戳
            - force_features: 力特征
            - torque_features: 扭矩特征
            - pressure_features: 压力分布特征
            - semantic_label: 语义标签（如果未被屏蔽）
            - mode: 当前感知模式
        """
        # 数据验证
        try:
            sample.validate()
        except ValueError as e:
            logger.error("Sample validation failed: %s", str(e))
            raise
        
        # 添加到缓冲区
        self._state.raw_buffer.append(sample)
        if len(self._state.raw_buffer) > self.buffer_size:
            self._state.raw_buffer.pop(0)
        
        # 计算原始特征
        force_magnitude = self._calculate_force_magnitude(sample.force_vector)
        torque_magnitude = self._calculate_force_magnitude(sample.torque_vector)
        pressure_stats = self._extract_pressure_stats(sample.pressure_distribution)
        
        # 自动检测是否需要进入悬置模式
        if self._detect_instability(force_magnitude) and self._state.mode == PerceptionMode.SEMANTIC:
            logger.debug("Force instability detected, auto-switching to phenomenological mode")
            self.suspend_semantic_labels(0.8)
        
        # 构建输出
        result = {
            "timestamp": sample.timestamp,
            "force_features": {
                "vector": sample.force_vector.tolist(),
                "magnitude": force_magnitude
            },
            "torque_features": {
                "vector": sample.torque_vector.tolist(),
                "magnitude": torque_magnitude
            },
            "pressure_features": pressure_stats,
            "mode": self._state.mode.value
        }
        
        # 根据悬置级别处理语义标签
        if self._state.mode == PerceptionMode.SEMANTIC or self._state.suspension_level < 0.5:
            result["semantic_label"] = sample.semantic_label
        else:
            # 完全悬置语义标签
            result["semantic_label"] = None
            logger.debug("Semantic label '%s' suspended", sample.semantic_label)
        
        return result
    
    def _extract_pressure_stats(self, pressure_matrix: np.ndarray) -> Dict[str, float]:
        """
        从压力分布矩阵中提取统计特征
        
        Args:
            pressure_matrix: 2D压力分布矩阵
            
        Returns:
            包含统计特征的字典
        """
        return {
            "mean": float(np.mean(pressure_matrix)),
            "std": float(np.std(pressure_matrix)),
            "max": float(np.max(pressure_matrix)),
            "min": float(np.min(pressure_matrix)),
            "centroid_x": float(np.average(np.arange(pressure_matrix.shape[1]), weights=np.sum(pressure_matrix, axis=0))),
            "centroid_y": float(np.average(np.arange(pressure_matrix.shape[0]), weights=np.sum(pressure_matrix, axis=1)))
        }
    
    def get_temporal_features(self, window_size: int = 10) -> Dict[str, Any]:
        """
        获取时间序列特征（用于实时跟踪）
        
        Args:
            window_size: 时间窗口大小
            
        Returns:
            时间序列特征字典，包含力觉流的趋势、变化率等
        """
        if len(self._state.raw_buffer) < 2:
            return {"status": "insufficient_data"}
        
        window = self._state.raw_buffer[-window_size:]
        
        forces = np.array([s.force_vector for s in window])
        timestamps = np.array([s.timestamp for s in window])
        
        # 计算时间序列特征
        force_magnitudes = np.linalg.norm(forces, axis=1)
        
        # 计算变化率（数值微分）
        if len(timestamps) > 1:
            dt = np.diff(timestamps)
            df = np.diff(force_magnitudes)
            rate_of_change = np.mean(df / np.maximum(dt, 1e-6))  # 避免除以零
        else:
            rate_of_change = 0.0
        
        return {
            "mean_force": float(np.mean(force_magnitudes)),
            "force_variance": float(np.var(force_magnitudes)),
            "rate_of_change": float(rate_of_change),
            "trend": "increasing" if rate_of_change > 0.1 else "decreasing" if rate_of_change < -0.1 else "stable",
            "window_size": len(window)
        }
    
    def execute_fine_manipulation(
        self,
        samples: List[TactileSample],
        target_force: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        执行精细操作（如穿针、修补裂痕）
        
        自动进入高悬置级别，基于原始力觉流进行实时跟踪和调整。
        
        Args:
            samples: 触觉样本列表
            target_force: 目标力大小（可选）
            
        Returns:
            处理后的感知结果列表
        """
        logger.info("Starting fine manipulation with %d samples", len(samples))
        
        # 进入高悬置模式
        self.suspend_semantic_labels(level=0.95)
        
        results = []
        for sample in samples:
            processed = self.process_sample(sample)
            
            # 添加实时调整建议
            if target_force is not None:
                current_force = processed["force_features"]["magnitude"]
                adjustment = target_force - current_force
                processed["adjustment_hint"] = {
                    "direction": "increase" if adjustment > 0 else "decrease",
                    "magnitude": abs(adjustment)
                }
            
            results.append(processed)
        
        # 恢复语义模式
        self.restore_semantic_perception()
        logger.info("Fine manipulation completed")
        
        return results


# 使用示例
if __name__ == "__main__":
    # 创建滤波器实例
    filter_system = PhenomenologicalTactileFilter(
        buffer_size=50,
        suspension_threshold=1.5,
        smoothing_factor=0.4
    )
    
    # 模拟触觉数据流
    np.random.seed(42)
    
    samples = []
    for i in range(10):
        sample = TactileSample(
            timestamp=float(i) * 0.1,
            force_vector=np.random.randn(3) * 2 + np.array([0, 0, 5]),
            torque_vector=np.random.randn(3) * 0.1,
            pressure_distribution=np.random.rand(8, 8) * 10,
            semantic_label="delicate_surface"
        )
        samples.append(sample)
    
    # 处理单个样本
    print("Single sample processing:")
    result = filter_system.process_sample(samples[0])
    print(f"  Mode: {result['mode']}")
    print(f"  Force magnitude: {result['force_features']['magnitude']:.3f}")
    print(f"  Semantic label: {result['semantic_label']}")
    
    # 执行精细操作
    print("\nFine manipulation execution:")
    results = filter_system.execute_fine_manipulation(samples[:5], target_force=5.0)
    for i, res in enumerate(results):
        print(f"  Sample {i}: Force={res['force_features']['magnitude']:.3f}, "
              f"Label={res['semantic_label']}, Hint={res.get('adjustment_hint', {})}")
    
    # 获取时间序列特征
    print("\nTemporal features:")
    temporal = filter_system.get_temporal_features(window_size=5)
    print(f"  Mean force: {temporal['mean_force']:.3f}")
    print(f"  Trend: {temporal['trend']}")
    print(f"  Rate of change: {temporal['rate_of_change']:.3f}")