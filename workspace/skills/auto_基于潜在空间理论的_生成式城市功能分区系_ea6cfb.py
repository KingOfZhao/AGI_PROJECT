"""
高级Python模块：基于潜在空间理论的生成式城市功能分区系统
该模块实现了一个利用深度学习模型（VAE或扩散模型）在城市功能流形上进行向量运算的系统，
支持通过数学运算探索创新的城市空间功能组合。

核心能力：
- 将城市空间结构编码为潜在向量
- 在功能流形上进行向量算术运算
- 解码生成新的城市功能分区方案

输入格式：
- 初始城市特征：Dict[str, float]，如 {"population_density": 0.8, "commercial_index": 0.3}
- 语义操作指令：List[Dict]，如 [{"operation": "add", "attribute": "commercial", "weight": 0.6}]

输出格式：
- 生成结果：Dict[str, float]，包含功能分区指标和潜在向量
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, validator, confloat
from enum import Enum

# 初始化日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('urban_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UrbanAttribute(Enum):
    """城市属性枚举，定义可操作的城市功能维度"""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    GREEN_SPACE = "green_space"
    TRANSPORT = "transport"
    MIXED_USE = "mixed_use"


class OperationType(Enum):
    """向量操作类型枚举"""
    ADD = "add"
    SUBTRACT = "subtract"
    INTERPOLATE = "interpolate"
    AVERAGE = "average"


class UrbanFeatureVector(BaseModel):
    """城市特征向量数据验证模型"""
    residential: confloat(ge=0, le=1) = 0.0
    commercial: confloat(ge=0, le=1) = 0.0
    industrial: confloat(ge=0, le=1) = 0.0
    green_space: confloat(ge=0, le=1) = 0.0
    transport: confloat(ge=0, le=1) = 0.0
    
    @validator('*')
    def validate_features(cls, v):
        """验证特征值在合理范围内"""
        if not 0 <= v <= 1:
            raise ValueError("Feature values must be between 0 and 1")
        return v


class LatentSpaceUrbanGenerator:
    """基于潜在空间理论的城市功能分区生成器"""
    
    def __init__(self, latent_dim: int = 128, model_path: Optional[str] = None):
        """
        初始化生成器
        
        Args:
            latent_dim: 潜在空间维度
            model_path: 预训练模型路径
        """
        self.latent_dim = latent_dim
        self._initialize_model(model_path)
        self.attribute_vectors = self._load_attribute_vectors()
        logger.info("LatentSpaceUrbanGenerator initialized with latent_dim=%d", latent_dim)
    
    def _initialize_model(self, model_path: Optional[str]) -> None:
        """
        初始化或加载深度学习模型（模拟实现）
        
        在实际应用中，这里会加载VAE或扩散模型
        """
        self.encoder = lambda x: np.random.randn(self.latent_dim) * 0.1 + np.mean(list(x.values()))
        self.decoder = lambda z: {
            "residential": np.clip(np.mean(z), 0, 1),
            "commercial": np.clip(np.std(z), 0, 1),
            "industrial": np.clip(np.min(z), 0, 1),
            "green_space": np.clip(np.max(z), 0, 1),
            "transport": np.clip(np.median(z), 0, 1)
        }
        
        if model_path:
            logger.info("Loading pretrained model from %s", model_path)
            # 实际实现中这里会加载模型权重
    
    def _load_attribute_vectors(self) -> Dict[UrbanAttribute, np.ndarray]:
        """
        加载属性向量（模拟实现）
        
        Returns:
            属性到潜在向量的映射字典
        """
        # 模拟属性向量，实际应用中应从训练数据中学习
        return {
            UrbanAttribute.RESIDENTIAL: np.random.randn(self.latent_dim) * 0.1 + 0.3,
            UrbanAttribute.COMMERCIAL: np.random.randn(self.latent_dim) * 0.1 + 0.5,
            UrbanAttribute.INDUSTRIAL: np.random.randn(self.latent_dim) * 0.1 + 0.2,
            UrbanAttribute.GREEN_SPACE: np.random.randn(self.latent_dim) * 0.1 + 0.1,
            UrbanAttribute.TRANSPORT: np.random.randn(self.latent_dim) * 0.1 + 0.4,
            UrbanAttribute.MIXED_USE: np.random.randn(self.latent_dim) * 0.1 + 0.6
        }
    
    def encode_urban_features(self, features: Dict[str, float]) -> np.ndarray:
        """
        将城市特征编码为潜在向量
        
        Args:
            features: 城市特征字典
            
        Returns:
            潜在空间向量
        """
        try:
            validated_features = UrbanFeatureVector(**features)
            logger.debug("Encoding features: %s", validated_features.dict())
            return self.encoder(validated_features.dict())
        except Exception as e:
            logger.error("Feature encoding failed: %s", str(e))
            raise ValueError(f"Invalid urban features: {str(e)}")
    
    def decode_latent_vector(self, latent_vector: np.ndarray) -> Dict[str, float]:
        """
        将潜在向量解码为城市特征
        
        Args:
            latent_vector: 潜在空间向量
            
        Returns:
            城市特征字典
        """
        if len(latent_vector) != self.latent_dim:
            error_msg = f"Expected latent vector of dim {self.latent_dim}, got {len(latent_vector)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.debug("Decoding latent vector with mean %.2f", np.mean(latent_vector))
        return self.decoder(latent_vector)
    
    def perform_latent_operations(
        self,
        initial_vector: np.ndarray,
        operations: List[Dict[str, Union[str, float]]]
    ) -> np.ndarray:
        """
        在潜在空间执行一系列向量操作
        
        Args:
            initial_vector: 初始潜在向量
            operations: 操作列表，每个操作包含type和attribute
            
        Returns:
            操作后的潜在向量
        """
        result_vector = initial_vector.copy()
        
        for op in operations:
            try:
                op_type = OperationType(op["operation"].lower())
                attribute = UrbanAttribute(op["attribute"].lower())
                weight = op.get("weight", 1.0)
                
                if op_type == OperationType.ADD:
                    result_vector += self.attribute_vectors[attribute] * weight
                elif op_type == OperationType.SUBTRACT:
                    result_vector -= self.attribute_vectors[attribute] * weight
                elif op_type == OperationType.INTERPOLATE:
                    result_vector = (result_vector + self.attribute_vectors[attribute] * weight) / 2
                elif op_type == OperationType.AVERAGE:
                    result_vector = (result_vector + self.attribute_vectors[attribute]) / 2
                    
                logger.info(
                    "Performed %s operation on %s with weight %.2f",
                    op_type.value, attribute.value, weight
                )
            except Exception as e:
                logger.error("Invalid operation %s: %s", op, str(e))
                continue
                
        return result_vector
    
    def generate_urban_design(
        self,
        initial_features: Dict[str, float],
        operations: List[Dict[str, Union[str, float]]],
        num_samples: int = 1
    ) -> Union[Dict[str, float], List[Dict[str, float]]]:
        """
        生成城市设计方案的完整流程
        
        Args:
            initial_features: 初始城市特征
            operations: 要执行的操作列表
            num_samples: 生成样本数量
            
        Returns:
            生成的设计方案，单个或列表
        """
        try:
            # 编码初始特征
            initial_vector = self.encode_urban_features(initial_features)
            
            # 执行潜在空间操作
            modified_vector = self.perform_latent_operations(initial_vector, operations)
            
            # 生成样本
            samples = []
            for _ in range(num_samples):
                # 添加小噪声增加多样性
                noisy_vector = modified_vector + np.random.randn(self.latent_dim) * 0.05
                sample = self.decode_latent_vector(noisy_vector)
                samples.append(sample)
            
            logger.info("Generated %d urban design samples", num_samples)
            
            return samples[0] if num_samples == 1 else samples
        except Exception as e:
            logger.error("Urban design generation failed: %s", str(e))
            raise RuntimeError(f"Generation failed: {str(e)}")


def visualize_latent_space(
    generator: LatentSpaceUrbanGenerator,
    samples: List[Dict[str, float]],
    output_path: str = "latent_space_viz.png"
) -> None:
    """
    可视化潜在空间中的样本分布（辅助函数）
    
    Args:
        generator: 城市生成器实例
        samples: 要可视化的样本列表
        output_path: 输出图像路径
    """
    try:
        import matplotlib.pyplot as plt
        from sklearn.decomposition import PCA
        
        # 收集所有样本的潜在向量
        vectors = []
        labels = []
        
        # 添加样本点
        for sample in samples:
            try:
                vector = generator.encode_urban_features(sample)
                vectors.append(vector)
                labels.append("Sample")
            except Exception as e:
                logger.warning("Skipping invalid sample: %s", str(e))
        
        # 添加属性向量
        for attr in UrbanAttribute:
            vectors.append(generator.attribute_vectors[attr])
            labels.append(attr.value)
        
        # 降维可视化
        pca = PCA(n_components=2)
        reduced_vectors = pca.fit_transform(vectors)
        
        plt.figure(figsize=(10, 8))
        plt.scatter(reduced_vectors[:len(samples), 0], reduced_vectors[:len(samples), 1], 
                   c='blue', label='Generated Samples')
        
        # 绘制属性向量
        for i, attr in enumerate(UrbanAttribute):
            idx = len(samples) + i
            plt.scatter(reduced_vectors[idx, 0], reduced_vectors[idx, 1], 
                       marker='x', label=attr.value)
        
        plt.title("Urban Function Latent Space Visualization")
        plt.xlabel("Principal Component 1")
        plt.ylabel("Principal Component 2")
        plt.legend()
        plt.savefig(output_path)
        plt.close()
        
        logger.info("Latent space visualization saved to %s", output_path)
    except ImportError:
        logger.warning("Visualization dependencies not available. Install matplotlib and scikit-learn.")
    except Exception as e:
        logger.error("Visualization failed: %s", str(e))


if __name__ == "__main__":
    # 使用示例
    print("=== 城市功能分区生成系统演示 ===")
    
    # 1. 初始化生成器
    generator = LatentSpaceUrbanGenerator(latent_dim=64)
    
    # 2. 定义初始城市特征 (高密度住宅区)
    residential_area = {
        "residential": 0.9,
        "commercial": 0.1,
        "industrial": 0.0,
        "green_space": 0.2,
        "transport": 0.3
    }
    
    # 3. 定义操作序列 (模拟: 高密度住宅区 - 拥挤属性 + 商业属性 = 综合体原型)
    operations = [
        {"operation": "subtract", "attribute": "residential", "weight": 0.4},  # 减少住宅密度
        {"operation": "add", "attribute": "commercial", "weight": 0.6},       # 增加商业属性
        {"operation": "add", "attribute": "green_space", "weight": 0.3}       # 增加绿化
    ]
    
    # 4. 生成设计方案
    try:
        design = generator.generate_urban_design(residential_area, operations)
        print("\n生成的设计方案:")
        for key, value in design.items():
            print(f"{key}: {value:.2f}")
        
        # 5. 生成多个样本并可视化
        multiple_designs = generator.generate_urban_design(
            residential_area, operations, num_samples=5
        )
        visualize_latent_space(generator, multiple_designs)
        
    except Exception as e:
        print(f"生成失败: {str(e)}")