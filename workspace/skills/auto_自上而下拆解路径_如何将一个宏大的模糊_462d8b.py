"""
高级AGI规划模块：自上而下拆解路径

本模块实现了一个递归式的意图识别与任务分解引擎，旨在解决宏大模糊目标（如'解决气候变化'）
与具体技能节点之间的语义粒度不匹配问题。通过多轮迭代的分层分解，将抽象目标转化为
可直接映射到现有Skill ID的可执行实践清单。

核心机制：
1. 语义对齐：将抽象概念映射到中间层策略
2. 递归分解：通过广度优先搜索(BFS)或深度优先搜索(DFS)策略细化任务
3. 叶子节点匹配：当子任务粒度足够细时，映射到预定义的588个技能节点

Created by: Senior Python Engineer for AGI System
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlanningError(Exception):
    """自定义规划异常基类"""
    pass

class MaxRecursionDepthError(PlanningError):
    """超过最大递归深度异常"""
    pass

class SkillMappingNotFoundError(PlanningError):
    """无法找到技能映射异常"""
    pass

class DecompositionStrategy(Enum):
    """分解策略枚举"""
    BREADTH_FIRST = "breadth_first"  # 广度优先，适用于全面覆盖
    DEPTH_FIRST = "depth_first"      # 深度优先，适用于快速验证路径

@dataclass
class SkillNode:
    """技能节点数据结构"""
    skill_id: str
    name: str
    description: str
    category: str
    required_capabilities: List[str] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.skill_id)

@dataclass
class TaskNode:
    """任务节点数据结构，用于构建分解树"""
    task_id: str
    description: str
    depth: int
    children: List['TaskNode'] = field(default_factory=list)
    mapped_skill: Optional[SkillNode] = None
    is_completed: bool = False
    
    def add_child(self, child: 'TaskNode') -> None:
        """添加子任务节点"""
        self.children.append(child)
        
    def get_all_skills(self) -> List[SkillNode]:
        """递归获取该节点及其所有子节点映射的技能"""
        skills = []
        if self.mapped_skill:
            skills.append(self.mapped_skill)
        for child in self.children:
            skills.extend(child.get_all_skills())
        return skills

class AutoTopDownDecomposer:
    """
    自上而下任务分解器
    
    自动将宏大的模糊目标分解为可执行的技能节点路径。
    """
    
    def __init__(
        self, 
        skill_database: Dict[str, SkillNode],
        max_depth: int = 5,
        min_granularity_score: float = 0.8,
        strategy: DecompositionStrategy = DecompositionStrategy.BREADTH_FIRST
    ):
        """
        初始化分解器
        
        Args:
            skill_database: 现有技能数据库 {skill_id: SkillNode}
            max_depth: 最大递归分解深度，防止无限循环
            min_granularity_score: 识别为可执行节点的最小粒度得分 (0.0-1.0)
            strategy: 分解策略
        """
        if not skill_database:
            raise ValueError("Skill database cannot be empty")
        if max_depth < 1:
            raise ValueError("Max depth must be at least 1")
        if not 0.0 <= min_granularity_score <= 1.0:
            raise ValueError("Granularity score must be between 0.0 and 1.0")
            
        self.skill_db = skill_database
        self.max_depth = max_depth
        self.min_granularity = min_granularity_score
        self.strategy = strategy
        self._task_counter = 0
        self._visited_tasks: Set[str] = set()  # 防止循环分解
        
        # 建立反向索引以提高查找效率
        self._keyword_index = self._build_keyword_index()
        
        logger.info(f"Decomposer initialized with {len(skill_database)} skills, strategy: {strategy.value}")

    def _build_keyword_index(self) -> Dict[str, List[SkillNode]]:
        """构建关键词到技能节点的反向索引"""
        index = {}
        for skill in self.skill_db.values():
            # 简单的关键词提取，实际应用中应使用NLP技术
            keywords = set(skill.name.split() + skill.description.split() + skill.required_capabilities)
            for keyword in keywords:
                keyword = keyword.lower().strip()
                if len(keyword) > 2:  # 过滤掉太短的词
                    if keyword not in index:
                        index[keyword] = []
                    index[keyword].append(skill)
        return index

    def decompose_macro_goal(self, macro_goal: str) -> TaskNode:
        """
        分解宏大的模糊目标
        
        Args:
            macro_goal: 宏大目标描述，如 "解决气候变化"
            
        Returns:
            TaskNode: 任务树的根节点
            
        Raises:
            PlanningError: 如果分解失败
        """
        if not macro_goal or not isinstance(macro_goal, str):
            raise ValueError("Macro goal must be a non-empty string")
            
        logger.info(f"Starting decomposition for macro goal: '{macro_goal}'")
        self._task_counter = 0
        self._visited_tasks = set()
        
        try:
            root_task = self._create_task_node(macro_goal, 0)
            self._recursive_decompose(root_task)
            
            # 验证分解结果
            total_skills = len(root_task.get_all_skills())
            if total_skills == 0:
                logger.warning("Decomposition completed but no skills were mapped")
            else:
                logger.info(f"Decomposition completed. Mapped {total_skills} unique skills.")
                
            return root_task
            
        except RecursionError:
            logger.error("Recursion depth exceeded during decomposition")
            raise MaxRecursionDepthError("Maximum recursion depth exceeded during task decomposition")
        except Exception as e:
            logger.error(f"Unexpected error during decomposition: {str(e)}")
            raise PlanningError(f"Failed to decompose macro goal: {str(e)}")

    def _create_task_node(self, description: str, depth: int) -> TaskNode:
        """创建新的任务节点"""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        return TaskNode(
            task_id=task_id,
            description=description,
            depth=depth
        )

    def _recursive_decompose(self, current_task: TaskNode) -> None:
        """
        递归分解任务的核心函数
        
        Args:
            current_task: 当前需要分解的任务节点
        """
        # 检查边界条件
        if current_task.depth > self.max_depth:
            logger.warning(f"Max depth {self.max_depth} reached for task: {current_task.description}")
            return
            
        if current_task.task_id in self._visited_tasks:
            logger.debug(f"Task already visited, skipping: {current_task.description}")
            return
            
        self._visited_tasks.add(current_task.task_id)
        
        # 1. 尝试直接映射到现有技能
        mapped_skill = self._try_map_to_skill(current_task.description)
        if mapped_skill:
            current_task.mapped_skill = mapped_skill
            logger.debug(f"Task '{current_task.description}' directly mapped to skill: {mapped_skill.skill_id}")
            return
            
        # 2. 如果无法直接映射，进行语义分解
        granularity = self._calculate_granularity(current_task.description)
        if granularity >= self.min_granularity:
            # 如果粒度足够细但仍未映射，尝试模糊匹配
            fuzzy_skill = self._fuzzy_match_skill(current_task.description)
            if fuzzy_skill:
                current_task.mapped_skill = fuzzy_skill
                logger.debug(f"Task '{current_task.description}' fuzzy matched to skill: {fuzzy_skill.skill_id}")
                return
            else:
                logger.warning(f"Task '{current_task.description}' has high granularity but no skill match")
                return
        
        # 3. 执行分解 (模拟LLM的分解过程)
        sub_tasks = self._generate_subtasks(current_task.description)
        
        if not sub_tasks:
            logger.warning(f"No subtasks generated for: {current_task.description}")
            return
            
        logger.debug(f"Decomposing '{current_task.description}' into {len(sub_tasks)} subtasks at depth {current_task.depth}")
        
        # 根据策略处理子任务
        if self.strategy == DecompositionStrategy.BREADTH_FIRST:
            # 广度优先：先创建所有子节点，再递归处理
            for sub_desc in sub_tasks:
                child_node = self._create_task_node(sub_desc, current_task.depth + 1)
                current_task.add_child(child_node)
            
            for child in current_task.children:
                self._recursive_decompose(child)
        else:
            # 深度优先：创建一个子节点就立即递归处理
            for sub_desc in sub_tasks:
                child_node = self._create_task_node(sub_desc, current_task.depth + 1)
                current_task.add_child(child_node)
                self._recursive_decompose(child_node)

    def _try_map_to_skill(self, task_description: str) -> Optional[SkillNode]:
        """
        尝试将任务描述精确映射到现有技能
        
        Args:
            task_description: 任务描述
            
        Returns:
            匹配的SkillNode或None
        """
        # 简化的映射逻辑，实际应用中应使用向量相似度搜索
        task_lower = task_description.lower().strip()
        
        # 1. 精确名称匹配
        for skill in self.skill_db.values():
            if skill.name.lower() == task_lower:
                return skill
                
        # 2. 高频关键词匹配
        task_keywords = set(task_lower.split())
        best_match = None
        best_score = 0
        
        for keyword, skills in self._keyword_index.items():
            if keyword in task_keywords:
                for skill in skills:
                    # 简单的评分机制：匹配的关键词数量
                    skill_keywords = set(skill.name.lower().split() + skill.description.lower().split())
                    common_keywords = task_keywords.intersection(skill_keywords)
                    score = len(common_keywords) / max(len(task_keywords), 1)
                    
                    if score > best_score and score >= 0.7:  # 阈值
                        best_score = score
                        best_match = skill
                        
        return best_match

    def _fuzzy_match_skill(self, task_description: str) -> Optional[SkillNode]:
        """
        模糊匹配技能（当精确匹配失败时使用）
        
        Args:
            task_description: 任务描述
            
        Returns:
            模糊匹配的SkillNode或None
        """
        # 这里使用简单的相似度算法，实际应使用词向量或BERT等模型
        task_words = set(task_description.lower().split())
        best_match = None
        best_similarity = 0.0
        
        for skill in self.skill_db.values():
            skill_words = set(skill.name.lower().split() + skill.description.lower().split())
            
            # Jaccard 相似度
            intersection = len(task_words.intersection(skill_words))
            union = len(task_words.union(skill_words))
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity > best_similarity and similarity >= 0.5:  # 较低阈值
                best_similarity = similarity
                best_match = skill
                
        return best_match

    def _calculate_granularity(self, description: str) -> float:
        """
        计算任务描述的粒度得分
        
        Args:
            description: 任务描述
            
        Returns:
            float: 粒度得分 (0.0-1.0)
        """
        # 简化的启发式规则，实际应使用更复杂的NLP分析
        words = description.split()
        
        # 1. 长度因素：过短或过长都可能是粒度不适中
        length_score = 1.0 - abs(len(words) - 8) / 10.0  # 假设8个词是最佳长度
        
        # 2. 具体动词检测
        action_verbs = {'分析', '设计', '实现', '测试', '部署', '监控', '优化', '编写', '构建', '修复'}
        verb_score = 0.2 if any(verb in description for verb in action_verbs) else 0.0
        
        # 3. 抽象概念检测
        abstract_terms = {'系统', '架构', '策略', '方法', '技术', '问题', '方案'}
        abstract_penalty = 0.1 * sum(1 for term in abstract_terms if term in description)
        
        # 综合得分
        score = length_score + verb_score - abstract_penalty
        return max(0.0, min(1.0, score))

    def _generate_subtasks(self, task_description: str) -> List[str]:
        """
        生成子任务列表（模拟LLM的分解能力）
        
        注意：这是一个简化实现，实际AGI系统应调用大语言模型API
        
        Args:
            task_description: 父任务描述
            
        Returns:
            子任务描述列表
        """
        # 这里使用预定义的分解规则，实际应调用LLM API
        if "气候变化" in task_description:
            return [
                "分析温室气体排放来源",
                "设计可再生能源替代方案",
                "实施碳捕获技术",
                "建立全球气候监测系统",
                "制定国际减排协议"
            ]
        elif "可再生能源" in task_description:
            return [
                "评估太阳能发电潜力",
                "优化风力发电机组布局",
                "建设智能电网系统",
                "开发储能技术解决方案"
            ]
        elif "监测系统" in task_description:
            return [
                "部署物联网传感器网络",
                "构建数据收集管道",
                "实现异常检测算法",
                "开发可视化仪表盘"
            ]
        elif "数据收集" in task_description:
            return [
                "设计数据Schema",
                "编写数据爬取脚本",
                "设置数据清洗流程",
                "配置数据存储方案"
            ]
        else:
            # 默认分解策略：添加具体动词前缀
            verbs = ["分析", "设计", "实现", "测试", "部署"]
            return [f"{verb}相关组件 for {task_description}" for verb in verbs]

    def get_execution_path(self, root_task: TaskNode) -> List[Tuple[str, Optional[SkillNode]]]:
        """
        获取可执行路径（扁平化的任务列表）
        
        Args:
            root_task: 任务树根节点
            
        Returns:
            List of (task_description, mapped_skill) tuples
        """
        execution_path = []
        
        def traverse(node: TaskNode):
            if node.mapped_skill:
                execution_path.append((node.description, node.mapped_skill))
            for child in node.children:
                traverse(child)
                
        traverse(root_task)
        return execution_path

# 示例技能数据库 (模拟588个技能节点)
def create_sample_skill_database() -> Dict[str, SkillNode]:
    """创建示例技能数据库"""
    skills = {
        "skill_001": SkillNode("skill_001", "数据分析", "使用Python进行数据清洗和分析", "数据科学", ["Python", "Pandas"]),
        "skill_002": SkillNode("skill_002", "机器学习建模", "构建和训练机器学习模型", "AI", ["TensorFlow", "Scikit-learn"]),
        "skill_003": SkillNode("skill_003", "物联网部署", "部署和管理IoT设备网络", "IoT", ["MQTT", "嵌入式系统"]),
        "skill_004": SkillNode("skill_004", "前端开发", "构建Web用户界面", "开发", ["React", "JavaScript"]),
        "skill_005": SkillNode("skill_005", "后端开发", "构建服务器端逻辑", "开发", ["Django", "REST API"]),
        "skill_006": SkillNode("skill_006", "数据可视化", "创建交互式数据可视化", "数据科学", ["D3.js", "Matplotlib"]),
        "skill_007": SkillNode("skill_007", "自动化测试", "编写和执行自动化测试脚本", "QA", ["Selenium", "PyTest"]),
        "skill_008": SkillNode("skill_008", "云计算部署", "部署应用到云平台", "运维", ["AWS", "Docker", "Kubernetes"]),
    }
    # 模拟更多技能节点...
    for i in range(9, 588):
        skills[f"skill_{i:03d}"] = SkillNode(
            f"skill_{i:03d}", 
            f"技能_{i}", 
            f"技能_{i}的描述", 
            f"类别_{i % 10}"
        )
    return skills

# 使用示例
if __name__ == "__main__":
    # 1. 初始化分解器
    skill_db = create_sample_skill_database()
    decomposer = AutoTopDownDecomposer(
        skill_database=skill_db,
        max_depth=4,
        min_granularity_score=0.7,
        strategy=DecompositionStrategy.BREADTH_FIRST
    )
    
    # 2. 分解宏大目标
    try:
        root_task = decomposer.decompose_macro_goal("解决气候变化")
        
        # 3. 获取执行路径
        execution_path = decomposer.get_execution_path(root_task)
        
        print("\n=== 可执行实践清单 ===")
        for idx, (task_desc, skill) in enumerate(execution_path[:10], 1):  # 只显示前10个
            print(f"{idx}. {task_desc} -> Skill: {skill.skill_id if skill else 'None'}")
        
        print(f"\n总计: {len(execution_path)} 个可执行任务节点")
        
    except PlanningError as e:
        print(f"规划失败: {str(e)}")