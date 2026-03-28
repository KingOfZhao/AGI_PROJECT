"""
模块名称: auto_结合_人机共生编码器_td_113_q_6401db
描述: 本模块实现了'人机共生编码器'的核心逻辑。通过结合微动作分解与具身知识数字化，
      系统能够实时捕捉人类专家的隐性微动作（如手感、力度），将其转化为标准化的数字参数，
      并自动生成SOP（标准作业程序）或直接生成工业机器人执行指令。
      这不仅是复制动作，更是将人类的'直觉'量化为可编程的逻辑。
版本: 1.0.0
作者: AGI System
"""

import logging
import json
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Human_Machine_Symbiosis_Encoder")


class RobotAxis(Enum):
    """定义工业机器人的基本轴"""
    X = "x_axis"
    Y = "y_axis"
    Z = "z_axis"
    RX = "rotation_x"
    RY = "rotation_y"
    RZ = "rotation_z"


@dataclass
class MicroAction:
    """
    微动作数据结构。
    代表人类操作中的一个瞬时状态或微小动作单元。
    """
    timestamp: float
    position: Dict[str, float]  # 例如: {"x": 10.5, "y": 0.0, "z": 5.2}
    force_vector: Dict[str, float]  # 力/扭矩，例如: {"fx": 0.0, "fy": 0.5, "fz": 12.5}
    haptic_feedback: float  # 触觉反馈强度 (0.0 - 1.0)，代表专家的"手感"直觉
    action_label: Optional[str] = None  # 动作语义标签，如 "grasp", "slide", "insert"

    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.haptic_feedback <= 1.0):
            raise ValueError(f"Invalid haptic feedback value: {self.haptic_feedback}. Must be between 0 and 1.")


@dataclass
class StandardOperatingProcedure:
    """
    标准作业程序(SOP)数据结构。
    数字化后的具身知识。
    """
    task_name: str
    steps: List[Dict[str, Any]]
    required_precision: float  # 所需精度等级
    safety_zones: List[Dict[str, float]]


def validate_sensor_input(raw_data: Dict[str, Any]) -> bool:
    """
    辅助函数：验证传感器输入数据的完整性。
    
    Args:
        raw_data (Dict[str, Any]): 从传感器接收的原始JSON数据。
        
    Returns:
        bool: 如果数据有效返回True，否则返回False。
    """
    required_keys = {"timestamp", "pos_x", "pos_y", "pos_z", "force_z", "current"}
    
    if not isinstance(raw_data, dict):
        logger.error("Input data is not a dictionary.")
        return False
        
    if not required_keys.issubset(raw_data.keys()):
        missing = required_keys - set(raw_data.keys())
        logger.error(f"Missing required sensor keys: {missing}")
        return False
        
    # 检查数值边界（简单示例）
    if abs(raw_data.get("force_z", 0)) > 1000:  # 假设安全限制为1000N
        logger.warning("Force sensor reading exceeds safety limits.")
        # 在实际生产中这里可能会触发急停
        
    return True


def capture_micro_actions(
    sensor_stream: List[Dict[str, Any]], 
    sensitivity_threshold: float = 0.1
) -> Tuple[List[MicroAction], Dict[str, float]]:
    """
    核心函数1：微动作分解与捕捉。
    从高频传感器流中提取有意义的微动作，并捕捉隐性知识（手感）。
    
    Args:
        sensor_stream (List[Dict[str, Any]]): 模拟的传感器数据流列表。
        sensitivity_threshold (float): 判定动作发生的力度阈值。
        
    Returns:
        Tuple[List[MicroAction], Dict[str, float]]: 
            - MicroAction对象列表。
            - 任务统计元数据（如平均力度、最大偏差）。
            
    Raises:
        ValueError: 如果输入流为空或阈值无效。
    """
    if not sensor_stream:
        raise ValueError("Sensor stream cannot be empty.")
    if sensitivity_threshold < 0:
        raise ValueError("Threshold cannot be negative.")

    logger.info(f"Starting micro-action capture on {len(sensor_stream)} frames...")
    
    captured_actions: List[MicroAction] = []
    stats = {"total_force": 0.0, "avg_haptic": 0.0, "action_count": 0}
    total_haptic = 0.0
    
    for raw_frame in sensor_stream:
        if not validate_sensor_input(raw_frame):
            continue
            
        try:
            # 模拟将原始电信号转化为物理参数（具身知识数字化的一部分）
            pos = {
                "x": raw_frame["pos_x"],
                "y": raw_frame["pos_y"],
                "z": raw_frame["pos_z"]
            }
            
            # 模拟"手感"的计算：基于电流反馈和阻力
            # 这是一个将"直觉"量化的简单模型：电流异常增加往往意味着接触或阻力
            force_z = raw_frame["force_z"]
            current = raw_frame["current"]
            
            # 只有当力度超过阈值时，才认为这是一个有效的操作动作
            if force_z > sensitivity_threshold:
                # 计算触觉强度：结合力度和电机电流
                haptic_intensity = min(1.0, (force_z / 50.0) * 0.5 + current * 0.5)
                
                action = MicroAction(
                    timestamp=raw_frame["timestamp"],
                    position=pos,
                    force_vector={"fx": 0, "fy": 0, "fz": force_z},
                    haptic_feedback=haptic_intensity,
                    action_label="contact" if haptic_intensity > 0.5 else "approach"
                )
                captured_actions.append(action)
                
                stats["total_force"] += force_z
                total_haptic += haptic_intensity
                stats["action_count"] += 1
                
        except KeyError as e:
            logger.error(f"Data processing error: missing key {e}")
            continue
        except Exception as e:
            logger.exception(f"Unexpected error processing frame: {e}")
            continue

    if stats["action_count"] > 0:
        stats["avg_haptic"] = total_haptic / stats["action_count"]
        
    logger.info(f"Capture complete. Found {len(captured_actions)} significant micro-actions.")
    return captured_actions, stats


