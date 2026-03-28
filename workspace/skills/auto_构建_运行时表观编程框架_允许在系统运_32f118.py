"""
运行时表观编程框架

该模块实现了一个受生物表观遗传学启发的运行时行为修饰系统。
通过注入'修饰信号'（如配置变更、规则脚本）来改变系统的核心行为模式，
而无需重启服务或重新部署镜像。

核心机制：
- 甲基化: 暂时沉默或降级非核心功能
- 去甲基化: 恢复被修饰的功能
- 修饰信号: 控制行为模式的配置指令

应用场景：
- 流量洪峰时动态降低算法复杂度
- 根据系统负载调整功能开关
- A/B测试不同行为模式
- 紧急情况下快速降级非核心服务
"""

import time
import json
import logging
import threading
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EpigeneticFramework")


class MethylationLevel(Enum):
    """甲基化级别枚举"""
    NONE = 0       # 无修饰，功能完整
    LIGHT = 1      # 轻度修饰，轻微降级
    MODERATE = 2   # 中度修饰，明显降级
    HEAVY = 3      # 重度修饰，基本禁用
    COMPLETE = 4   # 完全甲基化，功能沉默


@dataclass
class ModificationSignal:
    """修饰信号数据结构"""
    signal_id: str
    target_pattern: str          # 目标功能匹配模式
    methylation_level: MethylationLevel
    duration_seconds: Optional[int] = None  # 持续时间，None表示永久
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "signal_id": self.signal_id,
            "target_pattern": self.target_pattern,
            "methylation_level": self.methylation_level.name,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModificationSignal':
        """从字典创建实例"""
        return cls(
            signal_id=data["signal_id"],
            target_pattern=data["target_pattern"],
            methylation_level=MethylationLevel[data["methylation_level"]],
            duration_seconds=data.get("duration_seconds"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        )


class EpigeneticController:
    """
    表观遗传控制器 - 核心控制类
    
    负责管理修饰信号的注册、存储、查询和自动过期清理。
    线程安全，支持高并发访问。
    
    输入格式:
        - register_signal(): ModificationSignal 对象
        - query_methylation(): 功能名称字符串
        
    输出格式:
        - query_methylation(): MethylationLevel 枚举值
        - get_active_signals(): List[ModificationSignal]
    """
    
    def __init__(self, cleanup_interval: int = 60):
        """
        初始化控制器
        
        Args:
            cleanup_interval: 自动清理过期信号的间隔（秒）
        """
        self._signals: Dict[str, ModificationSignal] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = cleanup_interval
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 启动后台清理线程
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """启动后台清理线程"""
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_expired_signals,
            daemon=True,
            name="EpigeneticCleanup"
        )
        self._cleanup_thread.start()
        logger.info("表观遗传控制器已初始化，清理线程已启动")
    
    def _cleanup_expired_signals(self) -> None:
        """后台清理过期信号的线程函数"""
        while self._running:
            time.sleep(self._cleanup_interval)
            self.cleanup_expired()
    
    def cleanup_expired(self) -> int:
        """
        清理所有过期的修饰信号
        
        Returns:
            清理的信号数量
        """
        with self._lock:
            now = datetime.now()
            expired_ids = []
            
            for signal_id, signal in self._signals.items():
                if signal.duration_seconds is not None:
                    expiry_time = signal.created_at + timedelta(seconds=signal.duration_seconds)
                    if now > expiry_time:
                        expired_ids.append(signal_id)
            
            for signal_id in expired_ids:
                del self._signals[signal_id]
                logger.info(f"信号 {signal_id} 已过期并移除")
            
            if expired_ids:
                logger.info(f"清理完成，共移除 {len(expired_ids)} 个过期信号")
            
            return len(expired_ids)
    
    def register_signal(self, signal: ModificationSignal) -> bool:
        """
        注册新的修饰信号
        
        Args:
            signal: 修饰信号对象
            
        Returns:
            注册是否成功
            
        Raises:
            ValueError: 当信号数据无效时
        """
        # 数据验证
        if not signal.signal_id or not signal.signal_id.strip():
            raise ValueError("信号ID不能为空")
        
        if not signal.target_pattern or not signal.target_pattern.strip():
            raise ValueError("目标模式不能为空")
        
        if signal.duration_seconds is not None and signal.duration_seconds <= 0:
            raise ValueError("持续时间必须为正整数或None")
        
        with self._lock:
            self._signals[signal.signal_id] = signal
            logger.info(
                f"已注册修饰信号: {signal.signal_id} -> {signal.target_pattern} "
                f"(级别: {signal.methylation_level.name}, 持续: {signal.duration_seconds}s)"
            )
            return True
    
    def unregister_signal(self, signal_id: str) -> bool:
        """
        注销修饰信号
        
        Args:
            signal_id: 信号ID
            
        Returns:
            是否成功注销
        """
        with self._lock:
            if signal_id in self._signals:
                del self._signals[signal_id]
                logger.info(f"已注销修饰信号: {signal_id}")
                return True
            return False
    
    def query_methylation(self, function_name: str) -> MethylationLevel:
        """
        查询指定功能的甲基化级别
        
        Args:
            function_name: 功能名称
            
        Returns:
            该功能当前的最高甲基化级别
        """
        with self._lock:
            max_level = MethylationLevel.NONE
            
            for signal in self._signals.values():
                # 简单的模式匹配：支持通配符 * 和 ?
                if self._match_pattern(signal.target_pattern, function_name):
                    if signal.methylation_level.value > max_level.value:
                        max_level = signal.methylation_level
            
            return max_level
    
    def _match_pattern(self, pattern: str, text: str) -> bool:
        """
        简单的模式匹配辅助函数
        
        支持 * (任意字符) 和 ? (单个字符) 通配符
        """
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
    
    def get_active_signals(self) -> List[ModificationSignal]:
        """获取所有活跃的修饰信号"""
        with self._lock:
            return list(self._signals.values())
    
    def get_signal_by_id(self, signal_id: str) -> Optional[ModificationSignal]:
        """根据ID获取信号"""
        with self._lock:
            return self._signals.get(signal_id)
    
    def export_signals(self) -> str:
        """导出所有信号为JSON字符串"""
        with self._lock:
            data = [s.to_dict() for s in self._signals.values()]
            return json.dumps(data, indent=2, ensure_ascii=False)
    
    def import_signals(self, json_str: str) -> int:
        """
        从JSON字符串导入信号
        
        Returns:
            成功导入的信号数量
        """
        data = json.loads(json_str)
        count = 0
        for item in data:
            try:
                signal = ModificationSignal.from_dict(item)
                self.register_signal(signal)
                count += 1
            except Exception as e:
                logger.error(f"导入信号失败: {item}, 错误: {e}")
        return count
    
    def shutdown(self) -> None:
        """关闭控制器"""
        self._running = False
        logger.info("表观遗传控制器已关闭")


