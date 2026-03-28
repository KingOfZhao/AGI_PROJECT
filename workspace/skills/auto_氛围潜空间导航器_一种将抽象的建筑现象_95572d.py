"""
氛围潜空间导航器

一种将抽象的建筑现象学描述（如'忧郁的'、'崇高的'）直接映射为神经网络潜空间向量的系统。
通过人类建筑师对空间感受的文本描述，训练一个Text-to-Latent的映射模型，使得AI能够生成
不仅'视觉正确'而且'情感共鸣'的空间图像或音乐。将'诗意'量化为可微分的向量运算。

领域: cross_domain
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhenomenologyCategory(Enum):
    """建筑现象学分类枚举"""
    MELANCHOLY = "忧郁的"
    SUBLIME = "崇高的"
    INTIMATE = "亲密的"
    SACRED = "神圣的"
    DYNAMIC = "动态的"
    STATIC = "静态的"

@dataclass
class LatentVector:
    """潜空间向量数据结构"""
    vector: np.ndarray
    magnitude: float
    primary_emotion: str
    secondary_emotions: List[str]
    confidence: float

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.vector, np.ndarray):
            raise TypeError("vector must be numpy array")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("confidence must be between 0 and 1")

class AtmosphereLatentNavigator:
    """
    氛围潜空间导航器
    
    将建筑现象学描述映射到神经网络潜空间向量
    
    属性:
        latent_dim (int): 潜空间维度
        emotion_embeddings (Dict): 情感词向量映射
        emotion_lexicon (Dict): 情感词库
    """
    
    def __init__(self, latent_dim: int = 512):
        """
        初始化导航器
        
        参数:
            latent_dim: 潜空间维度，默认为512
        """
        self.latent_dim = latent_dim
        self.emotion_embeddings = self._initialize_emotion_embeddings()
        self.emotion_lexicon = self._build_emotion_lexicon()
        logger.info(f"Initialized AtmosphereLatentNavigator with latent_dim={latent_dim}")
    
    def _initialize_emotion_embeddings(self) -> Dict[str, np.ndarray]:
        """
        初始化情感词向量映射
        
        返回:
            Dict: 情感词到向量的映射字典
        """
        # 这里使用随机初始化，实际应用中应该使用预训练的词向量
        embeddings = {}
        for category in PhenomenologyCategory:
            embeddings[category.value] = np.random.randn(self.latent_dim) * 0.1
        return embeddings
    
    def _build_emotion_lexicon(self) -> Dict[str, List[str]]:
        """
        构建情感词库
        
        返回:
            Dict: 情感类别到相关词列表的映射
        """
        return {
            "忧郁的": ["悲伤", "沉静", "忧郁", "阴郁", "哀愁", "萧瑟"],
            "崇高的": ["雄伟", "庄严", "宏大", "壮观", "巍峨", "崇高"],
            "亲密的": ["温馨", "舒适", "私密", "亲切", "温暖", "柔和"],
            "神圣的": ["庄严", "神圣", "肃穆", "圣洁", "崇敬", "虔诚"],
            "动态的": ["流动", "活跃", "动感", "变化", "运动", "活跃"],
            "静态的": ["静止", "稳定", "宁静", "安详", "平和", "固定"]
        }
    
    def text_to_latent(
        self, 
        description: str, 
        intensity: float = 1.0,
        context: Optional[Dict] = None
    ) -> LatentVector:
        """
        将文本描述转换为潜空间向量
        
        参数:
            description: 建筑现象学描述文本
            intensity: 情感强度系数，0.1-2.0之间
            context: 上下文信息字典，可选
            
        返回:
            LatentVector: 生成的潜空间向量
            
        异常:
            ValueError: 如果输入描述为空或强度超出范围
        """
        if not description.strip():
            raise ValueError("Description cannot be empty")
        
        if not 0.1 <= intensity <= 2.0:
            raise ValueError("Intensity must be between 0.1 and 2.0")
        
        logger.info(f"Processing description: '{description}' with intensity {intensity}")
        
        # 分析文本中的情感成分
        emotion_weights = self._analyze_emotions(description)
        
        if not emotion_weights:
            logger.warning("No emotions detected, using neutral vector")
            return LatentVector(
                vector=np.zeros(self.latent_dim),
                magnitude=0.0,
                primary_emotion="neutral",
                secondary_emotions=[],
                confidence=0.0
            )
        
        # 加权组合情感向量
        latent_vector = np.zeros(self.latent_dim)
        for emotion, weight in emotion_weights.items():
            latent_vector += self.emotion_embeddings[emotion] * weight
        
        # 应用强度系数
        latent_vector *= intensity
        
        # 归一化
        magnitude = np.linalg.norm(latent_vector)
        if magnitude > 0:
            latent_vector = latent_vector / magnitude
        
        # 确定主要和次要情感
        sorted_emotions = sorted(
            emotion_weights.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        primary_emotion = sorted_emotions[0][0]
        secondary_emotions = [e[0] for e in sorted_emotions[1:4]] if len(sorted_emotions) > 1 else []
        
        # 计算置信度
        confidence = min(1.0, sum(emotion_weights.values()) / 2.0)
        
        return LatentVector(
            vector=latent_vector,
            magnitude=magnitude,
            primary_emotion=primary_emotion,
            secondary_emotions=secondary_emotions,
            confidence=confidence
        )
    
    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """
        分析文本中的情感成分
        
        参数:
            text: 输入文本
            
        返回:
            Dict: 情感到权重的映射
        """
        emotion_weights = {}
        words = text.lower().split()
        
        for emotion, lexicon in self.emotion_lexicon.items():
            weight = 0.0
            for word in words:
                if word in lexicon:
                    weight += 1.0
            
            if weight > 0:
                emotion_weights[emotion] = weight
        
        # 归一化权重
        total_weight = sum(emotion_weights.values())
        if total_weight > 0:
            emotion_weights = {
                k: v/total_weight for k, v in emotion_weights.items()
            }
        
        return emotion_weights
    
    def interpolate_atmospheres(
        self,
        descriptions: List[str],
        weights: Optional[List[float]] = None,
        method: str = "linear"
    ) -> LatentVector:
        """
        在多个氛围描述之间进行潜空间插值
        
        参数:
            descriptions: 氛围描述列表
            weights: 各描述的权重列表，默认为均匀权重
            method: 插值方法，目前支持'linear'
            
        返回:
            LatentVector: 插值后的潜空间向量
            
        异常:
            ValueError: 如果输入参数无效
        """
        if not descriptions:
            raise ValueError("Descriptions list cannot be empty")
        
        if len(descriptions) == 1:
            return self.text_to_latent(descriptions[0])
        
        if weights is None:
            weights = [1.0 / len(descriptions)] * len(descriptions)
        else:
            if len(weights) != len(descriptions):
                raise ValueError("Weights must match descriptions in length")
            if not np.isclose(sum(weights), 1.0, atol=1e-6):
                raise ValueError("Weights must sum to 1.0")
        
        logger.info(f"Interpolating {len(descriptions)} atmospheres using {method} method")
        
        # 获取每个描述的潜空间向量
        vectors = [
            self.text_to_latent(desc).vector 
            for desc in descriptions
        ]
        
        # 执行加权插值
        interpolated_vector = np.zeros(self.latent_dim)
        for vec, weight in zip(vectors, weights):
            interpolated_vector += vec * weight
        
        # 计算平均置信度
        confidences = [
            self.text_to_latent(desc).confidence 
            for desc in descriptions
        ]
        avg_confidence = np.mean(confidences)
        
        # 确定主要情感
        primary_emotions = [
            self.text_to_latent(desc).primary_emotion 
            for desc in descriptions
        ]
        # 使用权重投票确定主要情感
        emotion_votes = {}
        for emotion, weight in zip(primary_emotions, weights):
            emotion_votes[emotion] = emotion_votes.get(emotion, 0.0) + weight
        primary_emotion = max(emotion_votes.items(), key=lambda x: x[1])[0]
        
        return LatentVector(
            vector=interpolated_vector,
            magnitude=np.linalg.norm(interpolated_vector),
            primary_emotion=primary_emotion,
            secondary_emotions=[e for e in primary_emotions if e != primary_emotion],
            confidence=avg_confidence
        )

    def visualize_latent_space(
        self, 
        vectors: List[LatentVector],
        labels: Optional[List[str]] = None
    ) -> None:
        """
        可视化潜空间向量 (需要matplotlib)
        
        参数:
            vectors: 要可视化的潜空间向量列表
            labels: 向量标签列表，可选
        """
        try:
            import matplotlib.pyplot as plt
            from sklearn.decomposition import PCA
            
            if not vectors:
                raise ValueError("Vectors list cannot be empty")
            
            # 将向量堆叠为矩阵
            matrix = np.stack([v.vector for v in vectors])
            
            # 使用PCA降维到2D
            pca = PCA(n_components=2)
            coords = pca.fit_transform(matrix)
            
            # 绘制图形
            plt.figure(figsize=(10, 8))
            scatter = plt.scatter(coords[:, 0], coords[:, 1], alpha=0.7)
            
            if labels:
                for i, label in enumerate(labels):
                    plt.annotate(
                        label, 
                        (coords[i, 0], coords[i, 1]),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center'
                    )
            
            plt.title("Atmosphere Latent Space Visualization")
            plt.xlabel("Principal Component 1")
            plt.ylabel("Principal Component 2")
            plt.grid(True)
            plt.show()
            
        except ImportError:
            logger.warning("Matplotlib or sklearn not available, skipping visualization")
        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")

# 使用示例
if __name__ == "__main__":
    # 初始化导航器
    navigator = AtmosphereLatentNavigator(latent_dim=256)
    
    # 示例1: 将文本描述转换为潜空间向量
    description = "这是一个充满忧郁和崇高的空间，光线透过高窗洒下，营造出一种神圣的氛围"
    latent_vector = navigator.text_to_latent(description, intensity=1.2)
    
    print(f"\nGenerated latent vector:")
    print(f"Primary emotion: {latent_vector.primary_emotion}")
    print(f"Secondary emotions: {latent_vector.secondary_emotions}")
    print(f"Magnitude: {latent_vector.magnitude:.4f}")
    print(f"Confidence: {latent_vector.confidence:.4f}")
    
    # 示例2: 氛围插值
    descriptions = [
        "亲密而温暖的家庭空间",
        "庄严而神圣的宗教空间",
        "动态而流动的商业空间"
    ]
    interpolated_vector = navigator.interpolate_atmospheres(
        descriptions, 
        weights=[0.4, 0.3, 0.3]
    )
    
    print("\nInterpolated latent vector:")
    print(f"Primary emotion: {interpolated_vector.primary_emotion}")
    print(f"Confidence: {interpolated_vector.confidence:.4f}")
    
    # 示例3: 可视化 (需要matplotlib和sklearn)
    vectors = [
        navigator.text_to_latent("忧郁的庭院"),
        navigator.text_to_latent("崇高的教堂"),
        navigator.text_to_latent("亲密的卧室")
    ]
    labels = ["Melancholy", "Sublime", "Intimate"]
    # navigator.visualize_latent_space(vectors, labels)