"""
模块名称: auto_模糊逻辑的概率性测试生成
描述: 该模块实现了将非功能性的模糊意图（如'系统要感觉很流畅'）转化为可量化的自动化测试脚本。
      通过建立从自然语言形容词到性能指标（如FPS、延迟、丢包率）的概率映射模型，
      并结合蒙特卡洛模拟生成对应的混沌工程实验用例。

Author: AGI System
Version: 1.0.0
"""

import logging
import random
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """性能指标类型的枚举"""
    LATENCY_MS = "latency_ms"
    FPS = "fps"
    PACKET_LOSS_PERCENT = "packet_loss_percent"
    CPU_LOAD_PERCENT = "cpu_load_percent"
    MEMORY_LEAK_MB = "memory_leak_mb"

@dataclass
class FuzzyCondition:
    """模糊条件的数据结构"""
    intent_keyword: str  # 如 "流畅", "快", "稳定"
    target_metric: MetricType
    weight: float  # 该指标在整体体验中的权重
    threshold_optimal: float  # 理想阈值
    threshold_acceptable: float  # 可接受阈值
    distribution_mean: float  # 概率分布均值
    distribution_std: float  # 概率分布标准差

@dataclass
class ChaosExperiment:
    """混沌工程实验用例的数据结构"""
    experiment_id: str
    description: str
    injection_type: str  # e.g., "latency", "packet_loss", "cpu_stress"
    intensity: float  # 0.0 to 1.0
    duration_seconds: int
    target_service: str
    expected_resilience: Dict[str, float] = field(default_factory=dict)

