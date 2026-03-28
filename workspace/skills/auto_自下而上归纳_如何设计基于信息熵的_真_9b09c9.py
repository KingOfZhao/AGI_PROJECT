"""
Module: auto_bottom_up_induction.py
Description: 【自下而上归纳】基于信息熵的动态聚类算法，用于从离散SKILL节点中自动涌现高层级抽象概念。
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from scipy.spatial.distance import jensenshannon
from scipy.stats import entropy
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 节点的唯一标识符。
        name (str): 节点名称（如 '切菜', '备菜'）。
        feature_vector (np.ndarray): 语义或实践特征向量（归一化概率分布）。
        children (Set[str]): 子节点ID集合，如果是原子节点则为空。
        level (int): 节点层级，0为底层技能。
    """
    id: str
    name: str
    feature_vector: np.ndarray
    children: Set[str] = field(default_factory=set)
    level: int = 0

    def __post_init__(self):
        """数据验证：确保特征向量是有效的概率分布。"""
        if not isinstance(self.feature_vector, np.ndarray):
            raise TypeError("feature_vector 必须是 numpy ndarray 类型")
        
        if not np.allclose(self.feature_vector.sum(), 1.0, atol=1e-5):
            logger.warning(f"节点 {self.id} 的特征向量总和不为1，正在自动归一化...")
            self.feature_vector = self.feature_vector / self.feature_vector.sum()
            
        if np.any(self.feature_vector < 0):
            raise ValueError("特征向量包含负值，无效的概率分布")