def epigenetic_modifier(
    controller: EpigeneticController,
    function_name: str,
    fallback_behavior: Optional[Callable] = None
) -> Callable:
    """
    表观遗传修饰器工厂函数
    
    用于修饰函数，使其能够根据甲基化级别动态调整行为。
    
    Args:
        controller: 表观遗传控制器实例
        function_name: 功能名称（用于查询甲基化级别）
        fallback_behavior: 降级时的替代行为
        
    Returns:
        装饰器函数
        
    使用示例:
        >>> controller = EpigeneticController()
        >>> @epigenetic_modifier(controller, "recommendation_engine")
        ... def complex_recommendation(user_id: str) -> List[str]:
        ...     # 复杂推荐算法
        ...     return ["item1", "item2", "item3"]
        ...
        >>> result = complex_recommendation("user123")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            methylation = controller.query_methylation(function_name)
            
            if methylation == MethylationLevel.COMPLETE:
                logger.warning(f"功能 {function_name} 已完全甲基化（沉默）")
                if fallback_behavior:
                    return fallback_behavior(*args, **kwargs)
                return None
            
            if methylation == MethylationLevel.HEAVY:
                logger.info(f"功能 {function_name} 重度甲基化，执行降级")
                if fallback_behavior:
                    return fallback_behavior(*args, **kwargs)
                # 返回简化结果
                return _get_simplified_result(func, *args, **kwargs)
            
            if methylation == MethylationLevel.MODERATE:
                logger.debug(f"功能 {function_name} 中度甲基化")
                # 可以在这里实现复杂度的中等降级
                return _execute_with_reduced_complexity(func, methylation, *args, **kwargs)
            
            if methylation == MethylationLevel.LIGHT:
                logger.debug(f"功能 {function_name} 轻度甲基化")
                # 轻微降级，基本保持原有逻辑
                return func(*args, **kwargs)
            
            # 无甲基化，正常执行
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def _get_simplified_result(func: Callable, *args, **kwargs) -> Any:
    """
    辅助函数：获取简化结果
    
    根据函数返回类型提示返回适当的简化默认值
    """
    # 简化实现：返回常见类型的空值
    return []  # 假设大多数情况返回列表


def _execute_with_reduced_complexity(
    func: Callable,
    level: MethylationLevel,
    *args,
    **kwargs
) -> Any:
    """
    辅助函数：以降低的复杂度执行函数
    
    可以通过修改kwargs来传递复杂度参数
    """
    # 在实际实现中，可以通过参数控制算法复杂度
    kwargs['_complexity_level'] = level.value
    return func(*args, **kwargs)


class AdaptiveFunction:
    """
    自适应函数类 - 支持多级降级的函数包装器
    
    根据甲基化级别选择不同的实现策略
    """
    
    def __init__(
        self,
        controller: EpigeneticController,
        function_name: str,
        strategies: Dict[MethylationLevel, Callable]
    ):
        """
        初始化自适应函数
        
        Args:
            controller: 控制器实例
            function_name: 功能名称
            strategies: 各甲基化级别对应的实现策略
        """
        self.controller = controller
        self.function_name = function_name
        self.strategies = strategies
        
        # 验证策略完整性
        if MethylationLevel.NONE not in strategies:
            raise ValueError("必须提供 NONE 级别的默认策略")
    
    def __call__(self, *args, **kwargs) -> Any:
        """执行时根据当前甲基化级别选择策略"""
        methylation = self.controller.query_methylation(self.function_name)
        
        # 查找最适合的策略（当前级别或更高级别）
        strategy = self._find_best_strategy(methylation)
        
        logger.debug(
            f"执行自适应函数 {self.function_name}, "
            f"甲基化级别: {methylation.name}, 策略级别: {strategy[0].name}"
        )
        
        return strategy[1](*args, **kwargs)
    
    def _find_best_strategy(self, level: MethylationLevel) -> Tuple[MethylationLevel, Callable]:
        """查找最适合当前级别的策略"""
        # 从当前级别开始向上查找
        for l in MethylationLevel:
            if l.value >= level.value and l in self.strategies:
                return (l, self.strategies[l])
        
        # 回退到NONE级别
        return (MethylationLevel.NONE, self.strategies[MethylationLevel.NONE])


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建控制器
    controller = EpigeneticController(cleanup_interval=30)
    
    try:
        # 示例1：使用装饰器
        @epigenetic_modifier(controller, "data_processing")
        def process_data(data: List[int], complexity_level: int = 0) -> Dict[str, Any]:
            """数据处理函数示例"""
            if complexity_level >= 2:
                # 降级模式：简单统计
                return {"count": len(data), "mode": "simplified"}
            else:
                # 正常模式：完整分析
                return {
                    "count": len(data),
                    "sum": sum(data),
                    "avg": sum(data) / len(data) if data else 0,
                    "max": max(data) if data else None,
                    "mode": "full"
                }
        
        # 测试正常执行
        result = process_data([1, 2, 3, 4, 5])
        print(f"正常执行结果: {result}")
        
        # 注册中度甲基化信号
        signal = ModificationSignal(
            signal_id="stress_test_001",
            target_pattern="data_*",
            methylation_level=MethylationLevel.MODERATE,
            duration_seconds=60,
            metadata={"reason": "流量洪峰测试"}
        )
        controller.register_signal(signal)
        
        # 测试降级执行
        result = process_data([1, 2, 3, 4, 5])
        print(f"降级执行结果: {result}")
        
        # 示例2：使用自适应函数
        def full_recommendation(user_id: str) -> List[str]:
            return [f"premium_item_{i}" for i in range(10)]
        
        def basic_recommendation(user_id: str) -> List[str]:
            return [f"basic_item_{i}" for i in range(3)]
        
        def minimal_recommendation(user_id: str) -> List[str]:
            return ["default_item"]
        
        adaptive_rec = AdaptiveFunction(
            controller,
            "recommendation_engine",
            {
                MethylationLevel.NONE: full_recommendation,
                MethylationLevel.LIGHT: full_recommendation,
                MethylationLevel.MODERATE: basic_recommendation,
                MethylationLevel.HEAVY: minimal_recommendation,
                MethylationLevel.COMPLETE: lambda x: []
            }
        )
        
        # 测试自适应推荐
        print(f"推荐结果: {adaptive_rec('user123')}")
        
        # 导出信号配置
        print("\n当前活跃信号:")
        print(controller.export_signals())
        
    finally:
        controller.shutdown()