class FuzzyTestGenerator:
    """
    核心类：模糊逻辑测试生成器。
    
    将自然语言描述的非功能性需求转换为具体的测试参数。
    """
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化生成器。
        
        Args:
            knowledge_base_path (Optional[str]): 知识库配置文件路径。
        """
        self._initialize_knowledge_base()
        logger.info("FuzzyTestGenerator initialized with %d mapping rules.", len(self._rules))

    def _initialize_knowledge_base(self) -> None:
        """
        辅助函数：初始化内置的模糊逻辑知识库。
        
        建立形容词到指标的映射规则。
        """
        # 模拟从数据库或配置文件加载的规则
        self._rules: Dict[str, List[FuzzyCondition]] = {
            "流畅": [
                FuzzyCondition("流畅", MetricType.FPS, 0.7, 60.0, 30.0, 60.0, 5.0),
                FuzzyCondition("流畅", MetricType.LATENCY_MS, 0.3, 20.0, 100.0, 50.0, 20.0)
            ],
            "稳定": [
                FuzzyCondition("稳定", MetricType.PACKET_LOSS_PERCENT, 0.6, 0.0, 1.0, 0.5, 0.2),
                FuzzyCondition("稳定", MetricType.CPU_LOAD_PERCENT, 0.4, 40.0, 90.0, 50.0, 15.0)
            ]
        }

    def _validate_intent(self, intent: str) -> bool:
        """
        辅助函数：验证意图输入的有效性。
        
        Args:
            intent (str): 用户输入的意图字符串。
            
        Returns:
            bool: 是否包含有效的关键词。
        """
        if not isinstance(intent, str) or len(intent) < 2:
            logger.warning("Invalid intent input: %s", intent)
            return False
        return True

    def parse_fuzzy_intent(self, intent: str) -> List[FuzzyCondition]:
        """
        核心函数1：解析模糊意图。
        
        分析自然语言，提取相关的性能指标约束。
        
        Args:
            intent (str): 模糊意图，例如 "系统需要非常流畅且稳定"。
            
        Returns:
            List[FuzzyCondition]: 匹配到的条件列表。
        
        Raises:
            ValueError: 如果输入为空或格式错误。
        """
        if not self._validate_intent(intent):
            raise ValueError("Intent must be a non-empty string.")

        matched_conditions = []
        # 简单的关键词匹配逻辑，生产环境可替换为NLP模型
        for keyword, conditions in self._rules.items():
            if keyword in intent:
                logger.info(f"Matched keyword: '{keyword}'")
                matched_conditions.extend(conditions)
        
        if not matched_conditions:
            logger.warning(f"No specific rules found for intent: '{intent}'")
            
        return matched_conditions

    def generate_probabilistic_test_cases(
        self, 
        conditions: List[FuzzyCondition], 
        num_cases: int = 5,
        target_service: str = "default-service"
    ) -> List[ChaosExperiment]:
        """
        核心函数2：生成概率性测试用例。
        
        基于匹配到的条件和概率分布，生成具体的混沌实验配置。
        
        Args:
            conditions (List[FuzzyCondition]): 解析出的条件列表。
            num_cases (int): 需要生成的实验数量。
            target_service (str): 目标服务名称。
            
        Returns:
            List[ChaosExperiment]: 生成的混沌实验列表。
        """
        if not conditions:
            logger.error("No conditions provided for test generation.")
            return []

        experiments = []
        timestamp = int(time.time())

        for i in range(num_cases):
            # 随机选择一个主要关注的指标进行压力测试
            primary_condition = random.choice(conditions)
            
            # 使用高斯分布生成接近临界值的测试强度
            # 模拟 "在边界附近试探" 的行为
            random_val = random.gauss(primary_condition.distribution_mean, primary_condition.distribution_std)
            
            # 确定注入类型和强度
            injection_type = ""
            intensity = 0.0
            
            if primary_condition.target_metric == MetricType.LATENCY_MS:
                injection_type = "network_latency"
                # 将生成的延迟值映射为强度 (假设最大1000ms)
                intensity = min(max(random_val / 1000.0, 0.1), 0.9)
                desc = f"Injecting {random_val:.2f}ms latency to test smoothness"
            elif primary_condition.target_metric == MetricType.PACKET_LOSS_PERCENT:
                injection_type = "network_packet_loss"
                intensity = min(max(random_val / 10.0, 0.05), 0.5) # 0.5% to 5%
                desc = f"Injecting {intensity*100:.2f}% packet loss to test stability"
            else:
                injection_type = "resource_stress"
                intensity = random.uniform(0.5, 0.9)
                desc = f"Injecting CPU/Memory stress with intensity {intensity:.2f}"

            experiment = ChaosExperiment(
                experiment_id=f"chaos_{timestamp}_{i}",
                description=desc,
                injection_type=injection_type,
                intensity=round(intensity, 4),
                duration_seconds=random.randint(30, 180),
                target_service=target_service,
                expected_resilience={
                    "min_fps": primary_condition.threshold_acceptable if primary_condition.target_metric == MetricType.FPS else 0,
                    "max_latency": primary_condition.threshold_acceptable if primary_condition.target_metric == MetricType.LATENCY_MS else 999
                }
            )
            experiments.append(experiment)
            logger.debug(f"Generated experiment: {experiment.experiment_id}")

        return experiments

def main():
    """
    使用示例函数。
    """
    # 1. 初始化生成器
    generator = FuzzyTestGenerator()
    
    # 2. 定义模糊意图
    fuzzy_intent = "用户期望视频播放非常流畅，并且在弱网环境下保持稳定。"
    
    try:
        # 3. 解析意图
        logger.info(f"Processing intent: {fuzzy_intent}")
        conditions = generator.parse_fuzzy_intent(fuzzy_intent)
        
        print(f"\n--- Parsed Conditions for '{fuzzy_intent}' ---")
        for cond in conditions:
            print(f"Metric: {cond.target_metric.value}, Weight: {cond.weight}, Threshold: {cond.threshold_optimal}")

        # 4. 生成测试用例
        test_cases = generator.generate_probabilistic_test_cases(
            conditions, 
            num_cases=3, 
            target_service="video-streaming-service"
        )
        
        print("\n--- Generated Chaos Experiments ---")
        for case in test_cases:
            print(json.dumps(asdict(case), indent=2))
            
    except ValueError as e:
        logger.error(f"Error during test generation: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    main()