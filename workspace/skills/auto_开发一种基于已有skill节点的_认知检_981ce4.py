"""
模块名称: cognitive_skill_rag
描述: 实现基于语义向量的认知检索增强生成(RAG)系统。该系统旨在解决从海量技能节点库中
      根据模糊意图精准检索可复用代码块的挑战。通过建立“意图-技能”的语义索引，
      替代传统的关键词匹配，实现代码模式和逻辑块的智能复用。

作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === 数据结构定义 ===

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    属性:
        node_id (str): 唯一标识符
        name (str): 技能名称
        description (str): 功能描述
        code_snippet (str): Python代码块
        tags (List[str]): 功能标签
        embedding (Optional[List[float]]): 预计算的语义向量
    """
    node_id: str
    name: str
    description: str
    code_snippet: str
    tags: List[str]
    embedding: Optional[List[float]] = None

    def to_index_dict(self) -> Dict:
        """转换为用于索引的字典格式"""
        return {
            "id": self.node_id,
            "name": self.name,
            "desc": self.description,
            "tags": self.tags
        }


@dataclass
class RetrievalResult:
    """
    检索结果封装。
    
    属性:
        matched_node (SkillNode): 匹配到的最佳技能节点
        similarity_score (float): 语义相似度得分 (0.0 - 1.0)
        intent_alignment (str): 意图对齐解释
    """
    matched_node: SkillNode
    similarity_score: float
    intent_alignment: str


