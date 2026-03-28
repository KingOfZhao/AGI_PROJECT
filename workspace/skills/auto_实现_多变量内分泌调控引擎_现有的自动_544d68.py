"""
多变量内分泌调控引擎

该模块实现了一个仿生的自动伸缩控制系统，模拟生物内分泌系统的多激素协同调节机制。
系统综合延迟、错误率、成本、业务优先级等多种'激素水平'，通过多目标优化算法
输出精细化的控制指令，实现极高压力下的系统生存优先策略。

Author: AGI System
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EndocrineEngine")


class ServiceTier(Enum):
    """服务层级枚举"""
    CORE = 1       # 核心业务（心脑）
    STANDARD = 2   # 标准业务
    PERIPHERAL = 3 # 末梢业务（可牺牲）


@dataclass
class SystemMetrics:
    """
    系统指标数据结构（模拟'激素水平'）
    
    Attributes:
        latency_ms: 平均响应延迟（毫秒）
        error_rate: 错误率（0.0-1.0）
        cpu_usage: CPU使用率（0.0-1.0）
        memory_usage: 内存使用率（0.0-1.0）
        cost_burn_rate: 成本消耗速率（$/hour）
        timestamp: 时间戳
    """
    latency_ms: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    cost_burn_rate: float
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.error_rate <= 1:
            raise ValueError(f"错误率必须在0-1之间，当前: {self.error_rate}")
        if not 0 <= self.cpu_usage <= 1:
            raise ValueError(f"CPU使用率必须在0-1之间，当前: {self.cpu_usage}")
        if not 0 <= self.memory_usage <= 1:
            raise ValueError(f"内存使用率必须在0-1之间，当前: {self.memory_usage}")
        if self.latency_ms < 0:
            raise ValueError(f"延迟不能为负数，当前: {self.latency_ms}")
        if self.cost_burn_rate < 0:
            raise ValueError(f"成本消耗速率不能为负数，当前: {self.cost_burn_rate}")


@dataclass
class ServiceConfig:
    """
    服务配置数据结构
    
    Attributes:
        name: 服务名称
        tier: 服务层级
        priority: 优先级权重（0-100）
        min_replicas: 最小副本数
        max_replicas: 最大副本数
        current_replicas: 当前副本数
    """
    name: str
    tier: ServiceTier
    priority: int
    min_replicas: int
    max_replicas: int
    current_replicas: int
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.priority <= 100:
            raise ValueError(f"优先级必须在0-100之间，当前: {self.priority}")
        if self.min_replicas < 0:
            raise ValueError(f"最小副本数不能为负数，当前: {self.min_replicas}")
        if self.max_replicas < self.min_replicas:
            raise ValueError(f"最大副本数({self.max_replicas})不能小于最小副本数({self.min_replicas})")
        if not self.min_replicas <= self.current_replicas <= self.max_replicas:
            raise ValueError(
                f"当前副本数({self.current_replicas})必须在"
                f"[{self.min_replicas}, {self.max_replicas}]范围内"
            )


class EndocrineRegulationEngine:
    """
    多变量内分泌调控引擎
    
    通过模拟生物内分泌系统的多激素协同调节，实现精细化的自动伸缩控制。
    
    Example:
        >>> engine = EndocrineRegulationEngine(cost_budget=100.0)
        >>> metrics = SystemMetrics(
        ...     latency_ms=250, error_rate=0.05, cpu_usage=0.9,
        ...     memory_usage=0.8, cost_burn_rate=120
        ... )
        >>> services = [
        ...     ServiceConfig("payment", ServiceTier.CORE, 95, 3, 20, 10),
        ...     ServiceConfig("recommendation", ServiceTier.PERIPHERAL, 30, 1, 10, 5)
        ... ]
        >>> decisions = engine.regulate(metrics, services)
        >>> for decision in decisions:
        ...     print(decision)
    """
    
    # 激素阈值常量（模拟生物内分泌系统）
    CORTISOL_THRESHOLD_HIGH = 0.75      # 皮质醇（压力激素）高阈值
    CORTISOL_THRESHOLD_CRITICAL = 0.9   # 皮质醇危急阈值
    ADRENALINE_THRESHOLD = 0.85         # 肾上腺素阈值（成本压力）
    RECOVERY_THRESHOLD = 0.5            # 恢复阈值
    
    def __init__(self, cost_budget: float, emergency_mode_threshold: float = 0.9):
        """
        初始化内分泌调控引擎
        
        Args:
            cost_budget: 成本预算上限（$/hour）
            emergency_mode_threshold: 进入紧急模式的综合压力阈值
            
        Raises:
            ValueError: 当参数不合法时抛出
        """
        if cost_budget <= 0:
            raise ValueError(f"成本预算必须大于0，当前: {cost_budget}")
        if not 0 < emergency_mode_threshold < 1:
            raise ValueError(
                f"紧急模式阈值必须在(0,1)区间，当前: {emergency_mode_threshold}"
            )
        
        self.cost_budget = cost_budget
        self.emergency_mode_threshold = emergency_mode_threshold
        self._regulation_history: List[Dict] = []
        
        logger.info(
            f"内分泌调控引擎初始化完成 | 成本预算: ${cost_budget}/hour | "
            f"紧急模式阈值: {emergency_mode_threshold}"
        )
    
    def _calculate_stress_hormone(self, metrics: SystemMetrics) -> float:
        """
        计算系统综合压力激素水平（皮质醇）
        
        综合考虑延迟、错误率、资源使用率等因素，计算系统的整体压力水平。
        
        Args:
            metrics: 系统指标
            
        Returns:
            压力激素水平（0.0-1.0+）
            
        Note:
            - < 0.5: 放松状态
            - 0.5-0.75: 轻度压力
            - 0.75-0.9: 高度压力
            - > 0.9: 危急状态
        """
        # 各指标的权重
        latency_weight = 0.25
        error_weight = 0.35
        cpu_weight = 0.25
        memory_weight = 0.15
        
        # 延迟归一化（假设500ms为高压力基线）
        latency_score = min(metrics.latency_ms / 500.0, 1.5)
        
        # 错误率归一化（5%为高压力基线）
        error_score = min(metrics.error_rate / 0.05, 2.0)
        
        # 资源使用率
        resource_score = (
            metrics.cpu_usage * cpu_weight + 
            metrics.memory_usage * memory_weight
        ) / (cpu_weight + memory_weight)
        
        # 综合压力计算
        cortisol = (
            latency_score * latency_weight +
            error_score * error_weight +
            resource_score * (latency_weight + error_weight)
        )
        
        logger.debug(
            f"压力激素计算 | 延迟分数: {latency_score:.2f} | "
            f"错误分数: {error_score:.2f} | 资源分数: {resource_score:.2f} | "
            f"综合皮质醇: {cortisol:.3f}"
        )
        
        return cortisol
    
    def _calculate_cost_adrenaline(self, metrics: SystemMetrics) -> float:
        """
        计算成本肾上腺素水平（成本压力）
        
        当成本消耗接近或超过预算时，肾上腺素水平升高，
        触发成本节约机制。
        
        Args:
            metrics: 系统指标
            
        Returns:
            成本肾上腺素水平（0.0-1.0+）
        """
        if self.cost_budget <= 0:
            return 0.0
        
        burn_ratio = metrics.cost_burn_rate / self.cost_budget
        
        # 使用指数函数放大超支时的压力
        if burn_ratio > 1.0:
            adrenaline = 1.0 + (burn_ratio - 1.0) * 2.0
        else:
            adrenaline = burn_ratio ** 0.5
        
        logger.debug(
            f"成本肾上腺素 | 消耗率: {burn_ratio:.2%} | "
            f"肾上腺素水平: {adrenaline:.3f}"
        )
        
        return adrenaline
    
    def _optimize_allocation(
        self,
        services: List[ServiceConfig],
        cortisol: float,
        adrenaline: float,
        metrics: SystemMetrics
    ) -> List[Tuple[str, int, str]]:
        """
        多目标优化分配算法（受体结合算法）
        
        根据压力激素水平和服务优先级，计算每个服务的最优副本数。
        
        Args:
            services: 服务配置列表
            cortisol: 皮质醇水平
            adrenaline: 肾上腺素水平
            metrics: 系统指标
            
        Returns:
            决策列表，每个元素为(服务名, 目标副本数, 决策原因)元组
        """
        decisions = []
        
        # 判断系统状态
        is_critical = cortisol > self.CORTISOL_THRESHOLD_CRITICAL
        is_high_pressure = cortisol > self.CORTISOL_THRESHOLD_HIGH
        is_cost_pressure = adrenaline > self.ADRENALINE_THRESHOLD
        is_emergency = is_critical or (is_high_pressure and is_cost_pressure)
        
        logger.info(
            f"系统状态评估 | 皮质醇: {cortisol:.2f} | 肾上腺素: {adrenaline:.2f} | "
            f"危急: {is_critical} | 高压: {is_high_pressure} | "
            f"成本压力: {is_cost_pressure} | 紧急模式: {is_emergency}"
        )
        
        for service in services:
            target_replicas = service.current_replicas
            reason = "维持现状"
            
            # 紧急模式：生存优先策略
            if is_emergency:
                if service.tier == ServiceTier.CORE:
                    # 核心业务扩容保护
                    scale_factor = 1.3 if is_critical else 1.15
                    target_replicas = min(
                        int(service.current_replicas * scale_factor),
                        service.max_replicas
                    )
                    reason = f"紧急保护-核心业务扩容{scale_factor:.0%}"
                    
                elif service.tier == ServiceTier.PERIPHERAL:
                    # 末梢业务降级（血管收缩）
                    if is_cost_pressure:
                        target_replicas = max(
                            service.min_replicas,
                            int(service.current_replicas * 0.5)
                        )
                        reason = "紧急降级-末梢业务收缩(成本压力)"
                    else:
                        target_replicas = max(
                            service.min_replicas,
                            int(service.current_replicas * 0.7)
                        )
                        reason = "紧急降级-末梢业务收缩(资源压力)"
                        
                else:  # STANDARD
                    # 标准业务根据优先级调整
                    if service.priority > 70:
                        target_replicas = min(
                            service.current_replicas + 1,
                            service.max_replicas
                        )
                        reason = "紧急保护-高优先级标准业务"
                    else:
                        target_replicas = max(
                            service.min_replicas,
                            service.current_replicas - 1
                        )
                        reason = "紧急收缩-低优先级标准业务"
            
            # 正常调控模式
            elif is_high_pressure:
                if service.tier == ServiceTier.CORE:
                    target_replicas = min(
                        service.current_replicas + 2,
                        service.max_replicas
                    )
                    reason = "高压保护-核心业务预防性扩容"
                    
            elif is_cost_pressure:
                if service.tier == ServiceTier.PERIPHERAL:
                    target_replicas = max(
                        service.min_replicas,
                        service.current_replicas - 1
                    )
                    reason = "成本控制-末梢业务收缩"
            
            # 恢复模式
            elif cortisol < self.RECOVERY_THRESHOLD and not is_cost_pressure:
                if service.tier != ServiceTier.CORE:
                    if service.current_replicas < service.max_replicas:
                        target_replicas = min(
                            service.current_replicas + 1,
                            service.max_replicas
                        )
                        reason = "系统恢复-业务扩容"
            
            # 确保在合法范围内
            target_replicas = max(
                service.min_replicas,
                min(target_replicas, service.max_replicas)
            )
            
            decisions.append((service.name, target_replicas, reason))
            
            logger.info(
                f"服务决策 | {service.name}({service.tier.name}) | "
                f"当前: {service.current_replicas} -> 目标: {target_replicas} | "
                f"原因: {reason}"
            )
        
        return decisions
    
    def regulate(
        self,
        metrics: SystemMetrics,
        services: List[ServiceConfig]
    ) -> List[Dict]:
        """
        执行内分泌调控（主控制函数）
        
        综合分析系统指标，计算激素水平，并生成调控决策。
        
        Args:
            metrics: 系统指标
            services: 服务配置列表
            
        Returns:
            调控决策列表，每个决策包含服务名、目标副本数、原因等信息
            
        Raises:
            ValueError: 当输入数据不合法时抛出
            RuntimeError: 当调控过程发生严重错误时抛出
        """
        try:
            # 输入验证
            if not services:
                raise ValueError("服务列表不能为空")
            
            logger.info("=" * 60)
            logger.info("开始内分泌调控周期")
            logger.info(
                f"输入指标 | 延迟: {metrics.latency_ms}ms | "
                f"错误率: {metrics.error_rate:.2%} | "
                f"CPU: {metrics.cpu_usage:.1%} | "
                f"内存: {metrics.memory_usage:.1%} | "
                f"成本消耗: ${metrics.cost_burn_rate}/hour"
            )
            
            # 计算激素水平
            cortisol = self._calculate_stress_hormone(metrics)
            adrenaline = self._calculate_cost_adrenaline(metrics)
            
            # 执行多目标优化
            decisions = self._optimize_allocation(
                services, cortisol, adrenaline, metrics
            )
            
            # 构建输出结果
            results = []
            for service_name, target_replicas, reason in decisions:
                # 找到对应的服务配置
                service = next(s for s in services if s.name == service_name)
                
                decision = {
                    "service_name": service_name,
                    "service_tier": service.tier.name,
                    "current_replicas": service.current_replicas,
                    "target_replicas": target_replicas,
                    "scale_delta": target_replicas - service.current_replicas,
                    "reason": reason,
                    "timestamp": time.time(),
                    "hormone_levels": {
                        "cortisol": round(cortisol, 3),
                        "adrenaline": round(adrenaline, 3)
                    }
                }
                results.append(decision)
            
            # 记录调控历史
            self._regulation_history.append({
                "timestamp": time.time(),
                "metrics": metrics,
                "cortisol": cortisol,
                "adrenaline": adrenaline,
                "decisions": results
            })
            
            # 保持历史记录在合理大小
            if len(self._regulation_history) > 1000:
                self._regulation_history = self._regulation_history[-500:]
            
            logger.info(f"调控周期完成 | 生成 {len(results)} 个决策")
            logger.info("=" * 60)
            
            return results
            
        except ValueError as e:
            logger.error(f"输入验证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"调控过程发生严重错误: {e}", exc_info=True)
            raise RuntimeError(f"内分泌调控失败: {e}") from e
    
    def get_regulation_summary(self) -> Dict:
        """
        获取调控历史摘要
        
        Returns:
            包含调控统计信息的字典
        """
        if not self._regulation_history:
            return {"total_regulations": 0}
        
        total = len(self._regulation_history)
        avg_cortisol = sum(
            r["cortisol"] for r in self._regulation_history
        ) / total
        avg_adrenaline = sum(
            r["adrenaline"] for r in self._regulation_history
        ) / total
        
        return {
            "total_regulations": total,
            "average_cortisol": round(avg_cortisol, 3),
            "average_adrenaline": round(avg_adrenaline, 3),
            "last_regulation": self._regulation_history[-1]["timestamp"]
        }


# 使用示例
if __name__ == "__main__":
    """
    使用示例：模拟多变量内分泌调控引擎的工作流程
    
    输入格式:
        - SystemMetrics: 包含延迟、错误率、CPU、内存、成本消耗等指标
        - List[ServiceConfig]: 服务配置列表，包含名称、层级、优先级等信息
    
    输出格式:
        - List[Dict]: 每个服务的调控决策，包含目标副本数、调整原因等
    """
    
    print("=" * 70)
    print("多变量内分泌调控引擎 - 演示")
    print("=" * 70)
    
    # 1. 初始化引擎（成本预算$100/小时）
    engine = EndocrineRegulationEngine(cost_budget=100.0)
    
    # 2. 定义服务配置（模拟不同层级的业务）
    services = [
        ServiceConfig(
            name="payment-service",
            tier=ServiceTier.CORE,
            priority=95,
            min_replicas=3,
            max_replicas=20,
            current_replicas=8
        ),
        ServiceConfig(
            name="user-auth",
            tier=ServiceTier.CORE,
            priority=90,
            min_replicas=2,
            max_replicas=15,
            current_replicas=5
        ),
        ServiceConfig(
            name="product-catalog",
            tier=ServiceTier.STANDARD,
            priority=60,
            min_replicas=2,
            max_replicas=10,
            current_replicas=4
        ),
        ServiceConfig(
            name="recommendation-engine",
            tier=ServiceTier.PERIPHERAL,
            priority=30,
            min_replicas=1,
            max_replicas=8,
            current_replicas=4
        ),
        ServiceConfig(
            name="analytics-logger",
            tier=ServiceTier.PERIPHERAL,
            priority=20,
            min_replicas=1,
            max_replicas=5,
            current_replicas=3
        ),
    ]
    
    # 3. 场景一：高压力+成本超支（危急状态）
    print("\n【场景一】高延迟 + 高错误率 + 成本超支（危急状态）")
    print("-" * 70)
    
    critical_metrics = SystemMetrics(
        latency_ms=450,        # 高延迟
        error_rate=0.08,       # 8%错误率
        cpu_usage=0.92,        # CPU 92%
        memory_usage=0.88,     # 内存 88%
        cost_burn_rate=130.0   # 成本超支30%
    )
    
    decisions = engine.regulate(critical_metrics, services)
    
    print("\n调控决策结果:")
    for d in decisions:
        delta_str = f"+{d['scale_delta']}" if d['scale_delta'] > 0 else str(d['scale_delta'])
        print(
            f"  {d['service_name']:25s} | {d['service_tier']:10s} | "
            f"副本: {d['current_replicas']:2d} -> {d['target_replicas']:2d} ({delta_str:>3s}) | "
            f"{d['reason']}"
        )
    
    # 4. 场景二：正常运行状态
    print("\n【场景二】正常运行状态")
    print("-" * 70)
    
    # 更新服务当前副本数（基于上次决策）
    for d in decisions:
        for s in services:
            if s.name == d["service_name"]:
                s.current_replicas = d["target_replicas"]
    
    normal_metrics = SystemMetrics(
        latency_ms=80,
        error_rate=0.005,
        cpu_usage=0.45,
        memory_usage=0.50,
        cost_burn_rate=65.0
    )
    
    decisions = engine.regulate(normal_metrics, services)
    
    print("\n调控决策结果:")
    for d in decisions:
        delta_str = f"+{d['scale_delta']}" if d['scale_delta'] > 0 else str(d['scale_delta'])
        print(
            f"  {d['service_name']:25s} | {d['service_tier']:10s} | "
            f"副本: {d['current_replicas']:2d} -> {d['target_replicas']:2d} ({delta_str:>3s}) | "
            f"{d['reason']}"
        )
    
    # 5. 输出调控摘要
    print("\n" + "=" * 70)
    print("调控历史摘要:")
    summary = engine.get_regulation_summary()
    print(f"  总调控次数: {summary['total_regulations']}")
    print(f"  平均皮质醇水平: {summary['average_cortisol']:.3f}")
    print(f"  平均肾上腺素水平: {summary['average_adrenaline']:.3f}")
    print("=" * 70)