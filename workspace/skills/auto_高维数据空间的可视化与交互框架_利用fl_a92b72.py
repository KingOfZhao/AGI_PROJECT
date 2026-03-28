"""
高维数据空间的可视化与交互框架

本模块构建了一个专门用于处理海量工程图纸（如建筑总平图、电路图）的矢量视图引擎。
利用模拟Flutter高性能光栅化的能力，实现GB级图纸的流畅缩放与CAD级对象识别。
支持轻量化BIM浏览，允许用户在移动端查看图纸并交互获取属性。

依赖:
    - numpy: 用于矩阵运算和几何变换
    - Pillow: 用于图像处理和验证
    - logging: 内置日志模块
"""

import logging
import json
import math
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from PIL import Image

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VectorViewEngine")


class CoordinateSystem(Enum):
    """坐标系枚举，定义不同的空间映射模式"""
    CARTESIAN = "cartesian"
    SCREEN = "screen"
    BIM_GLOBAL = "bim_global"


@dataclass
class Viewport:
    """
    视图窗口类，定义当前可视区域的状态
    对应Flutter中的Viewport概念，用于计算局部渲染范围
    """
    x: float
    y: float
    width: float
    height: float
    scale: float = 1.0
    
    def __post_init__(self):
        """数据验证：确保宽高和缩放比例为正数"""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Viewport dimensions must be positive")
        if self.scale <= 0:
            raise ValueError("Scale factor must be positive")
        logger.debug(f"Viewport initialized: {self}")

    def transform_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """将世界坐标转换为屏幕坐标"""
        screen_x = (world_x - self.x) * self.scale
        screen_y = (world_y - self.y) * self.scale
        return int(screen_x), int(screen_y)

    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        """获取当前视口在世界坐标系中的边界"""
        return (self.x, self.y, self.x + self.width / self.scale, self.y + self.height / self.scale)


