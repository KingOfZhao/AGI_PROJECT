"""
模块名称: auto_结合_不确定性盲区识别_td_23_q_60c93f
描述: 结合'不确定性盲区识别'、'多模态时序对齐'与'反馈时效性衰减'，
      构建主动认知耦合的AGI交互模式。
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MultiModalInput:
    """
    多模态输入数据结构
    Attributes:
        timestamp: 时间戳
        video_frame: 视频帧数据，0.0-1.0表示犹豫动作强度
        audio_tone: 音频数据，0.0-1.0表示语调异常程度
        operation_input: 操作输入，0.0-1.0表示操作复杂度
    """
    timestamp: float
    video_frame: float  # 犹豫动作强度
    audio_tone: float   # 语调异常程度
    operation_input: float  # 操作复杂度


@dataclass
class SystemState:
    """
    系统状态数据结构
    Attributes:
        confidence: 系统当前置信度
        execution_risk: 当前执行风险等级
    """
    confidence: float
    execution_risk: float


def validate_input_range(value: float, name: str) -> float:
    """
    辅助函数：验证输入值是否在0.0到1.0范围内
    
    Args:
        value: 需要验证的数值
        name: 数值名称，用于错误信息
        
    Returns:
        float: 验证后的数值
        
    Raises:
        ValueError: 当数值超出范围时抛出
    """
    if not 0.0 <= value <= 1.0:
        error_msg = f"{name} must be between 0.0 and 1.0, got {value}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value


def align_modalities(
    video_data: MultiModalInput,
    audio_data: MultiModalInput,
    operation_data: MultiModalInput,
    tolerance: float = 0.5
) -> Tuple[MultiModalInput, MultiModalInput, MultiModalInput]:
    """
    多模态时序对齐 - 确保视频、音频和操作数据的时间戳对齐
    
    Args:
        video_data: 视频模态数据
        audio_data: 音频模态数据
        operation_data: 操作模态数据
        tolerance: 时间戳允许的最大偏差(秒)
        
    Returns:
        Tuple[MultiModalInput, MultiModalInput, MultiModalInput]: 对齐后的三元组数据
        
    Raises:
        ValueError: 当数据验证失败或时间戳差异过大时抛出
    """
    # 验证输入数据
    for data in [video_data, audio_data, operation_data]:
        validate_input_range(data.video_frame, "video_frame")
        validate_input_range(data.audio_tone, "audio_tone")
        validate_input_range(data.operation_input, "operation_input")
    
    # 检查时间戳是否在容忍范围内
    timestamps = [video_data.timestamp, audio_data.timestamp, operation_data.timestamp]
    max_diff = max(timestamps) - min(timestamps)
    
    if max_diff > tolerance:
        error_msg = f"Timestamps are not aligned. Max difference: {max_diff}s"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Modalities aligned successfully with tolerance {tolerance}s")
    return video_data, audio_data, operation_data


def calculate_uncertainty_blindspot(
    system_state: SystemState,
    aligned_data: Tuple[MultiModalInput, MultiModalInput, MultiModalInput]
) -> float:
    """
    不确定性盲区识别 - 计算当前场景的不确定性盲区指数
    
    Args:
        system_state: 系统当前状态
        aligned_data: 对齐后的多模态数据
        
    Returns:
        float: 不确定性盲区指数(0.0-1.0)，值越高表示盲区越大
        
    Note:
        计算考虑了系统置信度、执行风险、人类犹豫动作、语调异常和操作复杂度
    """
    video_data, audio_data, operation_data = aligned_data
    
    # 验证系统状态
    validate_input_range(system_state.confidence, "confidence")
    validate_input_range(system_state.execution_risk, "execution_risk")
    
    # 计算不确定性盲区
    uncertainty = (
        (1.0 - system_state.confidence) * 0.4 +  # 低置信度贡献
        system_state.execution_risk * 0.3 +      # 执行风险贡献
        video_data.video_frame * 0.1 +           # 视频犹豫动作贡献
        audio_data.audio_tone * 0.1 +            # 音频语调异常贡献
        operation_data.operation_input * 0.1     # 操作复杂度贡献
    )
    
    # 确保结果在0-1范围内
    uncertainty = max(0.0, min(1.0, uncertainty))
    
    logger.debug(f"Calculated uncertainty blindspot: {uncertainty:.4f}")
    return uncertainty


def calculate_feedback_decay(
    initial_feedback_weight: float,
    elapsed_time: float,
    decay_rate: float = 0.05
) -> float:
    """
    反馈时效性衰减计算 - 根据时间衰减反馈权重
    
    Args:
        initial_feedback_weight: 初始反馈权重(0.0-1.0)
        elapsed_time: 经过的时间(秒)
        decay_rate: 衰减率，默认0.05
        
    Returns:
        float: 衰减后的反馈权重
        
    Raises:
        ValueError: 当输入参数无效时抛出
    """
    # 验证输入
    validate_input_range(initial_feedback_weight, "initial_feedback_weight")
    
    if elapsed_time < 0:
        error_msg = f"Elapsed time cannot be negative: {elapsed_time}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if decay_rate <= 0:
        error_msg = f"Decay rate must be positive: {decay_rate}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 指数衰减模型
    decayed_weight = initial_feedback_weight * (1 - decay_rate) ** elapsed_time
    
    # 确保结果在0-1范围内
    decayed_weight = max(0.0, min(1.0, decayed_weight))
    
    logger.debug(
        f"Feedback decay: {initial_feedback_weight:.4f} -> {decayed_weight:.4f} "
        f"(elapsed: {elapsed_time}s, rate: {decay_rate})"
    )
    return decayed_weight


def decide_human_intervention(
    uncertainty_index: float,
    feedback_weight: float,
    intervention_threshold: float = 0.7
) -> bool:
    """
    核心函数：决定是否需要人类专家介入
    
    Args:
        uncertainty_index: 不确定性盲区指数
        feedback_weight: 当前反馈权重
        intervention_threshold: 介入阈值，默认0.7
        
    Returns:
        bool: True表示需要人类介入，False表示不需要
        
    Raises:
        ValueError: 当输入参数无效时抛出
    """
    # 验证输入
    validate_input_range(uncertainty_index, "uncertainty_index")
    validate_input_range(feedback_weight, "feedback_weight")
    validate_input_range(intervention_threshold, "intervention_threshold")
    
    # 计算综合介入指数
    intervention_index = uncertainty_index * feedback_weight
    
    # 决策
    needs_intervention = intervention_index >= intervention_threshold
    
    if needs_intervention:
        logger.warning(
            f"Human intervention needed! Intervention index: {intervention_index:.4f} "
            f"(threshold: {intervention_threshold})"
        )
    else:
        logger.info(
            f"System autonomous operation continues. Intervention index: {intervention_index:.4f} "
            f"(threshold: {intervention_threshold})"
        )
    
    return needs_intervention


def execute_cognitive_coupling(
    video_data: MultiModalInput,
    audio_data: MultiModalInput,
    operation_data: MultiModalInput,
    system_state: SystemState,
    initial_feedback_weight: float = 1.0,
    intervention_threshold: float = 0.7
) -> bool:
    """
    执行主动认知耦合交互
    
    Args:
        video_data: 视频模态数据
        audio_data: 音频模态数据
        operation_data: 操作模态数据
        system_state: 系统当前状态
        initial_feedback_weight: 初始反馈权重，默认1.0
        intervention_threshold: 介入阈值，默认0.7
        
    Returns:
        bool: True表示请求人类介入，False表示系统自主执行
        
    Example:
        >>> video = MultiModalInput(time.time(), 0.2, 0.1, 0.3)
        >>> audio = MultiModalInput(time.time(), 0.2, 0.1, 0.3)
        >>> operation = MultiModalInput(time.time(), 0.2, 0.1, 0.3)
        >>> state = SystemState(0.6, 0.4)
        >>> execute_cognitive_coupling(video, audio, operation, state)
        True  # 可能需要人类介入
    """
    try:
        logger.info("Starting cognitive coupling process...")
        
        # 1. 多模态时序对齐
        aligned_data = align_modalities(video_data, audio_data, operation_data)
        
        # 2. 不确定性盲区识别
        uncertainty = calculate_uncertainty_blindspot(system_state, aligned_data)
        
        # 3. 反馈时效性衰减
        elapsed_time = time.time() - video_data.timestamp
        feedback_weight = calculate_feedback_decay(initial_feedback_weight, elapsed_time)
        
        # 4. 决定是否需要人类介入
        needs_intervention = decide_human_intervention(
            uncertainty, feedback_weight, intervention_threshold
        )
        
        return needs_intervention
        
    except Exception as e:
        logger.error(f"Error in cognitive coupling process: {str(e)}")
        # 在出错情况下，为了安全起见请求人类介入
        return True


# 使用示例
if __name__ == "__main__":
    # 模拟输入数据
    current_time = time.time()
    
    # 视频数据：检测到中等程度的犹豫动作(0.3)
    video_input = MultiModalInput(
        timestamp=current_time,
        video_frame=0.3,
        audio_tone=0.1,  # 这个字段在视频数据中不重要
        operation_input=0.1  # 这个字段在视频数据中不重要
    )
    
    # 音频数据：检测到轻微语调异常(0.2)
    audio_input = MultiModalInput(
        timestamp=current_time,
        video_frame=0.1,  # 这个字段在音频数据中不重要
        audio_tone=0.2,
        operation_input=0.1  # 这个字段在音频数据中不重要
    )
    
    # 操作数据：检测到中等操作复杂度(0.4)
    operation_input = MultiModalInput(
        timestamp=current_time,
        video_frame=0.1,  # 这个字段在操作数据中不重要
        audio_tone=0.1,  # 这个字段在操作数据中不重要
        operation_input=0.4
    )
    
    # 系统状态：置信度中等(0.6)，风险中等(0.3)
    system_state = SystemState(confidence=0.6, execution_risk=0.3)
    
    # 执行认知耦合
    needs_intervention = execute_cognitive_coupling(
        video_data=video_input,
        audio_data=audio_input,
        operation_data=operation_input,
        system_state=system_state,
        initial_feedback_weight=1.0,
        intervention_threshold=0.7
    )
    
    if needs_intervention:
        print("请求人类专家介入！")
    else:
        print("系统自主执行操作。")