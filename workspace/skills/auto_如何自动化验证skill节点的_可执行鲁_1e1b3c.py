"""
Module: skill_robustness_validator
Description: 自动化验证SKILL节点的可执行鲁棒性。
             通过模糊测试(Fuzzing)输入边界值和异常数据，监测节点的崩溃率、
             超时率以及优雅降级能力。

Domain: software_engineering
Author: Senior Python Engineer
"""

import logging
import random
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """定义技能执行的四种状态。"""
    SUCCESS = "SUCCESS"                 # 正常执行且输出符合预期
    GRACEFUL_DEGRADATION = "GRACEFUL_DEGRADATION" # 输入异常但节点未崩溃，返回了安全值或预期错误
    CRASH = "CRASH"                     # 节点抛出未捕获异常导致崩溃
    TIMEOUT = "TIMEOUT"                 # 执行时间超过阈值


@dataclass
class SkillNode:
    """代表AGI系统中的一个技能节点。"""
    id: str
    func: Callable[[Any], Any]
    description: str = ""
    # 定义该节点预期的输入类型，用于生成针对性测试数据（可选）
    expected_input_type: type = Any


@dataclass
class TestResult:
    """单次模糊测试的执行结果。"""
    node_id: str
    input_data: Any
    status: ExecutionStatus
    output: Any
    execution_time: float
    error_message: Optional[str] = None


def generate_fuzz_input() -> Any:
    """
    辅助函数：生成模糊测试输入数据。
    
    策略包括：
    1. 空值
    2. 边界值
    3. 类型错误
    4. 随机噪声
    
    Returns:
        Any: 生成的测试输入。
    """
    fuzz_strategies = [
        lambda: None,                              # None Type
        lambda: "",                                # Empty String
        lambda: [],                                # Empty List
        lambda: {},                                # Empty Dict
        lambda: 0,                                 # Zero
        lambda: -1,                                # Negative Integer
        lambda: sys.maxsize,                       # Max Integer
        lambda: -sys.maxsize - 1,                  # Min Integer
        lambda: 3.1415926 * random.uniform(-1000, 1000), # Random Float
        lambda: "".join(random.choices("abc123!@#$%^&*()", k=20)), # Random String
        lambda: {"key": "value", "nested": {"bad_key": lambda x: x}}, # Malformed Dict
        lambda: True,                              # Boolean
        lambda: 1e308,                             # Float Max
        lambda: -1e308,                            # Float Min
        lambda: "2023-13-45",                      # Invalid Date format
    ]
    
    return random.choice(strategies)()


def execute_skill_safely(node: SkillNode, input_data: Any, timeout: float = 1.0) -> TestResult:
    """
    核心函数 1：安全地执行技能节点并捕获异常。
    
    监测节点在接收异常输入时的行为。区分“崩溃”与“优雅降级”。
    优雅降级定义为：捕获了预期的输入错误并返回None/默认值，或抛出ValueError/TypeError等预期异常。
    崩溃定义为：抛出IndexError, KeyError, AttributeError等逻辑错误或系统级错误。
    
    Args:
        node (SkillNode): 待测试的技能节点。
        input_data (Any): 模糊测试生成的输入数据。
        timeout (float): 超时时间阈值（秒）。
        
    Returns:
        TestResult: 包含执行状态、耗时和输出信息的对象。
    """
    start_time = time.time()
    status = ExecutionStatus.CRASH
    output = None
    error_msg = None
    
    try:
        # 执行技能函数
        result = node.func(input_data)
        exec_time = time.time() - start_time
        
        # 简单的优雅降级启发式判断逻辑
        # 如果输入是None或空，且返回了None或特定默认值，视为降级
        if input_data in [None, "", [], {}] and result in [None, "", [], {}]:
            status = ExecutionStatus.GRACEFUL_DEGRADATION
        else:
            status = ExecutionStatus.SUCCESS
            
        output = result
        
    except (ValueError, TypeError) as ve:
        # 这些异常通常意味着节点检测到了输入类型或值不合法，属于鲁棒性表现
        status = ExecutionStatus.GRACEFUL_DEGRADATION
        error_msg = f"{type(ve).__name__}: {str(ve)}"
        exec_time = time.time() - start_time
        logger.debug(f"Node {node.id} handled bad input gracefully: {error_msg}")
        
    except Exception as e:
        # 其他未预期的异常视为崩溃
        status = ExecutionStatus.CRASH
        error_msg = f"{type(e).__name__}: {str(e)}"
        exec_time = time.time() - start_time
        logger.error(f"Node {node.id} crashed on input {input_data}: {error_msg}")
        
    # 超时检查
    if time.time() - start_time > timeout:
        status = ExecutionStatus.TIMEOUT
        logger.warning(f"Node {node.id} timed out.")

    return TestResult(
        node_id=node.id,
        input_data=input_data,
        status=status,
        output=output,
        execution_time=exec_time,
        error_message=error_msg
    )


