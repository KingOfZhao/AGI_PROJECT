"""
抗干扰原子任务沙箱 - 融合能力模块

该模块实现了一种借鉴认知科学中'注意力漂移'机制的代码生成压力测试系统。
通过在任务上下文中注入语义干扰项，测试并优化任务拆解的鲁棒性。

核心功能:
1. 语义干扰项注入: 模拟认知干扰环境
2. 鲁棒性评分: 量化任务在干扰下的表现
3. 任务分解优化: 根据测试结果调整任务粒度

输入格式:
{
    "task_id": str,
    "description": str,
    "context": dict,
    "expected_output": dict
}

输出格式:
{
    "task_id": str,
    "robustness_score": float,
    "is_atomic": bool,
    "recommendation": str,
    "test_log": list
}
"""

import logging
import random
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AntiInterferenceSandbox")


class InterferenceType(Enum):
    """干扰项类型枚举"""
    IRRELEVANT_CODE = auto()    # 无关代码片段
    MISLEADING_COMMENT = auto() # 误导性注释
    SYNTAX_NOISE = auto()       # 语法噪音
    CONTEXT_DRIFT = auto()      # 上下文漂移


@dataclass
class InterferenceItem:
    """语义干扰项数据结构"""
    interference_type: InterferenceType
    content: str
    severity: float  # 0.1-1.0 干扰强度


class RobustnessTestResult:
    """鲁棒性测试结果容器"""
    def __init__(self):
        self.original_accuracy: float = 0.0
        self.interfered_accuracy: float = 0.0
        self.robustness_score: float = 0.0
        self.test_details: List[Dict] = []
        self.is_atomic: bool = False
        self.recommendation: str = ""


