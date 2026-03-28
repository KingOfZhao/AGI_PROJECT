"""
模块: anti_deception_cognitive_filter
名称: Auto 构建 抗欺骗认知滤波器

描述:
    本模块实现了'抗欺骗认知滤波器'，超越了传统物理噪声滤波器的范畴。
    传统滤波器仅关注信噪比（SNR）和数值平滑，而本模块引入了'逻辑连贯性检查'。
    
    核心机制:
    1. 传感器融合输入（多模态数据）。
    2. 构建临时'信念网'（Belief Network）。
    3. 当检测到数值异常时，不仅比较物理差异，还通过符号逻辑或概率图模型
       检查该读数与机器人其他感知（如视觉、听觉、物理常识）是否冲突。
    4. 如果读数导致系统'认知失调'（Cognitive Dissonance），即违背常识或
       跨模态一致性，即使信噪比很高，也被视为欺骗或故障并滤除。

领域: cross_domain (Robotics, Cybersecurity, AGI Logic)
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Cognitive_Filter")

@dataclass
class SensorReading:
    """
    单个传感器的读数数据结构。
    
    Attributes:
        sensor_id (str): 传感器唯一标识符。
        modality (str): 感知模态 (e.g., 'lidar', 'camera', 'odometry', 'proximity').
        value (float): 传感器读数值。
        timestamp (float): 时间戳。
        confidence (float): 传感器自身的置信度 (0.0 to 1.0)。
    """
    sensor_id: str
    modality: str
    value: float
    timestamp: float
    confidence: float

@dataclass
class WorldContext:
    """
    当前环境的上下文/常识库。
    
    Attributes:
        visual_obstacles (List[float]): 视觉系统检测到的障碍物距离列表。
        is_indoors (bool): 是否在室内（影响物理常识）。
        max_speed_limit (float): 当前允许的最大速度。
    """
    visual_obstacles: List[float]
    is_indoors: bool
    max_speed_limit: float

class CognitiveFilter:
    """
    抗欺骗认知滤波器核心类。
    
    实现了融合物理滤波与逻辑一致性检查的混合滤波算法。
    """

    def __init__(self, anomaly_threshold: float = 3.0, coherence_weight: float = 0.6):
        """
        初始化滤波器。
        
        Args:
            anomaly_threshold (float): 物理异常检测的标准差倍数阈值。
            coherence_weight (float): 逻辑一致性在决策中的权重 (0.0-1.0)。
        """
        if not 0.0 <= coherence_weight <= 1.0:
            raise ValueError("coherence_weight must be between 0 and 1.")
        
        self.anomaly_threshold = anomaly_threshold
        self.coherence_weight = coherence_weight
        self.history: Dict[str, List[float]] = {}
        logger.info("CognitiveFilter initialized with threshold %.2f", anomaly_threshold)

    def _update_history(self, sensor_id: str, value: float, max_history: int = 10) -> None:
        """
        [辅助函数] 更新传感器历史数据用于统计滤波。
        """
        if sensor_id not in self.history:
            self.history[sensor_id] = []
        
        self.history[sensor_id].append(value)
        if len(self.history[sensor_id]) > max_history:
            self.history[sensor_id].pop(0)

    def _check_physical_plausibility(self, reading: SensorReading, context: WorldContext) -> Tuple[bool, str]:
        """
        [核心函数1] 物理常识与上下文一致性检查。
        
        检查传感器读数是否违背物理定律或环境约束。
        """
        # 边界检查
        if reading.value < 0 and reading.modality in ['lidar', 'proximity']:
            return False, f"Negative distance detected for {reading.sensor_id}"
            
        # 场景1: 里程计报告速度超过物理极限或环境限制
        if reading.modality == 'odometry':
            if reading.value > context.max_speed_limit:
                return False, "Speed exceeds known physical/environment limits"
        
        # 场景2: 声纳/激光雷达报告距离，但视觉系统在相同方向未发现障碍物
        # 这里简化为：如果视觉前方无障碍(min_dist > 5m)，但距离传感器报告 < 1m
        if reading.modality in ['lidar', 'proximity']:
            min_visual_dist = min(context.visual_obstacles) if context.visual_obstacles else 100.0
            # 认知失调检测：视觉说很远，距离传感器说很近 -> 可能是传感器被欺骗或故障
            if reading.value < 1.0 and min_visual_dist > 5.0:
                return False, "Cognitive Dissonance: Sensor collision warning conflicts with Visual clear path"
        
        return True, "Physically plausible"

    def process_fusion(self, readings: List[SensorReading], context: WorldContext) -> Dict[str, float]:
        """
        [核心函数2] 处理多传感器融合并进行抗欺骗滤波。
        
        Args:
            readings (List[SensorReading]): 当前时刻的所有传感器读数。
            context (WorldContext): 当前世界的上下文信息（常识/其他模态摘要）。
            
        Returns:
            Dict[str, float]: 经过清洗和验证后的可信数据字典。
        
        Raises:
            ValueError: 如果输入数据为空。
        """
        if not readings:
            raise ValueError("Input readings cannot be empty")

        validated_data = {}
        
        for reading in readings:
            sensor_id = reading.sensor_id
            val = reading.value
            
            # 1. 统计异常检测
            hist = self.history.get(sensor_id, [])
            is_stat_anomaly = False
            
            if len(hist) > 2:
                mean = np.mean(hist)
                std = np.std(hist)
                if std > 1e-6:
                    z_score = abs((val - mean) / std)
                    if z_score > self.anomaly_threshold:
                        is_stat_anomaly = True
                        logger.warning(f"Statistical anomaly detected for {sensor_id}: Z={z_score:.2f}")

            # 2. 逻辑/认知一致性检测
            is_plausible, reason = self._check_physical_plausibility(reading, context)
            
            # 3. 决策融合
            # 如果统计上异常 且 逻辑上不通，则直接丢弃
            # 如果统计上正常 但 逻辑上严重冲突（认知失调），也丢弃 -> 这是"抗欺骗"的关键
            if not is_plausible:
                logger.error(f"FILTERED OUT {sensor_id} value {val:.2f}. Reason: {reason}")
                continue
            
            if is_stat_anomaly and not is_plausible:
                logger.error(f"FILTERED OUT {sensor_id} due to combined statistical and logical anomaly.")
                continue
            
            # 如果只是统计异常但逻辑合理（例如突然加速但符合环境），可能保留，但降低权重（此处简化为保留）
            if is_stat_anomaly:
                logger.warning(f"Passing {sensor_id} despite statistical anomaly (Logical check passed).")

            # 更新历史并接受数据
            self._update_history(sensor_id, val)
            validated_data[sensor_id] = val
            
        return validated_data

# 示例用法与测试
if __name__ == "__main__":
    # 模拟初始化
    filter_system = CognitiveFilter(anomaly_threshold=2.5)
    
    # 模拟环境上下文：视觉看到前方5米内有障碍物
    current_context = WorldContext(
        visual_obstacles=[5.2, 5.5, 6.0], 
        is_indoors=True, 
        max_speed_limit=10.0
    )
    
    # 模拟一组正常的传感器数据
    normal_readings = [
        SensorReading("lidar_01", "lidar", 5.3, time.time(), 0.9),
        SensorReading("odo_01", "odometry", 2.5, time.time(), 0.95)
    ]
    
    print("--- Processing Normal Data ---")
    result_normal = filter_system.process_fusion(normal_readings, current_context)
    print(f"Validated Data: {result_normal}")
    
    # 模拟攻击场景：黑客篡改了激光雷达数据，显示前方0.1米有墙（触发急停）
    # 但视觉系统（Context）显示前方5米是空的。这构成了"认知失调"。
    hacked_readings = [
        SensorReading("lidar_01", "lidar", 0.1, time.time(), 0.99), # 假数据，置信度甚至很高
        SensorReading("odo_01", "odometry", 2.5, time.time(), 0.95)
    ]
    
    print("\n--- Processing Deceptive Data (Cognitive Dissonance) ---")
    result_hacked = filter_system.process_fusion(hacked_readings, current_context)
    print(f"Validated Data: {result_hacked}")
    
    # 预期结果: lidar_01 应该被滤除，尽管它可能通过了物理噪声滤波（因为它是一个清晰的信号）
    # 但因为它与 WorldContext (视觉) 冲突。