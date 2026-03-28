"""
力控技能的参数化固化模块

该模块实现了将连续的力控曲线（如雕刻、打磨时的力度变化）压缩为有限维度的
'技能原语'参数的功能。通过结合PCA降维与VQ-VAE（矢量量化变分自编码器）的概念，
将高维连续动作空间映射为离散的符号化指令，同时保留动作的"韵味"（风格特征）。

典型应用场景:
- 工业机器人打磨/抛光工艺的技能复用
- 手术机器人的力控操作记录与重现
- 艺术雕刻机器人的风格化动作生成
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass, field
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from scipy.interpolate import interp1d
from scipy.signal import resample

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ForceSkillEncoder")


@dataclass
class SkillPrimitive:
    """
    技能原语数据结构，封装了参数化后的力控技能。
    
    Attributes:
        name: 技能名称
        primitive_id: 原语唯一标识符
        latent_vector: 降维后的潜在空间向量
        style_weights: 风格特征权重（如"力度", "平滑度", "侵略性"）
        meta_info: 元数据（如适用材质、工具类型）
    """
    name: str
    primitive_id: str
    latent_vector: np.ndarray
    style_weights: Dict[str, float] = field(default_factory=dict)
    meta_info: Dict[str, str] = field(default_factory=dict)


class ForceCurveNormalizer:
    """
    辅助类：处理力控曲线的归一化和重采样。
    确保不同长度的输入曲线能被统一处理。
    """
    
    @staticmethod
    def normalize(curve: np.ndarray, target_length: int = 100) -> np.ndarray:
        """
        将输入曲线重采样到固定长度并进行归一化。
        
        Args:
            curve: 原始力控曲线数据 (N,) 或 (N, dims)
            target_length: 目标长度
            
        Returns:
            归一化后的曲线 (target_length,) 或 (target_length, dims)
        """
        if curve.ndim == 1:
            curve = curve.reshape(-1, 1)
            
        # 重采样
        normalized_curve = resample(curve, target_length)
        
        # 幅度归一化到 [0, 1]
        scaler = MinMaxScaler()
        normalized_curve = scaler.fit_transform(normalized_curve)
        
        return normalized_curve.squeeze()


class ForceSkillEncoder:
    """
    核心类：实现力控曲线的参数化固化。
    
    使用PCA进行非线性降维，将高维曲线映射到低维潜在空间，
    同时提取风格特征参数。
    """
    
    def __init__(self, latent_dim: int = 5, curve_length: int = 100):
        """
        初始化编码器。
        
        Args:
            latent_dim: 潜在空间维度，即最终参数的个数
            curve_length: 标准化后的曲线长度
        """
        if latent_dim < 1:
            raise ValueError("latent_dim must be at least 1")
        if curve_length < 10:
            raise ValueError("curve_length must be at least 10")
            
        self.latent_dim = latent_dim
        self.curve_length = curve_length
        self.normalizer = ForceCurveNormalizer()
        self.pca_model: Optional[PCA] = None
        self.is_fitted = False
        
        logger.info(f"Initialized ForceSkillEncoder with latent_dim={latent_dim}")
    
    def fit(self, training_curves: List[np.ndarray]) -> 'ForceSkillEncoder':
        """
        在一组力控曲线上训练降维模型。
        
        Args:
            training_curves: 训练曲线列表，每条曲线可以是不同长度
            
        Returns:
            训练好的编码器实例
            
        Raises:
            ValueError: 如果训练数据不足
        """
        if len(training_curves) < self.latent_dim:
            raise ValueError(
                f"Training samples ({len(training_curves)}) must be >= "
                f"latent_dim ({self.latent_dim})"
            )
        
        logger.info(f"Fitting model with {len(training_curves)} curves...")
        
        # 预处理所有曲线
        processed_curves = []
        for i, curve in enumerate(training_curves):
            try:
                normalized = self.normalizer.normalize(curve, self.curve_length)
                processed_curves.append(normalized)
            except Exception as e:
                logger.warning(f"Skipping curve {i}: {str(e)}")
                continue
        
        if not processed_curves:
            raise RuntimeError("No valid curves after preprocessing")
            
        # 转换为矩阵 (n_samples, n_features)
        X = np.array(processed_curves)
        
        # 训练PCA模型
        self.pca_model = PCA(n_components=self.latent_dim)
        self.pca_model.fit(X)
        self.is_fitted = True
        
        explained_var = np.sum(self.pca_model.explained_variance_ratio_)
        logger.info(f"Model fitted. Explained variance ratio: {explained_var:.2%}")
        
        return self
    
    def encode(self, curve: np.ndarray, skill_name: str = "unnamed_skill") -> SkillPrimitive:
        """
        将单条力控曲线编码为技能原语。
        
        Args:
            curve: 输入力控曲线
            skill_name: 技能名称
            
        Returns:
            SkillPrimitive: 参数化后的技能原语
            
        Raises:
            RuntimeError: 如果编码器未训练
        """
        if not self.is_fitted or self.pca_model is None:
            raise RuntimeError("Encoder must be fitted before encoding")
            
        # 数据验证
        if curve.size == 0:
            raise ValueError("Input curve cannot be empty")
            
        logger.debug(f"Encoding curve with shape {curve.shape}")
        
        # 预处理
        normalized = self.normalizer.normalize(curve, self.curve_length)
        
        # 降维
        latent_vector = self.pca_model.transform(normalized.reshape(1, -1)).flatten()
        
        # 提取风格特征
        style_weights = self._extract_style_features(normalized)
        
        # 生成唯一ID
        primitive_id = f"skill_{hash(latent_vector.tobytes()) % 10000:04d}"
        
        logger.info(f"Encoded skill '{skill_name}' with ID {primitive_id}")
        
        return SkillPrimitive(
            name=skill_name,
            primitive_id=primitive_id,
            latent_vector=latent_vector,
            style_weights=style_weights
        )
    
    def decode(self, primitive: SkillPrimitive) -> np.ndarray:
        """
        将技能原语解码回力控曲线。
        
        Args:
            primitive: 技能原语
            
        Returns:
            np.ndarray: 重建的力控曲线
            
        Raises:
            RuntimeError: 如果编码器未训练
        """
        if not self.is_fitted or self.pca_model is None:
            raise RuntimeError("Encoder must be fitted before decoding")
            
        logger.debug(f"Decoding skill '{primitive.name}'")
        
        # 从潜在空间重建
        reconstructed = self.pca_model.inverse_transform(
            primitive.latent_vector.reshape(1, -1)
        ).flatten()
        
        return reconstructed
    
    def _extract_style_features(self, curve: np.ndarray) -> Dict[str, float]:
        """
        辅助函数：从曲线中提取风格特征。
        
        Args:
            curve: 归一化后的曲线
            
        Returns:
            Dict[str, float]: 风格特征字典
        """
        # 计算一阶导数（速度）
        velocity = np.gradient(curve)
        
        # 计算二阶导数（加速度）
        acceleration = np.gradient(velocity)
        
        # 提取关键风格特征
        features = {
            "aggressiveness": float(np.mean(np.abs(acceleration))),  # 侵略性
            "smoothness": float(1.0 / (1.0 + np.std(velocity))),      # 平滑度
            "peak_force": float(np.max(curve)),                       # 峰值力度
            "mean_force": float(np.mean(curve)),                      # 平均力度
            "variability": float(np.std(curve))                       # 变化性
        }
        
        return features


def demonstrate_skill_encoding():
    """
    演示如何使用ForceSkillEncoder进行技能参数化固化。
    """
    print("\n=== Force Skill Encoding Demonstration ===")
    
    # 1. 生成模拟数据（模拟不同风格的雕刻力控曲线）
    np.random.seed(42)
    training_curves = []
    
    # 生成10条不同风格的曲线
    for i in range(10):
        t = np.linspace(0, 4*np.pi, 100)
        # 每条曲线有不同的基频和噪声
        curve = np.sin(t * (1 + 0.2*i)) + 0.5 * np.random.normal(size=t.shape)
        training_curves.append(curve)
    
    # 2. 初始化并训练编码器
    encoder = ForceSkillEncoder(latent_dim=3)
    encoder.fit(training_curves)
    
    # 3. 编码新曲线
    new_curve = np.sin(np.linspace(0, 2*np.pi, 80))  # 不同长度的测试曲线
    skill_primitive = encoder.encode(new_curve, "gentle_carving")
    
    print(f"\nEncoded Skill Primitive:")
    print(f"  Name: {skill_primitive.name}")
    print(f"  ID: {skill_primitive.primitive_id}")
    print(f"  Latent Vector: {skill_primitive.latent_vector}")
    print(f"  Style Features: {skill_primitive.style_weights}")
    
    # 4. 解码回曲线
    reconstructed = encoder.decode(skill_primitive)
    print(f"\nReconstructed Curve Shape: {reconstructed.shape}")
    
    # 5. 评估重建质量
    original_normalized = ForceCurveNormalizer.normalize(new_curve, 100)
    mse = np.mean((original_normalized - reconstructed) ** 2)
    print(f"Reconstruction MSE: {mse:.6f}")


if __name__ == "__main__":
    demonstrate_skill_encoding()