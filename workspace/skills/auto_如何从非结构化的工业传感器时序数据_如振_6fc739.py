"""
模块名称: industrial_feature_atomizer
描述: 该模块实现了从非结构化的工业传感器时序数据（如振动、温度、电流）中自动化提取
      具备物理意义的“特征原子”的功能。通过结合信号处理技术与符号化规则，将连续的
      模拟信号映射为离散的认知节点，为下游推理提供可解释的数据基础。
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from scipy import stats, fft

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FeatureAtom:
    """
    特征原子数据结构，表示一个离散化的认知节点。
    
    Attributes:
        name (str): 特征名称（如 'RMS', 'PeakFrequency'）
        value (float): 特征值
        symbol (str): 映射后的符号标签（如 'HIGH', 'STABLE', 'SINE'）
        timestamp (float): 时间戳
        confidence (float): 置信度 [0, 1]
    """
    name: str
    value: float
    symbol: str
    timestamp: float
    confidence: float

def validate_input_data(data: np.ndarray, fs: float) -> None:
    """
    辅助函数：验证输入数据的合法性。
    
    Args:
        data (np.ndarray): 输入时序数据
        fs (float): 采样频率
    
    Raises:
        ValueError: 如果数据或采样频率不合法
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("输入数据必须是numpy数组")
    if data.ndim != 1:
        raise ValueError("输入数据必须是一维数组")
    if len(data) < 10:
        raise ValueError("输入数据长度过短，至少需要10个采样点")
    if fs <= 0:
        raise ValueError("采样频率必须大于0")
    if np.any(np.isnan(data)):
        raise ValueError("输入数据包含NaN值")

def extract_physical_features(
    signal: np.ndarray, 
    fs: float,
    window_size: Optional[int] = None
) -> Dict[str, float]:
    """
    从时序数据中提取物理特征。
    
    Args:
        signal (np.ndarray): 一维时序信号数据
        fs (float): 采样频率
        window_size (Optional[int]): 加窗大小，默认为None（自动选择）
    
    Returns:
        Dict[str, float]: 包含物理特征的字典
    
    Example:
        >>> data = np.random.randn(1000)
        >>> features = extract_physical_features(data, 1000.0)
        >>> print(features.keys())
    """
    try:
        validate_input_data(signal, fs)
        
        # 自动选择窗大小
        if window_size is None:
            window_size = min(len(signal), int(fs * 0.5))  # 默认0.5秒窗口
        
        features = {}
        
        # 时域特征
        features['mean'] = np.mean(signal)
        features['std'] = np.std(signal)
        features['rms'] = np.sqrt(np.mean(signal**2))
        features['peak_to_peak'] = np.ptp(signal)
        features['skewness'] = stats.skew(signal)
        features['kurtosis'] = stats.kurtosis(signal)
        
        # 频域特征
        n = len(signal)
        yf = fft.fft(signal)
        xf = fft.fftfreq(n, 1/fs)
        
        # 只取正频率部分
        positive_freq_mask = xf > 0
        xf = xf[positive_freq_mask]
        yf = np.abs(yf[positive_freq_mask])
        
        if len(yf) > 0:
            features['dominant_freq'] = xf[np.argmax(yf)]
            features['spectral_centroid'] = np.sum(xf * yf) / np.sum(yf)
            features['spectral_flatness'] = np.exp(np.mean(np.log(yf + 1e-10))) / np.mean(yf)
        else:
            features['dominant_freq'] = 0.0
            features['spectral_centroid'] = 0.0
            features['spectral_flatness'] = 0.0
        
        logger.info(f"成功提取{len(features)}个物理特征")
        return features
    
    except Exception as e:
        logger.error(f"特征提取失败: {str(e)}")
        raise

