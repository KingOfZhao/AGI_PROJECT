"""
模块: auto_cross_domain_structural_overlap_validator
名称: auto_跨域迁移中的_结构重叠_有效性验证_当系_ff4073
描述: 实现跨域迁移学习中'结构重叠'有效性的自动验证。通过计算源域与目标域的
      因果骨架相似度，判断迁移是否基于深层逻辑而非表层语义。
作者: AGI System Core
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """自定义验证异常，用于数据处理或逻辑校验失败时抛出"""
    pass

class SimilarityMetric(Enum):
    """定义结构相似度的计算指标"""
    COSINE = "cosine"
    JACCARD = "jaccard"
    EDIT_DISTANCE = "edit_distance"

@dataclass
class CausalNode:
    """因果图节点数据结构"""
    node_id: str
    feature_vector: np.ndarray  # 节点的深层特征嵌入
    causal_parents: Set[str]    # 父节点ID集合
    causal_children: Set[str]   # 子节点ID集合

@dataclass
class CausalGraph:
    """因果图数据结构"""
    domain_name: str
    nodes: Dict[str, CausalNode]
    adjacency_matrix: Optional[np.ndarray] = None

    def __post_init__(self):
        """初始化后处理，构建邻接矩阵"""
        self._build_adjacency_matrix()

    def _build_adjacency_matrix(self):
        """构建邻接矩阵用于快速计算"""
        node_ids = list(self.nodes.keys())
        n = len(node_ids)
        self.adjacency_matrix = np.zeros((n, n))
        id_to_index = {nid: i for i, nid in enumerate(node_ids)}

        for nid, node in self.nodes.items():
            i = id_to_index[nid]
            for child_id in node.causal_children:
                if child_id in id_to_index:
                    j = id_to_index[child_id]
                    self.adjacency_matrix[i, j] = 1.0

class StructuralProbe:
    """
    结构探针算法核心类。
    用于提取和比对深层因果图的结构特征。
    """

    def __init__(self, threshold: float = 0.75, metric: SimilarityMetric = SimilarityMetric.COSINE):
        """
        初始化探针。
        
        Args:
            threshold (float): 判定为有效重叠的阈值 (0.0 to 1.0)。
            metric (SimilarityMetric): 相似度计算方法。
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.threshold = threshold
        self.metric = metric
        logger.info(f"StructuralProbe initialized with threshold={threshold}, metric={metric.value}")

    def _validate_graph(self, graph: CausalGraph) -> bool:
        """
        辅助函数：验证因果图数据的有效性。
        
        Args:
            graph (CausalGraph): 待验证的图结构。
            
        Returns:
            bool: 验证是否通过。
            
        Raises:
            ValidationError: 如果数据无效。
        """
        if not graph.nodes:
            raise ValidationError(f"Graph in domain '{graph.domain_name}' has no nodes.")
        
        for node_id, node in graph.nodes.items():
            if node.feature_vector is None or len(node.feature_vector) == 0:
                raise ValidationError(f"Node {node_id} has empty feature vector.")
            if not isinstance(node.causal_parents, set) or not isinstance(node.causal_children, set):
                raise ValidationError(f"Node {node_id} parent/children must be sets.")
        
        return True

    def extract_structural_signature(self, graph: CausalGraph) -> np.ndarray:
        """
        核心函数 1: 提取因果图的深层结构签名。
        
        该方法将图的拓扑结构（邻接关系）与节点语义（特征向量）融合，
        生成一个能够代表该因果骨架的归一化向量。
        
        Args:
            graph (CausalGraph): 输入的因果图。
            
        Returns:
            np.ndarray: 归一化的结构签名向量 (1D Array)。
        """
        try:
            self._validate_graph(graph)
            logger.debug(f"Extracting signature for domain: {graph.domain_name}")
            
            # 1. 聚合节点特征：取平均作为语义基线
            all_features = np.array([n.feature_vector for n in graph.nodes.values()])
            semantic_vector = np.mean(all_features, axis=0)
            
            # 2. 提取拓扑特征：邻接矩阵的展开（拉直）
            if graph.adjacency_matrix is not None:
                topo_vector = graph.adjacency_matrix.flatten()
                # 简单降维：取连接密度统计量 (sum, mean, std)
                topo_stats = np.array([
                    np.sum(graph.adjacency_matrix), 
                    np.mean(graph.adjacency_matrix), 
                    np.std(graph.adjacency_matrix)
                ])
            else:
                topo_stats = np.zeros(3)

            # 3. 融合：将语义向量的统计特性与拓扑特性拼接
            # 这里简化为：[语义均值, 语义方差, 拓扑统计...]
            signature = np.concatenate([
                np.mean(semantic_vector, keepdims=True),
                np.var(semantic_vector, keepdims=True),
                topo_stats
            ])
            
            # 归一化
            norm = np.linalg.norm(signature)
            if norm == 0:
                return signature
            return signature / norm
            
        except Exception as e:
            logger.error(f"Signature extraction failed for {graph.domain_name}: {e}")
            raise ValidationError("Failed to extract structural signature") from e

    def compute_overlap_score(self, source_sig: np.ndarray, target_sig: np.ndarray) -> float:
        """
        核心函数 2: 计算两个结构签名之间的重叠分数。
        
        基于初始化时设定的度量方法（默认余弦相似度）。
        
        Args:
            source_sig (np.ndarray): 源域签名。
            target_sig (np.ndarray): 目标域签名。
            
        Returns:
            float: 0.0 到 1.0 之间的相似度分数。
        """
        if source_sig.shape != target_sig.shape:
            # 允许不同维度的简单对齐或报错，这里选择截断补零对齐
            logger.warning("Signature dimension mismatch. Attempting alignment.")
            max_len = max(len(source_sig), len(target_sig))
            s_aligned = np.zeros(max_len)
            t_aligned = np.zeros(max_len)
            s_aligned[:len(source_sig)] = source_sig
            t_aligned[:len(target_sig)] = target_sig
            source_sig, target_sig = s_aligned, t_aligned

        if self.metric == SimilarityMetric.COSINE:
            dot_product = np.dot(source_sig, target_sig)
            norm_s = np.linalg.norm(source_sig)
            norm_t = np.linalg.norm(target_sig)
            if norm_s == 0 or norm_t == 0:
                return 0.0
            score = dot_product / (norm_s * norm_t)
            return float(score)
        
        elif self.metric == SimilarityMetric.JACCARD:
            # 将连续值二值化用于Jaccard计算 (示例逻辑)
            s_binary = (source_sig > 0.5).astype(int)
            t_binary = (target_sig > 0.5).astype(int)
            intersection = np.sum(np.bitwise_and(s_binary, t_binary))
            union = np.sum(np.bitwise_or(s_binary, t_binary))
            return intersection / union if union > 0 else 0.0
        
        return 0.0

    def verify_transfer_validity(self, source_graph: CausalGraph, target_graph: CausalGraph) -> Tuple[bool, float, Dict]:
        """
        主入口函数：验证迁移有效性。
        
        Args:
            source_graph (CausalGraph): 源域（如编程）的因果图。
            target_graph (CausalGraph): 目标域（如烹饪）的因果图。
            
        Returns:
            Tuple[bool, float, Dict]: 
                - is_valid: 是否通过验证
                - score: 结构重叠分数
                - details: 详细信息字典
        """
        logger.info(f"Starting structural validation: {source_graph.domain_name} -> {target_graph.domain_name}")
        
        source_sig = self.extract_structural_signature(source_graph)
        target_sig = self.extract_structural_signature(target_graph)
        
        score = self.compute_overlap_score(source_sig, target_sig)
        
        is_valid = score >= self.threshold
        
        details = {
            "source_domain": source_graph.domain_name,
            "target_domain": target_graph.domain_name,
            "metric_used": self.metric.value,
            "threshold": self.threshold,
            "is_causal_overlap": is_valid
        }
        
        if is_valid:
            logger.info(f"Validation PASSED. Score: {score:.4f} (Threshold: {self.threshold})")
        else:
            logger.warning(f"Validation FAILED. Score: {score:.4f} (Threshold: {self.threshold})")
            
        return is_valid, score, details

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 模拟源域数据 (例如：Python编程)
    # 节点特征假设为某种抽象的能力向量 (如: [逻辑性, 抽象度, 严谨性])
    python_node_1 = CausalNode("func_def", np.array([0.9, 0.8, 0.9]), set(), {"indent_block"})
    python_node_2 = CausalNode("indent_block", np.array([0.7, 0.6, 1.0]), {"func_def"}, {"logic_flow"})
    python_graph = CausalGraph("Python_Programming", {
        "func_def": python_node_1,
        "indent_block": python_node_2
    })

    # 2. 模拟目标域数据 (例如：烹饪食谱)
    # 节点特征 (如: [逻辑性, 抽象度, 严谨性]) -> 烹饪步骤也包含逻辑流程和严格配比
    cooking_node_1 = CausalNode("recipe_start", np.array([0.8, 0.7, 0.85]), set(), {"prep_ingredients"})
    cooking_node_2 = CausalNode("prep_ingredients", np.array([0.75, 0.65, 0.95]), {"recipe_start"}, {"cooking_process"})
    cooking_graph = CausalGraph("French_Cooking", {
        "recipe_start": cooking_node_1,
        "prep_ingredients": cooking_node_2
    })

    # 3. 初始化探针并进行验证
    try:
        probe = StructuralProbe(threshold=0.7, metric=SimilarityMetric.COSINE)
        is_valid, score, info = probe.verify_transfer_validity(python_graph, cooking_graph)
        
        print("\n--- Verification Result ---")
        print(f"Transfer Valid: {is_valid}")
        print(f"Overlap Score: {score:.4f}")
        print(f"Details: {info}")
        
    except ValidationError as e:
        print(f"Error during validation: {e}")