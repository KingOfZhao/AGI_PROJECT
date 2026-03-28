"""
全息证伪沙盒系统

该模块实现了一个针对高风险或高成本专业领域的VR/AR实训环境，
通过AI生成无限边缘案例，监控人类在沙盒中的心流状态来判断技能内化程度。

Example:
    >>> sandbox = HolographicFalsificationSandbox("神经外科实训")
    >>> case = sandbox.generate_edge_case({"difficulty": "extreme"})
    >>> sandbox.start_simulation(case)
    >>> metrics = sandbox.monitor_flow_state()
    >>> sandbox.evaluate_skill_internalization()
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('holographic_sandbox.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HolographicSandbox")


class DomainType(Enum):
    """专业领域类型枚举"""
    SURGERY = "外科手术"
    CRISIS_PR = "危机公关"
    AEROSPACE = "航空航天"
    FINANCE = "金融交易"
    EMERGENCY = "应急救援"


class SimulationState(Enum):
    """模拟状态枚举"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class EdgeCase:
    """边缘案例数据结构"""
    case_id: str
    domain: DomainType
    difficulty: float  # 0.0-1.0
    parameters: Dict[str, Any]
    expected_actions: List[str]
    time_limit: int  # 秒
    risk_level: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FlowStateMetrics:
    """心流状态指标数据结构"""
    focus_level: float  # 0.0-1.0
    challenge_level: float  # 0.0-1.0
    skill_level: float  # 0.0-1.0
    immersion_score: float  # 0.0-1.0
    heart_rate: int
    stress_index: float
    timestamp: datetime = field(default_factory=datetime.now)


