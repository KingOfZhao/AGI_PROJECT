"""
可执行实践清单生成协议模块

本模块实现了将抽象的'真实节点'转化为具体的、人类可执行的TODO List的协议。
核心特点是每个任务都设计为具有'可证伪性'，能够产生明确的二元反馈（成功/失败）。

输入格式:
    抽象目标节点: {
        "id": "goal_123",
        "description": "提高系统可用性",
        "domain": "devops",
        "constraints": ["两周内完成", "零停机时间"]
    }

输出格式:
    可执行任务列表: [
        {
            "task_id": "task_001",
            "action": "部署负载均衡器",
            "expected_outcome": "系统具备冗余能力",
            "verification_method": "curl测试返回200状态码",
            "is_falsifiable": True,
            "binary_feedback": None  # 待执行后填充 'success' or 'failure'
        },
        ...
    ]
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ActionableTask:
    """可执行任务的数据结构"""
    task_id: str
    action: str
    expected_outcome: str
    verification_method: str
    is_falsifiable: bool
    binary_feedback: Optional[str] = None
    created_at: str = ""
    executed_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class GoalValidationError(Exception):
    """目标验证错误"""
    pass


class TaskGenerationError(Exception):
    """任务生成错误"""
    pass


def validate_abstract_goal(goal_node: Dict[str, Any]) -> bool:
    """
    验证抽象目标节点的完整性和有效性
    
    参数:
        goal_node: 包含目标信息的字典
        
    返回:
        bool: 验证是否通过
        
    异常:
        GoalValidationError: 当目标节点不符合要求时抛出
    """
    required_fields = ['id', 'description', 'domain']
    
    if not isinstance(goal_node, dict):
        error_msg = f"目标节点必须是字典类型，当前类型: {type(goal_node)}"
        logger.error(error_msg)
        raise GoalValidationError(error_msg)
    
    missing_fields = [field for field in required_fields if field not in goal_node]
    if missing_fields:
        error_msg = f"目标节点缺少必要字段: {missing_fields}"
        logger.error(error_msg)
        raise GoalValidationError(error_msg)
    
    if not goal_node['description'] or len(goal_node['description'].strip()) < 5:
        error_msg = "目标描述太短，至少需要5个字符"
        logger.error(error_msg)
        raise GoalValidationError(error_msg)
    
    logger.info(f"目标节点验证通过: {goal_node['id']}")
    return True


def generate_task_id() -> str:
    """
    生成唯一的任务ID
    
    返回:
        str: 格式为 'task_' + uuid4前8位的唯一标识符
    """
    return f"task_{uuid.uuid4().hex[:8]}"


def make_task_falsifiable(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    辅助函数：确保任务具有可证伪性
    
    参数:
        task: 原始任务字典
        
    返回:
        Dict[str, Any]: 增强后的任务字典，包含验证方法和可证伪性标志
    """
    if 'verification_method' not in task or not task['verification_method']:
        # 根据任务类型自动生成验证方法
        action = task.get('action', '').lower()
        
        if '测试' in action or 'test' in action:
            task['verification_method'] = "执行测试并检查通过率≥90%"
        elif '部署' in action or 'deploy' in action:
            task['verification_method'] = "系统健康检查返回状态码200"
        elif '文档' in action or 'document' in action:
            task['verification_method'] = "文档通过同行评审且无重大错误"
        else:
            task['verification_method'] = "人工确认任务完成并产生可见输出"
    
    task['is_falsifiable'] = True
    task['binary_feedback'] = None
    
    return task


def generate_actionable_tasks(
    goal_node: Dict[str, Any],
    max_tasks: int = 5,
    allow_partial: bool = False
) -> List[Dict[str, Any]]:
    """
    根据抽象目标生成可执行的实践清单
    
    这是核心函数，将抽象目标分解为具体的、可证伪的任务列表。
    每个任务都设计为能够产生明确的二元反馈（成功/失败）。
    
    参数:
        goal_node: 包含目标信息的字典
        max_tasks: 最大任务数量（默认5）
        allow_partial: 是否允许生成部分任务（当无法完全分解时）
        
    返回:
        List[Dict[str, Any]]: 可执行任务列表
        
    异常:
        TaskGenerationError: 当任务生成失败时抛出
    """
    try:
        # 验证输入
        validate_abstract_goal(goal_node)
        
        if not isinstance(max_tasks, int) or max_tasks < 1:
            raise ValueError("max_tasks必须是正整数")
        
        logger.info(f"开始为目标 {goal_node['id']} 生成可执行任务")
        
        # 模拟任务分解过程
        # 在实际AGI系统中，这里会调用NLP模型进行任务分解
        domain = goal_node.get('domain', 'general')
        description = goal_node.get('description', '')
        constraints = goal_node.get('constraints', [])
        
        # 根据领域生成不同的任务模板
        tasks = []
        
        if domain == 'devops':
            tasks = _generate_devops_tasks(description, constraints, max_tasks)
        elif domain == 'development':
            tasks = _generate_development_tasks(description, constraints, max_tasks)
        else:
            tasks = _generate_generic_tasks(description, constraints, max_tasks)
        
        # 确保每个任务都是可证伪的
        falsifiable_tasks = [make_task_falsifiable(task) for task in tasks]
        
        # 转换为标准格式
        actionable_tasks = []
        for task in falsifiable_tasks[:max_tasks]:
            actionable_task = ActionableTask(
                task_id=generate_task_id(),
                action=task['action'],
                expected_outcome=task['expected_outcome'],
                verification_method=task['verification_method'],
                is_falsifiable=task['is_falsifiable']
            )
            actionable_tasks.append(asdict(actionable_task))
        
        logger.info(f"成功生成 {len(actionable_tasks)} 个可执行任务")
        return actionable_tasks
        
    except Exception as e:
        error_msg = f"任务生成失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if not allow_partial:
            raise TaskGenerationError(error_msg)
        return []


