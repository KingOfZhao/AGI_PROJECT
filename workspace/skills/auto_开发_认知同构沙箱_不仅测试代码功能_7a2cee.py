"""
认知同构沙箱
该模块旨在不仅测试代码的功能正确性，还通过分析代码结构识别其与物理或生物领域的同构性，
并基于这些领域模型生成极端的边界测试用例，以实现基于认知模型的自动化压力测试。

领域: cross_domain
"""

import ast
import inspect
import logging
import random
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CognitiveSandbox")


class CognitiveDomain(Enum):
    """定义认知领域枚举，用于映射代码结构到现实世界模型。"""
    FLUID_DYNAMICS = "fluid_dynamics"  # 对应交换类算法（如冒泡排序），模拟气泡上浮
    BIOLOGICAL_SELECTION = "biological_selection"  # 对应迭代优化/筛选，模拟优胜劣汰
    TECTONIC_ACTIVITY = "tectonic_activity"  # 对应分治/递归，模拟地质板块运动
    UNKNOWN = "unknown"


class CognitiveIsomorphismSandbox:
    """
    认知同构沙箱类。
    
    该类负责分析输入函数的AST结构，识别其认知同构领域，
    并根据领域特性生成针对性的压力测试数据。
    """

    def __init__(self):
        self._domain_mapping: Dict[str, CognitiveDomain] = {}

    def _validate_input(self, func: Callable) -> None:
        """
        辅助函数：验证输入函数的有效性。
        
        Args:
            func: 待测试的可调用对象。
            
        Raises:
            TypeError: 如果输入不是可调用对象。
        """
        if not callable(func):
            logger.error(f"输入无效: {func} 不是可调用对象。")
            raise TypeError("输入必须是一个可调用的函数。")
        logger.info(f"函数验证通过: {func.__name__}")

    def _analyze_code_structure(self, func: Callable) -> CognitiveDomain:
        """
        核心函数 1：分析代码结构并识别认知同构领域。
        
        通过解析函数的AST（抽象语法树），寻找特定的模式（如变量交换、递归调用），
        从而推断其背后的认知模型。
        
        Args:
            func: 待分析的函数。
            
        Returns:
            CognitiveDomain: 识别出的认知领域。
        """
        try:
            source = inspect.getsource(func)
            tree = ast.parse(source)
            
            # 简单的启发式规则：检测嵌套循环中的交换操作（冒泡排序特征）
            # 映射到流体动力学（气泡上浮）
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    for inner_node in ast.walk(node):
                        if isinstance(inner_node, ast.Assign):
                            # 检查是否为 a, b = b, a 形式的赋值
                            if (isinstance(inner_node.targets[0], ast.Tuple) and
                                    isinstance(inner_node.value, ast.Tuple)):
                                logger.info("检测到交换结构，映射到流体动力学模型。")
                                return CognitiveDomain.FLUID_DYNAMICS
            
            # 检测递归调用
            # 映射到地质活动（分治/板块运动）或生物分裂
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == func.__name__:
                        logger.info("检测到递归结构，映射到地质活动模型。")
                        return CognitiveDomain.TECTONIC_ACTIVITY

        except (OSError, TypeError) as e:
            logger.warning(f"无法解析源代码进行结构分析: {e}，回退到默认模式。")

        logger.info("未检测到特定同构结构，使用通用测试模型。")
        return CognitiveDomain.UNKNOWN

    def _generate_domain_specific_inputs(
        self, 
        domain: CognitiveDomain, 
        sample_input: Any
    ) -> List[Any]:
        """
        核心函数 2：基于认知领域生成极端的边界测试用例。
        
        Args:
            domain: 认知领域枚举。
            sample_input: 原始输入样本，用于推断类型和结构。
            
        Returns:
            List[Any]: 生成的测试用例列表。
        """
        test_cases = []
        
        if not isinstance(sample_input, list):
            # 如果不是列表，简单返回原输入和None
            return [sample_input, None]

        n = len(sample_input)
        
        if domain == CognitiveDomain.FLUID_DYNAMICS:
            # 模拟高粘度环境：所有元素相同（测试排序稳定性）
            viscous_case = [sample_input[0]] * n if n > 0 else []
            test_cases.append(("高粘度流体模拟", viscous_case))
            
            # 模拟湍流环境：完全逆序（测试气泡上浮的最大阻力）
            turbulent_case = sorted(sample_input, reverse=True)
            test_cases.append(("湍流环境模拟", turbulent_case))
            
        elif domain == CognitiveDomain.TECTONIC_ACTIVITY:
            # 模拟极端压力：极大规模数据（测试递归深度/栈溢出）
            # 注意：这里为了演示只生成稍微大一点的列表，实际应更谨慎
            pressure_case = sample_input + [random.randint(0, 100) for _ in range(100)]
            test_cases.append(("地壳高压模拟", pressure_case))
            
            # 模拟断层：包含空值或异常值
            fault_case = sample_input.copy()
            if fault_case:
                fault_case[len(fault_case)//2] = None
            test_cases.append(("地质断层模拟", fault_case))
            
        else:
            # 通用边界测试
            test_cases.append(("空边界", []))
            test_cases.append(("单元素边界", [sample_input[0]] if n > 0 else []))
            
        return test_cases

    def run_cognitive_stress_test(
        self, 
        func: Callable, 
        initial_input: Any
    ) -> Dict[str, Union[bool, str]]:
        """
        执行认知同构压力测试的主入口。
        
        Args:
            func: 待测试的函数。
            initial_input: 初始标准输入，用于生成测试用例。
            
        Returns:
            Dict: 包含测试结果摘要的字典。
        """
        self._validate_input(func)
        
        logger.info(f"开始对函数 '{func.__name__}' 进行认知同构分析...")
        domain = self._analyze_code_structure(func)
        
        logger.info(f"识别认知领域: {domain.value}")
        test_cases = self._generate_domain_specific_inputs(domain, initial_input)
        
        results = {
            "function": func.__name__,
            "detected_domain": domain.value,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        for case_name, case_input in test_cases:
            try:
                logger.info(f"执行测试用例: {case_name} | 输入: {str(case_input)[:50]}...")
                # 执行函数
                output = func(case_input)
                
                # 简单验证：对于排序类函数，检查是否有序（仅作演示）
                if domain == CognitiveDomain.FLUID_DYNAMICS and isinstance(case_input, list):
                    is_sorted = all(output[i] <= output[i+1] for i in range(len(output)-1))
                    if not is_sorted:
                        raise AssertionError("输出结果未满足有序性（流体平衡未达成）")
                
                logger.info(f"测试用例 '{case_name}' 通过。")
                results["tests_passed"] += 1
                results["details"].append({"case": case_name, "status": "PASS"})
                
            except Exception as e:
                logger.error(f"测试用例 '{case_name}' 失败: {e}")
                results["tests_failed"] += 1
                results["details"].append({"case": case_name, "status": "FAIL", "error": str(e)})
                
        logger.info(f"测试完成。通过: {results['tests_passed']}, 失败: {results['tests_failed']}")
        return results


# 示例使用
if __name__ == "__main__":
    # 示例函数 1: 冒泡排序 (同构于流体动力学 - 气泡上浮)
    def bubble_sort(arr):
        if not arr:
            return []
        n = len(arr)
        # 处理 None 值的简单逻辑
        clean_arr = [x for x in arr if x is not None]
        for i in range(n):
            for j in range(0, n-i-1):
                if clean_arr[j] > clean_arr[j+1]:
                    clean_arr[j], clean_arr[j+1] = clean_arr[j+1], clean_arr[j]
        return clean_arr

    # 示例函数 2: 快速排序 (同构于地质活动 - 分治)
    def quick_sort(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quick_sort(left) + middle + quick_sort(right)

    # 初始化沙箱
    sandbox = CognitiveIsomorphismSandbox()
    
    # 准备初始数据
    sample_data = [random.randint(1, 100) for _ in range(10)]
    
    print("-" * 50)
    print("测试冒泡排序 (流体动力学模型)")
    print("-" * 50)
    report_bubble = sandbox.run_cognitive_stress_test(bubble_sort, sample_data)
    print(f"结果摘要: {report_bubble}")
    
    print("\n" + "-" * 50)
    print("测试快速排序 (地质活动模型)")
    print("-" * 50)
    report_quick = sandbox.run_cognitive_stress_test(quick_sort, sample_data)
    print(f"结果摘要: {report_quick}")