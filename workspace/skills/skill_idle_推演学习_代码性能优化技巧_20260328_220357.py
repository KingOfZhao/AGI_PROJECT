#!/usr/bin/env python3
"""
自动推演生成的Skill: 推演学习: 代码性能优化技巧
生成时间: 2026-03-28T22:03:57.966813
"""

import time
import asyncio
import functools
from typing import List, Dict, Set, Any, Callable

# ==========================================
# 场景 A: 算法复杂度优化 (O(N^2) -> O(N))
# ==========================================

def inefficient_search(list_a: List[int], list_b: List[int]) -> List[int]:
    """
    [反例] 嵌套循环查找交集
    时间复杂度: O(N * M)
    """
    result = []
    for item_a in list_a:
        for item_b in list_b:
            if item_a == item_b:
                result.append(item_a)
                break
    return result

def optimized_search(list_a: List[int], list_b: List[int]) -> Set[int]:
    """
    [正例] 利用 Hash Set 特性
    时间复杂度: O(N + M)
    原理: 空间换时间，将 list_b 转为哈希表，查找耗时 O(1)
    """
    set_b = set(list_b)
    # 列表推导式 + 集合查找
    return {item for item in list_a if item in set_b}

# ==========================================
# 场景 B: 缓存优化
# ==========================================

def expensive_computation(n: int) -> int:
    """模拟耗时计算"""
    time.sleep(0.01)
    return n * n

@functools.lru_cache(maxsize=None)
def cached_computation(n: int) -> int:
    """
    [正例] 使用内存缓存
    原理: 避免重复计算，牺牲内存换取CPU时间
    """
    return expensive_computation(n)

# ==========================================
# 场景 C: I/O 并发优化
# ==========================================

async def mock_network_request(url: str, delay: float = 0.1) -> str:
    """模拟网络请求耗时"""
    await asyncio.sleep(delay)
    return f"Response from {url}"

async def fetch_sync_style(urls: List[str]) -> List[str]:
    """
    [反例] 串行执行 (总耗时 = N * Delay)
    """
    results = []
    for url in urls:
        res = await mock_network_request(url)
        results.append(res)
    return results

async def fetch_async_style(urls: List[str]) -> List[str]:
    """
    [正例] 并发执行 (总耗时 ≈ Max(Delay))
    原理: 在等待 I/O 时释放控制权，执行其他任务
    """
    tasks = [mock_network_request(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

# ==========================================
# 测试驱动代码
# ==========================================

def run_performance_demo():
    print("--- [Test 1] 算法复杂度优化 ---")
    size = 1000
    l1 = list(range(size))
    l2 = list(range(size//2, size*2))
    
    start = time.perf_counter()
    inefficient_search(l1, l2)
    print(f"Nested Loop (O^2): {time.perf_counter() - start:.4f}s")

    start = time.perf_counter()
    optimized_search(l1, l2)
    print(f"Set Lookup (O):   {time.perf_counter() - start:.4f}s")

    print("\n--- [Test 2] 缓存优化 ---")
    start = time.perf_counter()
    cached_computation(10) # First run (Miss)
    cached_computation(10) # Second run (Hit)
    print(f"Cached calls:     {time.perf_counter() - start:.4f}s (2nd call instant)")

    print("\n--- [Test 3] I/O 并发优化 ---")
    urls = ["url1", "url2", "url3", "url4"]
    
    loop = asyncio.get_event_loop()
    
    start = time.perf_counter()
    loop.run_until_complete(fetch_sync_style(urls))
    print(f"Serial I/O:       {time.perf_counter() - start:.4f}s")

    start = time.perf_counter()
    loop.run_until_complete(fetch_async_style(urls))
    print(f"Concurrent I/O:   {time.perf_counter() - start:.4f}s")

if __name__ == "__main__":
    run_performance_demo()


if __name__ == "__main__":
    print("Skill: 推演学习: 代码性能优化技巧")
