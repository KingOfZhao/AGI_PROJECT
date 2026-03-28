"""
Module: auto_instruction_robustness_filter.py
Description: 【指令遵循的抗干扰性】在充满冗余信息、歧义指令或甚至故意误导的复杂Prompt中，
             AI能否准确提取核心约束条件并严格执行，而不被语义噪声带偏？
             本模块提供了一套机制，用于在生成输出后，根据预定义的约束（如JSON格式、禁止解释等）
             进行清洗和验证，确保最终结果满足核心约束，即使输入上下文包含大量干扰信息。
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """定义约束类型的枚举"""
    JSON_FORMAT = "json_format"
    NO_EXPLANATION = "no_explanation"
    MAX_LENGTH = "max_length"
    KEYWORD_BLACKLIST = "keyword_blacklist"

@dataclass
class ConstraintConfig:
    """
    约束配置类
    
    Attributes:
        require_json (bool): 是否强制输出为有效JSON
        strip_explanations (bool): 是否移除解释性文本（如"Sure, here is..."）
        max_tokens (Optional[int]): 最大允许Token长度（近似字符数）
        forbidden_patterns (List[str]): 禁止出现的正则表达式模式列表
    """
    require_json: bool = True
    strip_explanations: bool = True
    max_tokens: Optional[int] = None
    forbidden_patterns: List[str] = field(default_factory=list)

class ConstraintValidationError(Exception):
    """自定义异常：当输出无法满足核心约束时抛出"""
    pass

def _clean_noise(text: str, patterns: List[str]) -> str:
    """
    [辅助函数] 根据给定的正则表达式列表移除文本中的噪声。
    
    Args:
        text (str): 原始文本。
        patterns (List[str]): 需要移除的正则表达式列表。
        
    Returns:
        str: 清洗后的文本。
        
    Example:
        >>> _clean_noise("Output: {data} End", ["Output: ", " End"])
        '{data}'
    """
    if not text:
        return ""
        
    cleaned_text = text
    for pattern in patterns:
        try:
            # 使用 re.DOTALL 确保换行符也被匹配
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.DOTALL | re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            continue
            
    return cleaned_text.strip()

def extract_core_content(raw_response: str, config: ConstraintConfig) -> str:
    """
    [核心函数 1] 从充满噪声的LLM响应中提取核心内容。
    处理诱导性文本、前置/后置解释，并尝试提取有效的数据结构。
    
    Args:
        raw_response (str): 大模型返回的原始字符串，可能包含干扰信息。
        config (ConstraintConfig): 约束配置对象。
        
    Returns:
        str: 提取并清洗后的核心内容。
        
    Raises:
        ValueError: 如果输入为空。
    """
    if not raw_response:
        raise ValueError("Input raw_response cannot be empty.")
    
    logger.info("Starting core content extraction...")
    working_text = raw_response.strip()
    
    # 1. 处理解释性文本干扰
    if config.strip_explanations:
        # 常见的LLM解释性前缀/后缀模式
        explanation_patterns = [
            r"^Sure,?\s*(here is|here are).*?:",  # "Sure, here is the result:"
            r"^Based on the context.*?:",
            r"^Output:",
            r"^