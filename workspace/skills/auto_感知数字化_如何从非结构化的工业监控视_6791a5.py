"""
模块名称: tacit_feature_extractor
描述: 本模块用于从非结构化的工业监控视频中提取并量化老师傅的“隐性动作特征”。
      通过结合 MediaPipe 姿态估计与自定义物理/时序算法，将难以捕捉的“手感”
      （如敲击力度、手势微停顿）转化为可计算的时序向量。

依赖:
    - opencv-python
    - mediapipe
    - numpy
    - pandas

输入格式:
    - 视频文件路径 (支持 .mp4, .avi)
    - 或 RTSP 流地址

输出格式:
    - JSON 文件，包含时间戳与特征向量
    - 特征向量维度示例: [timestamp, velocity, acceleration, jerk, inferred_force, pause_score]
"""

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import logging
import json
import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 定义数据结构
@dataclass
class MotionFeature:
    """存储单帧动作特征的Data Class"""
    timestamp_ms: float
    hand_position: Tuple[float, float, float]  # x, y, z 坐标
    velocity: float          # 速度
    acceleration: float      # 加速度
    jerk: float              # 加加速度
    inferred_force: float    # 推断的力度 (基于加速度质量模型)
    pause_score: float       # 停顿得分 (0-1, 越高越可能是停顿)

@dataclass
class ExtractionConfig:
    """配置参数"""
    force_mass_estimate: float = 1.0  # 估算的工具/手部质量
    smoothing_window: int = 5         # 平滑窗口大小
    velocity_threshold: float = 0.01  # 判定静止的速度阈值
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.5

