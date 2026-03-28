"""
高级语义路由器模块：针对大规模Skill库的非线性意图映射系统

该模块实现了一个能够处理模糊自然语言意图到结构化Skill函数签名映射的语义路由器。
支持一对一映射、组合意图（多Skill组合）以及自动生成中间胶水代码。

典型用例:
    >>> router = SemanticRouter(skill_library)
    >>> result = router.route("分析销售数据并将结果发送给销售团队")
    >>> print(result.executable_code)

数据流:
    Input: 自然语言字符串
    -> [意图解析] -> [Skill检索] -> [组合规划] -> [代码生成] -> Output: 可执行Python代码
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum
import json
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillCategory(Enum):
    """Skill分类枚举"""
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    FILE_OPERATION = "file_operation"
    WEB_SCRAPING = "web_scraping"
    DATABASE = "database"

@dataclass
class SkillSignature:
    """Skill函数签名数据结构"""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    parameters: Dict[str, Any]
    return_type: str
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """数据验证"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', self.skill_id):
            raise ValueError(f"Invalid skill_id format: {self.skill_id}")
        if not self.name or len(self.name) > 50:
            raise ValueError("Skill name must be 1-50 characters")

@dataclass
class RoutingResult:
    """路由结果数据结构"""
    matched_skills: List[SkillSignature]
    confidence_score: float
    executable_code: str
    intermediate_vars: Dict[str, str] = field(default_factory=dict)
    execution_plan: List[str] = field(default_factory=list)

