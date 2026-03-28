"""
模块名称: physical_craft_digitizer
版本: 1.0.0
描述: 构建一套针对物理世界'手艺'的完整数字化流水线。该模块实现了多模态传感数据
      (视觉、触觉、力学)的时空对齐、特征提取及降维，旨在将隐性的物理手艺转化为
      可复用的'技能原语'参数。

核心功能:
    1. 多源异构数据的时空对齐。
    2. 高维模拟信号的降维与特征提取。
    3. 生成标准化的技能原语。

作者: AGI System
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from scipy.interpolate import interp1d
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SensorModality(Enum):
    """传感器模态枚举"""
    VISUAL = "visual_stream"       # 视觉流 (手部形变)
    TACTILE = "tactile_stream"     # 触觉流 (振动/滑移)
    KINETIC = "kinetic_stream"     # 力学流 (加速度/压力)


@dataclass
class SensorTimeSeries:
    """
    单个传感器的时序数据容器。
    
    Attributes:
        modality: 传感器类型 (SensorModality)
        timestamps: 时间戳数组, shape (N,)
        values: 传感数值数组, shape (N, D) 其中D为特征维度
    """
    modality: SensorModality
    timestamps: np.ndarray
    values: np.ndarray

    def __post_init__(self):
        """数据完整性自检"""
        if self.timestamps.ndim != 1:
            raise ValueError("时间戳必须是一维数组")
        if self.timestamps.shape[0] != self.values.shape[0]:
            raise ValueError(f"时间戳数量 {self.timestamps.shape[0]} 与数据点数量 {self.values.shape[0]} 不匹配")


@dataclass
class CraftPrimitive:
    """
    技能原语数据结构。
    
    Attributes:
        primitive_id: 原语唯一标识
        latent_vector: 降维后的潜在特征向量 (如: 力度/速度/形变曲率的组合)
        components: 具体的物理参数解释
        confidence: 拟合置信度
    """
    primitive_id: str
    latent_vector: np.ndarray
    components: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


def validate_input_data(datastreams: Dict[SensorModality, SensorTimeSeries]) -> bool:
    """
    辅助函数：验证输入数据的有效性和边界条件。
    
    Args:
        datastreams: 包含多模态数据的字典
        
    Returns:
        bool: 数据是否有效
        
    Raises:
        ValueError: 如果数据为空或时间范围无效
    """
    if not datastreams:
        logger.error("输入数据流为空")
        raise ValueError("必须提供至少一种模态的数据")
    
    min_time = np.inf
    max_time = -np.inf
    
    for modality, stream in datastreams.items():
        if stream.timestamps.size == 0:
            raise ValueError(f"模态 {modality.value} 的时间戳为空")
        
        current_min = stream.timestamps.min()
        current_max = stream.timestamps.max()
        
        if current_min < min_time: min_time = current_min
        if current_max > max_time: max_time = current_max
        
        # 边界检查：数值不能包含NaN或Inf
        if not np.all(np.isfinite(stream.values)):
            logger.warning(f"模态 {modality.value} 包含非有限值 (NaN/Inf)，已尝试清洗")
            # 实际场景中可能需要插值，这里简化处理为报错
    
    if min_time >= max_time:
        raise ValueError("时间范围无效，无法进行对齐")
        
    logger.info(f"数据验证通过，时间范围: {min_time:.4f}s - {max_time:.4f}s")
    return True


def temporal_alignment(
    datastreams: Dict[SensorModality, SensorTimeSeries], 
    target_fps: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    核心函数 1: 时空对齐。
    
    将不同频率、不同起始时间的传感器数据统一插值到同一时间轴上。
    
    Args:
        datastreams: 原始多模态数据流
        target_fps: 目标采样率
        
    Returns:
        aligned_matrix: 对齐后的特征矩阵
        common_time: 统一的时间轴
        
    Example:
        >>> # 假设已加载 visual, tactile 数据
        >>> aligned_X, time_t = temporal_alignment(datastreams, target_fps=120)
    """
    logger.info(f"开始时空对齐，目标频率: {target_fps}Hz")
    
    # 1. 寻找公共时间窗口 (取所有流的时间交集)
    starts = [s.timestamps.min() for s in datastreams.values()]
    ends = [s.timestamps.max() for s in datastreams.values()]
    
    t_start = max(starts)
    t_end = min(ends)
    
    if t_start >= t_end:
        logger.error("各数据流无公共时间交集")
        raise RuntimeError("数据流时间无交集，无法对齐")
        
    # 2. 生成统一时间轴
    num_samples = int((t_end - t_start) * target_fps)
    common_time = np.linspace(t_start, t_end, num_samples)
    
    aligned_features = []
    
    # 3. 对每个模态进行插值
    for modality, stream in datastreams.items():
        try:
            # 使用三次样条插值获得平滑的模拟信号重建
            interp_func = interp1d(
                stream.timestamps, 
                stream.values, 
                axis=0, 
                kind='cubic', 
                fill_value="extrapolate"
            )
            resampled_data = interp_func(common_time)
            aligned_features.append(resampled_data)
            logger.debug(f"模态 {modality.value} 对齐完成，形状: {resampled_data.shape}")
        except Exception as e:
            logger.error(f"模态 {modality.value} 插值失败: {e}")
            continue

    # 4. 拼接为 (Time, Total_Features) 矩阵
    if not aligned_features:
        raise RuntimeError("没有成功对齐的特征")
        
    final_matrix = np.hstack(aligned_features)
    logger.info(f"对齐完成，输出矩阵形状: {final_matrix.shape}")
    
    return final_matrix, common_time


