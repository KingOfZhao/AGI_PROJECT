"""
模块名称: probabilistic_code_planner
描述: 实现'意图-代码'概率规划器，通过思维链分解将抽象意图映射为可执行代码序列
核心功能: 概率化规划、思维链分解、上下文感知的API推荐、错误率降低验证
"""

import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""
    DATA_QUERY = "data_query"
    FILE_OPERATION = "file_operation"
    NETWORK_REQUEST = "network_request"
    UI_INTERACTION = "ui_interaction"
    SYSTEM_CONTROL = "system_control"
    UNKNOWN = "unknown"


@dataclass
class CodePlan:
    """代码规划数据结构"""
    steps: List[Dict[str, Union[str, float]]]
    total_confidence: float
    error_estimate: float
    context_usage: int


@dataclass
class PlanningContext:
    """规划上下文数据结构"""
    available_apis: Dict[str, Dict]
    context_window: int
    previous_errors: List[str]
    user_constraints: Dict[str, Union[int, str]]


class ProbabilisticCodePlanner:
    """
    概率化代码规划器核心类
    
    功能:
    1. 将抽象意图分解为思维链步骤
    2. 概率化评估每个步骤的可行性
    3. 生成低错误率的代码序列
    
    示例:
    >>> planner = ProbabilisticCodePlanner()
    >>> intent = "从用户输入获取日期并查询数据库"
    >>> plan = planner.plan_code_generation(intent)
    >>> print(plan.total_confidence)
    0.92
    """
    
    def __init__(self, context_window: int = 4096):
        """
        初始化规划器
        
        Args:
            context_window: 上下文窗口大小限制(字符数)
        """
        self.context_window = context_window
        self._validate_context_window()
        logger.info(f"初始化概率规划器，上下文窗口: {context_window}字符")
        
    def _validate_context_window(self) -> None:
        """验证上下文窗口大小是否合法"""
        if not isinstance(self.context_window, int) or self.context_window <= 0:
            raise ValueError("上下文窗口必须是正整数")
    
    def _analyze_intent(self, intent: str) -> Tuple[IntentType, Dict[str, float]]:
        """
        分析意图并确定类型及关键词权重
        
        Args:
            intent: 用户意图描述字符串
            
        Returns:
            Tuple[IntentType, Dict[str, float]]: 意图类型和关键词权重
            
        Raises:
            ValueError: 如果意图字符串为空或格式无效
        """
        if not isinstance(intent, str) or len(intent.strip()) == 0:
            logger.error("无效的意图输入")
            raise ValueError("意图必须是非空字符串")
            
        # 简单关键词分析(实际应用中可用NLP模型)
        keywords = {
            "查询": ("data_query", 0.8),
            "获取": ("data_query", 0.7),
            "保存": ("file_operation", 0.9),
            "读取": ("file_operation", 0.8),
            "下载": ("network_request", 0.9),
            "上传": ("network_request", 0.85),
            "点击": ("ui_interaction", 0.95),
            "输入": ("ui_interaction", 0.9),
            "系统": ("system_control", 0.8),
            "配置": ("system_control", 0.75)
        }
        
        intent_lower = intent.lower()
        scores = {t.value: 0.0 for t in IntentType if t != IntentType.UNKNOWN}
        
        for word, (intent_type, weight) in keywords.items():
            if word in intent_lower:
                scores[intent_type] += weight
                
        # 确定主要意图类型
        max_score = max(scores.values())
        if max_score < 0.5:
            intent_type = IntentType.UNKNOWN
        else:
            intent_type = IntentType(max(scores, key=scores.get))
            
        logger.debug(f"意图分析结果: {intent_type}, 关键词得分: {scores}")
        return intent_type, scores
    
    def plan_code_generation(
        self,
        intent: str,
        context: Optional[PlanningContext] = None
    ) -> CodePlan:
        """
        规划代码生成序列
        
        Args:
            intent: 用户意图描述
            context: 规划上下文(可选)
            
        Returns:
            CodePlan: 包含规划步骤和置信度的代码规划
            
        Example:
        >>> planner = ProbabilisticCodePlanner()
        >>> intent = "从用户输入获取日期并查询数据库"
        >>> plan = planner.plan_code_generation(intent)
        >>> print(plan.steps[0]['description'])
        '解析用户输入获取日期参数'
        """
        try:
            # 1. 分析意图
            intent_type, keyword_scores = self._analyze_intent(intent)
            
            # 2. 生成思维链步骤
            steps = self._generate_thought_chain(intent, intent_type)
            
            # 3. 计算总置信度和错误估计
            total_confidence = self._calculate_confidence(steps, keyword_scores)
            error_estimate = 1.0 - total_confidence
            
            # 4. 计算上下文使用量
            context_usage = sum(len(str(step)) for step in steps)
            if context and context.context_window > 0:
                context_usage = min(context_usage, context.context_window)
                
            logger.info(f"生成代码规划: {len(steps)}步骤, 置信度{total_confidence:.2f}")
            
            return CodePlan(
                steps=steps,
                total_confidence=total_confidence,
                error_estimate=error_estimate,
                context_usage=context_usage
            )
            
        except Exception as e:
            logger.error(f"代码规划失败: {str(e)}")
            raise RuntimeError("代码规划过程中发生错误") from e
    
    def _generate_thought_chain(
        self,
        intent: str,
        intent_type: IntentType
    ) -> List[Dict[str, Union[str, float]]]:
        """
        生成思维链步骤
        
        Args:
            intent: 用户意图描述
            intent_type: 意图类型
            
        Returns:
            List[Dict]: 思维链步骤列表，每个步骤包含描述和置信度
        """
        # 基于意图类型的模板步骤
        templates = {
            IntentType.DATA_QUERY: [
                ("解析用户输入获取查询参数", 0.95),
                ("验证参数格式和范围", 0.9),
                ("构建数据库查询语句", 0.85),
                ("执行查询并处理结果", 0.9),
                ("格式化输出结果", 0.95)
            ],
            IntentType.FILE_OPERATION: [
                ("验证文件路径和权限", 0.95),
                ("打开文件并设置模式", 0.9),
                ("执行读写操作", 0.85),
                ("处理文件异常", 0.9),
                ("关闭文件并释放资源", 0.95)
            ],
            IntentType.UNKNOWN: [
                ("分析用户意图", 0.6),
                ("生成通用代码框架", 0.5),
                ("添加错误处理", 0.7)
            ]
        }
        
        steps = []
        for desc, conf in templates.get(intent_type, templates[IntentType.UNKNOWN]):
            # 根据意图长度动态调整置信度
            adjusted_conf = conf * (0.9 + 0.1 * min(len(intent)/100, 1))
            steps.append({
                "description": desc,
                "confidence": adjusted_conf,
                "type": "thought"
            })
            
        return steps
    
    def _calculate_confidence(
        self,
        steps: List[Dict[str, Union[str, float]]],
        keyword_scores: Dict[str, float]
    ) -> float:
        """
        计算规划的总置信度
        
        Args:
            steps: 思维链步骤
            keyword_scores: 关键词得分
            
        Returns:
            float: 综合置信度(0-1之间)
        """
        if not steps:
            return 0.0
            
        # 步骤置信度平均值
        step_conf = sum(s["confidence"] for s in steps) / len(steps)
        
        # 关键词匹配度
        keyword_match = max(keyword_scores.values()) if keyword_scores else 0.5
        
        # 上下文复杂度调整(步骤越多置信度越低)
        complexity_factor = 1.0 - min(len(steps) * 0.05, 0.3)
        
        # 综合置信度
        total_conf = step_conf * 0.7 + keyword_match * 0.3 * complexity_factor
        return min(max(total_conf, 0.0), 1.0)
    
    def validate_plan(self, plan: CodePlan) -> bool:
        """
        验证代码规划的有效性
        
        Args:
            plan: 要验证的代码规划
            
        Returns:
            bool: 规划是否有效
            
        Example:
        >>> planner = ProbabilisticCodePlanner()
        >>> plan = planner.plan_code_generation("测试意图")
        >>> print(planner.validate_plan(plan))
        True
        """
        if not isinstance(plan, CodePlan):
            logger.error("无效的规划对象")
            return False
            
        # 检查基本属性
        if (plan.total_confidence < 0 or plan.total_confidence > 1 or
            plan.error_estimate < 0 or plan.error_estimate > 1 or
            plan.context_usage < 0):
            logger.error("规划属性值超出合理范围")
            return False
            
        # 检查步骤
        if not plan.steps or not isinstance(plan.steps, list):
            logger.error("规划步骤无效")
            return False
            
        for step in plan.steps:
            if (not isinstance(step, dict) or
                "description" not in step or
                "confidence" not in step or
                not (0 <= step["confidence"] <= 1)):
                logger.error("步骤格式无效")
                return False
                
        return True


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化规划器
        planner = ProbabilisticCodePlanner(context_window=8192)
        
        # 示例意图
        user_intent = "从用户输入获取日期范围，然后从数据库查询销售数据，最后将结果保存到CSV文件"
        
        # 生成规划
        plan = planner.plan_code_generation(user_intent)
        
        # 验证规划
        is_valid = planner.validate_plan(plan)
        
        # 打印结果
        print(f"规划有效性: {is_valid}")
        print(f"总置信度: {plan.total_confidence:.2f}")
        print(f"错误估计: {plan.error_estimate:.2f}")
        print("思维链步骤:")
        for i, step in enumerate(plan.steps, 1):
            print(f"{i}. {step['description']} (置信度: {step['confidence']:.2f})")
            
    except Exception as e:
        logger.error(f"规划示例失败: {str(e)}")