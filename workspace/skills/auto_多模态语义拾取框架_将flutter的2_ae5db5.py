"""
多模态语义拾取框架 - Flutter 2D命中测试到3D空间查询的扩展
将Flutter的2D命中测试扩展为3D空间查询接口，结合语义信息实现UI控件与3D实体同源事件处理
"""

import logging
from typing import Tuple, Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticPicker")


class HitTestResult(Enum):
    """命中测试结果类型"""
    UI_HIT = 1
    SPATIAL_HIT = 2
    COMBINED_HIT = 3
    MISS = 4


@dataclass
class FlutterEvent:
    """Flutter事件数据结构"""
    x: float
    y: float
    timestamp: float
    device_type: str
    pressure: float = 1.0
    metadata: Dict[str, Any] = None


@dataclass
class SemanticEntity:
    """语义实体数据结构"""
    entity_id: str
    entity_type: str
    position: Tuple[float, float, float]
    bbox: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    properties: Dict[str, Any]
    semantic_tags: List[str]


class SemanticPickerFramework:
    """
    多模态语义拾取框架核心类
    实现Flutter 2D事件到3D空间语义查询的转换
    """
    
    def __init__(self, camera_matrix: np.ndarray, projection_matrix: np.ndarray):
        """
        初始化语义拾取框架
        
        Args:
            camera_matrix: 3x3相机内参矩阵
            projection_matrix: 4x4投影矩阵
        """
        self._validate_matrices(camera_matrix, projection_matrix)
        self.camera_matrix = camera_matrix
        self.projection_matrix = projection_matrix
        self.semantic_database = {}
        self.ui_hierarchy = {}
        self.spatial_index = None
        
        logger.info("SemanticPickerFramework initialized with camera and projection matrices")
    
    def _validate_matrices(self, camera_matrix: np.ndarray, projection_matrix: np.ndarray) -> None:
        """验证矩阵格式"""
        if camera_matrix.shape != (3, 3):
            raise ValueError("Camera matrix must be 3x3")
        if projection_matrix.shape != (4, 4):
            raise ValueError("Projection matrix must be 4x4")
    
    def register_semantic_entity(self, entity: SemanticEntity) -> bool:
        """
        注册语义实体到空间数据库
        
        Args:
            entity: 要注册的语义实体
            
        Returns:
            bool: 注册是否成功
        """
        try:
            if not self._validate_entity(entity):
                logger.warning(f"Invalid entity data for {entity.entity_id}")
                return False
                
            self.semantic_database[entity.entity_id] = entity
            self._update_spatial_index(entity)
            logger.debug(f"Registered semantic entity: {entity.entity_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register entity {entity.entity_id}: {str(e)}")
            return False
    
    def _validate_entity(self, entity: SemanticEntity) -> bool:
        """验证实体数据有效性"""
        if not entity.entity_id or not isinstance(entity.entity_id, str):
            return False
            
        if len(entity.position) != 3 or len(entity.bbox) != 2:
            return False
            
        for point in entity.bbox:
            if len(point) != 3:
                return False
                
        return True
    
    def _update_spatial_index(self, entity: SemanticEntity) -> None:
        """更新空间索引结构"""
        # 简化的空间索引实现，实际应用中可使用R树等结构
        if not hasattr(self, '_spatial_hash'):
            self._spatial_hash = {}
            
        # 使用简单的网格哈希
        cell_size = 0.5  # 50cm网格
        min_x = int(entity.bbox[0][0] / cell_size)
        min_y = int(entity.bbox[0][1] / cell_size)
        min_z = int(entity.bbox[0][2] / cell_size)
        
        max_x = int(entity.bbox[1][0] / cell_size)
        max_y = int(entity.bbox[1][1] / cell_size)
        max_z = int(entity.bbox[1][2] / cell_size)
        
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    key = (x, y, z)
                    if key not in self._spatial_hash:
                        self._spatial_hash[key] = set()
                    self._spatial_hash[key].add(entity.entity_id)
    
    def flutter_event_to_ray(self, event: FlutterEvent) -> Tuple[np.ndarray, np.ndarray]:
        """
        将Flutter屏幕坐标转换为3D空间射线
        
        Args:
            event: Flutter输入事件
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: 射线原点和方向向量
        """
        # 将屏幕坐标转换为归一化设备坐标
        screen_x = (2.0 * event.x) - 1.0
        screen_y = 1.0 - (2.0 * event.y)  # 反转Y轴
        
        # 构建射线方向向量 (简化版，实际需要逆投影矩阵计算)
        ray_nds = np.array([screen_x, screen_y, -1.0, 1.0])
        ray_eye = np.linalg.inv(self.projection_matrix) @ ray_nds
        ray_eye = ray_eye / ray_eye[3]
        
        # 假设相机在原点，方向向量
        direction = ray_eye[:3]
        direction = direction / np.linalg.norm(direction)
        
        # 射线原点 (相机位置)
        origin = np.array([0.0, 0.0, 0.0])
        
        logger.debug(f"Generated ray from screen ({event.x}, {event.y}): origin={origin}, dir={direction}")
        return origin, direction
    
    def perform_semantic_pick(self, event: FlutterEvent, max_distance: float = 100.0) -> Dict[str, Any]:
        """
        执行多模态语义拾取操作
        
        Args:
            event: Flutter输入事件
            max_distance: 最大射线检测距离
            
        Returns:
            Dict[str, Any]: 包含命中结果的字典:
                - "ui_hit": UI层级命中结果
                - "spatial_hits": 3D空间命中结果
                - "combined_result": 合并后的语义结果
                - "hit_type": HitTestResult枚举值
        """
        result = {
            "ui_hit": None,
            "spatial_hits": [],
            "combined_result": None,
            "hit_type": HitTestResult.MISS,
            "metadata": {
                "event_time": event.timestamp,
                "device": event.device_type
            }
        }
        
        try:
            # 1. 首先执行Flutter UI命中测试
            ui_hit = self._flutter_ui_hit_test(event)
            result["ui_hit"] = ui_hit
            
            # 2. 执行3D空间射线检测
            ray_origin, ray_dir = self.flutter_event_to_ray(event)
            spatial_hits = self._perform_ray_cast(ray_origin, ray_dir, max_distance)
            result["spatial_hits"] = spatial_hits
            
            # 3. 合并UI和空间命中结果
            if ui_hit or spatial_hits:
                result["combined_result"] = self._combine_semantic_results(ui_hit, spatial_hits)
                
                # 确定命中类型
                if ui_hit and spatial_hits:
                    result["hit_type"] = HitTestResult.COMBINED_HIT
                elif ui_hit:
                    result["hit_type"] = HitTestResult.UI_HIT
                else:
                    result["hit_type"] = HitTestResult.SPATIAL_HIT
                    
            logger.info(f"Semantic pick completed: {result['hit_type']}")
            
        except Exception as e:
            logger.error(f"Semantic pick failed: {str(e)}", exc_info=True)
            result["error"] = str(e)
            
        return result
    
    def _flutter_ui_hit_test(self, event: FlutterEvent) -> Optional[Dict[str, Any]]:
        """
        执行Flutter UI层级命中测试 (模拟)
        
        Args:
            event: Flutter输入事件
            
        Returns:
            Optional[Dict]: UI命中结果或None
        """
        # 在实际实现中，这里会与Flutter框架集成
        # 这里模拟一个简单的UI命中测试
        
        # 假设我们有一个简单的UI层级结构
        if not hasattr(self, '_ui_elements'):
            self._ui_elements = [
                {"id": "button1", "rect": (0.4, 0.4, 0.6, 0.6), "type": "button", "action": "toggle_lamp"},
                {"id": "slider1", "rect": (0.2, 0.7, 0.8, 0.8), "type": "slider", "target": "light_intensity"}
            ]
        
        for element in self._ui_elements:
            x1, y1, x2, y2 = element["rect"]
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                logger.debug(f"UI hit detected: {element['id']}")
                return {
                    "element_id": element["id"],
                    "element_type": element["type"],
                    "action": element.get("action"),
                    "target": element.get("target"),
                    "rect": element["rect"]
                }
                
        return None
    
    def _perform_ray_cast(self, origin: np.ndarray, direction: np.ndarray, max_distance: float) -> List[Dict]:
        """
        执行3D空间射线检测
        
        Args:
            origin: 射线原点
            direction: 射线方向
            max_distance: 最大检测距离
            
        Returns:
            List[Dict]: 命中实体列表
        """
        hits = []
        
        # 使用空间索引优化检测
        if hasattr(self, '_spatial_hash'):
            # 计算射线经过的网格单元
            cell_size = 0.5
            potential_entities = set()
            
            # 简化版: 检查射线方向上的几个网格单元
            for t in np.linspace(0, max_distance, 10):
                check_point = origin + direction * t
                cell_x = int(check_point[0] / cell_size)
                cell_y = int(check_point[1] / cell_size)
                cell_z = int(check_point[2] / cell_size)
                
                if (cell_x, cell_y, cell_z) in self._spatial_hash:
                    potential_entities.update(self._spatial_hash[(cell_x, cell_y, cell_z)])
        
        # 对潜在实体进行精确射线-包围盒检测
        for entity_id in potential_entities:
            entity = self.semantic_database.get(entity_id)
            if entity:
                hit_distance = self._ray_bbox_intersect(origin, direction, entity.bbox)
                if hit_distance is not None and hit_distance <= max_distance:
                    hits.append({
                        "entity_id": entity.entity_id,
                        "entity_type": entity.entity_type,
                        "distance": hit_distance,
                        "position": tuple(origin + direction * hit_distance),
                        "properties": entity.properties,
                        "semantic_tags": entity.semantic_tags
                    })
        
        # 按距离排序
        hits.sort(key=lambda x: x["distance"])
        return hits
    
    def _ray_bbox_intersect(self, origin: np.ndarray, direction: np.ndarray, bbox: Tuple) -> Optional[float]:
        """
        射线与包围盒相交检测
        
        Args:
            origin: 射线原点
            direction: 射线方向
            bbox: 包围盒 (min_point, max_point)
            
        Returns:
            Optional[float]: 交点距离或None
        """
        min_point = np.array(bbox[0])
        max_point = np.array(bbox[1])
        
        t_min = -np.inf
        t_max = np.inf
        
        for i in range(3):
            if direction[i] != 0:
                t1 = (min_point[i] - origin[i]) / direction[i]
                t2 = (max_point[i] - origin[i]) / direction[i]
                
                if t1 > t2:
                    t1, t2 = t2, t1
                    
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                
                if t_min > t_max:
                    return None
            else:
                if origin[i] < min_point[i] or origin[i] > max_point[i]:
                    return None
        
        return t_min if t_min > 0 else None
    
    def _combine_semantic_results(self, ui_hit: Optional[Dict], spatial_hits: List[Dict]) -> Dict[str, Any]:
        """
        合并UI和空间命中结果
        
        Args:
            ui_hit: UI命中结果
            spatial_hits: 空间命中结果
            
        Returns:
            Dict: 合并后的语义结果
        """
        combined = {
            "ui_element": ui_hit,
            "spatial_entities": spatial_hits,
            "context": {}
        }
        
        # 如果同时命中UI和空间实体，建立语义关联
        if ui_hit and spatial_hits:
            # 查找语义关联
            for spatial in spatial_hits:
                if "target" in ui_hit and ui_hit["target"] in spatial.get("semantic_tags", []):
                    combined["context"]["linked"] = True
                    combined["context"]["linked_entity"] = spatial["entity_id"]
                    combined["context"]["action"] = ui_hit.get("action")
                    break
        
        return combined


