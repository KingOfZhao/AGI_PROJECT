"""
高级技能模块: 微观动作的时序边界检测
名称: auto_微观动作的时序边界检测_手工艺往往是一个_8fb655
描述: 本模块专门用于处理连续手工艺视频流，通过分析运动特征、停顿及工具交互，
      自动识别并切分具有独立语义的原子技能片段（如粗磨、精磨、检查）。
Author: AGI System
Version: 1.0.0
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
logger = logging.getLogger("MicroActionSegmenter")


class ActionType(Enum):
    """定义手工艺中常见的微观动作类型枚举"""
    ROUGH_GRINDING = "rough_grinding"  # 粗磨
    FINE_GRINDING = "fine_grinding"    # 精磨
    INSPECTION = "inspection"          # 检查
    TOOL_CHANGE = "tool_change"        # 工具更换
    IDLE = "idle"                      # 停顿/无操作
    UNKNOWN = "unknown"                # 未知动作


@dataclass
class MotionFeature:
    """
    单帧或短时窗内的运动特征数据结构。
    
    Attributes:
        timestamp (float): 时间戳（秒）。
        velocity_magnitude (float): 手部/工具的运动速度标量。
        acceleration (float): 运动加速度。
        curvature (float): 运动轨迹曲率（用于识别精细操作）。
        stillness_score (float): 静止评分（0-1，越高越静止）。
    """
    timestamp: float
    velocity_magnitude: float
    acceleration: float
    curvature: float = 0.0
    stillness_score: float = 0.0


@dataclass
class AtomicSkillSegment:
    """
    切分后的原子技能片段数据结构。
    
    Attributes:
        start_time (float): 片段开始时间。
        end_time (float): 片段结束时间。
        label (ActionType): 动作分类标签。
        confidence (float): 分类的置信度。
        features_summary (dict): 该片段的统计特征摘要。
    """
    start_time: float
    end_time: float
    label: ActionType
    confidence: float
    features_summary: dict = field(default_factory=dict)


def _validate_input_data(data: List[MotionFeature]) -> None:
    """
    [辅助函数] 验证输入的运动特征数据是否有效。
    
    Args:
        data (List[MotionFeature]): 输入的特征数据列表。
        
    Raises:
        ValueError: 如果数据为空、时间戳未排序或包含非法数值。
    """
    if not data:
        raise ValueError("输入数据不能为空列表。")
    
    # 检查时间戳单调性
    timestamps = [f.timestamp for f in data]
    if timestamps != sorted(timestamps):
        raise ValueError("时间戳必须是非递减的。")
    
    # 检查数值合法性
    for i, item in enumerate(data):
        if item.velocity_magnitude < 0:
            raise ValueError(f"索引 {i} 处的速度不能为负数。")
        if not (0.0 <= item.stillness_score <= 1.0):
            raise ValueError(f"索引 {i} 处的静止评分必须在 0.0 到 1.0 之间。")
    
    logger.debug("输入数据验证通过。")


def _analyze_motion_dynamics(features: List[MotionFeature], 
                             window_size: int = 5) -> np.ndarray:
    """
    [核心函数 1] 分析运动动力学特征，计算平滑后的运动强度指标。
    
    使用滑动窗口平均来平滑噪声，并计算瞬时运动强度 (IMI)。
    IMI = weighted_velocity * (1 - stillness_score)
    
    Args:
        features (List[MotionFeature]): 原始运动特征列表。
        window_size (int): 平滑窗口大小。
        
    Returns:
        np.ndarray: 每个时间点的运动强度数组。
    """
    logger.info(f"开始分析运动动力学，窗口大小: {window_size}")
    
    velocities = np.array([f.velocity_magnitude for f in features])
    stillness = np.array([f.stillness_score for f in features])
    
    # 简单移动平均平滑
    kernel = np.ones(window_size) / window_size
    smoothed_vel = np.convolve(velocities, kernel, mode='same')
    
    # 计算综合运动强度
    # 逻辑：如果静止评分高，则运动强度显著降低
    motion_intensity = smoothed_vel * (1.0 - stillness)
    
    # 归一化处理 (Min-Max)
    min_val, max_val = np.min(motion_intensity), np.max(motion_intensity)
    if max_val - min_val > 1e-6:
        normalized_intensity = (motion_intensity - min_val) / (max_val - min_val)
    else:
        normalized_intensity = np.zeros_like(motion_intensity)
        
    logger.debug("运动强度计算完成。")
    return normalized_intensity


def detect_semantic_boundaries(features: List[MotionFeature], 
                               pause_threshold: float = 0.1,
                               min_action_duration: float = 1.0) -> List[AtomicSkillSegment]:
    """
    [核心函数 2] 检测微观动作的时序语义边界。
    
    算法逻辑：
    1. 计算运动强度。
    2. 识别低运动状态（停顿）。
    3. 通过停顿切分长序列。
    4. 根据切分后片段的平均速度和曲率分类动作。
    
    Args:
        features (List[MotionFeature]): 输入的运动特征序列。
        pause_threshold (float): 判定为停顿的运动强度阈值。
        min_action_duration (float): 有效原子动作的最短时长（秒）。
        
    Returns:
        List[AtomicSkillSegment]: 识别出的原子技能片段列表。
        
    Example:
        >>> data = [MotionFeature(0.0, 10, 0), MotionFeature(0.5, 0.1, 0, stillness_score=1.0), ...]
        >>> segments = detect_semantic_boundaries(data)
    """
    try:
        _validate_input_data(features)
        logger.info(f"开始处理 {len(features)} 个特征帧...")
        
        intensities = _analyze_motion_dynamics(features)
        
        # 识别停顿帧
        # 如果运动强度低于阈值，则认为是潜在的边界
        is_pause = intensities < pause_threshold
        
        segments = []
        start_idx = 0
        current_state = 'action' if not is_pause[0] else 'pause'
        
        # 状态机遍历寻找边界
        for i in range(1, len(features)):
            frame_time = features[i].timestamp
            prev_time = features[i-1].timestamp
            
            # 状态转换检测
            if current_state == 'action' and is_pause[i]:
                # Action -> Pause 转换，记录 Action 片段
                duration = features[i-1].timestamp - features[start_idx].timestamp
                if duration >= min_action_duration:
                    segment = _classify_segment(features, start_idx, i-1, intensities)
                    segments.append(segment)
                    logger.debug(f"检测到动作片段: {segment.label.value} [{segment.start_time:.2f}s - {segment.end_time:.2f}s]")
                
                current_state = 'pause'
                start_idx = i
                
            elif current_state == 'pause' and not is_pause[i]:
                # Pause -> Action 转换，开始新的 Action
                current_state = 'action'
                start_idx = i
        
        # 处理末尾残留的片段
        if current_state == 'action' and start_idx < len(features) - 1:
            segment = _classify_segment(features, start_idx, len(features)-1, intensities)
            segments.append(segment)
            
        logger.info(f"检测完成，共发现 {len(segments)} 个原子技能片段。")
        return segments

    except ValueError as ve:
        logger.error(f"数据验证失败: {ve}")
        raise
    except Exception as e:
        logger.critical(f"边界检测过程中发生未预期错误: {e}", exc_info=True)
        raise RuntimeError("边界检测算法失败。") from e


def _classify_segment(features: List[MotionFeature], 
                      start_idx: int, end_idx: int, 
                      intensities: np.ndarray) -> AtomicSkillSegment:
    """
    [辅助函数] 根据特征统计对片段进行分类。
    
    简单规则：
    - 曲率高 + 速度中 = 精磨/抛光
    - 速度高 + 曲率低 = 粗磨
    - 速度极低 (但仍高于阈值) = 检查/微调
    
    Args:
        features: 特征列表
        start_idx: 开始索引
        end_idx: 结束索引
        intensities: 强度数组
        
    Returns:
        AtomicSkillSegment
    """
    segment_features = features[start_idx:end_idx+1]
    avg_velocity = np.mean([f.velocity_magnitude for f in segment_features])
    avg_curvature = np.mean([f.curvature for f in segment_features])
    
    # 简单的启发式分类逻辑
    label = ActionType.UNKNOWN
    confidence = 0.5
    
    if avg_curvature > 0.6:
        label = ActionType.FINE_GRINDING
        confidence = 0.85
    elif avg_velocity > 15.0:  # 假设单位
        label = ActionType.ROUGH_GRINDING
        confidence = 0.90
    else:
        label = ActionType.INSPECTION
        confidence = 0.75
        
    return AtomicSkillSegment(
        start_time=features[start_idx].timestamp,
        end_time=features[end_idx].timestamp,
        label=label,
        confidence=confidence,
        features_summary={
            "avg_velocity": avg_velocity,
            "avg_curvature": avg_curvature
        }
    )

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 模拟生成一段手工艺数据：粗磨 -> 停顿 -> 精磨
    mock_data = []
    
    # 1. 粗磨阶段 (高速度，低曲率)
    for t in np.arange(0, 5, 0.1):
        mock_data.append(MotionFeature(t, velocity_magnitude=20.0, acceleration=0.5, curvature=0.1))
        
    # 2. 停顿阶段 (低速度，高静止分)
    for t in np.arange(5, 6, 0.1):
        mock_data.append(MotionFeature(t, velocity_magnitude=0.0, acceleration=0.0, curvature=0.0, stillness_score=1.0))
        
    # 3. 精磨阶段 (中速度，高曲率)
    for t in np.arange(6, 10, 0.1):
        mock_data.append(MotionFeature(t, velocity_magnitude=8.0, acceleration=0.2, curvature=0.8))
        
    # 4. 检查阶段 (极低速度，低曲率)
    for t in np.arange(10, 12, 0.1):
        mock_data.append(MotionFeature(t, velocity_magnitude=0.5, acceleration=0.01, curvature=0.1))

    print("-" * 50)
    print("开始运行边界检测示例...")
    
    try:
        result_segments = detect_semantic_boundaries(mock_data, pause_threshold=0.2)
        
        print(f"\n检测结果 ({len(result_segments)} 个片段):")
        for seg in result_segments:
            print(f"Time: {seg.start_time:.1f}s - {seg.end_time:.1f}s | "
                  f"Action: {seg.label.value:<15} | "
                  f"Conf: {seg.confidence:.2f}")
                  
    except Exception as e:
        print(f"示例运行出错: {e}")