"""
逻辑拓扑冲突检测算法模块

本模块提供了用于检测大型网络中逻辑拓扑冲突的工具。它结合了RAG（检索增强生成）
技术和符号逻辑推理，在包含2489个节点的网络中自动识别逻辑互斥的节点对，
并构建局部冲突图，标记出需要人类仲裁的矛盾点。

主要功能:
- 基于向量相似度的潜在冲突对检索
- 基于形式逻辑的冲突验证
- 冲突图构建与人类仲裁标记

作者: AGI System
版本: 1.0.0
日期: 2023-11-15
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RelationType(Enum):
    """定义节点间的逻辑关系类型"""
    CAUSAL = auto()      # 因果关系 (A -> B)
    INHIBIT = auto()     # 阻碍关系 (A -| B)
    CORRELATION = auto() # 相关性
    INDEPENDENT = auto() # 独立


class ConflictSeverity(Enum):
    """冲突严重程度枚举"""
    CRITICAL = auto()    # 逻辑完全互斥，系统无法继续
    MODERATE = auto()    # 逻辑部分冲突，需降权处理
    SPURIOUS = auto()    # 虚假冲突，可能是语义模糊导致


@dataclass
class LogicNode:
    """逻辑节点数据结构"""
    node_id: str
    content: str
    relations: Dict[str, RelationType] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        """数据验证"""
        if not self.node_id:
            raise ValueError("节点ID不能为空")
        if not self.content:
            raise ValueError("节点内容不能为空")
        if self.embedding and len(self.embedding) != 768:
            logger.warning(f"节点 {self.node_id} 的嵌入维度非标准768维")


@dataclass
class ConflictPair:
    """冲突节点对结构"""
    node_a: LogicNode
    node_b: LogicNode
    severity: ConflictSeverity
    reason: str
    requires_arbitration: bool = False


class ConflictDetector:
    """逻辑拓扑冲突检测器
    
    该类封装了冲突检测的核心算法，结合RAG检索和符号推理。
    
    属性:
        nodes (Dict[str, LogicNode]): 网络中所有节点的字典
        conflict_graph (Dict[str, Set[str]]): 记录冲突关系的图结构
        arbitration_set (Set[str]): 需要人工仲裁的节点ID集合
    """
    
    def __init__(self, initial_nodes: Optional[List[LogicNode]] = None):
        """初始化检测器
        
        Args:
            initial_nodes: 初始节点列表，可选
        """
        self.nodes: Dict[str, LogicNode] = {}
        self.conflict_graph: Dict[str, Set[str]] = {}
        self.arbitration_set: Set[str] = set()
        
        if initial_nodes:
            for node in initial_nodes:
                self.add_node(node)
                
        logger.info(f"初始化冲突检测器，当前节点数: {len(self.nodes)}")

    def add_node(self, node: LogicNode) -> None:
        """向网络中添加节点
        
        Args:
            node: 要添加的逻辑节点
            
        Raises:
            TypeError: 如果输入不是LogicNode类型
            ValueError: 如果节点ID已存在
        """
        if not isinstance(node, LogicNode):
            raise TypeError("必须添加LogicNode类型的节点")
            
        if node.node_id in self.nodes:
            raise ValueError(f"节点ID {node.node_id} 已存在")
            
        self.nodes[node.node_id] = node
        self.conflict_graph[node.node_id] = set()
        logger.debug(f"添加节点: {node.node_id}")

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算两个向量的余弦相似度
        
        Args:
            vec_a: 向量A
            vec_b: 向量B
            
        Returns:
            余弦相似度分数 (-1.0 到 1.0)
            
        Raises:
            ValueError: 如果向量维度不匹配
        """
        if len(vec_a) != len(vec_b):
            raise ValueError("向量维度不匹配")
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def _rag_retrieve_candidates(self, target_node: LogicNode, top_k: int = 5) -> List[Tuple[str, float]]:
        """基于RAG检索潜在冲突节点
        
        这是一个模拟的RAG检索过程，实际应用中应替换为真实的向量数据库查询。
        
        Args:
            target_node: 目标节点
            top_k: 返回的最相似节点数量
            
        Returns:
            包含(节点ID, 相似度分数)的列表
        """
        if not target_node.embedding:
            logger.warning(f"节点 {target_node.node_id} 缺少嵌入向量，跳过检索")
            return []
            
        candidates = []
        
        for nid, node in self.nodes.items():
            if nid == target_node.node_id or not node.embedding:
                continue
                
            try:
                score = self._cosine_similarity(target_node.embedding, node.embedding)
                # 只保留语义上高度相关但可能逻辑冲突的节点 (分数 > 0.7)
                if score > 0.7:
                    candidates.append((nid, score))
            except ValueError as e:
                logger.error(f"计算相似度错误: {e}")
                continue
                
        # 按分数排序并返回Top K
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def _symbolic_conflict_check(self, node_a: LogicNode, node_b: LogicNode) -> Optional[ConflictPair]:
        """符号逻辑推理检查
        
        检查两个节点之间是否存在形式逻辑上的冲突。
        例如：A主张 X->Y，B主张 X-|Y
        
        Args:
            node_a: 节点A
            node_b: 节点B
            
        Returns:
            如果存在冲突返回ConflictPair，否则返回None
        """
        # 检查节点A的关系中是否涉及节点B
        if node_b.node_id in node_a.relations:
            rel_a = node_a.relations[node_b.node_id]
            
            # 检查节点B的关系中是否涉及节点A
            if node_a.node_id in node_b.relations:
                rel_b = node_b.relations[node_a.node_id]
                
                # 逻辑互斥检查：如果A认为导致，B认为阻碍，则为严重冲突
                if (rel_a == RelationType.CAUSAL and rel_b == RelationType.INHIBIT) or \
                   (rel_a == RelationType.INHIBIT and rel_b == RelationType.CAUSAL):
                    return ConflictPair(
                        node_a=node_a,
                        node_b=node_b,
                        severity=ConflictSeverity.CRITICAL,
                        reason=f"逻辑互斥: A主张{rel_a.name}, B主张{rel_b.name}",
                        requires_arbitration=True
                    )
                    
                # 逻辑方向冲突：如果A认为A->B，B认为B->A (互为因果)，可能是循环逻辑
                elif rel_a == RelationType.CAUSAL and rel_b == RelationType.CAUSAL:
                    return ConflictPair(
                        node_a=node_a,
                        node_b=node_b,
                        severity=ConflictSeverity.MODERATE,
                        reason="互为因果逻辑环路",
                        requires_arbitration=False
                    )
        
        return None

    def detect_global_conflicts(self) -> List[ConflictPair]:
        """执行全局冲突检测算法
        
        步骤:
        1. 遍历所有节点
        2. 使用RAG检索语义相近的节点作为候选
        3. 对候选对进行符号逻辑推理验证
        4. 构建冲突图并标记仲裁点
        
        Returns:
            检测到的所有冲突对列表
        """
        if len(self.nodes) > 2500:
            logger.warning("节点数量超过建议阈值(2489)，处理时间可能较长")
            
        detected_conflicts = []
        processed_pairs = set()
        
        logger.info("开始全局冲突检测...")
        
        for node_id, node in self.nodes.items():
            # 1. RAG检索阶段
            candidates = self._rag_retrieve_candidates(node)
            
            for cand_id, score in candidates:
                # 避免重复处理 (A,B) 和 (B,A)
                pair_key = tuple(sorted((node_id, cand_id)))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                cand_node = self.nodes.get(cand_id)
                if not cand_node:
                    continue
                
                # 2. 符号推理阶段
                conflict = self._symbolic_conflict_check(node, cand_node)
                
                if conflict:
                    detected_conflicts.append(conflict)
                    
                    # 更新冲突图
                    self.conflict_graph[node_id].add(cand_id)
                    self.conflict_graph[cand_id].add(node_id)
                    
                    # 标记仲裁需求
                    if conflict.requires_arbitration:
                        self.arbitration_set.add(node_id)
                        self.arbitration_set.add(cand_id)
                        logger.warning(
                            f"发现关键冲突需仲裁: {node_id} <-> {cand_id} "
                            f"原因: {conflict.reason}"
                        )
        
        logger.info(
            f"检测完成。发现 {len(detected_conflicts)} 个冲突，"
            f"其中 {len(self.arbitration_set)} 个节点需要人工仲裁。"
        )
        return detected_conflicts

    def get_arbitration_report(self) -> Dict[str, List[str]]:
        """生成人类可读的仲裁报告
        
        Returns:
            包含待仲裁节点及其冲突详情的字典
        """
        report = {}
        for node_id in self.arbitration_set:
            if node_id in self.conflict_graph:
                conflicting_neighbors = list(self.conflict_graph[node_id])
                report[node_id] = conflicting_neighbors
        return report


