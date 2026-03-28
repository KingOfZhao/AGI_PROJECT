"""
高级语义语法制导生成器

模块名称: auto_创建_语义语法制导生成器_不仅让llm_80b0d1
描述: 本模块实现了一套基于属性文法的生成器框架。它不仅仅是让LLM输出JSON，
      而是将大模型视为Token生成器，通过内嵌的'文法规则'和'语义约束'来
      指导生成过程。这确保了最终输出不仅语法正确（符合JSON语法），而且
      符合深层业务逻辑（如参数类型匹配、业务规则校验）。
      
领域: cross_domain
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 自定义异常类型
class GrammarValidationError(Exception):
    """当生成的Token违反文法规则时抛出"""
    pass

class SemanticValidationError(Exception):
    """当上下文语义不符合业务逻辑时抛出"""
    pass

class SemanticSyntaxDirectedGenerator:
    """
    语义语法制导生成器核心类。
    
    该类模拟了一个受约束的生成环境。在实际AGI场景中，这将与LLM的推理引擎
    深度绑定（如Logit Bias或Beam Search拦截）。此处实现一个后置验证与
    迭代修复的模拟器，展示如何通过代码强制执行“Prompt Grammar”。
    
    Attributes:
        grammar_rules (Dict): 定义文法产生式规则。
        semantic_constraints (Dict): 定义语义校验函数。
    """

    def __init__(self, 
                 grammar_schema: Dict[str, Any], 
                 semantic_validators: Optional[Dict[str, Callable]] = None):
        """
        初始化生成器。
        
        Args:
            grammar_schema: 定义数据结构的JSON Schema或类似结构。
            semantic_validators: 针对特定字段的语义校验函数字典。
        """
        self.grammar_schema = grammar_schema
        self.semantic_validators = semantic_validators or {}
        self._generation_context: Dict[str, Any] = {}  # 存储生成过程中的继承属性
        logger.info("SemanticSyntaxDirectedGenerator initialized with schema.")

    def _check_grammar_constraint(self, partial_data: Dict, key: str, value: Any) -> bool:
        """
        辅助函数：检查当前Token/数据是否满足基础文法约束（类型、格式）。
        
        Args:
            partial_data: 已生成的数据部分。
            key: 当前正在生成的键。
            value: 当前尝试填入的值。
            
        Returns:
            bool: 是否通过检查。
        """
        # 简化的Schema检查逻辑
        expected_type = self.grammar_schema.get("properties", {}).get(key, {}).get("type")
        if expected_type:
            type_map = {'string': str, 'integer': int, 'object': dict, 'array': list}
            if not isinstance(value, type_map.get(expected_type, object)):
                logger.warning(f"Grammar violation: Key '{key}' expected type {expected_type}, got {type(value)}.")
                return False
        return True

    def _check_semantic_constraint(self, key: str, value: Any) -> bool:
        """
        核心函数：检查语义约束（属性文法的综合属性检查）。
        
        根据上下文检查当前值的合法性。例如，如果生成API调用，
        检查参数是否与之前生成的函数名匹配。
        
        Args:
            key: 当前键。
            value: 当前值。
            
        Returns:
            bool: 是否通过语义检查。
        """
        if key in self.semantic_validators:
            validator = self.semantic_validators[key]
            try:
                # 传入上下文和当前值进行校验
                is_valid = validator(context=self._generation_context, value=value)
                if not is_valid:
                    logger.error(f"Semantic violation: Value '{value}' for key '{key}' is invalid in context.")
                    return False
            except Exception as e:
                logger.error(f"Error during semantic validation for {key}: {e}")
                return False
        
        # 更新上下文（继承属性传递）
        self._generation_context[key] = value
        return True

    def generate_constrained_output(self, llm_raw_output_func: Callable[[], Dict]) -> Dict[str, Any]:
        """
        核心函数：执行受控生成循环。
        
        该函数模拟了LLM生成-校验-反馈的闭环。
        在真实的AGI系统中，这将在Token生成级别进行干预。
        
        Args:
            llm_raw_output_func: 一个模拟LLM生成的函数，返回待校验的JSON对象。
            
        Returns:
            Dict[str, Any]: 最终符合文法和语义的有效数据。
            
        Raises:
            GrammarValidationError: 如果无法修复文法错误。
            SemanticValidationError: 如果无法修复语义错误。
        """
        max_retries = 3
        for attempt in range(max_retries):
            logger.info(f"Generation attempt {attempt + 1}/{max_retries}")
            
            # 1. 模拟获取LLM原始输出
            try:
                raw_data = llm_raw_output_func()
                if not isinstance(raw_data, dict):
                    raise GrammarValidationError("Output is not a valid dictionary.")
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                continue

            # 2. 重置上下文
            self._generation_context = {}
            is_valid_structure = True

            # 3. 逐层进行语法制导翻译与校验
            # 这里简化为对字典的遍历，实际上可以是树的后序遍历
            for key, value in raw_data.items():
                # 检查文法
                if not self._check_grammar_constraint(raw_data, key, value):
                    is_valid_structure = False
                    break # 需要重新生成
                
                # 检查语义
                if not self._check_semantic_constraint(key, value):
                    is_valid_structure = False
                    break

            if is_valid_structure:
                logger.info("Successfully generated output satisfying all constraints.")
                return raw_data
            
            logger.warning("Validation failed, requesting regeneration...")
            # 在真实场景中，这里会将错误信息作为Prompt反馈给LLM
        
        raise SemanticValidationError("Failed to generate valid output after maximum retries.")


# --- 辅助函数和具体的业务逻辑示例 ---

def create_api_call_schema() -> Dict[str, Any]:
    """
    辅助函数：定义API调用的文法规则。
    """
    return {
        "type": "object",
        "properties": {
            "service_name": {"type": "string"},
            "action": {"type": "string"},
            "parameters": {"type": "object"},
            "timestamp": {"type": "integer"}
        },
        "required": ["service_name", "action", "parameters"]
    }

def validate_action_context(context: Dict, value: str) -> bool:
    """
    示例语义校验器：确保 'action' 与 'service_name' 匹配。
    
    规则：如果 service_name 是 'UserService', action 必须是 'create' 或 'delete'。
    """
    service = context.get('service_name')
    logger.debug(f"Validating action '{value}' for service '{service}'")
    
    if service == "UserService":
        return value in ["create", "delete", "update"]
    if service == "PaymentService":
        return value in ["process", "refund"]
    
    # 默认允许
    return True

def simulate_llm_json_output() -> Dict[str, Any]:
    """
    模拟LLM生成的JSON数据。
    在真实场景中，这是LLM基于Prompt生成的Token流。
    """
    # 模拟一个可能包含逻辑错误的生成（例如：UserService 调用了 'refund' action）
    # 注意：为了演示成功路径，这里生成一个正确的数据，
    # 或者读者可以修改此处数据来观察验证失败的重试过程。
    return {
        "service_name": "PaymentService",
        "action": "refund",
        "parameters": {
            "transaction_id": "tx_12345"
        },
        "timestamp": 1709821200
    }

def main():
    """
    使用示例入口。
    """
    # 1. 定义文法
    schema = create_api_call_schema()
    
    # 2. 定义语义约束
    # 这里的 key 对应数据字段，value 是校验函数
    validators = {
        "action": validate_action_context
    }
    
    # 3. 初始化生成器
    generator = SemanticSyntaxDirectedGenerator(
        grammar_schema=schema, 
        semantic_validators=validators
    )
    
    # 4. 执行生成
    try:
        result = generator.generate_constrained_output(simulate_llm_json_output)
        print("\n=== Final Valid Output ===")
        print(json.dumps(result, indent=2))
    except (GrammarValidationError, SemanticValidationError) as e:
        print(f"\nGeneration Failed: {e}")

if __name__ == "__main__":
    main()