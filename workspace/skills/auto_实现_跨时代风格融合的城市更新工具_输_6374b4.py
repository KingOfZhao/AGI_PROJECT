"""
跨时代风格融合的城市更新工具 (Adaptive Style Transfer for Urban Renewal)

本模块实现了基于 Adaptive Instance Normalization (AdaIN) 的建筑风格迁移算法，
旨在解决历史街区风貌协调与城市更新的矛盾。通过分离图像的"内容"（结构、功能布局）
和"风格"（纹理、色彩、线条），实现现代建筑与历史建筑的深度融合。

Input Format:
    - Content Image: 现代建筑照片 (支持 .jpg/.png, RGB模式)
    - Style Image: 哥特式建筑参考图 (支持 .jpg/.png, RGB模式)

Output Format:
    - Blended Image: 风格融合后的建筑效果图 (RGB numpy array / .png file)

Dependencies:
    - torch, torchvision, PIL, numpy, logging
"""

import logging
import os
from typing import Tuple, Optional, Dict, Any

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import vgg19, VGG19_Weights

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UrbanStyleFusion")

# 常量定义
IMAGE_SIZE = 512
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}


class AdaptiveInstanceNorm(nn.Module):
    """
    自适应实例归一化层
    实现了论文 'Arbitrary Style Transfer in Real-time with Adaptive Instance Normalization' 
    的核心算法。
    
    Attributes:
        style_weight (float): 风格损失的权重
    """
    
    def __init__(self, style_weight: float = 1.0):
        super().__init__()
        self.style_weight = style_weight
        
    def forward(
        self, 
        content_feat: torch.Tensor, 
        style_feat: torch.Tensor
    ) -> torch.Tensor:
        """
        执行AdaIN操作
        
        Args:
            content_feat: 内容特征图 (B, C, H, W)
            style_feat: 风格特征图 (B, C, H, W)
            
        Returns:
            风格迁移后的特征图
        """
        # 计算内容特征的均值和标准差
        content_mean = torch.mean(content_feat, dim=[2, 3], keepdim=True)
        content_std = torch.std(content_feat, dim=[2, 3], keepdim=True) + 1e-6
        
        # 计算风格特征的均值和标准差
        style_mean = torch.mean(style_feat, dim=[2, 3], keepdim=True)
        style_std = torch.std(style_feat, dim=[2, 3], keepdim=True) + 1e-6
        
        # 归一化内容特征并应用风格统计量
        normalized = (content_feat - content_mean) / content_std
        return normalized * (self.style_weight * style_std) + style_mean


