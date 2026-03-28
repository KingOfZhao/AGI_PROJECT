"""
模块: structural_code_rag
描述: 实现基于'真实节点'图拓扑结构的代码检索增强生成(RAG)系统。
      该系统旨在解决传统向量检索仅关注语义相似性而忽略代码结构逻辑的问题，
      通过图算法在3052个预置节点中寻找最具'结构相似性'的代码片段作为Few-shot示例。
作者: Senior Python Engineer
版本: 1.0.0
"""

import logging
import hashlib
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class CodeNode:
    """
    表示代码图谱中的真实节点。
    
    属性:
        id (str): 节点的唯一标识符 (UUID)。
        node_type (str): 节点类型 (如 'Function', 'Class', 'Variable')。
        content (str): 代码片段内容。
        dependencies (List[str]): 该节点依赖的其他节点ID列表。
        structural_hash (str): 基于AST结构的哈希值，用于快速结构比对。
    """
    id: str
    node_type: str
    content: str
    dependencies: List[str] = field(default_factory=list)
    structural_hash: str = ""

@dataclass
class StructuredIntent:
    """
    结构化意图输入，包含用户需求及其推测的结构特征。
    
    属性:
        description (str): 自然语言描述。
        required_structure (Dict): 需要的代码结构特征 (如 {'loops': 1, 'api_calls': 2})。
        context_graph (List[str]): 当前上下文中已存在的相关节点ID。
    """
    description: str
    required_structure: Dict[str, int] = field(default_factory=dict)
    context_graph: List[str] = field(default_factory=list)

@dataclass
class RetrievalResult:
    """
    检索结果封装。
    """
    node_id: str
    code_snippet: str
    similarity_score: float
    structural_match_score: float

# --- 核心类实现 ---

