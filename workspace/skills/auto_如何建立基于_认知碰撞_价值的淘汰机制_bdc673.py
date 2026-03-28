"""
高级Python模块：基于认知碰撞价值的淘汰机制

该模块实现了一个复杂的节点淘汰评估系统，用于AGI知识图谱中的认知节点管理。
核心算法结合了使用频率（热度）和跨域连接能力（认知碰撞价值）两个维度，
通过介数中心性等指标来评估节点对系统创新能力的潜在贡献。

核心功能：
1. 计算节点的综合认知价值
2. 模拟节点移除对系统创新能力的影响
3. 生成优化的淘汰策略

作者: AGI Systems Engineer
版本: 1.0.0
最后更新: 2023-11-15
"""

import logging
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional, Union
from collections import Counter
from datetime import datetime
import warnings

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 类型别名定义
NodeId = Union[str, int]
KnowledgeGraph = nx.Graph
MetricsDict = Dict[NodeId, Dict[str, float]]

class CognitiveCollisionEvaluator:
    """
    认知碰撞价值评估器，用于计算和评估节点在知识网络中的认知碰撞价值。
    
    该类实现了基于使用频率和跨域连接能力的综合评估算法，
    可以识别出那些虽然使用频率低但对系统创新能力有重要贡献的"桥梁"节点。
    
    属性:
        graph (nx.Graph): 知识图谱网络
        decay_factor (float): 时间衰减因子
        domain_tags (Dict[NodeId, List[str]]): 节点的领域标签
        
    示例:
        >>> G = nx.karate_club_graph()
        >>> domain_tags = {n: ['domain_A'] if n < 16 else ['domain_B'] for n in G.nodes()}
        >>> evaluator = CognitiveCollisionEvaluator(G, domain_tags=domain_tags)
        >>> metrics = evaluator.calculate_comprehensive_metrics()
        >>> vulnerable_nodes = evaluator.identify_vulnerable_nodes(metrics)
    """
    
    def __init__(
        self,
        graph: nx.Graph,
        decay_factor: float = 0.95,
        domain_tags: Optional[Dict[NodeId, List[str]]] = None,
        access_history: Optional[Dict[NodeId, List[datetime]]] = None
    ) -> None:
        """
        初始化认知碰撞评估器。
        
        参数:
            graph: 知识图谱网络
            decay_factor: 访问记录的时间衰减因子 (0-1)
            domain_tags: 节点的领域标签字典 {node_id: ['domain1', 'domain2']}
            access_history: 节点的访问历史记录 {node_id: [datetime1, datetime2]}
            
        异常:
            ValueError: 如果输入参数不符合要求
        """
        if not isinstance(graph, nx.Graph):
            raise ValueError("输入必须是networkx.Graph对象")
        if not 0 < decay_factor <= 1:
            raise ValueError("衰减因子必须在(0, 1]范围内")
            
        self.graph = graph
        self.decay_factor = decay_factor
        self.domain_tags = domain_tags or {}
        self.access_history = access_history or {}
        self._validate_inputs()
        
        logger.info(f"初始化认知碰撞评估器，节点数: {len(graph.nodes)}, 边数: {len(graph.edges)}")
    
    def _validate_inputs(self) -> None:
        """验证输入数据的完整性和一致性。"""
        # 检查图是否为空
        if len(self.graph) == 0:
            warnings.warn("输入图为空图，某些功能可能不可用")
            
        # 检查domain_tags是否与图节点匹配
        if self.domain_tags:
            missing_nodes = set(self.domain_tags.keys()) - set(self.graph.nodes())
            if missing_nodes:
                warnings.warn(f"domain_tags中包含图中不存在的节点: {missing_nodes}")
                
        # 检查access_history是否与图节点匹配
        if self.access_history:
            missing_nodes = set(self.access_history.keys()) - set(self.graph.nodes())
            if missing_nodes:
                warnings.warn(f"access_history中包含图中不存在的节点: {missing_nodes}")
    
    def calculate_usage_metrics(self) -> Dict[NodeId, Dict[str, float]]:
        """
        计算节点的使用频率指标，包括原始访问次数和考虑时间衰减的加权访问次数。
        
        返回:
            包含使用频率指标的字典:
            {
                node_id: {
                    'access_count': int,       # 原始访问次数
                    'weighted_access': float,   # 考虑时间衰减的加权访问次数
                    'last_access_days': float   # 距离上次访问的天数
                }
            }
        """
        logger.info("开始计算使用频率指标...")
        metrics = {}
        now = datetime.now()
        
        for node in self.graph.nodes():
            node_metrics = {
                'access_count': 0,
                'weighted_access': 0.0,
                'last_access_days': float('inf')
            }
            
            if node in self.access_history and self.access_history[node]:
                access_times = sorted(self.access_history[node])
                node_metrics['access_count'] = len(access_times)
                
                # 计算时间衰减加权的访问次数
                weighted_sum = 0.0
                for access_time in access_times:
                    days_ago = (now - access_time).days
                    weighted_sum += self.decay_factor ** days_ago
                
                node_metrics['weighted_access'] = weighted_sum
                node_metrics['last_access_days'] = (now - access_times[-1]).days
            
            metrics[node] = node_metrics
        
        logger.info("使用频率指标计算完成")
        return metrics
    
    def calculate_structural_metrics(
        self,
        weight: str = 'weight',
        normalize: bool = True
    ) -> Dict[NodeId, Dict[str, float]]:
        """
        计算节点的结构指标，包括度中心性、介数中心性和领域交叉度。
        
        参数:
            weight: 边权重属性名
            normalize: 是否归一化中心性指标
            
        返回:
            包含结构指标的字典:
            {
                node_id: {
                    'degree_centrality': float,       # 度中心性
                    'betweenness_centrality': float,  # 介数中心性
                    'domain_crossing': float,         # 领域交叉度 (0-1)
                    'cross_domain_edges': int         # 跨领域边数量
                }
            }
        """
        logger.info("开始计算结构指标...")
        metrics = {}
        
        # 计算度中心性
        if len(self.graph) > 0:
            degree_cent = nx.degree_centrality(self.graph)
            betweenness_cent = nx.betweenness_centrality(self.graph, normalized=normalize, weight=weight)
        else:
            degree_cent = {}
            betweenness_cent = {}
        
        # 计算领域交叉度
        domain_crossing = {}
        cross_domain_edges = {}
        
        if self.domain_tags:
            for node in self.graph.nodes():
                node_domains = set(self.domain_tags.get(node, []))
                cross_count = 0
                
                for neighbor in self.graph.neighbors(node):
                    neighbor_domains = set(self.domain_tags.get(neighbor, []))
                    if node_domains and neighbor_domains and not node_domains.intersection(neighbor_domains):
                        cross_count += 1
                
                total_edges = len(list(self.graph.neighbors(node)))
                domain_crossing[node] = cross_count / total_edges if total_edges > 0 else 0.0
                cross_domain_edges[node] = cross_count
        else:
            # 如果没有领域标签，则无法计算领域交叉度
            for node in self.graph.nodes():
                domain_crossing[node] = 0.0
                cross_domain_edges[node] = 0
        
        # 合并所有指标
        for node in self.graph.nodes():
            metrics[node] = {
                'degree_centrality': degree_cent.get(node, 0),
                'betweenness_centrality': betweenness_cent.get(node, 0),
                'domain_crossing': domain_crossing.get(node, 0),
                'cross_domain_edges': cross_domain_edges.get(node, 0)
            }
        
        logger.info("结构指标计算完成")
        return metrics
    
    def calculate_comprehensive_metrics(
        self,
        usage_weight: float = 0.3,
        structural_weight: float = 0.7
    ) -> Dict[NodeId, Dict[str, float]]:
        """
        计算节点的综合认知价值指标，结合使用频率和结构重要性。
        
        参数:
            usage_weight: 使用频率指标的权重 (0-1)
            structural_weight: 结构指标的权重 (0-1)
            
        返回:
            包含综合指标的字典:
            {
                node_id: {
                    **usage_metrics,         # 使用频率指标
                    **structural_metrics,    # 结构指标
                    'cognitive_value': float # 综合认知价值
                }
            }
        """
        if not 0 <= usage_weight <= 1 or not 0 <= structural_weight <= 1:
            raise ValueError("权重必须在0-1范围内")
        if not np.isclose(usage_weight + structural_weight, 1.0):
            warnings.warn("使用权重和结构权重之和不等于1，将自动归一化")
            total = usage_weight + structural_weight
            usage_weight /= total
            structural_weight /= total
        
        logger.info(f"开始计算综合认知价值指标，使用权重: {usage_weight:.2f}, 结构权重: {structural_weight:.2f}")
        
        # 获取基础指标
        usage_metrics = self.calculate_usage_metrics()
        structural_metrics = self.calculate_structural_metrics()
        
        # 合并指标
        comprehensive_metrics = {}
        
        for node in self.graph.nodes():
            # 归一化使用频率指标
            max_access = max(m['access_count'] for m in usage_metrics.values()) if usage_metrics else 1
            max_weighted = max(m['weighted_access'] for m in usage_metrics.values()) if usage_metrics else 1
            
            norm_access = usage_metrics[node]['access_count'] / max_access if max_access > 0 else 0
            norm_weighted = usage_metrics[node]['weighted_access'] / max_weighted if max_weighted > 0 else 0
            
            # 计算使用分数 (0-1)
            usage_score = (norm_access + norm_weighted) / 2
            
            # 计算结构分数 (0-1)
            betweenness = structural_metrics[node]['betweenness_centrality']
            domain_crossing = structural_metrics[node]['domain_crossing']
            structure_score = (betweenness + domain_crossing) / 2
            
            # 计算综合认知价值
            cognitive_value = (usage_weight * usage_score) + (structural_weight * structure_score)
            
            # 合并所有指标
            comprehensive_metrics[node] = {
                **usage_metrics[node],
                **structural_metrics[node],
                'usage_score': usage_score,
                'structure_score': structure_score,
                'cognitive_value': cognitive_value
            }
        
        logger.info("综合认知价值指标计算完成")
        return comprehensive_metrics
    
    def identify_vulnerable_nodes(
        self,
        metrics: Dict[NodeId, Dict[str, float]],
        access_threshold: int = 5,
        betweenness_threshold: float = 0.1,
        domain_crossing_threshold: float = 0.3
    ) -> List[NodeId]:
        """
        识别那些使用频率低但对系统创新能力有重要贡献的"脆弱"节点。
        
        参数:
            metrics: 节点指标字典
            access_threshold: 访问次数阈值，低于此值视为低频节点
            betweenness_threshold: 介数中心性阈值，高于此值视为重要桥梁节点
            domain_crossing_threshold: 领域交叉度阈值，高于此值视为跨域重要节点
            
        返回:
            脆弱节点列表
        """
        logger.info(f"开始识别脆弱节点，访问阈值: {access_threshold}, 介数阈值: {betweenness_threshold}")
        
        vulnerable_nodes = []
        for node, node_metrics in metrics.items():
            if (node_metrics['access_count'] <= access_threshold and
                (node_metrics['betweenness_centrality'] >= betweenness_threshold or
                 node_metrics['domain_crossing'] >= domain_crossing_threshold)):
                vulnerable_nodes.append(node)
        
        logger.info(f"识别到 {len(vulnerable_nodes)} 个脆弱节点")
        return vulnerable_nodes
    
    def simulate_node_removal(
        self,
        nodes_to_remove: List[NodeId],
        metrics: Dict[NodeId, Dict[str, float]],
        innovation_metric: str = 'betweenness_centrality'
    ) -> Dict[str, Union[float, List[NodeId]]]:
        """
        模拟节点移除对系统创新能力的影响。
        
        参数:
            nodes_to_remove: 要移除的节点列表
            metrics: 节点指标字典
            innovation_metric: 用于衡量创新能力的指标
            
        返回:
            包含模拟结果的字典:
            {
                'original_innovation': float,      # 原始创新能力指标
                'post_removal_innovation': float,  # 移除后的创新能力指标
                'innovation_loss': float,          # 创新能力损失比例
                'removed_nodes': List[NodeId],     # 实际移除的节点
                'disconnected_components': int     # 移除后的连通分量数量
            }
        """
        logger.info(f"开始模拟移除 {len(nodes_to_remove)} 个节点...")
        
        # 创建图的副本
        G_copy = self.graph.copy()
        
        # 计算原始创新能力
        original_innovation = sum(metrics[node][innovation_metric] for node in G_copy.nodes())
        
        # 移除节点
        actual_removed = []
        for node in nodes_to_remove:
            if node in G_copy.nodes():
                G_copy.remove_node(node)
                actual_removed.append(node)
        
        # 计算移除后的创新能力
        post_removal_innovation = 0
        if len(G_copy) > 0:
            # 重新计算介数中心性
            new_betweenness = nx.betweenness_centrality(G_copy)
            post_removal_innovation = sum(new_betweenness.values())
        
        # 计算创新能力损失
        innovation_loss = (original_innovation - post_removal_innovation) / original_innovation if original_innovation > 0 else 0
        
        # 计算连通分量
        disconnected_components = nx.number_connected_components(G_copy) if len(G_copy) > 0 else 0
        
        result = {
            'original_innovation': original_innovation,
            'post_removal_innovation': post_removal_innovation,
            'innovation_loss': innovation_loss,
            'removed_nodes': actual_removed,
            'disconnected_components': disconnected_components
        }
        
        logger.info(f"模拟完成，创新能力损失: {innovation_loss:.2%}")
        return result
    
    def generate_pruning_strategy(
        self,
        metrics: Dict[NodeId, Dict[str, float]],
        innovation_loss_tolerance: float = 0.1,
        max_nodes_to_remove: int = 10
    ) -> Dict[str, Union[List[NodeId], Dict[str, float]]]:
        """
        生成优化的节点淘汰策略，确保创新能力损失在容忍范围内。
        
        参数:
            metrics: 节点指标字典
            innovation_loss_tolerance: 创新能力损失容忍度 (0-1)
            max_nodes_to_remove: 最大可移除节点数
            
        返回:
            包含淘汰策略的字典:
            {
                'nodes_to_remove': List[NodeId],    # 建议移除的节点
                'nodes_to_keep': List[NodeId],      # 建议保留的节点
                'projected_loss': float,            # 预计创新能力损失
                'component_increase': int           # 连通分量增加数量
            }
        """
        if not 0 <= innovation_loss_tolerance <= 1:
            raise ValueError("创新能力损失容忍度必须在0-1范围内")
        
        logger.info(f"开始生成淘汰策略，最大损失容忍: {innovation_loss_tolerance:.2%}")
        
        # 按认知价值从低到高排序节点
        sorted_nodes = sorted(metrics.items(), key=lambda x: x[1]['cognitive_value'])
        
        nodes_to_remove = []
        current_loss = 0.0
        original_components = nx.number_connected_components(self.graph)
        
        for node, node_metrics in sorted_nodes:
            if len(nodes_to_remove) >= max_nodes_to_remove:
                break
                
            # 模拟移除当前节点
            test_nodes = nodes_to_remove + [node]
            result = self.simulate_node_removal(test_nodes, metrics)
            
            # 检查是否超过容忍度
            if result['innovation_loss'] > innovation_loss_tolerance:
                continue
                
            # 检查是否会显著增加连通分量
            if result['disconnected_components'] > original_components + 1:
                continue
                
            nodes_to_remove.append(node)
            current_loss = result['innovation_loss']
        
        # 确定保留的节点
        all_nodes = set(self.graph.nodes())
        removed_set = set(nodes_to_remove)
        nodes_to_keep = list(all_nodes - removed_set)
        
        # 获取最终模拟结果
        final_result = self.simulate_node_removal(nodes_to_remove, metrics)
        
        strategy = {
            'nodes_to_remove': nodes_to_remove,
            'nodes_to_keep': nodes_to_keep,
            'projected_loss': current_loss,
            'component_increase': final_result['disconnected_components'] - original_components
        }
        
        logger.info(f"策略生成完成，建议移除 {len(nodes_to_remove)} 个节点，预计损失: {current_loss:.2%}")
        return strategy

