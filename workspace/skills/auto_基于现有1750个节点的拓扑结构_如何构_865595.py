"""
模块名称: cognitive_potential_optimizer
描述: 基于大规模图拓扑结构构建动态'认知势能'算法，用于识别结构洞并优化网络连接。

该算法旨在解决以下问题：
1. 在具有1750个节点的知识图谱中识别被高频访问但缺乏跨域连接的孤立节点簇。
2. 计算在何处建立新连接能最大程度降低网络的平均最短路径长度(ASPL)。
3. 为AGI系统生成提问策略，以填补知识空白。

核心概念：
- 认知势能: 结合节点中心性(流量)与聚类系数(局部封闭性)的指标。
- 结构洞: 连接不同紧密社群但本身连接稀疏的位置。
"""

import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CognitivePotentialAnalyzer:
    """
    认知势能分析器。
    
    用于分析图网络中的结构洞，并推荐最优的连接建立点。
    """
    
    def __init__(self, graph: nx.Graph, k_core_clusters: int = 3):
        """
        初始化分析器。
        
        Args:
            graph (nx.Graph): NetworkX图对象，代表拓扑结构。
            k_core_clusters (int): 用于社区检测的k-core分解参数。
        """
        if not isinstance(graph, nx.Graph):
            raise TypeError("输入必须是networkx.Graph对象")
        if graph.number_of_nodes() == 0:
            raise ValueError("图不能为空")
            
        self.graph = graph
        self.k_core_clusters = k_core_clusters
        self._cache = {} # 用于缓存计算结果
        
        logger.info(f"初始化分析器: 节点数 {graph.number_of_nodes()}, 边数 {graph.number_of_edges()}")

    def _validate_node(self, node_id: int) -> bool:
        """
        辅助函数：验证节点是否存在于图中。
        
        Args:
            node_id (int): 节点标识符
            
        Returns:
            bool: 节点是否存在
        """
        if node_id not in self.graph:
            logger.warning(f"节点 {node_id} 不在图中")
            return False
        return True

    def _calculate_structural_hole_score(self, node_u: int, node_v: int) -> float:
        """
        辅助函数：计算两个非邻接节点之间的结构洞得分。
        
        得分基于以下逻辑的简化版：
        - 如果两个节点属于不同的紧密社群，但它们之间的最短路径较长。
        - 连接它们将显著减少路径长度。
        
        Args:
            node_u (int): 节点u ID
            node_v (int): 节点v ID
            
        Returns:
            float: 结构洞潜力得分 (越高表示越值得连接)
        """
        try:
            # 如果已经连接，得分为0
            if self.graph.has_edge(node_u, node_v):
                return 0.0
                
            # 计算最短路径长度 (若不连通，设为较大值)
            try:
                spl = nx.shortest_path_length(self.graph, source=node_u, target=node_v)
            except nx.NetworkXNoPath:
                spl = 10  # 惩罚值，表示不连通

            # 计算并集邻居数 (用于衡量连接后的局部融合度)
            neighbors_u = set(self.graph.neighbors(node_u))
            neighbors_v = set(self.graph.neighbors(node_v))
            common_neighbors = len(neighbors_u.intersection(neighbors_v))
            
            # 惩罚共同邻居过多的连接（因为那意味着它们在同一个紧密簇内，不是结构洞）
            # 奖励路径长且共同邻居少的连接
            score = (spl ** 1.5) / (1 + common_neighbors)
            return score
            
        except Exception as e:
            logger.error(f"计算结构洞得分出错 ({node_u}, {node_v}): {e}")
            return 0.0

    def calculate_cognitive_potential_field(self) -> Dict[int, float]:
        """
        核心函数 1: 计算网络中每个节点的认知势能。
        
        认知势能 = (访问频率/介数中心性) * (1 - 聚类系数)。
        高势能节点是那些流量大但处于局部紧密团伙边缘或处于连接瓶颈的节点。
        
        Returns:
            Dict[int, float]: 节点ID到其认知势能得分的映射。
        """
        logger.info("开始计算认知势能场...")
        
        # 1. 计算介数中心性 (代表流量/访问频率)
        # 对于1750个节点，exact可能较慢，可以使用k约等于节点数的采样或近似算法
        logger.debug("计算介数中心性...")
        betweenness = nx.betweenness_centrality(self.graph, normalized=True, k=min(500, self.graph.number_of_nodes()))
        
        # 2. 计算聚类系数 (代表局部聚集度)
        logger.debug("计算聚类系数...")
        clustering = nx.clustering(self.graph)
        
        potentials = {}
        for node in self.graph.nodes():
            b = betweenness.get(node, 0)
            c = clustering.get(node, 0)
            
            # 势能公式：高流量 + 低聚类 = 高势能（容易形成结构洞）
            # 加上epsilon防止除零，但(1-c)本身处理了聚类系数为1的情况
            potential = b * (1 - c)
            potentials[node] = potential
            
        # 归一化
        max_pot = max(potentials.values()) if potentials else 1.0
        if max_pot > 0:
            potentials = {k: v/max_pot for k, v in potentials.items()}
            
        self._cache['potentials'] = potentials
        logger.info("认知势能计算完成。")
        return potentials

    def identify_structural_bridges(self, top_k: int = 20) -> List[Tuple[float, int, int]]:
        """
        核心函数 2: 识别具体的结构洞连接建议。
        
        遍历高势能节点，寻找能最大程度降低平均最短路径的非存在边。
        
        Args:
            top_k (int): 返回得分最高的前k个建议连接。
            
        Returns:
            List[Tuple[float, int, int]]: (得分, 节点A, 节点B) 的列表。
        """
        logger.info(f"开始识别结构洞，查找 Top {top_k} 候选连接...")
        
        if 'potentials' not in self._cache:
            self.calculate_cognitive_potential_field()
        
        potentials = self._cache['potentials']
        
        # 筛选出势能前10%的节点作为候选源
        sorted_nodes = sorted(potentials.items(), key=lambda x: x[1], reverse=True)
        candidate_count = int(len(sorted_nodes) * 0.1)
        high_potential_nodes = [n[0] for n in sorted_nodes[:candidate_count]]
        
        suggestions = []
        
        # 为了性能，我们不完全计算所有节点对的ASPL，而是基于启发式评分
        # 获取所有连通组件
        components = list(nx.connected_components(self.graph))
        if len(components) > 1:
            logger.warning(f"图非连通，包含 {len(components)} 个组件。优先连接组件。")
            # 简单策略：连接不同组件中势能最高的节点
            if len(components) >= 2:
                n1 = max(components[0], key=lambda x: potentials.get(x, 0))
                n2 = max(components[1], key=lambda x: potentials.get(x, 0))
                suggestions.append((100.0, n1, n2)) # 极高优先级

        # 针对连通图内部的优化
        # 采样分析：在候选节点和其他非邻接节点间寻找最佳连接
        # 注意：对于1750节点，全量O(N^2)最短路径计算成本极高，
        # 这里使用 _calculate_structural_hole_score 进行启发式估算
        
        count = 0
        for u in high_potential_nodes:
            # 随机采样一部分其他节点或基于度中心性选择目标
            # 这里简化为遍历非邻居的高势能节点
            non_neighbors = list(set(self.graph.nodes()) - set(self.graph.neighbors(u)) - {u})
            
            # 随机抽样以控制计算时间
            sample_size = min(50, len(non_neighbors))
            sampled_targets = np.random.choice(non_neighbors, size=sample_size, replace=False)
            
            for v in sampled_targets:
                if u < v: # 避免重复计算 (u,v) 和 (v,u)
                    score = self._calculate_structural_hole_score(u, v)
                    # 结合认知势能
                    combined_score = score * (potentials[u] + potentials[v])
                    suggestions.append((combined_score, u, v))
                    
        # 排序并返回Top K
        suggestions.sort(key=lambda x: x[0], reverse=True)
        logger.info(f"识别完成，共生成 {len(suggestions)} 个建议。")
        
        return suggestions[:top_k]

