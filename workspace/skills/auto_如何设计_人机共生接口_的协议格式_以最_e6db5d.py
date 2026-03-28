"""
模块名称: human_machine_symbiosis_protocol
描述: 实现人机共生接口的高效协议转换，将模糊直觉反馈转化为结构化IR
作者: AGI Systems
版本: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Union, Tuple
from datetime import datetime
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanMachineProtocol")


class FeedbackType(Enum):
    """反馈类型枚举"""
    NAMING = "naming"          # 命名操作
    CORRECTION = "correction"  # 修正操作
    REJECTION = "rejection"    # 拒绝操作
    CONFIRMATION = "confirmation"  # 确认操作


class IRFormat(Enum):
    """中间表示格式"""
    JSON = "json"              # JSON格式，LLM友好
    PROLOG = "prolog"          # Prolog格式，逻辑系统友好
    HYBRID = "hybrid"          # 混合格式


@dataclass
class FuzzyNode:
    """模糊节点数据结构"""
    node_id: str
    content: str
    confidence: float
    source: str = "ai_generated"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在0-1之间，当前值: {self.confidence}")
        if not self.content.strip():
            raise ValueError("节点内容不能为空")
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StructuredNode:
    """结构化节点数据结构"""
    node_id: str
    formal_name: str
    properties: Dict[str, Any]
    relations: Dict[str, str]
    timestamp: str
    ir_representation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class HumanMachineSymbiosisProtocol:
    """
    人机共生接口协议处理器
    
    该类实现了一种高效的协议格式，能够：
    1. 接收人类对AI生成节点的非结构化反馈
    2. 瞬间将反馈固化为结构化表示
    3. 生成同时满足LLM和Prolog系统需求的IR
    
    协议设计原则：
    - 最小带宽：只传输必要信息
    - 双向兼容：同时可被LLM和形式化系统解析
    - 实时固化：人类反馈立即转化为结构化数据
    
    使用示例:
    >>> protocol = HumanMachineSymbiosisProtocol()
    >>> fuzzy_node = FuzzyNode("n001", "需要优化性能", 0.75)
    >>> feedback = "这实际上是关于内存管理的需求"
    >>> structured = protocol.process_feedback(fuzzy_node, feedback, FeedbackType.CORRECTION)
    >>> print(structured.to_dict())
    """
    
    def __init__(self, ir_format: IRFormat = IRFormat.HYBRID):
        """
        初始化协议处理器
        
        参数:
            ir_format: 中间表示格式类型
        """
        self.ir_format = ir_format
        self._feedback_history: Dict[str, StructuredNode] = {}
        logger.info(f"初始化人机共生协议处理器，IR格式: {ir_format.value}")
    
    def process_feedback(
        self,
        fuzzy_node: FuzzyNode,
        human_feedback: str,
        feedback_type: FeedbackType
    ) -> StructuredNode:
        """
        处理人类反馈并生成结构化节点
        
        参数:
            fuzzy_node: 模糊节点对象
            human_feedback: 人类的非结构化反馈文本
            feedback_type: 反馈类型枚举值
            
        返回:
            StructuredNode: 结构化节点对象
            
        异常:
            ValueError: 当输入验证失败时抛出
        """
        try:
            # 验证输入
            if not human_feedback or not human_feedback.strip():
                raise ValueError("人类反馈不能为空")
            
            logger.info(
                f"处理反馈 - 节点ID: {fuzzy_node.node_id}, "
                f"类型: {feedback_type.value}, 反馈长度: {len(human_feedback)}"
            )
            
            # 提取形式化名称和属性
            formal_name, properties = self._extract_semantic_components(
                fuzzy_node.content, human_feedback, feedback_type
            )
            
            # 生成关系映射
            relations = self._infer_relations(fuzzy_node, properties)
            
            # 生成IR表示
            ir_representation = self._generate_ir(
                fuzzy_node.node_id, formal_name, properties, relations
            )
            
            # 创建结构化节点
            structured_node = StructuredNode(
                node_id=fuzzy_node.node_id,
                formal_name=formal_name,
                properties=properties,
                relations=relations,
                timestamp=datetime.utcnow().isoformat(),
                ir_representation=ir_representation
            )
            
            # 存储到历史记录
            self._feedback_history[fuzzy_node.node_id] = structured_node
            
            logger.info(f"成功固化节点: {formal_name}")
            return structured_node
            
        except Exception as e:
            logger.error(f"处理反馈失败: {str(e)}")
            raise
    
    def _extract_semantic_components(
        self,
        original_content: str,
        human_feedback: str,
        feedback_type: FeedbackType
    ) -> Tuple[str, Dict[str, Any]]:
        """
        从反馈中提取语义组件（辅助函数）
        
        参数:
            original_content: 原始节点内容
            human_feedback: 人类反馈
            feedback_type: 反馈类型
            
        返回            formal_name: 形式化名称
            properties: 属性字典
        """
        properties = {
            "original_confidence": None,
            "feedback_type": feedback_type.value,
            "semantic_category": "unknown",
            "priority": "medium"
        }
        
        # 基于反馈类型提取语义
        if feedback_type == FeedbackType.NAMING:
            # 命名操作：提取名称
            formal_name = self._sanitize_identifier(human_feedback)
            properties["semantic_category"] = "entity"
            
        elif feedback_type == FeedbackType.CORRECTION:
            # 修正操作：提取核心概念
            keywords = self._extract_keywords(human_feedback)
            formal_name = "_".join(keywords[:3]) if keywords else "corrected_concept"
            properties["semantic_category"] = "concept"
            properties["priority"] = "high"
            
        elif feedback_type == FeedbackType.REJECTION:
            formal_name = "rejected_node"
            properties["semantic_category"] = "invalid"
            properties["priority"] = "low"
            
        else:  # CONFIRMATION
            formal_name = self._sanitize_identifier(original_content)
            properties["semantic_category"] = "confirmed"
            properties["priority"] = "high"
        
        # 添加语义标记
        properties["has_negation"] = any(
            neg in human_feedback.lower() 
            for neg in ["不", "非", "no", "not", "never"]
        )
        
        return formal_name, properties
    
    def _generate_ir(
        self,
        node_id: str,
        formal_name: str,
        properties: Dict[str, Any],
        relations: Dict[str, str]
    ) -> str:
        """
        生成中间表示语言（核心函数）
        
        生成同时满足LLM和Prolog系统需求的IR格式
        
        参数:
            node_id: 节点ID
            formal_name: 形式化名称
            properties: 属性字典
            relations: 关系字典
            
        返回:
            str: IR表示字符串
        """
        if self.ir_format == IRFormat.JSON:
            # 纯JSON格式 - LLM友好
            ir_data = {
                "node": {
                    "id": node_id,
                    "name": formal_name,
                    "properties": properties,
                    "relations": relations
                }
            }
            return json.dumps(ir_data, ensure_ascii=False, indent=2)
            
        elif self.ir_format == IRFormat.PROLOG:
            # 纯Prolog格式 - 逻辑系统友好
            prolog_facts = []
            prolog_facts.append(f"node({node_id}, {formal_name}).")
            
            for prop_key, prop_value in properties.items():
                if isinstance(prop_value, str):
                    prolog_facts.append(f"property({node_id}, {prop_key}, '{prop_value}').")
                else:
                    prolog_facts.append(f"property({node_id}, {prop_key}, {prop_value}).")
            
            for rel_type, target in relations.items():
                prolog_facts.append(f"relation({node_id}, {rel_type}, {target}).")
            
            return "\n".join(prolog_facts)
            
        else:  # HYBRID
            # 混合格式 - 最小带宽优化
            # 使用紧凑的结构同时保持可读性
            lines = [f"@NODE {node_id}::{formal_name}"]
            
            # 属性行（压缩格式）
            props_str = " ".join(
                f"{k}={v}" if not isinstance(v, str) else f'{k}="{v}"'
                for k, v in properties.items()
            )
            lines.append(f"  @PROPS {props_str}")
            
            # 关系行
            if relations:
                rels_str = " ".join(f"{k}:{v}" for k, v in relations.items())
                lines.append(f"  @RELS {rels_str}")
            
            return "\n".join(lines)
    
    def _infer_relations(
        self,
        fuzzy_node: FuzzyNode,
        properties: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        推断节点关系（核心函数）
        
        基于节点内容和属性推断可能的关系
        
        参数:
            fuzzy_node: 模糊节点
            properties: 提取的属性
            
        返回:
            Dict[str, str]: 关系字典
        """
        relations = {}
        
        # 基于语义类别推断关系
        category = properties.get("semantic_category", "unknown")
        
        if category == "entity":
            relations["instance_of"] = "concept"
        elif category == "concept":
            relations["type"] = "abstract"
        elif category == "confirmed":
            relations["status"] = "validated"
        
        # 基于置信度推断
        if fuzzy_node.confidence > 0.8:
            relations["certainty"] = "high"
        elif fuzzy_node.confidence > 0.5:
            relations["certainty"] = "medium"
        else:
            relations["certainty"] = "low"
        
        return relations
    
    def _sanitize_identifier(self, text: str) -> str:
        """清理文本以生成有效标识符"""
        # 移除特殊字符，保留字母数字和下划线
        sanitized = re.sub(r'[^\w\s]', '', text)
        # 转换为下划线分隔
        sanitized = '_'.join(sanitized.split()[:5])
        return sanitized.lower() if sanitized else "unnamed_concept"
    
    def _extract_keywords(self, text: str) -> list:
        """从文本中提取关键词"""
        # 简单的关键词提取（实际应用可使用NLP）
        stopwords = {"的", "是", "在", "和", "了", "这", "那", "the", "a", "is", "of", "and"}
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stopwords and len(w) > 1][:5]
    
    def export_history(self, format: str = "json") -> str:
        """
        导出反馈历史
        
        参数:
            format: 导出格式 (json/prolog)
            
        返回:
            str: 导出的历史数据
        """
        if format == "json":
            history = {
                node_id: node.to_dict() 
                for node_id, node in self._feedback_history.items()
            }
            return json.dumps(history, ensure_ascii=False, indent=2)
        else:
            return "\n\n".join(
                node.ir_representation 
                for node in self._feedback_history.values()
            )


# 使用示例
if __name__ == "__main__":
    # 初始化协议处理器
    protocol = HumanMachineSymbiosisProtocol(ir_format=IRFormat.HYBRID)
    
    # 示例1: 处理命名反馈
    fuzzy_node1 = FuzzyNode(
        node_id="ai_001",
        content="系统性能优化建议",
        confidence=0.72,
        metadata={"source_model": "GPT-4"}
    )
    
    structured1 = protocol.process_feedback(
        fuzzy_node1,
        "内存管理策略",
        FeedbackType.NAMING
    )
    print("=== 命名反馈结果 ===")
    print(structured1.ir_representation)
    print()
    
    # 示例2: 处理修正反馈
    fuzzy_node2 = FuzzyNode(
        node_id="ai_002",
        content="用户界面需要改进",
        confidence=0.65
    )
    
    structured2 = protocol.process_feedback(
        fuzzy_node2,
        "这不是关于UI，而是关于后端API的响应速度",
        FeedbackType.CORRECTION
    )
    print("=== 修正反馈结果 ===")
    print(structured2.ir_representation)
    print()
    
    # 导出历史
    print("=== 完整历史 ===")
    print(protocol.export_history())