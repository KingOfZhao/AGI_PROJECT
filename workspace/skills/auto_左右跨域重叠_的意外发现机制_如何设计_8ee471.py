"""
名称: auto_左右跨域重叠_的意外发现机制_如何设计_8ee471
描述: 本模块实现了一个用于检测看似无关领域间结构同构性的算法。
      它通过图同构和网络分析方法，识别不同领域（如生物学与城市规划）实体关系网络中的
      结构相似性，从而生成可证伪的创新假设。
领域: innovation_theory
"""

import logging
import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DomainGraph:
    """
    封装领域数据的图结构。
    
    Attributes:
        name (str): 领域名称 (如 "Biology")
        nodes (List[Tuple[str, Dict]]): 节点列表，包含ID和属性字典
        edges (List[Tuple[str, str, Dict]]): 边列表，包含源节点、目标节点和属性字典
    """
    name: str
    nodes: List[Tuple[str, Dict]]
    edges: List[Tuple[str, str, Dict]]

def validate_graph_data(data: DomainGraph) -> bool:
    """
    辅助函数：验证输入的图数据是否符合基本要求。
    
    Args:
        data (DomainGraph): 待验证的领域图数据对象
        
    Returns:
        bool: 如果数据有效返回 True，否则抛出 ValueError
        
    Raises:
        ValueError: 如果节点或边数据格式不正确，或图为空
    """
    logger.debug(f"开始验证领域 '{data.name}' 的数据结构...")
    
    if not isinstance(data.nodes, list) or not isinstance(data.edges, list):
        raise ValueError(f"领域 '{data.name}': nodes 和 edges 必须是列表类型。")
    
    if len(data.nodes) < 2:
        raise ValueError(f"领域 '{data.name}': 至少需要2个节点才能进行比较。")
        
    # 检查节点ID唯一性
    node_ids = [n[0] for n in data.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError(f"领域 '{data.name}': 检测到重复的节点ID。")
        
    logger.info(f"领域 '{data.name}' 数据验证通过。节点数: {len(data.nodes)}, 边数: {len(data.edges)}")
    return True

def construct_networkx_graph(domain_data: DomainGraph) -> nx.Graph:
    """
    核心函数 1: 将领域数据转换为 NetworkX 图对象，并进行抽象化处理。
    
    该函数将具体的领域实体转换为抽象图结构，这是进行跨域比较的基础。
    它会提取节点的 'role_type' 和边的 'relation_type' 作为结构特征。
    
    Args:
        domain_data (DomainGraph): 输入的领域数据
        
    Returns:
        nx.Graph: 构建好的 NetworkX 无向图
        
    Raises:
        KeyError: 如果缺少必要的属性字段
    """
    try:
        validate_graph_data(domain_data)
        G = nx.Graph(name=domain_data.name)
        
        # 添加节点及其属性
        for node_id, attrs in domain_data.nodes:
            if 'type' not in attrs:
                logger.warning(f"节点 {node_id} 缺少 'type' 属性，将使用 'default'。")
                attrs['type'] = 'default'
            G.add_node(node_id, **attrs)
            
        # 添加边及其属性
        for u, v, attrs in domain_data.edges:
            if 'type' not in attrs:
                logger.warning(f"边 ({u}-{v}) 缺少 'type' 属性，将使用 'link'。")
                attrs['type'] = 'link'
            G.add_edge(u, v, **attrs)
            
        logger.info(f"图 '{domain_data.name}' 构建完成。")
        return G
    
    except Exception as e:
        logger.error(f"构建图失败: {str(e)}")
        raise

def detect_structural_isomorphism(
    graph_a: nx.Graph, 
    graph_b: nx.Graph, 
    min_subgraph_size: int = 3
) -> List[Dict[str, Any]]:
    """
    核心函数 2: 检测两个图之间的结构同构性（子图同构）。
    
    算法试图在较大的图中找到与较小图结构相似的子图。
    匹配规则基于：
    1. 节点的 'type' 属性必须匹配（模拟功能性同构）。
    2. 边的连接结构必须一致。
    
    Args:
        graph_a (nx.Graph): 领域 A 的图
        graph_b (nx.Graph): 领域 B 的图
        min_subgraph_size (int): 最小感兴趣的子图大小，过滤掉琐碎的匹配。
        
    Returns:
        List[Dict[str, Any]]: 匹配结果列表，每个字典包含：
            - 'mapping': 节点映射字典 {Domain_A_Node: Domain_B_Node}
            - 'confidence': 匹配置信度分数 (0.0-1.0)
            - 'hypothesis': 生成的初步创新假设描述
    """
    if not isinstance(graph_a, nx.Graph) or not isinstance(graph_b, nx.Graph):
        raise TypeError("输入必须是 networkx.Graph 对象")

    results = []
    
    # 确定较小的图作为模式图 以提高效率
    if len(graph_a.nodes) > len(graph_b.nodes):
        G_small, G_large = graph_b, graph_a
        reversed_order = True
    else:
        G_small, G_large = graph_a, graph_b
        reversed_order = False

    logger.info(f"开始同构检测: 小图 '{G_small.name}' ({len(G_small.nodes)} nodes) vs 大图 '{G_large.name}' ({len(G_large.nodes)} nodes)")

    # 定义节点匹配条件：必须是相同类型的节点
    def node_match(n1, n2):
        return n1.get('type') == n2.get('type')

    # 使用 VF2 算法进行子图同构检测
    # 注意：在大型图中，这是一个 NP-hard 问题，此处仅作演示，实际AGI系统需优化
    GM = GraphMatcher(G_large, G_small, node_match=node_match)
    
    found_matches = 0
    # 限制匹配数量以防止计算爆炸
    max_matches = 10 
    
    for subgraph in GM.subgraph_isomorphisms_iter():
        # subgraph 是一个字典: {G_large_node: G_small_node}
        
        # 过滤掉过小的匹配（虽然这里实际上是全图匹配，但如果是提取子图逻辑需注意）
        if len(subgraph) < min_subgraph_size:
            continue
            
        # 计算重叠度/置信度
        # 这里简单地用匹配节点数占总节点数的比例来模拟
        confidence = len(subgraph) / len(G_small.nodes)
        
        # 生成假设
        # 如果顺序反了，需要翻转映射来生成 A -> B 的假设
        if reversed_order:
            mapping = {v: k for k, v in subgraph.items()}
        else:
            mapping = subgraph
            
        hypothesis = _generate_hypothesis_text(G_small, G_large, mapping)
        
        result_entry = {
            "mapping": mapping,
            "confidence": round(confidence, 2),
            "hypothesis": hypothesis
        }
        results.append(result_entry)
        found_matches += 1
        
        if found_matches >= max_matches:
            logger.warning("达到最大匹配数限制，停止搜索。")
            break
            
    logger.info(f"检测完成，发现 {len(results)} 个有效结构重叠区。")
    return results

def _generate_hypothesis_text(
    source_g: nx.Graph, 
    target_g: nx.Graph, 
    mapping: Dict[str, str]
) -> str:
    """
    辅助函数：根据节点映射生成自然语言假设。
    
    Args:
        source_g: 源领域图
        target_g: 目标领域图
        mapping: 源节点到目标节点的映射
        
    Returns:
        str: 生成的假设字符串
    """
    # 简单提取部分关键节点名称用于生成描述
    src_examples = list(mapping.keys())[:2]
    tgt_examples = [mapping[k] for k in src_examples]
    
    src_name = source_g.name
    tgt_name = target_g.name
    
    hypothesis = (
        f"假设 [{tgt_name}] 领域中的机制可能与 [{src_name}] 存在结构同构："
        f"例如，'{tgt_name}' 中的 '{tgt_examples}' 可能类似于 "
        f"'{src_name}' 中的 '{src_examples}'。"
        f"建议研究 '{src_name}' 中这些组件的交互原理，以优化 '{tgt_name}' 的系统设计。"
    )
    return hypothesis

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 定义领域 A: 生物细胞渗透
    biology_nodes = [
        ("CellMembrane", {"type": "Boundary"}),
        ("IonChannel", {"type": "Gate"}),
        ("Solute", {"type": "Unit"}),
        ("Cytoplasm", {"type": "Zone"}),
    ]
    biology_edges = [
        ("CellMembrane", "IonChannel", {"type": "Component"}),
        ("IonChannel", "Solute", {"type": "Transport"}),
        ("Solute", "Cytoplasm", {"type": "Move"}),
    ]
    bio_domain = DomainGraph(name="Cell_Biology", nodes=biology_nodes, edges=biology_edges)

    # 2. 定义领域 B: 城市交通流
    traffic_nodes = [
        ("CityBorder", {"type": "Boundary"}),
        ("TrafficLight", {"type": "Gate"}), # 与 IonChannel 类型相同
        ("Car", {"type": "Unit"}),          # 与 Solute 类型相同
        ("Downtown", {"type": "Zone"}),     # 与 Cytoplasm 类型相同
        ("Highway", {"type": "Path"}),      # 额外的节点
    ]
    traffic_edges = [
        ("CityBorder", "TrafficLight", {"type": "Component"}),
        ("TrafficLight", "Car", {"type": "Control"}),
        ("Car", "Downtown", {"type": "Move"}),
        ("Highway", "CityBorder", {"type": "Link"}),
    ]
    traffic_domain = DomainGraph(name="Urban_Traffic", nodes=traffic_nodes, edges=traffic_edges)

    try:
        # 3. 构建图
        G_bio = construct_networkx_graph(bio_domain)
        G_traffic = construct_networkx_graph(traffic_domain)

        # 4. 检测跨域重叠
        # 这里的 min_subgraph_size=3 确保我们寻找的是有意义的结构，而不仅仅是单点匹配
        overlaps = detect_structural_isomorphism(G_bio, G_traffic, min_subgraph_size=3)

        print("\n=== 发现的创新假设 ===")
        for i, res in enumerate(overlaps, 1):
            print(f"\n匹配 #{i}:")
            print(f"置信度: {res['confidence']}")
            print(f"节点映射: {res['mapping']}")
            print(f"生成假设: {res['hypothesis']}")
            
    except ValueError as ve:
        logger.error(f"数据验证错误: {ve}")
    except Exception as e:
        logger.error(f"运行时错误: {e}")