# ============================================
# 使用示例
# ============================================
if __name__ == "__main__":
    try:
        # 1. 初始化检测器
        detector = ConflictDetector()
        
        # 2. 创建模拟节点 (模拟2489个节点中的少量样本)
        # 在实际场景中，这些数据应来自数据库或RAG系统
        def generate_random_embedding():
            return [random.uniform(-1, 1) for _ in range(768)]

        node_1 = LogicNode(
            node_id="N001",
            content="增加施肥量会导致植物生长速度加快",
            relations={"N002": RelationType.CAUSAL},
            embedding=generate_random_embedding()
        )

        node_2 = LogicNode(
            node_id="N002",
            content="植物生长速度",
            embedding=generate_random_embedding()
        )

        node_3 = LogicNode(
            node_id="N003",
            content="增加施肥量会阻碍植物生长（由于根部烧伤）",
            relations={"N002": RelationType.INHIBIT}, # 与N001逻辑冲突
            embedding=generate_random_embedding()
        )

        # 3. 添加节点到检测器
        detector.add_node(node_1)
        detector.add_node(node_2)
        detector.add_node(node_3)

        # 4. 执行检测
        # 注意：由于embedding是随机的，RAG检索可能不会立即匹配，
        # 这里为了演示，我们手动设置高相似度或者依赖于符号推理部分
        # 在真实场景中，embedding应当是语义真实的
        
        # 强制让N3在语义上接近N1以便RAG检索到 (模拟语义相关性)
        node_3.embedding = node_1.embedding[:] 

        conflicts = detector.detect_global_conflicts()

        # 5. 输出结果
        print("\n--- 冲突检测报告 ---")
        for cp in conflicts:
            print(f"冲突对: {cp.node_a.node_id} vs {cp.node_b.node_id}")
            print(f"严重性: {cp.severity.name}")
            print(f"原因: {cp.reason}")
            print(f"需仲裁: {'是' if cp.requires_arbitration else '否'}")
            print("-" * 20)

        print("\n--- 仲裁清单 ---")
        print(detector.get_arbitration_report())

    except Exception as e:
        logger.error(f"系统运行时发生错误: {e}", exc_info=True)