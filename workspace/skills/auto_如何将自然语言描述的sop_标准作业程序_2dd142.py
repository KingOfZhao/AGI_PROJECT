"""
高级Python模块：自然语言SOP转化为因果逻辑图及逆向故障诊断系统

该模块实现了一个将文本形式的标准作业程序（SOP）解析为结构化因果图（DAG）的系统。
它包含了使用逆向链式推理（反向传播）进行故障诊断的核心逻辑。

主要功能：
1. 将SOP文本解析为图节点和边。
2. 构建并验证因果逻辑图。
3. 基于观察到的故障现象，逆向推导可能的根本原因。

作者: AGI System Core Engineer
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名
NodeID = str

class NodeType(Enum):
    """节点类型枚举，用于区分SOP中的不同元素"""
    STEP = "STEP"           # 操作步骤
    CONDITION = "CONDITION" # 前置条件
    OUTCOME = "OUTCOME"     # 预期结果
    FAILURE = "FAILURE"     # 故障现象

@dataclass
class Node:
    """
    图节点数据结构
    
    属性:
        id: 唯一标识符
        content: 自然语言描述内容
        node_type: 节点类型
        metadata: 额外的元数据
    """
    id: NodeID
    content: str
    node_type: NodeType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not isinstance(self.content, str):
            raise ValueError("Node content must be a non-empty string.")

@dataclass
class Edge:
    """
    图边数据结构，表示因果关系
    
    属性:
        source: 源节点ID (原因/前置步骤)
        target: 目标节点ID (结果/后置步骤)
        relation: 关系描述 (例如: "causes", "requires")
    """
    source: NodeID
    target: NodeID
    relation: str = "causes"

class CausalGraph:
    """
    因果逻辑图类
    
    存储SOP转化后的图结构，并提供路径查询和验证功能。
    """
    def __init__(self):
        self.nodes: Dict[NodeID, Node] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[NodeID, List[NodeID]] = {} # 正向邻接表 source -> [targets]
        self.reverse_adjacency: Dict[NodeID, List[NodeID]] = {} # 逆向邻接表 target -> [sources]
        logger.info("Initialized empty CausalGraph.")

    def add_node(self, node: Node) -> None:
        """添加节点到图中，包含ID唯一性检查"""
        if node.id in self.nodes:
            logger.warning(f"Node ID {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        self.adjacency.setdefault(node.id, [])
        self.reverse_adjacency.setdefault(node.id, [])
        logger.debug(f"Added node: {node.id} ({node.node_type.value})")

    def add_edge(self, edge: Edge) -> None:
        """添加边，包含节点存在性检查"""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Cannot create edge. Node {edge.source} or {edge.target} does not exist.")
        
        self.edges.append(edge)
        self.adjacency[edge.source].append(edge.target)
        self.reverse_adjacency[edge.target].append(edge.source)
        logger.debug(f"Added edge: {edge.source} -> {edge.target}")

    def validate_dag(self) -> bool:
        """
        验证图是否为有向无环图 (DAG)
        使用深度优先搜索检测环
        """
        visited: Set[NodeID] = set()
        recursion_stack: Set[NodeID] = set()

        def dfs(node_id: NodeID) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)
            
            for neighbor in self.adjacency.get(node_id, []):
                if neighbor not in visited:
                    if not dfs(neighbor):
                        return False
                elif neighbor in recursion_stack:
                    logger.error(f"Cycle detected involving nodes: {node_id} -> {neighbor}")
                    return False
            
            recursion_stack.remove(node_id)
            return True

        for node_id in self.nodes:
            if node_id not in visited:
                if not dfs(node_id):
                    return False
        
        logger.info("Graph validation passed: No cycles detected.")
        return True

def parse_sop_text_to_graph(sop_text: str) -> CausalGraph:
    """
    核心函数 1: 将自然语言SOP文本解析为因果图对象
    
    这是一个简化的解析器示例。在生产环境中，这里通常会接入
    LLM（大语言模型）或NLP管道来提取实体和关系。
    本函数使用基于规则的解析逻辑作为演示。
    
    输入格式说明:
        sop_text: 必须遵循特定格式的多行字符串。
        - 使用 "Step[N]: [描述]" 定义步骤
        - 使用 "Result: [描述]" 定义结果
        - 使用 "If [条件]" 定义条件
        - 使用 "->" 指示因果流向 (例如: Step1 -> Step2)
    
    Args:
        sop_text (str): SOP文本描述
        
    Returns:
        CausalGraph: 构建完成的因果图
        
    Raises:
        ValueError: 如果文本格式无法解析或图结构验证失败
    """
    logger.info("Starting SOP parsing...")
    graph = CausalGraph()
    lines = sop_text.strip().split('\n')
    
    # 正则表达式定义
    step_pattern = re.compile(r"Step\s*(\d+):\s*(.*)")
    result_pattern = re.compile(r"Result:\s*(.*)")
    cond_pattern = re.compile(r"If\s+(.*?):\s*(.*)")
    link_pattern = re.compile(r"([a-zA-Z0-9_]+)\s*->\s*([a-zA-Z0-9_]+)")

    temp_node_map: Dict[str, str] = {} # 临时存储名称到ID的映射

    try:
        for line in lines:
            line = line.strip()
            if not line: continue

            # 解析步骤
            step_match = step_pattern.match(line)
            if step_match:
                node_id = f"step_{step_match.group(1)}"
                content = step_match.group(2)
                node = Node(id=node_id, content=content, node_type=NodeType.STEP)
                graph.add_node(node)
                continue

            # 解析结果
            result_match = result_pattern.match(line)
            if result_match:
                content = result_match.group(1)
                node_id = f"res_{len(graph.nodes)}"
                node = Node(id=node_id, content=content, node_type=NodeType.OUTCOME)
                graph.add_node(node)
                continue
            
            # 解析连接关系
            link_match = link_pattern.match(line)
            if link_match:
                # 假设连接引用的是 step_id 等标准格式
                src_id = link_match.group(1)
                tgt_id = link_match.group(2)
                
                # 简单的ID修正逻辑（如果文本中没有step_前缀）
                if src_id.isdigit(): src_id = f"step_{src_id}"
                if tgt_id.isdigit(): tgt_id = f"step_{tgt_id}"
                
                edge = Edge(source=src_id, target=tgt_id)
                graph.add_edge(edge)

        if not graph.validate_dag():
            raise ValueError("Parsed graph contains cycles and is not a valid SOP DAG.")
            
        logger.info(f"SOP parsing complete. Total nodes: {len(graph.nodes)}, Total edges: {len(graph.edges)}")
        return graph

    except Exception as e:
        logger.error(f"Failed to parse SOP text: {str(e)}")
        raise

def diagnose_fault(graph: CausalGraph, failed_node_id: NodeID) -> List[List[NodeID]]:
    """
    核心函数 2: 故障诊断 (逆向链式推理)
    
    给定一个失败的节点（例如：一个未达到的预期结果），通过图进行反向遍历，
    找出所有可能导致该失败的操作路径（根本原因）。
    
    算法逻辑:
        1. 从失败节点开始。
        2. 查找所有直接前驱（父节点）。
        3. 递归查找前驱的前驱，直到达到没有入边的节点（根节点/起始步骤）。
        4. 返回所有完整的反向路径。
    
    Args:
        graph (CausalGraph): SOP因果图
        failed_node_id (NodeID): 观察到故障的节点ID
        
    Returns:
        List[List[NodeID]]: 可能的故障路径列表。每条路径是从根原因到故障点的节点ID序列。
        
    Example:
        如果 Step1 -> Step2 -> Result 失败了，返回 [["step_1", "step_2", "res_0"]]
    """
    if failed_node_id not in graph.nodes:
        logger.error(f"Diagnosis failed: Node {failed_node_id} not found in graph.")
        raise ValueError(f"Node {failed_node_id} does not exist.")
    
    logger.info(f"Starting diagnosis for failure at: {failed_node_id}")
    
    all_paths: List[List[NodeID]] = []
    
    def _dfs_reverse(current_id: NodeID, current_path: List[NodeID]):
        """
        辅助函数: 深度优先搜索（逆向）
        """
        # 将当前节点加入路径
        current_path.append(current_id)
        
        # 获取所有上游节点（原因）
        predecessors = graph.reverse_adjacency.get(current_id, [])
        
        if not predecessors:
            # 如果没有上游节点，说明到达了根节点，记录这条路径
            # 反转路径使其变为 原因 -> 结果 的顺序，便于阅读
            all_paths.append(current_path[::-1])
        else:
            # 继续向上游递归
            for pred_id in predecessors:
                # 防止环路导致的无限递归（虽然validate_dag已检查，但仍需谨慎）
                if pred_id in current_path:
                    logger.warning(f"Loop detected during diagnosis at {pred_id}. Skipping.")
                    continue
                _dfs_reverse(pred_id, list(current_path)) # 传递副本

    _dfs_reverse(failed_node_id, [])
    
    if not all_paths:
        logger.warning("No root cause paths found.")
    else:
        logger.info(f"Diagnosis complete. Found {len(all_paths)} potential causal chains.")
        
    return all_paths

def format_diagnostic_report(paths: List[List[NodeID]], graph: CausalGraph) -> str:
    """
    辅助函数: 格式化诊断报告
    
    将路径ID列表转换为可读的文本描述。
    
    Args:
        paths: 路径列表
        graph: 包含节点内容的图对象
        
    Returns:
        str: 格式化的文本报告
    """
    if not paths:
        return "No potential causes identified."
    
    report_lines = ["=" * 20, "Fault Diagnostic Report", "=" * 20]
    
    for i, path in enumerate(paths, 1):
        report_lines.append(f"\nPotential Cause Chain #{i}:")
        for node_id in path:
            node = graph.nodes.get(node_id)
            if node:
                report_lines.append(f"  [{node.node_type.value}] {node_id}: {node.content}")
            else:
                report_lines.append(f"  [UNKNOWN] {node_id}")
                
    return "\n".join(report_lines)

# ==========================================
# 使用示例 / Example Usage
# ==========================================
if __name__ == "__main__":
    # 示例SOP文本 (模拟简单的服务器启动流程)
    sample_sop = """
    Step1: 检查电源连接
    Step2: 按下启动按钮
    Step3: 系统自检
    Result: 系统启动成功

    Step1 -> Step2
    Step2 -> Step3
    Step3 -> Result
    """

    print("--- 1. Parsing SOP ---")
    try:
        # 构建因果图
        sop_graph = parse_sop_text_to_graph(sample_sop)
        
        # 模拟添加一个额外的故障分支用于演示复杂场景
        # 假设 "电源损坏" 是 Step1 的一个潜在前因（虽然SOP文本没写，这里为了演示API）
        # sop_graph.add_node(Node(id="cause_power_fail", content="电源硬件损坏", node_type=NodeType.FAILURE))
        # sop_graph.add_edge(Edge(source="cause_power_fail", target="step_1"))

        print(f"Graph built with {len(sop_graph.nodes)} nodes.")
        
        # 执行诊断
        # 假设 "Result" (系统启动成功) 没有发生，即该节点是故障点
        print("\n--- 2. Running Diagnosis (Result failed) ---")
        failure_paths = diagnose_fault(sop_graph, "res_0") # res_0 是自动生成的Result ID
        
        # 生成并打印报告
        report = format_diagnostic_report(failure_paths, sop_graph)
        print(report)

    except Exception as e:
        print(f"An error occurred: {e}")