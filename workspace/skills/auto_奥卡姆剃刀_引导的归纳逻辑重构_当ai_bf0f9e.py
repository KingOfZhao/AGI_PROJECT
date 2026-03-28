"""
名称: auto_奥卡姆剃刀_引导的归纳逻辑重构_当ai_bf0f9e
描述: ‘奥卡姆剃刀’引导的归纳逻辑重构：当AI面对海量碎片化信息时，如何自动构建最简约的解释模型
      （最小描述长度原则）？本模块实现了基于符号回归和压缩感知的逻辑重构机制。
领域: software_engineering
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable, Dict, Any
from enum import Enum
import zlib
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelComplexity(Enum):
    """模型复杂度等级枚举"""
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3

@dataclass
class Observation:
    """观测数据结构，包含输入和输出"""
    inputs: np.ndarray
    outputs: np.ndarray
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """数据验证"""
        if self.inputs.shape[0] != self.outputs.shape[0]:
            raise ValueError("输入和输出数据的样本数量不一致")
        if self.inputs.size == 0 or self.outputs.size == 0:
            raise ValueError("输入或输出数据不能为空")

@dataclass
class StructuredNode:
    """结构化节点，表示归纳出的逻辑规则或公式"""
    expression: str
    parameters: Dict[str, float]
    complexity_score: float
    compression_ratio: float
    error_rate: float

class OccamRazorInductor:
    """奥卡姆剃刀引导的归纳逻辑重构系统"""
    
    def __init__(self, 
                 max_complexity: ModelComplexity = ModelComplexity.MODERATE,
                 error_threshold: float = 0.05):
        """
        初始化归纳器
        
        Args:
            max_complexity: 允许的最大模型复杂度
            error_threshold: 可接受的误差阈值
        """
        self.max_complexity = max_complexity
        self.error_threshold = error_threshold
        self._model_candidates: List[StructuredNode] = []
        
        logger.info("初始化奥卡姆剃刀归纳器，最大复杂度: %s, 误差阈值: %.2f", 
                   max_complexity.name, error_threshold)

    def _calculate_description_length(self, model: StructuredNode) -> float:
        """
        计算模型的描述长度（最小描述长度原则的核心）
        
        Args:
            model: 待评估的结构化节点
            
        Returns:
            float: 描述长度（字节数）
        """
        # 使用zlib压缩来估算描述长度
        model_str = f"{model.expression}:{str(model.parameters)}"
        compressed = zlib.compress(model_str.encode('utf-8'))
        return len(compressed)

    def _validate_observation(self, observation: Observation) -> bool:
        """
        验证观测数据的完整性
        
        Args:
            observation: 待验证的观测数据
            
        Returns:
            bool: 验证是否通过
        """
        try:
            if not isinstance(observation, Observation):
                raise TypeError("输入必须是Observation类型")
                
            if np.any(np.isnan(observation.inputs)) or np.any(np.isnan(observation.outputs)):
                raise ValueError("输入数据包含NaN值")
                
            if np.any(np.isinf(observation.inputs)) or np.any(np.isinf(observation.outputs)):
                raise ValueError("输入数据包含无限值")
                
            return True
            
        except Exception as e:
            logger.error("数据验证失败: %s", str(e))
            return False

    def generate_model_candidates(self, observation: Observation) -> List[StructuredNode]:
        """
        生成候选模型集合（核心函数1）
        
        Args:
            observation: 观测数据
            
        Returns:
            List[StructuredNode]: 候选模型列表
            
        Raises:
            ValueError: 当输入数据无效时
        """
        if not self._validate_observation(observation):
            raise ValueError("无效的观测数据")
            
        logger.info("开始生成模型候选，输入维度: %s, 样本数量: %d", 
                   observation.inputs.shape, observation.inputs.shape[0])
        
        candidates = []
        
        # 尝试线性模型 (y = ax + b)
        try:
            x = observation.inputs[:, 0]  # 假设单变量
            y = observation.outputs
            
            # 使用最小二乘法拟合
            A = np.vstack([x, np.ones(len(x))]).T
            slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
            
            # 计算误差
            y_pred = slope * x + intercept
            error_rate = np.mean(np.abs(y - y_pred) / (np.abs(y) + 1e-6))
            
            model = StructuredNode(
                expression="y = ax + b",
                parameters={"a": slope, "b": intercept},
                complexity_score=1.0,
                compression_ratio=0.0,  # 稍后计算
                error_rate=error_rate
            )
            model.compression_ratio = self._calculate_compression_ratio(observation, model)
            candidates.append(model)
            
        except Exception as e:
            logger.warning("线性模型拟合失败: %s", str(e))
        
        # 尝试幂律模型 (y = ax^b)
        try:
            log_x = np.log(x[x > 0])
            log_y = np.log(y[y > 0])
            
            # 确保对数变换后数据对齐
            min_len = min(len(log_x), len(log_y))
            log_x = log_x[:min_len]
            log_y = log_y[:min_len]
            
            A = np.vstack([log_x, np.ones(len(log_x))]).T
            power, log_coeff = np.linalg.lstsq(A, log_y, rcond=None)[0]
            coeff = np.exp(log_coeff)
            
            y_pred = coeff * np.power(x, power)
            error_rate = np.mean(np.abs(y - y_pred) / (np.abs(y) + 1e-6))
            
            model = StructuredNode(
                expression="y = a * x^b",
                parameters={"a": coeff, "b": power},
                complexity_score=2.0,
                compression_ratio=0.0,
                error_rate=error_rate
            )
            model.compression_ratio = self._calculate_compression_ratio(observation, model)
            candidates.append(model)
            
        except Exception as e:
            logger.warning("幂律模型拟合失败: %s", str(e))
        
        # 尝试指数模型 (y = a * e^(bx))
        try:
            log_y = np.log(y[y > 0])
            x_filtered = x[:len(log_y)]
            
            A = np.vstack([x_filtered, np.ones(len(x_filtered))]).T
            rate, log_coeff = np.linalg.lstsq(A, log_y, rcond=None)[0]
            coeff = np.exp(log_coeff)
            
            y_pred = coeff * np.exp(rate * x)
            error_rate = np.mean(np.abs(y - y_pred) / (np.abs(y) + 1e-6))
            
            model = StructuredNode(
                expression="y = a * e^(bx)",
                parameters={"a": coeff, "b": rate},
                complexity_score=2.0,
                compression_ratio=0.0,
                error_rate=error_rate
            )
            model.compression_ratio = self._calculate_compression_ratio(observation, model)
            candidates.append(model)
            
        except Exception as e:
            logger.warning("指数模型拟合失败: %s", str(e))
        
        self._model_candidates = candidates
        logger.info("生成了 %d 个候选模型", len(candidates))
        return candidates

    def _calculate_compression_ratio(self, observation: Observation, model: StructuredNode) -> float:
        """
        计算模型的压缩比率（辅助函数）
        
        Args:
            observation: 原始观测数据
            model: 候选模型
            
        Returns:
            float: 压缩比率 (原始数据大小 / 模型描述长度)
        """
        # 原始数据大小
        original_size = observation.inputs.nbytes + observation.outputs.nbytes
        
        # 模型描述长度
        model_size = self._calculate_description_length(model)
        
        return original_size / model_size if model_size > 0 else 0.0

    def select_optimal_model(self) -> Optional[StructuredNode]:
        """
        选择最优模型（核心函数2）
        
        使用奥卡姆剃刀原则和最小描述长度原则选择最佳模型
        
        Returns:
            Optional[StructuredNode]: 最优模型，如果没有合适模型则返回None
        """
        if not self._model_candidates:
            logger.warning("没有可用的候选模型")
            return None
            
        logger.info("开始选择最优模型，候选数量: %d", len(self._model_candidates))
        
        # 过滤掉误差超过阈值的模型
        valid_models = [
            model for model in self._model_candidates 
            if model.error_rate <= self.error_threshold
        ]
        
        if not valid_models:
            logger.warning("没有模型满足误差阈值要求")
            return None
        
        # 计算综合得分 (平衡复杂度和误差)
        def calculate_score(model: StructuredNode) -> float:
            """计算模型综合得分"""
            # 最小描述长度原则：更短的描述更好
            description_score = 1.0 / model.complexity_score
            
            # 压缩率得分：更高的压缩率更好
            compression_score = model.compression_ratio
            
            # 误差得分：更低的误差更好
            error_score = 1.0 / (model.error_rate + 1e-6)
            
            # 加权综合得分
            return 0.4 * description_score + 0.3 * compression_score + 0.3 * error_score
        
        # 选择得分最高的模型
        best_model = max(valid_models, key=calculate_score)
        
        logger.info(
            "选择最优模型: %s, 参数: %s, 误差: %.4f, 压缩率: %.2f",
            best_model.expression,
            best_model.parameters,
            best_model.error_rate,
            best_model.compression_ratio
        )
        
        return best_model

    def reconstruct_logic(self, observation: Observation) -> Optional[StructuredNode]:
        """
        执行完整的逻辑重构流程
        
        Args:
            observation: 输入观测数据
            
        Returns:
            Optional[StructuredNode]: 重构出的最优结构化节点
        """
        try:
            # 生成候选模型
            self.generate_model_candidates(observation)
            
            # 选择最优模型
            optimal_model = self.select_optimal_model()
            
            return optimal_model
            
        except Exception as e:
            logger.error("逻辑重构过程中发生错误: %s", str(e))
            return None

def generate_test_data() -> Observation:
    """生成测试数据（E=mc^2的模拟）"""
    np.random.seed(42)
    mass = np.linspace(0.1, 10, 100)
    c = 299792458  # 光速
    energy = mass * (c ** 2)
    
    # 添加一些噪声
    noise = np.random.normal(0, 0.05 * np.mean(energy), size=energy.shape)
    energy_noisy = energy + noise
    
    return Observation(
        inputs=mass.reshape(-1, 1),
        outputs=energy_noisy,
        metadata={"description": "E=mc^2 模拟数据"}
    )

if __name__ == "__main__":
    # 使用示例
    print("=" * 50)
    print("奥卡姆剃刀引导的归纳逻辑重构系统")
    print("=" * 50)
    
    # 创建归纳器实例
    inductor = OccamRazorInductor(
        max_complexity=ModelComplexity.MODERATE,
        error_threshold=0.1
    )
    
    # 生成测试数据
    test_data = generate_test_data()
    print(f"\n生成测试数据: {test_data.inputs.shape[0]} 个样本")
    
    # 执行逻辑重构
    result = inductor.reconstruct_logic(test_data)
    
    if result:
        print("\n成功重构逻辑:")
        print(f"表达式: {result.expression}")
        print(f"参数: {result.parameters}")
        print(f"误差率: {result.error_rate:.4f}")
        print(f"压缩率: {result.compression_ratio:.2f}x")
    else:
        print("\n无法重构逻辑，没有找到合适的模型")