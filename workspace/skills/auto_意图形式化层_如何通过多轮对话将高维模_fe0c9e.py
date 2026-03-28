"""
意图形式化层模块

本模块实现了一个基于"意图梯度下降"机制的多轮对话系统，用于将高维模糊意图
降维投影为结构化的JSON Schema。通过最小化'歧义熵'，系统能够自动识别模糊点
并生成澄清性问题，最终将非结构化语言转化为计算机可理解的严格类型定义。

核心功能：
1. 模糊意图分析与歧义熵计算
2. 基于状态机的多轮对话流程控制
3. 澄清性问题生成与用户反馈处理
4. 结构化JSON Schema生成

作者: AGI Architecture Team
版本: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentState(Enum):
    """意图形式化过程的状态枚举"""
    INIT = auto()               # 初始状态
    ANALYZING = auto()          # 分析模糊意图
    CLARIFYING = auto()         # 生成澄清性问题
    PROCESSING_FEEDBACK = auto() # 处理用户反馈
    SCHEMA_GENERATION = auto()  # 生成JSON Schema
    COMPLETED = auto()          # 完成状态
    ERROR = auto()              # 错误状态


@dataclass
class IntentContext:
    """意图上下文数据结构，用于在多轮对话中维护状态"""
    raw_intent: str                     # 原始模糊意图文本
    current_state: IntentState = IntentState.INIT  # 当前状态
    ambiguity_entropy: float = 1.0      # 当前歧义熵值 (0.0-1.0)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)  # 提取的实体
    clarification_history: List[Dict[str, str]] = field(default_factory=list)  # 澄清历史
    schema_template: Dict[str, Any] = field(default_factory=dict)  # Schema模板
    error_count: int = 0                # 错误计数器
    iteration_count: int = 0            # 迭代计数器


class AmbiguityEntropyCalculator:
    """
    歧义熵计算器
    
    用于计算和更新意图的歧义熵值，熵值越高表示意图越模糊。
    通过最小化熵值来锁定用户真实需求边界。
    """
    
    @staticmethod
    def calculate_initial_entropy(text: str) -> float:
        """
        计算初始歧义熵
        
        基于文本长度、词汇复杂度和语义模糊度计算初始熵值
        
        Args:
            text: 输入的模糊意图文本
            
        Returns:
            float: 初始歧义熵值 (0.0-1.0)
        """
        if not text or not isinstance(text, str):
            logger.warning("无效的输入文本，返回最大熵值")
            return 1.0
        
        # 简单实现：基于文本长度和词汇多样性
        words = text.split()
        if not words:
            return 1.0
            
        unique_words = set(words)
        lexical_diversity = len(unique_words) / len(words) if words else 0
        
        # 文本长度因子 (越长越清晰)
        length_factor = min(1.0, len(text) / 100)
        
        # 计算综合熵值
        entropy = max(0.0, min(1.0, 1.0 - (lexical_diversity * 0.5 + length_factor * 0.5)))
        
        logger.debug(f"计算初始熵值: {entropy:.4f} (词汇多样性: {lexical_diversity:.2f}, 长度因子: {length_factor:.2f})")
        return entropy
    
    @staticmethod
    def update_entropy(current_entropy: float, clarification_success: bool) -> float:
        """
        根据澄清结果更新歧义熵
        
        Args:
            current_entropy: 当前歧义熵值
            clarification_success: 澄清是否成功
            
        Returns:
            float: 更新后的歧义熵值
        """
        if clarification_success:
            # 每次成功澄清减少20-30%的熵值
            reduction = 0.2 + (current_entropy * 0.1)  # 自适应减少量
            new_entropy = max(0.0, current_entropy - reduction)
        else:
            # 澄清失败则略微增加熵值
            new_entropy = min(1.0, current_entropy + 0.05)
            
        logger.debug(f"熵值更新: {current_entropy:.4f} -> {new_entropy:.4f} (成功: {clarification_success})")
        return new_entropy


class IntentFormalizer:
    """
    意图形式化处理器
    
    通过多轮对话将模糊意图转化为结构化JSON Schema的核心类。
    实现了基于状态机的意图处理流程。
    """
    
    def __init__(self, entropy_threshold: float = 0.2, max_iterations: int = 5):
        """
        初始化意图形式化处理器
        
        Args:
            entropy_threshold: 熵值阈值，低于此值认为意图已足够清晰
            max_iterations: 最大迭代次数，防止无限循环
        """
        self.entropy_threshold = entropy_threshold
        self.max_iterations = max_iterations
        self.entropy_calculator = AmbiguityEntropyCalculator()
        
        logger.info(f"IntentFormalizer 初始化完成 (熵阈值: {entropy_threshold}, 最大迭代: {max_iterations})")
    
    def initialize_context(self, raw_intent: str) -> IntentContext:
        """
        初始化意图上下文
        
        Args:
            raw_intent: 原始模糊意图文本
            
        Returns:
            IntentContext: 初始化后的意图上下文对象
            
        Raises:
            ValueError: 如果输入为空或无效
        """
        if not raw_intent or not isinstance(raw_intent, str):
            error_msg = "原始意图不能为空且必须为字符串"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # 清理输入文本
        cleaned_intent = raw_intent.strip()
        if not cleaned_intent:
            raise ValueError("清理后的意图文本为空")
        
        # 创建上下文
        context = IntentContext(
            raw_intent=cleaned_intent,
            current_state=IntentState.ANALYZING,
            ambiguity_entropy=self.entropy_calculator.calculate_initial_entropy(cleaned_intent)
        )
        
        logger.info(f"上下文初始化完成: '{cleaned_intent}' (初始熵值: {context.ambiguity_entropy:.4f})")
        return context
    
    def analyze_intent(self, context: IntentContext) -> IntentContext:
        """
        分析模糊意图
        
        提取关键实体和语义特征，识别模糊点
        
        Args:
            context: 当前意图上下文
            
        Returns:
            IntentContext: 更新后的上下文
        """
        if context.current_state != IntentState.ANALYZING:
            logger.warning(f"状态转换错误: 当前状态 {context.current_state} 不允许分析操作")
            context.error_count += 1
            return context
            
        logger.info(f"开始分析意图: '{context.raw_intent}'")
        
        try:
            # 模拟实体提取 (实际应用中应使用NLP模型)
            entities = self._extract_entities(context.raw_intent)
            context.extracted_entities.update(entities)
            
            # 检查熵值决定下一步
            if context.ambiguity_entropy > self.entropy_threshold:
                context.current_state = IntentState.CLARIFYING
                logger.info(f"意图模糊 (熵: {context.ambiguity_entropy:.4f})，进入澄清阶段")
            else:
                context.current_state = IntentState.SCHEMA_GENERATION
                logger.info(f"意图清晰 (熵: {context.ambiguity_entropy:.4f})，直接生成Schema")
                
        except Exception as e:
            logger.error(f"意图分析失败: {str(e)}", exc_info=True)
            context.current_state = IntentState.ERROR
            context.error_count += 1
            
        return context
    
    def generate_clarification(self, context: IntentContext) -> Tuple[IntentContext, str]:
        """
        生成澄清性问题
        
        基于当前模糊点生成针对性的问题
        
        Args:
            context: 当前意图上下文
            
        Returns:
            Tuple[IntentContext, str]: 更新后的上下文和澄清问题
        """
        if context.current_state != IntentState.CLARIFYING:
            logger.warning(f"状态转换错误: 当前状态 {context.current_state} 不允许生成澄清")
            context.error_count += 1
            return context, "系统错误：当前状态无法生成澄清问题"
            
        # 检查迭代次数
        if context.iteration_count >= self.max_iterations:
            logger.warning(f"达到最大迭代次数 {self.max_iterations}，强制生成Schema")
            context.current_state = IntentState.SCHEMA_GENERATION
            return context, ""
            
        context.iteration_count += 1
        
        # 模拟澄清问题生成 (实际应用中应使用更复杂的逻辑)
        question = self._create_clarification_question(context)
        
        # 记录澄清历史
        clarification_entry = {
            "iteration": context.iteration_count,
            "entropy": context.ambiguity_entropy,
            "question": question
        }
        context.clarification_history.append(clarification_entry)
        
        logger.info(f"生成澄清问题 (迭代 {context.iteration_count}): {question}")
        return context, question
    
    def process_feedback(self, context: IntentContext, feedback: str) -> IntentContext:
        """
        处理用户反馈
        
        解析用户对澄清问题的回答，更新意图理解
        
        Args:
            context: 当前意图上下文
            feedback: 用户反馈文本
            
        Returns:
            IntentContext: 更新后的上下文
        """
        if context.current_state not in [IntentState.CLARIFYING, IntentState.PROCESSING_FEEDBACK]:
            logger.warning(f"状态转换错误: 当前状态 {context.current_state} 不允许处理反馈")
            context.error_count += 1
            return context
            
        if not feedback or not isinstance(feedback, str):
            logger.warning("无效的用户反馈，忽略处理")
            context.error_count += 1
            return context
            
        logger.info(f"处理用户反馈: '{feedback}'")
        
        try:
            # 模拟反馈分析 (实际应用中应使用NLP模型)
            feedback_entities = self._extract_entities(feedback)
            
            # 更新实体
            for key, value in feedback_entities.items():
                if key in context.extracted_entities:
                    if isinstance(context.extracted_entities[key], list):
                        context.extracted_entities[key].append(value)
                    else:
                        context.extracted_entities[key] = [context.extracted_entities[key], value]
                else:
                    context.extracted_entities[key] = value
            
            # 更新熵值 (模拟：假设反馈总是成功的)
            clarification_success = len(feedback_entities) > 0
            context.ambiguity_entropy = self.entropy_calculator.update_entropy(
                context.ambiguity_entropy, clarification_success
            )
            
            # 更新最后一条澄清记录
            if context.clarification_history:
                context.clarification_history[-1]["feedback"] = feedback
                context.clarification_history[-1]["success"] = clarification_success
            
            # 决定下一步
            if context.ambiguity_entropy <= self.entropy_threshold:
                context.current_state = IntentState.SCHEMA_GENERATION
                logger.info(f"熵值低于阈值 ({context.ambiguity_entropy:.4f})，准备生成Schema")
            else:
                context.current_state = IntentState.CLARIFYING
                logger.info(f"熵值仍高 ({context.ambiguity_entropy:.4f})，继续澄清")
                
        except Exception as e:
            logger.error(f"反馈处理失败: {str(e)}", exc_info=True)
            context.error_count += 1
            if context.error_count > 3:
                context.current_state = IntentState.ERROR
                
        return context
    
    def generate_schema(self, context: IntentContext) -> Tuple[IntentContext, Dict[str, Any]]:
        """
        生成JSON Schema
        
        基于提取的实体和澄清结果生成结构化Schema
        
        Args:
            context: 当前意图上下文
            
        Returns:
            Tuple[IntentContext, Dict[str, Any]]: 更新后的上下文和生成的Schema
        """
        if context.current_state != IntentState.SCHEMA_GENERATION:
            logger.warning(f"状态转换错误: 当前状态 {context.current_state} 不允许生成Schema")
            context.error_count += 1
            return context, {}
            
        logger.info("开始生成JSON Schema")
        
        try:
            # 模拟Schema生成 (实际应用中应基于更复杂的规则)
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Formalized Intent Schema",
                "description": f"Generated from intent: {context.raw_intent}",
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # 基于实体构建属性
            for key, value in context.extracted_entities.items():
                prop = {
                    "type": self._infer_type(value),
                    "description": f"Extracted from clarification process"
                }
                
                # 添加示例值
                if isinstance(value, (str, int, float, bool)):
                    prop["example"] = value
                elif isinstance(value, list) and value:
                    prop["example"] = value[0]
                    
                schema["properties"][key] = prop
                
                # 如果是关键实体，标记为必需
                if key in ["name", "id", "type", "action"]:
                    schema["required"].append(key)
            
            # 添加元数据
            schema["metadata"] = {
                "ambiguity_entropy": context.ambiguity_entropy,
                "iterations": context.iteration_count,
                "entities_found": len(context.extracted_entities)
            }
            
            context.schema_template = schema
            context.current_state = IntentState.COMPLETED
            
            logger.info(f"Schema生成完成: {len(schema['properties'])} 个属性")
            return context, schema
            
        except Exception as e:
            logger.error(f"Schema生成失败: {str(e)}", exc_info=True)
            context.current_state = IntentState.ERROR
            context.error_count += 1
            return context, {}
    
    # ==================== 辅助函数 ====================
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取实体 (模拟实现)
        
        实际应用中应使用NLP模型或更复杂的规则
        
        Args:
            text: 输入文本
            
        Returns:
            Dict[str, Any]: 提取的实体字典
        """
        entities = {}
        
        # 简单模式匹配 (仅用于演示)
        patterns = {
            "name": r"名称[是为]?[\"]?([^\"。，]+)[\"]?",
            "type": r"类型[是为]?[\"]?([^\"。，]+)[\"]?",
            "action": r"动作[是为]?[\"]?([^\"。，]+)[\"]?",
            "target": r"目标[是为]?[\"]?([^\"。，]+)[\"]?",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                entities[key] = match.group(1).strip()
        
        # 添加一些模拟实体
        if "后台" in text:
            entities["system_type"] = "backend"
        if "好用的" in text:
            entities["quality"] = "high_usability"
        if "用户" in text:
            entities["stakeholder"] = "user"
            
        logger.debug(f"从文本中提取实体: {entities}")
        return entities
    
    def _create_clarification_question(self, context: IntentContext) -> str:
        """
        创建澄清性问题 (模拟实现)
        
        基于当前模糊点生成针对性问题
        
        Args:
            context: 当前意图上下文
            
        Returns:
            str: 生成的澄清问题
        """
        # 基于缺失的关键实体生成问题
        missing = []
        for key in ["name", "type", "action"]:
            if key not in context.extracted_entities:
                missing.append(key)
        
        if not missing:
            return "请提供更多关于您需求的细节，以便我更好地理解。"
            
        # 简单问题模板
        question_templates = {
            "name": "您希望这个系统的名称是什么？",
            "type": "您需要的是什么类型的系统？（例如：Web应用、API服务、管理后台）",
            "action": "这个系统的主要功能或动作是什么？"
        }
        
        # 选择第一个缺失的关键实体提问
        first_missing = missing[0]
        return question_templates.get(first_missing, "请提供更多细节。")
    
    def _infer_type(self, value: Any) -> str:
        """
        推断值的JSON Schema类型
        
        Args:
            value: 要推断的值
            
        Returns:
            str: JSON Schema类型字符串
        """
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"  # 默认


def formalize_intent_automatically(raw_intent: str) -> Dict[str, Any]:
    """
    自动形式化意图的便捷函数
    
    执行完整的意图形式化流程，返回最终Schema
    
    Args:
        raw_intent: 原始模糊意图文本
        
    Returns:
        Dict[str, Any]: 生成的JSON Schema
        
    Example:
        >>> schema = formalize_intent_automatically("做一个好用的后台管理系统")
        >>> print(json.dumps(schema, indent=2, ensure_ascii=False))
    """
    formalizer = IntentFormalizer()
    
    try:
        # 初始化上下文
        context = formalizer.initialize_context(raw_intent)
        
        # 分析意图
        context = formalizer.analyze_intent(context)
        
        # 多轮澄清循环
        while context.current_state == IntentState.CLARIFYING:
            # 生成问题
            context, question = formalizer.generate_clarification(context)
            
            # 在实际应用中，这里应该获取用户输入
            # 模拟自动回答
            simulated_feedback = f"名称是示例系统，类型是管理后台，动作是数据管理"
            context = formalizer.process_feedback(context, simulated_feedback)
        
        # 生成Schema
        if context.current_state == IntentState.SCHEMA_GENERATION:
            context, schema = formalizer.generate_schema(context)
            return schema
        else:
            logger.error(f"意图形式化失败，最终状态: {context.current_state}")
            return {}
            
    except Exception as e:
        logger.error(f"自动形式化过程出错: {str(e)}", exc_info=True)
        return {}


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用类接口
    print("=== 示例1: 使用类接口 ===")
    formalizer = IntentFormalizer(entropy_threshold=0.3)
    
    # 初始化
    context = formalizer.initialize_context("做一个好用的后台管理系统")
    print(f"初始熵值: {context.ambiguity_entropy:.4f}")
    
    # 分析
    context = formalizer.analyze_intent(context)
    
    # 模拟多轮对话
    while context.current_state == IntentState.CLARIFYING:
        context, question = formalizer.generate_clarification(context)
        print(f"\n系统: {question}")
        
        # 模拟用户回答
        user_input = "名称是订单管理后台，类型是Web应用"
        print(f"用户: {user_input}")
        
        context = formalizer.process_feedback(context, user_input)
    
    # 生成Schema
    if context.current_state == IntentState.SCHEMA_GENERATION:
        context, schema = formalizer.generate_schema(context)
        print("\n生成的JSON Schema:")
        print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # 示例2: 使用便捷函数
    print("\n=== 示例2: 使用便捷函数 ===")
    quick_schema = formalize_intent_automatically("创建一个用户管理API")
    print(json.dumps(quick_schema, indent=2, ensure_ascii=False))