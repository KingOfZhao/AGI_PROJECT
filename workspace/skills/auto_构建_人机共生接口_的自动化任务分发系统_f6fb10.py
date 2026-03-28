"""
人机共生接口自动化任务分发系统

本模块实现了一个智能任务分发系统，用于构建人机共生接口。系统能够：
1. 识别认知网络中的缺口和模糊领域
2. 自动生成微任务清单供人类验证
3. 优化标签成本效益比
4. 处理AI难以自我验证的领域（如情感、审美）

数据流：
输入 -> 认知缺口检测 -> 微任务生成 -> 人类验证 -> 反馈学习 -> 更新认知网络

典型使用示例：
    system = HCAgentSystem()
    tasks = system.generate_microtasks({"text": "这首诗很美", "domain": "aesthetics"})
    result = system.collect_human_feedback(tasks[0], {"rating": 4, "notes": "优美的意象"})
"""

import logging
import json
import hashlib
import time
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HCAgentSystem")


class TaskDomain(Enum):
    """微任务领域分类"""
    EMOTION = "emotion"
    AESTHETICS = "aesthetics"
    ETHICS = "ethics"
    CULTURAL = "cultural"
    COMMON_SENSE = "common_sense"


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class MicroTask:
    """微任务数据结构"""
    task_id: str
    domain: TaskDomain
    description: str
    content: Dict
    priority: TaskPriority
    reward: float
    required_qualifications: List[str]
    time_estimate: float  # 估计完成时间(分钟)
    created_at: float
    expires_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """将任务转换为字典格式"""
        return {
            **asdict(self),
            "domain": self.domain.value,
            "priority": self.priority.value
        }


@dataclass
class HumanFeedback:
    """人类反馈数据结构"""
    task_id: str
    worker_id: str
    response: Dict
    confidence: float  # 0-1之间的置信度
    time_taken: float  # 实际完成时间(分钟)
    comments: Optional[str] = None


class CognitiveNetwork:
    """认知网络模拟类，用于检测认知缺口"""
    
    def __init__(self):
        self.known_domains = {
            TaskDomain.EMOTION: 0.7,  # 置信度分数
            TaskDomain.AESTHETICS: 0.5,
            TaskDomain.ETHICS: 0.6,
            TaskDomain.CULTURAL: 0.4,
            TaskDomain.COMMON_SENSE: 0.8
        }
        self.feedback_history = []
    
    def detect_gaps(self, threshold: float = 0.6) -> List[TaskDomain]:
        """检测认知缺口"""
        gaps = []
        for domain, confidence in self.known_domains.items():
            if confidence < threshold:
                gaps.append(domain)
        return gaps
    
    def update_with_feedback(self, feedback: HumanFeedback):
        """根据反馈更新认知网络"""
        domain = TaskDomain[feedback.response.get("domain", "EMOTION").upper()]
        current_confidence = self.known_domains.get(domain, 0)
        
        # 根据人类置信度和当前置信度计算新置信度
        new_confidence = min(1.0, current_confidence + 0.05 * feedback.confidence)
        self.known_domains[domain] = new_confidence
        
        # 记录反馈历史
        self.feedback_history.append(feedback)
        logger.info(f"Updated confidence for {domain.value} to {new_confidence:.2f}")


