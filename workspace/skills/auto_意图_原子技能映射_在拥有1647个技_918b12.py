"""
AGI 技能编排模块：意图-原子技能动态路由映射

本模块实现了一个针对大规模技能库（如1647个节点）的动态路由算法。
它负责将高层用户意图解析为有向无环图（DAG）形式的技能调用链。

核心功能：
1. 对用户意图进行向量化编码。
2. 在大规模技能库中进行语义匹配，识别潜在的原子技能。
3. 基于技能的元数据（颗粒度、依赖关系）自动判断是执行单技能调用还是多技能编排。
4. 处理技能间的依赖解析，确保执行顺序的逻辑正确性。

版本: 1.0.0
作者: Senior Python Engineer
"""

import logging
import heapq
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构和枚举 ---

class SkillGranularity(Enum):
    """技能颗粒度枚举"""
    ATOMIC = 10       # 原子操作，不可分割，如OCR
    COMPOSITE = 50    # 复合操作，包含多个步骤
    ORCHESTRATOR = 100 # 编排器，专门用于调度其他技能

class SkillCategory(Enum):
    """技能领域分类"""
    PERCEPTION = "perception"
    ANALYSIS = "analysis"
    ACTION = "action"
    GENERATION = "generation"

@dataclass
class SkillNode:
    """
    技能节点定义
    
    Attributes:
        id (str): 唯一标识符，如 'skill_022'
        name (str): 人类可读名称
        description (str): 功能描述，用于语义匹配
        granularity (SkillGranularity): 技能颗粒度
        dependencies (Set[str]): 依赖的前置技能ID集合
        input_type (str): 期望的输入数据格式
        output_type (str): 输出的数据格式
    """
    id: str
    name: str
    description: str
    granularity: SkillGranularity
    dependencies: Set[str] = field(default_factory=set)
    category: SkillCategory = SkillCategory.ACTION
    input_type: str = "raw"
    output_type: str = "raw"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, SkillNode):
            return self.id == other.id
        return False

@dataclass
class IntentContext:
    """
    用户意图上下文
    
    Attributes:
        query (str): 用户的原始查询文本
        data_types (List[str]): 当前上下文中涉及的数据类型（如 'image', 'csv'）
        complexity_score (float): 意图复杂度评分 (0.0 - 1.0)
    """
    query: str
    data_types: List[str] = field(default_factory=list)
    complexity_score: float = 0.0

@dataclass
class ExecutionPlan:
    """
    执行计划输出
    """
    is_single_skill: bool
    skill_chain: List[str]  # 拓扑排序后的技能ID列表
    reasoning: str          # 决策理由

# --- 异常定义 ---

class SkillOrchestrationError(Exception):
    """技能编排过程中的基础异常"""
    pass

class SkillNotFoundError(SkillOrchestrationError):
    """未找到匹配技能"""
    pass

class CyclicDependencyError(SkillOrchestrationError):
    """检测到循环依赖"""
    pass

# --- 核心类：动态路由器 ---

