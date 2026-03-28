"""
Module: auto_如何实现从非结构化自然语言到可证伪逻辑表_4260cf
Description: 自动将非结构化自然语言（如'菜炒糊了'）编译为可证伪的逻辑表达式（如 Check: Temp > 200）。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LogicExpression:
    """
    逻辑表达式数据结构。
    
    Attributes:
        subject (str): 监控主体 (e.g., 'Temperature')
        operator (str): 逻辑操作符 (e.g., '>', '==', 'contains')
        threshold (Any): 阈值或目标值
        unit (Optional[str]): 单位 (e.g., 'C', 'mins')
        raw_text (str): 原始输入文本
    """
    subject: str
    operator: str
    threshold: Any
    unit: Optional[str]
    raw_text: str

    def to_executable_code(self) -> str:
        """将逻辑结构转换为可执行字符串代码"""
        return f"Check: {self.subject} {self.operator} {self.threshold}{self.unit or ''}"

class NL2LogicCompiler:
    """
    核心编译器类：负责将自然语言转化为可执行逻辑。
    
    流程：
    1. 实体抽取
    2. 意图/状态映射
    3. 参数阈值估算
    4. 逻辑合成
    """

    def __init__(self, domain_config: Optional[Dict] = None):
        """
        初始化编译器。
        
        Args:
            domain_config: 领域特定配置，包含默认参数范围。
        """
        self.domain_config = domain_config or self._default_config()
        logger.info("NL2LogicCompiler initialized with domain config.")

    def _default_config(self) -> Dict:
        """提供默认的领域常识配置（模拟知识库）"""
        return {
            "cooking": {
                "h burnt": {"subject": "temperature", "op": ">", "val": 200, "unit": "C"},
                "h overcooked": {"subject": "time", "op": ">", "val": 30, "unit": "mins"},
                "h too salty": {"subject": "salt_grams", "op": ">", "val": 5, "unit": "g"},
                "h cold": {"subject": "temperature", "op": "<", "val": 30, "unit": "C"},
            },
            "system": {
                "h too slow": {"subject": "latency", "op": ">", "val": 500, "unit": "ms"},
            }
        }

    @staticmethod
    def _clean_input(text: str) -> str:
        """
        辅助函数：清洗输入文本。
        移除标点符号，转换小写，处理常见口语词。
        """
        if not text:
            return ""
        # 移除特殊字符，保留中文、字母、数字、空格
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        # 统一转换为小写（对英文有效）
        cleaned = cleaned.lower()
        logger.debug(f"Cleaned input: '{text}' -> '{cleaned}'")
        return cleaned.strip()

    def _map_intent_to_logic(self, domain: str, cleaned_text: str) -> Optional[Dict]:
        """
        核心函数1：意图映射。
        根据清洗后的文本匹配领域配置中的逻辑模板。
        
        Args:
            domain: 领域上下文 (e.g., 'cooking')
            cleaned_text: 清洗后的文本
            
        Returns:
            匹配到的逻辑字典或None
        """
        domain_rules = self.domain_config.get(domain, {})
        
        # 简化的关键词匹配逻辑（实际AGI应使用Vector Embedding）
        for key, logic in domain_rules.items():
            # 将配置键转换为匹配模式，例如 "h burnt" -> "burnt"
            keyword = key.replace('h ', '') 
            if keyword in cleaned_text:
                logger.info(f"Intent matched: Key='{key}', Logic={logic}")
                return logic
        
        logger.warning(f"No logic match found for: {cleaned_text} in domain {domain}")
        return None

    def compile_falsifiable_logic(self, natural_text: str, domain: str = "cooking") -> Optional[LogicExpression]:
        """
        核心函数2：编译主入口。
        将自然语言编译为 LogicExpression 对象。
        
        Args:
            natural_text (str): 用户输入，如 "这菜炒糊了"
            domain (str): 上下文领域
            
        Returns:
            LogicExpression: 可执行逻辑对象
            
        Raises:
            ValueError: 如果输入为空或领域无效
        """
        if not natural_text:
            raise ValueError("Input text cannot be empty")

        logger.info(f"Compiling: '{natural_text}' for domain '{domain}'")
        
        # 1. 预处理
        clean_text = self._clean_input(natural_text)
        
        # 2. 逻辑映射
        logic_template = self._map_intent_to_logic(domain, clean_text)
        
        if not logic_template:
            return None

        # 3. 数据验证与边界检查
        subject = logic_template.get("subject")
        operator = logic_template.get("op")
        value = logic_template.get("val")
        unit = logic_template.get("unit")

        # 边界检查：确保操作符合法
        valid_operators = {'>', '<', '>=', '<=', '==', '!='}
        if operator not in valid_operators:
            logger.error(f"Invalid operator detected: {operator}")
            raise SyntaxError(f"Operator {operator} is not supported")

        # 边界检查：确保数值合法
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except ValueError:
                logger.error(f"Non-numeric threshold value: {value}")
                raise TypeError("Threshold must be numeric")

        # 4. 构建表达式对象
        expression = LogicExpression(
            subject=subject,
            operator=operator,
            threshold=value,
            unit=unit,
            raw_text=natural_text
        )
        
        logger.info(f"Compilation successful: {expression.to_executable_code()}")
        return expression

def run_compilation_example():
    """
    使用示例：展示完整的编译流程。
    """
    compiler = NL2LogicCompiler()
    
    test_cases = [
        ("这菜炒糊了", "cooking"),
        ("汤太咸了", "cooking"),
        ("系统响应太慢了", "system"),
        ("服务员，牛排是凉的", "cooking")
    ]
    
    print("--- Starting Compilation Process ---")
    for text, domain in test_cases:
        try:
            result = compiler.compile_falsifiable_logic(text, domain)
            if result:
                print(f"Input: {text}")
                print(f"Output Code: {result.to_executable_code()}")
                print(f"Details: Subject={result.subject}, Threshold={result.threshold}")
                print("-" * 30)
            else:
                print(f"Input: {text} -> [FAILED TO COMPILE]")
        except Exception as e:
            print(f"Error processing '{text}': {e}")

if __name__ == "__main__":
    run_compilation_example()