"""
Module: auto_抽象阶梯_的自动爬升与固化
Description: '抽象阶梯'的自动爬升与固化系统。
             该模块旨在自动识别大量平铺的具体技能节点中的共同模式，
             将其抽象化为更高层级的元技能（Meta-Skills），并建立层级化的父子关系。
             例如，从‘写Java代码’和‘写Python代码’中自动构建‘面向对象编程设计模式’这一更高级的抽象节点。
Author: Senior Python Engineer for AGI System
Version: 1.0.0
Domain: cognitive_science
"""

import logging
import json
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillNodeType(Enum):
    """技能节点类型枚举"""
    CONCRETE = "concrete"      # 具体操作，如 "写Python打印语句"
    ABSTRACT = "abstract"      # 抽象概念，如 "面向对象编程"
    META = "meta"              # 元技能，系统级抽象

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 节点的唯一标识符。
        name (str): 节点名称。
        description (str): 节点的详细描述。
        type (SkillNodeType): 节点类型（具体/抽象/元）。
        keywords (Set[str]): 节点关联的关键词集合，用于模式识别。
        parent_ids (Set[str]): 父节点ID集合，用于构建层级结构。
        children_ids (Set[str]): 子节点ID集合。
    """
    id: str
    name: str
    description: str
    type: SkillNodeType = SkillNodeType.CONCRETE
    keywords: Set[str] = field(default_factory=set)
    parent_ids: Set[str] = field(default_factory=set)
    children_ids: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, SkillNode):
            return False
        return self.id == other.id

class AbstractionLadderSystem:
    """
    抽象阶梯自动爬升与固化系统。
    
    负责管理技能图谱，自动发现共同模式，创建高层级节点，并维护父子关系。
    """

    def __init__(self, initial_nodes: Optional[List[SkillNode]] = None):
        """
        初始化系统。
        
        Args:
            initial_nodes (Optional[List[SkillNode]]): 初始技能节点列表。
        """
        self.nodes: Dict[str, SkillNode] = {}
        self._similarity_threshold = 0.4  # 抽象相似度阈值
        self._min_cluster_size = 2        # 形成抽象所需的最小节点数
        
        if initial_nodes:
            self.load_nodes(initial_nodes)

    def load_nodes(self, nodes: List[SkillNode]) -> None:
        """
        批量加载技能节点。
        
        Args:
            nodes (List[SkillNode]): 待加载的节点列表。
        """
        logger.info(f"Loading {len(nodes)} skill nodes into the system...")
        for node in nodes:
            if node.id in self.nodes:
                logger.warning(f"Duplicate node ID detected: {node.id}. Skipping.")
                continue
            # 数据清洗：确保关键词为集合
            if not isinstance(node.keywords, set):
                node.keywords = set(node.keywords)
            self.nodes[node.id] = node
        logger.info("Node loading complete.")

    def _extract_keywords_from_text(self, text: str) -> Set[str]:
        """
        辅助函数：从文本中提取关键词（模拟）。
        在真实AGI环境中，这里会调用NLP模型或Embedding接口。
        
        Args:
            text (str): 输入文本。
            
        Returns:
            Set[str]: 提取的关键词集合。
        """
        # 简单的预处理：转小写，分词，过滤停用词（此处仅作示例）
        # 实际场景应接入NLP Pipeline
        stop_words = {"the", "a", "is", "of", "to", "and", "in", "on", "for"}
        words = text.lower().replace('_', ' ').split()
        return {w for w in words if w not in stop_words and len(w) > 2}

    def _calculate_similarity(self, node_a: SkillNode, node_b: SkillNode) -> float:
        """
        计算两个节点之间的语义/关键词重叠度。
        
        Args:
            node_a (SkillNode): 节点A。
            node_b (SkillNode): 节点B。
            
        Returns:
            float: 相似度分数 (0.0 到 1.0)。
        """
        if not node_a.keywords or not node_b.keywords:
            return 0.0
        
        intersection = len(node_a.keywords.intersection(node_b.keywords))
        union = len(node_a.keywords.union(node_b.keywords))
        
        if union == 0:
            return 0.0
            
        return intersection / union

    def discover_and_consolidate_abstractions(self) -> List[SkillNode]:
        """
        核心功能：自动发现共同模式并爬升抽象阶梯。
        
        流程：
        1. 遍历所有具体的(CONCRETE)技能节点。
        2. 基于关键词相似度进行聚类（简化版：两两比较寻找共同点）。
        3. 提取共同特征作为新的抽象节点。
        4. 建立父子关系并固化到系统中。
        
        Returns:
            List[SkillNode]: 新生成的抽象节点列表。
        """
        logger.info("Starting abstraction ladder climbing process...")
        
        # 1. 筛选待处理的底层节点
        concrete_nodes = [
            n for n in self.nodes.values() 
            if n.type == SkillNodeType.CONCRETE
        ]
        
        if len(concrete_nodes) < self._min_cluster_size:
            logger.info("Not enough concrete nodes to form abstractions.")
            return []

        new_abstract_nodes: List[SkillNode] = []
        processed_pairs: Set[Tuple[str, str]] = set()
        
        # 2. 寻找共同模式（简化算法：基于两两相似度）
        # 在生产环境中应使用聚类算法 (如 DBSCAN, K-Means on Embeddings)
        for i, node_a in enumerate(concrete_nodes):
            for j, node_b in enumerate(concrete_nodes):
                if i >= j: 
                    continue
                
                pair_key = tuple(sorted((node_a.id, node_b.id)))
                if pair_key in processed_pairs:
                    continue

                similarity = self._calculate_similarity(node_a, node_b)
                
                if similarity >= self._similarity_threshold:
                    # 发现共同模式，创建或更新抽象节点
                    abstract_node = self._create_or_update_meta_skill(node_a, node_b)
                    if abstract_node and abstract_node.id not in [n.id for n in new_abstract_nodes]:
                        new_abstract_nodes.append(abstract_node)
                        logger.info(f"Created/Updated abstract skill: {abstract_node.name}")
                    
                    processed_pairs.add(pair_key)

        logger.info(f"Abstraction process complete. Generated {len(new_abstract_nodes)} new abstract nodes.")
        return new_abstract_nodes

    def _create_or_update_meta_skill(self, node_a: SkillNode, node_b: SkillNode) -> Optional[SkillNode]:
        """
        核心功能：根据两个具体节点创建或更新一个抽象父节点。
        
        Args:
            node_a (SkillNode): 相关节点A。
            node_b (SkillNode): 相关节点B。
            
        Returns:
            Optional[SkillNode]: 生成的抽象节点，如果创建失败则返回None。
        """
        # 1. 提取共同特征
        common_keywords = node_a.keywords.intersection(node_b.keywords)
        if not common_keywords:
            return None

        # 2. 生成抽象节点的名称和ID
        # 逻辑：取最高频的共同特征作为名称的一部分
        abstract_name_suffix = "_".join(list(common_keywords)[:3]) 
        abstract_id = f"meta_{abstract_name_suffix}_{hash(frozenset(common_keywords)) % 10000}"
        
        # 3. 检查是否已存在相似的抽象节点
        if abstract_id in self.nodes:
            meta_node = self.nodes[abstract_id]
        else:
            # 4. 创建新的抽象节点
            meta_node = SkillNode(
                id=abstract_id,
                name=f"Meta-Skill: {abstract_name_suffix.replace('_', ' ').title()}",
                description=f"Abstract pattern derived from commonalities between skills like {node_a.name} and {node_b.name}.",
                type=SkillNodeType.ABSTRACT,
                keywords=common_keywords
            )
            self.nodes[meta_node.id] = meta_node

        # 5. 建立父子关系
        # 子节点指向父
        node_a.parent_ids.add(meta_node.id)
        node_b.parent_ids.add(meta_node.id)
        # 父节点指向子
        meta_node.children_ids.add(node_a.id)
        meta_node.children_ids.add(node_b.id)
        
        return meta_node

    def export_graph_structure(self) -> str:
        """
        辅助功能：导出图谱结构为JSON字符串。
        
        Returns:
            str: JSON格式的图谱数据。
        """
        logger.info("Exporting graph structure...")
        export_data = {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type.value,
                    "parents": list(n.parent_ids)
                } for n in self.nodes.values()
            ]
        }
        return json.dumps(export_data, indent=2)

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. 模拟数据输入
    # 假设这是从系统数据库中提取的原始技能节点
    raw_skills = [
        SkillNode(
            id="sk_001", 
            name="Java Spring MVC", 
            description="Develop web apps using Java Spring",
            type=SkillNodeType.CONCRETE,
            keywords={"java", "web", "mvc", "class", "oop"}
        ),
        SkillNode(
            id="sk_002", 
            name="Python Django Dev", 
            description="Develop web apps using Python Django",
            type=SkillNodeType.CONCRETE,
            keywords={"python", "web", "mvc", "class", "object"}
        ),
        SkillNode(
            id="sk_003", 
            name="C++ Graphics Engine", 
            description="Rendering graphics with C++",
            type=SkillNodeType.CONCRETE,
            keywords={"cpp", "graphics", "rendering", "oop"}
        ),
        SkillNode(
            id="sk_004", 
            name="Java HashMap Usage", 
            description="Using hashmaps in Java",
            type=SkillNodeType.CONCRETE,
            keywords={"java", "data_structure", "map"}
        ),
        SkillNode(
            id="sk_005",
            name="Python Dictionary Ops",
            description="Using dicts in Python",
            type=SkillNodeType.CONCRETE,
            keywords={"python", "data_structure", "map"}
        )
    ]

    # 2. 初始化系统
    ladder_system = AbstractionLadderSystem(initial_nodes=raw_skills)
    
    # 3. 执行自动爬升与固化
    # 预期结果：
    # - sk_001 和 sk_002 可能合并为 "Meta-Skill: Web Mvc"
    # - sk_002 和 sk_003 可能因为 "oop" (如果有足够重叠) 合并 (本例阈值设置下可能不会)
    # - sk_004 和 sk_005 可能合并为 "Meta-Skill: Data Structure Map"
    try:
        new_nodes = ladder_system.discover_and_consolidate_abstractions()
        
        print(f"\nDiscovered {len(new_nodes)} new abstract nodes.")
        for node in new_nodes:
            print(f"New Meta Node: {node.name} (Children: {len(node.children_ids)})")

        # 4. 验证结构
        # 检查 sk_001 的父节点
        original_node = ladder_system.nodes["sk_001"]
        if original_node.parent_ids:
            parent_id = list(original_node.parent_ids)[0]
            print(f"\nNode '{original_node.name}' is now a child of '{ladder_system.nodes[parent_id].name}'")
            
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)