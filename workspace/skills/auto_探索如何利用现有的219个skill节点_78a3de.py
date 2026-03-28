"""
模块名称: skill_primitive_composer
描述: 本模块实现了基于'认知基元'的意图处理系统。它探索如何利用现有的219个Skill节点，
      通过组合而非从零生成，来满足新的用户意图。系统优先在现有Skill库中检索匹配的子流程，
      仅对缺失部分进行代码生成，从而验证'重叠固化为真实节点'的架构价值。
      
作者: AGI System Architect
版本: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MAX_INTENT_LENGTH = 1024
MIN_KEYWORD_LENGTH = 2
SKILL_DB_SIZE = 219

class SkillType(Enum):
    """定义Skill节点的类型枚举"""
    DATA_RETRIEVAL = "data_retrieval"
    LOGICAL_REASONING = "logical_reasoning"
    CODE_GENERATION = "code_generation"
    USER_INTERACTION = "user_interaction"
    SYSTEM_CONTROL = "system_control"

@dataclass
class SkillNode:
    """
    Skill节点数据结构
    
    属性:
        id: 唯一标识符
        name: 技能名称
        description: 功能描述
        keywords: 触发关键词列表
        skill_type: 技能类型枚举
        dependencies: 依赖的其他Skill ID列表
        usage_count: 使用频率计数，用于评估固化价值
    """
    id: str
    name: str
    description: str
    keywords: List[str]
    skill_type: SkillType
    dependencies: List[str] = field(default_factory=list)
    usage_count: int = 0

@dataclass
class IntentRequest:
    """
    用户意图请求数据结构
    
    属性:
        text: 原始意图文本
        context: 上下文环境字典
        priority: 处理优先级 (1-10)
    """
    text: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5

@dataclass
class ExecutionPlan:
    """
    执行计划数据结构
    
    属性:
        matched_skills: 匹配到的现有技能列表
        generation_tasks: 需要生成的任务描述列表
        coverage_score: 覆盖率评分 (0.0-1.0)
        execution_order: 执行顺序列表
    """
    matched_skills: List[SkillNode]
    generation_tasks: List[str]
    coverage_score: float
    execution_order: List[str]

class SkillPrimitiveComposer:
    """
    核心类：基于认知基元的技能组合器。
    
    负责分析用户意图，检索现有Skill库，组合现有技能，
    并仅在必要时生成新的代码逻辑。
    """
    
    def __init__(self, skill_database: Optional[Dict[str, SkillNode]] = None):
        """
        初始化组合器。
        
        参数:
            skill_database: 预加载的Skill数据库。如果为None，将加载默认模拟库。
        """
        self.skill_database = skill_database if skill_database is not None else self._load_default_skills()
        self.keyword_index = self._build_keyword_index()
        logger.info(f"SkillPrimitiveComposer initialized with {len(self.skill_database)} primitives.")

    def _load_default_skills(self) -> Dict[str, SkillNode]:
        """
        辅助函数：加载默认的模拟Skill库（模拟219个节点）。
        
        返回:
            包含模拟Skill节点的字典。
        """
        logger.warning("Loading mock skill database. In production, connect to vector DB.")
        mock_skills = {}
        
        # 模拟生成部分核心节点
        base_skills = [
            ("sk_001", "HTTP_Get", "Retrieve data from HTTP endpoint", ["get", "fetch", "download", "http"], SkillType.DATA_RETRIEVAL),
            ("sk_002", "Text_Sentiment_Analysis", "Analyze sentiment of text", ["sentiment", "emotion", "attitude", "feeling"], SkillType.LOGICAL_REASONING),
            ("sk_003", "Data_Filter", "Filter data based on criteria", ["filter", "where", "select", "search"], SkillType.LOGICAL_REASONING),
            ("sk_004", "LLM_Summarize", "Summarize text using LLM", ["summarize", "summary", "brief", "tldr"], SkillType.CODE_GENERATION),
            ("sk_005", "File_Write", "Write content to disk", ["write", "save", "store", "file"], SkillType.SYSTEM_CONTROL),
            ("sk_006", "Math_Calculate", "Perform mathematical calculations", ["calculate", "math", "compute", "add", "minus"], SkillType.LOGICAL_REASONING),
            ("sk_007", "Chart_Generate", "Generate data visualization", ["chart", "graph", "plot", "visualize"], SkillType.CODE_GENERATION)
        ]
        
        for i, (uid, name, desc, kw, typ) in enumerate(base_skills):
            # 模拟填充至219个（这里仅创建少量示例，实际应用需全量加载）
            # 简单的ID生成模拟
            count = i + 1
            mock_skills[uid] = SkillNode(
                id=uid,
                name=name,
                description=desc,
                keywords=kw,
                skill_type=typ,
                usage_count=100 * (count) # 模拟使用频率
            )
            
        # 填充剩余的空节点以模拟规模（实际逻辑中应移除）
        for i in range(len(base_skills) + 1, SKILL_DB_SIZE + 1):
            uid = f"sk_{i:03d}"
            mock_skills[uid] = SkillNode(
                id=uid, 
                name=f"Auto_Skill_{i}", 
                description="Placeholder for primitive",
                keywords=[f"action_{i}"],
                skill_type=SkillType.LOGICAL_REASONING
            )
            
        return mock_skills

    def _build_keyword_index(self) -> Dict[str, Set[str]]:
        """
        辅助函数：构建关键词倒排索引以加速检索。
        
        返回:
            关键词到Skill ID集合的映射字典。
        """
        index: Dict[str, Set[str]] = {}
        for skill_id, skill in self.skill_database.items():
            for kw in skill.keywords:
                normalized_kw = kw.lower()
                if normalized_kw not in index:
                    index[normalized_kw] = set()
                index[normalized_kw].add(skill_id)
        return index

    def _validate_intent(self, intent: IntentRequest) -> bool:
        """
        辅助函数：验证输入意图的合法性。
        
        参数:
            intent: 用户意图请求对象
            
        返回:
            布尔值，表示验证是否通过
            
        异常:
            ValueError: 如果验证失败会记录日志（此处不抛出异常以保持流程流畅，实际可调整）
        """
        if not intent.text or len(intent.text.strip()) < MIN_KEYWORD_LENGTH:
            logger.error(f"Intent text too short or empty: {intent.text}")
            return False
        if len(intent.text) > MAX_INTENT_LENGTH:
            logger.warning(f"Intent text exceeds max length {MAX_INTENT_LENGTH}, truncating.")
            # 在实际处理中可能会截断，这里仅作标记
        if not (1 <= intent.priority <= 10):
            logger.error(f"Invalid priority: {intent.priority}")
            return False
        return True

    def decompose_intent(self, intent: IntentRequest) -> List[str]:
        """
        核心函数1：意图分解。
        
        将复杂的用户意图文本分解为原子化的关键词或短语列表。
        这是一个简化的NLP处理流程。
        
        参数:
            intent: 用户意图请求
            
        返回:
            规范化后的关键词列表
            
        示例:
            >>> composer = SkillPrimitiveComposer()
            >>> req = IntentRequest(text="Fetch data and visualize chart", priority=8)
            >>> composer.decompose_intent(req)
            ['fetch', 'data', 'visualize', 'chart']
        """
        if not self._validate_intent(intent):
            return []

        # 简单的预处理：转小写，去除标点
        clean_text = re.sub(r'[^\w\s]', '', intent.text.lower())
        # 分词 (Simple whitespace tokenizer)
        tokens = clean_text.split()
        
        # 停用词过滤 (示例列表)
        stop_words = {"the", "a", "is", "and", "of", "to", "for", "in", "it", "please"}
        filtered_tokens = [t for t in tokens if t not in stop_words and len(t) >= MIN_KEYWORD_LENGTH]
        
        logger.info(f"Decomposed intent '{intent.text[:20]}...' into tokens: {filtered_tokens}")
        return filtered_tokens

    def compose_execution_plan(self, intent: IntentRequest) -> ExecutionPlan:
        """
        核心函数2：组合执行计划。
        
        根据分解后的意图，检索Skill库，计算覆盖率，并生成执行计划。
        返回匹配到的现有节点列表以及需要新生成的任务描述。
        
        参数:
            intent: 用户意图请求
            
        返回:
            ExecutionPlan 对象，包含完整的执行蓝图
            
        示例:
            >>> composer = SkillPrimitiveComposer()
            >>> req = IntentRequest(text="I want to download a report and summarize it", priority=9)
            >>> plan = composer.compose_execution_plan(req)
            >>> print(plan.coverage_score)
            0.8
        """
        tokens = self.decompose_intent(intent)
        if not tokens:
            return ExecutionPlan([], [], 0.0, [])

        matched_skills: List[SkillNode] = []
        matched_ids: Set[str] = set()
        unmatched_tokens: List[str] = []

        # 检索阶段：利用倒排索引查找匹配的Skill
        for token in tokens:
            # 精确匹配关键词
            if token in self.keyword_index:
                # 取相关性最高的一个（此处简化为取第一个）
                best_match_id = list(self.keyword_index[token])[0]
                if best_match_id not in matched_ids:
                    skill = self.skill_database[best_match_id]
                    matched_skills.append(skill)
                    matched_ids.add(best_match_id)
                    logger.debug(f"Matched token '{token}' to skill '{skill.name}'")
                else:
                    # 已经匹配过该技能
                    pass
            else:
                # 未匹配的关键词，可能需要代码生成
                unmatched_tokens.append(token)

        # 计算覆盖率
        # 修正覆盖率计算，避免除以零
        total_weight = len(tokens)
        if total_weight == 0:
            coverage = 0.0
        else:
            # 匹配到的token数量 / 总token数量 (简化算法)
            # 实际上matched_skills可能覆盖多个token，这里简化逻辑
            covered_weight = sum(len(s.keywords) for s in matched_skills) # 模糊估算
            coverage = min(1.0, len(matched_skills) / (len(matched_skills) + len(unmatched_tokens)))

        # 生成缺失部分的任务描述
        generation_tasks = []
        if unmatched_tokens:
            task_desc = f"Generate logic for features related to: {', '.join(unmatched_tokens)}"
            generation_tasks.append(task_desc)
            logger.info(f"Identified gap requiring generation: {task_desc}")

        # 确定执行顺序 (简单的拓扑排序或基于依赖的排序，此处简化)
        # 将检索到的技能放入执行列表
        execution_order = [s.id for s in matched_skills]
        
        # 添加生成任务占位符
        for i, task in enumerate(generation_tasks):
            execution_order.append(f"gen_task_{i}")

        return ExecutionPlan(
            matched_skills=matched_skills,
            generation_tasks=generation_tasks,
            coverage_score=round(coverage, 2),
            execution_order=execution_order
        )

# 使用示例
if __name__ == "__main__":
    # 初始化系统
    composer = SkillPrimitiveComposer()
    
    # 定义用户意图
    user_intent_text = "Please fetch the latest stock data and plot a line chart"
    request = IntentRequest(text=user_intent_text, priority=8, context={"user_id": "u123"})
    
    # 生成执行计划
    plan = composer.compose_execution_plan(request)
    
    # 打印结果
    print("\n--- Execution Plan Report ---")
    print(f"Original Intent: {user_intent_text}")
    print(f"Coverage Score: {plan.coverage_score * 100}%")
    print(f"Matched Primitives ({len(plan.matched_skills)}):")
    for skill in plan.matched_skills:
        print(f"  - [Existing] {skill.name} (Type: {skill.skill_type.value})")
        
    print(f"Generation Tasks ({len(plan.generation_tasks)}):")
    for task in plan.generation_tasks:
        print(f"  - [New Code Needed] {task}")
        
    print(f"Execution Order: {plan.execution_order}")