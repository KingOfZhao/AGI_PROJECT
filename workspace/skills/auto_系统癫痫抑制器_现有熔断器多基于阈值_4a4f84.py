"""
高级AGI技能模块：系统癫痫抑制器

该模块实现了基于生物神经胶质细胞调节机制的负反馈控制系统。
不同于传统刚性的阈值熔断器，本系统引入“抑制性AI代理”概念。
当检测到系统指标（如网络流量、请求速率）出现高频振荡（模拟生物癫痫波）时，
代理会计算并注入抑制性信号（如延迟、阻尼、指数退避），
以主动平滑波形，防止系统进入正反馈循环导致自毁。

版权所有 (C) 2023 AGI Systems Inc.
"""

import time
import math
import logging
from collections import deque
from typing import Deque, Tuple, Optional, Callable
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemEpilepsySuppressor")


@dataclass
class SystemState:
    """
    系统状态数据结构。

    Attributes:
        timestamp (float): 时间戳。
        metric_value (float): 监控的指标值（如QPS、CPU使用率）。
        label (str): 可选的标签，用于标识数据来源。
    """
    timestamp: float
    metric_value: float
    label: str = "default"


@dataclass
class SuppressorConfig:
    """
    抑制器配置参数。

    Attributes:
        history_window_size (int): 振荡检测的历史窗口大小。
        oscillation_threshold (float): 判定为高频振荡的方差阈值。
        damping_factor (float): 阻尼系数，控制抑制信号的强度。
        max_delay_seconds (float): 最大允许的注入延迟。
    """
    history_window_size: int = 10
    oscillation_threshold: float = 15.0
    damping_factor: float = 0.5
    max_delay_seconds: float = 2.0


class EpilepsySuppressor:
    """
    系统癫痫抑制器核心类。

    模拟神经胶质细胞的行为，监控输入信号，
    并在检测到异常振荡时注入负反馈信号。
    """

    def __init__(self, config: SuppressorConfig):
        """
        初始化抑制器。

        Args:
            config (SuppressorConfig): 配置对象。
        """
        self.config = config
        self._signal_history: Deque[SystemState] = deque(maxlen=config.history_window_size)
        self._current_suppression_level = 0.0
        logger.info("EpilepsySuppressor initialized with config: %s", config)

    def _calculate_variance(self) -> float:
        """
        辅助函数：计算历史窗口内指标值的方差，用于量化振荡强度。

        Returns:
            float: 历史数据的方差。如果数据不足，返回0.0。
        """
        if len(self._signal_history) < 2:
            return 0.0

        values = [s.metric_value for s in self._signal_history]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

    def _validate_state(self, state: SystemState) -> bool:
        """
        辅助函数：验证输入状态数据的合法性。

        Args:
            state (SystemState): 输入的系统状态。

        Returns:
            bool: 数据是否合法。
        """
        if state.timestamp < 0:
            logger.error("Invalid timestamp detected: %f", state.timestamp)
            return False
        if state.metric_value < 0:
            logger.warning("Negative metric value detected, absolute value used.")
            # 修正数据而非直接拒绝，模拟生物系统的鲁棒性
            state.metric_value = abs(state.metric_value)
        return True

    def observe_and_respond(self, current_state: SystemState) -> Tuple[float, Optional[float]]:
        """
        核心函数：观测当前状态并生成抑制性响应。

        该方法实现了生物学中的负反馈回路：
        1. 记录当前的兴奋度（指标值）。
        2. 检测是否出现异常振荡（癫痫波）。
        3. 如果振荡超过阈值，计算需要的抑制信号（延迟/阻尼）。

        Args:
            current_state (SystemState): 当前系统的状态快照。

        Returns:
            Tuple[float, Optional[float]]:
                - float: 建议的系统阻尼系数（0.0-1.0，1.0表示完全抑制）。
                - Optional[float]: 建议的延迟时间（秒）。如果不需要延迟则为None。

        Raises:
            ValueError: 如果输入数据验证失败。
        """
        if not self._validate_state(current_state):
            raise ValueError("Invalid system state input.")

        # 1. 记录信号历史
        self._signal_history.append(current_state)

        # 2. 分析波形（检测振荡）
        variance = self._calculate_variance()
        logger.debug(f"Current variance: {variance:.2f}")

        response_delay = None
        damping_strength = 0.0

        # 3. 判断是否需要启动抑制机制
        if variance > self.config.oscillation_threshold:
            # 计算超出阈值的程度
            overflow_ratio = (variance - self.config.oscillation_threshold) / self.config.oscillation_threshold
            
            # 模拟抑制性神经元释放GABA（抑制性神经递质）
            # 强度随振荡强度指数级增加，但受最大延迟限制
            damping_strength = min(1.0, overflow_ratio * self.config.damping_factor)
            
            # 计算注入的延迟（模拟突触传递延迟增加）
            calculated_delay = math.exp(overflow_ratio) * 0.1
            response_delay = min(calculated_delay, self.config.max_delay_seconds)

            logger.warning(
                f"High-frequency oscillation detected! Variance: {variance:.2f}. "
                f"Injecting suppression: Damping={damping_strength:.2f}, Delay={response_delay:.2f}s"
            )
            
            # 更新内部抑制水平
            self._current_suppression_level = damping_strength
        else:
            # 恢复正常，抑制水平逐渐消退
            self._current_suppression_level *= 0.9
            logger.debug("System stable. Suppression relaxing.")

        return damping_strength, response_delay


# 示例使用和模拟
if __name__ == "__main__":
    # 初始化配置
    config = SuppressorConfig(
        history_window_size=5,
        oscillation_threshold=10.0,
        damping_factor=0.8
    )
    
    # 实例化抑制器
    suppressor = EpilepsySuppressor(config)
    
    print("--- Starting Simulation ---")
    
    # 模拟数据流
    # 阶段1: 稳定期
    print("\n[Phase 1: Stable State]")
    for i in range(5):
        state = SystemState(timestamp=time.time(), metric_value=50 + i*0.5)
        damp, delay = suppressor.observe_and_respond(state)
        print(f"Input: {state.metric_value:.1f} -> Damping: {damp:.2f}, Delay: {delay}")
        time.sleep(0.1)

    # 阶段2: 诱发振荡 (模拟癫痫发作前兆)
    print("\n[Phase 2: Inducing Oscillation]")
    for i in range(10):
        # 产生剧烈波动的数值 (高频振荡)
        val = 50 + 20 * math.sin(i * 1.5) * (i % 2 * 2 - 1) * (i/2)
        state = SystemState(timestamp=time.time(), metric_value=val)
        
        try:
            damp, delay = suppressor.observe_and_respond(state)
            print(f"Input: {state.metric_value:.1f} -> Damping: {damp:.2f}, Delay: {delay}")
            
            if delay:
                # 模拟系统执行延迟操作
                time.sleep(delay)
                
        except ValueError as e:
            print(f"Error processing state: {e}")

    # 阶段3: 恢复期
    print("\n[Phase 3: Recovery]")
    for i in range(5):
        state = SystemState(timestamp=time.time(), metric_value=55)
        damp, delay = suppressor.observe_and_respond(state)
        print(f"Input: {state.metric_value:.1f} -> Damping: {damp:.2f}, Delay: {delay}")
        time.sleep(0.1)