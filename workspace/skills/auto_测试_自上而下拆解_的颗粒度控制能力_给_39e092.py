"""
Module: auto_测试_自上而下拆解_的颗粒度控制能力_给_39e092
Description: AGI System Skill - Testing Top-Down Decomposition Granularity Control.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import re
from enum import Enum, unique
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field

# 1. 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. 定义常量与枚举

@unique
class SkillNodeType(Enum):
    """
    模拟AGI系统中已注册的SKILL节点类型。
    这些代表了原子能力的边界。
    """
    SKILL_PYTHON_PYGAME = "skill.python.pygame"
    SKILL_PYTHON_BASIC_SYNTAX = "skill.python.syntax"
    SKILL_EVENT_LOOP = "skill.system.event_loop"
    SKILL_UI_RENDER = "skill.ui.render_2d"
    SKILL_PHYSICS_ENGINE = "skill.physics.collision"
    SKILL_ASSET_MGMT = "skill.asset.management"
    SKILL_LOGIC_CONTROL = "skill.logic.control_flow"
    SKILL_UNKNOWN = "skill.unknown" # 用于标记无法映射的抽象描述

@unique
class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    MAPPED = "mapped"     # 已成功映射到SKILL
    ORPHANED = "orphaned" # 悬浮/未能映射

@dataclass
class TaskNode:
    """
    表示拆解后的任务节点。
    """
    id: str
    description: str
    level: int
    children: List['TaskNode'] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    mapped_skill: Optional[SkillNodeType] = None

    def __post_init__(self):
        # 简单的边界检查
        if not self.id or not self.description:
            raise ValueError("Task ID and Description cannot be empty.")

# 3. 辅助函数

def _normalize_description(text: str) -> str:
    """
    辅助函数：清洗和标准化文本描述。
    
    Args:
        text (str): 原始任务描述文本。
        
    Returns:
        str: 清洗后的标准化文本。
    """
    if not isinstance(text, str):
        logger.warning(f"Invalid input type for normalization: {type(text)}")
        return ""
    
    # 去除多余空格和换行，转小写
    cleaned = re.sub(r'\s+', ' ', text).strip().lower()
    return cleaned

def _match_skill_to_description(description: str) -> SkillNodeType:
    """
    核心映射逻辑：将自然语言描述映射到具体的SKILL枚举。
    在真实AGI系统中，这里会调用Embedding相似度搜索或LLM判断。
    这里使用关键词匹配作为模拟。
    
    Args:
        description (str): 任务描述。
        
    Returns:
        SkillNodeType: 映射到的技能节点。
    """
    desc = _normalize_description(description)
    
    if any(kw in desc for kw in ["pygame", "display", "window", "screen"]):
        return SkillNodeType.SKILL_PYTHON_PYGAME
    elif any(kw in desc for kw in ["event loop", "main loop", "while true"]):
        return SkillNodeType.SKILL_EVENT_LOOP
    elif any(kw in desc for kw in ["collision", "physics", "gravity", "jump"]):
        return SkillNodeType.SKILL_PHYSICS_ENGINE
    elif any(kw in desc for kw in ["draw", "render", "image", "sprite"]):
        return SkillNodeType.SKILL_UI_RENDER
    elif any(kw in desc for kw in ["class", "function", "def", "variable"]):
        return SkillNodeType.SKILL_PYTHON_BASIC_SYNTAX
    elif any(kw in desc for kw in ["logic", "if", "condition", "score"]):
        return SkillNodeType.SKILL_LOGIC_CONTROL
    elif any(kw in desc for kw in ["load", "asset", "sound", "image"]):
        return SkillNodeType.SKILL_ASSET_MGMT
    else:
        # 如果无法映射，则视为抽象或未知的悬浮任务
        return SkillNodeType.SKILL_UNKNOWN

# 4. 核心函数

def decompose_goal_recursively(
    goal: str, 
    current_depth: int = 0, 
    max_depth: int = 3
) -> TaskNode:
    """
    核心函数1: 模拟AGI对高层目标的自上而下拆解。
    通过递归模拟思维链，将大任务拆解为子任务。
    
    Args:
        goal (str): 当前层级的目标描述。
        current_depth (int): 当前递归深度。
        max_depth (int): 允许拆解的最大深度（控制颗粒度极限）。
        
    Returns:
        TaskNode: 包含完整拆解树的任务节点。
        
    Raises:
        ValueError: 如果goal为空。
    """
    if not goal:
        raise ValueError("Goal cannot be empty.")
    
    node_id = f"task_{current_depth}_{hash(goal) % 10000}"
    logger.info(f"{'  ' * current_depth}Decomposing: {goal} (Depth: {current_depth})")
    
    # 边界检查：如果超过最大深度，强制停止拆解
    if current_depth >= max_depth:
        logger.warning(f"Max depth {max_depth} reached for goal: {goal}")
        return TaskNode(id=node_id, description=goal, level=current_depth)
    
    # 模拟拆解逻辑 (基于硬编码规则模拟智能拆解)
    sub_tasks: List[str] = []
    
    if "flappy bird" in _normalize_description(goal):
        sub_tasks = [
            "Initialize Pygame window",
            "Load bird and pipe assets",
            "Implement Event Loop",
            "Implement Bird physics (gravity/jump)",
            "Implement Collision detection",
            "Render Score and UI"
        ]
    elif "event loop" in _normalize_description(goal):
        sub_tasks = ["Create while True loop", "Handle QUIT event", "Update game state"]
    elif "physics" in _normalize_description(goal):
        sub_tasks = ["Apply gravity constant", "Update bird Y position", "Check boundary"]
    elif "collision" in _normalize_description(goal):
        sub_tasks = ["Get bird rect", "Get pipe rects", "Check overlap"]
    else:
        # 无法进一步拆解，视为原子任务候选
        pass

    node = TaskNode(id=node_id, description=goal, level=current_depth)
    
    if sub_tasks:
        for sub in sub_tasks:
            child_node = decompose_goal_recursively(sub, current_depth + 1, max_depth)
            node.children.append(child_node)
            
    return node

def validate_granularity_and_map_skills(root_node: TaskNode) -> Dict[str, Any]:
    """
    核心函数2: 验证颗粒度并映射技能。
    遍历任务树，检查叶子节点是否能映射到现有的SKILL。
    
    Args:
        root_node (TaskNode): 拆解后的任务树根节点。
        
    Returns:
        Dict[str, Any]: 包含验证结果的报告。
            - total_tasks: 总任务数
            - mapped_skills: 成功映射的技能列表
            - orphaned_tasks: 未能映射的悬浮任务（即颗粒度控制失败的证据）
            - is_valid: 是否通过验证（无悬浮任务）
    """
    report = {
        "total_tasks": 0,
        "mapped_skills": [],
        "orphaned_tasks": [],
        "skill_distribution": {},
        "is_valid": True
    }
    
    # 使用栈进行DFS遍历
    stack = [root_node]
    
    while stack:
        current = stack.pop()
        report["total_tasks"] += 1
        
        # 只有叶子节点或者没有子节点的节点需要进行SKILL映射检查
        if not current.children:
            skill = _match_skill_to_description(current.description)
            current.mapped_skill = skill
            
            if skill == SkillNodeType.SKILL_UNKNOWN:
                current.status = TaskStatus.ORPHANED
                report["orphaned_tasks"].append({
                    "id": current.id,
                    "desc": current.description
                })
                report["is_valid"] = False
                logger.error(f"Orphaned task found: {current.description}")
            else:
                current.status = TaskStatus.MAPPED
                report["mapped_skills"].append(skill.value)
                
                # 统计分布
                if skill.value not in report["skill_distribution"]:
                    report["skill_distribution"][skill.value] = 0
                report["skill_distribution"][skill.value] += 1
                
                logger.debug(f"Task mapped: {current.id} -> {skill.value}")
        else:
            # 如果有子节点，将子节点加入栈
            stack.extend(current.children)
            
    return report

# 5. 主流程与示例

def run_granularity_test(target_goal: str) -> None:
    """
    执行完整的测试流程：拆解 -> 验证 -> 报告。
    
    Args:
        target_goal (str): 待测试的高层目标。
    """
    print(f"\n{'='*60}")
    print(f"Starting Granularity Control Test for: '{target_goal}'")
    print(f"{'='*60}\n")
    
    try:
        # 步骤 1: 自上而下拆解
        logger.info("Phase 1: Decomposing target...")
        task_tree = decompose_goal_recursively(target_goal, max_depth=3)
        
        # 步骤 2: 验证颗粒度
        logger.info("Phase 2: Validating granularity and mapping skills...")
        validation_report = validate_granularity_and_map_skills(task_tree)
        
        # 步骤 3: 输出结果
        print(f"\n{'-'*40}")
        print("VALIDATION REPORT")
        print(f"{'-'*40}")
        print(f"Total Nodes Generated: {validation_report['total_tasks']}")
        print(f"Validation Passed: {validation_report['is_valid']}")
        
        if validation_report['is_valid']:
            print("\n✅ SUCCESS: All abstract tasks have been decomposed to atomic SKILL level.")
            print("\nSkill Distribution:")
            for skill, count in validation_report['skill_distribution'].items():
                print(f"  - {skill}: {count}")
        else:
            print("\n❌ FAILURE: Detected orphaned tasks that cannot be executed (Too Abstract).")
            print("Orphaned Tasks:")
            for task in validation_report['orphaned_tasks']:
                print(f"  - [ID: {task['id']}] {task['desc']}")
                
    except Exception as e:
        logger.error(f"Critical error during test execution: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # 使用示例：测试一个模糊的高层目标
    ambiguous_goal = "Develop a Flappy Bird game"
    
    # 执行测试
    run_granularity_test(ambiguous_goal)
    
    # 测试一个可能导致失败的例子（模拟无法拆解的情况，虽然上面的逻辑覆盖了Flappy Bird）
    # 这里为了演示，我们可以手动构造一个难以映射的目标，或者修改max_depth
    # run_granularity_test("Make the system feel happy") # 这类目标通常难以映射到具体的Python Skill