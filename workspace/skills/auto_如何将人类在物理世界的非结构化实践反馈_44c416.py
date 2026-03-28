"""
模块名称: auto_how_to_map_human_feedback_to_graph_44c416
描述: 实现将人类非结构化反馈（语音、视频、随笔）转化为结构化计算图的系统。
      解决跨模态对齐问题，将模糊的“手感”映射为精确的逻辑节点与权重。
"""

import logging
import re
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackModality(Enum):
    """反馈模态枚举"""
    SPEECH = "speech"
    VIDEO = "video"
    TEXT = "text"
    SENSOR = "sensor"  # 例如力反馈数据


class NodeType(Enum):
    """计算图节点类型"""
    PERCEPTION = "perception"
    ACTION = "action"
    DECISION = "decision"
    CONTROL = "control"
    MEMORY = "memory"


@dataclass
class UnstructuredFeedback:
    """非结构化反馈数据结构"""
    modality: FeedbackModality
    raw_data: Any  # 原始数据（文本、音频路径、视频帧等）
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    timestamp: float = 0.0
    confidence: float = 1.0  # 数据质量置信度 [0.0, 1.0]

    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("置信度必须在[0.0, 1.0]范围内")


@dataclass
class ComputeNode:
    """计算图节点"""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.ACTION
    semantic_label: str = ""  # 人类可读的语义标签（如："轻轻抓取"）
    parameters: Dict[str, Any] = field(default_factory=dict)  # 节点参数
    connections: List[str] = field(default_factory=list)  # 连接的节点ID列表
    source_feedback_id: Optional[str] = None  # 来源反馈ID

    def to_dict(self) -> Dict:
        """将节点转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "semantic_label": self.semantic_label,
            "parameters": self.parameters,
            "connections": self.connections,
            "source_feedback_id": self.source_feedback_id
        }


class FeedbackToGraphConverter:
    """
    将非结构化人类反馈转化为结构化计算图的转换器。
    
    核心流程：
    1. 模态特征提取
    2. 语义解析与结构化
    3. 计算图生成与优化
    4. 权重与参数映射
    
    使用示例:
        >>> converter = FeedbackToGraphConverter()
        >>> text_feedback = UnstructuredFeedback(
        ...     modality=FeedbackModality.TEXT,
        ...     raw_data="如果物体较重，应该缓慢且稳定地抓取",
        ...     context={"task": "grasping"}
        ... )
        >>> graph = converter.convert(text_feedback)
        >>> print(f"生成图包含 {len(graph)} 个节点")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化转换器
        
        Args:
            config: 配置字典，可包含以下键:
                - min_confidence: 最小置信度阈值 (默认: 0.5)
                - max_graph_size: 最大图尺寸 (默认: 100)
                - enable_fuzzy_matching: 是否启用模糊匹配 (默认: True)
        """
        self.config = config or {}
        self._validate_config()
        self._init_semantic_mappings()
        logger.info("FeedbackToGraphConverter 初始化完成，配置: %s", self.config)

    def _validate_config(self) -> None:
        """验证配置参数"""
        self.config.setdefault("min_confidence", 0.5)
        self.config.setdefault("max_graph_size", 100)
        self.config.setdefault("enable_fuzzy_matching", True)
        
        if not 0 <= self.config["min_confidence"] <= 1:
            raise ValueError("min_confidence 必须在 [0.0, 1.0] 范围内")
        if self.config["max_graph_size"] < 1:
            raise ValueError("max_graph_size 必须大于等于 1")

    def _init_semantic_mappings(self) -> None:
        """
        初始化语义映射规则。
        这里建立从模糊的人类语言到精确参数的映射。
        """
        # 模糊词汇到参数范围的映射
        self.fuzzy_param_mappings = {
            "轻轻": {"force": (0.1, 0.3), "speed": (0.1, 0.4)},
            "稳定": {"variance": (0.0, 0.1), "smoothness": (0.7, 1.0)},
            "快速": {"speed": (0.7, 1.0), "acceleration": (0.5, 1.0)},
            "缓慢": {"speed": (0.1, 0.3), "acceleration": (0.0, 0.2)},
            "重": {"force": (0.7, 1.0), "grip_strength": (0.8, 1.0)},
            "精确": {"precision": (0.9, 1.0), "tolerance": (0.0, 0.05)},
        }
        
        # 动作关键词到节点类型的映射
        self.action_keywords = {
            "抓取": NodeType.ACTION,
            "移动": NodeType.ACTION,
            "旋转": NodeType.ACTION,
            "放置": NodeType.ACTION,
            "如果": NodeType.DECISION,
            "当": NodeType.DECISION,
            "记住": NodeType.MEMORY,
            "感知": NodeType.PERCEPTION,
        }

    def convert(self, feedback: UnstructuredFeedback) -> List[ComputeNode]:
        """
        核心转换函数：将非结构化反馈转换为计算图。
        
        Args:
            feedback: 非结构化反馈数据
            
        Returns:
            计算图节点列表
            
        Raises:
            ValueError: 如果输入数据无效或置信度过低
            RuntimeError: 如果图生成过程中发生错误
        """
        try:
            # 1. 数据验证
            self._validate_feedback(feedback)
            
            # 2. 模态特定处理
            processed_data = self._process_modality(feedback)
            
            # 3. 语义解析与结构化
            structured_data = self._parse_semantics(processed_data, feedback.context)
            
            # 4. 计算图生成
            compute_graph = self._generate_compute_graph(structured_data, feedback)
            
            # 5. 图优化与验证
            optimized_graph = self._optimize_graph(compute_graph)
            
            logger.info(
                "成功转换反馈，生成 %d 个节点 (反馈ID: %s)",
                len(optimized_graph),
                getattr(feedback, "id", "N/A")
            )
            return optimized_graph
            
        except Exception as e:
            logger.error("转换失败: %s", str(e), exc_info=True)
            raise RuntimeError(f"计算图生成失败: {str(e)}") from e

    def _validate_feedback(self, feedback: UnstructuredFeedback) -> None:
        """验证反馈数据的有效性"""
        if feedback.confidence < self.config["min_confidence"]:
            raise ValueError(
                f"反馈置信度 {feedback.confidence} 低于阈值 "
                f"{self.config['min_confidence']}"
            )
        
        if feedback.modality == FeedbackModality.TEXT:
            if not isinstance(feedback.raw_data, str) or not feedback.raw_data.strip():
                raise ValueError("文本反馈不能为空")
        elif feedback.modality in [FeedbackModality.SPEECH, FeedbackModality.VIDEO]:
            if not feedback.raw_data:
                raise ValueError(f"{feedback.modality.value} 反馈数据不能为空")

    def _process_modality(self, feedback: UnstructuredFeedback) -> Dict[str, Any]:
        """
        模态特定处理。
        
        实际系统中，这里会调用语音识别、计算机视觉等模型。
        本实现提供模拟逻辑。
        """
        processed = {
            "modality": feedback.modality.value,
            "content": None,
            "features": {},
            "temporal_info": []
        }
        
        if feedback.modality == FeedbackModality.TEXT:
            processed["content"] = feedback.raw_data
            # 模拟NLP特征提取
            processed["features"] = {
                "sentences": re.split(r'[。！？.!?]', feedback.raw_data),
                "word_count": len(feedback.raw_data.split())
            }
            
        elif feedback.modality == FeedbackModality.SPEECH:
            # 模拟语音转文本
            processed["content"] = f"[模拟语音转文本] {feedback.raw_data}"
            processed["features"] = {
                "duration": feedback.context.get("duration", 0),
                "tone": feedback.context.get("tone", "neutral")
            }
            
        elif feedback.modality == FeedbackModality.VIDEO:
            # 模拟视频关键帧提取
            processed["content"] = "[视频关键帧分析结果]"
            processed["features"] = {
                "key_frames": feedback.context.get("key_frames", []),
                "motion_pattern": feedback.context.get("motion_pattern", "unknown")
            }
            
        return processed

    def _parse_semantics(
        self, 
        processed_data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        语义解析与结构化。
        
        将提取的内容解析为结构化的语义表示。
        """
        structured = {
            "actions": [],
            "conditions": [],
            "parameters": {},
            "dependencies": []
        }
        
        content = processed_data.get("content", "")
        if not content:
            return structured
            
        # 简化的语义解析（实际系统会使用NLP模型）
        sentences = processed_data.get("features", {}).get("sentences", [content])
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # 检测条件语句
            if any(kw in sentence for kw in ["如果", "假如", "当"]):
                structured["conditions"].append({
                    "type": "conditional",
                    "expression": sentence,
                    "source": sentence
                })
                
            # 检测动作语句
            for keyword, node_type in self.action_keywords.items():
                if keyword in sentence:
                    structured["actions"].append({
                        "type": node_type.value,
                        "label": sentence,
                        "keyword": keyword
                    })
                    
            # 提取模糊参数
            for fuzzy_word, param_range in self.fuzzy_param_mappings.items():
                if fuzzy_word in sentence:
                    for param, value_range in param_range.items():
                        # 使用区间的中值作为默认值
                        mid_value = (value_range[0] + value_range[1]) / 2
                        structured["parameters"][param] = {
                            "value": mid_value,
                            "range": value_range,
                            "source": fuzzy_word
                        }
        
        return structured

    def _generate_compute_graph(
        self, 
        structured_data: Dict[str, Any], 
        feedback: UnstructuredFeedback
    ) -> List[ComputeNode]:
        """
        生成计算图。
        
        将结构化语义转换为计算图节点和连接。
        """
        nodes = []
        
        # 创建条件节点
        for cond in structured_data.get("conditions", []):
            node = ComputeNode(
                node_type=NodeType.DECISION,
                semantic_label=cond["expression"],
                source_feedback_id=feedback.context.get("id"),
                parameters={"condition_type": cond["type"]}
            )
            nodes.append(node)
            
        # 创建动作节点
        prev_action_node = None
        for action in structured_data.get("actions", []):
            # 获取相关参数
            action_params = {}
            for param, details in structured_data.get("parameters", {}).items():
                action_params[param] = details["value"]
                
            node = ComputeNode(
                node_type=NodeType(action["type"]),
                semantic_label=action["label"],
                parameters=action_params,
                source_feedback_id=feedback.context.get("id")
            )
            
            # 建立顺序连接（简化逻辑）
            if prev_action_node:
                prev_action_node.connections.append(node.node_id)
                
            nodes.append(node)
            prev_action_node = node
            
        # 如果没有提取到明确节点，创建一个通用节点
        if not nodes:
            node = ComputeNode(
                node_type=NodeType.ACTION,
                semantic_label=f"从反馈派生的隐式动作: {feedback.raw_data[:30]}...",
                source_feedback_id=feedback.context.get("id")
            )
            nodes.append(node)
            
        return nodes

    def _optimize_graph(self, nodes: List[ComputeNode]) -> List[ComputeNode]:
        """
        图优化。
        
        包括：冗余消除、连接优化、参数一致性检查。
        """
        if len(nodes) > self.config["max_graph_size"]:
            logger.warning(
                "图大小 %d 超过最大限制 %d，将进行裁剪",
                len(nodes),
                self.config["max_graph_size"]
            )
            nodes = nodes[:self.config["max_graph_size"]]
            
        # 消除重复节点（简化实现）
        unique_nodes = {}
        for node in nodes:
            key = (node.node_type, node.semantic_label)
            if key not in unique_nodes:
                unique_nodes[key] = node
            else:
                # 合并参数
                existing = unique_nodes[key]
                existing.parameters.update(node.parameters)
                existing.connections.extend(node.connections)
                
        return list(unique_nodes.values())

    def export_graph(self, nodes: List[ComputeNode], format: str = "json") -> str:
        """
        导出计算图。
        
        Args:
            nodes: 计算图节点列表
            format: 导出格式 ('json', 'mermaid')
            
        Returns:
            格式化后的图表示
        """
        if format == "json":
            return json.dumps(
                [node.to_dict() for node in nodes],
                indent=2,
                ensure_ascii=False
            )
        elif format == "mermaid":
            lines = ["graph TD"]
            for node in nodes:
                lines.append(
                    f'    {node.node_id}["{node.node_type.value}: '
                    f'{node.semantic_label[:20]}..."]'
                )
                for conn in node.connections:
                    lines.append(f"    {node.node_id} --> {conn}")
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的导出格式: {format}")


