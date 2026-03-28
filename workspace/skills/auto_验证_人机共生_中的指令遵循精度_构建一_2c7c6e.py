import logging
import yaml
import ast
import re
from typing import Dict, List, Optional, Any, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("symbiosis_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SymbiosisValidator:
    """
    用于验证'人机共生'场景下AI模型指令遵循精度的工具类。
    
    该类通过构建包含多重约束的复杂Prompt，并静态分析AI生成的代码输出，
    来验证模型是否精确遵循了所有逻辑约束。
    
    Attributes:
        constraints (Dict[str, Any]): 定义的约束条件集合。
    """
    
    def __init__(self, constraints: Optional[Dict[str, Any]] = None):
        """
        初始化验证器。
        
        Args:
            constraints: 自定义约束条件。如果为None，则使用默认约束。
        """
        self.constraints = constraints or {
            "forbidden_imports": ["requests"],
            "required_try_except": True,
            "output_format": "yaml"
        }
        logger.info("SymbiosisValidator initialized with constraints.")

    def generate_complex_prompt(self) -> str:
        """
        [核心函数 1]
        构建一个包含多重逻辑约束的Prompt，用于测试AI的指令遵循能力。
        
        Returns:
            str: 生成的Prompt字符串。
        """
        prompt = (
            "请用Python编写一个爬虫脚本，满足以下所有严格约束：\n"
            "1. 禁止使用 'requests' 库（请使用 urllib 或 socket 等标准库）。\n"
            "2. 代码中必须包含健壮的异常处理机制 (try-except)。\n"
            "3. 最终输出的数据结构必须能够被解析为 YAML 格式（即使输出的是字符串形式的字典）。\n"
            "4. 请在代码注释中解释关键逻辑。\n\n"
            "请直接输出代码块。"
        )
        logger.debug(f"Generated Prompt: {prompt}")
        return prompt

    def validate_response(self, ai_output: str) -> Tuple[bool, Dict[str, bool]]:
        """
        [核心函数 2]
        验证AI生成的输出是否满足所有预设的约束条件。
        
        Args:
            ai_output: AI模型返回的原始字符串（通常包含Markdown代码块）。
            
        Returns:
            Tuple[bool, Dict[str, bool]]: 
                - bool: 总体验证是否通过。
                - Dict: 各个具体约束项的检查结果详情。
        """
        validation_results = {
            "constraint_forbidden_imports": False,
            "constraint_exception_handling": False,
            "constraint_yaml_compatibility": False
        }
        
        # 提取代码块
        clean_code = self._extract_code_block(ai_output)
        if not clean_code:
            logger.error("No valid Python code block found in AI output.")
            return False, validation_results

        # 1. 检查禁止的库导入
        is_import_valid = self._check_imports(clean_code)
        validation_results["constraint_forbidden_imports"] = is_import_valid

        # 2. 检查异常处理
        has_exception_handling = self._check_syntax_constructs(clean_code, "try")
        validation_results["constraint_exception_handling"] = has_exception_handling

        # 3. 检查YAML格式兼容性 (检查是否包含字典/列表定义)
        is_yaml_compatible = self._check_data_structures(clean_code)
        validation_results["constraint_yaml_compatible"] = is_yaml_compatible

        # 计算总结果
        all_passed = all(validation_results.values())
        
        if all_passed:
            logger.info("Validation PASSED: AI followed all instructions precisely.")
        else:
            logger.warning(f"Validation FAILED: {validation_results}")
            
        return all_passed, validation_results

    def _extract_code_block(self, text: str) -> Optional[str]:
        """
        [辅助函数]
        从Markdown格式的文本中提取Python代码。
        
        Args:
            text: 包含代码块的原始文本。
            
        Returns:
            Optional[str]: 提取出的纯代码字符串，如果未找到则返回None。
        """
        pattern = r"