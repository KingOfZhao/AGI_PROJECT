"""
基于预测编码理论的软件测试沙箱实现
该沙箱模拟人类认知的预测-验证循环，通过生成反事实测试用例探索未知缺陷
"""

import random
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PredictiveCodingSandbox")

@dataclass
class SystemState:
    """系统状态表示"""
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    context: Dict[str, Any]
    timestamp: float

@dataclass
class Prediction:
    """预测编码模型输出"""
    expected_output: Dict[str, Any]
    confidence: float
    uncertainty_factors: List[str]

@dataclass
class TestCase:
    """测试用例表示"""
    inputs: Dict[str, Any]
    metadata: Dict[str, Any]
    attack_vector: Optional[str] = None

class PredictiveModel:
    """
    预测编码模型 - 模拟人类认知的预测生成过程
    基于当前状态生成对系统输出的预测
    """
    
    def __init__(self, system_model: Dict[str, Any]):
        """
        初始化预测模型
        
        Args:
            system_model: 系统行为模型（包含正常行为模式）
        """
        self.model = system_model
        self.prediction_history = []
        
    def predict(self, current_state: SystemState) -> Prediction:
        """
        基于当前状态生成预测
        
        Args:
            current_state: 当前系统状态
            
        Returns:
            Prediction: 包含预测结果和不确定性因素
        """
        try:
            # 模拟预测过程（实际应用中可使用ML模型）
            expected_output = {}
            uncertainty_factors = []
            
            # 基于系统模型生成预测
            for key, value in current_state.inputs.items():
                if key in self.model:
                    # 添加随机波动模拟认知不确定性
                    noise = np.random.normal(0, 0.1)
                    expected_output[key] = self.model[key] * (1 + noise)
                else:
                    # 未知输入增加不确定性
                    uncertainty_factors.append(key)
                    expected_output[key] = value * random.uniform(0.8, 1.2)
            
            # 计算预测置信度（基于输入熟悉度）
            confidence = 1.0 - (len(uncertainty_factors) / max(len(current_state.inputs), 1))
            
            prediction = Prediction(
                expected_output=expected_output,
                confidence=confidence,
                uncertainty_factors=uncertainty_factors
            )
            
            self.prediction_history.append(prediction)
            return prediction
            
        except Exception as e:
            logger.error(f"预测生成失败: {str(e)}")
            raise RuntimeError(f"预测模型错误: {str(e)}")