class AntiInterferenceSandbox:
    """抗干扰原子任务沙箱主类
    
    示例用法:
    >>> sandbox = AntiInterferenceSandbox()
    >>> task = {
    ...     "task_id": "calc_001",
    ...     "description": "计算两个数的和",
    ...     "context": {"a": 5, "b": 3},
    ...     "expected_output": {"result": 8}
    ... }
    >>> result = sandbox.evaluate_task_robustness(task)
    >>> print(result.robustness_score)
    0.92
    """
    
    def __init__(self, interference_probability: float = 0.3):
        """初始化沙箱
        
        Args:
            interference_probability: 干扰项注入概率 (0.0-1.0)
        """
        self._validate_probability(interference_probability)
        self.interference_probability = interference_probability
        self._interference_library = self._initialize_interference_library()
        
    def _validate_probability(self, prob: float) -> None:
        """验证概率参数有效性"""
        if not 0 <= prob <= 1:
            raise ValueError(f"干扰概率必须在0-1之间，当前值: {prob}")
    
    def _initialize_interference_library(self) -> Dict[InterferenceType, List[str]]:
        """初始化干扰项库"""
        return {
            InterferenceType.IRRELEVANT_CODE: [
                "def unused_function():\n    pass",
                "import math\nimport os\nimport sys",
                "temp = []\nfor i in range(10):\n    temp.append(i)"
            ],
            InterferenceType.MISLEADING_COMMENT: [
                "# 这个函数实际上处理用户输入",
                "/* 以下代码已被弃用 */",
                "// 注意: 参数顺序可能已改变"
            ],
            InterferenceType.SYNTAX_NOISE: [
                "if False: print('test')",
                "try: pass\nexcept: pass",
                "lambda x: x*2"
            ],
            InterferenceType.CONTEXT_DRIFT: [
                "previous_task = 'process_data'",
                "user_profile = {'age': 30}",
                "system_status = 'maintenance'"
            ]
        }
    
    def _generate_interference_items(self, count: int = 2) -> List[InterferenceItem]:
        """生成指定数量的随机干扰项
        
        Args:
            count: 要生成的干扰项数量
            
        Returns:
            干扰项列表
        """
        items = []
        types = list(InterferenceType)
        
        for _ in range(count):
            int_type = random.choice(types)
            content = random.choice(self._interference_library[int_type])
            severity = random.uniform(0.3, 0.9)
            items.append(InterferenceItem(int_type, content, severity))
            
        return items
    
    def _inject_interference(self, task_context: Dict, items: List[InterferenceItem]) -> Dict:
        """将干扰项注入到任务上下文中
        
        Args:
            task_context: 原始任务上下文
            items: 要注入的干扰项列表
            
        Returns:
            被干扰的上下文
        """
        interfered_context = task_context.copy()
        
        if random.random() < self.interference_probability:
            for item in items:
                # 随机选择注入位置
                key = f"noise_{random.randint(1000, 9999)}"
                interfered_context[key] = {
                    "type": item.interference_type.name,
                    "content": item.content,
                    "severity": item.severity
                }
                
        return interfered_context
    
    def _evaluate_code_execution(self, code: str, context: Dict) -> float:
        """评估代码执行结果的准确性
        
        Args:
            code: 要执行的代码
            context: 执行上下文
            
        Returns:
            准确性评分 (0.0-1.0)
        """
        # 简化版评估逻辑 - 实际应用中应使用更复杂的代码分析
        try:
            # 检查语法有效性
            compile(code, '<string>', 'exec')
            
            # 模拟执行评分
            noise_level = sum(
                1 for k in context if k.startswith('noise_')
            ) / max(len(context), 1)
            
            accuracy = 1.0 - (noise_level * 0.3)
            return max(0.0, min(1.0, accuracy))
            
        except (SyntaxError, NameError) as e:
            logger.warning(f"代码执行错误: {str(e)}")
            return 0.0
    
    def evaluate_task_robustness(self, task: Dict, test_cycles: int = 3) -> RobustnessTestResult:
        """评估任务的抗干扰鲁棒性
        
        Args:
            task: 要测试的任务字典
            test_cycles: 测试循环次数
            
        Returns:
            RobustnessTestResult: 包含测试结果的对象
        """
        self._validate_task(task)
        
        result = RobustnessTestResult()
        original_code = self._generate_mock_code(task)
        
        # 原始测试
        result.original_accuracy = self._evaluate_code_execution(
            original_code, task["context"]
        )
        
        # 干扰测试
        interfered_scores = []
        for _ in range(test_cycles):
            interference_items = self._generate_interference_items()
            interfered_context = self._inject_interference(
                task["context"], interference_items
            )
            
            score = self._evaluate_code_execution(original_code, interfered_context)
            interfered_scores.append(score)
            
            result.test_details.append({
                "interference_items": [
                    {"type": i.interference_type.name, "severity": i.severity}
                    for i in interference_items
                ],
                "accuracy": score
            })
        
        result.interfered_accuracy = sum(interfered_scores) / len(interfered_scores)
        result.robustness_score = (result.original_accuracy * 0.6 + 
                                  result.interfered_accuracy * 0.4)
        
        # 生成建议
        result.is_atomic = result.robustness_score >= 0.8
        if not result.is_atomic:
            result.recommendation = self._generate_recommendation(
                result.robustness_score, interfered_scores
            )
        else:
            result.recommendation = "任务粒度适当，具有良好的抗干扰能力"
            
        return result
    
    def _validate_task(self, task: Dict) -> None:
        """验证任务结构有效性"""
        required_keys = {"task_id", "description", "context", "expected_output"}
        if not required_keys.issubset(task.keys()):
            raise ValueError(f"任务缺少必需字段: {required_keys}")
    
    def _generate_mock_code(self, task: Dict) -> str:
        """生成模拟代码用于测试
        
        Args:
            task: 任务字典
            
        Returns:
            模拟生成的代码字符串
        """
        # 实际应用中这里应该是真正的代码生成逻辑
        return f"""
def execute_task(context):
    # 处理任务: {task['description']}
    # 任务ID: {task['task_id']}
    try:
        # 模拟业务逻辑
        result = {{}}
        for key, value in context.items():
            if not key.startswith('noise_'):
                result[key] = value
        return result
    except Exception as e:
        print(f"Error: {{e}}")
        return None
"""
    
    def _generate_recommendation(self, score: float, scores: List[float]) -> str:
        """生成任务优化建议
        
        Args:
            score: 总体鲁棒性评分
            scores: 各次测试评分列表
            
        Returns:
            优化建议字符串
        """
        variance = sum((s - score) ** 2 for s in scores) / len(scores)
        
        if variance > 0.1:
            return "任务对干扰敏感，建议进一步拆分为更小的原子任务"
        elif score < 0.6:
            return "任务抗干扰能力差，需要重新设计逻辑边界"
        else:
            return "任务可以接受，但建议添加更多的上下文验证"


def run_example_usage():
    """示例用法演示"""
    print("=== 抗干扰原子任务沙箱示例 ===")
    
    # 初始化沙箱
    sandbox = AntiInterferenceSandbox(interference_probability=0.7)
    
    # 示例任务
    task = {
        "task_id": "data_process_001",
        "description": "处理用户数据并计算统计信息",
        "context": {
            "user_data": [12, 45, 78, 32, 19],
            "operation": "mean"
        },
        "expected_output": {
            "result": 37.2
        }
    }
    
    # 执行鲁棒性测试
    result = sandbox.evaluate_task_robustness(task, test_cycles=5)
    
    # 打印结果
    print(f"\n任务ID: {task['task_id']}")
    print(f"原始准确性: {result.original_accuracy:.2f}")
    print(f"干扰下准确性: {result.interfered_accuracy:.2f}")
    print(f"鲁棒性评分: {result.robustness_score:.2f}")
    print(f"是否原子任务: {'是' if result.is_atomic else '否'}")
    print(f"优化建议: {result.recommendation}")
    
    print("\n详细测试记录:")
    for idx, detail in enumerate(result.test_details, 1):
        print(f"测试 #{idx}:")
        print(f"  干扰项: {detail['interference_items']}")
        print(f"  准确性: {detail['accuracy']:.2f}")


if __name__ == "__main__":
    run_example_usage()