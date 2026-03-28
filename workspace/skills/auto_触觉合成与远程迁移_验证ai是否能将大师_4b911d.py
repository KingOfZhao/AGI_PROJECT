"""
名称: auto_触觉合成与远程迁移_验证ai是否能将大师_4b911d
描述: 触觉合成与远程迁移模块。本模块实现了将高精度触觉传感器数据（如高频振动、压力分布）
     转换为标准化数字信号，并通过触觉渲染引擎合成为可被远程个体感知的触觉指令。
     旨在验证AI在跨域触觉传输中的可行性与保真度。
领域: haptic_technology
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HapticSynthesisModule")

class SignalType(Enum):
    """触觉信号类型枚举"""
    VIBRATION = "vibration"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    TEXTURE = "texture"

@dataclass
class HapticSensorData:
    """
    源端传感器数据结构
    Attributes:
        timestamp (float): 时间戳 (ms)
        signal_type (SignalType): 信号类型
        raw_waveform (np.ndarray): 原始波形数据 (高频振动或压力变化)
        spatial_matrix (np.ndarray): 空间压力分布矩阵 (2D array)
    """
    timestamp: float
    signal_type: SignalType
    raw_waveform: np.ndarray
    spatial_matrix: np.ndarray

@dataclass
class SynthesizedSignal:
    """
    合成后的触觉指令结构
    Attributes:
        target_actuator_id (str): 目标执行器ID
        frequency_hz (float): 合成频率
        amplitude (float): 振幅强度 (0.0-1.0)
        duration_ms (float): 持续时间
        waveform_pattern (List[float]): 生成波形
    """
    target_actuator_id: str
    frequency_hz: float
    amplitude: float
    duration_ms: float
    waveform_pattern: List[float]

class HapticSynthesisError(Exception):
    """自定义异常：触觉合成过程中的错误"""
    pass

def validate_sensor_input(data: HapticSensorData) -> bool:
    """
    [辅助函数] 验证输入的传感器数据是否有效
    
    Args:
        data (HapticSensorData): 待验证的传感器数据对象
        
    Returns:
        bool: 数据是否有效
        
    Raises:
        ValueError: 如果数据包含无效值
    """
    if data.timestamp < 0:
        raise ValueError("Timestamp cannot be negative.")
    
    if not isinstance(data.raw_waveform, np.ndarray) or data.raw_waveform.size == 0:
        raise ValueError("Raw waveform must be a non-empty numpy array.")
        
    if not isinstance(data.spatial_matrix, np.ndarray):
        raise ValueError("Spatial matrix must be a numpy array.")
        
    # 检查数值边界 (假设传感器量程为 0-10.0 Volts/Pressure Units)
    if np.any(data.raw_waveform < 0) or np.any(data.raw_waveform > 10.0):
        logger.warning("Waveform data contains values outside expected physical limits (0-10).")
        
    logger.debug(f"Sensor data validation passed for timestamp: {data.timestamp}")
    return True

def extract_haptic_features(data: HapticSensorData) -> Dict[str, float]:
    """
    [核心函数 1] 从原始数据中提取隐性触觉特征 (AI特征提取模拟)
    
    将高频时域数据和空间压力数据转换为频域特征和强度指标。
    
    Args:
        data (HapticSensorData): 原始传感器数据
        
    Returns:
        Dict[str, float]: 包含主频率、平均压力、峰值因子等特征的字典
        
    Example:
        >>> sensor_data = HapticSensorData(...)
        >>> features = extract_haptic_features(sensor_data)
        >>> print(features['dominant_freq'])
    """
    try:
        validate_sensor_input(data)
        logger.info(f"Extracting features for {data.signal_type.value} signal...")
        
        # 1. 频域分析 (模拟FFT提取主频)
        # 假设采样率为1000Hz
        sample_rate = 1000.0
        fft_vals = np.fft.fft(data.raw_waveform)
        freqs = np.fft.fftfreq(len(data.raw_waveform), 1/sample_rate)
        magnitude = np.abs(fft_vals)
        
        # 获取主频率
        peak_idx = np.argmax(magnitude[:len(freqs)//2])
        dominant_freq = abs(freqs[peak_idx])
        
        # 2. 空间分析 (计算压力中心 CoP)
        # 归一化空间矩阵
        norm_matrix = data.spatial_matrix / (np.max(data.spatial_matrix) + 1e-6)
        total_pressure = np.sum(data.spatial_matrix)
        
        if total_pressure == 0:
            cop_x, cop_y = 0.0, 0.0
        else:
            # 计算质心坐标
            y_coords, x_coords = np.indices(data.spatial_matrix.shape)
            cop_x = np.sum(x_coords * data.spatial_matrix) / total_pressure
            cop_y = np.sum(y_coords * data.spatial_matrix) / total_pressure
            
        features = {
            "dominant_freq": dominant_freq,
            "rms_intensity": float(np.sqrt(np.mean(data.raw_waveform**2))),
            "center_pressure_x": float(cop_x),
            "center_pressure_y": float(cop_y),
            "spatial_variance": float(np.var(data.spatial_matrix))
        }
        
        logger.info(f"Feature extraction complete. Dominant Freq: {dominant_freq:.2f}Hz")
        return features

    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
        raise HapticSynthesisError(f"Input validation failed: {ve}")
    except Exception as e:
        logger.exception("Unexpected error during feature extraction.")
        raise HapticSynthesisError("Feature extraction failed.")

def synthesize_remote_signal(
    features: Dict[str, float], 
    target_device_profile: Dict[str, any]
) -> SynthesizedSignal:
    """
    [核心函数 2] 基于特征合成远程触觉信号 (触觉渲染)
    
    将提取的数字特征转换为目标执行器可执行的物理参数。
    此过程模拟了AI将"手感"映射到不同硬件能力的过程。
    
    Args:
        features (Dict[str, float]): 从源端提取的特征数据
        target_device_profile (Dict[str, any]): 目标设备的性能参数
            (例如: max_freq, resolution, actuator_type)
            
    Returns:
        SynthesizedSignal: 合成后的信号对象
        
    Raises:
        HapticSynthesisError: 如果合成参数超出设备物理限制
        
    Example:
        >>> features = {'dominant_freq': 250, 'rms_intensity': 0.8, ...}
        >>> profile = {'max_freq': 500, 'id': 'act_01'}
        >>> signal = synthesize_remote_signal(features, profile)
    """
    # 设备限制检查
    max_freq = target_device_profile.get('max_freq', 1000)
    actuator_id = target_device_profile.get('id', 'default_actuator')
    
    target_freq = features['dominant_freq']
    if target_freq > max_freq:
        logger.warning(f"Target freq {target_freq} exceeds limit {max_freq}. Clamping.")
        target_freq = max_freq
        
    # 强度映射 (假设特征强度是0-1范围，映射到振幅)
    # 这里添加一个简单的非线性映射以模拟真实的触觉感知曲线
    raw_intensity = features['rms_intensity']
    mapped_amplitude = np.tanh(raw_intensity * 1.5)  # 压缩高动态范围
    
    # 波形生成 (生成正弦波 + 谐波以模拟纹理感)
    duration_ms = 100.0
    t = np.linspace(0, duration_ms / 1000, int(duration_ms), endpoint=False)
    
    # 基波 + 噪声纹理 (基于spatial_variance)
    wave = mapped_amplitude * np.sin(2 * np.pi * target_freq * t)
    texture_noise = features['spatial_variance'] * np.random.normal(0, 0.1, len(t))
    final_wave = wave + texture_noise
    
    # 归一化到 0-1 范围供执行器使用
    final_wave = (final_wave - np.min(final_wave)) / (np.max(final_wave) - np.min(final_wave) + 1e-6)

    logger.info(f"Synthesized signal for {actuator_id}: Freq={target_freq}Hz, Amp={mapped_amplitude:.2f}")

    return SynthesizedSignal(
        target_actuator_id=actuator_id,
        frequency_hz=target_freq,
        amplitude=float(mapped_amplitude),
        duration_ms=duration_ms,
        waveform_pattern=final_wave.tolist()
    )

# ==========================================
# 使用示例 / Main Execution Block
# ==========================================
if __name__ == "__main__":
    # 1. 模拟生成主人的手部触觉数据 (模拟抓握粗糙表面的瞬间)
    sample_rate = 1000
    t = np.linspace(0, 1, sample_rate, endpoint=False) # 1秒数据
    # 模拟 250Hz 的高频振动 (粗糙纹理)
    vibration_data = 0.6 * np.sin(2 * np.pi * 250 * t) + 0.1 * np.random.normal(0, 1, len(t))
    # 模拟 5x5 压力传感器阵列的分布 (指尖受力)
    pressure_matrix = np.zeros((5, 5))
    pressure_matrix[2:4, 2:4] = np.array([[0.8, 0.6], [0.7, 0.9]]) # 模拟非均匀压力

    master_data = HapticSensorData(
        timestamp=1698765432.123,
        signal_type=SignalType.TEXTURE,
        raw_waveform=vibration_data,
        spatial_matrix=pressure_matrix
    )

    print("-" * 30)
    print("Starting Haptic Teleportation Protocol...")
    print("-" * 30)

    try:
        # 2. 提取特征 (发送端处理)
        extracted_features = extract_haptic_features(master_data)
        print(f"Extracted Features: {extracted_features}")

        # 3. 合成远程信号 (接收端/接收者处理)
        # 假设远程设备性能较弱，最高支持 300Hz
        remote_device_config = {
            'id': 'remote_glove_01',
            'max_freq': 300,
            'resolution': 'low'
        }

        synthesized_output = synthesize_remote_signal(extracted_features, remote_device_config)
        
        print(f"\nSynthesized Output:")
        print(f"Target Actuator: {synthesized_output.target_actuator_id}")
        print(f"Frequency: {synthesized_output.frequency_hz} Hz")
        print(f"Amplitude: {synthesized_output.amplitude}")
        print(f"Waveform Samples (first 5): {synthesized_output.waveform_pattern[:5]}")
        
    except HapticSynthesisError as e:
        print(f"Error in transmission pipeline: {e}")
    except Exception as e:
        print(f"System crash: {e}")
