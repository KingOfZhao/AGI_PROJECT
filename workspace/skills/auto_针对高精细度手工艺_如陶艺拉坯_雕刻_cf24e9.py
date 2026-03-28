"""
高精细度手工艺数字孪生编码协议模块

该模块实现了基于多模态传感器（EMG+IMU+视频）的数字孪生系统，
用于捕捉和编码陶艺拉坯、雕刻等精细手工艺中的肌肉微动作和力度变化。

输入数据格式：
    - EMG数据: numpy.ndarray, shape=(n_samples, 8), 范围[-1, 1]
    - IMU数据: numpy.ndarray, shape=(n_samples, 6), [ax,ay,az,gx,gy,gz]
    - 视频帧: numpy.ndarray, shape=(height, width, 3), dtype=uint8

输出格式：
    - 时间序列特征数据: dict, 包含'timestamp', 'emg_features', 'motion_features', 'visual_features'

作者: AGI System
版本: 1.0.0
"""

import numpy as np
from typing import Dict, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from datetime import datetime
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import cv2

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CraftDigitalTwin")


@dataclass
class SensorConfig:
    """传感器配置参数"""
    emg_sample_rate: int = 2000  # EMG采样率
    imu_sample_rate: int = 200   # IMU采样率
    video_fps: int = 60          # 视频帧率
    emg_channels: int = 8        # EMG通道数
    imu_channels: int = 6        # IMU通道数(3加速度+3角速度)
    buffer_size: int = 256       # 数据缓冲区大小


class DataValidationError(Exception):
    """数据验证错误异常"""
    pass


