"""
人机共生最小化实践闭环协议模块

本模块实现了一个将复杂实践目标拆解为原子化、可证伪微任务的系统。
通过降低认知负荷来提高人类反馈率和系统学习效率。

核心功能:
1. 目标分解: 将复杂目标拆解为原子化任务
2. 反馈循环: 建立最小化实践闭环
3. 认知负荷评估: 确保任务适合人类执行

典型使用场景:
    >>> from hci_symbiosis import TaskDecomposer, FeedbackLoop
    >>> decomposer = TaskDecomposer()
    >>> tasks = decomposer.decompose("学习Python基础")
    >>> loop = FeedbackLoop(tasks)
    >>> loop.run()

数据格式:
    输入: 
        - 目标描述字符串
        - 或结构化目标字典 {"goal": str, "constraints": dict}
    
    输出:
        - 任务清单: List[Dict]
        - 反馈结果: Dict
"""

import json
import logging
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    ATOMIC = auto()      # 原子任务(1步完成)
    SIMPLE = auto()      # 简单任务(2-3步)
    MODERATE = auto()    # 中等任务(4-6步)
    COMPLEX = auto()     # 复杂任务(7+步)


class FeedbackStatus(Enum):
    """反馈状态枚举"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABANDONED = auto()


@dataclass
class MicroTask:
    """微任务数据结构"""
    id: str
    description: str
    complexity: TaskComplexity
    estimated_time: int  # 分钟
    cognitive_load: float  # 0-1的认知负荷评分
    dependencies: List[str]
    feedback_status: FeedbackStatus
    created_at: datetime
    updated_at: datetime


class TaskDecomposer:
    """任务分解器
    
    将复杂目标分解为原子化微任务，确保每个任务:
    1. 可在15分钟内完成
    2. 有明确的完成标准
    3. 认知负荷低于0.7
    
    示例:
        >>> decomposer = TaskDecomposer()
        >>> tasks = decomposer.decompose("学习Python基础")
        >>> print(f"生成了 {len(tasks)} 个微任务")
    """
    
    def __init__(self, max_cognitive_load: float = 0.7):
        """初始化任务分解器
        
        Args:
            max_cognitive_load: 最大允许认知负荷(0-1)
        """
        self.max_cognitive_load = self._validate_cognitive_load(max_cognitive_load)
        self.task_patterns = self._load_task_patterns()
        
    def _validate_cognitive_load(self, value: float) -> float:
        """验证认知负荷值"""
        if not 0 <= value <= 1:
            raise ValueError("认知负荷必须在0-1之间")
        return value
    
    def _load_task_patterns(self) -> Dict:
        """加载任务分解模式库"""
        return {
            "学习": {
                "分解模式": ["理解概念", "实践练习", "项目应用"],
                "认知负荷因子": 0.6
            },
            "开发": {
                "分解模式": ["需求分析", "设计", "编码", "测试"],
                "认知负荷因子": 0.8
            },
            "研究": {
                "分解模式": ["文献调研", "假设提出", "实验设计", "数据分析"],
                "认知负荷因子": 0.7
            }
        }
    
    def decompose(
        self, 
        goal: Union[str, Dict],
        constraints: Optional[Dict] = None
    ) -> List[MicroTask]:
        """将目标分解为微任务
        
        Args:
            goal: 目标描述或结构化目标字典
            constraints: 分解约束条件，如时间限制、资源限制等
            
        Returns:
            List[MicroTask]: 分解后的微任务列表
            
        Raises:
            ValueError: 如果目标无法分解为满足认知负荷要求的微任务
        """
        logger.info(f"开始分解目标: {goal}")
        
        # 规范化输入
        if isinstance(goal, str):
            goal_dict = {"goal": goal, "type": self._detect_goal_type(goal)}
        else:
            goal_dict = goal
            
        # 验证输入
        if not goal_dict.get("goal"):
            raise ValueError("目标描述不能为空")
            
        # 应用约束条件
        constraints = constraints or {}
        time_limit = constraints.get("time_limit", 60)  # 默认60分钟
        
        # 分解目标
        try:
            raw_tasks = self._apply_decomposition_pattern(goal_dict)
            micro_tasks = self._refine_tasks(raw_tasks, time_limit)
            
            logger.info(f"成功分解为 {len(micro_tasks)} 个微任务")
            return micro_tasks
            
        except Exception as e:
            logger.error(f"目标分解失败: {str(e)}")
            raise RuntimeError(f"无法分解目标: {str(e)}") from e
    
    def _detect_goal_type(self, goal: str) -> str:
        """检测目标类型"""
        goal_lower = goal.lower()
        if any(kw in goal_lower for kw in ["学习", "掌握", "了解"]):
            return "学习"
        elif any(kw in goal_lower for kw in ["开发", "实现", "构建"]):
            return "开发"
        elif any(kw in goal_lower for kw in ["研究", "分析", "调查"]):
            return "研究"
        return "通用"
    
    def _apply_decomposition_pattern(self, goal_dict: Dict) -> List[Dict]:
        """应用分解模式"""
        goal_type = goal_dict.get("type", "通用")
        pattern = self.task_patterns.get(goal_type, {})
        steps = pattern.get("分解模式", ["计划", "执行", "检查"])
        
        tasks = []
        for i, step in enumerate(steps):
            tasks.append({
                "description": f"{goal_dict['goal']} - {step}",
                "complexity": TaskComplexity.SIMPLE,
                "estimated_time": 15,
                "cognitive_load": pattern.get("认知负荷因子", 0.5),
                "dependencies": [] if i == 0 else [f"task_{i-1}"]
            })
        return tasks
    
    def _refine_tasks(
        self, 
        raw_tasks: List[Dict], 
        time_limit: int
    ) -> List[MicroTask]:
        """优化任务以满足约束条件"""
        micro_tasks = []
        current_time = 0
        
        for i, task in enumerate(raw_tasks):
            # 如果认知负荷过高，进一步分解
            if task["cognitive_load"] > self.max_cognitive_load:
                subtasks = self._split_high_load_task(task)
                for subtask in subtasks:
                    micro_tasks.append(self._create_micro_task(subtask, i))
            else:
                micro_tasks.append(self._create_micro_task(task, i))
            
            # 检查时间约束
            current_time += task["estimated_time"]
            if current_time > time_limit:
                logger.warning(f"任务分解超出时间限制 {time_limit}分钟")
                break
                
        return micro_tasks
    
    def _split_high_load_task(self, task: Dict) -> List[Dict]:
        """拆分高认知负荷任务"""
        # 简单实现: 将任务拆分为准备、执行、验证三部分
        return [
            {
                "description": f"准备: {task['description']}",
                "complexity": TaskComplexity.ATOMIC,
                "estimated_time": 5,
                "cognitive_load": task["cognitive_load"] * 0.3,
                "dependencies": task.get("dependencies", [])
            },
            {
                "description": f"执行: {task['description']}",
                "complexity": TaskComplexity.SIMPLE,
                "estimated_time": 10,
                "cognitive_load": task["cognitive_load"] * 0.5,
                "dependencies": ["准备"]
            },
            {
                "description": f"验证: {task['description']}",
                "complexity": TaskComplexity.ATOMIC,
                "estimated_time": 5,
                "cognitive_load": task["cognitive_load"] * 0.2,
                "dependencies": ["执行"]
            }
        ]
    
    def _create_micro_task(self, task: Dict, index: int) -> MicroTask:
        """创建微任务实例"""
        now = datetime.now()
        return MicroTask(
            id=f"task_{index}_{uuid.uuid4().hex[:8]}",
            description=task["description"],
            complexity=task["complexity"],
            estimated_time=task["estimated_time"],
            cognitive_load=task["cognitive_load"],
            dependencies=task.get("dependencies", []),
            feedback_status=FeedbackStatus.PENDING,
            created_at=now,
            updated_at=now
        )


class FeedbackLoop:
    """实践反馈闭环
    
    管理人类执行微任务并提交反馈的完整循环，包括:
    1. 任务展示
    2. 进度跟踪
    3. 反馈收集
    4. 结果分析
    
    示例:
        >>> tasks = [...]  # 从TaskDecomposer获取的微任务
        >>> loop = FeedbackLoop(tasks)
        >>> loop.display_next_task()
        >>> loop.submit_feedback("task_0", {"completed": True, "notes": "完成"})
        >>> results = loop.analyze_results()
    """
    
    def __init__(self, tasks: List[MicroTask]):
        """初始化反馈闭环
        
        Args:
            tasks: 微任务列表
            
        Raises:
            ValueError: 如果任务列表为空
        """
        if not tasks:
            raise ValueError("任务列表不能为空")
            
        self.tasks = {task.id: task for task in tasks}
        self.task_order = [task.id for task in tasks]
        self.current_index = 0
        self.feedback_history = []
        
        logger.info(f"初始化反馈闭环，共 {len(tasks)} 个任务")
    
    def display_next_task(self) -> Optional[MicroTask]:
        """展示下一个待执行任务
        
        Returns:
            MicroTask: 下一个待执行的任务，如果所有任务已完成则返回None
        """
        while self.current_index < len(self.task_order):
            task_id = self.task_order[self.current_index]
            task = self.tasks[task_id]
            
            if task.feedback_status == FeedbackStatus.PENDING:
                logger.info(f"展示任务 {task_id}: {task.description}")
                return task
                
            self.current_index += 1
            
        logger.info("所有任务已完成")
        return None
    
    def submit_feedback(
        self, 
        task_id: str, 
        feedback: Dict,
        user_id: Optional[str] = None
    ) -> bool:
        """提交任务反馈
        
        Args:
            task_id: 任务ID
            feedback: 反馈数据，必须包含 'completed' 字段
            user_id: 可选的用户标识
            
        Returns:
            bool: 反馈是否成功提交
            
        Raises:
            ValueError: 如果任务ID无效或反馈格式错误
        """
        if task_id not in self.tasks:
            raise ValueError(f"无效的任务ID: {task_id}")
            
        if "completed" not in feedback:
            raise ValueError("反馈必须包含 'completed' 字段")
            
        task = self.tasks[task_id]
        
        # 更新任务状态
        task.feedback_status = (
            FeedbackStatus.COMPLETED if feedback["completed"] 
            else FeedbackStatus.FAILED
        )
        task.updated_at = datetime.now()
        
        # 记录反馈历史
        self.feedback_history.append({
            "task_id": task_id,
            "feedback": feedback,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "cognitive_load": task.cognitive_load
        })
        
        logger.info(f"收到任务 {task_id} 的反馈: {feedback}")
        return True
    
    def analyze_results(self) -> Dict:
        """分析反馈结果
        
        Returns:
            Dict: 包含统计信息的字典，如完成率、平均认知负荷等
        """
        if not self.feedback_history:
            logger.warning("没有可分析的反馈数据")
            return {"status": "no_data"}
            
        total_tasks = len(self.tasks)
        completed_tasks = sum(
            1 for task in self.tasks.values() 
            if task.feedback_status == FeedbackStatus.COMPLETED
        )
        
        avg_cognitive_load = (
            sum(f["cognitive_load"] for f in self.feedback_history) / 
            len(self.feedback_history)
        )
        
        results = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "average_cognitive_load": avg_cognitive_load,
            "feedback_count": len(self.feedback_history),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"分析结果: {results}")
        return results
    
    def get_task_recommendations(self) -> List[Dict]:
        """基于历史反馈提供任务优化建议
        
        Returns:
            List[Dict]: 优化建议列表
        """
        recommendations = []
        
        # 分析失败任务
        failed_tasks = [
            task for task in self.tasks.values() 
            if task.feedback_status == FeedbackStatus.FAILED
        ]
        
        for task in failed_tasks:
            recommendations.append({
                "task_id": task.id,
                "recommendation": "考虑进一步拆分此任务",
                "reason": f"认知负荷: {task.cognitive_load:.2f} (建议<0.7)",
                "estimated_time": task.estimated_time
            })
        
        # 分析高负荷任务
        high_load_tasks = [
            task for task in self.tasks.values() 
            if task.cognitive_load > 0.7
        ]
        
        for task in high_load_tasks:
            if task.feedback_status != FeedbackStatus.FAILED:
                recommendations.append({
                    "task_id": task.id,
                    "recommendation": "监控此任务的完成质量",
                    "reason": "认知负荷接近阈值",
                    "estimated_time": task.estimated_time
                })
        
        return recommendations


def calculate_cognitive_load(task_description: str) -> float:
    """辅助函数: 估算任务的认知负荷
    
    使用简单的启发式方法估算认知负荷:
    - 任务长度
    - 包含的关键词
    - 复杂度指示符
    
    Args:
        task_description: 任务描述
        
    Returns:
        float: 估算的认知负荷(0-1)
        
    示例:
        >>> load = calculate_cognitive_load("完成Python基础练习")
        >>> print(f"认知负荷: {load:.2f}")
    """
    # 基础负荷: 基于描述长度
    base_load = min(len(task_description) / 100, 0.4)
    
    # 复杂度关键词
    complex_keywords = ["设计", "优化", "分析", "调试", "集成"]
    keyword_load = (
        0.2 * sum(1 for kw in complex_keywords if kw in task_description)
    )
    
    # 简单关键词可以降低负荷
    simple_keywords = ["复制", "粘贴", "检查", "运行"]
    simplicity_factor = (
        0.1 * sum(1 for kw in simple_keywords if kw in task_description)
    )
    
    # 计算总负荷
    total_load = base_load + keyword_load - simplicity_factor
    
    # 确保在0-1范围内
    return max(0.1, min(total_load, 1.0))


# 使用示例
if __name__ == "__main__":
    try:
        # 1. 创建任务分解器
        decomposer = TaskDecomposer(max_cognitive_load=0.6)
        
        # 2. 分解目标
        tasks = decomposer.decompose(
            "学习Python基础",
            constraints={"time_limit": 60}
        )
        
        print(f"\n生成了 {len(tasks)} 个微任务:")
        for task in tasks:
            print(f"- {task.description} (认知负荷: {task.cognitive_load:.2f})")
        
        # 3. 创建反馈闭环
        loop = FeedbackLoop(tasks)
        
        # 4. 模拟执行任务
        while True:
            task = loop.display_next_task()
            if not task:
                break
                
            # 模拟用户反馈
            feedback = {
                "completed": True,
                "notes": "任务完成",
                "time_spent": task.estimated_time
            }
            
            loop.submit_feedback(
                task.id, 
                feedback,
                user_id="user_123"
            )
        
        # 5. 分析结果
        results = loop.analyze_results()
        print(f"\n完成率: {results['completion_rate']:.1%}")
        
        # 6. 获取优化建议
        recommendations = loop.get_task_recommendations()
        if recommendations:
            print("\n优化建议:")
            for rec in recommendations:
                print(f"- {rec['recommendation']} (原因: {rec['reason']})")
        
    except Exception as e:
        logger.error(f"示例执行失败: {str(e)}")