# 辅助函数
def estimate_parameter_confidence(
    parameter_name: str, 
    value: float, 
    source_text: str
) -> float:
    """
    估算参数值的置信度。
    
    基于参数名称、值和来源文本，评估该参数映射的可靠程度。
    
    Args:
        parameter_name: 参数名称
        value: 参数值
        source_text: 来源文本
        
    Returns:
        置信度分数 [0.0, 1.0]
    """
    # 简化的置信度估算逻辑
    base_confidence = 0.5
    
    # 如果参数名在来源文本中直接出现，提高置信度
    if parameter_name.lower() in source_text.lower():
        base_confidence += 0.2
        
    # 如果值在合理范围内，提高置信度
    if 0 <= value <= 1:
        base_confidence += 0.2
        
    # 如果来源文本包含专业术语，提高置信度
    technical_terms = ["速度", "力度", "精度", "force", "speed", "precision"]
    if any(term in source_text.lower() for term in technical_terms):
        base_confidence += 0.1
        
    return min(1.0, base_confidence)


def merge_feedback_graphs(
    graph1: List[ComputeNode], 
    graph2: List[ComputeNode],
    merge_strategy: str = "union"
) -> List[ComputeNode]:
    """
    合并两个来自不同反馈的计算图。
    
    Args:
        graph1: 第一个计算图
        graph2: 第二个计算图
        merge_strategy: 合并策略 ('union', 'intersection', 'override')
        
    Returns:
        合并后的计算图
    """
    if merge_strategy == "union":
        # 简单联合，保留所有节点
        merged = graph1 + graph2
        # 去重逻辑可以在这里添加
        return merged
    elif merge_strategy == "intersection":
        # 只保留两个图中语义相似的节点
        # 简化实现
        return [n for n in graph1 if any(
            n.semantic_label == m.semantic_label for m in graph2
        )]
    elif merge_strategy == "override":
        # graph2 覆盖 graph1 中的相同类型节点
        merged = list(graph1)
        for node2 in graph2:
            overridden = False
            for i, node1 in enumerate(merged):
                if node1.node_type == node2.node_type:
                    merged[i] = node2
                    overridden = True
                    break
            if not overridden:
                merged.append(node2)
        return merged
    else:
        raise ValueError(f"未知的合并策略: {merge_strategy}")


