"""
全链路思维溯源护盾

该模块实现了AI决策过程的完整溯源能力，通过构建知识血缘图谱来追踪
结论的推导链路，标记黑盒节点和低信源节点，帮助用户建立过程导向的
审辩思维。

核心功能:
- 构建知识血缘图谱
- 追踪ETL(Extract-Transform-Load)推导过程
- 识别黑盒节点(不可解释的跳跃)
- 标记低信源节点(可信度低的信息源)
- 生成可视化溯源报告

典型用法:
    >>> from auto_构建_全链路思维溯源护盾_在ai辅助决_a7f0f4 import ThoughtTraceabilityShield
    >>> shield = ThoughtTraceabilityShield()
    >>> conclusion = "AI将取代50%的工作岗位"
    >>> trace = shield.trace_conclusion(conclusion, sources)
    >>> shield.visualize_lineage(trace)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union
import json
import hashlib
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('thought_traceability.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """知识图谱节点类型"""
    SOURCE = auto()      # 原始信息源
    DERIVATION = auto()  # 推导过程
    CONCLUSION = auto()  # 最终结论
    BLACKBOX = auto()    # 黑盒节点(不可解释的跳跃)
    LOW_TRUST = auto()   # 低信源节点


class TrustLevel(Enum):
    """信息源可信度级别"""
    HIGH = 0.9    # 学术期刊、官方数据
    MEDIUM = 0.6  # 主流媒体、行业报告
    LOW = 0.3     # 社交媒体、博客
    UNKNOWN = 0.1 # 无来源信息


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    content: str
    node_type: NodeType
    trust_level: TrustLevel = TrustLevel.MEDIUM
    parent_ids: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """验证节点数据"""
        if not self.content or not isinstance(self.content, str):
            raise ValueError("节点内容必须是非空字符串")
        if not isinstance(self.trust_level, TrustLevel):
            raise ValueError("无效的可信度级别")
        if not isinstance(self.node_type, NodeType):
            raise ValueError("无效的节点类型")


@dataclass
class TraceResult:
    """溯源结果"""
    conclusion_id: str
    lineage_graph: nx.DiGraph
    blackbox_nodes: List[str]
    low_trust_nodes: List[str]
    trust_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """将结果转换为字典格式"""
        return {
            'conclusion_id': self.conclusion_id,
            'blackbox_nodes': self.blackbox_nodes,
            'low_trust_nodes': self.low_trust_nodes,
            'trust_score': self.trust_score,
            'timestamp': self.timestamp.isoformat()
        }


class ThoughtTraceabilityShield:
    """全链路思维溯源护盾
    
    该类提供了完整的思维溯源能力，通过构建知识血缘图谱来追踪结论的
    推导过程，识别潜在的问题节点，帮助用户建立审辩思维。
    
    属性:
        knowledge_graph: 知识图谱存储
        trust_threshold: 低信源阈值
        blackbox_threshold: 黑盒跳跃阈值
    """
    
    def __init__(
        self,
        trust_threshold: float = 0.4,
        blackbox_threshold: int = 3
    ):
        """
        初始化溯源护盾
        
        参数:
            trust_threshold: 低信源阈值(0-1)
            blackbox_threshold: 黑盒跳跃阈值(推导步骤数)
        """
        self._validate_thresholds(trust_threshold, blackbox_threshold)
        
        self.knowledge_graph = nx.DiGraph()
        self.trust_threshold = trust_threshold
        self.blackbox_threshold = blackbox_threshold
        self._node_registry: Dict[str, KnowledgeNode] = {}
        
        logger.info(
            "ThoughtTraceabilityShield初始化完成 - "
            f"信任阈值: {trust_threshold}, 黑盒阈值: {blackbox_threshold}"
        )
    
    def _validate_thresholds(
        self,
        trust_threshold: float,
        blackbox_threshold: int
    ) -> None:
        """验证阈值参数的有效性"""
        if not 0 <= trust_threshold <= 1:
            raise ValueError("信任阈值必须在0到1之间")
        if blackbox_threshold < 1:
            raise ValueError("黑盒阈值必须大于0")
    
    def _generate_node_id(self, content: str) -> str:
        """生成唯一的节点ID"""
        timestamp = datetime.now().isoformat()
        hash_input = f"{content}-{timestamp}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()[:12]
    
    def register_knowledge_node(
        self,
        content: str,
        node_type: NodeType,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        parent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        注册知识节点到图谱
        
        参数:
            content: 节点内容
            node_type: 节点类型
            trust_level: 可信度级别
            parent_ids: 父节点ID列表
            metadata: 额外元数据
            
        返回:
            新生成的节点ID
            
        示例:
            >>> shield = ThoughtTraceabilityShield()
            >>> node_id = shield.register_knowledge_node(
            ...     "根据WHO报告，全球疫苗接种率达70%",
            ...     NodeType.SOURCE,
            ...     TrustLevel.HIGH
            ... )
        """
        try:
            # 验证父节点存在性
            if parent_ids:
                for pid in parent_ids:
                    if pid not in self._node_registry:
                        raise ValueError(f"父节点 {pid} 不存在")
            
            node_id = self._generate_node_id(content)
            node = KnowledgeNode(
                id=node_id,
                content=content,
                node_type=node_type,
                trust_level=trust_level,
                parent_ids=parent_ids or [],
                metadata=metadata or {}
            )
            
            # 添加到注册表和图谱
            self._node_registry[node_id] = node
            self.knowledge_graph.add_node(node_id, data=node)
            
            # 添加边关系
            if parent_ids:
                for parent_id in parent_ids:
                    self.knowledge_graph.add_edge(parent_id, node_id)
            
            logger.debug(f"注册新节点: {node_id} - 类型: {node_type.name}")
            return node_id
            
        except Exception as e:
            logger.error(f"注册知识节点失败: {str(e)}")
            raise
    
    def trace_conclusion(
        self,
        conclusion_id: str,
        max_depth: int = 10
    ) -> TraceResult:
        """
        追踪结论的完整推导链路
        
        参数:
            conclusion_id: 要追踪的结论节点ID
            max_depth: 最大追踪深度
            
        返回:
            TraceResult对象包含溯源结果
            
        示例:
            >>> trace = shield.trace_conclusion("conclusion_node_id")
            >>> print(f"发现{len(trace.blackbox_nodes)}个黑盒节点")
        """
        if conclusion_id not in self._node_registry:
            raise ValueError(f"结论节点 {conclusion_id} 不存在")
        
        logger.info(f"开始追踪结论: {conclusion_id}")
        
        # 构建血缘子图
        lineage_graph = self._build_lineage_graph(conclusion_id, max_depth)
        
        # 识别问题节点
        blackbox_nodes = self._identify_blackbox_nodes(lineage_graph)
        low_trust_nodes = self._identify_low_trust_nodes(lineage_graph)
        
        # 计算综合可信度分数
        trust_score = self._calculate_trust_score(
            lineage_graph,
            blackbox_nodes,
            low_trust_nodes
        )
        
        result = TraceResult(
            conclusion_id=conclusion_id,
            lineage_graph=lineage_graph,
            blackbox_nodes=blackbox_nodes,
            low_trust_nodes=low_trust_nodes,
            trust_score=trust_score
        )
        
        logger.info(
            f"溯源完成 - 黑盒节点: {len(blackbox_nodes)}, "
            f"低信源节点: {len(low_trust_nodes)}, "
            f"可信度: {trust_score:.2f}"
        )
        
        return result
    
    def _build_lineage_graph(
        self,
        start_node: str,
        max_depth: int
    ) -> nx.DiGraph:
        """构建从结论到信息源的子图"""
        lineage = nx.DiGraph()
        visited = set()
        queue = [(start_node, 0)]
        
        while queue:
            node_id, depth = queue.pop(0)
            
            if depth > max_depth or node_id in visited:
                continue
                
            visited.add(node_id)
            node = self._node_registry[node_id]
            lineage.add_node(node_id, data=node)
            
            # 添加父节点关系
            for parent_id in node.parent_ids:
                lineage.add_edge(parent_id, node_id)
                queue.append((parent_id, depth + 1))
        
        return lineage
    
    def _identify_blackbox_nodes(self, graph: nx.DiGraph) -> List[str]:
        """
        识别黑盒节点(不可解释的推导跳跃)
        
        条件:
        1. 推导步骤过长(超过blackbox_threshold)
        2. 缺乏中间推导节点
        3. 从低信源直接跳到高置信结论
        """
        blackbox_nodes = []
        
        for node_id in graph.nodes():
            node = graph.nodes[node_id]['data']
            
            # 检查推导链长度
            predecessors = list(graph.predecessors(node_id))
            if not predecessors and node.node_type == NodeType.DERIVATION:
                # 无源推导，可能是黑盒
                blackbox_nodes.append(node_id)
                continue
                
            # 检查跨信任级别的跳跃
            if predecessors:
                parent_nodes = [graph.nodes[p]['data'] for p in predecessors]
                max_parent_trust = max(
                    p.trust_level.value for p in parent_nodes
                )
                if (node.trust_level.value - max_parent_trust > 0.5 and
                    node.node_type == NodeType.CONCLUSION):
                    blackbox_nodes.append(node_id)
        
        return blackbox_nodes
    
    def _identify_low_trust_nodes(self, graph: nx.DiGraph) -> List[str]:
        """识别低信源节点"""
        low_trust_nodes = []
        
        for node_id in graph.nodes():
            node = graph.nodes[node_id]['data']
            if node.trust_level.value < self.trust_threshold:
                low_trust_nodes.append(node_id)
        
        return low_trust_nodes
    
    def _calculate_trust_score(
        self,
        graph: nx.DiGraph,
        blackbox_nodes: List[str],
        low_trust_nodes: List[str]
    ) -> float:
        """
        计算综合可信度分数
        
        算法:
        1. 基础分 = 所有节点的平均信任值
        2. 减去黑盒节点的惩罚分
        3. 减去低信源节点的惩罚分
        """
        if not graph.nodes:
            return 0.0
            
        # 计算平均节点信任值
        total_trust = sum(
            graph.nodes[n]['data'].trust_level.value
            for n in graph.nodes
        )
        avg_trust = total_trust / len(graph.nodes)
        
        # 应用惩罚
        blackbox_penalty = len(blackbox_nodes) * 0.15
        low_trust_penalty = len(low_trust_nodes) * 0.1
        
        final_score = max(0, min(1, avg_trust - blackbox_penalty - low_trust_penalty))
        return round(final_score, 2)
    
    def visualize_lineage(
        self,
        trace_result: TraceResult,
        output_file: Optional[str] = None
    ) -> None:
        """
        可视化知识血缘图谱
        
        参数:
            trace_result: 溯源结果对象
            output_file: 输出文件路径(可选)
        """
        graph = trace_result.lineage_graph
        
        # 设置节点颜色映射
        color_map = {
            NodeType.SOURCE: '#4CAF50',      # 绿色
            NodeType.DERIVATION: '#2196F3',  # 蓝色
            NodeType.CONCLUSION: '#FF9800',   # 橙色
            NodeType.BLACKBOX: '#F44336',     # 红色
            NodeType.LOW_TRUST: '#9E9E9E'     # 灰色
        }
        
        # 获取节点颜色
        node_colors = []
        for node_id in graph.nodes:
            node = graph.nodes[node_id]['data']
            
            # 优先标记问题节点
            if node_id in trace_result.blackbox_nodes:
                node_colors.append(color_map[NodeType.BLACKBOX])
            elif node_id in trace_result.low_trust_nodes:
                node_colors.append(color_map[NodeType.LOW_TRUST])
            else:
                node_colors.append(color_map[node.node_type])
        
        # 绘制图形
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(graph, k=0.5, iterations=50)
        
        # 绘制节点
        nx.draw_networkx_nodes(
            graph, pos,
            node_color=node_colors,
            node_size=800,
            alpha=0.9
        )
        
        # 绘制边
        nx.draw_networkx_edges(
            graph, pos,
            width=1.5,
            arrowstyle='->',
            arrowsize=20
        )
        
        # 添加标签(截断长文本)
        labels = {}
        for node_id in graph.nodes:
            content = graph.nodes[node_id]['data'].content
            labels[node_id] = content[:20] + '...' if len(content) > 20 else content
        
        nx.draw_networkx_labels(
            graph, pos,
            labels,
            font_size=10,
            font_weight='bold'
        )
        
        # 添加图例
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='信息源',
                      markerfacecolor='#4CAF50', markersize=10),
            plt.Line2D([0], [0], marker='o', color='w', label='推导过程',
                      markerfacecolor='#2196F3', markersize=10),
            plt.Line2D([0], [0], marker='o', color='w', label='结论',
                      markerfacecolor='#FF9800', markersize=10),
            plt.Line2D([0], [0], marker='o', color='w', label='黑盒节点',
                      markerfacecolor='#F44336', markersize=10),
            plt.Line2D([0], [0], marker='o', color='w', label='低信源',
                      markerfacecolor='#9E9E9E', markersize=10)
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title(f"知识血缘图谱 - 可信度: {trace_result.trust_score:.2f}")
        plt.axis('off')
        
        if output_file:
            plt.savefig(output_file, bbox_inches='tight', dpi=300)
            logger.info(f"图谱已保存到: {output_file}")
        else:
            plt.show()
        
        plt.close()
    
    def export_trace_report(
        self,
        trace_result: TraceResult,
        format: str = 'json'
    ) -> Union[str, Dict]:
        """
        导出溯源报告
        
        参数:
            trace_result: 溯源结果对象
            format: 输出格式('json'或'dict')
            
        返回:
            指定格式的溯源报告
        """
        report = {
            'meta': {
                'generated_at': datetime.now().isoformat(),
                'shield_version': '1.0',
                'trust_threshold': self.trust_threshold,
                'blackbox_threshold': self.blackbox_threshold
            },
            'result': trace_result.to_dict(),
            'nodes': [],
            'edges': []
        }
        
        # 添加节点信息
        for node_id in trace_result.lineage_graph.nodes:
            node = trace_result.lineage_graph.nodes[node_id]['data']
            report['nodes'].append({
                'id': node_id,
                'type': node.node_type.name,
                'content': node.content,
                'trust_level': node.trust_level.name,
                'is_blackbox': node_id in trace_result.blackbox_nodes,
                'is_low_trust': node_id in trace_result.low_trust_nodes
            })
        
        # 添加边信息
        for source, target in trace_result.lineage_graph.edges:
            report['edges'].append({
                'source': source,
                'target': target
            })
        
        if format == 'json':
            return json.dumps(report, indent=2, ensure_ascii=False)
        return report


