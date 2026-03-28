"""
模块名称: auto_融合意图结构化_bu_104_p1_隐_ef00de
描述: 融合意图结构化（bu_104_P1）、隐性技能数字化（bu_104_P2）与触觉回溯（ho_104_O1）。
      本模块将模糊的自然语言指令转换为精确的机器人控制参数，并通过模拟触觉反馈实现闭环修正。

输入格式:
    - 自然语言指令 (str): 例如 "轻轻地打磨平面，稍微用点力"
    - 环境上下文 (dict): 包含 'surface_material', 'tool_type' 等信息

输出格式:
    - 控制参数包 (dict): 包含 'pressure_N', 'speed_mm_s', 'angle_deg' 等关键参数
    - 执行日志 (list): 记录决策过程和修正历史
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PhysicsParameters:
    """物理参数数据类，用于存储机器人的具体控制指标。"""
    pressure_newtons: float = 0.0
    speed_mm_per_sec: float = 10.0
    angle_degrees: float = 45.0
    rigidity: float = 0.5  # 0.0 (柔顺) 到 1.0 (刚性)


@dataclass
class TactileFeedback:
    """触觉反馈数据类，模拟传感器读数。"""
    actual_force: float
    vibration_level: float
    contact_area: float
    timestamp: float


class IntentStructuringError(Exception):
    """自定义异常：意图解析失败。"""
    pass


class ParameterOutOfBoundsError(Exception):
    """自定义异常：生成的参数超出物理边界。"""
    pass


def _extract_semantic_modifiers(instruction: str) -> Dict[str, float]:
    """
    辅助函数：从自然语言中提取语义修饰词并映射为数值权重。
    
    Args:
        instruction (str): 用户的自然语言指令。
        
    Returns:
        Dict[str, float]: 包含 'force_weight', 'speed_weight' 的字典。
        
    Example:
        >>> _extract_semantic_modifiers("轻轻打磨")
        {'force_weight': 0.3, 'speed_weight': 0.5}
    """
    logger.debug(f"正在解析指令语义: {instruction}")
    
    # 默认权重
    weights = {
        'force_weight': 0.5,  # 0.0 (极轻) - 1.0 (极重)
        'speed_weight': 0.5   # 0.0 (极慢) - 1.0 (极快)
    }
    
    # 简单的关键词匹配规则（实际AGI场景中会使用LLM或NLP模型）
    if "轻" in instruction or "小心" in instruction:
        weights['force_weight'] = 0.2
        weights['speed_weight'] = 0.3
    elif "用力" in instruction or "重" in instruction:
        weights['force_weight'] = 0.8
        weights['speed_weight'] = 0.6
        
    if "快" in instruction or "迅速" in instruction:
        weights['speed_weight'] = 0.9
    elif "慢" in instruction or "缓慢" in instruction:
        weights['speed_weight'] = 0.2
        
    logger.info(f"提取的语义权重: {weights}")
    return weights


def structure_intent_to_physics(
    instruction: str, 
    context: Optional[Dict] = None
) -> PhysicsParameters:
    """
    核心函数1 (bu_104_P1 & bu_104_P2): 将模糊意图转化为结构化物理参数。
    
    结合隐性技能数字化，将抽象指令映射到具体的物理范围。
    
    Args:
        instruction (str): 自然语言指令。
        context (Optional[Dict]): 环境上下文，如材质硬度。
        
    Returns:
        PhysicsParameters: 包含具体控制参数的对象。
        
    Raises:
        IntentStructuringError: 如果指令无法解析。
    """
    if not instruction:
        raise IntentStructuringError("指令不能为空")
    
    # 默认上下文
    if context is None:
        context = {'material_hardness': 0.5}  # 0-1 scale
    
    # 1. 提取语义特征 (bu_104_P1)
    semantic_weights = _extract_semantic_modifiers(instruction)
    
    # 2. 隐性技能数字化 (bu_104_P2)
    # 将 0.0-1.0 的权重映射到实际物理量。
    # 假设打磨操作的物理约束：压力 1N-20N，速度 5-50 mm/s
    
    mat_hardness = context.get('material_hardness', 0.5)
    
    # 压力计算：结合意图权重和材料硬度（硬材料需要更大力）
    base_pressure = 5.0 + (mat_hardness * 15.0)  # 基础范围 5N - 20N
    target_pressure = base_pressure * semantic_weights['force_weight']
    
    # 速度计算
    max_speed = 50.0
    min_speed = 5.0
    target_speed = min_speed + (max_speed - min_speed) * semantic_weights['speed_weight']
    
    # 角度计算 (默认垂直，根据 '轻/重' 微调倾斜角)
    target_angle = 45.0 - (semantic_weights['force_weight'] * 10.0) # 越重越垂直
    
    params = PhysicsParameters(
        pressure_newtons=round(target_pressure, 2),
        speed_mm_per_sec=round(target_speed, 2),
        angle_degrees=round(target_angle, 1),
        rigidity=0.8 if semantic_weights['force_weight'] > 0.7 else 0.4
    )
    
    logger.info(f"结构化参数生成完成: {params}")
    return params


def closed_loop_tactile_correction(
    target_params: PhysicsParameters,
    feedback_data: List[TactileFeedback]
) -> Tuple[PhysicsParameters, bool]:
    """
    核心函数2 (ho_104_O1): 基于触觉回溯的闭环修正。
    
    分析实时触觉数据，动态调整压力和速度，确保操作安全。
    
    Args:
        target_params (PhysicsParameters): 初始计划参数。
        feedback_data (List[TactileFeedback]): 最近的触觉传感器数据流。
        
    Returns:
        Tuple[PhysicsParameters, bool]: 
            - 修正后的参数。
            - 是否需要紧急停止的标志。
            
    Raises:
        ParameterOutOfBoundsError: 如果修正后的参数超出安全范围。
    """
    if not feedback_data:
        return target_params, False
    
    # 只分析最近的一帧数据 (实时性)
    latest_feedback = feedback_data[-1]
    
    # 计算误差
    force_error = target_params.pressure_newtons - latest_feedback.actual_force
    vibration = latest_feedback.vibration_level
    
    corrected_params = PhysicsParameters(
        pressure_newtons=target_params.pressure_newtons,
        speed_mm_per_sec=target_params.speed_mm_per_sec,
        angle_degrees=target_params.angle_degrees
    )
    
    emergency_stop = False
    
    # 触觉回溯逻辑 (ho_104_O1)
    # 1. 震动过大，可能打滑或接触不良 -> 降速，调整角度
    if vibration > 0.8:
        logger.warning(f"检测到高震动: {vibration}, 执行降速修正。")
        corrected_params.speed_mm_per_sec *= 0.7
        corrected_params.angle_degrees += 5.0
        
    # 2. 力反馈误差过大 -> 调整压力
    if abs(force_error) > 2.0:  # 误差超过 2N
        # 增加积分项式的修正
        corrected_params.pressure_newtons += (force_error * 0.5)
        logger.info(f"力控修正: 目标 {target_params.pressure_newtons}, 实际 {latest_feedback.actual_force}, 修正量 {force_error * 0.5}")
        
    # 3. 边界检查与安全
    if corrected_params.pressure_newtons > 30.0:
        logger.error("修正压力超过30N安全阈值，触发紧急停止。")
        corrected_params.pressure_newtons = 0.0
        emergency_stop = True
        raise ParameterOutOfBoundsError("计算压力超过安全上限")
        
    if corrected_params.speed_mm_per_sec < 1.0:
        logger.warning("速度过低，可能卡死，尝试轻微增加速度。")
        corrected_params.speed_mm_per_sec = 1.0
        
    return corrected_params, emergency_stop


# ============================================================
# 使用示例 / Usage Example
# ============================================================
if __name__ == "__main__":
    # 模拟AGI系统运行流程
    
    user_cmd = "轻轻地打磨这块木头，不要太快"
    env_context = {'material_hardness': 0.3} # 木头较软
    
    print(f"--- 接收指令: {user_cmd} ---")
    
    try:
        # Step 1: 意图结构化
        planned_params = structure_intent_to_physics(user_cmd, env_context)
        print(f"初始规划参数: P={planned_params.pressure_newtons}N, V={planned_params.speed_mm_per_sec}mm/s")
        
        # Step 2: 模拟触觉反馈 (假设传感器读到比预期更硬的节点)
        mock_sensor_data = [
            TactileFeedback(actual_force=3.5, vibration_level=0.2, contact_area=10.0, timestamp=0.1),
            TactileFeedback(actual_force=4.5, vibration_level=0.9, contact_area=12.0, timestamp=0.2) # 突然震动变大
        ]
        
        # Step 3: 闭环修正
        final_params, stop_flag = closed_loop_tactile_correction(planned_params, mock_sensor_data)
        
        print(f"修正后参数: P={final_params.pressure_newtons}N, V={final_params.speed_mm_per_sec}mm/s")
        print(f"紧急停止状态: {stop_flag}")
        
    except IntentStructuringError as e:
        logger.error(f"意图解析失败: {e}")
    except ParameterOutOfBoundsError as e:
        logger.critical(f"安全边界违规: {e}")
    except Exception as e:
        logger.exception("系统未知错误")