"""
模块名称: auto_人机共生断点检测_在_ai梳理清单_人_33e3e5
描述: 【人机共生断点检测】在‘AI梳理清单→人类实践→人类反馈’的闭环中，验证AI对‘负面反馈’的处理能力。
      当人类标记AI的建议为‘不可行’时，AI是否能定位到具体的某个节点或连边作为错误源头，并重构局部网络。
作者: Senior Python Engineer
版本: 1.0.0
"""

import logging
import uuid
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """反馈类型枚举"""
    POSITIVE = "positive"
    NEGATIVE_INFEASIBLE = "negative_infeasible"
    NEGATIVE_SUBOPTIMAL = "negative_suboptimal"

class NodeType(Enum):
    """知识图谱节点类型"""
    TASK = "task"
    RESOURCE = "resource"
    CONDITION = "condition"

class GraphNode:
    """图谱节点类"""
    def __init__(self, node_id: str, node_type: NodeType, content: str, weight: float = 1.0):
        self.node_id = node_id
        self.node_type = node_type
        self.content = content
        self.weight = weight
        self.valid = True

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "type": self.node_type.value,
            "content": self.content,
            "weight": self.weight,
            "valid": self.valid
        }

class GraphEdge:
    """图谱连边类"""
    def __init__(self, source_id: str, target_id: str, relation: str, weight: float = 1.0):
        self.edge_id = f"{source_id}->{target_id}"
        self.source_id = source_id
        self.target_id = target_id
        self.relation = relation
        self.weight = weight
        self.valid = True

    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
            "valid": self.valid
        }

class KnowledgeGraph:
    """知识图谱数据结构"""
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}

    def add_node(self, node: GraphNode) -> bool:
        """添加节点"""
        if not isinstance(node, GraphNode):
            logger.error("Invalid node type")
            return False
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists")
            return False
        self.nodes[node.node_id] = node
        return True

    def add_edge(self, edge: GraphEdge) -> bool:
        """添加边"""
        if not isinstance(edge, GraphEdge):
            logger.error("Invalid edge type")
            return False
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            logger.error("Source or target node does not exist")
            return False
        self.edges[edge.edge_id] = edge
        return True

    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps({
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()]
        }, indent=2)

    def get_local_subgraph(self, node_id: str, depth: int = 1) -> Dict:
        """获取局部子图"""
        if node_id not in self.nodes:
            return {"nodes": [], "edges": []}
        
        visited_nodes = set()
        visited_edges = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth > depth:
                continue
                
            if current_id not in visited_nodes:
                visited_nodes.add(current_id)
                
                # 添加相关边
                for edge in self.edges.values():
                    if edge.source_id == current_id and edge.edge_id not in visited_edges:
                        visited_edges.add(edge.edge_id)
                        if edge.target_id not in visited_nodes:
                            queue.append((edge.target_id, current_depth + 1))
                    
                    if edge.target_id == current_id and edge.edge_id not in visited_edges:
                        visited_edges.add(edge.edge_id)
                        if edge.source_id not in visited_nodes:
                            queue.append((edge.source_id, current_depth + 1))
        
        return {
            "nodes": [self.nodes[nid].to_dict() for nid in visited_nodes],
            "edges": [self.edges[eid].to_dict() for eid in visited_edges]
        }

