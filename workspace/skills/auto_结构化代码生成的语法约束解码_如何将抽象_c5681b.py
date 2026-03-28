"""
模块名称: syntax_constrained_decoding
描述: 实现基于抽象语法树(AST)约束的结构化代码生成解码器。
      通过在LLM解码过程中集成语法检查，确保生成的代码符合目标语言语法规范。
"""

import logging
from typing import List, Dict, Optional, Tuple
import ast
import re
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DecodingConfig:
    """解码配置参数"""
    max_tokens: int = 100
    temperature: float = 1.0
    top_p: float = 0.9
    grammar_strictness: str = "high"  # high/medium/low
    stop_sequences: List[str] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["\n\n", "def ", "class "]

class SyntaxConstrainedDecoder:
    """语法约束解码器主类"""
    
    def __init__(self, config: Optional[DecodingConfig] = None):
        """
        初始化解码器
        
        参数:
            config: 解码配置对象
        """
        self.config = config or DecodingConfig()
        self._validate_config()
        logger.info("Initialized SyntaxConstrainedDecoder with config: %s", self.config)

    def _validate_config(self) -> None:
        """验证配置参数的有效性"""
        if not 0 < self.config.temperature <= 2.0:
            raise ValueError("Temperature must be between 0 and 2.0")
        if not 0 < self.config.top_p <= 1.0:
            raise ValueError("Top-p must be between 0 and 1.0")
        if self.config.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")

    def generate(
        self,
        prompt: str,
        partial_code: str = "",
        grammar_rules: Optional[Dict] = None
    ) -> str:
        """
        生成符合语法约束的代码
        
        参数:
            prompt: 输入提示词
            partial_code: 部分完成的代码(可选)
            grammar_rules: 自定义语法规则(可选)
            
        返回:
            完整的符合语法的代码字符串
            
        示例:
            >>> decoder = SyntaxConstrainedDecoder()
            >>> code = decoder.generate("Write a Python function", "def add(a, b:")
            >>> print(code)
        """
        if not prompt and not partial_code:
            raise ValueError("Either prompt or partial_code must be provided")
            
        logger.debug("Starting generation with prompt: %s", prompt[:50] + "...")
        
        # 这里应该是实际的LLM调用，这里用模拟实现
        generated_code = self._mock_llm_generation(prompt, partial_code)
        
        # 应用语法约束
        constrained_code = self._apply_syntax_constraints(
            generated_code, 
            grammar_rules or self._default_grammar_rules()
        )
        
        if self._validate_syntax(constrained_code):
            return constrained_code
        else:
            logger.warning("Generated code failed syntax validation, retrying...")
            return self.generate(prompt, constrained_code, grammar_rules)

    def _mock_llm_generation(self, prompt: str, partial: str) -> str:
        """模拟LLM生成过程(实际实现中应替换为真实LLM调用)"""
        # 这里返回一个简单的模拟结果
        if "add" in prompt.lower():
            return f"{partial}\n    return a + b"
        return f"{partial}\n    pass"

    def _default_grammar_rules(self) -> Dict:
        """返回默认的语法规则集"""
        return {
            "indentation": "4 spaces",
            "max_line_length": 88,
            "required_docstring": True,
            "type_hints": "optional"
        }

    def _apply_syntax_constraints(
        self, 
        code: str, 
        rules: Dict
    ) -> str:
        """
        应用语法约束到生成的代码
        
        参数:
            code: 原始生成的代码
            rules: 语法规则字典
            
        返回:
            经过语法约束修正的代码
        """
        try:
            # 处理缩进
            code = self._fix_indentation(code)
            
            # 确保函数有文档字符串
            if rules.get("required_docstring", False):
                code = self._ensure_docstring(code)
                
            # 处理行长度
            code = self._wrap_long_lines(code, rules.get("max_line_length", 88))
            
            return code
        except Exception as e:
            logger.error("Syntax constraint application failed: %s", str(e))
            raise

    def _validate_syntax(self, code: str) -> bool:
        """
        验证代码是否符合Python语法
        
        参数:
            code: 要验证的代码字符串
            
        返回:
            bool: 代码是否有效
        """
        try:
            ast.parse(code)
            logger.debug("Syntax validation passed")
            return True
        except SyntaxError as e:
            logger.warning("Syntax validation failed: %s", str(e))
            return False

    # 辅助方法
    def _fix_indentation(self, code: str) -> str:
        """修正代码缩进"""
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                # 计算当前缩进级别
                new_indent = len(line) - len(stripped)
                if new_indent < indent_level * 4:
                    indent_level = new_indent // 4
                
                # 应用正确的缩进
                fixed_line = ' ' * (indent_level * 4) + stripped
                fixed_lines.append(fixed_line)
                
                # 检查是否需要增加缩进级别
                if stripped.endswith(':'):
                    indent_level += 1
            else:
                fixed_lines.append('')
                
        return '\n'.join(fixed_lines)

    def _ensure_docstring(self, code: str) -> str:
        """确保函数有文档字符串"""
        if '"""' not in code and "'''" not in code:
            # 在函数定义后添加文档字符串
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('def '):
                    indent = len(line) - len(line.lstrip())
                    docstring = ' ' * (indent + 4) + '""\"Function docstring\"""'
                    lines.insert(i+1, docstring)
                    break
            return '\n'.join(lines)
        return code

    def _wrap_long_lines(self, code: str, max_length: int) -> str:
        """处理过长的代码行"""
        lines = code.split('\n')
        wrapped_lines = []
        
        for line in lines:
            if len(line) > max_length:
                # 简单实现: 在逗号处换行
                parts = []
                current = ""
                for part in line.split(','):
                    if len(current + part) > max_length and current:
                        parts.append(current + ',')
                        current = ' ' * (len(line) - len(line.lstrip())) + part
                    else:
                        current += part
                if current:
                    parts.append(current)
                wrapped_lines.extend(parts)
            else:
                wrapped_lines.append(line)
                
        return '\n'.join(wrapped_lines)

def demo_usage():
    """演示模块用法"""
    print("=== 语法约束解码器演示 ===")
    
    # 初始化解码器
    config = DecodingConfig(
        max_tokens=50,
        temperature=0.7,
        grammar_strictness="high"
    )
    decoder = SyntaxConstrainedDecoder(config)
    
    # 示例1: 生成简单函数
    print("\n示例1: 生成加法函数")
    code = decoder.generate("Write a Python add function", "def add(a: int, b: int) -> int:")
    print("生成的代码:")
    print(code)
    
    # 示例2: 从部分代码继续
    print("\n示例2: 从部分代码继续")
    partial = "def multiply(x, y):\n    "
    code = decoder.generate("", partial)
    print("完成的代码:")
    print(code)

if __name__ == "__main__":
    demo_usage()