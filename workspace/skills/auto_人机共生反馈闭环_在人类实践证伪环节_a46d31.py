"""
名称: auto_人机共生反馈闭环_在人类实践证伪环节_a46d31
描述: 实现人机共生反馈闭环中的直觉量化接口。
      本模块提供了一个将模糊的人类直觉（如“感觉不对”）转化为
      具体的AI模型参数梯度调整建议的工具。
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ModelWeights:
    """
    模拟的AI模型参数权重。
    
    Attributes:
        semantic_weight (float): 语义相关性的权重
        syntactic_weight (float): 语法结构的权重
        novelty_weight (float): 新颖性的权重
        safety_weight (float): 安全性的权重
    """
    semantic_weight: float = 0.5
    syntactic_weight: float = 0.5
    novelty_weight: float = 0.5
    safety_weight: float = 0.5

    def to_vector(self) -> np.ndarray:
        """将权重转换为numpy向量。"""
        return np.array([
            self.semantic_weight,
            self.syntactic_weight,
            self.novelty_weight,
            self.safety_weight
        ])

    def update_from_vector(self, vector: np.ndarray) -> None:
        """从numpy向量更新权重。"""
        self.semantic_weight = float(vector[0])
        self.syntactic_weight = float(vector[1])
        self.novelty_weight = float(vector[2])
        self.safety_weight = float(vector[3])

@dataclass
class IntuitionSignal:
    """
    人类的直觉信号数据结构。
    
    Attributes:
        direction (Tuple[float, float, float, float]): 
            调整方向向量，对应
        intensity (float): 
            调整力度，范围[0.0, 1.0]，0表示微调，1表示大幅度调整
        focus_area (str): 
            关注区域，如 'semantic', 'syntactic', 'novelty', 'safety'
        comment (str): 
            可选的口头反馈
    """
    direction: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    intensity: float = 0.5
    focus_area: str = "general"
    comment: str = ""

class IntuitionMappingInterface:
    """
    直觉映射接口。
    
    将人类的模糊直觉反馈转化为模型参数的梯度调整。
    
    Attributes:
        current_weights (ModelWeights): 当前的模型权重
        feedback_history (List[Tuple[IntuitionSignal, ModelWeights]]): 反馈历史记录
        learning_rate (float): 学习率，控制每次调整的幅度
    """
    
    def __init__(self, initial_weights: Optional[ModelWeights] = None, learning_rate: float = 0.1):
        """
        初始化直觉映射接口。
        
        Args:
            initial_weights: 初始模型权重，如果为None则使用默认值
            learning_rate: 学习率，控制调整幅度，默认0.1
        """
        self.current_weights = initial_weights if initial_weights else ModelWeights()
        self.feedback_history: List[Tuple[IntuitionSignal, np.ndarray]] = []
        self.learning_rate = learning_rate
        logger.info("IntuitionMappingInterface initialized with learning rate: %s", learning_rate)
        
    def _validate_signal(self, signal: IntuitionSignal) -> bool:
        """
        验证直觉信号的有效性。
        
        Args:
            signal: 待验证的直觉信号
            
        Returns:
            bool: 如果信号有效返回True，否则返回False
            
        Raises:
            ValueError: 如果信号无效
        """
        if not isinstance(signal, IntuitionSignal):
            error_msg = f"Expected IntuitionSignal, got {type(signal)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not (0.0 <= signal.intensity <= 1.0):
            error_msg = f"Intensity must be between 0.0 and 1.0, got {signal.intensity}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        valid_areas = ["general", "semantic", "syntactic", "novelty", "safety"]
        if signal.focus_area not in valid_areas:
            error_msg = f"Focus area must be one of {valid_areas}, got {signal.focus_area}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        return True
    
    def _calculate_gradient(self, signal: IntuitionSignal) -> np.ndarray:
        """
        根据直觉信号计算参数梯度。
        
        Args:
            signal: 人类的直觉信号
            
        Returns:
            np.ndarray: 计算出的梯度向量
        """
        direction = np.array(signal.direction)
        
        # 根据关注区域调整梯度权重
        area_mask = np.ones(4)
        if signal.focus_area == "semantic":
            area_mask = np.array([2.0, 0.5, 0.5, 0.5])
        elif signal.focus_area == "syntactic":
            area_mask = np.array([0.5, 2.0, 0.5, 0.5])
        elif signal.focus_area == "novelty":
            area_mask = np.array([0.5, 0.5, 2.0, 0.5])
        elif signal.focus_area == "safety":
            area_mask = np.array([0.5, 0.5, 0.5, 2.0])
            
        # 计算梯度：方向 * 力度 * 学习率 * 区域权重
        gradient = direction * signal.intensity * self.learning_rate * area_mask
        logger.debug("Calculated gradient: %s", gradient)
        return gradient
    
    def process_intuition(self, signal: IntuitionSignal) -> Tuple[ModelWeights, Dict[str, float]]:
        """
        处理人类的直觉反馈并更新模型权重。
        
        Args:
            signal: 人类的直觉信号
            
        Returns:
            Tuple[ModelWeights, Dict[str, float]]: 
                更新后的模型权重和调整详情字典
                
        Raises:
            ValueError: 如果信号验证失败
        """
        try:
            self._validate_signal(signal)
            logger.info("Processing intuition signal with focus on: %s", signal.focus_area)
            
            # 计算梯度
            gradient = self._calculate_gradient(signal)
            
            # 获取当前权重向量
            current_weights_vec = self.current_weights.to_vector()
            
            # 计算新权重 (当前权重 + 梯度)
            new_weights_vec = current_weights_vec + gradient
            
            # 确保权重在合理范围内 [0.1, 1.0]
            new_weights_vec = np.clip(new_weights_vec, 0.1, 1.0)
            
            # 更新权重
            self.current_weights.update_from_vector(new_weights_vec)
            
            # 记录反馈历史
            self.feedback_history.append((signal, gradient))
            
            # 准备调整详情
            adjustment_details = {
                "semantic_adjustment": float(gradient[0]),
                "syntactic_adjustment": float(gradient[1]),
                "novelty_adjustment": float(gradient[2]),
                "safety_adjustment": float(gradient[3]),
                "intensity": signal.intensity,
                "focus_area": signal.focus_area
            }
            
            logger.info("Weights updated. New weights: %s", self.current_weights)
            return self.current_weights, adjustment_details
            
        except Exception as e:
            logger.error("Error processing intuition signal: %s", str(e))
            raise

def simulate_human_intuition(interface: IntuitionMappingInterface, iterations: int = 5) -> None:
    """
    模拟人类直觉反馈的过程。
    
    Args:
        interface: 直觉映射接口实例
        iterations: 模拟迭代次数，默认5
    """
    print("\n=== 模拟人类直觉反馈 ===")
    print(f"初始权重: {interface.current_weights}")
    
    for i in range(iterations):
        print(f"\n--- 迭代 {i+1} ---")
        
        # 模拟人类直觉信号
        signal = IntuitionSignal(
            direction=(np.random.uniform(-0.2, 0.2), 
                      np.random.uniform(-0.2, 0.2),
                      np.random.uniform(-0.2, 0.2),
                      np.random.uniform(-0.2, 0.2)),
            intensity=np.random.uniform(0.3, 0.8),
            focus_area=np.random.choice(["general", "semantic", "syntactic", "novelty", "safety"]),
            comment=f"模拟反馈 {i+1}"
        )
        
        print(f"直觉信号: 方向={signal.direction}, 力度={signal.intensity:.2f}, 关注={signal.focus_area}")
        
        # 处理直觉反馈
        new_weights, details = interface.process_intuition(signal)
        
        print(f"权重调整: 语义={details['semantic_adjustment']:.4f}, 语法={details['syntactic_adjustment']:.4f}")
        print(f"更新后权重: 语义={new_weights.semantic_weight:.4f}, 语法={new_weights.syntactic_weight:.4f}")

if __name__ == "__main__":
    # 使用示例
    print("人机共生反馈闭环 - 直觉量化接口演示")
    
    # 创建接口实例
    interface = IntuitionMappingInterface(learning_rate=0.15)
    
    # 模拟人类直觉反馈
    simulate_human_intuition(interface, iterations=3)
    
    # 显示最终权重
    print("\n=== 最终模型权重 ===")
    print(interface.current_weights)
    
    # 显示反馈历史
    print("\n=== 反馈历史 ===")
    for i, (signal, gradient) in enumerate(interface.feedback_history):
        print(f"反馈 {i+1}: 关注={signal.focus_area}, 力度={signal.intensity:.2f}")
        print(f"  梯度调整: {gradient}")