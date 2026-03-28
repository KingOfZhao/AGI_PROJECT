"""
认知范式化引擎

该模块实现了一个用于分析、解构和重组人类专家知识结构的系统。
通过消除认知冗余（低效的思维步骤），生成高密度的“思维组块”，
旨在加速技能习得并构建结构化的长期记忆。

版本: 1.0.0
作者: AGI System Core
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeNodeType(Enum):
    """知识节点的类型枚举"""
    CONCEPT = "concept"         # 核心概念
    PROCEDURE = "procedure"     # 操作步骤
    REDUNDANT = "redundant"     # 冗余/低效步骤
    CHUNK = "chunk"             # 重组后的思维组块

@dataclass
class KnowledgeNode:
    """
    知识结构中的单个节点。
    
    Attributes:
        id (str): 节点的唯一标识符
        content (str): 知识内容描述
        node_type (KnowledgeNodeType): 节点类型
        frequency (int): 该步骤在专家思维中出现的频率
        efficiency_score (float): 效率评分 (0.0-1.0)，越高越好
        dependencies (Set[str]): 依赖的其他节点ID
    """
    id: str
    content: str
    node_type: KnowledgeNodeType
    frequency: int = 1
    efficiency_score: float = 1.0
    dependencies: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """数据验证"""
        if not self.id:
            raise ValueError("Node ID cannot be empty")
        if not 0.0 <= self.efficiency_score <= 1.0:
            raise ValueError("Efficiency score must be between 0.0 and 1.0")
        if self.frequency < 0:
            raise ValueError("Frequency cannot be negative")

class CognitiveParadigmEngine:
    """
    认知范式化引擎核心类。
    
    负责分析知识图谱，识别冗余，并重组为高效组块。
    
    Example:
        >>> engine = CognitiveParadigmEngine()
        >>> raw_nodes = [
        ...     KnowledgeNode("step1", "Check config", KnowledgeNodeType.PROCEDURE, efficiency_score=0.9),
        ...     KnowledgeNode("step2", "Wait 5s", KnowledgeNodeType.PROCEDURE, efficiency_score=0.2),
        ...     KnowledgeNode("step3", "Retry check", KnowledgeNodeType.PROCEDURE, efficiency_score=0.9)
        ... ]
        >>> engine.ingest_knowledge(raw_nodes)
        >>> engine.analyze_and_paradigmatize(redundancy_threshold=0.3)
        >>> chunks = engine.get_optimized_curriculum()
    """

    def __init__(self):
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.paradigm_chunks: List[KnowledgeNode] = []
        logger.info("Cognitive Paradigm Engine initialized.")

    def ingest_knowledge(self, nodes: List[KnowledgeNode]) -> None:
        """
        输入专家知识节点到引擎中。
        
        Args:
            nodes (List[KnowledgeNode]): 知识节点列表
        
        Raises:
            TypeError: 如果输入不是列表
        """
        if not isinstance(nodes, list):
            logger.error("Input must be a list of KnowledgeNodes.")
            raise TypeError("Input must be a list of KnowledgeNodes.")
        
        for node in nodes:
            if node.id in self.knowledge_graph:
                logger.warning(f"Node ID {node.id} already exists, merging frequency.")
                self.knowledge_graph[node.id].frequency += node.frequency
            else:
                self.knowledge_graph[node.id] = node
        
        logger.info(f"Ingested {len(nodes)} nodes. Total nodes: {len(self.knowledge_graph)}")

    def _identify_redundancies(self, threshold: float) -> List[str]:
        """
        [辅助函数] 识别图谱中的冗余节点。
        
        Args:
            threshold (float): 效率低于此值的节点被视为冗余
            
        Returns:
            List[str]: 冗余节点的ID列表
        """
        redundant_ids = []
        for node_id, node in self.knowledge_graph.items():
            if node.efficiency_score < threshold and node.node_type != KnowledgeNodeType.REDUNDANT:
                redundant_ids.append(node_id)
                logger.debug(f"Identified redundant node: {node_id} (Score: {node.efficiency_score})")
        return redundant_ids

    def analyze_and_paradigmatize(self, redundancy_threshold: float = 0.4) -> None:
        """
        核心功能：执行认知范式化分析。
        
        1. 识别低效（冗余）步骤。
        2. 标记冗余节点。
        3. 将剩余的高效节点重组为思维组块。
        
        Args:
            redundancy_threshold (float): 判定冗余的效率阈值 (0.0-1.0)。
        
        Raises:
            ValueError: 如果阈值不在有效范围内
        """
        if not (0.0 <= redundancy_threshold <= 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        if not self.knowledge_graph:
            logger.warning("Knowledge graph is empty. Nothing to analyze.")
            return

        logger.info(f"Starting analysis with redundancy threshold: {redundancy_threshold}")
        
        # 1. 识别并标记冗余
        redundant_ids = self._identify_redundancies(redundancy_threshold)
        for rid in redundant_ids:
            self.knowledge_graph[rid].node_type = KnowledgeNodeType.REDUNDANT
        
        logger.info(f"Marked {len(redundant_ids)} nodes as redundant.")

        # 2. 重组逻辑：将非冗余的连续节点合并为组块
        # 这里使用简单的线性聚合作为示例，实际应用中可使用拓扑排序或聚类算法
        current_chunk_content = []
        current_chunk_score = 0.0
        chunk_counter = 0

        sorted_nodes = sorted(self.knowledge_graph.values(), key=lambda n: n.id)

        for node in sorted_nodes:
            if node.node_type != KnowledgeNodeType.REDUNDANT:
                current_chunk_content.append(node.content)
                current_chunk_score += node.efficiency_score
            else:
                # 遇到冗余节点或列表结束时，保存当前累积的组块
                if current_chunk_content:
                    chunk_counter += 1
                    avg_score = current_chunk_score / len(current_chunk_content)
                    new_chunk = KnowledgeNode(
                        id=f"chunk_{chunk_counter}",
                        content=" -> ".join(current_chunk_content),
                        node_type=KnowledgeNodeType.CHUNK,
                        efficiency_score=avg_score,
                        dependencies=set() # 实际应用中需处理依赖关系
                    )
                    self.paradigm_chunks.append(new_chunk)
                    current_chunk_content = []
                    current_chunk_score = 0.0
        
        # 处理尾部剩余的组块
        if current_chunk_content:
            chunk_counter += 1
            avg_score = current_chunk_score / len(current_chunk_content)
            new_chunk = KnowledgeNode(
                id=f"chunk_{chunk_counter}",
                content=" -> ".join(current_chunk_content),
                node_type=KnowledgeNodeType.CHUNK,
                efficiency_score=avg_score
            )
            self.paradigm_chunks.append(new_chunk)

        logger.info(f"Paradigmatization complete. Generated {len(self.paradigm_chunks)} chunks.")

    def get_optimized_curriculum(self, format: str = "dict") -> Optional[List[Dict]]:
        """
        获取优化后的学习课程（思维组块列表）。
        
        Args:
            format (str): 返回格式，支持 'dict' 或 'json'。
            
        Returns:
            Optional[List[Dict]]: 优化后的组块数据列表。
        """
        if not self.paradigm_chunks:
            logger.warning("No paradigm chunks available. Run analyze_and_paradigmatize first.")
            return None

        result = []
        for chunk in self.paradigm_chunks:
            result.append({
                "id": chunk.id,
                "condensed_path": chunk.content,
                "density_score": round(chunk.efficiency_score, 2),
                "type": chunk.node_type.value
            })
        
        if format == "json":
            return json.dumps(result, indent=2)
        return result

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = CognitiveParadigmEngine()

    # 2. 模拟专家知识数据 (包含高效步骤和低效/冗余步骤)
    # 场景：模拟学习某种编程调试流程
    expert_data = [
        KnowledgeNode("s1", "Read Error Log", KnowledgeNodeType.PROCEDURE, efficiency_score=0.95),
        KnowledgeNode("s2", "Identify Stack Trace", KnowledgeNodeType.PROCEDURE, efficiency_score=0.90),
        KnowledgeNode("s3", "Panic and search Google", KnowledgeNodeType.PROCEDURE, efficiency_score=0.20), # 冗余
        KnowledgeNode("s4", "Open wrong file", KnowledgeNodeType.PROCEDURE, efficiency_score=0.30),         # 冗余
        KnowledgeNode("s5", "Locate Line Number", KnowledgeNodeType.PROCEDURE, efficiency_score=0.92),
        KnowledgeNode("s6", "Analyze Variable State", KnowledgeNodeType.PROCEDURE, efficiency_score=0.88),
    ]

    # 3. 导入数据
    try:
        engine.ingest_knowledge(expert_data)
        
        # 4. 执行范式化 (设定低于0.5为冗余)
        engine.analyze_and_paradigmatize(redundancy_threshold=0.5)
        
        # 5. 输出结果
        curriculum = engine.get_optimized_curriculum()
        print("\n--- Optimized Learning Curriculum (Mental Chunks) ---")
        for item in curriculum:
            print(f"Chunk ID: {item['id']}")
            print(f"  Path: {item['condensed_path']}")
            print(f"  Density: {item['density_score']}")
            print("-" * 40)
            
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected Error: {e}", exc_info=True)