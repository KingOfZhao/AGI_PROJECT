"""
物理-数字对抗性加固系统

该模块实现了一个在工业设计和复杂软件系统中应用的对抗性加固系统。
系统模拟传统工艺中的破坏性检验，通过生成极端边缘用例来测试系统鲁棒性。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
import json
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdversarialHardeningSystem")


class NodeStatus(Enum):
    """节点状态枚举"""
    UNTESTED = auto()
    TESTING = auto()
    HARDENED = auto()
    FAILED = auto()


class PhysicalDecayType(Enum):
    """物理衰减类型枚举"""
    MATERIAL_FATIGUE = auto()
    VOLTAGE_FLUCTUATION = auto()
    THERMAL_STRESS = auto()
    MECHANICAL_VIBRATION = auto()
    CORROSIVE_ENVIRONMENT = auto()


@dataclass
class TestNode:
    """测试节点数据结构"""
    node_id: str
    parameters: Dict[str, Union[float, int, str]]
    status: NodeStatus = NodeStatus.UNTESTED
    robustness_score: float = 0.0
    last_tested: Optional[datetime] = None
    test_history: List[Dict] = None

    def __post_init__(self):
        if self.test_history is None:
            self.test_history = []


class AdversarialHardeningSystem:
    """
    物理-数字对抗性加固系统
    
    该系统通过模拟物理衰减和极端条件来测试系统节点的鲁棒性，
    只有通过这些"数字淬火"测试的节点才会被标记为高鲁棒性节点。
    
    属性:
        nodes (Dict[str, TestNode]): 系统中的测试节点字典
        decay_profiles (Dict[PhysicalDecayType, Dict]): 物理衰减配置文件
        hardening_threshold (float): 加固阈值(0.0-1.0)
    """
    
    def __init__(self, hardening_threshold: float = 0.85):
        """
        初始化对抗性加固系统
        
        参数:
            hardening_threshold: 加固阈值，默认为0.85
        """
        self._validate_threshold(hardening_threshold)
        self.nodes: Dict[str, TestNode] = {}
        self.decay_profiles = self._initialize_decay_profiles()
        self.hardening_threshold = hardening_threshold
        logger.info("AdversarialHardeningSystem initialized with threshold %.2f", hardening_threshold)
    
    def _validate_threshold(self, threshold: float) -> None:
        """验证阈值是否在有效范围内"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Hardening threshold must be between 0.0 and 1.0, got {threshold}")
    
    def _initialize_decay_profiles(self) -> Dict[PhysicalDecayType, Dict]:
        """初始化物理衰减配置文件"""
        return {
            PhysicalDecayType.MATERIAL_FATIGUE: {
                "stress_range": (0.8, 1.5),
                "cycles": (1000, 10000),
                "probability": 0.15
            },
            PhysicalDecayType.VOLTAGE_FLUCTUATION: {
                "voltage_range": (0.7, 1.3),
                "frequency": (10, 1000),
                "probability": 0.12
            },
            PhysicalDecayType.THERMAL_STRESS: {
                "temp_range": (-40, 120),
                "rate": (0.1, 5.0),
                "probability": 0.18
            },
            PhysicalDecayType.MECHANICAL_VIBRATION: {
                "amplitude": (0.1, 2.0),
                "frequency": (5, 200),
                "probability": 0.10
            },
            PhysicalDecayType.CORROSIVE_ENVIRONMENT: {
                "concentration": (0.01, 0.5),
                "duration": (10, 1000),
                "probability": 0.08
            }
        }
    
    def add_node(self, node_id: str, parameters: Dict[str, Union[float, int, str]]) -> None:
        """
        添加测试节点到系统
        
        参数:
            node_id: 节点唯一标识符
            parameters: 节点参数字典
        """
        if not node_id:
            raise ValueError("Node ID cannot be empty")
        if node_id in self.nodes:
            raise ValueError(f"Node with ID {node_id} already exists")
        
        self.nodes[node_id] = TestNode(node_id=node_id, parameters=parameters)
        logger.info("Added new node: %s", node_id)
    
    def generate_adversarial_examples(
        self,
        node: TestNode,
        num_examples: int = 10,
        decay_types: Optional[List[PhysicalDecayType]] = None
    ) -> List[Dict]:
        """
        为指定节点生成对抗性示例
        
        参数:
            node: 要测试的节点
            num_examples: 要生成的示例数量
            decay_types: 要模拟的衰减类型列表，None表示使用所有类型
            
        返回:
            生成的对抗性示例列表
        """
        if decay_types is None:
            decay_types = list(PhysicalDecayType)
        
        examples = []
        for _ in range(num_examples):
            decay_type = np.random.choice(decay_types)
            profile = self.decay_profiles[decay_type]
            
            example = {
                "decay_type": decay_type.name,
                "parameters": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # 根据衰减类型生成特定参数
            if decay_type == PhysicalDecayType.MATERIAL_FATIGUE:
                example["parameters"] = {
                    "stress_factor": np.random.uniform(*profile["stress_range"]),
                    "cycles": np.random.randint(*profile["cycles"])
                }
            elif decay_type == PhysicalDecayType.VOLTAGE_FLUCTUATION:
                example["parameters"] = {
                    "voltage_factor": np.random.uniform(*profile["voltage_range"]),
                    "frequency_hz": np.random.uniform(*profile["frequency"])
                }
            elif decay_type == PhysicalDecayType.THERMAL_STRESS:
                example["parameters"] = {
                    "temperature_c": np.random.uniform(*profile["temp_range"]),
                    "change_rate_c_per_min": np.random.uniform(*profile["rate"])
                }
            elif decay_type == PhysicalDecayType.MECHANICAL_VIBRATION:
                example["parameters"] = {
                    "amplitude_mm": np.random.uniform(*profile["amplitude"]),
                    "frequency_hz": np.random.uniform(*profile["frequency"])
                }
            elif decay_type == PhysicalDecayType.CORROSIVE_ENVIRONMENT:
                example["parameters"] = {
                    "concentration_mol": np.random.uniform(*profile["concentration"]),
                    "duration_hours": np.random.randint(*profile["duration"])
                }
            
            examples.append(example)
        
        return examples
    
    def _evaluate_node_response(
        self,
        node: TestNode,
        adversarial_example: Dict
    ) -> float:
        """
        评估节点对对抗性示例的响应
        
        这是一个模拟函数，实际应用中应替换为真实的测试逻辑
        
        参数:
            node: 测试节点
            adversarial_example: 对抗性示例
            
        返回:
            节点对该示例的鲁棒性得分(0.0-1.0)
        """
        # 模拟评估逻辑 - 实际应用中这里应该是真实的测试代码
        decay_type = adversarial_example["decay_type"]
        profile = self.decay_profiles[PhysicalDecayType[decay_type]]
        
        # 基于参数计算基本得分
        params = adversarial_example["parameters"]
        base_score = 0.8  # 假设基本性能良好
        
        # 根据不同的衰减类型调整得分
        if decay_type == "MATERIAL_FATIGUE":
            stress_factor = params["stress_factor"]
            cycles = params["cycles"]
            # 高应力和高循环次数会降低得分
            score = base_score * (1 - (stress_factor - 0.8) / 0.7) * (1 - np.log10(cycles) / 4)
        elif decay_type == "VOLTAGE_FLUCTUATION":
            voltage_factor = params["voltage_factor"]
            # 电压偏差越大，得分越低
            score = base_score * (1 - abs(voltage_factor - 1.0) / 0.3)
        elif decay_type == "THERMAL_STRESS":
            temperature = params["temperature_c"]
            change_rate = params["change_rate_c_per_min"]
            # 极端温度和快速变化会降低得分
            score = base_score * (1 - (abs(temperature - 20) / 100)) * (1 - change_rate / 5.0)
        else:
            # 其他类型使用默认评分
            score = base_score
        
        # 添加一些随机性以模拟真实测试的不确定性
        score += np.random.normal(0, 0.05)
        
        # 确保得分在0.0-1.0范围内
        return max(0.0, min(1.0, score))
    
    def harden_node(
        self,
        node_id: str,
        num_iterations: int = 5,
        examples_per_iteration: int = 10,
        decay_types: Optional[List[PhysicalDecayType]] = None
    ) -> Tuple[bool, Dict]:
        """
        对指定节点执行对抗性加固过程
        
        参数:
            node_id: 要加固的节点ID
            num_iterations: 加固迭代次数
            examples_per_iteration: 每次迭代生成的示例数
            decay_types: 要测试的衰减类型列表
            
        返回:
            Tuple[是否通过加固, 测试结果摘要]
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in system")
        
        node = self.nodes[node_id]
        node.status = NodeStatus.TESTING
        logger.info("Starting hardening process for node: %s", node_id)
        
        results = {
            "iterations": [],
            "overall_score": 0.0,
            "passed": False,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        try:
            total_score = 0.0
            for i in range(num_iterations):
                # 生成对抗性示例
                examples = self.generate_adversarial_examples(
                    node, examples_per_iteration, decay_types
                )
                
                # 评估每个示例
                iteration_scores = []
                for example in examples:
                    score = self._evaluate_node_response(node, example)
                    iteration_scores.append(score)
                    node.test_history.append({
                        "example": example,
                        "score": score
                    })
                
                # 计算本次迭代的平均得分
                avg_score = np.mean(iteration_scores)
                min_score = np.min(iteration_scores)
                max_score = np.max(iteration_scores)
                
                iteration_result = {
                    "iteration": i + 1,
                    "avg_score": avg_score,
                    "min_score": min_score,
                    "max_score": max_score,
                    "examples_tested": len(examples)
                }
                
                results["iterations"].append(iteration_result)
                total_score += avg_score
                
                logger.debug(
                    "Iteration %d: avg=%.2f, min=%.2f, max=%.2f",
                    i + 1, avg_score, min_score, max_score
                )
            
            # 计算总体得分
            overall_score = total_score / num_iterations
            node.robustness_score = overall_score
            node.last_tested = datetime.now()
            
            # 判断是否通过加固
            passed = overall_score >= self.hardening_threshold
            node.status = NodeStatus.HARDENED if passed else NodeStatus.FAILED
            
            results["overall_score"] = overall_score
            results["passed"] = passed
            results["end_time"] = datetime.now().isoformat()
            
            logger.info(
                "Hardening completed for node %s: %s (score=%.2f)",
                node_id, "PASSED" if passed else "FAILED", overall_score
            )
            
            return passed, results
        
        except Exception as e:
            node.status = NodeStatus.FAILED
            logger.error("Error during hardening of node %s: %s", node_id, str(e))
            results["error"] = str(e)
            results["passed"] = False
            results["end_time"] = datetime.now().isoformat()
            return False, results
    
    def get_node_status(self, node_id: str) -> Dict:
        """
        获取节点状态信息
        
        参数:
            node_id: 节点ID
            
        返回:
            包含节点状态信息的字典
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in system")
        
        node = self.nodes[node_id]
        return {
            "node_id": node.node_id,
            "status": node.status.name,
            "robustness_score": node.robustness_score,
            "last_tested": node.last_tested.isoformat() if node.last_tested else None,
            "test_count": len(node.test_history)
        }
    
    def export_results(self, file_path: str) -> None:
        """
        将测试结果导出到JSON文件
        
        参数:
            file_path: 输出文件路径
        """
        export_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "hardening_threshold": self.hardening_threshold,
                "node_count": len(self.nodes)
            },
            "nodes": []
        }
        
        for node in self.nodes.values():
            node_data = {
                "node_id": node.node_id,
                "parameters": node.parameters,
                "status": node.status.name,
                "robustness_score": node.robustness_score,
                "last_tested": node.last_tested.isoformat() if node.last_tested else None,
                "test_history": node.test_history
            }
            export_data["nodes"].append(node_data)
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info("Exported results to %s", file_path)


# 使用示例
if __name__ == "__main__":
    # 初始化对抗性加固系统
    hardening_system = AdversarialHardeningSystem(hardening_threshold=0.85)
    
    # 添加测试节点
    hardening_system.add_node(
        node_id="industrial_controller_01",
        parameters={
            "max_voltage": 24.0,
            "operating_temp_range": (-20, 60),
            "ip_rating": "IP65",
            "mtbf_hours": 50000
        }
    )
    
    # 执行对抗性加固
    passed, results = hardening_system.harden_node(
        node_id="industrial_controller_01",
        num_iterations=3,
        examples_per_iteration=5
    )
    
    # 获取节点状态
    status = hardening_system.get_node_status("industrial_controller_01")
    print("\nNode Status:")
    print(json.dumps(status, indent=2))
    
    # 导出结果
    hardening_system.export_results("hardening_results.json")
    
    print("\nHardening Summary:")
    print(f"Overall Score: {results['overall_score']:.2f}")
    print(f"Result: {'PASSED' if passed else 'FAILED'}")
    print(f"Test Iterations: {len(results['iterations'])}")