"""
模块: auto_构建意图一致性的数学验证器_在代码生成过_b904d9
描述: 构建意图一致性的数学验证器。在代码生成过程中，如何将模糊的意图（如‘高性能’、‘用户友好’）
      量化为可测量的目标函数约束？系统需在每次代码变更时，自动运行微观基准测试或静态分析，
      验证新生成的结构化代码是否在数学定义上更接近目标向量，形成‘自下而上’的归纳构建闭环。
作者: AGI System
版本: 1.0.0
"""

import ast
import inspect
import logging
import statistics
import time
import timeit
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentMathVerifier")


@dataclass
class MetricVector:
    """
    表示代码在特定维度上的度量值。
    
    Attributes:
        name: 度量名称 (e.g., 'performance_latency_ms')
        value: 度量值
        weight: 该度量在总目标中的权重
        is_score: 如果为True，值越高越好；如果为False，值越低越好
    """
    name: str
    value: float
    weight: float = 1.0
    is_score: bool = False  # False means cost (lower is better), True means score

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError("Weight must be non-negative.")
        if self.value < 0 and not self.is_score:
            logger.warning(f"Cost metric '{self.name}' has negative value, which may be unusual.")


@dataclass
class IntentTarget:
    """
    定义模糊意图的数学映射目标。
    
    Attributes:
        name: 意图名称 (e.g., 'high_performance')
        optimization_direction: 'maximize' or 'minimize' (currently derived from metrics)
        metrics: 包含的度量向量列表
    """
    name: str
    metrics: List[MetricVector] = field(default_factory=list)

    def add_metric(self, metric: MetricVector):
        """向目标中添加一个度量维度。"""
        self.metrics.append(metric)
        logger.debug(f"Added metric '{metric.name}' to target '{self.name}'.")


