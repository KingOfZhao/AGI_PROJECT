"""
模块: auto_人机共生_反直觉效率_测试_验证ai_193818
描述: 执行'反直觉效率'实验，验证AI生成的策略与人类专家直觉在解决复杂问题上的效能差异。
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """策略类型枚举"""
    AI_GENERATED = "AI_Best_Practice"
    HUMAN_INTUITION = "Human_Expert_Intuition"

@dataclass
class TaskNode:
    """表示工作流中的一个任务节点"""
    node_id: str
    base_duration: float  # 基础耗时 (秒)
    complexity_factor: float  # 复杂度系数 (1.0-5.0)
    dependencies: List[str] = field(default_factory=list)
    error_probability: float = 0.05  # 任务失败概率

@dataclass
class ExperimentResult:
    """实验结果数据结构"""
    strategy_name: str
    total_duration: float
    error_count: int
    completed: bool
    path_trace: List[str]

class WorkflowSimulator:
    """
    工作流模拟器
    模拟执行任务清单并记录时间、错误等指标。
    """

    def __init__(self, nodes: List[TaskNode]):
        self.nodes = {node.node_id: node for node in nodes}
        self.simulation_time = 0.0
        self.errors = 0
        self.trace: List[str] = []

    def reset(self):
        """重置模拟器状态"""
        self.simulation_time = 0.0
        self.errors = 0
        self.trace = []

    def execute_node(self, node_id: str) -> bool:
        """
        执行单个节点任务
        
        Args:
            node_id: 节点ID
            
        Returns:
            bool: 任务是否成功完成
            
        Raises:
            ValueError: 如果节点不存在
        """
        if node_id not in self.nodes:
            logger.error(f"节点 {node_id} 不存在")
            raise ValueError(f"Invalid node ID: {node_id}")
            
        node = self.nodes[node_id]
        logger.debug(f"执行节点: {node_id}")
        
        # 模拟任务执行时间（受复杂度影响）
        actual_duration = node.base_duration * (1 + node.complexity_factor * random.random())
        self.simulation_time += actual_duration
        
        # 模拟可能的错误
        if random.random() < node.error_probability:
            self.errors += 1
            logger.warning(f"节点 {node_id} 执行出错")
            # 错误处理需要额外时间
            self.simulation_time += node.base_duration * 0.5
            return False
            
        self.trace.append(node_id)
        return True

    def run_workflow(self, sequence: List[str]) -> ExperimentResult:
        """
        按给定顺序执行工作流
        
        Args:
            sequence: 任务节点ID的执行顺序列表
            
        Returns:
            ExperimentResult: 实验结果
        """
        self.reset()
        completed = True
        
        for node_id in sequence:
            # 检查依赖是否满足
            node = self.nodes[node_id]
            unmet_deps = [dep for dep in node.dependencies if dep not in self.trace]
            
            if unmet_deps:
                logger.error(f"节点 {node_id} 的依赖未满足: {unmet_deps}")
                completed = False
                break
                
            success = self.execute_node(node_id)
            if not success:
                # 模拟错误恢复策略
                logger.info(f"尝试恢复节点 {node_id}...")
                time.sleep(0.1)  # 模拟恢复思考时间
                success = self.execute_node(node_id)
                if not success:
                    completed = False
                    break
        
        return ExperimentResult(
            strategy_name="",
            total_duration=self.simulation_time,
            error_count=self.errors,
            completed=completed,
            path_trace=self.trace.copy()
        )

def generate_complex_workflow(num_nodes: int = 10) -> List[TaskNode]:
    """
    生成复杂的工作流节点列表
    
    Args:
        num_nodes: 要生成的节点数量
        
    Returns:
        List[TaskNode]: 生成的节点列表
    """
    nodes = []
    for i in range(num_nodes):
        # 随机生成依赖关系（确保无环）
        dependencies = []
        if i > 0:
            possible_deps = [f"node_{j}" for j in range(i)]
            num_deps = random.randint(0, min(3, i))
            dependencies = random.sample(possible_deps, num_deps)
            
        node = TaskNode(
            node_id=f"node_{i}",
            base_duration=random.uniform(0.5, 2.0),
            complexity_factor=random.uniform(1.0, 5.0),
            dependencies=dependencies,
            error_probability=random.uniform(0.01, 0.1)
        )
        nodes.append(node)
    
    return nodes

def ai_strategy_planner(nodes: List[TaskNode]) -> List[str]:
    """
    AI生成的"最佳实践"策略
    基于复杂度评估和依赖关系的优化排序
    
    Args:
        nodes: 任务节点列表
        
    Returns:
        List[str]: AI推荐的任务执行顺序
    """
    # AI策略：优先执行复杂度低且依赖少的任务
    # 这是一个简化的启发式算法，实际AI可能会使用更复杂的模型
    
    # 计算每个节点的优先级分数 (越低越优先)
    priority_scores = {}
    for node in nodes:
        # 分数 = 复杂度 * (1 + 依赖数量)
        score = node.complexity_factor * (1 + len(node.dependencies))
        priority_scores[node.node_id] = score
    
    # 拓扑排序结合优先级
    in_degree = {node.node_id: 0 for node in nodes}
    graph = {node.node_id: [] for node in nodes}
    
    for node in nodes:
        for dep in node.dependencies:
            graph[dep].append(node.node_id)
            in_degree[node.node_id] += 1
    
    # 使用优先队列进行拓扑排序
    import heapq
    queue = []
    for node_id in in_degree:
        if in_degree[node_id] == 0:
            heapq.heappush(queue, (priority_scores[node_id], node_id))
    
    result = []
    while queue:
        score, node_id = heapq.heappop(queue)
        result.append(node_id)
        
        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(queue, (priority_scores[neighbor], neighbor))
    
    logger.info(f"AI生成的执行顺序: {result}")
    return result

def human_intuition_planner(nodes: List[TaskNode]) -> List[str]:
    """
    人类专家的"经验直觉"策略
    基于领域知识和经验模式的决策
    
    Args:
        nodes: 任务节点列表
        
    Returns:
        List[str]: 人类专家推荐的任务执行顺序
    """
    # 人类直觉策略：
    # 1. 优先处理看起来"重要"的任务（即使复杂）
    # 2. 倾向于按照熟悉的工作模式（如线性顺序）
    # 3. 可能忽略某些隐藏的依赖关系
    
    # 简化模型：人类专家会基于"重要性直觉"排序
    # 这里我们模拟人类可能会优先处理某些特定类型的任务
    
    # 首先按node_id排序（模拟线性思维）
    sorted_nodes = sorted(nodes, key=lambda x: x.node_id)
    
    # 但人类可能会在某些点做出"直觉跳跃"
    result = []
    remaining = {node.node_id for node in nodes}
    
    # 模拟人类专家的决策过程
    while remaining:
        # 选择下一个任务（简化模型）
        candidates = [n for n in sorted_nodes if n.node_id in remaining]
        
        if not candidates:
            break
            
        # 人类专家可能会基于"直觉"选择复杂度适中的任务
        # 或者选择看起来"最紧急"的任务
        selected = None
        
        # 模拟人类专家可能会优先处理基础任务(node_0, node_1等)
        for node in candidates:
            if node.node_id == f"node_{len(result)}":
                selected = node
                break
                
        if not selected:
            # 如果没有明显的顺序，选择复杂度适中的任务
            avg_complexity = sum(n.complexity_factor for n in candidates) / len(candidates)
            selected = min(candidates, key=lambda x: abs(x.complexity_factor - avg_complexity))
        
        result.append(selected.node_id)
        remaining.remove(selected.node_id)
    
    logger.info(f"人类专家的执行顺序: {result}")
    return result

def run_experiment(
    num_trials: int = 10,
    num_nodes: int = 8,
    verbose: bool = False
) -> Dict[str, Dict[str, float]]:
    """
    运行对比实验
    
    Args:
        num_trials: 实验次数
        num_nodes: 每次实验的节点数量
        verbose: 是否显示详细日志
        
    Returns:
        Dict[str, Dict[str, float]]: 实验结果统计
    """
    if not isinstance(num_trials, int) or num_trials < 1:
        raise ValueError("实验次数必须是正整数")
        
    if not isinstance(num_nodes, int) or num_nodes < 3:
        raise ValueError("节点数量必须至少为3")
    
    # 临时调整日志级别
    if not verbose:
        logging.getLogger().setLevel(logging.WARNING)
    
    results = {
        StrategyType.AI_GENERATED.value: {
            "total_duration": 0.0,
            "total_errors": 0,
            "success_rate": 0.0
        },
        StrategyType.HUMAN_INTUITION.value: {
            "total_duration": 0.0,
            "total_errors": 0,
            "success_rate": 0.0
        }
    }
    
    for trial in range(1, num_trials + 1):
        print(f"\n=== 实验第 {trial}/{num_trials} 次 ===")
        
        # 生成随机工作流
        nodes = generate_complex_workflow(num_nodes)
        simulator = WorkflowSimulator(nodes)
        
        # AI策略
        ai_sequence = ai_strategy_planner(nodes)
        ai_result = simulator.run_workflow(ai_sequence)
        ai_result.strategy_name = StrategyType.AI_GENERATED.value
        
        # 人类策略
        human_sequence = human_intuition_planner(nodes)
        human_result = simulator.run_workflow(human_sequence)
        human_result.strategy_name = StrategyType.HUMAN_INTUITION.value
        
        # 记录结果
        results[StrategyType.AI_GENERATED.value]["total_duration"] += ai_result.total_duration
        results[StrategyType.AI_GENERATED.value]["total_errors"] += ai_result.error_count
        if ai_result.completed:
            results[StrategyType.AI_GENERATED.value]["success_rate"] += 1
            
        results[StrategyType.HUMAN_INTUITION.value]["total_duration"] += human_result.total_duration
        results[StrategyType.HUMAN_INTUITION.value]["total_errors"] += human_result.error_count
        if human_result.completed:
            results[StrategyType.HUMAN_INTUITION.value]["success_rate"] += 1
        
        # 打印单次结果
        print(f"AI策略 - 耗时: {ai_result.total_duration:.2f}s, 错误: {ai_result.error_count}, 完成: {'是' if ai_result.completed else '否'}")
        print(f"人类策略 - 耗时: {human_result.total_duration:.2f}s, 错误: {human_result.error_count}, 完成: {'是' if human_result.completed else '否'}")
    
    # 计算平均值
    for strategy in results:
        results[strategy]["avg_duration"] = results[strategy]["total_duration"] / num_trials
        results[strategy]["avg_errors"] = results[strategy]["total_errors"] / num_trials
        results[strategy]["success_rate"] = results[strategy]["success_rate"] / num_trials * 100
    
    # 恢复日志级别
    if not verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    return results

def analyze_results(results: Dict[str, Dict[str, float]]) -> None:
    """
    分析并打印实验结果
    
    Args:
        results: run_experiment返回的结果字典
    """
    print("\n=== 实验结果分析 ===")
    
    ai_data = results[StrategyType.AI_GENERATED.value]
    human_data = results[StrategyType.HUMAN_INTUITION.value]
    
    print(f"AI生成策略:")
    print(f"  平均耗时: {ai_data['avg_duration']:.2f}秒")
    print(f"  平均错误: {ai_data['avg_errors']:.1f}")
    print(f"  成功率: {ai_data['success_rate']:.1f}%")
    
    print(f"\n人类专家策略:")
    print(f"  平均耗时: {human_data['avg_duration']:.2f}秒")
    print(f"  平均错误: {human_data['avg_errors']:.1f}")
    print(f"  成功率: {human_data['success_rate']:.1f}%")
    
    # 判断哪种策略更优
    print("\n=== 结论 ===")
    if ai_data['avg_duration'] < human_data['avg_duration'] * 0.9:
        print("AI生成的策略在效率上显著优于人类直觉")
    elif human_data['avg_duration'] < ai_data['avg_duration'] * 0.9:
        print("人类专家的直觉在效率上显著优于AI生成策略")
    else:
        print("两种策略在效率上没有显著差异")
    
    if ai_data['success_rate'] > human_data['success_rate'] + 10:
        print("AI生成的策略在可靠性上显著优于人类直觉")
    elif human_data['success_rate'] > ai_data['success_rate'] + 10:
        print("人类专家的直觉在可靠性上显著优于AI生成策略")
    else:
        print("两种策略在可靠性上相当")

if __name__ == "__main__":
    # 示例用法
    print("开始人机共生反直觉效率实验...")
    print("本实验将对比AI生成的策略与人类专家直觉在解决复杂工作流时的效率")
    
    # 运行实验（可调整参数）
    experiment_results = run_experiment(
        num_trials=5,
        num_nodes=6,
        verbose=True
    )
    
    # 分析结果
    analyze_results(experiment_results)