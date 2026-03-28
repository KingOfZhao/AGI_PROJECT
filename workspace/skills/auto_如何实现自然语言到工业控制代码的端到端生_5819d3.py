"""
模块名称: industrial_nl2code
功能描述: 将自然语言指令转换为可执行的工业控制代码片段。
作者: Senior Python Engineer (AGI System)
版本: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommandType(Enum):
    """定义支持的工业控制命令类型"""
    SET_VALUE = "SET"           # 设定绝对值
    INCREMENT = "INCREMENT"     # 增加数值
    DECREMENT = "DECREMENT"     # 减少数值
    STOP = "STOP"               # 停止操作
    UNKNOWN = "UNKNOWN"         # 未知指令

@dataclass
class ParsedIntent:
    """解析后的意图数据结构"""
    command: CommandType
    device: str
    value: Optional[float] = None
    unit: Optional[str] = None
    raw_text: str = ""

@dataclass
class ControlCode:
    """生成的控制代码数据结构"""
    code: str
    language: str = "iec-st" # IEC 61131-3 Structured Text
    explanation: str = ""
    safety_check: bool = True

class IndustrialNL2CodeConverter:
    """
    自然语言到工业控制代码的转换器类。
    
    负责将模糊的自然语言（如专家口述）转化为精确的可执行逻辑。
    
    使用示例:
    >>> converter = IndustrialNL2CodeConverter()
    >>> text = "稍微把进水阀调大一点"
    >>> result = converter.generate_control_code(text)
    >>> print(result.code)
    "VALVE_INLET := VALVE_INLET + 5.0;"
    """

    def __init__(self, default_increment_pct: float = 5.0):
        """
        初始化转换器。
        
        Args:
            default_increment_pct (float): 模糊增量指令的默认百分比步长。
        """
        self.default_increment = default_increment_pct
        self._device_map = {
            "阀门": "VALVE_CTRL",
            "泵": "PUMP_SPEED",
            "温度": "TEMP_SETPOINT",
            "压力": "PRESSURE_SETPOINT",
            "电机": "MOTOR_RPM"
        }
        logger.info("IndustrialNL2CodeConverter initialized with default step: %.2f", self.default_increment)

    def _preprocess_text(self, text: str) -> str:
        """
        辅助函数：文本预处理。
        清洗输入文本，去除多余空格和标点，统一小写（针对非专有名词部分）。
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # 去除首尾空格
        cleaned = text.strip()
        # 简单的分词标记保留，实际场景应使用NLP分词器
        logger.debug(f"Preprocessed text: '{cleaned}'")
        return cleaned

    def parse_intent(self, text: str) -> ParsedIntent:
        """
        核心函数1：自然语言理解与意图解析。
        从文本中提取操作对象、动作类型和数值。
        
        Args:
            text (str): 输入的自然语言指令。
            
        Returns:
            ParsedIntent: 解析出的结构化意图。
            
        Raises:
            ValueError: 如果无法识别有效的设备或动作。
        """
        processed_text = self._preprocess_text(text)
        intent = ParsedIntent(command=CommandType.UNKNOWN, device="UNKNOWN", raw_text=processed_text)

        # 1. 实体识别（基于规则的简单实现，AGI场景下应替换为NER模型）
        for keyword, device_id in self._device_map.items():
            if keyword in processed_text:
                intent.device = device_id
                break
        
        if intent.device == "UNKNOWN":
            logger.warning(f"Device not recognized in text: {processed_text}")
            # 尝试容错，假设是默认设备或者抛出异常
            raise ValueError("Unrecognized device in command")

        # 2. 意图识别与数值提取
        # 匹配具体数值，如 "增加到50%", "设定为100"
        value_match = re.search(r"(\d+(\.\d+)?)", processed_text)
        
        if "增加" in processed_text or "调大" in processed_text or "提高" in processed_text:
            intent.command = CommandType.INCREMENT
            if value_match:
                intent.value = float(value_match.group(1))
            else:
                # 如果没有指定数值，使用默认策略
                intent.value = self.default_increment
                logger.info(f"No specific value found for increment, using default: {self.default_increment}")

        elif "减少" in processed_text or "调小" in processed_text or "降低" in processed_text:
            intent.command = CommandType.DECREMENT
            if value_match:
                intent.value = float(value_match.group(1))
            else:
                intent.value = self.default_increment

        elif "设定" in processed_text or "调整到" in processed_text or "等于" in processed_text:
            intent.command = CommandType.SET_VALUE
            if value_match:
                intent.value = float(value_match.group(1))
            else:
                raise ValueError("Set command requires a specific target value")
        
        elif "停止" in processed_text or "关闭" in processed_text:
            intent.command = CommandType.STOP
            intent.value = 0.0

        else:
            logger.error(f"Unable to parse intent for: {processed_text}")
            intent.command = CommandType.UNKNOWN

        return intent

    def validate_constraints(self, intent: ParsedIntent) -> bool:
        """
        数据验证与边界检查。
        确保生成的指令在物理和逻辑允许的范围内。
        
        Args:
            intent (ParsedIntent): 解析后的意图。
            
        Returns:
            bool: 验证是否通过。
        """
        if intent.value is not None:
            # 假设所有控制量不能为负
            if intent.value < 0 and intent.command in [CommandType.SET_VALUE, CommandType.INCREMENT]:
                logger.warning(f"Negative value detected: {intent.value}, clamping or rejecting.")
                return False
            
            # 假设设定值不能超过100%（示例）
            if intent.command == CommandType.SET_VALUE and intent.value > 100:
                logger.error(f"Value {intent.value} exceeds safety limit of 100.")
                return False
        
        return True

    def generate_control_code(self, text: str) -> ControlCode:
        """
        核心函数2：代码生成与合成。
        将解析后的意图转换为符合IEC 61131-3标准的代码片段。
        
        Args:
            text (str): 输入的自然语言指令。
            
        Returns:
            ControlCode: 包含代码字符串、解释和安全状态的对象。
        """
        try:
            intent = self.parse_intent(text)
            
            if not self.validate_constraints(intent):
                return ControlCode(
                    code="// ERROR: Safety constraint violation",
                    explanation="指令违反了安全约束（如数值越界）。",
                    safety_check=False
                )

            code_line = ""
            explanation = ""

            if intent.command == CommandType.INCREMENT:
                # 生成增量代码
                code_line = f"{intent.device} := {intent.device} + {intent.value:.2f};"
                explanation = f"将 {intent.device} 增加 {intent.value}"
            
            elif intent.command == CommandType.DECREMENT:
                # 生成减量代码
                code_line = f"{intent.device} := {intent.device} - {intent.value:.2f};"
                explanation = f"将 {intent.device} 减少 {intent.value}"

            elif intent.command == CommandType.SET_VALUE:
                # 生成绝对值设定代码
                code_line = f"{intent.device} := {intent.value:.2f};"
                explanation = f"将 {intent.device} 设定为 {intent.value}"
            
            elif intent.command == CommandType.STOP:
                code_line = f"{intent.device} := 0.0;"
                explanation = f"停止/复位 {intent.device}"
            
            else:
                code_line = "// Unimplemented command"
                explanation = "无法生成代码：未知指令"

            logger.info(f"Generated code: {code_line}")
            return ControlCode(code=code_line, explanation=explanation)

        except Exception as e:
            logger.exception("Error during code generation")
            return ControlCode(
                code=f"// Exception: {str(e)}",
                explanation="处理过程中发生错误",
                safety_check=False
            )

# 模块级测试与演示
if __name__ == "__main__":
    # 模拟AGI系统调用该Skill
    converter = IndustrialNL2CodeConverter(default_increment_pct=5.0)
    
    test_inputs = [
        "稍微调大一点阀门",      # 模糊指令 -> 默认增量
        "把泵的转速设定为50",    # 精确设定
        "降低温度到20",          # 语义包含设定
        "压力太高了减少5",       # 精确减量
        "关闭电机"               # 停止指令
    ]

    print(f"{'Original Text':<20} | {'Generated Code':<40} | {'Explanation'}")
    print("-" * 80)
    
    for text in test_inputs:
        result = converter.generate_control_code(text)
        print(f"{text:<20} | {result.code:<40} | {result.explanation}")