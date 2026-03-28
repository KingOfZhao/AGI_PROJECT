"""
Module: auto_explore_multimodal_primitives.py
Description: 探索基于多模态传感器数据（力反馈、IMU）的动作原语提取技术。
             旨在构建类似"肌肉记忆"的数字化节点，用于AGI系统的底层运动控制。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SensorDataPacket(BaseModel):
    """
    单次传感器数据采样的数据结构。
    
    Attributes:
        timestamp (float): 时间戳 (秒)。
        force_x (float): X轴力反馈 (牛顿)。
        force_y (float): Y轴力反馈 (牛顿)。
        force_z (float): Z轴力反馈 (牛顿)。
        acc_x (float): X轴加速度 (m/s^2)。
        acc_y (float): Y轴加速度 (m/s^2)。
        acc_z (float): Z轴加速度 (m/s^2)。
        gyro_x (float): X轴角速度。
        gyro_y (float): Y轴角速度。
        gyro_z (float): Z轴角速度。
    """
    timestamp: float
    force_x: float = 0.0
    force_y: float = 0.0
    force_z: float = 0.0
    acc_x: float = 0.0
    acc_y: float = 0.0
    acc_z: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0

    @validator('timestamp')
    def check_timestamp(cls, v):
        if v < 0:
            raise ValueError("Timestamp cannot be negative")
        return v

class MotionPrimitiveType(Enum):
    """动作原语类型的枚举。"""
    IDLE = "idle"
    CONTACT = "contact"          # 接触瞬间
    SLIDE = "slide"              # 滑动/摩擦
    IMPACT = "impact"            # 冲击/碰撞
    STATIC_HOLD = "static_hold"  # 静态保持
    UNKNOWN = "unknown"

class MotionPrimitive(BaseModel):
    """
    提取出的动作原语（数字化肌肉记忆节点）。
    
    Attributes:
        primitive_type (MotionPrimitiveType): 原语类型。
        start_time (float): 开始时间。
        end_time (float): 结束时间。
        avg_force (float): 平均力大小。
        peak_force (float): 峰值力。
        trajectory_vector (List[float]): 运动轨迹特征向量。
        confidence (float): 识别置信度。
    """
    primitive_type: MotionPrimitiveType
    start_time: float
    end_time: float
    avg_force: float
    peak_force: float
    trajectory_vector: List[float] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

def _calculate_vector_magnitude(x: float, y: float, z: float) -> float:
    """
    辅助函数：计算三维向量的模长。
    
    Args:
        x, y, z: 向量分量。
        
    Returns:
        float: 向量模长。
    """
    return np.sqrt(x**2 + y**2 + z**2)

def preprocess_sensor_stream(data_stream: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
    """
    核心函数 1: 预处理多模态传感器数据流。
    
    将原始字典列表转换为结构化的numpy数组，进行滤波和数据清洗。
    
    Args:
        data_stream (List[Dict[str, Any]]): 原始传感器数据列表。
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: 
            - timestamps: 时间戳数组 (N,)
            - features: 特征矩阵 (N, 7)，列顺序为 [ForceMag, AccMag, GyroMag, Fx, Fy, Ax, Ay]
            
    Raises:
        ValueError: 如果数据流为空或格式不正确。
    """
    if not data_stream:
        logger.error("Input data stream is empty.")
        raise ValueError("Input data stream cannot be empty.")

    logger.info(f"Starting preprocessing for {len(data_stream)} data points.")
    
    validated_data = []
    try:
        for i, item in enumerate(data_stream):
            try:
                # 使用Pydantic进行数据验证
                packet = SensorDataPacket(**item)
                validated_data.append(packet)
            except ValidationError as e:
                logger.warning(f"Skipping invalid data point at index {i}: {e}")
                continue
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        raise

    if not validated_data:
        raise ValueError("No valid data points remaining after validation.")

    # 转换为numpy数组进行处理
    n = len(validated_data)
    timestamps = np.zeros(n)
    features = np.zeros((n, 7)) # ForceMag, AccMag, GyroMag, Fx, Fy, Ax, Ay
    
    for i, packet in enumerate(validated_data):
        timestamps[i] = packet.timestamp
        
        force_mag = _calculate_vector_magnitude(packet.force_x, packet.force_y, packet.force_z)
        acc_mag = _calculate_vector_magnitude(packet.acc_x, packet.acc_y, packet.acc_z)
        gyro_mag = _calculate_vector_magnitude(packet.gyro_x, packet.gyro_y, packet.gyro_z)
        
        features[i, 0] = force_mag
        features[i, 1] = acc_mag
        features[i, 2] = gyro_mag
        features[i, 3] = packet.force_x
        features[i, 4] = packet.force_y
        features[i, 5] = packet.acc_x
        features[i, 6] = packet.acc_y

    # 简单的移动平均滤波 (窗口大小=3) 以去噪
    # 边界处理：保持原样
    if n > 3:
        smoothed_features = np.copy(features)
        for col in range(features.shape[1]):
            smoothed_features[1:-1, col] = (features[:-2, col] + features[1:-1, col] + features[2:, col]) / 3.0
        features = smoothed_features

    logger.info("Preprocessing completed.")
    return timestamps, features

def extract_motion_primitive(
    timestamps: np.ndarray, 
    features: np.ndarray, 
    force_threshold: float = 5.0, 
    acc_impact_threshold: float = 15.0
) -> List[MotionPrimitive]:
    """
    核心函数 2: 从预处理后的数据中提取动作原语。
    
    分析力反馈和IMU特征，将连续数据流分割为有意义的动作单元。
    
    Args:
        timestamps (np.ndarray): 时间戳数组。
        features (np.ndarray): 预处理后的特征矩阵。
        force_threshold (float): 判断是否有力的阈值。
        acc_impact_threshold (float): 判断是否为冲击的加速度阈值。
        
    Returns:
        List[MotionPrimitive]: 检测到的动作原语列表。
        
    Note:
        输入特征矩阵列: [ForceMag, AccMag, GyroMag, Fx, Fy, Ax, Ay]
    """
    if timestamps.shape[0] != features.shape[0]:
        raise ValueError("Timestamps and features must have the same length.")
    
    primitives = []
    n = len(timestamps)
    i = 0
    
    logger.info("Starting motion primitive extraction...")
    
    while i < n:
        current_force = features[i, 0]
        current_acc = features[i, 1]
        
        # 1. 检测冲击 - 优先级最高
        if current_acc > acc_impact_threshold and current_force > force_threshold:
            start_idx = i
            # 寻找冲击结束 (加速度下降)
            while i < n and features[i, 1] > acc_impact_threshold * 0.5:
                i += 1
            
            end_idx = min(i, n - 1)
            segment = features[start_idx:end_idx+1, :]
            
            primitive = MotionPrimitive(
                primitive_type=MotionPrimitiveType.IMPACT,
                start_time=timestamps[start_idx],
                end_time=timestamps[end_idx],
                avg_force=float(np.mean(segment[:, 0])),
                peak_force=float(np.max(segment[:, 0])),
                trajectory_vector=segment.mean(axis=0).tolist(),
                confidence=0.9
            )
            primitives.append(primitive)
            continue

        # 2. 检测接触/操作
        if current_force > force_threshold:
            start_idx = i
            # 持续检测直到力消失
            while i < n and features[i, 0] > force_threshold * 0.8:
                i += 1
            
            end_idx = min(i, n - 1)
            segment = features[start_idx:end_idx+1, :]
            avg_gyro = np.mean(segment[:, 2])
            
            # 根据运动状态细分类型
            if avg_gyro > 0.5:
                p_type = MotionPrimitiveType.SLIDE
                conf = 0.85
            else:
                p_type = MotionPrimitiveType.CONTACT
                conf = 0.88
            
            primitive = MotionPrimitive(
                primitive_type=p_type,
                start_time=timestamps[start_idx],
                end_time=timestamps[end_idx],
                avg_force=float(np.mean(segment[:, 0])),
                peak_force=float(np.max(segment[:, 0])),
                trajectory_vector=segment.mean(axis=0).tolist(),
                confidence=conf
            )
            primitives.append(primitive)
            continue

        # 3. 空闲状态
        i += 1

    logger.info(f"Extraction complete. Found {len(primitives)} primitives.")
    return primitives

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 模拟生成一些多模态传感器数据
    mock_data = []
    
    # 1. 空闲阶段 (0-2s)
    for t in np.linspace(0, 2, 20):
        mock_data.append({
            "timestamp": t,
            "force_x": 0.1, "force_y": 0.1, "force_z": 0.1,
            "acc_x": 0.0, "acc_y": 9.8, "acc_z": 0.0,
            "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0
        })
        
    # 2. 接触/滑动阶段 (2-4s)
    for t in np.linspace(2, 4, 20):
        mock_data.append({
            "timestamp": t,
            "force_x": 5.5, "force_y": 2.0, "force_z": 8.0, # Force > Threshold
            "acc_x": 1.0, "acc_y": 10.0, "acc_z": 0.5,
            "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 1.2 # 旋转 > 0.5
        })
        
    # 3. 碰撞阶段 (瞬间)
    for t in np.linspace(4, 4.1, 5):
        mock_data.append({
            "timestamp": t,
            "force_x": 20.0, "force_y": 5.0, "force_z": 25.0,
            "acc_x": 15.0, "acc_y": 25.0, "acc_z": 10.0, # Acc > 15.0
            "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0
        })

    # 添加一个异常数据用于测试验证
    mock_data.append({"timestamp": -1.0, "force_x": 0}) 

    try:
        # 步骤 1: 预处理
        ts, feats = preprocess_sensor_stream(mock_data)
        print(f"Preprocessed shape: {feats.shape}")
        
        # 步骤 2: 提取原语
        detected_primitives = extract_motion_primitive(ts, feats)
        
        # 打印结果
        for p in detected_primitives:
            print(f"Detected: {p.primitive_type.value} | Start: {p.start_time:.2f}s | "
                  f"AvgForce: {p.avg_force:.2f}N | Conf: {p.confidence:.2f}")
                  
    except ValueError as e:
        print(f"Processing Error: {e}")