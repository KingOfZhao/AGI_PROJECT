"""
跨模态意图对齐模块

该模块实现了将视觉信息（如UI截图、草图）与文本描述融合，转化为统一结构化数据的功能。
核心功能包括多模态特征提取、特征融合和结构化输出生成。

典型使用场景：
- 用户上传UI草图并附注"风格要现代"，系统生成对应的DOM树描述
- 解析参考网页截图，结合文本指令生成结构化布局数据

输入格式：
- 视觉输入: 支持PIL.Image/numpy.ndarray格式的图像数据
- 文本输入: UTF-8编码的字符串

输出格式：
- 结构化JSON，包含布局元素、样式属性和位置信息
"""

import logging
import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union, Any
from pathlib import Path

import numpy as np
from PIL import Image

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MultimodalConfig:
    """多模态处理配置"""
    image_size: Tuple[int, int] = (224, 224)
    text_max_length: int = 512
    feature_dim: int = 768
    fusion_strategy: str = 'attention'  # ['concat', 'attention', 'bilinear']

class MultimodalEncoder:
    """多模态编码器基类"""
    
    def __init__(self, config: MultimodalConfig):
        self.config = config
        self._validate_config()
        
    def _validate_config(self) -> None:
        """验证配置参数有效性"""
        if self.config.image_size[0] <= 0 or self.config.image_size[1] <= 0:
            raise ValueError("Image dimensions must be positive")
        if self.config.text_max_length <= 0:
            raise ValueError("Text max length must be positive")
        if self.config.feature_dim <= 0:
            raise ValueError("Feature dimension must be positive")
        if self.config.fusion_strategy not in ['concat', 'attention', 'bilinear']:
            raise ValueError(f"Unsupported fusion strategy: {self.config.fusion_strategy}")

