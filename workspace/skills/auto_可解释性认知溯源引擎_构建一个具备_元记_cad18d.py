"""
可解释性认知溯源引擎

构建一个具备“元记忆”的AI系统。当AGI输出一个决策或创意时，系统能够像人类回忆童年事件一样，
构建一个可视化的“思维血缘图”。这不仅是列出参考文档，而是重现“念头”的产生路径：
它碰撞了哪些旧知识？排除了哪些干扰项？这种能力让人类能对AI的“黑盒”进行“心理分析”，
精准定位幻觉或偏见的源头，实现真正的认知自洽。

Domain: cross_domain
Version: 1.0.0
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveProvenanceEngine")


class ThoughtNodeType(Enum):
    """定义思维节点的类型"""
    SOURCE_DATA = "Source Data"          # 源数据/原始输入
    CORE_CONCEPT = "Core Concept"        # 核心概念/旧知识
    DISTRACTOR = "Distractor"            # 干扰项/被排除的路径
    HALLUCINATION_RISK = "Hallucination" # 潜在幻觉/不确定性
    SYNTHESIS = "Synthesis"              # 综合/推理中间态
    DECISION = "Final Decision"          # 最终决策


@dataclass
class ThoughtNode:
    """
    思维节点数据结构
    代表思维血缘图中的一个节点，类似于神经元或一个具体的念头。
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    node_type: ThoughtNodeType = ThoughtNodeType.CORE_CONCEPT
    confidence: float = 1.0  # 0.0 to 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.confidence <= 1.0:
            logger.warning(f"Confidence {self.confidence} out of bounds for node {self.node_id}. Clamping.")
            self.confidence = max(0.0, min(1.0, self.confidence))
        if not isinstance(self.node_type, ThoughtNodeType):
            raise ValueError(f"Invalid node_type: {self.node_type}")