def map_features_to_symbols(
    features: Dict[str, float],
    rules: Optional[Dict[str, Dict[str, Union[float, str]]]] = None
) -> List[FeatureAtom]:
    """
    将连续特征值映射为离散符号（特征原子）。
    
    Args:
        features (Dict[str, float]): 由extract_physical_features生成的特征字典
        rules (Optional[Dict]): 自定义映射规则，格式为:
            {
                'feature_name': {
                    'bins': [threshold1, threshold2, ...],
                    'labels': ['label1', 'label2', ...]
                }
            }
    
    Returns:
        List[FeatureAtom]: 特征原子列表
    
    Example:
        >>> features = {'rms': 5.2, 'dominant_freq': 50.0}
        >>> atoms = map_features_to_symbols(features)
        >>> print(atoms[0].symbol)
    """
    if not features:
        raise ValueError("特征字典不能为空")
    
    # 默认映射规则（可被自定义规则覆盖）
    default_rules = {
        'rms': {
            'bins': [1.0, 3.0, 6.0, 10.0],
            'labels': ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
        },
        'dominant_freq': {
            'bins': [10.0, 50.0, 100.0, 200.0],
            'labels': ['ULTRA_LOW', 'LOW_FREQ', 'MID_FREQ', 'HIGH_FREQ', 'ULTRA_HIGH']
        },
        'spectral_flatness': {
            'bins': [0.1, 0.3, 0.6, 0.9],
            'labels': ['TONAL', 'MIXED_TONAL', 'MIXED_NOISE', 'NOISE', 'PURE_NOISE']
        }
    }
    
    # 合并自定义规则
    final_rules = {**default_rules, **(rules or {})}
    
    atoms = []
    current_time = np.datetime64('now').astype(np.float64)
    
    for feature_name, value in features.items():
        if feature_name not in final_rules:
            logger.warning(f"没有为特征'{feature_name}'定义映射规则，跳过符号化")
            continue
            
        rule = final_rules[feature_name]
        bins = rule['bins']
        labels = rule['labels']
        
        if len(bins) + 1 != len(labels):
            raise ValueError(f"特征'{feature_name}'的bins和labels数量不匹配")
        
        # 边界检查
        if value < bins[0]:
            symbol = labels[0]
            confidence = 1.0 - (bins[0] - value) / bins[0]
        elif value > bins[-1]:
            symbol = labels[-1]
            confidence = 1.0 - (value - bins[-1]) / bins[-1]
        else:
            # 使用np.digitize进行分箱
            idx = np.digitize(value, bins)
            symbol = labels[idx]
            confidence = 1.0  # 在边界内，置信度最高
        
        confidence = max(0.0, min(1.0, confidence))  # 确保在[0,1]范围内
        
        atom = FeatureAtom(
            name=feature_name,
            value=value,
            symbol=symbol,
            timestamp=current_time,
            confidence=confidence
        )
        atoms.append(atom)
    
    logger.info(f"成功映射{len(atoms)}个特征原子")
    return atoms

def process_sensor_stream(
    signal: np.ndarray,
    fs: float,
    custom_rules: Optional[Dict] = None
) -> Tuple[Dict[str, float], List[FeatureAtom]]:
    """
    处理传感器数据流的完整流水线：特征提取 -> 符号映射。
    
    Args:
        signal (np.ndarray): 传感器时序数据
        fs (float): 采样频率
        custom_rules (Optional[Dict]): 自定义符号映射规则
    
    Returns:
        Tuple[Dict[str, float], List[FeatureAtom]]: 
            (原始特征字典, 特征原子列表)
    
    Example:
        >>> import numpy as np
        >>> # 生成模拟振动数据 (50Hz正弦波 + 噪声)
        >>> t = np.linspace(0, 1, 1000)
        >>> data = 2.5 * np.sin(2 * np.pi * 50 * t) + 0.5 * np.random.randn(1000)
        >>> features, atoms = process_sensor_stream(data, 1000.0)
        >>> for atom in atoms:
        ...     print(f"{atom.name}: {atom.value:.2f} -> {atom.symbol}")
    """
    logger.info("开始处理传感器数据流")
    
    # 1. 特征提取
    features = extract_physical_features(signal, fs)
    
    # 2. 符号映射
    atoms = map_features_to_symbols(features, custom_rules)
    
    logger.info(f"数据处理完成，生成{len(atoms)}个认知节点")
    return features, atoms

# 单元测试
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    t = np.linspace(0, 1, 1000)
    
    # 测试1: 正常振动信号 (50Hz正弦波 + 噪声)
    print("测试1: 正常振动信号")
    data1 = 2.5 * np.sin(2 * np.pi * 50 * t) + 0.5 * np.random.randn(1000)
    features1, atoms1 = process_sensor_stream(data1, 1000.0)
    
    # 测试2: 异常高频振动
    print("\n测试2: 异常高频振动")
    data2 = 5.0 * np.sin(2 * np.pi * 200 * t) + 1.0 * np.random.randn(1000)
    features2, atoms2 = process_sensor_stream(data2, 1000.0)
    
    # 测试3: 自定义规则
    print("\n测试3: 自定义规则")
    custom_rules = {
        'rms': {
            'bins': [1.0, 2.0, 3.0],
            'labels': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        }
    }
    features3, atoms3 = process_sensor_stream(data1, 1000.0, custom_rules)
    
    # 打印部分结果
    print("\n示例结果:")
    for atom in atoms1[:3]:
        print(f"{atom.name}: {atom.value:.2f} -> {atom.symbol} (置信度: {atom.confidence:.2f})")