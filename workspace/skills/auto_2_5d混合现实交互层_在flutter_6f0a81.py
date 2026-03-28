"""
模块名称: auto_2_5d混合现实交互层_在flutter_6f0a81
描述: 2.5D混合现实交互层。在Flutter中嵌入轻量级3D视图，利用CAD的射线拾取算法优化复杂堆叠UI。
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Vector3:
    """三维向量类"""
    x: float
    y: float
    z: float

    def __post_init__(self):
        """数据验证"""
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.z]):
            raise ValueError("Vector3坐标必须是数字类型")

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def dot(self, other: 'Vector3') -> float:
        """向量点积"""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3') -> 'Vector3':
        """向量叉积"""
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        """向量长度"""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vector3':
        """单位化向量"""
        l = self.length()
        if l == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / l, self.y / l, self.z / l)

@dataclass
class Ray:
    """射线类"""
    origin: Vector3
    direction: Vector3

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.origin, Vector3) or not isinstance(self.direction, Vector3):
            raise TypeError("Ray的origin和direction必须是Vector3类型")
        # 确保方向向量是单位向量
        self.direction = self.direction.normalize()

@dataclass
class UIElement:
    """2.5D UI元素"""
    id: str
    position: Vector3
    width: float
    height: float
    depth_weight: float = 1.0  # 深度权重，用于智能选中
    opacity: float = 1.0  # 透明度 [0.0, 1.0]
    is_interactive: bool = True
    normal: Vector3 = field(default_factory=lambda: Vector3(0, 0, 1))  # 默认法线朝向观察者

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.id, str):
            raise TypeError("UIElement的id必须是字符串")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError("opacity必须在0.0到1.0之间")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("宽度和高度必须大于0")

class MixedRealityInteractionEngine:
    """
    2.5D混合现实交互引擎
    
    核心功能：
    1. 基于射线投射的3D空间点击检测
    2. 考虑视觉遮挡和深度权重的智能选中
    3. 事件分发优化
    
    使用示例:
    >>> engine = MixedRealityInteractionEngine()
    >>> camera_pos = Vector3(0, 0, 10)
    >>> screen_pos = Vector3(100, 200, 0)  # 屏幕坐标
    
    # 创建UI元素
    >>> button1 = UIElement("btn1", Vector3(95, 195, 2), 10, 10)
    >>> button2 = UIElement("btn2", Vector3(100, 200, 5), 10, 10, opacity=0.5)
    >>> engine.register_ui_element(button1)
    >>> engine.register_ui_element(button2)
    
    # 处理点击
    >>> hit_element = engine.process_interaction(camera_pos, screen_pos)
    >>> if hit_element:
    ...     print(f"命中元素: {hit_element.id}")
    """

    def __init__(self, max_interaction_distance: float = 1000.0):
        """
        初始化交互引擎
        
        参数:
            max_interaction_distance: 最大交互距离，超过此距离的元素将被忽略
        """
        self.ui_elements: List[UIElement] = []
        self.max_distance = max_interaction_distance
        self._spatial_index = {}  # 简单的空间索引，实际应用中可使用更高效的算法
        
        logger.info("MixedRealityInteractionEngine 初始化完成")

    def register_ui_element(self, element: UIElement) -> None:
        """
        注册UI元素
        
        参数:
            element: 要注册的UI元素
            
        异常:
            TypeError: 如果element不是UIElement类型
        """
        if not isinstance(element, UIElement):
            raise TypeError("必须注册UIElement类型的对象")
            
        self.ui_elements.append(element)
        logger.debug(f"注册UI元素: {element.id}")

    def _calculate_ray_from_screen(
        self, 
        camera_pos: Vector3, 
        screen_pos: Vector3,
        viewport_width: float = 1920.0,
        viewport_height: float = 1080.0
    ) -> Ray:
        """
        从屏幕坐标计算3D射线（辅助函数）
        
        参数:
            camera_pos: 相机位置
            screen_pos: 屏幕坐标 (z分量通常忽略)
            viewport_width: 视口宽度
            viewport_height: 视口高度
            
        返回:
            Ray: 计算出的射线
            
        注意:
            这里简化了投影计算，实际应用中可能需要考虑相机的投影矩阵
        """
        try:
            # 将屏幕坐标归一化到[-1, 1]范围
            ndc_x = (2.0 * screen_pos.x) / viewport_width - 1.0
            ndc_y = 1.0 - (2.0 * screen_pos.y) / viewport_height
            
            # 简化计算：假设相机朝向-Z方向
            direction = Vector3(ndc_x, ndc_y, -1.0).normalize()
            return Ray(camera_pos, direction)
            
        except Exception as e:
            logger.error(f"计算射线失败: {str(e)}")
            raise

    def _ray_plane_intersection(
        self, 
        ray: Ray, 
        plane_point: Vector3, 
        plane_normal: Vector3
    ) -> Optional[Tuple[Vector3, float]]:
        """
        计算射线与平面的交点（辅助函数）
        
        参数:
            ray: 射线
            plane_point: 平面上的点
            plane_normal: 平面法线
            
        返回:
            Optional[Tuple[Vector3, float]]: 交点和距离，如果没有交点则返回None
        """
        try:
            denom = plane_normal.dot(ray.direction)
            
            # 射线与平面平行
            if abs(denom) < 1e-6:
                return None
                
            t = (plane_point - ray.origin).dot(plane_normal) / denom
            
            # 交点在射线背后
            if t < 0:
                return None
                
            intersection = Vector3(
                ray.origin.x + ray.direction.x * t,
                ray.origin.y + ray.direction.y * t,
                ray.origin.z + ray.direction.z * t
            )
            
            return (intersection, t)
            
        except Exception as e:
            logger.error(f"计算射线平面交点失败: {str(e)}")
            return None

    def _is_point_in_element(self, point: Vector3, element: UIElement) -> bool:
        """
        判断点是否在UI元素范围内（辅助函数）
        
        参数:
            point: 要判断的点
            element: UI元素
            
        返回:
            bool: 是否在范围内
        """
        try:
            # 简化计算：假设UI元素是轴对齐的矩形
            half_width = element.width / 2
            half_height = element.height / 2
            
            return (
                element.position.x - half_width <= point.x <= element.position.x + half_width and
                element.position.y - half_height <= point.y <= element.position.y + half_height
            )
        except Exception as e:
            logger.error(f"判断点是否在元素内失败: {str(e)}")
            return False

    def process_interaction(
        self, 
        camera_pos: Vector3, 
        screen_pos: Vector3,
        viewport_width: float = 1920.0,
        viewport_height: float = 1080.0
    ) -> Optional[UIElement]:
        """
        处理用户交互
        
        参数:
            camera_pos: 相机位置
            screen_pos: 屏幕坐标
            viewport_width: 视口宽度
            viewport_height: 视口高度
            
        返回:
            Optional[UIElement]: 被选中的UI元素，如果没有则返回None
            
        异常:
            ValueError: 如果输入参数无效
        """
        try:
            # 验证输入
            if not isinstance(camera_pos, Vector3) or not isinstance(screen_pos, Vector3):
                raise ValueError("camera_pos和screen_pos必须是Vector3类型")
                
            if viewport_width <= 0 or viewport_height <= 0:
                raise ValueError("视口宽度和高度必须大于0")
                
            # 计算射线
            ray = self._calculate_ray_from_screen(
                camera_pos, screen_pos, viewport_width, viewport_height
            )
            
            # 收集所有可能命中的元素
            potential_hits = []
            
            for element in self.ui_elements:
                if not element.is_interactive:
                    continue
                    
                # 计算射线与元素平面的交点
                result = self._ray_plane_intersection(
                    ray, element.position, element.normal
                )
                
                if result is None:
                    continue
                    
                intersection, distance = result
                
                # 检查距离限制
                if distance > self.max_distance:
                    continue
                    
                # 检查点是否在元素范围内
                if not self._is_point_in_element(intersection, element):
                    continue
                    
                potential_hits.append((element, distance))
            
            # 如果没有命中任何元素
            if not potential_hits:
                logger.debug("没有命中任何UI元素")
                return None
                
            # 智能选择：基于视觉遮挡和深度权重
            # 这里简化处理：优先选择深度权重高的，距离近的
            potential_hits.sort(
                key=lambda x: (x[0].depth_weight, -x[1], -x[0].opacity),
                reverse=True
            )
            
            selected_element = potential_hits[0][0]
            logger.info(f"选中UI元素: {selected_element.id}")
            return selected_element
            
        except Exception as e:
            logger.error(f"处理交互失败: {str(e)}")
            return None

    def clear_elements(self) -> None:
        """清除所有注册的UI元素"""
        self.ui_elements.clear()
        logger.info("已清除所有UI元素")

# 示例用法（在实际运行时会被忽略）
if __name__ == "__main__":
    # 创建交互引擎
    engine = MixedRealityInteractionEngine()
    
    # 设置相机位置
    camera = Vector3(0, 0, 10)
    
    # 创建一些UI元素
    button1 = UIElement(
        "button1",
        Vector3(100, 100, 5),
        50, 30,
        depth_weight=1.0,
        opacity=0.8
    )
    
    button2 = UIElement(
        "button2",
        Vector3(105, 105, 3),  # 在button1后面
        50, 30,
        depth_weight=1.2,  # 更高的深度权重
        opacity=0.5
    )
    
    # 注册UI元素
    engine.register_ui_element(button1)
    engine.register_ui_element(button2)
    
    # 模拟点击
    screen_point = Vector3(110, 110, 0)
    hit = engine.process_interaction(camera, screen_point)
    
    if hit:
        print(f"命中元素: {hit.id}")
    else:
        print("没有命中任何元素")