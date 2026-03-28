"""
名称: auto_开发_文化基因组_断层扫描仪_利用nlp_0ccfe8
描述: 开发'文化基因组'断层扫描仪。利用NLP分析历史文献与现代技术文档的向量分布差异，
      自动识别'失传技艺'对应的认知空洞。系统不仅仅是发现空洞，还能基于周边节点的逻辑
      （如相关工具的使用、半成品的制作）自动生成'复现假设'（候选节点），指导现代工匠
      进行针对性的'考古式'实践证伪。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识符
        text (str): 原始文本描述
        vector (Optional[np.ndarray]): 文本的向量表示
        era (str): 年代或时期标识 (e.g., 'modern', '1800s')
        meta (Dict[str, Any]): 元数据 (如工具类型、原材料)
    """
    id: str
    text: str
    vector: Optional[np.ndarray] = None
    era: str = "unknown"
    meta: Dict[str, Any] = field(default_factory=dict)

class CulturalGenomeScanner:
    """
    文化基因组断层扫描仪。
    
    通过比较历史文献与现代技术文档的语义向量空间，识别知识断层，
    并基于上下文生成复现假设。
    
    Example:
        >>> scanner = CulturalGenomeScanner()
        >>> modern_docs = [KnowledgeNode(id="m1", text="use a hammer", era="modern", vector=np.random.rand(384))]
        >>> hist_docs = [KnowledgeNode(id="h1", text="strike with heavy stone", era="ancient", vector=np.random.rand(384))]
        >>> gaps = scanner.scan_knowledge_gaps(modern_docs, hist_docs)
        >>> for gap in gaps:
        >>>     print(f"Gap found: {gap['center_node'].id}, Hypothesis: {gap['hypothesis']}")
    """
    
    def __init__(self, outlier_threshold: float = 0.5, similarity_floor: float = 0.3):
        """
        初始化扫描仪。
        
        Args:
            outlier_threshold (float): LOF异常检测的阈值。
            similarity_floor (float): 生成假设时邻居相似度的最低阈值。
        """
        self.outlier_threshold = outlier_threshold
        self.similarity_floor = similarity_floor
        logger.info("Cultural Genome Scanner initialized.")

    def _validate_vectors(self, nodes: List[KnowledgeNode]) -> bool:
        """
        辅助函数：验证节点列表中的向量数据是否有效。
        
        Args:
            nodes (List[KnowledgeNode]): 待验证的节点列表。
            
        Returns:
            bool: 如果所有节点都包含非空且维度一致的向量，返回True。
            
        Raises:
            ValueError: 如果向量缺失或维度不一致。
        """
        if not nodes:
            return True # 空列表视为有效（由调用者决定逻辑）
        
        first_vec_dim = None
        for node in nodes:
            if node.vector is None:
                msg = f"Node {node.id} is missing vector data."
                logger.error(msg)
                raise ValueError(msg)
            if first_vec_dim is None:
                first_vec_dim = node.vector.shape[0]
            elif node.vector.shape[0] != first_vec_dim:
                msg = f"Dimension mismatch for node {node.id}. Expected {first_vec_dim}, got {node.vector.shape[0]}"
                logger.error(msg)
                raise ValueError(msg)
        
        logger.debug(f"Validated {len(nodes)} nodes with dimension {first_vec_dim}.")
        return True

    def detect_semantic_outliers(self, modern_nodes: List[KnowledgeNode], historical_nodes: List[KnowledgeNode]) -> List[KnowledgeNode]:
        """
        核心函数：检测语义断层（认知空洞）。
        
        利用Local Outlier Factor (LOF) 或简单的密度分析，找出历史节点中
        远离现代节点聚集区的点，这些点代表了可能失传或未被现代工程体系
        覆盖的技艺。
        
        Args:
            modern_nodes (List[KnowledgeNode]): 现代技术文档节点列表。
            historical_nodes (List[KnowledgeNode]): 历史文献节点列表。
            
        Returns:
            List[KnowledgeNode]: 被标记为'认知空洞'的历史节点列表。
        """
        try:
            self._validate_vectors(modern_nodes)
            self._validate_vectors(historical_nodes)
        except ValueError as e:
            logger.error(f"Input validation failed: {e}")
            return []

        if not modern_nodes or not historical_nodes:
            logger.warning("Empty node list provided for comparison.")
            return []

        # 构建现代知识的背景分布 (Background Distribution)
        modern_vectors = np.array([n.vector for n in modern_nodes])
        historical_vectors = np.array([n.vector for n in historical_nodes])
        
        # 计算历史节点在现代知识背景下的局部密度
        # 这里简化使用 LOF 或者是平均距离，这里我们使用到现代簇中心的距离作为简单示例
        # 更高级的实现应使用特定的流形学习或LOF
        
        # 1. 计算现代知识的质心
        modern_centroid = np.mean(modern_vectors, axis=0)
        
        gaps = []
        logger.info(f"Scanning {len(historical_nodes)} historical nodes against modern context...")
        
        # 2. 计算每个历史节点到现代质心的距离（或Cosine相似度）
        # 这里的逻辑是：如果历史概念与现代核心概念差异极大，它可能是失传技艺
        # 但也可能仅仅是无关的噪音。我们需要结合上下文。
        # 使用 Local Outlier Factor 对 combined space 进行分析
        
        X = np.vstack([modern_vectors, historical_vectors])
        # 假设历史节点较少，标记为novelty
        clf = LocalOutlierFactor(novelty=True, n_neighbors=20)
        clf.fit(modern_vectors) # 仅在现代数据上训练
        
        # 预测历史数据是否为离群点
        predictions = clf.predict(historical_vectors)
        
        outlier_nodes = []
        for i, pred in enumerate(predictions):
            if pred == -1: # -1 代表离群点
                outlier_nodes.append(historical_nodes[i])
                logger.debug(f"Identified potential gap: {historical_nodes[i].id}")
                
        return outlier_nodes

    def generate_hypotheses(self, gap_node: KnowledgeNode, context_nodes: List[KnowledgeNode]) -> Dict[str, Any]:
        """
        核心函数：生成复现假设。
        
        基于认知空洞周边的节点（如相关的工具使用、半成品制作记录），
        推断该空洞可能的工艺逻辑。
        
        Args:
            gap_node (KnowledgeNode): 识别出的认知空洞节点。
            context_nodes (List[KnowledgeNode]): 相关的上下文节点（包括现代和历史）。
            
        Returns:
            Dict[str, Any]: 包含复现假设的字典，结构如下：
                {
                    "target_node_id": str,
                    "hypothesis": str,
                    "required_tools": List[str],
                    "estimated_logic": str,
                    "confidence": float
                }
        """
        if not context_nodes:
            return {
                "target_node_id": gap_node.id,
                "hypothesis": "Insufficient context to generate hypothesis.",
                "confidence": 0.0
            }

        # 寻找最相似的上下文节点（逻辑上的“相邻技艺”）
        gap_vec = gap_node.vector.reshape(1, -1)
        context_vecs = np.array([n.vector for n in context_nodes])
        
        similarities = cosine_similarity(gap_vec, context_vecs)[0]
        
        # 过滤低相似度的噪音
        relevant_indices = np.where(similarities > self.similarity_floor)[0]
        
        if len(relevant_indices) == 0:
            return {
                "target_node_id": gap_node.id,
                "hypothesis": "Context found but logical link is weak.",
                "confidence": 0.1
            }
            
        # 提取逻辑链条：工具 + 动作 -> 结果
        # 这里模拟NLP推理过程，实际应调用LLM或知识图谱推理
        related_tools = set()
        related_actions = set()
        
        for idx in relevant_indices:
            node = context_nodes[idx]
            # 假设meta中包含提取好的实体
            if "tools" in node.meta:
                related_tools.update(node.meta["tools"])
            # 简单地从文本提取动词（模拟）
            words = node.text.split()
            if words:
                related_actions.add(words[0]) # 假设第一个词是动作

        # 构建假设描述
        tool_str = ", ".join(related_tools) if related_tools else "unknown tools"
        action_str = ", ".join(related_actions) if related_actions else "manipulate"
        
        hypothesis_text = (
            f"To recreate '{gap_node.text}', likely involves using [{tool_str}] "
            f"to perform [{action_str}]. "
            f"Check physical residues on related artifacts."
        )
        
        # 计算置信度（基于最相似邻居的得分）
        max_sim = np.max(similarities[relevant_indices])
        
        result = {
            "target_node_id": gap_node.id,
            "hypothesis": hypothesis_text,
            "required_tools": list(related_tools),
            "estimated_logic": f"Combination of {action_str}",
            "confidence": float(max_sim)
        }
        
        logger.info(f"Generated hypothesis for {gap_node.id} with confidence {max_sim:.2f}")
        return result

    def scan_and_propose(self, 
                         modern_nodes: List[KnowledgeNode], 
                         historical_nodes: List[KnowledgeNode]) -> List[Dict[str, Any]]:
        """
        高级封装：执行完整的扫描与假设生成流程。
        
        Args:
            modern_nodes (List[KnowledgeNode]): 现代知识库。
            historical_nodes (List[KnowledgeNode]): 历史档案。
            
        Returns:
            List[Dict[str, Any]]: 所有识别出的空洞及其复现假设列表。
        """
        logger.info("Starting full Cultural Genome Scan...")
        
        # 1. 识别空洞
        gaps = self.detect_semantic_outliers(modern_nodes, historical_nodes)
        
        results = []
        # 2. 为每个空洞生成假设
        # 这里我们将所有非gap的历史节点和现代节点作为上下文
        all_context = [n for n in modern_nodes + historical_nodes if n not in gaps]
        
        for gap in gaps:
            hypothesis_data = self.generate_hypotheses(gap, all_context)
            results.append(hypothesis_data)
            
        logger.info(f"Scan complete. Found {len(results)} gaps.")
        return results

