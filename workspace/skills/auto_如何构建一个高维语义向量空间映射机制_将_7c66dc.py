"""
高维语义向量空间映射机制模块

该模块实现了一个复杂的NLP处理管道，旨在将非结构化的自然语言意图（如用户的模糊想法）
映射为结构化的、可执行的功能需求树。它利用向量嵌入技术进行语义聚类，识别核心价值点，
并构建需求间的依赖关系图。

主要组件:
- SemanticIntentStructurer: 核心类，负责协调整个映射流程。
- 核心函数:
    - embed_intent: 将文本转换为高维向量。
    - cluster_and_extract_requirements: 执行聚类并生成需求列表。

依赖:
    pip install numpy scikit-learn networkx

输入格式:
    str: 自然语言文本，例如 "我想做一个更有格调的个人主页，需要展示我的摄影作品，还要有联系方式。"

输出格式:
    Dict: 包含 'requirements' (需求列表) 和 'dependency_graph' (邻接表表示的依赖关系图) 的字典。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Requirement:
    """
    需求数据结构
    
    Attributes:
        id (str): 需求唯一标识
        description (str): 需求描述
        category (str): 需求类别（如 'UI', 'Backend', 'Content'）
        priority (float): 优先级评分 (0.0 - 1.0)
        embedding (Optional[np.ndarray]): 需求的向量表示
    """
    id: str
    description: str
    category: str
    priority: float
    embedding: Optional[np.ndarray] = None

class SemanticIntentStructurer:
    """
    高维语义向量空间映射器。
    
    将非结构化文本转化为结构化需求树，包含聚类分析和依赖关系构建。
    """
    
    def __init__(self, n_clusters: int = 3, random_state: int = 42):
        """
        初始化映射器。
        
        Args:
            n_clusters (int): 语义聚类的主观数量，代表将意图拆解为几个主要模块。
            random_state (int): 随机种子，确保复现性。
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        # 在实际AGI场景中，这里会加载预训练模型 (e.g., SentenceTransformer)
        # 此处使用 TfidfVectorizer 作为演示用的嵌入生成器
        self.vectorizer = TfidfVectorizer(max_features=512)
        logger.info("SemanticIntentStructurer initialized with %d clusters.", n_clusters)

    def _validate_input(self, text: str) -> None:
        """
        辅助函数：验证输入文本的有效性。
        
        Args:
            text (str): 输入文本
            
        Raises:
            ValueError: 如果文本为空或过短
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input intent must be a non-empty string.")
        if len(text.strip()) < 5:
            raise ValueError("Input intent is too short for meaningful analysis.")
        logger.debug("Input validation passed.")

    def embed_intent(self, text: str) -> np.ndarray:
        """
        核心函数 1: 将自然语言意图映射到高维向量空间。
        
        注意：为了代码可独立运行，此处使用 TF-IDF 模拟语义嵌入。
        在生产环境中，应替换为 BERT/Roberta 等模型的输出。
        
        Args:
            text (str): 输入的自然语言意图
            
        Returns:
            np.ndarray: 形状为 (1, D) 的高维向量
            
        Raises:
            RuntimeError: 如果向量化失败
        """
        try:
            # 简单的预处理：将句子拆分为伪token以适应 Tfidf
            # 这里构造一个伪语料库来模拟 fit_transform
            corpus = [text, text[::-1]] # 仅为了演示创建上下文
            self.vectorizer.fit(corpus)
            vector = self.vectorizer.transform([text]).toarray()
            
            # 模拟高维填充，确保维度一致性
            padded_vector = np.zeros((1, 512))
            padded_vector[0, :vector.shape[1]] = vector
            logger.info("Intent embedded into vector space.")
            return padded_vector
        except Exception as e:
            logger.error("Embedding failed: %s", str(e))
            raise RuntimeError(f"Failed to embed text: {e}")

    def cluster_and_extract_requirements(self, text: str, pre_defined_modules: List[str] = None) -> Dict[str, Any]:
        """
        核心函数 2: 聚类分析并提取结构化需求。
        
        该函数执行以下步骤：
        1. 将句子拆解为语义片段（此处通过简单的标点或关键词模拟）。
        2. 对片段进行向量化。
        3. 使用 K-Means 进行聚类，识别核心功能点。
        4. 构建需求节点，并计算依赖关系。
        
        Args:
            text (str): 原始意图文本
            pre_defined_modules (List[str], optional): 预定义的功能域
            
        Returns:
            Dict: 包含需求数据和依赖图的结果集
        """
        self._validate_input(text)
        
        # 1. 模拟意图拆解 (AGI 应具备复杂的 Chunking 能力)
        # 这里简单按逗号和句号分割，实际应使用依存句法分析
        raw_segments = [s.strip() for s in text.replace('，', ',').replace('。', '.').split(',') if len(s.strip()) > 2]
        if not raw_segments:
            raw_segments = [text] # Fallback

        logger.info("Segmented intent into %d parts.", len(raw_segments))

        # 2. 向量化片段
        # 为了演示，我们重新初始化一个 vectorizer 用于这些片段
        try:
            seg_vectorizer = TfidfVectorizer()
            embeddings = seg_vectorizer.fit_transform(raw_segments).toarray()
        except ValueError:
            # 处理词汇表为空的情况
            embeddings = np.random.rand(len(raw_segments), 10) # Fallback random

        # 3. 聚类分析
        # 如果片段数量小于聚类数，减少聚类数
        n_clusters = min(self.n_clusters, len(raw_segments))
        if n_clusters == 0:
             return {"requirements": [], "dependency_graph": {}}

        kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
        clusters = kmeans.fit_predict(embeddings)
        
        # 4. 构建需求对象
        requirements = []
        category_map = {0: "Core_Functionality", 1: "User_Interface", 2: "Data_Management", 3: "Integration"}
        
        for idx, (segment, cluster_id) in enumerate(zip(raw_segments, clusters)):
            req = Requirement(
                id=f"REQ_{idx:02d}",
                description=segment,
                category=category_map.get(cluster_id, "Misc"),
                priority=np.random.uniform(0.5, 1.0), # 模拟优先级计算
                embedding=embeddings[idx]
            )
            requirements.append(req)
            
        # 5. 构建依赖关系图
        dep_graph = self._build_dependency_graph(requirements)
        
        logger.info("Structuring complete. Generated %d requirements.", len(requirements))
        
        return {
            "requirements": [r.__dict__ for r in requirements],
            "dependency_graph": dep_graph
        }

    def _build_dependency_graph(self, requirements: List[Requirement]) -> Dict[str, List[str]]:
        """
        辅助函数：基于语义相似度构建需求间的依赖图。
        
        逻辑：如果需求 B 与需求 A 的相似度超过阈值，且 B 是后续需求，
        则可能存在依赖 A -> B (或者基于语义包含关系)。
        
        Args:
            requirements (List[Requirement]): 需求列表
            
        Returns:
            Dict[str, List[str]]: 邻接表形式的依赖图 {source_id: [target_id]}
        """
        graph = {req.id: [] for req in requirements}
        threshold = 0.2 # 模拟阈值
        
        if len(requirements) < 2:
            return graph

        # 提取所有 embeddings
        matrix = np.array([req.embedding for req in requirements])
        
        # 计算余弦相似度矩阵
        # 注意：如果 embedding 维度不一致，这里会报错，但在真实 AGI 系统中 embedding 维度通常是固定的
        try:
            sim_matrix = cosine_similarity(matrix)
        except ValueError:
            return graph

        for i, req_i in enumerate(requirements):
            for j, req_j in enumerate(requirements):
                if i != j:
                    # 简单的依赖逻辑：如果语义高度相关，建立连接
                    # 在真实场景中，这里会有更复杂的逻辑判断 "A is prerequisite for B"
                    if sim_matrix[i][j] > threshold:
                        # 避免循环依赖，简单强制 i < j
                        if i < j:
                            graph[req_i.id].append(req_j.id)
                            
        return graph

# 使用示例
if __name__ == "__main__":
    # 初始化结构化器
    structurer = SemanticIntentStructurer(n_clusters=3)
    
    sample_intent = (
        "我想做一个更有格调的个人主页，"
        "需要展示我的摄影作品，"
        "还要有深色的模式切换功能，"
        "以及一个联系我的动态表单。"
    )
    
    try:
        # 执行映射
        result = structurer.cluster_and_extract_requirements(sample_intent)
        
        # 打印结果
        print("="*30)
        print("Extracted Requirements:")
        for req in result['requirements']:
            print(f"ID: {req['id']}, Cat: {req['category']}, Desc: {req['description']}")
            
        print("\nDependency Graph (Adjacency List):")
        for node, edges in result['dependency_graph'].items():
            print(f"{node} -> {edges}")
            
    except Exception as e:
        logger.error("An error occurred during execution: %s", e)