class SymbiosisBreakpointDetector:
    """人机共生断点检测器"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        初始化断点检测器
        
        参数:
            knowledge_graph: 知识图谱实例
        """
        if not isinstance(knowledge_graph, KnowledgeGraph):
            raise ValueError("Invalid knowledge graph instance")
        self.kg = knowledge_graph
        self.restructure_history: List[Dict] = []
        
    def analyze_negative_feedback(
        self,
        feedback_node_id: str,
        feedback_type: FeedbackType,
        human_comment: Optional[str] = None
    ) -> Dict:
        """
        分析负面反馈并定位错误源头
        
        参数:
            feedback_node_id: 反馈关联的节点ID
            feedback_type: 反馈类型
            human_comment: 人类评论(可选)
            
        返回:
            包含错误源头和重构建议的字典
        """
        logger.info(f"Analyzing negative feedback for node: {feedback_node_id}")
        
        # 数据验证
        if feedback_node_id not in self.kg.nodes:
            logger.error(f"Node {feedback_node_id} not found in knowledge graph")
            return {"status": "error", "message": "Node not found"}
            
        if feedback_type not in [FeedbackType.NEGATIVE_INFEASIBLE, FeedbackType.NEGATIVE_SUBOPTIMAL]:
            logger.error("Invalid feedback type for breakpoint detection")
            return {"status": "error", "message": "Invalid feedback type"}
            
        # 定位错误源头
        error_source = self._locate_error_source(feedback_node_id)
        if not error_source:
            logger.warning("No error source located")
            return {"status": "warning", "message": "No error source found"}
            
        logger.info(f"Error source located: {error_source}")
        
        # 重构局部网络
        restructure_result = self._restructure_local_network(error_source)
        
        # 记录重构历史
        self.restructure_history.append({
            "feedback_node": feedback_node_id,
            "error_source": error_source,
            "restructure_result": restructure_result,
            "human_comment": human_comment
        })
        
        return {
            "status": "success",
            "error_source": error_source,
            "restructure_suggestions": restructure_result,
            "affected_nodes": self._get_affected_nodes(error_source)
        }
    
    def _locate_error_source(self, node_id: str) -> Optional[Union[str, Tuple[str, str]]]:
        """
        定位错误源头(节点或连边)
        
        参数:
            node_id: 起始节点ID
            
        返回:
            错误源头(节点ID或连边元组)
        """
        # 获取相关边
        incoming_edges = [
            edge for edge in self.kg.edges.values() 
            if edge.target_id == node_id and edge.valid
        ]
        
        # 检查节点本身的合理性
        node = self.kg.nodes[node_id]
        if node.node_type == NodeType.CONDITION and "不满足" in node.content:
            logger.info(f"Condition node {node_id} is not satisfied")
            return node_id
        
        # 检查输入边
        for edge in incoming_edges:
            source_node = self.kg.nodes[edge.source_id]
            
            # 规则1: 如果源节点是资源且权重低于阈值，标记为错误
            if (source_node.node_type == NodeType.RESOURCE and 
                source_node.weight < 0.5 and
                "关键资源" in source_node.content):
                logger.info(f"Critical resource shortage detected at node {source_node.node_id}")
                return source_node.node_id
                
            # 规则2: 如果边的关系类型与上下文不符
            if (edge.relation == "依赖" and 
                "可选" in source_node.content and
                "必需" in self.kg.nodes[node_id].content):
                logger.info(f"Dependency mismatch detected in edge {edge.edge_id}")
                return (edge.source_id, edge.target_id)
        
        # 如果没有明确错误，返回最近的条件节点
        for edge in incoming_edges:
            if self.kg.nodes[edge.source_id].node_type == NodeType.CONDITION:
                logger.info(f"Upstream condition node {edge.source_id} identified as potential error source")
                return edge.source_id
                
        # 默认返回当前节点
        return node_id
    
    def _restructure_local_network(self, error_source: Union[str, Tuple[str, str]]) -> Dict:
        """
        重构局部网络
        
        参数:
            error_source: 错误源头(节点ID或连边元组)
            
        返回:
            重构结果字典
        """
        if isinstance(error_source, tuple):
            # 处理连边错误
            source_id, target_id = error_source
            edge_id = f"{source_id}->{target_id}"
            
            # 修改边关系
            if edge_id in self.kg.edges:
                edge = self.kg.edges[edge_id]
                original_relation = edge.relation
                edge.relation = "弱依赖" if edge.relation == "依赖" else "依赖"
                
                logger.info(f"Restructured edge {edge_id}: {original_relation} -> {edge.relation}")
                return {
                    "type": "edge_restructure",
                    "edge_id": edge_id,
                    "changes": {
                        "original_relation": original_relation,
                        "new_relation": edge.relation
                    }
                }
        
        else:
            # 处理节点错误
            node_id = error_source
            if node_id in self.kg.nodes:
                node = self.kg.nodes[node_id]
                
                # 如果是条件节点，尝试添加备选路径
                if node.node_type == NodeType.CONDITION:
                    # 创建备选节点
                    alt_node_id = f"alt_{node_id}_{uuid.uuid4().hex[:6]}"
                    alt_node = GraphNode(
                        node_id=alt_node_id,
                        node_type=NodeType.TASK,
                        content=f"备选方案: {node.content}",
                        weight=0.8
                    )
                    self.kg.add_node(alt_node)
                    
                    # 创建备选边
                    for edge in list(self.kg.edges.values()):
                        if edge.source_id == node_id:
                            alt_edge = GraphEdge(
                                source_id=alt_node_id,
                                target_id=edge.target_id,
                                relation="备选路径",
                                weight=0.7
                            )
                            self.kg.add_edge(alt_edge)
                    
                    logger.info(f"Created alternative path via node {alt_node_id}")
                    return {
                        "type": "node_alternative",
                        "original_node": node_id,
                        "alternative_node": alt_node_id,
                        "changes": {
                            "added_node": alt_node.to_dict(),
                            "added_edges": [
                                edge.to_dict() for edge in self.kg.edges.values() 
                                if edge.source_id == alt_node_id
                            ]
                        }
                    }
                
                # 如果是任务节点，调整权重
                elif node.node_type == NodeType.TASK:
                    original_weight = node.weight
                    node.weight = max(0.1, node.weight * 0.5)  # 降低权重但不低于0.1
                    
                    logger.info(f"Adjusted task node {node_id} weight: {original_weight} -> {node.weight}")
                    return {
                        "type": "node_weight_adjustment",
                        "node_id": node_id,
                        "changes": {
                            "original_weight": original_weight,
                            "new_weight": node.weight
                        }
                    }
        
        return {"type": "no_action", "message": "No restructure action taken"}

    def _get_affected_nodes(self, error_source: Union[str, Tuple[str, str]]) -> List[str]:
        """获取受影响的所有节点"""
        if isinstance(error_source, tuple):
            # 如果是连边错误，返回连边两端的节点
            return [error_source[0], error_source[1]]
        else:
            # 如果是节点错误，返回该节点及其直接邻居
            affected = {error_source}
            for edge in self.kg.edges.values():
                if edge.source_id == error_source:
                    affected.add(edge.target_id)
                if edge.target_id == error_source:
                    affected.add(edge.source_id)
            return list(affected)

