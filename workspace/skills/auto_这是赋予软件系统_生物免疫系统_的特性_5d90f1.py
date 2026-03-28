"""
Module: auto_immune_system.py
Description: 这是赋予软件系统'生物免疫系统'的特性。
             实现了内省校验（预防）、边界监测（抗压）、自主重构（自愈）和熔断求救（免疫反应）。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import time
import logging
import threading
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("AGI_Immune_System")


@dataclass
class SystemState:
    """系统上下文状态数据类，用于存储环境一致性校验所需的数据。"""
    env_vars: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    health_score: float = 1.0  # 0.0 (Dead) to 1.0 (Perfect)


class ImmuneSystemError(Exception):
    """免疫系统自定义异常基类。"""
    pass


class AutoReconstructionError(ImmuneSystemError):
    """当自愈失败时抛出的异常。"""
    pass


class CircuitBreakerTriggered(ImmuneSystemError):
    """当熔断机制触发时抛出的异常。"""
    pass


class AGIImmuneSystem:
    """
    AGI免疫系统核心类。
    
    赋予代码主动防御、自我修复和环境适应的能力。
    
    Attributes:
        state (SystemState): 当前系统的上下文状态。
        failure_threshold (int): 触发熔断的连续失败次数阈值。
        recovery_timeout (float): 熔断后尝试恢复的超时时间（秒）。
    """

    def __init__(self, initial_state: Optional[SystemState] = None):
        self.state = initial_state if initial_state else SystemState()
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._is_broken = False
        self._lock = threading.RLock()
        logger.info("AGI Immune System initialized.")

    def _introspection_check(self, required_keys: List[str]) -> bool:
        """
        [预防] 辅助函数：内省与上下文一致性校验。
        
        在执行关键任务前，检查环境变量和依赖是否满足预期。
        
        Args:
            required_keys (List[str]): 必须存在的环境变量键列表。
            
        Returns:
            bool: 校验是否通过。
        """
        logger.debug(f"Running introspection check for: {required_keys}")
        missing = [key for key in required_keys if key not in self.state.env_vars]
        
        if missing:
            logger.warning(f"Context consistency check failed. Missing keys: {missing}")
            return False
        
        if self.state.health_score < 0.5:
            logger.warning("System health score low. Risk of execution failure.")
            # 这里不直接阻止运行，但记录风险，模拟带有风险的内省
            
        return True

    def _monitor_boundary(self, value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> bool:
        """
        [抗压] 辅助函数：边界条件监测。
        
        检查数值是否在安全范围内，防止溢出或无效输入导致的系统崩溃。
        
        Args:
            value: 待检查的值。
            min_val: 允许的最小值。
            max_val: 允许的最大值。
            
        Returns:
            bool: 是否在边界内。
        """
        if not (min_val <= value <= max_val):
            logger.error(f"Boundary violation detected: Value {value} out of range [{min_val}, {max_val}].")
            return False
        return True

    def _self_healing_trigger(self, func_name: str, error: Exception) -> None:
        """
        [自愈] 核心机制：自主触发重构请求。
        
        当捕获到异常时，不立即崩溃，而是尝试清理状态或回滚，
        模拟向更高级别的控制系统发送重构信号。
        
        Args:
            func_name (str): 发生错误的函数名。
            error (Exception): 捕获的异常对象。
        """
        logger.warning(f"Self-healing triggered for function '{func_name}' due to: {str(error)}")
        
        # 模拟自愈逻辑：重置部分状态或清理缓存
        try:
            # 假设自愈操作是清理环境变量中的脏数据
            if "dirty_data" in self.state.env_vars:
                del self.state.env_vars["dirty_data"]
                logger.info("Self-healing action: Cleaned dirty data.")
            
            # 降低健康度
            self.state.health_score = max(0.0, self.state.health_score - 0.1)
            logger.info(f"System health score adjusted to: {self.state.health_score:.2f}")
            
        except Exception as heal_error:
            logger.critical(f"Self-healing failed! Manual intervention required. Error: {heal_error}")
            raise AutoReconstructionError("Critical failure during self-healing process.")

    def _circuit_breaker_check(self) -> None:
        """
        [免疫反应] 核心机制：熔断与求救。
        
        如果短时间内错误频繁发生，暂停系统接受新请求，
        防止雪崩（类似于生物体的发热或休克反应）。
        """
        with self._lock:
            if self._is_broken:
                # 检查是否可以尝试恢复（半开启状态）
                if time.time() - self._last_failure_time > 5.0: # 5秒冷却时间
                    logger.info("Circuit Breaker in Half-Open state. Probing...")
                    return
                else:
                    raise CircuitBreakerTriggered("System is currently immune-isolated (Circuit Broken). Too many errors.")

    def _record_failure(self) -> None:
        """记录一次失败，用于熔断判断。"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= 3:
                self._is_broken = True
                logger.critical("Circuit Breaker ACTIVATED. System entering protected mode.")

    def _record_success(self) -> None:
        """记录一次成功，重置熔断计数器。"""
        with self._lock:
            self._failure_count = 0
            if self._is_broken:
                self._is_broken = False
                logger.info("Circuit Breaker RESET. System recovered.")

    def immune_wrapper(self, required_context: List[str] = None):
        """
        装饰器：将普通函数包裹在免疫系统中。
        
        集成了内省、边界检查（需在函数内部调用）、异常捕获自愈和熔断机制。
        """
        if required_context is None:
            required_context = []

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 1. 预防：上下文校验
                if not self._introspection_check(required_context):
                    raise ImmuneSystemError("Pre-execution introspection failed.")

                # 2. 免疫反应：熔断检查
                self._circuit_breaker_check()

                try:
                    # 执行目标函数
                    result = func(*args, **kwargs)
                    self._record_success()
                    return result
                
                except CircuitBreakerTriggered:
                    raise # 直接向上抛出熔断异常
                except Exception as e:
                    logger.error(f"Exception caught in immune wrapper: {e}")
                    # 3. 自愈：触发重构
                    self._self_healing_trigger(func.__name__, e)
                    self._record_failure()
                    
                    # 根据策略，可以选择重试一次或者抛出特定异常
                    # 这里演示：自愈后尝试重试一次（仅限一次）
                    try:
                        logger.info(f"Retrying {func.__name__} after self-healing...")
                        result = func(*args, **kwargs)
                        self._record_success()
                        return result
                    except Exception as retry_e:
                        self._record_failure()
                        raise ImmuneSystemError(f"Execution failed even after self-healing attempt. Root cause: {retry_e}")

            return wrapper
        return decorator


