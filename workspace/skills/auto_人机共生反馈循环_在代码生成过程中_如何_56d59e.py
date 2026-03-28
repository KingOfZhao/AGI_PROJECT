"""
人机共生反馈循环模块

该模块实现了一套基于不确定性量化(Uncertainty Quantification)的代码生成辅助系统。
核心思想是在代码生成过程中，通过实时监测模型的"认知不确定性"(Epistemic Uncertainty)，
在可能出现错误前主动请求人类干预，而非生成错误代码后再报错。

主要功能：
1. 不确定性量化算法验证
2. 最小化干预请求生成
3. 人机交互式代码生成循环

数据流：
输入：代码生成请求 + 模型置信度指标
输出：安全代码片段或人类干预请求

使用示例：
>>> from auto_human_loop import UncertaintyQuantifier, HumanLoopManager
>>> quantifier = UncertaintyQuantifier(threshold=0.85)
>>> manager = HumanLoopManager(quantifier)
>>> manager.generate_code("def calculate_sum(a, b):")
"""

import logging
import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, List, Dict, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('human_loop.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UncertaintyType(Enum):
    """不确定性类型枚举"""
    ALEATORIC = auto()  # 数据噪声导致的不确定性
    EPISTEMIC = auto()  # 知识缺乏导致的不确定性


@dataclass
class UncertaintyMetrics:
    """不确定性度量数据结构"""
    entropy: float  # 信息熵
    variance: float  # 预测方差
    confidence: float  # 模型置信度
    type: UncertaintyType  # 不确定性类型

    def is_high_uncertainty(self, threshold: float = 0.85) -> bool:
        """判断是否为高不确定性"""
        return self.confidence < threshold


class UncertaintyQuantifier:
    """
    不确定性量化器
    
    实现基于蒙特卡洛Dropout和预测方差的不确定性量化算法。
    用于在代码生成过程中实时评估模型的不确定性水平。
    """
    
    def __init__(self, threshold: float = 0.85, n_samples: int = 10):
        """
        初始化不确定性量化器
        
        Args:
            threshold: 置信度阈值，低于此值视为高不确定性
            n_samples: 蒙特卡洛采样次数
        """
        self.threshold = threshold
        self.n_samples = n_samples
        self._validate_parameters()
        logger.info(f"Initialized UncertaintyQuantifier with threshold={threshold}, n_samples={n_samples}")
    
    def _validate_parameters(self) -> None:
        """验证输入参数有效性"""
        if not 0 <= self.threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        if self.n_samples < 1:
            raise ValueError("Number of samples must be positive integer")
    
    def calculate_uncertainty(
        self, 
        model_probs: List[float],
        dropout_predictions: Optional[List[List[float]]] = None
    ) -> UncertaintyMetrics:
        """
        计算不确定性指标
        
        Args:
            model_probs: 模型输出的token概率分布
            dropout_predictions: 蒙特卡洛Dropout的多次预测结果
            
        Returns:
            UncertaintyMetrics: 包含各种不确定性指标的数据结构
        """
        if not model_probs:
            raise ValueError("Model probabilities cannot be empty")
        
        # 计算信息熵
        entropy = -sum(p * math.log(p + 1e-10) for p in model_probs if p > 0)
        
        # 计算预测方差（如果有Dropout预测结果）
        variance = 0.0
        if dropout_predictions:
            avg_probs = [
                sum(p[i] for p in dropout_predictions) / len(dropout_predictions)
                for i in range(len(model_probs))
            ]
            variance = sum(
                (p - avg_probs[i])**2 
                for i, p in enumerate(model_probs)
            ) / len(model_probs)
        
        # 计算置信度
        confidence = max(model_probs)
        
        # 判断不确定性类型
        uncertainty_type = (
            UncertaintyType.EPISTEMIC 
            if variance > 0.2 else 
            UncertaintyType.ALEATORIC
        )
        
        return UncertaintyMetrics(
            entropy=entropy,
            variance=variance,
            confidence=confidence,
            type=uncertainty_type
        )
    
    def should_request_intervention(self, metrics: UncertaintyMetrics) -> bool:
        """
        判断是否需要请求人类干预
        
        Args:
            metrics: 不确定性指标
            
        Returns:
            bool: 如果需要干预返回True
        """
        if metrics.is_high_uncertainty(self.threshold):
            logger.warning(
                f"High uncertainty detected: confidence={metrics.confidence:.3f}, "
                f"type={metrics.type.name}"
            )
            return True
        return False


class HumanLoopManager:
    """
    人机共生循环管理器
    
    协调代码生成过程与人类干预请求，实现最小化干预策略。
    """
    
    def __init__(self, quantifier: UncertaintyQuantifier):
        """
        初始化人机循环管理器
        
        Args:
            quantifier: 不确定性量化器实例
        """
        self.quantifier = quantifier
        self.intervention_count = 0
        self.generated_code = []
        logger.info("HumanLoopManager initialized")
    
    def _generate_intervention_prompt(
        self, 
        metrics: UncertaintyMetrics,
        context: str
    ) -> str:
        """
        生成人类干预请求提示
        
        Args:
            metrics: 不确定性指标
            context: 当前代码生成上下文
            
        Returns:
            str: 格式化的干预请求
        """
        prompt = (
            f"\n[系统检测到高不确定性区域]\n"
            f"当前置信度: {metrics.confidence:.3f}\n"
            f"不确定性类型: {metrics.type.name}\n"
            f"上下文代码: {context[-100:]}\n\n"
            "请提供最小化干预以继续生成安全代码:\n"
            "1. 确认当前代码方向是否正确\n"
            "2. 提供关键补充信息\n"
            "3. 或输入'skip'继续自动生成\n"
        )
        return prompt
    
    def generate_code(
        self, 
        prompt: str,
        max_length: int = 100
    ) -> Tuple[str, Dict[str, Any]]:
        """
        带不确定性监控的代码生成主循环
        
        Args:
            prompt: 代码生成提示
            max_length: 最大生成长度
            
        Returns:
            Tuple[str, Dict]: 生成的代码和元数据
            
        Example:
            >>> manager.generate_code("def sort_list(items):")
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        logger.info(f"Starting code generation for prompt: {prompt[:50]}...")
        
        # 模拟代码生成过程
        generated = []
        metadata = {
            'interventions': 0,
            'uncertainty_points': [],
            'final_confidence': 1.0
        }
        
        for i in range(max_length):
            # 模拟模型生成token概率分布
            model_probs = self._simulate_model_probs()
            dropout_preds = [self._simulate_model_probs() for _ in range(3)]
            
            metrics = self.quantifier.calculate_uncertainty(
                model_probs, dropout_preds
            )
            
            if self.quantifier.should_request_intervention(metrics):
                metadata['uncertainty_points'].append({
                    'position': i,
                    'metrics': metrics
                })
                
                # 在实际应用中这里会暂停并请求人类干预
                intervention = self._mock_human_intervention(
                    metrics, 
                    prompt + ''.join(generated)
                )
                
                if intervention != 'skip':
                    generated.append(intervention)
                    metadata['interventions'] += 1
                    continue
            
            # 模拟正常token生成
            token = self._select_token(model_probs)
            generated.append(token)
            
            # 模拟生成结束
            if token == '\n' and random.random() > 0.7:
                break
        
        final_code = prompt + ''.join(generated)
        metadata['final_confidence'] = metrics.confidence
        
        logger.info(
            f"Code generation completed with {metadata['interventions']} interventions, "
            f"final confidence: {metrics.confidence:.3f}"
        )
        
        return final_code, metadata
    
    def _simulate_model_probs(self) -> List[float]:
        """模拟模型输出的概率分布"""
        base_probs = [random.random() for _ in range(10)]
        total = sum(base_probs)
        return [p/total for p in base_probs]
    
    def _select_token(self, probs: List[float]) -> str:
        """根据概率选择token"""
        tokens = ['def', ' ', '(', ')', ':', '\n', 'return', ' if', ' else', ' +']
        return random.choices(tokens, weights=probs, k=1)[0]
    
    def _mock_human_intervention(
        self, 
        metrics: UncertaintyMetrics,
        context: str
    ) -> str:
        """
        模拟人类干预（实际应用中会连接真实UI）
        
        Args:
            metrics: 不确定性指标
            context: 当前代码上下文
            
        Returns:
            str: 人类干预内容
        """
        prompt = self._generate_intervention_prompt(metrics, context)
        logger.info(f"Generated intervention prompt:\n{prompt}")
        
        # 模拟人类响应
        responses = [
            " # Added type hints",
            " # Error handling",
            " # Edge case check",
            "skip"
        ]
        return random.choice(responses)


def evaluate_uncertainty_algorithm(
    test_cases: List[str],
    quantifier: UncertaintyQuantifier
) -> Dict[str, float]:
    """
    评估不确定性量化算法性能
    
    Args:
        test_cases: 测试用例列表
        quantifier: 不确定性量化器
        
    Returns:
        Dict[str, float]: 评估指标
        
    Example:
        >>> evaluate_uncertainty_algorithm(["def foo():", "class Bar:"], quantifier)
    """
    if not test_cases:
        raise ValueError("Test cases cannot be empty")
    
    results = {
        'total_cases': len(test_cases),
        'high_uncertainty_count': 0,
        'avg_confidence': 0.0,
        'epistemic_ratio': 0.0
    }
    
    total_confidence = 0.0
    epistemic_count = 0
    
    for case in test_cases:
        probs = quantifier._simulate_model_probs()
        metrics = quantifier.calculate_uncertainty(probs)
        
        if metrics.is_high_uncertainty(quantifier.threshold):
            results['high_uncertainty_count'] += 1
        
        total_confidence += metrics.confidence
        if metrics.type == UncertaintyType.EPISTEMIC:
            epistemic_count += 1
    
    results['avg_confidence'] = total_confidence / len(test_cases)
    results['epistemic_ratio'] = epistemic_count / len(test_cases)
    
    logger.info(f"Algorithm evaluation results: {results}")
    return results


if __name__ == "__main__":
    # 初始化不确定性量化器
    quantifier = UncertaintyQuantifier(threshold=0.8, n_samples=5)
    
    # 创建人机循环管理器
    manager = HumanLoopManager(quantifier)
    
    # 示例代码生成
    code, meta = manager.generate_code("def calculate_sum(a, b):")
    print("\nGenerated Code:")
    print(code)
    print("\nGeneration Metadata:")
    print(meta)
    
    # 评估算法性能
    test_cases = [
        "def sort_list(items):",
        "class NeuralNetwork:",
        "async def fetch_data(url):",
        "def process_image(img_path):"
    ]
    evaluation = evaluate_uncertainty_algorithm(test_cases, quantifier)
    print("\nAlgorithm Evaluation:")
    print(evaluation)