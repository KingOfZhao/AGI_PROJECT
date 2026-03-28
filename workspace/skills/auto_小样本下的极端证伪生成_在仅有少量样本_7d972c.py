"""
高级Python模块：小样本下的极端证伪生成器

该模块实现了一个用于AGI系统的核心组件，旨在解决小样本学习中的长尾分布问题。
通过利用生成式模型（此处使用基于PyTorch的变分自编码器VAE）的"想象力"，
系统构建逻辑上可能但尚未在观测数据中出现的"潜在失败样本"（反例）。
生成的样本旨在主动寻求人类专家的证伪，从而在极少样本条件下提升系统的鲁棒性。

核心方法：
1. 基于VAE的潜在空间扰动生成。
2. 基于马氏距离的异常/边界样本筛选。
"""

import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Tuple, Dict, Optional, Union
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EmpiricalCovariance

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FalsificationGenerator")

# 类型别名定义
Tensor = torch.Tensor
Array = np.ndarray

class VAE(nn.Module):
    """
    变分自编码器（VAE）实现，用于学习数据分布并在潜在空间生成新样本。
    
    Attributes:
        encoder (nn.Sequential): 编码器网络
        decoder (nn.Sequential): 解码器网络
        fc_mu (nn.Linear): 均值映射层
        fc_var (nn.Linear): 方差映射层
    """
    
    def __init__(self, input_dim: int, latent_dim: int = 32, hidden_dim: int = 64):
        """
        初始化VAE模型。
        
        Args:
            input_dim: 输入特征维度
            latent_dim: 潜在空间维度
            hidden_dim: 隐藏层维度
        """
        super(VAE, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.2)
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_var = nn.Linear(hidden_dim, latent_dim)
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, input_dim),
            nn.Sigmoid()  # 假设输入数据已归一化到[0,1]
        )
        
    def encode(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        """编码输入到潜在空间，返回均值和对数方差。"""
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_var(h)
    
    def reparameterize(self, mu: Tensor, logvar: Tensor) -> Tensor:
        """重参数化技巧，从高斯分布中采样。"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z: Tensor) -> Tensor:
        """从潜在空间解码回原始空间。"""
        return self.decoder(z)
    
    def forward(self, x: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        """前向传播：编码 -> 重参数化 -> 解码。"""
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decode(z), mu, logvar

def vae_loss_function(recon_x: Tensor, x: Tensor, mu: Tensor, logvar: Tensor) -> Tensor:
    """
    计算VAE的损失函数（重建损失 + KL散度）。
    
    Args:
        recon_x: 重建的输入
        x: 原始输入
        mu: 潜在空间均值
        logvar: 潜在空间对数方差
        
    Returns:
        计算得到的总损失
    """
    BCE = nn.functional.binary_cross_entropy(recon_x, x, reduction='sum')
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return BCE + KLD

def validate_input_data(data: Array) -> bool:
    """
    验证输入数据的合法性。
    
    Args:
        data: 输入数据数组
        
    Returns:
        bool: 数据是否合法
        
    Raises:
        ValueError: 如果数据不符合要求
    """
    if not isinstance(data, np.ndarray):
        raise ValueError("输入数据必须是numpy数组")
        
    if data.ndim != 2:
        raise ValueError("输入数据必须是2维数组 (samples, features)")
        
    if data.shape[0] < 2:
        raise ValueError("至少需要2个样本才能进行协方差估计")
        
    if np.any(np.isnan(data)) or np.any(np.isinf(data)):
        raise ValueError("输入数据包含NaN或无限值")
        
    return True

class FalsificationGenerator:
    """
    极端证伪生成器核心类，封装了模型训练、潜在空间探索和反例生成逻辑。
    """
    
    def __init__(self, input_dim: int, latent_dim: int = 32, device: str = 'auto'):
        """
        初始化生成器。
        
        Args:
            input_dim: 输入特征维度
            latent_dim: 潜在空间维度
            device: 计算设备 ('auto', 'cuda', 'cpu')
        """
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.scaler = StandardScaler()
        self.cov_estimator = EmpiricalCovariance()
        
        # 自动选择设备
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        logger.info(f"初始化生成器，使用设备: {self.device}")
        
        self.model = VAE(input_dim, latent_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=1e-3)
        self.is_fitted = False
        
    def fit(self, X: Array, epochs: int = 100, batch_size: int = 32) -> None:
        """
        在小样本数据上训练生成模型。
        
        Args:
            X: 输入数据 (n_samples, n_features)
            epochs: 训练轮数
            batch_size: 批大小
            
        Raises:
            ValueError: 如果输入数据验证失败
        """
        validate_input_data(X)
        logger.info(f"开始训练，样本数: {X.shape[0]}, 特征数: {X.shape[1]}")
        
        # 数据标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 转换为PyTorch张量
        dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(X_scaled).to(self.device)
        )
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=True
        )
        
        # 训练循环
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                x = batch[0]
                self.optimizer.zero_grad()
                
                recon_x, mu, logvar = self.model(x)
                loss = vae_loss_function(recon_x, x, mu, logvar)
                
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
                
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}/{epochs}, Loss: {total_loss:.4f}")
                
        # 训练完成后估计数据分布
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled).to(self.device)
            _, mu, _ = self.model(X_tensor)
            self.cov_estimator.fit(mu.cpu().numpy())
            
        self.is_fitted = True
        logger.info("模型训练完成")
        
    def generate_falsifications(
        self,
        n_samples: int = 10,
        temperature: float = 1.0,
        boundary_threshold: float = 0.95
    ) -> Tuple[Array, Array]:
        """
        生成潜在失败样本（反例）。
        
        算法：
        1. 在潜在空间中进行随机采样
        2. 筛选位于分布边界（高马氏距离）的样本
        3. 解码回原始空间
        
        Args:
            n_samples: 要生成的样本数
            temperature: 采样温度系数（控制多样性）
            boundary_threshold: 边界阈值（0-1，越高表示越接近边界）
            
        Returns:
            Tuple[Array, Array]: (生成的反例, 潜在空间坐标)
            
        Raises:
            RuntimeError: 如果模型尚未训练
        """
        if not self.is_fitted:
            raise RuntimeError("模型尚未训练，请先调用fit()方法")
            
        logger.info(f"开始生成 {n_samples} 个反例，温度: {temperature}")
        
        generated_samples = []
        latent_coords = []
        
        while len(generated_samples) < n_samples:
            # 1. 在潜在空间中随机采样
            z = torch.randn(1, self.latent_dim).to(self.device) * temperature
            
            # 2. 计算马氏距离并筛选边界样本
            z_np = z.cpu().numpy().reshape(1, -1)
            mahalanobis = self.cov_estimator.mahalanobis(z_np)[0]
            
            # 将马氏距离转换为边界概率（使用sigmoid）
            boundary_prob = 1 / (1 + np.exp(-mahalanobis + 5))
            
            if boundary_prob > boundary_threshold:
                # 3. 解码回原始空间
                with torch.no_grad():
                    sample = self.model.decode(z).cpu().numpy()
                
                # 反标准化
                sample_original = self.scaler.inverse_transform(sample)
                generated_samples.append(sample_original[0])
                latent_coords.append(z_np[0])
                
        logger.info(f"成功生成 {len(generated_samples)} 个反例")
        return np.array(generated_samples), np.array(latent_coords)
        
    def evaluate_falsification(
        self,
        original_data: Array,
        falsification: Array,
        metric: str = 'euclidean'
    ) -> float:
        """
        评估生成反例的质量（与原始数据的平均距离）。
        
        Args:
            original_data: 原始数据集
            falsification: 生成的反例
            metric: 距离度量 ('euclidean' 或 'cosine')
            
        Returns:
            float: 平均距离分数
            
        Raises:
            ValueError: 如果metric参数无效
        """
        if metric not in ['euclidean', 'cosine']:
            raise ValueError("metric参数必须是'euclidean'或'cosine'")
            
        if metric == 'euclidean':
            dists = np.linalg.norm(original_data - falsification, axis=1)
        else:
            # 余弦相似度
            dot_product = np.dot(original_data, falsification)
            norm_original = np.linalg.norm(original_data, axis=1)
            norm_falsification = np.linalg.norm(falsification)
            dists = 1 - dot_product / (norm_original * norm_falsification)
            
        return float(np.mean(dists))

# 使用示例
if __name__ == "__main__":
    # 1. 生成模拟的小样本数据（如罕见病特征）
    np.random.seed(42)
    n_samples = 20  # 小样本
    n_features = 10
    X_train = np.random.rand(n_samples, n_features)  # 假设已归一化
    
    # 2. 初始化生成器
    generator = FalsificationGenerator(
        input_dim=n_features,
        latent_dim=8,
        device='auto'
    )
    
    # 3. 训练模型
    generator.fit(X_train, epochs=50)
    
    # 4. 生成潜在失败样本
    falsifications, latent_coords = generator.generate_falsifications(
        n_samples=5,
        temperature=1.5,
        boundary_threshold=0.9
    )
    
    # 5. 评估生成质量
    for i, sample in enumerate(falsifications):
        score = generator.evaluate_falsification(X_train, sample)
        print(f"反例 {i+1}: 与原始数据的平均距离 = {score:.4f}")
        
    print("生成的反例样本（前5维）:")
    print(falsifications[:, :5])