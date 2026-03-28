"""
模块名称: auto_针对2978个认知节点的图拓扑结构分析_ffbd42
描述: 针对2978个认知节点的图拓扑结构分析工具。

本模块用于构建加权有向图，分析认知节点的拓扑结构。
主要目标是识别“理论僵尸”节点——即在逻辑链中处于核心位置（高PageRank值）
但在应用实践中极少被调用的节点。这些节点占用了推理资源但缺乏实践反馈。

主要功能:
1. 构建带有认知依赖强度的加权有向图。
2. 计算节点的理论重要性。
3. 识别并清洗低频调用的核心理论节点。

Author: AGI System
Version: 1.0.0
"""

import logging
import sys
from typing import Dict, List, Tuple, Set, Any, Optional

import networkx as nx
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_NODE_COUNT = 2978
MIN_DEPENDENCY_WEIGHT = 0.0
MAX_DEPENDENCY_WEIGHT = 1.0


class CognitiveGraphAnalyzer:
    """
    认知图拓扑分析器。
    
    用于构建、分析认知节点网络，并识别低效用的“理论僵尸”节点。
    """

    def __init__(self, node_count: int = DEFAULT_NODE_COUNT):
        """
        初始化分析器。

        Args:
            node_count (int): 图中预期的节点数量，默认为2978。
        """
        self.node_count = node_count
        self.graph: Optional[nx.DiGraph] = None
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性。"""
        if not isinstance(self.node_count, int) or self.node_count <= 0:
            error_msg = f"节点数量必须是正整数，得到: {self.node_count}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info(f"初始化认知图分析器，预期节点数: {self.node_count}")

    def construct_weighted_graph(
        self,
        edges: List[Tuple[str, str, float]],
        node_attributes: Dict[str, Dict[str, Any]]
    ) -> nx.DiGraph:
        """
        构建加权有向图。

        Args:
            edges (List[Tuple[str, str, float]]): 边列表，格式为 [(源节点, 目标节点, 权重), ...]。
                                                  权重代表认知依赖强度 (0.0 to 1.0)。
            node_attributes (Dict[str, Dict[str, Any]]): 节点属性字典。
                                                  必须包含 'theoretical_importance' 和 'invocation_frequency'。

        Returns:
            nx.DiGraph: 构建完成的 NetworkX 有向图对象。

        Raises:
            ValueError: 如果输入数据格式不正确或缺失关键字段。
        """
        logger.info("开始构建加权有向图...")
        self.graph = nx.DiGraph()

        # 边界检查：检查数据量是否与预期大致相符（可选的严格检查）
        if len(node_attributes) < self.node_count * 0.9:
            logger.warning(f"输入的节点属性数量 ({len(node_attributes)}) 少于预期 ({self.node_count})。")

        # 添加节点和属性
        missing_attrs = []
        for node_id, attrs in node_attributes.items():
            if 'theoretical_importance' not in attrs or 'invocation_frequency' not in attrs:
                missing_attrs.append(node_id)
                continue
            
            # 数据清洗：确保数值类型正确
            clean_attrs = {
                'theoretical_importance': float(attrs.get('theoretical_importance', 0.0)),
                'invocation_frequency': int(attrs.get('invocation_frequency', 0))
            }
            self.graph.add_node(node_id, **clean_attrs)

        if missing_attrs:
            logger.warning(f"发现 {len(missing_attrs)} 个节点缺失关键属性，已跳过。")

        # 添加边
        valid_edges = 0
        for u, v, w in edges:
            if not (MIN_DEPENDENCY_WEIGHT <= w <= MAX_DEPENDENCY_WEIGHT):
                logger.debug(f"边 ({u}->{v}) 权重 {w} 超出范围，进行截断。")
                w = np.clip(w, MIN_DEPENDENCY_WEIGHT, MAX_DEPENDENCY_WEIGHT)
            
            if self.graph.has_node(u) and self.graph.has_node(v):
                self.graph.add_edge(u, v, weight=w)
                valid_edges += 1

        logger.info(f"图构建完成: {self.graph.number_of_nodes()} 个节点, {valid_edges} 条有效边。")
        return self.graph

    def identify_zombie_nodes(
        self,
        pagerank_damping: float = 0.85,
        importance_threshold: float = 0.75,
        frequency_percentile: float = 0.10
    ) -> List[Tuple[str, float, int]]:
        """
        识别“理论僵尸”节点。

        计算流程:
        1. 计算加权 PageRank 以确定拓扑核心性。
        2. 结合节点的 'theoretical_importance'。
        3. 筛选出高核心性但低 'invocation_frequency' 的节点。

        Args:
            pagerank_damping (float): PageRank 阻尼系数。
            importance_threshold (float): 节点被认为是“核心”的 PageRank 分位数阈值 (0-1)。
            frequency_percentile (float): 节点被认为是“低频”的调用频率分位数阈值 (0-1)。

        Returns:
            List[Tuple[str, float, int]]: 僵尸节点列表，格式为 [(节点ID, 综合重要性得分, 调用频率), ...]。
        
        Raises:
            RuntimeError: 如果图尚未构建。
        """
        if self.graph is None or self.graph.number_of_nodes() == 0:
            raise RuntimeError("图未构建或为空，请先调用 construct_weighted_graph。")

        logger.info("开始计算 PageRank...")
        try:
            # 计算加权 PageRank
            pagerank_scores = nx.pagerank(self.graph, alpha=pagerank_damping, weight='weight')
        except Exception as e:
            logger.error(f"PageRank 计算失败: {e}")
            raise

        # 辅助函数：归一化处理
        pr_values = np.array(list(pagerank_scores.values()))
        freq_values = np.array([d['invocation_frequency'] for n, d in self.graph.nodes(data=True)])

        # 计算阈值
        pr_threshold_val = np.percentile(pr_values, importance_threshold * 100)
        freq_threshold_val = np.percentile(freq_values, frequency_percentile * 100)

        logger.info(f"筛选条件 - PageRank > {pr_threshold_val:.6f} (Top {int((1-importance_threshold)*100)}%)")
        logger.info(f"筛选条件 - 频率 <= {freq_threshold_val} (Bottom {int(frequency_percentile*100)}%)")

        zombies = []

        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            pr_score = pagerank_scores.get(node_id, 0)
            frequency = node_data['invocation_frequency']
            base_importance = node_data['theoretical_importance']

            # 僵尸节点判定逻辑：
            # 1. 拓扑位置重要 (高 PageRank)
            # 2. 实际调用极少 (低 Frequency)
            if pr_score >= pr_threshold_val and frequency <= freq_threshold_val:
                # 计算一个综合得分用于排序，越高代表越“僵”
                # 这里的逻辑是：理论地位越高、调用越少，越是需要清洗的目标
                # 使用 log1p 处理频率以避免除零，并反转逻辑
                zombie_score = pr_score * base_importance
                zombies.append((node_id, zombie_score, frequency))

        # 按综合得分降序排序
        zombies.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"识别出 {len(zombies)} 个理论僵尸节点。")
        return zombies


def _generate_mock_data(analyzer: CognitiveGraphAnalyzer) -> Tuple[List[Tuple[str, str, float]], Dict[str, Dict[str, Any]]]:
    """
    辅助函数：生成模拟数据用于测试。
    
    生成指定数量的节点和随机的依赖关系，模拟真实场景。
    """
    logger.info("正在生成模拟测试数据...")
    node_ids = [f"cog_node_{i:04d}" for i in range(analyzer.node_count)]
    
    # 1. 生成节点属性
    # 使用 Zipf 分布模拟调用频率（少数节点被大量调用，大量节点很少被调用）
    # 使用正态分布模拟理论重要性
    nodes_attrs = {}
    rng = np.random.default_rng(42)
    
    # 生成频率：大多数节点频率很低
    frequencies = rng.zipf(a=1.5, size=analyzer.node_count)
    # 生成理论重要性：正态分布
    importances = rng.normal(loc=0.5, scale=0.2, size=analyzer.node_count)
    
    for i, nid in enumerate(node_ids):
        nodes_attrs[nid] = {
            'theoretical_importance': np.clip(importances[i], 0, 1),
            'invocation_frequency': int(frequencies[i])
        }

    # 2. 生成边 (模拟无标度网络特性，少数核心节点拥有大量连接)
    edges = []
    # 选取前 10% 的节点作为 Hub
    hub_nodes = node_ids[:int(analyzer.node_count * 0.1)]
    
    for nid in node_ids:
        # 每个节点随机连接到 2-5 个其他节点
        num_edges = rng.integers(2, 6)
        # 倾向于连接到 Hub 节点（构造高 PageRank 节点）
        targets = rng.choice(hub_nodes, size=num_edges, replace=False)
        
        for target in targets:
            if nid != target:
                weight = rng.random()
                edges.append((nid, target, weight))
                
    return edges, nodes_attrs

def main():
    """
    主函数：演示模块的使用方法。
    """
    try:
        # 1. 初始化
        analyzer = CognitiveGraphAnalyzer(node_count=2978)
        
        # 2. 准备数据 (这里使用模拟数据)
        mock_edges, mock_attrs = _generate_mock_data(analyzer)
        
        # 3. 构建图
        analyzer.construct_weighted_graph(mock_edges, mock_attrs)
        
        # 4. 分析并识别僵尸节点
        # 寻找 PageRank 前 25% 但调用频率处于后 10% 的节点
        zombie_nodes = analyzer.identify_zombie_nodes(
            importance_threshold=0.75, 
            frequency_percentile=0.10
        )
        
        # 5. 输出结果
        print("\n=== 识别结果: Top 10 '理论僵尸' 节点 ===")
        print(f"{'Node ID':<20} | {'Zombie Score':<15} | {'Frequency':<10}")
        print("-" * 50)
        for node, score, freq in zombie_nodes[:10]:
            print(f"{node:<20} | {score:.6f}        | {freq:<10}")
            
        print(f"\n总共识别出 {len(zombie_nodes)} 个待清洗节点。")
        
    except ValueError as ve:
        logger.error(f"参数验证错误: {ve}")
    except Exception as e:
        logger.error(f"运行时发生未捕获异常: {e}", exc_info=True)

if __name__ == "__main__":
    main()