# 示例用法
if __name__ == "__main__":
    try:
        # 创建转换器实例
        converter = FeedbackToGraphConverter(config={
            "min_confidence": 0.6,
            "max_graph_size": 50
        })
        
        # 示例1: 处理文本反馈
        text_feedback = UnstructuredFeedback(
            modality=FeedbackModality.TEXT,
            raw_data="如果物体看起来很重，应该缓慢且稳定地抓取。"
                    "移动时保持精确，避免碰撞。",
            context={"task": "pick_and_place", "id": "feedback_001"},
            confidence=0.85
        )
        
        # 转换为计算图
        compute_graph = converter.convert(text_feedback)
        
        # 输出结果
        print("\n=== 生成的计算图 (JSON) ===")
        print(converter.export_graph(compute_graph, format="json"))
        
        print("\n=== 生成的计算图 (Mermaid) ===")
        print(converter.export_graph(compute_graph, format="mermaid"))
        
        # 示例2: 使用辅助函数
        confidence = estimate_parameter_confidence(
            "force", 0.7, "缓慢且稳定地抓取"
        )
        print(f"\n参数置信度估计: {confidence:.2f}")
        
        # 示例3: 合并计算图
        another_graph = [
            ComputeNode(
                node_type=NodeType.ACTION,
                semantic_label="旋转物体",
                parameters={"angle": 90}
            )
        ]
        merged_graph = merge_feedback_graphs(
            compute_graph, another_graph, merge_strategy="union"
        )
        print(f"\n合并后的图包含 {len(merged_graph)} 个节点")
        
    except Exception as e:
        logger.error("示例运行失败: %s", str(e), exc_info=True)