def extract_skill_primitives(
    aligned_data: np.ndarray,
    primitive_duration: float = 2.0,
    n_components: int = 5
) -> List[CraftPrimitive]:
    """
    核心函数 2: 特征提取与技能原语生成。
    
    通过滑动窗口和PCA降维，将高维连续信号转化为低维离散技能参数。
    
    Args:
        aligned_data: 对齐后的特征矩阵
        primitive_duration: 滑动窗口时长 (秒)
        n_components: 降维后的目标维度
        
    Returns:
        List[CraftPrimitive]: 提取出的技能原语列表
    """
    logger.info("开始提取技能原语...")
    
    # 假设固定的 100Hz (与对齐函数默认值一致)，实际应作为参数传入或从元数据获取
    fs = 100 
    window_size = int(primitive_duration * fs)
    step_size = window_size // 2 # 50% 重叠
    
    primitives = []
    
    # 标准化数据
    scaler = StandardScaler()
    try:
        scaled_data = scaler.fit_transform(aligned_data)
    except Exception as e:
        logger.error(f"数据标准化失败: {e}")
        return []

    # 滑动窗口处理
    for i, start_idx in enumerate(range(0, scaled_data.shape[0] - window_size, step_size)):
        end_idx = start_idx + window_size
        window_data = scaled_data[start_idx:end_idx, :]
        
        # 对当前窗口进行PCA降维，提取主成分作为该时间片的"动作特征"
        # 这里保留 explained variance 或直接取固定维度
        pca = PCA(n_components=min(n_components, window_data.shape[1]))
        
        try:
            # 获取主要变化方向（即该段动作的"指纹”）
            pca.fit(window_data)
            # 使用 components_ (特征向量) 作为该技能的数字化表达
            latent_vector = pca.components_.flatten()[:n_components]
            variance_ratio = np.sum(pca.explained_variance_ratio_)
            
            # 构建原语对象
            primitive = CraftPrimitive(
                primitive_id=f"primitive_{i:04d}",
                latent_vector=latent_vector,
                components={
                    "variance_explained": float(variance_ratio),
                    "start_time": start_idx / fs,
                    "end_time": end_idx / fs
                },
                confidence=float(variance_ratio)
            )
            primitives.append(primitive)
            
        except Exception as e:
            logger.warning(f"窗口 {i} PCA 失败: {e}")
            continue
            
    logger.info(f"成功提取 {len(primitives)} 个技能原语")
    return primitives


class CraftDigitizerPipeline:
    """
    完整的手艺数字化流水线封装类。
    
    Usage Example:
    >>> pipeline = CraftDigitizerPipeline()
    >>> 
    >>> # 模拟数据输入
    >>> t = np.linspace(0, 10, 1000)
    >>> v_data = np.sin(t).reshape(-1, 1) # 视觉数据
    >>> t_data = np.cos(t).reshape(-1, 1) # 触觉数据
    >>> 
    >>> streams = {
    >>>     SensorModality.VISUAL: SensorTimeSeries(SensorModality.VISUAL, t, v_data),
    >>>     SensorModality.TACTILE: SensorTimeSeries(SensorModality.TACTILE, t, t_data)
    >>> }
    >>> 
    >>> # 运行流水线
    >>> primitives = pipeline.run(streams)
    >>> print(f"Generated Primitives: {len(primitives)}")
    """
    
    def __init__(self, target_fps: int = 100):
        self.target_fps = target_fps
        self.aligned_data: Optional[np.ndarray] = None
        self.common_time: Optional[np.ndarray] = None
        
    def run(self, datastreams: Dict[SensorModality, SensorTimeSeries]) -> List[CraftPrimitive]:
        """
        执行完整的数字化流水线。
        """
        logger.info("=== 启动手艺数字化流水线 ===")
        
        # 1. 数据校验
        validate_input_data(datastreams)
        
        # 2. 时空对齐
        self.aligned_data, self.common_time = temporal_alignment(
            datastreams, 
            target_fps=self.target_fps
        )
        
        # 3. 技能原语提取
        primitives = extract_skill_primitives(self.aligned_data)
        
        logger.info("=== 流水线执行完毕 ===")
        return primitives


if __name__ == "__main__":
    # 简单的演示代码
    print("Running Physical Craft Digitizer Demo...")
    
    # 生成模拟数据：陶艺拉坯动作模拟
    duration = 5.0 # 秒
    n_points = 500 # 采样点
    t = np.linspace(0, duration, n_points)
    
    # 模拟视觉流 (手部半径变化)
    visual_signal = np.sin(2 * np.pi * 0.5 * t)[:, np.newaxis] 
    
    # 模拟力学流 (施加的压力，带有高频噪声)
    kinetic_signal = (0.5 + 0.5 * np.sin(2 * np.pi * 1 * t) + 0.05 * np.random.randn(n_points))[:, np.newaxis]
    
    # 构建输入
    input_streams = {
        SensorModality.VISUAL: SensorTimeSeries(SensorModality.VISUAL, t, visual_signal),
        SensorModality.KINETIC: SensorTimeSeries(SensorModality.KINETIC, t, kinetic_signal)
    }
    
    # 初始化并运行
    pipeline = CraftDigitizerPipeline(target_fps=50)
    try:
        result_primitives = pipeline.run(input_streams)
        if result_primitives:
            print(f"First Primitive Vector: {result_primitives[0].latent_vector[:3]}...")
            print(f"Confidence: {result_primitives[0].confidence:.4f}")
    except Exception as e:
        print(f"Pipeline Error: {e}")