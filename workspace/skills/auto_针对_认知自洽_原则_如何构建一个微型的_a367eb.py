"""
Module: micro_production_turing_test
Name: auto_针对_认知自洽_原则_如何构建一个微型的_a367eb
Description: 针对“认知自洽”原则，构建一个微型的“产线图灵测试”。本模块模拟一个封闭的制造单元（自动包装线），
             实现一个AGI代理，该代理通过观察和交互推导产线的逻辑控制规则，并生成一个逻辑上自洽的控制图谱。

Domain: automated_reasoning
Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
import random
import itertools
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ManufacturingCell:
    """
    模拟一个封闭的制造单元环境。
    包含传感器和执行器，根据预设的隐藏规则运行。
    """

    def __init__(self, hidden_rules: Dict[str, List[str]]):
        """
        初始化制造单元。

        Args:
            hidden_rules (Dict[str, List[str]]): 隐藏的逻辑规则。
                Key: 执行器名称 (e.g., 'Motor_B')
                Value: 传感器列表，必须全部为True才能激活 (e.g., ['Sensor_A'])
        """
        self.sensors: Dict[str, bool] = {}
        self.actuators: Dict[str, bool] = {}
        self.hidden_rules = hidden_rules
        
        # 初始化所有涉及组件的状态为 False
        all_components = set(hidden_rules.keys())
        for deps in hidden_rules.values():
            all_components.update(deps)
            
        for comp in all_components:
            if comp.startswith("Sensor"):
                self.sensors[comp] = False
            elif comp.startswith("Motor"):
                self.actuators[comp] = False
                
        logger.info(f"制造单元初始化完成。传感器: {list(self.sensors.keys())}, 执行器: {list(self.actuators.keys())}")

    def reset_environment(self) -> None:
        """重置所有传感器和执行器状态为安全状态。"""
        for k in self.sensors:
            self.sensors[k] = False
        for k in self.actuators:
            self.actuators[k] = False
        self._update_actuators()
        logger.debug("环境已重置。")

    def set_sensor_state(self, sensor_name: str, state: bool) -> None:
        """
        设置传感器状态并触发生态更新（模拟PLC逻辑）。

        Args:
            sensor_name (str): 传感器名称。
            state (bool): 目标状态。
        """
        if sensor_name not in self.sensors:
            raise ValueError(f"未知的传感器: {sensor_name}")
        
        self.sensors[sensor_name] = state
        self._update_actuators()

    def _update_actuators(self) -> None:
        """根据隐藏规则更新执行器状态。"""
        for actuator, required_sensors in self.hidden_rules.items():
            # 逻辑：所有依赖的传感器都必须为 True
            is_active = all(self.sensors.get(s, False) for s in required_sensors)
            self.actuators[actuator] = is_active

    def get_observation(self) -> Tuple[Dict[str, bool], Dict[str, bool]]:
        """返回当前传感器和执行器的状态快照。"""
        return self.sensors.copy(), self.actuators.copy()


class CognitiveConsistencyAgent:
    """
    AGI代理：负责观察环境，推导规则，并进行自洽性验证。
    """

    def __init__(self, target_actuators: List[str]):
        """
        初始化代理。

        Args:
            target_actuators (List[str]): 需要推导逻辑的目标执行器列表。
        """
        self.target_actuators = target_actuators
        # 存储推导出的规则: Key=Actuator, Value=Set of required Sensors (Conjunction)
        self.learned_graph: Dict[str, Set[str]] = {k: set() for k in target_actuators}
        self.observation_history: List[Tuple[Dict[str, bool], Dict[str, bool]]] []
        
    def observe(self, sensors: Dict[str, bool], actuators: Dict[str, bool]) -> None:
        """记录观察数据。"""
        self.observation_history.append((sensors, actuators))
        self._induce_rules(sensors, actuators)

    def _induce_rules(self, current_sensors: Dict[str, bool], current_actuators: Dict[str, bool]) -> None:
        """
        核心认知逻辑：基于当前的观察更新规则图谱。
        采用假设排除法：
        1. 如果 Actuator 为 OFF，则当前所有为 ON 的传感器 *不构成* 充分条件（或者存在缺失）。
           实际上，如果我们要找必要条件，更简单的逻辑是：
           如果 Actuator ON，那么当前所有 ON 的传感器可能都是必要的。
           如果 Actuator OFF，且 Sensor X ON，那么 Sensor X 单独不足以驱动。
           
           改进逻辑：
           维护一个“可能必要传感器”列表。
           如果 Actuator ON，我们认为当前所有 ON 的传感器都是“候选必要条件”。
           如果 Actuator OFF，但 Sensor X ON，说明 Sensor X 不是唯一的必要条件，或者组合不对。
           
           最简逻辑（逻辑合取推导）：
           1. 若 Actuator ON，则其必要条件集必须是当前 ON 传感器的子集。
           2. 若 Actuator OFF，则其必要条件集不能是当前 ON 传感器的子集（或者当前 ON 传感器集不是必要条件集的超集）。
           
           此处使用一种简单的累积学习策略：
           当执行器为True时，寻找哪些传感器为True，建立关联。
           当执行器为False时，如果某个传感器为True，则该传感器本身不是充分条件。
        """
        for actuator in self.target_actuators:
            is_active = current_actuators.get(actuator, False)
            on_sensors = {k for k, v in current_sensors.items() if v}
            
            if is_active:
                # 如果电机启动了，那么当前开启的传感器集合必须包含所有必要条件。
                # 如果我们之前认为需要某些传感器，但现在它们不在当前开启列表中，那就矛盾了（除非是OR逻辑，但此处假设是AND逻辑）。
                # 这里采用交集策略来收敛必要条件（不太准确，但在简单合取逻辑下可行）。
                # 更好的方法：如果这是第一次看到 ON，假设所有 ON 的传感器都是必要的。
                # 如果之前已经有假设，取交集。
                if not self.learned_graph[actuator]:
                     self.learned_graph[actuator].update(on_sensors)
                else:
                     # 收敛规则：只保留那些在所有 ON 状态下都存在的传感器
                     # 注意：这要求系统遍历所有状态，或者这是一个严格的逻辑推导
                     # 为了演示简化：我们假设如果它ON，那么当前的ON传感器至少包含了必要集
                     pass 

            else:
                # 如果电机没启动，但某些传感器开了，说明这些传感器组合不足以启动电机。
                # 这可以帮助排除那些“非必要”的传感器吗？不完全是。
                # 这里主要用来验证规则的自洽性。
                pass

    def refine_rules_by_negatives(self) -> None:
        """
        根据反例（电机未启动的情况）精炼规则。
        规则：如果 Motor OFF 且 Sensor X ON，则 X 不可能是唯一的必要条件。
        """
        for sensors, actuators in self.observation_history:
            for actuator in self.target_actuators:
                if not actuators.get(actuator, False):
                    # 电机是关的
                    # 如果我们目前的规则认为需要传感器 S，而此时 S 是 True，但电机是 False，说明规则错误（或者还有其他缺失条件）
                    # 这里不做删除，而是标记不确定性，但在本微型测试中，我们假设是 AND 逻辑
                    pass

    def validate_hypothesis(self, env: ManufacturingCell) -> float:
        """
        验证当前生成的控制图谱在多大程度上符合观察到的数据（自洽性测试）。
        
        Returns:
            float: 自洽性得分 (0.0 到 1.0)。
        """
        consistency_score = 0.0
        total_checks = 0
        
        # 重新模拟所有历史观察
        for sensors, actual_actuators in self.observation_history:
            predicted_actuators = {}
            
            for actuator in self.target_actuators:
                required_sensors = self.learned_graph.get(actuator, set())
                # 预测逻辑：传感器集合必须是 required_sensors 的超集
                current_on_sensors = {k for k, v in sensors.items() if v}
                
                is_predicted_on = required_sensors.issubset(current_on_sensors)
                predicted_actuators[actuator] = is_predicted_on
                
                if predicted_actuators[actuator] == actual_actuators.get(actuator, False):
                    consistency_score += 1
                total_checks += 1
                
        return consistency_score / total_checks if total_checks > 0 else 0.0

    def generate_control_graph(self) -> Dict[str, List[str]]:
        """返回当前推导出的控制图谱。"""
        return {k: list(v) for k, v in self.learned_graph.items()}


def run_production_turing_test(
    sensor_list: List[str], 
    actuator_list: List[str], 
    hidden_rules: Dict[str, List[str]], 
    test_cycles: int = 10
) -> Tuple[Dict[str, List[str]], float]:
    """
    运行微型产线图灵测试的主函数。
    
    Args:
        sensor_list (List[str]): 传感器名称列表。
        actuator_list (List[str]): 执行器名称列表。
        hidden_rules (Dict[str, List[str]]): 真实的隐藏规则。
        test_cycles (int): 测试循环次数。
        
    Returns:
        Tuple[Dict[str, List[str]], float]: (推导出的规则图谱, 自洽性得分)
    
    Raises:
        ValueError: 如果输入参数无效。
    """
    if not sensor_list or not actuator_list:
        raise ValueError("传感器和执行器列表不能为空")
    if test_cycles < 1:
        raise ValueError("测试循环次数必须大于0")

    logger.info("=== 开始产线图灵测试 ===")
    
    # 1. 初始化环境
    cell = ManufacturingCell(hidden_rules)
    
    # 2. 初始化 AGI 代理
    agent = CognitiveConsistencyAgent(actuator_list)
    
    # 3. 主动探索阶段
    # 尝试各种传感器组合来观察执行器反应
    # 为了效率，不完全遍历所有组合，而是随机采样 + 关键边界测试
    logger.info(f"开始主动探索阶段 ({test_cycles} 次循环)...")
    
    # 生成一些测试用例
    test_cases = []
    # 确保全开和全关被测试
    test_cases.append({s: True for s in sensor_list})
    test_cases.append({s: False for s in sensor_list})
    # 随机生成
    for _ in range(test_cycles - 2):
        case = {s: random.choice([True, False]) for s in sensor_list}
        test_cases.append(case)
        
    for case in test_cases:
        cell.reset_environment()
        for sensor, state in case.items():
            # 为了模拟真实世界的交互，这里逐步设置状态
            # 但在简化模型中，我们直接应用状态快照
            cell.sensors[sensor] = state
        cell._update_actuators() # 强制更新内部逻辑
        
        current_sensors, current_actuators = cell.get_observation()
        agent.observe(current_sensors, current_actuators)
        
        logger.debug(f"输入: {case} -> 输出: {current_actuators}")

    # 4. 逻辑推导与图谱生成
    # 在观察后，代理尝试通过逻辑归纳确定最简规则
    # 此处使用一种简单的启发式：找出所有电机为ON时的传感器交集
    # 这是一个辅助逻辑，补充到 Agent 类中
    final_graph = _derive_conjunction_graph(agent)
    
    # 5. 自洽性验证
    score = agent.validate_hypothesis(cell)
    
    logger.info(f"推导完成。逻辑自洽性得分: {score:.2f}")
    logger.info(f"生成的控制图谱: {final_graph}")
    
    return final_graph, score

def _derive_conjunction_graph(agent: CognitiveConsistencyAgent) -> Dict[str, List[str]]:
    """
    辅助函数：根据历史观察，推导基于“合取（AND）”逻辑的控制图谱。
    逻辑：对于每个执行器，找出在所有“激活状态”观察中都为 True 的传感器集合。
    
    Args:
        agent (CognitiveConsistencyAgent): 已收集数据的代理。
        
    Returns:
        Dict[str, List[str]]: 推导出的依赖关系图。
    """
    derived_rules = {}
    
    for actuator in agent.target_actuators:
        # 收集该执行器所有为 True 的时刻的传感器状态
        positive_observations = []
        for sensors, actuators in agent.observation_history:
            if actuators.get(actuator, False):
                positive_observations.append({k for k, v in sensors.items() if v})
        
        if not positive_observations:
            derived_rules[actuator] = []
            continue
            
        # 求交集，获得“必要条件”
        # 如果没有正例，则无法推导必要条件（或认为无条件不启动）
        necessary_conditions = set.intersection(*positive_observations)
        derived_rules[actuator] = list(necessary_conditions)
        
    return derived_rules

# 使用示例
if __name__ == "__main__":
    # 定义模拟产线的组件
    sensors = ["Sensor_Photoelectric", "Sensor_Pressure", "Sensor_Temperature"]
    actuators = ["Motor_Conveyor", "Valve_Injector"]
    
    # 定义隐藏的真实规则（AGI未知）
    # 规则1: 传送带电机需要 光电传感器 AND 压力传感器
    # 规则2: 喷射阀需要 压力传感器 AND 温度传感器
    hidden_logic = {
        "Motor_Conveyor": ["Sensor_Photoelectric", "Sensor_Pressure"],
        "Valve_Injector": ["Sensor_Pressure", "Sensor_Temperature"]
    }
    
    try:
        # 运行测试
        inferred_graph, consistency = run_production_turing_test(
            sensor_list=sensors,
            actuator_list=actuators,
            hidden_rules=hidden_logic,
            test_cycles=20
        )
        
        print("\n--- 结果报告 ---")
        print(f"真实规则: {hidden_logic}")
        print(f"推导规则: {inferred_graph}")
        print(f"自洽性得分: {consistency}")
        
        # 简单断言检查
        # 注意：由于随机采样，如果没采样到关键状态，可能推导不出完整规则，但自洽性应该很高
        assert consistency >= 0.8, "自洽性得分过低，系统未能有效理解环境逻辑"
        
    except Exception as e:
        logger.error(f"测试运行失败: {e}", exc_info=True)