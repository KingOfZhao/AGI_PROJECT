"""
名称: auto_物理约束下的认知节点生成_neuro_s_e7173e
描述: 物理约束下的认知节点生成（Neuro-Symbolic融合）。
     本模块实现了一个基于PyTorch的深度学习框架，将工业物理公式（如热传导方程）
     作为硬约束或软约束（损失函数项）嵌入网络训练过程。
     旨在解决纯数据驱动模型违背物理常识（如能量不守恒）的问题，
     使生成的'认知节点'不仅拟合观测数据，且符合物理规律。
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Dict, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_EPOCHS = 1000
PHYSICS_WEIGHT_INIT = 0.1

class PhysicsInformedNet(nn.Module):
    """
    一个简单的全连接神经网络，用于模拟物理场（如温度场）。
    包含自动微分机制以计算物理方程所需的导数。
    """
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super(PhysicsInformedNet, self).__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.layer3 = nn.Linear(hidden_dim, output_dim)
        self.activation = nn.Tanh()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.activation(self.layer1(x))
        x = self.activation(self.layer2(x))
        return self.layer3(x)


def validate_inputs(
    X_train: np.ndarray, 
    y_train: np.ndarray, 
    X_phys: np.ndarray
) -> None:
    """
    辅助函数：验证输入数据的维度和有效性。
    
    Args:
        X_train (np.ndarray): 训练集特征.
        y_train (np.ndarray): 训练集标签.
        X_phys (np.ndarray): 用于计算物理约束的坐标点.
        
    Raises:
        ValueError: 如果维度不匹配或数据包含非法值.
    """
    if X_train.shape[0] != y_train.shape[0]:
        raise ValueError("训练特征和标签的样本数量不匹配。")
    if X_train.shape[1] != X_phys.shape[1]:
        raise ValueError("训练数据和物理约束点的特征维度必须一致。")
    if np.isnan(X_train).any() or np.isnan(y_train).any():
        raise ValueError("输入数据包含NaN值，请清洗数据。")
    logger.info("输入数据验证通过。")


def compute_pde_residual(
    model: nn.Module, 
    x: torch.Tensor, 
    alpha: float = 0.1
) -> torch.Tensor:
    """
    核心函数 1: 计算物理方程的残差。
    以一维热传导方程为例: u_t = alpha * u_xx
    Residual = u_t - alpha * u_xx
    
    Args:
        model (nn.Module): 神经网络模型.
        x (torch.Tensor): 输入坐标.
        alpha (float): 热扩散系数.
        
    Returns:
        torch.Tensor: 物理方程的残差.
    """
    if not isinstance(x, torch.Tensor):
        raise TypeError("输入 x 必须是 torch.Tensor")
        
    # 开启梯度计算以便求导
    x.requires_grad_(True)
    
    u = model(x)
    
    # 计算一阶导数 (u_t 和 u_x)
    # grad_outputs=torch.ones_like(u) 用于缩放梯度
    u_grads = torch.autograd.grad(
        outputs=u, 
        inputs=x, 
        grad_outputs=torch.ones_like(u),
        create_graph=True,  # 保留计算图用于二阶导
        retain_graph=True
    )[0]
    
    u_t = u_grads[:, 0:1]  # 假设第0维是时间
    u_x = u_grads[:, 1:2]  # 假设第1维是空间
    
    # 计算二阶导数 u_xx
    u_xx = torch.autograd.grad(
        outputs=u_x, 
        inputs=x, 
        grad_outputs=torch.ones_like(u_x),
        create_graph=True
    )[0][:, 1:2]
    
    # 热传导方程残差
    residual = u_t - alpha * u_xx
    return residual


def train_physics_constrained_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_phys: np.ndarray,
    epochs: int = DEFAULT_EPOCHS,
    lambda_data: float = 1.0,
    lambda_physics: float = PHYSICS_WEIGHT_INIT
) -> Tuple[nn.Module, Dict[str, list]]:
    """
    核心函数 2: 训练物理约束下的神经网络。
    
    Args:
        X_train (np.ndarray): 观测数据输入.
        y_train (np.ndarray): 观测数据输出.
        X_phys (np.ndarray): 施加物理约束的采样点 (通常比观测数据更密集).
        epochs (int): 训练轮数.
        lambda_data (float): 数据损失的权重.
        lambda_physics (float): 物理损失的权重.
        
    Returns:
        Tuple[nn.Module, Dict]: 训练好的模型和损失历史记录。
        
    Example:
        >>> X = np.random.rand(100, 2)  # (t, x)
        >>> y = np.random.rand(100, 1)  # u
        >>> X_p = np.random.rand(1000, 2)
        >>> model, history = train_physics_constrained_model(X, y, X_p)
    """
    # 1. 数据验证
    validate_inputs(X_train, y_train, X_phys)
    
    # 2. 数据转换
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    X_tensor = torch.tensor(X_train, dtype=torch.float32).to(device)
    y_tensor = torch.tensor(y_train, dtype=torch.float32).to(device)
    X_phys_tensor = torch.tensor(X_phys, dtype=torch.float32).to(device)
    
    # 3. 模型初始化
    input_dim = X_train.shape[1]
    model = PhysicsInformedNet(input_dim=input_dim, hidden_dim=64, output_dim=1).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=DEFAULT_LEARNING_RATE)
    mse_loss = nn.MSELoss()
    
    history = {'data_loss': [], 'physics_loss': [], 'total_loss': []}
    
    logger.info("开始训练 Neuro-Symbolic 物理约束模型...")
    
    try:
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            
            # A. 数据驱动损失
            y_pred = model(X_tensor)
            loss_data = mse_loss(y_pred, y_tensor)
            
            # B. 物理约束损失
            # 计算PDE残差，目标是让残差趋近于0
            residual = compute_pde_residual(model, X_phys_tensor)
            loss_physics = torch.mean(residual ** 2)
            
            # C. 加权总损失
            total_loss = (lambda_data * loss_data) + (lambda_physics * loss_physics)
            
            # 反向传播
            total_loss.backward()
            optimizer.step()
            
            # 记录日志
            history['data_loss'].append(loss_data.item())
            history['physics_loss'].append(loss_physics.item())
            history['total_loss'].append(total_loss.item())
            
            if epoch % 100 == 0:
                logger.info(
                    f"Epoch {epoch}/{epochs} | "
                    f"Data Loss: {loss_data.item():.6f} | "
                    f"Physics Loss: {loss_physics.item():.6f}"
                )
                
    except Exception as e:
        logger.error(f"训练过程中发生错误: {str(e)}")
        raise RuntimeError("训练失败") from e
        
    logger.info("训练完成。")
    return model, history

# 以下为模块测试/使用示例代码
if __name__ == "__main__":
    # 模拟一个简单的热传导场景数据
    # 输入: (时间 t, 空间 x), 输出: 温度 u
    N_OBSERVATION = 50
    N_COLLOCATION = 200
    
    # 生成模拟观测数据 (带噪声)
    t_obs = np.random.uniform(0, 1, N_OBSERVATION)
    x_obs = np.random.uniform(0, 1, N_OBSERVATION)
    X_obs = np.vstack([t_obs, x_obs]).T
    # 模拟真实解 (例如 sin(pi*x)*exp(-t)) 加上噪声
    y_obs = (np.sin(np.pi * x_obs) * np.exp(-t_obs)).reshape(-1, 1) + \
            0.05 * np.random.randn(N_OBSERVATION, 1)
            
    # 生成配点 (用于物理约束，不需要标签)
    t_col = np.random.uniform(0, 1, N_COLLOCATION)
    x_col = np.random.uniform(0, 1, N_COLLOCATION)
    X_col = np.vstack([t_col, x_col]).T
    
    # 运行训练
    try:
        trained_model, loss_history = train_physics_constrained_model(
            X_train=X_obs,
            y_train=y_obs,
            X_phys=X_col,
            epochs=500,
            lambda_physics=0.5
        )
        print(f"最终数据损失: {loss_history['data_loss'][-1]:.4f}")
    except Exception as e:
        print(f"运行示例失败: {e}")