# ================= 使用示例 =================
if __name__ == "__main__":
    # 模拟数据生成 (通常这里会调用Embedding模型，如Sentence-Transformers)
    def generate_mock_vector(dim=128):
        return np.random.rand(dim)

    # 1. 准备现代知识
    modern_data = [
        KnowledgeNode(id="m1", text="Use CAD software to design gears", vector=generate_mock_vector(), era="modern", meta={"tools": ["Computer", "CAD"]}),
        KnowledgeNode(id="m2", text="CNC milling for metal parts", vector=generate_mock_vector(), era="modern", meta={"tools": ["CNC Machine", "Endmill"]}),
    ]

    # 2. 准备历史知识
    # 假设 h1 是现代知识的古代对应物 (非空洞，但在语义空间边缘)
    # h2 是完全失传的技艺 (语义空间离群点)
    # 为了模拟，我们让 h2 的向量稍微偏离一些
    base_vec = generate_mock_vector()
    
    historical_data = [
        KnowledgeNode(id="h1", text="Use compass to draw gears", vector=base_vec + np.random.normal(0, 0.1, 128), era="1800s", meta={"tools": ["Compass", "Paper"]}),
        KnowledgeNode(id="h2", text="Heat treatment of crystal swords", vector=np.random.rand(128) * 10, era="ancient", meta={"tools": ["Fire", "Crystal"]}), # 这个向量分布明显不同
    ]
    
    # 强制让现代数据聚集一点，以便 h2 成为离群点
    for n in modern_data:
        n.vector = base_vec + np.random.normal(0, 0.1, 128)
    historical_data[0].vector = base_vec + np.random.normal(0, 0.1, 128) # h1 也在簇附近

    # 3. 执行扫描
    scanner = CulturalGenomeScanner(outlier_threshold=0.2)
    scan_results = scanner.scan_and_propose(modern_data, historical_data)

    # 4. 输出结果
    print("-" * 50)
    print("Cultural Genome Tomography Report")
    print("-" * 50)
    for res in scan_results:
        print(f"Target: {res['target_node_id']}")
        print(f"Hypothesis: {res['hypothesis']}")
        print(f"Confidence: {res['confidence']:.4f}")
        print("-" * 20)