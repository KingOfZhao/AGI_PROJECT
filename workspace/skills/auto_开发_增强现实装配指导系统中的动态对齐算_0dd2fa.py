"""
增强现实装配指导系统中的动态对齐算法

该模块实现了将CAD装配体的公差约束映射为AR界面动态布局的核心算法。
通过实时分析物理公差与视觉遮挡，计算UI元素的最佳吸附位置。

典型应用场景：
1. 工业AR装配指导
2. 数字孪生可视化
3. 精密仪器维修辅助

输入格式示例：
{
    "tolerances": {
        "shaft_diameter": {"nominal": 50.0, "upper": 0.05, "lower": -0.02},
        "hole_position": {"x": 100.0, "y": 75.0, "tolerance_zone": 0.1}
    },
    "ui_elements": [
        {"id": "label_1", "size": [120, 40], "priority": "high"},
        {"id": "arrow_1", "size": [80, 80], "priority": "medium"}
    ]
}

输出格式示例：
{
    "layout_adjustments": [
        {"element_id": "label_1", "position": [95.3, 110.2], "visibility_score": 0.95}
    ],
    "alignment_status": "ALIGNED_WITHIN_TOLERANCE"
}
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AR_Alignment_Engine")


class AlignmentStatus(Enum):
    """对齐状态枚举"""
    ALIGNED_PERFECT = auto()
    ALIGNED_WITHIN_TOLERANCE = auto()
    MISALIGNED_WARNING = auto()
    MISALIGNED_CRITICAL = auto()
    OCCLUSION_DETECTED = auto()


@dataclass
class ToleranceZone:
    """公差区域数据结构"""
    x: float
    y: float
    zone_radius: float

    def contains(self, point: Tuple[float, float]) -> bool:
        """检查点是否在公差区域内"""
        distance = math.sqrt((point[0] - self.x)**2 + (point[1] - self.y)**2)
        return distance <= self.zone_radius


@dataclass
class UIElement:
    """AR界面元素"""
    id: str
    width: float
    height: float
    priority: int  # 1-5, 5最高
    base_position: Tuple[float, float]


class DynamicAlignmentEngine:
    """
    动态对齐引擎核心类
    
    处理CAD公差与AR UI的动态对齐，主要功能包括：
    1. 公差区域计算与映射
    2. 视觉遮挡检测
    3. 最佳吸附位置计算
    4. 实时对齐状态评估
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化对齐引擎
        
        Args:
            config: 配置字典，包含：
                - max_iterations: 最大迭代次数 (默认50)
                - convergence_threshold: 收敛阈值 (默认0.01)
                - occlusion_penalty: 遮挡惩罚系数 (默认0.8)
        """
        self.config = config or {
            "max_iterations": 50,
            "convergence_threshold": 0.01,
            "occlusion_penalty": 0.8
        }
        self.tolerance_zones: Dict[str, ToleranceZone] = {}
        self.ui_elements: Dict[str, UIElement] = {}
        logger.info("DynamicAlignmentEngine initialized with config: %s", self.config)
    
    def load_cad_tolerances(self, cad_data: Dict[str, Dict]) -> None:
        """
        加载并解析CAD公差数据
        
        Args:
            cad_data: CAD系统导出的公差数据
                格式: {
                    "feature_name": {
                        "x": float, "y": float, 
                        "tolerance_zone": float
                    }
                }
        
        Raises:
            ValueError: 当数据格式无效时
        """
        if not cad_data:
            logger.error("Empty CAD data provided")
            raise ValueError("CAD tolerance data cannot be empty")
        
        try:
            for feature, data in cad_data.items():
                self._validate_tolerance_data(data)
                self.tolerance_zones[feature] = ToleranceZone(
                    x=data["x"],
                    y=data["y"],
                    zone_radius=data["tolerance_zone"]
                )
            logger.info("Loaded %d tolerance zones from CAD data", len(cad_data))
        except KeyError as e:
            logger.error("Missing required key in CAD data: %s", str(e))
            raise ValueError(f"Invalid CAD data format: missing {str(e)}")
    
    def _validate_tolerance_data(self, data: Dict) -> None:
        """
        验证公差数据的有效性 (辅助函数)
        
        Args:
            data: 单个公差数据项
            
        Raises:
            ValueError: 当数据无效时
        """
        required_keys = {"x", "y", "tolerance_zone"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Tolerance data must contain {required_keys}")
        
        if data["tolerance_zone"] <= 0:
            raise ValueError("Tolerance zone must be positive")
        
        if not all(isinstance(data[k], (int, float)) for k in required_keys):
            raise ValueError("Tolerance values must be numeric")
    
    def register_ui_element(self, element: UIElement) -> None:
        """
        注册UI元素到对齐引擎
        
        Args:
            element: UIElement实例
        """
        if element.priority < 1 or element.priority > 5:
            logger.warning("Priority %d out of range (1-5), clamping", element.priority)
            element.priority = max(1, min(5, element.priority))
        
        self.ui_elements[element.id] = element
        logger.debug("Registered UI element: %s", element.id)
    
    def calculate_optimal_position(
        self, 
        element_id: str, 
        current_position: Tuple[float, float],
        camera_transform: Tuple[float, float, float]
    ) -> Tuple[Tuple[float, float], AlignmentStatus]:
        """
        计算UI元素的最佳吸附位置 (核心函数1)
        
        基于以下因素计算：
        1. 公差约束
        2. 相机视角变换
        3. 其他UI元素的遮挡
        4. 元素优先级
        
        Args:
            element_id: UI元素ID
            current_position: 当前位置
            camera_transform: 相机变换矩阵
        
        Returns:
            Tuple[最佳位置, 对齐状态]
            
        Raises:
            KeyError: 当元素未注册时
        """
        if element_id not in self.ui_elements:
            logger.error("Unregistered element: %s", element_id)
            raise KeyError(f"UI element {element_id} not registered")
        
        element = self.ui_elements[element_id]
        best_position = current_position
        best_score = -float("inf")
        status = AlignmentStatus.MISALIGNED_CRITICAL
        
        # 检查所有公差区域
        for zone_name, zone in self.tolerance_zones.items():
            # 计算在公差区域内的候选位置
            candidates = self._generate_candidate_positions(zone, current_position)
            
            for pos in candidates:
                # 计算位置评分
                score = self._evaluate_position(
                    pos, element, zone, camera_transform
                )
                
                if score > best_score:
                    best_score = score
                    best_position = pos
        
        # 确定对齐状态
        in_tolerance = any(
            zone.contains(best_position) 
            for zone in self.tolerance_zones.values()
        )
        
        if best_score > 0.9:
            status = AlignmentStatus.ALIGNED_PERFECT
        elif in_tolerance:
            status = AlignmentStatus.ALIGNED_WITHIN_TOLERANCE
        elif best_score > 0.5:
            status = AlignmentStatus.MISALIGNED_WARNING
        
        logger.info(
            "Calculated optimal position for %s: %s (score: %.2f, status: %s)",
            element_id, best_position, best_score, status.name
        )
        return best_position, status
    
    def _generate_candidate_positions(
        self, 
        zone: ToleranceZone, 
        base_pos: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """
        生成候选位置 (辅助函数)
        
        在公差区域周围生成一组候选位置点
        """
        candidates = [base_pos]
        
        # 在公差区域边界生成均匀分布的点
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x = zone.x + zone.zone_radius * math.cos(rad)
            y = zone.y + zone.zone_radius * math.sin(rad)
            candidates.append((x, y))
        
        # 添加公差区域中心
        candidates.append((zone.x, zone.y))
        return candidates
    
    def _evaluate_position(
        self,
        position: Tuple[float, float],
        element: UIElement,
        zone: ToleranceZone,
        camera_transform: Tuple[float, float, float]
    ) -> float:
        """
        评估位置质量 (内部方法)
        
        考虑因素：
        1. 与公差区域的距离
        2. 与相机视角的对齐
        3. 与其他UI元素的遮挡
        """
        # 1. 公差区域评分 (0-1)
        dist_to_zone = math.sqrt(
            (position[0] - zone.x)**2 + (position[1] - zone.y)**2
        )
        tolerance_score = max(0, 1 - dist_to_zone / (2 * zone.zone_radius))
        
        # 2. 相机对齐评分 (0-1)
        cam_x, cam_y, cam_z = camera_transform
        if cam_z <= 0:
            camera_score = 0.5  # 默认评分
        else:
            # 简单的透视投影模型
            projected_x = position[0] * (1 + cam_z / 1000)
            projected_y = position[1] * (1 + cam_z / 1000)
            camera_score = 1 - min(1, abs(projected_x - position[0]) / 100)
        
        # 3. 遮挡检测
        occlusion_penalty = 0
        for other_id, other_elem in self.ui_elements.items():
            if other_id == element.id:
                continue
            
            # 简单的边界框碰撞检测
            if self._check_occlusion(position, element, other_elem):
                occlusion_penalty += self.config["occlusion_penalty"] * (
                    element.priority / other_elem.priority
                )
        
        # 综合评分
        total_score = (
            0.5 * tolerance_score + 
            0.3 * camera_score + 
            0.2 * (1 - min(1, occlusion_penalty))
        ) * (element.priority / 5)
        
        return total_score
    
    def _check_occlusion(
        self, 
        pos: Tuple[float, float], 
        elem1: UIElement, 
        elem2: UIElement
    ) -> bool:
        """检查两个元素是否重叠 (内部方法)"""
        # 简化的矩形碰撞检测
        return (
            abs(pos[0] - elem2.base_position[0]) < (elem1.width + elem2.width) / 2 and
            abs(pos[1] - elem2.base_position[1]) < (elem1.height + elem2.height) / 2
        )
    
    def batch_align_ui_elements(
        self,
        elements_data: List[Dict],
        camera_transform: Tuple[float, float, float]
    ) -> Dict[str, Dict]:
        """
        批量处理UI元素对齐 (核心函数2)
        
        Args:
            elements_data: 元素数据列表，每项包含:
                - id: 元素ID
                - current_position: 当前位置
            camera_transform: 相机变换矩阵
        
        Returns:
            Dict: {
                "layout_adjustments": [
                    {
                        "element_id": str,
                        "position": List[float],
                        "visibility_score": float
                    }
                ],
                "alignment_status": str
            }
        """
        results = {"layout_adjustments": [], "alignment_status": "UNKNOWN"}
        worst_status = AlignmentStatus.ALIGNED_PERFECT
        
        for elem_data in elements_data:
            elem_id = elem_data["id"]
            if elem_id not in self.ui_elements:
                logger.warning("Skipping unregistered element: %s", elem_id)
                continue
            
            try:
                optimal_pos, status = self.calculate_optimal_position(
                    elem_id,
                    elem_data["current_position"],
                    camera_transform
                )
                
                results["layout_adjustments"].append({
                    "element_id": elem_id,
                    "position": list(optimal_pos),
                    "visibility_score": self._calculate_visibility_score(elem_id, optimal_pos)
                })
                
                # 跟踪最差状态
                if status.value > worst_status.value:
                    worst_status = status
                    
            except Exception as e:
                logger.error("Failed to align element %s: %s", elem_id, str(e))
                results["layout_adjustments"].append({
                    "element_id": elem_id,
                    "error": str(e)
                })
                worst_status = AlignmentStatus.MISALIGNED_CRITICAL
        
        results["alignment_status"] = worst_status.name
        return results
    
    def _calculate_visibility_score(
        self, 
        element_id: str, 
        position: Tuple[float, float]
    ) -> float:
        """
        计算UI元素的可见性评分 (内部方法)
        
        考虑因素：
        1. 屏幕边界约束
        2. 与其他元素的重叠
        3. 优先级权重
        """
        if element_id not in self.ui_elements:
            return 0.0
        
        element = self.ui_elements[element_id]
        width, height = element.width, element.height
        
        # 检查是否在屏幕边界内 (假设屏幕1920x1080)
        in_screen = (
            0 <= position[0] <= 1920 and
            0 <= position[1] <= 1080
        )
        
        if not in_screen:
            return 0.0
        
        # 计算与公差区域的距离
        min_distance = float("inf")
        for zone in self.tolerance_zones.values():
            dist = math.sqrt(
                (position[0] - zone.x)**2 + (position[1] - zone.y)**2
            )
            min_distance = min(min_distance, dist)
        
        # 归一化评分
        visibility = max(0, 1 - min_distance / 200) * (element.priority / 5)
        return visibility


# 使用示例
if __name__ == "__main__":
    # 示例1: 基本使用流程
    print("=== AR动态对齐系统示例 ===")
    
    # 初始化引擎
    engine = DynamicAlignmentEngine()
    
    # 加载CAD公差数据
    cad_tolerances = {
        "bearing_hole": {"x": 960.0, "y": 540.0, "tolerance_zone": 25.0},
        "shaft_connection": {"x": 850.0, "y": 600.0, "tolerance_zone": 15.0}
    }
    engine.load_cad_tolerances(cad_tolerances)
    
    # 注册UI元素
    label = UIElement(
        id="torque_label",
        width=120,
        height=40,
        priority=4,
        base_position=(960.0, 500.0)
    )
    engine.register_ui_element(label)
    
    # 计算最佳位置
    optimal_pos, status = engine.calculate_optimal_position(
        "torque_label",
        (970.0, 510.0),
        (50.0, -30.0, 200.0)
    )
    print(f"最佳位置: {optimal_pos}, 状态: {status.name}")
    
    # 示例2: 批量处理
    print("\n=== 批量处理示例 ===")
    elements_to_align = [
        {"id": "torque_label", "current_position": (970.0, 510.0)},
    ]
    
    batch_result = engine.batch_align_ui_elements(
        elements_to_align,
        (0.0, 0.0, 150.0)
    )
    print("批量处理结果:", batch_result)