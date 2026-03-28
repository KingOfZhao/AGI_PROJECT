"""
数字免疫认知系统

该模块实现了一个模拟生物免疫机制的微服务健壮性系统。
它通过混沌工程主动注入故障（疫苗），监测系统反应，
并利用AI生成防御策略（抗体），从而实现系统的获得性免疫。

核心功能：
1. 主动巡逻：持续监控微服务健康状态
2. 疫苗注射：受控的故障注入测试
3. 抗体生成：AI驱动的防御策略生成
4. 免疫记忆：将防御策略固化到知识库

作者: AGI System
版本: 1.0.0
"""

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalImmuneSystem")


class HealthStatus(Enum):
    """服务健康状态枚举"""
    HEALTHY = auto()
    DEGRADED = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


class FaultType(Enum):
    """故障类型枚举"""
    LATENCY = auto()     # 延迟注入
    EXCEPTION = auto()   # 异常注入
    RESOURCE = auto()    # 资源耗尽
    NETWORK = auto()     # 网络分区


@dataclass
class ServiceEndpoint:
    """服务端点数据结构"""
    name: str
    url: str
    criticality: float  # 0.0-1.0 关键程度评分
    dependencies: List[str]


@dataclass
class Vaccine:
    """疫苗(故障注入测试用例)数据结构"""
    fault_type: FaultType
    intensity: float  # 0.0-1.0 故障强度
    target_service: str
    duration_seconds: int
    description: str


@dataclass
class Antibody:
    """抗体(防御策略)数据结构"""
    strategy_type: str
    rules: Dict
    effectiveness_score: float
    created_at: datetime
    applicable_services: List[str]


