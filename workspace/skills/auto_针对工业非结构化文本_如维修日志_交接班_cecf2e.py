"""
工业非结构化文本认知自洽语义解析器

该模块实现了一个针对工业领域非结构化文本（如维修日志、交接班记录）的语义解析器。
其核心目标是验证“语言混乱但逻辑闭环”的经验是否能被现有知识图谱节点通过
“自下而上归纳”所同化。

核心概念：
1. 认知自洽: 即使语法混乱，只要文本中的实体关系逻辑闭环，即视为有效信息。
2. 真实节点: 从文本中提取的、能够映射到现有工业知识库的有效实体或概念。
3. 自下而上归纳: 将碎片化的日志信息聚合，试图匹配或扩展现有的2978个基础节点。

Author: AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialCognitiveParser")

class NodeType(Enum):
    """定义工业知识图谱中的节点类型"""
    DEVICE = "device"           # 设备
    SYMPTOM = "symptom"         # 故障现象
    ACTION = "action"           # 维修动作
    SPARE_PART = "spare_part"   # 备件
    STATE = "state"             # 状态
    UNKNOWN = "unknown"         # 未知节点

@dataclass
class KnowledgeNode:
    """知识图谱节点定义"""
    id: str
    name: str
    type: NodeType
    aliases: Set[str] = field(default_factory=set)
    connections: Set[str] = field(default_factory=set)

@dataclass
class SemanticFragment:
    """语义碎片：从非结构化文本中提取的原始片段"""
    raw_text: str
    source_type: str  # e.g., 'repair_log', 'shift_handover'
    timestamp: Optional[str] = None

@dataclass
class CognitiveResult:
    """认知解析结果"""
    is_self_consistent: bool
    extracted_nodes: List[KnowledgeNode]
    confidence: float
    reasoning_path: List[str]
    raw_text: str

class IndustrialKnowledgeBase:
    """
    模拟工业知识库（模拟包含2978个节点的系统）
    实际生产环境中应连接图数据库（如Neo4j）
    """
    def __init__(self):
        # 这里仅作演示，初始化部分硬编码节点
        self.nodes: Dict[str, KnowledgeNode] = {}
        self._initialize_mock_nodes()

    def _initialize_mock_nodes(self):
        """初始化模拟节点数据"""
        mock_data = [
            ("DEV_001", "泵P101", NodeType.DEVICE, {"P101", "1号泵", "给水泵"}),
            ("DEV_002", "阀门V302", NodeType.DEVICE, {"V302", "进水阀"}),
            ("SYP_001", "振动过大", NodeType.SYMPTOM, {"震动", "抖动", "异常响动"}),
            ("ACT_001", "紧固螺栓", NodeType.ACTION, {"拧紧", "加固"}),
            ("ACT_002", "更换密封圈", NodeType.ACTION, {"换密封", "换垫片"}),
            ("STA_001", "停机", NodeType.STATE, {"停机", "停运"}),
            ("SPA_001", "密封圈", NodeType.SPARE_PART, {"垫片", "O型圈"}),
        ]
        
        for nid, name, ntype, aliases in mock_data:
            self.nodes[nid] = KnowledgeNode(
                id=nid, name=name, type=ntype, aliases=aliases
            )
        logger.info(f"Knowledge base initialized with {len(self.nodes)} nodes (Mock of 2978).")

    def get_node_count(self) -> int:
        return len(self.nodes)

class CognitiveSemanticParser:
    """
    认知自洽语义解析器
    
    用于处理工业现场产生的非结构化文本，通过语义碎片提取和逻辑闭环验证，
    实现知识的自下而上归纳。
    """

    def __init__(self, knowledge_base: IndustrialKnowledgeBase):
        self.kb = knowledge_base
        # 定义一些简单的启发式规则用于解析“语法混乱”的文本
        self._action_patterns = [
            re.compile(r'(更换|紧固|检查|启动|停止)([a-zA-Z0-9\u4e00-\u9fa5]+)'),
            re.compile(r'([a-zA-Z0-9\u4e00-\u9fa5]+)(松动|泄漏|发热)')
        ]
        logger.info("CognitiveSemanticParser initialized.")

    def _clean_text(self, text: str) -> str:
        """
        辅助函数：文本预处理
        清理工业文本中常见的噪点（如不规则标点、多余空格）。
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 统一中文标点
        text = text.replace('，', ',').replace('。', '.')
        # 去除特殊控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # 压缩多余空格
        return re.sub(r'\s+', ' ', text).strip()

    def _map_to_node(self, entity_text: str) -> Optional[KnowledgeNode]:
        """
        核心函数：将提取的文本实体映射到知识库节点
        
        Args:
            entity_text: 从日志中提取的实体片段
            
        Returns:
            匹配到的KnowledgeNode或None
        """
        if not entity_text:
            return None
            
        # 简单的字符串匹配与别名匹配
        for node in self.kb.nodes.values():
            if node.name == entity_text or entity_text in node.aliases:
                return node
        
        # 如果未匹配，尝试模糊匹配（此处省略复杂的模糊匹配逻辑）
        return None

    def parse_fragment(self, fragment: SemanticFragment) -> CognitiveResult:
        """
        核心函数：解析语义碎片并验证认知自洽性
        
        此函数尝试从混乱的文本中提取实体，并构建一个临时的逻辑图。
        如果逻辑图闭环（如：设备->故障->动作->备件），则认为认知自洽。
        
        Args:
            fragment: 包含原始文本和元数据的语义碎片
            
        Returns:
            CognitiveResult: 包含解析结果、置信度和推理路径的对象
            
        Raises:
            ValueError: 如果输入文本为空
        """
        raw_text = self._clean_text(fragment.raw_text)
        if not raw_text:
            raise ValueError("Input text cannot be empty after cleaning")

        logger.debug(f"Parsing text: {raw_text}")
        
        extracted_nodes: List[KnowledgeNode] = []
        reasoning_path: List[str] = []
        detected_types: Set[NodeType] = set()
        
        # 1. 实体提取 (模拟NLP分词或正则提取)
        # 这里使用简单的滑动窗口或关键词匹配模拟
        tokens = re.split(r'[,\s\.]+', raw_text)
        
        for token in tokens:
            node = self._map_to_node(token)
            if node:
                extracted_nodes.append(node)
                detected_types.add(node.type)
                reasoning_path.append(f"Found node: {node.name} ({node.type.value})")

        # 2. 认知自洽性校验
        # 工业逻辑闭环规则：必须包含 [设备] + [状态/现象] -> 视为有效上下文
        # 或者 [动作] + [备件] -> 视为有效维修记录
        
        is_consistent = False
        confidence = 0.0
        
        has_device = NodeType.DEVICE in detected_types
        has_symptom = NodeType.SYMPTOM in detected_types
        has_action = NodeType.ACTION in detected_types
        has_part = NodeType.SPARE_PART in detected_types
        
        # 逻辑闭环判定
        if has_device and has_symptom:
            reasoning_path.append("Logic check: Device + Symptom detected (Fault Context).")
            confidence = 0.7
            is_consistent = True
            
        if has_action and has_part:
            reasoning_path.append("Logic check: Action + Part detected (Repair Context).")
            confidence = max(confidence, 0.8)
            is_consistent = True
            
        if has_device and has_action:
            reasoning_path.append("Logic check: Device + Action detected (Maintenance Context).")
            confidence = max(confidence, 0.6)
            is_consistent = True

        # 如果逻辑不自洽，但提取到了节点，降低置信度
        if not is_consistent and extracted_nodes:
            reasoning_path.append("Logic check: Nodes found but logic loop is incomplete.")
            confidence = 0.3
            # 即使逻辑不完全闭环，也允许通过，但标记为低置信度，等待人工确认或后续归纳
            
        return CognitiveResult(
            is_self_consistent=is_consistent,
            extracted_nodes=list(set(extracted_nodes)), # 去重
            confidence=confidence,
            reasoning_path=reasoning_path,
            raw_text=fragment.raw_text
        )

    def induct_new_node(self, result: CognitiveResult) -> bool:
        """
        辅助函数：自下而上归纳
        
        如果提取的信息无法完全匹配现有节点，但逻辑自洽，
        尝试将高频碎片作为“候选节点”进行归纳。
        
        Args:
            result: 解析结果
            
        Returns:
            bool: 是否触发了新的归纳过程
        """
        if result.confidence > 0.5 and not result.is_self_consistent:
            logger.info(f"Triggering bottom-up induction for ambiguous text: {result.raw_text}")
            # 这里应触发外部系统进行新节点的创建流程
            return True
        return False