# ================= 使用示例 =================

# 初始化免疫系统
immune_sys = AGIImmuneSystem()
# 模拟设置一些环境变量
immune_sys.state.env_vars["API_KEY"] = "12345"
immune_sys.state.env_vars["DB_CONN"] = "postgres://localhost"

@immune_sys.immune_wrapper(required_context=["API_KEY", "DB_CONN"])
def process_data_pipeline(data_size: int):
    """
    模拟数据处理管道。
    受免疫系统保护：需要API_KEY，具备自愈和熔断能力。
    """
    # 模拟边界检查
    if not immune_sys._monitor_boundary(data_size, 1, 1000):
        raise ValueError("Data size out of permissible boundary.")

    # 模拟业务逻辑
    print(f"Processing {data_size} records...")
    
    # 模拟随机故障场景（仅用于演示）
    # 如果环境中标记了 'simulate_failure'，则抛出错误
    if immune_sys.state.env_vars.get("simulate_failure", False):
        raise RuntimeError("Database connection lost during processing!")
    
    return f"Successfully processed {data_size} records."

def run_demonstration():
    """运行演示场景"""
    print("\n--- Scenario 1: Normal Execution ---")
    try:
        msg = process_data_pipeline(100)
        print(f"Result: {msg}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Scenario 2: Context Missing (Introspection) ---")
    # 临时删除一个必需的上下文变量
    temp = immune_sys.state.env_vars.pop("API_KEY")
    try:
        process_data_pipeline(50)
    except Exception as e:
        print(f"Caught expected error: {e}")
    finally:
        immune_sys.state.env_vars["API_KEY"] = temp

    print("\n--- Scenario 3: Boundary Violation (Stress Test) ---")
    try:
        process_data_pipeline(5000) # 超出边界
    except Exception as e:
        print(f"Caught expected error: {e}")

    print("\n--- Scenario 4: Self-Healing & Circuit Breaker ---")
    # 激活模拟故障
    immune_sys.state.env_vars["simulate_failure"] = True
    
    for i in range(5):
        print(f"\nAttempt {i+1}:")
        try:
            process_data_pipeline(10)
        except Exception as e:
            print(f"System Response: {e}")
            if immune_sys._is_broken:
                print(">> The system has triggered the Circuit Breaker (Immune Response). <<")
                break
    
    # 演示结束，清理
    immune_sys.state.env_vars["simulate_failure"] = False

if __name__ == "__main__":
    run_demonstration()