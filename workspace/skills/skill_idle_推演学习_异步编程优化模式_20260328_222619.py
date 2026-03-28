#!/usr/bin/env python3
"""
自动推演生成的Skill: 推演学习: 异步编程优化模式
生成时间: 2026-03-28T22:26:19.984159
"""

# === 导入必要库 ===
import asyncio
import time
import random
from typing import List, Dict, Any, Callable, TypeVar, Optional
from functools import wraps
from dataclasses import dataclass

# === 类型定义 ===
T = TypeVar('T')

# === 1. 核心概念总结 ===
"""
【异步编程优化模式：核心概念推演】

1. 并发控制：
   - 核心痛点：无限并发会导致内存溢出（OOM）或触发下游服务限流。
   - 解决方案：使用 Semaphore (信号量) 或令牌桶算法限制同时进行的协程数量。

2. 批处理与聚合：
   - 核心痛点：频繁的小任务调度会增加事件循环开销。
   - 解决方案：将多个小任务合并为批次执行，或使用 asyncio.gather 进行结果聚合。

3. 弹性容错：
   - 核心痛点：网络波动或单点故障导致整个任务链中断。
   - 解决方案：引入 Timeout (超时控制)、Retry (指数退避重试) 和 Circuit Breaker (熔断)。

4. 结构化并发：
   - 核心理念：确保任务的生命周期作用域明确，防止任务泄漏。
"""

# === 2. 实践应用示例：通用异步优化器 ===

class AsyncPatternOptimizer:
    """
    一个封装了并发限制、超时控制和重试机制的异步任务处理器。
    """
    
    def __init__(self, concurrency_limit: int = 10, timeout: float = 5.0, max_retries: int = 3):
        self.concurrency_limit = concurrency_limit
        self.timeout = timeout
        self.max_retries = max_retries
        # 信号量，用于限制并发数
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        
    async def _execute_with_retry(self, task_func: Callable[..., T], *args, **kwargs) -> T:
        """
        包装单个任务，包含重试逻辑和超时控制
        """
        attempt = 0
        last_exception = None
        
        while attempt < self.max_retries:
            try:
                # 使用信号量限制并发
                async with self.semaphore:
                    # wait_for 负责超时控制
                    return await asyncio.wait_for(task_func(*args, **kwargs), timeout=self.timeout)
            except asyncio.TimeoutError as e:
                last_exception = e
                print(f"⚠️ Task timed out (Attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                last_exception = e
                print(f"❌ Task failed: {e} (Attempt {attempt + 1}/{self.max_retries})")
            
            attempt += 1
            # 指数退避策略
            backoff_time = min(2 ** attempt, 10) 
            await asyncio.sleep(backoff_time)
            
        raise Exception(f"Task failed after {self.max_retries} retries. Last error: {last_exception}")

    async def batch_process(self, tasks: List[Callable[..., T]]) -> List[T]:
        """
        批量处理任务，保持并发限制
        """
        print(f"🚀 Starting batch processing with concurrency: {self.concurrency_limit}")
        # 将函数调用包装为协程对象列表
        coroutines = [self._execute_with_retry(task) for task in tasks]
        
        # 使用 gather 聚合结果，return_exceptions=True 防止单个失败中断全部
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        processed_results = []
        for res in results:
            if isinstance(res, Exception):
                processed_results.append(None) # 或者根据业务需求处理错误
            else:
                processed_results.append(res)
        return processed_results

# === 模拟业务函数 ===

async def mock_api_call(item_id: int):
    """模拟一个不稳定的异步IO操作"""
    print(f"🔄 Processing item {item_id}...")
    await asyncio.sleep(random.uniform(0.1, 0.5)) # 模拟网络延迟
    
    # 模拟随机失败
    if random.random() < 0.2:
        raise ConnectionError("Network unstable")
    
    return {"id": item_id, "status": "success", "data": f"Result-{item_id}"}

# === 3. Skill 封装模板 (符合 skill-factory 规范) ===

@dataclass
class SkillConfig:
    """Skill 配置元数据"""
    skill_name: str = "AsyncOptimizerSkill"
    description: str = "Provides controlled concurrency, retry, and timeout patterns for async tasks."
    version: str = "1.0.0"
    author: str = "AGI-v13"

class AsyncOptimizerSkill:
    """
    [Skill Code Template]
    这是一个标准化的 Skill 封装，可直接集成到 Skill-Factory 中。
    """
    
    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()
        self.optimizer = None # 延迟初始化

    def initialize(self, concurrency: int = 5, timeout: float = 3.0):
        """初始化 Skill 运行参数"""
        self.optimizer = AsyncPatternOptimizer(
            concurrency_limit=concurrency, 
            timeout=timeout
        )
        print(f"✅ Skill [{self.config.skill_name}] Initialized.")

    async def execute(self, input_data: List[Callable]):
        """
        Skill 执行入口
        :param input_data: 可调用的异步函数列表
        """
        if not self.optimizer:
            self.initialize()
            
        print(f"Executing Skill: {self.config.skill_name}")
        try:
            results = await self.optimizer.batch_process(input_data)
            return {
                "status": "completed",
                "result_count": len(results),
                "data": results
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

# === 主程序测试入口 ===

async def main():
    # 1. 实例化 Skill
    skill = AsyncOptimizerSkill()
    skill.initialize(concurrency=3, timeout=0.4) # 设置并发为3，超时0.4s(测试会触发超时)

    # 2. 准备任务数据
    # 注意：这里传入的是函数对象，不是协程对象
    tasks_to_run = [
        lambda: mock_api_call(1),
        lambda: mock_api_call(2),
        lambda: mock_api_call(3),
        lambda: mock_api_call(4), # 可能会触发重试
        lambda: mock_api_call(5),
    ]

    # 3. 运行 Skill
    start_time = time.time()
    result_wrapper = await skill.execute(tasks_to_run)
    end_time = time.time()

    # 4. 输出结果
    print("\n--- Execution Report ---")
    print(f"Duration: {end_time - start_time:.2f}s")
    print(f"Status: {result_wrapper['status']}")
    print(f"Results: {result_wrapper['data']}")

if __name__ == "__main__":
    # 兼容 Windows 的事件循环策略 (如果使用 Python 3.8+ 且在 Windows 上)
    if asyncio.run.__module__ == 'asyncio':
        asyncio.run(main())


if __name__ == "__main__":
    print("Skill: 推演学习: 异步编程优化模式")