def run_robustness_verification(nodes: List[SkillNode], iterations_per_node: int = 100) -> Dict[str, Dict[str, float]]:
    """
    核心函数 2：对技能节点集合进行批量鲁棒性验证。
    
    统计每个节点的崩溃率、优雅降级率和平均执行时间。
    
    Args:
        nodes (List[SkillNode]): 技能节点列表。
        iterations_per_node (int): 每个节点进行的模糊测试次数。
        
    Returns:
        Dict[str, Dict[str, float]]: 汇总报告，键为节点ID，值为各项指标。
    """
    report: Dict[str, Dict[str, float]] = {}
    
    logger.info(f"Starting robustness verification for {len(nodes)} nodes ({iterations_per_node} iterations each).")
    
    for node in nodes:
        crash_count = 0
        timeout_count = 0
        degradation_count = 0
        total_time = 0.0
        
        for _ in range(iterations_per_node):
            # 生成模糊输入
            fuzz_input = generate_fuzz_input()
            
            # 执行测试
            result = execute_skill_safely(node, fuzz_input)
            
            total_time += result.execution_time
            
            # 统计结果
            if result.status == ExecutionStatus.CRASH:
                crash_count += 1
            elif result.status == ExecutionStatus.TIMEOUT:
                timeout_count += 1
            elif result.status == ExecutionStatus.GRACEFUL_DEGRADATION:
                degradation_count += 1
        
        # 计算指标
        total_failures = crash_count + timeout_count
        crash_rate = total_failures / iterations_per_node
        degradation_rate = degradation_count / iterations_per_node
        avg_time = total_time / iterations_per_node
        
        report[node.id] = {
            "crash_rate": crash_rate,
            "degradation_rate": degradation_rate,
            "avg_execution_time": avg_time,
            "robustness_score": 1.0 - crash_rate # 鲁棒性评分：1 - 崩溃率
        }
        
        logger.info(
            f"Node [{node.id}] | Crash Rate: {crash_rate:.2%} | "
            f"Graceful Degradation: {degradation_rate:.2%} | "
            f"Avg Time: {avg_time:.4f}s"
        )
        
    return report


# --- 使用示例 ---

def example_skill_text_processor(text: str) -> str:
    """示例技能：处理文本。如果输入不是字符串，抛出TypeError（鲁棒设计）。"""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    return text.strip().upper()

def example_skill_unsafe_divider(data: dict) -> float:
    """示例技能：执行除法。如果缺少Key或除以0，会崩溃（非鲁棒设计）。"""
    # 故意不检查 'denominator' 是否存在，也不检查是否为0
    return data['numerator'] / data['denominator']

def example_skill_safe_calculator(value: Any) -> int:
    """示例技能：安全计算。对异常输入进行优雅降级。"""
    try:
        num = int(value)
        return num * num
    except (ValueError, TypeError):
        return 0 # 降级：输入无效返回0

if __name__ == "__main__":
    # 构建测试节点列表
    test_nodes = [
        SkillNode(id="text_processor", func=example_skill_text_processor),
        SkillNode(id="unsafe_divider", func=example_skill_unsafe_divider),
        SkillNode(id="safe_calculator", func=example_skill_safe_calculator),
    ]
    
    # 运行验证
    # 注意：unsafe_divider 预期会有较高的崩溃率
    final_report = run_robustness_verification(test_nodes, iterations_per_node=50)
    
    # 打印最终报告
    print("\n=== Final Robustness Report ===")
    for nid, metrics in final_report.items():
        print(f"Skill: {nid}")
        print(f"  Robustness Score: {metrics['robustness_score']:.2f}/1.0")
        print(f"  Crash Rate: {metrics['crash_rate']:.2%}")
        print("-" * 40)