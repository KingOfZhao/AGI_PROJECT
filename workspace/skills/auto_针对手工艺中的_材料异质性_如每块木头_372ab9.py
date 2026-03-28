"""
Module: adaptive_material_manipulation.py
Description: 针对#材料异质性#的高级技能模块。
             本模块构建了一个'动态参数自适应'系统，用于处理非均质材料（如天然木材、皮革）。
             核心逻辑不再是执行固定的G代码，而是基于实时传感器反馈（如阻力、密度反馈）
             动态调整机器人末端执行器的力度、进给速度和旋转速率。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptiveCraftSkill")


class MaterialType(Enum):
    """定义支持的异质材料类型"""
    SOFT_WOOD = "pine"
    HARD_WOOD = "oak"
    LEATHER = "leather"
    COMPOSITE = "carbon_fiber"


class ManipulationMode(Enum):
    """操作模式枚举"""
    ROUGHING = "roughing"   # 粗加工
    FINISHING = "finishing" # 精加工
    DETAILING = "detailing" # 细节处理


@dataclass
class SensorReading:
    """传感器实时读数数据结构"""
    timestamp: float
    resistance_force: float  # 当前受到的阻力
    density_variance: float   # 密度变化率 (0.0 - 1.0)
    vibration_level: float    # 振动水平 (Hz)

    def __post_init__(self):
        """数据边界检查与清洗"""
        if self.resistance_force < 0:
            logger.warning("Negative force detected, clamping to 0.0")
            self.resistance_force = 0.0
        if not (0.0 <= self.density_variance <= 1.0):
            logger.warning(f"Density variance {self.density_variance} out of bounds, clamping")
            self.density_variance = max(0.0, min(1.0, self.density_variance))


@dataclass
class SkillParameters:
    """技能执行参数"""
    cutting_depth: float = 2.0     # mm
    feed_rate: float = 150.0       # mm/min
    spindle_speed: int = 12000     # RPM
    max_force_limit: float = 10.0  # N (安全限制)


@dataclass
class MaterialProfile:
    """材料物理属性档案"""
    type: MaterialType
    base_density: float
    elasticity: float
    grain_uniformity: float  # 0.0 (完全随机) to 1.0 (完全均匀)


class AdaptiveController:
    """
    自适应控制器核心类。
    实现基于PID类似算法的实时参数调整，适应材料异质性。
    """

    def __init__(self, profile: MaterialProfile, mode: ManipulationMode):
        self.profile = profile
        self.mode = mode
        self.current_params = SkillParameters()
        self.history: List[SensorReading] = []
        self._initialize_parameters()
        logger.info(f"Controller initialized for {profile.type.value} in {mode.value} mode.")

    def _initialize_parameters(self):
        """根据材料类型初始化基础参数"""
        if self.profile.type == MaterialType.HARD_WOOD:
            self.current_params.feed_rate = 100.0
            self.current_params.spindle_speed = 16000
        elif self.profile.type == MaterialType.SOFT_WOOD:
            self.current_params.feed_rate = 200.0
            self.current_params.spindle_speed = 12000
        
        if self.mode == ManipulationMode.FINISHING:
            self.current_params.feed_rate *= 0.6
            self.current_params.cutting_depth *= 0.5

    def _calculate_dynamic_adjustment(self, reading: SensorReading) -> Tuple[float, float]:
        """
        辅助函数：计算动态调整增量。
        基于当前读数与历史趋势计算修正值。
        
        Args:
            reading (SensorReading): 当前传感器读数
            
        Returns:
            Tuple[float, float]: (速度调整因子, 力度调整因子)
        """
        # 基础反应：阻力大则减速
        # 归一化阻力：假设 10N 是当前最大预期阻力
        normalized_force = reading.resistance_force / self.current_params.max_force_limit
        
        # 异质性反应：如果密度变化剧烈（纹理变化点），需要进一步减速以防止过切
        heterogeneity_factor = 1.0 + (reading.density_variance * 2.0)
        
        # 计算目标速度因子 (0.5 - 1.2)
        # 阻力大或纹理变化大时，因子减小
        speed_factor = 1.0 - (normalized_force * heterogeneity_factor)
        speed_factor = max(0.3, min(1.2, speed_factor)) # Clamping
        
        # 计算目标力度/深度因子
        # 如果阻力突然增大，减小切削深度
        depth_factor = 1.0
        if normalized_force > 0.8:
            depth_factor = 0.8
        
        return speed_factor, depth_factor

    def update_skill_parameters(self, reading: SensorReading) -> SkillParameters:
        """
        核心函数：根据实时感知更新技能参数。
        
        Args:
            reading (SensorReading): 实时传感器数据
            
        Returns:
            SkillParameters: 更新后的控制参数
            
        Raises:
            ValueError: 如果读数数据无效
        """
        if not isinstance(reading, SensorReading):
            raise ValueError("Invalid sensor data format")

        # 记录历史用于趋势分析
        self.history.append(reading)
        if len(self.history) > 10:
            self.history.pop(0)

        # 获取调整因子
        speed_adj, depth_adj = self._calculate_dynamic_adjustment(reading)

        # 应用调整
        original_feed = self.current_params.feed_rate
        self.current_params.feed_rate *= speed_adj
        self.current_params.cutting_depth *= depth_adj
        
        # 安全边界检查
        if self.current_params.feed_rate < 20.0:
            logger.warning("Feed rate critically low, potential tool stuck.")
            self.current_params.feed_rate = 20.0
            
        logger.debug(f"Params updated: Feed {original_feed:.1f} -> {self.current_params.feed_rate:.1f}")
        
        return self.current_params

    def execute_tool_path_segment(self, segment_id: int):
        """
        核心函数：执行一段工具路径，带有自适应逻辑。
        模拟真实的机器人控制循环。
        """
        logger.info(f"--- Starting Path Segment {segment_id} ---")
        
        # 模拟循环：在实际硬件中这会是高频实时循环
        for i in range(5):
            # 1. 模拟获取传感器数据 (模拟木材纹理变化)
            # 假设在第3次循环遇到了硬节点
            force = 2.0 + (i * 0.5)
            density_var = 0.1
            if i == 3:
                force = 9.5  # 突发高阻力
                density_var = 0.9 # 高异质性
            
            current_reading = SensorReading(
                timestamp=time.time(),
                resistance_force=force,
                density_variance=density_var,
                vibration_level=50.0
            )
            
            # 2. 动态调整参数
            updated_params = self.update_skill_parameters(current_reading)
            
            # 3. 执行动作 (这里是伪代码，实际是发送指令给机器人驱动器)
            self._send_to_actuator(updated_params)
            
            time.sleep(0.1) # 模拟处理时间

    def _send_to_actuator(self, params: SkillParameters):
        """辅助函数：模拟发送指令给执行器"""
        logger.info(f"ACTUATOR CMD | Speed: {params.spindle_speed} RPM | "
                    f"Feed: {params.feed_rate:.2f} mm/min | "
                    f"Depth: {params.cutting_depth:.2f} mm")

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 定义材料档案 (例如：一块纹理不均匀的橡木)
    oak_profile = MaterialProfile(
        type=MaterialType.HARD_WOOD,
        base_density=0.75,
        elasticity=0.12,
        grain_uniformity=0.4 # 较低的均匀性意味着高异质性
    )

    # 2. 初始化控制器
    controller = AdaptiveController(profile=oak_profile, mode=ManipulationMode.ROUGHING)

    # 3. 执行任务
    try:
        # 执行一段加工路径
        controller.execute_tool_path_segment(segment_id=101)
        
        print("\n--- Simulation Complete ---")
        
    except Exception as e:
        logger.error(f"Critical failure during execution: {e}")