def create_sample_knowledge_graph(
    num_nodes: int = 30,
    num_domains: int = 3,
    edge_prob: float = 0.1
) -> Tuple[nx.Graph, Dict[NodeId, List[str]], Dict[NodeId, List[datetime]]]:
    """
    创建示例知识图谱，用于测试和演示。
    
    参数:
        num_nodes: 节点数量
        num_domains: 领域数量
        edge_prob: 边生成概率
        
    返回:
        (graph, domain_tags, access_history)
    """
    import random
    from datetime import timedelta
    
    # 创建随机图
    G = nx.erdos_renyi_graph(num_nodes, edge_prob)
    
    # 为节点分配领域标签
    domain_names = [f"domain_{chr(65+i)}" for i in range(num_domains)]
    domain_tags = {}
    
    for node in G.nodes():
        # 随机分配1-2个领域标签
        num_tags = random.randint(1, 2)
        tags = random.sample(domain_names, num_tags)
        domain_tags[node] = tags
    
    # 创建模拟访问历史
    access_history = {}
    now = datetime.now()
    
    for node in G.nodes():
        # 随机生成0-20次访问
        num_access = random.randint(0, 20)
        access_times = []
        
        for _ in range(num_access):
            days_ago = random.randint(1, 365)
            access_time = now - timedelta(days=days_ago)
            access_times.append(access_time)
        
        access_history[node] = sorted(access_times)
    
    return G, domain_tags, access_history