class SemanticRouter:
    """
    语义路由器核心类，实现自然语言到Skill的非线性映射
    
    属性:
        skill_library (Dict[str, SkillSignature]): Skill库字典
        embedding_model (Any): 语义嵌入模型
        code_generator (Callable): 代码生成函数
    """
    
    def __init__(self, skill_library: List[SkillSignature]):
        """
        初始化语义路由器
        
        参数:
            skill_library: Skill签名列表
        """
        self.skill_library = {skill.skill_id: skill for skill in skill_library}
        self._validate_skill_library()
        logger.info(f"SemanticRouter initialized with {len(skill_library)} skills")
    
    def _validate_skill_library(self) -> None:
        """验证Skill库的完整性和一致性"""
        required_fields = ['skill_id', 'name', 'description', 'category']
        for skill_id, skill in self.skill_library.items():
            for field_ in required_fields:
                if not getattr(skill, field_, None):
                    raise ValueError(f"Missing required field '{field_}' in skill {skill_id}")
        
        # 检查循环依赖
        self._check_circular_dependencies()
    
    def _check_circular_dependencies(self) -> None:
        """检查Skill库中是否存在循环依赖"""
        # 简化的循环依赖检查实现
        visited = set()
        for skill_id, skill in self.skill_library.items():
            self._dfs_check(skill_id, visited, set())
    
    def _dfs_check(self, current_id: str, visited: set, path: set) -> None:
        """深度优先搜索检查循环依赖"""
        if current_id in path:
            raise ValueError(f"Circular dependency detected involving skill {current_id}")
        if current_id in visited:
            return
        
        visited.add(current_id)
        path.add(current_id)
        
        skill = self.skill_library.get(current_id)
        if skill and skill.dependencies:
            for dep_id in skill.dependencies:
                if dep_id not in self.skill_library:
                    logger.warning(f"Missing dependency {dep_id} for skill {current_id}")
                    continue
                self._dfs_check(dep_id, visited, path.copy())
    
    def route(self, user_intent: str, max_skills: int = 3) -> RoutingResult:
        """
        根据用户意图路由到最合适的Skill组合
        
        参数:
            user_intent: 用户的自然语言意图描述
            max_skills: 最多组合的Skill数量
            
        返回:
            RoutingResult: 包含匹配的Skills和生成的代码
            
        异常:
            ValueError: 如果输入意图为空或格式不正确
        """
        if not user_intent or not isinstance(user_intent, str):
            raise ValueError("User intent must be a non-empty string")
        
        logger.info(f"Processing user intent: {user_intent[:100]}...")
        
        # 1. 意图解析
        parsed_intent = self._parse_intent(user_intent)
        
        # 2. Skill检索和排序
        candidate_skills = self._retrieve_skills(parsed_intent, max_skills)
        
        # 3. 组合规划
        execution_plan = self._plan_execution(candidate_skills)
        
        # 4. 代码生成
        code = self._generate_glue_code(execution_plan)
        
        return RoutingResult(
            matched_skills=candidate_skills,
            confidence_score=self._calculate_confidence(parsed_intent, candidate_skills),
            executable_code=code,
            execution_plan=[s.skill_id for s in execution_plan]
        )
    
    def _parse_intent(self, intent: str) -> Dict[str, Any]:
        """
        解析用户意图，提取关键信息和操作
        
        参数:
            intent: 原始用户意图文本
            
        返回:
            Dict: 包含解析后的意图组件
        """
        # 在实际实现中，这里会使用NLP模型进行更复杂的解析
        parsed = {
            'actions': [],
            'objects': [],
            'conditions': [],
            'connectors': []
        }
        
        # 简化的意图解析逻辑
        action_keywords = {
            '分析': 'analyze', '发送': 'send', '处理': 'process',
            '获取': 'fetch', '保存': 'save', '计算': 'calculate',
            '比较': 'compare', '生成': 'generate'
        }
        
        connector_keywords = ['并', '然后', '接着', '同时', '之后']
        
        # 检测连接词
        for conn in connector_keywords:
            if conn in intent:
                parsed['connectors'].append(conn)
        
        # 检测动作关键词
        for kw, action in action_keywords.items():
            if kw in intent:
                parsed['actions'].append(action)
        
        # 简单的名词提取（实际应用中应使用NLP技术）
        words = re.findall(r'[\w\u4e00-\u9fa5]+', intent)
        for word in words[1:]:  # 跳过第一个词通常是动作
            if word not in action_keywords and word not in connector_keywords:
                parsed['objects'].append(word)
        
        logger.debug(f"Parsed intent: {parsed}")
        return parsed
    
    def _retrieve_skills(self, parsed_intent: Dict, max_skills: int) -> List[SkillSignature]:
        """
        根据解析的意图检索相关Skills
        
        参数:
            parsed_intent: 解析后的意图字典
            max_skills: 返回的最大Skill数量
            
        返回:
            List[SkillSignature]: 按相关性排序的Skill列表
        """
        candidates = []
        
        # 基于动作的Skill匹配
        for action in parsed_intent['actions']:
            for skill in self.skill_library.values():
                if action.lower() in skill.description.lower():
                    candidates.append(skill)
        
        # 基于对象的Skill匹配
        for obj in parsed_intent['objects']:
            for skill in self.skill_library.values():
                if obj.lower() in skill.description.lower() and skill not in candidates:
                    candidates.append(skill)
        
        # 去重并限制数量
        unique_skills = list({s.skill_id: s for s in candidates}.values())
        sorted_skills = sorted(
            unique_skills,
            key=lambda s: self._score_skill_relevance(s, parsed_intent),
            reverse=True
        )
        
        return sorted_skills[:max_skills]
    
    def _score_skill_relevance(self, skill: SkillSignature, parsed_intent: Dict) -> float:
        """
        计算Skill与解析意图的相关性分数
        
        参数:
            skill: 待评估的Skill
            parsed_intent: 解析后的意图
            
        返回:
            float: 相关性分数(0-1)
        """
        score = 0.0
        
        # 动作匹配权重
        for action in parsed_intent['actions']:
            if action.lower() in skill.description.lower():
                score += 0.5
        
        # 对象匹配权重
        for obj in parsed_intent['objects']:
            if obj.lower() in skill.description.lower():
                score += 0.3
        
        # 连接词调整
        if parsed_intent['connectors']:
            # 如果有连接词，倾向于选择能够组合的Skills
            if skill.dependencies:
                score += 0.2
        
        return min(score, 1.0)
    
    def _plan_execution(self, skills: List[SkillSignature]) -> List[SkillSignature]:
        """
        规划Skill执行顺序
        
        参数:
            skills: 匹配的Skill列表
            
        返回:
            List[SkillSignature]: 按执行顺序排序的Skill列表
        """
        if not skills:
            return []
        
        # 简化的执行计划：按依赖关系排序
        executed = set()
        execution_order = []
        
        remaining_skills = skills.copy()
        while remaining_skills:
            progress = False
            for skill in remaining_skills.copy():
                # 检查所有依赖是否已满足
                if all(dep in executed or dep not in self.skill_library 
                       for dep in skill.dependencies):
                    execution_order.append(skill)
                    executed.add(skill.skill_id)
                    remaining_skills.remove(skill)
                    progress = True
            
            if not progress:
                logger.warning("Cannot resolve skill dependencies, using fallback order")
                execution_order.extend(remaining_skills)
                break
        
        return execution_order
    
    def _generate_glue_code(self, skills: List[SkillSignature]) -> str:
        """
        生成连接Skills的胶水代码
        
        参数:
            skills: 按执行顺序排序的Skill列表
            
        返回:
            str: 生成的Python代码字符串
        """
        if not skills:
            return "# No skills matched the user intent"
        
        code_lines = [
            "# Auto-generated glue code by SemanticRouter",
            "import logging",
            "from typing import Any, Dict",
            "",
            "logger = logging.getLogger(__name__)",
            "",
            "def execute_workflow(**kwargs) -> Dict[str, Any]:",
            "    results = {}",
            "    try:"
        ]
        
        # 生成Skill调用代码
        for i, skill in enumerate(skills):
            var_name = f"result_{i}"
            params = ", ".join(f"{k}={v}" for k, v in skill.parameters.items())
            
            code_lines.extend([
                f"        # Execute skill: {skill.name}",
                f"        {var_name} = {skill.skill_id}({params})",
                f"        results['{skill.skill_id}'] = {var_name}",
                ""
            ])
        
        # 添加返回和错误处理
        code_lines.extend([
            "        return results",
            "    except Exception as e:",
            "        logger.error(f'Workflow execution failed: {str(e)}')",
            "        return {'error': str(e)}",
            "",
            "# Entry point",
            'if __name__ == "__main__":',
            "    workflow_result = execute_workflow()",
            "    print(json.dumps(workflow_result, indent=2))"
        ])
        
        return "\n".join(code_lines)
    
    def _calculate_confidence(self, parsed_intent: Dict, skills: List[SkillSignature]) -> float:
        """
        计算路由结果的置信度分数
        
        参数:
            parsed_intent: 解析后的意图
            skills: 匹配的Skills
            
        返回:
            float: 置信度分数(0-1)
        """
        if not skills:
            return 0.0
        
        # 基于动作和对象的覆盖率计算置信度
        covered_actions = set()
        covered_objects = set()
        
        for skill in skills:
            for action in parsed_intent['actions']:
                if action.lower() in skill.description.lower():
                    covered_actions.add(action)
            
            for obj in parsed_intent['objects']:
                if obj.lower() in skill.description.lower():
                    covered_objects.add(obj)
        
        action_coverage = len(covered_actions) / len(parsed_intent['actions']) if parsed_intent['actions'] else 0
        object_coverage = len(covered_objects) / len(parsed_intent['objects']) if parsed_intent['objects'] else 0
        
        # 加权平均
        confidence = 0.6 * action_coverage + 0.4 * object_coverage
        return min(max(confidence, 0.0), 1.0)