class DigitalImmuneCognitionSystem:
    """
    数字免疫认知系统核心类
    
    实现了主动巡逻、疫苗生成、抗体产生和免疫记忆功能。
    
    使用示例:
    >>> immune_system = DigitalImmuneCognitionSystem()
    >>> immune_system.register_service(ServiceEndpoint("payment", "http://payment.api", 0.9, ["db", "auth"]))
    >>> immune_system.start_patrol()
    >>> vaccine = immune_system.generate_vaccine("payment", FaultType.LATENCY)
    >>> result = immune_system.inject_vaccine(vaccine)
    >>> if result["status"] == "compromised":
    ...     antibody = immune_system.generate_antibody(result)
    ...     immune_system.remember_antibody(antibody)
    """
    
    def __init__(self, knowledge_base_path: str = "./immune_memory.json"):
        """
        初始化数字免疫系统
        
        Args:
            knowledge_base_path: 免疫记忆存储路径
        """
        self.services: Dict[str, ServiceEndpoint] = {}
        self.immune_memory: Dict[str, List[Antibody]] = {}
        self.knowledge_base_path = knowledge_base_path
        self.patrol_active = False
        self.last_patrol_time: Optional[datetime] = None
        
        # 加载已有免疫记忆
        self._load_immune_memory()
        
        logger.info("数字免疫认知系统初始化完成")

    def register_service(self, service: ServiceEndpoint) -> bool:
        """
        注册需要监控的微服务
        
        Args:
            service: 服务端点描述
            
        Returns:
            bool: 注册是否成功
            
        Raises:
            ValueError: 如果服务数据无效
        """
        if not service.name or not service.url:
            raise ValueError("服务名称和URL不能为空")
            
        if not 0 <= service.criticality <= 1:
            raise ValueError("关键性评分必须在0.0到1.0之间")
            
        self.services[service.name] = service
        logger.info(f"已注册服务: {service.name} (关键性: {service.criticality})")
        return True

    def start_patrol(self, interval_seconds: int = 300) -> None:
        """
        启动主动巡逻模式
        
        Args:
            interval_seconds: 巡逻间隔(秒)
            
        说明:
            该方法会启动一个后台线程，定期执行健康检查和
            随机疫苗注射测试。
        """
        self.patrol_active = True
        logger.info(f"开始主动巡逻模式，间隔: {interval_seconds}秒")
        
        while self.patrol_active:
            self._execute_patrol_round()
            time.sleep(interval_seconds)

    def generate_vaccine(
        self,
        target_service: str,
        fault_type: Optional[FaultType] = None,
        intensity: Optional[float] = None
    ) -> Vaccine:
        """
        生成疫苗(故障注入测试用例)
        
        Args:
            target_service: 目标服务名称
            fault_type: 指定故障类型(可选，默认随机)
            intensity: 指定故障强度(可选，默认根据服务关键性计算)
            
        Returns:
            Vaccine: 生成的疫苗对象
            
        Raises:
            ValueError: 如果目标服务未注册
        """
        if target_service not in self.services:
            raise ValueError(f"服务 {target_service} 未注册")
            
        service = self.services[target_service]
        
        # 如果没有指定故障类型，则随机选择
        selected_fault = fault_type or random.choice(list(FaultType))
        
        # 如果没有指定强度，则根据服务关键性计算
        calculated_intensity = intensity or self._calculate_vaccine_intensity(service)
        
        vaccine = Vaccine(
            fault_type=selected_fault,
            intensity=calculated_intensity,
            target_service=target_service,
            duration_seconds=random.randint(10, 60),
            description=f"自动生成的{selected_fault.name}测试疫苗"
        )
        
        logger.info(f"生成疫苗: {vaccine.description} 强度: {vaccine.intensity}")
        return vaccine

    def inject_vaccine(self, vaccine: Vaccine) -> Dict:
        """
        注射疫苗(执行故障注入测试)
        
        Args:
            vaccine: 要注射的疫苗
            
        Returns:
            Dict: 测试结果，包含以下字段:
                - status: 系统状态
                - impact_score: 影响评分
                - affected_services: 受影响的服务列表
                - recovery_time_seconds: 恢复时间
                
        Raises:
            RuntimeError: 如果疫苗注射过程出错
        """
        logger.info(f"开始注射疫苗: {vaccine.description}")
        
        try:
            # 模拟故障注入和系统反应
            impact_score = self._simulate_fault_impact(vaccine)
            affected_services = self._identify_affected_services(vaccine)
            recovery_time = self._measure_recovery_time(vaccine)
            
            # 根据影响评分确定系统状态
            if impact_score < 0.3:
                status = "healthy"
            elif impact_score < 0.7:
                status = "degraded"
            else:
                status = "compromised"
                
            result = {
                "vaccine": vaccine,
                "status": status,
                "impact_score": impact_score,
                "affected_services": affected_services,
                "recovery_time_seconds": recovery_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"疫苗注射结果: {status} (影响评分: {impact_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"疫苗注射失败: {str(e)}")
            raise RuntimeError(f"疫苗注射失败: {str(e)}")

    def generate_antibody(self, vaccine_result: Dict) -> Antibody:
        """
        生成抗体(防御策略)
        
        Args:
            vaccine_result: 疫苗注射结果
            
        Returns:
            Antibody: 生成的抗体对象
            
        说明:
            使用AI分析疫苗结果，生成相应的防御策略。
        """
        vaccine = vaccine_result["vaccine"]
        
        # 根据故障类型选择防御策略
        strategy_type = self._determine_strategy_type(vaccine.fault_type)
        
        # 生成防御规则
        rules = self._generate_defense_rules(vaccine, vaccine_result)
        
        # 计算有效性评分
        effectiveness = 1.0 - vaccine_result["impact_score"]
        
        antibody = Antibody(
            strategy_type=strategy_type,
            rules=rules,
            effectiveness_score=effectiveness,
            created_at=datetime.now(),
            applicable_services=self._find_similar_services(vaccine.target_service)
        )
        
        logger.info(f"生成抗体: {strategy_type} 有效性: {effectiveness:.2f}")
        return antibody

    def remember_antibody(self, antibody: Antibody) -> bool:
        """
        将抗体固化到免疫记忆(知识库)
        
        Args:
            antibody: 要记忆的抗体
            
        Returns:
            bool: 是否成功记忆
        """
        for service in antibody.applicable_services:
            if service not in self.immune_memory:
                self.immune_memory[service] = []
            self.immune_memory[service].append(antibody)
            
        logger.info(f"抗体已记忆，适用于 {len(antibody.applicable_services)} 个服务")
        return True

    # 辅助函数
    def _calculate_vaccine_intensity(self, service: ServiceEndpoint) -> float:
        """根据服务关键性计算疫苗强度"""
        # 关键性越高的服务，初始测试强度越低
        base_intensity = 1.0 - service.criticality
        # 添加随机因素
        random_factor = random.uniform(-0.1, 0.1)
        return max(0.1, min(0.9, base_intensity + random_factor))

    def _simulate_fault_impact(self, vaccine: Vaccine) -> float:
        """模拟故障影响"""
        # 在实际系统中，这里会执行真实的故障注入
        # 这里使用随机模拟
        base_impact = vaccine.intensity
        
        # 检查是否有已有的抗体可以减轻影响
        if vaccine.target_service in self.immune_memory:
            memory = self.immune_memory[vaccine.target_service]
            applicable_antibodies = [
                a for a in memory 
                if a.strategy_type == self._determine_strategy_type(vaccine.fault_type)
            ]
            if applicable_antibodies:
                # 抗体可以减轻影响
                max_effectiveness = max(a.effectiveness_score for a in applicable_antibodies)
                base_impact *= (1.0 - max_effectiveness)
                
        # 添加随机因素
        random_factor = random.uniform(-0.1, 0.1)
        return max(0.0, min(1.0, base_impact + random_factor))

    def _identify_affected_services(self, vaccine: Vaccine) -> List[str]:
        """识别受影响的服务"""
        # 在实际系统中，这里会分析服务依赖关系
        affected = [vaccine.target_service]
        service = self.services.get(vaccine.target_service)
        
        if service and service.dependencies:
            # 随机选择部分依赖服务作为受影响
            num_affected = random.randint(0, len(service.dependencies))
            affected.extend(random.sample(service.dependencies, num_affected))
            
        return affected

    def _measure_recovery_time(self, vaccine: Vaccine) -> int:
        """测量系统恢复时间"""
        # 在实际系统中，这里会测量真实的恢复时间
        # 这里使用随机模拟
        base_time = vaccine.duration_seconds
        random_factor = random.randint(-5, 10)
        return max(5, base_time + random_factor)

    def _determine_strategy_type(self, fault_type: FaultType) -> str:
        """根据故障类型确定防御策略"""
        strategy_map = {
            FaultType.LATENCY: "circuit_breaker",
            FaultType.EXCEPTION: "retry_policy",
            FaultType.RESOURCE: "autoscaling",
            FaultType.NETWORK: "fallback_mechanism"
        }
        return strategy_map.get(fault_type, "generic_mitigation")

    def _generate_defense_rules(self, vaccine: Vaccine, result: Dict) -> Dict:
        """生成防御规则"""
        strategy_type = self._determine_strategy_type(vaccine.fault_type)
        
        rules = {
            "condition": {
                "fault_type": vaccine.fault_type.name,
                "threshold": result["impact_score"]
            },
            "action": {
                "type": strategy_type,
                "parameters": {
                    "intensity": vaccine.intensity,
                    "timeout": 30,
                    "max_retries": 3
                }
            }
        }
        
        return rules

    def _find_similar_services(self, target_service: str) -> List[str]:
        """查找类似的服务"""
        # 在实际系统中，这里会使用服务拓扑分析
        similar = [target_service]
        
        # 简单模拟：添加有相似依赖的服务
        target_deps = set(self.services[target_service].dependencies) if target_service in self.services else set()
        
        for name, service in self.services.items():
            if name != target_service:
                deps = set(service.dependencies)
                # 如果有50%以上的依赖相同，则认为相似
                if target_deps and len(deps & target_deps) / len(target_deps) > 0.5:
                    similar.append(name)
                    
        return similar

    def _load_immune_memory(self) -> None:
        """加载免疫记忆"""
        # 在实际系统中，这里会从持久化存储加载
        logger.info("加载免疫记忆...")
        # 模拟加载一些初始抗体
        if "payment" in self.services:
            self.immune_memory["payment"] = [
                Antibody(
                    strategy_type="circuit_breaker",
                    rules={"threshold": 0.5},
                    effectiveness_score=0.7,
                    created_at=datetime.now(),
                    applicable_services=["payment"]
                )
            ]

    def _execute_patrol_round(self) -> None:
        """执行一轮巡逻"""
        self.last_patrol_time = datetime.now()
        logger.info("执行巡逻检查...")
        
        # 随机选择一个服务进行疫苗测试
        if self.services:
            target = random.choice(list(self.services.keys()))
            try:
                vaccine = self.generate_vaccine(target)
                result = self.inject_vaccine(vaccine)
                
                if result["status"] == "compromised":
                    antibody = self.generate_antibody(result)
                    self.remember_antibody(antibody)
                    
            except Exception as e:
                logger.error(f"巡逻测试失败: {str(e)}")


# 示例用法
if __name__ == "__main__":
    # 创建免疫系统实例
    immune_system = DigitalImmuneCognitionSystem()
    
    # 注册几个微服务
    services = [
        ServiceEndpoint("payment", "http://payment.api", 0.9, ["db", "auth"]),
        ServiceEndpoint("inventory", "http://inventory.api", 0.7, ["db"]),
        ServiceEndpoint("shipping", "http://shipping.api", 0.6, ["inventory", "payment"])
    ]
    
    for service in services:
        immune_system.register_service(service)
    
    # 生成并注射疫苗
    print("\n=== 疫苗测试 ===")
    vaccine = immune_system.generate_vaccine("payment", FaultType.LATENCY, 0.8)
    result = immune_system.inject_vaccine(vaccine)
    
    # 如果系统被突破，生成并记忆抗体
    if result["status"] == "compromised":
        print("\n=== 生成抗体 ===")
        antibody = immune_system.generate_antibody(result)
        immune_system.remember_antibody(antibody)
        print(f"生成的抗体策略: {antibody.strategy_type}")
    
    # 启动短期巡逻演示
    print("\n=== 启动巡逻模式(演示) ===")
    immune_system.patrol_active = True
    immune_system._execute_patrol_round()