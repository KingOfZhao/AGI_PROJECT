"""
Module: tacit_skill_digitalizer.py
Description: 构建一个针对物理世界'隐性手艺'的全方位数字化流水线。
             该模块通过融合触觉感知数字化与多模态微观动作流对齐，
             将工匠指尖的微小形变、振动频率、滑移信号及肌肉力度曲线
             转化为可计算的'触觉频谱图'与时序向量。
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TacitSkillDigitalizer")


class SensorType(Enum):
    """支持的传感器类型枚举"""
    PRESSURE = "pressure"
    VIBRATION = "vibration"
    SLIP = "slip"
    EMG = "emg"  # 肌肉电信号


@dataclass
class TactileSample:
    """触觉样本数据结构"""
    timestamp: float
    sensor_type: SensorType
    values: np.ndarray  # 多维传感器数值数组
    
    def validate(self) -> bool:
        """验证数据有效性"""
        if self.timestamp < 0:
            logger.error(f"Invalid timestamp: {self.timestamp}")
            return False
        if not isinstance(self.values, np.ndarray):
            logger.error("Values must be numpy array")
            return False
        if self.values.size == 0:
            logger.error("Values array cannot be empty")
            return False
        return True


@dataclass
class SkillPrimitive:
    """技能原语数据结构"""
    primitive_id: str
    time_series_vector: np.ndarray
    spectral_features: np.ndarray
    parameters: Dict[str, float] = field(default_factory=dict)


def _normalize_signal(signal: np.ndarray, scale: Tuple[float, float] = (0, 1)) -> np.ndarray:
    """
    辅助函数：将信号归一化到指定范围
    
    Args:
        signal: 输入信号数组
        scale: 目标范围
        
    Returns:
        归一化后的信号数组
        
    Raises:
        ValueError: 如果输入信号全为相同值导致无法归一化
    """
    min_val, max_val = scale
    sig_min = np.min(signal)
    sig_max = np.max(signal)
    
    if np.isclose(sig_min, sig_max):
        logger.warning("Signal has constant values, returning zeros")
        return np.zeros_like(signal)
    
    normalized = (signal - sig_min) / (sig_max - sig_min)
    return normalized * (max_val - min_val) + min_val


def process_tactile_stream(
    samples: List[TactileSample],
    window_size: int = 50,
    overlap: float = 0.5
) -> Tuple[np.ndarray, Dict[SensorType, np.ndarray]]:
    """
    核心函数1: 处理触觉数据流，生成时序向量和频谱特征
    
    Args:
        samples: 触觉样本列表
        window_size: 滑动窗口大小
        overlap: 窗口重叠率(0-1)
        
    Returns:
        Tuple containing:
            - 时序特征向量
            - 各传感器类型的频谱特征字典
            
    Raises:
        ValueError: 如果输入参数无效或数据验证失败
    """
    logger.info(f"Processing tactile stream with {len(samples)} samples")
    
    # 数据验证
    if not samples:
        raise ValueError("Empty sample list provided")
    if not 0 <= overlap < 1:
        raise ValueError("Overlap must be in [0, 1)")
    if window_size < 1:
        raise ValueError("Window size must be positive integer")
    
    # 按传感器类型分组
    sensor_data: Dict[SensorType, List[np.ndarray]] = {}
    timestamps: List[float] = []
    
    for sample in samples:
        if not sample.validate():
            continue
        if sample.sensor_type not in sensor_data:
            sensor_data[sample.sensor_type] = []
        sensor_data[sample.sensor_type].append(sample.values)
        timestamps.append(sample.timestamp)
    
    if not sensor_data:
        raise ValueError("No valid samples after validation")
    
    # 处理每个传感器类型的数据
    spectral_features: Dict[SensorType, np.ndarray] = {}
    time_series_vectors = []
    
    for sensor_type, values_list in sensor_data.items():
        # 合并数据并归一化
        raw_signal = np.concatenate(values_list)
        norm_signal = _normalize_signal(raw_signal)
        
        # 计算短时傅里叶变换生成频谱特征
        try:
            freqs, times, Sxx = _compute_stft(norm_signal, window_size, overlap)
            spectral_features[sensor_type] = Sxx
        except Exception as e:
            logger.error(f"STFT computation failed for {sensor_type}: {str(e)}")
            spectral_features[sensor_type] = np.zeros((window_size//2 + 1, 10))
        
        # 提取时域特征
        features = _extract_time_features(norm_signal)
        time_series_vectors.append(features)
    
    # 合并多模态时序特征
    combined_vector = np.concatenate(time_series_vectors)
    logger.info(f"Generated combined vector of shape {combined_vector.shape}")
    
    return combined_vector, spectral_features


def _compute_stft(
    signal: np.ndarray,
    window_size: int,
    overlap: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    辅助函数: 计算短时傅里叶变换
    
    Args:
        signal: 输入信号
        window_size: 窗口大小
        overlap: 重叠率
        
    Returns:
        Tuple of (frequencies, times, STFT matrix)
    """
    hop_length = int(window_size * (1 - overlap))
    n_fft = window_size
    
    # 简化的STFT实现 (实际应用中可使用librosa或scipy)
    Sxx = []
    for i in range(0, len(signal) - window_size, hop_length):
        window = signal[i:i+window_size]
        fft_result = np.abs(np.fft.rfft(window))
        Sxx.append(fft_result)
    
    Sxx = np.array(Sxx).T
    freqs = np.fft.rfftfreq(window_size)
    times = np.arange(len(Sxx[0])) * hop_length
    
    return freqs, times, Sxx


