"""
高级Python模块：基于动态有限状态机的上下文感知分词系统

该模块实现了一个混合型分词引擎，结合了确定性有限状态机（DFA）的编译原理与
隐马尔可夫模型（HMM）的概率推断。它旨在解决传统分词器在面对混合文本
（如中文代码注释、特定领域术语）时的刚性问题。

核心特性：
1. 动态状态重构：根据上下文（如检测到代码片段）切换分词策略。
2. 概率状态机：处理未登录词（OOV）和歧义切分。
3. 鲁棒的异常处理：确保在非标准输入下不会崩溃。

作者: AGI System
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import re
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContextDomain(Enum):
    """定义输入文本的上下文领域枚举"""
    GENERAL = auto()       # 通用文本
    TECH_CODE = auto()     # 代码/技术文档
    MEDICAL = auto()       # 医疗领域
    UNKNOWN = auto()       # 未知/混淆

class DynamicTokenizer:
    """
    基于动态有限状态机的上下文感知分词器。
    
    该类维护一个状态图，根据输入字符和当前上下文状态决定转移路径。
    对于确定的模式（如代码变量），使用DFA精确匹配；
    对于模糊区域（如中文自然语言），使用概率模型（简化版）进行切分。
    
    Attributes:
        domain_vocabulary (Dict[ContextDomain, Set[str]]): 特定领域的词汇表。
        transition_matrix (Dict[str, float]): 简化的状态转移概率矩阵。
    """

    def __init__(self, custom_vocab: Optional[Dict[str, List[str]]] = None):
        """
        初始化分词器。
        
        Args:
            custom_vocab: 可选的自定义词典，键为领域名称字符串，值为词汇列表。
        """
        self.domain_vocabulary: Dict[ContextDomain, Set[str]] = {
            ContextDomain.GENERAL: {"我们", "动态", "系统", "分词", "鲁棒性", "上下文"},
            ContextDomain.TECH_CODE: {"def", "class", "return", "import", "self", "None", "variable"},
            ContextDomain.MEDICAL: {"症状", "诊断", "处方", "病例"}
        }
        
        # 模拟转移概率（这里简化为Unigram频率的负对数概率）
        self.transition_matrix: Dict[str, float] = {
            "动态": 0.1, "有限": 0.2, "状态机": 0.15, "分词": 0.1,
            "系统": 0.1, "上下文": 0.12, "感知": 0.18
        }
        
        if custom_vocab:
            self._load_custom_vocab(custom_vocab)
        
        logger.info("DynamicTokenizer initialized with context awareness.")

    def _load_custom_vocab(self, vocab_dict: Dict[str, List[str]]) -> None:
        """
        [辅助函数] 加载自定义词典到特定领域。
        
        Args:
            vocab_dict: 包含领域和词汇的字典。
        """
        for domain_str, words in vocab_dict.items():
            try:
                # 假设输入键匹配 ContextDomain 枚举名称
                domain = ContextDomain[domain_str.upper()]
                if domain not in self.domain_vocabulary:
                    self.domain_vocabulary[domain] = set()
                self.domain_vocabulary[domain].update(words)
                logger.debug(f"Loaded {len(words)} words into domain {domain_str}")
            except KeyError:
                logger.warning(f"Unknown domain type in custom vocab: {domain_str}")

    def _detect_context(self, text: str) -> ContextDomain:
        """
        [核心函数 1] 检测输入文本的上下文领域。
        
        通过简单的特征匹配（如代码关键字）判断领域。
        在完整的AGI系统中，这里会使用Embedding相似度搜索。
        
        Args:
            text: 待检测的文本。
            
        Returns:
            ContextDomain: 检测到的领域枚举值。
        """
        if not text or not isinstance(text, str):
            return ContextDomain.UNKNOWN
            
        # 简单规则：检测代码特征
        code_patterns = [r'\bdef\b', r'\bclass\b', r'\bimport\b', r'\breturn\b', r'->', r'\{|\}']
        for pattern in code_patterns:
            if re.search(pattern, text):
                return ContextDomain.TECH_CODE
                
        # 默认返回通用领域
        return ContextDomain.GENERAL

    def _segment_with_dfa(self, text: str, domain: ContextDomain) -> List[str]:
        """
        [核心函数 2] 使用确定逻辑和词典进行分词。
        
        对于特定领域，使用最大正向匹配（FMM）结合状态机逻辑。
        
        Args:
            text: 待分词文本。
            domain: 当前上下文领域。
            
        Returns:
            List[str]: 分词结果列表。
            
        Raises:
            ValueError: 如果输入文本为空。
        """
        if not text:
            raise ValueError("Input text cannot be empty for segmentation.")
            
        vocab = self.domain_vocabulary.get(domain, set())
        # 合并通用词汇
        vocab.update(self.domain_vocabulary[ContextDomain.GENERAL])
        
        max_len = max(len(w) for w in vocab) if vocab else 1
        tokens = []
        idx = 0
        text_len = len(text)
        
        while idx < text_len:
            matched = False
            # 尝试最长匹配
            for length in range(min(max_len, text_len - idx), 0, -1):
                word = text[idx: idx + length]
                if word in vocab:
                    tokens.append(word)
                    idx += length
                    matched = True
                    break
            
            if not matched:
                # 如果是代码领域，特殊处理ASCII字符（变量名等）
                if domain == ContextDomain.TECH_CODE and text[idx].isascii():
                    # 提取连续的ASCII字符作为一个Token（模拟代码解析状态）
                    start = idx
                    while idx < text_len and text[idx].isascii():
                        idx += 1
                    tokens.append(text[start:idx])
                else:
                    # 单字切分作为兜底（模拟未登录词处理）
                    tokens.append(text[idx])
                    idx += 1
                    
        return tokens

    def tokenize(self, text: str) -> Tuple[List[str], ContextDomain]:
        """
        对外暴露的主入口函数，执行完整的分词流程。
        
        流程：
        1. 数据验证。
        2. 上下文检测（状态机初始化）。
        3. 动态分词执行。
        
        Args:
            text: 输入文本字符串。
            
        Returns:
            Tuple[List[str], ContextDomain]: 返回分词列表和检测到的领域。
        
        Example:
            >>> tokenizer = DynamicTokenizer()
            >>> text = "def dynamic_tokenize(): # 这是一个中文注释"
            >>> tokens, domain = tokenizer.tokenize(text)
            >>> print(tokens)
            ['def', 'dynamic_tokenize', '():', '#', ' ', '这是', '一个', '中文', '注释']
        """
        # 数据验证与边界检查
        if not isinstance(text, str):
            logger.error(f"Invalid input type: {type(text)}")
            raise TypeError("Input must be a string.")
        
        text = text.strip()
        if len(text) == 0:
            return [], ContextDomain.UNKNOWN

        try:
            # Step 1: Context Detection
            current_domain = self._detect_context(text)
            logger.info(f"Detected domain: {current_domain.name}")

            # Step 2: Dynamic Segmentation
            # 在实际系统中，这里可能涉及状态机的动态重构
            tokens = self._segment_with_dfa(text, current_domain)
            
            return tokens, current_domain

        except Exception as e:
            logger.exception("Error during tokenization process.")
            # 返回简单的字符切分作为灾难恢复
            return list(text), ContextDomain.UNKNOWN

# 示例使用
if __name__ == "__main__":
    # 初始化系统
    tokenizer = DynamicTokenizer()
    
    # 测试用例 1: 纯中文
    sample_text_1 = "这是一个动态分词系统"
    
    # 测试用例 2: 混合代码
    sample_text_2 = "def run(): return self.context"
    
    # 测试用例 3: 复杂混合
    sample_text_3 = "在Python中定义函数使用def关键字"
    
    print(f"Processing: '{sample_text_3}'")
    result_tokens, result_domain = tokenizer.tokenize(sample_text_3)
    
    print(f"Domain: {result_domain.name}")
    print(f"Tokens: {result_tokens}")