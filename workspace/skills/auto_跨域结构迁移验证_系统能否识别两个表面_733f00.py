"""
跨域结构迁移验证模块

该模块实现了跨领域概念间的深层拓扑结构同构识别与映射生成功能。
主要应用于认知科学领域，用于验证AGI系统在不同领域间发现深层结构相似性的能力。

核心功能：
1. 解析输入概念的结构特征
2. 识别跨领域概念间的拓扑同构性
3. 生成有效的结构映射方程
4. 验证映射的一致性和有效性

典型用例：
    >>> validator = CrossDomainStructureValidator()
    >>> concept_a = {"nodes": [...], "edges": [...]}
    >>> concept_b = {"nodes": [...], "edges": [...]}
    >>> result = validator.validate_structure_mapping(concept_a, concept_b)
    >>> print(result["isomorphic"])
"""

import logging
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict
import numpy as np
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """表示概念结构中的节点数据类"""
    id: str
    properties: Dict[str, Union[str, int, float]]
    domain: str


@dataclass
class ConceptEdge:
    """表示概念结构中的边数据类"""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0


class CrossDomainStructureValidator:
    """
    跨域结构迁移验证器
    
    该类实现了识别不同领域概念间深层拓扑结构同构性的功能，
    并能生成有效的结构映射方程。
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化验证器
        
        Args:
            similarity_threshold: 结构相似度阈值，高于此值认为结构同构
        """
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("相似度阈值必须在0到1之间")
            
        self.similarity_threshold = similarity_threshold
        self._node_map = {}
        self._edge_map = {}
        logger.info("初始化跨域结构验证器，阈值: %.2f", similarity_threshold)
    
    def _validate_input_structure(self, structure: Dict) -> None:
        """
        验证输入概念结构的有效性
        
        Args:
            structure: 要验证的概念结构
            
        Raises:
            ValueError: 如果结构无效
        """
        if not isinstance(structure, dict):
            raise ValueError("输入结构必须是字典类型")
            
        if "nodes" not in structure or "edges" not in structure:
            raise ValueError("输入结构必须包含'nodes'和'edges'键")
            
        if not structure["nodes"]:
            raise ValueError("节点列表不能为空")
            
        # 检查节点ID唯一性
        node_ids = [node["id"] for node in structure["nodes"]]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("节点ID必须唯一")
    
    def _build_adjacency_matrix(self, edges: List[Dict], node_ids: List[str]) -> np.ndarray:
        """
        构建邻接矩阵表示概念结构
        
        Args:
            edges: 边列表
            node_ids: 节点ID列表
            
        Returns:
            邻接矩阵
        """
        size = len(node_ids)
        node_index = {node_id: idx for idx, node_id in enumerate(node_ids)}
        adj_matrix = np.zeros((size, size))
        
        for edge in edges:
            src_idx = node_index[edge["source"]]
            tgt_idx = node_index[edge["target"]]
            adj_matrix[src_idx][tgt_idx] = edge.get("weight", 1.0)
            
        return adj_matrix
    
    def extract_structural_features(self, structure: Dict) -> Dict:
        """
        从概念结构中提取拓扑特征
        
        Args:
            structure: 概念结构字典
            
        Returns:
            包含拓扑特征的字典
            
        Example:
            >>> features = validator.extract_structural_features(bio_immune_system)
            >>> print(features["degree_distribution"])
        """
        self._validate_input_structure(structure)
        
        node_ids = [node["id"] for node in structure["nodes"]]
        adj_matrix = self._build_adjacency_matrix(structure["edges"], node_ids)
        
        # 计算度分布
        in_degree = np.sum(adj_matrix, axis=0)
        out_degree = np.sum(adj_matrix, axis=1)
        degree_distribution = (in_degree + out_degree).tolist()
        
        # 计算聚类系数
        clustering_coeffs = []
        for i in range(len(node_ids)):
            neighbors = np.where(adj_matrix[i] > 0)[0]
            if len(neighbors) < 2:
                clustering_coeffs.append(0.0)
                continue
                
            actual_edges = 0
            for j in neighbors:
                for k in neighbors:
                    if adj_matrix[j][k] > 0:
                        actual_edges += 1
                        
            possible_edges = len(neighbors) * (len(neighbors) - 1)
            clustering_coeffs.append(actual_edges / possible_edges if possible_edges > 0 else 0.0)
        
        # 计算路径长度
        path_lengths = self._calculate_all_path_lengths(adj_matrix)
        
        return {
            "node_ids": node_ids,
            "degree_distribution": degree_distribution,
            "clustering_coefficients": clustering_coeffs,
            "path_lengths": path_lengths,
            "adjacency_matrix": adj_matrix
        }
    
    def _calculate_all_path_lengths(self, adj_matrix: np.ndarray) -> Dict[Tuple[int, int], float]:
        """
        计算所有节点对之间的最短路径长度
        
        Args:
            adj_matrix: 邻接矩阵
            
        Returns:
            节点对到路径长度的映射
        """
        size = len(adj_matrix)
        path_lengths = {}
        
        # 使用Floyd-Warshall算法计算最短路径
        dist = np.full((size, size), np.inf)
        np.fill_diagonal(dist, 0)
        dist[adj_matrix > 0] = 1
        
        for k in range(size):
            for i in range(size):
                for j in range(size):
                    if dist[i][j] > dist[i][k] + dist[k][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
        
        for i in range(size):
            for j in range(size):
                if dist[i][j] < np.inf:
                    path_lengths[(i, j)] = dist[i][j]
                    
        return path_lengths
    
    def calculate_structural_similarity(self, features_a: Dict, features_b: Dict) -> float:
        """
        计算两个概念结构之间的相似度
        
        Args:
            features_a: 第一个概念的特征
            features_b: 第二个概念的特征
            
        Returns:
            结构相似度分数 (0-1)
            
        Example:
            >>> sim = validator.calculate_structural_similarity(features_a, features_b)
            >>> print(f"结构相似度: {sim:.2f}")
        """
        # 检查节点数量是否接近
        size_a = len(features_a["node_ids"])
        size_b = len(features_b["node_ids"])
        size_ratio = min(size_a, size_b) / max(size_a, size_b)
        
        if size_ratio < 0.5:
            logger.warning("节点数量差异过大，相似度可能较低")
            return 0.0
        
        # 比较度分布相似性
        deg_dist_a = np.array(features_a["degree_distribution"])
        deg_dist_b = np.array(features_b["degree_distribution"])
        
        # 标准化度分布
        if np.max(deg_dist_a) > 0:
            deg_dist_a = deg_dist_a / np.max(deg_dist_a)
        if np.max(deg_dist_b) > 0:
            deg_dist_b = deg_dist_b / np.max(deg_dist_b)
            
        # 计算余弦相似度
        degree_sim = np.dot(deg_dist_a, deg_dist_b) / (
            np.linalg.norm(deg_dist_a) * np.linalg.norm(deg_dist_b) + 1e-10)
        
        # 比较聚类系数相似性
        cc_a = np.array(features_a["clustering_coefficients"])
        cc_b = np.array(features_b["clustering_coefficients"])
        
        # 处理不同长度的情况
        min_len = min(len(cc_a), len(cc_b))
        cc_a = cc_a[:min_len]
        cc_b = cc_b[:min_len]
        
        clustering_sim = 1 - np.mean(np.abs(cc_a - cc_b))
        
        # 综合相似度计算
        similarity = 0.6 * degree_sim + 0.4 * clustering_sim
        
        logger.debug("计算结构相似度: 度分布相似度=%.2f, 聚类相似度=%.2f, 总相似度=%.2f",
                    degree_sim, clustering_sim, similarity)
        
        return float(np.clip(similarity, 0, 1))
    
    def generate_mapping_equation(self, features_a: Dict, features_b: Dict) -> Dict:
        """
        生成两个概念结构之间的映射方程
        
        Args:
            features_a: 第一个概念的特征
            features_b: 第二个概念的特征
            
        Returns:
            包含映射方程的字典
            
        Example:
            >>> mapping = validator.generate_mapping_equation(features_a, features_b)
            >>> print(mapping["node_mapping"])
        """
        # 找到最佳节点映射
        node_mapping = self._find_best_node_mapping(features_a, features_b)
        
        # 生成边映射
        edge_mapping = self._generate_edge_mapping(
            features_a["adjacency_matrix"],
            features_b["adjacency_matrix"],
            node_mapping
        )
        
        # 创建映射方程
        mapping_equation = {
            "node_mapping": node_mapping,
            "edge_mapping": edge_mapping,
            "confidence": self.calculate_structural_similarity(features_a, features_b)
        }
        
        return mapping_equation
    
    def _find_best_node_mapping(self, features_a: Dict, features_b: Dict) -> Dict[str, str]:
        """
        找到最佳节点映射方案
        
        Args:
            features_a: 第一个概念的特征
            features_b: 第二个概念的特征
            
        Returns:
            节点ID到节点ID的映射字典
        """
        node_ids_a = features_a["node_ids"]
        node_ids_b = features_b["node_ids"]
        
        # 简单实现: 基于度中心性排序进行映射
        deg_a = np.array(features_a["degree_distribution"])
        deg_b = np.array(features_b["degree_distribution"])
        
        # 获取排序索引
        sort_idx_a = np.argsort(-deg_a)  # 降序排列
        sort_idx_b = np.argsort(-deg_b)
        
        # 创建映射
        mapping = {}
        min_len = min(len(sort_idx_a), len(sort_idx_b))
        for i in range(min_len):
            a_idx = sort_idx_a[i]
            b_idx = sort_idx_b[i]
            mapping[node_ids_a[a_idx]] = node_ids_b[b_idx]
            
        return mapping
    
    def _generate_edge_mapping(self, adj_a: np.ndarray, adj_b: np.ndarray, 
                             node_mapping: Dict[str, str]) -> List[Dict]:
        """
        生成边映射
        
        Args:
            adj_a: 第一个概念的邻接矩阵
            adj_b: 第二个概念的邻接矩阵
            node_mapping: 节点映射
            
        Returns:
            边映射列表
        """
        edge_mapping = []
        size_a = adj_a.shape[0]
        
        for i in range(size_a):
            for j in range(size_a):
                if adj_a[i][j] > 0:
                    source_a = list(node_mapping.keys())[i]
                    target_a = list(node_mapping.keys())[j]
                    
                    # 获取映射后的节点
                    mapped_source = node_mapping.get(source_a, "")
                    mapped_target = node_mapping.get(target_a, "")
                    
                    if mapped_source and mapped_target:
                        # 检查映射后的边是否存在
                        try:
                            b_indices = list(node_mapping.values())
                            src_idx_b = b_indices.index(mapped_source)
                            tgt_idx_b = b_indices.index(mapped_target)
                            
                            edge_exists = adj_b[src_idx_b][tgt_idx_b] > 0
                            edge_mapping.append({
                                "source_a": source_a,
                                "target_a": target_a,
                                "source_b": mapped_source,
                                "target_b": mapped_target,
                                "exists_in_b": edge_exists,
                                "weight_a": float(adj_a[i][j]),
                                "weight_b": float(adj_b[src_idx_b][tgt_idx_b]) if edge_exists else 0.0
                            })
                        except ValueError:
                            continue
                            
        return edge_mapping
    
    def validate_structure_mapping(self, structure_a: Dict, structure_b: Dict) -> Dict:
        """
        验证两个概念结构之间的映射
        
        Args:
            structure_a: 第一个概念结构
            structure_b: 第二个概念结构
            
        Returns:
            包含验证结果的字典，包括是否同构、映射方程和相似度分数
            
        Example:
            >>> result = validator.validate_structure_mapping(immune_system, firewall_arch)
            >>> print(f"结构同构: {result['isomorphic']}, 相似度: {result['similarity']:.2f}")
        """
        try:
            # 验证输入
            self._validate_input_structure(structure_a)
            self._validate_input_structure(structure_b)
            
            # 提取特征
            features_a = self.extract_structural_features(structure_a)
            features_b = self.extract_structural_features(structure_b)
            
            # 计算相似度
            similarity = self.calculate_structural_similarity(features_a, features_b)
            
            # 生成映射方程
            mapping_equation = self.generate_mapping_equation(features_a, features_b)
            
            # 判断是否同构
            isomorphic = similarity >= self.similarity_threshold
            
            result = {
                "isomorphic": isomorphic,
                "similarity": similarity,
                "mapping_equation": mapping_equation,
                "features_a": features_a,
                "features_b": features_b
            }
            
            logger.info("结构映射验证完成: 相似度=%.2f, 同构=%s", similarity, isomorphic)
            
            return result
            
        except Exception as e:
            logger.error("结构映射验证失败: %s", str(e))
            raise RuntimeError(f"结构映射验证失败: {str(e)}") from e


# 示例用法
if __name__ == "__main__":
    # 示例概念结构: 生物免疫系统
    immune_system = {
        "nodes": [
            {"id": "pathogen", "properties": {"type": "foreign", "threat_level": "high"}},
            {"id": "antigen", "properties": {"type": "marker"}},
            {"id": "b_cell", "properties": {"type": "defender"}},
            {"id": "t_cell", "properties": {"type": "coordinator"}},
            {"id": "antibody", "properties": {"type": "weapon"}}
        ],
        "edges": [
            {"source": "pathogen", "target": "antigen", "relation_type": "has_marker"},
            {"source": "antigen", "target": "b_cell", "relation_type": "activates"},
            {"source": "b_cell", "target": "antibody", "relation_type": "produces"},
            {"source": "t_cell", "target": "b_cell", "relation_type": "stimulates"},
            {"source": "antibody", "target": "pathogen", "relation_type": "neutralizes"}
        ]
    }
    
    # 示例概念结构: 分布式防火墙架构
    firewall_arch = {
        "nodes": [
            {"id": "intruder", "properties": {"type": "external", "threat_level": "high"}},
            {"id": "signature", "properties": {"type": "pattern"}},
            {"id": "sensor", "properties": {"type": "detector"}},
            {"id": "controller", "properties": {"type": "manager"}},
            {"id": "block_rule", "properties": {"type": "countermeasure"}}
        ],
        "edges": [
            {"source": "intruder", "target": "signature", "relation_type": "has_pattern"},
            {"source": "signature", "target": "sensor", "relation_type": "triggers"},
            {"source": "sensor", "target": "block_rule", "relation_type": "generates"},
            {"source": "controller", "target": "sensor", "relation_type": "coordinates"},
            {"source": "block_rule", "target": "intruder", "relation_type": "blocks"}
        ]
    }
    
    # 创建验证器并验证结构映射
    validator = CrossDomainStructureValidator(similarity_threshold=0.6)
    result = validator.validate_structure_mapping(immune_system, firewall_arch)
    
    print("\n验证结果:")
    print(f"结构同构: {result['isomorphic']}")
    print(f"相似度分数: {result['similarity']:.2f}")
    print("\n节点映射:")
    for k, v in result["mapping_equation"]["node_mapping"].items():
        print(f"{k} -> {v}")
    
    print("\n边映射示例:")
    for edge in result["mapping_equation"]["edge_mapping"][:3]:
        print(f"{edge['source_a']}->{edge['target_a']} 映射到 {edge['source_b']}->{edge['target_b']}")