class TacitFeatureExtractor:
    """
    核心类：用于从视频中提取隐性动作特征。
    
    主要流程:
    1. 视频解码与帧提取
    2. 手部/姿态关键点检测
    3. 轨迹平滑与滤波
    4. 运动学特征计算 (v, a, jerk)
    5. 隐性特征映射 (力度推断, 停顿检测)
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        初始化提取器。
        
        Args:
            config (ExtractionConfig, optional): 配置对象。如果为None则使用默认配置。
        """
        self.config = config if config else ExtractionConfig()
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # 初始化 MediaPipe Hands
        self.hands_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # 假设主要关注一只手操作工具
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence
        )
        logger.info("TacitFeatureExtractor 初始化完成。")

    def _validate_video_source(self, source: str) -> bool:
        """
        辅助函数：验证视频源是否有效。
        
        Args:
            source (str): 视频文件路径或流地址。
            
        Returns:
            bool: 是否有效。
        """
        if not isinstance(source, str):
            logger.error(f"无效的源类型: {type(source)}")
            return False
        
        # 简单检查文件是否存在（如果是文件路径）
        if not source.startswith(('rtsp://', 'http://', 'https://')):
            if not os.path.exists(source):
                logger.error(f"文件不存在: {source}")
                return False
        return True

    def _calculate_kinematics(self, positions: List[Tuple[float, float, float]], timestamps: List[float]) -> List[Dict[str, Any]]:
        """
        核心函数：根据位置序列计算运动学特征。
        
        Args:
            positions: 手部关键点坐标列表。
            timestamps: 对应的时间戳列表。
            
        Returns:
            包含计算后特征的字典列表。
        """
        if len(positions) < 3:
            logger.warning("数据点不足，无法计算二阶导数。")
            return []

        features = []
        
        # 转换为 numpy 数组以便向量化计算
        pos_array = np.array(positions)
        ts_array = np.array(timestamps)
        
        # 1. 计算位移差分
        # delta_p = np.diff(pos_array, axis=0)
        # delta_t = np.diff(ts_array)
        
        # 使用中心差分法提高数值稳定性（如果点数足够），这里为了演示使用简单差分
        # 但为了平滑效果，实际应用建议使用 Savitzky-Golay 滤波器
        
        # 平滑处理 (简单移动平均)
        # 实际工程中可用 signal.savgol_filter
        df = pd.DataFrame(pos_array, columns=['x', 'y', 'z'])
        df_smooth = df.rolling(window=self.config.smoothing_window, min_periods=1).mean().values
        
        # 计算速度 (欧几里得距离/时间)
        velocities = [0.0]
        for i in range(1, len(df_smooth)):
            dist = np.linalg.norm(df_smooth[i] - df_smooth[i-1])
            dt = (ts_array[i] - ts_array[i-1]) / 1000.0 # ms -> s
            if dt > 0:
                v = dist / dt
            else:
                v = 0.0
            velocities.append(v)
            
        # 计算加速度
        accelerations = [0.0]
        for i in range(1, len(velocities)):
            dv = velocities[i] - velocities[i-1]
            dt = (ts_array[i] - ts_array[i-1]) / 1000.0
            if dt > 0:
                a = dv / dt
            else:
                a = 0.0
            accelerations.append(a)
            
        # 计算加加速度
        jerks = [0.0]
        for i in range(1, len(accelerations)):
            da = accelerations[i] - accelerations[i-1]
            dt = (ts_array[i] - ts_array[i-1]) / 1000.0
            if dt > 0:
                j = da / dt
            else:
                j = 0.0
            jerks.append(j)
            
        # 合并特征
        for i in range(len(df_smooth)):
            # 推断力度: F = m * |a|
            inferred_force = self.config.force_mass_estimate * abs(accelerations[i])
            
            # 停顿检测: 如果速度低于阈值，且加速度接近0
            is_pause = 1.0 if velocities[i] < self.config.velocity_threshold else 0.0
            
            feat = {
                "timestamp_ms": ts_array[i],
                "position": tuple(df_smooth[i]),
                "velocity": velocities[i],
                "acceleration": accelerations[i],
                "jerk": jerks[i],
                "inferred_force": inferred_force,
                "pause_score": is_pause
            }
            features.append(feat)
            
        return features

    def extract_features_from_video(self, video_source: str, output_json: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        核心函数：主处理流程，从视频提取特征。
        
        Args:
            video_source (str): 视频路径或流。
            output_json (str, optional): 如果提供，将结果保存为JSON。
            
        Returns:
            List[Dict]: 提取的特征向量列表。
        """
        if not self._validate_video_source(video_source):
            raise ValueError(f"无法打开视频源: {video_source}")

        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.error("无法打开视频流。")
            return []

        raw_positions = []
        timestamps = []
        frame_count = 0

        logger.info("开始处理视频帧...")
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # 获取时间戳 (如果是文件，使用帧数推算；如果是流，使用当前时间)
                # 这里简单使用帧计数模拟时间戳，实际应读取 cap.get(cv2.CAP_PROP_POS_MSEC)
                current_time_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                
                # BGR -> RGB
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                
                # 检测
                results = self.hands_detector.process(image)
                
                image.flags.writeable = True
                
                # 提取关键点
                if results.multi_hand_landmarks:
                    # 仅取第一只检测到的手
                    hand_landmarks = results.multi_hand_landmarks[0]
                    
                    # 提取手腕位置作为主要追踪点 (Landmark 0)
                    # 也可以计算所有关键点的质心
                    wrist = hand_landmarks.landmark[0] 
                    
                    # MediaPipe 返回的是相对坐标，需要根据帧宽高转回绝对坐标或保留归一化
                    # 这里保留归一化坐标 [0,1]，但添加 Z 轴深度
                    pos = (wrist.x, wrist.y, wrist.z)
                    
                    raw_positions.append(pos)
                    timestamps.append(current_time_ms)
                    
                    # 可视化 (可选，在生产环境中通常关闭以提速)
                    # self.mp_drawing.draw_landmarks(
                    #     frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                frame_count += 1
                if frame_count % 100 == 0:
                    logger.debug(f"已处理 {frame_count} 帧...")

        except Exception as e:
            logger.error(f"处理视频时发生错误: {e}", exc_info=True)
        finally:
            cap.release()
            logger.info(f"视频处理结束，共 {frame_count} 帧。")

        # 数据验证
        if len(raw_positions) < self.config.smoothing_window:
            logger.warning("检测到的有效帧太少，无法生成有效特征。")
            return []

        # 计算运动学特征
        logger.info("正在计算运动学特征与隐性指标...")
        calculated_features = self._calculate_kinematics(raw_positions, timestamps)
        
        # 输出保存
        if output_json and calculated_features:
            try:
                with open(output_json, 'w') as f:
                    json.dump(calculated_features, f, indent=4)
                logger.info(f"特征数据已保存至: {output_json}")
            except IOError as e:
                logger.error(f"无法写入文件 {output_json}: {e}")

        return calculated_features

# 使用示例
if __name__ == "__main__":
    # 创建一个模拟配置
    config = ExtractionConfig(
        force_mass_estimate=0.8,  # 假设手持工具重0.8kg
        smoothing_window=3
    )
    
    extractor = TacitFeatureExtractor(config=config)
    
    # 示例：如果有一个名为 'demo.mp4' 的视频
    # features = extractor.extract_features_from_video('demo.mp4', 'output_features.json')
    
    # 由于当前环境没有视频文件，这里演示调用逻辑（会返回空列表或错误，取决于是否有文件）
    # 为展示代码可运行性，此处仅打印初始化成功信息
    print("模块加载成功。实例化对象:", extractor)
    
    # 伪运行示例
    dummy_video = "industrial_operation_sample.mp4" 
    if os.path.exists(dummy_video):
        data = extractor.extract_features_from_video(dummy_video)
        print(f"提取到 {len(data)} 个特征点")
        if data:
            print("第一帧特征:", data[0])
    else:
        print(f"未找到示例视频文件 {dummy_video}，跳过处理步骤。")