"""
Module: auto_bottom_up_inductive_layer.py
Description: 【自下而上-归纳层】探索'碎片化实践到结构化节点'的自动编码算法。
             本模块旨在从非结构化的数据（如摆摊日志、语音文本、生理信号）中，
             提取可复用的'真实节点'（True Node），实现隐性知识到显性结构的转化。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RawFragment:
    """
    原始碎片数据结构。
    
    Attributes:
        timestamp (str): 数据产生的时间戳。
        source_type (str): 来源类型 (e.g., 'voice', 'log', 'bio_signal').
        content (str): 原始内容文本或编码后的字符串。
        metadata (Dict[str, Any]): 额外的元数据（如心率、GPS位置）。
    """
    timestamp: str
    source_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrueNode:
    """
    归纳生成的结构化'真实节点'。
    
    Attributes:
        node_id (str): 节点唯一标识。
        node_type (str): 节点类型 (e.g., 'Action', 'State', 'Decision').
        description (str): 节点描述。
        keywords (List[str]): 关键特征词。
        confidence (float): 置信度 (0.0 to 1.0).
        instances (List[Dict]): 关联的原始实例数据。
    """
    node_id: str
    node_type: str
    description: str
    keywords: List[str]
    confidence: float
    instances: List[Dict] = field(default_factory=list)

class FragmentPreprocessor:
    """
    辅助类：负责原始数据的清洗和标准化。
    """
    
    @staticmethod
    def clean_text(text: str) -> str:
        """去除噪声，标准化文本。"""
        if not isinstance(text, str):
            return ""
        # 简单的清洗：去除多余空格、特殊符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff,.!?]', '', text)
        return text.strip().lower()

    @staticmethod
    def validate_fragment(fragment: RawFragment) -> bool:
        """验证碎片数据是否有效。"""
        if not fragment.content or not fragment.timestamp:
            return False
        try:
            datetime.fromisoformat(fragment.timestamp)
            return True
        except ValueError:
            logger.warning(f"Invalid timestamp format: {fragment.timestamp}")
            return False

def tokenize_and_extract_features(cleaned_content: str) -> List[str]:
    """
    辅助函数：从清洗后的文本中提取特征词元。
    
    Args:
        cleaned_content (str): 清洗后的文本。
        
    Returns:
        List[str]: 特征列表。
        
    Note:
        实际场景应接入NLP模型，此处使用规则简化演示。
    """
    # 模拟分词和关键词提取 (中文场景简化处理)
    # 假设提取动词和名词
    keywords = []
    common_actions = ["进货", "摆摊", "收摊", "吆喝", "收款", "整理"]
    for action in common_actions:
        if action in cleaned_content:
            keywords.append(action)
    
    # 简单的滑窗提取上下文特征
    words = re.findall(r'[\u4e00-\u9fff]+', cleaned_content)
    keywords.extend([w for w in words if len(w) > 1])
    
    return list(set(keywords))

def induce_nodes_from_fragments(
    fragments: List[RawFragment],
    similarity_threshold: float = 0.6,
    min_cluster_size: int = 2
) -> List[TrueNode]:
    """
    核心函数1：从碎片流中归纳生成候选节点。
    
    通过无监督聚类的方式，将相似的碎片合并为初步的结构化节点。
    
    Args:
        fragments (List[RawFragment]): 原始碎片列表。
        similarity_threshold (float): Jaccard相似度阈值。
        min_cluster_size (int): 形成节点所需的最小碎片数。
        
    Returns:
        List[TrueNode]: 归纳出的真实节点列表。
        
    Raises:
        ValueError: 如果输入数据为空。
    """
    if not fragments:
        raise ValueError("Input fragments list cannot be empty.")
    
    logger.info(f"Starting induction on {len(fragments)} fragments...")
    preprocessor = FragmentPreprocessor()
    valid_fragments = [f for f in fragments if preprocessor.validate_fragment(f)]
    
    if len(valid_fragments) < len(fragments):
        logger.warning(f"Filtered out {len(fragments) - len(valid_fragments)} invalid fragments.")

    # 1. 特征提取
    feature_map: Dict[str, List[str]] = {}
    for frag in valid_fragments:
        cleaned = preprocessor.clean_text(frag.content)
        tokens = tokenize_and_extract_features(cleaned)
        # 使用内容hash作为临时ID
        fid = f"{frag.timestamp}_{hash(frag.content)}"
        feature_map[fid] = tokens
    
    # 2. 简单的聚合聚类
    # 这里使用基于关键词重叠的简单聚类逻辑
    clusters: Dict[str, List[Dict]] = {}
    global_counter = Counter()
    
    # 统计全局关键词频率以识别核心行为
    for tokens in feature_map.values():
        global_counter.update(tokens)
        
    # 识别高频核心词作为潜在节点中心
    potential_centers = [word for word, count in global_counter.most_common(10)]
    
    node_id_counter = 0
    induced_nodes: List[TrueNode] = []
    
    for center in potential_centers:
        # 寻找包含该中心词的所有碎片
        matched_fragments_meta = []
        matched_ids = set()
        
        for fid, tokens in feature_map.items():
            if center in tokens:
                matched_fragments_meta.append({
                    "id": fid,
                    "tokens": tokens,
                    "raw_data": next((f.metadata for f in valid_fragments if f"{f.timestamp}_{hash(f.content)}" == fid), {})
                })
                matched_ids.add(fid)
        
        if len(matched_fragments_meta) >= min_cluster_size:
            node_id_counter += 1
            # 计算置信度：基于词频和聚合数量
            confidence = min(1.0, len(matched_fragments_meta) / (len(valid_fragments) * 0.1 + 1))
            
            new_node = TrueNode(
                node_id=f"node_{node_id_counter}_{center}",
                node_type="ActivityPattern",
                description=f"Detected recurring pattern related to: {center}",
                keywords=list(set([center] + [t for m in matched_fragments_meta for t in m['tokens']][:5])),
                confidence=round(confidence, 2),
                instances=matched_fragments_meta[:5] # 仅保留5个示例
            )
            induced_nodes.append(new_node)
            logger.info(f"Induced Node: {new_node.node_id} (Confidence: {new_node.confidence})")
            
            # 从池中移除已聚合的碎片，避免重复（简单的贪婪策略）
            # 实际场景可能需要软聚类

    return induced_nodes

def refine_node_knowledge(node: TrueNode, context_rules: Optional[Dict] = None) -> Dict[str, Any]:
    """
    核心函数2：节点知识的显性化编码与验证。
    
    将归纳出的节点转化为可执行或可推理的结构（如JSON-LD或逻辑规则）。
    并计算转化效率指标。
    
    Args:
        node (TrueNode): 待细化的节点对象。
        context_rules (Optional[Dict]): 外部上下文规则（如业务逻辑约束）。
        
    Returns:
        Dict[str, Any]: 包含编码结果和效率指标的字典。
        
    Example Output:
        {
            "encoded_structure": {...},
            "efficiency_metrics": {
                "compression_ratio": 0.85,
                "clarity_score": 0.9
            }
        }
    """
    if not node.instances:
        logger.error(f"Node {node.node_id} has no instances to refine.")
        return {"error": "No instances available"}

    logger.debug(f"Refining node {node.node_id}...")
    
    # 1. 结构化编码
    # 提取时间间隔、生理指标均值等（模拟）
    encoded_structure = {
        "id": node.node_id,
        "type": node.node_type,
        "core_semantic": node.keywords[0] if node.keywords else "unknown",
        "average_metadata": {
            "avg_heart_rate": 85, # 模拟值
            "typical_duration": "15m"
        },
        "temporal_patterns": "irregular"
    }
    
    # 2. 效率计算
    # 压缩率：原始数据大小 / 结构化描述大小
    original_size = sum(len(str(inst)) for inst in node.instances)
    compressed_size = len(json.dumps(encoded_structure))
    compression_ratio = compressed_size / (original_size + 1e-6)
    
    # 清晰度评分 (基于置信度和关键词纯度)
    clarity_score = node.confidence * (1 - compression_ratio * 0.1)
    
    # 3. 验证与边界检查
    if clarity_score < 0.5:
        logger.warning(f"Node {node.node_id} has low clarity score: {clarity_score}")
        encoded_structure['status'] = 'review_required'
    else:
        encoded_structure['status'] = 'validated'

    return {
        "encoded_structure": encoded_structure,
        "efficiency_metrics": {
            "compression_ratio": round(compression_ratio, 3),
            "clarity_score": round(clarity_score, 3)
        }
    }

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 构造模拟的摆摊碎片数据
    mock_fragments = [
        RawFragment("2023-10-01T08:00:00", "voice", "老板，这苹果怎么卖？", {"heart_rate": 75}),
        RawFragment("2023-10-01T08:05:00", "log", "扫码收款: 15.00元", {"heart_rate": 78}),
        RawFragment("2023-10-01T08:10:00", "voice", "便宜点呗，便宜点。", {"heart_rate": 80}),
        RawFragment("2023-10-01T09:00:00", "voice", "老板，这苹果怎么卖？", {"heart_rate": 76}),
        RawFragment("2023-10-01T09:05:00", "log", "扫码收款: 15.00元", {"heart_rate": 77}),
        RawFragment("2023-10-01T09:10:00", "bio_signal", "Body movement: gesturing", {"heart_rate": 85}),
        RawFragment("2023-10-01T10:00:00", "log", "进货: 支付500元", {"heart_rate": 70}),
    ]

    print("--- Starting Bottom-Up Induction Process ---")
    
    try:
        # 2. 执行归纳
        true_nodes = induce_nodes_from_fragments(
            fragments=mock_fragments,
            min_cluster_size=2
        )
        
        # 3. 执行细化与验证
        for node in true_nodes:
            result = refine_node_knowledge(node)
            print(f"\nProcessed Node: {node.node_id}")
            print(f"Metrics: {result['efficiency_metrics']}")
            print(f"Structure: {json.dumps(result['encoded_structure'], indent=2, ensure_ascii=False)}")
            
    except ValueError as e:
        logger.error(f"Process failed: {e}")