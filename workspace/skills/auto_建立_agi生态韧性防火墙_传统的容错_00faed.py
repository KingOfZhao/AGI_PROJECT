"""
AGI生态韧性防火墙模块

该模块实现了一种基于生态动力学的AGI系统自愈架构。不同于传统的基于规则的容错机制，
本系统通过监测认知网络的'临界慢化'(Critical Slowing Down, CSD)指标来预测系统性
崩溃的临界点。在资源耗尽前主动执行'断尾求生'策略(丢弃非核心功能模块)，并在危机
过后利用'土壤种子库'(核心真实节点)快速重构认知网络。

核心算法:
1. 临界慢化监测: 通过自相关系数和方差变化率检测系统稳定性
2. 模块重要性评估: 基于生态位价值模型评估模块重要性
3. 断尾求生策略: 根据模块重要性有序丢弃非核心模块
4. 网络重构: 利用种子库快速恢复核心认知功能

典型使用示例:
    >>> firewall = AGIEcologicalResilienceFirewall()
    >>> firewall.register_module("visual_perception", importance=0.9, resource_usage=0.3)
    >>> firewall.register_module("chitchat_bot", importance=0.2, resource_usage=0.1)
    >>> # 监测系统状态
    >>> status = firewall.monitor_system()
    >>> if status == SystemState.CRITICAL:
    ...     firewall.execute_autotomy_strategy()
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Ecological_Resilience")


class SystemState(Enum):
    """AGI系统状态枚举"""
    HEALTHY = auto()       # 系统健康
    WARNING = auto()       # 警告状态
    CRITICAL = auto()      # 临界状态
    RECOVERY = auto()      # 恢复中


@dataclass
class CognitiveModule:
    """认知模块数据结构"""
    name: str
    importance: float  # 生态位价值 [0.0, 1.0]
    resource_usage: float  # 资源使用率 [0.0, 1.0]
    is_active: bool = True
    last_active_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"重要性必须在[0, 1]范围内: {self.importance}")
        if not 0.0 <= self.resource_usage <= 1.0:
            raise ValueError(f"资源使用率必须在[0, 1]范围内: {self.resource_usage}")


class AGIEcologicalResilienceFirewall:
    """
    AGI生态韧性防火墙
    
    实现基于生态动力学的系统自愈架构，包含临界慢化监测、
    断尾求生策略和网络重构功能。
    """
    
    def __init__(self, history_window: int = 10, csd_threshold: float = 0.75):
        """
        初始化防火墙
        
        Args:
            history_window: 历史数据窗口大小
            csd_threshold: 临界慢化阈值
        """
        self.modules: Dict[str, CognitiveModule] = {}
        self.seed_bank: List[str] = []  # 土壤种子库
        self.system_resource_usage: float = 0.0
        self.history_window = history_window
        self.csd_threshold = csd_threshold
        
        # 用于临界慢化计算的历史数据
        self._resource_history: deque = deque(maxlen=history_window)
        self._variance_history: deque = deque(maxlen=history_window)
        
        # 系统状态
        self.current_state = SystemState.HEALTHY
        self.last_check_time = time.time()
        
        logger.info("AGI生态韧性防火墙初始化完成")
    
    def register_module(
        self, 
        name: str, 
        importance: float, 
        resource_usage: float,
        is_seed: bool = False
    ) -> None:
        """
        注册认知模块
        
        Args:
            name: 模块名称
            importance: 重要性评分 [0.0, 1.0]
            resource_usage: 资源使用率 [0.0, 1.0]
            is_seed: 是否为核心种子模块
        """
        try:
            module = CognitiveModule(
                name=name,
                importance=importance,
                resource_usage=resource_usage
            )
            self.modules[name] = module
            
            if is_seed:
                self.seed_bank.append(name)
                logger.info(f"核心种子模块已注册: {name}")
            else:
                logger.info(f"认知模块已注册: {name}")
                
        except ValueError as e:
            logger.error(f"模块注册失败: {e}")
            raise
    
    def _calculate_autocorrelation(self, data: List[float]) -> float:
        """
        计算时间序列的自相关系数(滞后1)
        
        Args:
            data: 时间序列数据
            
        Returns:
            自相关系数 [-1, 1]
        """
        if len(data) < 2:
            return 0.0
        
        n = len(data)
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        
        if variance == 0:
            return 0.0
        
        covariance = sum(
            (data[i] - mean) * (data[i - 1] - mean) 
            for i in range(1, n)
        ) / (n - 1)
        
        return covariance / variance
    
    def _calculate_variance_trend(self) -> float:
        """
        计算方差变化趋势
        
        Returns:
            方差变化率 (正值表示方差增大)
        """
        if len(self._variance_history) < 2:
            return 0.0
        
        current = self._variance_history[-1]
        previous = self._variance_history[-2]
        
        if previous == 0:
            return 0.0
        
        return (current - previous) / previous
    
    def monitor_system(self) -> SystemState:
        """
        监测系统状态，检测临界慢化指标
        
        Returns:
            当前系统状态
        """
        # 更新资源使用历史
        active_modules = [m for m in self.modules.values() if m.is_active]
        if not active_modules:
            logger.warning("没有活跃的认知模块")
            return SystemState.CRITICAL
        
        # 计算当前总资源使用率
        total_resource = sum(m.resource_usage for m in active_modules)
        self.system_resource_usage = total_resource / len(active_modules)
        self._resource_history.append(self.system_resource_usage)
        
        # 计算当前方差
        if len(self._resource_history) >= 2:
            current_variance = self._calculate_variance(list(self._resource_history))
            self._variance_history.append(current_variance)
        
        # 计算临界慢化指标
        autocorr = self._calculate_autocorrelation(list(self._resource_history))
        variance_trend = self._calculate_variance_trend()
        
        # 综合评估系统状态
        csd_indicator = (autocorr + variance_trend) / 2
        
        logger.debug(
            f"系统监测 - 资源使用率: {self.system_resource_usage:.3f}, "
            f"自相关系数: {autocorr:.3f}, 方差趋势: {variance_trend:.3f}, "
            f"CSD指标: {csd_indicator:.3f}"
        )
        
        # 状态判断
        if csd_indicator > self.csd_threshold:
            self.current_state = SystemState.CRITICAL
            logger.warning(f"系统进入临界状态! CSD指标: {csd_indicator:.3f}")
        elif csd_indicator > self.csd_threshold * 0.7:
            self.current_state = SystemState.WARNING
            logger.info(f"系统警告状态 - CSD指标: {csd_indicator:.3f}")
        else:
            self.current_state = SystemState.HEALTHY
        
        return self.current_state
    
    def _calculate_variance(self, data: List[float]) -> float:
        """计算方差"""
        if not data:
            return 0.0
        mean = sum(data) / len(data)
        return sum((x - mean) ** 2 for x in data) / len(data)
    
    def execute_autotomy_strategy(self, target_resource: float = 0.6) -> int:
        """
        执行断尾求生策略
        
        主动丢弃非核心功能模块以释放资源
        
        Args:
            target_resource: 目标资源使用率
            
        Returns:
            丢弃的模块数量
        """
        if self.current_state != SystemState.CRITICAL:
            logger.info("系统未处于临界状态，无需执行断尾策略")
            return 0
        
        logger.warning("启动断尾求生策略...")
        
        # 获取可丢弃的模块(排除种子模块)
        disposable_modules = [
            m for m in self.modules.values() 
            if m.is_active and m.name not in self.seed_bank
        ]
        
        # 按重要性升序排序(先丢弃低重要性模块)
        disposable_modules.sort(key=lambda x: x.importance)
        
        dropped_count = 0
        current_resource = self.system_resource_usage
        
        for module in disposable_modules:
            if current_resource <= target_resource:
                break
            
            # 执行丢弃
            module.is_active = False
            current_resource -= module.resource_usage
            dropped_count += 1
            
            logger.warning(
                f"已丢弃模块: {module.name} (重要性: {module.importance:.2f}, "
                f"释放资源: {module.resource_usage:.2f})"
            )
        
        self.current_state = SystemState.RECOVERY
        logger.info(
            f"断尾策略执行完成，共丢弃 {dropped_count} 个模块，"
            f"当前资源使用率: {current_resource:.2f}"
        )
        
        return dropped_count
    
    def reconstruct_network(self) -> int:
        """
        利用土壤种子库重构认知网络
        
        Returns:
            成功恢复的模块数量
        """
        if self.current_state != SystemState.RECOVERY:
            logger.info("系统未处于恢复状态，无需重构")
            return 0
        
        logger.info("开始从种子库重构认知网络...")
        
        recovered_count = 0
        
        # 恢复种子模块
        for seed_name in self.seed_bank:
            if seed_name in self.modules:
                module = self.modules[seed_name]
                if not module.is_active:
                    module.is_active = True
                    module.last_active_time = time.time()
                    recovered_count += 1
                    logger.info(f"种子模块已恢复: {seed_name}")
        
        # 尝试恢复部分高重要性模块
        inactive_modules = [
            m for m in self.modules.values()
            if not m.is_active and m.name not in self.seed_bank
        ]
        inactive_modules.sort(key=lambda x: x.importance, reverse=True)
        
        # 简单的资源检查
        for module in inactive_modules[:3]:  # 尝试恢复前3个
            if self.system_resource_usage + module.resource_usage < 0.8:
                module.is_active = True
                module.last_active_time = time.time()
                recovered_count += 1
                logger.info(f"高重要性模块已恢复: {module.name}")
        
        self.current_state = SystemState.HEALTHY
        logger.info(f"网络重构完成，共恢复 {recovered_count} 个模块")
        
        return recovered_count
    
    def get_system_report(self) -> Dict:
        """
        获取系统状态报告
        
        Returns:
            包含系统状态的字典
        """
        active_modules = [m.name for m in self.modules.values() if m.is_active]
        inactive_modules = [m.name for m in self.modules.values() if not m.is_active]
        
        return {
            "state": self.current_state.name,
            "total_modules": len(self.modules),
            "active_modules": len(active_modules),
            "inactive_modules": len(inactive_modules),
            "seed_bank_size": len(self.seed_bank),
            "resource_usage": round(self.system_resource_usage, 3),
            "active_module_list": active_modules,
            "seed_bank": self.seed_bank
        }


# 使用示例
if __name__ == "__main__":
    # 创建防火墙实例
    firewall = AGIEcologicalResilienceFirewall(history_window=8, csd_threshold=0.65)
    
    # 注册核心种子模块(不可丢弃)
    firewall.register_module("core_reasoning", 0.95, 0.25, is_seed=True)
    firewall.register_module("value_alignment", 0.98, 0.15, is_seed=True)
    firewall.register_module("memory_management", 0.90, 0.20, is_seed=True)
    
    # 注册普通模块
    firewall.register_module("visual_perception", 0.85, 0.30)
    firewall.register_module("language_generation", 0.80, 0.25)
    firewall.register_module("chitchat_bot", 0.30, 0.10)
    firewall.register_module("creative_writing", 0.40, 0.15)
    firewall.register_module("game_player", 0.25, 0.20)
    
    # 模拟系统监测
    print("\n=== 系统监测 ===")
    for i in range(5):
        state = firewall.monitor_system()
        print(f"监测周期 {i+1}: {state.name}")
        time.sleep(0.1)
    
    # 模拟临界状态
    print("\n=== 模拟系统压力 ===")
    # 增加资源使用历史波动
    for _ in range(8):
        firewall._resource_history.append(0.7 + (time.time() % 1) * 0.3)
        firewall._variance_history.append(0.1 + (time.time() % 1) * 0.2)
    
    state = firewall.monitor_system()
    print(f"当前状态: {state.name}")
    
    # 执行断尾策略
    if state == SystemState.CRITICAL:
        print("\n=== 执行断尾求生策略 ===")
        dropped = firewall.execute_autotomy_strategy(target_resource=0.5)
        print(f"丢弃了 {dropped} 个模块")
    
    # 查看系统报告
    print("\n=== 系统报告 ===")
    report = firewall.get_system_report()
    for key, value in report.items():
        print(f"{key}: {value}")
    
    # 执行网络重构
    print("\n=== 执行网络重构 ===")
    recovered = firewall.reconstruct_network()
    print(f"恢复了 {recovered} 个模块")
    
    # 最终状态
    print("\n=== 最终状态 ===")
    final_report = firewall.get_system_report()
    print(f"系统状态: {final_report['state']}")
    print(f"活跃模块: {final_report['active_modules']}")