def generate_mock_topology(num_nodes: int = 1750) -> nx.Graph:
    """
    辅助函数：生成模拟的拓扑结构（用于测试）。
    生成包含幂律分布特征的Barabási-Albert优先连接图。
    """
    logger.info(f"生成模拟拓扑: {num_nodes} 节点...")
    # m=3 每个新节点附着3个边，这会产生自然的结构洞
    G = nx.barabasi_albert_graph(n=num_nodes, m=3, seed=42)
    return G

if __name__ == "__main__":
    # 使用示例
    try:
        # 1. 准备数据 (这里使用模拟数据，实际应用中应加载真实图谱)
        # 假设我们需要1750个节点
        mock_graph = generate_mock_topology(1750)
        
        # 2. 初始化分析器
        analyzer = CognitivePotentialAnalyzer(graph=mock_graph)
        
        # 3. 计算认知势能
        potentials = analyzer.calculate_cognitive_potential_field()
        print(f"Top 5 势能节点: {sorted(potentials.items(), key=lambda x: x[1], reverse=True)[:5]}")
        
        # 4. 识别结构洞
        bridges = analyzer.identify_structural_bridges(top_k=5)
        
        print("\n--- 推荐建立的新连接 (结构洞) ---")
        print("Score\t\tNode A\t\tNode B")
        for score, u, v in bridges:
            print(f"{score:.4f}\t\t{u}\t\t{v}")
            
        # 5. (可选) 验证连接后的ASPL变化
        # 这部分仅作为演示，实际生产中需谨慎计算ASPL
        if bridges:
            _, u, v = bridges[0]
            initial_aspl = nx.average_shortest_path_length(mock_graph) if nx.is_connected(mock_graph) else float('inf')
            
            # 模拟添加边
            mock_graph.add_edge(u, v)
            if nx.is_connected(mock_graph):
                new_aspl = nx.average_shortest_path_length(mock_graph)
                logger.info(f"验证: 添加边 ({u},{v}) 后，ASPL 变化: {initial_aspl:.4f} -> {new_aspl:.4f}")
            
    except Exception as e:
        logger.error(f"运行时发生错误: {e}", exc_info=True)