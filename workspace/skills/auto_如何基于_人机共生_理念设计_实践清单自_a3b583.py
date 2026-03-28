"""
人机共生实践清单自动生成器

本模块实现了一个基于人机共生理念的实践清单生成系统。系统将模糊的假设性节点
转化为具体的人类可执行步骤，并通过反馈机制验证节点状态。

核心功能：
1. 将模糊假设转化为具体行动步骤
2. 生成可执行清单并跟踪执行状态
3. 根据人类反馈固化假设节点
4. 提供详细的执行日志和状态报告

输入格式示例：
{
    "assumption": "用户可能需要更好的时间管理",
    "context": "工作场景",
    "priority": 3
}

输出格式示例：
{
    "status": "generated",
    "steps": [
        {
            "action": "记录每日时间消耗",
            "type": "physical",
            "estimated_time": "15分钟/天",
            "verification_method": "提供一周的时间记录"
        }
    ],
    "assumption_id": "a3b583"
}
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hci_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """行动步骤类型枚举"""
    PHYSICAL = auto()    # 物理行动
    SOCIAL = auto()      # 社会行动
    COGNITIVE = auto()   # 认知行动
    DIGITAL = auto()     # 数字行动


class NodeStatus(Enum):
    """节点状态枚举"""
    ASSUMPTION = auto()  # 假设状态
    GENERATED = auto()   # 已生成清单
    EXECUTING = auto()   # 执行中
    VERIFIED = auto()    # 已验证/固化


@dataclass
class ActionStep:
    """行动步骤数据类"""
    action: str
    type: ActionType
    estimated_time: str
    verification_method: str
    completed: bool = False
    feedback: Optional[str] = None


@dataclass
class AssumptionNode:
    """假设节点数据类"""
    assumption: str
    context: str
    priority: int
    status: NodeStatus
    steps: List[ActionStep]
    created_at: str
    updated_at: str
    node_id: str


class HCIGeneratorError(Exception):
    """自定义异常类"""
    pass


def validate_input_data(data: Dict) -> bool:
    """
    验证输入数据是否符合要求
    
    参数:
        data: 输入数据字典
        
    返回:
        bool: 数据是否有效
        
    示例:
        >>> validate_input_data({"assumption": "test", "context": "work", "priority": 3})
        True
    """
    required_fields = ["assumption", "context", "priority"]
    
    if not isinstance(data, dict):
        logger.error("输入数据不是字典类型")
        return False
    
    for field in required_fields:
        if field not in data:
            logger.error(f"缺少必要字段: {field}")
            return False
    
    if not isinstance(data["assumption"], str) or len(data["assumption"]) < 5:
        logger.error("假设描述过短或类型错误")
        return False
    
    if not isinstance(data["priority"], int) or not (1 <= data["priority"] <= 5):
        logger.error("优先级应为1-5之间的整数")
        return False
    
    return True


def generate_node_id(assumption: str) -> str:
    """
    生成唯一节点ID
    
    参数:
        assumption: 假设描述文本
        
    返回:
        str: 唯一节点ID
        
    示例:
        >>> generate_node_id("用户需要更好的时间管理")
        "a3b583"
    """
    hash_obj = hashlib.md5(assumption.encode())
    return hash_obj.hexdigest()[:6]


def generate_action_steps(assumption: str, context: str) -> List[ActionStep]:
    """
    将模糊假设转化为具体行动步骤
    
    参数:
        assumption: 假设描述
        context: 上下文环境
        
    返回:
        List[ActionStep]: 行动步骤列表
        
    示例:
        >>> steps = generate_action_steps("用户需要更好的时间管理", "工作场景")
        >>> print(steps[0].action)
        "记录每日时间消耗"
    """
    # 这里应该有更复杂的NLP处理逻辑，简化示例
    templates = {
        "时间管理": [
            ("记录每日时间消耗", ActionType.PHYSICAL, "15分钟/天", "提供一周的时间记录"),
            ("设定每日优先任务", ActionType.COGNITIVE, "10分钟/天", "展示任务清单"),
            ("每周回顾时间使用", ActionType.COGNITIVE, "30分钟/周", "提供回顾报告")
        ],
        "健康管理": [
            ("每日记录饮食", ActionType.PHYSICAL, "10分钟/天", "提供饮食记录"),
            ("每周运动3次", ActionType.PHYSICAL, "30分钟/次", "提供运动日志"),
            ("每月体检", ActionType.SOCIAL, "2小时/月", "提供体检报告")
        ]
    }
    
    steps = []
    for keyword, actions in templates.items():
        if keyword in assumption:
            for action in actions:
                steps.append(ActionStep(
                    action=action[0],
                    type=action[1],
                    estimated_time=action[2],
                    verification_method=action[3]
                ))
    
    if not steps:
        # 默认通用步骤
        steps = [
            ActionStep(
                action="明确具体需求",
                type=ActionType.COGNITIVE,
                estimated_time="30分钟",
                verification_method="提供需求文档"
            ),
            ActionStep(
                action="与相关方讨论",
                type=ActionType.SOCIAL,
                estimated_time="1小时",
                verification_method="会议记录"
            )
        ]
    
    logger.info(f"为假设 '{assumption}' 生成了 {len(steps)} 个行动步骤")
    return steps


def create_practice_checklist(input_data: Dict) -> Dict:
    """
    创建实践清单的主函数
    
    参数:
        input_data: 包含假设信息的输入数据
        
    返回:
        Dict: 生成的实践清单
        
    示例:
        >>> result = create_practice_checklist({
        ...     "assumption": "用户需要更好的时间管理",
        ...     "context": "工作场景",
        ...     "priority": 3
        ... })
        >>> print(result["status"])
        "generated"
    """
    try:
        # 验证输入
        if not validate_input_data(input_data):
            raise HCIGeneratorError("输入数据验证失败")
        
        # 生成节点ID
        node_id = generate_node_id(input_data["assumption"])
        
        # 生成行动步骤
        steps = generate_action_steps(
            input_data["assumption"],
            input_data["context"]
        )
        
        # 创建节点
        node = AssumptionNode(
            assumption=input_data["assumption"],
            context=input_data["context"],
            priority=input_data["priority"],
            status=NodeStatus.GENERATED,
            steps=steps,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            node_id=node_id
        )
        
        # 转换为可序列化字典
        result = asdict(node)
        result["status"] = node.status.name
        result["steps"] = [
            {
                **asdict(step),
                "type": step.type.name
            }
            for step in node.steps
        ]
        
        logger.info(f"成功生成实践清单，节点ID: {node_id}")
        return result
        
    except Exception as e:
        logger.error(f"生成实践清单时出错: {str(e)}")
        raise HCIGeneratorError(f"生成失败: {str(e)}")


def update_node_with_feedback(
    node_data: Dict,
    step_index: int,
    completed: bool,
    feedback: str
) -> Dict:
    """
    根据人类反馈更新节点状态
    
    参数:
        node_data: 节点数据
        step_index: 步骤索引
        completed: 是否完成
        feedback: 反馈内容
        
    返回:
        Dict: 更新后的节点数据
        
    示例:
        >>> updated = update_node_with_feedback(node_data, 0, True, "已完成时间记录")
        >>> print(updated["steps"][0]["completed"])
        True
    """
    try:
        # 验证步骤索引
        if not 0 <= step_index < len(node_data["steps"]):
            raise HCIGeneratorError("无效的步骤索引")
        
        # 更新步骤状态
        node_data["steps"][step_index]["completed"] = completed
        node_data["steps"][step_index]["feedback"] = feedback
        
        # 检查所有步骤是否完成
        all_completed = all(step["completed"] for step in node_data["steps"])
        
        if all_completed:
            node_data["status"] = NodeStatus.VERIFIED.name
            logger.info(f"节点 {node_data['node_id']} 已固化")
        else:
            node_data["status"] = NodeStatus.EXECUTING.name
        
        node_data["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"更新节点 {node_data['node_id']} 的步骤 {step_index}")
        return node_data
        
    except Exception as e:
        logger.error(f"更新节点时出错: {str(e)}")
        raise HCIGeneratorError(f"更新失败: {str(e)}")


if __name__ == "__main__":
    # 使用示例
    sample_input = {
        "assumption": "用户需要更好的时间管理",
        "context": "工作场景",
        "priority": 3
    }
    
    try:
        # 生成实践清单
        checklist = create_practice_checklist(sample_input)
        print("生成的实践清单:")
        print(json.dumps(checklist, indent=2, ensure_ascii=False))
        
        # 模拟人类反馈
        if checklist["steps"]:
            updated_checklist = update_node_with_feedback(
                checklist,
                step_index=0,
                completed=True,
                feedback="已完成一周的时间记录"
            )
            print("\n更新后的清单:")
            print(json.dumps(updated_checklist, indent=2, ensure_ascii=False))
            
    except HCIGeneratorError as e:
        print(f"错误: {str(e)}")