class CrossModalAligner(MultimodalEncoder):
    """跨模态意图对齐器"""
    
    def __init__(self, config: Optional[MultimodalConfig] = None):
        config = config or MultimodalConfig()
        super().__init__(config)
        logger.info("Initialized CrossModalAligner with config: %s", config)
    
    def _preprocess_image(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """图像预处理辅助函数"""
        if isinstance(image, np.ndarray):
            if image.ndim not in [2, 3]:
                raise ValueError("Input array must be 2D (grayscale) or 3D (color)")
            image = Image.fromarray(image)
        
        # 转换为RGB模式（处理灰度/RGBA等情况）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 调整大小并归一化
        image = image.resize(self.config.image_size)
        return np.array(image) / 255.0
    
    def _encode_text(self, text: str) -> np.ndarray:
        """文本编码（模拟实现）"""
        if not isinstance(text, str):
            raise TypeError("Text input must be a string")
        
        # 简单特征提取：使用字符频率统计作为特征（实际应用中应使用预训练模型）
        char_freq = np.zeros((self.config.feature_dim,))
        for char in text.lower():
            idx = ord(char) % self.config.feature_dim
            char_freq[idx] += 1
        
        # 归一化
        norm = np.linalg.norm(char_freq)
        return char_freq / norm if norm > 0 else char_freq
    
    def _encode_image(self, image: np.ndarray) -> np.ndarray:
        """图像编码（模拟实现）"""
        # 简单特征提取：使用颜色直方图作为特征（实际应用中应使用CNN等）
        features = []
        for channel in range(3):
            hist, _ = np.histogram(
                image[:, :, channel].ravel(),
                bins=self.config.feature_dim // 3,
                range=(0, 1)
            )
            features.append(hist)
        
        # 合并通道特征
        image_features = np.concatenate(features)
        
        # 填充到指定维度
        if len(image_features) < self.config.feature_dim:
            padding = np.zeros((self.config.feature_dim - len(image_features),))
            image_features = np.concatenate([image_features, padding])
        elif len(image_features) > self.config.feature_dim:
            image_features = image_features[:self.config.feature_dim]
        
        return image_features / np.sum(image_features)
    
    def _fuse_features(
        self,
        visual_features: np.ndarray,
        text_features: np.ndarray
    ) -> np.ndarray:
        """特征融合"""
        if self.config.fusion_strategy == 'concat':
            return np.concatenate([visual_features, text_features])
        elif self.config.fusion_strategy == 'attention':
            # 简单注意力机制（模拟）
            weights = np.exp(visual_features) / np.sum(np.exp(visual_features))
            return weights * text_features
        else:  # bilinear
            return visual_features * text_features
    
    def align_intent(
        self,
        image: Union[Image.Image, np.ndarray, str, Path],
        text: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对齐视觉和文本意图，生成结构化输出
        
        参数:
            image: 输入图像，可以是PIL.Image/numpy数组/文件路径
            text: 文本描述
            output_path: 可选，结构化输出保存路径
            
        返回:
            包含对齐结果的结构化字典
            
        示例:
            >>> aligner = CrossModalAligner()
            >>> result = aligner.align_intent("ui_sketch.png", "现代风格")
            >>> print(result['dom_tree']['style']['theme'])
            'modern'
        """
        try:
            # 输入验证
            if not text.strip():
                raise ValueError("Text description cannot be empty")
            
            # 处理不同输入类型的图像
            if isinstance(image, (str, Path)):
                image = Image.open(image)
            
            processed_img = self._preprocess_image(image)
            
            # 特征提取
            visual_features = self._encode_image(processed_img)
            text_features = self._encode_text(text)
            
            # 特征融合
            fused_features = self._fuse_features(visual_features, text_features)
            
            # 生成结构化输出（简化版DOM树）
            dom_tree = {
                "metadata": {
                    "source": "multimodal_aligner",
                    "version": "1.0",
                    "input_shapes": {
                        "image": processed_img.shape,
                        "text": len(text)
                    }
                },
                "layout": self._generate_layout(fused_features),
                "style": self._generate_style(text, fused_features),
                "components": self._detect_components(fused_features)
            }
            
            # 保存输出（如果指定路径）
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(dom_tree, f, indent=2)
                logger.info("Saved structured output to %s", output_path)
            
            return {"status": "success", "dom_tree": dom_tree}
        
        except Exception as e:
            logger.error("Intent alignment failed: %s", str(e))
            return {"status": "error", "message": str(e)}
    
    def _generate_layout(self, features: np.ndarray) -> Dict[str, Any]:
        """生成布局信息（辅助函数）"""
        # 简化逻辑：基于特征统计生成布局
        layout_type = "grid" if np.mean(features) > 0.5 else "flex"
        return {
            "type": layout_type,
            "columns": int(np.sum(features[:10]) * 12) + 1,  # 模拟12列网格
            "rows": int(np.sum(features[10:20]) * 10) + 1,
            "spacing": f"{int(np.max(features[:30]) * 20)}px"
        }
    
    def _generate_style(self, text: str, features: np.ndarray) -> Dict[str, Any]:
        """生成样式信息（辅助函数）"""
        # 基于文本关键词确定风格
        style = {
            "theme": "default",
            "color_scheme": "light",
            "font_family": "sans-serif"
        }
        
        if "现代" in text or "极简" in text:
            style.update({
                "theme": "modern",
                "font_family": "Helvetica Neue"
            })
        elif "复古" in text or "古典" in text:
            style.update({
                "theme": "classic",
                "font_family": "Georgia"
            })
        
        # 基于特征确定配色
        if np.mean(features[100:200]) > 0.7:
            style["color_scheme"] = "dark"
        
        return style
    
    def _detect_components(self, features: np.ndarray) -> list:
        """检测UI组件（辅助函数）"""
        # 模拟组件检测逻辑
        components = []
        if np.max(features[:50]) > 0.8:
            components.append({"type": "header", "confidence": 0.92})
        if np.mean(features[50:100]) > 0.6:
            components.append({"type": "card", "count": int(np.sum(features[50:100]) * 5)})
        if np.max(features[200:250]) > 0.9:
            components.append({"type": "button", "position": "bottom-right"})
        
        return components

# 示例用法
if __name__ == "__main__":
    # 初始化对齐器
    config = MultimodalConfig(fusion_strategy='attention')
    aligner = CrossModalAligner(config)
    
    # 示例1：使用图像文件和文本
    try:
        # 创建示例图像（实际应用中应替换为真实图像路径）
        demo_img = np.random.rand(300, 300, 3) * 255
        demo_img = demo_img.astype(np.uint8)
        
        result = aligner.align_intent(
            image=demo_img,
            text="创建一个现代风格的仪表盘布局，包含三个数据卡片",
            output_path="demo_output.json"
        )
        
        if result["status"] == "success":
            print("对齐成功！生成的DOM树结构：")
            print(json.dumps(result["dom_tree"], indent=2))
        else:
            print(f"处理失败: {result['message']}")
    
    except Exception as e:
        print(f"示例运行出错: {str(e)}")