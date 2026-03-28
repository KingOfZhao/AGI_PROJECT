"""
高级Python模块：基于环境响应式的上下文参数生成网络

该模块实现了一种受“气候适应性建筑表皮”启发的神经网络微架构。
它不再依赖固定的微调权重（如LoRA），而是通过感知输入数据的统计特征（即“数据气候”），
实时动态地生成或插值网络参数，实现零样本的领域自适应。
"""

import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NetworkConfig:
    """网络配置参数"""
    input_dim: int = 512
    hidden_dim: int = 256
    output_dim: int = 128
    climate_dim: int = 32  # 用于描述数据气候的潜在空间维度
    dynamic_rank: int = 16  # 动态生成的低秩矩阵秩
    climate_sensitivity: float = 0.1  # 对环境变化的敏感度阈值

class ClimateSensor(nn.Module):
    """
    气候感知模块
    类比于建筑中的环境传感器，用于检测输入数据的统计分布特征。
    """
    def __init__(self, input_dim: int, climate_dim: int):
        super().__init__()
        self.sensor = nn.Sequential(
            nn.Linear(input_dim, climate_dim * 2),
            nn.ReLU(),
            nn.Linear(climate_dim * 2, climate_dim),
            nn.Tanh()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        感知数据气候
        
        Args:
            x: 输入张量 (batch_size, input_dim)
            
        Returns:
            气候特征向量 (batch_size, climate_dim)
        """
        # 数据验证
        if x.dim() != 2:
            raise ValueError(f"输入张量必须是2D (batch, dim), 但得到 {x.dim()}D")
            
        # 计算输入的统计特征
        mean = torch.mean(x, dim=1, keepdim=True)
        std = torch.std(x, dim=1, keepdim=True)
        
        # 归一化输入
        normalized_x = (x - mean) / (std + 1e-8)
        
        # 感知气候特征
        climate_features = self.sensor(normalized_x)
        
        return climate_features

class DynamicEpidermis(nn.Module):
    """
    动态表皮模块
    类比于建筑的呼吸幕墙，根据感知到的气候特征动态调整网络形态。
    """
    def __init__(self, config: NetworkConfig):
        super().__init__()
        self.config = config
        
        # 基础静态权重（作为锚点）
        self.base_weight = nn.Parameter(torch.randn(config.output_dim, config.input_dim) * 0.01)
        
        # 动态参数生成器
        self.delta_A_generator = nn.Linear(config.climate_dim, config.input_dim * config.dynamic_rank)
        self.delta_B_generator = nn.Linear(config.climate_dim, config.output_dim * config.dynamic_rank)
        
        # 气候感知器
        self.climate_sensor = ClimateSensor(config.input_dim, config.climate_dim)
        
        # 形态记忆（存储历史气候模式）
        self.morph_memory: Dict[str, torch.Tensor] = {}
        
    def _validate_climate_features(self, climate_features: torch.Tensor) -> None:
        """验证气候特征的有效性"""
        if torch.isnan(climate_features).any():
            raise ValueError("检测到气候特征中的NaN值")
        if torch.isinf(climate_features).any():
            raise ValueError("检测到气候特征中的无限值")
            
    def generate_dynamic_weights(self, climate_features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        根据气候特征生成动态权重调整量
        
        Args:
            climate_features: 气候特征向量 (batch_size, climate_dim)
            
        Returns:
            Tuple[delta_A, delta_B]: 动态低秩矩阵分量
        """
        self._validate_climate_features(climate_features)
        
        # 生成低秩矩阵分量 (类比于建筑表皮的动态开合)
        delta_A = self.delta_A_generator(climate_features)
        delta_B = self.delta_B_generator(climate_features)
        
        # 重塑为矩阵形式
        batch_size = climate_features.size(0)
        delta_A = delta_A.view(batch_size, self.config.input_dim, self.config.dynamic_rank)
        delta_B = delta_B.view(batch_size, self.config.dynamic_rank, self.config.output_dim)
        
        return delta_A, delta_B
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播，实现动态参数调整
        
        Args:
            x: 输入张量 (batch_size, input_dim)
            
        Returns:
            输出张量 (batch_size, output_dim)
        """
        try:
            # 感知当前数据气候
            climate_features = self.climate_sensor(x)
            
            # 生成动态权重调整
            delta_A, delta_B = self.generate_dynamic_weights(climate_features)
            
            # 计算动态权重增量 (低秩分解)
            # 使用 einsum 优化计算
            delta_W = torch.einsum('bir, bro -> bio', delta_A, delta_B)
            
            # 应用动态调整 (形态发生)
            batch_size = x.size(0)
            output = torch.zeros(batch_size, self.config.output_dim, device=x.device)
            
            for i in range(batch_size):
                # 结合基础权重和动态权重
                adapted_weight = self.base_weight + delta_W[i]
                
                # 边界检查
                if torch.isnan(adapted_weight).any():
                    logger.warning(f"批次 {i} 中检测到异常权重，使用基础权重")
                    adapted_weight = self.base_weight
                
                # 计算输出
                output[i] = F.linear(x[i:i+1], adapted_weight).squeeze(0)
                
            return output
            
        except Exception as e:
            logger.error(f"动态表皮处理错误: {str(e)}")
            # 回退到基础权重
            return F.linear(x, self.base_weight)

class DataClimateAE(nn.Module):
    """
    自适应环境响应网络 (Adaptive Environment Responsive Network)
    主模型类，整合气候感知和动态表皮模块。
    """
    def __init__(self, config: Optional[NetworkConfig] = None):
        super().__init__()
        self.config = config or NetworkConfig()
        
        # 验证配置
        self._validate_config()
        
        # 构建网络组件
        self.climate_sensor = ClimateSensor(self.config.input_dim, self.config.climate_dim)
        self.dynamic_epidermis = DynamicEpidermis(self.config)
        
        # 输出层
        self.output_layer = nn.Sequential(
            nn.Linear(self.config.output_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.config.hidden_dim, self.config.input_dim)
        )
        
        logger.info(f"初始化DataClimateAE，配置: {self.config}")
        
    def _validate_config(self) -> None:
        """验证网络配置的有效性"""
        if self.config.input_dim <= 0:
            raise ValueError(f"输入维度必须为正数，得到 {self.config.input_dim}")
        if self.config.hidden_dim <= 0:
            raise ValueError(f"隐藏维度必须为正数，得到 {self.config.hidden_dim}")
        if self.config.dynamic_rank <= 0:
            raise ValueError(f"动态秩必须为正数，得到 {self.config.dynamic_rank}")
        if not 0 <= self.config.climate_sensitivity <= 1:
            raise ValueError(f"敏感度必须在[0,1]之间，得到 {self.config.climate_sensitivity}")
            
    def analyze_climate(self, x: torch.Tensor) -> Dict[str, float]:
        """
        辅助函数：分析数据气候的统计特征
        
        Args:
            x: 输入张量 (batch_size, input_dim)
            
        Returns:
            包含气候统计信息的字典
        """
        with torch.no_grad():
            climate_features = self.climate_sensor(x)
            
            return {
                "climate_mean": torch.mean(climate_features).item(),
                "climate_std": torch.std(climate_features).item(),
                "climate_max": torch.max(climate_features).item(),
                "climate_min": torch.min(climate_features).item(),
                "climate_entropy": self._calculate_climate_entropy(climate_features)
            }
            
    def _calculate_climate_entropy(self, features: torch.Tensor) -> float:
        """计算气候特征的熵（衡量多样性）"""
        # 归一化为概率分布
        prob = F.softmax(features.flatten(), dim=0)
        log_prob = torch.log(prob + 1e-10)
        entropy = -torch.sum(prob * log_prob).item()
        return entropy
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        前向传播
        
        Args:
            x: 输入张量 (batch_size, input_dim)
            
        Returns:
            Tuple[output, climate_stats]: 输出张量和气候统计信息
        """
        # 数据验证
        if x.dim() != 2:
            raise ValueError(f"输入必须是2D张量，但得到 {x.dim()}D")
        if x.size(1) != self.config.input_dim:
            raise ValueError(f"输入维度不匹配，期望 {self.config.input_dim}，得到 {x.size(1)}")
            
        # 处理动态表皮
        epidermis_output = self.dynamic_epidermis(x)
        
        # 最终输出
        output = self.output_layer(epidermis_output)
        
        # 分析气候
        climate_stats = self.analyze_climate(x)
        
        return output, climate_stats

# 使用示例
if __name__ == "__main__":
    # 示例配置
    config = NetworkConfig(
        input_dim=128,
        hidden_dim=64,
        output_dim=32,
        climate_dim=16,
        dynamic_rank=8
    )
    
    # 初始化模型
    model = DataClimateAE(config)
    
    # 模拟不同"气候"的输入数据
    batch_size = 4
    input_dim = config.input_dim
    
    # 气候1: 平稳分布
    data_stable = torch.randn(batch_size, input_dim) * 0.5 + 2.0
    
    # 气候2: 剧烈波动
    data_volatile = torch.randn(batch_size, input_dim) * 5.0 - 3.0
    
    # 运行模型
    print("\n=== 平稳气候测试 ===")
    output_stable, stats_stable = model(data_stable)
    print(f"输出形状: {output_stable.shape}")
    print(f"气候统计: {stats_stable}")
    
    print("\n=== 剧烈波动气候测试 ===")
    output_volatile, stats_volatile = model(data_volatile)
    print(f"输出形状: {output_volatile.shape}")
    print(f"气候统计: {stats_volatile}")
    
    # 比较不同气候下的模型行为差异
    print("\n=== 气候影响分析 ===")
    print(f"平稳气候熵: {stats_stable['climate_entropy']:.4f}")
    print(f"波动气候熵: {stats_volatile['climate_entropy']:.4f}")