class DigitalTwinEncoder:
    """
    高精细度手工艺数字孪生编码器
    
    该类实现了将多模态传感器数据编码为数字孪生特征的核心算法，
    包含信号预处理、特征提取和多模态融合功能。
    
    示例:
        >>> config = SensorConfig()
        >>> encoder = DigitalTwinEncoder(config)
        >>> emg_data = np.random.randn(256, 8)
        >>> imu_data = np.random.randn(256, 6)
        >>> frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        >>> features = encoder.encode_craft_motion(emg_data, imu_data, frame)
    """
    
    def __init__(self, config: Optional[SensorConfig] = None):
        """
        初始化数字孪生编码器
        
        参数:
            config: 传感器配置参数，如未提供则使用默认配置
        """
        self.config = config or SensorConfig()
        self._initialize_filters()
        logger.info("DigitalTwinEncoder initialized with config: %s", self.config)
        
    def _initialize_filters(self) -> None:
        """初始化信号处理滤波器"""
        # EMG带通滤波器 (20-500Hz)
        self.emg_b, self.emg_a = signal.butter(
            4, [20, 500], btype='bandpass', 
            fs=self.config.emg_sample_rate
        )
        
        # IMU低通滤波器 (截止频率10Hz)
        self.imu_b, self.imu_a = signal.butter(
            4, 10, btype='lowpass',
            fs=self.config.imu_sample_rate
        )
        
        # 视频背景减除器
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=50, detectShadows=True
        )
        
    def _validate_input_data(
        self,
        emg_data: np.ndarray,
        imu_data: np.ndarray,
        frame: np.ndarray
    ) -> Tuple[bool, str]:
        """
        验证输入数据的完整性和格式
        
        参数:
            emg_data: EMG信号数据
            imu_data: IMU运动数据
            frame: 视频帧数据
            
        返回:
            (is_valid, message): 验证结果和错误信息
        """
        # 检查数据形状
        if emg_data.ndim != 2 or emg_data.shape[1] != self.config.emg_channels:
            return False, f"EMG数据形状错误，期望(n, {self.config.emg_channels})，实际{emg_data.shape}"
            
        if imu_data.ndim != 2 or imu_data.shape[1] != self.config.imu_channels:
            return False, f"IMU数据形状错误，期望(n, {self.config.imu_channels})，实际{imu_data.shape}"
            
        if frame.ndim != 3 or frame.shape[2] != 3:
            return False, f"视频帧形状错误，期望(h, w, 3)，实际{frame.shape}"
            
        # 检查数据范围
        if np.any(np.abs(emg_data) > 1.0):
            logger.warning("EMG数据超出归一化范围[-1, 1]，将进行截断处理")
            
        # 检查缓冲区大小
        if len(emg_data) != self.config.buffer_size:
            return False, f"EMG缓冲区大小错误，期望{self.config.buffer_size}，实际{len(emg_data)}"
            
        return True, "数据验证通过"
    
    def preprocess_emg_signal(self, emg_data: np.ndarray) -> np.ndarray:
        """
        EMG信号预处理：滤波、整流、平滑
        
        参数:
            emg_data: 原始EMG信号，shape=(n_samples, n_channels)
            
        返回:
            处理后的EMG信号，shape=(n_samples, n_channels)
            
        异常:
            ValueError: 当输入数据包含NaN或Inf时
        """
        if np.any(np.isnan(emg_data)) or np.any(np.isinf(emg_data)):
            logger.error("EMG数据包含NaN或Inf值")
            raise ValueError("EMG数据包含无效值(NaN或Inf)")
            
        try:
            # 带通滤波去除噪声
            filtered_emg = signal.filtfilt(
                self.emg_b, self.emg_a, 
                emg_data, axis=0, padtype='odd', padlen=50
            )
            
            # 全波整流
            rectified_emg = np.abs(filtered_emg)
            
            # 高斯平滑保留"手感"特征
            smoothed_emg = gaussian_filter1d(
                rectified_emg, sigma=3, axis=0, mode='reflect'
            )
            
            # 归一化到[0, 1]范围
            normalized_emg = smoothed_emg / np.max(smoothed_emg + 1e-10)
            
            logger.debug("EMG预处理完成，数据范围: [%.3f, %.3f]", 
                        normalized_emg.min(), normalized_emg.max())
            
            return normalized_emg
            
        except Exception as e:
            logger.error("EMG预处理失败: %s", str(e))
            raise RuntimeError(f"EMG信号处理错误: {str(e)}")
    
    def preprocess_imu_signal(self, imu_data: np.ndarray) -> np.ndarray:
        """
        IMU信号预处理：滤波、坐标系转换
        
        参数:
            imu_data: 原始IMU数据，shape=(n_samples, 6)
                     [ax, ay, az, gx, gy, gz]
            
        返回:
            处理后的IMU数据，shape=(n_samples, 6)
        """
        if np.any(np.isnan(imu_data)) or np.any(np.isinf(imu_data)):
            logger.error("IMU数据包含NaN或Inf值")
            raise ValueError("IMU数据包含无效值(NaN或Inf)")
            
        try:
            # 分离加速度和角速度
            accel = imu_data[:, :3]
            gyro = imu_data[:, 3:]
            
            # 低通滤波去除高频噪声
            filtered_accel = signal.filtfilt(
                self.imu_b, self.imu_a,
                accel, axis=0, padtype='odd', padlen=20
            )
            
            filtered_gyro = signal.filtfilt(
                self.imu_b, self.imu_a,
                gyro, axis=0, padtype='odd', padlen=20
            )
            
            # 计算运动强度特征
            accel_magnitude = np.linalg.norm(filtered_accel, axis=1, keepdims=True)
            gyro_magnitude = np.linalg.norm(filtered_gyro, axis=1, keepdims=True)
            
            # 合并特征
            processed_imu = np.hstack([
                filtered_accel,
                filtered_gyro,
                accel_magnitude,
                gyro_magnitude
            ])
            
            logger.debug("IMU预处理完成，加速度模: %.3f, 角速度模: %.3f",
                        accel_magnitude.mean(), gyro_magnitude.mean())
            
            return processed_imu
            
        except Exception as e:
            logger.error("IMU预处理失败: %s", str(e))
            raise RuntimeError(f"IMU信号处理错误: {str(e)}")
    
    def extract_visual_features(self, frame: np.ndarray) -> Dict[str, np.ndarray]:
        """
        从视频帧中提取视觉特征
        
        参数:
            frame: BGR格式的视频帧
            
        返回:
            包含以下特征的字典:
            - 'motion_mask': 运动区域掩码
            - 'hand_region': 手部区域特征
            - 'tool_edge': 工具边缘特征
        """
        if frame.size == 0:
            raise DataValidationError("视频帧为空")
            
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 背景减除获取运动区域
            motion_mask = self.bg_subtractor.apply(frame)
            _, motion_mask = cv2.threshold(
                motion_mask, 200, 255, cv2.THRESH_BINARY
            )
            
            # 手部区域检测 (简化版，实际应用需使用专业手部检测模型)
            skin_mask = self._detect_skin_region(frame)
            
            # 工具边缘检测
            edges = cv2.Canny(gray, 50, 150)
            tool_edges = cv2.bitwise_and(edges, edges, mask=motion_mask)
            
            # 提取特征向量
            features = {
                'motion_mask': motion_mask,
                'hand_region': skin_mask,
                'tool_edge': tool_edges,
                'motion_intensity': np.mean(motion_mask > 0),
                'edge_density': np.mean(tool_edges > 0)
            }
            
            logger.debug("视觉特征提取完成，运动强度: %.3f, 边缘密度: %.3f",
                        features['motion_intensity'], features['edge_density'])
            
            return features
            
        except Exception as e:
            logger.error("视觉特征提取失败: %s", str(e))
            raise RuntimeError(f"视觉处理错误: {str(e)}")
    
    def _detect_skin_region(self, frame: np.ndarray) -> np.ndarray:
        """
        辅助函数：检测皮肤区域
        
        使用HSV色彩空间进行皮肤检测
        
        参数:
            frame: BGR格式的视频帧
            
        返回:
            皮肤区域二值掩码
        """
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 定义皮肤颜色范围
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # 创建掩码
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        
        return skin_mask
    
    def encode_craft_motion(
        self,
        emg_data: np.ndarray,
        imu_data: np.ndarray,
        frame: np.ndarray,
        timestamp: Optional[float] = None
    ) -> Dict[str, Union[float, np.ndarray, Dict]]:
        """
        核心编码函数：将多模态传感器数据编码为数字孪生特征
        
        参数:
            emg_data: EMG信号数据
            imu_data: IMU运动数据
            frame: 视频帧数据
            timestamp: 可选的时间戳
            
        返回:
            包含完整数字孪生特征的字典
            
        异常:
            DataValidationError: 当输入数据验证失败时
            RuntimeError: 当特征提取过程出错时
        """
        # 数据验证
        is_valid, message = self._validate_input_data(emg_data, imu_data, frame)
        if not is_valid:
            logger.error("数据验证失败: %s", message)
            raise DataValidationError(message)
            
        try:
            start_time = datetime.now()
            
            # 预处理各模态数据
            processed_emg = self.preprocess_emg_signal(emg_data)
            processed_imu = self.preprocess_imu_signal(imu_data)
            visual_features = self.extract_visual_features(frame)
            
            # 提取EMG特征
            emg_features = {
                'mean_absolute_value': np.mean(processed_emg, axis=0),
                'zero_crossing_rate': self._calculate_zero_crossing(processed_emg),
                'muscle_activation': np.max(processed_emg, axis=0),
                'synergy_pattern': self._extract_synergy_pattern(processed_emg)
            }
            
            # 提取IMU特征
            imu_features = {
                'accel_mean': np.mean(processed_imu[:, :3], axis=0),
                'gyro_mean': np.mean(processed_imu[:, 3:6], axis=0),
                'accel_magnitude': np.mean(processed_imu[:, 6]),
                'gyro_magnitude': np.mean(processed_imu[:, 7]),
                'motion_smoothness': self._calculate_smoothness(processed_imu[:, :6])
            }
            
            # 多模态融合特征
            fusion_features = self._fuse_multimodal_features(
                emg_features, imu_features, visual_features
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'timestamp': timestamp or datetime.now().timestamp(),
                'emg_features': emg_features,
                'motion_features': imu_features,
                'visual_features': visual_features,
                'fusion_features': fusion_features,
                'metadata': {
                    'processing_time_ms': processing_time * 1000,
                    'emg_sample_rate': self.config.emg_sample_rate,
                    'imu_sample_rate': self.config.imu_sample_rate,
                    'video_fps': self.config.video_fps
                }
            }
            
            logger.info("数字孪生编码完成，处理时间: %.2fms", processing_time * 1000)
            
            return result
            
        except Exception as e:
            logger.error("数字孪生编码失败: %s", str(e))
            raise RuntimeError(f"编码过程错误: {str(e)}")
    
    def _calculate_zero_crossing(self, data: np.ndarray) -> np.ndarray:
        """计算过零率"""
        signs = np.sign(data)
        diff = np.diff(signs, axis=0)
        zero_crossings = np.sum(np.abs(diff) > 0, axis=0) / (len(data) - 1)
        return zero_crossings
    
    def _extract_synergy_pattern(self, emg_data: np.ndarray) -> np.ndarray:
        """提取肌肉协同模式（简化版PCA）"""
        # 中心化
        centered = emg_data - np.mean(emg_data, axis=0)
        # 计算协方差矩阵
        cov = np.cov(centered.T)
        # 特征值分解
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # 取前3个主成分
        sorted_idx = np.argsort(eigenvalues)[::-1]
        synergy = eigenvectors[:, sorted_idx[:3]].flatten()
        return synergy
    
    def _calculate_smoothness(self, motion_data: np.ndarray) -> float:
        """计算运动平滑度"""
        # 计算速度
        velocity = np.diff(motion_data, axis=0)
        # 计算加速度
        acceleration = np.diff(velocity, axis=0)
        # 平滑度指标：加速度的变化程度
        jerk = np.diff(acceleration, axis=0)
        smoothness = 1.0 / (1.0 + np.mean(np.abs(jerk)))
        return float(smoothness)
    
    def _fuse_multimodal_features(
        self,
        emg_features: Dict,
        imu_features: Dict,
        visual_features: Dict
    ) -> Dict[str, float]:
        """
        多模态特征融合
        
        将不同模态的特征进行加权融合，生成统一的表示
        """
        # 计算EMG激活强度
        emg_intensity = float(np.mean(emg_features['muscle_activation']))
        
        # 计算运动强度
        motion_intensity = float(imu_features['accel_magnitude'] + imu_features['gyro_magnitude'])
        
        # 计算视觉运动强度
        visual_intensity = float(visual_features['motion_intensity'])
        
        # 加权融合 (权重可根据实际应用调整)
        fusion_score = (
            0.4 * emg_intensity +
            0.3 * motion_intensity +
            0.3 * visual_intensity
        )
        
        # 计算精细度指标
        finesse_score = float(
            emg_features['synergy_pattern'].mean() * 
            imu_features['motion_smoothness']
        )
        
        return {
            'fusion_score': fusion_score,
            'finesse_score': finesse_score,
            'coordination_index': emg_intensity * motion_intensity
        }


# 使用示例
if __name__ == "__main__":
    # 创建配置
    config = SensorConfig(
        emg_sample_rate=2000,
        imu_sample_rate=200,
        video_fps=60,
        buffer_size=256
    )
    
    # 实例化编码器
    encoder = DigitalTwinEncoder(config)
    
    # 模拟生成测试数据
    test_emg = np.random.randn(256, 8) * 0.3
    test_imu = np.random.randn(256, 6) * 0.5
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # 执行编码
    try:
        features = encoder.encode_craft_motion(test_emg, test_imu, test_frame)
        print("数字孪生特征提取成功!")
        print(f"融合得分: {features['fusion_features']['fusion_score']:.4f}")
        print(f"精细度得分: {features['fusion_features']['finesse_score']:.4f}")
    except Exception as e:
        print(f"编码失败: {e}")