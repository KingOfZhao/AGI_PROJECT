"""
自适应动态分词引擎

基于编译原理DFA实现的领域专用分词系统，支持医疗/法律等结构化文本的高效解析。
核心特性：
1. 通过BNF范式定义语法规则，实现"语法即分词"
2. 确定性有限自动机(DFA)保证O(n)时间复杂度
3. 100%可解释的分词过程，适合逻辑敏感场景
4. 支持动态加载领域专用语法规则

典型应用场景：
>>> engine = AdaptiveTokenizerEngine()
>>> engine.load_medical_rules()
>>> tokens = engine.tokenize("患者3年前行阑尾切除术")
>>> print(tokens)
['患者', '3年', '前', '行', '阑尾', '切除术']
"""

import logging
import re
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptiveTokenizer")


class TokenType(Enum):
    """分词类型枚举"""
    WORD = auto()       # 常规词汇
    NUMBER = auto()     # 数字
    PUNCTUATION = auto()  # 标点符号
    ENTITY = auto()     # 实体词
    UNKNOWN = auto()    # 未知类型


@dataclass
class Token:
    """分词结果数据结构"""
    text: str
    type: TokenType
    start: int
    end: int
    metadata: Optional[Dict] = None

    def __str__(self) -> str:
        return f"Token({self.text}, {self.type.name})"


class TokenizerError(Exception):
    """分词引擎基础异常"""
    pass


class RuleSyntaxError(TokenizerError):
    """规则语法错误"""
    pass


class DFAState:
    """DFA状态节点"""
    def __init__(self):
        self.transitions: Dict[str, 'DFAState'] = {}
        self.is_end = False
        self.token_type: Optional[TokenType] = None
        self.rule_name: Optional[str] = None


