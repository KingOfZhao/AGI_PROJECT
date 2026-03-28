"""
模块名称: auto_基于力控动态系统的不变量提取_在雕刻工艺_67cd31
描述: 基于力控动态系统的不变量提取：在雕刻工艺中，提取不随工匠肢体运动轨迹变化，
      但随工件表面反馈变化的'力-位'耦合关系。核心在于分离'过程噪声'(工匠习惯)与
      '核心算子'(物理约束)，获取纯粹的隐性力学逻辑。
作者: AGI System
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, List, Dict, Optional, Union
from dataclasses import dataclass
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedData:
    """存储处理后的数据结构"""
    time_stamps: np.ndarray
    force_data: np.ndarray       # 力传感器数据 [Fx, Fy, Fz]
    position_data: np.ndarray    # 位置数据 [x, y, z]
    invariant_operator: np.ndarray  # 提取的不变量算子
    noise_profile: np.ndarray    # 过程噪声轮廓

class DynamicsInvariantExtractor:
    """
    基于力控动态系统的不变量提取器。
    
    用于在雕刻工艺中分离工匠习惯(过程噪声)与物理约束(核心算子)，
    提取不随工匠肢体运动轨迹变化，但随工件表面反馈变化的'力-位'耦合关系。
    
    Attributes:
        window_size (int): 滤波窗口大小
        poly_order (int): 多项式拟合阶数
        regularization (float): 正则化参数
    """
    
    def __init__(self, window_size: int = 15, poly_order: int = 3, regularization: float = 0.1):
        """
        初始化不变量提取器。
        
        Args:
            window_size: 滤波窗口大小，必须为奇数且大于等于3
            poly_order: 多项式拟合阶数，必须小于window_size
            regularization: 正则化参数，用于控制拟合平滑度
        """
        self.window_size = window_size
        self.poly_order = poly_order
        self.regularization = regularization
        
        # 参数验证
        if window_size % 2 == 0 or window_size < 3:
            raise ValueError("window_size必须是大于等于3的奇数")
        if poly_order >= window_size:
            raise ValueError("poly_order必须小于window_size")
        if regularization <= 0:
            raise ValueError("regularization必须是正数")
            
        logger.info("DynamicsInvariantExtractor初始化完成")
    
    def preprocess_sensor_data(
        self,
        time_stamps: np.ndarray,
        force_data: np.ndarray,
        position_data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        预处理传感器数据，进行滤波和归一化。
        
        Args:
            time_stamps: 时间戳数组，形状为(N,)
            force_data: 力传感器数据，形状为(N, 3) [Fx, Fy, Fz]
            position_data: 位置数据，形状为(N, 3) [x, y, z]
            
        Returns:
            处理后的时间戳、力数据和位置数据元组
            
        Raises:
            ValueError: 如果输入数据形状不匹配或包含无效值
        """
        # 输入验证
        self._validate_input_data(time_stamps, force_data, position_data)
        
        try:
            # 应用Savitzky-Golay滤波器平滑数据
            smoothed_force = np.zeros_like(force_data)
            for i in range(3):  # 对每个力分量分别处理
                smoothed_force[:, i] = savgol_filter(
                    force_data[:, i], 
                    self.window_size, 
                    self.poly_order
                )
            
            # 位置数据平滑
            smoothed_position = np.zeros_like(position_data)
            for i in range(3):  # 对每个位置分量分别处理
                smoothed_position[:, i] = savgol_filter(
                    position_data[:, i], 
                    self.window_size, 
                    self.poly_order
                )
            
            # 归一化处理
            normalized_force = self._normalize_data(smoothed_force)
            normalized_position = self._normalize_data(smoothed_position)
            
            logger.info("传感器数据预处理完成")
            return time_stamps, normalized_force, normalized_position
            
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            raise RuntimeError(f"数据预处理失败: {str(e)}") from e
    
    def extract_invariant_operator(
        self,
        force_data: np.ndarray,
        position_data: np.ndarray,
        time_stamps: np.ndarray
    ) -> ProcessedData:
        """
        提取力控动态系统的不变量算子。
        
        核心算法通过以下步骤实现:
        1. 计算力与位置的动态耦合矩阵
        2. 通过奇异值分解分离主导模式
        3. 提取不随轨迹变化的核心算子
        
        Args:
            force_data: 预处理后的力数据，形状为(N, 3)
            position_data: 预处理后的位置数据，形状为(N, 3)
            time_stamps: 时间戳数组，形状为(N,)
            
        Returns:
            ProcessedData对象，包含处理后的数据和提取的不变量
            
        Raises:
            RuntimeError: 如果不变量提取失败
        """
        if not (force_data.shape[0] == position_data.shape[0] == time_stamps.shape[0]):
            raise ValueError("输入数据长度不匹配")
            
        try:
            # 计算速度和加速度(数值微分)
            velocity = np.gradient(position_data, time_stamps, axis=0)
            acceleration = np.gradient(velocity, time_stamps, axis=0)
            
            # 构建动态耦合矩阵
            coupling_matrix = self._build_coupling_matrix(force_data, acceleration)
            
            # 奇异值分解分离主导模式
            u, s, vh = np.linalg.svd(coupling_matrix, full_matrices=False)
            
            # 提取核心算子(前k个主导模式)
            k = min(3, len(s))  # 保留前3个或更少的主导模式
            invariant_operator = u[:, :k] @ np.diag(s[:k]) @ vh[:k, :]
            
            # 计算过程噪声(原始数据与核心算子的差异)
            noise_profile = coupling_matrix - invariant_operator
            
            logger.info("不变量算子提取完成")
            
            return ProcessedData(
                time_stamps=time_stamps,
                force_data=force_data,
                position_data=position_data,
                invariant_operator=invariant_operator,
                noise_profile=noise_profile
            )
            
        except Exception as e:
            logger.error(f"不变量提取失败: {str(e)}")
            raise RuntimeError(f"不变量提取失败: {str(e)}") from e
    
    def _validate_input_data(
        self,
        time_stamps: np.ndarray,
        force_data: np.ndarray,
        position_data: np.ndarray
    ) -> None:
        """
        验证输入数据的完整性和有效性。
        
        Args:
            time_stamps: 时间戳数组
            force_data: 力传感器数据
            position_data: 位置数据
            
        Raises:
            ValueError: 如果数据无效
        """
        if len(time_stamps) < 10:
            raise ValueError("时间戳数据点太少，至少需要10个点")
            
        if force_data.shape[0] != time_stamps.shape[0]:
            raise ValueError("力数据与时间戳长度不匹配")
            
        if position_data.shape[0] != time_stamps.shape[0]:
            raise ValueError("位置数据与时间戳长度不匹配")
            
        if force_data.shape[1] != 3 or position_data.shape[1] != 3:
            raise ValueError("力数据和位置数据必须是3维的")
            
        if np.any(np.isnan(force_data)) or np.any(np.isnan(position_data)):
            raise ValueError("输入数据包含NaN值")
            
        if np.any(np.isinf(force_data)) or np.any(np.isinf(position_data)):
            raise ValueError("输入数据包含无穷大值")
    
    def _normalize_data(self, data: np.ndarray) -> np.ndarray:
        """
        数据归一化辅助函数，将数据缩放到[-1, 1]范围。
        
        Args:
            data: 输入数据数组
            
        Returns:
            归一化后的数据数组
        """
        min_val = np.min(data, axis=0)
        max_val = np.max(data, axis=0)
        
        # 避免除以零
        range_val = max_val - min_val
        range_val[range_val == 0] = 1.0
        
        normalized = 2 * (data - min_val) / range_val - 1
        return normalized
    
    def _build_coupling_matrix(
        self,
        force_data: np.ndarray,
        acceleration: np.ndarray
    ) -> np.ndarray:
        """
        构建力-加速度耦合矩阵。
        
        Args:
            force_data: 力数据，形状为(N, 3)
            acceleration: 加速度数据，形状为(N, 3)
            
        Returns:
            耦合矩阵，形状为(N, 3)
        """
        # 这里使用简单的线性耦合模型
        # 实际应用中可以使用更复杂的非线性模型
        coupling_matrix = np.zeros((force_data.shape[0], 3))
        
        # 计算每个时间步的力-加速度耦合
        for i in range(3):
            coupling_matrix[:, i] = force_data[:, i] * acceleration[:, i]
        
        return coupling_matrix

