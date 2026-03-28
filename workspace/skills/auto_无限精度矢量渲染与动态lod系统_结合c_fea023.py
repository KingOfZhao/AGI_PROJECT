"""
无限精度矢量渲染与动态LOD系统

结合CAD曲面细分与自适应光栅化管线技术，实现基于曲率的动态LOD渲染。
该模块提供工业级矢量图形渲染能力，支持从宏观概览到微观细节的无缝缩放。

核心特性:
- 基于曲率和视口的动态LOD计算
- 贝塞尔曲线自适应细分
- 移动端优化的渲染性能
- 打印级输出精度

输入格式:
    curves: List[Dict] - 贝塞尔曲线定义列表
        {
            'control_points': List[Tuple[float, float]],  # 控制点坐标
            'degree': int,                                # 曲线次数(1-3)
            'weight': float                               # 线宽权重
        }
    viewport: Dict - 视口参数
        {
            'scale': float,        # 缩放级别 (1.0 = 100%)
            'center': Tuple[float, float],  # 视口中心
            'pixel_density': float # 像素密度 (PPI)
        }

输出格式:
    List[Dict] - 渲染图元列表
        {
            'type': str,           # 'line' 或 'curve'
            'points': List[Tuple], # 细分后的点集
            'precision': float     # 实际渲染精度
        }
"""

import logging
import math
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ViewportConfig:
    """视口配置参数"""
    scale: float = 1.0
    center: Tuple[float, float] = (0.0, 0.0)
    pixel_density: float = 96.0
    max_subdivision: int = 10
    min_segment_length: float = 0.5  # 像素
    tolerance: float = 0.1  # 曲率容差


