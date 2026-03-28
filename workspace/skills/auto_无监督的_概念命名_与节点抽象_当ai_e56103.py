"""
无监督的'概念命名'与节点抽象模块

本模块实现了从高维向量聚类中提取可解释符号名称的功能，
完成从Sub-symbolic（亚符号）到Symbolic（符号）的认知跃迁。

核心功能：
1. 从向量聚类中提取代表性样本
2. 基于样本特征生成概念标签
3. 将概念节点融入认知网络

输入格式：
- vectors: np.ndarray, 形状为(n_samples, n_features)的高维向量
- cluster_labels: np.ndarray, 形状为(n_samples,)的聚类标签
- feature_names: Optional[List[str]], 特征维度名称列表

输出格式：
- List[ConceptNode]: 概念节点列表，包含名称、描述、核心向量等
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """
    概念节点数据结构
    
    Attributes:
        name (str): 概念名称，具有指代性的标签
        description (str): 概念的自然语言描述
        centroid (np.ndarray): 聚类中心向量
        member_indices (List[int]): 属于该概念的样本索引
        confidence (float): 概念提取的置信度 [0, 1]
        metadata (Dict): 额外的元数据
    """
    name: str
    description: str
    centroid: np.ndarray
    member_indices: List[int]
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在[0,1]范围内，当前值: {self.confidence}")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("概念名称必须是非空字符串")
        if len(self.member_indices) == 0:
            logger.warning(f"概念 '{self.name}' 没有关联的成员样本")


class ConceptNamingEngine:
    """
    概念命名引擎
    
    从无监督聚类结果中自动生成具有指代性的概念标签，
    并将其抽象为认知网络中的节点。
    
    Example:
        >>> vectors = np.random.rand(100, 128)  # 100个128维向量
        >>> labels = np.random.randint(0, 5, 100)  # 5个聚类
        >>> engine = ConceptNamingEngine()
        >>> concepts = engine.extract_concepts(vectors, labels)
        >>> print(concepts[0].name)
        'pattern_alpha_42'
    """
    
    # 预定义的概念词根，用于组合命名
    CONCEPT_PREFIXES = [
        'alpha', 'beta', 'gamma', 'delta', 'epsilon',
        'sigma', 'omega', 'theta', 'lambda', 'phi'
    ]
    
    CONCEPT_ROOTS = [
        'pattern', 'cluster', 'node', 'archetype', 'prototype',
        'schema', 'template', 'structure', 'motif', 'paradigm'
    ]
    
    def __init__(self, min_cluster_size: int = 3, similarity_threshold: float = 0.7):
        """
        初始化概念命名引擎
        
        Args:
            min_cluster_size: 最小聚类大小，小于此值的聚类将被忽略
            similarity_threshold: 相似度阈值，用于确定概念边界
        """
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self._existing_names: Set[str] = set()
        self._name_counter: Dict[str, int] = {}
        
        logger.info(f"概念命名引擎初始化完成，最小聚类大小: {min_cluster_size}")
    
    def extract_concepts(
        self,
        vectors: np.ndarray,
        cluster_labels: np.ndarray,
        feature_names: Optional[List[str]] = None,
        textual_hints: Optional[List[str]] = None
    ) -> List[ConceptNode]:
        """
        从向量聚类中提取概念节点
        
        Args:
            vectors: 高维向量矩阵
            cluster_labels: 聚类标签
            feature_names: 特征维度名称（可选）
            textual_hints: 文本提示列表，用于辅助命名（可选）
            
        Returns:
            List[ConceptNode]: 提取的概念节点列表
            
        Raises:
            ValueError: 输入数据格式不正确
        """
        # 输入验证
        self._validate_inputs(vectors, cluster_labels)
        
        logger.info(f"开始提取概念，共 {len(np.unique(cluster_labels))} 个聚类")
        
        unique_labels = np.unique(cluster_labels)
        concepts: List[ConceptNode] = []
        
        for label in unique_labels:
            if label == -1:  # 跳过噪声点
                continue
                
            # 获取当前聚类的样本
            mask = cluster_labels == label
            cluster_vectors = vectors[mask]
            indices = np.where(mask)[0].tolist()
            
            # 边界检查
            if len(indices) < self.min_cluster_size:
                logger.debug(f"聚类 {label} 样本数不足，跳过")
                continue
            
            # 计算聚类中心
            centroid = np.mean(cluster_vectors, axis=0)
            
            # 计算聚类内聚度（用于置信度）
            cohesion = self._calculate_cohesion(cluster_vectors, centroid)
            
            # 生成概念名称
            hints_for_cluster = None
            if textual_hints is not None:
                hints_for_cluster = [textual_hints[i] for i in indices if i < len(textual_hints)]
            
            name = self._generate_concept_name(
                centroid, feature_names, hints_for_cluster
            )
            
            # 生成概念描述
            description = self._generate_description(
                name, cohesion, len(indices), feature_names, hints_for_cluster
            )
            
            # 创建概念节点
            concept = ConceptNode(
                name=name,
                description=description,
                centroid=centroid,
                member_indices=indices,
                confidence=cohesion,
                metadata={
                    'cluster_label': int(label),
                    'cluster_size': len(indices),
                    'feature_names': feature_names[:5] if feature_names else None
                }
            )
            
            concepts.append(concept)
            self._existing_names.add(name)
            
            logger.info(f"提取概念: {name}, 置信度: {cohesion:.3f}, 样本数: {len(indices)}")
        
        logger.info(f"概念提取完成，共 {len(concepts)} 个有效概念")
        return concepts
    
    def _validate_inputs(self, vectors: np.ndarray, cluster_labels: np.ndarray) -> None:
        """
        验证输入数据的合法性
        
        Args:
            vectors: 向量矩阵
            cluster_labels: 聚类标签
            
        Raises:
            ValueError: 数据验证失败
        """
        if not isinstance(vectors, np.ndarray) or not isinstance(cluster_labels, np.ndarray):
            raise ValueError("输入必须是numpy数组")
        
        if vectors.ndim != 2:
            raise ValueError(f"向量必须是2维数组，当前维度: {vectors.ndim}")
        
        if cluster_labels.ndim != 1:
            raise ValueError(f"标签必须是1维数组，当前维度: {cluster_labels.ndim}")
        
        if vectors.shape[0] != cluster_labels.shape[0]:
            raise ValueError(
                f"向量数量({vectors.shape[0]})与标签数量({cluster_labels.shape[0]})不匹配"
            )
        
        if vectors.shape[0] == 0:
            raise ValueError("输入向量不能为空")
        
        # 检查NaN和Inf
        if np.any(np.isnan(vectors)) or np.any(np.isinf(vectors)):
            raise ValueError("向量包含NaN或Inf值")
        
        logger.debug("输入验证通过")
    
    def _calculate_cohesion(self, cluster_vectors: np.ndarray, centroid: np.ndarray) -> float:
        """
        计算聚类的内聚度
        
        内聚度定义为样本到中心的平均余弦相似度
        
        Args:
            cluster_vectors: 聚类内的向量
            centroid: 聚类中心
            
        Returns:
            float: 内聚度值 [0, 1]
        """
        if len(cluster_vectors) < 2:
            return 1.0
        
        # 计算每个样本与中心的余弦相似度
        centroid_reshaped = centroid.reshape(1, -1)
        similarities = cosine_similarity(cluster_vectors, centroid_reshaped)
        avg_similarity = float(np.mean(similarities))
        
        return max(0.0, min(1.0, avg_similarity))
    
    def _generate_concept_name(
        self,
        centroid: np.ndarray,
        feature_names: Optional[List[str]] = None,
        textual_hints: Optional[List[str]] = None
    ) -> str:
        """
        生成具有指代性的概念名称
        
        策略：
        1. 如果有文本提示，尝试提取关键词
        2. 基于特征重要性组合词根
        3. 添加唯一标识符
        
        Args:
            centroid: 聚类中心向量
            feature_names: 特征名称列表
            textual_hints: 文本提示
            
        Returns:
            str: 生成的概念名称
        """
        # 策略1：从文本提示中提取关键词
        if textual_hints and len(textual_hints) > 0:
            keyword = self._extract_keyword_from_hints(textual_hints)
            if keyword:
                base_name = f"concept_{keyword}"
                return self._ensure_unique_name(base_name)
        
        # 策略2：基于特征重要性命名
        if feature_names and len(feature_names) > 0:
            top_feature_idx = np.argmax(np.abs(centroid))
            if top_feature_idx < len(feature_names):
                feature_name = self._sanitize_name(feature_names[top_feature_idx])
                base_name = f"pattern_{feature_name}"
                return self._ensure_unique_name(base_name)
        
        # 策略3：基于向量哈希和预定义词根
        import hashlib
        vector_hash = hashlib.md5(centroid.tobytes()).hexdigest()[:6]
        prefix_idx = int(vector_hash[0], 16) % len(self.CONCEPT_PREFIXES)
        root_idx = int(vector_hash[1], 16) % len(self.CONCEPT_ROOTS)
        
        base_name = f"{self.CONCEPT_PREFIXES[prefix_idx]}_{self.CONCEPT_ROOTS[root_idx]}_{vector_hash}"
        return self._ensure_unique_name(base_name)
    
    def _extract_keyword_from_hints(self, hints: List[str]) -> Optional[str]:
        """
        从文本提示中提取关键词
        
        使用TF-IDF识别最具代表性的词汇
        
        Args:
            hints: 文本提示列表
            
        Returns:
            Optional[str]: 提取的关键词，如果失败返回None
        """
        try:
            if len(hints) < 2:
                # 样本太少，使用简单的词频
                words = re.findall(r'\b[a-zA-Z]{3,}\b', ' '.join(hints).lower())
                if words:
                    return max(set(words), key=words.count)
                return None
            
            # 使用TF-IDF
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(hints)
            feature_names = vectorizer.get_feature_names_out()
            
            # 获取平均TF-IDF最高的词
            mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
            top_idx = np.argmax(mean_scores)
            
            keyword = feature_names[top_idx]
            return self._sanitize_name(keyword)
            
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return None
    
    def _sanitize_name(self, name: str) -> str:
        """
        清理名称，使其符合标识符规范
        
        Args:
            name: 原始名称
            
        Returns:
            str: 清理后的名称
        """
        # 转小写，替换非法字符
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        # 移除连续下划线
        sanitized = re.sub(r'_+', '_', sanitized)
        # 移除首尾下划线
        sanitized = sanitized.strip('_')
        # 限制长度
        return sanitized[:30] if sanitized else 'unnamed'
    
    def _ensure_unique_name(self, base_name: str) -> str:
        """
        确保名称唯一
        
        Args:
            base_name: 基础名称
            
        Returns:
            str: 唯一的名称
        """
        if base_name not in self._existing_names:
            return base_name
        
        # 添加计数器
        if base_name not in self._name_counter:
            self._name_counter[base_name] = 1
        
        self._name_counter[base_name] += 1
        unique_name = f"{base_name}_v{self._name_counter[base_name]}"
        
        return unique_name
    
    def _generate_description(
        self,
        name: str,
        cohesion: float,
        size: int,
        feature_names: Optional[List[str]] = None,
        textual_hints: Optional[List[str]] = None
    ) -> str:
        """
        生成概念的自然语言描述
        
        Args:
            name: 概念名称
            cohesion: 内聚度
            size: 聚类大小
            feature_names: 特征名称
            textual_hints: 文本提示
            
        Returns:
            str: 概念描述
        """
        desc_parts = [f"概念 '{name}' 表示从 {size} 个样本中归纳出的模式"]
        
        if cohesion > 0.8:
            desc_parts.append(f"该模式具有高度内聚性({cohesion:.2f})，表明样本间存在强关联")
        elif cohesion > 0.5:
            desc_parts.append(f"该模式内聚度为{cohesion:.2f}，存在一定的变体")
        else:
            desc_parts.append(f"该模式内聚度较低({cohesion:.2f})，可能包含多个子模式")
        
        if textual_hints and len(textual_hints) > 0:
            sample_hint = textual_hints[0][:50] if textual_hints[0] else ""
            if sample_hint:
                desc_parts.append(f"示例: '{sample_hint}...'")
        
        return "。".join(desc_parts) + "。"


def integrate_into_cognitive_network(
    concepts: List[ConceptNode],
    existing_network: Optional[Dict[str, ConceptNode]] = None,
    merge_threshold: float = 0.85
) -> Dict[str, ConceptNode]:
    """
    将概念节点融入认知网络
    
    这是一个辅助函数，展示如何将新提取的概念整合到现有网络中
    
    Args:
        concepts: 新提取的概念列表
        existing_network: 现有的认知网络（字典形式）
        merge_threshold: 合并阈值，余弦相似度超过此值则合并
        
    Returns:
        Dict[str, ConceptNode]: 更新后的认知网络
        
    Example:
        >>> concepts = engine.extract_concepts(vectors, labels)
        >>> network = integrate_into_cognitive_network(concepts)
        >>> print(list(network.keys()))
        ['alpha_pattern_a1b2c3', 'beta_node_d4e5f6']
    """
    if existing_network is None:
        existing_network = {}
    
    logger.info(f"开始整合 {len(concepts)} 个概念到认知网络")
    
    for concept in concepts:
        should_add = True
        
        # 检查是否与现有概念重复
        for existing_name, existing_concept in existing_network.items():
            similarity = cosine_similarity(
                concept.centroid.reshape(1, -1),
                existing_concept.centroid.reshape(1, -1)
            )[0, 0]
            
            if similarity > merge_threshold:
                logger.info(
                    f"概念 '{concept.name}' 与 '{existing_name}' 相似度 "
                    f"{similarity:.3f}，执行合并"
                )
                # 合并成员索引
                existing_concept.member_indices.extend(concept.member_indices)
                # 更新置信度（取加权平均）
                total_size = len(existing_concept.member_indices)
                existing_concept.confidence = (
                    existing_concept.confidence * (total_size - len(concept.member_indices)) +
                    concept.confidence * len(concept.member_indices)
                ) / total_size
                should_add = False
                break
        
        if should_add:
            existing_network[concept.name] = concept
            logger.info(f"新概念 '{concept.name}' 已添加到认知网络")
    
    logger.info(f"认知网络整合完成，当前共 {len(existing_network)} 个概念节点")
    return existing_network


# 使用示例
if __name__ == "__main__":
    # 模拟数据：创建一些聚类数据
    np.random.seed(42)
    
    # 创建3个聚类中心
    centers = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ])
    
    # 生成样本
    vectors_list = []
    labels_list = []
    for i, center in enumerate(centers):
        samples = center + np.random.randn(20, 4) * 0.2
        vectors_list.append(samples)
        labels_list.extend([i] * 20)
    
    vectors = np.vstack(vectors_list)
    labels = np.array(labels_list)
    
    # 文本提示（模拟代码优化策略描述）
    hints = [
        "loop unrolling optimization for better performance",
        "loop unrolling optimization for better performance",
        "loop unrolling optimization for better performance"
    ] * 7 + [
        "memory caching strategy implementation",
        "memory caching strategy implementation"
    ] * 7 + [
        "parallel execution thread pooling",
        "parallel execution thread pooling"
    ] * 6
    
    # 创建引擎并提取概念
    engine = ConceptNamingEngine(min_cluster_size=5)
    concepts = engine.extract_concepts(
        vectors,
        labels,
        feature_names=['performance', 'memory', 'parallelism', 'complexity'],
        textual_hints=hints
    )
    
    # 打印结果
    print("\n" + "="*60)
    print("提取的概念节点:")
    print("="*60)
    for concept in concepts:
        print(f"\n名称: {concept.name}")
        print(f"描述: {concept.description}")
        print(f"置信度: {concept.confidence:.3f}")
        print(f"样本数: {len(concept.member_indices)}")
    
    # 整合到认知网络
    network = integrate_into_cognitive_network(concepts)
    print(f"\n认知网络节点数: {len(network)}")