class CognitiveRAGSystem:
    """
    认知检索增强生成系统。
    
    核心功能:
    1. 对自然语言意图进行向量化编码
    2. 在高维向量空间中检索最匹配的技能节点
    3. 支持模糊意图的语义对齐
    
    使用示例:
        >>> # 初始化系统并加载技能库
        >>> rag = CognitiveRAGSystem(dimension=128)
        >>> skills = [SkillNode(...), ...]
        >>> rag.build_semantic_index(skills)
        >>> 
        >>> # 执行检索
        >>> intent = "我需要处理Excel文件并发送邮件"
        >>> result = rag.retrieve_skill(intent, top_k=1)
        >>> print(result[0].matched_node.name)
    """

    def __init__(self, dimension: int = 256, similarity_threshold: float = 0.75):
        """
        初始化RAG系统。
        
        参数:
            dimension (int): 语义向量的维度
            similarity_threshold (float): 判定为有效匹配的最低相似度阈值
        """
        if dimension <= 0:
            raise ValueError("Vector dimension must be positive.")
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0.")

        self.dimension = dimension
        self.similarity_threshold = similarity_threshold
        self._skill_database: Dict[str, SkillNode] = {}
        self._index_map: Dict[str, List[float]] = {}  # node_id -> vector
        
        logger.info(f"CognitiveRAGSystem initialized with dim={dimension}, threshold={similarity_threshold}")

    def _mock_embedding_model(self, text_input: str) -> List[float]:
        """
        [辅助函数] 模拟语义编码模型。
        
        在生产环境中，这应替换为真实的模型调用（如OpenAI Embedding或BERT）。
        这里使用简单的哈希映射来模拟稳定的向量生成。
        
        参数:
            text_input (str): 输入文本
            
        返回:
            List[float]: 归一化的语义向量
        """
        if not text_input:
            return [0.0] * self.dimension
        
        # 简单的模拟：基于字符生成伪随机但稳定的向量
        import hashlib
        text_hash = hashlib.sha256(text_input.encode()).hexdigest()
        
        vector = []
        for i in range(self.dimension):
            # 使用哈希片段生成浮点数
            start = (i * 4) % len(text_hash)
            hex_val = text_hash[start:start+4]
            val = int(hex_val, 16) / 65535.0  # 归一化
            vector.append(val)
            
        return vector

    def build_semantic_index(self, skill_nodes: List[SkillNode]) -> int:
        """
        [核心函数 1] 构建语义索引。
        
        遍历输入的技能节点列表，为每个节点生成语义向量并存储在内存数据库中。
        
        参数:
            skill_nodes (List[SkillNode]): 待索引的技能节点列表
            
        返回:
            int: 成功索引的节点数量
            
        异常:
            ValueError: 如果输入列表为空
        """
        if not skill_nodes:
            logger.warning("Empty skill node list provided for indexing.")
            return 0

        start_time = time.time()
        count = 0
        
        for node in skill_nodes:
            try:
                # 数据验证
                if not node.node_id or not node.code_snippet:
                    logger.warning(f"Skipping invalid node: {node.node_id}")
                    continue
                
                # 生成组合文本用于向量化 (名称 + 描述 + 标签)
                combined_text = f"{node.name} {node.description} {' '.join(node.tags)}"
                vector = self._mock_embedding_model(combined_text)
                
                # 存储
                node.embedding = vector
                self._skill_database[node.node_id] = node
                self._index_map[node.node_id] = vector
                count += 1
                
            except Exception as e:
                logger.error(f"Error indexing node {node.node_id}: {str(e)}")
                continue

        end_time = time.time()
        logger.info(f"Indexed {count} skills in {end_time - start_time:.4f} seconds.")
        return count

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        [辅助函数] 计算余弦相似度。
        """
        if len(vec_a) != len(vec_b):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def retrieve_skill(self, user_intent: str, top_k: int = 3) -> List[RetrievalResult]:
        """
        [核心函数 2] 执行认知检索。
        
        将用户意图转化为向量，与索引库中的向量进行比对，返回Top-K个最相关的技能。
        
        参数:
            user_intent (str): 用户的自然语言意图描述
            top_k (int): 返回的最大结果数量
            
        返回:
            List[RetrievalResult]: 检索结果列表，按相似度降序排列
        """
        if not user_intent:
            raise ValueError("User intent cannot be empty.")
        if not self._skill_database:
            logger.warning("Retrieval attempted on empty database.")
            return []

        logger.info(f"Processing intent: '{user_intent}'")
        
        # 1. 意图向量化
        intent_vector = self._mock_embedding_model(user_intent)
        
        # 2. 全量检索与打分 (在大规模场景下应使用FAISS等向量数据库)
        scored_candidates: List[Tuple[float, str]] = []
        
        for node_id, skill_vector in self._index_map.items():
            score = self._cosine_similarity(intent_vector, skill_vector)
            # 只保留高于阈值的结果
            if score >= self.similarity_threshold:
                scored_candidates.append((score, node_id))
        
        # 3. 排序并取Top-K
        # 使用Heapq在大规模数据下更高效，这里简单使用sort
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_candidates[:top_k]
        
        # 4. 构建返回结果
        results = []
        for score, node_id in top_matches:
            node = self._skill_database[node_id]
            result = RetrievalResult(
                matched_node=node,
                similarity_score=score,
                intent_alignment=f"Matched based on semantic similarity with score {score:.2f}"
            )
            results.append(result)
            
        logger.info(f"Found {len(results)} matches for intent.")
        return results

# === 独立的功能函数 ===

def export_rag_context(results: List[RetrievalResult], output_format: str = "json") -> str:
    """
    将检索结果格式化为LLM可读取的上下文提示词。
    
    参数:
        results (List[RetrievalResult]): 检索结果列表
        output_format (str): 输出格式，支持 'json' 或 'prompt'
        
    返回:
        str: 格式化后的字符串
    """
    if not results:
        return "No relevant skills found."
        
    if output_format == "json":
        # 简单的JSON导出
        data = []
        for res in results:
            data.append({
                "skill_name": res.matched_node.name,
                "score": res.similarity_score,
                "code": res.matched_node.code_snippet
            })
        return json.dumps(data, indent=2)
        
    elif output_format == "prompt":
        # 构造RAG Prompt
        context_blocks = []
        for i, res in enumerate(results):
            block = (
                f"[CANDIDATE {i+1}] (Score: {res.similarity_score:.2f})\n"
                f"Skill: {res.matched_node.name}\n"
                f"Description: {res.matched_node.description}\n"
                f"Code:\n{res.matched_node.code_snippet}\n"
            )
            context_blocks.append(block)
            
        return "Retrieved Skill Context:\n" + "\n".join(context_blocks)
    
    else:
        raise ValueError(f"Unsupported format: {output_format}")

# === 主程序入口 (演示) ===

if __name__ == "__main__":
    # 1. 构造模拟数据
    mock_skills = [
        SkillNode(
            node_id="skill_001",
            name="Data Cleaning",
            description="Removes null values and duplicates from pandas DataFrames",
            code_snippet="df.dropna(inplace=True)",
            tags=["pandas", "preprocessing"]
        ),
        SkillNode(
            node_id="skill_002",
            name="Send Email",
            description="Sends an email via SMTP protocol with attachments",
            code_snippet="smtplib.SMTP('smtp.example.com')",
            tags=["communication", "smtp"]
        ),
        SkillNode(
            node_id="skill_003",
            name="Excel Export",
            description="Exports DataFrame to an Excel file with formatting",
            code_snippet="df.to_excel('report.xlsx')",
            tags=["pandas", "excel", "io"]
        )
    ]

    # 2. 初始化RAG系统
    rag_system = CognitiveRAGSystem(dimension=64, similarity_threshold=0.5)
    
    # 3. 建立索引
    rag_system.build_semantic_index(mock_skills)
    
    # 4. 执行模糊检索
    # 意图：处理数据表格并保存为Excel (预期匹配 skill_001 和 skill_003)
    user_query = "Clean up my data table and save it as a spreadsheet"
    
    try:
        retrieved_results = rag_system.retrieve_skill(user_query, top_k=2)
        
        # 5. 格式化输出
        context_prompt = export_rag_context(retrieved_results, output_format="prompt")
        print("-" * 30)
        print(context_prompt)
        print("-" * 30)
        
    except Exception as e:
        logger.error(f"System error during execution: {e}")