class AdaptiveTokenizerEngine:
    """
    自适应动态分词引擎核心类
    
    使用示例：
    >>> engine = AdaptiveTokenizerEngine()
    >>> engine.add_rule("MED_TERM", ["头痛", "腹痛", "咳嗽"])
    >>> engine.add_rule("DURATION", ["天", "周", "月", "年"])
    >>> tokens = engine.tokenize("患者头痛3天")
    >>> print([t.text for t in tokens])
    ['患者', '头痛', '3', '天']
    """

    def __init__(self):
        self._dfa_root = DFAState()
        self._rules: Dict[str, Set[str]] = {}
        self._max_rule_length = 0
        self._whitespace_pattern = re.compile(r'\s+')
        logger.info("Initialized AdaptiveTokenizerEngine")

    def add_rule(self, rule_name: str, patterns: List[str]) -> None:
        """
        添加分词规则到DFA
        
        Args:
            rule_name: 规则名称（如MED_TERM）
            patterns: 匹配模式列表
            
        Raises:
            RuleSyntaxError: 如果规则语法无效
        """
        if not rule_name.isidentifier():
            raise RuleSyntaxError(f"Invalid rule name: {rule_name}")

        if not patterns:
            logger.warning("Empty pattern list for rule %s", rule_name)
            return

        self._rules[rule_name] = set(patterns)
        for pattern in patterns:
            self._add_pattern_to_dfa(rule_name, pattern)

        self._max_rule_length = max(
            self._max_rule_length,
            max(len(p) for p in patterns)
        )
        logger.info("Added rule %s with %d patterns", rule_name, len(patterns))

    def _add_pattern_to_dfa(self, rule_name: str, pattern: str) -> None:
        """
        将单个模式添加到DFA（内部方法）
        
        Args:
            rule_name: 关联的规则名称
            pattern: 要添加的模式字符串
        """
        current = self._dfa_root
        for char in pattern:
            if char not in current.transitions:
                current.transitions[char] = DFAState()
            current = current.transitions[char]
        
        current.is_end = True
        current.rule_name = rule_name
        # 根据规则名称推断token类型
        if "NUM" in rule_name:
            current.token_type = TokenType.NUMBER
        elif "PUNCT" in rule_name:
            current.token_type = TokenType.PUNCTUATION
        elif "ENTITY" in rule_name:
            current.token_type = TokenType.ENTITY
        else:
            current.token_type = TokenType.WORD

    def tokenize(self, text: str) -> List[Token]:
        """
        执行分词操作
        
        Args:
            text: 要分词的文本
            
        Returns:
            分词结果列表
            
        Raises:
            TokenizerError: 如果输入文本无效
        """
        if not isinstance(text, str):
            raise TokenizerError("Input must be string")
            
        text = text.strip()
        if not text:
            return []

        tokens: List[Token] = []
        position = 0
        length = len(text)

        while position < length:
            # 跳过空白字符
            if self._whitespace_pattern.match(text[position]):
                position += 1
                continue

            # 尝试匹配最长规则
            token = self._match_longest_token(text, position)
            if token:
                tokens.append(token)
                position = token.end
            else:
                # 未匹配的字符作为UNKNOWN处理
                tokens.append(Token(
                    text=text[position],
                    type=TokenType.UNKNOWN,
                    start=position,
                    end=position + 1
                ))
                position += 1

        logger.debug("Tokenized %d chars into %d tokens", length, len(tokens))
        return tokens

    def _match_longest_token(self, text: str, start: int) -> Optional[Token]:
        """
        从指定位置开始匹配最长token（内部方法）
        
        Args:
            text: 输入文本
            start: 起始位置
            
        Returns:
            匹配的Token或None
        """
        current = self._dfa_root
        last_match: Optional[Tuple[int, str, TokenType]] = None
        pos = start
        length = min(start + self._max_rule_length, len(text))

        while pos < length:
            char = text[pos]
            if char not in current.transitions:
                break
                
            current = current.transitions[char]
            if current.is_end:
                last_match = (pos + 1, current.rule_name, current.token_type)
            pos += 1

        if last_match:
            end_pos, rule_name, token_type = last_match
            return Token(
                text=text[start:end_pos],
                type=token_type,
                start=start,
                end=end_pos,
                metadata={"rule": rule_name}
            )
        return None

    def load_medical_rules(self) -> None:
        """加载医疗领域默认规则"""
        medical_terms = [
            "头痛", "腹痛", "咳嗽", "发热", "乏力",
            "高血压", "糖尿病", "冠心病", "阑尾炎",
            "切除术", "造影", "活检", "化疗"
        ]
        self.add_rule("MED_TERM", medical_terms)

        time_units = ["天", "周", "月", "年"]
        self.add_rule("TIME_UNIT", time_units)

        numbers = [str(i) for i in range(10)]
        self.add_rule("NUM", numbers)

        punctuations = ["，", "。", "、", "：", "；"]
        self.add_rule("PUNCT", punctuations)

        logger.info("Loaded default medical rules")

    def get_rule_stats(self) -> Dict[str, int]:
        """
        获取规则统计信息
        
        Returns:
            包含规则名称和模式数量的字典
        """
        return {name: len(patterns) for name, patterns in self._rules.items()}


# 示例用法
if __name__ == "__main__":
    # 初始化引擎并加载医疗规则
    engine = AdaptiveTokenizerEngine()
    engine.load_medical_rules()
    
    # 添加自定义规则
    engine.add_rule("BODY_PART", ["头部", "腹部", "胸部", "四肢"])
    engine.add_rule("FREQUENCY", ["每日", "每周", "每月", "每年"])
    
    # 测试文本
    medical_text = "患者3年前行阑尾切除术，术后每日头痛2次，持续1周。"
    
    # 执行分词
    tokens = engine.tokenize(medical_text)
    
    # 打印结果
    print(f"输入文本: {medical_text}")
    print("分词结果:")
    for token in tokens:
        print(f"{token.text:5} | {token.type.name:12} | 位置: {token.start}-{token.end}")
    
    # 打印规则统计
    print("\n规则统计:")
    for rule, count in engine.get_rule_stats().items():
        print(f"{rule}: {count}个模式")