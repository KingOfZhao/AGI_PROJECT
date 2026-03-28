"""
全尺度一致性生成系统

本模块实现了一个基于改进U-Net架构的多尺度图像生成系统，专门解决AI画图中"大关系对但构造错"的问题。
通过分层生成和跳跃连接机制，确保建筑外观（宏观）与构造细节（微观）的一致性。

核心功能：
1. 多尺度特征提取与融合
2. 建筑风格到材质纹理的跨尺度传递
3. 力学逻辑约束的构造节点生成

输入格式：
- 输入图像: RGB格式，尺寸为(H, W, 3)，值域[0, 1]
- 风格向量: 形状为(1, style_dim)的numpy数组

输出格式：
- 生成图像: RGB格式，尺寸为(H*scale, W*scale, 3)
- 构造层级: 单通道灰度图，尺寸与生成图像相同

示例用法:
    >>> system = ConsistencyGenerationSystem()
    >>> output = system.generate("input.jpg", style_vector=np.random.randn(1, 128))
"""

import logging
import numpy as np
from typing import Tuple, Optional, Dict, Union
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('consistency_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MultiScaleConsistencyBlock(nn.Module):
    """多尺度一致性特征融合模块
    
    通过跳跃连接将不同尺度的特征图进行融合，确保风格一致性
    
    Attributes:
        in_channels (int): 输入特征通道数
        out_channels (int): 输出特征通道数
        scale_factor (int): 尺度因子
    """
    
    def __init__(self, in_channels: int, out_channels: int, scale_factor: int = 2):
        """初始化多尺度一致性块
        
        Args:
            in_channels: 输入特征通道数
            out_channels: 输出特征通道数
            scale_factor: 尺度缩放因子，默认为2
            
        Raises:
            ValueError: 如果scale_factor小于1
        """
        super().__init__()
        if scale_factor < 1:
            raise ValueError("Scale factor must be greater than or equal to 1")
            
        self.scale_factor = scale_factor
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.InstanceNorm2d(out_channels),
            nn.LeakyReLU(0.2, inplace=True)
        )
        
        # 力学逻辑约束层
        self.structural_constraint = nn.Sequential(
            nn.Conv2d(out_channels, out_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor, skip: Optional[torch.Tensor] = None) -> torch.Tensor:
        """前向传播
        
        Args:
            x: 输入特征张量
            skip: 跳跃连接的特征张量
            
        Returns:
            融合后的特征张量
        """
        if skip is not None:
            # 调整跳跃连接特征的尺度以匹配当前特征
            if skip.shape[2:] != x.shape[2:]:
                skip = F.interpolate(skip, size=x.shape[2:], mode='bilinear', align_corners=True)
            x = torch.cat([x, skip], dim=1)
            
        x = self.conv(x)
        
        # 应用力学约束
        structural_mask = self.structural_constraint(x)
        x = x * structural_mask
        
        return x


class ConsistencyGenerationSystem(nn.Module):
    """全尺度一致性生成系统主类
    
    基于改进U-Net架构实现建筑外观与构造细节的一致性生成
    
    Attributes:
        image_size (int): 输入图像尺寸
        style_dim (int): 风格向量维度
        device (str): 计算设备
    """
    
    def __init__(self, image_size: int = 256, style_dim: int = 128, device: str = 'auto'):
        """初始化生成系统
        
        Args:
            image_size: 输入图像尺寸，默认为256
            style_dim: 风格向量维度，默认为128
            device: 计算设备，'auto'表示自动选择
            
        Raises:
            ValueError: 如果参数不合法
        """
        super().__init__()
        
        # 参数验证
        if image_size <= 0 or image_size % 2 != 0:
            raise ValueError("Image size must be positive even number")
        if style_dim <= 0:
            raise ValueError("Style dimension must be positive")
            
        self.image_size = image_size
        self.style_dim = style_dim
        
        # 设备选择
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        logger.info(f"Initializing system on {self.device}")
        
        # 编码器路径
        self.enc1 = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.enc2 = MultiScaleConsistencyBlock(64, 128)
        self.enc3 = MultiScaleConsistencyBlock(128, 256)
        self.enc4 = MultiScaleConsistencyBlock(256, 512)
        
        # 风格注入模块
        self.style_proj = nn.Linear(style_dim, 512)
        
        # 解码器路径
        self.dec1 = MultiScaleConsistencyBlock(512 + 512, 256)
        self.dec2 = MultiScaleConsistencyBlock(256 + 256, 128)
        self.dec3 = MultiScaleConsistencyBlock(128 + 128, 64)
        self.dec4 = nn.Sequential(
            nn.ConvTranspose2d(64 + 64, 3, kernel_size=4, stride=2, padding=1),
            nn.Tanh()
        )
        
        # 构造细节生成器
        self.detail_gen = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, 1, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        
        self.to(self.device)
        logger.info("System initialized successfully")
        
    def _validate_input(self, image: Union[str, np.ndarray, torch.Tensor]) -> torch.Tensor:
        """验证并预处理输入图像
        
        Args:
            image: 输入图像，可以是文件路径、numpy数组或torch张量
            
        Returns:
            预处理后的图像张量
            
        Raises:
            ValueError: 如果输入格式不支持
            FileNotFoundError: 如果文件路径不存在
        """
        try:
            if isinstance(image, str):
                if not Path(image).exists():
                    raise FileNotFoundError(f"Image file not found: {image}")
                image = Image.open(image).convert('RGB')
                image = transforms.ToTensor()(image)
            elif isinstance(image, np.ndarray):
                if image.ndim != 3 or image.shape[2] != 3:
                    raise ValueError("Input numpy array must be HWC format with 3 channels")
                image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
            elif isinstance(image, torch.Tensor):
                if image.ndim != 3 or image.shape[0] != 3:
                    raise ValueError("Input tensor must be CHW format with 3 channels")
            else:
                raise ValueError(f"Unsupported input type: {type(image)}")
                
            # 调整尺寸
            if image.shape[1] != self.image_size or image.shape[2] != self.image_size:
                image = F.interpolate(
                    image.unsqueeze(0), 
                    size=(self.image_size, self.image_size), 
                    mode='bilinear',
                    align_corners=True
                ).squeeze(0)
                
            return image.unsqueeze(0).to(self.device)
            
        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            raise
            
    def _validate_style_vector(self, style_vector: Optional[np.ndarray]) -> torch.Tensor:
        """验证并预处理风格向量
        
        Args:
            style_vector: 风格向量，形状为(1, style_dim)
            
        Returns:
            预处理后的风格向量张量
            
        Raises:
            ValueError: 如果风格向量维度不匹配
        """
        if style_vector is None:
            style_vector = np.random.randn(1, self.style_dim)
            
        if not isinstance(style_vector, np.ndarray):
            style_vector = np.array(style_vector)
            
        if style_vector.shape != (1, self.style_dim):
            raise ValueError(f"Style vector must have shape (1, {self.style_dim})")
            
        return torch.from_numpy(style_vector).float().to(self.device)
        
    def forward(self, x: torch.Tensor, style_vector: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播
        
        Args:
            x: 输入图像张量，形状为(B, C, H, W)
            style_vector: 风格向量，形状为(B, style_dim)
            
        Returns:
            Tuple[生成图像, 构造层级]
        """
        # 编码器路径
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        
        # 风格注入
        style_features = self.style_proj(style_vector).unsqueeze(-1).unsqueeze(-1)
        e4 = e4 * style_features
        
        # 解码器路径（带跳跃连接）
        d1 = self.dec1(e4, e3)
        d2 = self.dec2(d1, e2)
        d3 = self.dec3(d2, e1)
        output = self.dec4(d3)
        
        # 生成构造细节
        structural_details = self.detail_gen(output)
        
        return output, structural_details
        
    def generate(
        self, 
        image: Union[str, np.ndarray, torch.Tensor], 
        style_vector: Optional[np.ndarray] = None,
        output_size: int = 512
    ) -> Dict[str, np.ndarray]:
        """生成全尺度一致性图像
        
        Args:
            image: 输入图像
            style_vector: 风格向量，如果为None则随机生成
            output_size: 输出图像尺寸，默认为512
            
        Returns:
            包含生成图像和构造层级的字典
            
        Raises:
            ValueError: 如果参数不合法
        """
        try:
            # 验证输出尺寸
            if output_size <= 0 or output_size % 2 != 0:
                raise ValueError("Output size must be positive even number")
                
            logger.info("Starting generation process")
            
            # 验证输入
            input_tensor = self._validate_input(image)
            style_tensor = self._validate_style_vector(style_vector)
            
            # 生成图像
            with torch.no_grad():
                output, structural = self.forward(input_tensor, style_tensor)
                
            # 后处理
            output = F.interpolate(
                output, 
                size=(output_size, output_size), 
                mode='bilinear',
                align_corners=True
            )
            structural = F.interpolate(
                structural, 
                size=(output_size, output_size), 
                mode='bilinear',
                align_corners=True
            )
            
            # 转换为numpy数组
            output_np = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
            structural_np = structural.squeeze(0).permute(1, 2, 0).cpu().numpy()
            
            # 值域调整到[0, 255]
            output_np = ((output_np + 1) / 2 * 255).astype(np.uint8)
            structural_np = (structural_np * 255).astype(np.uint8)
            
            logger.info("Generation completed successfully")
            
            return {
                'generated_image': output_np,
                'structural_details': structural_np,
                'metadata': {
                    'input_size': self.image_size,
                    'output_size': output_size,
                    'style_dim': self.style_dim
                }
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise


# 示例用法
if __name__ == "__main__":
    try:
        # 初始化系统
        system = ConsistencyGenerationSystem(image_size=256, style_dim=128)
        
        # 生成示例图像
        # 输入: 随机生成的噪声图像
        # 输出: 512x512的建筑图像和构造细节
        input_image = np.random.rand(256, 256, 3).astype(np.float32)
        style_vector = np.random.randn(1, 128)
        
        result = system.generate(input_image, style_vector=style_vector, output_size=512)
        
        print(f"Generated image shape: {result['generated_image'].shape}")
        print(f"Structural details shape: {result['structural_details'].shape}")
        
        # 保存结果
        Image.fromarray(result['generated_image']).save('generated_building.png')
        Image.fromarray(result['structural_details'].squeeze(), mode='L').save('structural_details.png')
        
    except Exception as e:
        logger.error(f"Error in example usage: {str(e)}")