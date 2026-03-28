"""
Module: auto_动态语境锚定_在多轮对话编程中_如何建_bcaa47
Description: 实现多轮对话编程中的动态语境锚定。构建‘变量引用解析图’，
             利用‘注意力焦点栈’将模糊代词（如‘它’）锚定到具体的真实节点。
Author: Senior Python Engineer (AGI System Component)
Domain: Cognitive Science / NLP
"""

import logging
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EntityType(Enum):
    """定义对话中可能出现的实体类型"""
    FILE = "file"
    VARIABLE = "variable"
    RESULT = "operation_result"
    FUNCTION = "function"
    UNDEFINED = "undefined"

@dataclass
class MemoryNode:
    """
    记忆节点，代表对话上下文中的一个具体对象或实体。
    
    Attributes:
        id (str): 唯一标识符
        content (Any): 节点存储的实际数据或内容
        type (EntityType): 实体类型
        timestamp (str): 创建时间
        salience (float): 显著性分数 (0.0 - 1.0)，用于判断被引用的可能性
        metadata (Dict): 额外的元数据
    """
    id: str
    content: Any
    type: EntityType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    salience: float = 0.5
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.type, EntityType):
            try:
                self.type = EntityType(self.type)
            except ValueError:
                self.type = EntityType.UNDEFINED
                logger.warning(f"Invalid entity type provided, defaulted to UNDEFINED for node {self.id}")

class AttentionFocusStack:
    """
    注意力焦点栈。
    维护当前对话中活跃的临时对象，模拟工作记忆。
    栈顶元素通常是当前注意力的焦点。
    """
    def __init__(self, max_size: int = 10):
        self._stack: List[MemoryNode] = []
        self.max_size = max_size

    def push(self, node: MemoryNode) -> None:
        """将新节点推入焦点栈"""
        # 如果节点已存在，先移除旧的（更新位置）
        self._stack = [n for n in self._stack if n.id != node.id]
        
        self._stack.append(node)
        # 维护栈大小，移除最旧/最底部的元素
        if len(self._stack) > self.max_size:
            removed = self._stack.pop(0)
            logger.info(f"Stack overflow, removed node: {removed.id}")
        
        logger.info(f"Pushed to focus stack: {node.id} (Type: {node.type.value})")

    def peek(self) -> Optional[MemoryNode]:
        """查看栈顶元素"""
        if not self._stack:
            return None
        return self._stack[-1]

    def get_all_active(self) -> List[MemoryNode]:
        """获取所有活跃节点，按显著性（最近使用）排序"""
        return sorted(self._stack, key=lambda x: x.salience, reverse=True)