class StructuralCodeRAG:
    """
    基于图结构的代码检索增强生成系统。
    
    该系统不依赖单纯的向量距离，而是利用预置的代码知识图谱（约3052个节点），
    通过计算结构指纹和拓扑重叠率来检索最佳Few-shot示例。
    """
    
    MIN_SIMILARITY_THRESHOLD = 0.15
    MAX_DEPENDENCY_HOPS = 3

    def __init__(self, graph_data: Optional[List[Dict]] = None):
        """
        初始化RAG系统。
        
        参数:
            graph_data: 预加载的图谱数据列表。如果为None，需手动调用load_graph。
        """
        self.node_store: Dict[str, CodeNode] = {}
        self.structure_index: Dict[str, Set[str]] = {}  # Hash -> Set of Node IDs
        self._initialize_graph(graph_data or [])
        logger.info(f"StructuralCodeRAG initialized with {len(self.node_store)} nodes.")

    def _initialize_graph(self, graph_data: List[Dict]) -> None:
        """加载并验证图谱数据。"""
        for item in graph_data:
            try:
                node = CodeNode(**item)
                if not node.structural_hash:
                    node.structural_hash = self._generate_structural_hash(node)
                
                self.node_store[node.id] = node
                
                # 构建结构哈希索引
                if node.structural_hash not in self.structure_index:
                    self.structure_index[node.structural_hash] = set()
                self.structure_index[node.structural_hash].add(node.id)
            except (TypeError, KeyError) as e:
                logger.warning(f"Skipping invalid node data: {item.get('id', 'Unknown')}. Error: {e}")

    def retrieve_few_shot_examples(
        self, 
        intent: StructuredIntent, 
        top_k: int = 3
    ) -> List[RetrievalResult]:
        """
        [核心函数] 根据结构化意图检索最佳代码示例。
        
        步骤:
        1. 结构指纹过滤: 基于哈希快速筛选结构相似的候选集。
        2. 拓扑邻近搜索: 基于上下文节点ID进行广度优先搜索(BFS)扩展。
        3. 综合评分: 结合结构匹配度与拓扑距离生成最终排序。
        
        参数:
            intent: 结构化意图对象。
            top_k: 返回的最大结果数量。
            
        返回:
            List[RetrievalResult]: 排序后的检索结果列表。
        
        异常:
            ValueError: 如果意图数据缺失关键字段。
        """
        if not intent.description:
            raise ValueError("Intent description cannot be empty")

        logger.info(f"Processing retrieval for intent: {intent.description[:50]}...")
        
        # 1. 计算意图的结构指纹
        target_hash = self._calculate_intent_hash(intent.required_structure)
        
        # 2. 候选集生成 (基于结构哈希)
        candidate_ids = self._find_candidates_by_hash(target_hash)
        
        # 3. 拓扑相关性计算
        scored_candidates = []
        
        # 如果有上下文图，优先寻找拓扑距离近的节点
        context_neighbors = self._get_context_neighbors(intent.context_graph)
        
        for cid in candidate_ids:
            if cid not in self.node_store:
                continue
                
            node = self.node_store[cid]
            
            # 计算结构匹配分 (0.0 - 1.0)
            struct_score = self._calculate_structure_similarity(
                intent.required_structure, 
                node
            )
            
            # 计算拓扑关联分 (0.0 - 1.0)
            topo_score = 0.0
            if cid in context_neighbors:
                # 如果候选节点在上下文的邻居中，增加权重
                topo_score = 1.0 / (context_neighbors[cid] + 1) # 距离越近分越高
            
            # 综合评分: 结构是基础，拓扑是加权
            # 如果没有上下文，主要看结构；有上下文，则结合拓扑
            final_score = (struct_score * 0.6) + (topo_score * 0.4)
            
            if final_score >= self.MIN_SIMILARITY_THRESHOLD:
                scored_candidates.append(
                    RetrievalResult(
                        node_id=cid,
                        code_snippet=node.content,
                        similarity_score=final_score,
                        structural_match_score=struct_score
                    )
                )
        
        # 排序并返回Top K
        scored_candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_candidates[:top_k]

    def _generate_structural_hash(self, node: CodeNode) -> str:
        """
        [辅助函数] 生成节点的结构哈希。
        
        真实场景中应基于AST生成。此处模拟基于类型和依赖数量的简单哈希。
        """
        # 模拟AST特征的简化逻辑
        signature = f"{node.node_type}:{len(node.dependencies)}"
        return hashlib.md5(signature.encode()).hexdigest()

    def _calculate_intent_hash(self, structure: Dict[str, int]) -> str:
        """计算意图特征的结构哈希。"""
        if not structure:
            return "generic_structure"
        sorted_keys = sorted(structure.keys())
        signature = ",".join([f"{k}:{structure[k]}" for k in sorted_keys])
        return hashlib.md5(signature.encode()).hexdigest()

    def _find_candidates_by_hash(self, target_hash: str) -> Set[str]:
        """通过哈希索引寻找候选节点。"""
        # 精确匹配
        if target_hash in self.structure_index:
            return self.structure_index[target_hash]
        
        # 如果没有精确匹配，这里应该实现模糊匹配或向量检索作为后备
        # 为演示目的，如果精确匹配失败，返回所有节点的一个子集或空集
        logger.warning("Exact structural hash match not found, falling back to broad search.")
        return set(list(self.node_store.keys())[:50]) # 仅作演示，限制范围

    def _get_context_neighbors(self, node_ids: List[str]) -> Dict[str, int]:
        """
        获取上下文节点的邻居及距离。
        返回 Dict[NodeID, Distance]。
        """
        neighbors_map: Dict[str, int] = {}
        queue = [(nid, 0) for nid in node_ids if nid in self.node_store]
        visited = set(node_ids)
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth > self.MAX_DEPENDENCY_HOPS:
                continue
            
            neighbors_map[current_id] = depth
            
            # 向外扩展 (查找依赖)
            current_node = self.node_store.get(current_id)
            if current_node:
                for dep_id in current_node.dependencies:
                    if dep_id not in visited and dep_id in self.node_store:
                        visited.add(dep_id)
                        queue.append((dep_id, depth + 1))
                        
        return neighbors_map

    def _calculate_structure_similarity(self, required: Dict[str, int], node: CodeNode) -> float:
        """计算结构特征的相似度（简化版Jaccard相似度逻辑）。"""
        if not required:
            return 0.5 # 无特定结构要求，给基础分
        
        # 这里应该比较AST特征，此处简化为比较依赖数量是否接近
        # 真实代码应解析 node.content 的 AST 与 required 进行比对
        score = 0.0
        # 模拟逻辑：如果节点类型匹配，得分
        if "type" in required and node.node_type == required.get("type"):
            score += 0.5
        
        return min(score + 0.3, 1.0) # 加上基础分

    def save_index(self, filepath: str) -> None:
        """将当前索引状态保存到文件。"""
        data = {
            "nodes": [n.__dict__ for n in self.node_store.values()],
            "index": {k: list(v) for k, v in self.structure_index.items()}
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Index saved to {filepath}")
        except IOError as e:
            logger.error(f"Failed to save index: {e}")

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 模拟数据准备 (模拟 3052 个节点的缩影)
    mock_nodes = [
        {
            "id": "node_001",
            "node_type": "Function",
            "content": "def fetch_data(url):\n    return requests.get(url)",
            "dependencies": ["node_002"], # depends on requests lib wrapper
            "structural_hash": "" # Auto-generated
        },
        {
            "id": "node_002",
            "node_type": "Import",
            "content": "import requests",
            "dependencies": [],
            "structural_hash": ""
        },
        {
            "id": "node_003",
            "node_type": "Function",
            "content": "def process_data(data):\n    for item in data:\n        print(item)",
            "dependencies": [],
            "structural_hash": ""
        }
    ]
    
    # 2. 初始化系统
    rag_system = StructuralCodeRAG(graph_data=mock_nodes)
    
    # 3. 定义用户意图
    user_intent = StructuredIntent(
        description="I need a function to call an external API",
        required_structure={"type": "Function", "api_calls": 1},
        context_graph=[] # No prior context
    )
    
    # 4. 检索
    try:
        results = rag_system.retrieve_few_shot_examples(user_intent, top_k=2)
        print("\n--- Retrieval Results ---")
        for res in results:
            print(f"Score: {res.similarity_score:.2f} | ID: {res.node_id}")
            print(f"Code:\n{res.code_snippet}\n")
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")