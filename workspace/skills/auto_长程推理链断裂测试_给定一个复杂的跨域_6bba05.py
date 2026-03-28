"""
长程推理链断裂测试模块

该模块用于测试AGI系统在处理复杂跨域任务时的推理能力。特别是验证系统是否能够
主动生成关键节点（如'彩排'），并在其中预置必要的测试动作（如'读屏软件兼容性测试'）。

示例:
    >>> test_chain = LongRangeReasoningChainTest()
    >>> result = test_chain.execute_test(
    ...     task="策划并执行一次针对盲人用户的线上产品发布会",
    ...     required_nodes=["无障碍设计", "视频流媒体技术", "活动营销"],
    ...     critical_check=("彩排", "读屏软件兼容性测试")
    ... )
    >>> print(f"测试结果: {'通过' if result.passed else '失败'}")
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum, auto
from datetime import datetime
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reasoning_chain_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """测试状态枚举"""
    PASSED = auto()
    FAILED_MISSING_NODE = auto()
    FAILED_MISSING_ACTION = auto()
    FAILED_INVALID_CHAIN = auto()
    ERROR = auto()


@dataclass
class Node:
    """推理链节点数据结构"""
    name: str
    actions: List[str]
    dependencies: List[str]
    is_critical: bool = False
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """将节点转换为字典格式"""
        return {
            "name": self.name,
            "actions": self.actions,
            "dependencies": self.dependencies,
            "is_critical": self.is_critical,
            "metadata": self.metadata
        }


@dataclass
class TestResult:
    """测试结果数据结构"""
    passed: bool
    status: TestStatus
    message: str
    missing_nodes: List[str]
    missing_actions: List[str]
    timestamp: str
    execution_time: float
    chain_integrity: float  # 0.0-1.0 表示推理链完整性评分

    def to_dict(self) -> Dict:
        """将结果转换为字典格式"""
        return {
            "passed": self.passed,
            "status": self.status.name,
            "message": self.message,
            "missing_nodes": self.missing_nodes,
            "missing_actions": self.missing_actions,
            "timestamp": self.timestamp,
            "execution_time": self.execution_time,
            "chain_integrity": self.chain_integrity
        }


class LongRangeReasoningChainTest:
    """
    长程推理链断裂测试主类
    
    用于验证AGI系统在处理复杂跨域任务时是否能够:
    1. 生成所有必要的领域节点
    2. 主动识别并创建关键节点（如彩排）
    3. 在关键节点中预置必要的测试动作（如读屏软件兼容性测试）
    4. 保持推理链的完整性和逻辑性
    """

    def __init__(self):
        """初始化测试环境"""
        self.required_domains = {
            "无障碍设计": ["WCAG标准", "读屏软件测试", "盲文支持", "高对比度模式"],
            "视频流媒体技术": ["实时字幕", "音频描述", "低延迟传输", "自适应码率"],
            "活动营销": ["多渠道推广", "无障碍宣传材料", "无障碍反馈渠道"]
        }
        self.critical_nodes = {
            "彩排": ["读屏软件兼容性测试", "实时字幕验证", "音频描述同步检查"]
        }
        logger.info("长程推理链测试模块初始化完成")

    def _validate_input(
        self,
        task: str,
        required_nodes: List[str],
        critical_check: Tuple[str, str]
    ) -> bool:
        """
        验证输入参数的有效性
        
        参数:
            task: 任务描述
            required_nodes: 必需的领域节点列表
            critical_check: 关键检查元组(节点名称, 动作名称)
            
        返回:
            bool: 输入是否有效
            
        异常:
            ValueError: 当输入无效时抛出
        """
        if not isinstance(task, str) or len(task) < 10:
            raise ValueError("任务描述必须至少包含10个字符")
            
        if not isinstance(required_nodes, list) or len(required_nodes) < 1:
            raise ValueError("必须指定至少一个必需节点")
            
        if (not isinstance(critical_check, tuple) or 
            len(critical_check) != 2 or
            not all(isinstance(x, str) for x in critical_check)):
            raise ValueError("关键检查必须是包含两个字符串的元组")
            
        return True

    def _analyze_chain_integrity(
        self,
        generated_nodes: List[Node],
        required_nodes: List[str]
    ) -> float:
        """
        分析推理链的完整性
        
        参数:
            generated_nodes: 生成的节点列表
            required_nodes: 必需的节点名称列表
            
        返回:
            float: 完整性评分(0.0-1.0)
        """
        if not generated_nodes:
            return 0.0
            
        # 计算必需节点覆盖率
        generated_names = {node.name for node in generated_nodes}
        required_set = set(required_nodes)
        coverage = len(generated_names & required_set) / len(required_set)
        
        # 计算依赖关系完整性
        dependency_score = 0.0
        for node in generated_nodes:
            if node.dependencies:
                resolved_deps = sum(
                    1 for dep in node.dependencies 
                    if dep in generated_names
                )
                dependency_score += resolved_deps / len(node.dependencies)
                
        if generated_nodes:
            dependency_score /= len(generated_nodes)
            
        # 综合评分 (60% 节点覆盖率 + 40% 依赖完整性)
        return 0.6 * coverage + 0.4 * dependency_score

    def _check_critical_node(
        self,
        generated_nodes: List[Node],
        critical_node: str,
        critical_action: str
    ) -> Tuple[bool, bool]:
        """
        检查关键节点及其动作是否存在
        
        参数:
            generated_nodes: 生成的节点列表
            critical_node: 关键节点名称
            critical_action: 关键动作名称
            
        返回:
            Tuple[bool, bool]: (节点是否存在, 动作是否存在)
        """
        node_exists = False
        action_exists = False
        
        for node in generated_nodes:
            if node.name == critical_node:
                node_exists = True
                if critical_action in node.actions:
                    action_exists = True
                break
                
        return node_exists, action_exists

    def execute_test(
        self,
        task: str,
        required_nodes: List[str],
        critical_check: Tuple[str, str],
        mock_generated_nodes: Optional[List[Node]] = None
    ) -> TestResult:
        """
        执行长程推理链测试
        
        参数:
            task: 任务描述
            required_nodes: 必需的领域节点列表
            critical_check: 关键检查元组(节点名称, 动作名称)
            mock_generated_nodes: 用于测试的模拟节点(可选)
            
        返回:
            TestResult: 测试结果对象
            
        异常:
            ValueError: 当输入验证失败时抛出
        """
        start_time = datetime.now()
        logger.info(f"开始执行测试: 任务='{task}'")
        
        try:
            # 验证输入
            self._validate_input(task, required_nodes, critical_check)
            
            # 在实际应用中，这里会调用AGI系统生成推理链
            # 使用mock数据或模拟生成的推理链
            generated_nodes = mock_generated_nodes or self._mock_generate_chain(task)
            
            # 检查必需节点
            generated_names = {node.name for node in generated_nodes}
            missing_nodes = [
                node for node in required_nodes 
                if node not in generated_names
            ]
            
            # 检查关键节点
            critical_node, critical_action = critical_check
            node_exists, action_exists = self._check_critical_node(
                generated_nodes, critical_node, critical_action
            )
            
            # 计算推理链完整性
            integrity = self._analyze_chain_integrity(generated_nodes, required_nodes)
            
            # 确定测试状态
            if missing_nodes:
                status = TestStatus.FAILED_MISSING_NODE
                message = f"缺少必需节点: {', '.join(missing_nodes)}"
            elif not node_exists:
                status = TestStatus.FAILED_MISSING_NODE
                message = f"缺少关键节点: {critical_node}"
            elif not action_exists:
                status = TestStatus.FAILED_MISSING_ACTION
                message = f"关键节点 '{critical_node}' 中缺少动作: {critical_action}"
            elif integrity < 0.7:
                status = TestStatus.FAILED_INVALID_CHAIN
                message = f"推理链完整性不足: {integrity:.2f}"
            else:
                status = TestStatus.PASSED
                message = "所有检查通过"
                
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 创建结果对象
            result = TestResult(
                passed=status == TestStatus.PASSED,
                status=status,
                message=message,
                missing_nodes=missing_nodes,
                missing_actions=[critical_action] if not action_exists and node_exists else [],
                timestamp=start_time.isoformat(),
                execution_time=execution_time,
                chain_integrity=integrity
            )
            
            logger.info(f"测试完成: 状态={status.name}, 完整性={integrity:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"测试执行失败: {str(e)}")
            return TestResult(
                passed=False,
                status=TestStatus.ERROR,
                message=f"测试执行错误: {str(e)}",
                missing_nodes=[],
                missing_actions=[],
                timestamp=start_time.isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds(),
                chain_integrity=0.0
            )

    def _mock_generate_chain(self, task: str) -> List[Node]:
        """
        模拟AGI系统生成推理链(仅用于测试)
        
        参数:
            task: 任务描述
            
        返回:
            List[Node]: 模拟生成的推理链节点
        """
        # 这是一个模拟实现，实际应用中应该调用AGI系统
        if "盲人用户" in task and "发布会" in task:
            return [
                Node(
                    name="无障碍设计",
                    actions=["WCAG标准实现", "高对比度模式"],
                    dependencies=["需求分析"]
                ),
                Node(
                    name="视频流媒体技术",
                    actions=["实时字幕生成", "音频描述"],
                    dependencies=["技术选型"]
                ),
                Node(
                    name="活动营销",
                    actions=["多渠道推广", "无障碍宣传材料"],
                    dependencies=["市场调研"]
                ),
                Node(
                    name="彩排",
                    actions=["流程演练", "读屏软件兼容性测试"],
                    dependencies=["技术准备", "内容制作"],
                    is_critical=True
                )
            ]
        else:
            return [
                Node(
                    name="常规策划",
                    actions=["流程设计"],
                    dependencies=[]
                )
            ]


# 使用示例
if __name__ == "__main__":
    # 创建测试实例
    tester = LongRangeReasoningChainTest()
    
    # 测试用例1: 完整推理链
    print("\n=== 测试用例1: 完整推理链 ===")
    result1 = tester.execute_test(
        task="策划并执行一次针对盲人用户的线上产品发布会",
        required_nodes=["无障碍设计", "视频流媒体技术", "活动营销"],
        critical_check=("彩排", "读屏软件兼容性测试")
    )
    print(json.dumps(result1.to_dict(), indent=2, ensure_ascii=False))
    
    # 测试用例2: 缺少关键动作
    print("\n=== 测试用例2: 缺少关键动作 ===")
    mock_nodes = [
        Node(name="无障碍设计", actions=["WCAG标准"], dependencies=[]),
        Node(name="彩排", actions=["流程演练"], dependencies=[])
    ]
    result2 = tester.execute_test(
        task="策划并执行一次针对盲人用户的线上产品发布会",
        required_nodes=["无障碍设计"],
        critical_check=("彩排", "读屏软件兼容性测试"),
        mock_generated_nodes=mock_nodes
    )
    print(json.dumps(result2.to_dict(), indent=2, ensure_ascii=False))
    
    # 测试用例3: 缺少必需节点
    print("\n=== 测试用例3: 缺少必需节点 ===")
    result3 = tester.execute_test(
        task="策划并执行一次普通线上发布会",
        required_nodes=["活动营销", "视频技术"],
        critical_check=("彩排", "流程演练")
    )
    print(json.dumps(result3.to_dict(), indent=2, ensure_ascii=False))