class HCAgentSystem:
    """人机共生接口自动化任务分发系统"""
    
    def __init__(self):
        self.cognitive_network = CognitiveNetwork()
        self.task_queue: List[MicroTask] = []
        self.completed_tasks: Dict[str, HumanFeedback] = {}
        self.worker_pool: Dict[str, Dict] = {}  # 工作者池
        
        # 领域相关的任务模板
        self.task_templates = {
            TaskDomain.EMOTION: {
                "description": "请评价这段文本表达的情感",
                "reward_range": (0.05, 0.15),
                "time_range": (1, 5)
            },
            TaskDomain.AESTHETICS: {
                "description": "请评价这个作品的美学价值",
                "reward_range": (0.10, 0.25),
                "time_range": (2, 10)
            },
            TaskDomain.ETHICS: {
                "description": "请评价这个行为的伦理合理性",
                "reward_range": (0.15, 0.30),
                "time_range": (3, 15)
            }
        }
    
    def generate_microtasks(
        self,
        content: Dict,
        domain: Optional[Union[str, TaskDomain]] = None,
        num_tasks: int = 1,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> List[MicroTask]:
        """
        生成微任务清单
        
        参数:
            content: 需要人类验证的内容
            domain: 任务领域(可选)
            num_tasks: 需要生成的任务数量
            priority: 任务优先级
            
        返回:
            生成的微任务列表
            
        示例:
            system = HCAgentSystem()
            tasks = system.generate_microtasks(
                {"text": "这首诗很美", "domain": "aesthetics"},
                domain=TaskDomain.AESTHETICS
            )
        """
        if num_tasks <= 0:
            raise ValueError("Number of tasks must be positive")
        
        # 确定任务领域
        if domain is None:
            detected_domain = self._detect_domain(content)
            domain_enum = TaskDomain(detected_domain.lower())
        elif isinstance(domain, str):
            domain_enum = TaskDomain(domain.lower())
        else:
            domain_enum = domain
        
        # 获取任务模板
        template = self.task_templates.get(
            domain_enum,
            {"description": "请评价这个内容", "reward_range": (0.05, 0.10), "time_range": (1, 5)}
        )
        
        tasks = []
        current_time = time.time()
        
        for i in range(num_tasks):
            # 生成唯一任务ID
            task_id = hashlib.md5(
                f"{domain_enum.value}_{current_time}_{i}".encode()
            ).hexdigest()
            
            # 计算奖励和时间估计
            reward = random.uniform(*template["reward_range"])
            time_estimate = random.uniform(*template["time_range"])
            
            # 创建微任务
            task = MicroTask(
                task_id=task_id,
                domain=domain_enum,
                description=template["description"],
                content=content,
                priority=priority,
                reward=round(reward, 2),
                required_qualifications=self._determine_qualifications(domain_enum),
                time_estimate=round(time_estimate, 1),
                created_at=current_time,
                expires_at=current_time + 3600  # 1小时后过期
            )
            
            tasks.append(task)
            self.task_queue.append(task)
            
            logger.info(f"Generated task {task_id} in domain {domain_enum.value}")
        
        return tasks
    
    def collect_human_feedback(
        self,
        task: MicroTask,
        response: Dict,
        worker_id: str = "default_worker",
        confidence: float = 1.0,
        comments: Optional[str] = None
    ) -> HumanFeedback:
        """
        收集人类对微任务的反馈
        
        参数:
            task: 要反馈的微任务
            response: 人类响应内容
            worker_id: 工作者ID
            confidence: 工作者对响应的置信度(0-1)
            comments: 可选的附加注释
            
        返回:
            人类反馈对象
            
        示例:
            feedback = system.collect_human_feedback(
                tasks[0],
                {"rating": 4, "notes": "优美的意象"},
                worker_id="worker123",
                confidence=0.9
            )
        """
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        if task.task_id not in [t.task_id for t in self.task_queue]:
            logger.warning(f"Task {task.task_id} not found in queue")
        
        # 记录完成时间
        time_taken = time.time() - task.created_at
        
        feedback = HumanFeedback(
            task_id=task.task_id,
            worker_id=worker_id,
            response=response,
            confidence=confidence,
            time_taken=time_taken,
            comments=comments
        )
        
        # 更新认知网络
        self.cognitive_network.update_with_feedback(feedback)
        
        # 记录完成的任务
        self.completed_tasks[task.task_id] = feedback
        
        # 从队列中移除任务
        self.task_queue = [t for t in self.task_queue if t.task_id != task.task_id]
        
        logger.info(f"Collected feedback for task {task.task_id} from worker {worker_id}")
        
        return feedback
    
    def optimize_task_distribution(self) -> Dict[str, List[MicroTask]]:
        """
        优化任务分发，将任务分配给最合适的工作者
        
        返回:
            工作者ID到任务列表的映射
            
        示例:
            distribution = system.optimize_task_distribution()
            for worker_id, tasks in distribution.items():
                print(f"Assign {len(tasks)} tasks to {worker_id}")
        """
        # 按优先级排序任务
        sorted_tasks = sorted(
            self.task_queue,
            key=lambda t: t.priority.value
        )
        
        distribution = {}
        
        # 为每个任务找到最合适的工作者
        for task in sorted_tasks:
            best_worker = self._find_best_worker(task)
            
            if best_worker not in distribution:
                distribution[best_worker] = []
            
            distribution[best_worker].append(task)
        
        logger.info(f"Optimized distribution for {len(self.task_queue)} tasks")
        return distribution
    
    # 辅助方法
    def _detect_domain(self, content: Dict) -> str:
        """检测内容所属领域"""
        text = content.get("text", "").lower()
        
        if any(word in text for word in ["美", "漂亮", "艺术", "审美"]):
            return "aesthetics"
        elif any(word in text for word in ["情感", "情绪", "感觉", "感受"]):
            return "emotion"
        elif any(word in text for word in ["伦理", "道德", "正确", "错误"]):
            return "ethics"
        else:
            return "common_sense"
    
    def _determine_qualifications(self, domain: TaskDomain) -> List[str]:
        """确定完成任务所需的资格"""
        qualifications = ["basic_verification"]
        
        if domain == TaskDomain.EMOTION:
            qualifications.append("emotional_intelligence")
        elif domain == TaskDomain.AESTHETICS:
            qualifications.append("artistic_judgment")
        elif domain == TaskDomain.ETHICS:
            qualifications.append("ethical_reasoning")
        
        return qualifications
    
    def _find_best_worker(self, task: MicroTask) -> str:
        """为任务找到最合适的工作者"""
        if not self.worker_pool:
            return "default_worker"
        
        # 这里应该有更复杂的匹配逻辑
        # 简化版: 随机选择一个工作者
        return random.choice(list(self.worker_pool.keys()))
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "pending_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "cognitive_gaps": [d.value for d in self.cognitive_network.detect_gaps()],
            "confidence_scores": {
                d.value: c for d, c in self.cognitive_network.known_domains.items()
            }
        }


if __name__ == "__main__":
    # 示例用法
    system = HCAgentSystem()
    
    # 添加一些模拟工作者
    system.worker_pool = {
        "worker1": {"skills": ["emotional_intelligence"]},
        "worker2": {"skills": ["artistic_judgment"]},
        "worker3": {"skills": ["ethical_reasoning"]}
    }
    
    # 生成微任务
    tasks = system.generate_microtasks(
        {"text": "这首诗通过优美的意象表达了深沉的忧伤", "domain": "aesthetics"},
        domain=TaskDomain.AESTHETICS,
        num_tasks=3
    )
    
    print(f"Generated {len(tasks)} tasks")
    
    # 收集人类反馈
    if tasks:
        feedback = system.collect_human_feedback(
            tasks[0],
            {"rating": 4, "notes": "优美的意象"},
            worker_id="worker2",
            confidence=0.9
        )
        print(f"Collected feedback: {feedback}")
    
    # 优化任务分发
    distribution = system.optimize_task_distribution()
    print("Task distribution:", distribution)
    
    # 获取系统状态
    status = system.get_system_status()
    print("System status:", status)