class CognitiveNetwork:
    """
    认知网络类，管理技能节点的聚合与层级结构演化。
    实现了基于信息熵（Jensen-Shannon Divergence）的动态聚类。
    """

    def __init__(self, entropy_threshold: float = 0.15, min_samples: int = 2):
        """
        初始化认知网络。
        
        Args:
            entropy_threshold (float): 聚类融合的熵距离阈值。值越小，融合条件越严格。
            min_samples (int): 形成一个新概念所需的最小节点数。
        """
        self.nodes: Dict[str, SkillNode] = {}
        self.entropy_threshold = entropy_threshold
        self.min_samples = min_samples
        self.next_node_id = 0
        logger.info(f"认知网络初始化完成，熵阈值={entropy_threshold}")

    def add_nodes(self, nodes: List[SkillNode]) -> None:
        """批量添加节点到网络中。"""
        for node in nodes:
            if node.id in self.nodes:
                logger.warning(f"节点ID {node.id} 已存在，跳过覆盖。")
                continue
            self.nodes[node.id] = node
        logger.info(f"成功添加 {len(nodes)} 个节点，当前总节点数: {len(self.nodes)}")

    def _calculate_semantic_overlap(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        辅助函数：计算两个概率分布之间的语义重叠度（基于Jensen-Shannon散度）。
        
        Args:
            p (np.ndarray): 概率分布A。
            q (np.ndarray): 概率分布B。
            
        Returns:
            float: JS散度值，范围[0, 1]。值越小表示重叠度越高。
        """
        if p.shape != q.shape:
            raise ValueError("特征向量维度不匹配")
        
        # 计算JS散度 (scipy的jensenshannon返回的是距离，即sqrt(JS))
        # 这里直接使用JS散度作为距离度量
        js_distance = jensenshannon(p, q, base=2)
        
        # 处理NaN情况（通常在两个向量都为0时出现）
        if np.isnan(js_distance):
            return 0.0  # 视为完全一致
        
        return float(js_distance)

    def _merge_vectors(self, vectors: List[np.ndarray]) -> np.ndarray:
        """
        辅助函数：将多个特征向量融合为一个，代表抽象概念。
        使用几何中心法，保持归一化。
        """
        stacked = np.vstack(vectors)
        merged = np.mean(stacked, axis=0)
        # 再次归一化以确保是有效的概率分布
        return merged / merged.sum()

    def induce_abstractions(self) -> Dict[str, SkillNode]:
        """
        核心函数：执行自下而上的归纳聚类。
        
        流程:
        1. 计算所有活跃节点（level=0或未标记为已处理）两两之间的JS散度。
        2. 寻找距离小于阈值的节点对。
        3. 构建连通图，找出强相关的簇。
        4. 将簇融合为新的父节点（抽象概念）。
        5. 更新网络结构，降低系统熵。
        
        Returns:
            Dict[str, SkillNode]: 新生成的抽象节点字典。
        """
        logger.info("开始执行自下而上归纳算法...")
        
        # 获取当前层级的叶子节点（简化处理，实际中应支持多层级迭代）
        # 这里假设我们对当前所有未合并的节点进行操作
        current_node_ids = [nid for nid, node in self.nodes.items() if node.level == 0]
        
        if len(current_node_ids) < self.min_samples:
            logger.info("节点数量不足，无法进行聚类。")
            return {}

        # 1. 构建相似度矩阵 (距离矩阵)
        n = len(current_node_ids)
        # 仅存储上三角矩阵以节省内存
        distances = np.full((n, n), np.inf)
        
        logger.info(f"计算 {n} 个节点的语义距离矩阵...")
        
        for i in range(n):
            for j in range(i + 1, n):
                node_i = self.nodes[current_node_ids[i]]
                node_j = self.nodes[current_node_ids[j]]
                dist = self._calculate_semantic_overlap(node_i.feature_vector, node_j.feature_vector)
                distances[i, j] = dist
                distances[j, i] = dist

        # 2. 寻找高重叠度邻居 (基于阈值)
        adjacency_list = defaultdict(set)
        for i in range(n):
            for j in range(i + 1, n):
                if distances[i, j] < self.entropy_threshold:
                    adjacency_list[i].add(j)
                    adjacency_list[j].add(i)

        # 3. 发现连通分量 (简单的BFS聚类)
        visited = set()
        clusters = []
        
        for i in range(n):
            if i not in visited:
                # 只有包含足够邻居的节点才被视为核心
                if len(adjacency_list[i]) >= 1: # 至少有一个朋友
                    queue = [i]
                    current_cluster = set()
                    while queue:
                        curr = queue.pop(0)
                        if curr not in visited:
                            visited.add(curr)
                            current_cluster.add(curr)
                            # 添加未访问的邻居
                            for neighbor in adjacency_list[curr]:
                                if neighbor not in visited:
                                    queue.append(neighbor)
                    
                    if len(current_cluster) >= self.min_samples:
                        clusters.append(current_cluster)
                else:
                    visited.add(i) # 标记孤立点为已访问

        logger.info(f"检测到 {len(clusters)} 个潜在的抽象概念簇。")

        # 4. 生成父节点
        new_abstractions = {}
        for cluster_indices in clusters:
            cluster_node_ids = [current_node_ids[idx] for idx in cluster_indices]
            cluster_nodes = [self.nodes[nid] for nid in cluster_node_ids]
            
            # 生成新节点ID和名称
            new_id = f"abstract_{self.next_node_id}"
            self.next_node_id += 1
            names = [n.name for n in cluster_nodes]
            new_name = f"Concept_({'|'.join(names[:2])}...)" if len(names) > 2 else f"Concept_({'|'.join(names)})"
            
            # 融合特征向量
            merged_vector = self._merge_vectors([n.feature_vector for n in cluster_nodes])
            
            # 计算该次融合带来的熵减（信息增益）
            # 简单指标：簇内平均距离 vs 阈值
            cluster_entropy = np.mean([distances[i, j] for i in cluster_indices for j in cluster_indices if i < j])
            
            # 创建新节点
            parent_node = SkillNode(
                id=new_id,
                name=new_name,
                feature_vector=merged_vector,
                children=set(cluster_node_ids),
                level=1 # 提升层级
            )
            
            # 更新旧节点的层级关系（标记为非叶子节点）
            for nid in cluster_node_ids:
                self.nodes[nid].level = -1 # 标记为已归约，防止下一轮重复聚类
            
            self.nodes[new_id] = parent_node
            new_abstractions[new_id] = parent_node
            logger.info(f"涌现新概念: {new_name} (包含 {len(cluster_nodes)} 个技能, 内部熵: {cluster_entropy:.4f})")

        return new_abstractions

# 使用示例
if __name__ == "__main__":
    # 模拟生成416个离散的Skill节点数据
    # 假设特征向量维度为64维
    NUM_NODES = 416
    VECTOR_DIM = 64
    
    # 生成随机数据，但人为制造一些强相关的簇（例如：'切菜'和'备菜'向量非常接近）
    np.random.seed(42)
    mock_skills = []
    
    # 基础噪音节点
    for i in range(400):
        vec = np.random.rand(VECTOR_DIM)
        mock_skills.append(SkillNode(id=f"skill_{i}", name=f"Action_{i}", feature_vector=vec))

    # 制造强相关节点组 (模拟冗余)
    base_vec_cooking = np.random.rand(VECTOR_DIM)
    mock_skills.append(SkillNode(id="s_cut", name="Cutting", feature_vector=base_vec_cooking + np.random.normal(0, 0.01, VECTOR_DIM)))
    mock_skills.append(SkillNode(id="s_prep", name="Preping", feature_vector=base_vec_cooking + np.random.normal(0, 0.01, VECTOR_DIM)))
    mock_skills.append(SkillNode(id="s_chop", name="Chopping", feature_vector=base_vec_cooking + np.random.normal(0, 0.01, VECTOR_DIM)))

    base_vec_code = np.random.rand(VECTOR_DIM)
    mock_skills.append(SkillNode(id="s_py", name="Python", feature_vector=base_vec_code + np.random.normal(0, 0.01, VECTOR_DIM)))
    mock_skills.append(SkillNode(id="s_jv", name="Java", feature_vector=base_vec_code + np.random.normal(0, 0.05, VECTOR_DIM)))

    # 初始化网络
    # 阈值设为0.2，容忍一定的噪声但仍能聚合相似概念
    network = CognitiveNetwork(entropy_threshold=0.2, min_samples=2)
    network.add_nodes(mock_skills)

    # 执行归纳
    new_concepts = network.induce_abstractions()

    print("\n--- 涌现结果 ---")
    for nid, node in new_concepts.items():
        print(f"新概念节点: {node.name}")
        print(f"  包含子节点: {node.children}")