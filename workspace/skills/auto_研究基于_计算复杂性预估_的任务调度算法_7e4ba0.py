"""
高级任务调度器模块：基于计算复杂性预估的自适应调度

该模块实现了一个智能任务调度算法，能够根据任务预估的计算复杂性、
当前系统负载和剩余算力资源，动态决策执行路径：
- 轻量级Skill链：适用于低复杂性、高并发场景
- 深度推理树：适用于高复杂性、需要深度推理的场景

核心功能：
1. 计算复杂性评估
2. 动态资源监控
3. 自适应路径选择
4. 执行计划优化

示例用法:
    >>> from task_scheduler import TaskScheduler
    >>> scheduler = TaskScheduler()
    >>> task = {"type": "analysis", "data_size": 1000}
    >>> result = scheduler.execute_task(task)
"""

import logging
import math
import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("TaskScheduler")


class ExecutionPath(Enum):
    """定义任务执行路径的枚举类型"""
    SKILL_CHAIN = auto()  # 轻量级Skill链路径
    REASONING_TREE = auto()  # 深度推理树路径


@dataclass
class SystemResources:
    """系统资源状态数据类"""
    cpu_usage: float  # CPU使用率 (0.0-1.0)
    memory_available: float  # 可用内存 (GB)
    gpu_available: bool  # GPU是否可用
    concurrent_tasks: int  # 当前并发任务数

    def is_under_loaded(self) -> bool:
        """判断系统是否处于低负载状态"""
        return self.cpu_usage < 0.5 and self.concurrent_tasks < 4


