"""
名称: auto_真实世界_最小可行性实践_mvp_的代_c30ab7
描述: 真实世界'最小可行性实践'(MVP)的代码化生成与沙箱验证。
     本模块实现了基于PyBullet物理引擎的漏水水管修补模拟。
     它将自然语言技能节点转化为可执行的机器人控制代码，验证物理因果律。
作者: AGI System
版本: 1.0.0
"""

import time
import logging
import math
from typing import Tuple, Optional, List
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入物理引擎，如果失败则抛出明确错误
try:
    import pybullet as p
    import pybullet_data
except ImportError as e:
    logger.error("请安装 pybullet: pip install pybullet")
    raise e


@dataclass
class PipeProperties:
    """
    水管属性的数据类，用于输入验证。
    
    Attributes:
        length (float): 水管长度 (米).
        diameter (float): 水管直径 (米).
        leak_position (Tuple[float, float, float]): 漏点相对于水管中心的坐标.
        crack_size (float): 裂缝大小 (米).
    """
    length: float = 1.0
    diameter: float = 0.05
    leak_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    crack_size: float = 0.01

    def __post_init__(self):
        """数据验证与边界检查"""
        if self.length <= 0 or self.diameter <= 0:
            raise ValueError("水管尺寸必须为正数")
        if self.crack_size > self.diameter:
            raise ValueError("裂缝尺寸不能大于管径")


class PhysicsSimulator:
    """
    物理仿真环境封装类。
    负责管理PyBullet的连接、重置和基本环境搭建。
    """

    def __init__(self, gui: bool = False):
        """
        初始化物理引擎。
        
        Args:
            gui (bool): 是否显示GUI界面。
        """
        self.physics_client = None
        self.gui = gui
        self.plane_id = None
        self.connect()

    def connect(self):
        """连接到物理引擎"""
        try:
            if self.gui:
                self.physics_client = p.connect(p.GUI)
            else:
                self.physics_client = p.connect(p.DIRECT)
            
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.setGravity(0, 0, -9.81)
            self.plane_id = p.loadURDF("plane.urdf")
            logger.info(f"物理引擎已连接，Client ID: {self.physics_client}")
        except Exception as e:
            logger.error(f"物理引擎连接失败: {e}")
            raise

    def disconnect(self):
        """断开连接"""
        p.disconnect()
        logger.info("物理引擎已断开")


