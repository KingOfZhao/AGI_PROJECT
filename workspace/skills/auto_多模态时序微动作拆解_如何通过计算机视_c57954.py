"""
多模态时序微动作拆解模块

本模块实现了从非结构化手工艺视频（如陶艺拉坯）中提取高精度'关键帧序列'的功能。
通过计算机视觉技术将连续视频流转化为带有时间戳的'原子操作'序列，
解决隐性知识中'只可意会不可言传'的动作节奏捕捉问题。

典型使用场景:
- 传统手工艺数字化存档
- 技能培训系统
- 动作质量评估

输入格式:
- 视频文件路径 (支持mp4/avi/mov等常见格式)
- 可选的帧采样率参数

输出格式:
- JSON格式的动作序列，包含:
  - 时间戳
  - 动作类别
  - 关键帧图像
  - 置信度评分
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime

import cv2
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AtomicAction:
    """原子操作数据结构"""
    timestamp: float  # 时间戳(秒)
    action_type: str  # 动作类型
    confidence: float  # 置信度(0-1)
    key_frame: np.ndarray  # 关键帧图像
    frame_idx: int  # 帧索引
    motion_vector: Optional[Tuple[float, float]] = None  # 运动向量


class MultiModalActionExtractor:
    """多模态时序微动作拆解器"""
    
    def __init__(self, 
                 video_path: str, 
                 sample_rate: int = 5,
                 motion_threshold: float = 0.2,
                 min_action_duration: float = 0.5):
        """
        初始化动作提取器
        
        参数:
            video_path: 视频文件路径
            sample_rate: 帧采样率(每秒采样帧数)
            motion_threshold: 运动检测阈值(0-1)
            min_action_duration: 最小动作持续时间(秒)
            
        异常:
            FileNotFoundError: 视频文件不存在
            ValueError: 参数验证失败
        """
        self._validate_inputs(video_path, sample_rate, motion_threshold, min_action_duration)
        
        self.video_path = video_path
        self.sample_rate = sample_rate
        self.motion_threshold = motion_threshold
        self.min_action_duration = min_action_duration
        
        # 初始化视频捕获
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"无法打开视频文件: {video_path}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps
        
        logger.info(f"视频加载成功: {video_path} (FPS: {self.fps}, 时长: {self.duration:.2f}s)")
        
        # 预定义动作类别 (实际应用中应从模型加载)
        self.action_classes = [
            "拇指下压", "手掌扶正", "四指收拢", 
            "手腕旋转", "手指微调", "整体提拉"
        ]
        
    def _validate_inputs(self, 
                        video_path: str, 
                        sample_rate: int,
                        motion_threshold: float,
                        min_action_duration: float) -> None:
        """验证输入参数"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        if not 1 <= sample_rate <= 30:
            raise ValueError("采样率必须在1-30之间")
            
        if not 0 < motion_threshold <= 1:
            raise ValueError("运动阈值必须在0-1之间")
            
        if min_action_duration <= 0:
            raise ValueError("最小动作持续时间必须大于0")
    
    def extract_keyframe_sequence(self) -> List[AtomicAction]:
        """
        从视频中提取关键帧序列
        
        返回:
            包含AtomicAction对象的列表，按时间戳排序
            
        异常:
            RuntimeError: 视频处理过程中发生错误
        """
        try:
            actions = []
            prev_frame = None
            frame_idx = 0
            sample_interval = max(1, int(self.fps / self.sample_rate))
            
            logger.info("开始提取关键帧序列...")
            
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                    
                # 仅处理采样帧
                if frame_idx % sample_interval == 0:
                    timestamp = frame_idx / self.fps
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    if prev_frame is not None:
                        # 计算帧间差异
                        motion_score = self._calculate_motion_score(prev_frame, gray_frame)
                        
                        # 如果检测到显著运动，识别动作
                        if motion_score > self.motion_threshold:
                            action_type, confidence = self._classify_action(frame)
                            
                            actions.append(AtomicAction(
                                timestamp=timestamp,
                                action_type=action_type,
                                confidence=confidence,
                                key_frame=frame,
                                frame_idx=frame_idx,
                                motion_vector=self._estimate_motion_vector(prev_frame, gray_frame)
                            ))
                            
                            logger.debug(f"检测到动作: {action_type} (时间: {timestamp:.2f}s, 置信度: {confidence:.2f})")
                    
                    prev_frame = gray_frame
                
                frame_idx += 1
                
            # 后处理: 合并相似动作
            processed_actions = self._merge_similar_actions(actions)
            
            logger.info(f"提取完成，共发现 {len(processed_actions)} 个原子操作")
            return processed_actions
            
        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            raise RuntimeError(f"视频处理失败: {str(e)}")
            
    def _calculate_motion_score(self, 
                               prev_frame: np.ndarray, 
                               current_frame: np.ndarray) -> float:
        """
        计算帧间运动得分
        
        参数:
            prev_frame: 前一帧(灰度图)
            current_frame: 当前帧(灰度图)
            
        返回:
            运动得分(0-1)
        """
        # 计算帧间差异
        diff = cv2.absdiff(prev_frame, current_frame)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # 计算运动像素比例
        motion_pixels = np.count_nonzero(thresh) / thresh.size
        return motion_pixels
    
    def _classify_action(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        分类当前帧中的动作 (模拟实现)
        
        实际应用中应使用预训练模型，这里用随机选择模拟
        
        参数:
            frame: 输入帧图像
            
        返回:
            (动作类别, 置信度) 元组
        """
        # 实际应用中这里应该调用深度学习模型
        # 这里模拟返回随机动作和置信度
        action_type = np.random.choice(self.action_classes)
        confidence = np.random.uniform(0.7, 0.99)
        return action_type, confidence
    
    def _estimate_motion_vector(self, 
                               prev_frame: np.ndarray, 
                               current_frame: np.ndarray) -> Tuple[float, float]:
        """
        估计帧间运动向量 (使用光流法)
        
        参数:
            prev_frame: 前一帧(灰度图)
            current_frame: 当前帧(灰度图)
            
        返回:
            (x方向运动, y方向运动) 向量
        """
        # 使用稠密光流法计算运动向量
        flow = cv2.calcOpticalFlowFarneback(
            prev_frame, current_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        
        # 计算平均运动向量
        avg_flow = np.mean(flow, axis=(0, 1))
        return tuple(avg_flow)
    
    def _merge_similar_actions(self, actions: List[AtomicAction]) -> List[AtomicAction]:
        """
        合并时间上相近且类型相同的动作
        
        参数:
            actions: 原始动作列表
            
        返回:
            处理后的动作列表
        """
        if not actions:
            return []
            
        merged_actions = [actions[0]]
        
        for action in actions[1:]:
            last_action = merged_actions[-1]
            
            # 检查是否为相同动作且时间间隔小于最小持续时间
            if (action.action_type == last_action.action_type and 
                (action.timestamp - last_action.timestamp) < self.min_action_duration):
                
                # 合并动作，保留置信度更高的
                if action.confidence > last_action.confidence:
                    merged_actions[-1] = action
            else:
                merged_actions.append(action)
                
        return merged_actions
    
    def export_to_json(self, 
                      actions: List[AtomicAction], 
                      output_path: str,
                      save_frames: bool = True) -> None:
        """
        将提取的动作序列导出为JSON格式
        
        参数:
            actions: 动作列表
            output_path: 输出文件路径
            save_frames: 是否保存关键帧图像
            
        异常:
            IOError: 文件写入失败
        """
        try:
            output_data = {
                "metadata": {
                    "source_video": self.video_path,
                    "duration": self.duration,
                    "extracted_actions": len(actions),
                    "timestamp": datetime.now().isoformat()
                },
                "actions": []
            }
            
            for action in actions:
                action_data = {
                    "timestamp": action.timestamp,
                    "action_type": action.action_type,
                    "confidence": float(action.confidence),
                    "frame_idx": action.frame_idx,
                }
                
                if save_frames:
                    # 保存关键帧为base64编码
                    _, buffer = cv2.imencode('.jpg', action.key_frame)
                    action_data["key_frame"] = buffer.tobytes().hex()
                
                if action.motion_vector:
                    action_data["motion_vector"] = action.motion_vector
                    
                output_data["actions"].append(action_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"动作序列已导出到: {output_path}")
            
        except Exception as e:
            logger.error(f"导出JSON失败: {str(e)}")
            raise IOError(f"导出JSON失败: {str(e)}")
    
    def __del__(self):
        """释放视频资源"""
        if hasattr(self, 'cap'):
            self.cap.release()


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化提取器
        extractor = MultiModalActionExtractor(
            video_path="pottery_wheel.mp4",
            sample_rate=10,
            motion_threshold=0.15,
            min_action_duration=0.3
        )
        
        # 提取关键帧序列
        actions = extractor.extract_keyframe_sequence()
        
        # 导出结果
        extractor.export_to_json(actions, "extracted_actions.json")
        
        # 打印摘要
        print(f"提取完成，共发现 {len(actions)} 个原子操作:")
        for i, action in enumerate(actions[:5], 1):  # 只显示前5个
            print(f"{i}. [{action.timestamp:.2f}s] {action.action_type} (置信度: {action.confidence:.2f})")
        
    except Exception as e:
        print(f"处理失败: {str(e)}")