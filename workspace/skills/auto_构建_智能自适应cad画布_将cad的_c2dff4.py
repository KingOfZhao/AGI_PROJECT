"""
Module: intelligent_cad_canvas.py
Description: 构建智能自适应CAD画布逻辑核心。
             将CAD的几何约束求解器概念与Flutter的Layout算法融合。
             当用户拖动草图点时，系统触发类似Widget的Relayout流程，
             由微型求解器实时计算参数化约束，实现自适应联动。
Author: Senior Python Engineer (AGI System)
Date: 2023-10-27
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """定义CAD中的几何约束类型"""
    FIXED = auto()         # 固定点
    HORIZONTAL = auto()    # 水平约束
    VERTICAL = auto()      # 垂直约束
    COINCIDENT = auto()    # 重合点
    DISTANCE = auto()      # 距离约束

@dataclass
class Point:
    """表示CAD画布上的一个二维点"""
    id: str
    x: float
    y: float
    is_locked: bool = False  # 类似于Flutter中的fixed position约束

    def move(self, dx: float, dy: float) -> None:
        if self.is_locked:
            logger.warning(f"Attempted to move locked point: {self.id}")
            return
        self.x += dx
        self.y += dy

@dataclass
class Constraint:
    """几何约束定义"""
    type: ConstraintType
    target_ids: List[str]
    params: Dict[str, Any] = field(default_factory=dict)

class CADLayoutSolver:
    """
    核心求解器类。
    模拟Flutter的Layout算法，但在内部处理几何约束。
    """

    def __init__(self):
        self._points: Dict[str, Point] = {}
        self._constraints: List[Constraint] = []
        self._dirty: bool = True
        self._layout_callback: Optional[Callable[[Dict[str, Point]], None]] = None

    def register_layout_callback(self, callback: Callable[[Dict[str, Point]], None]) -> None:
        """注册布局更新回调，类似于Flutter中的setState触发重绘"""
        self._layout_callback = callback

    def add_point(self, point: Point) -> None:
        """向画布添加点"""
        if point.id in self._points:
            raise ValueError(f"Point ID {point.id} already exists.")
        self._points[point.id] = point
        self._mark_dirty()
        logger.info(f"Added point: {point.id}")

    def add_constraint(self, constraint: Constraint) -> None:
        """添加几何约束"""
        for pid in constraint.target_ids:
            if pid not in self._points:
                raise ValueError(f"Target point {pid} not found for constraint.")
        self._constraints.append(constraint)
        self._mark_dirty()
        logger.info(f"Added constraint: {constraint.type} for {constraint.target_ids}")

    def update_point_position(self, point_id: str, new_x: float, new_y: float) -> None:
        """
        核心交互函数：用户拖动点。
        类似于Flutter中Widget的状态更新，触发Relayout。
        """
        if point_id not in self._points:
            raise KeyError(f"Point {point_id} not found.")
        
        point = self._points[point_id]
        if point.is_locked:
            return

        # 更新驱动点的位置
        old_x, old_y = point.x, point.y
        point.x = new_x
        point.y = new_y
        
        logger.debug(f"User moved {point_id} to ({new_x}, {new_y})")
        
        # 触发布局更新
        self.relayout()
        
        return {
            "old_pos": (old_x, old_y),
            "new_pos": (point.x, point.y),
            "point_id": point_id
        }

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _check_boundary(self, x: float, y: float) -> bool:
        """辅助函数：边界检查，防止数值溢出或超出画布"""
        CANVAS_LIMIT = 10000.0
        if not (math.isfinite(x) and math.isfinite(y)):
            return False
        if abs(x) > CANVAS_LIMIT or abs(y) > CANVAS_LIMIT:
            return False
        return True

    def relayout(self) -> None:
        """
        核心算法：执行约束求解。
        这是一个简化的迭代求解器，模拟Flutter的ParentData传递和BoxConstraints调整。
        """
        if not self._dirty:
            return

        logger.info("Starting CAD Constraint Relayout...")
        
        # 迭代求解
        for _ in range(5): # 限制迭代次数防止死循环
            changes_made = False
            for constraint in self._constraints:
                if constraint.type == ConstraintType.HORIZONTAL:
                    # 强制两点Y轴一致
                    p1 = self._points[constraint.target_ids[0]]
                    p2 = self._points[constraint.target_ids[1]]
                    if not p1.is_locked and p1.y != p2.y:
                        p1.y = p2.y
                        changes_made = True
                    elif not p2.is_locked and p2.y != p1.y:
                        p2.y = p1.y
                        changes_made = True
                
                elif constraint.type == ConstraintType.VERTICAL:
                    # 强制两点X轴一致
                    p1 = self._points[constraint.target_ids[0]]
                    p2 = self._points[constraint.target_ids[1]]
                    if not p1.is_locked and p1.x != p2.x:
                        p1.x = p2.x
                        changes_made = True
                    elif not p2.is_locked and p2.x != p1.x:
                        p2.x = p1.x
                        changes_made = True

                elif constraint.type == ConstraintType.DISTANCE:
                    # 保持两点间距离
                    p1 = self._points[constraint.target_ids[0]]
                    p2 = self._points[constraint.target_ids[1]]
                    target_dist = constraint.params['value']
                    
                    current_dist = math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
                    if current_dist < 1e-6: continue # 避免除零

                    delta = current_dist - target_dist
                    if abs(delta) > 0.01:
                        # 简单的弹簧模型：两点各移动一半距离
                        dx = (p2.x - p1.x) / current_dist * (delta / 2)
                        dy = (p2.y - p1.y) / current_dist * (delta / 2)
                        
                        if not p1.is_locked:
                            p1.x += dx
                            p1.y += dy
                        if not p2.is_locked:
                            p2.x -= dx
                            p2.y -= dy
                        changes_made = True

            # 边界验证
            for p in self._points.values():
                if not self._check_boundary(p.x, p.y):
                    logger.error(f"Boundary violation detected for point {p.id}")
                    # 回滚或修正逻辑应在此处添加
                    p.x = max(min(p.x, 10000), -10000)
                    p.y = max(min(p.y, 10000), -10000)

            if not changes_made:
                break
        
        self._dirty = False
        logger.info("Relayout complete.")
        
        # 触发渲染回调
        if self._layout_callback:
            self._layout_callback(self._points)

    def export_layout_data(self) -> Dict[str, Tuple[float, float]]:
        """导出当前所有点的坐标，供Flutter渲染层使用"""
        return {pid: (p.x, p.y) for pid, p in self._points.items()}

# 使用示例
if __name__ == "__main__":
    def mock_flutter_render(points: Dict[str, Point]):
        print("\n>>> [Flutter Layer] Updating Canvas...")
        for pid, p in points.items():
            print(f"   Drawing Point {pid} at ({p.x:.2f}, {p.y:.2f})")

    # 1. 初始化求解器
    solver = CADLayoutSolver()
    solver.register_layout_callback(mock_flutter_render)

    try:
        # 2. 构建初始草图
        # 定义三个点，形成一个直角三角形的结构基础
        pA = Point("A", 100, 100)
        pB = Point("B", 200, 100)
        pC = Point("C", 200, 200)

        solver.add_point(pA)
        solver.add_point(pB)
        solver.add_point(pC)

        # 3. 添加约束
        # A-B 水平
        solver.add_constraint(Constraint(ConstraintType.HORIZONTAL, ["A", "B"]))
        # B-C 垂直
        solver.add_constraint(Constraint(ConstraintType.VERTICAL, ["B", "C"]))
        # A-C 固定距离 141.4 (约100*sqrt(2))
        solver.add_constraint(Constraint(ConstraintType.DISTANCE, ["A", "C"], {"value": 141.4}))

        # 4. 用户交互：拖动点 A
        print("\n[Action] User drags Point A to (150, 100)")
        solver.update_point_position("A", 150, 100)
        
        # 验证结果：B点应该跟随移动以保持水平，C点应该调整位置以满足距离约束
        coords = solver.export_layout_data()
        print("\n[Result] Final Coordinates:", coords)

    except ValueError as e:
        logger.error(f"Input Error: {e}")
    except Exception as e:
        logger.error(f"System Error: {e}", exc_info=True)