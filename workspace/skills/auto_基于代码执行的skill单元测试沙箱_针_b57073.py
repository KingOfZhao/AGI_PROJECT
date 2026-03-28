"""
模块名称: skill_sandbox_testing_unit.py
描述: 基于代码执行的SKILL单元测试沙箱系统。
     该模块用于自动化回归测试SKILL节点（特别是涉及工具调用的节点）。
     通过在受控沙箱中执行节点代码并验证输出，系统能自动识别因底层API变更导致的损坏节点，
     并触发降权或熔断机制。
作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import json
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from functools import wraps

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillSandbox")


class SkillStatus(Enum):
    """SKILL节点的健康状态枚举"""
    HEALTHY = "healthy"           # 健康，正常运行
    DEGRADED = "degraded"         # 降级，轻微问题但可用
    DAMAGED = "damaged"           # 损坏，输出格式错误或崩溃
    QUARANTINED = "quarantined"   # 隔离，连续多次失败


@dataclass
class SkillNode:
    """SKILL节点数据结构"""
    node_id: str
    name: str
    exec_callable: Callable[..., Any]  # 节点实际执行的函数/代码
    version: str = "1.0"
    status: SkillStatus = SkillStatus.HEALTHY
    reliability_score: float = 1.0  # 0.0 到 1.0，用于降权
    last_check_time: float = field(default_factory=time.time)
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """测试用例定义"""
    test_id: str
    inputs: Dict[str, Any]
    expected_output: Any  # 期望的输出值
    validation_type: str = "exact"  # exact, schema, regex, contains
    timeout_seconds: int = 5


class SandboxEnvironment:
    """
    沙箱环境类。
    用于隔离执行SKILL代码，防止外部污染和捕获异常。
    """
    
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self._context = {}  # 沙箱上下文

    def setup(self) -> None:
        """初始化沙箱环境"""
        logger.info("Initializing sandbox environment...")
        # 在实际生产中，这里可能涉及Docker容器或 RestrictedPython 的设置
        self._context = {
            "__builtins__": __builtins__,
            "json": json,
            "time": time
        }
        logger.info("Sandbox ready.")

    def teardown(self) -> None:
        """清理沙箱环境"""
        self._context.clear()
        logger.info("Sandbox environment cleaned.")

    def execute(self, skill: SkillNode, inputs: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """
        在沙箱中执行指定的SKILL节点。

        Args:
            skill: 要执行的SKILL节点对象
            inputs: 输入参数字典

        Returns:
            Tuple[bool, Any, str]: (是否成功, 执行结果或异常对象, 日志/追踪信息)
        """
        logger.info(f"Executing skill [{skill.name}] in sandbox...")
        
        # 数据边界检查
        if not isinstance(inputs, dict):
            return False, None, "Inputs must be a dictionary."

        start_time = time.time()
        try:
            # 模拟执行环境隔离
            # 注意：真实环境应使用 subprocess 或 ast 解释器隔离
            result = skill.exec_callable(**inputs)
            
            duration = time.time() - start_time
            logger.info(f"Skill [{skill.name}] executed in {duration:.4f}s.")
            return True, result, ""
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Execution failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Skill [{skill.name}] crashed: {error_msg}")
            return False, e, error_msg


def validate_output(result: Any, test_case: TestCase) -> bool:
    """
    辅助函数：验证输出是否符合预期。

    Args:
        result: SKILL节点的实际输出
        test_case: 包含期望输出的测试用例

    Returns:
        bool: 验证是否通过
    """
    logger.debug(f"Validating output using strategy: {test_case.validation_type}")
    
    expected = test_case.expected_output
    
    if test_case.validation_type == "exact":
        return result == expected
    
    elif test_case.validation_type == "schema":
        # 检查结果是否符合JSON Schema或特定类型结构
        if not isinstance(result, type(expected)):
            logger.warning(f"Type mismatch: expected {type(expected)}, got {type(result)}")
            return False
        # 简单的键检查示例
        if isinstance(expected, dict):
            return all(k in result for k in expected.keys())
        return True

    elif test_case.validation_type == "contains":
        # 检查结果是否包含特定内容
        return expected in result
        
    return False


def run_regression_tests(
    skills_to_test: List[SkillNode],
    test_suites: Dict[str, List[TestCase]]
) -> Dict[str, SkillStatus]:
    """
    核心函数：运行回归测试并更新SKILL节点状态。
    如果节点依赖的底层API变更导致错误，将其标记为'DAMAGED'并降权。

    Args:
        skills_to_test: 待测试的SKILL节点列表
        test_suites: 测试套件字典，key为skill_id，value为TestCase列表

    Returns:
        Dict[str, SkillStatus]: 每个节点的最新状态映射
    """
    sandbox = SandboxEnvironment()
    sandbox.setup()
    results_map = {}

    for skill in skills_to_test:
        # 边界检查：是否有对应的测试用例
        if skill.node_id not in test_suites:
            logger.warning(f"No tests found for skill {skill.node_id}, skipping.")
            continue

        cases = test_suites[skill.node_id]
        passed_count = 0
        total_count = len(cases)

        for case in cases:
            success, output, _ = sandbox.execute(skill, case.inputs)
            
            if not success:
                # 执行崩溃直接判定失败
                logger.error(f"Test {case.test_id} CRASHED for skill {skill.name}")
                continue

            # 验证输出格式
            if validate_output(output, case):
                passed_count += 1
                logger.info(f"Test {case.test_id} PASSED")
            else:
                logger.warning(
                    f"Test {case.test_id} FAILED. Output format mismatch or content error. "
                    f"Expected {case.expected_output}, got {output}"
                )

        # 计算健康度与状态更新
        pass_rate = passed_count / total_count if total_count > 0 else 0.0
        
        # 状态机逻辑
        if pass_rate == 1.0:
            skill.status = SkillStatus.HEALTHY
            skill.reliability_score = min(1.0, skill.reliability_score + 0.1)
            skill.failure_count = 0
        elif pass_rate >= 0.5:
            skill.status = SkillStatus.DEGRADED
            skill.reliability_score = max(0.5, skill.reliability_score - 0.1)
            logger.warning(f"Skill {skill.name} is DEGRADED.")
        else:
            skill.status = SkillStatus.DAMAGED
            skill.reliability_score = max(0.0, skill.reliability_score - 0.5)
            skill.failure_count += 1
            logger.error(f"Skill {skill.name} marked as DAMAGED. Downgrading weight.")
            
            if skill.failure_count > 3:
                skill.status = SkillStatus.QUARANTINED

        skill.last_check_time = time.time()
        results_map[skill.node_id] = skill.status

    sandbox.teardown()
    return results_map


# --- 示例代码 (用于演示模块功能) ---

def mock_plotting_tool(data: List[float], title: str) -> Dict[str, Any]:
    """模拟一个正常的绘图工具SKILL"""
    if not data:
        raise ValueError("Data cannot be empty")
    return {
        "chart_type": "line",
        "title": title,
        "data_points": len(data),
        "status": "rendered"
    }

def mock_broken_api_tool(query: str) -> str:
    """模拟一个因API变更导致输出错误的SKILL"""
    # 假设原本应返回 "Result: xxx"，但底层API变了，现在返回无意义的JSON
    # 或者直接抛出异常
    if "fail" in query:
        raise ConnectionError("External API timeout")
    return json.dumps({"error": "invalid_response_format"})


if __name__ == "__main__":
    # 1. 定义SKILL节点
    skill_plot = SkillNode(
        node_id="skill_001",
        name="Python Plotting",
        exec_callable=mock_plotting_tool
    )
    
    skill_api = SkillNode(
        node_id="skill_002",
        name="External Data Fetcher",
        exec_callable=mock_broken_api_tool,
        reliability_score=0.9
    )

    skills = [skill_plot, skill_api]

    # 2. 定义测试用例
    test_suites = {
        "skill_001": [
            TestCase(
                test_id="t_plot_1",
                inputs={"data": [1, 2, 3], "title": "Sales"},
                expected_output={"chart_type": "line", "title": "Sales", "data_points": 3, "status": "rendered"},
                validation_type="exact"
            )
        ],
        "skill_002": [
            TestCase(
                test_id="t_api_1",
                inputs={"query": "fetch_data"},
                expected_output="Result: Success", # 期望是字符串，但实际返回JSON
                validation_type="contains"
            ),
            TestCase(
                test_id="t_api_2",
                inputs={"query": "fail_trigger"}, # 触发异常
                expected_output="Result: Any",
                validation_type="contains"
            )
        ]
    }

    # 3. 运行沙箱测试
    print("-" * 30)
    print("Starting Skill Sandbox Regression Tests...")
    print("-" * 30)
    
    final_status = run_regression_tests(skills, test_suites)
    
    print("\nFinal Results:")
    for skill_id, status in final_status.items():
        # 找到对应的skill对象以显示分数
        s = next((x for x in skills if x.node_id == skill_id), None)
        if s:
            print(f"Skill: {s.name} | Status: {status.value} | Score: {s.reliability_score:.2f}")