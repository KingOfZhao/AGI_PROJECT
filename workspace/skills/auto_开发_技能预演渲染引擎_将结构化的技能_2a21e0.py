"""
技能预演渲染引擎

本模块实现了AGI系统中的‘技能预演渲染引擎’，负责将结构化的技能节点数据
转化为简化的2D物理仿真动画。该模块形成了‘感知-数字化-预演-修正’闭环中的
关键‘预演’环节，允许系统在执行真实动作前评估技能的物理可行性和结果。

主要功能:
- 解析结构化的技能节点数据 (JSON/Dict)
- 构建简化的物理仿真环境 (含重力和碰撞)
- 渲染并生成预演轨迹数据
- 验证输入数据的完整性和边界安全性

作者: AGI System Core Engineer
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import math
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ObjectType(Enum):
    """仿真对象类型枚举"""
    SPHERE = "sphere"
    CUBE = "cube"
    GROUND = "ground"

@dataclass
class PhysicsObject:
    """物理仿真对象的数据结构"""
    id: str
    type: ObjectType
    mass: float  # kg
    position: List[float]  # [x, y, z] in meters
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: Dict[str, float] = field(default_factory=lambda: {"radius": 0.5}) # size params

    def __post_init__(self):
        """数据验证"""
        if self.mass <= 0:
            raise ValueError(f"Mass must be positive, got {self.mass}")
        if len(self.position) != 3:
            raise ValueError("Position must be a list of 3 coordinates [x, y, z]")

@dataclass
class SimulationResult:
    """仿真结果数据结构"""
    success: bool
    message: str
    trajectory: List[Dict[str, Any]]  # 记录每一帧的关键状态
    final_state: Optional[Dict[str, Any]] = None

class PreRenderEngine:
    """
    技能预演渲染引擎核心类。
    
    负责维护仿真状态，处理物理计算逻辑，并生成预演数据。
    """

    def __init__(self, gravity: float = -9.81, time_step: float = 0.02, ground_level: float = 0.0):
        """
        初始化引擎。
        
        Args:
            gravity (float): 重力加速度 (m/s^2)，默认为地球重力。
            time_step (float): 仿真时间步长 (秒)。
            ground_level (float): 地面高度 (m)。
        """
        self.gravity = gravity
        self.time_step = time_step
        self.ground_level = ground_level
        self.objects: Dict[str, PhysicsObject] = {}
        logger.info(f"PreRenderEngine initialized with gravity={gravity}, dt={time_step}")

    def _validate_skill_node(self, skill_node: Dict[str, Any]) -> bool:
        """
        辅助函数：验证输入的技能节点数据结构是否合法。
        
        Args:
            skill_node (Dict): 输入的技能数据节点。
            
        Returns:
            bool: 如果数据有效返回 True，否则抛出 ValueError。
            
        Raises:
            ValueError: 当数据缺失关键字段或数据类型不匹配时。
        """
        if not isinstance(skill_node, dict):
            raise TypeError("Skill node must be a dictionary.")
        
        required_fields = ["id", "parameters"]
        for field in required_fields:
            if field not in skill_node:
                raise ValueError(f"Missing required field: {field}")
                
        params = skill_node.get("parameters", {})
        if "mass" not in params or "initial_pos" not in params:
            raise ValueError("Parameters must include 'mass' and 'initial_pos'")
            
        # 边界检查
        if not (0.1 <= params["mass"] <= 1000):
            logger.warning(f"Unusual mass value detected: {params['mass']}")
            
        return True

    def load_skill_to_object(self, skill_node: Dict[str, Any]) -> str:
        """
        核心函数 1: 将结构化技能数据解析并加载为物理对象。
        
        Args:
            skill_node (Dict): 包含技能参数的字典，例如:
                {
                    "id": "throw_ball_01",
                    "parameters": {
                        "mass": 1.0,
                        "initial_pos": [0, 10, 0],
                        "initial_vel": [5, 10, 0],
                        "type": "sphere"
                    }
                }
                
        Returns:
            str: 创建的物理对象 ID。
        """
        try:
            self._validate_skill_node(skill_node)
            
            obj_id = skill_node["id"]
            params = skill_node["parameters"]
            
            # 解析类型
            obj_type_str = params.get("type", "sphere").upper()
            try:
                obj_type = ObjectType[obj_type_str]
            except KeyError:
                logger.warning(f"Unknown object type {obj_type_str}, defaulting to SPHERE")
                obj_type = ObjectType.SPHERE
            
            # 创建对象
            phys_obj = PhysicsObject(
                id=obj_id,
                type=obj_type,
                mass=params["mass"],
                position=params["initial_pos"],
                velocity=params.get("initial_vel", [0.0, 0.0, 0.0])
            )
            
            self.objects[obj_id] = phys_obj
            logger.info(f"Successfully loaded skill node as object: {obj_id}")
            return obj_id
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to load skill node: {e}")
            raise

    def simulate_step(self, obj: PhysicsObject) -> None:
        """
        辅助函数：对单个对象进行单步物理模拟。
        包含重力和地面碰撞检测。
        """
        # 1. 应用重力
        # v = v0 + a*t
        obj.velocity[1] += self.gravity * self.time_step
        
        # 2. 更新位置
        # p = p0 + v*t
        obj.position[0] += obj.velocity[0] * self.time_step
        obj.position[1] += obj.velocity[1] * self.time_step
        obj.position[2] += obj.velocity[2] * self.time_step
        
        # 3. 地面碰撞检测
        # 假设物体是一个质点或球体，当Y坐标低于地面时反弹
        radius = obj.size.get("radius", 0.5)
        if obj.position[1] - radius < self.ground_level:
            obj.position[1] = self.ground_level + radius
            # 能量损失系数 (恢复系数)
            restitution = 0.6
            obj.velocity[1] = -obj.velocity[1] * restitution
            obj.velocity[0] *= 0.9 # 摩擦力
            obj.velocity[2] *= 0.9
            
            # 如果速度很小，停止运动
            if abs(obj.velocity[1]) < 0.1:
                obj.velocity[1] = 0.0

    def run_simulation(self, object_id: str, duration: float = 5.0) -> SimulationResult:
        """
        核心函数 2: 运行指定时长的物理仿真并生成轨迹。
        
        Args:
            object_id (str): 要模拟的对象 ID。
            duration (float): 仿真持续时间 (秒)。
            
        Returns:
            SimulationResult: 包含轨迹数据和最终状态的结果对象。
        """
        if object_id not in self.objects:
            logger.error(f"Object ID {object_id} not found in engine.")
            return SimulationResult(success=False, message="Object not found", trajectory=[])
            
        obj = self.objects[object_id]
        total_steps = int(duration / self.time_step)
        trajectory_data = []
        
        logger.info(f"Starting simulation for {object_id} over {duration}s ({total_steps} steps)")
        
        try:
            for step in range(total_steps):
                # 记录当前状态
                frame_data = {
                    "time": round(step * self.time_step, 3),
                    "pos": obj.position.copy(),
                    "vel": obj.velocity.copy()
                }
                trajectory_data.append(frame_data)
                
                # 执行模拟步
                self.simulate_step(obj)
                
                # 稳定性检查 (防止飞出场景)
                if any(abs(p) > 1000 for p in obj.position):
                     raise RuntimeError("Object escaped simulation boundaries")

            final_state = {
                "position": obj.position.copy(),
                "velocity": obj.velocity.copy(),
                "is_resting": all(abs(v) < 0.1 for v in obj.velocity)
            }
            
            logger.info("Simulation completed successfully.")
            return SimulationResult(
                success=True,
                message="Simulation finished",
                trajectory=trajectory_data,
                final_state=final_state
            )
            
        except Exception as e:
            logger.error(f"Simulation crashed: {e}")
            return SimulationResult(success=False, message=str(e), trajectory=trajectory_data)

# 使用示例
if __name__ == "__main__":
    # 1. 实例化引擎
    engine = PreRenderEngine(gravity=-9.8, time_step=0.05)
    
    # 2. 定义输入的技能数据 (模拟抛物线运动)
    skill_input = {
        "id": "projectile_test_01",
        "type": "action",
        "parameters": {
            "mass": 0.5,
            "initial_pos": [0, 0, 0],
            "initial_vel": [10.0, 15.0, 0.0], # 45度角抛出
            "type": "sphere"
        }
    }
    
    try:
        # 3. 加载技能
        obj_id = engine.load_skill_to_object(skill_input)
        
        # 4. 运行预演
        result = engine.run_simulation(obj_id, duration=3.0)
        
        # 5. 输出结果摘要
        if result.success:
            print(f"Simulation Success! Total Frames: {len(result.trajectory)}")
            print(f"Final Position: {result.final_state['position']}")
            print(f"First 3 frames: {json.dumps(result.trajectory[:3], indent=2)}")
        else:
            print(f"Simulation Failed: {result.message}")
            
    except Exception as e:
        print(f"Engine Error: {e}")