def main() -> None:
    """主函数，演示认知碰撞评估器的使用方法。"""
    # 创建示例数据
    print("创建示例知识图谱...")
    G, domain_tags, access_history = create_sample_knowledge_graph(num_nodes=50)
    
    # 初始化评估器
    evaluator = CognitiveCollisionEvaluator(
        graph=G,
        domain_tags=domain_tags,
        access_history=access_history,
        decay_factor=0.9
    )
    
    # 计算综合指标
    print("\n计算节点综合认知价值指标...")
    metrics = evaluator.calculate_comprehensive_metrics()
    
    # 打印部分结果
    print("\n节点指标示例 (前5个节点):")
    for i, (node, node_metrics) in enumerate(metrics.items()):
        if i >= 5:
            break
        print(f"节点 {node}:")
        print(f"  访问次数: {node_metrics['access_count']}")
        print(f"  加权访问: {node_metrics['weighted_access']:.2f}")
        print(f"  介数中心性: {node_metrics['betweenness_centrality']:.4f}")
        print(f"  领域交叉度: {node_metrics['domain_crossing']:.2f}")
        print(f"  认知价值: {node_metrics['cognitive_value']:.4f}")
    
    # 识别脆弱节点
    print("\n识别脆弱节点...")
    vulnerable_nodes = evaluator.identify_vulnerable_nodes(metrics)
    print(f"发现 {len(vulnerable_nodes)} 个脆弱节点: {vulnerable_nodes[:10]}...")
    
    # 生成淘汰策略
    print("\n生成淘汰策略...")
    strategy = evaluator.generate_pruning_strategy(
        metrics,
        innovation_loss_tolerance=0.15,
        max_nodes_to_remove=15
    )
    
    print(f"\n淘汰策略:")
    print(f"建议移除的节点数: {len(strategy['nodes_to_remove'])}")
    print(f"预计创新能力损失: {strategy['projected_loss']:.2%}")
    print(f"连通分量增加: {strategy['component_increase']}")
    print(f"建议移除的节点: {strategy['nodes_to_remove'][:10]}...")

if __name__ == "__main__":
    main()