"""
Module: auto_针对_肌肉记忆_的隐性特征_研究如何利用_423879
Description: 针对'肌肉记忆'的隐性特征，研究如何利用EMG（肌电图）信号或计算机视觉估算的肌肉张力，
             构建'生理状态-动作质量'关联模型。验证'松弛感'或'爆发力'等主观词汇在生理信号上的
             具体数值分布，将其固化为AI可理解的真实节点。
Domain: Biomechanics / AGI Skills
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pydantic import BaseModel, Field, validator, ValidationError

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# 数据模型定义
# ==========================================

class PhysiologicalSignal(BaseModel):
    """生理信号输入数据模型"""
    timestamp: float = Field(..., description="时间戳
    emg_signal: List[float] = Field(..., description="EMG原始信号序列 (毫伏)")
    joint_angles: Optional[List[float]] = Field(None, description="关节角度序列 (度)")
    
    @validator('emg_signal')
    def validate_emg(cls, v):
        if not v:
            raise ValueError("EMG信号不能为空")
        if len(v) < 10:
            logger.warning("EMG信号长度过短，可能影响分析精度")
        return v

class SubjectiveLabels(BaseModel):
    """主观标签数据模型"""
    relaxation_score: float = Field(..., ge=0, le=1, description="松弛感评分 [0-1]")
    explosiveness_score: float = Field(..., ge=0, le=1, description="爆发力评分 [0-1]")
    movement_quality: float = Field(..., ge=0, le=1, description="整体动作质量 [0-1]")

class MuscleMemoryNode(BaseModel):
    """固化后的AI可理解的肌肉记忆节点"""
    node_id: str
    feature_vector: List[float]
    subjective_mapping: Dict[str, float]
    confidence: float

# ==========================================
# 核心函数实现
# ==========================================

def extract_implicit_features(signal_data: PhysiologicalSignal) -> Dict[str, float]:
    """
    从生理信号中提取隐性特征，计算肌肉激活度、张力变化率等关键指标。
    
    Args:
        signal_data: 包含EMG信号和可选的关节角度数据的结构化输入
        
    Returns:
        Dict[str, float]: 包含以下特征的字典:
            - rms_amplitude: 均方根振幅 (肌肉激活强度)
            - mean_frequency: 平均功率频率 (肌肉疲劳度指标)
            - co_contraction_index: 拮抗肌协同收缩指数 (僵硬/松弛度)
            - smoothness_index: 动作平滑度 (基于关节角度变化)
            - onset_rate: 肌肉激活上升速率 (爆发力指标)
            
    Raises:
        ValueError: 如果输入数据不符合要求
        RuntimeError: 如果特征计算过程中出现数学错误
    """
    logger.info(f"开始处理时间戳 {signal_data.timestamp} 的信号数据")
    
    try:
        # 数据预处理
        emg = np.array(signal_data.emg_signal)
        
        # 去除直流偏置
        emg = emg - np.mean(emg)
        
        # 1. 计算RMS振幅 (肌肉激活强度)
        rms = np.sqrt(np.mean(emg ** 2))
        
        # 2. 计算平均功率频率 (需要简单的频域分析)
        # 这里使用简化的过零率近似，实际应用应使用FFT
        zero_crossings = np.where(np.diff(np.sign(emg)))[0]
        mean_freq = len(zero_crossings) / (len(emg) * 0.001) if len(emg) > 0 else 0.0
        
        # 3. 估算协同收缩指数 (模拟拮抗肌数据)
        # 假设信号中包含主动肌和拮抗肌的混合成分
        # 这里使用信号变异系数的倒数作为松弛度的代理指标
        coeff_var = np.std(emg) / (np.mean(np.abs(emg)) + 1e-8)
        co_contraction = 1.0 / (1.0 + coeff_var)  # 值越高，表示越僵硬
        
        # 4. 动作平滑度 (如果提供了关节角度)
        smoothness = 0.0
        if signal_data.joint_angles:
            angles = np.array(signal_data.joint_angles)
            if len(angles) > 2:
                # 使用速度的加加速度 作为平滑度指标
                velocity = np.diff(angles)
                acceleration = np.diff(velocity)
                jerk = np.diff(acceleration)
                smoothness = 1.0 / (1.0 + np.std(jerk))  # 值越高越平滑
        
        # 5. 爆发力指标 (激活上升速率)
        # 模拟寻找激活起始点
        threshold = np.mean(np.abs(emg)) + 2 * np.std(emg)
        above_thresh = np.where(np.abs(emg) > threshold)[0]
        onset_rate = 0.0
        if len(above_thresh) > 1:
            # 计算10%-90%上升时间
            start = above_thresh[0]
            end = above_thresh[-1]
            rise_time = (end - start) * 0.001  # 假设采样率1000Hz
            amplitude_diff = np.max(emg) - np.min(emg)
            onset_rate = amplitude_diff / (rise_time + 1e-8)
        
        features = {
            "rms_amplitude": float(rms),
            "mean_frequency": float(mean_freq),
            "co_contraction_index": float(co_contraction),
            "smoothness_index": float(smoothness),
            "onset_rate": float(onset_rate)
        }
        
        logger.debug(f"提取的特征: {features}")
        return features
        
    except ZeroDivisionError as zde:
        logger.error(f"数学计算错误: {zde}")
        raise RuntimeError("特征计算失败：除零错误") from zde
    except Exception as e:
        logger.error(f"特征提取未知错误: {e}")
        raise RuntimeError(f"处理失败: {e}") from e

def correlate_physio_subjective(
    features: Dict[str, float], 
    subjective: SubjectiveLabels,
    historical_nodes: Optional[List[MuscleMemoryNode]] = None
) -> MuscleMemoryNode:
    """
    构建生理状态与主观评价的关联模型，生成固化的AI节点。
    
    此函数分析提取的特征与主观标签（如'松弛感'）之间的映射关系，
    并将其转换为可供AGI系统调用的向量表示。
    
    Args:
        features: extract_implicit_features 提取的特征字典
        subjective: 对应的主观评分标签
        historical_nodes: 历史数据节点，用于校准模型 (可选)
        
    Returns:
        MuscleMemoryNode: 包含特征向量和主观映射的固化节点
        
    Raises:
        ValidationError: 如果数据验证失败
    """
    logger.info("正在构建生理-主观关联模型...")
    
    # 边界检查
    if not features:
        raise ValueError("特征字典不能为空")
        
    try:
        # 将特征标准化为向量
        feature_keys = sorted(features.keys())
        vector = np.array([features[k] for k in feature_keys])
        
        # 简单的归一化处理 (实际应用应使用训练好的Scaler)
        # 这里假设我们知道大概的物理范围
        norm_bounds = {
            "rms_amplitude": (0.0, 5.0),
            "mean_frequency": (0.0, 500.0),
            "co_contraction_index": (0.0, 1.0),
            "smoothness_index": (0.0, 1.0),
            "onset_rate": (0.0, 1000.0)
        }
        
        normalized_vector = []
        for k in feature_keys:
            val = features[k]
            min_v, max_v = norm_bounds.get(k, (0.0, 1.0))
            norm_val = (val - min_v) / (max_v - min_v + 1e-8)
            normalized_vector.append(np.clip(norm_val, 0.0, 1.0))
            
        # 验证'松弛感'假设：
        # 假设松弛感与低协同收缩指数(co_contraction)和高平滑度正相关
        calculated_relaxation = (
            (1.0 - features.get("co_contraction_index", 0.5)) * 0.6 +
            features.get("smoothness_index", 0.5) * 0.4
        )
        
        # 验证'爆发力'假设：
        # 假设爆发力与高RMS和高Onset Rate正相关
        calculated_explosiveness = (
            features.get("rms_amplitude", 0.0) / 5.0 * 0.5 +
            features.get("onset_rate", 0.0) / 1000.0 * 0.5
        )
        
        # 固化映射关系
        mapping = {
            "relaxation": float(subjective.relaxation_score),
            "inferred_relaxation": float(calculated_relaxation),
            "explosiveness": float(subjective.explosiveness_score),
            "inferred_explosiveness": float(calculated_explosiveness),
            "quality_weight": float(subjective.movement_quality)
        }
        
        # 计算置信度 (基于主观评分与推断值的一致性)
        diff_relax = abs(mapping["relaxation"] - mapping["inferred_relaxation"])
        diff_expl = abs(mapping["explosiveness"] - mapping["inferred_explosiveness"])
        confidence = 1.0 - (diff_relax + diff_expl) / 2.0
        
        # 创建节点
        node = MuscleMemoryNode(
            node_id=f"MM_{int(signal_data.timestamp * 1000)}" if 'signal_data' in globals() else "MM_Sim",
            feature_vector=normalized_vector,
            subjective_mapping=mapping,
            confidence=float(np.clip(confidence, 0.0, 1.0))
        )
        
        logger.info(f"节点生成成功，置信度: {node.confidence:.2f}")
        return node
        
    except Exception as e:
        logger.error(f"模型构建失败: {e}")
        raise

# ==========================================
# 辅助函数
# ==========================================

def simulate_emg_signal(
    duration_sec: float = 2.0, 
    sample_rate: int = 1000,
    signal_type: str = "explosive"
) -> Tuple[PhysiologicalSignal, SubjectiveLabels]:
    """
    辅助函数：生成模拟的EMG信号和对应的主观标签，用于测试和演示。
    
    Args:
        duration_sec: 信号持续时间（秒）
        sample_rate: 采样率
        signal_type: 信号类型 ('relaxed', 'explosive', 'random')
        
    Returns:
        Tuple[PhysiologicalSignal, SubjectiveLabels]: 模拟数据和标签
    """
    logger.info(f"生成模拟信号: 类型={signal_type}, 时长={duration_sec}s")
    
    t = np.linspace(0, duration_sec, int(duration_sec * sample_rate))
    noise = np.random.normal(0, 0.1, len(t))
    
    if signal_type == "relaxed":
        # 低振幅，平滑
        emg = 0.2 * np.sin(2 * np.pi * 5 * t) + 0.05 * noise
        angles = 45 + 10 * np.sin(2 * np.pi * 1 * t) # 平滑的正弦
        labels = SubjectiveLabels(
            relaxation_score=0.9,
            explosiveness_score=0.1,
            movement_quality=0.8
        )
    elif signal_type == "explosive":
        # 高振幅，快速上升
        burst = np.exp(-((t - 0.5)**2) / (2 * 0.1**2)) * 3.0 # 高斯脉冲
        emg = burst + 0.2 * noise
        angles = 45 + 50 * t * np.exp(-t*5) # 快速伸展
        labels = SubjectiveLabels(
            relaxation_score=0.2,
            explosiveness_score=0.95,
            movement_quality=0.85
        )
    else:
        emg = 0.5 * np.random.randn(len(t))
        angles = 45 + np.cumsum(np.random.randn(len(t)))
        labels = SubjectiveLabels(
            relaxation_score=0.5,
            explosiveness_score=0.5,
            movement_quality=0.5
        )
        
    signal = PhysiologicalSignal(
        timestamp=0.0,
        em_signal=emg.tolist(),
        joint_angles=angles.tolist()
    )
    
    return signal, labels

# ==========================================
# 主程序与使用示例
# ==========================================

if __name__ == "__main__":
    try:
        # 1. 生成模拟数据 (模拟'爆发力'动作)
        sim_signal, sim_labels = simulate_emg_signal(signal_type="explosive")
        
        # 2. 提取隐性特征
        implicit_feats = extract_implicit_features(sim_signal)
        print(f"\n提取的隐性特征: {implicit_feats}")
        
        # 3. 构建关联模型并固化节点
        memory_node = correlate_physio_subjective(implicit_feats, sim_labels)
        
        # 4. 输出结果
        print("\n=== AGI 肌肉记忆节点 ===")
        print(f"Node ID: {memory_node.node_id}")
        print(f"Confidence: {memory_node.confidence:.4f}")
        print("Subjective Mapping:")
        for k, v in memory_node.subjective_mapping.items():
            print(f"  - {k}: {v:.4f}")
            
        # 验证模型解释性
        if memory_node.subjective_mapping["inferred_explosiveness"] > 0.7:
            print("\n[系统判定]: 该动作具有显著的'爆发力'特征，已固化。")
            
    except ValidationError as ve:
        logger.error(f"数据验证错误: {ve}")
    except Exception as e:
        logger.critical(f"系统运行异常: {e}")