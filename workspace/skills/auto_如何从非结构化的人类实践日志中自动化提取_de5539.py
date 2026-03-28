"""
Module: concept_extraction_pipeline
Description: 自动化从非结构化的人类实践日志中提取新的'概念节点'。
             该模块旨在识别现有知识图谱中不存在的异常现象或新概念，
             并将其封装为待验证的候选节点。

Domain: software_engineering
Author: AGI System
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExtractionStatus(Enum):
    """提取过程的状态枚举"""
    SUCCESS = "success"
    EMPTY_INPUT = "empty_input"
    VALIDATION_ERROR = "validation_error"
    NO_NEW_CONCEPTS = "no_new_concepts"


@dataclass
class ConceptNode:
    """表示现有的概念节点"""
    id: str
    name: str
    aliases: Set[str] = field(default_factory=set)
    description: Optional[str] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("ConceptNode name cannot be empty")


@dataclass
class CandidateNode:
    """表示待验证的新节点候选"""
    proposed_name: str
    source_context: str
    confidence_score: float
    occurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


def _validate_input_data(log_text: str, existing_nodes: List[ConceptNode]) -> None:
    """
    辅助函数：验证输入数据的完整性和合法性。

    Args:
        log_text: 非结构化的日志文本。
        existing_nodes: 现有的概念节点列表。

    Raises:
        ValueError: 如果输入数据不符合要求。
        TypeError: 如果输入类型不正确。
    """
    if not isinstance(log_text, str):
        raise TypeError(f"log_text must be a string, got {type(log_text)}")
    
    if not log_text.strip():
        raise ValueError("log_text cannot be empty or whitespace only.")
    
    if not isinstance(existing_nodes, list):
        raise TypeError(f"existing_nodes must be a list, got {type(existing_nodes)}")
    
    for node in existing_nodes:
        if not isinstance(node, ConceptNode):
            raise TypeError("All items in existing_nodes must be instances of ConceptNode")


def _preprocess_log_entry(log_text: str) -> List[str]:
    """
    辅助函数：对日志文本进行预处理和分词。
    提取潜在的名词短语或技术术语（基于正则表达式的启发式方法）。

    Args:
        log_text: 原始日志文本。

    Returns:
        包含潜在术语的列表，已转换为小写。
    """
    # 简单的预处理：移除特殊字符，但保留连字符和下划线
    cleaned_text = re.sub(r'[^\w\s-]', ' ', log_text)
    
    # 提取看起来像技术术语的单词（例如：驼峰命名法、长单词）
    # 这里使用简单的正则匹配，实际生产环境可能需要NLP模型（如spaCy或BERT）
    tokens = re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', cleaned_text)
    
    # 转换为小写以进行标准化比较
    normalized_tokens = [token.lower() for token in tokens]
    
    logger.debug(f"Preprocessed {len(normalized_tokens)} tokens from log.")
    return normalized_tokens


def extract_unknown_entities(
    log_text: str,
    existing_nodes: List[ConceptNode],
    min_term_length: int = 3
) -> List[CandidateNode]:
    """
    核心函数 1：从日志中提取现有节点网络无法解释的实体/概念。
    
    该函数通过比对日志中的术语与现有节点的名称/别名，识别出“异常”
    或“未知”的术语，这些术语代表了潜在的新概念节点。

    Args:
        log_text: 人类实践日志，非结构化文本。
        existing_nodes: 当前知识库中已有的概念节点列表。
        min_term_length: 术语的最小长度，用于过滤噪音。

    Returns:
        包含候选新节点的列表。

    Raises:
        ValueError: 输入数据验证失败。
    """
    try:
        _validate_input_data(log_text, existing_nodes)
    except (ValueError, TypeError) as e:
        logger.error(f"Input validation failed: {e}")
        raise

    # 构建现有概念的查找集合（包含名称和别名）
    known_concepts: Set[str] = set()
    for node in existing_nodes:
        known_concepts.add(node.name.lower())
        known_concepts.update({alias.lower() for alias in node.aliases})
    
    logger.info(f"Known concepts loaded: {len(known_concepts)} items.")

    # 预处理日志
    tokens = _preprocess_log_entry(log_text)
    
    # 统计词频以评估重要性
    token_counts: Dict[str, int] = {}
    for token in tokens:
        if len(token) >= min_term_length:
            token_counts[token] = token_counts.get(token, 0) + 1

    # 识别未知实体
    candidates: List[CandidateNode] = []
    for term, count in token_counts.items():
        if term not in known_concepts:
            # 简单的置信度计算逻辑：基于出现频率和长度
            confidence = min(0.1 * count + 0.01 * len(term), 0.95)
            
            # 提取上下文（简化版：取包含该词的原始句子片段）
            # 在实际应用中，这里应该提取更精确的上下文窗口
            context_snippet = f"...found in log with frequency {count}..."
            
            candidate = CandidateNode(
                proposed_name=term,
                source_context=context_snippet,
                confidence_score=confidence,
                occurrence_count=count
            )
            candidates.append(candidate)

    logger.info(f"Extracted {len(candidates)} candidate nodes.")
    return candidates


def validate_and_rank_candidates(
    candidates: List[CandidateNode],
    confidence_threshold: float = 0.2
) -> List[CandidateNode]:
    """
    核心函数 2：验证并排序候选节点。
    
    过滤掉低置信度的候选，并根据置信度和出现频率对剩余候选进行排序，
    以便优先处理最有可能成为新节点的概念。

    Args:
        candidates: 待验证的候选节点列表。
        confidence_threshold: 保留候选节点的最低置信度阈值。

    Returns:
        经过筛选和排序后的候选节点列表。
    """
    if not candidates:
        logger.info("No candidates to validate.")
        return []

    # 数据验证
    if not (0.0 <= confidence_threshold <= 1.0):
        logger.warning(f"Invalid threshold {confidence_threshold}, defaulting to 0.2")
        confidence_threshold = 0.2

    # 过滤
    valid_candidates = [
        c for c in candidates 
        if c.confidence_score >= confidence_threshold
    ]

    # 排序：优先按置信度降序，其次按出现频率降序
    sorted_candidates = sorted(
        valid_candidates,
        key=lambda x: (x.confidence_score, x.occurrence_count),
        reverse=True
    )

    logger.info(
        f"Validation complete. Retained {len(sorted_candidates)} "
        f"out of {len(candidates)} candidates."
    )
    
    return sorted_candidates


# 示例用法
if __name__ == "__main__":
    # 模拟现有知识库
    existing_knowledge = [
        ConceptNode(id="c1", name="database", aliases=["db", "storage"]),
        ConceptNode(id="c2", name="api", aliases=["endpoint", "interface"]),
        ConceptNode(id="c3", name="user", aliases=["client", "actor"])
    ]

    # 模拟非结构化的人类实践日志
    # 包含已知概念和未知概念（如 "RedisCluster", "LatencySpike"）
    raw_log = """
    Today I noticed a significant LatencySpike when connecting to the database.
    The API was responding slowly. It seems the new RedisCluster configuration 
    is causing timeouts. We need to investigate the RedisCluster setup and 
    monitor for any further LatencySpike events. The user is unhappy.
    """

    try:
        # 步骤 1: 提取未知实体
        raw_candidates = extract_unknown_entities(raw_log, existing_knowledge)
        
        # 步骤 2: 验证和排序
        final_candidates = validate_and_rank_candidates(raw_candidates, confidence_threshold=0.1)

        # 输出结果
        print("\n--- Detected New Concept Candidates ---")
        for idx, cand in enumerate(final_candidates, 1):
            print(f"{idx}. Name: {cand.proposed_name}")
            print(f"   Confidence: {cand.confidence_score:.2f}")
            print(f"   Occurrences: {cand.occurrence_count}")
            print("-" * 30)

    except Exception as e:
        print(f"Error during concept extraction pipeline: {e}")