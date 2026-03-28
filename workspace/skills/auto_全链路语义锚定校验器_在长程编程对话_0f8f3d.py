"""
全链路语义锚定校验器

该模块实现了一个在长程编程对话中，用于打通自然语言变量与代码变量边界的校验系统。
系统能够构建“语义-变量对照表”，实时监控用户意图与代码状态的一致性。
一旦发现锚点冲突（如用户试图修改常量），立即生成澄清提问或自动修正。

核心功能：
1. 语境锚定：确定自然语言中代词的具体指代对象。
2. 逻辑校验：验证用户意图在代码逻辑层面是否可行（如写权限、类型匹配）。
3. 冲突解决：在发现冲突时生成澄清提问或执行自动修正策略。

典型用例：
>>> validator = SemanticAnchorValidator()
>>> validator.update_context("img_size", value=1024, type_=int, is_constant=False)
>>> validator.update_context("MAX_RESOLUTION", value=4096, type_=int, is_constant=True)
>>> intent = "make it bigger" # "它"指代 img_size
>>> result = validator.validate_intent(intent, target_var="img_size", delta=1000)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticAnchorValidator")

class AnchorStatus(Enum):
    """锚定校验结果状态枚举"""
    VALID = "valid"                     # 校验通过
    CONFLICT_CONST = "conflict_const"   # 冲突：试图修改常量
    CONFLICT_TYPE = "conflict_type"     # 冲突：类型不匹配
    CONFLICT_RANGE = "conflict_range"   # 冲突：数值越界
    AMBIGUOUS_TARGET = "ambiguous"      # 模糊：无法确定目标对象

@dataclass
class CodeVariable:
    """
    代码变量数据结构
    
    Attributes:
        name (str): 变量名
        type (type): 变量类型
        value (Any): 当前值
        is_constant (bool): 是否为常量（只读）
        constraints (Dict): 变量约束条件（如最大值、最小值等）
    """
    name: str
    type: type
    value: Any
    is_constant: bool = False
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """
    校验结果数据结构
    
    Attributes:
        status (AnchorStatus): 校验状态
        message (str): 校验消息
        suggested_fix (Optional[Dict]): 建议的修正方案
        target_variable (Optional[str]): 目标变量名
    """
    status: AnchorStatus
    message: str
    suggested_fix: Optional[Dict[str, Any]] = None
    target_variable: Optional[str] = None

class SemanticAnchorValidator:
    """
    全链路语义锚定校验器
    
    用于在长程编程对话中监控用户意图与代码状态的一致性。
    """
    
    def __init__(self):
        """初始化校验器，创建语义-变量对照表"""
        self._variable_table: Dict[str, CodeVariable] = {}
        self._conversation_history: List[Dict[str, Any]] = []
        logger.info("SemanticAnchorValidator initialized")
    
    def update_context(self, 
                      var_name: str, 
                      value: Any, 
                      type_: type = None,
                      is_constant: bool = False,
                      constraints: Dict[str, Any] = None) -> None:
        """
        更新或添加变量到语义-变量对照表
        
        Args:
            var_name (str): 变量名
            value (Any): 变量值
            type_ (type, optional): 变量类型，如果为None则自动推断
            is_constant (bool, optional): 是否为常量，默认为False
            constraints (Dict[str, Any], optional): 变量约束条件
        
        Raises:
            ValueError: 如果变量名无效或试图修改常量
        """
        if not var_name or not isinstance(var_name, str):
            raise ValueError("Variable name must be a non-empty string")
            
        # 检查是否试图修改已存在的常量
        if var_name in self._variable_table and self._variable_table[var_name].is_constant:
            raise ValueError(f"Cannot modify constant variable: {var_name}")
        
        # 自动推断类型
        inferred_type = type_ if type_ is not None else type(value)
        
        # 创建或更新变量
        self._variable_table[var_name] = CodeVariable(
            name=var_name,
            type=inferred_type,
            value=value,
            is_constant=is_constant,
            constraints=constraints or {}
        )
        
        logger.debug(f"Updated variable: {var_name} = {value} (type: {inferred_type}, const: {is_constant})")
    
    def _find_variable_by_heuristics(self, 
                                    description: str, 
                                    operation: str) -> Optional[str]:
        """
        根据启发式规则从自然语言描述中推断变量
        
        Args:
            description (str): 自然语言描述（如"它"、"那个图片"）
            operation (str): 操作类型（如"改大"、"修改"）
            
        Returns:
            Optional[str]: 推断的变量名，如果无法确定则返回None
        """
        # 简单实现：实际项目中可以使用更复杂的NLP模型
        candidates = []
        
        # 规则1：如果描述是代词，查找最近的可修改变量
        if description.lower() in ['它', '那个', '这个']:
            # 从后向前查找最近的可修改变量
            for var_name in reversed(list(self._variable_table.keys())):
                if not self._variable_table[var_name].is_constant:
                    candidates.append(var_name)
        
        # 规则2：根据操作类型筛选（例如"改大"通常指数值类型）
        if operation in ['改大', '增大', '改小', '减小']:
            candidates = [v for v in candidates if self._variable_table[v].type in (int, float)]
        
        # 如果只有一个候选，返回它
        if len(candidates) == 1:
            return candidates[0]
        
        # 否则无法确定
        return None
    
    def validate_intent(self,
                       intent: str,
                       target_var: Optional[str] = None,
                       **kwargs) -> ValidationResult:
        """
        校验用户意图的可行性
        
        Args:
            intent (str): 用户意图描述（如"把它改大一点"）
            target_var (Optional[str]): 明确指定的目标变量名，如果为None则尝试自动推断
            **kwargs: 意图相关的参数（如delta=100表示增加100）
            
        Returns:
            ValidationResult: 校验结果对象
            
        Example:
            >>> validator.validate_intent("make it bigger", target_var="img_size", delta=100)
        """
        # 1. 确定目标变量
        if target_var is None:
            # 尝试从意图中推断
            target_var = self._find_variable_by_heuristics(intent.split()[0] if intent else "", 
                                                          intent.split()[-1] if intent else "")
            if target_var is None:
                logger.warning(f"Could not determine target variable for intent: {intent}")
                return ValidationResult(
                    status=AnchorStatus.AMBIGUOUS_TARGET,
                    message=f"无法确定目标对象，请明确指定要修改的变量。",
                    target_variable=None
                )
        
        # 检查变量是否存在
        if target_var not in self._variable_table:
            logger.error(f"Variable not found: {target_var}")
            return ValidationResult(
                status=AnchorStatus.AMBIGUOUS_TARGET,
                message=f"变量 '{target_var}' 不存在。",
                target_variable=target_var
            )
        
        var = self._variable_table[target_var]
        
        # 2. 检查是否试图修改常量
        if var.is_constant:
            logger.warning(f"Attempt to modify constant variable: {target_var}")
            return ValidationResult(
                status=AnchorStatus.CONFLICT_CONST,
                message=f"无法修改常量 '{target_var}'。",
                suggested_fix={"action": "clarify", "message": f"'{target_var}' 是只读常量，是否要修改其他变量？"},
                target_variable=target_var
            )
        
        # 3. 根据意图类型进行具体校验
        if '改大' in intent or '增大' in intent or 'bigger' in intent.lower():
            return self._validate_modify_operation(target_var, operation='increase', **kwargs)
        elif '改小' in intent or '减小' in intent or 'smaller' in intent.lower():
            return self._validate_modify_operation(target_var, operation='decrease', **kwargs)
        elif '修改' in intent or 'change' in intent.lower():
            return self._validate_modify_operation(target_var, operation='set', **kwargs)
        
        # 默认返回有效
        return ValidationResult(
            status=AnchorStatus.VALID,
            message="校验通过。",
            target_variable=target_var
        )
    
    def _validate_modify_operation(self,
                                  var_name: str,
                                  operation: str,
                                  **kwargs) -> ValidationResult:
        """
        验证修改操作的可行性（辅助函数）
        
        Args:
            var_name (str): 变量名
            operation (str): 操作类型
            **kwargs: 操作参数
            
        Returns:
            ValidationResult: 校验结果
        """
        var = self._variable_table[var_name]
        
        # 类型检查
        if var.type not in (int, float, str):
            logger.warning(f"Unsupported type for modification: {var.type}")
            return ValidationResult(
                status=AnchorStatus.CONFLICT_TYPE,
                message=f"不支持修改变量 '{var_name}' 的类型 {var.type}。",
                target_variable=var_name
            )
        
        # 数值类型操作检查
        if var.type in (int, float):
            if operation == 'increase':
                delta = kwargs.get('delta', 1)
                new_value = var.value + delta
            elif operation == 'decrease':
                delta = kwargs.get('delta', 1)
                new_value = var.value - delta
            else:
                new_value = kwargs.get('value', var.value)
            
            # 边界检查
            min_val = var.constraints.get('min')
            max_val = var.constraints.get('max')
            
            if min_val is not None and new_value < min_val:
                logger.warning(f"Value {new_value} below minimum {min_val}")
                return ValidationResult(
                    status=AnchorStatus.CONFLICT_RANGE,
                    message=f"值 {new_value} 低于最小限制 {min_val}。",
                    suggested_fix={"action": "auto_correct", "value": min_val},
                    target_variable=var_name
                )
            
            if max_val is not None and new_value > max_val:
                logger.warning(f"Value {new_value} exceeds maximum {max_val}")
                return ValidationResult(
                    status=AnchorStatus.CONFLICT_RANGE,
                    message=f"值 {new_value} 超过最大限制 {max_val}。",
                    suggested_fix={"action": "auto_correct", "value": max_val},
                    target_variable=var_name
                )
        
        # 如果所有检查都通过
        return ValidationResult(
            status=AnchorStatus.VALID,
            message=f"操作校验通过。准备{operation}变量 '{var_name}'。",
            target_variable=var_name
        )
    
    def get_variable_info(self, var_name: str) -> Optional[Dict[str, Any]]:
        """
        获取变量信息
        
        Args:
            var_name (str): 变量名
            
        Returns:
            Optional[Dict[str, Any]]: 变量信息字典，如果不存在则返回None
        """
        if var_name in self._variable_table:
            var = self._variable_table[var_name]
            return {
                'name': var.name,
                'type': str(var.type),
                'value': var.value,
                'is_constant': var.is_constant,
                'constraints': var.constraints
            }
        return None
    
    def list_variables(self) -> List[str]:
        """返回当前上下文中所有变量名"""
        return list(self._variable_table.keys())

if __name__ == "__main__":
    # 使用示例
    validator = SemanticAnchorValidator()
    
    # 添加一些变量到上下文
    validator.update_context("img_size", value=1024, type_=int, is_constant=False, constraints={"max": 4096})
    validator.update_context("MAX_RESOLUTION", value=4096, type_=int, is_constant=True)
    validator.update_context("app_name", value="MyApp", type_=str)
    
    # 测试校验
    print("\n=== 测试1：正常修改 ===")
    result = validator.validate_intent("make img_size bigger", target_var="img_size", delta=100)
    print(f"结果: {result.status.value}, 消息: {result.message}")
    
    print("\n=== 测试2：试图修改常量 ===")
    result = validator.validate_intent("change MAX_RESOLUTION", target_var="MAX_RESOLUTION")
    print(f"结果: {result.status.value}, 消息: {result.message}")
    
    print("\n=== 测试3：数值越界 ===")
    result = validator.validate_intent("increase img_size", target_var="img_size", delta=5000)
    print(f"结果: {result.status.value}, 消息: {result.message}")
    print(f"建议修正: {result.suggested_fix}")
    
    print("\n=== 测试4：模糊目标 ===")
    result = validator.validate_intent("change it")
    print(f"结果: {result.status.value}, 消息: {result.message}")