def generate_sample_data(duration: float = 10.0, fs: int = 100) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    生成模拟的雕刻工艺数据用于测试。
    
    Args:
        duration: 数据持续时间(秒)
        fs: 采样频率(Hz)
        
    Returns:
        时间戳、力数据和位置数据的元组
    """
    t = np.linspace(0, duration, int(duration * fs), endpoint=False)
    
    # 生成模拟的位置数据(工匠运动轨迹)
    position = np.zeros((len(t), 3))
    position[:, 0] = np.sin(2 * np.pi * 0.5 * t)  # x方向
    position[:, 1] = np.cos(2 * np.pi * 0.3 * t)  # y方向
    position[:, 2] = 0.5 * np.sin(2 * np.pi * 0.2 * t)  # z方向
    
    # 生成模拟的力数据(包含表面反馈和工匠习惯)
    force = np.zeros((len(t), 3))
    # 表面反馈(不变量部分)
    surface_response = np.array([0.3, 0.4, 0.5])
    # 工匠习惯(过程噪声)
    craftsman_habit = np.array([0.1 * np.sin(2 * np.pi * 2 * t),
                               0.2 * np.cos(2 * np.pi * 1.5 * t),
                               0.15 * np.sin(2 * np.pi * 1.8 * t)]).T
    
    force = surface_response * position + craftsman_habit
    
    return t, force, position

# 使用示例
if __name__ == "__main__":
    try:
        # 生成模拟数据
        time_stamps, force_data, position_data = generate_sample_data()
        
        # 创建提取器实例
        extractor = DynamicsInvariantExtractor(window_size=15, poly_order=3)
        
        # 预处理数据
        processed_time, processed_force, processed_pos = extractor.preprocess_sensor_data(
            time_stamps, force_data, position_data
        )
        
        # 提取不变量
        result = extractor.extract_invariant_operator(
            processed_force, processed_pos, processed_time
        )
        
        print("不变量算子形状:", result.invariant_operator.shape)
        print("过程噪声轮廓形状:", result.noise_profile.shape)
        
    except Exception as e:
        print(f"示例运行出错: {str(e)}")