class HolographicFalsificationSandbox:
    """
    全息证伪沙盒系统
    
    针对高风险或高成本的专业领域构建VR/AR实训环境，
    通过游戏化机制促进技能内化。
    
    Attributes:
        domain (DomainType): 专业领域类型
        state (SimulationState): 当前模拟状态
        current_case (Optional[EdgeCase]): 当前运行的边缘案例
        flow_history (List[FlowStateMetrics]): 心流状态历史记录
        performance_metrics (Dict[str, Any]): 性能指标集合
    """
    
    def __init__(self, domain: Union[str, DomainType]) -> None:
        """
        初始化全息证伪沙盒
        
        Args:
            domain: 专业领域，可以是字符串或DomainType枚举
        
        Raises:
            ValueError: 当领域类型无效时抛出
        """
        self.domain = self._validate_domain(domain)
        self.state = SimulationState.IDLE
        self.current_case: Optional[EdgeCase] = None
        self.flow_history: List[FlowStateMetrics] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_cases": 0,
            "successful_cases": 0,
            "average_flow_score": 0.0,
            "skill_progression": []
        }
        self._simulation_start_time: Optional[float] = None
        
        logger.info(f"全息证伪沙盒初始化完成 - 领域: {self.domain.value}")
    
    def _validate_domain(self, domain: Union[str, DomainType]) -> DomainType:
        """
        验证并转换领域类型
        
        Args:
            domain: 输入的领域类型
        
        Returns:
            DomainType: 验证后的领域枚举
        
        Raises:
            ValueError: 当领域类型无效时抛出
        """
        if isinstance(domain, DomainType):
            return domain
        
        domain_mapping = {e.value: e for e in DomainType}
        if domain in domain_mapping:
            return domain_mapping[domain]
        
        logger.error(f"无效的领域类型: {domain}")
        raise ValueError(f"无效的领域类型。有效选项: {list(domain_mapping.keys())}")
    
    def generate_edge_case(
        self,
        parameters: Optional[Dict[str, Any]] = None,
        difficulty_range: Tuple[float, float] = (0.5, 1.0)
    ) -> EdgeCase:
        """
        生成边缘案例
        
        使用AI算法生成具有挑战性的边缘案例，用于在沙盒中进行证伪训练。
        
        Args:
            parameters: 自定义案例参数
            difficulty_range: 难度范围 (min, max)
        
        Returns:
            EdgeCase: 生成的边缘案例
        
        Raises:
            ValueError: 当难度范围无效时抛出
        """
        # 参数验证
        if difficulty_range[0] < 0 or difficulty_range[1] > 1:
            raise ValueError("难度范围必须在0.0到1.0之间")
        if difficulty_range[0] > difficulty_range[1]:
            raise ValueError("难度范围最小值不能大于最大值")
        
        parameters = parameters or {}
        
        # 生成案例ID
        case_id = f"CASE-{self.domain.name}-{int(time.time() * 1000)}"
        
        # 计算难度
        difficulty = random.uniform(*difficulty_range)
        
        # 根据领域生成预期行动
        expected_actions = self._generate_expected_actions(difficulty)
        
        # 确定风险等级
        risk_level = self._calculate_risk_level(difficulty)
        
        # 合并参数
        merged_params = {
            "environment_complexity": random.uniform(0.3, 1.0),
            "time_pressure": difficulty > 0.7,
            "resource_constraints": difficulty > 0.8,
            **parameters
        }
        
        edge_case = EdgeCase(
            case_id=case_id,
            domain=self.domain,
            difficulty=difficulty,
            parameters=merged_params,
            expected_actions=expected_actions,
            time_limit=int(300 + difficulty * 600),  # 5-15分钟
            risk_level=risk_level
        )
        
        logger.info(f"生成边缘案例: {case_id}, 难度: {difficulty:.2f}, 风险: {risk_level}")
        return edge_case
    
    def _generate_expected_actions(self, difficulty: float) -> List[str]:
        """
        根据难度生成预期行动序列
        
        Args:
            difficulty: 难度系数
        
        Returns:
            List[str]: 预期行动列表
        """
        base_actions = {
            DomainType.SURGERY: ["识别解剖结构", "评估风险区域", "执行精确切割", "处理并发症"],
            DomainType.CRISIS_PR: ["分析舆情态势", "制定回应策略", "媒体沟通", "后续跟进"],
            DomainType.AEROSPACE: ["系统诊断", "故障定位", "应急程序执行", "安全着陆评估"],
            DomainType.FINANCE: ["市场分析", "风险评估", "交易决策", "组合调整"],
            DomainType.EMERGENCY: ["现场评估", "资源调配", "救援协调", "后续处理"]
        }
        
        actions = base_actions.get(self.domain, ["通用行动"])
        
        # 高难度添加额外复杂行动
        if difficulty > 0.7:
            actions.extend(["处理突发变量", "多任务协同", "压力下决策"])
        
        return actions
    
    def _calculate_risk_level(self, difficulty: float) -> str:
        """
        计算风险等级
        
        Args:
            difficulty: 难度系数
        
        Returns:
            str: 风险等级描述
        """
        if difficulty >= 0.9:
            return "极高"
        elif difficulty >= 0.7:
            return "高"
        elif difficulty >= 0.5:
            return "中等"
        else:
            return "低"
    
    def start_simulation(self, edge_case: EdgeCase) -> bool:
        """
        启动沙盒模拟
        
        Args:
            edge_case: 要运行的边缘案例
        
        Returns:
            bool: 启动是否成功
        
        Raises:
            RuntimeError: 当系统状态不允许启动时抛出
        """
        if self.state == SimulationState.RUNNING:
            raise RuntimeError("已有模拟正在运行，请先结束当前模拟")
        
        try:
            self.state = SimulationState.INITIALIZING
            logger.info(f"正在初始化模拟环境: {edge_case.case_id}")
            
            # 模拟环境初始化
            time.sleep(0.1)  # 模拟初始化延迟
            
            self.current_case = edge_case
            self._simulation_start_time = time.time()
            self.state = SimulationState.RUNNING
            self.performance_metrics["total_cases"] += 1
            
            logger.info(f"模拟已启动 - 案例: {edge_case.case_id}, 时间限制: {edge_case.time_limit}秒")
            return True
            
        except Exception as e:
            self.state = SimulationState.ERROR
            logger.error(f"模拟启动失败: {str(e)}")
            return False
    
    def monitor_flow_state(
        self,
        bio_feedback: Optional[Dict[str, Any]] = None
    ) -> FlowStateMetrics:
        """
        监控心流状态
        
        采集并分析用户在沙盒中的心流状态指标，用于判断技能内化程度。
        
        Args:
            bio_feedback: 生物反馈数据 (心率、皮肤电导等)
        
        Returns:
            FlowStateMetrics: 心流状态指标
        
        Raises:
            RuntimeError: 当没有运行中的模拟时抛出
        """
        if self.state != SimulationState.RUNNING or self.current_case is None:
            raise RuntimeError("没有正在运行的模拟")
        
        # 模拟采集心流数据
        bio_feedback = bio_feedback or {}
        
        # 计算各项指标
        elapsed_time = time.time() - (self._simulation_start_time or time.time())
        progress = min(elapsed_time / self.current_case.time_limit, 1.0)
        
        # 基于进度和难度计算挑战与技能平衡
        challenge = self.current_case.difficulty * (1 + progress * 0.5)
        skill = min(0.5 + self.performance_metrics["successful_cases"] * 0.05, 1.0)
        
        # 计算心流核心指标
        focus_level = self._calculate_focus_level(challenge, skill, bio_feedback)
        immersion_score = (focus_level + min(challenge, skill)) / 2
        
        # 获取心率数据
        heart_rate = bio_feedback.get("heart_rate", random.randint(60, 100))
        
        # 计算压力指数
        stress_index = abs(challenge - skill) * (1 + (heart_rate - 70) / 100)
        
        metrics = FlowStateMetrics(
            focus_level=focus_level,
            challenge_level=challenge,
            skill_level=skill,
            immersion_score=immersion_score,
            heart_rate=heart_rate,
            stress_index=stress_index
        )
        
        self.flow_history.append(metrics)
        
        logger.debug(
            f"心流监控 - 专注度: {focus_level:.2f}, "
            f"沉浸感: {immersion_score:.2f}, "
            f"压力指数: {stress_index:.2f}"
        )
        
        return metrics
    
    def _calculate_focus_level(
        self,
        challenge: float,
        skill: float,
        bio_feedback: Dict[str, Any]
    ) -> float:
        """
        计算专注度水平
        
        Args:
            challenge: 挑战水平
            skill: 技能水平
            bio_feedback: 生物反馈数据
        
        Returns:
            float: 专注度水平 (0.0-1.0)
        """
        # 心流状态最佳区域：挑战与技能平衡
        balance_factor = 1 - abs(challenge - skill)
        
        # 生物反馈加权
        bio_factor = 0.5
        if "eye_tracking" in bio_feedback:
            bio_factor += 0.2
        if "eeg" in bio_feedback:
            bio_factor += 0.3
        
        focus = balance_factor * bio_factor
        return max(0.0, min(1.0, focus))
    
    def evaluate_skill_internalization(self) -> Dict[str, Any]:
        """
        评估技能内化程度
        
        基于心流状态历史数据评估用户的技能内化程度，
        而非传统的考试分数。
        
        Returns:
            Dict[str, Any]: 技能内化评估报告
        
        Raises:
            RuntimeError: 当没有足够数据时抛出
        """
        if not self.flow_history:
            raise RuntimeError("没有足够的心流数据进行评估")
        
        # 计算平均心流指标
        avg_focus = sum(m.focus_level for m in self.flow_history) / len(self.flow_history)
        avg_immersion = sum(m.immersion_score for m in self.flow_history) / len(self.flow_history)
        avg_stress = sum(m.stress_index for m in self.flow_history) / len(self.flow_history)
        
        # 计算心流持续性 (在心流状态的时间比例)
        flow_threshold = 0.7
        flow_time_ratio = sum(
            1 for m in self.flow_history 
            if m.focus_level > flow_threshold and m.immersion_score > flow_threshold
        ) / len(self.flow_history)
        
        # 技能内化指数
        internalization_index = (
            avg_focus * 0.3 +
            avg_immersion * 0.3 +
            flow_time_ratio * 0.25 +
            (1 - avg_stress) * 0.15
        )
        
        # 判断内化程度
        if internalization_index >= 0.8:
            level = "精通"
        elif internalization_index >= 0.6:
            level = "熟练"
        elif internalization_index >= 0.4:
            level = "发展中"
        else:
            level = "初学"
        
        report = {
            "internalization_index": round(internalization_index, 3),
            "skill_level": level,
            "metrics": {
                "average_focus": round(avg_focus, 3),
                "average_immersion": round(avg_immersion, 3),
                "average_stress": round(avg_stress, 3),
                "flow_time_ratio": round(flow_time_ratio, 3)
            },
            "total_cases_completed": self.performance_metrics["total_cases"],
            "recommendation": self._generate_recommendation(internalization_index, avg_stress)
        }
        
        # 更新性能指标
        self.performance_metrics["average_flow_score"] = internalization_index
        self.performance_metrics["skill_progression"].append({
            "timestamp": datetime.now().isoformat(),
            "index": internalization_index
        })
        
        logger.info(f"技能内化评估完成 - 指数: {internalization_index:.3f}, 等级: {level}")
        return report
    
    def _generate_recommendation(
        self,
        internalization_index: float,
        stress_index: float
    ) -> str:
        """
        生成训练建议
        
        Args:
            internalization_index: 内化指数
            stress_index: 压力指数
        
        Returns:
            str: 训练建议
        """
        if internalization_index < 0.4:
            return "建议降低案例难度，增加基础训练频次"
        elif internalization_index < 0.6 and stress_index > 0.5:
            return "建议在中等难度案例中增加休息间隔，注重压力管理"
        elif internalization_index < 0.8:
            return "技能发展中，建议逐步增加案例复杂度"
        else:
            return "技能已内化，建议挑战极限边缘案例以突破瓶颈"
    
    def complete_simulation(self, success: bool = True) -> Dict[str, Any]:
        """
        完成当前模拟
        
        Args:
            success: 案例是否成功完成
        
        Returns:
            Dict[str, Any]: 模拟总结报告
        
        Raises:
            RuntimeError: 当没有运行中的模拟时抛出
        """
        if self.state != SimulationState.RUNNING:
            raise RuntimeError("没有正在运行的模拟")
        
        if success:
            self.performance_metrics["successful_cases"] += 1
        
        # 生成总结报告
        elapsed = time.time() - (self._simulation_start_time or time.time())
        
        summary = {
            "case_id": self.current_case.case_id if self.current_case else None,
            "domain": self.domain.value,
            "success": success,
            "elapsed_time": round(elapsed, 2),
            "flow_records": len(self.flow_history),
            "final_evaluation": None
        }
        
        try:
            summary["final_evaluation"] = self.evaluate_skill_internalization()
        except RuntimeError:
            pass
        
        # 重置状态
        self.state = SimulationState.COMPLETED
        self.current_case = None
        self._simulation_start_time = None
        self.flow_history = []
        
        logger.info(f"模拟完成 - 成功: {success}, 耗时: {elapsed:.2f}秒")
        return summary
    
    def export_session_data(self, filepath: str) -> None:
        """
        导出会话数据
        
        Args:
            filepath: 导出文件路径
        
        Raises:
            IOError: 当文件写入失败时抛出
        """
        data = {
            "domain": self.domain.value,
            "performance_metrics": self.performance_metrics,
            "export_time": datetime.now().isoformat()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"会话数据已导出至: {filepath}")
        except IOError as e:
            logger.error(f"数据导出失败: {str(e)}")
            raise


