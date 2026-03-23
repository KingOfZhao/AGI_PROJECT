"""
跨领域系统：将CAD参数化约束与Flutter响应式状态结合
实现几何约束对象作为状态，根据约束逻辑自动解算空间位置
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import matplotlib.animation as animation
import numpy as np

@dataclass
class GeometricConstraint:
    """
    几何约束对象，封装CAD参数化约束逻辑
    属性:
        constraint_type: 约束类型 (distance, angle, parallel, etc.)
        entities: 约束涉及的实体ID列表
        parameters: 约束参数 (如距离值、角度值等)
        active: 约束是否激活
    """
    constraint_type: str
    entities: List[str]
    parameters: Dict[str, float]
    active: bool = True

    def apply_constraint(self, entities: Dict[str, 'GeometricEntity']) -> bool:
        """
        应用约束到几何实体
        返回: 约束是否成功应用
        """
        if not self.active or len(self.entities) < 2:
            return False
            
        try:
            entity1 = entities[self.entities[0]]
            entity2 = entities[self.entities[1]]
            
            if self.constraint_type == "distance":
                target_dist = self.parameters["distance"]
                current_dist = math.sqrt(
                    (entity1.x - entity2.x)**2 + 
                    (entity1.y - entity2.y)**2
                )
                # 调整位置以满足距离约束
                if abs(current_dist - target_dist) > 0.01:
                    scale = target_dist / current_dist
                    dx = (entity2.x - entity1.x) * scale
                    dy = (entity2.y - entity1.y) * scale
                    entity2.x = entity1.x + dx
                    entity2.y = entity1.y + dy
                    return True
                    
            elif self.constraint_type == "horizontal":
                # 水平对齐约束
                entity2.y = entity1.y
                return True
                
            elif self.constraint_type == "vertical":
                # 垂直对齐约束
                entity2.x = entity1.x
                return True
                
        except (KeyError, AttributeError) as e:
            print(f"约束应用错误: {e}")
            return False
        return False

@dataclass
class GeometricEntity:
    """
    几何实体类，表示UI组件的几何属性
    属性:
        id: 实体唯一标识符
        x: x坐标
        y: y坐标
        width: 宽度
        height: 高度
        rotation: 旋转角度(弧度)
    """
    id: str
    x: float
    y: float
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0

class FlutterResponsiveState:
    """
    Flutter响应式状态管理器
    结合几何约束对象实现描述即构建的动态工程图
    """
    
    def __init__(self):
        """初始化状态管理器"""
        self.entities: Dict[str, GeometricEntity] = {}
        self.constraints: List[GeometricConstraint] = []
        self.state_history: List[Dict] = []
        self._setup_visualization()
        
    def _setup_visualization(self):
        """设置可视化环境"""
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.ax.set_aspect('equal')
        self.ax.grid(True)
        self.ax.set_title("CAD参数化约束与Flutter响应式状态结合系统")
        
    def add_entity(self, entity: GeometricEntity) -> None:
        """
        添加几何实体到状态
        参数:
            entity: 几何实体对象
        """
        self.entities[entity.id] = entity
        self._update_visualization()
        
    def add_constraint(self, constraint: GeometricConstraint) -> None:
        """
        添加几何约束到状态
        参数:
            constraint: 几何约束对象
        """
        self.constraints.append(constraint)
        self._apply_all_constraints()
        self._update_visualization()
        
    def _apply_all_constraints(self) -> None:
        """应用所有激活的约束"""
        changed = True
        iterations = 0
        max_iterations = 100
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for constraint in self.constraints:
                if constraint.active:
                    if constraint.apply_constraint(self.entities):
                        changed = True
                        
        if iterations >= max_iterations:
            print("警告: 约束求解达到最大迭代次数，可能存在冲突约束")
            
    def update_entity(self, entity_id: str, **kwargs) -> None:
        """
        更新实体属性并触发约束重算
        参数:
            entity_id: 实体ID
            kwargs: 要更新的属性 (x, y, width, height, rotation)
        """
        if entity_id not in self.entities:
            raise ValueError(f"实体ID {entity_id} 不存在")
            
        entity = self.entities[entity_id]
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            else:
                print(f"警告: 实体 {entity_id} 没有属性 {key}")
                
        self._apply_all_constraints()
        self._update_visualization()
        self._save_state()
        
    def _update_visualization(self) -> None:
        """更新可视化显示"""
        self.ax.clear()
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.ax.set_aspect('equal')
        self.ax.grid(True)
        self.ax.set_title("CAD参数化约束与Flutter响应式状态结合系统")
        
        # 绘制所有实体
        for entity in self.entities.values():
            if entity.rotation == 0:
                rect = Rectangle(
                    (entity.x - entity.width/2, entity.y - entity.height/2),
                    entity.width, entity.height,
                    fill=True, alpha=0.7, edgecolor='black'
                )
                self.ax.add_patch(rect)
            else:
                # 简化处理：仅显示旋转中心
                circle = Circle((entity.x, entity.y), 0.2, 
                              fill=True, alpha=0.7, edgecolor='black')
                self.ax.add_patch(circle)
                
        # 绘制约束关系
        for constraint in self.constraints:
            if constraint.active and len(constraint.entities) >= 2:
                e1 = self.entities[constraint.entities[0]]
                e2 = self.entities[constraint.entities[1]]
                
                if constraint.constraint_type == "distance":
                    self.ax.plot([e1.x, e2.x], [e1.y, e2.y], 'r--', alpha=0.5)
                    mid_x = (e1.x + e2.x) / 2
                    mid_y = (e1.y + e2.y) / 2
                    self.ax.text(mid_x, mid_y, f"{constraint.parameters['distance']:.1f}", 
                               color='red', fontsize=8)
                elif constraint.constraint_type in ["horizontal", "vertical"]:
                    self.ax.plot([e1.x, e2.x], [e1.y, e2.y], 'g--', alpha=0.5)
                    
        plt.draw()
        plt.pause(0.1)
        
    def _save_state(self) -> None:
        """保存当前状态历史"""
        state = {
            'entities': {eid: vars(e) for eid, e in self.entities.items()},
            'constraints': [vars(c) for c in self.constraints]
        }
        self.state_history.append(state)
        
    def run_simulation(self, steps: int = 50) -> None:
        """
        运行动态模拟
        参数:
            steps: 模拟步数
        """
        plt.ion()
        
        # 创建动画
        def update(frame):
            # 模拟状态变化
            if 'rect1' in self.entities:
                self.update_entity(
                    'rect1',
                    x=5 * math.sin(frame * 0.1),
                    y=5 * math.cos(frame * 0.1)
                )
            return []
        
        ani = animation.FuncAnimation(
            self.fig, update, frames=steps,
            interval=100, blit=True, repeat=True
        )
        
        plt.show()
        plt.ioff()
        
        # 保持窗口打开
        input("按Enter键退出模拟...")

def main():
    """主函数：演示系统功能"""
    try:
        # 初始化状态管理器
        state_manager = FlutterResponsiveState()
        
        # 创建几何实体
        rect1 = GeometricEntity("rect1", x=0, y=0, width=2, height=1)
        rect2 = GeometricEntity("rect2", x=5, y=0, width=2, height=1)
        circle1 = GeometricEntity("circle1", x=0, y=5, width=1, height=1)
        
        # 添加实体到状态
        state_manager.add_entity(rect1)
        state_manager.add_entity(rect2)
        state_manager.add_entity(circle1)
        
        # 添加几何约束
        distance_constraint = GeometricConstraint(
            constraint_type="distance",
            entities=["rect1", "rect2"],
            parameters={"distance": 4.0}
        )
        
        horizontal_constraint = GeometricConstraint(
            constraint_type="horizontal",
            entities=["rect1", "circle1"],
            parameters={}
        )
        
        state_manager.add_constraint(distance_constraint)
        state_manager.add_constraint(horizontal_constraint)
        
        # 手动更新实体位置
        print("初始状态设置完成")
        state_manager.update_entity("rect1", x=3, y=2)
        
        # 运行动态模拟
        print("开始动态模拟...")
        state_manager.run_simulation()
        
    except Exception as e:
        print(f"系统运行错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()