class DynamicSkillRouter:
    """
    动态技能路由器。
    负责管理大规模技能节点，并根据意图生成最优执行路径。
    """

    def __init__(self, skill_repository: Dict[str, SkillNode]):
        """
        初始化路由器
        
        Args:
            skill_repository (Dict[str, SkillNode]): 技能库字典
        """
        if not skill_repository:
            raise ValueError("Skill repository cannot be empty")
        
        self.skills = skill_repository
        self._build_dependency_graph()
        logger.info(f"Router initialized with {len(self.skills)} skills.")

    def _build_dependency_graph(self):
        """构建内部依赖图索引以加速查找"""
        self.dependents_map: Dict[str, Set[str]] = {k: set() for k in self.skills}
        for skill_id, node in self.skills.items():
            for dep_id in node.dependencies:
                if dep_id in self.dependents_map:
                    self.dependents_map[dep_id].add(skill_id)
                else:
                    logger.warning(f"Skill {skill_id} depends on non-existent skill {dep_id}")

    def resolve_intent_to_plan(self, context: IntentContext) -> ExecutionPlan:
        """
        核心方法：将意图上下文解析为执行计划。
        
        步骤：
        1. 语义匹配：找到候选技能。
        2. 颗粒度评估：判断是需要单一技能还是工作流。
        3. 依赖解析：如果需要工作流，构建DAG并拓扑排序。
        
        Args:
            context (IntentContext): 用户意图上下文
            
        Returns:
            ExecutionPlan: 包含执行路径的计划
            
        Raises:
            SkillNotFoundError: 如果无法找到处理该意图的技能
        """
        logger.info(f"Resolving intent: {context.query}")
        
        # 1. 模拟语义匹配 (在实际AGI中这里会是Vector Search)
        candidate_skills = self._semantic_search(context)
        
        if not candidate_skills:
            raise SkillNotFoundError(f"No skills found for query: {context.query}")

        # 2. 选择最佳入口节点
        primary_skill = self._select_primary_skill(candidate_skills, context)
        
        # 3. 决策：单一调用 vs 编排
        # 逻辑：如果意图复杂度高 且 技能存在依赖，或者匹配到的是Orchestrator类型，则进行编排
        needs_orchestration = (
            context.complexity_score > 0.6 or 
            primary_skill.granularity == SkillGranularity.ORCHESTRATOR or
            (primary_skill.granularity == SkillGranularity.COMPOSITE and primary_skill.dependencies)
        )

        if not needs_orchestration and primary_skill.granularity == SkillGranularity.ATOMIC:
            logger.info(f"Mapped to single atomic skill: {primary_skill.id}")
            return ExecutionPlan(
                is_single_skill=True,
                skill_chain=[primary_skill.id],
                reasoning="Intent matches a single atomic capability."
            )
        
        # 4. 构建编排链 (DAG)
        logger.info("Initiating orchestration mode...")
        required_skills = self._resolve_dependencies_recursive(primary_skill.id, set())
        
        # 5. 拓扑排序
        sorted_chain = self._topological_sort(required_skills)
        
        return ExecutionPlan(
            is_single_skill=False,
            skill_chain=sorted_chain,
            reasoning=f"Complex intent resolved into {len(sorted_skills)} steps workflow."
        )

    def _semantic_search(self, context: IntentContext) -> List[SkillNode]:
        """
        辅助函数：模拟在大规模技能库中的语义搜索。
        实际生产中会使用 Embedding + Vector DB。
        这里使用简单的关键词匹配进行模拟。
        """
        candidates = []
        query_lower = context.query.lower()
        
        # 简单模拟匹配逻辑
        for skill in self.skills.values():
            score = 0
            if any(word in skill.description.lower() for word in query_lower.split()):
                score = 0.8
            if skill.category.value in query_lower:
                score = 0.9
            
            # 数据类型匹配加成
            if any(dtype in skill.input_type for dtype in context.data_types):
                score += 0.1
            
            if score > 0:
                candidates.append(skill)
                
        return candidates

    def _select_primary_skill(self, candidates: List[SkillNode], context: IntentContext) -> SkillNode:
        """
        从候选技能中选择最合适的“入口”技能。
        """
        # 优先选择颗粒度高的，或者匹配度高的（这里简化为随机选一个模拟）
        # 实际应基于 Rank Score
        if not candidates:
            raise SkillNotFoundError("No candidates to select from.")
            
        # 优先选择能够处理当前数据类型的技能
        for skill in candidates:
            if skill.input_type in context.data_types:
                return skill
        
        return candidates[0]

    def _resolve_dependencies_recursive(self, skill_id: str, visited: Set[str]) -> Set[str]:
        """
        递归解析所有依赖项。
        
        Args:
            skill_id (str): 当前技能ID
            visited (Set[str]): 已访问节点，用于防止死循环
            
        Returns:
            Set[str]: 所有需要的技能ID集合
        """
        if skill_id in visited:
            return visited
            
        visited.add(skill_id)
        current_skill = self.skills.get(skill_id)
        
        if not current_skill:
            logger.warning(f"Dependency {skill_id} not found in repository.")
            return visited
            
        for dep_id in current_skill.dependencies:
            self._resolve_dependencies_recursive(dep_id, visited)
            
        return visited

    def _topological_sort(self, skill_ids: Set[str]) -> List[str]:
        """
        对技能节点进行拓扑排序，确定执行顺序。
        使用 Kahn's 算法 (入度表)。
        """
        in_degree = {uid: 0 for uid in skill_ids}
        queue = []
        result = []
        
        # 仅构建相关子图的邻接关系
        adj = {uid: [] for uid in skill_ids}
        
        for uid in skill_ids:
            node = self.skills[uid]
            for dep in node.dependencies:
                if dep in skill_ids:
                    adj[dep].append(uid)
                    in_degree[uid] += 1
        
        # 将入度为0的节点加入队列
        for uid, degree in in_degree.items():
            if degree == 0:
                queue.append(uid)
                
        while queue:
            u = queue.pop(0)
            result.append(u)
            
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        if len(result) != len(skill_ids):
            logger.error("Cyclic dependency detected in skill graph!")
            raise CyclicDependencyError("Skills contain cyclic dependencies.")
            
        return result

