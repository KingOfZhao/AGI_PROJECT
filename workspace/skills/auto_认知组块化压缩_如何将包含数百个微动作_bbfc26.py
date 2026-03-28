"""
Module: auto_cognitive_chunking_compression
Description: 【认知组块化压缩】如何将包含数百个微动作的‘熟练工操作流’压缩为单一的‘认知组块’？
             例如，老手把‘穿针引线’视为一个动作，而新手视为10个动作。
             AI需要通过检测操作序列中的高频共现模式，自动生成高阶技能节点
             （如‘双环结’），从而降低规划系统的搜索空间，模拟人类专家的直觉。
Domain: sequence_mining
Author: AGI System
Version: 1.0.0
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Set
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionSequenceValidator:
    """
    辅助类：用于验证输入的动作序列数据是否符合预期格式。
    确保微动作流是可迭代的且包含有效数据。
    """

    @staticmethod
    def validate_sequence(sequence: List[str]) -> bool:
        """
        验证动作序列。
        
        Args:
            sequence (List[str]): 待验证的动作列表。
            
        Returns:
            bool: 如果序列有效返回 True，否则抛出 ValueError。
        """
        if not isinstance(sequence, list):
            logger.error("输入数据类型错误：期望 List[str]，得到 %s", type(sequence))
            raise ValueError("Input must be a list of strings.")
        
        if len(sequence) < 2:
            logger.warning("序列长度过短（%d），无法进行有效的模式挖掘。", len(sequence))
            return False
            
        for item in sequence:
            if not isinstance(item, str) or not item.strip():
                logger.error("序列中包含无效元素：'%s'", item)
                raise ValueError("All actions in the sequence must be non-empty strings.")
        
        logger.info("输入序列验证通过，长度: %d", len(sequence))
        return True


def extract_ngrams(sequence: List[str], n: int) -> List[Tuple[str, ...]]:
    """
    辅助函数：从序列中提取 N-grams。
    
    Args:
        sequence (List[str]): 动作序列。
        n (int): N-gram 的窗口大小。
        
    Returns:
        List[Tuple[str, ...]]: 提取出的 N-gram 元组列表。
    """
    if n <= 0:
        return []
    return [tuple(sequence[i:i + n]) for i in range(len(sequence) - n + 1)]


def identify_chunk_candidates(
    action_stream: List[str],
    min_occurrences: int = 5,
    max_chunk_size: int = 5,
    min_chunk_size: int = 2
) -> Dict[Tuple[str, ...], int]:
    """
    核心函数 1: 识别高频共现的动作模式。
    
    通过滑动窗口和频率统计，找出出现次数超过阈值的 N-gram 序列。
    这些序列被视为潜在的“认知组块”候选。
    
    Args:
        action_stream (List[str]): 原始微动作流（例如 ['hold', 'rotate', 'hold', 'rotate', ...]）。
        min_occurrences (int): 模式被视为有效的最小出现次数。
        max_chunk_size (int): 寻找模式的最大长度（模拟人类短期记忆限制）。
        min_chunk_size (int): 模式的最小长度。
        
    Returns:
        Dict[Tuple[str, ...], int]: 候选组块及其频率的字典。
    
    Raises:
        ValueError: 如果输入流为空或参数无效。
    """
    logger.info("开始识别组块候选，参数: min_occ=%d, max_size=%d", min_occurrences, max_chunk_size)
    
    # 数据验证
    if not ActionSequenceValidator.validate_sequence(action_stream):
        return {}

    if min_chunk_size > max_chunk_size:
        raise ValueError("min_chunk_size cannot be greater than max_chunk_size")

    candidate_chunks: Dict[Tuple[str, ...], int] = defaultdict(int)
    
    # 遍历不同的 N-gram 长度
    for n in range(min_chunk_size, max_chunk_size + 1):
        ngrams = extract_ngrams(action_stream, n)
        counts = Counter(ngrams)
        
        for ngram, count in counts.items():
            if count >= min_occurrences:
                candidate_chunks[ngram] = count
                logger.debug(f"发现候选组块: {ngram} (频次: {count})")

    logger.info("识别完成，共找到 %d 个候选组块。", len(candidate_chunks))
    return dict(candidate_chunks)


def compress_sequence_with_chunks(
    original_sequence: List[str],
    chunks: Dict[Tuple[str, ...], int],
    min_frequency_ratio: float = 0.01
) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    核心函数 2: 执行压缩并生成高阶技能节点。
    
    将识别出的高频模式替换为单一的“认知组块”标签（例如 'Chunk_0'）。
    这模拟了老手将“穿针引线”视为单一动作的过程，从而大幅降低序列长度。
    
    Args:
        original_sequence (List[str]): 原始动作序列。
        chunks (Dict[Tuple[str, ...], int]): 识别出的组块及其频率。
        min_frequency_ratio (float): 过滤低频组块的阈值比例。
        
    Returns:
        Tuple[List[str], Dict[str, List[str]]]: 
            - 压缩后的序列（包含新的组块标签）。
            - 组块映射表（标签 -> 原始微动作列表）。
            
    Example:
        >>> seq = ['a', 'b', 'c', 'a', 'b', 'c', 'd']
        >>> # 假设 发现了
        >>> compress_sequence_with_chunks(seq, {('a', 'b', 'c'): 2})
        (['Chunk_abc', 'Chunk_abc', 'd'], {'Chunk_abc': ['a', 'b', 'c']})
    """
    if not chunks:
        logger.warning("未提供组块字典，返回原始序列。")
        return original_sequence, {}

    # 1. 筛选并排序组块（优先匹配最长的模式，避免歧义）
    # 这里简单的按长度降序排序，实际生产环境可能需要更复杂的冲突解决机制
    sorted_chunks = sorted(
        [k for k, v in chunks.items()], 
        key=lambda x: len(x), 
        reverse=True
    )
    
    chunk_mapping: Dict[str, List[str]] = {}
    compressed_sequence = list(original_sequence) # 创建副本
    chunk_id_counter = 0
    
    logger.info("开始序列压缩，原始长度: %d", len(original_sequence))

    # 2. 迭代替换
    # 注意：简单的迭代替换可能会重叠，这里采用一种贪心策略：
    # 每次只处理找到的第一个最长匹配，将其替换，然后继续扫描。
    # 为了处理嵌套，我们可能需要多轮压缩，但此处演示单轮最长匹配替换。
    
    # 更健壮的实现方式：构建 Trie 树进行替换，这里为了代码清晰使用字符串连接技巧
    # 使用特殊分隔符确保不会错误匹配跨边界字符
    seq_str = "|".join(compressed_sequence) + "|"
    
    for pattern_tuple in sorted_chunks:
        pattern_list = list(pattern_tuple)
        pattern_str = "|".join(pattern_list) + "|"
        
        # 简单的字符串计数来确认是否存在（避免正则复杂度）
        if pattern_str in seq_str:
            # 生成新节点名称
            skill_name = f"Skill_{ '_'.join(pattern_list[:2]) }_{chunk_id_counter}"
            if len(skill_name) > 30: # 截断过长的名字
                 skill_name = f"Skill_HighLevel_{chunk_id_counter}"
            
            chunk_mapping[skill_name] = pattern_list
            
            # 执行替换
            # 注意：这种简单的字符串替换可能会替换掉重叠部分。
            # 例如 "A B C" 和 "B C D"，如果先替换了 "B C"，"A B C" 可能就断了。
            # 但在“认知组块化”中，我们通常希望抽象最显著的模式。
            # 这里保持简单的全局替换逻辑。
            
            # 重新构建序列比较安全
            # 我们重新实现一个基于索引的扫描器以避免分隔符问题
            pass
            
    # --- 更安全的基于索引的替换逻辑 ---
    i = 0
    new_sequence: List[str] = []
    used_indices = set()
    
    # 重新获取带名称的组块列表
    named_chunks = {}
    for idx, pattern in enumerate(sorted_chunks):
        # 过滤低频（如果传入了原始频率）
        # 在这个函数中我们假设传入的 chunks 都是有效的
        name = f"Skill_{idx}_{'_'.join(pattern)}"
        if len(name) > 20: name = f"Skill_Complex_{idx}"
        named_chunks[pattern] = name
        chunk_mapping[name] = list(pattern)

    while i < len(original_sequence):
        matched = False
        # 尝试匹配最长的可能组块
        for pattern in sorted_chunks:
            chunk_len = len(pattern)
            # 检查边界和内容匹配
            if i + chunk_len <= len(original_sequence):
                sub_sequence = tuple(original_sequence[i : i + chunk_len])
                if sub_sequence == pattern:
                    # 命中组块
                    chunk_name = named_chunks[pattern]
                    new_sequence.append(chunk_name)
                    logger.debug(f"在索引 {i} 处匹配组块: {chunk_name}")
                    i += chunk_len
                    matched = True
                    break
        
        if not matched:
            # 没有匹配到组块，保留原始微动作
            new_sequence.append(original_sequence[i])
            i += 1

    logger.info("压缩完成。原始长度: %d, 压缩后长度: %d, 压缩率: %.2f%%",
                len(original_sequence), len(new_sequence),
                (1 - len(new_sequence)/len(original_sequence)) * 100)
                
    return new_sequence, chunk_mapping


