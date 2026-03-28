"""
模块名称: auto_真实节点_的时变环境生存测试_针对与现_527eed
描述: 本模块实现了针对“真实节点”的时变环境生存测试机制（微实践）。
      它模拟或管理与现实物理世界交互的节点（如IoT传感器、股票API），
      通过主动、低频的探测来验证节点内部存储的缓存状态与外部真实世界的一致性，
      从而在用户请求到达之前发现数据滞后或节点失效问题。
作者: AGI System
版本: 1.0.0
"""

import logging
import time
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Callable
from enum import Enum
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """节点状态枚举"""
    HEALTHY = "healthy"          # 健康：缓存与外部一致
    DRIFTED = "drifted"          # 漂移：数据存在轻微偏差但在允许范围内
    STALE = "stale"              # 过时：数据明显滞后或不一致
    OFFLINE = "offline"          # 离线：无法连接到外部数据源
    ERROR = "error"              # 错误：探测过程中发生异常


@dataclass
class RealityCheckReport:
    """
    真实性验证报告数据结构
    
    Attributes:
        node_id (str): 节点唯一标识符
        status (NodeStatus): 验证后的节点状态
        internal_value (Any): 节点内部存储的值
        external_value (Any): 从外部世界获取的真实值
        deviation (float): 偏差度 (0.0 到 1.0)
        timestamp (datetime): 验证发生的时间
        latency_ms (float): 探测延迟（毫秒）
        message (str): 附加信息
    """
    node_id: str
    status: NodeStatus
    internal_value: Any
    external_value: Any
    deviation: float
    timestamp: datetime
    latency_ms: float
    message: str


class MicroPraxisValidator:
    """
    微实践验证器：负责对真实节点进行生存测试。
    
    实现了主动探测逻辑，不等待用户反馈，而是周期性或触发式地验证
    节点内部状态与物理世界的一致性。
    """

    def __init__(self, tolerance_threshold: float = 0.1, timeout: int = 5000):
        """
        初始化验证器。
        
        Args:
            tolerance_threshold (float): 允许的数据偏差阈值 (默认0.1即10%)
            timeout (int): 外部探测超时时间（毫秒）
        """
        if not 0.0 <= tolerance_threshold <= 1.0:
            raise ValueError("tolerance_threshold 必须在 0.0 和 1.0 之间")
        
        self.tolerance_threshold = tolerance_threshold
        self.timeout = timeout
        self._node_registry: Dict[str, Dict[str, Any]] = {}
        logger.info("MicroPraxisValidator 初始化完成，容差阈值: %.2f", tolerance_threshold)

    def register_node(
        self, 
        node_id: str, 
        current_state: Any, 
        external_prober: Callable[[], Any]
    ) -> None:
        """
        注册一个需要监控的真实节点。
        
        Args:
            node_id (str): 节点ID
            current_state (Any): 当前节点存储的状态值
            external_prober (Callable): 用于获取外部真实数据的无参函数/API调用
        """
        if not node_id:
            raise ValueError("node_id 不能为空")
        
        self._node_registry[node_id] = {
            "state": current_state,
            "prober": external_prober,
            "last_check": None
        }
        logger.debug("节点已注册: %s", node_id)

    def _calculate_deviation(self, val1: Any, val2: Any) -> float:
        """
        辅助函数：计算两个值之间的归一化偏差。
        
        支持数值型和布尔型比较。如果是字符串或复杂数据，使用精确匹配（0或1）。
        
        Args:
            val1: 内部值
            val2: 外部值
            
        Returns:
            float: 归一化偏差值 (0.0 表示完全一致, 1.0 表示完全偏离)
        """
        if val1 is None and val2 is None:
            return 0.0
        if val1 is None or val2 is None:
            return 1.0
        
        # 数值型偏差计算
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if val1 == 0 and val2 == 0:
                return 0.0
            # 防止除以零，加上极小值
            denominator = max(abs(val1), abs(val2), 1e-9)
            return min(abs(val1 - val2) / denominator, 1.0)
        
        # 布尔型偏差
        if isinstance(val1, bool) and isinstance(val2, bool):
            return 0.0 if val1 == val2 else 1.0
            
        # 默认：精确匹配
        return 0.0 if val1 == val2 else 1.0

    def _execute_probe(self, prober: Callable) -> Tuple[Optional[Any], Optional[float]]:
        """
        内部函数：执行实际的探测操作并计算耗时。
        
        包含错误处理和超时逻辑（简化模拟）。
        
        Args:
            prober (Callable): 探测函数
            
        Returns:
            Tuple[Optional[Any], Optional[float]]: (获取的值, 延迟毫秒数)
        """
        start_time = time.time()
        try:
            # 在生产环境中，这里应包含 asyncio.wait_for 或 threading 超时控制
            external_value = prober()
            latency = (time.time() - start_time) * 1000
            return external_value, latency
        except Exception as e:
            logger.error("探测过程中发生异常: %s", str(e))
            return None, None

    def perform_survival_check(self, node_id: str) -> RealityCheckReport:
        """
        核心函数：对指定节点执行一次“微实践”生存检查。
        
        流程:
        1. 从注册表中获取节点当前状态和探测钩子。
        2. 调用外部探测获取真实世界数据。
        3. 比较内部状态与外部真实数据。
        4. 生成并返回验证报告。
        
        Args:
            node_id (str): 目标节点ID
            
        Returns:
            RealityCheckReport: 包含验证结果的详细报告
            
        Raises:
            KeyError: 如果节点ID未注册
        """
        if node_id not in self._node_registry:
            raise KeyError(f"节点 {node_id} 未在注册表中")
            
        node_info = self._node_registry[node_id]
        internal_val = node_info["state"]
        
        logger.info(f"开始对节点 [{node_id}] 进行生存测试...")
        
        # 1. 执行探测
        external_val, latency = self._execute_probe(node_info["prober"])
        
        # 2. 处理探测失败情况
        if external_val is None:
            return RealityCheckReport(
                node_id=node_id,
                status=NodeStatus.OFFLINE,
                internal_value=internal_val,
                external_value=None,
                deviation=1.0,
                timestamp=datetime.now(),
                latency_ms=latency if latency else 0,
                message="无法获取外部数据，节点可能离线或网络超时。"
            )
            
        # 3. 计算偏差
        deviation = self._calculate_deviation(internal_val, external_val)
        
        # 4. 判定状态
        status = NodeStatus.HEALTHY
        msg = "节点状态与外部世界一致。"
        
        if deviation > 0.0:
            if deviation <= self.tolerance_threshold:
                status = NodeStatus.DRIFTED
                msg = f"检测到轻微偏差 ({deviation:.2%})，但在容许范围内。"
            else:
                status = NodeStatus.STALE
                msg = f"检测到严重偏差 ({deviation:.2%})，内部状态已过时。"
        
        # 5. 更新内部注册表的时间戳（可选：也可以在这里自动更新内部状态）
        node_info["last_check"] = datetime.now()
        
        logger.info(f"节点 [{node_id}] 检查完成: 状态={status.value}, 偏差={deviation:.4f}")
        
        return RealityCheckReport(
            node_id=node_id,
            status=status,
            internal_value=internal_val,
            external_value=external_val,
            deviation=deviation,
            timestamp=datetime.now(),
            latency_ms=latency,
            message=msg
        )

    def auto_reconcile(self, report: RealityCheckReport) -> bool:
        """
        核心函数：根据验证报告尝试自动修正节点状态。
        
        如果检测到 STALE 或 DRIFTED，尝试将内部状态同步为最新探测到的真实值。
        
        Args:
            report (RealityCheckReport): perform_survival_check 生成的报告
            
        Returns:
            bool: 是否执行了修正操作
        """
        if report.node_id not in self._node_registry:
            return False

        if report.status in [NodeStatus.STALE, NodeStatus.DRIFTED]:
            logger.warning(f"正在对节点 [{report.node_id}] 执行状态对齐修正...")
            self._node_registry[report.node_id]["state"] = report.external_value
            self._node_registry[report.node_id]["last_check"] = datetime.now()
            logger.info(f"节点 [{report.node_id}] 状态已更新为: {report.external_value}")
            return True
        
        return False


