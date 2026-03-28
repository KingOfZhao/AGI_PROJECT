"""
模块名称: auto_基于代码语法的上下文无关文法_cfg_约_dddf98
描述: 本模块实现了一个基于代码语法的上下文无关文法（CFG）约束生成器。
     旨在通过形式化的文法结构，约束和引导代码生成过程，确保生成的
     代码骨架符合预定义的语法规范。这对应了AGI系统中“自上而下拆解”
     的过程，验证结构约束能否优先于概率生成。

Domain: compiler_principles
Author: AGI System
Version: 1.0.0
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GrammarSymbol:
    """表示文法中的符号（终结符或非终结符）。"""
    name: str
    is_terminal: bool
    
    def __hash__(self):
        return hash((self.name, self.is_terminal))

    def __eq__(self, other):
        if not isinstance(other, GrammarSymbol):
            return False
        return self.name == other.name and self.is_terminal == other.is_terminal

@dataclass
class ProductionRule:
    """表示产生式规则：LHS -> RHS。"""
    lhs: str  # 左侧非终结符
    rhs: List[str]  # 右侧符号列表（可以是终结符或非终结符的名称）
    
    def __str__(self):
        return f"{self.lhs} -> {' '.join(self.rhs)}"

class CFGConstraintEngine:
    """
    上下文无关文法约束引擎。
    
    负责加载文法定义，验证输入是否符合文法，并生成符合文法约束的结构骨架。
    
    Attributes:
        non_terminals (Set[str]): 非终结符集合。
        terminals (Set[str]): 终结符集合。
        start_symbol (str): 起始符号。
        rules (List[ProductionRule]): 产生式规则列表。
        parse_table (Dict): 用于解析的查找表（简化版）。
    """
    
    def __init__(self, grammar_config: Dict[str, Any]):
        """
        初始化CFG引擎。
        
        Args:
            grammar_config (Dict[str, Any]): 包含文法配置的字典。
                必须包含 'non_terminals', 'terminals', 'start_symbol', 'rules'.
        
        Raises:
            ValueError: 如果配置缺少必要字段或格式无效。
        """
        self._validate_config(grammar_config)
        
        self.non_terminals: Set[str] = set(grammar_config['non_terminals'])
        self.terminals: Set[str] = set(grammar_config['terminals'])
        self.start_symbol: str = grammar_config['start_symbol']
        self.rules: List[ProductionRule] = []
        
        for rule_dict in grammar_config['rules']:
            rule = ProductionRule(
                lhs=rule_dict['lhs'],
                rhs=rule_dict['rhs']
            )
            self.rules.append(rule)
            
        logger.info(f"CFG Engine initialized with {len(self.rules)} rules.")
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        验证输入的文法配置是否有效。
        
        Args:
            config (Dict[str, Any]): 输入配置。
        
        Raises:
            ValueError: 配置无效时抛出。
        """
        required_keys = ['non_terminals', 'terminals', 'start_symbol', 'rules']
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required key in grammar config: {key}")
                raise ValueError(f"Invalid grammar config: Missing '{key}'")
        
        if not isinstance(config['rules'], list):
            raise ValueError("Grammar 'rules' must be a list.")
            
        if config['start_symbol'] not in config['non_terminals']:
            raise ValueError("Start symbol must be a non-terminal.")

    def get_rule_for_non_terminal(self, nt: str) -> Optional[ProductionRule]:
        """
        辅助函数：获取指定非终结符的随机或默认产生式规则。
        (此处简化为获取第一个匹配的规则)
        
        Args:
            nt (str): 非终结符名称。
            
        Returns:
            Optional[ProductionRule]: 匹配的产生式规则，若无则返回None。
        """
        if nt not in self.non_terminals:
            return None
            
        for rule in self.rules:
            if rule.lhs == nt:
                return rule
        return None

    def generate_skeleton(self, max_depth: int = 5) -> str:
        """
        核心函数1：基于CFG生成代码骨架。
        
        从起始符号开始，递归展开非终结符，直到达到最大深度或仅剩终结符。
        这是一个典型的“自上而下”生成过程。
        
        Args:
            max_depth (int): 递归展开的最大深度，防止无限递归。
            
        Returns:
            str: 生成的代码骨架字符串。
        """
        if max_depth < 1:
            logger.warning("Max depth must be at least 1.")
            return ""
            
        logger.info(f"Generating skeleton with max depth {max_depth}...")
        
        # 初始化为起始符号列表
        current_tokens = [self.start_symbol]
        
        for depth in range(max_depth):
            if not any(token in self.non_terminals for token in current_tokens):
                break
                
            new_tokens = []
            expanded = False
            for token in current_tokens:
                if token in self.non_terminals:
                    rule = self.get_rule_for_non_terminal(token)
                    if rule:
                        new_tokens.extend(rule.rhs)
                        expanded = True
                    else:
                        # 保持原样如果找不到规则
                        new_tokens.append(token)
                else:
                    new_tokens.append(token)
            
            current_tokens = new_tokens
            
            if not expanded:
                break
                
        # 清理输出，处理占位符
        result = self._post_process_tokens(current_tokens)
        logger.info("Skeleton generation complete.")
        return result

    def validate_structure(self, tokens: List[str]) -> bool:
        """
        核心函数2：验证给定的Token序列是否符合文法结构（简化版验证）。
        
        注：真正的CFG验证需要完整的解析器（如CYK或Earley算法）。
        这里实现简化逻辑：检查是否存在非法符号，并模拟简单的归约过程。
        
        Args:
            tokens (List[str]): 待验证的token列表。
            
        Returns:
            bool: 如果结构大致符合文法约束返回True，否则False。
        """
        logger.info(f"Validating structure for {len(tokens)} tokens.")
        
        # 1. 检查是否存在未定义的符号
        all_symbols = self.non_terminals.union(self.terminals)
        for token in tokens:
            # 允许字面量（假设包含在终结符定义中或被忽略）
            if token not in all_symbols and not self._is_literal(token):
                logger.error(f"Unknown symbol found: {token}")
                return False
                
        # 2. 模拟归约过程（自底向上检查）
        # 这是一个简化的检查：尝试将RHS归约为LHS
        stack = []
        buffer = list(tokens)
        
        while buffer:
            stack.append(buffer.pop(0))
            # 尝试规约栈顶
            changed = True
            while changed:
                changed = False
                # 遍历所有规则，看栈顶是否匹配RHS
                for rule in self.rules:
                    rhs_len = len(rule.rhs)
                    if len(stack) >= rhs_len:
                        top_of_stack = stack[-rhs_len:]
                        if top_of_stack == rule.rhs:
                            # 规约
                            stack = stack[:-rhs_len]
                            stack.append(rule.lhs)
                            changed = True
                            break
        
        # 最终如果栈中只剩下起始符号，则完全匹配
        # 这里放宽条件：只要不包含无法归约的非终结符即可
        if stack == [self.start_symbol]:
            logger.info("Structure validation passed (Full match).")
            return True
        else:
            # 检查是否只剩下合法的结构片段
            has_unreducible_nt = any(t in self.non_terminals for t in stack)
            if has_unreducible_nt:
                logger.warning("Structure validation failed: Unreducible non-terminals.")
                return False
            logger.info("Structure validation passed (Partial/Fuzzy match).")
            return True

    def _is_literal(self, token: str) -> bool:
        """辅助：检查是否是字面量（数字、字符串等）"""
        # 简单的正则检查
        return bool(re.match(r'^[0-9]+$', token)) or token.startswith('"')

    def _post_process_tokens(self, tokens: List[str]) -> str:
        """
        辅助函数：后处理生成的Token列表，格式化为字符串。
        """
        # 简单的拼接，实际中可能需要处理空格等
        # 将非终结符替换为占位符 <NT>
        output = []
        for t in tokens:
            if t in self.non_terminals:
                output.append(f"<{t}>")
            else:
                output.append(t)
        return " ".join(output)

