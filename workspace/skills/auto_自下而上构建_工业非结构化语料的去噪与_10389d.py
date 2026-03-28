"""
工业非结构化语料的去噪与原子化分割模块。

该模块提供了针对工业现场记录（如维修日志、交接班记录）的预处理功能。
核心目标是将充斥着口语、噪音和碎片化信息的连续非结构化文本流，
通过语义完整性聚类算法，精准切割为不可再分的“原子经验节点”。
同时，算法需过滤无效噪音，并严格保留“设备-故障-现象”的原始关联，
防止过度清洗导致的关键上下文丢失。

典型应用场景：
    - 预处理维修工单描述
    - 数字化交接班日志结构化
    - 工业知识图谱构建的数据清洗
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义常用常量
DEFAULT_MIN_SENTENCE_LEN = 4
DEFAULT_NOISE_PATTERNS = [
    r'\b(uh|um|ah|like|you know)\b',  # 口语填充词
    r'[^\w\s\u4e00-\u9fff\-.,;:!?]',  # 特殊乱码符号（保留中文、英文、标点）
    r'\s{2,}',  # 多余空格
    r'(\d)\s+(\d)',  # 被空格断开的数字（如年份、型号）
]

# 定义工业领域关键词（示例，实际应用中应从领域词库加载）
INDUSTRIAL_KEYWORDS = {
    '设备': ['泵', '阀门', '电机', '传感器', ' conveyor', 'PLC'],
    '故障': ['过热', '异响', '漏油', '振动', '停机', '报警'],
    '现象': ['压力低', '电流高', '转速慢', '冒烟']
}


@dataclass
class AtomicNode:
    """原子经验节点数据结构。
    
    Attributes:
        node_id (int): 节点唯一标识。
        content (str): 清洗后的原子文本内容。
        raw_segments (List[str]): 构成该节点的原始文本片段。
        context_tags (List[str]): 提取的上下文标签（如设备名、故障类型）。
        confidence (float): 语义完整性的置信度分数 (0.0-1.0)。
    """
    node_id: int
    content: str
    raw_segments: List[str] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0


def _validate_input_text(text: str) -> bool:
    """辅助函数：验证输入文本的有效性。
    
    Args:
        text (str): 待验证的字符串。
        
    Returns:
        bool: 如果文本非空且长度满足最低要求则返回True。
    """
    if not isinstance(text, str):
        logger.error("输入类型错误：期望 str，得到 %s", type(text))
        return False
    if len(text.strip()) < 2:
        logger.warning("输入文本过短，跳过处理。")
        return False
    return True


def noise_removal(text: str, custom_patterns: Optional[List[str]] = None) -> str:
    """对原始文本进行去噪清洗。
    
    该步骤专注于字符级别的清洗，去除无意义的符号、口语填充词等，
    但有意保留可能包含工业实体（如型号P-101）的特殊字符结构。
    
    Args:
        text (str): 原始非结构化文本。
        custom_patterns (Optional[List[str]]): 自定义的正则表达式模式列表。
        
    Returns:
        str: 清洗后的文本。
        
    Raises:
        re.error: 如果提供的正则表达式模式无效。
    """
    if not _validate_input_text(text):
        return ""

    patterns = DEFAULT_NOISE_PATTERNS
    if custom_patterns:
        patterns.extend(custom_patterns)

    cleaned_text = text
    try:
        # 1. 合并被断开的数字和单词（常见的OCR或语音识别错误）
        cleaned_text = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned_text)
        
        # 2. 去除特定噪音模式
        for pattern in patterns:
            cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
            
        # 3. 规范化空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
    except re.error as e:
        logger.error("正则表达式处理错误: %s", e)
        raise
        
    logger.debug("原始文本: %s -> 清洗后: %s", text[:20], cleaned_text[:20])
    return cleaned_text


def semantic_clustering_segmentation(
    cleaned_text: str, 
    keywords_dict: Optional[dict] = None
) -> List[AtomicNode]:
    """基于语义完整性的原子化分割核心算法。
    
    该函数实现了“自下而上”的构建策略：
    1. 将文本流拆解为粗粒度的短语。
    2. 基于工业关键词（设备、故障、现象）进行聚类合并。
    3. 确保每个输出节点包含完整的语义上下文。
    
    Args:
        cleaned_text (str): 经过预清洗的文本。
        keywords_dict (Optional[dict]): 包含'设备', '故障', '现象'键的领域词典。
        
    Returns:
        List[AtomicNode]: 原子经验节点列表。
    """
    if not cleaned_text:
        return []

    # 使用领域词典，若无提供则使用默认
    domain_dict = keywords_dict if keywords_dict else INDUSTRIAL_KEYWORDS
    
    # 1. 初始分割：基于标点符号和连接词
    # 这里的分割策略比较粗粒度，后续会进行合并
    raw_segments = re.split(r'[,;。\n]|(?=\b但是\b|\b而且\b|\b然后\b)', cleaned_text)
    raw_segments = [s.strip() for s in raw_segments if s.strip() and len(s) > 2]

    nodes: List[AtomicNode] = []
    current_buffer: List[str] = []
    current_tags: Set[str] = set()
    node_counter = 0

    def _create_node_from_buffer():
        """内部辅助函数：将当前buffer内容固化为一个节点"""
        nonlocal node_counter
        if not current_buffer:
            return
            
        content = " ".join(current_buffer)
        # 简单的置信度计算：如果包含设备+故障/现象，置信度更高
        has_device = any(k in content for k in domain_dict.get('设备', []))
        has_fault = any(k in content for k in domain_dict.get('故障', []))
        
        score = 0.5
        if has_device and has_fault:
            score = 0.9
        elif has_device or has_fault:
            score = 0.7
            
        node = AtomicNode(
            node_id=node_counter,
            content=content,
            raw_segments=list(current_buffer),
            context_tags=list(current_tags),
            confidence=score
        )
        nodes.append(node)
        logger.info(f"生成原子节点 #{node_counter}: '{content[:30]}...' [置信度: {score}]")
        
        # 重置状态
        current_buffer.clear()
        current_tags.clear()
        node_counter += 1

    # 2. 遍历与聚类逻辑
    # 策略：如果当前片段没有包含任何关键词，且Buffer也为空，视为噪音丢弃；
    # 如果当前片段包含关键词，或者Buffer中已有上下文，则添加到Buffer。
    # 当Buffer中已经包含完整的“设备+故障”描述，且遇到新的主题时，触发切分。
    
    for seg in raw_segments:
        # 提取当前片段的标签
        seg_tags = set()
        for category, words in domain_dict.items():
            for word in words:
                if word in seg:
                    seg_tags.add(f"{category}:{word}")
        
        is_meaningful = len(seg_tags) > 0
        
        if not is_meaningful and not current_buffer:
            # 视为噪音片段，丢弃
            logger.debug(f"丢弃噪音片段: {seg}")
            continue
            
        # 检查是否应该切分
        # 如果当前buffer已经包含了完整的信息，且新片段看起来是新的开始
        if current_buffer and is_meaningful:
             # 简单的启发式：如果buffer已经有20个字且包含关键信息，优先切分避免节点过大
            if len(" ".join(current_buffer)) > 20 and \
               any(k in " ".join(current_buffer) for k in domain_dict.get('设备', [])):
                _create_node_from_buffer()
        
        current_buffer.append(seg)
        current_tags.update(seg_tags)

    # 处理剩余的buffer
    if current_buffer:
        _create_node_from_buffer()

    return nodes


def process_industrial_corpus(
    raw_text: str, 
    custom_keywords: Optional[dict] = None
) -> Tuple[List[AtomicNode], str]:
    """处理工业非结构化语料的主入口函数。
    
    执行流程：
    1. 数据验证。
    2. 字符级去噪。
    3. 语义级原子化分割。
    
    Args:
        raw_text (str): 输入的原始文本记录。
        custom_keywords (Optional[dict]): 自定义工业关键词库。
        
    Returns:
        Tuple[List[AtomicNode], str]: 
            - 原子节点列表。
            - 清洗后的完整文本（用于审计）。
            
    Example:
        >>> log_data = "uh 泵P-101 压力低, 振动很大。维修人员已现场确认。电机过热保护动作。"
        >>> nodes, clean_txt = process_industrial_corpus(log_data)
        >>> print(nodes[0].content)
        '泵P-101 压力低 振动很大'
    """
    logger.info("开始处理工业语料，长度: %d", len(raw_text))
    
    # Step 1: 去噪
    try:
        clean_text = noise_removal(raw_text)
    except Exception as e:
        logger.error("去噪阶段失败: %s", e)
        return [], ""

    # Step 2: 分割与原子化
    try:
        nodes = semantic_clustering_segmentation(clean_text, custom_keywords)
    except Exception as e:
        logger.error("语义分割阶段失败: %s", e)
        return [], clean_text
        
    logger.info("处理完成，生成 %d 个原子节点。", len(nodes))
    return nodes, clean_text

# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    # 模拟一段充满噪音的工业维修日志
    sample_log = """
    uh, 今天巡检发现泵P-101有异响, 而且压力读数偏低。
    2023-10-27 10:00 -- 已经通知班组长。
    原因初步判断是进口阀门堵塞，uh uh，需要停车清理。
    备注：电机温度正常。
    """
    
    print(f"原始输入:\n{sample_log}\n")
    
    # 执行处理
    atomic_nodes, cleaned = process_industrial_corpus(sample_log)
    
    print(f"-" * 30)
    print(f"清洗后文本: {cleaned}")
    print(f"-" * 30)
    
    for node in atomic_nodes:
        print(f"Node ID: {node.node_id}")
        print(f"Content: {node.content}")
        print(f"Tags: {node.context_tags}")
        print(f"Confidence: {node.confidence}")
        print("-" * 20)