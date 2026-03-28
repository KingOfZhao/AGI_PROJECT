"""
Module: auto_cognitive_consistency_validator.py
Description: 认知自洽性的自动化验证闭环系统。
             旨在针对低频或边缘节点（如小摊贩经济学）构建轻量级仿真环境，
             通过自动生成'情境-行动-反馈'三元组，验证认知单元是否形成逻辑闭环。
Author: Senior Python Engineer for AGI System
Version: 1.0.0
"""

import logging
import random
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ActionType(Enum):
    """定义小摊贩可能的行动类型"""
    ADJUST_PRICE = "调整价格"
    CHANGE_LOCATION = "更换地点"
    RESTOCK = "补货"
    DO_NOTHING = "维持现状"

@dataclass
class ScenarioContext:
    """情境上下文：描述当前的环境状态"""
    weather: str  # 天气：晴天, 雨天
    traffic: str  # 人流：高, 中, 低
    time_of_day: str  # 时间段：早高峰, 午餐, 晚高峰, 深夜
    cost_fluctuation: float  # 成本波动系数 (e.g., 1.1 表示成本上涨10%)

@dataclass
class CognitiveUnit:
    """认知单元：包含待验证的策略逻辑"""
    unit_id: str
    description: str
    strategy_logic: Dict[str, Any]  # 简化的策略规则 (如: "雨天->涨价" 的预期逻辑)
    expected_outcome: str  # 预期的结果描述

@dataclass
class SimulationResult:
    """仿真结果三元组"""
    scenario: ScenarioContext
    action: ActionType
    feedback: float  # 收益或效用值
    is_consistent: bool  # 是否符合预期（自洽性标志）

class StreetVendorSimulator:
    """
    核心类：小摊贩经济学仿真环境。
    
    模拟小摊贩在不同情境下的决策收益，用于验证特定的认知逻辑（如"雨天涨价能提升利润"）
    是否在仿真世界中自洽。
    """

    def __init__(self, base_cost: float = 100.0, base_price: float = 15.0):
        """
        初始化仿真器。
        
        Args:
            base_cost (float): 基础成本
            base_price (float): 基础售价
        """
        self.base_cost = base_cost
        self.base_price = base_price
        logger.info("StreetVendorSimulator initialized with base_cost=%.2f, base_price=%.2f", base_cost, base_price)

    def _calculate_demand(self, context: ScenarioContext, price_multiplier: float) -> int:
        """
        辅助函数：根据情境和价格计算需求量。
        
        Args:
            context (ScenarioContext): 当前环境情境
            price_multiplier (float): 价格系数
            
        Returns:
            int: 模拟的销量
        """
        base_demand = 50
        
        # 流量影响
        traffic_mod = {"高": 1.5, "中": 1.0, "低": 0.5}.get(context.traffic, 1.0)
        
        # 天气影响
        weather_mod = {"晴天": 1.0, "雨天": 0.6}.get(context.weather, 1.0)
        
        # 价格弹性 (价格越高，买的人越少)
        price_elasticity = max(0, 1.5 - price_multiplier) 
        
        demand = int(base_demand * traffic_mod * weather_mod * price_elasticity)
        return max(0, demand)

    def step(self, context: ScenarioContext, action: ActionType) -> Tuple[float, Dict[str, Any]]:
        """
        核心函数1：执行一步仿真。
        
        根据情境和行动计算反馈（利润）。
        
        Args:
            context (ScenarioContext): 环境情境
            action (ActionType): 采取的行动
            
        Returns:
            Tuple[float, Dict]: (利润, 详细调试信息)
        """
        current_cost = self.base_cost * context.cost_fluctuation
        current_price = self.base_price
        
        # 行动逻辑处理
        if action == ActionType.ADJUST_PRICE:
            # 策略：根据情境微调价格
            if context.weather == "雨天":
                current_price *= 1.2  # 雨天涨价20%
            elif context.traffic == "低":
                current_price *= 0.9  # 流量低降价10%
        elif action == ActionType.CHANGE_LOCATION:
            # 换地点可能增加潜在流量，但也增加时间成本（简化为固定扣费）
            current_cost += 20 
            # 假设换地点能稍微提升流量等级的权重
            # 这里简化逻辑，实际应更复杂
        elif action == ActionType.RESTOCK:
            current_cost += 50  # 补货成本

        demand = self._calculate_demand(context, current_price / self.base_price)
        revenue = demand * current_price
        profit = revenue - current_cost
        
        debug_info = {
            "calculated_demand": demand,
            "final_price": current_price,
            "final_cost": current_cost
        }
        
        return profit, debug_info