class CognitiveProvenanceEngine:
    """
    可解释性认知溯源引擎主类
    
    负责记录思维过程、关联旧知识、排除干扰项，并生成思维血缘图。
    """

    def __init__(self):
        """初始化引擎，包含元记忆存储和图谱结构"""
        self.knowledge_graph: Dict[str, ThoughtNode] = {}  # 元记忆存储
        self.edges: Dict[str, Set[str]] = {}               # 思维路径连接
        logger.info("Cognitive Provenance Engine initialized.")

    def _validate_input(self, data: Any) -> bool:
        """
        辅助函数：验证输入数据的有效性
        
        Args:
            data: 输入数据
            
        Returns:
            bool: 数据是否有效
        """
        if data is None:
            return False
        if isinstance(data, str) and not data.strip():
            return False
        return True

    def recall_knowledge(self, query: str, threshold: float = 0.5) -> List[ThoughtNode]:
        """
        核心函数 1: 元记忆检索
        模拟人类回忆过程，根据查询内容检索相关的旧知识或经验。
        
        Args:
            query (str): 当前面临的上下文或查询。
            threshold (float): 记忆检索的激活阈值。
            
        Returns:
            List[ThoughtNode]: 激活的记忆节点列表。
        """
        if not self._validate_input(query):
            logger.error("Invalid query input for memory recall.")
            return []

        activated_nodes = []
        logger.info(f"Recalling memories related to: '{query}'...")
        
        # 模拟检索逻辑：遍历元记忆，寻找语义重叠（此处简化为关键词匹配）
        for node_id, node in self.knowledge_graph.items():
            # 简单模拟：如果查询内容包含节点内容的关键部分，则激活
            # 在真实AGI场景中，这里会使用向量嵌入相似度搜索
            similarity = 0.0
            if node.content.lower() in query.lower():
                similarity = 0.8
            elif query.lower() in node.content.lower():
                similarity = 0.6
            
            if similarity >= threshold:
                logger.debug(f"Activated memory: {node.content} (Sim: {similarity})")
                activated_nodes.append(node)
                
        return activated_nodes

    def add_thought_node(self, node: ThoughtNode, parents: Optional[List[str]] = None) -> str:
        """
        辅助函数：向血缘图中添加节点并建立连接
        
        Args:
            node (ThoughtNode): 思维节点实例
            parents (List[str]): 父节点ID列表，表示思维的来源
            
        Returns:
            str: 新节点的ID
        """
        if not isinstance(node, ThoughtNode):
            raise TypeError("Input must be a ThoughtNode instance")

        self.knowledge_graph[node.node_id] = node
        self.edges[node.node_id] = set()
        
        if parents:
            for parent_id in parents:
                if parent_id in self.knowledge_graph:
                    self.edges[node.node_id].add(parent_id)
                else:
                    logger.warning(f"Parent node {parent_id} not found in memory. Orphan link created.")
        
        logger.info(f"Added thought node: [{node.node_type.value}] {node.content[:20]}...")
        return node.node_id

    def synthesize_decision(
        self, 
        decision_content: str, 
        reasoning_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        核心函数 2: 认知综合与决策生成
        模拟决策过程，生成最终结果并标记思维路径（包括排除的干扰项）。
        
        Args:
            decision_content (str): 最终生成的决策内容。
            reasoning_context (Dict): 包含推理上下文的字典，格式如下：
                {
                    "inputs": ["input_id_1", ...],      # 输入依据
                    "conflicts": ["conflict_id_1", ...] # 冲突/排除项
                }
                
        Returns:
            Tuple[str, Dict]: (决策ID, 完整的思维血缘图数据)
        """
        if not self._validate_input(decision_content):
            raise ValueError("Decision content cannot be empty.")

        logger.info("Synthesizing decision and building cognitive lineage...")
        
        # 1. 创建决策节点
        decision_node = ThoughtNode(
            content=decision_content,
            node_type=ThoughtNodeType.DECISION,
            confidence=0.95 # 假设高确信度
        )
        
        # 2. 确定父节点（思维来源）
        parent_ids = reasoning_context.get("inputs", [])
        self.add_thought_node(decision_node, parents=parent_ids)
        
        # 3. 处理干扰项（被排除的思维路径）
        # 在图中建立连接但标记为低权重或特殊状态，用于溯源分析
        conflict_ids = reasoning_context.get("conflicts", [])
        for conf_id in conflict_ids:
            if conf_id in self.knowledge_graph:
                # 建立弱连接表示"曾经考虑过但排除了"
                self.edges[decision_node.node_id].add(conf_id)
                logger.info(f"Marking node {conf_id} as a suppressed distractor for decision.")
        
        # 4. 生成思维血缘图
        lineage_data = self.export_lineage(decision_node.node_id)
        
        return decision_node.node_id, lineage_data

    def export_lineage(self, node_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        导出指定节点的思维血缘图（递归追溯父节点）
        
        Args:
            node_id (str): 起始节点ID
            depth (int): 递归深度
            
        Returns:
            Dict: 包含节点和边的可视化数据结构
        """
        if node_id not in self.knowledge_graph:
            return {"error": "Node not found"}

        nodes_to_visit = [(node_id, 0)]
        visited_nodes = set()
        result_graph = {"nodes": [], "edges": []}

        while nodes_to_visit:
            current_id, current_depth = nodes_to_visit.pop(0)
            
            if current_id in visited_nodes or current_depth > depth:
                continue
            
            visited_nodes.add(current_id)
            node = self.knowledge_graph[current_id]
            
            # 添加节点信息
            result_graph["nodes"].append({
                "id": node.node_id,
                "label": node.content[:30] + "...",
                "type": node.node_type.value,
                "confidence": node.confidence
            })
            
            # 添加边并继续追溯
            for parent_id in self.edges.get(current_id, set()):
                result_graph["edges"].append({
                    "source": current_id,
                    "target": parent_id,
                    "relation": "derived_from" if self.knowledge_graph[parent_id].node_type != ThoughtNodeType.DISTRACTOR else "rejected"
                })
                nodes_to_visit.append((parent_id, current_depth + 1))
                
        return result_graph

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = CognitiveProvenanceEngine()

    # 2. 模拟预置的元记忆（旧知识）
    node_concept_1 = ThoughtNode(content="E = mc^2", node_type=ThoughtNodeType.CORE_CONCEPT, metadata={"domain": "physics"})
    node_concept_2 = ThoughtNode(content="Gravity bends light", node_type=ThoughtNodeType.CORE_CONCEPT, metadata={"domain": "relativity"})
    node_distractor = ThoughtNode(content="Light is instant", node_type=ThoughtNodeType.DISTRACTOR, confidence=0.1)

    id_c1 = engine.add_thought_node(node_concept_1)
    id_c2 = engine.add_thought_node(node_concept_2)
    id_d1 = engine.add_thought_node(node_distractor)

    # 3. 模拟一个中间推理过程（碰撞知识）
    # 假设AI正在思考黑洞问题
    related_memories = engine.recall_knowledge("black holes gravity", threshold=0.4)
    # 简单模拟：AI基于回忆到的 "E=mc^2" 和 "Gravity bends light" 生成了中间推论
    node_synth = ThoughtNode(
        content="Extreme gravity implies extreme time dilation", 
        node_type=ThoughtNodeType.SYNTHESIS
    )
    id_synth = engine.add_thought_node(node_synth, parents=[id_c1, id_c2])

    # 4. 生成最终决策并构建血缘图
    # AI得出结论，同时明确排除了 "Light is instant" 这个错误观念
    final_decision_text = "Time moves slower near a black hole event horizon."
    
    reasoning_context = {
        "inputs": [id_synth],  # 基于中间推理
        "conflicts": [id_d1]   # 排除了"光速无限"的旧观念
    }

    decision_id, lineage = engine.synthesize_decision(final_decision_text, reasoning_context)

    # 5. 输出结果
    print(f"\n=== Cognitive Provenance Output for Decision {decision_id} ===")
    print(json.dumps(lineage, indent=2))
    
    # 验证数据
    assert len(lineage['nodes']) == 4 # Decision, Synthesis, Concept1, Concept2 (Distractor may be pruned or included based on depth)