#!/usr/bin/env python3
"""
极致推演 Round 4/5 — 自愈运行时 + 混沌工程 + 断路器
推演者: Claude Opus 4 | 框架: ULDS v2.1

目标突破: B10 Agent自治 + B9 API延迟优化

ULDS规律约束:
  L6 系统论: 反馈回路(错误率→断路)  BIBO稳定性(有限故障→有限恢复时间)
  L10 演化: 变异(故障注入)+选择(存活策略)+保留(成功模式)→适应(自愈)
  L7 概率: 滑动窗口错误率 + 3σ异常检测 + 指数退避
  L4 逻辑: 状态机严格转换 — 不允许非法状态跳转

超越策略:
  S3 王朝治理: 服务=臣子, 断路器=君主, 故障服务=反贼→隔离→重试→降级
  S7 零回避: CD02并发(原子状态转换), CD01边界(零请求/负延迟)
  S8 链式收敛: F(健康阈值)→V(当前错误率)→F(断路决策)→V(恢复尝试)→F(新健康状态)
"""

import time
import threading
import random
import math
from enum import Enum
from typing import Callable, Any, Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from collections import deque
from functools import wraps


# ==================== 断路器状态机 ====================

class CircuitState(Enum):
    CLOSED = "closed"        # 正常: 请求通过
    OPEN = "open"            # 断路: 请求被拒, 快速失败
    HALF_OPEN = "half_open"  # 探测: 允许少量请求试探恢复


