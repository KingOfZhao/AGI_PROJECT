"""
高级物理装配模拟器模块 - 基于约束协商

该模块实现了一个自适应物理装配模拟系统，灵感来源于Flutter的弹性布局协议。
它将传统的CAD刚性配合转化为动态的约束协商过程。当机械结构发生设计变更时，
系统能够像UI重排一样自动传播约束变化，重新计算装配体空间位置，并检测干涉。

核心特性:
- 约束传播与协商
- 溢出检测
- 热修复建议生成

作者: AGI System
版本: 2.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConstraintSimulator")


class ConstraintType(Enum):
    """定义支持的约束类型枚举"""
    COINCIDENT = auto()  # 重合约束
    DISTANCE = auto()    # 距离约束
    ANGLE = auto()       # 角度约束
    PARALLEL = auto()    # 平行约束


class FixType(Enum):
    """修复建议类型"""
    EXPAND_GAP = auto()     # 扩大间隙
    REDUCE_SIZE = auto()    # 减小尺寸
    CHANGE_OFFSET = auto()  # 修改偏移


@dataclass
class Vector3D:
    """三维向量表示"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def magnitude(self) -> float:
        """计算向量模长"""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)


@dataclass
class Component:
    """装配体组件定义"""
    id: str
    name: str
    position: Vector3D = field(default_factory=Vector3D)
    size: Vector3D = field(default_factory=Vector3D)
    is_flexible: bool = True  # 是否可弹性调整


@dataclass
class Constraint:
    """几何约束定义"""
    id: str
    type: ConstraintType
    source_id: str
    target_id: str
    value: float = 0.0  # 约束值(距离/角度等)
    tolerance: float = 0.01  # 容差范围
    is_violated: bool = False  # 约束是否被违反


@dataclass
class OverflowWarning:
    """布局溢出警告"""
    component_id: str
    overflow_amount: float
    direction: str
    suggested_fix: str