# 示例用法
if __name__ == "__main__":
    # 初始化溯源护盾
    shield = ThoughtTraceabilityShield()
    
    try:
        # 注册知识节点
        source1 = shield.register_knowledge_node(
            "WHO 2023年报告: 全球疫苗接种率达70%",
            NodeType.SOURCE,
            TrustLevel.HIGH
        )
        
        source2 = shield.register_knowledge_node(
            "某博客文章: 疫苗导致严重副作用",
            NodeType.SOURCE,
            TrustLevel.LOW
        )
        
        # 添加推导节点
        derivation1 = shield.register_knowledge_node(
            "疫苗接种率提升有助于群体免疫形成",
            NodeType.DERIVATION,
            TrustLevel.MEDIUM,
            parent_ids=[source1]
        )
        
        derivation2 = shield.register_knowledge_node(
            "疫苗副作用率低于自然感染风险",
            NodeType.DERIVATION,
            TrustLevel.MEDIUM,
            parent_ids=[source1]
        )
        
        # 添加结论节点
        conclusion = shield.register_knowledge_node(
            "应继续推广疫苗接种计划",
            NodeType.CONCLUSION,
            TrustLevel.HIGH,
            parent_ids=[derivation1, derivation2]
        )
        
        # 追踪结论
        trace = shield.trace_conclusion(conclusion)
        
        # 可视化结果
        shield.visualize_lineage(trace)
        
        # 导出报告
        report = shield.export_trace_report(trace)
        print(report)
        
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")