# 使用示例
if __name__ == "__main__":
    # 初始化知识库
    kb = IndustrialKnowledgeBase()
    parser = CognitiveSemanticParser(kb)
    
    # 模拟工业非结构化输入（包含语法混乱、简写）
    log_entries = [
        "P101 振动过大，停机检查",  # 标准清晰
        "V302 泄漏，换密封",         # 稍微简写
        "1号泵 抖动，紧固螺栓",      # 使用别名
        "天气不错，无维修",          # 无关节点
        "设备异常，但不知道是哪",    # 逻辑不自洽
    ]
    
    print("-" * 50)
    print(f"{'Raw Text':<20} | {'Consistent':<10} | {'Confidence':<10} | {'Extracted Nodes'}")
    print("-" * 50)
    
    for entry in log_entries:
        fragment = SemanticFragment(raw_text=entry, source_type="repair_log")
        try:
            result = parser.parse_fragment(fragment)
            nodes_str = ", ".join([n.name for n in result.extracted_nodes])
            print(f"{entry:<20} | {str(result.is_self_consistent):<10} | {result.confidence:<10.2f} | {nodes_str}")
            
            # 尝试归纳
            parser.induct_new_node(result)
            
        except ValueError as e:
            logger.error(f"Error processing '{entry}': {e}")

    print("-" * 50)