"""
Module: somatic_digitalizer.py

这是一个将人类隐性的、非结构化的肉身感知（如手感、听音、肌肉微调）转化为机器可读、可量化参数的系统工程。
该模块建立了'感官语义映射'，将人类模糊的自然语言描述与传感器捕获的精确物理量进行对齐。
通过对比'失败'与'成功'轨迹的微小差异，自动提取关键特征向量，完成从'主观经验'到'客观算法'的编译。

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SomaticDigitalizer")


class TrajectoryLabel(Enum):
    """轨迹标签枚举，用于区分成功与失败的样本"""
    SUCCESS = 1
    FAILURE = 0
    UNKNOWN = -1


@dataclass
class SensorySample:
    """
    单次感官样本数据结构。
    
    Attributes:
        timestamp (float): 时间戳 (秒)
        torque (float): 扭矩数值 (Nm)
        vibration_freq (float): 振动频率 (Hz)
        acoustic_db (float): 声学分贝 (dB)
        pressure (float): 压力数值 (Pa)
        label (TrajectoryLabel): 轨迹标签 (成功/失败)
        natural_language_desc (Optional[str]): 自然语言描述
    """
    timestamp: float
    torque: float
    vibration_freq: float
    acoustic_db: float
    pressure: float
    label: TrajectoryLabel = TrajectoryLabel.UNKNOWN
    natural_language_desc: Optional[str] = None

    def __post_init__(self):
        """数据验证与边界检查"""
        if self.timestamp < 0:
            raise ValueError("Timestamp cannot be negative.")
        if not (0 <= self.torque <= 100):  # 假设扭矩最大100Nm
            logger.warning(f"Torque value {self.torque} is out of typical range [0, 100].")
        if self.vibration_freq < 0:
            raise ValueError("Vibration frequency cannot be negative.")


@dataclass
class SemanticMapping:
    """
    语义映射结果，包含自然语言描述与物理参数的对应关系。
    """
    description: str
    feature_vector: np.ndarray
    confidence_score: float
    physical_ranges: Dict[str, Tuple[float, float]]


class SomaticDigitalizer:
    """
    核心类：负责将非结构化的肉身感知数据转化为可量化的参数空间。
    """

    def __init__(self, sensitivity_threshold: float = 0.05):
        """
        初始化数字化器。
        
        Args:
            sensitivity_threshold (float): 特征提取的敏感度阈值，用于过滤噪声。
        """
        self.sensitivity_threshold = sensitivity_threshold
        self._feature_buffer: List[SensorySample] = []
        logger.info("SomaticDigitalizer initialized with threshold %.4f", sensitivity_threshold)

    def ingest_trajectory(self, samples: List[SensorySample]) -> None:
        """
        采集并输入一组感官轨迹数据。
        
        Args:
            samples (List[SensorySample]): 包含时序感官数据的列表。
        
        Raises:
            ValueError: 如果输入数据为空或格式错误。
        """
        if not samples:
            raise ValueError("Input sample list cannot be empty.")
        
        try:
            self._feature_buffer.extend(samples)
            logger.info(f"Ingested {len(samples)} samples. Total buffer size: {len(self._feature_buffer)}")
        except Exception as e:
            logger.error(f"Failed to ingest trajectory: {str(e)}")
            raise

    def _extract_features(self, sample: SensorySample) -> np.ndarray:
        """
        [辅助函数] 从单个样本中提取特征向量。
        这是一个简化的特征工程示例，实际场景可能涉及FFT或小波变换。
        
        Args:
            sample (SensorySample): 输入的感官样本。
            
        Returns:
            np.ndarray: 归一化的特征向量。
        """
        # 简单的拼接与基础处理，实际工程中会包含频域分析
        # 归一化处理 (Mock logic for demonstration)
        norm_torque = sample.torque / 100.0
        norm_vib = sample.vibration_freq / 5000.0  # 假设最大频率
        norm_acoustic = sample.acoustic_db / 120.0 # 假设最大分贝
        norm_pressure = sample.pressure / 1000.0   # 假设最大压力
        
        features = np.array([norm_torque, norm_vib, norm_acoustic, norm_pressure])
        
        # 处理可能的NaN或Inf
        if not np.isfinite(features).all():
             return np.zeros(4)
             
        return features

    def compile_sensory_semantics(self, natural_language_desc: str) -> SemanticMapping:
        """
        核心函数1: 将模糊的自然语言描述与历史数据中的物理特征对齐。
        例如：将"稍微紧一点"映射到具体的扭矩区间。
        
        Args:
            natural_language_desc (str): 目标自然语言描述，如"稍微紧一点"、"声音沉闷"。
            
        Returns:
            SemanticMapping: 包含特征向量和置信度的映射对象。
        """
        logger.info(f"Compiling semantics for: '{natural_language_desc}'")
        
        # 筛选带有该描述的成功样本
        relevant_samples = [
            s for s in self._feature_buffer 
            if s.natural_language_desc == natural_language_desc and s.label == TrajectoryLabel.SUCCESS
        ]
        
        if not relevant_samples:
            logger.warning(f"No matching success samples found for description: {natural_language_desc}")
            return SemanticMapping(
                description=natural_language_desc,
                feature_vector=np.zeros(4),
                confidence_score=0.0,
                physical_ranges={}
            )
            
        # 提取特征矩阵
        feature_matrix = np.array([self._extract_features(s) for s in relevant_samples])
        
        # 计算特征中心点（均值）作为该语义的数字表征
        mean_feature_vector = np.mean(feature_matrix, axis=0)
        
        # 计算物理范围 (基于统计数据)
        torque_values = [s.torque for s in relevant_samples]
        physical_ranges = {
            "torque": (float(np.min(torque_values)), float(np.max(torque_values)))
        }
        
        # 计算置信度 (简化的基于样本量的计算)
        confidence = min(1.0, len(relevant_samples) / 100.0) 
        
        logger.info(f"Semantic compilation complete. Confidence: {confidence:.2f}")
        
        return SemanticMapping(
            description=natural_language_desc,
            feature_vector=mean_feature_vector,
            confidence_score=confidence,
            physical_ranges=physical_ranges
        )

    def differentiate_trajectory_outcomes(self) -> Dict[str, float]:
        """
        核心函数2: 对比'失败'与'成功'轨迹的微小差异，提取关键特征权重。
        用于找出哪些物理量对成功与否影响最大（例如：振动频率 vs 扭矩）。
        
        Returns:
            Dict[str, float]: 各个物理维度的区分度权重 (0.0-1.0)。
        """
        logger.info("Analyzing differential features between Success and Failure trajectories...")
        
        success_vectors = []
        failure_vectors = []
        
        for sample in self._feature_buffer:
            vec = self._extract_features(sample)
            if sample.label == TrajectoryLabel.SUCCESS:
                success_vectors.append(vec)
            elif sample.label == TrajectoryLabel.FAILURE:
                failure_vectors.append(vec)
                
        if not success_vectors or not failure_vectors:
            logger.warning("Insufficient data for differentiation (need both success and failure cases).")
            return {"torque_weight": 0.0, "vibration_weight": 0.0, "acoustic_weight": 0.0, "pressure_weight": 0.0}

        # 计算质心
        success_centroid = np.mean(success_vectors, axis=0)
        failure_centroid = np.mean(failure_vectors, axis=0)
        
        # 计算差异向量
        diff_vector = np.abs(success_centroid - failure_centroid)
        
        # 归一化差异向量作为权重
        total_diff = np.sum(diff_vector)
        if total_diff == 0:
            weights = np.zeros_like(diff_vector)
        else:
            weights = diff_vector / total_diff
            
        result = {
            "torque_weight": float(weights[0]),
            "vibration_weight": float(weights[1]),
            "acoustic_weight": float(weights[2]),
            "pressure_weight": float(weights[3])
        }
        
        logger.info(f"Differentiation complete. Key factor weights: {result}")
        return result

# ============================
# Usage Example
# ============================
if __name__ == "__main__":
    # 1. 初始化系统
    digitalizer = SomaticDigitalizer(sensitivity_threshold=0.01)
    
    # 2. 模拟生成数据
    # 模拟成功案例：扭矩较高，声音低沉 (成功拧紧螺丝的感觉)
    success_data = [
        SensorySample(
            timestamp=i*0.1, 
            torque=8.5 + np.random.normal(0, 0.2), 
            vibration_freq=200 + np.random.normal(0, 10),
            acoustic_db=60 + np.random.normal(0, 5),
            pressure=500,
            label=TrajectoryLabel.SUCCESS,
            natural_language_desc="拧紧到位的手感"
        ) for i in range(50)
    ]
    
    # 模拟失败案例：扭矩较低，振动异常 (螺丝滑丝或未对齐)
    failure_data = [
        SensorySample(
            timestamp=i*0.1, 
            torque=4.2 + np.random.normal(0, 0.2), 
            vibration_freq=800 + np.random.normal(0, 20), # 振动频率高
            acoustic_db=85 + np.random.normal(0, 5),       # 噪音大
            pressure=200,
            label=TrajectoryLabel.FAILURE,
            natural_language_desc="打滑的震动感"
        ) for i in range(50)
    ]
    
    # 3. 输入数据
    try:
        digitalizer.ingest_trajectory(success_data)
        digitalizer.ingest_trajectory(failure_data)
    except ValueError as e:
        print(f"Error: {e}")

    # 4. 编译感官语义：将"手感"转化为参数
    semantic_map = digitalizer.compile_sensory_semantics("拧紧到位的手感")
    print(f"\n[Result] Semantic Mapping for '拧紧到位的手感':")
    print(f"Feature Vector: {semantic_map.feature_vector}")
    print(f"Physical Torque Range: {semantic_map.physical_ranges.get('torque')}")
    
    # 5. 区分成功/失败的关键因子
    diff_weights = digitalizer.differentiate_trajectory_outcomes()
    print(f"\n[Result] Differentiation Weights:")
    print(f"Torque Importance: {diff_weights['torque_weight']:.4f}")
    print(f"Vibration Importance: {diff_weights['vibration_weight']:.4f}")