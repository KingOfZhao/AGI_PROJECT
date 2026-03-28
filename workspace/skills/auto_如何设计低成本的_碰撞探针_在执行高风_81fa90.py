"""
模块名称: low_cost_collision_probe.py
描述: 实现了一个基于轻量级几何与语义规则的“碰撞探针”仿真器。
      该模块旨在AGI决策流中，以极低的算力成本过滤掉必然失败的行动路径。
      它不依赖笨重的物理引擎或大型神经网络，而是使用解析解和启发式算法
      生成“足够真实”的碰撞反馈。
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CollisionProbe")

class ObstacleType(Enum):
    """障碍物类型枚举"""
    STATIC = 1    # 静态障碍（墙壁、固定物体）
    DYNAMIC = 2   # 动态障碍（人类、车辆）
    RESTRICTED = 3 # 逻辑禁区（ROI区域）

@dataclass
class Vector2D:
    """二维向量，用于表示位置和速度"""
    x: float
    y: float

    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x - other.x, self.y - other.y)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

@dataclass
class SimulatedObstacle:
    """仿真环境中的障碍物定义"""
    id: str
    position: Vector2D
    radius: float  # 使用圆形包围盒以简化计算
    type: ObstacleType
    velocity: Vector2D = field(default_factory=Vector2D) # 动态障碍物的速度

@dataclass
class AgentState:
    """AGI代理的状态"""
    position: Vector2D
    velocity: Vector2D
    bounding_radius: float
    planned_path: List[Vector2D] = field(default_factory=list)

@dataclass
class CollisionReport:
    """碰撞探测报告"""
    is_safe: bool
    collision_point: Optional[Vector2D]
    collision_obstacle_id: Optional[str]
    risk_level: float  # 0.0 (Safe) to 1.0 (Critical)
    message: str

class LowCostCollisionProbe:
    """
    低成本碰撞探针仿真器。
    
    使用轻量级的几何计算（圆-圆碰撞检测、射线投射）来验证路径可行性。
    包含针对动态障碍物的时间-空间预测。
    """

    def __init__(self, safety_margin: float = 0.1):
        """
        初始化探针。
        
        Args:
            safety_margin (float): 额外的安全膨胀系数，例如 0.1 表示半径膨胀10%。
        """
        self.safety_margin = safety_margin
        self.obstacles: Dict[str, SimulatedObstacle] = {}
        logger.info(f"CollisionProbe initialized with safety margin: {safety_margin}")

    def update_environment(self, obstacles: List[SimulatedObstacle]) -> None:
        """
        更新仿真环境中的障碍物列表。
        
        Args:
            obstacles (List[SimulatedObstacle]): 新的障碍物列表。
        """
        self.obstacles = {obs.id: obs for obs in obstacles}
        logger.debug(f"Environment updated with {len(obstacles)} obstacles.")

    def _check_circle_collision(
        self, 
        p1: Vector2D, r1: float, 
        p2: Vector2D, r2: float
    ) -> bool:
        """
        辅助函数：检测两个圆是否相交。
        
        Args:
            p1, p2: 圆心坐标
            r1, r2: 半径
            
        Returns:
            bool: 是否发生碰撞
        """
        dist_sq = (p1.x - p2.x)**2 + (p1.y - p2.y)**2
        radius_sum = r1 + r2
        return dist_sq <= radius_sum**2

    def predict_trajectory_risk(
        self, 
        agent_state: AgentState, 
        time_horizon: float = 2.0, 
        steps: int = 10
    ) -> CollisionReport:
        """
        核心函数1：基于当前状态预测未来一段时间内的碰撞风险。
        适用于动态环境预演。
        
        Args:
            agent_state (AgentState): 代理当前状态（包含瞬时速度）。
            time_horizon (float): 预测的时间长度（秒）。
            steps (int): 仿真离散步数。
            
        Returns:
            CollisionReport: 包含风险等级和碰撞信息的报告。
        """
        if not agent_state.velocity.magnitude() > 0:
            return CollisionReport(True, None, None, 0.0, "Agent is stationary.")

        dt = time_horizon / steps
        current_pos = agent_state.position
        agent_r = agent_state.bounding_radius * (1 + self.safety_margin)
        
        # 模拟运动轨迹
        for i in range(steps):
            # 简单的线性运动模型（可扩展为PID模型）
            future_pos = current_pos + Vector2D(
                agent_state.velocity.x * dt * i,
                agent_state.velocity.y * dt * i
            )
            
            for obs in self.obstacles.values():
                # 粗略预测动态障碍物位置
                obs_future_pos = obs.position + Vector2D(
                    obs.velocity.x * dt * i,
                    obs.velocity.y * dt * i
                )
                
                # 边界检查
                if obs.radius <= 0:
                    continue

                if self._check_circle_collision(future_pos, agent_r, obs_future_pos, obs.radius):
                    logger.warning(f"Collision predicted with {obs.id} at step {i}")
                    return CollisionReport(
                        is_safe=False,
                        collision_point=future_pos,
                        collision_obstacle_id=obs.id,
                        risk_level=0.9 if obs.type == ObstacleType.DYNAMIC else 0.7,
                        message=f"Dynamic collision predicted with {obs.id}"
                    )
        
        return CollisionReport(True, None, None, 0.0, "Trajectory clear.")

    def validate_planned_path(self, agent_state: AgentState) -> CollisionReport:
        """
        核心函数2：验证预定义的路径点序列是否安全。
        使用射线投射逻辑检测路径穿过障碍物的情况。
        
        Args:
            agent_state (AgentState): 包含 planned_path 的代理状态。
            
        Returns:
            CollisionReport: 路径验证报告。
        """
        if not agent_state.planned_path:
            return CollisionReport(False, None, None, 1.0, "Empty path provided.")

        current_pos = agent_state.position
        agent_r = agent_state.bounding_radius * (1 + self.safety_margin)

        for waypoint in agent_state.planned_path:
            # 检查路径段 (current_pos -> waypoint)
            # 简化：在路径段上采样多个点进行球体检测（比射线-圆相交解析法略慢但代码更健壮且易于维护）
            segment_vec = waypoint - current_pos
            segment_len = segment_vec.magnitude()
            
            if segment_len == 0:
                continue

            # 采样密度：每半个代理半径采样一次
            num_samples = max(2, int(segment_len / (agent_r / 2)))
            
            for s in range(num_samples + 1):
                t = s / num_samples
                sample_point = current_pos + Vector2D(
                    segment_vec.x * t,
                    segment_vec.y * t
                )
                
                for obs in self.obstacles.values():
                    if self._check_circle_collision(sample_point, agent_r, obs.position, obs.radius):
                        logger.warning(f"Path blocked by {obs.id}")
                        return CollisionReport(
                            is_safe=False,
                            collision_point=sample_point,
                            collision_obstacle_id=obs.id,
                            risk_level=1.0 if obs.type == ObstacleType.STATIC else 0.8,
                            message=f"Path intersects with obstacle {obs.id}"
                        )
            
            current_pos = waypoint

        return CollisionReport(True, None, None, 0.0, "Path validation successful.")

# 使用示例
if __name__ == "__main__":
    # 1. 初始化环境
    probe = LowCostCollisionProbe(safety_margin=0.15)
    
    # 2. 定义障碍物 (例如：一个静态墙和一个移动的人)
    obstacles = [
        SimulatedObstacle(
            id="wall_01", 
            position=Vector2D(5, 5), 
            radius=1.0, 
            type=ObstacleType.STATIC
        ),
        SimulatedObstacle(
            id="human_01", 
            position=Vector2D(10, 1), 
            radius=0.5, 
            type=ObstacleType.DYNAMIC,
            velocity=Vector2D(-0.5, 0.1) # 人正在向左移动
        )
    ]
    probe.update_environment(obstacles)

    # 3. 定义AGI代理状态
    # 场景A：直线运动预测
    agent = AgentState(
        position=Vector2D(0, 0),
        velocity=Vector2D(2.0, 2.0), # 向右上方快速移动
        bounding_radius=0.3
    )
    
    print("--- Scenario A: Velocity Prediction ---")
    report_a = probe.predict_trajectory_risk(agent, time_horizon=3.0)
    print(f"Result: {report_a.message}, Safe: {report_a.is_safe}")

    # 场景B：特定路径验证
    agent_path = AgentState(
        position=Vector2D(0, 0),
        velocity=Vector2D(0, 0),
        bounding_radius=0.3,
        planned_path=[Vector2D(3, 4), Vector2D(6, 6)] # 路径穿过 wall_01
    )
    
    print("\n--- Scenario B: Path Validation ---")
    report_b = probe.validate_planned_path(agent_path)
    print(f"Result: {report_b.message}, Safe: {report_b.is_safe}")