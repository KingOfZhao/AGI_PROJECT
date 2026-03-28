"""
Module: auto_cognitive_overlap_detector
Description: 基于LLM语义向量空间的认知重叠检测与节点合并机制。
             旨在识别语义描述不同但底层实践逻辑一致的节点（如"摆摊选址" vs "流量入口分析"），
             防止AGI知识图谱中的认知冗余。
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, ValidationError

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型 ---

class NodeData(BaseModel):
    """定义知识节点的数据结构"""
    id: str = Field(..., description="节点唯一标识符")
    content: str = Field(..., description="节点的语义描述内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    embedding: Optional[List[float]] = Field(default=None, description="LLM生成的语义向量")

class OverlapReport(BaseModel):
    """重叠分析报告结构"""
    source_node_id: str
    target_node_id: str
    similarity_score: float
    is_overlapping: bool
    suggested_action: str  # "merge", "link", "ignore"

# --- 核心类 ---

class CognitiveSpace:
    """
    管理语义向量空间，负责节点的存储、检索和重叠计算。
    """
    
    def __init__(self, similarity_threshold: float = 0.85, vector_dim: int = 1536):
        """
        初始化认知空间。
        
        Args:
            similarity_threshold (float): 判定为"认知重叠"的余弦相似度阈值。
            vector_dim (int): LLM向量的维度（例如OpenAI text-embedding-3-small为1536）。
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("相似度阈值必须在0.0到1.0之间")
            
        self.nodes: Dict[str, NodeData] = {}
        self.vectors: Dict[str, np.ndarray] = {}  # 使用numpy加速计算
        self.similarity_threshold = similarity_threshold
        self.vector_dim = vector_dim
        logger.info(f"CognitiveSpace initialized with threshold {similarity_threshold}")

    def add_node(self, node: NodeData) -> bool:
        """
        向空间中添加节点。
        
        Args:
            node (NodeData): 包含向量的节点数据。
            
        Returns:
            bool: 是否添加成功。
        """
        try:
            if not node.embedding:
                logger.warning(f"Node {node.id} missing embedding, skipped.")
                return False
            
            if len(node.embedding) != self.vector_dim:
                logger.error(f"Vector dimension mismatch for node {node.id}. Expected {self.vector_dim}, got {len(node.embedding)}")
                return False
                
            self.nodes[node.id] = node
            self.vectors[node.id] = np.array(node.embedding, dtype=np.float32)
            logger.debug(f"Node {node.id} added to cognitive space.")
            return True
            
        except Exception as e:
            logger.error(f"Error adding node {node.id}: {str(e)}")
            return False

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度。
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def detect_overlaps(self, new_node: NodeData, top_k: int = 5) -> List[OverlapReport]:
        """
        核心功能：检测新节点与现有节点的认知重叠。
        
        Args:
            new_node (NodeData): 待检测的新节点。
            top_k (int): 返回最相似的前K个节点。
            
        Returns:
            List[OverlapReport]: 重叠报告列表。
        """
        if not new_node.embedding:
            logger.error(f"Node {new_node.id} has no embedding.")
            return []
            
        new_vec = np.array(new_node.embedding, dtype=np.float32)
        scores: List[Tuple[str, float]] = []
        
        # 计算与所有现有节点的相似度
        # 注意：生产环境应使用FAISS或Milvus等向量数据库进行ANN检索
        for existing_id, existing_vec in self.vectors.items():
            if existing_id == new_node.id:
                continue
                
            sim = self._cosine_similarity(new_vec, existing_vec)
            scores.append((existing_id, sim))
            
        # 排序并取Top K
        scores.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scores[:top_k]
        
        reports = []
        for target_id, score in top_candidates:
            is_overlap = score >= self.similarity_threshold
            action = "ignore"
            
            # 简单的决策逻辑：高重叠建议合并，中重叠建议链接
            if is_overlap:
                action = "merge" if score > 0.95 else "link"
                
            report = OverlapReport(
                source_node_id=new_node.id,
                target_node_id=target_id,
                similarity_score=round(score, 4),
                is_overlapping=is_overlap,
                suggested_action=action
            )
            reports.append(report)
            
            if is_overlap:
                logger.info(f"Overlap detected: '{new_node.content}' vs ID {target_id} (Score: {score:.4f})")
                
        return reports

# --- 辅助函数 ---

def generate_mock_embedding(text: str, dim: int = 1536) -> List[float]:
    """
    辅助函数：生成模拟的语义向量。
    在实际生产中，此处应调用LLM API (e.g., OpenAI, Anthropic)。
    为了代码可运行，使用简单的哈希映射生成确定性向量。
    """
    np.random.seed(hash(text) % (2**32))
    vec = np.random.randn(dim)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()

def format_merge_suggestion(report: OverlapReport, nodes_db: Dict[str, NodeData]) -> str:
    """
    辅助函数：格式化输出合并建议。
    """
    target_node = nodes_db.get(report.target_node_id)
    if not target_node:
        return "Target node not found."
        
    return (
        f"\n[Overlap Alert]\n"
        f"Source: '{nodes_db[report.source_node_id].content}'\n"
        f"Target: '{target_node.content}'\n"
        f"Similarity: {report.similarity_score}\n"
        f"Action: {report.suggested_action.upper()}\n"
        f"Reason: Possible semantic equivalence despite different wording."
    )

# --- 主程序示例 ---

if __name__ == "__main__":
    # 模拟现有数据库
    existing_nodes_data = [
        {"id": "node_001", "content": "分析商业街的人流量以确定最佳摊位位置"},
        {"id": "node_002", "content": "使用Python进行线性回归分析"},
        {"id": "node_003", "content": "确定实体店流量入口的分析逻辑"},
    ]
    
    # 初始化认知空间
    space = CognitiveSpace(similarity_threshold=0.85, vector_dim=128) # 使用128维简化演示
    
    # 加载现有节点
    all_nodes = {}
    for item in existing_nodes_data:
        # 生成模拟向量
        emb = generate_mock_embedding(item["content"], dim=128)
        node = NodeData(**item, embedding=emb)
        all_nodes[node.id] = node
        space.add_node(node)
        
    logger.info(f"Loaded {len(space.nodes)} existing nodes.")
    
    # 新输入信息
    new_input_content = "摆摊选址策略"
    new_node_input = {
        "id": "node_new_01",
        "content": new_input_content,
        "embedding": generate_mock_embedding(new_input_content, dim=128)
    }
    
    # 验证数据
    try:
        new_node_obj = NodeData(**new_node_input)
    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
        exit(1)
        
    # 执行检测
    overlap_reports = space.detect_overlaps(new_node_obj)
    
    # 输出结果
    print(f"Analyzing new input: '{new_input_content}'")
    for report in overlap_reports:
        if report.is_overlapping:
            msg = format_merge_suggestion(report, all_nodes)
            print(msg)