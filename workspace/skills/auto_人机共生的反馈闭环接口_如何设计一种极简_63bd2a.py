"""
人机共生的反馈闭环接口：结构化干预协议

该模块实现了一种极简的“结构化干预协议”，允许人类在AI执行过程中注入纠偏信号。
AI系统能够实时解析这些自然语言信号，将其转化为参数修正，并动态更新执行状态，
而无需重新运行整个生成流程。

核心组件:
- InterventionProtocol: 协议类，负责解析和验证干预信号
- FeedbackClosedLoop: 闭环控制器，处理信号并更新执行上下文
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanAIFeedbackLoop")


@dataclass
class ExecutionState:
    """
    表示AI当前的执行状态。
    
    Attributes:
        task_id (str): 当前任务的唯一标识符
        parameters (Dict[str, Any]): 当前生成任务的参数集（如颜色、大小、风格等）
        history (List[Dict[str, Any]]): 历史修改记录
        status (str): 当前状态 ('running', 'paused', 'completed', 'error')
    """
    task_id: str
    parameters: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"

    def update_param(self, key: str, value: Any, reason: str = "N/A") -> None:
        """辅助方法：更新参数并记录历史"""
        old_value = self.parameters.get(key)
        self.parameters[key] = value
        self.history.append({
            "modified_key": key,
            "old_value": old_value,
            "new_value": value,
            "reason": reason
        })
        logger.info(f"参数更新: {key} 从 {old_value} 变更为 {value}")


class StructuredInterventionProtocol:
    """
    结构化干预协议解析器。
    
    将非结构化的自然语言反馈（如“颜色太冷，要暖一点”）解析为结构化的参数指令。
    这是一个极简实现，演示了如何将语义映射为参数。
    """

    # 定义语义到参数的映射规则
    # 在实际AGI场景中，这里会连接到NLU模型或LLM
    SEMANTIC_RULES = {
        r"暖(?:一点|些)|(?:更)?温暖": {"key": "temperature", "adjustment": "warmer"},
        r"冷(?:一点|些)|(?:更)?冷(?:色调)?": {"key": "temperature", "adjustment": "colder"},
        r"大(?:一点|些)|(?:更)?大": {"key": "scale", "adjustment": "increase"},
        r"小(?:一点|些)|(?:更)?小": {"key": "scale", "adjustment": "decrease"},
        r"快(?:一点|些)": {"key": "speed", "adjustment": "increase"},
        r"慢(?:一点|些)": {"key": "speed", "adjustment": "decrease"},
    }

    @staticmethod
    def parse_signal(raw_input: str) -> Optional[Dict[str, Any]]:
        """
        解析原始输入信号。
        
        Args:
            raw_input (str): 人类的自然语言输入
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的指令字典，包含 'target_param', 'action', 'raw_intent'
            
        Raises:
            ValueError: 如果输入为空或无法解析
        """
        if not raw_input or not isinstance(raw_input, str):
            raise ValueError("输入信号必须是非空字符串")

        cleaned_input = raw_input.strip().lower()
        logger.debug(f"正在解析信号: {cleaned_input}")

        for pattern, rule in StructuredInterventionProtocol.SEMANTIC_RULES.items():
            if re.search(pattern, cleaned_input):
                logger.info(f"匹配规则成功: 模式 '{pattern}' 匹配输入 '{cleaned_input}'")
                return {
                    "target_param": rule["key"],
                    "action": rule["adjustment"],
                    "raw_intent": raw_input
                }
        
        logger.warning(f"无法识别的干预信号: {raw_input}")
        return None


class FeedbackClosedLoop:
    """
    人机共生反馈闭环系统的核心接口。
    
    管理执行状态，接收干预信号，并实时应用修正。
    """

    def __init__(self, initial_state: ExecutionState):
        """
        初始化闭环控制器。
        
        Args:
            initial_state (ExecutionState): 初始执行状态对象
        """
        if not isinstance(initial_state, ExecutionState):
            raise TypeError("initial_state 必须是 ExecutionState 的实例")
        
        self.state = initial_state
        self.protocol = StructuredInterventionProtocol()
        logger.info(f"反馈闭环接口已初始化，任务ID: {self.state.task_id}")

    def _calculate_adjustment(self, key: str, action: str) -> Any:
        """
        辅助函数：根据动作类型计算新的参数值。
        
        这是一个简化的逻辑，实际应用中可能涉及复杂的向量运算或代码生成。
        
        Args:
            key (str): 参数键名
            action (str): 动作类型
            
        Returns:
            Any: 计算后的新参数值
        """
        current_value = self.state.parameters.get(key)
        
        # 简单的数值或枚举调整逻辑
        if key == "temperature":
            # 假设温度是 0-10000 的开尔文值或枚举
            val_map = {"cold": 3000, "neutral": 5000, "warm": 8000}
            if action == "warmer":
                return min(10000, (current_value or 5000) + 1000)
            elif action == "colder":
                return max(1000, (current_value or 5000) - 1000)
                
        elif key == "scale":
            # 假设 scale 是浮点数
            if action == "increase":
                return (current_value or 1.0) * 1.2
            elif action == "decrease":
                return (current_value or 1.0) * 0.8
                
        elif key == "speed":
            # 假设 speed 是浮点数
            if action == "increase":
                return (current_value or 1.0) * 1.5
            elif action == "decrease":
                return (current_value or 1.0) * 0.7

        return current_value

    def inject_intervention(self, human_signal: str) -> Tuple[bool, str]:
        """
        核心函数：注入人类干预信号并实时更新状态。
        
        这是接口的主入口，模拟“中断-修正-继续”的过程。
        
        Args:
            human_signal (str): 人类的自然语言干预指令
            
        Returns:
            Tuple[bool, str]: (是否成功, 状态消息)
        """
        if self.state.status == "completed":
            logger.error("任务已完成，无法接受干预")
            return False, "Task already completed"

        try:
            # 1. 解析信号
            parsed_intent = self.protocol.parse_signal(human_signal)
            
            if not parsed_intent:
                return False, "Unable to parse intervention signal"
            
            # 2. 数据验证与边界检查
            target_key = parsed_intent['target_param']
            if target_key not in self.state.parameters:
                # 动态扩展参数（可选），或者报错。这里选择报错以严格边界
                # 但为了演示柔性，我们允许初始化不存在的键
                logger.warning(f"参数 '{target_key}' 不在初始参数中，将动态创建。")
                self.state.parameters[target_key] = None

            # 3. 计算修正值
            new_value = self._calculate_adjustment(target_key, parsed_intent['action'])
            
            # 4. 应用修正
            self.state.update_param(target_key, new_value, parsed_intent['raw_intent'])
            
            # 5. 模拟代码/指令更新 (这里仅打印日志，实际可生成代码补丁)
            self._apply_patch_to_runtime(target_key, new_value)
            
            return True, f"Parameter '{target_key}' updated to {new_value}"

        except Exception as e:
            logger.error(f"处理干预信号时发生错误: {e}")
            return False, str(e)

    def _apply_patch_to_runtime(self, key: str, value: Any) -> None:
        """
        辅助函数：模拟将参数更新应用到运行时代码。
        
        在真实场景中，这可能涉及重写配置文件、更新渲染引擎参数或修改AST。
        """
        logger.info(f"--- [RUNTIME PATCH] Applying: ctx['{key}'] = {value} ---")
        # 这里没有重新运行整个流程，只是更新了上下文
        pass

    def finalize(self) -> Dict[str, Any]:
        """
        结束任务并返回最终结果。
        """
        self.state.status = "completed"
        logger.info("任务已完成。")
        return self.state.parameters


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 初始化执行状态
    initial_params = {
        "temperature": 5500,  # 初始色温
        "scale": 1.0,
        "style": "modern"
    }
    task_state = ExecutionState(task_id="gen_img_001", parameters=initial_params)
    
    # 2. 初始化反馈闭环接口
    loop_interface = FeedbackClosedLoop(task_state)
    
    print("初始状态:", loop_interface.state.parameters)
    
    # 3. 模拟人类干预 1: "这个颜色不对，要更暖一点"
    print("\n> 用户输入: '这个颜色不对，要更暖一点'")
    success, msg = loop_interface.inject_intervention("这个颜色不对，要更暖一点")
    print(f"系统响应: {success}, {msg}")
    print("当前状态:", loop_interface.state.parameters)

    # 4. 模拟人类干预 2: "太小了"
    print("\n> 用户输入: '太小了'")
    success, msg = loop_interface.inject_intervention("太小了")
    print(f"系统响应: {success}, {msg}")
    print("当前状态:", loop_interface.state.parameters)

    # 5. 模拟无效干预
    print("\n> 用户输入: '搞个蓝色的背景'")
    success, msg = loop_interface.inject_intervention("搞个蓝色的背景")
    print(f"系统响应: {success}, {msg}")