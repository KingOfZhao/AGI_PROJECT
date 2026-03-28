```python
"""
名称: auto_非结构化物理动作的语义分割与基元提取_大_3d882f
描述: 非结构化物理动作的语义分割与基元提取：大师的连续动作流（如揉面、雕刻）是模糊且连续的，
      如何利用现有的Skill节点作为“锚点”，将连续流切分为具有语义意义的“动作基元”？
      例如，将一段复杂的修补动作拆解为‘打磨’、‘填补’、‘抹平’等已有节点或新节点的组合。
领域: computer_vision
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ActionSegment:
    """
    动作基元数据结构
    """
    start_frame: int
    end_frame: int
    label: str
    confidence: float
    features: Dict[str, float] = field(default_factory=dict)

class SkillPrimitiveExtractor:
    """
    非结构化物理动作的语义分割与基元提取系统。
    
    该类利用预定义的Skill节点作为锚点，将连续的动作流分割为具有语义意义的动作基元。
    支持对复杂动作序列（如揉面、雕刻等）进行自动分解和识别。
    
    Attributes:
        anchors (Dict[str, np.ndarray]): 预定义的Skill锚点特征字典
        similarity_threshold (float): 动作分割的相似度阈值
        min_segment_length (int): 最小动作片段长度（帧数）
    """
    
    def __init__(self, 
                 anchor_skills: Dict[str, np.ndarray],
                 similarity_threshold: float = 0.75,
                 min_segment_length: int = 10):
        """
        初始化动作基元提取器。
        
        Args:
            anchor_skills: 预定义的Skill锚点特征字典，键为动作名称，值为特征向量
            similarity_threshold: 动作分割的相似度阈值，默认为0.75
            min_segment_length: 最小动作片段长度（帧数），默认为10
            
        Raises:
            ValueError: 如果输入参数验证失败
        """
        self._validate_inputs(anchor_skills, similarity_threshold, min_segment_length)
        self.anchors = anchor_skills
        self.similarity_threshold = similarity_threshold
        self.min_segment_length = min_segment_length
        logger.info("SkillPrimitiveExtractor initialized with %d anchor skills", len(anchor_skills))
    
    def _validate_inputs(self, 
                        anchor_skills: Dict[str, np.ndarray],
                        similarity_threshold: float,
                        min_segment_length: int) -> None:
        """
        验证输入参数的有效性。
        
        Args:
            anchor_skills: 预定义的Skill锚点特征字典
            similarity_threshold: 相似度阈值
            min_segment_length: 最小片段长度
            
        Raises:
            ValueError: 如果参数验证失败
        """
        if not anchor_skills:
            raise ValueError("Anchor skills dictionary cannot be empty")
            
        if not 0 < similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
            
        if min_segment_length <= 0:
            raise ValueError("Minimum segment length must be positive")
            
        for name, features in anchor_skills.items():
            if not isinstance(features, np.ndarray):
                raise ValueError(f"Feature for skill '{name}' must be a numpy array")
            if features.size == 0:
                raise ValueError(f"Feature for skill '{name}' cannot be empty")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度。
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            余弦相似度值 (0-1)
            
        Raises:
            ValueError: 如果向量维度不匹配
        """
        if vec1.shape != vec2.shape:
            raise ValueError("Vector dimensions must match for similarity calculation")
            
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def extract_motion_features(self, 
                              motion_data: np.ndarray,
                              window_size: int = 5) -> np.ndarray:
        """
        从原始运动数据中提取特征向量。
        
        Args:
            motion_data: 原始运动数据 (帧数 × 特征维度)
            window_size: 特征提取的滑动窗口大小
            
        Returns:
            提取的特征矩阵 (帧数 × 特征维度)
            
        Raises:
            ValueError: 如果输入数据无效或窗口大小不合法
        """
        if not isinstance(motion_data, np.ndarray) or motion_data.ndim != 2:
            raise ValueError("Motion data must be a 2D numpy array")
            
        if window_size <= 0:
            raise ValueError("Window size must be positive")
            
        n_frames = motion_data.shape[0]
        if n_frames < window_size:
            raise ValueError("Motion data must have at least window_size frames")
            
        logger.info("Extracting features from motion data with shape %s", motion_data.shape)
        
        # 使用滑动窗口提取特征 (这里使用简单的均值作为示例)
        features = np.zeros_like(motion_data)
        half_window = window_size // 2
        
        for i in range(n_frames):
            start = max(0, i - half_window)
            end = min(n_frames, i + half_window + 1)
            window_data = motion_data[start:end]
            features[i] = np.mean(window_data, axis=0)
        
        logger.info("Feature extraction completed. Output shape: %s", features.shape)
        return features
    
    def segment_motion(self, 
                      motion_features: np.ndarray,
                      merge_similar: bool = True) -> List[ActionSegment]:
        """
        将运动特征序列分割为语义动作基元。
        
        Args:
            motion_features: 运动特征序列 (帧数 × 特征维度)
            merge_similar: 是否合并相邻的相似动作片段
            
        Returns:
            动作基元列表，每个基元包含起止帧、标签和置信度
            
        Raises:
            ValueError: 如果输入特征无效
        """
        if not isinstance(motion_features, np.ndarray) or motion_features.ndim != 2:
            raise ValueError("Motion features must be a 2D numpy array")
            
        n_frames = motion_features.shape[0]
        if n_frames == 0:
            return []
            
        logger.info("Segmenting motion with %d frames", n_frames)
        
        # 计算每帧与所有锚点的相似度
        similarities = np.zeros((n_frames, len(self.anchors)))
        anchor_names = list(self.anchors.keys())
        
        for i, frame_features in enumerate(motion_features):
            for j, anchor_name in enumerate(anchor_names):
                anchor_features = self.anchors[anchor_name]
                similarities[i, j] = self._cosine_similarity(frame_features, anchor_features)
        
        # 初始分割：为每帧分配最相似的锚点标签
        segment_labels = [anchor_names[np.argmax(s)] for s in similarities]
        segment_confidences = [np.max(s) for s in similarities]
        
        # 生成初始动作片段
        segments = []
        current_label = segment_labels[0]
        start_frame = 0
        
        for i in range(1, n_frames):
            if segment_labels[i] != current_label:
                # 结束当前片段并开始新片段
                segments.append(ActionSegment(
                    start_frame=start_frame,
                    end_frame=i-1,
                    label=current_label,
                    confidence=np.mean(segment_confidences[start_frame:i]),
                    features={"avg_similarity": np.mean(similarities[start_frame:i, anchor_names.index(current_label)])}
                ))
                current_label = segment_labels[i]
                start_frame = i
        
        # 添加最后一个片段
        segments.append(ActionSegment(
            start_frame=start_frame,
            end_frame=n_frames-1,
            label=current_label,
            confidence=np.mean(segment_confidences[start_frame:]),
            features={"avg_similarity": np.mean(similarities[start_frame:, anchor_names.index(current_label)])}
        ))
        
        # 合并过短的片段
        if merge_similar:
            segments = self._merge_short_segments(segments)
        
        logger.info("Segmentation completed. Found %d segments", len(segments))
        return segments
    
    def _merge_short_segments(self, segments: List[ActionSegment]) -> List[ActionSegment]:
        """
        合并过短的动作片段。
        
        Args:
            segments: 原始动作片段列表
            
        Returns:
            合并后的动作片段列表
        """
        if not segments:
            return []
            
        merged = []
        current_segment = segments[0]
        
        for next_segment in segments[1:]:
            # 如果当前片段太短，尝试与下一个片段合并
            if (current_segment.end_frame - current_segment.start_frame + 1) < self.min_segment_length:
                # 合并片段
                new_confidence = (current_segment.confidence + next_segment.confidence) / 2
                current_segment = ActionSegment(
                    start_frame=current_segment.start_frame,
                    end_frame=next_segment.end_frame,
                    label=next_segment.label if next_segment.confidence > current_segment.confidence else current_segment.label,
                    confidence=new_confidence,
                    features={
                        "avg_similarity": (current_segment.features["avg_similarity"] + 
                                         next_segment.features["avg_similarity"]) / 2
                    }
                )
            else:
                merged.append(current_segment)
                current_segment = next_segment
        
        # 添加最后一个片段
        merged.append(current_segment)
        
        return merged

# 示例用法
if __name__ == "__main__":
    # 创建模拟锚点特征 (实际应用中应从真实数据加载)
    anchor_skills = {
        "sanding": np.array([0.9, 0.1, 0.2, 0.3]),
        "filling": np.array([0.2, 0.8, 0.1, 0.4]),
        "smoothing": np.array([0.3, 0.2, 0.9, 0.1]),
        "carving": np.array([0.4, 0.3, 0.2, 0.8])
    }
    
    # 初始化提取器
    extractor = SkillPrimitiveExtractor(
        anchor_skills=anchor_skills,
        similarity_threshold=0.7,
        min_segment_length=15
    )
    
    # 创建模拟运动数据 (100帧 × 4维特征)
    np.random.seed(42)
    motion_data = np.random.rand(100, 4)
    
    # 在特定帧范围内注入锚点特征 (模拟特定动作)
    motion_data[10:30] = anchor_skills["sanding"] + np.random.normal(0, 0.1, (20, 4))
    motion_data[50:70] = anchor_skills["filling"] + np.random.normal(0, 0.1, (20, 4))
    
    try:
        # 提取特征
        features = extractor.extract_motion_features(motion_data)
        
        # 分割动作
        segments = extractor.segment_motion(features)
        
        # 打印结果
        print("\nSegmentation Results:")
        for i, segment in enumerate(segments):
            print(f"Segment {i+1}: {segment.label} (frames {segment.start_frame}-{segment.end_frame}), "
                  f"confidence: {segment.confidence:.2f}")
            
    except ValueError as e:
        logger.error("Error in motion processing: %s", str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)