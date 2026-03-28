"""
工业场景多模态维修数据结构化解析模块

该模块实现了从非结构化的工业维修数据（音频、视频）中提取关键信息，
并将其转化为结构化的【故障现象-操作动作-结果状态】三元组。

核心功能：
1. 音频特征提取与语义解析
2. 视频关键帧分析与动作识别
3. 多模态数据融合与三元组生成
4. 噪声过滤与逻辑连贯性校验

输入格式：
- 音频数据: numpy数组, 采样率16kHz, 单声道
- 视频数据: numpy数组, shape=(frames, height, width, channels), RGB格式
- 已知故障现象: List[Dict], 每个Dict包含'id', 'name', 'keywords'字段

输出格式：
- 三元组列表: List[Dict], 每个Dict包含'fault', 'action', 'result'字段
- 置信度评分: float, 范围[0.0, 1.0]
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, conlist, validator

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('industrial_data_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FaultPhenomenon(BaseModel):
    """故障现象数据模型"""
    id: str
    name: str
    keywords: List[str]
    threshold: float = 0.7

    @validator('keywords')
    def validate_keywords(cls, v):
        if not v:
            raise ValueError("关键词列表不能为空")
        return v


class MaintenanceTriple(BaseModel):
    """维修三元组数据模型"""
    fault: str
    action: str
    result: str
    confidence: float
    timestamp: str
    source_frame: Optional[int] = None
    source_audio_segment: Optional[Tuple[float, float]] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("置信度必须在0.0到1.0之间")
        return v


@dataclass
class AudioSegment:
    """音频分段数据结构"""
    start_time: float
    end_time: float
    transcript: str
    confidence: float
    keywords: List[str]


def _validate_input_data(audio_data: np.ndarray, video_data: np.ndarray) -> bool:
    """
    验证输入数据的完整性和合法性
    
    参数:
        audio_data: 音频数据数组
        video_data: 视频数据数组
    
    返回:
        bool: 数据是否有效
        
    异常:
        ValueError: 当数据格式不符合要求时
    """
    if audio_data is None or video_data is None:
        raise ValueError("音频和视频数据不能为空")
    
    if len(audio_data.shape) != 1:
        raise ValueError("音频数据必须是单声道一维数组")
    
    if len(video_data.shape) != 4:
        raise ValueError("视频数据必须是四维数组(frames, height, width, channels)")
    
    if video_data.shape[3] != 3:
        raise ValueError("视频数据必须是RGB三通道格式")
    
    return True


def extract_audio_features(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    noise_threshold: float = 0.02
) -> List[AudioSegment]:
    """
    从音频数据中提取特征并生成文本分段
    
    参数:
        audio_data: 音频数据数组, shape=(samples,)
        sample_rate: 音频采样率, 默认16kHz
        noise_threshold: 噪声过滤阈值
    
    返回:
        List[AudioSegment]: 包含转录文本和元数据的音频分段列表
        
    示例:
        >>> audio = np.random.randn(16000 * 10)  # 10秒模拟音频
        >>> segments = extract_audio_features(audio)
        >>> print(len(segments))
        3  # 根据语音活动检测分段
    """
    logger.info("开始音频特征提取，数据长度: %.2f秒", len(audio_data) / sample_rate)
    
    # 模拟语音活动检测 (VAD)
    frame_size = int(sample_rate * 0.03)  # 30ms帧
    frames = [
        audio_data[i:i+frame_size]
        for i in range(0, len(audio_data), frame_size)
        if i + frame_size <= len(audio_data)
    ]
    
    # 计算每帧能量
    energies = [np.sum(np.square(frame)) for frame in frames]
    energy_threshold = np.percentile(energies, 70)  # 使用70百分位作为阈值
    
    # 识别活跃段
    active_segments = []
    current_start = None
    
    for i, energy in enumerate(energies):
        if energy > energy_threshold and current_start is None:
            current_start = i * frame_size / sample_rate
        elif energy <= energy_threshold and current_start is not None:
            end_time = i * frame_size / sample_rate
            if end_time - current_start > 0.5:  # 忽略短于0.5秒的段
                active_segments.append((current_start, end_time))
            current_start = None
    
    # 模拟语音识别 (ASR)
    transcripts = [
        "设备振动异常，声音比平时大",
        "检查了电机底座螺丝",
        "紧固了松动的螺丝",
        "振动明显减小了"
    ][:len(active_segments)]  # 只取与分段数量相同的文本
    
    # 创建音频分段对象
    audio_segments = []
    keywords = [
        ["振动", "异常", "声音"],
        ["检查", "电机", "螺丝"],
        ["紧固", "松动"],
        ["振动", "减小"]
    ]
    
    for i, (start, end) in enumerate(active_segments[:len(transcripts)]):
        audio_segments.append(AudioSegment(
            start_time=start,
            end_time=end,
            transcript=transcripts[i],
            confidence=np.random.uniform(0.7, 0.95),
            keywords=keywords[i] if i < len(keywords) else []
        ))
    
    logger.info("音频处理完成，识别出%d个有效分段", len(audio_segments))
    return audio_segments


def analyze_video_frames(
    video_data: np.ndarray,
    keyframe_threshold: float = 0.3,
    motion_threshold: float = 0.15
) -> List[Dict[str, Union[int, float, str]]]:
    """
    分析视频帧并提取关键动作节点
    
    参数:
        video_data: 视频数据数组, shape=(frames, height, width, channels)
        keyframe_threshold: 关键帧检测阈值
        motion_threshold: 运动检测阈值
    
    返回:
        List[Dict]: 关键帧信息列表，每项包含帧索引、时间戳、动作描述和置信度
        
    示例:
        >>> video = np.random.randint(0, 255, (100, 480, 640, 3), dtype=np.uint8)
        >>> keyframes = analyze_video_frames(video)
        >>> print(len(keyframes))
        5  # 提取的关键帧数量
    """
    logger.info("开始视频分析，总帧数: %d", video_data.shape[0])
    
    # 计算帧间差异
    frame_diffs = []
    for i in range(1, len(video_data)):
        diff = np.mean(np.abs(video_data[i].astype(float) - video_data[i-1].astype(float)))
        frame_diffs.append(diff)
    
    # 识别关键帧
    avg_diff = np.mean(frame_diffs)
    keyframes = []
    
    for i, diff in enumerate(frame_diffs):
        if diff > avg_diff * (1 + keyframe_threshold):
            keyframes.append({
                'frame_index': i + 1,
                'timestamp': (i + 1) / 30.0,  # 假设30fps
                'motion_intensity': diff,
                'confidence': min(diff / (avg_diff * 2), 1.0)
            })
    
    # 模拟动作识别 (实际应用中会使用CNN等模型)
    action_labels = [
        "接近设备",
        "检查电机",
        "使用工具",
        "紧固螺丝",
        "测试设备"
    ]
    
    # 为关键帧分配动作标签
    for i, kf in enumerate(keyframes[:len(action_labels)]):
        kf['action'] = action_labels[i]
    
    logger.info("视频分析完成，识别出%d个关键帧", len(keyframes))
    return keyframes


def align_semantics(
    audio_segments: List[AudioSegment],
    video_keyframes: List[Dict],
    known_faults: List[FaultPhenomenon],
    min_confidence: float = 0.6
) -> List[MaintenanceTriple]:
    """
    将音频和视频特征与已知故障现象进行语义对齐，生成维修三元组
    
    参数:
        audio_segments: 音频分段列表
        video_keyframes: 视频关键帧列表
        known_faults: 已知故障现象列表
        min_confidence: 最小置信度阈值
    
    返回:
        List[MaintenanceTriple]: 生成的维修三元组列表
        
    示例:
        >>> faults = [FaultPhenomenon(id='f1', name='振动异常', keywords=['振动', '异常'])]
        >>> triples = align_semantics(audio_segments, video_keyframes, faults)
        >>> print(triples[0].fault)
        '振动异常'
    """
    logger.info("开始语义对齐，已知故障现象: %d", len(known_faults))
    
    triples = []
    
    # 1. 识别故障现象
    fault_match = None
    for segment in audio_segments:
        for fault in known_faults:
            match_score = sum(
                1 for kw in fault.keywords if kw in segment.transcript
            ) / len(fault.keywords)
            
            if match_score >= fault.threshold:
                fault_match = fault.name
                break
        if fault_match:
            break
    
    if not fault_match:
        logger.warning("未能识别匹配的故障现象")
        return []
    
    # 2. 提取操作动作和结果状态
    actions = []
    results = []
    
    # 从音频提取
    action_keywords = ["检查", "紧固", "更换", "调整"]
    result_keywords = ["正常", "减小", "恢复", "解决"]
    
    for segment in audio_segments:
        for kw in action_keywords:
            if kw in segment.transcript:
                actions.append(f"{kw}操作")
                break
        
        for kw in result_keywords:
            if kw in segment.transcript:
                results.append(f"状态{kw}")
                break
    
    # 从视频提取补充信息
    for kf in video_keyframes:
        if 'action' in kf and kf['confidence'] > min_confidence:
            if "检查" in kf['action']:
                actions.append("检查操作")
            elif "紧固" in kf['action']:
                actions.append("紧固操作")
    
    # 3. 生成三元组
    if actions and results:
        triple = MaintenanceTriple(
            fault=fault_match,
            action=" -> ".join(actions[:3]),  # 限制动作数量
            result=" -> ".join(results[:2]),
            confidence=np.mean([
                seg.confidence for seg in audio_segments[:3]
            ]),
            timestamp=datetime.now().isoformat(),
            source_frame=video_keyframes[0]['frame_index'] if video_keyframes else None,
            source_audio_segment=(
                audio_segments[0].start_time,
                audio_segments[0].end_time
            ) if audio_segments else None
        )
        triples.append(triple)
    
    logger.info("语义对齐完成，生成%d个三元组", len(triples))
    return triples


def process_maintenance_data(
    audio_data: np.ndarray,
    video_data: np.ndarray,
    known_faults: List[Dict],
    sample_rate: int = 16000
) -> List[Dict]:
    """
    处理多模态维修数据并生成结构化三元组的主函数
    
    参数:
        audio_data: 音频数据数组
        video_data: 视频数据数组
        known_faults: 已知故障现象字典列表
        sample_rate: 音频采样率
    
    返回:
        List[Dict]: 结构化的维修三元组字典列表
        
    示例:
        >>> # 模拟数据
        >>> audio = np.random.randn(16000 * 30)  # 30秒音频
        >>> video = np.random.randint(0, 255, (900, 480, 640, 3), dtype=np.uint8)  # 30秒视频
        >>> faults = [{'id': 'f1', 'name': '振动异常', 'keywords': ['振动', '异常']}]
        >>> result = process_maintenance_data(audio, video, faults)
        >>> print(result[0]['fault'])
        '振动异常'
    """
    logger.info("开始处理多模态维修数据")
    
    try:
        # 验证输入数据
        _validate_input_data(audio_data, video_data)
        
        # 转换故障现象为模型对象
        fault_models = [FaultPhenomenon(**f) for f in known_faults]
        
        # 处理音频
        audio_segments = extract_audio_features(audio_data, sample_rate)
        
        # 处理视频
        keyframes = analyze_video_frames(video_data)
        
        # 语义对齐生成三元组
        triples = align_semantics(audio_segments, keyframes, fault_models)
        
        # 转换为字典格式
        result = [triple.dict() for triple in triples]
        
        logger.info("数据处理完成，生成%d个有效三元组", len(result))
        return result
        
    except Exception as e:
        logger.error("数据处理过程中发生错误: %s", str(e), exc_info=True)
        raise


if __name__ == "__main__":
    # 示例用法
    try:
        # 生成模拟数据
        sample_audio = np.random.randn(16000 * 30)  # 30秒模拟音频
        sample_video = np.random.randint(
            0, 255, (900, 480, 640, 3), dtype=np.uint8
        )  # 30秒模拟视频
        
        known_faults = [
            {
                'id': 'f001',
                'name': '设备振动异常',
                'keywords': ['振动', '异常', '声音大'],
                'threshold': 0.6
            },
            {
                'id': 'f002',
                'name': '电机过热',
                'keywords': ['温度', '热', '烫手'],
                'threshold': 0.7
            }
        ]
        
        # 处理数据
        result_triples = process_maintenance_data(
            sample_audio,
            sample_video,
            known_faults
        )
        
        # 打印结果
        print("\n生成的维修三元组:")
        for i, triple in enumerate(result_triples, 1):
            print(f"\n三元组 #{i}:")
            print(f"故障现象: {triple['fault']}")
            print(f"操作动作: {triple['action']}")
            print(f"结果状态: {triple['result']}")
            print(f"置信度: {triple['confidence']:.2f}")
            
    except Exception as e:
        print(f"处理失败: {str(e)}")