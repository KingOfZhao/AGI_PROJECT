"""
模块名称: recursive_task_decomposer
描述: 该模块实现了一个基于启发式规则的递归式问题拆解器。
      它能够将复杂的自然语言意图（如“构建一个电商网站”）拆解为一棵多层次的子任务树。
      拆解过程持续进行，直到叶子节点达到可执行的原子粒度（即匹配预定义的技能库或可编码任务）。
      
主要组件:
    - TaskNode: 用于构建任务树的数据结构。
    - RecursiveDecomposer: 核心拆解逻辑类。
    - SkillRegistry: 模拟的技能注册表，用于判断任务是否可执行。

作者: AGI System
版本: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class TaskNode:
    """
    表示任务树中的一个节点。
    
    属性:
        id: 节点的唯一标识符。
        description: 任务的自然语言描述。
        complexity_score: 估算的任务复杂度 (0.0 到 1.0)。
        children: 子任务列表。
        is_atomic: 是否为不可再分的原子任务。
    """
    id: str
    description: str
    complexity_score: float = 0.5
    children: List['TaskNode'] = field(default_factory=list)
    is_atomic: bool = False

    def __post_init__(self):
        # 验证数据
        if not self.id or not self.description:
            raise ValueError("Task ID and description cannot be empty.")
        if not (0.0 <= self.complexity_score <= 1.0):
            raise ValueError("Complexity score must be between 0.0 and 1.0.")

    def add_child(self, child: 'TaskNode'):
        """添加子任务节点。"""
        self.children.append(child)

    def __repr__(self) -> str:
        return f"<TaskNode id='{self.id}' desc='{self.description[:20]}...' atomic={self.is_atomic}>"

# --- 辅助类: 技能注册表 ---

class SkillRegistry:
    """
    模拟的技能注册表。
    在真实AGI系统中，这里会连接到向量数据库检索已有的Skill。
    """
    
    def __init__(self):
        # 预定义一些原子技能关键词
        self._atomic_skills: Set[str] = {
            "user_authentication", "database_schema_design", "api_endpoint_creation",
            "react_component_render", "payment_gateway_integration", 
            "write_unit_test", "dockerfile_creation", "css_styling"
        }
        logger.info("SkillRegistry initialized with %d atomic skills.", len(self._atomic_skills))

    def check_atomicity(self, task_description: str) -> bool:
        """
        检查任务描述是否匹配现有的原子技能。
        
        参数:
            task_description: 任务的文本描述。
            
        返回:
            bool: 如果匹配则返回True。
        """
        # 简单的关键词匹配模拟语义搜索
        desc_normalized = task_description.lower().replace(" ", "_")
        for skill in self._atomic_skills:
            if skill in desc_normalized:
                return True
        return False

# --- 核心逻辑类: 递归拆解器 ---

class RecursiveDecomposer:
    """
    递归式问题拆解器。
    
    负责将复杂意图拆解为子任务树。使用启发式规则和模拟的LLM调用进行拆解。
    包含防止无限递归和过度碎片化的保护机制。
    """

    def __init__(self, skill_registry: SkillRegistry, max_depth: int = 5):
        """
        初始化拆解器。
        
        参数:
            skill_registry: 用于检查任务原子性的注册表。
            max_depth: 最大递归深度，防止无限循环。
        """
        if max_depth < 1:
            raise ValueError("Max depth must be at least 1.")
            
        self.registry = skill_registry
        self.max_depth = max_depth
        self._node_counter = 0
        logger.info("RecursiveDecomposer initialized with max_depth=%d", max_depth)

    def _estimate_complexity(self, description: str) -> float:
        """
        辅助函数：估算任务描述的复杂度。
        
        逻辑:
            - 基于文本长度和特定关键词（如"系统", "架构" vs "函数", "变量"）。
            - 这是一个简化的启发式示例。
        
        参数:
            description: 任务描述。
            
        返回:
            float: 复杂度评分 (0.0 - 1.0)。
        """
        score = 0.2
        if len(description) > 100:
            score += 0.3
        if any(word in description for word in ["系统", "架构", "平台", "完整", "构建"]):
            score += 0.4
        if any(word in description for word in ["实现", "编写", "函数", "变量"]):
            score -= 0.2
            
        return max(0.0, min(1.0, score))

    def _decompose_logic(self, current_node: TaskNode, depth: int) -> None:
        """
        核心递归函数：执行拆解逻辑。
        
        参数:
            current_node: 当前待处理的节点。
            depth: 当前递归深度。
        """
        # 1. 边界检查：深度限制
        if depth >= self.max_depth:
            logger.warning("Max recursion depth reached at node: %s", current_node.id)
            current_node.is_atomic = True # 强制标记为原子任务以停止拆解
            return

        # 2. 终止条件检查：是否已经在技能库中
        if self.registry.check_atomicity(current_node.description):
            current_node.is_atomic = True
            logger.debug("Node %s matched existing skill.", current_node.id)
            return
            
        # 3. 终止条件检查：复杂度是否足够低
        if current_node.complexity_score < 0.3:
            current_node.is_atomic = True
            logger.debug("Node %s complexity low enough (%.2f), treating as atomic.", 
                         current_node.id, current_node.complexity_score)
            return

        # 4. 执行拆解 (此处模拟LLM的CoT拆解过程)
        logger.info("Decomposing node: %s (Depth: %d)", current_node.id, depth)
        sub_tasks = self._generate_subtasks_heuristic(current_node.description)

        if not sub_tasks:
            current_node.is_atomic = True
            return

        # 5. 递归处理子节点
        for sub_desc in sub_tasks:
            self._node_counter += 1
            child_id = f"{current_node.id}.{self._node_counter}"
            
            # 创建子节点
            child_node = TaskNode(
                id=child_id,
                description=sub_desc,
                complexity_score=self._estimate_complexity(sub_desc),
                is_atomic=False
            )
            current_node.add_child(child_node)
            
            # 递归
            self._decompose_logic(child_node, depth + 1)

    def _generate_subtasks_heuristic(self, description: str) -> List[str]:
        """
        模拟LLM的拆解思维链。
        在生产环境中，这里应调用LLM API (如GPT-4)。
        
        参数:
            description: 父任务描述。
            
        返回:
            List[str]: 子任务描述列表。
        """
        # 模拟针对“电商网站”的固定拆解逻辑
        if "电商" in description and "网站" in description:
            return [
                "搭建基础后端架构",
                "实现用户认证系统 (User Authentication)",
                "设计商品数据库模式 (Database Schema Design)",
                "开发购物车API接口 (API Endpoint Creation)",
                "集成支付网关 (Payment Gateway Integration)",
                "前端页面渲染与CSS样式 (CSS Styling)"
            ]
        elif "基础后端架构" in description:
            return [
                "初始化项目环境",
                "创建Dockerfile (Dockerfile Creation)",
                "编写单元测试框架 (Write Unit Test)"
            ]
        elif "用户认证" in description:
            return ["实现登录API", "实现注册逻辑", "密码加密存储"]
        
        # 默认情况：如果无法拆解，返回空列表，使其成为叶子节点
        logger.debug("No decomposition rules found for: %s", description)
        return []

    def decompose(self, intent: str) -> Optional[TaskNode]:
        """
        主入口函数：将意图转化为任务树。
        
        参数:
            intent: 复杂的用户意图字符串。
            
        返回:
            TaskNode: 任务树的根节点。
        """
        if not intent or not isinstance(intent, str):
            logger.error("Invalid intent provided.")
            return None

        logger.info("Starting decomposition for intent: %s", intent)
        
        self._node_counter = 0
        root_node = TaskNode(
            id="T0",
            description=intent,
            complexity_score=self._estimate_complexity(intent)
        )
        
        try:
            self._decompose_logic(root_node, 0)
        except Exception as e:
            logger.exception("Error during task decomposition: %s", e)
            return None
            
        logger.info("Decomposition completed. Total nodes: %d", self._node_counter + 1)
        return root_node

# --- 可视化辅助函数 ---

def print_tree(node: TaskNode, indent: str = ""):
    """
    辅助函数：打印任务树结构。
    """
    status = "[ATOMIC]" if node.is_atomic else "[COMPLEX]"
    print(f"{indent}|- {node.id}: {node.description} {status}")
    for child in node.children:
        print_tree(child, indent + "   ")

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 初始化依赖
    registry = SkillRegistry()
    decomposer = RecursiveDecomposer(skill_registry=registry, max_depth=4)
    
    # 2. 定义复杂意图
    complex_intent = "构建一个功能完善的电商网站"
    
    # 3. 执行拆解
    task_tree = decomposer.decompose(complex_intent)
    
    # 4. 展示结果
    if task_tree:
        print("\n" + "="*30)
        print(f"Generated Task Tree for: '{complex_intent}'")
        print("="*30)
        print_tree(task_tree)