@dataclass
class VectorObject:
    """
    矢量对象类，模拟CAD中的基本图元
    包含几何数据和BIM元数据
    """
    obj_id: str
    geometry_type: str  # e.g., 'line', 'circle', 'path'
    coordinates: List[Tuple[float, float]]  # 几何顶点
    layer: str
    properties: Dict[str, Any] = field(default_factory=dict)
    bounding_box: Tuple[float, float, float, float] = field(init=False)

    def __post_init__(self):
        """计算包围盒用于快速碰撞检测"""
        if not self.coordinates:
            raise ValueError("Coordinates cannot be empty")
        
        x_coords = [c[0] for c in self.coordinates]
        y_coords = [c[1] for c in self.coordinates]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # 添加微小容差防止零宽度对象
        tolerance = 1e-9
        self.bounding_box = (
            min_x - tolerance, 
            min_y - tolerance, 
            max_x + tolerance, 
            max_y + tolerance
        )

    def contains_point(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        """
        检查点是否击中该对象（基于包围盒简化检测）
        
        Args:
            x: 点击的世界坐标X
            y: 点击的世界坐标Y
            tolerance: 点击容差（像素单位，需根据scale转换）
        
        Returns:
            bool: 是否击中
        """
        min_x, min_y, max_x, max_y = self.bounding_box
        return (min_x <= x <= max_x) and (min_y <= y <= max_y)


class HighPerfRasterizationEngine:
    """
    模拟Flutter Engine的高性能光栅化能力。
    负责管理海量图纸数据的LOD（Level of Detail）和分块加载策略。
    """

    def __init__(self, max_memory_cache_mb: int = 512):
        self._cache_limit = max_memory_cache_mb * 1024 * 1024
        self._current_cache_size = 0
        self._tile_cache: Dict[str, np.ndarray] = {}
        logger.info(f"Rasterization Engine initialized with {max_memory_cache_mb}MB cache")

    def load_vector_tile(self, tile_key: str, data_stream: bytes) -> bool:
        """
        加载矢量分块数据并转换为光栅化格式
        
        Args:
            tile_key: 唯一的瓦片标识
            data_stream: 原始矢量数据流
        
        Returns:
            bool: 加载是否成功
        """
        try:
            # 模拟解析矢量数据并生成位图缓存
            # 这里使用numpy随机数组模拟光栅化后的数据
            mock_raster_data = np.frombuffer(data_stream, dtype=np.uint8)
            if mock_raster_data.nbytes > self._cache_limit:
                raise MemoryError("Single tile exceeds cache limit")

            if self._current_cache_size + mock_raster_data.nbytes > self._cache_limit:
                self._evict_cache()

            self._tile_cache[tile_key] = mock_raster_data
            self._current_cache_size += mock_raster_data.nbytes
            logger.debug(f"Tile {tile_key} loaded. Cache usage: {self._current_cache_size} bytes")
            return True

        except Exception as e:
            logger.error(f"Failed to load tile {tile_key}: {str(e)}")
            return False

    def _evict_cache(self):
        """LRU缓存淘汰策略"""
        # 简单的模拟：清空一半缓存
        keys_to_remove = list(self._tile_cache.keys())[:len(self._tile_cache)//2]
        for key in keys_to_remove:
            self._current_cache_size -= self._tile_cache[key].nbytes
            del self._tile_cache[key]
        logger.info(f"Cache evicted. New size: {self._current_cache_size}")


class BIMDataSpaceFramework:
    """
    高维数据空间的可视化与交互框架主类。
    整合矢量视图引擎、对象识别和交互逻辑。
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.rasterizer = HighPerfRasterizationEngine()
        self.vector_objects: Dict[str, VectorObject] = {}
        self.current_viewport: Optional[Viewport] = None
        self._spatial_index: List[str] = []  # 简化的空间索引列表
        
        logger.info(f"BIM Framework initialized for project: {project_id}")

    def load_drawing_data(self, raw_data: Dict[str, Any]) -> int:
        """
        加载并解析图纸数据（模拟GB级数据的元数据加载）
        
        Args:
            raw_data: 包含 'objects' 列表的字典数据
        
        Returns:
            int: 成功加载的对象数量
        
        Raises:
            ValueError: 数据格式无效时抛出
        """
        if not isinstance(raw_data, dict) or 'objects' not in raw_data:
            raise ValueError("Invalid data format: 'objects' key missing")

        count = 0
        objects_data = raw_data.get('objects', [])
        
        for item in objects_data:
            try:
                # 数据验证
                if not all(k in item for k in ['id', 'type', 'coords']):
                    logger.warning(f"Skipping invalid object: {item}")
                    continue
                
                vec_obj = VectorObject(
                    obj_id=item['id'],
                    geometry_type=item['type'],
                    coordinates=[(c[0], c[1]) for c in item['coords']], # 类型转换确保
                    layer=item.get('layer', 'default'),
                    properties=item.get('props', {})
                )
                
                self.vector_objects[vec_obj.obj_id] = vec_obj
                self._spatial_index.append(vec_obj.obj_id)
                count += 1
                
            except Exception as e:
                logger.error(f"Error parsing object {item.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Loaded {count} vector objects. Total: {len(self.vector_objects)}")
        return count

    def update_viewport(self, x: float, y: float, width: float, height: float, scale: float) -> None:
        """
        更新当前视口状态，触发潜在的渲染更新
        
        Args:
            x, y: 视口左上角在世界坐标系的位置
            width, height: 视口的像素宽高
            scale: 缩放比例 (1.0 = 100%)
        """
        try:
            self.current_viewport = Viewport(x, y, width, height, scale)
            # 在真实场景中，这里会触发Flutter的重绘流程
            # self.rasterizer.load_vector_tile(...)
            logger.info(f"Viewport updated: Center=({x+width/2:.2f}, {y+height/2:.2f}), Zoom={scale:.2f}x")
        except ValueError as e:
            logger.error(f"Viewport update failed: {e}")

    def query_object_at_point(self, screen_x: int, screen_y: int) -> Optional[Dict[str, Any]]:
        """
        核心交互函数：查询屏幕坐标位置的矢量对象及其BIM属性。
        模拟CAD中的"点选"功能。
        
        Args:
            screen_x: 屏幕像素X坐标
            screen_y: 屏幕像素Y坐标
            
        Returns:
            包含对象ID和属性的字典，如果未击中则返回None
        """
        if not self.current_viewport:
            logger.warning("Query attempted without active viewport")
            return None

        # 1. 屏幕坐标转世界坐标 (逆变换)
        world_x = self.current_viewport.x + screen_x / self.current_viewport.scale
        world_y = self.current_viewport.y + screen_y / self.current_viewport.scale
        
        logger.debug(f"Query point Screen({screen_x}, {screen_y}) -> World({world_x:.2f}, {world_y:.2f})")

        # 2. 空间搜索 (此处简化为遍历，生产环境应使用R-Tree或QuadTree)
        # 设定一个基于缩放级别的拾取半径
        pick_radius_world = 10.0 / self.current_viewport.scale

        for obj_id in self._spatial_index:
            obj = self.vector_objects[obj_id]
            # 简单的包围盒碰撞检测
            # 生产级代码会在此处进行更精细的线段距离检测
            min_x, min_y, max_x, max_y = obj.bounding_box
            
            if (min_x - pick_radius_world <= world_x <= max_x + pick_radius_world and
                min_y - pick_radius_world <= world_y <= max_y + pick_radius_world):
                
                # 命中对象
                logger.info(f"Object hit: {obj_id}")
                return {
                    "id": obj.obj_id,
                    "type": obj.geometry_type,
                    "layer": obj.layer,
                    "properties": obj.properties,
                    "geometry_summary": f"Vertices: {len(obj.coordinates)}"
                }

        logger.debug("No object hit at specified coordinates")
        return None

    def export_viewport_image(self, output_path: str) -> bool:
        """
        辅助函数：将当前视口内容导出为图像
        模拟Flutter的toImage功能
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        if not self.current_viewport:
            logger.error("Cannot export: No active viewport")
            return False

        try:
            # 模拟生成图像数据
            w = int(self.current_viewport.width)
            h = int(self.current_viewport.height)
            
            # 创建一个简单的渐变图模拟渲染结果
            # 在真实应用中，这里是从底层渲染引擎获取的像素数据
            img_array = np.zeros((h, w, 3), dtype=np.uint8)
            
            # 添加一些模拟的线条
            for obj in self.vector_objects.values():
                # 极其简化的光栅化：只画包围盒
                x1, y1 = self.current_viewport.transform_to_screen(*obj.bounding_box[:2])
                x2, y2 = self.current_viewport.transform_to_screen(*obj.bounding_box[2:])
                
                # 确保在图像范围内 (简单的裁剪)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x1 < x2 and y1 < y2:
                    # 简单填充颜色区分图层
                    color = [255, 255, 255] # Default White
                    if "wall" in obj.layer: color = [100, 100, 100]
                    if "door" in obj.layer: color = [200, 0, 0]
                    
                    img_array[y1:y2, x1:x2] = color

            img = Image.fromarray(img_array, 'RGB')
            img.save(output_path)
            logger.info(f"Viewport exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False


# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 初始化框架
    framework = BIMDataSpaceFramework(project_id="PROJ_001")
    
    # 2. 模拟输入数据 (通常是解析DXF/DWG得到的JSON)
    mock_drawing_data = {
        "objects": [
            {
                "id": "wall_01", 
                "type": "polyline", 
                "coords": [(0, 0), (0, 100), (200, 100), (200, 0)],
                "layer": "architecture_wall",
                "props": {"material": "Concrete", "height": 3.0, "fire_rating": "2h"}
            },
            {
                "id": "door_01", 
                "type": "line", 
                "coords": [(50, 0), (80, 0)],
                "layer": "architecture_door",
                "props": {"material": "Wood", "width": 0.9, "type": "Single Swing"}
            },
            {
                "id": "cable_99", 
                "type": "line", 
                "coords": [(10, 10), (50, 50)],
                "layer": "electrical",
                "props": {"voltage": "220V", "wire_type": "Copper"}
            }
        ]
    }
    
    # 3. 加载数据
    loaded_count = framework.load_drawing_data(mock_drawing_data)
    print(f"成功加载 {loaded_count} 个对象")
    
    # 4. 设置视口 (模拟用户在移动端查看)
    # 观察原点附近，缩放0.5倍
    framework.update_viewport(x=-50, y=-50, width=800, height=600, scale=0.5)
    
    # 5. 模拟用户点击交互 (点击屏幕坐标 100, 100)
    # 坐标转换计算: WorldX = -50 + 100/0.5 = 150, WorldY = -50 + 100/0.5 = 150
    # Wall bounding box is (0,0) to (200,100), so (150, 150) is actually above the wall in this data
    # Let's click at screen (200, 300) -> World (350, 550) -> Out of bounds
    # Let's click at screen (100, 120) -> World (150, 190) -> Should hit nothing (Wall is at y<=100)
    
    # Try hitting the wall at screen (50, 50) -> World (-50+100, -50+100) = (50, 50)
    hit_result = framework.query_object_at_point(screen_x=50, screen_y=50)
    
    if hit_result:
        print(f"\n>>> 捕获到对象: {hit_result['id']}")
        print(f"    类型: {hit_result['type']}")
        print(f"    属性: {json.dumps(hit_result['properties'], indent=4)}")
    else:
        print("\n>>> 未捕获到任何对象")

    # 6. 导出当前视图
    framework.export_viewport_image("demo_viewport_export.png")