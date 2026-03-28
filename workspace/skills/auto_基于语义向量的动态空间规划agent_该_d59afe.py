"""
高级技能模块：基于语义向量的动态空间规划Agent

该模块实现了从用户行为日志到物理空间拓扑的自动转译。
通过将建筑功能视为节点，用户行为视为注意力权重，构建动态语义向量网络，
从而生成空间布局建议（如开放式厨房）及模拟的BIM调整指令。

Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SpatialPlanningAgent")


class SpaceType(Enum):
    """定义建筑空间类型的枚举"""
    KITCHEN = "kitchen"
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    DINING = "dining"
    BALCONY = "balcony"
    UNKNOWN = "unknown"


@dataclass
class SpaceNode:
    """空间节点数据结构，包含语义向量"""
    id: str
    name: str
    space_type: SpaceType
    # 128维语义向量，模拟功能属性（如: 湿度、噪音、隐私性等特征的嵌入）
    semantic_vector: np.ndarray = field(default_factory=lambda: np.random.rand(128))
    position: Tuple[float, float] = (0.0, 0.0)  # x, y 坐标


@dataclass
class UserBehaviorLog:
    """用户行为日志数据结构"""
    timestamp: str
    origin_space: str  # 源空间ID
    target_space: str  # 目标空间ID
    duration: float    # 持续时间/权重
    action_type: str   # 动作类型


@dataclass
class LayoutSuggestion:
    """布局建议输出结构"""
    suggestion_id: str
    involved_spaces: Tuple[str, str]
    action: str  # e.g., "merge", "adjacent", "separate"
    confidence: float
    bim_instruction: Dict[str, Any]  # 模拟的BIM指令


class SemanticSpacePlanner:
    """
    基于语义向量和注意力机制的动态空间规划Agent。
    """
    
    def __init__(self, spatial_graph: Optional[Dict[str, SpaceNode]] = None):
        """
        初始化规划器。
        
        Args:
            spatial_graph (Optional[Dict[str, SpaceNode]]): 初始的空间图数据。
        """
        self.spatial_graph = spatial_graph if spatial_graph else {}
        self.attention_matrix = np.zeros((len(self.spatial_graph), len(self.spatial_graph)))
        logger.info(f"SemanticSpacePlanner initialized with {len(self.spatial_graph)} nodes.")

    def add_space_node(self, node: SpaceNode) -> None:
        """向图中添加空间节点"""
        if node.id in self.spatial_graph:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.spatial_graph[node.id] = node
        # 重置注意力矩阵以适应新节点
        self._reset_attention_matrix()
        logger.info(f"Added space node: {node.name} ({node.id})")

    def _reset_attention_matrix(self) -> None:
        """重置注意力矩阵大小"""
        n = len(self.spatial_graph)
        self.attention_matrix = np.zeros((n, n))

    def _get_node_index(self, node_id: str) -> int:
        """辅助函数：获取节点在矩阵中的索引"""
        try:
            return list(self.spatial_graph.keys()).index(node_id)
        except ValueError:
            logger.error(f"Node ID {node_id} not found in spatial graph.")
            raise KeyError(f"Node ID {node_id} not found.")

    def calculate_attention_weights(self, behavior_logs: List[UserBehaviorLog]) -> np.ndarray:
        """
        核心函数 1: 分析用户行为日志，计算空间之间的注意力权重矩阵。
        这里的'动线'被视为'Attention路径'。
        
        Args:
            behavior_logs (List[UserBehaviorLog]): 用户行为日志列表。
            
        Returns:
            np.ndarray: 更新后的注意力权重矩阵。
        """
        if not behavior_logs:
            logger.warning("Empty behavior logs provided.")
            return self.attention_matrix

        logger.info(f"Processing {len(behavior_logs)} behavior logs...")
        
        # 确保矩阵大小正确
        if self.attention_matrix.shape != (len(self.spatial_graph), len(self.spatial_graph)):
            self._reset_attention_matrix()

        for log in behavior_logs:
            try:
                i = self._get_node_index(log.origin_space)
                j = self._get_node_index(log.target_space)
                
                # 简单的注意力计算：累加交互频率和持续时间
                # 公式: Attention(i, j) += frequency_weight * duration_weight
                weight = 1.0 + (log.duration / 60.0) # 简单的归一化处理
                self.attention_matrix[i][j] += weight
                self.attention_matrix[j][i] += weight # 对称矩阵，表示双向关联
                
            except KeyError as e:
                logger.error(f"Skipping log due to missing node: {e}")
                continue
            except Exception as e:
                logger.exception(f"Unexpected error processing log: {e}")
                continue

        # 归一化处理
        max_val = np.max(self.attention_matrix)
        if max_val > 0:
            self.attention_matrix = self.attention_matrix / max_val
            
        logger.info("Attention matrix calculation complete.")
        return self.attention_matrix

    def generate_layout_suggestions(self, threshold: float = 0.7) -> List[LayoutSuggestion]:
        """
        核心函数 2: 基于注意力权重和语义向量相似度，生成空间布局调整建议。
        
        Args:
            threshold (float): 触发合并或连接建议的注意力阈值 (0.0 - 1.0)。
            
        Returns:
            List[LayoutSuggestion]: 建议列表。
        """
        suggestions = []
        node_ids = list(self.spatial_graph.keys())
        n = len(node_ids)
        
        if n == 0:
            return suggestions

        logger.info(f"Generating suggestions with threshold {threshold}...")

        # 遍历上三角矩阵以避免重复
        for i in range(n):
            for j in range(i + 1, n):
                weight = self.attention_matrix[i][j]
                
                if weight > threshold:
                    node_a = self.spatial_graph[node_ids[i]]
                    node_b = self.spatial_graph[node_ids[j]]
                    
                    # 计算语义相似度 (余弦相似度)
                    semantic_sim = self._calculate_cosine_similarity(
                        node_a.semantic_vector, 
                        node_b.semantic_vector
                    )
                    
                    # 决策逻辑：高交互 + 高语义相似 -> 建议开放式布局(合并)
                    # 高交互 + 低语义相似 -> 建议相邻但隔离(动线优化)
                    action = ""
                    bim_instr = {}
                    
                    if semantic_sim > 0.8:
                        action = "merge_open_layout"
                        confidence = (weight * 0.6) + (semantic_sim * 0.4)
                        bim_instr = {
                            "command": "REMOVE_WALL",
                            "between": [node_a.id, node_b.id],
                            "new_zone_type": "open_plan",
                            "merge_ids": f"{node_a.id}_{node_b.id}"
                        }
                        desc = f"Suggest merging {node_a.name} and {node_b.name} into open layout."
                    else:
                        action = "optimize_adjacency"
                        confidence = weight * 0.9
                        bim_instr = {
                            "command": "MOVE_OBJECT",
                            "target_space": node_a.id,
                            "new_position_adjacent_to": node_b.id,
                            "distance_weight": 1.0 / weight
                        }
                        desc = f"Suggest optimizing path between {node_a.name} and {node_b.name}."

                    suggestion = LayoutSuggestion(
                        suggestion_id=f"sug_{i}_{j}",
                        involved_spaces=(node_a.id, node_b.id),
                        action=action,
                        confidence=round(confidence, 3),
                        bim_instruction=bim_instr
                    )
                    suggestions.append(suggestion)
                    logger.info(desc)

        # 根据置信度排序
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions

    def _calculate_cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        辅助函数: 计算两个向量的余弦相似度。
        """
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化空间节点 (模拟语义向量)
    # 厨房和客厅的向量设置得比较相似 (模拟生活区域属性)
    vec_kitchen = np.random.rand(128)
    vec_living = vec_kitchen * 0.9 + np.random.rand(128) * 0.1 
    
    # 卧室向量差异较大
    vec_bedroom = np.random.rand(128) * -1

    node_kitchen = SpaceNode(id="s1", name="Kitchen", space_type=SpaceType.KITCHEN, semantic_vector=vec_kitchen)
    node_living = SpaceNode(id="s2", name="Living Room", space_type=SpaceType.LIVING_ROOM, semantic_vector=vec_living)
    node_bedroom = SpaceNode(id="s3", name="Master Bedroom", space_type=SpaceType.BEDROOM, semantic_vector=vec_bedroom)

    # 2. 初始化 Agent
    planner = SemanticSpacePlanner()
    planner.add_space_node(node_kitchen)
    planner.add_space_node(node_living)
    planner.add_space_node(node_bedroom)

    # 3. 模拟用户行为日志 (高频率在厨房和客厅之间移动)
    logs = [
        UserBehaviorLog("2023-10-01 10:00", "s1", "s2", 15.0, "walk"),
        UserBehaviorLog("2023-10-01 10:15", "s2", "s1", 20.0, "walk"),
        UserBehaviorLog("2023-10-01 12:00", "s1", "s2", 5.0, "walk"),
        UserBehaviorLog("2023-10-01 18:00", "s3", "s2", 60.0, "stay"), # 卧室到客厅，但频率低
    ]

    # 4. 计算注意力
    planner.calculate_attention_weights(logs)

    # 5. 生成建议
    results = planner.generate_layout_suggestions(threshold=0.5)

    print("\n--- Generated Spatial Planning Suggestions ---")
    for res in results:
        print(f"Suggestion: {res.action}")
        print(f"Spaces: {res.involved_spaces}")
        print(f"Confidence: {res.confidence}")
        print(f"BIM Instruction: {res.bim_instruction}")
        print("-" * 30)