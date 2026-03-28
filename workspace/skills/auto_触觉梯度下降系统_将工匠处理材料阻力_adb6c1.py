"""
触觉梯度下降系统

该模块实现了将工匠处理材料阻力（如木纹走向、陶土湿度）的微妙体感转化为数字信号，
构建'物理损失函数'。通过力反馈传感器实时计算'物理阻力损失'，实现AI在物理世界中
非结构化环境下的精细化作业。

典型使用示例:
    sensor_data = [
        {'position': [0.1, 0.2, 0.3], 'force_vector': [0.5, 0.2, 0.1]},
        {'position': [0.2, 0.3, 0.4], 'force_vector': [0.6, 0.3, 0.2]},
    ]
    
    system = TactileGradientDescent(
        material_type='wood',
        resistance_threshold=0.8,
        learning_rate=0.01
    )
    
    result = system.process_sensor_data(sensor_data)
    print(f"调整策略: {result['adjustments']}")
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """传感器读数数据结构"""
    position: Tuple[float, float, float]  # 3D坐标位置 (x, y, z)
    force_vector: Tuple[float, float, float]  # 力向量
    timestamp: Optional[float] = None  # 时间戳


@dataclass
class Adjustment:
    """调整策略数据结构"""
    position_adjustment: Tuple[float, float, float]
    force_adjustment: Tuple[float, float, float]
    confidence: float  # 调整置信度 (0-1)


class TactileGradientDescent:
    """触觉梯度下降系统核心类
    
    该系统通过分析力反馈传感器的数据，模拟工匠的'手感'，实现对材料阻力的
    实时响应和精细调整。
    
    属性:
        material_type (str): 材料类型 ('wood', 'clay', 'metal'等)
        resistance_threshold (float): 阻力阈值
        learning_rate (float): 学习率
        adjustment_history (List[Adjustment]): 调整历史记录
        
    方法:
        process_sensor_data: 处理传感器数据并生成调整策略
        calculate_physical_loss: 计算物理损失函数
        fine_tune_strategy: 生成微调策略
    """
    
    def __init__(
        self,
        material_type: str = 'wood',
        resistance_threshold: float = 0.8,
        learning_rate: float = 0.01,
        max_history: int = 100
    ) -> None:
        """初始化触觉梯度下降系统
        
        参数:
            material_type: 材料类型
            resistance_threshold: 阻力阈值 (0-1)
            learning_rate: 学习率 (0-1)
            max_history: 最大历史记录数
            
        异常:
            ValueError: 当参数超出有效范围时抛出
        """
        self._validate_init_params(material_type, resistance_threshold, learning_rate)
        
        self.material_type = material_type
        self.resistance_threshold = resistance_threshold
        self.learning_rate = learning_rate
        self.max_history = max_history
        self.adjustment_history: List[Adjustment] = []
        
        # 材料特性常量
        self.MATERIAL_PROPERTIES = {
            'wood': {'grain_factor': 0.7, 'elasticity': 0.3},
            'clay': {'grain_factor': 0.4, 'elasticity': 0.8},
            'metal': {'grain_factor': 0.9, 'elasticity': 0.1},
            'plastic': {'grain_factor': 0.5, 'elasticity': 0.6}
        }
        
        logger.info(f"初始化触觉梯度下降系统 - 材料: {material_type}, 阈值: {resistance_threshold}")
    
    def _validate_init_params(
        self,
        material_type: str,
        resistance_threshold: float,
        learning_rate: float
    ) -> None:
        """验证初始化参数
        
        参数:
            material_type: 材料类型
            resistance_threshold: 阻力阈值
            learning_rate: 学习率
            
        异常:
            ValueError: 当参数无效时抛出
        """
        valid_materials = ['wood', 'clay', 'metal', 'plastic']
        if material_type not in valid_materials:
            raise ValueError(f"无效材料类型: {material_type}. 有效选项: {valid_materials}")
            
        if not 0 <= resistance_threshold <= 1:
            raise ValueError(f"阻力阈值必须在0-1范围内: {resistance_threshold}")
            
        if not 0 < learning_rate < 1:
            raise ValueError(f"学习率必须在0-1范围内: {learning_rate}")
    
    def process_sensor_data(
        self,
        sensor_data: List[Dict[str, Union[List[float], float]]]
    ) -> Dict[str, Union[List[Adjustment], float]]:
        """处理传感器数据并生成调整策略
        
        参数:
            sensor_data: 传感器数据列表，每个元素包含position和force_vector
            
        返回:
            包含调整策略和损失值的字典:
            {
                'adjustments': List[Adjustment],  # 调整策略列表
                'total_loss': float,             # 总损失值
                'average_loss': float            # 平均损失值
            }
            
        异常:
            ValueError: 当输入数据格式无效时抛出
        """
        if not sensor_data:
            raise ValueError("传感器数据不能为空")
            
        try:
            readings = self._parse_sensor_data(sensor_data)
            adjustments = []
            total_loss = 0.0
            
            for reading in readings:
                loss = self.calculate_physical_loss(reading)
                total_loss += loss
                
                if loss > self.resistance_threshold:
                    adjustment = self.fine_tune_strategy(reading, loss)
                    adjustments.append(adjustment)
                    self._update_history(adjustment)
            
            average_loss = total_loss / len(readings) if readings else 0.0
            
            logger.info(f"处理完成 - 总损失: {total_loss:.4f}, 平均损失: {average_loss:.4f}")
            
            return {
                'adjustments': adjustments,
                'total_loss': total_loss,
                'average_loss': average_loss
            }
            
        except Exception as e:
            logger.error(f"处理传感器数据时出错: {str(e)}")
            raise
    
    def calculate_physical_loss(self, reading: SensorReading) -> float:
        """计算物理损失函数
        
        基于力反馈数据计算物理损失，模拟工匠感知材料阻力的'手感'。
        
        参数:
            reading: 传感器读数
            
        返回:
            物理损失值 (0-1)
        """
        # 获取材料特性
        properties = self.MATERIAL_PROPERTIES.get(self.material_type, {})
        grain_factor = properties.get('grain_factor', 0.5)
        elasticity = properties.get('elasticity', 0.5)
        
        # 计算力的大小
        force_magnitude = math.sqrt(sum(f**2 for f in reading.force_vector))
        
        # 计算方向一致性损失 (假设理想情况下力方向与材料纹理一致)
        direction_loss = 1 - abs(sum(reading.force_vector)) / (force_magnitude + 1e-6)
        
        # 综合损失函数
        physical_loss = (
            0.4 * force_magnitude + 
            0.3 * direction_loss + 
            0.2 * (1 - grain_factor) + 
            0.1 * (1 - elasticity)
        )
        
        # 边界检查
        physical_loss = max(0.0, min(1.0, physical_loss))
        
        logger.debug(f"位置 {reading.position} 的物理损失: {physical_loss:.4f}")
        return physical_loss
    
    def fine_tune_strategy(
        self,
        reading: SensorReading,
        current_loss: float
    ) -> Adjustment:
        """生成微调策略
        
        当物理损失超过阈值时，计算位置和力的调整量，模拟老工匠的'手感'微调。
        
        参数:
            reading: 当前传感器读数
            current_loss: 当前物理损失
            
        返回:
            包含调整策略的Adjustment对象
        """
        # 计算调整幅度 (基于学习率和当前损失)
        adjustment_scale = self.learning_rate * current_loss
        
        # 计算位置调整 (向阻力较小的方向移动)
        position_adjustment = tuple(
            -p * adjustment_scale * 0.1 for p in reading.position
        )
        
        # 计算力调整 (减小力的大小)
        force_adjustment = tuple(
            -f * adjustment_scale for f in reading.force_vector
        )
        
        # 计算调整置信度 (损失越大，置信度越高)
        confidence = min(1.0, current_loss / self.resistance_threshold)
        
        adjustment = Adjustment(
            position_adjustment=position_adjustment,
            force_adjustment=force_adjustment,
            confidence=confidence
        )
        
        logger.info(f"生成微调策略 - 位置调整: {position_adjustment}, 置信度: {confidence:.2f}")
        return adjustment
    
    def _parse_sensor_data(
        self,
        sensor_data: List[Dict[str, Union[List[float], float]]]
    ) -> List[SensorReading]:
        """解析传感器数据
        
        辅助函数，将原始字典数据转换为SensorReading对象。
        
        参数:
            sensor_data: 原始传感器数据
            
        返回:
            SensorReading对象列表
            
        异常:
            ValueError: 当数据格式无效时抛出
        """
        readings = []
        for i, data in enumerate(sensor_data):
            try:
                if 'position' not in data or 'force_vector' not in data:
                    raise ValueError(f"数据点 {i} 缺少必要字段")
                
                position = tuple(data['position'])
                force_vector = tuple(data['force_vector'])
                
                if len(position) != 3 or len(force_vector) != 3:
                    raise ValueError(f"数据点 {i} 的位置或力向量维度不正确")
                
                timestamp = data.get('timestamp')
                readings.append(SensorReading(position, force_vector, timestamp))
                
            except Exception as e:
                logger.error(f"解析数据点 {i} 时出错: {str(e)}")
                raise ValueError(f"无效的传感器数据格式: {str(e)}")
        
        return readings
    
    def _update_history(self, adjustment: Adjustment) -> None:
        """更新调整历史
        
        维护一个有限长度的调整历史记录，用于后续分析和优化。
        
        参数:
            adjustment: 新的调整记录
        """
        self.adjustment_history.append(adjustment)
        
        # 保持历史记录在最大限制内
        if len(self.adjustment_history) > self.max_history:
            self.adjustment_history.pop(0)
    
    def get_adjustment_trends(self) -> Dict[str, float]:
        """分析调整趋势
        
        基于历史调整记录，分析系统的调整趋势和性能。
        
        返回:
            包含趋势分析的字典:
            {
                'avg_confidence': float,  # 平均置信度
                'adjustment_rate': float, # 调整频率
                'position_variance': float # 位置调整方差
            }
        """
        if not self.adjustment_history:
            return {'avg_confidence': 0.0, 'adjustment_rate': 0.0, 'position_variance': 0.0}
        
        # 计算平均置信度
        avg_confidence = sum(a.confidence for a in self.adjustment_history) / len(self.adjustment_history)
        
        # 计算位置调整方差
        position_adjustments = [a.position_adjustment for a in self.adjustment_history]
        position_variance = sum(
            sum(p**2 for p in pos) for pos in position_adjustments
        ) / len(position_adjustments)
        
        return {
            'avg_confidence': avg_confidence,
            'adjustment_rate': len(self.adjustment_history) / self.max_history,
            'position_variance': position_variance
        }