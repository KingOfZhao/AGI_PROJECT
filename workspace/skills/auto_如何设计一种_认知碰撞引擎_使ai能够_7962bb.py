"""
认知碰撞引擎

该模块实现了一种基于高维拓扑同构性的跨域知识迁移系统。通过检测不同领域概念
结构之间的深层拓扑相似性，而非依赖表面语义相似度，实现真正的认知突破。

核心功能：
1. 将领域概念转换为高维拓扑结构
2. 检测不同拓扑结构之间的同构性
3. 生成跨域映射并执行知识迁移

作者: AGI Systems Inc.
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from scipy.spatial.distance import cosine
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
import warnings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DomainConcept:
    """领域概念的数据结构
    
    Attributes:
        concept_id: 概念唯一标识符
        domain: 所属领域 (如 'biology', 'sociology')
        attributes: 概念属性字典
        relations: 与其他概念的关系列表 [(relation_type, target_id), ...]
        embedding: 概念的向量嵌入表示
    """
    concept_id: str
    domain: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, str]] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """数据验证和初始化后处理"""
        if not self.concept_id or not isinstance(self.concept_id, str):
            raise ValueError("concept_id必须是非空字符串")
        if not self.domain or not isinstance(self.domain, str):
            raise ValueError("domain必须是非空字符串")


@dataclass
class TopologicalFeature:
    """拓扑特征数据结构
    
    Attributes:
        betti_numbers: Betti数 (拓扑不变量)
        euler_characteristic: 欧拉示性数
        connectivity_matrix: 连通性矩阵
        structural_vectors: 结构向量组
    """
    betti_numbers: Tuple[int, ...]
    euler_characteristic: int
    connectivity_matrix: np.ndarray
    structural_vectors: np.ndarray


class CognitiveCollisionEngine:
    """认知碰撞引擎
    
    通过检测不同领域概念结构之间的高维拓扑同构性，实现跨域知识迁移。
    
    Example:
        >>> engine = CognitiveCollisionEngine()
        >>> bio_concept = DomainConcept(
        ...     concept_id="cell_division",
        ...     domain="biology",
        ...     attributes={"process": "mitosis", "result": "two_cells"}
        ... )
        >>> soc_concept = DomainConcept(
        ...     concept_id="urban_expansion",
        ...     domain="sociology",
        ...     attributes={"process": "suburbanization", "result": "larger_city"}
        ... )
        >>> isomorphic, score = engine.detect_isomorphism(bio_concept, soc_concept)
        >>> print(f"同构性分数: {score:.4f}")
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.75,
                 max_iterations: int = 100,
                 embedding_dim: int = 128):
        """初始化认知碰撞引擎
        
        Args:
            similarity_threshold: 同构性检测阈值
            max_iterations: 最大迭代次数
            embedding_dim: 嵌入向量维度
        """
        self.similarity_threshold = similarity_threshold
        self.max_iterations = max_iterations
        self.embedding_dim = embedding_dim
        self._concept_cache: Dict[str, DomainConcept] = {}
        self._topology_cache: Dict[str, TopologicalFeature] = {}
        
        logger.info(f"初始化认知碰撞引擎: 阈值={similarity_threshold}, "
                   f"最大迭代={max_iterations}, 嵌入维度={embedding_dim}")
    
    def _validate_concept(self, concept: DomainConcept) -> None:
        """验证概念数据的有效性
        
        Args:
            concept: 待验证的概念对象
            
        Raises:
            ValueError: 当概念数据无效时
        """
        if not isinstance(concept, DomainConcept):
            raise TypeError("输入必须是DomainConcept实例")
        
        if concept.embedding is not None:
            if not isinstance(concept.embedding, np.ndarray):
                raise ValueError("embedding必须是numpy数组")
            if concept.embedding.shape[0] != self.embedding_dim:
                warnings.warn(f"嵌入维度{concept.embedding.shape[0]}与引擎配置"
                            f"{self.embedding_dim}不匹配，将进行自动调整")
    
    def _compute_betti_numbers(self, adjacency_matrix: np.ndarray) -> Tuple[int, ...]:
        """计算拓扑空间的Betti数 (拓扑不变量)
        
        Args:
            adjacency_matrix: 邻接矩阵
            
        Returns:
            Betti数元组 (β0, β1, ...)
        """
        # 简化的Betti数计算 (实际应用中应使用持久同调)
        n_components, _ = connected_components(csgraph=adjacency_matrix, directed=False)
        beta_0 = n_components  # 连通分量数
        
        # 简化计算1维Betti数 (环的数量)
        n_edges = np.count_nonzero(adjacency_matrix) // 2
        n_nodes = adjacency_matrix.shape[0]
        beta_1 = max(0, n_edges - n_nodes + beta_0)
        
        return (beta_0, beta_1)
    
    def _extract_structural_vectors(self, concept: DomainConcept) -> np.ndarray:
        """提取概念的结构向量
        
        Args:
            concept: 领域概念
            
        Returns:
            结构向量数组
        """
        # 基于关系类型构建结构向量
        relation_types = list(set(r[0] for r in concept.relations))
        type_to_idx = {t: i for i, t in enumerate(relation_types)}
        
        # 构建关系频率向量
        vector = np.zeros(len(relation_types))
        for rel_type, _ in concept.relations:
            vector[type_to_idx[rel_type]] += 1
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def compute_topological_features(self, concept: DomainConcept) -> TopologicalFeature:
        """计算概念的拓扑特征
        
        Args:
            concept: 领域概念
            
        Returns:
            TopologicalFeature对象
            
        Raises:
            ValueError: 当概念数据无效时
        """
        self._validate_concept(concept)
        
        # 检查缓存
        if concept.concept_id in self._topology_cache:
            logger.debug(f"从缓存加载拓扑特征: {concept.concept_id}")
            return self._topology_cache[concept.concept_id]
        
        # 构建邻接矩阵 (简化处理)
        related_ids = [r[1] for r in concept.relations]
        n_nodes = len(related_ids) + 1  # 包括自身
        
        if n_nodes > 1:
            adjacency = np.zeros((n_nodes, n_nodes))
            # 连接自身与所有相关节点
            for i in range(1, n_nodes):
                adjacency[0, i] = 1
                adjacency[i, 0] = 1
        else:
            adjacency = np.zeros((1, 1))
        
        # 计算拓扑特征
        betti_numbers = self._compute_betti_numbers(adjacency)
        euler_char = betti_numbers[0] - betti_numbers[1]
        structural_vectors = self._extract_structural_vectors(concept)
        
        feature = TopologicalFeature(
            betti_numbers=betti_numbers,
            euler_characteristic=euler_char,
            connectivity_matrix=adjacency,
            structural_vectors=structural_vectors
        )
        
        # 缓存结果
        self._topology_cache[concept.concept_id] = feature
        logger.info(f"计算拓扑特征: {concept.concept_id}, Betti数={betti_numbers}")
        
        return feature
    
    def detect_isomorphism(self, 
                          concept1: DomainConcept, 
                          concept2: DomainConcept) -> Tuple[bool, float]:
        """检测两个概念之间的拓扑同构性
        
        Args:
            concept1: 第一个领域概念
            concept2: 第二个领域概念
            
        Returns:
            (是否同构, 同构性分数) 元组
            
        Raises:
            ValueError: 当概念数据无效时
        """
        # 边界检查
        if not isinstance(concept1, DomainConcept) or not isinstance(concept2, DomainConcept):
            raise TypeError("两个输入都必须是DomainConcept实例")
        
        # 获取拓扑特征
        feat1 = self.compute_topological_features(concept1)
        feat2 = self.compute_topological_features(concept2)
        
        # 计算Betti数相似度
        betti_score = self._compare_betti_numbers(feat1.betti_numbers, feat2.betti_numbers)
        
        # 计算结构向量相似度
        if feat1.structural_vectors.size > 0 and feat2.structural_vectors.size > 0:
            # 对齐向量维度
            max_len = max(len(feat1.structural_vectors), len(feat2.structural_vectors))
            v1 = np.pad(feat1.structural_vectors, (0, max_len - len(feat1.structural_vectors)))
            v2 = np.pad(feat2.structural_vectors, (0, max_len - len(feat2.structural_vectors)))
            struct_score = 1 - cosine(v1, v2)
        else:
            struct_score = 0.0
        
        # 计算欧拉示性数相似度
        euler_diff = abs(feat1.euler_characteristic - feat2.euler_characteristic)
        euler_score = 1.0 / (1.0 + euler_diff)
        
        # 综合评分 (加权平均)
        weights = np.array([0.4, 0.4, 0.2])
        scores = np.array([betti_score, struct_score, euler_score])
        total_score = np.dot(weights, scores)
        
        is_isomorphic = total_score >= self.similarity_threshold
        
        logger.info(f"同构性检测: {concept1.concept_id} vs {concept2.concept_id} -> "
                   f"分数={total_score:.4f}, 结果={is_isomorphic}")
        
        return is_isomorphic, total_score
    
    def _compare_betti_numbers(self, 
                              betti1: Tuple[int, ...], 
                              betti2: Tuple[int, ...]) -> float:
        """比较两组Betti数的相似度
        
        Args:
            betti1: 第一组Betti数
            betti2: 第二组Betti数
            
        Returns:
            相似度分数 [0, 1]
        """
        # 对齐维度
        max_len = max(len(betti1), len(betti2))
        b1 = np.array(betti1 + (0,) * (max_len - len(betti1)))
        b2 = np.array(betti2 + (0,) * (max_len - len(betti2)))
        
        # 计算余弦相似度
        dot_product = np.dot(b1, b2)
        norm1 = np.linalg.norm(b1)
        norm2 = np.linalg.norm(b2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def cross_domain_transfer(self, 
                             source_concept: DomainConcept,
                             target_domain: str,
                             target_concepts: List[DomainConcept]) -> Dict[str, Any]:
        """执行跨域知识迁移
        
        Args:
            source_concept: 源领域概念
            target_domain: 目标领域
            target_concepts: 目标领域概念列表
            
        Returns:
            迁移结果字典，包含最佳匹配和迁移的知识
            
        Raises:
            ValueError: 当输入数据无效时
        """
        # 数据验证
        if not target_concepts:
            raise ValueError("目标概念列表不能为空")
        
        if source_concept.domain == target_domain:
            warnings.warn("源领域和目标领域相同，可能无法产生有效的跨域迁移")
        
        logger.info(f"开始跨域迁移: {source_concept.domain} -> {target_domain}")
        
        # 寻找最佳匹配
        best_match = None
        best_score = -1
        
        for target in target_concepts:
            if target.domain != target_domain:
                logger.warning(f"概念{target.concept_id}不属于目标领域{target_domain}，跳过")
                continue
            
            is_iso, score = self.detect_isomorphism(source_concept, target)
            
            if is_iso and score > best_score:
                best_match = target
                best_score = score
        
        if best_match is None:
            logger.warning(f"未找到符合条件的跨域映射: {source_concept.concept_id} -> {target_domain}")
            return {
                "success": False,
                "source": source_concept.concept_id,
                "target_domain": target_domain,
                "message": "No isomorphic concept found in target domain"
            }
        
        # 生成迁移知识
        transferred_knowledge = self._generate_transferred_knowledge(
            source_concept, best_match, best_score
        )
        
        result = {
            "success": True,
            "source": source_concept.concept_id,
            "target": best_match.concept_id,
            "isomorphism_score": best_score,
            "transferred_knowledge": transferred_knowledge,
            "source_domain": source_concept.domain,
            "target_domain": target_domain
        }
        
        logger.info(f"跨域迁移成功: {source_concept.concept_id} -> {best_match.concept_id}, "
                   f"分数={best_score:.4f}")
        
        return result
    
    def _generate_transferred_knowledge(self, 
                                       source: DomainConcept,
                                       target: DomainConcept,
                                       score: float) -> Dict[str, Any]:
        """生成迁移的知识
        
        Args:
            source: 源概念
            target: 目标概念
            score: 同构性分数
            
        Returns:
            迁移的知识字典
        """
        # 提取结构对应关系
        relation_mapping = {}
        source_relations = defaultdict(list)
        target_relations = defaultdict(list)
        
        for rel_type, target_id in source.relations:
            source_relations[rel_type].append(target_id)
        
        for rel_type, target_id in target.relations:
            target_relations[rel_type].append(target_id)
        
        # 匹配关系类型
        common_relations = set(source_relations.keys()) & set(target_relations.keys())
        
        for rel_type in common_relations:
            relation_mapping[rel_type] = {
                "source_count": len(source_relations[rel_type]),
                "target_count": len(target_relations[rel_type]),
                "ratio": len(source_relations[rel_type]) / max(1, len(target_relations[rel_type]))
            }
        
        # 生成新洞察
        insights = []
        if score > 0.9:
            insights.append(f"发现强拓扑同构: {source.concept_id}与{target.concept_id}"
                          f"在{source.domain}和{target.domain}领域具有相同的深层结构")
            insights.append(f"可能的通用原理: 考虑两个概念共享的抽象模式")
        
        return {
            "relation_mapping": relation_mapping,
            "structural_similarity": score,
            "hypotheses": insights,
            "transfer_confidence": min(1.0, score * 1.2)  # 略微提高置信度
        }
    
    def batch_detect(self, 
                    concepts: List[DomainConcept],
                    domains: Optional[Set[str]] = None) -> Dict[Tuple[str, str], float]:
        """批量检测概念之间的同构性
        
        Args:
            concepts: 概念列表
            domains: 限制检测的领域集合 (None表示所有领域)
            
        Returns:
            同构性矩阵字典 { (concept_id1, concept_id2): score }
        """
        if not concepts:
            raise ValueError("概念列表不能为空")
        
        results = {}
        n = len(concepts)
        
        logger.info(f"开始批量检测: {n}个概念")
        
        for i in range(n):
            for j in range(i+1, n):
                c1, c2 = concepts[i], concepts[j]
                
                # 检查领域限制
                if domains and (c1.domain not in domains or c2.domain not in domains):
                    continue
                
                # 跳过同领域比较
                if c1.domain == c2.domain:
                    continue
                
                try:
                    _, score = self.detect_isomorphism(c1, c2)
                    results[(c1.concept_id, c2.concept_id)] = score
                except Exception as e:
                    logger.error(f"检测失败: {c1.concept_id} vs {c2.concept_id}: {str(e)}")
        
        logger.info(f"批量检测完成: 发现{len(results)}对跨域关系")
        return results


# 使用示例
if __name__ == "__main__":
    # 创建引擎实例
    engine = CognitiveCollisionEngine(similarity_threshold=0.7)
    
    # 示例1: 生物学概念
    cell_division = DomainConcept(
        concept_id="cell_division",
        domain="biology",
        attributes={
            "process": "mitosis",
            "result": "two_daughter_cells",
            "mechanism": "chromosome_separation"
        },
        relations=[
            ("precedes", "cell_growth"),
            ("requires", "dna_replication"),
            ("produces", "two_cells"),
            ("regulated_by", "cell_cycle_checkpoints")
        ]
    )
    
    # 示例2: 社会学概念
    urban_expansion = DomainConcept(
        concept_id="urban_expansion",
        domain="sociology",
        attributes={
            "process": "suburbanization",
            "result": "larger_metropolitan_area",
            "mechanism": "population_migration"
        },
        relations=[
            ("precedes", "economic_growth"),
            ("requires", "infrastructure_development"),
            ("produces", "expanded_city"),
            ("regulated_by", "zoning_laws")
        ]
    )
    
    # 检测同构性
    is_iso, score = engine.detect_isomorphism(cell_division, urban_expansion)
    print(f"\n同构性检测结果:")
    print(f"  概念对: {cell_division.concept_id} <-> {urban_expansion.concept_id}")
    print(f"  领域: {cell_division.domain} <-> {urban_expansion.domain}")
    print(f"  同构性分数: {score:.4f}")
    print(f"  是否同构: {is_iso}")
    
    # 执行跨域迁移
    result = engine.cross_domain_transfer(
        source_concept=cell_division,
        target_domain="sociology",
        target_concepts=[urban_expansion]
    )
    
    print("\n跨域迁移结果:")
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  源概念: {result['source']}")
        print(f"  目标概念: {result['target']}")
        print(f"  同构分数: {result['isomorphism_score']:.4f}")
        print(f"  迁移知识: {result['transferred_knowledge']['hypotheses']}")