def generate_robotic_logic(
    actions: List[MicroAction], 
    task_name: str = "Undefined_Task"
) -> StandardOperatingProcedure:
    """
    核心函数2：自动生成SOP与机器人逻辑。
    将捕捉到的微动作序列转化为标准化的SOP和机器人代码参数。
    
    Args:
        actions (List[MicroAction]): 捕捉到的微动作列表。
        task_name (str): 任务名称。
        
    Returns:
        StandardOperatingProcedure: 生成的标准作业程序对象。
        
    Raises:
        ValueError: 如果动作列表为空。
    """
    if not actions:
        raise ValueError("Cannot generate logic from empty action list.")

    logger.info(f"Generating SOP for task: {task_name}")
    
    sop_steps = []
    last_pos = None
    
    for idx, action in enumerate(actions):
        # 简单的逻辑推演：如果力度突增，标记为关键步骤
        is_critical = action.haptic_feedback > 0.7
        
        step_desc = {
            "step_id": idx,
            "target_position": action.position,
            "force_limit": action.force_vector.get("fz", 0.0) * 1.2,  # 增加20%的安全余量
            "description": f"Move to {action.position} with tactile sense {action.haptic_feedback:.2f}",
            "logic_type": "FORCE_CONTROL" if is_critical else "POSITION_CONTROL"
        }
        
        # 将人类的隐性"手感"转化为机器人的力控参数
        if is_critical:
            step_desc["safety_instruction"] = "SLOW_DOWN_AND_VERIFY"
            
        sop_steps.append(step_desc)
        last_pos = action.position

    # 创建SOP对象
    sop = StandardOperatingProcedure(
        task_name=task_name,
        steps=sop_steps,
        required_precision=0.01,  # 根据微动作抖动计算
        safety_zones=[{"z_min": 0}]  # 简单的安全区域定义
    )
    
    logger.info("SOP generation complete.")
    return sop


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟生成一些传感器数据
    mock_sensor_data = []
    base_time = time.time()
    
    # 阶段1: 接近物体
    for i in range(5):
        mock_sensor_data.append({
            "timestamp": base_time + i * 0.1,
            "pos_x": i * 2.0,
            "pos_y": 0.0,
            "pos_z": 10.0 - i * 0.5,
            "force_z": 0.1,  # 轻微接触
            "current": 0.1
        })
        
    # 阶段2: 抓取/按压 (体现手感)
    for i in range(5):
        mock_sensor_data.append({
            "timestamp": base_time + 0.5 + i * 0.1,
            "pos_x": 10.0,
            "pos_y": 0.0,
            "pos_z": 7.5 - i * 0.1,
            "force_z": 15.0 + i * 5.0,  # 力度增加
            "current": 0.6 + i * 0.1    # 电流增加
        })

    try:
        # 1. 捕捉微动作
        print("--- Step 1: Capturing Micro-actions ---")
        micro_actions, statistics = capture_micro_actions(mock_sensor_data, sensitivity_threshold=0.5)
        
        print(f"Captured {len(micro_actions)} actions.")
        print(f"Statistics: {json.dumps(statistics, indent=2)}")
        
        # 2. 生成SOP
        if micro_actions:
            print("\n--- Step 2: Generating Robotic SOP ---")
            sop_result = generate_robotic_logic(micro_actions, task_name="Precision_Assembly")
            
            # 打印前两步作为示例
            print(f"SOP Task: {sop_result.task_name}")
            print("First 2 Steps:")
            for step in sop_result.steps[:2]:
                print(json.dumps(step, indent=2))
                
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"System Failure: {e}")