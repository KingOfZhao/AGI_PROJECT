"""
Module: auto_digital_twin_stress_test.py
Description: 【数字孪生压力测试场】
             为特定技能（如危机公关、精密制造）生成一个'虚拟对抗环境'。
             AI自动生成极端的突发状况（如机器故障、客户暴怒），迫使受训者进行实时决策。
             系统根据决策路径自动评估其技能树的'鲁棒性'，找出薄弱环节。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stress_test_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SkillDomain(Enum):
    """技能领域枚举"""
    CRISIS_PR = "crisis_public_relations"
    PRECISION_MFG = "precision_manufacturing"
    SURGERY = "surgical_procedures"
    FINANCE = "high_frequency_trading"

class DecisionOutcome(Enum):
    """决策结果枚举"""
    OPTIMAL = "optimal"
    SUBOPTIMAL = "suboptimal"
    FAILURE = "failure"
    CATASTROPHIC = "catastrophic"

@dataclass
class ScenarioEvent:
    """突发事件数据结构"""
    event_id: str
    description: str
    intensity: float  # 0.0 到 1.0，表示事件严重程度
    required_skills: List[str]
    time_limit_seconds: int

@dataclass
class UserDecision:
    """用户决策数据结构"""
    decision_id: str
    action_taken: str
    response_time_ms: int
    resources_used: List[str]

@dataclass
class SkillNode:
    """技能树节点"""
    name: str
    current_level: float = 100.0  # 0.0 到 100.0，表示鲁棒性/健康度
    weak_points: List[str] = field(default_factory=list)

class DigitalTwinStressTest:
    """
    数字孪生压力测试场核心类。
    
    负责生成虚拟对抗环境、执行压力测试、分析决策路径并评估技能鲁棒性。
    
    Attributes:
        domain (SkillDomain): 当前测试的技能领域。
        skill_tree (Dict[str, SkillNode]): 受训者的技能树模型。
        scenario_history (List[Dict]): 历史场景记录。
    """

    def __init__(self, domain: SkillDomain, initial_skill_tree: Optional[Dict[str, float]] = None):
        """
        初始化压力测试场。

        Args:
            domain (SkillDomain): 技能领域。
            initial_skill_tree (Optional[Dict[str, float]]): 初始技能水平字典，默认为满状态。
        """
        self.domain = domain
        self.scenario_history: List[Dict] = []
        
        # 初始化技能树
        self.skill_tree: Dict[str, SkillNode] = {}
        default_skills = self._get_default_skills(domain)
        
        for skill, level in default_skills.items():
            user_level = initial_skill_tree.get(skill, 100.0) if initial_skill_tree else 100.0
            self.skill_tree[skill] = SkillNode(name=skill, current_level=user_level)
            
        logger.info(f"数字孪生测试场已初始化: 领域={domain.value}, 技能数={len(self.skill_tree)}")

    def _get_default_skills(self, domain: SkillDomain) -> Dict[str, float]:
        """辅助函数：获取特定领域的默认技能集"""
        if domain == SkillDomain.CRISIS_PR:
            return {"empathy": 100.0, "quick_thinking": 100.0, "brand_loyalty": 100.0, "legal_knowledge": 100.0}
        elif domain == SkillDomain.PRECISION_MFG:
            return {"calibration": 100.0, "safety_protocols": 100.0, "efficiency": 100.0, "repair_speed": 100.0}
        else:
            return {"general_skill": 100.0}

    def generate_adversarial_scenario(self, intensity_target: float = 0.8) -> ScenarioEvent:
        """
        核心函数 1: 生成对抗性场景。
        
        基于当前技能树中的薄弱环节（如果有的话）或随机生成高压力场景。
        
        Args:
            intensity_target (float): 目标压力强度 (0.0-1.0)。
            
        Returns:
            ScenarioEvent: 生成的事件对象。
        """
        if not (0.0 <= intensity_target <= 1.0):
            logger.error(f"无效的压力强度: {intensity_target}")
            raise ValueError("Intensity must be between 0.0 and 1.0")

        # 简单的模拟逻辑：根据领域生成不同描述
        # 实际AGI系统中，这里会调用LLM生成复杂的文本场景
        event_id = f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        description = ""
        required = []

        if self.domain == SkillDomain.CRISIS_PR:
            description = f"突发：公司产品被检测出严重安全隐患，社交媒体热搜排名第1，客户情绪极度愤怒。"
            required = ["empathy", "quick_thinking"]
        elif self.domain == SkillDomain.PRECISION_MFG:
            description = f"警报：核心装配机器人传感器失灵，生产线停滞，且备件库存不足。"
            required = ["calibration", "repair_speed", "safety_protocols"]
        
        # 添加随机扰动
        if random.random() > 0.7:
            description += " 同时，外部网络正遭受DDoS攻击，通讯延迟极高。"
            required.append("crisis_management")

        event = ScenarioEvent(
            event_id=event_id,
            description=description,
            intensity=intensity_target,
            required_skills=required,
            time_limit_seconds=int(60 / intensity_target) # 强度越高，时间越少
        )
        
        logger.info(f"生成对抗场景: ID={event_id}, 强度={intensity_target}")
        return event

    def evaluate_decision(self, scenario: ScenarioEvent, decision: UserDecision) -> Tuple[DecisionOutcome, Dict[str, Any]]:
        """
        核心函数 2: 评估用户决策并更新技能树。
        
        分析决策是否满足场景需求，计算对技能树的影响。
        
        Args:
            scenario (ScenarioEvent): 当前场景。
            decision (UserDecision): 用户的决策输入。
            
        Returns:
            Tuple[DecisionOutcome, Dict]: 评估结果和详细的分析报告。
        """
        analysis_report = {
            "scenario_id": scenario.event_id,
            "timestamp": datetime.now().isoformat(),
            "impact_summary": {},
            "detected_weaknesses": []
        }

        # 边界检查
        if not decision.action_taken:
            logger.warning("收到空决策")
            return DecisionOutcome.FAILURE, analysis_report

        # 模拟评估逻辑 (实际系统中会使用复杂的规则引擎或模型)
        # 假设如果响应时间超过限制，或者动作不包含特定关键词，则扣分
        is_timeout = decision.response_time_ms > (scenario.time_limit_seconds * 1000)
        score_reduction = 0.0
        
        if is_timeout:
            score_reduction += 15.0
            analysis_report["detected_weaknesses"].append("response_latency")

        # 模拟基于决策内容的评分
        # 这里只是一个简单的示例：检查决策中是否包含"安全"或"道歉"等关键词
        content_score = 0
        if self.domain == SkillDomain.CRISIS_PR and "apologize" in decision.action_taken.lower():
            content_score = 10
        elif self.domain == SkillDomain.PRECISION_MFG and "shutdown" in decision.action_taken.lower():
            content_score = 10 # 紧急停机通常是正确的第一步
        else:
            score_reduction += 20.0
            analysis_report["detected_weaknesses"].append("incorrect_protocol")

        # 更新技能树
        outcome_status = DecisionOutcome.OPTIMAL
        if score_reduction > 30:
            outcome_status = DecisionOutcome.FAILURE
        elif score_reduction > 10:
            outcome_status = DecisionOutcome.SUBOPTIMAL

        # 更新涉及的技能节点
        for skill in scenario.required_skills:
            if skill in self.skill_tree:
                old_level = self.skill_tree[skill].current_level
                new_level = max(0.0, old_level - score_reduction * scenario.intensity)
                self.skill_tree[skill].current_level = new_level
                
                if new_level < 60.0:
                    self.skill_tree[skill].weak_points.append(f"Failed under {scenario.intensity} intensity")
                
                analysis_report["impact_summary"][skill] = {
                    "old": old_level,
                    "new": new_level,
                    "delta": new_level - old_level
                }

        # 记录历史
        self.scenario_history.append({
            "scenario": scenario.__dict__,
            "decision": decision.__dict__,
            "outcome": outcome_status.value
        })

        logger.info(f"决策已评估: 结果={outcome_status.value}, 技能影响={analysis_report['impact_summary']}")
        return outcome_status, analysis_report

    def get_system_status(self) -> Dict[str, Any]:
        """
        辅助函数: 获取当前系统的鲁棒性报告。
        
        Returns:
            Dict: 包含技能树当前状态和总鲁棒性评分的字典。
        """
        total_robustness = 0.0
        skill_status = {}
        
        for name, node in self.skill_tree.items():
            skill_status[name] = {
                "level": node.current_level,
                "is_weak": len(node.weak_points) > 0
            }
            total_robustness += node.current_level
            
        avg_robustness = total_robustness / len(self.skill_tree) if self.skill_tree else 0
        
        return {
            "domain": self.domain.value,
            "average_robustness": avg_robustness,
            "skill_details": skill_status,
            "total_scenarios_run": len(self.scenario_history)
        }

# Usage Example
if __name__ == "__main__":
    # 1. 初始化测试场（以危机公关为例）
    print("--- 初始化数字孪生压力测试场 ---")
    test_system = DigitalTwinStressTest(domain=SkillDomain.CRISIS_PR)
    
    # 2. 生成一个高强度的对抗场景
    print("\n--- 生成对抗场景 ---")
    scenario = test_system.generate_adversarial_scenario(intensity_target=0.9)
    print(f"场景描述: {scenario.description}")
    print(f"所需技能: {scenario.required_skills}")
    
    # 3. 模拟用户输入决策
    print("\n--- 提交用户决策 ---")
    # 假设用户做了一个还可以的决策
    user_action = UserDecision(
        decision_id="dec_001",
        action_taken="Immediately issue a public apology and recall product.",
        response_time_ms=45000, # 45秒
        resources_used=["PR_Team", "Legal Dept"]
    )
    
    # 4. 评估决策
    print("\n--- 评估结果 ---")
    outcome, report = test_system.evaluate_decision(scenario, user_action)
    print(f"决策结果: {outcome.value}")
    print(f"详细报告: {json.dumps(report, indent=2)}")
    
    # 5. 查看系统状态
    print("\n--- 当前技能树状态 ---")
    status = test_system.get_system_status()
    print(f"平均鲁棒性: {status['average_robustness']:.2f}")
    print(f"详细状态: {json.dumps(status['skill_details'], indent=2)}")