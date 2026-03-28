"""
工业级数据可视化与交互沙盒后端核心模块

该模块作为AGI系统的SKILL组件，负责解析CAD图纸数据，将其转换为Flutter前端
可渲染的高性能图层模型。核心功能包括：
1. 基于工程属性的图层分组（BIM分层逻辑）。
2. 图层过滤与状态管理（实现“剥洋葱”查看逻辑）。
3. 动态效果数据注入（生成前端Lottie/Canvas动画所需的矢量指令）。

输出数据格式: JSON (供Flutter解析)
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Union, Any, TypedDict
from enum import Enum
from dataclasses import dataclass, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialVisSandbox")

class LayerType(Enum):
    """定义工业图纸的图层类型枚举"""
    STRUCTURE_CONCRETE = "structure_concrete"
    STRUCTURE_STEEL = "structure_steel"
    PIPE_WATER = "pipe_water"
    PIPE_GAS = "pipe_gas"
    PIPE_HVAC = "pipe_hvac"
    ELECTRICAL = "electrical"
    ANNOTATION = "annotation"

class EffectType(Enum):
    """定义动态视觉效果类型"""
    FLOW_FORWARD = "flow_forward"
    FLOW_BACKWARD = "flow_backward"
    PULSE_HIGHLIGHT = "pulse_highlight"
    BLINK_ALERT = "blink_alert"

@dataclass
class GeometricBounds:
    """几何边界数据结构"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

@dataclass
class CADLayer:
    """CAD图层内部数据结构"""
    id: str
    name: str
    layer_type: LayerType
    visible: bool
    geometry_ref: str  # 指向具体几何数据的路径或ID
    attributes: Dict[str, Any]
    bounds: GeometricBounds

@dataclass
class DynamicEffect:
    """动态效果配置"""
    effect_id: str
    effect_type: EffectType
    speed: float  # 动画速度因子
    color_override: Optional[str] = None  #十六进制颜色码