def _extract_time_features(signal: np.ndarray) -> np.ndarray:
    """
    辅助函数: 提取时域特征
    
    Args:
        signal: 输入信号
        
    Returns:
        特征向量 [mean, std, max, min, skewness, kurtosis]
    """
    from scipy.stats import skew, kurtosis
    
    features = [
        np.mean(signal),
        np.std(signal),
        np.max(signal),
        np.min(signal),
        skew(signal),
        kurtosis(signal)
    ]
    
    return np.array(features)


def compress_to_skill_primitive(
    time_series: np.ndarray,
    spectral_features: Dict[SensorType, np.ndarray],
    primitive_id: str,
    compression_ratio: float = 0.2
) -> SkillPrimitive:
    """
    核心函数2: 将连续动作流压缩为技能原语
    
    Args:
        time_series: 时序特征向量
        spectral_features: 频谱特征字典
        primitive_id: 技能原语ID
        compression_ratio: 压缩比例 (0-1)
        
    Returns:
        SkillPrimitive 对象
        
    Raises:
        ValueError: 如果输入参数无效
    """
    logger.info(f"Compressing to skill primitive {primitive_id}")
    
    # 输入验证
    if not 0 < compression_ratio <= 1:
        raise ValueError("Compression ratio must be in (0, 1]")
    if not isinstance(time_series, np.ndarray):
        raise ValueError("Time series must be numpy array")
    if not spectral_features:
        raise ValueError("Spectral features cannot be empty")
    
    # 压缩时序特征
    compressed_dim = max(1, int(len(time_series) * compression_ratio))
    compressed_vector = np.random.choice(time_series, size=compressed_dim, replace=False)
    
    # 压缩频谱特征
    compressed_spectral = []
    for sensor_type, features in spectral_features.items():
        # 使用SVD降维
        if features.shape[1] > 0:
            u, s, vh = np.linalg.svd(features, full_matrices=False)
            rank = max(1, int(min(u.shape[1], vh.shape[0]) * compression_ratio))
            compressed = np.dot(u[:, :rank] * s[:rank], vh[:rank, :])
            compressed_spectral.append(compressed.flatten())
        else:
            compressed_spectral.append(np.zeros(1))
    
    # 合并频谱特征
    combined_spectral = np.concatenate(compressed_spectral)
    
    # 生成参数字典
    params = {
        "compression_ratio": compression_ratio,
        "input_dim": len(time_series),
        "output_dim": len(compressed_vector),
        "spectral_bands": len(combined_spectral)
    }
    
    logger.info(f"Compressed from {len(time_series)} to {len(compressed_vector)} dimensions")
    
    return SkillPrimitive(
        primitive_id=primitive_id,
        time_series_vector=compressed_vector,
        spectral_features=combined_spectral,
        parameters=params
    )


# 使用示例
if __name__ == "__main__":
    try:
        # 生成模拟触觉数据
        np.random.seed(42)
        samples = []
        
        # 创建多模态样本数据
        for i in range(100):
            timestamp = i * 0.01
            pressure_values = np.random.normal(0.5, 0.1, 3)  # 3维压力传感器
            vibration_values = np.random.normal(0.2, 0.05, 2)  # 2维振动传感器
            
            samples.append(TactileSample(
                timestamp=timestamp,
                sensor_type=SensorType.PRESSURE,
                values=pressure_values
            ))
            
            samples.append(TactileSample(
                timestamp=timestamp,
                sensor_type=SensorType.VIBRATION,
                values=vibration_values
            ))
        
        # 处理触觉流
        time_series, spectral_features = process_tactile_stream(
            samples, window_size=10, overlap=0.3
        )
        
        # 压缩为技能原语
        skill_primitive = compress_to_skill_primitive(
            time_series=time_series,
            spectral_features=spectral_features,
            primitive_id="welding_motion_001",
            compression_ratio=0.15
        )
        
        # 输出结果
        print(f"Skill Primitive ID: {skill_primitive.primitive_id}")
        print(f"Time Series Vector Shape: {skill_primitive.time_series_vector.shape}")
        print(f"Spectral Features Shape: {skill_primitive.spectral_features.shape}")
        print(f"Parameters: {skill_primitive.parameters}")
        
    except Exception as e:
        logger.error(f"Example execution failed: {str(e)}")