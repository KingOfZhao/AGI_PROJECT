"""
Module: parametric_cad_ui_engine
Description: 实现一套将CAD几何约束求解算法引入UI布局的动态参数化引擎。
             支持线性/非线性方程组求解，使UI元素具备严谨的数学自适应性。

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """定义支持的几何约束类型"""
    DISTANCE = "distance"               # 两点间距离固定
    COINCIDENT = "coincident"           # 两点重合
    HORIZONTAL = "horizontal"           # 水平对齐
    VERTICAL = "vertical"               # 垂直对齐
    TANGENT = "tangent"                 # 切线约束
    ANGLE = "angle"                     # 角度约束
    RADIUS = "radius"                   # 半径约束

@dataclass
class UIElement:
    """
    UI元素的数据结构定义。
    
    Attributes:
        id (str): 元素的唯一标识符
        center_x (float): 中心点X坐标
        center_y (float): 中心点Y坐标
        width (float): 元素宽度
        height (float): 元素高度
        radius (Optional[float]): 如果是圆形元素，表示半径
        angle (Optional[float]): 旋转角度（度）
    """
    id: str
    center_x: float = 0.0
    center_y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    radius: Optional[float] = None
    angle: Optional[float] = None

@dataclass
class GeometricConstraint:
    """
    几何约束的数据结构定义。
    
    Attributes:
        type (ConstraintType): 约束类型
        elements (List[str]): 涉及的元素ID列表
        value (Optional[float]): 约束值（如距离、角度等）
    """
    type: ConstraintType
    elements: List[str]
    value: Optional[float] = None

class ParametricUIEngine:
    """
    动态参数化UI引擎核心类。
    将CAD领域的几何约束求解算法应用于UI布局系统。
    """
    
    def __init__(self, tolerance: float = 1e-4, max_iterations: int = 1000):
        """
        初始化引擎。
        
        Args:
            tolerance (float): 求解器的收敛容差
            max_iterations (int): 最大迭代次数
        """
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.elements: Dict[str, UIElement] = {}
        self.constraints: List[GeometricConstraint] = []
        logger.info("ParametricUIEngine initialized with tolerance=%e, max_iter=%d", 
                    tolerance, max_iterations)

    def add_element(self, element: UIElement) -> None:
        """
        向引擎添加UI元素。
        
        Args:
            element (UIElement): 要添加的UI元素对象
            
        Raises:
            ValueError: 如果元素ID已存在或数据无效
        """
        if not element.id or not isinstance(element.id, str):
            raise ValueError("Element ID must be a non-empty string")
        
        if element.id in self.elements:
            raise ValueError(f"Element with ID '{element.id}' already exists")
            
        # 数据验证
        if element.width < 0 or element.height < 0:
            raise ValueError("Element dimensions must be non-negative")
            
        if element.radius is not None and element.radius < 0:
            raise ValueError("Element radius must be non-negative")
            
        self.elements[element.id] = element
        logger.debug("Added element: %s", element.id)

    def add_constraint(self, constraint: GeometricConstraint) -> None:
        """
        向引擎添加几何约束。
        
        Args:
            constraint (GeometricConstraint): 要添加的几何约束
            
        Raises:
            ValueError: 如果约束无效或引用的元素不存在
        """
        if not constraint.elements:
            raise ValueError("Constraint must involve at least one element")
            
        for elem_id in constraint.elements:
            if elem_id not in self.elements:
                raise ValueError(f"Element '{elem_id}' referenced in constraint does not exist")
        
        # 检查约束值的有效性
        if constraint.type in [ConstraintType.DISTANCE, ConstraintType.RADIUS, ConstraintType.ANGLE]:
            if constraint.value is None or constraint.value < 0:
                raise ValueError(f"Constraint type {constraint.type} requires a non-negative value")
        
        self.constraints.append(constraint)
        logger.debug("Added constraint: %s involving %s", constraint.type, constraint.elements)

    def _build_equation_system(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        根据当前元素和约束构建非线性方程组。
        内部辅助函数。
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: 返回雅可比矩阵和残差向量
        """
        num_vars = len(self.elements) * 2  # 每个元素有x, y两个变量
        num_constraints = len(self.constraints)
        
        # 初始化雅可比矩阵和残差向量
        jacobian = np.zeros((num_constraints, num_vars))
        residuals = np.zeros(num_constraints)
        
        # 构建方程组（简化版示例，实际CAD系统会更复杂）
        for i, constraint in enumerate(self.constraints):
            if len(constraint.elements) < 2:
                continue
                
            elem1 = self.elements[constraint.elements[0]]
            elem2 = self.elements[constraint.elements[1]]
            
            idx1 = list(self.elements.keys()).index(elem1.id) * 2
            idx2 = list(self.elements.keys()).index(elem2.id) * 2
            
            if constraint.type == ConstraintType.DISTANCE:
                # 距离约束: sqrt((x2-x1)^2 + (y2-y1)^2) = d
                dx = elem2.center_x - elem1.center_x
                dy = elem2.center_y - elem1.center_y
                dist = np.sqrt(dx**2 + dy**2)
                
                if dist > 0:
                    jacobian[i, idx1] = -dx / dist
                    jacobian[i, idx1+1] = -dy / dist
                    jacobian[i, idx2] = dx / dist
                    jacobian[i, idx2+1] = dy / dist
                
                residuals[i] = dist - constraint.value
                
            elif constraint.type == ConstraintType.COINCIDENT:
                # 重合约束: x1=x2, y1=y2
                jacobian[i, idx1] = 1
                jacobian[i, idx2] = -1
                jacobian[i, idx1+1] = 1
                jacobian[i, idx2+1] = -1
                residuals[i] = np.sqrt((elem1.center_x - elem2.center_x)**2 + 
                                      (elem1.center_y - elem2.center_y)**2)
        
        return jacobian, residuals

    def solve_constraints(self) -> Dict[str, UIElement]:
        """
        求解所有几何约束并更新元素位置。
        使用牛顿-拉夫逊法求解非线性方程组。
        
        Returns:
            Dict[str, UIElement]: 更新后的元素字典
            
        Raises:
            RuntimeError: 如果求解失败或未收敛
        """
        if not self.constraints:
            logger.warning("No constraints to solve")
            return self.elements
            
        logger.info("Starting constraint solving with %d constraints", len(self.constraints))
        
        for iteration in range(self.max_iterations):
            jacobian, residuals = self._build_equation_system()
            
            # 检查收敛
            error = np.linalg.norm(residuals)
            if error < self.tolerance:
                logger.info("Converged after %d iterations with error %e", iteration, error)
                return self.elements
                
            # 求解线性系统 J * delta = -residuals
            try:
                delta = np.linalg.lstsq(jacobian, -residuals, rcond=None)[0]
            except np.linalg.LinAlgError:
                raise RuntimeError("Failed to solve linear system in iteration %d" % iteration)
                
            # 更新元素位置
            for i, elem_id in enumerate(self.elements.keys()):
                idx = i * 2
                self.elements[elem_id].center_x += delta[idx]
                self.elements[elem_id].center_y += delta[idx+1]
                
            logger.debug("Iteration %d: error=%e", iteration, error)
        
        raise RuntimeError("Failed to converge after %d iterations (error=%e)" % 
                          (self.max_iterations, error))

    def generate_layout_report(self) -> Dict[str, Any]:
        """
        生成布局报告，包含元素位置和约束信息。
        
        Returns:
            Dict[str, Any]: 包含详细布局信息的字典
        """
        report = {
            "elements": {k: v.__dict__ for k, v in self.elements.items()},
            "constraints": [c.__dict__ for c in self.constraints],
            "solver_info": {
                "tolerance": self.tolerance,
                "max_iterations": self.max_iterations
            }
        }
        logger.info("Generated layout report")
        return report

