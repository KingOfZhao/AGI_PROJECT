"""
Module: cognitive_spatial_mapping_engine
Description: 构建'认知-空间双重映射引擎'。
             该能力不仅构建物理空间的几何地图，同时并行构建语义与社会关系的'认知地图'。
             机器人在物理移动时，实时更新对物体功能、人类意图及社会规则的动态理解，
             实现物理导航与社会认知的同步定位与自适应。
Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ObjectCategory(Enum):
    """物体功能分类枚举"""
    FURNITURE = "furniture"
    APPLIANCE = "appliance"
    HUMAN = "human"
    RESTRICTED_AREA = "restricted_area"
    INTERACTIVE_OBJECT = "interactive_object"

class SocialContext(Enum):
    """社会语境与规则枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    HIGH_INTERACTION_ZONE = "high_interaction"
    QUIET_ZONE = "quiet_zone"
    RESTRICTED = "restricted"

@dataclass
class SpatialNode:
    """物理空间节点：存储几何位置与基本属性"""
    node_id: str
    position_x: float
    position_y: float
    timestamp: float
    is_traversable: bool = True

@dataclass
class CognitiveNode:
    """认知节点：存储语义信息、社会关系与意图推测"""
    node_id: str
    linked_spatial_id: str
    category: ObjectCategory
    semantic_label: str
    social_context: SocialContext
    interaction_probability: float = 0.0
    human_intent_hint: Optional[str] = None
    last_updated: float = 0.0

@dataclass
class DualMapState:
    """双重地图状态容器"""
    spatial_graph: Dict[str, SpatialNode] = field(default_factory=dict)
    cognitive_graph: Dict[str, CognitiveNode] = field(default_factory=dict)
    adjacency_matrix: Dict[str, List[str]] = field(default_factory=dict)