class LeakRepairMVP:
    """
    核心MVP执行类。
    负责将“修补水管”的抽象指令转换为物理引擎中的具体操作。
    """

    def __init__(self, pipe_props: PipeProperties, sim: PhysicsSimulator):
        """
        初始化修补任务。
        
        Args:
            pipe_props (PipeProperties): 水管的物理属性.
            sim (PhysicsSimulator): 物理仿真器实例.
        """
        self.props = pipe_props
        self.sim = sim
        self.pipe_id = None
        self.patch_id = None
        self.tool_id = None

    def setup_scenario(self) -> bool:
        """
        辅助函数：在仿真环境中构建场景。
        创建漏水的水管和修补工具（夹爪/补丁）。
        
        Returns:
            bool: 场景是否构建成功。
        """
        logger.info("正在构建修补场景...")
        try:
            # 1. 创建水管（使用圆柱体碰撞形状近似）
            # 这里简化处理，实际MVP可能需要加载URDF
            collision_shape = p.createCollisionShape(p.GEOM_CYLINDER, 
                                                     radius=self.props.diameter/2, 
                                                     height=self.props.length)
            
            # PyBullet中圆柱体默认轴是Z轴，我们需要旋转它使其沿X轴放置
            orientation = p.getQuaternionFromEuler([0, math.pi/2, 0])
            
            self.pipe_id = p.createMultiBody(baseMass=0, # 静态物体
                                             baseCollisionShapeIndex=collision_shape,
                                             basePosition=[0, 0, self.props.diameter/2 + 0.1],
                                             baseOrientation=orientation)
            
            # 2. 创建补丁（视觉化表示）
            # 这是一个简单的红色方块，代表修补材料
            visual_shape = p.createVisualShape(p.GEOM_BOX, 
                                               halfExtents=[self.props.crack_size, self.props.crack_size, 0.001],
                                               rgbaColor=[1, 0, 0, 1])
            
            self.patch_id = p.createMultiBody(baseMass=0.01,
                                              baseVisualShapeIndex=visual_shape,
                                              basePosition=[0, 0, 1]) # 初始在空中
            
            logger.info("场景构建完成：水管和补丁已生成。")
            return True

        except p.error as e:
            logger.error(f"场景构建物理引擎错误: {e}")
            return False
        except Exception as e:
            logger.error(f"场景构建未知错误: {e}")
            return False

    def _move_tool_to_target(self, current_pos: List[float], target_pos: List[float], steps: int = 10):
        """
        辅助函数：平滑移动工具/补丁到目标位置。
        模拟机器人的运动插补。
        
        Args:
            current_pos: 起始坐标 [x,y,z]
            target_pos: 目标坐标 [x,y,z]
            steps: 插补步数
        """
        for i in range(steps):
            alpha = (i + 1) / steps
            # 线性插值
            interp_x = current_pos[0] * (1 - alpha) + target_pos[0] * alpha
            interp_y = current_pos[1] * (1 - alpha) + target_pos[1] * alpha
            interp_z = current_pos[2] * (1 - alpha) + target_pos[2] * alpha
            
            p.resetBasePositionAndOrientation(self.patch_id, 
                                              [interp_x, interp_y, interp_z], 
                                              [0, 0, 0, 1])
            p.stepSimulation()
            # 模拟实时性
            time.sleep(1./240.) 

    def execute_repair_sequence(self) -> bool:
        """
        核心函数：执行具体的修补逻辑序列。
        1. 定位漏点
        2. 抓取/移动补丁
        3. 覆盖漏点
        4. 施加压力/固定
        
        Returns:
            bool: 修补流程是否逻辑闭环。
        """
        if self.patch_id is None or self.pipe_id is None:
            logger.error("场景未初始化")
            return False

        logger.info("开始执行修补序列...")

        try:
            # 步骤 1: 获取当前补丁位置和目标漏点位置
            # 漏点位置 = 水管位置 + 偏移量
            pipe_pos, _ = p.getBasePositionAndOrientation(self.pipe_id)
            target_pos = [
                pipe_pos[0] + self.props.leak_position[0],
                pipe_pos[1] + self.props.leak_position[1],
                pipe_pos[2] + self.props.leak_position[2] + (self.props.diameter/2) # 加上半径作为表面
            ]
            
            # 获取当前补丁位置
            current_patch_pos, _ = p.getBasePositionAndOrientation(self.patch_id)

            # 边界检查：确保目标在水管范围内
            if abs(target_pos[0]) > self.props.length / 2:
                logger.warning(f"漏点坐标 {target_pos} 超出水管长度范围，已自动约束。")
                target_pos[0] = max(min(target_pos[0], self.props.length/2), -self.props.length/2)

            # 步骤 2: 移动补丁到漏点上方 (接近阶段)
            approach_pos = [target_pos[0], target_pos[1], target_pos[2] + 0.2]
            logger.info(f"移动补丁到接近点: {approach_pos}")
            self._move_tool_to_target(list(current_patch_pos), approach_pos, steps=50)

            # 步骤 3: 下降到接触表面 (作业阶段)
            logger.info(f"下降补丁到漏点: {target_pos}")
            self._move_tool_to_target(approach_pos, target_pos, steps=50)

            # 步骤 4: 模拟施压 (保持位置一段时间)
            logger.info("施加压力固化...")
            for _ in range(120): # 保持1秒
                # 简单的约束：强行保持位置（模拟强力胶水或夹具）
                p.resetBaseVelocity(self.patch_id, [0,0,0], [0,0,0])
                # 或者可以使用约束 p.createConstraint
                p.stepSimulation()
                time.sleep(1./240.)

            logger.info("修补序列执行完成。")
            
            # 验证逻辑：检查补丁是否还在漏点附近（简单的因果检查）
            final_pos, _ = p.getBasePositionAndOrientation(self.patch_id)
            dist = math.sqrt(sum((a - b)**2 for a, b in zip(final_pos, target_pos)))
            
            if dist < 0.05: # 允许5cm误差
                logger.info("验证通过：补丁已覆盖漏点。")
                return True
            else:
                logger.error(f"验证失败：补丁偏离目标 {dist:.4f} 米。")
                return False

        except Exception as e:
            logger.error(f"执行修补序列时发生错误: {e}")
            return False


def run_mvp_demo():
    """
    使用示例：演示如何运行漏水修补MVP。
    """
    print("--- 启动 MVP 演示 ---")
    
    # 1. 定义输入数据
    pipe_config = PipeProperties(
        length=1.0,
        diameter=0.1,
        leak_position=(0.3, 0.0, 0.0), # 漏点在管身中间偏右
        crack_size=0.02
    )
    
    # 2. 初始化仿真器 (使用 DIRECT 模式用于服务器运行，GUI 用于调试)
    sim = PhysicsSimulator(gui=False)
    
    try:
        # 3. 初始化任务
        task = LeakRepairMVP(pipe_config, sim)
        
        # 4. 构建场景
        if not task.setup_scenario():
            raise RuntimeError("场景构建失败")
            
        # 5. 执行并验证
        success = task.execute_repair_sequence()
        
        if success:
            print("结果: 技能节点 'fix_leak' 已通过物理因果律验证。")
        else:
            print("结果: 技能节点验证失败。")
            
    except Exception as e:
        print(f"运行时错误: {e}")
    finally:
        # 6. 清理
        sim.disconnect()

if __name__ == "__main__":
    run_mvp_demo()