class StyleFusionEngine:
    """
    城市更新风格融合引擎
    
    核心功能:
        1. 加载预训练的VGG19网络用于特征提取
        2. 执行基于AdaIN的风格迁移
        3. 生成结构保留、风格融合的建筑效果图
        
    Example:
        >>> engine = StyleFusionEngine()
        >>> result = engine.generate(
        ...     content_path="modern_building.jpg",
        ...     style_path="gothic_cathedral.jpg",
        ...     output_path="blended_result.png"
        ... )
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        初始化引擎
        
        Args:
            device: 计算设备 ('cuda' 或 'cpu')
        """
        self.device = self._determine_device(device)
        logger.info(f"Initializing StyleFusionEngine on {self.device}")
        
        # 加载预训练模型
        self.encoder = self._load_encoder()
        self.decoder = self._load_decoder()
        self.adain = AdaptiveInstanceNorm()
        
        # 图像预处理
        self.preprocess = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=MEAN, std=STD)
        ])
        
        # 图像后处理
        self.postprocess = transforms.Compose([
            transforms.Normalize(
                mean=[-m/s for m, s in zip(MEAN, STD)],
                std=[1/s for s in STD]
            ),
            transforms.Lambda(lambda x: torch.clamp(x, 0, 1)),
            transforms.ToPILImage()
        ])

    def _determine_device(self, device: Optional[str]) -> str:
        """确定计算设备"""
        if device:
            return device
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_encoder(self) -> nn.Module:
        """加载VGG19编码器"""
        weights = VGG19_Weights.DEFAULT
        vgg = vgg19(weights=weights).features
        
        # 冻结所有参数
        for param in vgg.parameters():
            param.requires_grad = False
            
        return vgg.to(self.device).eval()

    def _load_decoder(self) -> nn.Module:
        """
        加载解码器 (简化实现)
        实际应用中应使用训练好的解码器权重
        """
        decoder = nn.Sequential(
            nn.Conv2d(512, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(256, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(128, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(64, 3, 3, padding=1)
        )
        return decoder.to(self.device).eval()

    def _validate_image_path(self, image_path: str) -> None:
        """
        验证图像路径
        
        Args:
            image_path: 图像文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {ext}. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )

    def _load_and_preprocess(
        self, 
        image_path: str
    ) -> Tuple[torch.Tensor, Image.Image]:
        """
        加载并预处理图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            预处理后的张量和原始PIL图像
        """
        self._validate_image_path(image_path)
        
        try:
            img = Image.open(image_path).convert('RGB')
            tensor = self.preprocess(img).unsqueeze(0).to(self.device)
            return tensor, img
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {str(e)}")
            raise

    def _extract_features(
        self, 
        x: torch.Tensor, 
        layers: Optional[list] = None
    ) -> Dict[str, torch.Tensor]:
        """
        提取多层特征
        
        Args:
            x: 输入张量
            layers: 需要提取特征的层索引列表
            
        Returns:
            特征字典 {层索引: 特征张量}
        """
        if layers is None:
            layers = ['4', '9', '18', '27']  # VGG19的关键层
            
        features = {}
        for name, module in self.encoder._modules.items():
            x = module(x)
            if name in layers:
                features[name] = x
                
        return features

    def generate(
        self,
        content_path: str,
        style_path: str,
        output_path: Optional[str] = None,
        alpha: float = 1.0,
        preserve_structure: bool = True
    ) -> np.ndarray:
        """
        生成风格融合图像
        
        Args:
            content_path: 现代建筑内容图像路径
            style_path: 哥特式风格图像路径
            output_path: 输出路径 (可选)
            alpha: 风格强度 [0.0, 1.0]
            preserve_structure: 是否严格保留建筑结构
            
        Returns:
            生成的RGB图像数组 (H, W, 3)
            
        Raises:
            ValueError: 输入参数无效
            RuntimeError: 生成过程出错
        """
        # 输入验证
        if not 0 <= alpha <= 1:
            raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
            
        logger.info(
            f"Generating style fusion: content={content_path}, "
            f"style={style_path}, alpha={alpha}"
        )
        
        try:
            # 加载并预处理图像
            content_tensor, _ = self._load_and_preprocess(content_path)
            style_tensor, _ = self._load_and_preprocess(style_path)
            
            # 提取特征
            with torch.no_grad():
                content_feats = self._extract_features(content_tensor)
                style_feats = self._extract_features(style_tensor)
                
                # 在关键层执行AdaIN
                target_feats = {}
                for layer in content_feats:
                    target_feats[layer] = self.adain(
                        content_feats[layer],
                        style_feats[layer]
                    )
                    
                # 如果需要严格保留结构，对底层特征进行混合
                if preserve_structure:
                    for layer in ['4', '9']:  # 底层特征保留更多内容
                        target_feats[layer] = (
                            alpha * target_feats[layer] + 
                            (1 - alpha) * content_feats[layer]
                        )
                
                # 使用解码器生成图像
                output = self.decoder(target_feats['27'])
                
            # 后处理
            output_img = self.postprocess(output.squeeze(0).cpu())
            output_array = np.array(output_img)
            
            # 保存结果
            if output_path:
                self._save_result(output_array, output_path)
                
            logger.info("Style fusion completed successfully")
            return output_array
            
        except Exception as e:
            logger.error(f"Error during style fusion: {str(e)}")
            raise RuntimeError(f"Style fusion failed: {str(e)}")

    def _save_result(self, img_array: np.ndarray, path: str) -> None:
        """
        保存结果图像
        
        Args:
            img_array: RGB图像数组
            path: 保存路径
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            Image.fromarray(img_array).save(path)
            logger.info(f"Result saved to {path}")
        except Exception as e:
            logger.error(f"Error saving result: {str(e)}")
            raise


def analyze_style_compatibility(
    content_path: str,
    style_path: str
) -> Dict[str, Any]:
    """
    分析风格兼容性 (辅助函数)
    
    计算内容图像与风格图像在特征空间的距离，
    为设计师提供量化参考指标。
    
    Args:
        content_path: 内容图像路径
        style_path: 风格图像路径
        
    Returns:
        兼容性分析结果字典，包含:
        - 'feature_distance': 特征空间距离
        - 'color_histogram_diff': 色彩直方图差异
        - 'texture_complexity': 纹理复杂度评分
        
    Example:
        >>> metrics = analyze_style_compatibility(
        ...     "modern_building.jpg",
        ...     "gothic_cathedral.jpg"
        ... )
        >>> print(f"Style distance: {metrics['feature_distance']:.2f}")
    """
    logger.info("Analyzing style compatibility...")
    
    # 加载图像
    preprocess = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor()
    ])
    
    try:
        content_img = Image.open(content_path).convert('RGB')
        style_img = Image.open(style_path).convert('RGB')
        
        content_tensor = preprocess(content_img).unsqueeze(0)
        style_tensor = preprocess(style_img).unsqueeze(0)
        
        # 计算特征距离
        with torch.no_grad():
            # 使用简单的L2距离作为示例
            distance = torch.norm(content_tensor - style_tensor).item()
            
        # 计算色彩直方图差异
        content_hist = np.histogram(
            np.array(content_img).flatten(), 
            bins=256, range=(0, 256)
        )[0]
        style_hist = np.histogram(
            np.array(style_img).flatten(), 
            bins=256, range=(0, 256)
        )[0]
        
        hist_diff = np.sum(np.abs(content_hist - style_hist)) / (
            content_img.size[0] * content_img.size[1]
        )
        
        # 计算纹理复杂度 (使用标准差作为简单度量)
        texture_complexity = np.std(np.array(style_img)) / 255
        
        return {
            'feature_distance': distance,
            'color_histogram_diff': hist_diff,
            'texture_complexity': texture_complexity
        }
        
    except Exception as e:
        logger.error(f"Error in compatibility analysis: {str(e)}")
        raise


if __name__ == "__main__":
    # 使用示例
    print("=== 跨时代风格融合的城市更新工具 ===")
    
    # 初始化引擎
    engine = StyleFusionEngine()
    
    # 分析风格兼容性
    try:
        metrics = analyze_style_compatibility(
            "modern_building.jpg",
            "gothic_cathedral.jpg"
        )
        print(f"Style compatibility metrics: {metrics}")
    except Exception as e:
        print(f"Compatibility analysis skipped: {str(e)}")
    
    # 生成风格融合图像
    try:
        result = engine.generate(
            content_path="modern_building.jpg",
            style_path="gothic_cathedral.jpg",
            output_path="blended_result.png",
            alpha=0.8,
            preserve_structure=True
        )
        print(f"Generated blended image with shape: {result.shape}")
    except Exception as e:
        print(f"Style fusion failed: {str(e)}")