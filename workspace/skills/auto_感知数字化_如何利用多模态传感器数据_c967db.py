"""
Module: auto_perception_digitization.py
Description: 【感知数字化】多模态传感器数据处理与专家经验数字化工具。
             本模块构建了一个特征提取管道，将非结构化的传感器波形（振动、电流、温度）
             映射为与专家描述（如'轻微抖动'、'过载嗡鸣'）对齐的结构化向量。
             旨在解决工业现场数据标注稀缺的问题，通过数据驱动方式保留老师傅的隐性知识。

Domain: Industrial IoT / Signal Processing
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from scipy import stats, signal
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名，提高代码可读性
SensorData = Dict[str, np.ndarray]  # e.g., {'vibration': array, 'temp': array}
FeatureVector = np.ndarray
FeatureDict = Dict[str, Union[float, int]]

class SensorDataValidationError(Exception):
    """自定义异常：传感器数据验证失败"""
    pass

def _validate_input_signals(raw_data: SensorData, min_length: int = 10) -> None:
    """
    [辅助函数] 验证输入的传感器数据格式和完整性。
    
    确保所有关键传感器通道存在，数据类型正确，且长度满足处理要求。
    
    Args:
        raw_data (SensorData): 包含传感器名称和对应时序数组的字典。
        min_length (int): 允许的最小数据点长度。
        
    Raises:
        SensorDataValidationError: 如果数据缺失、类型错误或长度不足。
        ValueError: 如果输入参数无效。
    """
    if not isinstance(raw_data, dict):
        raise SensorDataValidationError("输入数据必须是字典格式。")
    
    required_keys = ['vibration', 'temperature', 'current']
    for key in required_keys:
        if key not in raw_data:
            logger.warning(f"缺少关键传感器通道: {key}，可能会影响特征提取完整性。")
            continue # 允许缺失部分通道，但在日志中警告，实际工程中可能需要降级处理
        
        arr = raw_data[key]
        if not isinstance(arr, (np.ndarray, list)):
            raise SensorDataValidationError(f"通道 {key} 的数据必须是 np.ndarray 或 list。")
        
        if len(arr) < min_length:
            raise SensorDataValidationError(f"通道 {key} 的数据长度 ({len(arr)}) 小于最小要求 ({min_length})。")
        
        # 检查NaN或Inf
        if isinstance(arr, np.ndarray):
            if np.isnan(arr).any() or np.isinf(arr).any():
                logger.warning(f"通道 {key} 包含 NaN 或 Inf 值，将在后续处理中进行清洗。")

def extract_time_domain_features(signal_chunk: np.ndarray, label: str = '') -> FeatureDict:
    """
    [核心函数 1] 从单个信号片段中提取时域特征。
    
    模拟专家对信号“幅值”、“波动”和“趋势”的直观感受。
    
    Args:
        signal_chunk (np.ndarray): 一维时序信号数据。
        label (str): 可选的信号标签，用于日志记录。
        
    Returns:
        FeatureDict: 包含均值、标准差、峰峰值、偏度、峰度等统计特征的字典。
        
    Raises:
        ValueError: 如果输入信号维度不为1。
    """
    if signal_chunk.ndim != 1:
        logger.error(f"输入信号维度错误: {signal_chunk.ndim}, 期望为 1。")
        raise ValueError("输入信号必须是一维数组。")
    
    features = {}
    prefix = f"{label}_" if label else ""
    
    # 数据清洗：处理 NaN/Inf
    clean_signal = np.nan_to_num(signal_chunk, nan=0.0, posinf=0.0, neginf=0.0)
    
    try:
        # 基础统计量 - 反映信号“强度”和“稳定性”
        features[f"{prefix}mean"] = np.mean(clean_signal)
        features[f"{prefix}std"] = np.std(clean_signal)
        features[f"{prefix}max"] = np.max(clean_signal)
        features[f"{prefix}min"] = np.min(clean_signal)
        features[f"{prefix}ptp"] = np.ptp(clean_signal)  # 峰峰值，反映振动幅度
        
        # 形状统计量 - 反映“手感”或“异常冲击”
        # 偏度：衡量分布的不对称性
        features[f"{prefix}skew"] = stats.skew(clean_signal)
        # 峰度：衡量分布的平坦度，高锋度可能意味着冲击或尖锐噪声
        features[f"{prefix}kurtosis"] = stats.kurtosis(clean_signal)
        
        # 变异系数 - 反映相对于均值的波动程度
        if features[f"{prefix}mean"] != 0:
            features[f"{prefix}cv"] = features[f"{prefix}std"] / abs(features[f"{prefix}mean"])
        else:
            features[f"{prefix}cv"] = 0.0
            
    except Exception as e:
        logger.error(f"计算时域特征时发生错误: {e}")
        # 返回空特征或抛出异常，视业务容错性而定
        return {}

    return features

def extract_frequency_domain_features(
    signal_chunk: np.ndarray, 
    sample_rate: int = 1000, 
    label: str = ''
) -> FeatureDict:
    """
    [核心函数 2] 从信号中提取频域特征。
    
    模拟专家对“音调”、“嗡鸣声”或“特定频率异响”的听觉感知。
    
    Args:
        signal_chunk (np.ndarray): 一维时序信号数据。
        sample_rate (int): 采样频率。
        label (str): 可选的信号标签。
        
    Returns:
        FeatureDict: 包含主频、谱质心、谱熵等特征的字典。
    """
    features = {}
    prefix = f"{label}_" if label else ""
    
    # 数据清洗
    clean_signal = np.nan_to_num(signal_chunk, nan=0.0)
    n = len(clean_signal)
    
    if n < 2:
        return {f"{prefix}dominant_freq": 0, f"{prefix}spectral_centroid": 0}

    try:
        # FFT 计算
        yf = np.fft.rfft(clean_signal)
        xf = np.fft.rfftfreq(n, 1 / sample_rate)
        power_spectrum = np.abs(yf) ** 2
        
        # 归一化功率谱用于计算概率分布类的特征
        ps_norm = power_spectrum / (np.sum(power_spectrum) + 1e-9)
        
        # 主频 - 对应“音调”或“嗡鸣”的基础频率
        dominant_freq_idx = np.argmax(power_spectrum)
        features[f"{prefix}dominant_freq"] = xf[dominant_freq_idx]
        
        # 谱质心 - 声音“亮度”的指标，高频能量占比大则质心高
        features[f"{prefix}spectral_centroid"] = np.sum(xf * power_spectrum) / (np.sum(power_spectrum) + 1e-9)
        
        # 谱熵 - 衡量频谱分布的混乱程度，噪声通常熵高，单音信号熵低
        features[f"{prefix}spectral_entropy"] = stats.entropy(ps_norm + 1e-9)
        
        # 频带能量比 - 例如低频(0-100Hz) vs 高频，用于识别不同类型的故障
        low_band_mask = xf < 100
        high_band_mask = xf >= 100
        low_energy = np.sum(power_spectrum[low_band_mask])
        high_energy = np.sum(power_spectrum[high_band_mask])
        features[f"{prefix}energy_ratio"] = low_energy / (high_energy + 1e-9)

    except Exception as e:
        logger.error(f"计算频域特征时发生错误: {e}")
        return {}

    return features

def process_multimodal_sensor_pipeline(
    raw_data: SensorData, 
    sample_rates: Optional[Dict[str, int]] = None
) -> pd.DataFrame:
    """
    [管道函数] 整合多模态数据并进行特征数字化。
    
    将非结构化的传感器波形映射为结构化向量，对齐专家经验标签。
    输出格式适合直接输入机器学习模型进行训练（如时序分类任务）。
    
    Args:
        raw_data (SensorData): 字典，键为传感器名，值为 np.ndarray。
        sample_rates (Optional[Dict[str, int]]): 各传感器的采样率字典，默认均为 1000Hz。
        
    Returns:
        pd.DataFrame: 包含所有提取特征的单行 DataFrame。
        
    Example Input:
        raw_data = {
            'vibration': np.random.normal(0, 1, 1000),
            'temperature': np.random.normal(60, 5, 1000),
            'current': np.random.normal(5, 0.5, 1000)
        }
        
    Example Output:
        DataFrame with columns: ['vibration_mean', 'vibration_kurtosis', ..., 'current_dominant_freq', ...]
    """
    logger.info("开始执行多模态感知数字化管道...")
    
    # 1. 数据验证
    try:
        _validate_input_signals(raw_data)
    except SensorDataValidationError as e:
        logger.critical(f"输入数据验证失败: {e}")
        raise
    
    if sample_rates is None:
        sample_rates = {'vibration': 1000, 'temperature': 100, 'current': 1000}
        
    all_features = {}
    
    # 2. 遍历传感器通道提取特征
    for sensor_name, data_array in raw_data.items():
        if sensor_name not in sample_rates:
            logger.warning(f"未找到传感器 {sensor_name} 的采样率，使用默认值 1000Hz。")
            sr = 1000
        else:
            sr = sample_rates[sensor_name]
            
        # 转换为 numpy 数组
        arr = np.array(data_array)
        
        # 3. 特征提取
        # 时域特征（对应专家对幅度、抖动的感知）
        time_feats = extract_time_domain_features(arr, label=sensor_name)
        
        # 频域特征（对应专家对声音、嗡鸣的感知）
        # 注意：温度通常变化缓慢，频域意义较小，但为了一致性这里保留，实际中可选择性关闭
        freq_feats = extract_frequency_domain_features(arr, sample_rate=sr, label=sensor_name)
        
        # 合并特征
        channel_features = {**time_feats, **freq_feats}
        all_features.update(channel_features)
        
    logger.info(f"特征提取完成，共生成 {len(all_features)} 维特征向量。")
    
    # 4. 构建输出 DataFrame
    df_features = pd.DataFrame([all_features])
    
    # 5. 后处理：标准化或归一化通常在模型训练阶段进行，
    # 但此处可进行简单的异常值清洗（虽然特征提取中已做部分处理）
    # 将任何剩余的 inf 转换为 0
    df_features.replace([np.inf, -np.inf], 0, inplace=True)
    
    return df_features

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟工业现场采集的数据
    # 假设采样时长 1秒，振动和电流采样率 10kHz，温度采样率较低
    N_POINTS = 10000
    
    # 场景：设备轻微抖动
    # 振动：基频50Hz + 少量高频噪声
    t = np.linspace(0, 1, N_POINTS)
    vibration_signal = 0.5 * np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(N_POINTS)
    
    # 温度：缓慢上升
    temp_signal = 60 + 0.001 * t + 0.05 * np.random.randn(N_POINTS)
    
    # 电流：周期性波动（过载嗡鸣模拟）
    current_signal = 5.0 + 0.2 * np.sin(2 * np.pi * 100 * t) + 0.05 * np.random.randn(N_POINTS)
    
    # 构建输入数据包
    sensor_payload = {
        'vibration': vibration_signal,
        'temperature': temp_signal,
        'current': current_signal
    }
    
    sampling_info = {
        'vibration': 10000,
        'temperature': 10000, # 实际工程中可能更低，这里为了统一长度方便演示
        'current': 10000
    }
    
    try:
        # 运行管道
        feature_vector_df = process_multimodal_sensor_pipeline(sensor_payload, sampling_info)
        
        print("\n=== 生成的结构化特征向量 (前5列) ===")
        print(feature_vector_df.iloc[:, :5])
        print(f"\n特征总维度: {feature_vector_df.shape[1]}")
        
        # 展示特定特征，验证是否符合预期
        print(f"\n振动主频 (期望约50Hz): {feature_vector_df['vibration_dominant_freq'].values[0]:.2f} Hz")
        print(f"电流峰峰值: {feature_vector_df['current_ptp'].values[0]:.4f}")
        
        # 此时，feature_vector_df 可以与人工标签（如 "轻微抖动"）结合，
        # 用于训练分类器，从而将专家经验数字化。
        
    except Exception as e:
        logger.error(f"管道运行失败: {e}")