# --- 辅助函数：模拟技能库构建 ---

def create_mock_skill_repository(count: int = 1647) -> Dict[str, SkillNode]:
    """
    辅助函数：生成模拟的大规模技能库。
    实际上这里只手动构建几个关键的，其余填充空数据以模拟规模。
    """
    repo = {}
    
    # 关键技能定义
    repo['skill_022_image_recognition'] = SkillNode(
        id='skill_022_image_recognition',
        name='Image Recognizer',
        description='Identify objects and text in images',
        granularity=SkillGranularity.ATOMIC,
        category=SkillCategory.PERCEPTION,
        input_type='image',
        output_type='labeled_data'
    )
    
    repo['skill_108_data_analysis'] = SkillNode(
        id='skill_108_data_analysis',
        name='Data Analyzer',
        description='Perform statistical analysis on structured data',
        granularity=SkillGranularity.ATOMIC,
        category=SkillCategory.ANALYSIS,
        input_type='csv', # 假设识别后的数据转为CSV结构
        output_type='analytics_report',
        dependencies=set() 
    )
    
    repo['skill_209_report_generation'] = SkillNode(
        id='skill_209_report_generation',
        name='Report Generator',
        description='Generate natural language report from analysis',
        granularity=SkillGranularity.ATOMIC,
        category=SkillCategory.GENERATION,
        input_type='analytics_report',
        output_type='text',
        dependencies={'skill_108_data_analysis'} # 依赖于分析完成
    )
    
    # 模拟高层复合技能
    repo['skill_comprehensive_chart_analysis'] = SkillNode(
        id='skill_comprehensive_chart_analysis',
        name='Chart Analysis Orchestrator',
        description='Analyze charts deeply',
        granularity=SkillGranularity.ORCHESTRATOR,
        category=SkillCategory.ANALYSIS,
        input_type='image',
        dependencies={'skill_022_image_recognition', 'skill_108_data_analysis', 'skill_209_report_generation'}
    )
    
    # 填充剩余的模拟技能以达到数量级（仅为了演示构造）
    # 实际代码中不会这样做，这里为了满足 "拥有1647个技能节点" 的背景描述
    for i in range(210, count):
        s_id = f"skill_{i}_generic"
        repo[s_id] = SkillNode(
            id=s_id, 
            name=f"Generic Skill {i}", 
            description="N/A", 
            granularity=SkillGranularity.ATOMIC
        )
        
    return repo

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 初始化环境
    skills_db = create_mock_skill_repository(1647)
    router = DynamicSkillRouter(skills_db)
    
    print("-" * 50)
    
    # 场景 A: 简单意图，只需单一原子技能
    intent_simple = IntentContext(
        query="这张图里有什么？",
        data_types=["image"],
        complexity_score=0.2
    )
    
    try:
        plan_simple = router.resolve_intent_to_plan(intent_simple)
        print(f"Plan A (Simple): {plan_simple.skill_chain}")
        print(f"Reasoning: {plan_simple.reasoning}")
    except SkillOrchestrationError as e:
        print(f"Error: {e}")

    print("-" * 50)

    # 场景 B: 复杂意图，需要编排 (分析图表 -> 生成报告)
    # 假设我们的语义搜索能匹配到 'skill_comprehensive_chart_analysis'
    intent_complex = IntentContext(
        query="请深入分析这张图表并给出结论报告", # 关键词匹配到 comprehensive/analysis
        data_types=["image"],
        complexity_score=0.8
    )
    
    try:
        plan_complex = router.resolve_intent_to_plan(intent_complex)
        print(f"Plan B (Complex): {plan_complex.skill_chain}")
        print(f"Is Single Skill: {plan_complex.is_single_skill}")
        print(f"Reasoning: {plan_complex.reasoning}")
    except SkillOrchestrationError as e:
        print(f"Error: {e}")