class ConstraintSimulator:
    """
    基于约束协商的自适应物理装配模拟器
    
    该类实现了类似Flutter弹性布局的物理装配系统，能够处理组件间的
    约束关系，自动协商位置，并检测结构冲突。
    
    属性:
        components (Dict[str, Component]): 组件字典
        constraints (Dict[str, Constraint]): 约束字典
        constraint_graph (Dict[str, Set[str]]): 约束关系图
    
    示例:
        >>> simulator = ConstraintSimulator()
        >>> simulator.add_component(Component("bolt", "M8螺栓", size=Vector3D(8, 8, 40)))
        >>> simulator.add_component(Component("nut", "M8螺母", size=Vector3D(13, 13, 8)))
        >>> simulator.add_constraint(Constraint("c1", ConstraintType.COINCIDENT, "bolt", "nut"))
        >>> result = simulator.simulate_assembly()
    """
    
    def __init__(self, tolerance: float = 0.1):
        """
        初始化模拟器
        
        参数:
            tolerance: 全局容差阈值
        """
        self.components: Dict[str, Component] = {}
        self.constraints: Dict[str, Constraint] = {}
        self.constraint_graph: Dict[str, Set[str]] = {}
        self.tolerance = tolerance
        self._iteration_count = 0
        self._max_iterations = 100
        
        logger.info("ConstraintSimulator initialized with tolerance %.3f", tolerance)
    
    def add_component(self, component: Component) -> bool:
        """
        添加组件到装配体
        
        参数:
            component: 要添加的组件对象
            
        返回:
            bool: 添加是否成功
            
        异常:
            ValueError: 当组件ID已存在或数据无效时
        """
        # 数据验证
        if not component.id or not component.id.strip():
            raise ValueError("Component ID cannot be empty")
            
        if component.id in self.components:
            logger.error("Component ID %s already exists", component.id)
            raise ValueError(f"Component ID {component.id} already exists")
            
        # 边界检查
        if component.size.x < 0 or component.size.y < 0 or component.size.z < 0:
            raise ValueError("Component dimensions must be non-negative")
            
        self.components[component.id] = component
        self.constraint_graph[component.id] = set()
        
        logger.debug("Added component: %s (%s)", component.id, component.name)
        return True
    
    def add_constraint(self, constraint: Constraint) -> bool:
        """
        添加几何约束
        
        参数:
            constraint: 约束对象
            
        返回:
            bool: 添加是否成功
            
        异常:
            ValueError: 当约束引用不存在的组件时
        """
        # 验证组件存在性
        if constraint.source_id not in self.components:
            raise ValueError(f"Source component {constraint.source_id} not found")
        if constraint.target_id not in self.components:
            raise ValueError(f"Target component {constraint.target_id} not found")
            
        self.constraints[constraint.id] = constraint
        
        # 更新约束图
        self.constraint_graph[constraint.source_id].add(constraint.target_id)
        self.constraint_graph[constraint.target_id].add(constraint.source_id)
        
        logger.debug("Added constraint %s between %s and %s", 
                    constraint.id, constraint.source_id, constraint.target_id)
        return True
    
    def _calculate_distance(self, comp1: Component, comp2: Component) -> float:
        """
        辅助函数：计算两个组件中心点之间的距离
        
        参数:
            comp1: 第一个组件
            comp2: 第二个组件
            
        返回:
            float: 欧几里得距离
        """
        delta = comp1.position - comp2.position
        return delta.magnitude()
    
    def _check_collision(self, comp1: Component, comp2: Component) -> Tuple[bool, float]:
        """
        辅助函数：检测两个组件是否发生碰撞
        
        参数:
            comp1: 第一个组件
            comp2: 第二个组件
            
        返回:
            Tuple[bool, float]: (是否碰撞, 穿透深度)
        """
        # 简化的AABB碰撞检测
        overlap_x = (comp1.size.x + comp2.size.x) / 2 - abs(comp1.position.x - comp2.position.x)
        overlap_y = (comp1.size.y + comp2.size.y) / 2 - abs(comp1.position.y - comp2.position.y)
        overlap_z = (comp1.size.z + comp2.size.z) / 2 - abs(comp1.position.z - comp2.position.z)
        
        if overlap_x > 0 and overlap_y > 0 and overlap_z > 0:
            penetration = min(overlap_x, overlap_y, overlap_z)
            return True, penetration
        return False, 0.0
    
    def _propagate_constraint_change(self, source_id: str, visited: Set[str] = None) -> None:
        """
        核心函数：传播约束变化
        
        该方法递归地传播约束变化，类似于Flutter的约束传递机制。
        当一个组件位置改变时，所有相关联的约束都会被重新评估。
        
        参数:
            source_id: 变更源组件ID
            visited: 已访问组件集合(防止循环)
        """
        if visited is None:
            visited = set()
            
        if source_id in visited:
            return
            
        visited.add(source_id)
        source = self.components.get(source_id)
        if not source:
            return
            
        # 获取所有关联的约束
        related_constraints = [
            c for c in self.constraints.values() 
            if c.source_id == source_id or c.target_id == source_id
        ]
        
        for constraint in related_constraints:
            target_id = (constraint.target_id if constraint.source_id == source_id 
                        else constraint.source_id)
            target = self.components.get(target_id)
            
            if not target or not target.is_flexible:
                continue
                
            # 根据约束类型调整目标位置
            if constraint.type == ConstraintType.DISTANCE:
                current_dist = self._calculate_distance(source, target)
                if abs(current_dist - constraint.value) > constraint.tolerance:
                    # 计算调整方向
                    direction = target.position - source.position
                    if direction.magnitude() > 0:
                        direction = Vector3D(
                            direction.x / direction.magnitude(),
                            direction.y / direction.magnitude(),
                            direction.z / direction.magnitude()
                        )
                        # 应用弹性调整
                        adjustment = constraint.value - current_dist
                        target.position = target.position + Vector3D(
                            direction.x * adjustment * 0.5,  # 0.5为阻尼系数
                            direction.y * adjustment * 0.5,
                            direction.z * adjustment * 0.5
                        )
                        logger.debug("Adjusted %s position by %.3f", target_id, adjustment)
                        
            # 递归传播
            self._propagate_constraint_change(target_id, visited)
    
    def simulate_assembly(self) -> Dict[str, any]:
        """
        核心函数：执行装配模拟
        
        该方法执行完整的装配模拟过程，包括约束协商、位置计算和冲突检测。
        返回模拟结果和诊断信息。
        
        返回:
            Dict包含:
            - 'success': 模拟是否成功收敛
            - 'iterations': 迭代次数
            - 'warnings': 溢出警告列表
            - 'fix_suggestions': 修复建议列表
        """
        logger.info("Starting assembly simulation with %d components", len(self.components))
        
        warnings: List[OverflowWarning] = []
        suggestions: List[str] = []
        converged = False
        
        for iteration in range(self._max_iterations):
            self._iteration_count = iteration + 1
            max_error = 0.0
            
            # 遍历所有约束进行协商
            for constraint in self.constraints.values():
                source = self.components.get(constraint.source_id)
                target = self.components.get(constraint.target_id)
                
                if not source or not target:
                    continue
                    
                if constraint.type == ConstraintType.DISTANCE:
                    current_dist = self._calculate_distance(source, target)
                    error = abs(current_dist - constraint.value)
                    max_error = max(max_error, error)
                    
                    if error > constraint.tolerance:
                        constraint.is_violated = True
                        self._propagate_constraint_change(constraint.source_id)
                        
            # 检查碰撞
            comp_ids = list(self.components.keys())
            for i in range(len(comp_ids)):
                for j in range(i + 1, len(comp_ids)):
                    comp1 = self.components[comp_ids[i]]
                    comp2 = self.components[comp_ids[j]]
                    
                    is_colliding, penetration = self._check_collision(comp1, comp2)
                    if is_colliding:
                        warning = OverflowWarning(
                            component_id=f"{comp1.id}-{comp2.id}",
                            overflow_amount=penetration,
                            direction="internal",
                            suggested_fix=f"Separate {comp1.name} and {comp2.name} by {penetration:.2f}mm"
                        )
                        warnings.append(warning)
                        logger.warning("Collision detected: %s and %s overlap %.2fmm",
                                     comp1.name, comp2.name, penetration)
                        
            # 检查收敛
            if max_error < self.tolerance:
                converged = True
                logger.info("Simulation converged after %d iterations", self._iteration_count)
                break
                
        # 生成修复建议
        suggestions = self._generate_fix_suggestions(warnings)
        
        result = {
            'success': converged,
            'iterations': self._iteration_count,
            'final_positions': {cid: (c.position.x, c.position.y, c.position.z) 
                               for cid, c in self.components.items()},
            'warnings': warnings,
            'fix_suggestions': suggestions
        }
        
        logger.info("Simulation completed. Converged: %s, Warnings: %d", 
                   converged, len(warnings))
        return result
    
    def _generate_fix_suggestions(self, warnings: List[OverflowWarning]) -> List[str]:
        """
        辅助函数：生成热修复建议
        
        根据检测到的布局溢出问题，生成类似UI Debug的结构化修复建议。
        
        参数:
            warnings: 溢出警告列表
            
        返回:
            修复建议字符串列表
        """
        suggestions = []
        
        for warning in warnings:
            # 基于警告类型生成智能建议
            if warning.overflow_amount > 5.0:
                fix_type = FixType.REDUCE_SIZE
                suggestion = (
                    f"[CRITICAL] Structural conflict in {warning.component_id}: "
                    f"Consider reducing component size or using flexible material. "
                    f"Overflow: {warning.overflow_amount:.2f}mm"
                )
            elif warning.overflow_amount > 1.0:
                fix_type = FixType.CHANGE_OFFSET
                suggestion = (
                    f"[WARNING] Layout constraint violated in {warning.component_id}: "
                    f"Adjust mounting position by {warning.overflow_amount:.2f}mm. "
                    f"Quick fix: Add washer or spacer."
                )
            else:
                fix_type = FixType.EXPAND_GAP
                suggestion = (
                    f"[INFO] Minor fit issue in {warning.component_id}: "
                    f"Within manufacturing tolerance. No action required."
                )
                
            suggestions.append(suggestion)
            
        return suggestions
    
    def update_component_size(self, component_id: str, new_size: Vector3D) -> bool:
        """
        更新组件尺寸并触发约束重协商
        
        参数:
            component_id: 组件ID
            new_size: 新的尺寸向量
            
        返回:
            bool: 更新是否成功
        """
        if component_id not in self.components:
            logger.error("Component %s not found for size update", component_id)
            return False
            
        component = self.components[component_id]
        old_size = component.size
        component.size = new_size
        
        logger.info("Updated %s size from (%.2f,%.2f,%.2f) to (%.2f,%.2f,%.2f)",
                   component_id, old_size.x, old_size.y, old_size.z,
                   new_size.x, new_size.y, new_size.z)
        
        # 触发约束传播
        self._propagate_constraint_change(component_id)
        return True


