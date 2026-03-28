"""
情境感知的动态配方引擎 - 环境敏感性模块

该模块实现了一个能够根据环境参数（网络延迟、系统温度、负载等）动态调整任务执行策略的引擎。
它模拟了“量子态坍缩”的概念：当环境漂移超过阈值时，任务状态会从高精度模式瞬间切换至鲁棒模式，
确保系统在各种极端条件下的可用性和稳定性。

核心功能：
1. 环境参数验证与边界检查。
2. 基于多维环境指标的运行状态评估。
3. 动态生成适应环境的任务配方（模型选择、逻辑复杂度、资源分配）。

使用示例:
    >>> env_params = {"network_latency_ms": 50.0, "cpu_temp_c": 45.0, "load_avg": 1.2}
    >>> recipe = generate_dynamic_recipe("分析用户行为数据", env_params)
    >>> print(f"Selected Model: {recipe.model_name}, Complexity: {recipe.complexity}")
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Literal, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationalMode(Enum):
    """定义系统的运行模式，模拟量子态的不同表现形式。"""
    HIGH_PRECISION = "HIGH_PRECISION"  # 高精度模式：资源充足，追求最佳效果
    ROBUST = "ROBUST"                  # 鲁棒模式：资源受限，追求稳定性和速度


@dataclass
class TaskRecipe:
    """动态生成的任务配方，包含执行任务所需的具体参数。"""
    model_name: str
    complexity_level: str
    max_tokens: int
    temperature: float
    retry_strategy: Dict[str, Any]
    estimated_duration_sec: float
    fallback_enabled: bool = True

    def __repr__(self) -> str:
        return (f"<TaskRecipe(model={self.model_name}, complexity={self.complexity_level}, "
                f"tokens={self.max_tokens})>")


@dataclass
class EnvironmentContext:
    """环境上下文数据结构，用于封装环境参数。"""
    network_latency_ms: float
    cpu_temperature_c: float
    available_memory_gb: float
    system_load_avg: float


def validate_environment_params(params: Dict[str, Any]) -> EnvironmentContext:
    """
    辅助函数：验证输入的环境参数，并进行边界检查。

    Args:
        params: 包含环境指标的字典。

    Returns:
        EnvironmentContext: 验证通过后的环境上下文对象。

    Raises:
        ValueError: 如果参数缺失、类型错误或超出物理合理范围。
    """
    required_keys = {
        "network_latency_ms": (float, int),
        "cpu_temp_c": (float, int),  # 兼容 key 别名
        "available_memory_gb": (float, int),
        "system_load_avg": (float, int)
    }

    # 处理可能的键名变体
    if "cpu_temp_c" not in params and "cpu_temperature_c" in params:
        params["cpu_temp_c"] = params["cpu_temperature_c"]

    for key, expected_type in required_keys.items():
        if key not in params:
            raise ValueError(f"Missing required environment parameter: {key}")
        if not isinstance(params[key], expected_type):
            raise ValueError(f"Parameter {key} must be of type {expected_type}")

    # 边界检查
    latency = float(params["network_latency_ms"])
    temp = float(params["cpu_temp_c"])
    memory = float(params["available_memory_gb"])
    load = float(params["system_load_avg"])

    if latency < 0:
        raise ValueError("Network latency cannot be negative.")
    if temp < -20 or temp > 120:
        logger.warning(f"Unusual CPU temperature detected: {temp}C. Proceeding with caution.")
    if memory < 0:
        raise ValueError("Available memory cannot be negative.")
    if load < 0:
        raise ValueError("System load cannot be negative.")

    logger.info("Environment parameters validated successfully.")
    return EnvironmentContext(latency, temp, memory, load)


def assess_environmental_state(context: EnvironmentContext) -> OperationalMode:
    """
    核心函数 1：评估当前环境状态，决定系统运行模式。

    该函数模拟“量子观测”，根据环境漂移决定系统坍缩至哪种状态。
    阈值设定：
    - 网络延迟 > 200ms 或 CPU温度 > 85度 或 内存 < 2GB -> 切换至鲁棒模式
    - 否则 -> 保持高精度模式

    Args:
        context: 验证过的环境上下文。

    Returns:
        OperationalMode: 计算得出的运行模式。
    """
    logger.debug(f"Assessing environment state: Latency={context.network_latency_ms}ms, "
                 f"Temp={context.cpu_temperature_c}C, Mem={context.available_memory_gb}GB")

    # 环境敏感性阈值逻辑
    is_network_poor = context.network_latency_ms > 200.0
    is_thermal_critical = context.cpu_temperature_c > 85.0
    is_memory_low = context.available_memory_gb < 2.0

    if is_network_poor or is_thermal_critical or is_memory_low:
        logger.warning("Environmental drift detected. Collapsing state to ROBUST mode.")
        return OperationalMode.ROBUST
    else:
        logger.info("Environment stable. Maintaining HIGH_PRECISION mode.")
        return OperationalMode.HIGH_PRECISION


def generate_dynamic_recipe(task_description: str, env_params: Dict[str, Any]) -> TaskRecipe:
    """
    核心函数 2：根据环境状态生成动态任务配方。

    这是“实践清单生成与闭环”的体现。它不仅仅是选择模型，还会调整任务的逻辑复杂度。
    - 高精度模式：使用云端大模型（如GPT-4），高Token限制，复杂推理链。
    - 鲁棒模式：使用本地小模型（如Llama 3），低Token限制，简化指令，启用快速失败。

    Args:
        task_description: 待执行任务的文本描述。
        env_params: 原始环境参数字典。

    Returns:
        TaskRecipe: 针对当前环境优化的任务配方对象。
    """
    try:
        context = validate_environment_params(env_params)
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        # 在验证失败时，默认回退到最安全的鲁棒模式
        context = EnvironmentContext(9999, 90, 0.5, 10.0)
        logger.info("Defaulting to safe ROBUST context due to validation error.")

    mode = assess_environmental_state(context)

    if mode == OperationalMode.HIGH_PRECISION:
        logger.info("Generating recipe for High Precision execution.")
        recipe = TaskRecipe(
            model_name="gpt-4-turbo",
            complexity_level="deep_reasoning",
            max_tokens=4096,
            temperature=0.7,
            retry_strategy={"attempts": 3, "backoff": "exponential"},
            estimated_duration_sec=15.0,
            fallback_enabled=False
        )
        # 在实际系统中，这里会根据 task_description 注入复杂的 Prompt 模板
    else:
        logger.info("Generating recipe for Robust execution (Simplified logic).")
        recipe = TaskRecipe(
            model_name="llama-3-8b-local",
            complexity_level="simple_extraction",
            max_tokens=512,
            temperature=0.1, # 降低随机性以增加稳定性
            retry_strategy={"attempts": 1, "backoff": "none"},
            estimated_duration_sec=2.0,
            fallback_enabled=True
        )

    logger.info(f"Recipe generated: {recipe}")
    return recipe


def simulate_task_execution(recipe: TaskRecipe, input_data: str) -> str:
    """
    模拟执行配方（用于演示闭环）。
    """
    logger.info(f"Executing task with {recipe.model_name}...")
    time.sleep(1)  # 模拟处理时间
    if recipe.complexity_level == "simple_extraction":
        return f"[SIMULATED OUTPUT] Simple result for: {input_data[:20]}..."
    else:
        return f"[SIMULATED OUTPUT] Deep analysis result for: {input_data[:20]}... (Confidence: 98%)"


if __name__ == "__main__":
    # 示例 1: 理想环境
    print("--- 场景 1: 理想环境 ---")
    ideal_env = {
        "network_latency_ms": 30.5,
        "cpu_temperature_c": 50.0,
        "available_memory_gb": 16.0,
        "system_load_avg": 0.8
    }
    recipe_1 = generate_dynamic_recipe("生成Q3财务报告", ideal_env)
    print(recipe_1)

    # 示例 2: 恶劣环境（网络延迟高）
    print("\n--- 场景 2: 恶劣环境 (高延迟) ---")
    poor_env = {
        "network_latency_ms": 350.0,
        "cpu_temperature_c": 65.0,
        "available_memory_gb": 8.0,
        "system_load_avg": 2.1
    }
    recipe_2 = generate_dynamic_recipe("生成Q3财务报告", poor_env)
    print(recipe_2)

    # 示例 3: 临界环境（高温）
    print("\n--- 场景 3: 临界环境 (过热) ---")
    hot_env = {
        "network_latency_ms": 45.0,
        "cpu_temperature_c": 90.0,
        "available_memory_gb": 4.0,
        "system_load_avg": 1.5
    }
    recipe_3 = generate_dynamic_recipe("简单文本分类", hot_env)
    print(recipe_3)

    # 模拟闭环执行
    result = simulate_task_execution(recipe_3, "这是一段测试文本")
    print(f"Execution Result: {result}")