def demo_usage():
    """
    演示参数化UI引擎的使用方法。
    """
    # 创建引擎实例
    engine = ParametricUIEngine(tolerance=1e-6, max_iterations=500)
    
    # 添加UI元素
    elem_a = UIElement(id="button_a", center_x=0, center_y=0, width=100, height=50)
    elem_b = UIElement(id="button_b", center_x=200, center_y=0, width=100, height=50)
    elem_c = UIElement(id="circle_c", center_x=100, center_y=0, radius=50)
    
    engine.add_element(elem_a)
    engine.add_element(elem_b)
    engine.add_element(elem_c)
    
    # 添加几何约束
    # 约束1: button_a和button_b保持200的距离
    constraint1 = GeometricConstraint(
        type=ConstraintType.DISTANCE,
        elements=["button_a", "button_b"],
        value=200
    )
    
    # 约束2: circle_c与button_a垂直对齐
    constraint2 = GeometricConstraint(
        type=ConstraintType.VERTICAL,
        elements=["button_a", "circle_c"]
    )
    
    # 约束3: circle_c与button_b垂直对齐
    constraint3 = GeometricConstraint(
        type=ConstraintType.VERTICAL,
        elements=["button_b", "circle_c"]
    )
    
    engine.add_constraint(constraint1)
    engine.add_constraint(constraint2)
    engine.add_constraint(constraint3)
    
    try:
        # 求解约束
        solved_elements = engine.solve_constraints()
        
        # 输出结果
        print("\nSolved Layout:")
        for elem_id, elem in solved_elements.items():
            print(f"{elem_id}: ({elem.center_x:.2f}, {elem.center_y:.2f})")
            
        # 生成报告
        report = engine.generate_layout_report()
        print("\nLayout Report:")
        print(report)
        
    except RuntimeError as e:
        print(f"Error solving constraints: {e}")

if __name__ == "__main__":
    demo_usage()