def _generate_devops_tasks(
    description: str,
    constraints: List[str],
    max_tasks: int
) -> List[Dict[str, Any]]:
    """
    生成DevOps领域的任务（辅助函数）
    
    参数:
        description: 目标描述
        constraints: 约束条件列表
        max_tasks: 最大任务数
        
    返回:
        List[Dict[str, Any]]: DevOps任务列表
    """
    # 这里应该是智能分解逻辑，简化为模板生成
    base_tasks = [
        {
            "action": "分析当前系统架构瓶颈",
            "expected_outcome": "识别出至少3个性能瓶颈点",
            "verification_method": "生成分析报告并经团队确认"
        },
        {
            "action": "部署负载均衡器",
            "expected_outcome": "系统具备冗余能力",
            "verification_method": "模拟故障切换测试成功"
        },
        {
            "action": "配置监控和报警系统",
            "expected_outcome": "关键指标可视化且报警可用",
            "verification_method": "触发测试报警并收到通知"
        }
    ]
    
    return base_tasks[:max_tasks]


def _generate_development_tasks(
    description: str,
    constraints: List[str],
    max_tasks: int
) -> List[Dict[str, Any]]:
    """生成开发领域的任务"""
    base_tasks = [
        {
            "action": "编写单元测试覆盖核心功能",
            "expected_outcome": "测试覆盖率≥80%",
            "verification_method": "运行测试套件并生成覆盖率报告"
        },
        {
            "action": "重构遗留代码模块",
            "expected_outcome": "代码复杂度降低30%",
            "verification_method": "静态代码分析工具对比结果"
        }
    ]
    return base_tasks[:max_tasks]


def _generate_generic_tasks(
    description: str,
    constraints: List[str],
    max_tasks: int
) -> List[Dict[str, Any]]:
    """生成通用任务"""
    return [
        {
            "action": f"分解目标: {description}",
            "expected_outcome": "生成详细实施计划",
            "verification_method": "计划包含至少3个可验证步骤"
        }
    ]


def update_task_feedback(
    tasks: List[Dict[str, Any]],
    task_id: str,
    feedback: str
) -> List[Dict[str, Any]]:
    """
    更新任务的二元反馈
    
    参数:
        tasks: 任务列表
        task_id: 要更新的任务ID
        feedback: 反馈值，必须是 'success' 或 'failure'
        
    返回:
        List[Dict[str, Any]]: 更新后的任务列表
        
    异常:
        ValueError: 当feedback不是有效值时
    """
    if feedback not in ['success', 'failure']:
        raise ValueError("反馈必须是 'success' 或 'failure'")
    
    updated_tasks = []
    for task in tasks:
        if task['task_id'] == task_id:
            task['binary_feedback'] = feedback
            task['executed_at'] = datetime.now().isoformat()
            logger.info(f"任务 {task_id} 反馈已更新为: {feedback}")
        updated_tasks.append(task)
    
    return updated_tasks


# 使用示例
if __name__ == "__main__":
    # 示例目标节点
    sample_goal = {
        "id": "goal_2023_001",
        "description": "提高系统可用性到99.9%",
        "domain": "devops",
        "constraints": ["两周内完成", "零停机时间"]
    }
    
    try:
        # 生成可执行任务
        tasks = generate_actionable_tasks(sample_goal, max_tasks=3)
        
        print("\n生成的可执行任务清单:")
        print("=" * 50)
        for i, task in enumerate(tasks, 1):
            print(f"\n任务 {i}:")
            print(f"ID: {task['task_id']}")
            print(f"行动: {task['action']}")
            print(f"预期结果: {task['expected_outcome']}")
            print(f"验证方法: {task['verification_method']}")
            print(f"可证伪: {'是' if task['is_falsifiable'] else '否'}")
        
        # 模拟任务反馈
        if tasks:
            print("\n模拟任务执行反馈...")
            updated_tasks = update_task_feedback(
                tasks,
                tasks[0]['task_id'],
                'success'
            )
            print(f"任务 {updated_tasks[0]['task_id']} 反馈: {updated_tasks[0]['binary_feedback']}")
        
        # 导出为JSON
        with open('actionable_tasks.json', 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        print("\n任务已导出到 actionable_tasks.json")
        
    except Exception as e:
        print(f"错误: {str(e)}")