class IntentMathValidator:
    """
    核心验证器类：负责将模糊意图转化为数学约束，并验证代码变更的一致性。
    
    通过计算欧几里得距离或加权评分，判断新代码是否比旧代码更接近目标向量。
    """

    def __init__(self, target: IntentTarget):
        self.target = target
        self._baseline_code: Optional[str] = None
        self._baseline_vector: Optional[Dict[str, float]] = None
        logger.info(f"Validator initialized for target: '{target.name}'")

    def _normalize_metrics(self, raw_metrics: Dict[str, float]) -> Dict[str, float]:
        """
        辅助函数：归一化度量值。
        这里使用简单的Min-Max假设或直接返回值（视具体上下文而定）。
        在实际AGI场景中，这里需要更复杂的统计归一化。
        """
        return raw_metrics

    def quantify_intent(self) -> Dict[str, float]:
        """
        将当前的IntentTarget转化为具体的数值向量字典。
        这一步完成了从 'High Performance' -> {latency: 0.05, memory: 10MB} 的映射。
        """
        vector = {}
        for m in self.target.metrics:
            vector[m.name] = m.value
        return self._normalize_metrics(vector)

    def extract_static_features(self, code_string: str) -> Dict[str, float]:
        """
        辅助函数：执行静态分析，提取代码结构特征。
        
        Args:
            code_string: 待分析的Python代码字符串
            
        Returns:
            包含静态特征（如行数、圈复杂度）的字典
        """
        try:
            tree = ast.parse(code_string)
            
            # 简单的圈复杂度估算 (节点数)
            complexity = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.If, ast.For, ast.While, ast.IfExp)))
            
            # 代码行数
            lines = len(code_string.splitlines())
            
            return {
                "static_complexity": float(complexity),
                "loc": float(lines)
            }
        except SyntaxError as e:
            logger.error(f"Static analysis failed: Syntax error in code - {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error during static analysis: {e}")
            return {}

    def run_micro_benchmark(self, func: Callable, setup: str = "pass", iterations: int = 1000) -> float:
        """
        核心函数1: 执行微观基准测试以量化性能意图。
        
        Args:
            func: 需要测试的可调用对象
            setup: timeit所需的setup代码
            iterations: 运行次数
            
        Returns:
            平均执行时间（秒）
        """
        if not callable(func):
            raise ValueError("Input must be a callable function.")
        
        try:
            # 使用timeit进行精确测量
            timer = timeit.Timer(stmt=func, setup=setup)
            times = timer.repeat(repeat=3, number=iterations)
            avg_time = statistics.mean(times) / iterations
            logger.info(f"Benchmark run: Avg time {avg_time:.6f}s over {iterations} iterations.")
            return avg_time
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return float('inf') # 返回无穷大表示最差情况

    def calculate_distance_to_target(self, current_metrics: Dict[str, float]) -> float:
        """
        核心函数2: 计算当前代码度量向量与目标意图向量之间的“距离”（差异度）。
        距离越小，表示越符合意图。
        
        使用加权欧几里得距离。
        对于Cost类型指标（如延迟，越低越好），目标值通常设为理想下限。
        对于Score类型指标（如吞吐量，越高越好），目标值通常设为理想上限。
        
        Args:
            current_metrics: 当前代码运行得到的度量值
            
        Returns:
            float: 距离分值 (越低越好)
        """
        target_vector = self.quantify_intent()
        distance_sq = 0.0
        
        for metric in self.target.metrics:
            target_val = target_vector.get(metric.name)
            current_val = current_metrics.get(metric.name)
            
            if target_val is None or current_val is None:
                logger.warning(f"Missing metric data for '{metric.name}'. Skipping.")
                continue
            
            # 计算差异分量
            # 如果是Cost (is_score=False): 差异为 current - target (我们要最小化这个差值)
            # 如果是Score (is_score=True): 差异为 target - current (我们要最小化差值，即最大化current)
            
            diff = 0.0
            if not metric.is_score:
                # Target is the ideal lower bound
                # If current < target, that's great (0 or negative diff), but usually target is 'ideal'
                diff = (current_val - target_val) * metric.weight
            else:
                # Target is the ideal upper bound
                # We want (target - current) to be small
                diff = (target_val - current_val) * metric.weight
            
            distance_sq += (diff ** 2)
            
        return distance_sq ** 0.5

    def validate_change(self, old_code_metrics: Dict[str, float], new_code_metrics: Dict[str, float]) -> bool:
        """
        验证代码变更是否在数学定义上更接近目标。
        
        Args:
            old_code_metrics: 旧代码的度量数据
            new_code_metrics: 新代码的度量数据
            
        Returns:
            bool: 如果新代码更接近目标则返回True
        """
        old_dist = self.calculate_distance_to_target(old_code_metrics)
        new_dist = self.calculate_distance_to_target(new_code_metrics)
        
        logger.info(f"Validation - Old Distance: {old_dist:.4f}, New Distance: {new_dist:.4f}")
        
        if new_dist <= old_dist:
            logger.info("Change accepted: New code is mathematically closer to intent.")
            return True
        else:
            logger.warning("Change rejected: New code deviates from intent.")
            return False

# --- 使用示例与数据格式说明 ---

def example_usage():
    """
    展示如何使用 IntentMathValidator 进行意图一致性验证。
    
    场景：
    意图 = "High Performance" (高性能)
    具体目标 = 最小化执行时间 (目标 < 0.001s)
    """
    print("--- Starting Intent Validation Example ---")
    
    # 1. 定义意图目标 (量化模糊意图)
    # 我们希望代码运行时间在 0.001秒以内
    target = IntentTarget(name="high_performance")
    target.add_metric(MetricVector(
        name="execution_time_s", 
        value=0.001, 
        weight=1.0, 
        is_score=False  # 这是一个Cost指标（越低越好）
    ))
    
    validator = IntentMathValidator(target)
    
    # 2. 定义旧代码和新代码
    def old_algorithm():
        return sum([i for i in range(100)])
        
    def new_algorithm():
        # 使用公式优化，理论上更快
        return 100 * 99 / 2
    
    # 3. 运行微观基准测试
    print("Benchmarking old code...")
    old_metrics = {
        "execution_time_s": validator.run_micro_benchmark(old_algorithm, iterations=10000)
    }
    
    print("Benchmarking new code...")
    new_metrics = {
        "execution_time_s": validator.run_micro_benchmark(new_algorithm, iterations=10000)
    }
    
    # 4. 验证变更
    is_improvement = validator.validate_change(old_metrics, new_metrics)
    
    print(f"Is the new code an improvement? {'Yes' if is_improvement else 'No'}")
    print("--- Example Finished ---")

if __name__ == "__main__":
    example_usage()