class CognitiveValidator:
    """
    核心类：认知自洽性验证器。
    
    负责生成测试情境，运行仿真，并对比认知单元的预期与实际反馈。
    """

    def __init__(self, simulator: StreetVendorSimulator):
        self.simulator = simulator
        self.history: List[SimulationResult] = []

    def generate_edge_scenarios(self, count: int = 10) -> List[ScenarioContext]:
        """
        辅助函数：生成边缘或低频情境。
        
        重点生成极端天气、低流量等不常见的组合。
        
        Args:
            count (int): 生成数量
            
        Returns:
            List[ScenarioContext]: 情境列表
        """
        scenarios = []
        weathers = ["晴天", "雨天", "暴雨"]  # 包含极端天气
        traffics = ["高", "中", "低"]
        times = ["早高峰", "午餐", "深夜"]
        
        for _ in range(count):
            # 增加低频情境出现的概率
            w = random.choice(weathers) if random.random() > 0.3 else "暴雨"
            t = random.choice(traffics) if random.random() > 0.3 else "低"
            cost_fluct = round(random.uniform(0.8, 1.5), 2)
            
            scenarios.append(ScenarioContext(
                weather=w,
                traffic=t,
                time_of_day=random.choice(times),
                cost_fluctuation=cost_fluct
            ))
        return scenarios

    def validate_unit(self, unit: CognitiveUnit, rounds: int = 20) -> Dict[str, Any]:
        """
        核心函数2：执行完整的验证闭环。
        
        流程：
        1. 生成情境
        2. 根据认知单元逻辑选择行动
        3. 运行仿真
        4. 验证反馈是否符合预期
        
        Args:
            unit (CognitiveUnit): 待验证的认知单元
            rounds (int): 蒙特卡洛仿真的轮数
            
        Returns:
            Dict: 验证报告
        """
        logger.info(f"Starting validation for Cognitive Unit: {unit.unit_id}")
        scenarios = self.generate_edge_scenarios(rounds)
        consistent_count = 0
        total_profit = 0.0
        
        for context in scenarios:
            # 1. 策略映射：将自然语言描述/逻辑转化为行动（此处为简化规则）
            action = self._infer_action_from_logic(unit, context)
            
            # 2. 仿真执行
            profit, details = self.simulator.step(context, action)
            total_profit += profit
            
            # 3. 自洽性检查
            # 这里简化为：如果利润为正，且符合"盈利"的预期，则视为自洽
            # 复杂情况下需对比 unit.expected_outcome
            is_consistent = self._check_consistency(unit, profit, context)
            
            if is_consistent:
                consistent_count += 1
                
            self.history.append(SimulationResult(
                scenario=context,
                action=action,
                feedback=profit,
                is_consistent=is_consistent
            ))
            
        consistency_rate = consistent_count / rounds
        report = {
            "unit_id": unit.unit_id,
            "total_rounds": rounds,
            "consistency_rate": consistency_rate,
            "average_profit": total_profit / rounds,
            "verdict": "PASS" if consistency_rate > 0.7 else "FAIL" 
        }
        
        logger.info(f"Validation complete. Verdict: {report['verdict']} (Rate: {consistency_rate:.2f})")
        return report

    def _infer_action_from_logic(self, unit: CognitiveUnit, context: ScenarioContext) -> ActionType:
        """
        简单的策略解释器。
        实际AGI系统中这里应是一个NLP模型或规则引擎。
        """
        # 模拟逻辑：如果是雨天且策略倾向于高价，则调整价格
        if context.weather == "雨天" and "涨价" in unit.description:
            return ActionType.ADJUST_PRICE
        if context.traffic == "低" and "更换地点" in unit.description:
            return ActionType.CHANGE_LOCATION
            
        return ActionType.DO_NOTHING

    def _check_consistency(self, unit: CognitiveUnit, profit: float, context: ScenarioContext) -> bool:
        """
        检查结果是否自洽。
        """
        # 简单的自洽性定义：在边缘情况下（如雨天），如果没有巨额亏损，且策略逻辑被触发，即视为逻辑自洽
        # 或者利润高于某个基准线
        baseline_profit = 20.0 
        
        if "盈利" in unit.expected_outcome:
            return profit > baseline_profit
        return False

# Usage Example
if __name__ == "__main__":
    # 1. 初始化仿真环境
    env = StreetVendorSimulator(base_cost=100.0, base_price=12.0)
    
    # 2. 初始化验证器
    validator = CognitiveValidator(simulator=env)
    
    # 3. 定义一个认知单元（假设这是LLM生成的一个关于小摊贩经济学的片段）
    # 描述：在雨天时，因为供给减少，应该涨价以获取最大利润。
    cognition = CognitiveUnit(
        unit_id="street_vendor_001",
        description="雨天激进策略：利用伞的稀缺性，在雨天大幅涨价。",
        strategy_logic={"trigger": "rain", "action": "increase_price"},
        expected_outcome="利润提升"
    )
    
    # 4. 运行验证闭环
    validation_report = validator.validate_unit(cognition, rounds=50)
    
    # 5. 输出结果
    print("\n--- Validation Report ---")
    print(json.dumps(validation_report, indent=4))
    
    # 打印最后几条仿真细节
    print("\n--- Sample Simulation Logs ---")
    for res in validator.history[-3:]:
        print(f"Context: {res.scenario.weather}, Action: {res.action.value}, Profit: {res.feedback:.2f}, Consistent: {res.is_consistent}")
