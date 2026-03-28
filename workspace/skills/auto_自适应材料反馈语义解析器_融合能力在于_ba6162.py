"""
自适应材料反馈语义解析器

该模块实现了一个能够将物理传感器数据转化为结构化反馈信号的系统。
通过模拟老匠人的直觉，将材料特性（如震动、阻力）量化为可计算的指标，
并指导机器人进行自适应调整。

核心功能：
1. 传感器数据融合与解析
2. 材料特性状态推断
3. 自适应操作参数生成
4. 异常检测与预警

作者: AGI System
版本: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptiveMaterialParser")


class MaterialState(Enum):
    """材料状态枚举"""
    STABLE = auto()       # 稳定
    UNSTABLE = auto()     # 不稳定
    RESISTANT = auto()    # 高阻力
    FRAGILE = auto()      # 脆弱
    UNKNOWN = auto()      # 未知


class FeedbackType(Enum):
    """反馈类型枚举"""
    NORMAL = auto()       # 正常
    WARNING = auto()      # 警告
    ERROR = auto()        # 错误
    CRITICAL = auto()     # 严重


@dataclass
class SensorData:
    """传感器数据结构"""
    timestamp: float
    vibration_freq: float    # 刀具震动频率
    resistance: float       # 阻力值
    temperature: float      # 温度
    humidity: float         # 湿度
    position: Tuple[float, float, float]  # 三维坐标


@dataclass
class FeedbackSignal:
    """反馈信号结构"""
    code: str               # 错误代码
    message: str            # 描述信息
    feedback_type: FeedbackType  # 反馈类型
    adjustment: Dict[str, float]  # 调整参数
    confidence: float       # 置信度 (0-1)


class AdaptiveMaterialParser:
    """
    自适应材料反馈语义解析器
    
    该类将物理传感器数据转化为结构化反馈信号，模拟老匠人对材料特性的直觉判断。
    
    属性:
        material_thresholds (dict): 材料特性阈值配置
        history_window (int): 历史数据窗口大小
        _sensor_history (list): 传感器历史数据缓存
    """
    
    def __init__(
        self,
        material_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        history_window: int = 10
    ):
        """
        初始化解析器
        
        参数:
            material_thresholds: 材料阈值配置字典
            history_window: 历史数据窗口大小
        """
        # 默认材料阈值配置
        self.material_thresholds = material_thresholds or {
            'wood': {
                'vibration_min': 10.0,
                'vibration_max': 100.0,
                'resistance_min': 0.3,
                'resistance_max': 0.8
            },
            'clay': {
                'vibration_min': 5.0,
                'vibration_max': 50.0,
                'resistance_min': 0.5,
                'resistance_max': 0.9
            },
            'metal': {
                'vibration_min': 20.0,
                'vibration_max': 200.0,
                'resistance_min': 0.7,
                'resistance_max': 1.5
            }
        }
        
        self.history_window = history_window
        self._sensor_history: List[SensorData] = []
        
        logger.info("AdaptiveMaterialParser initialized with %d material profiles", 
                   len(self.material_thresholds))
    
    def parse_sensor_data(
        self,
        sensor_data: SensorData,
        material_type: str = 'wood'
    ) -> FeedbackSignal:
        """
        解析传感器数据并生成反馈信号
        
        参数:
            sensor_data: 传感器数据对象
            material_type: 材料类型
            
        返回:
            FeedbackSignal: 结构化反馈信号
            
        异常:
            ValueError: 当传感器数据无效时
        """
        # 数据验证
        self._validate_sensor_data(sensor_data)
        
        # 更新历史数据
        self._update_history(sensor_data)
        
        # 获取材料阈值
        thresholds = self._get_material_thresholds(material_type)
        
        # 分析材料状态
        state = self._analyze_material_state(sensor_data, thresholds)
        
        # 生成反馈信号
        feedback = self._generate_feedback_signal(
            state, sensor_data, thresholds, material_type
        )
        
        logger.debug("Generated feedback: %s for material %s", 
                    feedback.code, material_type)
        
        return feedback
    
    def generate_adaptive_parameters(
        self,
        feedback_signal: FeedbackSignal,
        current_params: Dict[str, float]
    ) -> Dict[str, float]:
        """
        根据反馈信号生成自适应调整参数
        
        参数:
            feedback_signal: 反馈信号
            current_params: 当前操作参数
            
        返回:
            Dict[str, float]: 调整后的参数
        """
        adjusted_params = current_params.copy()
        
        # 应用反馈调整
        for param, adjustment in feedback_signal.adjustment.items():
            if param in adjusted_params:
                # 根据置信度调整修改幅度
                modified_value = adjusted_params[param] * (1 + adjustment * feedback_signal.confidence)
                
                # 边界检查
                if param == 'force':
                    modified_value = max(0.1, min(modified_value, 10.0))
                elif param == 'speed':
                    modified_value = max(0.05, min(modified_value, 5.0))
                
                adjusted_params[param] = modified_value
        
        logger.info("Parameters adjusted: %s -> %s", current_params, adjusted_params)
        return adjusted_params
    
    def _validate_sensor_data(self, data: SensorData) -> None:
        """
        验证传感器数据的有效性
        
        参数:
            data: 传感器数据
            
        异常:
            ValueError: 当数据无效时
        """
        if data.timestamp <= 0:
            raise ValueError(f"Invalid timestamp: {data.timestamp}")
            
        if not (0 <= data.vibration_freq <= 1000):
            raise ValueError(f"Vibration frequency out of range: {data.vibration_freq}")
            
        if not (0 <= data.resistance <= 10):
            raise ValueError(f"Resistance out of range: {data.resistance}")
            
        if not (-50 <= data.temperature <= 300):
            raise ValueError(f"Temperature out of range: {data.temperature}")
            
        if not (0 <= data.humidity <= 100):
            raise ValueError(f"Humidity out of range: {data.humidity}")
            
        for coord in data.position:
            if not (-10000 <= coord <= 10000):
                raise ValueError(f"Position coordinate out of range: {data.position}")
    
    def _update_history(self, data: SensorData) -> None:
        """更新传感器历史数据缓存"""
        self._sensor_history.append(data)
        if len(self._sensor_history) > self.history_window:
            self._sensor_history.pop(0)
    
    def _get_material_thresholds(self, material_type: str) -> Dict[str, float]:
        """获取材料阈值配置"""
        if material_type not in self.material_thresholds:
            logger.warning("Unknown material type: %s, using default", material_type)
            return self.material_thresholds['wood']
        return self.material_thresholds[material_type]
    
    def _analyze_material_state(
        self,
        data: SensorData,
        thresholds: Dict[str, float]
    ) -> MaterialState:
        """
        分析材料状态
        
        参数:
            data: 传感器数据
            thresholds: 材料阈值
            
        返回:
            MaterialState: 材料状态
        """
        # 检查震动频率
        if data.vibration_freq < thresholds['vibration_min']:
            return MaterialState.FRAGILE
        elif data.vibration_freq > thresholds['vibration_max']:
            return MaterialState.UNSTABLE
        
        # 检查阻力
        if data.resistance < thresholds['resistance_min']:
            return MaterialState.FRAGILE
        elif data.resistance > thresholds['resistance_max']:
            return MaterialState.RESISTANT
        
        return MaterialState.STABLE
    
    def _generate_feedback_signal(
        self,
        state: MaterialState,
        data: SensorData,
        thresholds: Dict[str, float],
        material_type: str
    ) -> FeedbackSignal:
        """
        生成结构化反馈信号
        
        参数:
            state: 材料状态
            data: 传感器数据
            thresholds: 材料阈值
            material_type: 材料类型
            
        返回:
            FeedbackSignal: 反馈信号
        """
        # 计算偏差
        vibration_deviation = self._calculate_deviation(
            data.vibration_freq,
            thresholds['vibration_min'],
            thresholds['vibration_max']
        )
        
        resistance_deviation = self._calculate_deviation(
            data.resistance,
            thresholds['resistance_min'],
            thresholds['resistance_max']
        )
        
        # 根据状态生成反馈
        if state == MaterialState.STABLE:
            return FeedbackSignal(
                code="MAT_200",
                message=f"Material {material_type} is stable",
                feedback_type=FeedbackType.NORMAL,
                adjustment={'force': 0.0, 'speed': 0.0},
                confidence=0.9
            )
        elif state == MaterialState.RESISTANT:
            return FeedbackSignal(
                code="MAT_301",
                message=f"High resistance detected in {material_type}",
                feedback_type=FeedbackType.WARNING,
                adjustment={'force': 0.15, 'speed': -0.1},
                confidence=0.85
            )
        elif state == MaterialState.FRAGILE:
            return FeedbackSignal(
                code="MAT_302",
                message=f"Fragile condition detected in {material_type}",
                feedback_type=FeedbackType.WARNING,
                adjustment={'force': -0.2, 'speed': -0.15},
                confidence=0.8
            )
        elif state == MaterialState.UNSTABLE:
            return FeedbackSignal(
                code="MAT_401",
                message=f"Unstable vibration detected in {material_type}",
                feedback_type=FeedbackType.ERROR,
                adjustment={'force': -0.3, 'speed': -0.2},
                confidence=0.75
            )
        else:
            return FeedbackSignal(
                code="MAT_500",
                message="Unknown material state",
                feedback_type=FeedbackType.CRITICAL,
                adjustment={'force': -0.5, 'speed': -0.5},
                confidence=0.6
            )
    
    def _calculate_deviation(
        self,
        value: float,
        min_val: float,
        max_val: float
    ) -> float:
        """
        计算值相对于范围的偏差
        
        参数:
            value: 当前值
            min_val: 最小值
            max_val: 最大值
            
        返回:
            float: 偏差值 (负数表示低于范围，正数表示高于范围)
        """
        if value < min_val:
            return (value - min_val) / min_val
        elif value > max_val:
            return (value - max_val) / max_val
        return 0.0
    
    def get_trend_analysis(self) -> Dict[str, str]:
        """
        分析传感器数据趋势
        
        返回:
            Dict[str, str]: 趋势分析结果
        """
        if len(self._sensor_history) < 3:
            return {'status': 'insufficient_data'}
        
        # 计算震动频率趋势
        vibration_trend = self._calculate_trend(
            [d.vibration_freq for d in self._sensor_history]
        )
        
        # 计算阻力趋势
        resistance_trend = self._calculate_trend(
            [d.resistance for d in self._sensor_history]
        )
        
        return {
            'vibration_trend': vibration_trend,
            'resistance_trend': resistance_trend,
            'data_points': len(self._sensor_history)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        计算数据趋势
        
        参数:
            values: 数值列表
            
        返回:
            str: 趋势描述
        """
        if len(values) < 2:
            return 'stable'
        
        # 计算简单线性回归斜率
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if abs(slope) < 0.01:
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'


# 使用示例
if __name__ == "__main__":
    # 创建解析器实例
    parser = AdaptiveMaterialParser()
    
    # 模拟传感器数据
    sensor_data = SensorData(
        timestamp=1625097600.0,
        vibration_freq=45.0,
        resistance=0.6,
        temperature=25.0,
        humidity=45.0,
        position=(100.0, 200.0, 50.0)
    )
    
    # 解析传感器数据
    feedback = parser.parse_sensor_data(sensor_data, material_type='wood')
    print(f"Feedback: {feedback.code} - {feedback.message}")
    
    # 生成自适应参数
    current_params = {'force': 1.0, 'speed': 0.5}
    adjusted_params = parser.generate_adaptive_parameters(feedback, current_params)
    print(f"Adjusted params: {adjusted_params}")
    
    # 趋势分析
    for i in range(5):
        data = SensorData(
            timestamp=1625097600.0 + i,
            vibration_freq=40.0 + i * 2,
            resistance=0.5 + i * 0.05,
            temperature=25.0,
            humidity=45.0,
            position=(100.0, 200.0, 50.0)
        )
        parser.parse_sensor_data(data, material_type='wood')
    
    trend = parser.get_trend_analysis()
    print(f"Trend analysis: {trend}")