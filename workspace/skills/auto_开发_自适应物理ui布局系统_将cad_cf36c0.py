"""
自适应物理UI布局系统

该模块将CAD领域的'自由度分析'引入UI布局设计，实现基于物理模拟的自适应布局系统。
UI组件不仅响应屏幕尺寸变化，还能根据内容'质量'和'引力'进行物理模拟排列，
支持机械连接关系（如铰链、滑块）的联动效果。

典型应用场景：
- 可视化仪表盘设计
- 动态表单布局
- 交互式信息可视化

输入格式：
    组件数据: Dict[str, Component]  # 组件ID到组件属性的映射
    连接关系: List[Connection]      # 组件间的机械连接关系

输出格式：
    布局结果: Dict[str, Position]   # 组件ID到最终位置的映射
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """机械连接类型枚举"""
    HINGE = auto()      # 铰链连接 - 允许旋转
    SLIDER = auto()     # 滑块连接 - 允许线性移动
    FIXED = auto()      # 固定连接 - 不允许相对运动
    SPRING = auto()     # 弹簧连接 - 弹性连接


@dataclass
class Vector2D:
    """二维向量类，用于表示位置和方向"""
    x: float
    y: float
    
    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Vector2D':
        return Vector2D(self.x * scalar, self.y * scalar)
    
    def magnitude(self) -> float:
        """计算向量长度"""
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def normalize(self) -> 'Vector2D':
        """返回单位向量"""
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)


@dataclass
class Component:
    """UI组件数据类"""
    id: str
    mass: float = 1.0  # 内容质量，影响物理模拟
    position: Vector2D = field(default_factory=lambda: Vector2D(0, 0))
    velocity: Vector2D = field(default_factory=lambda: Vector2D(0, 0))
    size: Tuple[float, float] = (100, 100)  # 组件尺寸
    is_fixed: bool = False  # 是否固定位置
    damping: float = 0.1  # 阻尼系数
    
    def __post_init__(self):
        """数据验证和初始化后处理"""
        if self.mass <= 0:
            raise ValueError(f"组件 {self.id} 的质量必须为正数")
        if not (0 <= self.damping <= 1):
            logger.warning(f"组件 {self.id} 的阻尼系数 {self.damping} 超出推荐范围 [0, 1]")


@dataclass
class Connection:
    """组件间的机械连接关系"""
    source_id: str
    target_id: str
    connection_type: ConnectionType
    stiffness: float = 1.0  # 连接刚度
    rest_length: float = 0  # 自然长度
    damping: float = 0.1    # 连接阻尼
    
    def __post_init__(self):
        """验证连接参数"""
        if self.stiffness < 0:
            raise ValueError("刚度必须为非负数")
        if self.rest_length < 0:
            raise ValueError("自然长度必须为非负数")


@dataclass
class SimulationParams:
    """物理模拟参数"""
    gravity: float = 0.0  # 重力加速度
    time_step: float = 0.016  # 时间步长 (约60fps)
    iterations: int = 10  # 每帧迭代次数
    boundary_damping: float = 0.8  # 边界碰撞阻尼


class AdaptivePhysicsLayout:
    """
    自适应物理UI布局系统
    
    将CAD的自由度分析应用于UI布局，实现基于物理模拟的组件排列。
    
    示例:
        >>> layout_system = AdaptivePhysicsLayout()
        >>> layout_system.add_component("card1", mass=2.0, position=(100, 100))
        >>> layout_system.add_component("card2", mass=1.0, position=(300, 100))
        >>> layout_system.add_connection("card1", "card2", ConnectionType.SPRING)
        >>> layout_system.simulate()
        >>> positions = layout_system.get_positions()
    """
    
    def __init__(self, width: float = 800, height: float = 600):
        """
        初始化布局系统
        
        Args:
            width: 布局区域宽度
            height: 布局区域高度
        """
        self.width = width
        self.height = height
        self.components: Dict[str, Component] = {}
        self.connections: List[Connection] = []
        self.params = SimulationParams()
        self._is_initialized = False
        
        logger.info(f"初始化自适应物理布局系统，尺寸: {width}x{height}")
    
    def add_component(
        self,
        component_id: str,
        mass: float = 1.0,
        position: Tuple[float, float] = (0, 0),
        size: Tuple[float, float] = (100, 100),
        is_fixed: bool = False
    ) -> None:
        """
        添加UI组件到布局系统
        
        Args:
            component_id: 组件唯一标识符
            mass: 组件质量（影响物理行为）
            position: 初始位置
            size: 组件尺寸
            is_fixed: 是否固定位置
            
        Raises:
            ValueError: 如果组件ID已存在或参数无效
        """
        if component_id in self.components:
            raise ValueError(f"组件ID {component_id} 已存在")
        
        try:
            pos = Vector2D(position[0], position[1])
            component = Component(
                id=component_id,
                mass=mass,
                position=pos,
                size=size,
                is_fixed=is_fixed
            )
            self.components[component_id] = component
            logger.debug(f"添加组件: {component_id}, 质量: {mass}, 位置: {position}")
        except Exception as e:
            logger.error(f"添加组件 {component_id} 失败: {str(e)}")
            raise
    
    def add_connection(
        self,
        source_id: str,
        target_id: str,
        connection_type: ConnectionType,
        stiffness: float = 1.0,
        rest_length: Optional[float] = None
    ) -> None:
        """
        添加组件间的机械连接关系
        
        Args:
            source_id: 源组件ID
            target_id: 目标组件ID
            connection_type: 连接类型
            stiffness: 连接刚度
            rest_length: 自然长度（None表示自动计算当前距离）
            
        Raises:
            ValueError: 如果组件不存在或参数无效
        """
        if source_id not in self.components or target_id not in self.components:
            raise ValueError("源组件或目标组件不存在")
        
        if rest_length is None:
            # 自动计算当前距离作为自然长度
            source = self.components[source_id]
            target = self.components[target_id]
            delta = target.position - source.position
            rest_length = delta.magnitude()
        
        connection = Connection(
            source_id=source_id,
            target_id=target_id,
            connection_type=connection_type,
            stiffness=stiffness,
            rest_length=rest_length
        )
        
        self.connections.append(connection)
        logger.debug(f"添加连接: {source_id} -> {target_id}, 类型: {connection_type.name}")
    
    def _apply_constraints(self, component: Component) -> None:
        """
        应用边界约束（辅助函数）
        
        Args:
            component: 要约束的组件
        """
        # 边界检查
        half_width = component.size[0] / 2
        half_height = component.size[1] / 2
        
        # 左右边界
        if component.position.x < half_width:
            component.position.x = half_width
            component.velocity.x *= -self.params.boundary_damping
        elif component.position.x > self.width - half_width:
            component.position.x = self.width - half_width
            component.velocity.x *= -self.params.boundary_damping
        
        # 上下边界
        if component.position.y < half_height:
            component.position.y = half_height
            component.velocity.y *= -self.params.boundary_damping
        elif component.position.y > self.height - half_height:
            component.position.y = self.height - half_height
            component.velocity.y *= -self.params.boundary_damping
    
    def _calculate_connection_force(self, connection: Connection) -> Tuple[Vector2D, Vector2D]:
        """
        计算连接力（辅助函数）
        
        Args:
            connection: 连接关系
            
        Returns:
            作用在源组件和目标组件上的力
        """
        source = self.components[connection.source_id]
        target = self.components[connection.target_id]
        
        delta = target.position - source.position
        distance = delta.magnitude()
        
        if distance == 0:
            return Vector2D(0, 0), Vector2D(0, 0)
        
        # 计算弹簧力
        displacement = distance - connection.rest_length
        direction = delta.normalize()
        
        force_magnitude = connection.stiffness * displacement
        force = direction * force_magnitude
        
        # 根据连接类型调整力
        if connection.connection_type == ConnectionType.HINGE:
            # 铰链连接：只传递切向力
            # 这里简化处理，实际应考虑旋转自由度
            pass
        elif connection.connection_type == ConnectionType.SLIDER:
            # 滑块连接：只允许沿某一方向移动
            # 这里简化处理，实际应限制移动方向
            pass
        elif connection.connection_type == ConnectionType.FIXED:
            # 固定连接：强力保持相对位置
            force_magnitude *= 10  # 增加刚度
            force = direction * force_magnitude
        
        return force, force * -1
    
    def simulate(self, external_forces: Optional[Dict[str, Vector2D]] = None) -> None:
        """
        执行物理模拟，计算组件最终位置
        
        Args:
            external_forces: 外部力字典，键为组件ID，值为力向量
        """
        if not self.components:
            logger.warning("没有组件可供模拟")
            return
        
        logger.info("开始物理模拟...")
        
        for iteration in range(self.params.iterations):
            # 计算每个组件受到的力
            forces: Dict[str, Vector2D] = {comp_id: Vector2D(0, 0) for comp_id in self.components}
            
            # 添加重力
            if self.params.gravity != 0:
                for comp_id, force in forces.items():
                    forces[comp_id] = Vector2D(force.x, force.y + self.params.gravity * self.components[comp_id].mass)
            
            # 添加外部力
            if external_forces:
                for comp_id, ext_force in external_forces.items():
                    if comp_id in forces:
                        forces[comp_id] = forces[comp_id] + ext_force
            
            # 计算连接力
            for connection in self.connections:
                force_on_source, force_on_target = self._calculate_connection_force(connection)
                
                if connection.source_id in forces:
                    forces[connection.source_id] = forces[connection.source_id] + force_on_source
                if connection.target_id in forces:
                    forces[connection.target_id] = forces[connection.target_id] + force_on_target
            
            # 更新速度和位置
            for comp_id, component in self.components.items():
                if component.is_fixed:
                    continue
                
                # 计算加速度 (F = ma)
                acceleration = forces[comp_id] * (1.0 / component.mass)
                
                # 更新速度 (考虑阻尼)
                component.velocity = (component.velocity + acceleration * self.params.time_step) * (1 - component.damping)
                
                # 更新位置
                component.position = component.position + component.velocity * self.params.time_step
                
                # 应用边界约束
                self._apply_constraints(component)
        
        logger.info("物理模拟完成")
    
    def get_positions(self) -> Dict[str, Tuple[float, float]]:
        """
        获取所有组件的当前位置
        
        Returns:
            组件ID到位置的映射字典
        """
        return {
            comp_id: (comp.position.x, comp.position.y)
            for comp_id, comp in self.components.items()
        }
    
    def drag_component(self, component_id: str, target_position: Tuple[float, float]) -> None:
        """
        拖动组件到新位置，触发联动效果
        
        Args:
            component_id: 要拖动的组件ID
            target_position: 目标位置
            
        Raises:
            ValueError: 如果组件不存在或固定
        """
        if component_id not in self.components:
            raise ValueError(f"组件 {component_id} 不存在")
        
        component = self.components[component_id]
        if component.is_fixed:
            logger.warning(f"尝试拖动固定组件 {component_id}")
            return
        
        # 设置新位置并添加初始速度以产生联动效果
        new_pos = Vector2D(target_position[0], target_position[1])
        component.velocity = (new_pos - component.position) * 0.5  # 速度与移动距离相关
        component.position = new_pos
        
        logger.debug(f"拖动组件 {component_id} 到位置 {target_position}")
    
    def get_component_degrees_of_freedom(self, component_id: str) -> Dict[str, bool]:
        """
        分析组件的自由度（基于连接关系）
        
        Args:
            component_id: 组件ID
            
        Returns:
            自由度字典:
            {
                'translate_x': bool,
                'translate_y': bool,
                'rotate': bool
            }
        """
        if component_id not in self.components:
            raise ValueError(f"组件 {component_id} 不存在")
        
        component = self.components[component_id]
        if component.is_fixed:
            return {'translate_x': False, 'translate_y': False, 'rotate': False}
        
        # 初始自由度
        dofs = {'translate_x': True, 'translate_y': True, 'rotate': True}
        
        # 根据连接关系限制自由度
        for conn in self.connections:
            if conn.source_id == component_id or conn.target_id == component_id:
                if conn.connection_type == ConnectionType.FIXED:
                    return {'translate_x': False, 'translate_y': False, 'rotate': False}
                elif conn.connection_type == ConnectionType.SLIDER:
                    # 简化处理：滑块限制一个方向的移动
                    dofs['translate_y'] = False
                    dofs['rotate'] = False
                elif conn.connection_type == ConnectionType.HINGE:
                    # 铰链允许旋转但限制移动
                    dofs['translate_x'] = False
                    dofs['translate_y'] = False
        
        return dofs


# 使用示例
if __name__ == "__main__":
    # 创建布局系统
    layout = AdaptivePhysicsLayout(width=1200, height=800)
    
    # 添加组件
    layout.add_component("card1", mass=2.0, position=(200, 300), size=(150, 100))
    layout.add_component("card2", mass=1.5, position=(400, 300), size=(150, 100))
    layout.add_component("card3", mass=1.0, position=(300, 500), size=(200, 150))
    
    # 添加连接关系
    layout.add_connection("card1", "card2", ConnectionType.SPRING, stiffness=0.5)
    layout.add_connection("card2", "card3", ConnectionType.HINGE)
    
    # 分析自由度
    dofs = layout.get_component_degrees_of_freedom("card2")
    print(f"card2的自由度: {dofs}")
    
    # 模拟布局
    layout.simulate()
    
    # 获取结果
    positions = layout.get_positions()
    print("布局结果:")
    for comp_id, pos in positions.items():
        print(f"  {comp_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
    
    # 模拟拖动操作
    layout.drag_component("card1", (250, 350))
    layout.simulate()
    
    print("\n拖动后的布局:")
    new_positions = layout.get_positions()
    for comp_id, pos in new_positions.items():
        print(f"  {comp_id}: ({pos[0]:.1f}, {pos[1]:.1f})")