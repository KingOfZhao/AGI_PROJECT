"""
模块名称: auto_如何构建多模态对齐模型_将高频振动传感器_7bea38
描述: 本模块实现了一个用于高频振动传感器数据与自然语言描述对齐的轻量级多模态架构。
      它通过对比学习构建共享嵌入空间，将物理信号（如振动频谱）与语义描述
      （如"轴承磨损的异响"）进行绑定，生成可用于RAG（检索增强生成）或
      AGI知识库的感官-语义节点。
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from sklearn.preprocessing import normalize

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型与验证 ---

class VibrationSignal(BaseModel):
    """
    高频振动传感器输入数据模型。
    """
    signal_id: str = Field(..., description="信号唯一标识符")
    sampling_rate: int = Field(..., gt=0, description="采样率
    amplitude: np.ndarray = Field(..., description="振动幅值时间序列")
    
    @validator('amplitude')
    def validate_amplitude(cls, v):
        if v.ndim != 1:
            raise ValueError("振幅数据必须是一维数组")
        if len(v) < 256:
            raise ValueError("信号长度过短，至少需要256个采样点以进行有效分析")
        return v

    class Config:
        arbitrary_types_allowed = True

class SemanticDescription(BaseModel):
    """
    自然语言描述输入数据模型。
    """
    text_id: str = Field(..., description="文本唯一标识符")
    content: str = Field(..., min_length=2, description="故障描述文本")
    language: str = Field(default="zh", description="语言代码")

class SensorySemanticNode(BaseModel):
    """
    输出的感官-语义节点结构。
    """
    node_id: str
    embedding_vector: np.ndarray
    source_type: str # 'vibration' or 'text'
    metadata: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True

# --- 核心组件类 ---

class MultiModalSignalAligner:
    """
    多模态对齐模型核心类。
    
    该类负责将传感器信号和文本描述映射到同一维度的向量空间，
    并计算它们的相似度以实现语义绑定。
    
    Attributes:
        embed_dim (int): 嵌入向量的维度。
        text_encoder (object): 模拟的文本编码器。
        signal_encoder (object): 模拟的信号编码器。
    """

    def __init__(self, embedding_dim: int = 128):
        """
        初始化对齐模型。
        
        Args:
            embedding_dim (int): 统一嵌入空间的维度。
        """
        self.embed_dim = embedding_dim
        self.text_encoder = self._mock_text_encoder
        self.signal_encoder = self._mock_signal_encoder
        logger.info(f"MultiModalSignalAligner initialized with dim={self.embed_dim}")

    @property
    def _mock_text_encoder(self):
        """模拟文本编码器 (实际生产中应替换为BERT等Transformers)"""
        def encoder(text: str) -> np.ndarray:
            # 简单的Hash向量化模拟，仅用于演示逻辑
            vec = np.random.randn(self.embed_dim)
            # 确保相同文本生成相同向量（模拟确定性）
            np.random.seed(hash(text) % (2**32))
            vec = np.random.randn(self.embed_dim)
            np.random.seed(None) # 恢复随机状态
            return normalize(vec.reshape(1, -1))[0]
        return encoder

    @property
    def _mock_signal_encoder(self):
        """模拟信号编码器 (实际生产中应替换为1D-CNN或Transformer)"""
        def encoder(signal: np.ndarray) -> np.ndarray:
            # 模拟特征提取：计算统计特征并映射到embed_dim
            # 实际场景通常会使用FFT + CNN
            features = np.array([
                np.mean(signal),
                np.std(signal),
                np.max(signal),
                np.min(signal)
            ])
            # 简单的线性投影模拟
            np.random.seed(42) # 模拟固定的权重初始化
            proj_matrix = np.random.randn(len(features), self.embed_dim)
            vec = np.dot(features, proj_matrix)
            np.random.seed(None)
            return normalize(vec.reshape(1, -1))[0]
        return encoder

    def preprocess_signal(self, raw_signal: VibrationSignal) -> np.ndarray:
        """
        辅助函数: 信号预处理。
        
        包括去噪、归一化和快速傅里叶变换(FFT)。
        
        Args:
            raw_signal (VibrationSignal): 原始振动信号对象。
            
        Returns:
            np.ndarray: 处理后的频谱特征。
        """
        try:
            data = raw_signal.amplitude
            # 1. 归一化
            data = (data - np.mean(data)) / (np.std(data) + 1e-6)
            
            # 2. FFT转换 (取前半部分频率)
            fft_vals = np.fft.fft(data)
            fft_abs = np.abs(fft_vals)[:len(data)//2]
            
            return fft_abs
        except Exception as e:
            logger.error(f"Signal preprocessing failed for {raw_signal.signal_id}: {e}")
            raise

    def encode_modality(self, data: Any, modality_type: str) -> np.ndarray:
        """
        核心函数: 统一编码接口。
        
        根据模态类型选择编码器并生成向量。
        
        Args:
            data: 输入数据 (VibrationSignal 或 str)。
            modality_type (str): 'signal' 或 'text'。
            
        Returns:
            np.ndarray: 归一化的嵌入向量。
        """
        if modality_type == 'text':
            if not isinstance(data, str):
                raise TypeError("Text modality requires string input")
            return self.text_encoder(data)
        
        elif modality_type == 'signal':
            if not isinstance(data, VibrationSignal):
                raise TypeError("Signal modality requires VibrationSignal input")
            
            # 预处理信号
            processed_features = self.preprocess_signal(data)
            # 这里为了演示，我们将处理后的特征视为编码器的输入
            # 实际上signal_encoder内部通常包含深度网络结构
            return self.signal_encoder(processed_features)
        
        else:
            raise ValueError(f"Unsupported modality: {modality_type}")

    def build_semantic_node(
        self, 
        signal_data: VibrationSignal, 
        description: str
    ) -> Tuple[SensorySemanticNode, float]:
        """
        核心函数: 构建并绑定感官-语义节点。
        
        计算两个模态的嵌入向量，验证相似度，并生成最终的节点对象。
        
        Args:
            signal_data (VibrationSignal): 传感器数据。
            description (str): 对应的自然语言描述。
            
        Returns:
            Tuple[SensorySemanticNode, float]: 包含融合特征的节点对象和两模态的对齐置信度(余弦相似度)。
        """
        try:
            # 1. 生成嵌入
            signal_vec = self.encode_modality(signal_data, 'signal')
            text_vec = self.encode_modality(description, 'text')
            
            # 2. 计算对齐分数 (余弦相似度)
            alignment_score = np.dot(signal_vec, text_vec)
            
            # 3. 特征融合
            # 使用加权求和或平均作为节点的最终表示
            fused_embedding = (signal_vec + text_vec) / 2.0
            fused_embedding = normalize(fused_embedding.reshape(1, -1))[0]
            
            # 4. 构建节点
            node = SensorySemanticNode(
                node_id=f"node_{signal_data.signal_id}",
                embedding_vector=fused_embedding,
                source_type="multimodal_vibration_text",
                metadata={
                    "signal_id": signal_data.signal_id,
                    "description": description,
                    "sampling_rate": signal_data.sampling_rate,
                    "alignment_confidence": float(alignment_score)
                }
            )
            
            logger.info(f"Node built. Alignment Score: {alignment_score:.4f}")
            return node, alignment_score
            
        except Exception as e:
            logger.error(f"Failed to build semantic node: {e}")
            raise

# --- 使用示例 ---

def run_demonstration():
    """
    演示如何使用该模块构建多模态对齐。
    """
    print("--- Starting Multimodal Alignment Demonstration ---")
    
    # 1. 初始化模型
    aligner = MultiModalSignalAligner(embedding_dim=256)
    
    # 2. 准备模拟数据
    # 模拟轴承磨损的高频振动 (加入特定的噪声模式)
    time_steps = np.linspace(0, 1, 1000)
    # 50Hz基频 + 150Hz谐波(模拟磨损异响)
    vibration_data = np.sin(2 * np.pi * 50 * time_steps) + 0.5 * np.sin(2 * np.pi * 150 * time_steps)
    vibration_data += np.random.normal(0, 0.1, 1000) # 添加白噪声
    
    signal_input = VibrationSignal(
        signal_id="bearing_001",
        sampling_rate=1000,
        amplitude=vibration_data
    )
    
    text_input = "轴承磨损产生的异响"
    
    # 3. 构建节点
    try:
        node, score = aligner.build_semantic_node(signal_input, text_input)
        
        print(f"\nNode Created: {node.node_id}")
        print(f"Alignment Confidence: {score:.4f}")
        print(f"Embedding Vector Dimension: {len(node.embedding_vector)}")
        print(f"Metadata: {node.metadata}")
        
        # 4. 模拟检索场景
        # 在实际AGI系统中，这些向量会被存入向量数据库(如Milvus/Pinecone)
        query_vec = aligner.encode_modality("Check for bearing damage", 'text')
        similarity = np.dot(node.embedding_vector, query_vec)
        print(f"\nRetrieval Test Similarity with 'Check for bearing damage': {similarity:.4f}")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")

if __name__ == "__main__":
    run_demonstration()