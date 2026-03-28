"""
意图-参数闭环校验器

该模块实现了一个基于变量引用解析图的参数约束系统，用于在多轮对话中处理模糊意图，
并将其转化为具体的数值参数，同时进行约束验证。

核心功能：
1. 锚定模糊代词到具体对象
2. 将模糊意图转化为具体参数
3. 反向验证参数调整是否违背隐含约束

数据格式：
输入：
    - 对话历史: List[Dict[str, Any]]
    - 当前意图: Dict[str, Any]
    - 上下文状态: Dict[str, Any]
输出：
    - 参数校验结果: Dict[str, Any]
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentParamValidator")


class ConstraintType(Enum):
    """约束类型枚举"""
    ASPECT_RATIO = "aspect_ratio"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    DEPENDENCY = "dependency"


@dataclass
class Constraint:
    """约束条件数据结构"""
    type: ConstraintType
    params: Dict[str, Any]
    description: str = ""


class IntentParamValidator:
    """
    意图-参数闭环校验器
    
    该类负责在多轮对话中处理模糊意图，将其转化为具体参数，并验证参数调整是否满足预设约束。
    
    Attributes:
        reference_graph (Dict[str, Any]): 变量引用解析图
        constraints (Dict[str, List[Constraint]]): 对象约束字典
        context_state (Dict[str, Any]): 当前上下文状态
    """
    
    def __init__(self):
        """初始化校验器"""
        self.reference_graph: Dict[str, Any] = {}
        self.constraints: Dict[str, List[Constraint]] = {}
        self.context_state: Dict[str, Any] = {}
        self._init_default_constraints()
        logger.info("IntentParamValidator initialized")
    
    def _init_default_constraints(self) -> None:
        """初始化默认约束条件"""
        self.default_constraints = [
            Constraint(
                type=ConstraintType.ASPECT_RATIO,
                params={"tolerance": 0.1},
                description="Maintain aspect ratio"
            ),
            Constraint(
                type=ConstraintType.MIN_VALUE,
                params={"value": 100},
                description="Minimum size limit"
            )
        ]
    
    def _resolve_reference(self, reference: str) -> Optional[str]:
        """
        解析模糊引用到具体对象ID
        
        Args:
            reference: 模糊引用词，如'它'、'这个'
            
        Returns:
            Optional[str]: 解析到的对象ID，未找到返回None
        """
        reference_map = {
            "它": "last_object",
            "这个": "current_selection",
            "那个": "previous_selection"
        }
        
        resolved = reference_map.get(reference.lower())
        if resolved and resolved in self.reference_graph:
            logger.debug(f"Resolved reference '{reference}' to '{resolved}'")
            return resolved
        
        logger.warning(f"Failed to resolve reference: {reference}")
        return None
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """
        从文本中提取数值
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[float]: 提取的数值，未找到返回None
        """
        match = re.search(r"[-+]?\d*\.\d+|\d+", text)
        return float(match.group()) if match else None
    
    def _apply_context_constraints(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用上下文约束到参数
        
        Args:
            params: 原始参数
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 约束调整后的参数
        """
        adjusted_params = params.copy()
        
        # 示例：处理尺寸调整
        if "size" in params and "current_size" in context:
            current_size = context["current_size"]
            relative_factor = params["size"]
            
            if isinstance(relative_factor, str) and relative_factor.endswith("%"):
                factor = float(relative_factor[:-1]) / 100
                adjusted_params["width"] = int(current_size["width"] * factor)
                adjusted_params["height"] = int(current_size["height"] * factor)
                logger.debug(f"Adjusted size to {adjusted_params['width']}x{adjusted_params['height']}")
        
        return adjusted_params
    
    def _validate_constraints(
        self,
        object_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        验证参数是否满足约束条件
        
        Args:
            object_id: 对象ID
            params: 待验证参数
            context: 上下文信息
            
        Returns:
            Tuple[bool, Optional[str]]: (验证结果, 错误消息)
        """
        constraints = self.constraints.get(object_id, self.default_constraints)
        
        for constraint in constraints:
            if constraint.type == ConstraintType.ASPECT_RATIO:
                if "width" in params and "height" in params and "original_size" in context:
                    original = context["original_size"]
                    original_ratio = original["width"] / original["height"]
                    new_ratio = params["width"] / params["height"]
                    
                    if abs(new_ratio - original_ratio) > constraint.params["tolerance"]:
                        msg = f"Aspect ratio violation: original {original_ratio:.2f} vs new {new_ratio:.2f}"
                        logger.warning(msg)
                        return False, msg
            
            elif constraint.type == ConstraintType.MIN_VALUE:
                for dim in ["width", "height"]:
                    if dim in params and params[dim] < constraint.params["value"]:
                        msg = f"{dim} below minimum: {params[dim]} < {constraint.params['value']}"
                        logger.warning(msg)
                        return False, msg
        
        logger.info("All constraints satisfied")
        return True, None
    
    def process_intent(
        self,
        intent: Dict[str, Any],
        context: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理用户意图并校验参数
        
        Args:
            intent: 用户意图字典，包含'action'和'params'
            context: 当前上下文状态
            history: 对话历史
            
        Returns:
            Dict[str, Any]: 包含处理结果和调整后参数的字典
            
        Example:
            >>> validator = IntentParamValidator()
            >>> intent = {
            ...     "action": "resize",
            ...     "params": {"size": "50%"},
            ...     "reference": "它"
            ... }
            >>> context = {
            ...     "current_size": {"width": 1920, "height": 1080},
            ...     "original_size": {"width": 1920, "height": 1080}
            ... }
            >>> result = validator.process_intent(intent, context, [])
            >>> print(result["success"])
            True
        """
        result = {
            "success": False,
            "adjusted_params": None,
            "error": None,
            "requires_confirmation": False
        }
        
        try:
            # 1. 解析模糊引用
            if "reference" in intent:
                object_id = self._resolve_reference(intent["reference"])
                if not object_id:
                    result["error"] = f"无法解析引用: {intent['reference']}"
                    return result
            else:
                object_id = "default"
            
            # 2. 应用上下文约束调整参数
            adjusted_params = self._apply_context_constraints(intent["params"], context)
            
            # 3. 验证约束条件
            valid, error = self._validate_constraints(object_id, adjusted_params, context)
            if not valid:
                result["error"] = error
                result["requires_confirmation"] = True
                return result
            
            # 4. 返回成功结果
            result.update({
                "success": True,
                "adjusted_params": adjusted_params,
                "object_id": object_id
            })
            
        except Exception as e:
            logger.error(f"Intent processing failed: {str(e)}", exc_info=True)
            result["error"] = f"处理意图时发生错误: {str(e)}"
        
        return result
    
    def add_constraint(
        self,
        object_id: str,
        constraint_type: ConstraintType,
        params: Dict[str, Any],
        description: str = ""
    ) -> None:
        """
        为对象添加约束条件
        
        Args:
            object_id: 对象ID
            constraint_type: 约束类型
            params: 约束参数
            description: 约束描述
        """
        if object_id not in self.constraints:
            self.constraints[object_id] = []
        
        self.constraints[object_id].append(
            Constraint(
                type=constraint_type,
                params=params,
                description=description
            )
        )
        logger.info(f"Added constraint to {object_id}: {constraint_type}")


# 使用示例
if __name__ == "__main__":
    # 创建校验器实例
    validator = IntentParamValidator()
    
    # 添加自定义约束
    validator.add_constraint(
        "image_123",
        ConstraintType.ASPECT_RATIO,
        {"tolerance": 0.05},
        "Strict aspect ratio for image_123"
    )
    
    # 示例意图处理
    intent = {
        "action": "resize",
        "params": {"size": "50%"},
        "reference": "它"
    }
    
    context = {
        "current_size": {"width": 1920, "height": 1080},
        "original_size": {"width": 1920, "height": 1080}
    }
    
    # 更新引用图
    validator.reference_graph["last_object"] = "image_123"
    
    # 处理意图
    result = validator.process_intent(intent, context, [])
    
    # 输出结果
    print("处理结果:")
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"调整后参数: {result['adjusted_params']}")
        print(f"对象ID: {result['object_id']}")
    else:
        print(f"错误: {result['error']}")
        if result['requires_confirmation']:
            print("需要用户确认")