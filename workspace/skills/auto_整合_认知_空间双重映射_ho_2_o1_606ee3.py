"""
高级技能模块：认知-空间双重映射与动态语境锚定整合
名称: auto_整合_认知_空间双重映射_ho_2_o1_606ee3

该模块实现了物理环境中的语义理解与空间定位的深度融合。通过整合认知映射
与动态语境，系统能够将模糊的自然语言指令（如"那个红色的阀门"）转化为
精确的物理坐标，并结合操作意图（如"关小点"）生成增强现实(AR)导航路径。

主要功能：
1. 多模态语义解析与实体对齐
2. 物理空间坐标实时计算
3. 基于语境的操作指令生成
4. AR可视化路径渲染数据生成

依赖库：
- numpy: 用于空间向量计算
- typing: 类型注解支持
- logging: 日志记录
- dataclasses: 数据结构定义
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """物理实体类型枚举"""
    VALVE = "valve"
    PUMP = "pump"
    SENSOR = "sensor"
    PIPE = "pipe"
    TANK = "tank"
    CONTROL_PANEL = "control_panel"
    UNKNOWN = "unknown"


class OperationType(Enum):
    """操作类型枚举"""
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    ADJUST = "adjust"
    INSPECT = "inspect"
    REPAIR = "repair"
    NAVIGATE = "navigate"


class UrgencyLevel(Enum):
    """紧急程度枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SpatialPosition:
    """空间位置数据结构"""
    x: float  # X坐标（米）
    y: float  # Y坐标（米）
    z: float  # Z坐标（米）
    confidence: float = 1.0  # 位置置信度 [0.0, 1.0]
    reference_frame: str = "world"  # 参考坐标系
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "confidence": self.confidence,
            "reference_frame": self.reference_frame
        }
    
    def distance_to(self, other: 'SpatialPosition') -> float:
        """计算到另一个位置的距离"""
        return np.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([self.x, self.y, self.z])


@dataclass
class PhysicalEntity:
    """物理实体数据结构"""
    entity_id: str
    entity_type: EntityType
    position: SpatialPosition
    attributes: Dict[str, Any] = field(default_factory=dict)
    semantic_tags: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def matches_description(self, description: Dict[str, Any]) -> bool:
        """检查实体是否匹配描述"""
        # 检查颜色
        if "color" in description:
            if self.attributes.get("color") != description["color"]:
                return False
        
        # 检查类型
        if "type" in description:
            if self.entity_type.value != description["type"]:
                return False
        
        # 检查语义标签
        if "tags" in description:
            for tag in description["tags"]:
                if tag not in self.semantic_tags:
                    return False
        
        return True


@dataclass
class NavigationWaypoint:
    """导航路径点数据结构"""
    position: SpatialPosition
    instruction: str
    visual_cue: Optional[str] = None
    distance_to_next: float = 0.0
    estimated_time: float = 0.0  # 秒
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "position": self.position.to_dict(),
            "instruction": self.instruction,
            "visual_cue": self.visual_cue,
            "distance_to_next": self.distance_to_next,
            "estimated_time": self.estimated_time
        }


@dataclass
class ARVisualizationData:
    """AR可视化数据结构"""
    waypoints: List[NavigationWaypoint]
    target_entity: PhysicalEntity
    operation_hints: List[Dict[str, Any]]
    path_length: float
    estimated_duration: float
    visualization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "visualization_id": self.visualization_id,
            "waypoints": [wp.to_dict() for wp in self.waypoints],
            "target_entity": {
                "id": self.target_entity.entity_id,
                "type": self.target_entity.entity_type.value,
                "position": self.target_entity.position.to_dict()
            },
            "operation_hints": self.operation_hints,
            "path_length": self.path_length,
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at.isoformat()
        }


