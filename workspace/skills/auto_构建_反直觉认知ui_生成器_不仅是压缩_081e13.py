"""
高级AGI技能模块：反直觉认知UI生成器

该模块实现了一个基于“Affordance（示能性）”原理的认知UI生成器。
它不仅仅是信息的压缩，而是将复杂的博弈论反直觉结论转化为可交互的、
高密度的微型决策场景（节点与连线的动态逻辑）。

核心逻辑：
1. 解析概念节点与逻辑连线。
2. 注入反直觉逻辑（如：纳什均衡中的非合作优于合作）。
3. 生成可供前端渲染的交互式场景描述数据。

Author: AGI System
Version: 1.0.0
"""

import logging
import json
from enum import Enum
from typing import Dict, List, Optional, TypedDict, Any
from dataclasses import dataclass, field
from uuid import uuid4

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeCategory(Enum):
    """节点类别枚举，定义认知对象的属性"""
    CONCEPT = "concept"       # 基础概念（如：囚徒）
    ACTION = "action"         # 可执行动作（如：背叛、合作）
    OUTCOME = "outcome"       # 结果状态（如：5年刑期）
    AFFORDANCE = "affordance" # 示能性提示（交互暗示）

class LogicType(Enum):
    """连线逻辑类型，定义节点间的关系强度与性质"""
    INTUITIVE = "intuitive"    # 直觉逻辑（符合常识）
    COUNTER = "counter"        # 反直觉逻辑（认知冲突点）
    CAUSAL = "causal"          # 因果关系

@dataclass
class CognitiveNode:
    """
    认知节点数据结构。
    代表UI中的一个可交互概念单元。
    """
    node_id: str
    label: str
    category: NodeCategory
    description: str
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid4())

@dataclass
class LogicLink:
    """
    逻辑连线数据结构。
    代表节点间的逻辑依赖，支持动态断裂效果。
    """
    source_id: str
    target_id: str
    logic_type: LogicType
    weight: float = 1.0  # 逻辑强度或相关性
    is_broken: bool = False # 是否在UI中表现为"断裂"（即反直觉点）