class TaskScheduler:
    """基于计算复杂性预估的自适应任务调度器"""
    
    def __init__(self) -> None:
        """初始化任务调度器"""
        self.resource_monitor = ResourceMonitor()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("TaskScheduler initialized successfully")

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务的主入口方法
        
        参数:
            task: 包含任务信息的字典，应包含'type'和'data'字段
            
        返回:
            包含执行结果的字典，包括:
            - status: 执行状态 ("success" 或 "failed")
            - result: 执行结果
            - execution_path: 选择的执行路径
            - execution_time: 执行时间(秒)
            - complexity_score: 预估的计算复杂性分数
            
        异常:
            ValueError: 如果任务格式无效
        """
        # 验证任务格式
        self._validate_task(task)
        
        start_time = time.time()
        task_type = task["type"]
        task_data = task["data"]
        
        try:
            # 获取当前系统资源状态
            resources = self.resource_monitor.get_current_resources()
            logger.info(f"Current system resources: {resources}")
            
            # 预估任务计算复杂性
            complexity = self.complexity_analyzer.estimate_complexity(task)
            logger.info(f"Estimated task complexity: {complexity:.2f}")
            
            # 根据复杂性和资源状态选择执行路径
            path = self._select_execution_path(complexity, resources)
            logger.info(f"Selected execution path: {path.name}")
            
            # 执行任务
            if path == ExecutionPath.SKILL_CHAIN:
                result = self._execute_skill_chain(task_data)
            else:
                result = self._execute_reasoning_tree(task_data)
            
            # 记录执行历史
            execution_time = time.time() - start_time
            self._record_execution(
                task_type=task_type,
                complexity=complexity,
                path=path,
                execution_time=execution_time,
                success=True
            )
            
            return {
                "status": "success",
                "result": result,
                "execution_path": path.name,
                "execution_time": execution_time,
                "complexity_score": complexity
            }
            
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            execution_time = time.time() - start_time
            self._record_execution(
                task_type=task_type,
                complexity=complexity,
                path=path if 'path' in locals() else None,
                execution_time=execution_time,
                success=False
            )
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "complexity_score": complexity if 'complexity' in locals() else None
            }

    def _validate_task(self, task: Dict[str, Any]) -> None:
        """
        验证任务格式是否有效
        
        参数:
            task: 要验证的任务字典
            
        异常:
            ValueError: 如果任务格式无效
        """
        if not isinstance(task, dict):
            raise ValueError("Task must be a dictionary")
            
        if "type" not in task or "data" not in task:
            raise ValueError("Task must contain 'type' and 'data' fields")
            
        if not task["type"] or not task["data"]:
            raise ValueError("Task 'type' and 'data' fields cannot be empty")

    def _select_execution_path(
        self, complexity: float, resources: SystemResources
    ) -> ExecutionPath:
        """
        根据复杂性和资源状态选择最佳执行路径
        
        参数:
            complexity: 任务的计算复杂性分数 (0.0-1.0)
            resources: 当前系统资源状态
            
        返回:
            选择的ExecutionPath枚举值
        """
        # 基于复杂性的决策因子
        complexity_factor = 0.7 * complexity
        
        # 基于资源状态的决策因子
        resource_factor = 0.3 * (1 - resources.cpu_usage)
        
        # 综合决策分数
        decision_score = complexity_factor + resource_factor
        
        # 根据决策分数选择路径
        if decision_score < 0.6 and resources.is_under_loaded():
            return ExecutionPath.SKILL_CHAIN
        else:
            return ExecutionPath.REASONING_TREE

    def _execute_skill_chain(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行轻量级Skill链路径
        
        参数:
            task_data: 任务数据
            
        返回:
            执行结果
        """
        logger.info("Executing lightweight skill chain...")
        # 模拟执行过程
        time.sleep(random.uniform(0.1, 0.5))
        return {
            "path": "skill_chain",
            "processed_data": f"Processed: {task_data}",
            "steps": ["preprocess", "analyze", "format"]
        }

    def _execute_reasoning_tree(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行深度推理树路径
        
        参数:
            task_data: 任务数据
            
        返回:
            执行结果
        """
        logger.info("Executing deep reasoning tree...")
        # 模拟执行过程
        time.sleep(random.uniform(0.5, 2.0))
        return {
            "path": "reasoning_tree",
            "processed_data": f"Deeply analyzed: {task_data}",
            "reasoning_steps": [
                "hypothesis_generation",
                "evidence_collection",
                "logical_analysis",
                "conclusion_formation"
            ]
        }

    def _record_execution(
        self,
        task_type: str,
        complexity: float,
        path: Optional[ExecutionPath],
        execution_time: float,
        success: bool
    ) -> None:
        """
        记录任务执行历史
        
        参数:
            task_type: 任务类型
            complexity: 计算复杂性分数
            path: 执行路径
            execution_time: 执行时间(秒)
            success: 是否成功执行
        """
        record = {
            "timestamp": time.time(),
            "task_type": task_type,
            "complexity": complexity,
            "path": path.name if path else None,
            "execution_time": execution_time,
            "success": success
        }
        self.execution_history.append(record)
        logger.debug(f"Recorded execution: {record}")


class ResourceMonitor:
    """系统资源监控器"""
    
    def __init__(self) -> None:
        """初始化资源监控器"""
        logger.debug("Initializing ResourceMonitor")

    def get_current_resources(self) -> SystemResources:
        """
        获取当前系统资源状态
        
        返回:
            SystemResources对象，包含当前系统资源状态
        """
        # 模拟获取系统资源状态
        cpu_usage = random.uniform(0.1, 0.9)
        memory_available = random.uniform(1.0, 16.0)
        gpu_available = random.choice([True, False])
        concurrent_tasks = random.randint(1, 10)
        
        return SystemResources(
            cpu_usage=cpu_usage,
            memory_available=memory_available,
            gpu_available=gpu_available,
            concurrent_tasks=concurrent_tasks
        )


class ComplexityAnalyzer:
    """任务复杂性分析器"""
    
    def __init__(self) -> None:
        """初始化复杂性分析器"""
        self.type_weights = {
            "analysis": 0.8,
            "generation": 0.7,
            "classification": 0.5,
            "retrieval": 0.3,
            "simple": 0.2
        }
        logger.debug("Initializing ComplexityAnalyzer")

    def estimate_complexity(self, task: Dict[str, Any]) -> float:
        """
        预估任务的计算复杂性
        
        参数:
            task: 任务字典
            
        返回:
            计算复杂性分数 (0.0-1.0)
            
        异常:
            ValueError: 如果无法确定任务类型
        """
        task_type = task["type"].lower()
        task_data = task["data"]
        
        # 获取任务类型权重
        if task_type not in self.type_weights:
            logger.warning(f"Unknown task type: {task_type}, using default weight")
            type_weight = 0.5
        else:
            type_weight = self.type_weights[task_type]
        
        # 计算数据复杂性
        data_complexity = self._analyze_data_complexity(task_data)
        
        # 综合复杂性分数
        complexity = min(1.0, max(0.0, 0.6 * type_weight + 0.4 * data_complexity))
        
        return complexity

    def _analyze_data_complexity(self, data: Any) -> float:
        """
        分析任务数据的复杂性
        
        参数:
            data: 任务数据
            
        返回:
            数据复杂性分数 (0.0-1.0)
        """
        if isinstance(data, (str, int, float, bool)):
            return 0.1
        elif isinstance(data, dict):
            # 字典大小影响复杂性
            return min(1.0, len(data) / 10)
        elif isinstance(data, (list, tuple, set)):
            # 集合大小影响复杂性
            return min(1.0, math.sqrt(len(data)) / 10)
        else:
            return 0.5


def demonstrate_scheduler() -> None:
    """演示任务调度器的使用"""
    scheduler = TaskScheduler()
    
    # 创建不同类型的任务
    tasks = [
        {"type": "simple", "data": "Hello, world!"},
        {"type": "analysis", "data": {"text": "Sample text for analysis", "length": 100}},
        {"type": "classification", "data": list(range(100))},
        {"type": "generation", "data": {"prompt": "Generate a story", "length": 500}},
        {"type": "unknown", "data": {"key": "value"}}
    ]
    
    # 执行并显示结果
    for i, task in enumerate(tasks, 1):
        print(f"\n=== Task {i} ===")
        print(f"Task: {task['type']}")
        
        result = scheduler.execute_task(task)
        
        print(f"Execution path: {result['execution_path']}")
        print(f"Complexity score: {result['complexity_score']:.2f}")
        print(f"Execution time: {result['execution_time']:.4f} seconds")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Result: {result['result']}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    demonstrate_scheduler()