"""
模块: auto_如何构建_反脆弱性_测试用例自动生成器_5748f9
描述: 实现针对核心逻辑节点的反脆弱性测试用例自动生成与逻辑崩溃阈值量化。
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class TestCase:
    """测试用例数据结构"""
    test_id: str
    inputs: Dict[str, Any]
    category: str  # 'edge', 'fuzz', 'adversarial'
    description: str
    expected_behavior: str = "Should handle gracefully or raise specific exception"

@dataclass
class StressTestResult:
    """压力测试结果数据结构"""
    test_case: TestCase
    passed: bool
    exception_type: Optional[str] = None
    exception_msg: Optional[str] = None
    execution_time_ms: float = 0.0
    resource_spike: bool = False  # 是否引发资源（内存/CPU）异常

@dataclass
class NodeVulnerabilityReport:
    """节点脆弱性评估报告"""
    node_name: str
    total_tests: int = 0
    failures: int = 0
    crashes: int = 0  # 未捕获的异常
    logic_collapse_score: float = 0.0  # 0.0 (Robust) - 100.0 (Fragile)
    failure_points: List[str] = field(default_factory=list)

# --- 辅助函数 ---

def validate_numeric_input(value: Any, param_name: str) -> float:
    """
    验证并转换数值输入。
    
    Args:
        value: 输入值
        param_name: 参数名称（用于错误提示）
        
    Returns:
        float: 转换后的浮点数
        
    Raises:
        ValueError: 如果输入无法转换为数值
    """
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        logger.error(f"参数 {param_name} 必须是数值类型，收到: {type(value)}")
        raise ValueError(f"Invalid numeric input for {param_name}") from e

def calculate_collapse_score(results: List[StressTestResult]) -> float:
    """
    计算逻辑崩溃阈值/得分。
    公式: (Crashes * 1.0 + Failures * 0.5) / Total * 100
    权重解释：未捕获的异常比断言失败更危险。
    
    Args:
        results: 测试结果列表
        
    Returns:
        float: 崩溃得分 (0-100)
    """
    if not results:
        return 0.0
    
    total = len(results)
    crashes = sum(1 for r in results if not r.passed and r.exception_type is not None)
    failures = sum(1 for r in results if not r.passed and r.exception_type is None)
    
    score = ((crashes * 1.0) + (failures * 0.5)) / total * 100
    return round(score, 2)

# --- 核心类与函数 ---

class AdversarialGenerator:
    """
    反脆弱性测试用例生成器。
    
    自动生成针对数值、边界和逻辑约束的攻击性测试用例。
    """
    
    def __init__(self, node_name: str):
        self.node_name = node_name
        self._test_case_counter = 0

    def _generate_test_id(self) -> str:
        self._test_case_counter += 1
        return f"{self.node_name}_adv_{self._test_case_counter:04d}"

    def generate_numeric_adversarials(self, param_name: str, baseline: float = 1.0) -> List[TestCase]:
        """
        针对数值型参数生成对抗性用例。
        包含：负成本、极大值、NaN、Infinity、微小值。
        
        Args:
            param_name: 参数名称
            baseline: 基准值，用于生成相对偏移
            
        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        test_cases = []
        
        # 定义攻击策略
        strategies = [
            ("Negative/Reverse", -abs(baseline) * 10),
            ("Huge Value", baseline * 1e9),
            ("Near Zero", 1e-9),
            ("Python Max Float", 1.7976931348623157e+308),
            ("NaN Attack", float('nan')),
            ("Positive Infinity", float('inf')),
            ("Negative Infinity", float('-inf')),
        ]
        
        for desc, value in strategies:
            tc = TestCase(
                test_id=self._generate_test_id(),
                inputs={param_name: value},
                category="adversarial",
                description=f"Testing {param_name} with {desc} ({value})"
            )
            test_cases.append(tc)
            
        return test_cases

    def generate_logic_edge_cases(self, logic_type: str, params: Dict[str, Any]) -> List[TestCase]:
        """
        根据逻辑类型生成边缘攻击用例。
        
        Args:
            logic_type: 逻辑类型，如 'pricing', 'supply_chain', 'authentication'
            params: 相关参数
            
        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        cases = []
        if logic_type == 'pricing':
            # 针对定价逻辑：负价格、零价格、价格高于GDP等
            cases.append(TestCase(self._generate_test_id(), {"price": -100, "quantity": 10}, "edge", "Negative Price"))
            cases.append(TestCase(self._generate_test_id(), {"price": 0, "quantity": 0}, "edge", "Zero Transaction"))
            
        elif logic_type == 'supply_chain':
            # 针对供应链：无限需求、负库存
            cases.append(TestCase(self._generate_test_id(), {"demand": float('inf'), "stock": 100}, "edge", "Infinite Demand"))
            cases.append(TestCase(self._generate_test_id(), {"demand": 50, "stock": -10}, "edge", "Negative Stock"))
            
        return cases

def stress_test_node(
    target_function: Callable,
    test_cases: List[TestCase],
    catch_exceptions: bool = True
) -> NodeVulnerabilityReport:
    """
    对目标节点函数执行压力测试并量化崩溃阈值。
    
    Args:
        target_function: 需要测试的目标函数（节点逻辑）
        test_cases: 测试用例列表
        catch_exceptions: 是否捕获所有异常（设为False则中断测试）
        
    Returns:
        NodeVulnerabilityReport: 包含崩溃得分的完整报告
        
    Example:
        >>> def pricing_engine(price, quantity):
        ...     if price < 0: raise ValueError("Invalid price")
        ...     return price * quantity
        >>> generator = AdversarialGenerator("PricingNode")
        >>> cases = generator.generate_numeric_adversarials("price")
        >>> report = stress_test_node(pricing_engine, cases)
        >>> print(report.logic_collapse_score)
    """
    report = NodeVulnerabilityReport(node_name=target_function.__name__)
    results = []
    
    logger.info(f"Starting stress test for node: {target_function.__name__} with {len(test_cases)} cases.")
    
    for case in test_cases:
        passed = False
        ex_type = None
        ex_msg = None
        
        try:
            # 尝试执行目标节点
            # 注意：这里假设target_function接受 **case.inputs
            # 如果签名不匹配，由inspect机制或错误处理捕获
            result = target_function(**case.inputs)
            
            # 简单的返回值验证（防止返回NaN或Inf导致后续节点崩溃）
            if isinstance(result, (int, float)):
                if math.isnan(result) or math.isinf(result):
                    raise ArithmeticError("Function returned NaN or Infinity")
            
            passed = True
            logger.debug(f"Case {case.test_id} passed.")
            
        except Exception as e:
            ex_type = type(e).__name__
            ex_msg = str(e)
            logger.warning(f"Case {case.test_id} failed: {ex_type} - {ex_msg}")
            if not catch_exceptions:
                raise
        finally:
            res = StressTestResult(
                test_case=case,
                passed=passed,
                exception_type=ex_type,
                exception_msg=ex_msg
            )
            results.append(res)
            
    report.total_tests = len(test_cases)
    report.failures = sum(1 for r in results if not r.passed)
    report.crashes = sum(1 for r in results if r.exception_type and r.exception_type not in ['ValueError', 'TypeError'])
    report.logic_collapse_score = calculate_collapse_score(results)
    report.failure_points = [r.test_case.description for r in results if not r.passed]
    
    return report

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 定义一个典型的业务节点：小摊贩定价逻辑
    def street_vendor_pricing(cost: float, markup: float, quantity: int) -> float:
        """
        计算总价。如果输入不合理应抛出异常。
        """
        # 假设这里有一些防御性编程，但可能不完整
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
            
        # 逻辑：如果markup过高，可能会导致溢出或业务逻辑错误
        # 这里故意不处理 infinity 或极大值，以演示漏洞
        total = (cost + cost * markup) * quantity
        return total

    # 2. 初始化生成器
    generator = AdversarialGenerator("StreetVendorNode")
    
    # 3. 生成对抗性用例
    # 针对 'cost' 参数生成极端值
    cost_cases = generator.generate_numeric_adversarials("cost", baseline=10.0)
    # 针对 'quantity' 参数生成极端值
    quantity_cases = generator.generate_numeric_adversarials("quantity", baseline=5)
    
    # 合并所有用例
    all_cases = cost_cases + quantity_cases
    
    # 添加一个自定义的"无限供给"逻辑用例
    all_cases.append(TestCase(
        test_id="custom_001",
        inputs={"cost": 10, "markup": 0.2, "quantity": float('inf')},
        category="logic",
        description="Infinite quantity supply test"
    ))

    # 4. 执行压力测试
    vulnerability_report = stress_test_node(street_vendor_pricing, all_cases)
    
    # 5. 输出报告
    print(f"\n--- Vulnerability Report for {vulnerability_report.node_name} ---")
    print(f"Total Tests: {vulnerability_report.total_tests}")
    print(f"Failures: {vulnerability_report.failures}")
    print(f"Logic Collapse Score: {vulnerability_report.logic_collapse_score}")
    print("Failure Points:")
    for fp in vulnerability_report.failure_points:
        print(f"- {fp}")