class CognitiveSpatialMapper:
    """
    认知-空间双重映射核心类
    
    该类整合了认知映射(ho_2_O1_7686)与动态语境锚定(tds_3_Q2_3)，
    实现语义空间与物理空间的深度融合。
    
    输入格式：
    {
        "text_input": "那个红色的阀门",
        "operation": "把它关小点",
        "user_position": {"x": 10.5, "y": 3.2, "z": 0.0},
        "context": {"urgency": "medium", "environment": "factory_floor_a"}
    }
    
    输出格式：
    {
        "visualization_id": "uuid",
        "waypoints": [...],
        "target_entity": {...},
        "operation_hints": [...],
        "path_length": 15.3,
        "estimated_duration": 45.0
    }
    """
    
    def __init__(self, knowledge_base: Optional[Dict[str, PhysicalEntity]] = None):
        """
        初始化认知-空间映射器
        
        Args:
            knowledge_base: 预加载的物理实体知识库
        """
        self.knowledge_base: Dict[str, PhysicalEntity] = knowledge_base or {}
        self.spatial_index: Dict[str, List[str]] = {}  # 空间索引，加速查询
        self.semantic_index: Dict[str, List[str]] = {}  # 语义索引
        
        # 初始化默认工厂环境
        self._initialize_default_environment()
        
        logger.info("CognitiveSpatialMapper initialized with %d entities", 
                   len(self.knowledge_base))
    
    def _initialize_default_environment(self) -> None:
        """初始化默认工厂环境实体"""
        default_entities = [
            PhysicalEntity(
                entity_id="VALVE_RED_001",
                entity_type=EntityType.VALVE,
                position=SpatialPosition(x=15.0, y=5.0, z=1.2),
                attributes={"color": "red", "size": "medium", "status": "open"},
                semantic_tags=["main", "cooling_system", "critical"]
            ),
            PhysicalEntity(
                entity_id="VALVE_BLUE_002",
                entity_type=EntityType.VALVE,
                position=SpatialPosition(x=12.0, y=8.0, z=1.2),
                attributes={"color": "blue", "size": "large", "status": "closed"},
                semantic_tags=["secondary", "water_supply"]
            ),
            PhysicalEntity(
                entity_id="PUMP_MAIN_001",
                entity_type=EntityType.PUMP,
                position=SpatialPosition(x=20.0, y=10.0, z=0.0),
                attributes={"color": "yellow", "power": "50kW", "status": "running"},
                semantic_tags=["main", "high_pressure"]
            ),
            PhysicalEntity(
                entity_id="SENSOR_TEMP_003",
                entity_type=EntityType.SENSOR,
                position=SpatialPosition(x=18.0, y=6.0, z=2.5),
                attributes={"type": "temperature", "range": "0-100C"},
                semantic_tags=["monitoring", "cooling_system"]
            )
        ]
        
        for entity in default_entities:
            self.knowledge_base[entity.entity_id] = entity
        
        self._rebuild_indices()
    
    def _rebuild_indices(self) -> None:
        """重建空间和语义索引"""
        # 清空现有索引
        self.spatial_index.clear()
        self.semantic_index.clear()
        
        for entity_id, entity in self.knowledge_base.items():
            # 构建空间索引（按区域划分）
            grid_x = int(entity.position.x // 10)
            grid_y = int(entity.position.y // 10)
            grid_key = f"{grid_x}_{grid_y}"
            
            if grid_key not in self.spatial_index:
                self.spatial_index[grid_key] = []
            self.spatial_index[grid_key].append(entity_id)
            
            # 构建语义索引
            for tag in entity.semantic_tags:
                if tag not in self.semantic_index:
                    self.semantic_index[tag] = []
                self.semantic_index[tag].append(entity_id)
            
            # 索引颜色属性
            color = entity.attributes.get("color")
            if color:
                color_key = f"color_{color}"
                if color_key not in self.semantic_index:
                    self.semantic_index[color_key] = []
                self.semantic_index[color_key].append(entity_id)
    
    def parse_semantic_input(
        self, 
        text_input: str,
        operation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解析语义输入，提取实体特征和操作意图
        
        Args:
            text_input: 用户输入的自然语言描述
            operation_context: 操作语境
            
        Returns:
            解析后的语义特征字典
        """
        logger.debug("Parsing semantic input: %s", text_input)
        
        # 颜色关键词映射
        color_keywords = {
            "红色": "red", "红": "red",
            "蓝色": "blue", "蓝": "blue",
            "黄色": "yellow", "黄": "yellow",
            "绿色": "green", "绿": "green",
            "白色": "white", "白": "white"
        }
        
        # 实体类型关键词映射
        type_keywords = {
            "阀门": "valve", "阀": "valve",
            "泵": "pump", "水泵": "pump",
            "传感器": "sensor",
            "管道": "pipe", "管": "pipe",
            "水箱": "tank",
            "控制面板": "control_panel"
        }
        
        # 操作关键词映射
        operation_keywords = {
            "关小": OperationType.ADJUST,
            "关小点": OperationType.ADJUST,
            "开大": OperationType.ADJUST,
            "开大点": OperationType.ADJUST,
            "打开": OperationType.TURN_ON,
            "开启": OperationType.TURN_ON,
            "关闭": OperationType.TURN_OFF,
            "关掉": OperationType.TURN_OFF,
            "检查": OperationType.INSPECT,
            "查看": OperationType.INSPECT,
            "维修": OperationType.REPAIR
        }
        
        parsed_result = {
            "entity_description": {},
            "operation_type": None,
            "operation_params": {},
            "confidence": 0.0
        }
        
        # 提取颜色
        for keyword, color in color_keywords.items():
            if keyword in text_input:
                parsed_result["entity_description"]["color"] = color
                parsed_result["confidence"] += 0.3
                break
        
        # 提取实体类型
        for keyword, entity_type in type_keywords.items():
            if keyword in text_input:
                parsed_result["entity_description"]["type"] = entity_type
                parsed_result["confidence"] += 0.4
                break
        
        # 提取操作意图
        if operation_context:
            for keyword, op_type in operation_keywords.items():
                if keyword in operation_context:
                    parsed_result["operation_type"] = op_type.value
                    parsed_result["operation_params"]["action"] = keyword
                    
                    # 提取调整方向
                    if "小" in operation_context:
                        parsed_result["operation_params"]["direction"] = "decrease"
                    elif "大" in operation_context:
                        parsed_result["operation_params"]["direction"] = "increase"
                    
                    parsed_result["confidence"] += 0.3
                    break
        
        # 语义歧义检测
        if parsed_result["confidence"] < 0.5:
            logger.warning("Low confidence in semantic parsing: %s", 
                         parsed_result["confidence"])
        
        logger.info("Semantic parsing result: %s", parsed_result)
        return parsed_result
    
    def find_matching_entities(
        self,
        description: Dict[str, Any],
        user_position: SpatialPosition,
        max_distance: float = 100.0,
        max_results: int = 5
    ) -> List[Tuple[PhysicalEntity, float]]:
        """
        根据描述查找匹配的物理实体
        
        Args:
            description: 实体描述字典
            user_position: 用户当前位置
            max_distance: 最大搜索距离（米）
            max_results: 最大返回结果数
            
        Returns:
            匹配的实体列表，包含实体和匹配分数
        """
        logger.debug("Finding entities matching: %s", description)
        
        candidates = []
        
        # 使用索引加速查询
        candidate_ids = set()
        
        # 通过颜色索引查找
        if "color" in description:
            color_key = f"color_{description['color']}"
            if color_key in self.semantic_index:
                candidate_ids.update(self.semantic_index[color_key])
        
        # 如果没有通过索引找到，遍历所有实体
        if not candidate_ids:
            candidate_ids = set(self.knowledge_base.keys())
        
        # 评估每个候选实体
        for entity_id in candidate_ids:
            entity = self.knowledge_base[entity_id]
            
            # 检查距离
            distance = entity.position.distance_to(user_position)
            if distance > max_distance:
                continue
            
            # 计算匹配分数
            score = self._calculate_match_score(entity, description)
            
            if score > 0:
                # 距离惩罚
                distance_penalty = distance / max_distance * 0.2
                final_score = score - distance_penalty
                candidates.append((entity, final_score, distance))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回结果
        results = [(c[0], c[1]) for c in candidates[:max_results]]
        
        logger.info("Found %d matching entities", len(results))
        return results
    
    def _calculate_match_score(
        self,
        entity: PhysicalEntity,
        description: Dict[str, Any]
    ) -> float:
        """
        计算实体与描述的匹配分数
        
        Args:
            entity: 物理实体
            description: 描述字典
            
        Returns:
            匹配分数 [0.0, 1.0]
        """
        score = 0.0
        total_weight = 0.0
        
        # 颜色匹配 (权重0.4)
        if "color" in description:
            total_weight += 0.4
            if entity.attributes.get("color") == description["color"]:
                score += 0.4
        
        # 类型匹配 (权重0.5)
        if "type" in description:
            total_weight += 0.5
            if entity.entity_type.value == description["type"]:
                score += 0.5
        
        # 标签匹配 (权重0.1)
        if "tags" in description:
            total_weight += 0.1
            matching_tags = sum(
                1 for tag in description["tags"] 
                if tag in entity.semantic_tags
            )
            score += 0.1 * (matching_tags / len(description["tags"]))
        
        # 归一化分数
        if total_weight > 0:
            score = score / total_weight
        
        return score
    
    def generate_navigation_path(
        self,
        start_position: SpatialPosition,
        target_entity: PhysicalEntity,
        operation_type: Optional[str] = None,
        obstacles: Optional[List[SpatialPosition]] = None
    ) -> List[NavigationWaypoint]:
        """
        生成从起点到目标的导航路径
        
        Args:
            start_position: 起始位置
            target_entity: 目标实体
            operation_type: 操作类型
            obstacles: 障碍物列表
            
        Returns:
            导航路径点列表
        """
        logger.info("Generating navigation path to entity: %s", 
                   target_entity.entity_id)
        
        waypoints = []
        
        # 简化的路径规划（实际应用中应使用A*或RRT算法）
        direct_distance = start_position.distance_to(target_entity.position)
        
        # 根据距离生成中间路径点
        num_waypoints = max(2, int(direct_distance / 5))
        
        start_np = start_position.to_numpy()
        end_np = target_entity.position.to_numpy()
        
        for i in range(num_waypoints):
            t = i / (num_waypoints - 1)
            # 线性插值
            interp_pos = start_np * (1 - t) + end_np * t
            
            # 添加小的随机偏移以模拟避障
            if 0 < i < num_waypoints - 1:
                interp_pos += np.random.randn(3) * 0.3
            
            position = SpatialPosition(
                x=float(interp_pos[0]),
                y=float(interp_pos[1]),
                z=float(interp_pos[2]),
                confidence=0.95
            )
            
            # 生成导航指令
            if i == 0:
                instruction = "开始导航"
                visual_cue = "arrow_start"
            elif i == num_waypoints - 1:
                instruction = f"已到达目标：{target_entity.entity_type.value}"
                visual_cue = "highlight_target"
            else:
                remaining = direct_distance * (1 - t)
                instruction = f"继续前进，剩余 {remaining:.1f} 米"
                visual_cue = "arrow_continue"
            
            waypoint = NavigationWaypoint(
                position=position,
                instruction=instruction,
                visual_cue=visual_cue,
                distance_to_next=direct_distance / num_waypoints if i < num_waypoints - 1 else 0,
                estimated_time=direct_distance / num_waypoints / 1.2  # 假设步行速度1.2m/s
            )
            
            waypoints.append(waypoint)
        
        # 添加操作提示
        if operation_type:
            operation_waypoint = NavigationWaypoint(
                position=target_entity.position,
                instruction=self._generate_operation_instruction(
                    target_entity, operation_type
                ),
                visual_cue="operation_hint",
                distance_to_next=0,
                estimated_time=0
            )
            waypoints.append(operation_waypoint)
        
        logger.info("Generated %d waypoints", len(waypoints))
        return waypoints
    
    def _generate_operation_instruction(
        self,
        entity: PhysicalEntity,
        operation_type: str
    ) -> str:
        """
        生成操作指令
        
        Args:
            entity: 目标实体
            operation_type: 操作类型
            
        Returns:
            操作指令字符串
        """
        instructions = {
            "adjust": f"请调整{entity.entity_type.value}，根据指示进行操作",
            "turn_on": f"请打开{entity.entity_type.value}",
            "turn_off": f"请关闭{entity.entity_type.value}",
            "inspect": f"请检查{entity.entity_type.value}状态",
            "repair": f"请对{entity.entity_type.value}进行维修"
        }
        
        return instructions.get(
            operation_type, 
            f"请对{entity.entity_type.value}执行操作"
        )
    
    def generate_ar_visualization(
        self,
        text_input: str,
        operation_context: str,
        user_position: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> ARVisualizationData:
        """
        主入口函数：生成完整的AR可视化数据
        
        Args:
            text_input: 用户输入的文本描述
            operation_context: 操作语境
            user_position: 用户当前位置 {"x": float, "y": float, "z": float}
            context: 额外上下文信息
            
        Returns:
            ARVisualizationData: 完整的AR可视化数据
            
        Raises:
            ValueError: 输入参数无效时
            RuntimeError: 无法找到匹配实体时
        """
        logger.info("Starting AR visualization generation")
        logger.debug("Input: text=%s, operation=%s, position=%s", 
                    text_input, operation_context, user_position)
        
        # 数据验证
        self._validate_input(user_position)
        
        # 创建用户位置对象
        user_pos = SpatialPosition(
            x=user_position["x"],
            y=user_position["y"],
            z=user_position.get("z", 0.0)
        )
        
        # 1. 语义解析
        parsed_semantics = self.parse_semantic_input(
            text_input, 
            operation_context
        )
        
        if parsed_semantics["confidence"] < 0.3:
            raise RuntimeError(
                f"语义理解置信度过低: {parsed_semantics['confidence']:.2f}"
            )
        
        # 2. 实体匹配
        matching_entities = self.find_matching_entities(
            parsed_semantics["entity_description"],
            user_pos
        )
        
        if not matching_entities:
            raise RuntimeError("未找到匹配的物理实体")
        
        # 选择最佳匹配
        target_entity, match_score = matching_entities[0]
        logger.info("Selected target entity: %s (score: %.2f)", 
                   target_entity.entity_id, match_score)
        
        # 3. 路径生成
        waypoints = self.generate_navigation_path(
            user_pos,
            target_entity,
            parsed_semantics.get("operation_type")
        )
        
        # 4. 生成操作提示
        operation_hints = self._generate_operation_hints(
            target_entity,
            parsed_semantics,
            context
        )
        
        # 5. 计算路径统计
        path_length = sum(wp.distance_to_next for wp in waypoints)
        estimated_duration = sum(wp.estimated_time for wp in waypoints)
        
        # 6. 构建结果
        result = ARVisualizationData(
            waypoints=waypoints,
            target_entity=target_entity,
            operation_hints=operation_hints,
            path_length=path_length,
            estimated_duration=estimated_duration
        )
        
        logger.info("AR visualization generated successfully: id=%s, path=%.2fm", 
                   result.visualization_id, path_length)
        
        return result
    
    def _validate_input(self, user_position: Dict[str, float]) -> None:
        """
        验证输入参数
        
        Args:
            user_position: 用户位置字典
            
        Raises:
            ValueError: 参数无效时
        """
        if not isinstance(user_position, dict):
            raise ValueError("user_position 必须是字典类型")
        
        required_keys = ["x", "y"]
        for key in required_keys:
            if key not in user_position:
                raise ValueError(f"user_position 缺少必需的键: {key}")
            
            value = user_position[key]
            if not isinstance(value, (int, float)):
                raise ValueError(f"user_position[{key}] 必须是数值类型")
            
            # 边界检查
            if abs(value) > 10000:
                raise ValueError(f"user_position[{key}] 超出有效范围")
    
    def _generate_operation_hints(
        self,
        target_entity: PhysicalEntity,
        parsed_semantics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        生成操作提示
        
        Args:
            target_entity: 目标实体
            parsed_semantics: 解析的语义信息
            context: 上下文信息
            
        Returns:
            操作提示列表
        """
        hints = []
        
        # 基本操作提示
        operation_type = parsed_semantics.get("operation_type")
        if operation_type:
            hints.append({
                "type": "operation",
                "content": f"建议操作: {operation_type}",
                "icon": "hand_pointer",
                "priority": 1
            })
        
        # 实体状态提示
        status = target_entity.attributes.get("status")
        if status:
            hints.append({
                "type": "status",
                "content": f"当前状态: {status}",
                "icon": "info_circle",
                "priority": 2
            })
        
        # 安全警告
        if "critical" in target_entity.semantic_tags:
            hints.append({
                "type": "warning",
                "content": "警告: 关键设备，请谨慎操作",
                "icon": "exclamation_triangle",
                "priority": 0
            })
        
        # 上下文相关提示
        if context and context.get("urgency") == "high":
            hints.append({
                "type": "urgency",
                "content": "紧急任务，请尽快完成",
                "icon": "bolt",
                "priority": 0
            })
        
        # 按优先级排序
        hints.sort(key=lambda x: x["priority"])
        
        return hints
    
    def add_entity(self, entity: PhysicalEntity) -> None:
        """
        添加新实体到知识库
        
        Args:
            entity: 要添加的物理实体
        """
        self.knowledge_base[entity.entity_id] = entity
        self._rebuild_indices()
        logger.info("Added entity: %s", entity.entity_id)
    
    def remove_entity(self, entity_id: str) -> bool:
        """
        从知识库移除实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            是否成功移除
        """
        if entity_id in self.knowledge_base:
            del self.knowledge_base[entity_id]
            self._rebuild_indices()
            logger.info("Removed entity: %s", entity_id)
            return True
        return False
    
    def get_entities_in_range(
        self,
        center: SpatialPosition,
        radius: float
    ) -> List[PhysicalEntity]:
        """
        获取指定范围内的所有实体
        
        Args:
            center: 中心位置
            radius: 搜索半径（米）
            
        Returns:
            范围内的实体列表
        """
        entities = []
        for entity in self.knowledge_base.values():
            if entity.position.distance_to(center) <= radius:
                entities.append(entity)
        return entities


# 使用示例
if __name__ == "__main__":
    """
    使用示例：
    
    # 创建映射器实例
    mapper = CognitiveSpatialMapper()
    
    # 准备输入数据
    user_input = {
        "text_input": "那个红色的阀门",
        "operation": "把它关小点",
        "user_position": {"x": 5.0, "y": 5.0, "z": 0.0},
        "context": {"urgency": "medium", "environment": "factory_floor_a"}
    }
    
    # 生成AR可视化
    result = mapper.generate_ar_visualization(
        text_input=user_input["text_input"],
        operation_context=user_input["operation"],
        user_position=user_input["user_position"],
        context=user_input["context"]
    )
    
    # 输出结果
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    """
    
    # 创建映射器实例
    mapper = CognitiveSpatialMapper()
    
    try:
        # 示例1: 查找红色阀门
        print("=" * 60)
        print("示例1: 查找红色阀门并生成导航路径")
        print("=" * 60)
        
        result = mapper.generate_ar_visualization(
            text_input="那个红色的阀门",
            operation_context="把它关小点",
            user_position={"x": 5.0, "y": 5.0, "z": 0.0},
            context={"urgency": "medium"}
        )
        
        print(f"可视化ID: {result.visualization_id}")
        print(f"目标实体: {result.target_entity.entity_id}")
        print(f"路径长度: {result.path_length:.2f}米")
        print(f"预计时间: {result.estimated_duration:.1f}秒")
        print(f"路径点数量: {len(result.waypoints)}")
        
        print("\n导航路径:")
        for i, wp in enumerate(result.waypoints):
            print(f"  {i+1}. ({wp.position.x:.1f}, {wp.position.y:.1f}) - {wp.instruction}")
        
        print("\n操作提示:")
        for hint in result.operation_hints:
            print(f"  [{hint['type']}] {hint['content']}")
        
        # 示例2: 查找蓝色阀门
        print("\n" + "=" * 60)
        print("示例2: 查找蓝色阀门")
        print("=" * 60)
        
        result2 = mapper.generate_ar_visualization(
            text_input="蓝色的阀",
            operation_context="检查一下",
            user_position={"x": 10.0, "y": 10.0, "z": 0.0}
        )
        
        print(f"目标实体: {result2.target_entity.entity_id}")
        print(f"路径长度: {result2.path_length:.2f}米")
        
        # 示例3: 添加新实体并查找
        print("\n" + "=" * 60)
        print("示例3: 动态添加实体")
        print("=" * 60)
        
        new_valve = PhysicalEntity(
            entity_id="VALVE_GREEN_NEW",
            entity_type=EntityType.VALVE,
            position=SpatialPosition(x=8.0, y=12.0, z=1.2),
            attributes={"color": "green", "size": "small"},
            semantic_tags=["new", "emergency"]
        )
        
        mapper.add_entity(new_valve)
        
        result3 = mapper.generate_ar_visualization(
            text_input="绿色的新阀门",
            operation_context="打开",
            user_position={"x": 5.0, "y": 10.0, "z": 0.0}
        )
        
        print(f"新添加的实体: {result3.target_entity.entity_id}")
        print(f"位置: ({result3.target_entity.position.x}, {result3.target_entity.position.y})")
        
    except ValueError as e:
        logger.error("输入参数错误: %s", e)
    except RuntimeError as e:
        logger.error("运行时错误: %s", e)
    except Exception as e:
        logger.exception("未知错误: %s", e)
    
    print("\n" + "=" * 60)
    print("模块演示完成")
    print("=" * 60)