# 示例使用配置（模拟Python子集的文法）
PYTHON_SUBSET_GRAMMAR = {
    "non_terminals": ["program", "stmt", "expr", "assign_stmt", "if_stmt"],
    "terminals": ["if", "else", "print", "ID", "=", ":", "NUMBER", "STRING"],
    "start_symbol": "program",
    "rules": [
        {"lhs": "program", "rhs": ["stmt"]},
        {"lhs": "stmt", "rhs": ["assign_stmt"]},
        {"lhs": "stmt", "rhs": ["if_stmt"]},
        {"lhs": "assign_stmt", "rhs": ["ID", "=", "expr"]},
        {"lhs": "if_stmt", "rhs": ["if", "expr", ":", "stmt"]},
        {"lhs": "expr", "rhs": ["ID"]},
        {"lhs": "expr", "rhs": ["NUMBER"]},
        {"lhs": "expr", "rhs": ["STRING"]}
    ]
}

if __name__ == "__main__":
    # 示例1：初始化并生成骨架
    try:
        engine = CFGConstraintEngine(PYTHON_SUBSET_GRAMMAR)
        skeleton = engine.generate_skeleton(max_depth=4)
        print(f"\nGenerated Skeleton:\n{skeleton}\n")
        
        # 示例2：验证结构
        valid_code = ["ID", "=", "NUMBER"]
        is_valid = engine.validate_structure(valid_code)
        print(f"Validation for {' '.join(valid_code)}: {is_valid}")
        
        invalid_code = ["if", "NUMBER", "NUMBER"] # 缺少冒号和stmt
        is_valid_invalid = engine.validate_structure(invalid_code)
        print(f"Validation for {' '.join(invalid_code)}: {is_valid_invalid}")

    except ValueError as e:
        logger.error(f"Initialization failed: {e}")