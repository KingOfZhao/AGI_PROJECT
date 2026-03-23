"""
交互式意图澄清循环模块

该模块实现了一个基于信息论的意图澄清系统，当且仅当意图模糊度超过阈值时，
触发"最小能耗提问"策略，通过计算信息增益/提问成本比率生成最优澄清问题。

核心功能:
1. 模糊度评估与阈值判断
2. 基于信息增益的最小能耗提问生成
3. 二选一或填空式问题构建

示例:
    >>> from auto_interaction_intent_clarification import IntentClarifier
    >>> clarifier = IntentClarifier(ambiguity_threshold=0.7)
    >>> intent = {"contrast": 0.5, "saturation": 0.5}
    >>> while clarifier.is_ambiguous(intent):
    ...     question = clarifier.generate_question(intent)
    ...     print(question)
    ...     response = input("Your answer: ")
    ...     intent = clarifier.update_intent(intent, response)
"""

import math
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """问题类型枚举"""
    BINARY = auto()  # 二选一问题
    FILL_BLANK = auto()  # 填空式问题
    SCALE = auto()  # 量表式问题

@dataclass
class Question:
    """澄清问题数据结构"""
    text: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    target_attribute: str = ""
    information_gain: float = 0.0
    cost: float = 1.0  # 默认提问成本为1