def example_usage():
    """使用示例展示如何初始化和使用SemanticRouter"""
    # 示例Skill库
    skills = [
        SkillSignature(
            skill_id="pandas_analyze",
            name="数据分析工具",
            description="使用Pandas分析结构化数据，支持统计计算和数据清洗",
            category=SkillCategory.DATA_PROCESSING,
            parameters={"data": "DataFrame", "operations": "List[str]"},
            return_type="DataFrame",
            dependencies=[]
        ),
        SkillSignature(
            skill_id="smtp_send",
            name="邮件发送服务",
            description="通过SMTP协议发送电子邮件，支持附件和HTML内容",
            category=SkillCategory.COMMUNICATION,
            parameters={"to": "str", "subject": "str", "body": "str"},
            return_type="bool",
            dependencies=["pandas_analyze"]
        ),
        SkillSignature(
            skill_id="web_scraper",
            name="网页数据抓取",
            description="从指定网页抓取结构化数据，支持CSS选择器和XPath",
            category=SkillCategory.WEB_SCRAPING,
            parameters={"url": "str", "selectors": "Dict[str, str]"},
            return_type="List[Dict]",
            dependencies=[]
        )
    ]
    
    try:
        # 初始化路由器
        router = SemanticRouter(skills)
        
        # 示例1: 简单意图
        print("\n=== 示例1: 简单数据分析 ===")
        result1 = router.route("分析这些销售数据")
        print(f"匹配的Skills: {[s.name for s in result1.matched_skills]}")
        print(f"置信度: {result1.confidence_score:.2f}")
        
        # 示例2: 组合意图
        print("\n=== 示例2: 数据分析和邮件发送 ===")
        result2 = router.route("分析客户反馈数据并发送报告给营销团队")
        print(f"匹配的Skills: {[s.name for s in result2.matched_skills]}")
        print(f"执行计划: {result2.execution_plan}")
        
        # 示例3: 生成胶水代码
        print("\n=== 示例3: 生成的胶水代码 ===")
        print(result2.executable_code)
        
    except Exception as e:
        logger.error(f"Error in example usage: {str(e)}")

if __name__ == "__main__":
    example_usage()