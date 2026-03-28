"""
模块名称: auto_基于现有3714个节点库_构建语义指纹聚_b4f637
描述: 基于现有3714个节点库，构建语义指纹聚类模型，解决'意图词汇'与'节点标准名'的多对多映射问题。
      本实验旨在测试基于向量空间的相似度检索与基于图结构的关联度检索的融合效率。
"""

import logging
import time
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeItem:
    """节点数据结构"""
    node_id: str
    standard_name: str
    description: str
    category: str
    embedding: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "standard_name": self.standard_name,
            "description": self.description,
            "category": self.category
        }

@dataclass
class IntentQuery:
    """意图查询数据结构"""
    query_text: str
    context: Optional[Dict[str, Any]] = None

class SemanticFingerprintCluster:
    """
    语义指纹聚类模型，用于解决意图词汇与节点标准名的多对多映射问题。
    
    该模型融合了向量空间相似度检索和图结构关联度检索，通过以下步骤实现：
    1. 构建节点语义向量空间
    2. 基于K-Means进行语义聚类
    3. 构建节点关联图
    4. 融合向量相似度和图关联度进行最终排序
    
    输入格式:
        - nodes: List[Dict], 包含node_id, standard_name, description, category等字段
        - query: str, 用户意图描述文本
    
    输出格式:
        - List[Dict], 包含node_id, standard_name, score等字段的Top 5节点列表
    
    示例:
        >>> model = SemanticFingerprintCluster()
        >>> model.load_nodes(node_data)
        >>> model.build_model()
        >>> results = model.query("帮我调整一下图片的大小")
    """
    
    def __init__(self, n_clusters: int = 50, top_k: int = 5):
        """
        初始化语义指纹聚类模型。
        
        参数:
            n_clusters: 聚类数量，默认50
            top_k: 返回的Top K结果数，默认5
        """
        self.n_clusters = n_clusters
        self.top_k = top_k
        self.nodes: List[NodeItem] = []
        self.embeddings: Optional[np.ndarray] = None
        self.kmeans_model: Optional[KMeans] = None
        self.cluster_map: Dict[int, List[int]] = {}
        self.node_graph: Dict[str, Set[str]] = {}
        self._is_model_built = False
        
    def load_nodes(self, nodes_data: List[Dict[str, Any]]) -> None:
        """
        加载节点数据并生成嵌入向量。
        
        参数:
            nodes_data: 节点数据列表，每个元素包含node_id, standard_name, description, category
            
        异常:
            ValueError: 如果输入数据格式不正确
        """
        if not isinstance(nodes_data, list):
            raise ValueError("输入数据必须是列表格式")
            
        self.nodes = []
        for item in nodes_data:
            if not all(key in item for key in ['node_id', 'standard_name', 'description']):
                logger.warning(f"节点数据格式不正确，跳过: {item}")
                continue
                
            node = NodeItem(
                node_id=item['node_id'],
                standard_name=item['standard_name'],
                description=item['description'],
                category=item.get('category', 'default')
            )
            self.nodes.append(node)
            
        logger.info(f"成功加载 {len(self.nodes)} 个节点")
        
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        生成文本的嵌入向量（模拟实现）。
        
        实际应用中应替换为真实的嵌入模型，如BERT、RoBERTa等。
        
        参数:
            texts: 文本列表
            
        返回:
            嵌入向量矩阵
        """
        # 模拟嵌入向量生成 - 实际应用中应替换为真实模型
        np.random.seed(42)
        embeddings = np.random.rand(len(texts), 384)  # 384维向量
        
        # 模拟语义相似性 - 相同类别的节点有相似的嵌入
        for i, node in enumerate(self.nodes):
            if hasattr(node, 'category'):
                # 相同类别的节点嵌入相似
                category_hash = hash(node.category) % 100
                embeddings[i] = embeddings[i] * 0.7 + np.random.rand(384) * 0.3
                embeddings[i, :10] = embeddings[i, :10] + category_hash * 0.01
                
        logger.info(f"生成了 {len(texts)} 个文本的嵌入向量")
        return embeddings
    
    def build_model(self) -> None:
        """
        构建语义指纹聚类模型。
        
        步骤:
        1. 生成节点嵌入向量
        2. 执行K-Means聚类
        3. 构建节点关联图
        """
        if not self.nodes:
            raise ValueError("没有可用的节点数据，请先调用load_nodes加载数据")
            
        start_time = time.time()
        
        # 生成节点嵌入向量
        texts = [f"{node.standard_name} {node.description}" for node in self.nodes]
        self.embeddings = self._generate_embeddings(texts)
        
        # 为每个节点赋值嵌入向量
        for i, node in enumerate(self.nodes):
            node.embedding = self.embeddings[i]
        
        # 执行K-Means聚类
        self.kmeans_model = KMeans(n_clusters=min(self.n_clusters, len(self.nodes)), 
                                  random_state=42)
        clusters = self.kmeans_model.fit_predict(self.embeddings)
        
        # 构建聚类映射
        self.cluster_map = {}
        for i, cluster_id in enumerate(clusters):
            if cluster_id not in self.cluster_map:
                self.cluster_map[cluster_id] = []
            self.cluster_map[cluster_id].append(i)
            
        # 构建节点关联图（基于共现关系和类别相似性）
        self._build_node_graph()
        
        self._is_model_built = True
        logger.info(f"模型构建完成，耗时 {time.time() - start_time:.2f} 秒")
        
    def _build_node_graph(self) -> None:
        """构建节点关联图，基于类别和描述相似性"""
        self.node_graph = {node.node_id: set() for node in self.nodes}
        
        # 基于类别建立连接
        category_map = {}
        for i, node in enumerate(self.nodes):
            if node.category not in category_map:
                category_map[node.category] = []
            category_map[node.category].append(i)
            
        # 同类别的节点建立关联
        for indices in category_map.values():
            if len(indices) > 1:
                for i in range(len(indices)):
                    for j in range(i+1, len(indices)):
                        node_id_i = self.nodes[indices[i]].node_id
                        node_id_j = self.nodes[indices[j]].node_id
                        self.node_graph[node_id_i].add(node_id_j)
                        self.node_graph[node_id_j].add(node_id_i)
        
        # 基于描述相似性建立连接（前10%最相似的节点）
        similarity_matrix = cosine_similarity(self.embeddings)
        threshold = np.percentile(similarity_matrix, 90)
        
        for i in range(len(self.nodes)):
            for j in range(i+1, len(self.nodes)):
                if similarity_matrix[i, j] > threshold:
                    node_id_i = self.nodes[i].node_id
                    node_id_j = self.nodes[j].node_id
                    self.node_graph[node_id_i].add(node_id_j)
                    self.node_graph[node_id_j].add(node_id_i)
                    
        logger.info("节点关联图构建完成")
        
    def query(self, query_text: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        执行意图查询，返回Top 5匹配节点。
        
        参数:
            query_text: 用户意图描述文本
            context: 查询上下文信息（可选）
            
        返回:
            匹配节点列表，包含node_id, standard_name, score等信息
            
        异常:
            RuntimeError: 如果模型尚未构建
        """
        if not self._is_model_built:
            raise RuntimeError("模型尚未构建，请先调用build_model方法")
            
        if not query_text or not isinstance(query_text, str):
            raise ValueError("查询文本必须是非空字符串")
            
        logger.info(f"执行查询: {query_text}")
        
        # 1. 向量相似度检索
        query_embedding = self._generate_embeddings([query_text])[0]
        cosine_scores = cosine_similarity([query_embedding], self.embeddings)[0]
        
        # 2. 找到最相似的聚类
        cluster_id = self.kmeans_model.predict([query_embedding])[0]
        cluster_indices = self.cluster_map[cluster_id]
        
        # 3. 基于聚类结果提升相关节点的分数
        adjusted_scores = cosine_scores.copy()
        for idx in cluster_indices:
            adjusted_scores[idx] *= 1.5  # 聚类内节点加权
            
        # 4. 图关联度调整（基于图传播）
        top_indices = np.argsort(adjusted_scores)[-10:][::-1]  # 取前10个进行图扩展
        graph_boost = np.zeros(len(self.nodes))
        
        for idx in top_indices:
            node_id = self.nodes[idx].node_id
            neighbors = self.node_graph.get(node_id, set())
            for neighbor_id in neighbors:
                # 找到邻居节点的索引
                neighbor_idx = next((i for i, n in enumerate(self.nodes) if n.node_id == neighbor_id), None)
                if neighbor_idx is not None:
                    graph_boost[neighbor_idx] += 0.1 * adjusted_scores[idx]
                    
        # 5. 融合最终分数
        final_scores = adjusted_scores + graph_boost
        
        # 6. 返回Top K结果
        top_indices = np.argsort(final_scores)[-self.top_k:][::-1]
        results = []
        for idx in top_indices:
            node = self.nodes[idx]
            results.append({
                "node_id": node.node_id,
                "standard_name": node.standard_name,
                "description": node.description,
                "category": node.category,
                "score": float(final_scores[idx]),
                "match_type": "cluster" if idx in cluster_indices else "global"
            })
            
        logger.info(f"查询完成，返回 {len(results)} 个结果")
        return results
    
    def save_model(self, filepath: str) -> None:
        """
        保存模型到文件。
        
        参数:
            filepath: 模型保存路径
        """
        if not self._is_model_built:
            raise RuntimeError("模型尚未构建，无法保存")
            
        model_data = {
            "n_clusters": self.n_clusters,
            "top_k": self.top_k,
            "nodes": [node.to_dict() for node in self.nodes],
            "embeddings": self.embeddings.tolist() if self.embeddings is not None else None,
            "cluster_centers": self.kmeans_model.cluster_centers_.tolist() if self.kmeans_model else None,
            "node_graph": {k: list(v) for k, v in self.node_graph.items()}
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"模型已保存到 {filepath}")
        
    @classmethod
    def load_model(cls, filepath: str) -> 'SemanticFingerprintCluster':
        """
        从文件加载模型。
        
        参数:
            filepath: 模型文件路径
            
        返回:
            加载的模型实例
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
            
        instance = cls(
            n_clusters=model_data["n_clusters"],
            top_k=model_data["top_k"]
        )
        
        # 加载节点数据
        instance.nodes = [
            NodeItem(
                node_id=node["node_id"],
                standard_name=node["standard_name"],
                description=node["description"],
                category=node["category"]
            ) for node in model_data["nodes"]
        ]
        
        # 加载嵌入向量
        if model_data["embeddings"]:
            instance.embeddings = np.array(model_data["embeddings"])
            
        # 重建聚类模型
        if model_data["cluster_centers"]:
            instance.kmeans_model = KMeans(n_clusters=instance.n_clusters)
            instance.kmeans_model.cluster_centers_ = np.array(model_data["cluster_centers"])
            
        # 重建节点图
        instance.node_graph = {k: set(v) for k, v in model_data["node_graph"].items()}
        
        instance._is_model_built = True
        logger.info(f"模型从 {filepath} 加载完成")
        return instance

# 辅助函数
def evaluate_accuracy(model: SemanticFingerprintCluster, test_cases: List[Dict[str, Any]]) -> float:
    """
    评估模型的准确率。
    
    参数:
        model: 已构建的语义指纹聚类模型
        test_cases: 测试用例列表，每个用例包含query和expected_nodes
        
    返回:
        准确率（0-1之间）
    """
    if not test_cases:
        logger.warning("没有测试用例，无法评估准确率")
        return 0.0
        
    correct_count = 0
    total_count = len(test_cases)
    
    for case in test_cases:
        query = case.get("query", "")
        expected_nodes = set(case.get("expected_nodes", []))
        
        if not query or not expected_nodes:
            continue
            
        results = model.query(query)
        predicted_nodes = {result["node_id"] for result in results}
        
        # 计算交集比例作为准确率
        intersection = len(predicted_nodes.intersection(expected_nodes))
        case_accuracy = intersection / len(expected_nodes) if expected_nodes else 0
        
        if case_accuracy >= 0.8:  # 80%以上匹配视为正确
            correct_count += 1
            
    accuracy = correct_count / total_count
    logger.info(f"模型准确率: {accuracy:.2%}")
    return accuracy

# 示例数据生成函数
def generate_sample_nodes(count: int = 100) -> List[Dict[str, Any]]:
    """
    生成示例节点数据。
    
    参数:
        count: 要生成的节点数量
        
    返回:
        节点数据列表
    """
    categories = ["图像处理", "文本编辑", "数据转换", "文件操作", "网络请求", "UI控制"]
    actions = ["调整", "转换", "获取", "设置", "删除", "添加", "合并", "分割"]
    objects = ["图片", "文本", "文件", "数据", "配置", "界面", "元素", "属性"]
    
    nodes = []
    for i in range(count):
        category = categories[i % len(categories)]
        action = actions[i % len(actions)]
        obj = objects[i % len(objects)]
        
        node = {
            "node_id": f"node_{i:04d}",
            "standard_name": f"{action}{obj}_{i:04d}",
            "description": f"用于{action}{obj}的节点，属于{category}类别",
            "category": category
        }
        nodes.append(node)
        
    return nodes

if __name__ == "__main__":
    # 使用示例
    try:
        # 1. 生成示例数据
        sample_nodes = generate_sample_nodes(100)
        print(f"生成了 {len(sample_nodes)} 个示例节点")
        
        # 2. 初始化模型
        model = SemanticFingerprintCluster(n_clusters=10, top_k=5)
        
        # 3. 加载节点数据
        model.load_nodes(sample_nodes)
        
        # 4. 构建模型
        model.build_model()
        
        # 5. 执行查询
        query_result = model.query("帮我调整一下图片的大小")
        print("\n查询结果:")
        for i, result in enumerate(query_result, 1):
            print(f"{i}. {result['standard_name']} (分数: {result['score']:.4f})")
        
        # 6. 评估准确率（使用模拟测试用例）
        test_cases = [
            {
                "query": "调整图片大小",
                "expected_nodes": ["node_0000", "node_0006", "node_0012"]  # 模拟预期结果
            },
            {
                "query": "转换文本格式",
                "expected_nodes": ["node_0001", "node_0007", "node_0013"]
            }
        ]
        accuracy = evaluate_accuracy(model, test_cases)
        print(f"\n模型准确率: {accuracy:.2%}")
        
        # 7. 保存模型
        model.save_model("semantic_fingerprint_model.json")
        print("模型已保存")
        
        # 8. 加载模型
        loaded_model = SemanticFingerprintCluster.load_model("semantic_fingerprint_model.json")
        print("模型已加载")
        
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)