class TestCaseGenerator:
    """
    测试用例生成器 - 基于预测编码理论生成反事实测试用例
    专注于探索边界条件和潜在缺陷
    """
    
    def __init__(self, system_model: Dict[str, Any]):
        """
        初始化测试用例生成器
        
        Args:
            system_model: 系统行为模型
        """
        self.system_model = system_model
        self.attack_vectors = [
            "boundary_values",  # 边界值测试
            "invalid_inputs",   # 无效输入
            "resource_stress",  # 资源压力
            "state_corruption", # 状态破坏
            "time_anomalies"    # 时间异常
        ]
        
    def generate_attack_case(self, prediction: Prediction) -> TestCase:
        """
        基于预测生成攻击性测试用例
        
        Args:
            prediction: 当前预测结果
            
        Returns:
            TestCase: 攻击性测试用例
        """
        try:
            # 选择攻击向量（基于预测不确定性）
            attack_vector = random.choice(self.attack_vectors)
            
            # 基于预测不确定性生成针对性测试
            test_inputs = {}
            metadata = {
                "attack_vector": attack_vector,
                "confidence": prediction.confidence,
                "uncertainty": prediction.uncertainty_factors
            }
            
            if attack_vector == "boundary_values":
                # 生成边界值测试用例
                for key in prediction.expected_output:
                    base_val = prediction.expected_output[key]
                    test_inputs[key] = self._generate_boundary_value(base_val)
                    
            elif attack_vector == "invalid_inputs":
                # 生成无效输入
                for key in prediction.expected_output:
                    test_inputs[key] = self._generate_invalid_value(key)
                    
            elif attack_vector == "resource_stress":
                # 生成资源压力测试
                test_inputs = {
                    "memory_load": 10**9,  # 1GB内存
                    "cpu_load": 0.95,     # 95% CPU
                    "disk_io": 10**8      # 高磁盘IO
                }
                
            elif attack_vector == "state_corruption":
                # 生成状态破坏测试
                test_inputs = {
                    "corrupted_state": True,
                    "invalid_pointer": 0xDEADBEEF
                }
                
            elif attack_vector == "time_anomalies":
                # 生成时间异常测试
                test_inputs = {
                    "time_jump": 86400,   # 24小时时间跳跃
                    "negative_timestamp": -1
                }
            
            return TestCase(
                inputs=test_inputs,
                metadata=metadata,
                attack_vector=attack_vector
            )
            
        except Exception as e:
            logger.error(f"攻击用例生成失败: {str(e)}")
            raise RuntimeError(f"测试用例生成错误: {str(e)}")
    
    def _generate_boundary_value(self, base_value: float) -> float:
        """生成边界值测试数据"""
        if isinstance(base_value, (int, float)):
            return random.choice([
                base_value * 0.0,      # 零值
                base_value * 1e-10,    # 极小值
                base_value * 1e10,     # 极大值
                float('inf'),          # 正无穷
                float('-inf'),         # 负无穷
                float('nan')           # 非数值
            ])
        return base_value
    
    def _generate_invalid_value(self, key: str) -> Any:
        """生成无效输入值"""
        invalid_generators = {
            "string": lambda: "".join(chr(random.randint(0, 255)) for _ in range(1000)),
            "number": lambda: random.choice(["not_a_number", None, [], {}]),
            "list": lambda: [random.random() for _ in range(10**6)],
            "dict": lambda: {str(i): i for i in range(10**5)}
        }
        return invalid_generators.get(key, lambda: None)()

class TestExecutor:
    """
    测试执行器 - 在受控环境中执行测试用例
    模拟系统行为并捕获异常
    """
    
    def __init__(self, system_under_test: Any):
        """
        初始化测试执行器
        
        Args:
            system_under_test: 被测系统实例
        """
        self.sut = system_under_test
        self.execution_history = []
        
    def execute(self, test_case: TestCase) -> Tuple[SystemState, Optional[Exception]]:
        """
        执行测试用例
        
        Args:
            test_case: 测试用例
            
        Returns:
            Tuple[SystemState, Optional[Exception]]: 系统状态和异常信息
        """
        try:
            # 模拟系统执行（实际应用中替换为真实系统调用）
            state = SystemState(
                inputs=test_case.inputs,
                outputs={},
                context={"attack_vector": test_case.attack_vector},
                timestamp=random.random()
            )
            
            # 模拟系统行为（根据攻击向量产生不同结果）
            if test_case.attack_vector == "boundary_values":
                # 边界值测试可能产生数值错误
                for key, value in test_case.inputs.items():
                    if isinstance(value, float) and np.isnan(value):
                        raise ValueError(f"NaN值检测: {key}")
                        
            elif test_case.attack_vector == "invalid_inputs":
                # 无效输入类型错误
                if "string" in test_case.inputs and not isinstance(test_case.inputs["string"], str):
                    raise TypeError("字符串类型错误")
                    
            elif test_case.attack_vector == "resource_stress":
                # 资源压力模拟
                if test_case.inputs.get("cpu_load", 0) > 0.9:
                    raise MemoryError("CPU资源耗尽")
                    
            elif test_case.attack_vector == "state_corruption":
                # 状态破坏模拟
                if test_case.inputs.get("corrupted_state"):
                    raise RuntimeError("系统状态损坏")
                    
            elif test_case.attack_vector == "time_anomalies":
                # 时间异常模拟
                if test_case.inputs.get("time_jump", 0) > 86400:
                    raise TimeoutError("时间跳跃异常")
            
            # 模拟正常输出
            state.outputs = {
                "status": "success",
                "result": random.random()
            }
            
            self.execution_history.append(state)
            return state, None
            
        except Exception as e:
            # 捕获异常并记录
            state.outputs = {
                "status": "failure",
                "error": str(e)
            }
            self.execution_history.append(state)
            return state, e