# --- 使用示例 ---
if __name__ == "__main__":
    # 模拟外部传感器/API数据源
    class MockWeatherSensor:
        def __init__(self):
            self._real_temp = 25.0
        
        def get_real_temp(self):
            # 模拟温度随时间微小波动
            self._real_temp += random.uniform(-0.2, 0.2)
            return round(self._real_temp, 2)

    # 1. 初始化验证器
    validator = MicroPraxisValidator(tolerance_threshold=0.05) # 5% 容差
    
    # 2. 模拟一个内部状态已经滞后的节点（内部认为25度，实际可能变了）
    sensor = MockWeatherSensor()
    # 故意让内部状态不同步
    internal_cache = 25.0 
    
    validator.register_node(
        node_id="weather_station_01",
        current_state=internal_cache,
        external_prober=sensor.get_real_temp
    )
    
    # 3. 连续执行几次测试，模拟时变环境
    print("\n--- 开始时变环境生存测试 ---")
    for i in range(3):
        # 模拟时间流逝，传感器真实值在变，但内部缓存没变（除非auto_reconcile）
        time.sleep(0.1) 
        
        # 执行检查
        report = validator.perform_survival_check("weather_station_01")
        
        print(f"轮次 {i+1}:")
        print(f"  内部值: {report.internal_value}")
        print(f"  外部值: {report.external_value}")
        print(f"  状态: {report.status.value}")
        print(f"  信息: {report.message}")
        
        # 如果发现不一致，尝试修正
        if report.status != NodeStatus.HEALTHY:
            corrected = validator.auto_reconcile(report)
            if corrected:
                print("  -> 系统已执行自动修正。")
        
        # 强制让传感器发生一次剧烈变化，模拟突变环境
        if i == 1:
            sensor._real_temp += 5.0 # 突然升温
            print("  [环境事件] 外部温度突然升高!")