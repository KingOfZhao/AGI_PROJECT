"""
embodied-vision/simulation — 2D物理仿真引擎

纯Python实现(无PyBullet/MuJoCo依赖):
- 2D刚体物理(重力/碰撞/摩擦)
- 桌面场景(桌子+物体+机器人)
- 视觉仿真(虚拟相机渲染)
- 抓取模拟(夹爪物理)
"""

import numpy as np
import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import json


# ═══════════════════════════════════════════
# 2D物理引擎
# ═══════════════════════════════════════════

@dataclass
class Body2D:
    """2D刚体"""
    id: int
    name: str
    x: float; y: float  # 中心位置
    vx: float = 0.0; vy: float = 0.0  # 速度
    angle: float = 0.0  # 旋转角度
    omega: float = 0.0  # 角速度
    width: float = 50.0; height: float = 50.0  # 尺寸
    mass: float = 1.0
    static: bool = False  # 静态物体(不受力)
    friction: float = 0.5
    restitution: float = 0.3  # 弹性系数
    color: Tuple[int, int, int] = (128, 128, 128)
    body_type: str = "box"  # box/circle/gripper
    
    @property
    def left(self): return self.x - self.width / 2
    @property
    def right(self): return self.x + self.width / 2
    @property
    def top(self): return self.y - self.height / 2  # y轴向下
    @property
    def bottom(self): return self.y + self.height / 2
    
    def aabb(self):
        return (self.left, self.top, self.right, self.bottom)
    
    def contains(self, px: float, py: float) -> bool:
        return (self.left <= px <= self.right and 
                self.top <= py <= self.bottom)


class Physics2D:
    """简单2D物理引擎"""
    
    def __init__(self, gravity: float = 980.0, dt: float = 1.0/60.0):
        self.gravity = gravity
        self.dt = dt
        self.bodies: Dict[int, Body2D] = {}
        self.next_id = 0
        self.time = 0.0
    
    def add_body(self, name: str, x: float, y: float, 
                 width: float = 50, height: float = 50,
                 mass: float = 1.0, static: bool = False,
                 color: Tuple[int, int, int] = (128, 128, 128),
                 body_type: str = "box") -> Body2D:
        body = Body2D(
            id=self.next_id, name=name, x=x, y=y,
            width=width, height=height, mass=mass,
            static=static, color=color, body_type=body_type
        )
        self.bodies[body.id] = body
        self.next_id += 1
        return body
    
    def step(self, n_steps: int = 1):
        """模拟n步"""
        for _ in range(n_steps):
            for body in self.bodies.values():
                if body.static:
                    continue
                
                # 重力
                body.vy += self.gravity * self.dt
                
                # 摩擦(简化: 速度衰减)
                body.vx *= (1 - body.friction * self.dt)
                body.omega *= (1 - body.friction * self.dt * 2)
                
                # 更新位置
                body.x += body.vx * self.dt
                body.y += body.vy * self.dt
                body.angle += body.omega * self.dt
            
            # 碰撞检测与响应
            self._resolve_collisions()
            self.time += self.dt
    
    def _resolve_collisions(self):
        """AABB碰撞检测与响应"""
        bodies = list(self.bodies.values())
        for i in range(len(bodies)):
            for j in range(i+1, len(bodies)):
                a, b = bodies[i], bodies[j]
                self._check_collision(a, b)
    
    def _check_collision(self, a: Body2D, b: Body2D):
        """检测并解决两个物体间的碰撞"""
        # AABB重叠
        if (a.right < b.left or a.left > b.right or
            a.bottom < b.top or a.top > b.bottom):
            return  # 无碰撞
        
        # 计算重叠
        overlap_x = min(a.right, b.right) - max(a.left, b.left)
        overlap_y = min(a.bottom, b.bottom) - max(a.top, b.top)
        
        if a.static and b.static:
            return
        
        # 选择最小穿透轴分离
        if overlap_x < overlap_y:
            # 水平分离
            if a.x < b.x:
                sep = -overlap_x
            else:
                sep = overlap_x
            
            if a.static:
                b.x -= sep
                a.vx, b.vx = 0, 0
            elif b.static:
                a.x += sep
                a.vx, b.vx = 0, 0
            else:
                a.x += sep / 2
                b.x -= sep / 2
                a.vx, b.vx = b.vx * b.restitution, a.vx * a.restitution
        else:
            # 垂直分离
            if a.y < b.y:
                sep = -overlap_y
            else:
                sep = overlap_y
            
            if a.static:
                b.y -= sep
                b.vy = 0  # 落地停止
            elif b.static:
                a.y += sep
                a.vy = 0
            else:
                a.y += sep / 2
                b.y -= sep / 2
                a.vy, b.vy = b.vy * b.restitution, a.vy * a.restitution
    
    def get_state(self) -> Dict:
        """获取当前状态"""
        return {
            "time": self.time,
            "bodies": {
                b.name: {"x": b.x, "y": b.y, "vx": b.vx, "vy": b.vy,
                          "angle": b.angle, "type": b.body_type}
                for b in self.bodies.values()
            }
        }


