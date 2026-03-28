"""
模块名称: industrial_perception_digitizer.py
描述: 实现工业现场非结构化多模态数据的融合与数字化映射。
      将震动声音、视觉火花、电气时序等异构数据统一映射到高维技能向量空间。
作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pydantic import BaseModel, Field, ValidationError, validator
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型定义 ---

class SensorDataPacket(BaseModel):
    """工业传感器数据包的基类，包含时间戳和数据有效性标记"""
    timestamp: float = Field(..., description="Unix时间戳")
    is_valid: bool = Field(True, description="数据是否有效")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="传感器置信度")

    class Config:
        extra = 'allow'

class AudioVibrationData(SensorDataPacket):
    """音频和震动数据结构"""
    sample_rate: int = Field(..., description="采样率
    waveform: np.ndarray = Field(..., description="原始波形数据")
    frequency_domain: Optional[np.ndarray] = Field(None, description="频域特征(FFT)")

    @validator('waveform', pre=True)
    def check_array(cls, v):
        if not isinstance(v, np.ndarray):
            raise TypeError("waveform must be a numpy array")
        return v

class VisualSparkData(SensorDataPacket):
    """视觉火花/焊接场景数据"""
    frame_id: int = Field(..., description="帧ID")
    roi_features: np.ndarray = Field(..., description="感兴趣区域特征向量 (N维)")
    brightness_mean: float = Field(..., description="平均亮度")

class ElectricalTimeSeries(SensorDataPacket):
    """电流电压时序数据"""
    voltage_rms: float = Field(..., description="电压有效值")
    current_rms: float = Field(..., description="电流有效值")
    power_factor: float = Field(..., ge=-1.0, le=1.0, description="功率因数")
    waveform_harmonics: np.ndarray = Field(..., description="谐波失真向量")

class SkillVectorSpace:
    """
    技能向量空间管理类。
    模拟管理671个技能节点的高维空间，并提供映射接口。
    """
    def __init__(self, dim: int = 512, num_skills: int = 671):
        self.dim = dim
        self.num_skills = num_skills
        # 模拟已存在的技能节点中心点 (Random seed for reproducibility)
        np.random.seed(42)
        self.skill_centroids = np.random.randn(num_skills, dim).astype(np.float32)
        self.skill_centroids /= np.linalg.norm(self.skill_centroids, axis=1, keepdims=True)
        logger.info(f"Initialized SkillVectorSpace with {num_skills} nodes, dim {dim}")

    def find_nearest_skill(self, vector: np.ndarray) -> Tuple[int, float]:
        """寻找最近的技能节点"""
        if vector.shape[0] != self.dim:
            raise ValueError(f"Vector dim mismatch. Expected {self.dim}, got {vector.shape[0]}")
        
        # 归一化输入向量
        vec_norm = vector / (np.linalg.norm(vector) + 1e-8)
        # 计算余弦相似度
        similarities = np.dot(self.skill_centroids, vec_norm)
        best_idx = np.argmax(similarities)
        return best_idx, similarities[best_idx]

# --- 核心功能函数 ---

def extract_modality_features(audio: Optional[AudioVibrationData], 
                              visual: Optional[VisualSparkData], 
                              electrical: Optional[ElectricalTimeSeries]) -> np.ndarray:
    """
    从异构传感器数据中提取特征向量。
    
    步骤:
    1. 数据有效性检查与清洗。
    2. 针对特定模态的特征工程 (降维/统计)。
    3. 拼接为初始特征向量。
    
    Args:
        audio: 音频/震动数据对象
        visual: 视觉数据对象
        electrical: 电气参数数据对象
        
    Returns:
        np.ndarray: 拼接后的原始特征向量
        
    Raises:
        ValueError: 如果所有输入数据均无效
    """
    feature_chunks = []

    # 1. 处理音频/震动 (频域特征提取模拟)
    if audio and audio.is_valid:
        try:
            # 模拟: 取FFT的前64个系数作为特征
            # 在实际工程中这里会用到librosa或scipy.fft
            fft_features = np.abs(np.fft.fft(audio.waveform)[:64])
            feature_chunks.append(fft_features)
            logger.debug("Audio features extracted.")
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
    else:
        # 缺失数据填充
        feature_chunks.append(np.zeros(64))

    # 2. 处理视觉 (ROI特征降维)
    if visual and visual.is_valid:
        try:
            # 模拟: 简单的全局平均池化
            visual_vec = visual.roi_features.mean(axis=0) # 假设输入是 (H, W, C) 或
            if visual_vec.ndim > 1: visual_vec = visual_vec.flatten()
            # 强制截断或填充至128维
            visual_vec = _pad_or_truncate(visual_vec, 128)
            feature_chunks.append(visual_vec)
            logger.debug("Visual features extracted.")
        except Exception as e:
            logger.error(f"Visual processing error: {e}")
    else:
        feature_chunks.append(np.zeros(128))

    # 3. 处理电气 (时序统计)
    if electrical and electrical.is_valid:
        try:
            # 构建特征: [V_rms, I_rms, PF, Harmonics_mean]
            elec_stats = np.array([
                electrical.voltage_rms,
                electrical.current_rms,
                electrical.power_factor,
                np.mean(electrical.waveform_harmonics)
            ])
            feature_chunks.append(elec_stats)
            logger.debug("Electrical features extracted.")
        except Exception as e:
            logger.error(f"Electrical processing error: {e}")
    else:
        feature_chunks.append(np.zeros(4))

    if not feature_chunks:
        raise ValueError("No valid data available for feature extraction")

    return np.concatenate(feature_chunks)


def fuse_and_map_to_space(features: np.ndarray, 
                          target_dim: int = 512, 
                          scaler: Optional[StandardScaler] = None) -> np.ndarray:
    """
    将原始特征向量融合并映射到统一的高维认知空间。
    
    使用线性映射(模拟PCA/全连接层)将不同长度的特征向量投影到
    技能节点所在的统一向量空间，实现‘认知网络’的统一表达。
    
    Args:
        features (np.ndarray): 原始拼接特征 (N,)
        target_dim (int): 目标维度 (需与SkillVectorSpace维度一致)
        scaler (StandardScaler): 可选的数据标准化器 (用于归一化)
        
    Returns:
        np.ndarray: 高维向量空间中的映射向量
    """
    if features.ndim != 1:
        features = features.flatten()
    
    # 边界检查
    if np.any(np.isnan(features)):
        logger.warning("NaN detected in features, replacing with zeros")
        features = np.nan_to_num(features)

    # 1. 标准化 (模拟消除传感器量纲差异)
    # 这里为了演示简单，我们使用简单的L2归一化，实际场景应使用训练好的Scaler
    norm = np.linalg.norm(features)
    if norm > 1e-6:
        normalized_features = features / norm
    else:
        normalized_features = features

    # 2. 维度映射
    # 这里模拟一个线性投影层: 将 raw_dim -> target_dim
    # 在生产环境中，这通常是一个训练好的神经网络层 (如 Torch Linear)
    input_dim = len(normalized_features)
    
    # 使用确定性随机种子生成投影矩阵，确保同一技能映射的一致性
    # 实际上这里应该是 self.projection_layer.weight
    np.random.seed(input_dim) 
    projection_matrix = np.random.randn(input_dim, target_dim).astype(np.float32)
    
    # 投影 (矩阵乘法)
    high_dim_vector = np.dot(normalized_features, projection_matrix)
    
    # 3. 激活/后处理
    # 使用Tanh模拟非线性激活，确保向量值域稳定
    high_dim_vector = np.tanh(high_dim_vector)
    
    return high_dim_vector

# --- 辅助函数 ---

def _pad_or_truncate(vec: np.ndarray, length: int) -> np.ndarray:
    """
    辅助函数：将向量调整为固定长度。
    长则截断，短则补零。
    """
    current_len = len(vec)
    if current_len == length:
        return vec
    elif current_len > length:
        return vec[:length]
    else:
        pad_width = length - current_len
        return np.pad(vec, (0, pad_width), 'constant', constant_values=0)

# --- 主逻辑与示例 ---

def run_perception_pipeline(
    audio_data: Dict, 
    visual_data: Dict, 
    elec_data: Dict
) -> Dict[str, Any]:
    """
    完整的感知数字化管道。
    
    输入格式说明:
    - audio_data: 包含 'timestamp', 'waveform'(list/np.array), 'sample_rate'
    - visual_data: 包含 'timestamp', 'roi_features'(list/np.array), 'brightness'
    - elec_data: 包含 'timestamp', 'voltage', 'current', 'pf', 'harmonics'
    
    输出格式说明:
    - Dict: 包含 'skill_id', 'similarity', 'vector_norm'
    """
    logger.info("Starting perception digitization pipeline...")
    
    try:
        # 1. 数据验证与解析
        a_obj = AudioVibrationData(**audio_data)
        v_obj = VisualSparkData(**visual_data)
        e_obj = ElectricalTimeSeries(**elec_data)
        
        # 2. 特征提取
        raw_features = extract_modality_features(a_obj, v_obj, e_obj)
        logger.info(f"Extracted raw feature vector of size: {raw_features.shape}")
        
        # 3. 空间映射
        # 假设我们的认知空间是 128维 (为了演示速度，实际可能更高)
        mapping_dim = 128 
        skill_space = SkillVectorSpace(dim=mapping_dim)
        
        final_vector = fuse_and_map_to_space(raw_features, target_dim=mapping_dim)
        
        # 4. 技能匹配
        skill_id, similarity = skill_space.find_nearest_skill(final_vector)
        
        result = {
            "status": "success",
            "mapped_skill_node": int(skill_id),
            "confidence": float(similarity),
            "vector_norm": float(np.linalg.norm(final_vector)),
            "timestamp": audio_data.get("timestamp", 0)
        }
        
        logger.info(f"Pipeline completed. Mapped to Skill #{skill_id} with similarity {similarity:.4f}")
        return result

    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Pipeline runtime error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # --- 模拟数据生成 ---
    # 模拟 1秒 的震动数据
    dummy_audio = {
        "timestamp": 1678886400.0,
        "sample_rate": 16000,
        "waveform": np.random.normal(0, 1, 16000).astype(np.float32),
        "is_valid": True
    }
    
    # 模拟视觉特征 (例如 ResNet 倒数第二层输出, 展平后)
    dummy_visual = {
        "timestamp": 1678886400.1,
        "frame_id": 1024,
        "roi_features": np.random.rand(256).astype(np.float32), # 假设提取了256维特征
        "brightness_mean": 220.5,
        "is_valid": True
    }
    
    # 模拟电气参数
    dummy_elec = {
        "timestamp": 1678886400.1,
        "voltage_rms": 380.2,
        "current_rms": 12.5,
        "power_factor": 0.98,
        "waveform_harmonics": np.array([0.1, 0.05, 0.02, 0.01]),
        "is_valid": True
    }

    # 运行管道
    result = run_perception_pipeline(dummy_audio, dummy_visual, dummy_elec)
    print("\n--- Pipeline Output ---")
    print(result)