def demo_skill_usage():
    """
    使用示例：展示如何将微动作流压缩为认知组块。
    """
    # 模拟一个熟练工的操作流：包含重复的复杂动作（如双环结、穿针）
    # 'grip', 'rotate', 'hold' 可能代表 "DoubleLoop"
    # 'aim', 'insert' 可能代表 "ThreadNeedle"
    raw_stream = [
        'grip', 'rotate', 'hold',    # 模式 1 开始
        'aim', 'insert',             # 模式 2 开始
        'grip', 'rotate', 'hold',    # 模式 1
        'grip', 'rotate', 'hold',    # 模式 1
        'pull', 'tighten',           # 随机微动作
        'aim', 'insert',             # 模式 2
        'aim', 'insert',             # 模式 2
        'grip', 'rotate', 'hold',    # 模式 1
        'cut'
    ] * 10 # 重复以增加频率

    logger.info("--- 启动认知组块化系统 ---")
    
    try:
        # 1. 挖掘高频模式
        candidates = identify_chunk_candidates(
            action_stream=raw_stream,
            min_occurrences=5,
            max_chunk_size=4
        )
        
        if not candidates:
            logger.warning("未发现显著的高频模式。")
            return

        print(f"\n发现的高频模式: {json.dumps({str(k): v for k, v in candidates.items()}, indent=2)}")

        # 2. 压缩序列
        compressed_stream, skill_map = compress_sequence_with_chunks(
            original_sequence=raw_stream,
            chunks=candidates
        )
        
        print(f"\n生成的技能映射表: {json.dumps(skill_map, indent=2)}")
        print(f"\n压缩后序列片段: {compressed_stream[:15]}...")
        
    except ValueError as ve:
        logger.error(f"数据处理错误: {ve}")
    except Exception as e:
        logger.error(f"系统运行时错误: {e}", exc_info=True)

if __name__ == "__main__":
    demo_skill_usage()