class DualMappingEngine:
    """
    认知-空间双重映射引擎核心类。
    
    负责同步处理几何地图构建与语义认知图的更新，支持动态环境下的自适应导航。
    """
    
    def __init__(self, initial_range: Tuple[float, float, float, float] = (-100.0, -100.0, 100.0, 100.0)):
        """
        初始化引擎。
        
        Args:
            initial_range (Tuple): 地图的有效边界
        """
        self.state = DualMapState()
        self.map_bounds = initial_range  # (min_x, min_y, max_x, max_y)
        logger.info("Dual Mapping Engine initialized with bounds: %s", self.map_bounds)

    def _validate_coordinates(self, x: float, y: float) -> bool:
        """
        辅助函数：验证坐标是否在有效边界内。
        
        Args:
            x, y: 坐标值
            
        Returns:
            bool: 是否有效
        """
        min_x, min_y, max_x, max_y = self.map_bounds
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            logger.warning(f"Coordinates ({x}, {y}) out of bounds.")
            return False
        return True

    def _calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """
        辅助函数：计算两点间的欧几里得距离。
        """
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def add_observation(
        self, 
        position: Tuple[float, float], 
        semantic_data: Dict[str, Any],
        timestamp: float
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        核心函数 1: 添加新的观测数据，同步更新物理与认知地图。
        
        Args:
            position (Tuple): 物理坐标
            semantic_data (Dict): 包含 category, label, social_context, intent 等字段
            timestamp (float): 时间戳
            
        Returns:
            Tuple[str, str]: (物理节点ID, 认知节点ID)
            
        Raises:
            ValueError: 如果输入数据无效
        """
        x, y = position
        if not self._validate_coordinates(x, y):
            raise ValueError(f"Invalid coordinates: {position}")

        # 1. 更新物理地图
        spatial_id = f"sp_{uuid.uuid4().hex[:8]}"
        try:
            s_node = SpatialNode(
                node_id=spatial_id,
                position_x=x,
                position_y=y,
                timestamp=timestamp,
                is_traversable=semantic_data.get('is_traversable', True)
            )
            self.state.spatial_graph[spatial_id] = s_node
            logger.debug(f"Spatial node {spatial_id} added at ({x}, {y})")
        except Exception as e:
            logger.error(f"Failed to create spatial node: {e}")
            return None, None

        # 2. 更新认知地图
        cognitive_id = f"cg_{uuid.uuid4().hex[:8]}"
        try:
            category = ObjectCategory(semantic_data.get('category', 'FURNITURE'))
            context = SocialContext(semantic_data.get('social_context', 'PUBLIC'))
            
            c_node = CognitiveNode(
                node_id=cognitive_id,
                linked_spatial_id=spatial_id,
                category=category,
                semantic_label=semantic_data.get('label', 'unknown_object'),
                social_context=context,
                interaction_probability=semantic_data.get('interaction_prob', 0.5),
                human_intent_hint=semantic_data.get('intent', None),
                last_updated=timestamp
            )
            self.state.cognitive_graph[cognitive_id] = c_node
            logger.info(f"Cognitive node {cognitive_id} linked to {spatial_id} | Label: {c_node.semantic_label}")
            
        except ValueError as ve:
            logger.warning(f"Semantic data enum conversion failed: {ve}. Using defaults.")
            # 回退逻辑略
        except Exception as e:
            logger.error(f"Failed to create cognitive node: {e}")
            return spatial_id, None

        return spatial_id, cognitive_id

    def update_social_dynamics(self, robot_pos: Tuple[float, float], influence_radius: float = 5.0) -> Dict[str, Any]:
        """
        核心函数 2: 基于机器人当前位置，动态更新社会认知与导航代价。
        
        模拟机器人在移动过程中，根据与人类/物体的距离动态调整社会规则理解。
        
        Args:
            robot_pos (Tuple): 机器人当前位置
            influence_radius (float): 感知半径
            
        Returns:
            Dict: 包含当前环境的社会评估与导航建议
        """
        if not self._validate_coordinates(robot_pos[0], robot_pos[1]):
            return {"status": "error", "message": "Robot position out of bounds"}

        nearby_humans = 0
        high_priority_objects = []
        navigation_cost_multiplier = 1.0
        
        logger.info(f"Updating social dynamics at {robot_pos}...")

        for cg_id, c_node in self.state.cognitive_graph.items():
            # 获取关联的物理位置
            s_node = self.state.spatial_graph.get(c_node.linked_spatial_id)
            if not s_node: continue
            
            distance = self._calculate_distance(robot_pos, (s_node.position_x, s_node.position_y))
            
            if distance <= influence_radius:
                # 动态社会规则计算
                if c_node.category == ObjectCategory.HUMAN:
                    nearby_humans += 1
                    # 如果有人，增加周围区域的导航代价（礼貌性回避）
                    navigation_cost_multiplier += 0.5
                
                elif c_node.category == ObjectCategory.RESTRICTED_AREA:
                    # 禁区检测
                    high_priority_objects.append(c_node.semantic_label)
                    navigation_cost_multiplier = 999.0 # 不可通行

                elif c_node.category == ObjectCategory.INTERACTIVE_OBJECT and c_node.interaction_probability > 0.8:
                    high_priority_objects.append(c_node.semantic_label)

        # 生成环境状态摘要
        current_social_state = {
            "nearby_humans": nearby_humans,
            "detected_interactive_entities": high_priority_objects,
            "estimated_navigation_cost": navigation_cost_multiplier,
            "suggested_behavior": "CAUTIOUS" if nearby_humans > 0 else "NORMAL"
        }
        
        if navigation_cost_multiplier > 100:
            current_social_state["suggested_behavior"] = "STOP_REPLAN"
            logger.warning("Restricted zone detected! Triggering re-planning.")

        return current_social_state

    def get_map_status(self) -> Dict[str, int]:
        """获取当前地图状态统计"""
        return {
            "spatial_nodes": len(self.state.spatial_graph),
            "cognitive_nodes": len(self.state.cognitive_graph)
        }

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 实例化引擎
    engine = DualMappingEngine(initial_range=(0, 0, 50, 50))
    
    # 模拟数据输入
    # 格式说明: 
    # position: (x, y) 浮点数元组
    # semantic_data: 字典，包含 category(枚举值), label(字符串), social_context(枚举值), etc.
    
    data_point_1 = {
        "position": (10.5, 12.0),
        "semantic_data": {
            "category": "FURNITURE",
            "label": "Sofa",
            "social_context": "PUBLIC",
            "interaction_prob": 0.2
        },
        "timestamp": 1678900000.0
    }
    
    data_point_2 = {
        "position": (11.0, 12.5),
        "semantic_data": {
            "category": "HUMAN",
            "label": "Visitor_A",
            "social_context": "PUBLIC",
            "intent": "Watching TV",
            "interaction_prob": 0.9
        },
        "timestamp": 1678900001.0
    }

    # 1. 构建双重地图
    s_id_1, c_id_1 = engine.add_observation(**data_point_1)
    s_id_2, c_id_2 = engine.add_observation(**data_point_2)
    
    print(f"Map Status: {engine.get_map_status()}")

    # 2. 模拟机器人移动并更新认知
    robot_current_pos = (10.0, 11.0)
    social_insight = engine.update_social_dynamics(robot_current_pos, influence_radius=2.0)
    
    print(f"Social Insight at {robot_current_pos}: {social_insight}")