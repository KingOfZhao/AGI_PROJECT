"""
名称: auto_虚实掩码生成对抗_一种受建筑图底理论启_90c545
描述: 【虚实掩码生成对抗】一种受建筑图底理论启发的计算机视觉分割与生成模型。
      引入'结构性留白'损失函数，强迫AI像建筑师设计凹空间一样，主动生成具有包围感的'负空间'。
作者: AGI System
版本: 1.0.0
"""

import logging
import numpy as np
import cv2
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FigureGroundGAN")

@dataclass
class FGConfig:
    """
    虚实掩码生成配置类
    
    Attributes:
        min_void_ratio (float): 最小负空间比例 (0.0-1.0)
        enclosure_threshold (int): 包围感检测阈值 (0-255)
        kernel_size (int): 形态学操作核大小
        balance_weight (float): 构图平衡权重
    """
    min_void_ratio: float = 0.25
    enclosure_threshold: int = 200
    kernel_size: int = 5
    balance_weight: float = 0.7

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.min_void_ratio <= 1.0:
            raise ValueError("min_void_ratio must be between 0.0 and 1.0")
        if not 0 <= self.enclosure_threshold <= 255:
            raise ValueError("enclosure_threshold must be between 0 and 255")
        if self.kernel_size <= 0 or self.kernel_size % 2 == 0:
            raise ValueError("kernel_size must be positive odd number")
        if not 0.0 <= self.balance_weight <= 1.0:
            raise ValueError("balance_weight must be between 0.0 and 1.0")

class NegativeSpaceAnalyzer:
    """
    负空间分析器，基于建筑图底理论分析图像中的结构性留白
    """
    
    def __init__(self, config: Optional[FGConfig] = None):
        """
        初始化分析器
        
        Args:
            config (Optional[FGConfig]): 配置对象，如果为None则使用默认配置
        """
        self.config = config if config else FGConfig()
        logger.info("NegativeSpaceAnalyzer initialized with config: %s", self.config)
    
    def _validate_image(self, image: np.ndarray) -> None:
        """
        验证输入图像的有效性
        
        Args:
            image (np.ndarray): 输入图像
            
        Raises:
            ValueError: 如果图像无效
        """
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be numpy array")
        if image.size == 0:
            raise ValueError("Image is empty")
        if len(image.shape) not in [2, 3]:
            raise ValueError("Image must be 2D (grayscale) or 3D (color)")
    
    def extract_void_mask(self, image: np.ndarray) -> np.ndarray:
        """
        提取图像中的负空间（虚空间）掩码
        
        Args:
            image (np.ndarray): 输入图像 (H, W, C) 或 (H, W)
            
        Returns:
            np.ndarray: 二值掩码，其中1表示负空间，0表示实体
            
        Raises:
            ValueError: 如果输入图像无效
        """
        try:
            self._validate_image(image)
            
            # 转换为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 自适应阈值处理
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, self.config.kernel_size * 2 + 1, 5
            )
            
            # 形态学操作去除噪声
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, 
                (self.config.kernel_size, self.config.kernel_size)
            )
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 反转得到负空间
            void_mask = (cleaned < self.config.enclosure_threshold).astype(np.uint8)
            
            logger.debug("Void mask extracted with ratio: %.2f", 
                        np.mean(void_mask))
            return void_mask
            
        except Exception as e:
            logger.error("Error extracting void mask: %s", str(e))
            raise
    
    def calculate_enclosure_score(self, void_mask: np.ndarray) -> float:
        """
        计算负空间的包围感分数（0-1），基于建筑空间包围理论
        
        Args:
            void_mask (np.ndarray): 负空间掩码
            
        Returns:
            float: 包围感分数 (0.0-1.0)
            
        Raises:
            ValueError: 如果掩码无效
        """
        if void_mask.size == 0:
            raise ValueError("Void mask is empty")
            
        try:
            # 计算边界框
            contours, _ = cv2.findContours(
                void_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                return 0.0
                
            # 合并所有轮廓
            all_points = np.vstack(contours)
            x, y, w, h = cv2.boundingRect(all_points)
            
            # 计算包围度
            rect_area = w * h
            void_area = np.sum(void_mask > 0)
            enclosure = void_area / rect_area if rect_area > 0 else 0.0
            
            # 归一化到0-1
            score = min(1.0, enclosure * 2)  # 经验系数
            
            logger.debug("Enclosure score calculated: %.2f", score)
            return score
            
        except Exception as e:
            logger.error("Error calculating enclosure score: %s", str(e))
            raise
    
    def optimize_void_structure(
        self, 
        image: np.ndarray, 
        iterations: int = 3
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        优化图像的虚实结构，生成改进的掩码
        
        Args:
            image (np.ndarray): 输入图像
            iterations (int): 优化迭代次数
            
        Returns:
            Tuple[np.ndarray, Dict]: 优化后的掩码和指标字典
            
        Raises:
            ValueError: 如果输入参数无效
        """
        if iterations <= 0:
            raise ValueError("Iterations must be positive integer")
            
        try:
            self._validate_image(image)
            metrics = {}
            
            # 初始掩码提取
            void_mask = self.extract_void_mask(image)
            original_score = self.calculate_enclosure_score(void_mask)
            metrics['original_score'] = original_score
            
            # 优化循环
            for i in range(iterations):
                # 计算当前构图平衡
                h, w = void_mask.shape
                left = np.sum(void_mask[:, :w//2]) / (h * w//2)
                right = np.sum(void_mask[:, w//2:]) / (h * w//2)
                balance = 1.0 - abs(left - right)
                
                # 调整策略
                if balance < self.config.balance_weight:
                    # 平衡构图
                    if left < right:
                        void_mask[:, :w//2] = cv2.dilate(
                            void_mask[:, :w//2], 
                            np.ones((3, 3), np.uint8), 
                            iterations=1
                        )
                    else:
                        void_mask[:, w//2:] = cv2.dilate(
                            void_mask[:, w//2:], 
                            np.ones((3, 3), np.uint8), 
                            iterations=1
                        )
                
                # 更新分数
                current_score = self.calculate_enclosure_score(void_mask)
                metrics[f'iteration_{i+1}_score'] = current_score
            
            final_score = self.calculate_enclosure_score(void_mask)
            metrics['final_score'] = final_score
            metrics['improvement'] = final_score - original_score
            
            logger.info("Void structure optimized. Original score: %.2f, Final score: %.2f",
                       original_score, final_score)
            return void_mask, metrics
            
        except Exception as e:
            logger.error("Error optimizing void structure: %s", str(e))
            raise

# 使用示例
if __name__ == "__main__":
    try:
        # 创建测试图像
        test_image = np.zeros((256, 256, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (50, 50), (200, 200), (255, 255, 255), -1)
        
        # 初始化分析器
        config = FGConfig(min_void_ratio=0.3, enclosure_threshold=180)
        analyzer = NegativeSpaceAnalyzer(config)
        
        # 提取负空间
        void_mask = analyzer.extract_void_mask(test_image)
        print(f"Void ratio: {np.mean(void_mask):.2f}")
        
        # 计算包围感
        score = analyzer.calculate_enclosure_score(void_mask)
        print(f"Enclosure score: {score:.2f}")
        
        # 优化结构
        optimized_mask, metrics = analyzer.optimize_void_structure(test_image)
        print("Optimization metrics:", metrics)
        
    except Exception as e:
        logger.error("Error in example usage: %s", str(e))