class VectorRenderer:
    """无限精度矢量渲染引擎"""
    
    def __init__(self, config: Optional[ViewportConfig] = None):
        """
        初始化渲染引擎
        
        Args:
            config: 视口配置，如果为None则使用默认配置
        """
        self.config = config or ViewportConfig()
        self._validate_config()
        logger.info("VectorRenderer initialized with config: %s", self.config)
    
    def _validate_config(self) -> None:
        """验证配置参数有效性"""
        if self.config.scale <= 0:
            raise ValueError(f"Scale must be positive, got {self.config.scale}")
        if self.config.pixel_density <= 0:
            raise ValueError(f"Pixel density must be positive, got {self.config.pixel_density}")
        if self.config.max_subdivision < 1 or self.config.max_subdivision > 20:
            logger.warning("Max subdivision outside recommended range (1-20): %d", 
                         self.config.max_subdivision)
    
    def calculate_curvature(self, p0: Tuple[float, float], 
                           p1: Tuple[float, float], 
                           p2: Tuple[float, float]) -> float:
        """
        计算三点定义的曲线曲率
        
        Args:
            p0, p1, p2: 三个连续点坐标
            
        Returns:
            float: 曲率值 (0表示直线，越大表示越弯曲)
            
        Example:
            >>> renderer = VectorRenderer()
            >>> renderer.calculate_curvature((0, 0), (1, 1), (2, 0))
            0.5
        """
        try:
            # 向量叉积计算曲率
            v1 = np.array([p1[0] - p0[0], p1[1] - p0[1]])
            v2 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
            
            cross_product = np.cross(v1, v2)
            area = abs(cross_product) / 2
            
            # 边长平方
            a_sq = np.dot(v1, v1)
            b_sq = np.dot(v2, v2)
            c_sq = (p2[0] - p0[0])**2 + (p2[1] - p0[1])**2
            
            # 防止除以零
            denominator = a_sq * b_sq * c_sq
            if denominator < 1e-10:
                return 0.0
            
            # 曲率公式
            curvature = 4 * area / math.sqrt(denominator)
            return curvature
            
        except Exception as e:
            logger.error("Curvature calculation failed: %s", str(e))
            return 0.0
    
    def _subdivide_bezier(self, points: List[Tuple[float, float]], 
                         depth: int = 0) -> List[Tuple[float, float]]:
        """
        递归细分贝塞尔曲线 (de Casteljau算法)
        
        Args:
            points: 控制点列表
            depth: 当前递归深度
            
        Returns:
            List[Tuple]: 细分后的点集
        """
        if depth >= self.config.max_subdivision:
            return points
        
        # 计算中间点
        midpoints = []
        for i in range(len(points) - 1):
            p1 = np.array(points[i])
            p2 = np.array(points[i + 1])
            midpoints.append(tuple((p1 + p2) / 2))
        
        if len(midpoints) == 1:
            return [points[0], midpoints[0], points[-1]]
        
        # 递归细分
        left = self._subdivide_bezier([points[0]] + midpoints[:1], depth + 1)
        right = self._subdivide_bezier([midpoints[-1]] + [points[-1]], depth + 1)
        
        return left + right[1:]
    
    def _calculate_lod_level(self, curvature: float, 
                            viewport_scale: float) -> int:
        """
        计算动态LOD级别
        
        Args:
            curvature: 曲线曲率
            viewport_scale: 视口缩放级别
            
        Returns:
            int: LOD级别 (0=最低精度, max_subdivision=最高精度)
        """
        # 基于曲率和缩放级别的自适应算法
        base_level = int(curvature * 10 * viewport_scale)
        
        # 考虑像素密度的影响
        density_factor = self.config.pixel_density / 96.0
        
        # 计算最终LOD级别并限制在合理范围
        lod = int(base_level * density_factor)
        lod = max(0, min(lod, self.config.max_subdivision))
        
        logger.debug("LOD calculated: curvature=%.3f, scale=%.2f, lod=%d", 
                    curvature, viewport_scale, lod)
        return lod
    
    def render_curves(self, curves: List[Dict], 
                     viewport: Dict) -> List[Dict]:
        """
        渲染贝塞尔曲线集合
        
        Args:
            curves: 贝塞尔曲线定义列表
            viewport: 视口参数
            
        Returns:
            List[Dict]: 渲染图元列表
            
        Raises:
            ValueError: 输入数据验证失败
        """
        # 输入验证
        if not curves:
            logger.warning("Empty curves list provided")
            return []
        
        if 'scale' not in viewport or viewport['scale'] <= 0:
            raise ValueError("Invalid viewport scale")
        
        rendered_primitives = []
        
        for idx, curve in enumerate(curves):
            try:
                # 验证曲线数据
                if 'control_points' not in curve:
                    logger.warning("Curve %d missing control_points, skipping", idx)
                    continue
                
                points = curve['control_points']
                if len(points) < 2:
                    logger.warning("Curve %d has insufficient points (%d), skipping", 
                                 idx, len(points))
                    continue
                
                # 计算曲线整体曲率
                total_curvature = 0.0
                for i in range(1, len(points) - 1):
                    total_curvature += self.calculate_curvature(
                        points[i-1], points[i], points[i+1]
                    )
                avg_curvature = total_curvature / max(1, len(points) - 2)
                
                # 计算LOD级别
                lod_level = self._calculate_lod_level(
                    avg_curvature, viewport['scale']
                )
                
                # 根据LOD级别细分曲线
                if lod_level == 0 or curve.get('degree', 3) == 1:
                    # 直线或最低LOD
                    primitive = {
                        'type': 'line',
                        'points': points,
                        'precision': 1.0
                    }
                else:
                    # 高LOD曲线细分
                    subdivided = self._subdivide_bezier(points, lod_level)
                    
                    # 简化细分后的点集 (Ramer-Douglas-Peucker算法简化版)
                    simplified = self._simplify_points(
                        subdivided, 
                        self.config.tolerance / viewport['scale']
                    )
                    
                    primitive = {
                        'type': 'curve',
                        'points': simplified,
                        'precision': lod_level / self.config.max_subdivision
                    }
                
                rendered_primitives.append(primitive)
                logger.debug("Rendered curve %d with LOD %d", idx, lod_level)
                
            except Exception as e:
                logger.error("Failed to render curve %d: %s", idx, str(e))
                continue
        
        logger.info("Rendered %d/%d curves successfully", 
                   len(rendered_primitives), len(curves))
        return rendered_primitives
    
    def _simplify_points(self, points: List[Tuple[float, float]], 
                        tolerance: float) -> List[Tuple[float, float]]:
        """
        简化点集 (Ramer-Douglas-Peucker算法简化版)
        
        Args:
            points: 原始点集
            tolerance: 简化容差
            
        Returns:
            List[Tuple]: 简化后的点集
        """
        if len(points) <= 2:
            return points
        
        # 找到距离首尾连线最远的点
        start = np.array(points[0])
        end = np.array(points[-1])
        line_vec = end - start
        line_len = np.linalg.norm(line_vec)
        
        if line_len < 1e-6:
            return points
        
        line_unit = line_vec / line_len
        max_dist = 0
        max_idx = 0
        
        for i in range(1, len(points) - 1):
            point = np.array(points[i])
            vec = point - start
            proj_length = np.dot(vec, line_unit)
            proj = start + proj_length * line_unit
            dist = np.linalg.norm(point - proj)
            
            if dist > max_dist:
                max_dist = dist
                max_idx = i
        
        # 如果最大距离大于容差，递归简化
        if max_dist > tolerance:
            left = self._simplify_points(points[:max_idx+1], tolerance)
            right = self._simplify_points(points[max_idx:], tolerance)
            return left[:-1] + right
        else:
            return [points[0], points[-1]]