class DynamicContextAnchor:
    """
    动态语境锚定系统。
    负责解析模糊引用，维护引用解析图。
    """
    def __init__(self):
        self.focus_stack = AttentionFocusStack()
        self.long_term_memory: Dict[str, MemoryNode] = {} # 模拟长程记忆
        self.reference_graph: Dict[str, List[str]] = {} # 引用关系图: {ref_word: [node_ids]}

    def add_context_node(self, node: MemoryNode) -> None:
        """
        添加新的上下文节点到系统（工作记忆+长程记忆）。
        
        Args:
            node (MemoryNode): 要添加的节点
        """
        if not isinstance(node, MemoryNode):
            raise ValueError("Invalid node type provided.")
        
        # 存入长程记忆
        self.long_term_memory[node.id] = node
        # 推入注意力焦点栈
        self.focus_stack.push(node)
        
        logger.info(f"Context updated: Node {node.id} added.")

    def _calculate_relevance_score(self, pronoun: str, node: MemoryNode) -> float:
        """
        辅助函数：计算代词与特定节点的相关性分数。
        
        Args:
            pronoun (str): 代词 (e.g., '它', '这个')
            node (MemoryNode): 候选节点
            
        Returns:
            float: 相关性分数 (0.0 - 1.0)
        """
        score = node.salience  # 基础分为显著性
        
        # 1. 位置加权：栈顶（最近）的元素权重更高
        active_nodes = self.focus_stack.get_all_active()
        if node in active_nodes:
            # 越靠前（栈顶），索引越大，权重越高
            idx = active_nodes.index(node)
            recency_boost = (idx + 1) / len(active_nodes) * 0.4
            score += recency_boost
        
        # 2. 语义加权 (此处简化逻辑，实际应接入向量模型)
        # 假设 '它' 倾向于指代 operation_result 或 variable
        if pronoun in ["它", "那个", "结果"]:
            if node.type == EntityType.RESULT:
                score += 0.2
            elif node.type == EntityType.VARIABLE:
                score += 0.1
        
        # 3. 类型匹配检查
        if node.type == EntityType.FILE and pronoun == "这个函数":
            score -= 0.5 # 惩罚类型不匹配

        return max(0.0, min(1.0, score))

    def resolve_reference(self, ambiguous_ref: str) -> Tuple[Optional[MemoryNode], Dict[str, Any]]:
        """
        核心函数：解析模糊引用，返回最可能的真实节点。
        
        Args:
            ambiguous_ref (str): 模糊引用词 (e.g., '它', '那个文件')
            
        Returns:
            Tuple[Optional[MemoryNode], Dict]: 返回解析出的节点及解析路径/日志
        """
        logger.info(f"Resolving reference: '{ambiguous_ref}'")
        
        candidates = self.focus_stack.get_all_active()
        if not candidates:
            logger.warning("No active context nodes found in attention stack.")
            return None, {"error": "Empty context"}

        best_match: Optional[MemoryNode] = None
        highest_score = -1.0
        resolution_path = []

        for node in candidates:
            score = self._calculate_relevance_score(ambiguous_ref, node)
            resolution_path.append({
                "node_id": node.id,
                "type": node.type.value,
                "score": score
            })
            
            if score > highest_score:
                highest_score = score
                best_match = node

        if best_match:
            # 锚定成功，更新节点的显著性
            best_match.salience = min(1.0, best_match.salience + 0.1)
            logger.info(f"Anchored '{ambiguous_ref}' to Node '{best_match.id}' (Score: {highest_score:.2f})")
            
            # 更新引用图
            if ambiguous_ref not in self.reference_graph:
                self.reference_graph[ambiguous_ref] = []
            self.reference_graph[ambiguous_ref].append(best_match.id)
            
            return best_match, {"path": resolution_path, "final_score": highest_score}
        
        return None, {"path": resolution_path, "error": "No match found"}

# 使用示例
if __name__ == "__main__":
    # 初始化锚定系统
    anchor_system = DynamicContextAnchor()
    
    # 模拟多轮对话产生的历史节点
    # 1. 用户提及一个文件
    file_node = MemoryNode(
        id="node_001", 
        content="data.csv", 
        type=EntityType.FILE,
        metadata={"size": "2GB"}
    )
    anchor_system.add_context_node(file_node)
    
    # 2. 系统执行操作，产生了一个结果对象 (这通常是最新的焦点)
    result_node = MemoryNode(
        id="node_002",
        content={"mean": 50.5, "std": 2.1},
        type=EntityType.RESULT,
        salience=0.8 # 结果通常是高焦点
    )
    anchor_system.add_context_node(result_node)
    
    # 3. 用户提问："把它保存起来"
    # 这里的 "它" 是模糊的，是指文件还是计算结果？
    # 系统应该解析为最新的、类型匹配的 'result_node'
    
    resolved_node, debug_info = anchor_system.resolve_reference("它")
    
    print("-" * 30)
    if resolved_node:
        print(f"解析成功:")
        print(f"  引用词: '它'")
        print(f"  锚定节点ID: {resolved_node.id}")
        print(f"  节点类型: {resolved_node.type.value}")
        print(f"  节点内容: {resolved_node.content}")
        print(f"  置信度: {debug_info['final_score']:.2f}")
    else:
        print("解析失败：无法在当前语境中找到匹配对象。")
    print("-" * 30)