class CounterIntuitiveUIGenerator:
    """
    反直觉认知UI生成器核心类。
    
    利用博弈论原理构建微型决策场景。不仅仅是展示知识图谱，
    而是构建一个"认知游乐场"，用户通过交互（如拖拽）改变节点位置，
    触发逻辑连线的断裂或重连，从而验证反直觉结论。
    """

    def __init__(self, scenario_name: str):
        """
        初始化生成器。

        Args:
            scenario_name (str): 场景名称，如"囚徒困境"或"公地悲剧"。
        """
        self.scenario_name = scenario_name
        self.nodes: Dict[str, CognitiveNode] = {}
        self.links: List[LogicLink] = []
        self._validation_cache = {}
        logger.info(f"Initialized UI Generator for scenario: {scenario_name}")

    def add_concept_node(self, 
                         label: str, 
                         description: str, 
                         category: NodeCategory,
                         initial_pos: Optional[Dict[str, float]] = None) -> str:
        """
        核心函数 1: 添加认知节点。
        
        向场景中添加一个概念或动作节点，并自动分配ID。

        Args:
            label (str): 节点显示名称。
            description (str): 节点详细解释（用于Tooltip）。
            category (NodeCategory): 节点类型。
            initial_pos (Optional[Dict]): 初始坐标。

        Returns:
            str: 生成的节点ID。

        Raises:
            ValueError: 如果label为空。
        """
        if not label or not label.strip():
            logger.error("Attempted to add node with empty label.")
            raise ValueError("Node label cannot be empty.")

        node_id = f"node_{uuid4().hex[:8]}"
        pos = initial_pos if initial_pos else {"x": 0.0, "y": 0.0}
        
        node = CognitiveNode(
            node_id=node_id,
            label=label,
            category=category,
            description=description,
            position=pos
        )
        
        self.nodes[node_id] = node
        logger.debug(f"Added node: {label} ({category.value})")
        return node_id

    def define_logic_chain(self, 
                           source_id: str, 
                           target_id: str, 
                           logic_type: LogicType,
                           weight: float = 1.0) -> bool:
        """
        核心函数 2: 定义逻辑链路与示能性。
        
        连接两个节点，并标记逻辑类型。如果类型是COUNTER（反直觉），
        则在UI渲染时会被标记为"潜在断裂点"。

        Args:
            source_id (str): 源节点ID。
            target_id (str): 目标节点ID。
            logic_type (LogicType): 逻辑关系类型。
            weight (float): 关系权重 (0.0 - 1.0)。

        Returns:
            bool: 是否成功添加。

        Raises:
            KeyError: 如果节点ID不存在。
        """
        # 数据验证
        if source_id not in self.nodes or target_id not in self.nodes:
            msg = f"Invalid node ID in link: {source_id} -> {target_id}"
            logger.error(msg)
            raise KeyError(msg)
        
        if not (0.0 <= weight <= 1.0):
            logger.warning(f"Weight {weight} out of bounds, clamping to 0-1.")
            weight = max(0.0, min(1.0, weight))

        link = LogicLink(
            source_id=source_id,
            target_id=target_id,
            logic_type=logic_type,
            weight=weight,
            is_broken=(logic_type == LogicType.COUNTER) # 反直觉逻辑默认标记为"断裂/需验证"
        )
        
        self.links.append(link)
        logger.info(f"Defined logic chain: {source_id} -> {target_id} ({logic_type.value})")
        return True

    def _calculate_affordance_hints(self) -> List[Dict[str, str]]:
        """
        辅助函数: 计算示能性提示。
        
        遍历所有节点和连线，生成给UI层的交互提示。
        例如，对于反直觉连线，提示用户"尝试拖拽节点观察逻辑断裂"。

        Returns:
            List[Dict]: 提示信息列表。
        """
        hints = []
        for link in self.links:
            if link.logic_type == LogicType.COUNTER:
                source_node = self.nodes.get(link.source_id)
                if source_node:
                    hints.append({
                        "type": "interaction_hint",
                        "target_node": link.source_id,
                        "message": f"拖拽 '{source_node.label}' 可能会导致逻辑链断裂，揭示深层博弈逻辑。"
                    })
        return hints

    def generate_ui_schema(self) -> Dict[str, Any]:
        """
        生成最终的UI渲染Schema。
        
        将内部数据结构转化为前端（React/Vue/Canvas）可直接使用的JSON格式。
        包含节点定位、样式配置和交互规则。

        Returns:
            Dict[str, Any]: 完整的场景描述JSON。
        """
        logger.info("Generating UI Schema...")
        
        # 简单的自动布局逻辑 (实际场景中会使用力导向图算法)
        self._auto_layout()
        
        ui_data = {
            "meta": {
                "title": self.scenario_name,
                "description": "Interactive Cognitive Playground based on Game Theory"
            },
            "nodes": [
                {
                    "id": n.node_id, 
                    "label": n.label, 
                    "category": n.category.value,
                    "position": n.position,
                    "style": self._get_node_style(n.category)
                } for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": l.source_id,
                    "target": l.target_id,
                    "type": "logic_edge",
                    "animated": l.logic_type == LogicType.COUNTER,
                    "dashed": l.is_broken,
                    "label": l.logic_type.value
                } for l in self.links
            ],
            "affordance_hints": self._calculate_affordance_hints()
        }
        
        return ui_data

    def _get_node_style(self, category: NodeCategory) -> Dict[str, Any]:
        """根据类别返回默认样式配置"""
        styles = {
            NodeCategory.CONCEPT: {"color": "#4A90E2", "shape": "circle"},
            NodeCategory.ACTION: {"color": "#F5A623", "shape": "rect"},
            NodeCategory.OUTCOME: {"color": "#D0021B", "shape": "diamond"},
            NodeCategory.AFFORDANCE: {"color": "#7ED321", "shape": "triangle"}
        }
        return styles.get(category, {})

    def _auto_layout(self):
        """简单的网格布局辅助函数，防止节点重叠"""
        # 这是一个简化的布局逻辑，实际生产中应集成 networkx 或 d3-force
        x_offset = 0
        y_offset = 0
        for i, node in enumerate(self.nodes.values()):
            node.position['x'] = x_offset + (i % 3) * 150
            node.position['y'] = y_offset + (i // 3) * 100

# 使用示例
if __name__ == "__main__":
    # 1. 实例化生成器
    generator = CounterIntuitiveUIGenerator(scenario_name="Prisoner's Dilemma Playground")

    try:
        # 2. 构建节点（概念、动作、结果）
        node_prisoner_a = generator.add_concept_node(
            label="囚犯 A",
            description="理性的决策主体",
            category=NodeCategory.CONCEPT
        )
        
        node_betray = generator.add_concept_node(
            label="背叛",
            description="追求个人利益最大化的行动",
            category=NodeCategory.ACTION
        )
        
        node_silence = generator.add_concept_node(
            label="沉默",
            description="基于信任的合作行动",
            category=NodeCategory.ACTION
        )
        
        node_bad_outcome = generator.add_concept_node(
            label="双方判刑5年",
            description="纳什均衡结果",
            category=NodeCategory.OUTCOME
        )

        # 3. 构建逻辑链（直觉 vs 反直觉）
        # 直觉逻辑：合作(沉默)应该导致最好的结果
        generator.define_logic_chain(
            source_id=node_silence,
            target_id=node_bad_outcome, # 这里故意连接到坏结果，或者可以连接到一个理想结果然后被逻辑打破
            logic_type=LogicType.INTUITIVE
        )

        # 反直觉逻辑：背叛导致纳什均衡（虽然是局部最优，但是全局非最优）
        # 在UI中，这条线会是虚线或特殊颜色，提示用户这里的逻辑是"反直觉"的
        generator.define_logic_chain(
            source_id=node_betray,
            target_id=node_bad_outcome,
            logic_type=LogicType.COUNTER,
            weight=0.9
        )

        # 4. 生成UI Schema
        schema = generator.generate_ui_schema()
        
        # 打印输出
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Failed to generate UI: {e}")