# 使用示例
if __name__ == "__main__":
    # 创建知识图谱
    kg = KnowledgeGraph()
    
    # 添加节点
    task1 = GraphNode("task1", NodeType.TASK, "准备材料", 1.0)
    resource1 = GraphNode("resource1", NodeType.RESOURCE, "关键资源A", 0.4)  # 权重低
    condition1 = GraphNode("condition1", NodeType.CONDITION, "天气不满足", 1.0)
    task2 = GraphNode("task2", NodeType.TASK, "执行操作", 1.0)
    
    kg.add_node(task1)
    kg.add_node(resource1)
    kg.add_node(condition1)
    kg.add_node(task2)
    
    # 添加边
    kg.add_edge(GraphEdge("resource1", "task1", "依赖", 1.0))
    kg.add_edge(GraphEdge("task1", "task2", "依赖", 1.0))
    kg.add_edge(GraphEdge("condition1", "task2", "条件", 1.0))
    
    # 创建断点检测器
    detector = SymbiosisBreakpointDetector(kg)
    
    # 模拟负面反馈
    print("\n=== 测试1: 资源不足 ===")
    result1 = detector.analyze_negative_feedback(
        "task1",
        FeedbackType.NEGATIVE_INFEASIBLE,
        "材料不足，无法开始"
    )
    print("分析结果:", json.dumps(result1, indent=2))
    
    print("\n=== 测试2: 条件不满足 ===")
    result2 = detector.analyze_negative_feedback(
        "task2",
        FeedbackType.NEGATIVE_INFEASIBLE,
        "天气条件不允许"
    )
    print("分析结果:", json.dumps(result2, indent=2))
    
    print("\n=== 重构后的知识图谱 ===")
    print(kg.to_json())