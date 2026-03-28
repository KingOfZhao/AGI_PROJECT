"""
名称: auto_人机共生中的_概念结晶_提取器_当人类在_1cefec
描述: 人机共生中的'概念结晶'提取器。当人类在实践过程中产生大量非结构化数据
      （如聊天记录、代码提交记录、操作日志）时，AI如何从中识别出重复出现的模式，
      并将其'命名'为一个新概念（节点）？这涉及到从隐性行为到显性符号的转换。
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConceptCrystallizer")

@dataclass
class UnstructuredData:
    """
    输入数据结构。
    
    Attributes:
        content (str): 原始文本内容（如单条聊天记录、一行日志）。
        source_type (str): 来源类型 (e.g., 'chat', 'log', 'commit').
        timestamp (int): 时间戳。
    """
    content: str
    source_type: str
    timestamp: int

@dataclass
class ConceptNode:
    """
    提取出的概念结晶结构。
    
    Attributes:
        concept_id (str): 概念的唯一标识符。
        name (str): 概念的名称（显性符号）。
        pattern_regex (str): 匹配该概念的正则表达式。
        frequency (int): 该模式在数据中出现的频率。
        source_ids (List[str]): 关联的原始数据ID列表。
        description (str): AI生成的概念描述。
    """
    concept_id: str
    name: str
    pattern_regex: str
    frequency: int
    source_ids: List[str] = field(default_factory=list)
    description: str = ""

class ConceptCrystallizer:
    """
    人机共生中的概念结晶提取器。
    
    负责从非结构化的人机交互数据中挖掘潜在模式，并将其转化为显性的概念节点。
    """

    def __init__(self, min_frequency_threshold: int = 3, ngram_range: Tuple[int, int] = (2, 4)):
        """
        初始化提取器。

        Args:
            min_frequency_threshold (int): 模式被视为概念的最低出现次数。
            ngram_range (tuple): 提取N-Gram模式的范围。
        """
        if min_frequency_threshold < 1:
            raise ValueError("min_frequency_threshold must be at least 1")
        self.min_freq = min_frequency_threshold
        self.ngram_range = ngram_range
        logger.info(f"ConceptCrystallizer initialized with threshold: {self.min_freq}")

    def _preprocess_text(self, text: str) -> List[str]:
        """
        [辅助函数] 文本预处理与分词。
        
        Args:
            text (str): 原始文本。
            
        Returns:
            List[str]: 清洗后的Token列表。
        """
        # 简单的清洗：转小写，去除特殊字符（保留基本标点用于结构分析）
        text = text.lower()
        text = re.sub(r'[^\w\s\-_\.\?]', '', text)
        tokens = text.split()
        return tokens

    def _generate_ngrams(self, tokens: List[str]) -> List[str]:
        """
        生成N-grams列表。
        """
        ngrams = []
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i:i+n])
                ngrams.append(phrase)
        return ngrams

    def extract_patterns(self, data_stream: List[UnstructuredData]) -> List[ConceptNode]:
        """
        [核心函数 1] 从数据流中提取高频模式。
        
        Args:
            data_stream (List[UnstructuredData]): 非结构化数据列表。
            
        Returns:
            List[ConceptNode]: 识别出的概念节点列表（尚未命名，仅有模式）。
        
        Raises:
            ValueError: 如果输入数据为空。
        """
        if not data_stream:
            logger.warning("Input data stream is empty.")
            return []

        logger.info(f"Starting pattern extraction on {len(data_stream)} records.")
        pattern_counter = Counter()
        pattern_sources: Dict[str, List[str]] = {} # pattern -> list of data content (for demo, using content as ID)

        # 1. 模式挖掘
        for item in data_stream:
            if not item.content or not item.content.strip():
                continue
            
            tokens = self._preprocess_text(item.content)
            ngrams = self._generate_ngrams(tokens)
            
            for gram in ngrams:
                pattern_counter[gram] += 1
                if gram not in pattern_sources:
                    pattern_sources[gram] = []
                # 简单去重，避免同一条记录重复计数同一个模式
                if item.content not in pattern_sources[gram]:
                    pattern_sources[gram].append(item.content)

        # 2. 筛选与结晶
        crystallized_concepts = []
        concept_idx = 0

        for pattern, freq in pattern_counter.most_common():
            if freq >= self.min_freq:
                # 过滤掉过于通用的停用词组合（简单规则检查）
                if self._is_valid_concept(pattern):
                    concept_idx += 1
                    # 生成正则表达式：将空格转义为通用分隔符
                    regex_pattern = re.escape(pattern).replace(r'\ ', r'[\s]+')
                    
                    node = ConceptNode(
                        concept_id=f"concept_{concept_idx}",
                        name=f"Unnamed_Pattern_{concept_idx}", # 待后续命名
                        pattern_regex=regex_pattern,
                        frequency=freq,
                        source_ids=pattern_sources[pattern][:5] # 仅保留前5个样例
                    )
                    crystallized_concepts.append(node)
        
        logger.info(f"Extraction complete. Found {len(crystallized_concepts)} potential concepts.")
        return crystallized_concepts

    def _is_valid_concept(self, pattern: str) -> bool:
        """
        [辅助函数] 简单验证模式是否具有足够的信息熵，排除简单的停用词组合。
        """
        # 示例规则：长度太短或全是单个字符
        if len(pattern) < 4:
            return False
        # 实际场景应加载停用词表
        return True

    def name_and_formalize(self, concepts: List[ConceptNode], context_hint: Optional[str] = None) -> List[ConceptNode]:
        """
        [核心函数 2] 对识别出的模式进行命名和形式化。
        
        模拟AI对概念的理解和命名过程。
        
        Args:
            concepts (List[ConceptNode]): 待命名的概念列表。
            context_hint (Optional[str]): 上下文提示（如项目类型），辅助命名。
            
        Returns:
            List[ConceptNode]: 已完成命名的概念列表。
        """
        logger.info("Starting concept naming and formalization...")
        formalized_concepts = []

        for concept in concepts:
            # 模拟AI命名逻辑：这里使用简单的规则替代LLM生成
            # 在真实AGI场景中，这里会调用LLM生成名称和描述
            sample_text = concept.source_ids[0] if concept.source_ids else ""
            
            # 自动生成名称逻辑 (模拟)
            generated_name = self._generate_synthetic_name(concept.pattern_regex, sample_text)
            
            concept.name = generated_name
            concept.description = f"Detected recurring pattern: '{concept.pattern_regex}' occurring {concept.frequency} times. Context hint: {context_hint}"
            
            formalized_concepts.append(concept)
            
        return formalized_concepts

    def _generate_synthetic_name(self, pattern: str, sample: str) -> str:
        """简单的命名生成器逻辑"""
        # 提取前两个单词作为标签
        clean_name = pattern.replace(r'[\s]+', ' ').replace(r'\', '')
        words = clean_name.split()
        if len(words) > 2:
            return f"Concept::{words[0].capitalize()}_{words[1].capitalize()}"
        return f"Concept::{clean_name.capitalize()}"

# 使用示例
if __name__ == "__main__":
    # 1. 模拟输入数据 (人机交互日志)
    raw_logs = [
        UnstructuredData("User requested system status check", "log", 1000),
        UnstructuredData("System status check initiated", "log", 1001),
        UnstructuredData("User requested system status check", "log", 1002),
        UnstructuredData("Error: Connection timeout", "log", 1005),
        UnstructuredData("User requested data export", "log", 1010),
        UnstructuredData("System status check initiated", "log", 1011),
        UnstructuredData("User requested system status check", "log", 1012),
        UnstructuredData("User requested data export", "log", 1013),
        UnstructuredData("User requested data export", "log", 1014),
        UnstructuredData("User requested system status check", "log", 1015),
    ]

    # 2. 初始化提取器
    extractor = ConceptCrystallizer(min_frequency_threshold=3, ngram_range=(3, 5))

    # 3. 提取模式
    potential_concepts = extractor.extract_patterns(raw_logs)

    # 4. 命名与形式化
    final_concepts = extractor.name_and_formalize(potential_concepts, context_hint="DevOps Logs")

    # 5. 输出结果
    print("-" * 30)
    print("Extracted Concept Crystals:")
    print("-" * 30)
    for c in final_concepts:
        print(f"ID: {c.concept_id}")
        print(f"Name: {c.name}")
        print(f"Regex: {c.pattern_regex}")
        print(f"Freq: {c.frequency}")
        print(f"Examples: {c.source_ids}")
        print("-" * 10)