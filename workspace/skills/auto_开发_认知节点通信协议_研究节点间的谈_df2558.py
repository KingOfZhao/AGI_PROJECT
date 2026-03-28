"""
Module: cognitive_comm_protocol.py
Description: 实现认知节点通信协议，包含谈判、拍卖与任务分配机制，用于验证多智能体系统的涌现能力。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveProtocol")


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    description: str
    complexity: float  # 任务复杂度 (1.0 - 10.0)
    required_resources: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_node: Optional[str] = None

    def __post_init__(self):
        """数据验证"""
        if not 1.0 <= self.complexity <= 10.0:
            raise ValueError("Task complexity must be between 1.0 and 10.0")
        if not self.task_id or not self.description:
            raise ValueError("Task ID and description cannot be empty")


@dataclass
class Bid:
    """出价数据结构"""
    node_id: str
    task_id: str
    estimated_time: float  # 预估完成时间 (小时)
    cost: float  # 成本
    confidence: float  # 信心指数 (0.0 - 1.0)

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.estimated_time <= 0 or self.cost <= 0:
            raise ValueError("Estimated time and cost must be positive values")


class CognitiveNode:
    """认知节点类，模拟智能体行为"""

    def __init__(self, node_id: str, capabilities: List[str], capacity: float = 1.0):
        """
        初始化认知节点
        
        Args:
            node_id: 节点唯一标识符
            capabilities: 节点具备的能力列表
            capacity: 节点处理能力 (0.1 - 2.0)
        """
        if not 0.1 <= capacity <= 2.0:
            raise ValueError("Capacity must be between 0.1 and 2.0")
        
        self.node_id = node_id
        self.capabilities = capabilities
        self.capacity = capacity
        self.current_load = 0.0
        self.task_history: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized cognitive node: {node_id} with capabilities: {capabilities}")

    def evaluate_task(self, task: Task) -> Optional[Bid]:
        """
        评估任务并生成出价
        
        Args:
            task: 待评估的任务
            
        Returns:
            Bid对象或None(如果节点无法处理该任务)
        """
        # 检查是否具备所需资源
        missing_resources = set(task.required_resources) - set(self.capabilities)
        if missing_resources:
            logger.debug(f"Node {self.node_id} lacks resources for task {task.task_id}: {missing_resources}")
            return None
        
        # 计算出价参数
        try:
            base_time = task.complexity * 2.0 / self.capacity
            # 添加一些随机性模拟真实世界的不确定性
            estimated_time = base_time * (1 + random.uniform(-0.1, 0.1))
            cost = task.complexity * 5.0 * (1.5 - self.capacity)
            confidence = min(1.0, self.capacity / task.complexity * 0.8)
            
            return Bid(
                node_id=self.node_id,
                task_id=task.task_id,
                estimated_time=max(0.1, estimated_time),  # 确保不为零
                cost=max(1.0, cost),
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Error evaluating task {task.task_id}: {str(e)}")
            return None


def run_auction(tasks: List[Task], nodes: List[CognitiveNode]) -> Dict[str, Tuple[str, float]]:
    """
    运行拍卖机制分配任务
    
    Args:
        tasks: 待分配的任务列表
        nodes: 参与竞标的节点列表
        
    Returns:
        任务分配结果字典 {task_id: (assigned_node, final_cost)}
        
    Example:
        >>> tasks = [Task("T1", "Data processing", 5.0, ["compute"])]
        >>> nodes = [CognitiveNode("N1", ["compute"], 1.2)]
        >>> allocation = run_auction(tasks, nodes)
        >>> print(allocation["T1"])  # 输出: ('N1', 12.5)
    """
    if not tasks or not nodes:
        logger.warning("Empty tasks or nodes list provided to auction")
        return {}

    allocation = {}
    
    for task in tasks:
        logger.info(f"Starting auction for task: {task.task_id}")
        
        # 收集所有出价
        bids = []
        for node in nodes:
            try:
                bid = node.evaluate_task(task)
                if bid:
                    bids.append(bid)
                    logger.debug(f"Node {node.node_id} bid on task {task.task_id}: "
                                f"Time={bid.estimated_time:.2f}h, Cost=${bid.cost:.2f}, "
                                f"Confidence={bid.confidence:.2f}")
            except Exception as e:
                logger.error(f"Node {node.node_id} failed to evaluate task {task.task_id}: {str(e)}")
        
        # 选择最优出价 (基于成本和信心的加权评分)
        if bids:
            best_bid = max(bids, key=lambda b: b.confidence / b.cost)
            allocation[task.task_id] = (best_bid.node_id, best_bid.cost)
            
            # 更新任务状态
            task.status = TaskStatus.ASSIGNED
            task.assigned_node = best_bid.node_id
            
            # 更新节点负载
            for node in nodes:
                if node.node_id == best_bid.node_id:
                    node.current_load += task.complexity / node.capacity
                    node.task_history.append({
                        "task_id": task.task_id,
                        "cost": best_bid.cost,
                        "time": best_bid.estimated_time
                    })
                    break
            
            logger.info(f"Task {task.task_id} assigned to node {best_bid.node_id} "
                       f"at cost ${best_bid.cost:.2f}")
        else:
            task.status = TaskStatus.FAILED
            logger.warning(f"No valid bids for task {task.task_id}")
    
    return allocation


def negotiate_task_reallocation(
    nodes: List[CognitiveNode],
    overloaded_threshold: float = 1.5
) -> Dict[str, List[str]]:
    """
    谈判机制：过载节点尝试将任务重新分配给其他节点
    
    Args:
        nodes: 参与谈判的节点列表
        overloaded_threshold: 判定节点过载的阈值
        
    Returns:
        重新分配的任务映射 {source_node: [task_ids_to_transfer]}
        
    Example:
        >>> overloaded_nodes = [node for node in nodes if node.current_load > overloaded_threshold]
        >>> transfers = negotiate_task_reallocation(overloaded_nodes)
        >>> print(transfers)  # 输出: {'N1': ['T1', 'T2']}
    """
    transfer_plan = {}
    
    # 识别过载节点
    overloaded_nodes = [node for node in nodes if node.current_load > overloaded_threshold]
    if not overloaded_nodes:
        logger.info("No overloaded nodes detected during negotiation")
        return transfer_plan
    
    logger.info(f"Detected {len(overloaded_nodes)} overloaded nodes, starting negotiation")
    
    # 识别有空闲能力的节点
    available_nodes = [
        node for node in nodes 
        if node.current_load < overloaded_threshold * 0.8
    ]
    
    if not available_nodes:
        logger.warning("No available nodes for task reallocation")
        return transfer_plan
    
    # 过载节点发起谈判
    for overloaded_node in overloaded_nodes:
        tasks_to_transfer = []
        avg_load = sum(node.current_load for node in available_nodes) / len(available_nodes)
        
        # 按成本从高到低排序任务 (优先转移高成本任务)
        sorted_tasks = sorted(
            overloaded_node.task_history,
            key=lambda t: t['cost'],
            reverse=True
        )
        
        # 计算需要转移的任务量以达到平衡
        transfer_amount = overloaded_node.current_load - (overloaded_threshold * 0.7)
        current_transferred = 0.0
        
        for task in sorted_tasks:
            # 检查是否有节点愿意接收该任务
            for available_node in available_nodes:
                # 简单谈判逻辑: 如果接收后不超过平均负载的1.2倍，则接受
                if (available_node.current_load + task['cost'] / available_node.capacity) < avg_load * 1.2:
                    tasks_to_transfer.append(task['task_id'])
                    current_transferred += task['cost'] / available_node.capacity
                    available_node.current_load += task['cost'] / available_node.capacity
                    break
            
            if current_transferred >= transfer_amount:
                break
        
        if tasks_to_transfer:
            transfer_plan[overloaded_node.node_id] = tasks_to_transfer
            logger.info(f"Negotiated transfer of {len(tasks_to_transfer)} tasks from "
                       f"{overloaded_node.node_id} to available nodes")
    
    return transfer_plan


def simulate_cognitive_system(num_nodes: int = 5, num_tasks: int = 10) -> None:
    """
    模拟认知节点系统的完整运行流程
    
    Args:
        num_nodes: 节点数量
        num_tasks: 任务数量
    """
    logger.info(f"Starting cognitive system simulation with {num_nodes} nodes and {num_tasks} tasks")
    
    # 创建认知节点
    capabilities = ["compute", "storage", "network", "ai", "database"]
    nodes = [
        CognitiveNode(
            node_id=f"Node-{i}",
            capabilities=random.sample(capabilities, random.randint(1, 3)),
            capacity=random.uniform(0.5, 1.8)
        )
        for i in range(num_nodes)
    ]
    
    # 创建任务
    tasks = [
        Task(
            task_id=f"Task-{i}",
            description=f"Complex task {i}",
            complexity=random.uniform(1.0, 10.0),
            required_resources=random.sample(capabilities, random.randint(1, 2))
        )
        for i in range(num_tasks)
    ]
    
    # 第一轮任务分配
    allocation = run_auction(tasks, nodes)
    
    # 显示分配结果
    print("\nInitial Task Allocation:")
    for task_id, (node_id, cost) in allocation.items():
        print(f"{task_id} -> {node_id} (${cost:.2f})")
    
    # 模拟负载不平衡
    for node in nodes:
        print(f"{node.node_id} current load: {node.current_load:.2f}")
    
    # 谈判重新分配过载任务
    transfers = negotiate_task_reallocation(nodes)
    
    print("\nTask Reallocation Plan:")
    for source_node, task_ids in transfers.items():
        print(f"{source_node} will transfer tasks: {', '.join(task_ids)}")
    
    # 模拟任务执行结果
    completed_tasks = []
    for task in tasks:
        if task.status == TaskStatus.ASSIGNED:
            # 模拟执行结果 (80%成功率)
            if random.random() < 0.8:
                task.status = TaskStatus.COMPLETED
                completed_tasks.append(task.task_id)
            else:
                task.status = TaskStatus.FAILED
    
    print("\nTask Execution Results:")
    print(f"Completed: {len(completed_tasks)}/{num_tasks}")
    print(f"Failed: {num_tasks - len(completed_tasks) - (num_tasks - len(allocation))}")


if __name__ == "__main__":
    # 示例使用
    simulate_cognitive_system(num_nodes=5, num_tasks=15)