def main():
    """使用示例：模拟螺栓-螺母装配"""
    # 创建模拟器实例
    simulator = ConstraintSimulator(tolerance=0.05)
    
    # 添加组件
    bolt = Component(
        id="bolt_001",
        name="M8x40 Hex Bolt",
        position=Vector3D(0, 0, 0),
        size=Vector3D(8, 8, 40),
        is_flexible=False  # 螺栓固定
    )
    
    washer = Component(
        id="washer_001",
        name="M8 Washer",
        position=Vector3D(0, 0, 42),  # 初始位置在螺栓上方
        size=Vector3D(16, 16, 2),
        is_flexible=True
    )
    
    nut = Component(
        id="nut_001",
        name="M8 Hex Nut",
        position=Vector3D(0, 0, 45),
        size=Vector3D(13, 13, 8),
        is_flexible=True
    )
    
    # 添加到模拟器
    simulator.add_component(bolt)
    simulator.add_component(washer)
    simulator.add_component(nut)
    
    # 添加约束
    constraint1 = Constraint(
        id="const_001",
        type=ConstraintType.DISTANCE,
        source_id="bolt_001",
        target_id="washer_001",
        value=41.0,  # 螺栓头到垫圈的期望距离
        tolerance=0.5
    )
    
    constraint2 = Constraint(
        id="const_002",
        type=ConstraintType.DISTANCE,
        source_id="washer_001",
        target_id="nut_001",
        value=2.0,  # 垫圈到螺母的间隙
        tolerance=0.2
    )
    
    simulator.add_constraint(constraint1)
    simulator.add_constraint(constraint2)
    
    # 执行模拟
    result = simulator.simulate_assembly()
    
    # 输出结果
    print("\n=== Simulation Results ===")
    print(f"Converged: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print("\nFinal Positions:")
    for comp_id, pos in result['final_positions'].items():
        print(f"  {comp_id}: x={pos[0]:.2f}, y={pos[1]:.2f}, z={pos[2]:.2f}")
    
    if result['warnings']:
        print("\n=== Warnings ===")
        for warning in result['warnings']:
            print(f"  {warning.component_id}: {warning.suggested_fix}")
    
    # 演示设计变更：修改螺母尺寸
    print("\n=== Design Change: Nut size increased ===")
    simulator.update_component_size("nut_001", Vector3D(14, 14, 9))
    
    # 重新模拟
    result2 = simulator.simulate_assembly()
    print(f"Re-simulation converged: {result2['success']}")


if __name__ == "__main__":
    main()