# ═══════════════════════════════════════════
# 仿真场景
# ═══════════════════════════════════════════

class TableScene:
    """桌面场景: 桌子 + 物体"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.physics = Physics2D()
        self.robot_x = width // 2
        self.robot_y = height // 2
        self.gripper_open = True
        self.gripper_target: Optional[Body2D] = None
        
        self._setup_scene()
    
    def _setup_scene(self):
        """设置桌面场景"""
        # 地面
        self.physics.add_body("ground", self.width/2, self.height - 10,
                              self.width, 20, static=True, color=(100, 80, 60))
        # 桌子
        self.physics.add_body("table", self.width/2, self.height - 60,
                              self.width - 100, 80, static=True, color=(139, 90, 43))
    
    def add_object(self, name: str, x: float, y: float,
                   width: float = 40, height: float = 40,
                   color: Tuple[int, int, int] = (200, 50, 50)) -> Body2D:
        """在桌面上添加物体"""
        body = self.physics.add_body(name, x, y, width, height,
                                     color=color, body_type="object")
        return body
    
    def add_random_objects(self, n: int = 5):
        """添加随机物体"""
        np.random.seed(42)
        colors = [(200,50,50), (50,50,200), (50,200,50), 
                  (200,200,50), (200,50,200), (50,200,200)]
        for i in range(n):
            x = np.random.uniform(100, self.width - 100)
            y = np.random.uniform(100, self.height - 150)
            w = np.random.uniform(25, 60)
            h = np.random.uniform(25, 60)
            color = colors[i % len(colors)]
            self.add_object(f"obj_{i}", x, y, w, h, color)
    
    def simulate(self, steps: int = 120) -> Dict:
        """运行仿真"""
        self.physics.step(steps)
        return self.physics.get_state()
    
    def get_virtual_image(self) -> np.ndarray:
        """渲染虚拟相机图像(用于视觉算法测试)"""
        import cv2
        
        img = np.ones((self.height, self.width, 3), dtype=np.uint8) * 240
        # 桌面背景
        table = self.physics.bodies.get(1)
        if table:
            cv2.rectangle(img, 
                         (int(table.left), int(table.top)),
                         (int(table.right), int(table.bottom)),
                         table.color, -1)
        
        # 物体
        for body in self.physics.bodies.values():
            if body.body_type in ("ground", "table"):
                continue
            x1, y1 = int(body.left), int(body.top)
            x2, y2 = int(body.right), int(body.bottom)
            cv2.rectangle(img, (x1, y1), (x2, y2), body.color, -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), 1)
            cv2.putText(img, body.name, (x1+2, y1+15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)
        
        # 机器人(十字标记)
        cv2.drawMarker(img, (int(self.robot_x), int(self.robot_y)), (0, 0, 255),
                       cv2.MARKER_CROSS, 20, 2)
        cv2.circle(img, (int(self.robot_x), int(self.robot_y)), 5, (0, 0, 255), -1)
        
        return img
    
    def get_virtual_depth(self) -> np.ndarray:
        """生成虚拟深度图"""
        depth = np.ones((self.height, self.width), dtype=np.float32) * 5000
        
        for body in self.physics.bodies.values():
            x1, y1 = int(max(0, body.left)), int(max(0, body.top))
            x2, y2 = int(min(self.width, body.right)), int(min(self.height, body.bottom))
            if body.body_type == "ground":
                depth[y1:y2, x1:x2] = 500  # 近
            elif body.body_type == "table":
                depth[y1:y2, x1:x2] = 400
            elif body.body_type == "object":
                depth[y1:y2, x1:x2] = 300  # 物体最近
        
        return depth


class GripperController:
    """夹爪控制器"""
    
    def __init__(self, scene: TableScene):
        self.scene = scene
        self.state = "idle"  # idle/moving/grasping/lifting/placing/releasing
        self.grabbed: Optional[Body2D] = None
        self.target_pos: Optional[Tuple[float, float]] = None
        self.speed: float = 200.0  # px/s
    
    def move_to(self, x: float, y: float):
        """移动到位置"""
        self.target_pos = (x, y)
        self.state = "moving"
    
    def grasp(self):
        """在当前位置抓取"""
        self.state = "grasping"
    
    def release(self):
        """释放"""
        self.state = "releasing"
    
    def update(self, dt: float = 1.0/60.0):
        """更新夹爪状态"""
        scene = self.scene
        
        if self.state == "moving" and self.target_pos:
            tx, ty = self.target_pos
            dx = tx - scene.robot_x
            dy = ty - scene.robot_y
            dist = math.sqrt(dx**2 + dy**2)
            
            if dist < 5:
                scene.robot_x, scene.robot_y = tx, ty
                self.state = "idle"
            else:
                speed = min(self.speed * dt, dist)
                scene.robot_x += dx / dist * speed
                scene.robot_y += dy / dist * speed
        
        elif self.state == "grasping":
            # 检查夹爪范围内是否有物体
            for body in scene.physics.bodies.values():
                if body.body_type != "object" or body.static:
                    continue
                if body.contains(scene.robot_x, scene.robot_y):
                    self.grabbed = body
                    self.state = "idle"
                    return
            self.state = "idle"  # 没有抓到
        
        elif self.state == "releasing" and self.grabbed:
            self.grabbed = None
            self.state = "idle"


class PickAndPlaceDemo:
    """Pick and Place 演示"""
    
    def __init__(self):
        self.scene = TableScene()
        self.gripper = GripperController(self.scene)
        
        # 添加物体
        self.scene.add_object("red_box", 200, 300, 45, 45, (200, 50, 50))
        self.scene.add_object("blue_box", 500, 280, 35, 55, (50, 50, 200))
        self.scene.add_object("green_cyl", 350, 350, 50, 50, (50, 200, 50))
        
        # 让物体落下
        self.scene.simulate(60)
    
    def run(self, n_steps: int = 300) -> List[np.ndarray]:
        """运行demo, 返回每帧的虚拟图像"""
        import cv2
        frames = []
        
        # Phase 1: 移动到红色方块上方
        red = self.scene.physics.bodies.get(2)  # ground=0, table=1, obj=2
        if red:
            self.gripper.move_to(red.x, red.y - 30)
        
        for step in range(n_steps):
            self.gripper.update()
            self.scene.physics.step(1)
            
            # 如果到达目标且还没抓
            if (self.gripper.state == "idle" and 
                self.gripper.grabbed is None and step < 100):
                self.gripper.grasp()
            
            # 抓到后移动到目标位置
            if (self.gripper.grabbed is not None and 
                self.gripper.state == "idle" and step > 100):
                self.gripper.move_to(600, 300)
                # 移动到位后释放
                if abs(self.scene.robot_x - 600) < 10:
                    self.gripper.release()
            
            # 抓取后物体跟随夹爪
            if self.gripper.grabbed:
                self.gripper.grabbed.x = self.scene.robot_x
                self.gripper.grabbed.y = self.scene.robot_y
                self.gripper.grabbed.vx = 0
                self.gripper.grabbed.vy = 0
            
            # 每5帧渲染一次
            if step % 5 == 0:
                frames.append(self.scene.get_virtual_image())
        
        return frames


if __name__ == "__main__":
    import cv2
    
    print("=== 2D物理仿真演示 ===\n")
    
    demo = PickAndPlaceDemo()
    frames = demo.run(300)
    
    print(f"仿真完成: {len(frames)} 帧")
    print(f"最终状态:")
    state = demo.scene.physics.get_state()
    for name, body in state["bodies"].items():
        print(f"  {name}: pos=({body['x']:.0f}, {body['y']:.0f})")
    
    # 保存首帧和末帧
    if frames:
        cv2.imwrite("/tmp/sim_first_frame.png", frames[0])
        cv2.imwrite("/tmp/sim_last_frame.png", frames[-1])
        print(f"\n首帧保存: /tmp/sim_first_frame.png")
        print(f"末帧保存: /tmp/sim_last_frame.png")
    
    # 简单碰撞测试
    print(f"\n=== 碰撞测试 ===")
    p = Physics2D()
    ground = p.add_body("ground", 400, 590, 800, 20, static=True)
    ball = p.add_body("ball", 400, 100, 30, 30, mass=1.0)
    ball.vy = 0
    
    for i in range(180):
        p.step()
        if i % 30 == 0:
            print(f"  t={p.time:.2f}s ball: y={ball.y:.1f} vy={ball.vy:.1f}")
    
    print(f"\n✅ 仿真测试完成")