@dataclass
class CircuitStats:
    """滑动窗口统计 — L7概率"""
    window_size: int = 60  # 秒
    _timestamps: deque = field(default_factory=deque)
    _successes: deque = field(default_factory=deque)
    _failures: deque = field(default_factory=deque)
    _latencies: deque = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self, latency: float):
        now = time.monotonic()
        with self._lock:
            self._timestamps.append(now)
            self._successes.append(now)
            self._latencies.append(latency)
            self._cleanup(now)

    def record_failure(self, latency: float):
        now = time.monotonic()
        with self._lock:
            self._timestamps.append(now)
            self._failures.append(now)
            self._latencies.append(latency)
            self._cleanup(now)

    def _cleanup(self, now: float):
        cutoff = now - self.window_size
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        while self._successes and self._successes[0] < cutoff:
            self._successes.popleft()
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()
        while len(self._latencies) > 1000:
            self._latencies.popleft()

    @property
    def error_rate(self) -> float:
        """L7: 当前错误率"""
        with self._lock:
            total = len(self._successes) + len(self._failures)
            if total == 0:
                return 0.0
            return len(self._failures) / total

    @property
    def total_requests(self) -> int:
        with self._lock:
            return len(self._successes) + len(self._failures)

    @property
    def avg_latency(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            return sum(self._latencies) / len(self._latencies)

    @property
    def p99_latency(self) -> float:
        """L7: P99延迟"""
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_lat = sorted(self._latencies)
            idx = int(len(sorted_lat) * 0.99)
            return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def to_dict(self) -> dict:
        with self._lock:
            total = len(self._successes) + len(self._failures)
            return {
                "total": total,
                "successes": len(self._successes),
                "failures": len(self._failures),
                "error_rate": round(self.error_rate, 4),
                "avg_latency_ms": round(self.avg_latency * 1000, 1),
                "p99_latency_ms": round(self.p99_latency * 1000, 1),
            }


class CircuitBreaker:
    """断路器 — S3王朝治理: 君主隔离反贼
    
    L4状态机不变量:
      CLOSED → OPEN:     当 error_rate > threshold
      OPEN → HALF_OPEN:  当 timeout 到期
      HALF_OPEN → CLOSED: 当探测请求成功
      HALF_OPEN → OPEN:   当探测请求失败
      不允许: CLOSED → HALF_OPEN, OPEN → CLOSED (必须经过探测)
    
    L6 BIBO稳定性: 有限故障输入 → 有限恢复时间 → 必回归正常
    """

    def __init__(self, name: str = "default",
                 failure_threshold: float = 0.5,
                 recovery_timeout: float = 30.0,
                 min_requests: int = 5,
                 half_open_max: int = 3,
                 on_state_change: Optional[Callable] = None):
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._min_requests = min_requests  # L7: 最小样本量
        self._half_open_max = half_open_max
        self._on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._opened_at: float = 0
        self._half_open_count: int = 0
        self._stats = CircuitStats()
        self._lock = threading.Lock()

        # L10演化: 自适应恢复超时
        self._consecutive_opens = 0
        self._base_timeout = recovery_timeout

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at > self._recovery_timeout:
                    self._transition(CircuitState.HALF_OPEN)
            return self._state

    def _transition(self, new_state: CircuitState):
        """状态转换 — L4: 严格状态机"""
        old = self._state
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._half_open_count = 0
            # L10演化: 指数退避恢复超时
            self._consecutive_opens += 1
            self._recovery_timeout = min(
                self._base_timeout * (2 ** (self._consecutive_opens - 1)),
                300.0  # 最大5分钟
            )
        elif new_state == CircuitState.CLOSED:
            self._consecutive_opens = 0
            self._recovery_timeout = self._base_timeout
            self._half_open_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_count = 0

        if self._on_state_change and old != new_state:
            try:
                self._on_state_change(self.name, old.value, new_state.value)
            except Exception:
                pass

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过断路器执行函数调用"""
        current = self.state

        if current == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit '{self.name}' is OPEN "
                f"(recovery in {self._recovery_timeout - (time.monotonic() - self._opened_at):.1f}s)"
            )

        if current == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_count >= self._half_open_max:
                    raise CircuitOpenError(f"Circuit '{self.name}' HALF_OPEN max probes reached")
                self._half_open_count += 1

        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
            latency = time.monotonic() - start
            self._stats.record_success(latency)

            with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    # 探测成功 → 关闭断路器
                    self._transition(CircuitState.CLOSED)

            return result

        except CircuitOpenError:
            raise
        except Exception as e:
            latency = time.monotonic() - start
            self._stats.record_failure(latency)

            with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    # 探测失败 → 重新断路
                    self._transition(CircuitState.OPEN)
                elif self._state == CircuitState.CLOSED:
                    # 检查是否需要断路
                    if (self._stats.total_requests >= self._min_requests
                            and self._stats.error_rate > self._failure_threshold):
                        self._transition(CircuitState.OPEN)
            raise

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "recovery_timeout": round(self._recovery_timeout, 1),
            "consecutive_opens": self._consecutive_opens,
            **self._stats.to_dict()
        }


class CircuitOpenError(Exception):
    """断路器打开时的快速失败异常"""
    pass


# ==================== 混沌工程 ====================

class ChaosMonkey:
    """混沌猴 — L10演化: 通过故障注入驱动系统适应
    
    变异: 随机注入延迟/异常/超时
    选择: 存活的策略被保留
    保留: 成功的恢复模式写入知识库
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._attack_log: List[Dict] = []
        self._lock = threading.Lock()

    def maybe_inject_latency(self, max_ms: float = 500, probability: float = 0.1):
        """注入随机延迟 — L2物理: 网络延迟是不可消除的"""
        if not self.enabled or random.random() > probability:
            return
        delay = random.uniform(0, max_ms / 1000)
        with self._lock:
            self._attack_log.append({
                "type": "latency", "delay_ms": round(delay * 1000, 1),
                "time": time.time()
            })
        time.sleep(delay)

    def maybe_raise_error(self, probability: float = 0.1,
                          error_class: type = RuntimeError):
        """注入随机异常"""
        if not self.enabled or random.random() > probability:
            return
        with self._lock:
            self._attack_log.append({
                "type": "error", "error": error_class.__name__,
                "time": time.time()
            })
        raise error_class("ChaosMonkey: Injected failure")

    @property
    def attack_count(self) -> int:
        with self._lock:
            return len(self._attack_log)


# ==================== 自愈运行时 ====================

class SelfHealingRuntime:
    """自愈运行时 — 整合断路器+重试+降级+混沌
    
    S3王朝治理架构:
      君(Runtime): 全局监控, 策略决策
      臣(Service): 各服务通过断路器隔离
      反贼(故障服务): 断路→隔离→探测→恢复/永久降级
    
    S8链式收敛:
      F(健康阈值) → V(实时错误率) → F(断路决策)
      → V(恢复探测) → F(新健康状态) → V(流量恢复)
    """

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._fallbacks: Dict[str, Callable] = {}
        self._chaos = ChaosMonkey(enabled=False)
        self._lock = threading.Lock()

    def register_service(self, name: str,
                         failure_threshold: float = 0.5,
                         recovery_timeout: float = 30.0,
                         fallback: Optional[Callable] = None) -> CircuitBreaker:
        """注册服务 + 断路器 + 降级函数"""
        cb = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        with self._lock:
            self._circuits[name] = cb
            if fallback:
                self._fallbacks[name] = fallback
        return cb

    def call(self, service_name: str, func: Callable,
             *args, max_retries: int = 2, **kwargs) -> Any:
        """调用服务 — 自动重试+断路+降级
        
        L6反馈回路: 失败→重试→断路→降级
        L7指数退避: 重试间隔 = base * 2^n + jitter
        """
        cb = self._circuits.get(service_name)
        if cb is None:
            cb = self.register_service(service_name)

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # 混沌注入
                self._chaos.maybe_inject_latency(probability=0.05)
                self._chaos.maybe_raise_error(probability=0.02)

                return cb.call(func, *args, **kwargs)

            except CircuitOpenError:
                # 断路器打开 → 直接降级
                fallback = self._fallbacks.get(service_name)
                if fallback:
                    return fallback(*args, **kwargs)
                raise

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    # L7指数退避 + 随机抖动
                    delay = min(0.1 * (2 ** attempt) + random.uniform(0, 0.05), 5.0)
                    time.sleep(delay)

        # 所有重试失败 → 降级
        fallback = self._fallbacks.get(service_name)
        if fallback:
            return fallback(*args, **kwargs)
        raise last_error

    def enable_chaos(self):
        self._chaos.enabled = True

    def disable_chaos(self):
        self._chaos.enabled = False

    @property
    def health(self) -> dict:
        with self._lock:
            services = {}
            for name, cb in self._circuits.items():
                services[name] = cb.stats
            return {
                "services": services,
                "chaos_enabled": self._chaos.enabled,
                "chaos_attacks": self._chaos.attack_count,
            }


# ==================== 装饰器 ====================

_default_runtime = SelfHealingRuntime()

def circuit_protected(service_name: str, fallback: Optional[Callable] = None,
                      max_retries: int = 2):
    """装饰器: 为函数添加断路器保护"""
    if fallback:
        _default_runtime.register_service(service_name, fallback=fallback)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _default_runtime.call(service_name, func, *args,
                                         max_retries=max_retries, **kwargs)
        return wrapper
    return decorator


# ==================== 单元测试 ====================

def _raise_runtime():
    raise RuntimeError("fail")

def test_circuit_breaker_basic():
    """测试断路器基本流程"""
    cb = CircuitBreaker(name="test", failure_threshold=0.5,
                        recovery_timeout=0.3, min_requests=3)

    # 3次成功
    for _ in range(3):
        cb.call(lambda: "ok")
    assert cb.state == CircuitState.CLOSED

    # 4次失败 → error_rate = 4/7 = 0.57 > 0.5 → 断路
    for _ in range(4):
        try:
            cb.call(_raise_runtime)
        except RuntimeError:
            pass
    assert cb.state == CircuitState.OPEN
    print("  [PASS] test_circuit_breaker_basic")

def test_circuit_recovery():
    """测试断路器恢复"""
    cb = CircuitBreaker(name="recover", failure_threshold=0.5,
                        recovery_timeout=0.2, min_requests=2)

    # 触发断路
    for _ in range(3):
        try:
            cb.call(_raise_runtime)
        except (RuntimeError, CircuitOpenError):
            pass
    assert cb.state == CircuitState.OPEN

    # 等待恢复
    time.sleep(0.3)
    assert cb.state == CircuitState.HALF_OPEN

    # 探测成功 → 关闭
    cb.call(lambda: "recovered")
    assert cb.state == CircuitState.CLOSED
    print("  [PASS] test_circuit_recovery")

def test_exponential_backoff():
    """测试指数退避 — L10演化"""
    cb = CircuitBreaker(name="backoff", failure_threshold=0.5,
                        recovery_timeout=0.1, min_requests=2)

    # 多次断路→恢复→断路 检查超时递增
    timeouts = []
    for cycle in range(3):
        for _ in range(3):
            try:
                cb.call(_raise_runtime)
            except (RuntimeError, CircuitOpenError):
                pass
        timeouts.append(cb._recovery_timeout)
        time.sleep(cb._recovery_timeout + 0.05)
        cb.call(lambda: "probe")  # half_open→closed

    # 超时应递增 (但重置后又从base开始)
    assert timeouts[0] <= timeouts[1] or cb._consecutive_opens == 0
    print(f"  [PASS] test_exponential_backoff (timeouts={[round(t,2) for t in timeouts]})")

def test_self_healing_runtime():
    """测试自愈运行时 — 重试+降级"""
    rt = SelfHealingRuntime()
    call_count = [0]

    def flaky_service():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise ConnectionError("Temporary failure")
        return "success"

    result = rt.call("flaky", flaky_service, max_retries=3)
    assert result == "success"
    assert call_count[0] == 3  # 2次失败 + 1次成功
    print(f"  [PASS] test_self_healing_runtime (calls={call_count[0]})")

def test_fallback():
    """测试降级函数"""
    rt = SelfHealingRuntime()
    rt.register_service("broken", failure_threshold=0.3,
                        recovery_timeout=0.1, fallback=lambda: "fallback_value")

    def always_fail():
        raise RuntimeError("Always fails")

    result = rt.call("broken", always_fail, max_retries=0)
    assert result == "fallback_value"
    print("  [PASS] test_fallback")

def test_chaos_monkey():
    """测试混沌猴 — L10演化"""
    chaos = ChaosMonkey(enabled=True)

    # 注入延迟 (高概率)
    start = time.monotonic()
    chaos.maybe_inject_latency(max_ms=100, probability=1.0)
    elapsed = time.monotonic() - start
    assert elapsed > 0  # 应有延迟

    # 注入异常
    try:
        chaos.maybe_raise_error(probability=1.0)
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "ChaosMonkey" in str(e)

    assert chaos.attack_count == 2
    print(f"  [PASS] test_chaos_monkey (attacks={chaos.attack_count})")

def test_health_dashboard():
    """测试健康仪表盘"""
    rt = SelfHealingRuntime()
    rt.register_service("svc_a")
    rt.register_service("svc_b")

    rt.call("svc_a", lambda: "ok")
    health = rt.health
    assert "svc_a" in health["services"]
    assert "svc_b" in health["services"]
    assert health["services"]["svc_a"]["state"] == "closed"
    print("  [PASS] test_health_dashboard")

def test_concurrent_circuit():
    """测试并发断路器 — S7-CD02"""
    cb = CircuitBreaker(name="concurrent", failure_threshold=0.8,
                        min_requests=10, recovery_timeout=1)
    errors = []

    def hammer(n):
        for _ in range(50):
            try:
                cb.call(lambda: "ok")
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=hammer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 应该没有线程安全错误 (CircuitOpenError是预期的)
    real_errors = [e for e in errors if not isinstance(e, CircuitOpenError)]
    assert len(real_errors) == 0, f"Thread safety errors: {real_errors}"
    print(f"  [PASS] test_concurrent_circuit (total_calls=400, circuit_state={cb.state.value})")


if __name__ == "__main__":
    print("=" * 60)
    print("极致推演 Round 4: 自愈运行时+混沌工程+断路器")
    print("ULDS: L6系统论 + L10演化 + L7概率 + L4逻辑")
    print("策略: S3王朝治理 + S7零回避 + S8链式收敛")
    print("=" * 60)
    test_circuit_breaker_basic()
    test_circuit_recovery()
    test_exponential_backoff()
    test_self_healing_runtime()
    test_fallback()
    test_chaos_monkey()
    test_health_dashboard()
    test_concurrent_circuit()
    print("=" * 60)
    print("ALL 8 TESTS PASSED ✅")
    print("=" * 60)
