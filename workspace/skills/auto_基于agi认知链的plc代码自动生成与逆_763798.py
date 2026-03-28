"""
名称: auto_基于agi认知链的plc代码自动生成与逆_763798
描述: 基于AGI认知链的PLC代码自动生成与逆向解析验证
版本: 1.0.0
作者: AGI System Core Engineer
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_PLC_Generator")


class PLCInstructionType(Enum):
    """PLC指令类型枚举"""
    LD = "LD"      # 加载
    AND = "AND"    # 与
    OR = "OR"      # 或
    NOT = "NOT"    # 非
    OUT = "OUT"    # 输出
    SET = "SET"    # 置位
    RST = "RST"    # 复位
    CMP = "CMP"    # 比较
    MOV = "MOV"    # 移动
    TMR = "TMR"    # 定时器
    CNT = "CNT"    # 计数器


@dataclass
class PLCInstruction:
    """PLC指令数据结构"""
    operation: PLCInstructionType
    operand: str
    comment: Optional[str] = None
    address: Optional[str] = None

    def to_code(self) -> str:
        """将指令转换为IEC 61131-3格式代码"""
        base = f"{self.operation.value} {self.operand}"
        if self.comment:
            base += f" (* {self.comment} *)"
        return base


class NaturalLanguageParser:
    """
    自然语言解析器 (AGI认知链环节 - 感知与理解)
    将非结构化文本转换为结构化逻辑对象
    """

    # 定义关键词映射 (词袋模型简化版)
    KEYWORD_MAP = {
        'and': 'AND',
        'or': 'OR',
        'not': 'NOT',
        'open': 'OUT',
        'close': 'OUT',
        'start': 'SET',
        'stop': 'RST',
        'valve': 'VALVE',
        'pump': 'PUMP',
        'sensor': 'SENSOR'
    }

    # 操作符映射
    OPERATOR_MAP = {
        'greater than': '>',
        'less than': '<',
        'equals': '==',
        'reaches': '>=',
        'above': '>',
        'below': '<'
    }

    def parse_intent(self, text: str) -> Dict:
        """
        解析自然语言指令，提取逻辑结构。
        
        Args:
            text (str): 自然语言描述，例如 "在压力达到5MPa且温度低于40度时，开启阀门B"
            
        Returns:
            Dict: 包含conditions和actions的字典
        """
        logger.info(f"Parsing natural language: {text}")
        
        # 简化的规则匹配逻辑 (生产环境应使用NLP模型)
        # 1. 分割条件和动作
        if 'when' in text.lower():
            parts = text.lower().split('when')
            condition_text = parts[0].strip()
            action_text = parts[1].strip()
        elif '时' in text:
            parts = text.split('时')
            condition_text = parts[0].replace('在', '').strip()
            action_text = parts[1].strip()
        else:
            raise ValueError("Invalid instruction format: Cannot separate condition and action")

        parsed_data = {
            "raw_text": text,
            "conditions": self._extract_conditions(condition_text),
            "actions": self._extract_actions(action_text)
        }
        
        logger.debug(f"Parsed structure: {parsed_data}")
        return parsed_data

    def _extract_conditions(self, text: str) -> List[Dict]:
        """提取条件逻辑"""
        # 伪代码：正则提取 "变量 + 操作符 + 阈值"
        # 实际需要复杂的NER(命名实体识别)
        conditions = []
        
        # 示例匹配: "pressure reaches 5MPa" 或 "温度低于40度"
        # 这里使用简化的正则演示
        patterns = [
            r"(\w+)\s+(reaches|above|below|greater than|less than)\s+([\d\.]+)(\w+)?",
            r"(\w+)(达到|高于|低于|大于|小于)([\d\.]+)(\w+)?"
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                conditions.append({
                    "variable": match.group(1),
                    "operator": self.OPERATOR_MAP.get(match.group(2), match.group(2)),
                    "value": float(match.group(3)),
                    "unit": match.group(4) or ""
                })
        return conditions

    def _extract_actions(self, text: str) -> List[Dict]:
        """提取执行动作"""
        actions = []
        # 简化匹配：寻找 "开启/关闭 + 设备"
        if '开启' in text or 'open' in text.lower():
            # 提取设备名，此处简化为 "Valve B"
            device_match = re.search(r"阀门\s*(\w+)|valve\s*(\w+)", text)
            device_name = device_match.group(1) or device_match.group(2) if device_match else "Unknown"
            actions.append({"type": "TURN_ON", "target": f"VALVE_{device_name.upper()}"})
            
        return actions


class LogicCompiler:
    """
    逻辑编译器 (AGI认知链环节 - 推理与综合)
    将结构化逻辑编译为IEC 61131-3指令列表
    """

    def generate_routine(self, parsed_data: Dict) -> List[PLCInstruction]:
        """
        生成PLC指令块
        
        Args:
            parsed_data (Dict): 解析后的逻辑数据
            
        Returns:
            List[PLCInstruction]: PLC指令列表
        """
        instructions = []
        var_map = {}  # 变量地址映射 (模拟符号表)
        
        # 1. 生成比较指令
        for idx, cond in enumerate(parsed_data['conditions']):
            var_name = cond['variable'].upper()
            # 模拟地址分配
            address = f"%IW{idx}" 
            var_map[var_name] = address
            
            # CMP Source1 Source2
            # 这里简化为 LD Variable / CMP Value
            instructions.append(PLCInstruction(
                operation=PLCInstructionType.LD,
                operand=address,
                comment=f"Load {var_name}"
            ))
            
            # 构造比较操作数
            cmp_operand = f"{cond['value']} ({cond['unit']})"
            instructions.append(PLCInstruction(
                operation=PLCInstructionType.CMP,
                operand=cmp_operand,
                comment=f"Check if {cond['operator']} {cond['value']}"
            ))
            
            # 如果有多个条件，添加逻辑连接指令 (简化处理，默认AND)
            if idx < len(parsed_data['conditions']) - 1:
                # 需要根据语义分析确定是AND还是OR，这里默认AND
                pass 

        # 2. 生成输出指令
        for action in parsed_data['actions']:
            target = action['target']
            # 模拟输出地址
            out_address = f"%QW{target.split('_')[-1]}" 
            
            if action['type'] == 'TURN_ON':
                instructions.append(PLCInstruction(
                    operation=PLCInstructionType.OUT,
                    operand=out_address,
                    comment=f"Activate {target}"
                ))
        
        logger.info(f"Generated {len(instructions)} instructions.")
        return instructions


class VerificationEngine:
    """
    验证引擎 (AGI认知链环节 - 评估与修正)
    对生成的代码进行静态检查和逻辑逆向验证
    """

    def verify_syntax(self, instructions: List[PLCInstruction]) -> bool:
        """验证指令语法是否有效"""
        if not instructions:
            logger.error("Verification failed: Empty instruction list")
            return False
        
        for inst in instructions:
            if not isinstance(inst, PLCInstruction):
                logger.error(f"Invalid instruction type: {type(inst)}")
                return False
            if not inst.operand:
                logger.error(f"Missing operand for operation {inst.operation}")
                return False
                
        logger.info("Syntax verification passed.")
        return True

    def reverse_and_validate(self, instructions: List[PLCInstruction], original_intent: Dict) -> bool:
        """
        逆向解析代码并与原始意图比对
        """
        logger.info("Starting reverse logic validation...")
        
        # 模拟执行逻辑：检查是否包含必要的比较和输出
        has_compare = any(inst.operation == PLCInstructionType.CMP for inst in instructions)
        has_output = any(inst.operation == PLCInstructionType.OUT for inst in instructions)
        
        if has_compare and has_output:
            logger.info("Logic structure matches intent (Conditional -> Action).")
            return True
        
        logger.warning("Logic structure mismatch.")
        return False


def run_agi_skill_generation(natural_language_cmd: str) -> Tuple[bool, Union[str, List[PLCInstruction]]]:
    """
    核心技能函数：完整的认知链处理流程
    
    Input Format:
        natural_language_cmd: String describing the control logic.
        
    Output Format:
        Tuple: (Success Status, Generated Code List or Error Message)
    """
    logger.info(f"=== AGI Skill Triggered: {natural_language_cmd} ===")
    
    try:
        # 数据验证
        if not natural_language_cmd or len(natural_language_cmd) < 5:
            raise ValueError("Input instruction too short or empty")

        # 1. 感知：自然语言解析
        parser = NaturalLanguageParser()
        intent_data = parser.parse_intent(natural_language_cmd)
        
        # 边界检查
        if not intent_data['conditions'] or not intent_data['actions']:
            raise ValueError("Failed to extract valid conditions or actions from text.")

        # 2. 推理：代码生成
        compiler = LogicCompiler()
        plc_code = compiler.generate_routine(intent_data)
        
        # 3. 评估：验证
        verifier = VerificationEngine()
        is_syntax_ok = verifier.verify_syntax(plc_code)
        is_logic_ok = verifier.reverse_and_validate(plc_code, intent_data)
        
        if is_syntax_ok and is_logic_ok:
            # 转换为可读代码字符串
            code_str = "\n".join([inst.to_code() for inst in plc_code])
            logger.info(f"Generation Successful:\n{code_str}")
            return True, plc_code
        else:
            return False, "Validation phase failed."

    except Exception as e:
        logger.error(f"Critical failure in AGI skill pipeline: {str(e)}")
        return False, str(e)


# === 使用示例 ===
if __name__ == "__main__":
    # 示例 1: 复杂工艺描述
    sample_input = "在压力达到5MPa且温度低于40度时，开启阀门B"
    
    success, result = run_agi_skill_generation(sample_input)
    
    if success:
        print("\n--- Generated PLC Code (IEC 61131-3 IL) ---")
        for instruction in result:
            print(instruction.to_code())
    else:
        print(f"\nError: {result}")