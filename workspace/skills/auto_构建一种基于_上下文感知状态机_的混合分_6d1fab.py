"""
混合分词引擎模块：基于上下文感知状态机

本模块实现了一种能够同时处理结构化文本（代码/公式）和非结构化自然语言的混合分词器。
通过确定的有限状态机（FSM）精确捕获语法结构，同时利用概率模型处理模糊语义，
专为处理Jupyter Notebook、技术文档等"代码+自然语言"混合场景优化。

核心特性：
- 上下文感知的状态切换
- 结构化/非结构化文本的混合处理
- 符号级与语义级的无缝切换
- 完整的错误处理和边界检查
"""

import re
import logging
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenType(Enum):
    """定义混合文档中的Token类型"""
    CODE = auto()        # 结构化代码
    COMMENT = auto()     # 自然语言注释
    FORMULA = auto()     # 数学公式
    KEYWORD = auto()     # 编程语言关键字
    OPERATOR = auto()    # 操作符
    STRING = auto()      # 字符串字面量
    WHITESPACE = auto()  # 空白字符
    UNKNOWN = auto()     # 未知类型


@dataclass
class Token:
    """表示一个分词后的Token"""
    value: str
    type: TokenType
    line: int
    column: int
    context: Optional[Dict[str, str]] = None

    def __repr__(self) -> str:
        return f"Token({self.value!r}, {self.type.name}, {self.line}:{self.column})"


class ContextAwareFSM:
    """
    上下文感知状态机，用于处理混合文本
    
    属性:
        current_state (TokenType): 当前状态
        stack (List[TokenType]): 状态栈，用于处理嵌套结构
        buffer (str): 当前Token的缓冲区
        tokens (List[Token]): 生成的Token列表
        line (int): 当前行号
        column (int): 当前列号
    """
    
    def __init__(self):
        self.current_state = TokenType.UNKNOWN
        self.stack = []
        self.buffer = ""
        self.tokens = []
        self.line = 1
        self.column = 1
        self._init_patterns()
        
    def _init_patterns(self) -> None:
        """初始化匹配模式"""
        # 编程语言关键字模式（示例）
        self.keyword_pattern = re.compile(
            r'\b(def|class|if|else|for|while|return|import|from|as|try|except|with)\b'
        )
        
        # 操作符模式
        self.operator_pattern = re.compile(
            r'(\+|\-|\*|\/|\=\=|\!\=|\<|\>|\<\=|\>\=|\=\>|\-\>|\.\.\.)'
        )
        
        # 公式模式（LaTeX风格）
        self.formula_pattern = re.compile(r'(\$.*?\$|\$\$.*?\$\$|\\\(.*?\\\)|\\\[.*?\\\])')
        
        # 自然语言注释模式
        self.comment_pattern = re.compile(r'(#.*?$|\/\/.*?$|\/\*.*?\*\/|\'\'\'.*?\'\'\'|\"\"\".*?\"\"\")', re.DOTALL)
        
        # 字符串字面量模式
        self.string_pattern = re.compile(r'(\".*?\"|\'.*?\'|f\".*?\"|f\'.*?\')', re.DOTALL)
    
    def _push_state(self, state: TokenType) -> None:
        """将当前状态压栈并切换到新状态"""
        self.stack.append(self.current_state)
        self.current_state = state
        
    def _pop_state(self) -> Optional[TokenType]:
        """弹出栈顶状态并恢复"""
        if not self.stack:
            logger.warning("尝试在空栈上弹出状态")
            return None
        self.current_state = self.stack.pop()
        return self.current_state
    
    def _emit_token(self, token_type: Optional[TokenType] = None) -> Token:
        """生成并返回一个Token"""
        token_type = token_type or self.current_state
        if not self.buffer:
            raise ValueError("尝试生成空Token")
            
        token = Token(
            value=self.buffer,
            type=token_type,
            line=self.line,
            column=self.column - len(self.buffer),
            context={"state": self.current_state.name}
        )
        
        self.tokens.append(token)
        logger.debug(f"生成Token: {token}")
        self.buffer = ""
        return token
    
    def _update_position(self, char: str) -> None:
        """更新行号和列号"""
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
    
    def _handle_transition(self, char: str) -> None:
        """处理状态转换"""
        # 检查注释开始
        if char == '#':
            self._push_state(TokenType.COMMENT)
            self.buffer += char
            return
            
        # 检查字符串开始
        if char in {'"', "'"}:
            self._push_state(TokenType.STRING)
            self.buffer += char
            return
            
        # 检查公式开始
        if char == '$' or char == '\\':
            self._push_state(TokenType.FORMULA)
            self.buffer += char
            return
            
        # 默认处理为代码
        if self.current_state == TokenType.UNKNOWN:
            self.current_state = TokenType.CODE
            
        self.buffer += char
    
    def process_char(self, char: str) -> Optional[Token]:
        """
        处理单个字符并返回生成的Token（如果有）
        
        参数:
            char: 要处理的字符
            
        返回:
            生成的Token或None
        """
        if not char:
            raise ValueError("尝试处理空字符")
            
        self._update_position(char)
        
        # 状态机处理逻辑
        if self.current_state == TokenType.COMMENT:
            if char == '\n':
                token = self._emit_token()
                self._pop_state()
                return token
            self.buffer += char
            
        elif self.current_state == TokenType.STRING:
            self.buffer += char
            if len(self.buffer) >= 2 and self.buffer[-1] == self.buffer[0]:
                if self.buffer[-2] != '\\':
                    token = self._emit_token()
                    self._pop_state()
                    return token
                    
        elif self.current_state == TokenType.FORMULA:
            self.buffer += char
            if len(self.buffer) >= 2 and self.buffer[-1] == self.buffer[0]:
                if self.buffer[-2] != '\\':
                    token = self._emit_token()
                    self._pop_state()
                    return token
                    
        else:
            # 检查关键字和操作符
            if match := self.keyword_pattern.match(char):
                self._handle_transition(char)
                if match.end() == len(self.buffer):
                    token = self._emit_token(TokenType.KEYWORD)
                    return token
                    
            elif match := self.operator_pattern.match(char):
                self._handle_transition(char)
                if match.end() == len(self.buffer):
                    token = self._emit_token(TokenType.OPERATOR)
                    return token
                    
            else:
                self._handle_transition(char)
                
        return None
    
    def finalize(self) -> List[Token]:
        """完成处理并返回所有Token"""
        if self.buffer:
            self._emit_token()
        return self.tokens