# 使用示例
if __name__ == "__main__":
    # 初始化相机和投影矩阵
    camera_matrix = np.array([
        [800, 0, 320],
        [0, 800, 240],
        [0, 0, 1]
    ], dtype=np.float32)
    
    projection_matrix = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, -1.002002, -0.2002002],
        [0.0, 0.0, -1.0, 0.0]
    ], dtype=np.float32)
    
    # 创建语义拾取框架
    picker = SemanticPickerFramework(camera_matrix, projection_matrix)
    
    # 注册一些3D实体
    bolt_entity = SemanticEntity(
        entity_id="bolt_001",
        entity_type="fastener",
        position=(1.2, 0.5, -3.0),
        bbox=((1.1, 0.4, -3.1), (1.3, 0.6, -2.9)),
        properties={"spec": "M8x1.25", "torque": "45Nm", "material": "steel"},
        semantic_tags=["fastener", "repair_target", "bolt"]
    )
    picker.register_semantic_entity(bolt_entity)
    
    # 模拟Flutter事件
    flutter_event = FlutterEvent(
        x=0.5,  # 屏幕X坐标 (0-1)
        y=0.5,  # 屏幕Y坐标 (0-1)
        timestamp=1625097600.0,
        device_type="touch",
        pressure=0.8,
        metadata={"session_id": "repair_123"}
    )
    
    # 执行语义拾取
    result = picker.perform_semantic_pick(flutter_event)
    
    # 输出结果
    print("\nSemantic Pick Result:")
    print(f"Hit Type: {result['hit_type']}")
    print(f"UI Hit: {result['ui_hit']}")
    print(f"Spatial Hits: {len(result['spatial_hits'])} entities")
    
    if result['combined_result']:
        print("\nCombined Semantic Context:")
        print(f"Linked: {result['combined_result']['context'].get('linked', False)}")
        if 'linked_entity' in result['combined_result']['context']:
            print(f"Linked Entity: {result['combined_result']['context']['linked_entity']}")
            
        if result['spatial_hits']:
            hit = result['spatial_hits'][0]
            print(f"\nHit Entity Details:")
            print(f"ID: {hit['entity_id']}")
            print(f"Type: {hit['entity_type']}")
            print(f"Distance: {hit['distance']:.2f}m")
            print(f"Properties: {hit['properties']}")