class DiscrepancyAnalyzer:
    """
    差异分析器 - 比较预测与实际结果
    识别预测编码理论与实际系统行为之间的差异
    """
    
    def analyze(self, prediction: Prediction, actual_state: SystemState) -> Dict[str, Any]:
        """
        分析预测与实际结果的差异
        
        Args:
            prediction: 预测结果
            actual_state: 实际系统状态
            
        Returns:
            Dict[str, Any]: 差异分析报告
        """
        try:
            discrepancies = []
            
            # 比较输出差异
            for key in prediction.expected_output:
                if key in actual_state.outputs:
                    expected = prediction.expected_output[key]
                    actual = actual_state.outputs.get(key)
                    
                    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                        diff = abs(expected - actual)
                        if diff > 0.1:  # 差异阈值
                            discrepancies.append({
                                "type": "output_mismatch",
                                "field": key,
                                "expected": expected,
                                "actual": actual,
                                "difference": diff
                            })
            
            # 检测异常情况
            if actual_state.outputs.get("status") == "failure":
                discrepancies.append({
                    "type": "unpredicted_exception",
                    "error": actual_state.outputs.get("error"),
                    "confidence": prediction.confidence
                })
            
            # 生成分析报告
            report = {
                "prediction_confidence": prediction.confidence,
                "actual_status": actual_state.outputs.get("status"),
                "discrepancies": discrepancies,
                "severity": self._calculate_severity(discrepancies),
                "recommendations": self._generate_recommendations(discrepancies)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"差异分析失败: {str(e)}")
            raise RuntimeError(f"差异分析错误: {str(e)}")
    
    def _calculate_severity(self, discrepancies: List[Dict]) -> str:
        """计算差异严重程度"""
        if not discrepancies:
            return "none"
        
        critical_count = sum(1 for d in discrepancies if d.get("type") == "unpredicted_exception")
        if critical_count > 0:
            return "critical"
        
        high_diff_count = sum(1 for d in discrepancies if d.get("difference", 0) > 1.0)
        if high_diff_count > 0:
            return "high"
        
        return "medium"
    
    def _generate_recommendations(self, discrepancies: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for discrepancy in discrepancies:
            if discrepancy["type"] == "output_mismatch":
                recommendations.append(f"检查字段 {discrepancy['field']} 的计算逻辑")
            elif discrepancy["type"] == "unpredicted_exception":
                recommendations.append(f"增强异常处理: {discrepancery['error']}")
        
        if not recommendations:
            recommendations.append("系统行为符合预期，继续探索边界条件")
        
        return recommendations

class PredictiveCodingSandbox:
    """
    基于预测编码理论的测试沙箱主类
    协调预测、测试执行和差异分析
    """
    
    def __init__(self, system_model: Dict[str, Any], system_under_test: Any):
        """
        初始化测试沙箱
        
        Args:
            system_model: 系统行为模型
            system_under_test: 被测系统实例
        """
        self.predictive_model = PredictiveModel(system_model)
        self.test_generator = TestCaseGenerator(system_model)
        self.test_executor = TestExecutor(system_under_test)
        self.analyzer = DiscrepancyAnalyzer()
        self.test_results = []
        
    def run_test_cycle(self, initial_state: SystemState, max_cycles: int = 10) -> List[Dict]:
        """
        运行完整的测试周期
        
        Args:
            initial_state: 初始系统状态
            max_cycles: 最大测试周期数
            
        Returns:
            List[Dict]: 测试结果报告
        """
        try:
            current_state = initial_state
            results = []
            
            for cycle in range(max_cycles):
                logger.info(f"开始测试周期 {cycle + 1}/{max_cycles}")
                
                # 1. 生成预测
                prediction = self.predictive_model.predict(current_state)
                logger.info(f"预测置信度: {prediction.confidence:.2f}")
                
                # 2. 生成攻击性测试用例
                test_case = self.test_generator.generate_attack_case(prediction)
                logger.info(f"生成攻击向量: {test_case.attack_vector}")
                
                # 3. 执行测试
                actual_state, error = self.test_executor.execute(test_case)
                
                # 4. 分析差异
                analysis = self.analyzer.analyze(prediction, actual_state)
                results.append({
                    "cycle": cycle + 1,
                    "prediction": prediction,
                    "test_case": test_case,
                    "actual_state": actual_state,
                    "analysis": analysis,
                    "error": str(error) if error else None
                })
                
                # 5. 更新当前状态（基于实际结果）
                current_state = actual_state
                
                # 6. 检查终止条件
                if analysis["severity"] == "critical":
                    logger.warning("发现严重缺陷，提前终止测试")
                    break
            
            self.test_results = results
            return results
            
        except Exception as e:
            logger.error(f"测试周期执行失败: {str(e)}")
            raise RuntimeError(f"测试沙箱错误: {str(e)}")
    
    def generate_report(self) -> Dict:
        """生成测试报告摘要"""
        if not self.test_results:
            return {"status": "no_tests_run"}
        
        total_cycles = len(self.test_results)
        critical_issues = sum(1 for r in self.test_results if r["analysis"]["severity"] == "critical")
        high_issues = sum(1 for r in self.test_results if r["analysis"]["severity"] == "high")
        
        return {
            "total_test_cycles": total_cycles,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "average_confidence": np.mean([r["prediction"].confidence for r in self.test_results]),
            "recommendations": self._generate_final_recommendations()
        }
    
    def _generate_final_recommendations(self) -> List[str]:
        """生成最终建议"""
        recommendations = []
        
        # 分析所有测试结果
        for result in self.test_results:
            analysis = result["analysis"]
            if analysis["severity"] in ["critical", "high"]:
                recommendations.extend(analysis["recommendations"])
        
        # 去重并限制数量
        unique_recommendations = list(set(recommendations))[:5]
        
        if not unique_recommendations:
            unique_recommendations = ["系统行为符合预期，建议增加测试复杂度"]
        
        return unique_recommendations

# 示例使用
if __name__ == "__main__":
    # 定义系统模型（模拟计算器行为）
    system_model = {
        "addition": lambda x, y: x + y,
        "subtraction": lambda x, y: x - y,
        "multiplication": lambda x, y: x * y,
        "division": lambda x, y: x / y if y != 0 else float('inf')
    }
    
    # 模拟被测系统（简化版）
    class MockSystem:
        def process(self, inputs):
            # 模拟系统处理逻辑
            return {"result": random.random()}
    
    # 初始化测试沙箱
    sandbox = PredictiveCodingSandbox(
        system_model=system_model,
        system_under_test=MockSystem()
    )
    
    # 创建初始状态
    initial_state = SystemState(
        inputs={"x": 10, "y": 5, "operation": "addition"},
        outputs={},
        context={"test_type": "initial"},
        timestamp=0.0
    )
    
    # 运行测试周期
    results = sandbox.run_test_cycle(initial_state, max_cycles=5)
    
    # 生成报告
    report = sandbox.generate_report()
    
    # 打印结果
    print("\n=== 测试结果摘要 ===")
    print(f"总测试周期: {report['total_test_cycles']}")
    print(f"严重问题: {report['critical_issues']}")
    print(f"高风险问题: {report['high_issues']}")
    print(f"平均预测置信度: {report['average_confidence']:.2f}")
    print("\n建议:")
    for rec in report['recommendations']:
        print(f"- {rec}")