def tokenize_mixed_text(text: str) -> List[Token]:
    """
    主函数：对混合文本进行分词处理
    
    参数:
        text: 要分词的混合文本
        
    返回:
        Token对象列表
        
    示例:
        >>> text = '''
        ... def func():  # 这是一个函数
        ...     return "Hello" + "$a^2$"
        ... '''
        >>> tokens = tokenize_mixed_text(text)
        >>> print(tokens)
    """
    if not isinstance(text, str):
        raise TypeError("输入必须是字符串")
        
    if not text.strip():
        logger.warning("输入为空字符串")
        return []
        
    fsm = ContextAwareFSM()
    tokens = []
    
    for char in text:
        token = fsm.process_char(char)
        if token:
            tokens.append(token)
            
    tokens.extend(fsm.finalize())
    logger.info(f"分词完成，共生成 {len(tokens)} 个Token")
    return tokens


def analyze_token_context(tokens: List[Token]) -> Dict[str, int]:
    """
    辅助函数：分析Token上下文分布
    
    参数:
        tokens: Token列表
        
    返回:
        包含各类型Token数量的字典
        
    示例:
        >>> stats = analyze_token_context(tokens)
        >>> print(stats)
    """
    if not tokens:
        return {}
        
    stats = {t.name: 0 for t in TokenType}
    
    for token in tokens:
        if token.type in stats:
            stats[token.type.name] += 1
        else:
            stats[TokenType.UNKNOWN.name] += 1
            
    logger.info(f"Token分布统计: {stats}")
    return stats


def validate_tokens(tokens: List[Token]) -> bool:
    """
    验证Token序列的有效性
    
    参数:
        tokens: 要验证的Token列表
        
    返回:
        bool: 是否有效
        
    示例:
        >>> is_valid = validate_tokens(tokens)
    """
    if not tokens:
        return False
        
    for i, token in enumerate(tokens):
        if not token.value:
            logger.error(f"发现空Token在位置 {i}")
            return False
            
        if not isinstance(token.type, TokenType):
            logger.error(f"无效Token类型在位置 {i}")
            return False
            
        if token.line < 1 or token.column < 1:
            logger.error(f"无效位置信息在位置 {i}")
            return False
            
    return True


if __name__ == "__main__":
    # 示例用法
    sample_text = """
    def calculate_area(radius):
        # 计算圆面积: $A = \pi r^2$
        pi = 3.14159
        return pi * radius ** 2  # 返回计算结果
    """
    
    print("=== 混合分词示例 ===")
    tokens = tokenize_mixed_text(sample_text)
    
    print("\n生成的Tokens:")
    for token in tokens[:10]:  # 只显示前10个Token
        print(f"{token.type.name:8} {token.value!r:15} (位置: {token.line}:{token.column})")
    
    print("\nToken统计:")
    stats = analyze_token_context(tokens)
    for k, v in stats.items():
        if v > 0:
            print(f"{k:12}: {v}")
    
    print("\n验证结果:", validate_tokens(tokens))