class IntentClarifier:
    """
    交互式意图澄清系统核心类
    
    实现当且仅当意图模糊度超过阈值时，触发最小能耗提问策略，
    通过计算信息增益/提问成本比率生成最优澄清问题。
    
    属性:
        ambiguity_threshold (float): 触发澄清的模糊度阈值(0-1)
        max_questions (int): 最大提问次数
        current_questions (int): 当前已提问次数
        cost_weights (Dict[str, float]): 不同类型问题的成本权重
    """
    
    def __init__(self, ambiguity_threshold: float = 0.75, max_questions: int = 5):
        """
        初始化意图澄清器
        
        参数:
            ambiguity_threshold: 模糊度阈值，超过此值触发澄清
            max_questions: 最大提问次数，防止无限循环
        """
        if not 0 <= ambiguity_threshold <= 1:
            raise ValueError("Ambiguity threshold must be between 0 and 1")
        if max_questions <= 0:
            raise ValueError("Max questions must be positive")
            
        self.ambiguity_threshold = ambiguity_threshold
        self.max_questions = max_questions
        self.current_questions = 0
        self.cost_weights = {
            QuestionType.BINARY: 1.0,
            QuestionType.FILL_BLANK: 1.5,
            QuestionType.SCALE: 1.2
        }
        logger.info(f"Initialized IntentClarifier with threshold {ambiguity_threshold}")
    
    def is_ambiguous(self, intent: Dict[str, float]) -> bool:
        """
        判断当前意图是否模糊
        
        参数:
            intent: 意图字典，键为属性名，值为确定性(0-1)
            
        返回:
            bool: 如果模糊度超过阈值且未达到最大提问次数返回True
        """
        if not intent:
            logger.warning("Empty intent provided")
            return False
            
        self._validate_intent(intent)
        ambiguity = self._calculate_ambiguity(intent)
        logger.debug(f"Current ambiguity: {ambiguity:.2f}")
        
        return (ambiguity > self.ambiguity_threshold and 
                self.current_questions < self.max_questions)
    
    def generate_question(self, intent: Dict[str, float]) -> Question:
        """
        生成最小能耗澄清问题
        
        参数:
            intent: 当前意图状态
            
        返回:
            Question: 生成的澄清问题
            
        异常:
            ValueError: 如果意图不模糊或已达到最大提问次数
        """
        if not self.is_ambiguous(intent):
            raise ValueError("Intent is not ambiguous or max questions reached")
            
        # 找出最模糊的属性
        target_attr = max(intent.items(), key=lambda x: 1 - x[1])[0]
        ambiguity = 1 - intent[target_attr]
        
        # 根据信息增益选择最佳问题类型
        question_type = self._select_question_type(ambiguity)
        
        # 生成问题文本
        if question_type == QuestionType.BINARY:
            question_text = self._generate_binary_question(target_attr)
            options = self._generate_binary_options(target_attr)
        else:
            question_text = self._generate_fill_blank_question(target_attr)
            options = None
            
        # 计算信息增益/成本比
        igc_ratio = self._calculate_information_gain_cost_ratio(
            ambiguity, self.cost_weights[question_type]
        )
        
        self.current_questions += 1
        logger.info(f"Generated {question_type.name} question for {target_attr}")
        
        return Question(
            text=question_text,
            question_type=question_type,
            options=options,
            target_attribute=target_attr,
            information_gain=igc_ratio * self.cost_weights[question_type],
            cost=self.cost_weights[question_type]
        )
    
    def update_intent(
        self, 
        intent: Dict[str, float], 
        question: Question, 
        response: Union[str, float]
    ) -> Dict[str, float]:
        """
        根据用户响应更新意图状态
        
        参数:
            intent: 当前意图状态
            question: 提问的问题对象
            response: 用户响应(二选一时为选项，填空时为具体值)
            
        返回:
            Dict[str, float]: 更新后的意图状态
        """
        self._validate_intent(intent)
        updated_intent = intent.copy()
        
        if question.question_type == QuestionType.BINARY:
            if response not in question.options:  # type: ignore
                raise ValueError("Invalid response for binary question")
            # 二选一问题将属性确定性设为1.0
            updated_intent[question.target_attribute] = 1.0
        elif question.question_type == QuestionType.FILL_BLANK:
            try:
                value = float(response)
                if not 0 <= value <= 1:
                    raise ValueError("Scale response must be between 0 and 1")
                updated_intent[question.target_attribute] = value
            except ValueError as e:
                logger.error(f"Invalid response for fill blank: {e}")
                raise
        
        logger.info(f"Updated intent for {question.target_attribute}")
        return updated_intent
    
    def _calculate_ambiguity(self, intent: Dict[str, float]) -> float:
        """
        计算意图的整体模糊度
        
        参数:
            intent: 意图字典
            
        返回:
            float: 整体模糊度(0-1)
        """
        # 使用熵计算模糊度
        total = sum(intent.values())
        if total <= 0:
            return 1.0
            
        entropy = 0.0
        for v in intent.values():
            if v > 0:
                p = v / total
                entropy -= p * math.log2(p)
                
        # 归一化到0-1
        max_entropy = math.log2(len(intent)) if len(intent) > 1 else 1.0
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return min(max(normalized, 0.0), 1.0)
    
    def _select_question_type(self, ambiguity: float) -> QuestionType:
        """
        根据模糊度选择最佳问题类型
        
        参数:
            ambiguity: 当前模糊度
            
        返回:
            QuestionType: 选定的问题类型
        """
        # 简单策略: 模糊度高时用二选一，否则用填空
        if ambiguity > 0.9:
            return QuestionType.BINARY
        elif ambiguity > 0.6:
            return QuestionType.FILL_BLANK
        else:
            return QuestionType.SCALE
    
    def _generate_binary_question(self, attribute: str) -> str:
        """生成二选一问题文本"""
        questions = {
            "contrast": "是指高对比度还是高饱和度?",
            "brightness": "是指明亮还是暗淡?",
            "saturation": "是指鲜艳还是柔和?",
            "clarity": "是指清晰还是模糊?"
        }
        return questions.get(attribute, f"是指高{attribute}还是低{attribute}?")
    
    def _generate_fill_blank_question(self, attribute: str) -> str:
        """生成填空式问题文本"""
        return f"请指定{attribute}的程度(0-1): "
    
    def _generate_binary_options(self, attribute: str) -> List[str]:
        """生成二选一问题的选项"""
        options = {
            "contrast": ["高对比度", "高饱和度"],
            "brightness": ["明亮", "暗淡"],
            "saturation": ["鲜艳", "柔和"],
            "clarity": ["清晰", "模糊"]
        }
        return options.get(attribute, [f"高{attribute}", f"低{attribute}"])
    
    def _calculate_information_gain_cost_ratio(
        self, 
        ambiguity: float, 
        cost: float
    ) -> float:
        """
        计算信息增益/成本比率
        
        参数:
            ambiguity: 当前模糊度
            cost: 提问成本
            
        返回:
            float: 信息增益/成本比率
        """
        # 简化模型: 信息增益与模糊度成正比
        information_gain = ambiguity * 0.8  # 假设能消除80%的模糊度
        return information_gain / cost if cost > 0 else 0.0
    
    def _validate_intent(self, intent: Dict[str, float]) -> None:
        """验证意图数据格式"""
        if not isinstance(intent, dict):
            raise TypeError("Intent must be a dictionary")
        for k, v in intent.items():
            if not isinstance(k, str):
                raise TypeError("Intent keys must be strings")
            if not isinstance(v, (int, float)):
                raise TypeError("Intent values must be numeric")
            if not 0 <= v <= 1:
                raise ValueError("Intent values must be between 0 and 1")

# 使用示例
if __name__ == "__main__":
    # 初始化澄清器
    clarifier = IntentClarifier(ambiguity_threshold=0.7)
    
    # 初始意图(所有属性都模糊)
    current_intent = {
        "contrast": 0.5,
        "brightness": 0.5,
        "saturation": 0.5
    }
    
    print("初始意图:", current_intent)
    
    # 澄清循环
    while clarifier.is_ambiguous(current_intent):
        question = clarifier.generate_question(current_intent)
        print(f"\n问题: {question.text}")
        
        if question.question_type == QuestionType.BINARY:
            print(f"选项: {question.options}")
            response = input("请选择(输入选项): ")
        else:
            response = input("请输入值(0-1): ")
        
        try:
            current_intent = clarifier.update_intent(current_intent, question, response)
            print("更新后意图:", current_intent)
        except ValueError as e:
            print(f"无效输入: {e}")
            clarifier.current_questions -= 1  # 不计数无效输入
    
    print("\n最终意图:", current_intent)