def main():
    """使用示例"""
    # 创建外科手术领域的沙盒
    sandbox = HolographicSandbox("外科手术")
    
    # 生成高难度边缘案例
    case = sandbox.generate_edge_case(
        parameters={"patient_condition": "critical"},
        difficulty_range=(0.8, 0.95)
    )
    
    print(f"\n=== 边缘案例生成 ===")
    print(f"案例ID: {case.case_id}")
    print(f"难度: {case.difficulty:.2f}")
    print(f"风险等级: {case.risk_level}")
    print(f"预期行动: {case.expected_actions}")
    
    # 启动模拟
    sandbox.start_simulation(case)
    
    # 模拟运行过程
    print("\n=== 模拟运行中 ===")
    for i in range(5):
        time.sleep(0.1)
        metrics = sandbox.monitor_flow_state({
            "heart_rate": 75 + random.randint(-5, 5)
        })
        print(f"时间点 {i+1}: 专注度={metrics.focus_level:.2f}, "
              f"沉浸感={metrics.immersion_score:.2f}")
    
    # 完成模拟并评估
    summary = sandbox.complete_simulation(success=True)
    
    print("\n=== 技能内化评估 ===")
    if summary["final_evaluation"]:
        eval_data = summary["final_evaluation"]
        print(f"内化指数: {eval_data['internalization_index']}")
        print(f"技能等级: {eval_data['skill_level']}")
        print(f"建议: {eval_data['recommendation']}")


if __name__ == "__main__":
    main()