class VisualizationSandbox:
    """
    工业级可视化沙盒主类。
    
    负责管理图层状态、处理过滤逻辑并生成前端渲染指令。
    """

    def __init__(self, project_id: str):
        """
        初始化沙盒。
        
        Args:
            project_id (str): 工程项目唯一标识符
        """
        self.project_id = project_id
        self._layers: Dict[str, CADLayer] = {}
        self._active_effects: Dict[str, DynamicEffect] = {}
        logger.info(f"Initialized Visualization Sandbox for project: {project_id}")

    def load_cad_data(self, raw_data: List[Dict[str, Any]]) -> bool:
        """
        核心函数1: 加载并解析CAD数据。
        
        将原始CAD字典数据转换为系统内部的图层对象。
        进行数据验证和边界检查。
        
        Args:
            raw_data (List[Dict]): 原始CAD数据列表。
            
        Returns:
            bool: 加载是否成功。
            
        Raises:
            ValueError: 如果数据格式不符合要求。
        """
        if not isinstance(raw_data, list):
            logger.error("Invalid CAD data format: Expected a list of layers.")
            raise ValueError("Input data must be a list of dictionaries.")

        count = 0
        for item in raw_data:
            try:
                # 数据验证
                if not all(k in item for k in ['name', 'type', 'bounds', 'geo_ref']):
                    logger.warning(f"Skipping invalid item missing keys: {item.get('name', 'Unknown')}")
                    continue
                
                # 解析边界并检查数值有效性
                b = item['bounds']
                bounds = GeometricBounds(
                    min_x=float(b['min_x']),
                    min_y=float(b['min_y']),
                    max_x=float(b['max_x']),
                    max_y=float(b['max_y'])
                )
                if bounds.min_x >= bounds.max_x or bounds.min_y >= bounds.max_y:
                    logger.warning(f"Invalid bounds for layer {item['name']}")
                    continue

                # 创建图层对象
                layer_id = f"lyr_{uuid.uuid4().hex[:8]}"
                layer = CADLayer(
                    id=layer_id,
                    name=item['name'],
                    layer_type=LayerType(item['type']),
                    visible=True,
                    geometry_ref=item['geo_ref'],
                    attributes=item.get('attrs', {}),
                    bounds=bounds
                )
                self._layers[layer_id] = layer
                count += 1
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error parsing layer item {item.get('name', 'Unknown')}: {e}")
                continue

        logger.info(f"Successfully loaded {count} layers.")
        return count > 0

    def apply_layer_filter(
        self, 
        target_types: Optional[List[LayerType]] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        核心函数2: 应用图层过滤器（剥洋葱逻辑）。
        
        根据类型或属性搜索更新图层可见性，并生成Flutter渲染所需的JSON结构。
        
        Args:
            target_types (Optional[List[LayerType]]): 需要保留显示的图层类型列表。
                                                     如果为None，则显示所有。
            search_query (Optional[str]): 模糊匹配图层名称的查询字符串。
        
        Returns:
            Dict[str, Any]: 包含图层树结构和更新指令的字典。
        """
        if not self._layers:
            logger.warning("Attempted to filter empty sandbox.")
            return {"status": "empty", "layers": []}

        update_payload = []
        visible_count = 0

        for layer_id, layer in self._layers.items():
            # 逻辑判断：类型匹配 或 名称搜索
            type_match = (target_types is None) or (layer.layer_type in target_types)
            name_match = (search_query is None) or (search_query.lower() in layer.name.lower())
            
            should_show = type_match and name_match
            
            # 更新内部状态
            if layer.visible != should_show:
                layer.visible = should_show
                logger.debug(f"Toggled layer {layer.name} visibility to {should_show}")

            if layer.visible:
                visible_count += 1
                # 构造前端渲染所需的数据片断
                update_payload.append({
                    "id": layer.id,
                    "name": layer.name,
                    "type": layer.layer_type.value,
                    "visible": layer.visible,
                    "geo_ref": layer.geometry_ref,
                    "effect": self._get_effect_config(layer.id) # 辅助函数调用
                })
        
        logger.info(f"Filter applied. Visible layers: {visible_count}/{len(self._layers)}")
        return {
            "project_id": self.project_id,
            "status": "success",
            "layer_count": visible_count,
            "layers": update_payload
        }

    def _get_effect_config(self, layer_id: str) -> Optional[Dict]:
        """
        辅助函数: 获取特定图层的动态效果配置。
        
        封装了从内部状态读取效果并转换为前端可识别格式的逻辑。
        
        Args:
            layer_id (str): 图层ID。
            
        Returns:
            Optional[Dict]: 效果配置字典，若无效果则返回None。
        """
        effect = self._active_effects.get(layer_id)
        if not effect:
            return None
        
        return {
            "type": effect.effect_type.value,
            "speed": effect.speed,
            "color": effect.color_override
        }

    def add_dynamic_effect(
        self, 
        layer_id: str, 
        effect_type: EffectType, 
        speed: float = 1.0,
        color: Optional[str] = None
    ) -> bool:
        """
        为特定图层添加动态效果（如水流动画）。
        
        Args:
            layer_id (str): 目标图层ID。
            effect_type (EffectType): 效果类型。
            speed (float): 动画速度 (0.1 - 5.0)。
            color (Optional[str]): 颜色覆盖 (Hex string)。
        
        Returns:
            bool: 操作是否成功。
        """
        if layer_id not in self._layers:
            logger.error(f"Layer {layer_id} not found for adding effect.")
            return False
        
        # 边界检查
        safe_speed = max(0.1, min(5.0, speed))
        
        effect_id = f"fx_{uuid.uuid4().hex[:6]}"
        new_effect = DynamicEffect(
            effect_id=effect_id,
            effect_type=effect_type,
            speed=safe_speed,
            color_override=color
        )
        
        self._active_effects[layer_id] = new_effect
        logger.info(f"Added effect {effect_type.value} to layer {layer_id}")
        return True

# 使用示例
if __name__ == "__main__":
    # 模拟从数据库或文件读取的CAD数据
    mock_cad_data = [
        {
            "name": "1F-Concrete-Walls",
            "type": "structure_concrete",
            "geo_ref": "/assets/geo/f1_walls.vec",
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 50},
            "attrs": {"phase": "A"}
        },
        {
            "name": "Water-Pipe-Main",
            "type": "pipe_water",
            "geo_ref": "/assets/geo/water_main.vec",
            "bounds": {"min_x": 10, "min_y": 10, "max_x": 90, "max_y": 40},
            "attrs": {"pressure": "High"}
        },
        {
            "name": "Gas-Line-Sec",
            "type": "pipe_gas",
            "geo_ref": "/assets/geo/gas_sec.vec",
            "bounds": {"min_x": 20, "min_y": 20, "max_x": 80, "max_y": 30},
            "attrs": {}
        }
    ]

    try:
        # 1. 初始化沙盒
        sandbox = VisualizationSandbox(project_id="PLANT_X_001")
        
        # 2. 加载数据
        if sandbox.load_cad_data(mock_cad_data):
            # 3. 模拟用户操作：隐藏混凝土结构，只看管道
            # 用户点击“隐藏结构”按钮
            visible_types = [LayerType.PIPE_WATER, LayerType.PIPE_GAS]
            result = sandbox.apply_layer_filter(target_types=visible_types)
            
            print("\n--- Flutter 渲染载荷 (仅管道) ---")
            print(json.dumps(result, indent=2))
            
            # 4. 模拟用户操作：高亮水管并添加流动效果
            # 获取水管ID (实际中由前端点击事件传回)
            water_layer_id = [lid for lid, l in sandbox._layers.items() if l.layer_type == LayerType.PIPE_WATER][0]
            
            sandbox.add_dynamic_effect(
                layer_id=water_layer_id,
                effect_type=EffectType.FLOW_FORWARD,
                speed=1.5,
                color="#00BFFF" # Deep Sky Blue
            )
            
            # 5. 再次生成状态，包含动画数据
            final_state = sandbox.apply_layer_filter(target_types=visible_types)
            
            print("\n--- Flutter 渲染载荷 (包含动画配置) ---")
            # 仅打印水管的配置以演示
            water_layer_data = next((item for item in final_state['layers'] if item['type'] == 'pipe_water'), None)
            print(json.dumps(water_layer_data, indent=2))

    except Exception as e:
        logger.critical(f"System crash: {e}")