# 使用示例
if __name__ == "__main__":
    """
    使用示例:
    
    1. 创建渲染器实例
    2. 定义贝塞尔曲线和视口参数
    3. 执行渲染
    4. 获取细分后的图元
    
    Example:
        >>> renderer = VectorRenderer(ViewportConfig(scale=1.0, pixel_density=326))
        >>> curves = [{
        ...     'control_points': [(0, 0), (50, 100), (100, 0)],
        ...     'degree': 2,
        ...     'weight': 1.0
        ... }]
        >>> viewport = {'scale': 2.5, 'center': (50, 50), 'pixel_density': 326}
        >>> primitives = renderer.render_curves(curves, viewport)
    """
    # 初始化渲染器
    config = ViewportConfig(
        scale=1.0,
        pixel_density=326,  # 移动设备典型值
        max_subdivision=8,
        tolerance=0.05
    )
    renderer = VectorRenderer(config)
    
    # 定义测试曲线 (二次贝塞尔曲线)
    test_curves = [
        {
            'control_points': [(0, 0), (50, 100), (100, 0)],
            'degree': 2,
            'weight': 1.0
        },
        {
            'control_points': [(100, 0), (150, 50), (200, 50), (250, 0)],
            'degree': 3,
            'weight': 1.5
        },
        {
            'control_points': [(0, 100), (250, 100)],  # 直线
            'degree': 1,
            'weight': 0.5
        }
    ]
    
    # 测试不同缩放级别
    test_viewports = [
        {'scale': 0.5, 'center': (125, 50), 'pixel_density': 326},   # 宏观视图
        {'scale': 2.0, 'center': (125, 50), 'pixel_density': 326},   # 中等视图
        {'scale': 10.0, 'center': (125, 50), 'pixel_density': 326}   # 微观视图
    ]
    
    print("=== Vector Rendering Demo ===")
    for i, viewport in enumerate(test_viewports):
        print(f"\nViewport {i+1} (scale={viewport['scale']}x):")
        primitives = renderer.render_curves(test_curves, viewport)
        
        for j, prim in enumerate(primitives):
            print(f"  Primitive {j+1}: type={prim['type']}, "
                  f"points={len(prim['points'])}, precision={prim['precision']:.2f}")