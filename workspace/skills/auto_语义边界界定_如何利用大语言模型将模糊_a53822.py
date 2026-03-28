"""
Module: auto_semantic_boundary_resolver.py
Description: 实现自然语言意图的结构化转化与边界界定。
             核心功能是将模糊的自然语言（NL）意图转化为符合严格JSON Schema的结构化对象。
             系统通过校验机制识别缺失的必要参数，并自动生成澄清问题，拒绝盲目臆测填充。
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

# 配置模块级日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 常量定义 ---
# 模拟LLM生成的原始意图分析结果（未校验）
_MOCK_LLM_RAW_OUTPUT = {
    "intent": "book_flight",
    "params": {
        "destination": "北京",
        "date": "明天",  # 模糊时间
        "passengers": "大概3个",  # 模糊数量
        # "origin": None,  # 缺失必要参数：出发地
        "class": "经济"  # 非必要参数
    }
}

# 定义严格的参数边界约束 Schema
_FLIGHT_BOOKING_SCHEMA = {
    "intent": {"type": "string", "required": True, "pattern": r"^[a-z_]+$"},
    "params": {
        "type": "dict",
        "required": True,
        "schema": {
            "origin": {"type": "string", "required": True, "description": "出发城市IATA代码或标准名"},
            "destination": {"type": "string", "required": True, "description": "到达城市IATA代码或标准名"},
            "date": {"type": "string", "required": True, "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "ISO格式日期 },
            "passengers": {"type": "int", "required": True, "min": 1, "max": 9, "description": "乘客人数 (1-9)"},
            "class": {"type": "string", "required": False, "default": "economy"}
        }
    }
}

class SemanticValidationError(ValueError):
    """自定义异常：当语义边界校验失败时抛出。"""
    pass

def _validate_data_type(value: Any, expected_type: str) -> bool:
    """
    [辅助函数] 校验数据的类型是否符合Schema预期。
    
    Args:
        value: 待校验的值。
        expected_type: 预期的类型字符串 (e.g., 'int', 'string', 'dict')。
        
    Returns:
        bool: 类型是否匹配。
    """
    type_mapping = {
        "string": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict
    }
    
    validator = type_mapping.get(expected_type)
    if not validator:
        logger.warning(f"未知的Schema类型定义: {expected_type}")
        return False
    
    # 特殊处理：布尔值的类型检查在Python中比较严格
    if expected_type == "bool":
        return isinstance(value, bool)
    
    return isinstance(value, validator)

def analyze_intent_parameters(
    raw_data: Dict[str, Any], 
    schema: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    """
    [核心函数 1] 分析并清洗意图参数，执行边界检查。
    
    此函数负责将"差不多"的模糊输入转化为"非0即1"的结构化数据。
    如果关键数据缺失或类型不匹配，它不会臆测，而是记录错误。
    
    Args:
        raw_data: 从LLM或用户输入解析出的原始字典。
        schema: 包含类型、必填项、正则等约束的Schema字典。
        
    Returns:
        Tuple[Dict, List]: 
            - 第一个元素是清洗后的"干净"数据（仅包含通过校验的字段）。
            - 第二个元素是缺失或错误的字段描述列表（用于生成澄清问题）。
            
    Raises:
        SemanticValidationError: 如果Schema本身无效或数据结构根本性错误。
    """
    if not isinstance(raw_data, dict) or not isinstance(schema, dict):
        raise SemanticValidationError("输入数据或Schema格式无效，必须为字典。")

    cleaned_data: Dict[str, Any] = {}
    clarification_requests: List[str] = []
    
    logger.info(f"开始语义边界分析，意图ID: {raw_data.get('intent', 'Unknown')}")

    # 提取参数定义
    params_schema = schema.get("params", {}).get("schema", {})
    if not params_schema:
        logger.error("Schema中未找到参数定义。")
        return cleaned_data, ["系统内部配置错误：缺少参数约束定义"]

    for param_name, constraints in params_schema.items():
        is_required = constraints.get("required", False)
        param_desc = constraints.get("description", param_name)
        raw_value = raw_data.get("params", {}).get(param_name)
        
        # 1. 检查必填项是否存在
        if raw_value is None:
            if is_required:
                msg = f"缺失必要参数: '{param_desc}' ({param_name})"
                clarification_requests.append(msg)
                logger.warning(f"边界校验失败 - {msg}")
            continue # 无论是否必填，值为None则跳过后续检查

        # 2. 类型校验与转换尝试
        expected_type = constraints.get("type")
        clean_value = None
        
        # 尝试智能转换（处理LLM输出的字符串化数字等情况）
        try:
            if expected_type == "int" and isinstance(raw_value, str):
                # 提取数字（例如 "大概3个" -> 3）
                num_match = re.search(r'\d+', raw_value)
                if num_match:
                    clean_value = int(num_match.group())
                else:
                    raise ValueError(f"无法从 '{raw_value}' 解析整数")
            elif expected_type == "string":
                clean_value = str(raw_value)
            else:
                if not _validate_data_type(raw_value, expected_type):
                    raise ValueError(f"类型不匹配: 期望 {expected_type}, 实际 {type(raw_value)}")
                clean_value = raw_value
        except (ValueError, TypeError) as e:
            msg = f"参数格式错误 '{param_desc}': 期望类型 {expected_type}, 输入值 '{raw_value}' 无效"
            clarification_requests.append(msg)
            logger.warning(f"边界校验失败 - {msg}")
            continue

        # 3. 边界值检查
        min_val = constraints.get("min")
        max_val = constraints.get("max")
        if min_val is not None and clean_value < min_val:
            clarification_requests.append(f"'{param_desc}' 数值不能小于 {min_val}")
            continue
        if max_val is not None and clean_value > max_val:
            clarification_requests.append(f"'{param_desc}' 数值不能大于 {max_val}")
            continue

        # 4. 正则/格式校验
        pattern = constraints.get("pattern")
        if pattern and expected_type == "string":
            if not re.match(pattern, str(clean_value)):
                clarification_requests.append(
                    f"'{param_desc}' 格式不正确，期望格式: {pattern} (例如: 2023-01-01)"
                )
                continue

        # 通过所有校验，加入清洗后的数据
        cleaned_data[param_name] = clean_value
        logger.debug(f"参数 '{param_name}' 通过校验: {clean_value}")

    return cleaned_data, clarification_requests

def generate_clarification_response(
    intent_name: str, 
    issues: List[str]
) -> Dict[str, Any]:
    """
    [核心函数 2] 根据校验失败的问题列表，生成结构化的澄清回复对象。
    
    这是解决"人与机器冲突"的关键：系统承认不知道，并主动询问，
    而不是使用默认值或幻觉填充。
    
    Args:
        intent_name: 当前尝试处理的意图名称。
        issues: analyze_intent_parameters 返回的问题描述列表。
        
    Returns:
        Dict: 符合前端或对话管理器渲染要求的结构化对象。
    """
    if not issues:
        return {
            "status": "ready_to_execute",
            "message": "所有参数校验通过，准备执行。",
            "content": None
        }

    logger.info(f"生成澄清回复，共 {len(issues)} 个问题。")
    
    # 构造结构化的询问对象
    response = {
        "status": "clarification_needed",
        "intent": intent_name,
        "message": "为了精确执行您的指令，我需要确认以下信息：",
        "missing_slots": issues,
        "suggested_actions": [
            {"type": "prompt_user", "content": issue} for issue in issues
        ]
    }
    
    return response

def process_user_intent(
    raw_user_input: Dict[str, Any], 
    target_schema: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    [主流程函数] 处理自然语言意图的完整流程。
    
    包含输入清洗、Schema校验、决策生成。
    
    Args:
        raw_user_input: 原始解析的JSON数据。
        target_schema: 目标约束Schema，如果为None则使用默认飞行预订Schema。
        
    Returns:
        Dict: 最终的处理结果（结构化数据或澄清请求）。
        
    Example:
        >>> result = process_user_intent(_MOCK_LLM_RAW_OUTPUT, _FLIGHT_BOOKING_SCHEMA)
        >>> print(result['status'])
        'clarification_needed'
    """
    logger.info("启动 AGI 语义边界界定模块...")
    
    if target_schema is None:
        target_schema = _FLIGHT_BOOKING_SCHEMA

    try:
        # 1. 深度拷贝以避免污染原始数据
        current_data = json.loads(json.dumps(raw_user_input))
        
        # 2. 提取意图名称
        intent_name = current_data.get("intent", "unknown_intent")
        
        # 3. 执行核心校验逻辑
        cleaned_params, issues = analyze_intent_parameters(current_data, target_schema)
        
        # 4. 决策分支
        if issues:
            # 存在模糊或缺失信息，生成澄清请求
            return generate_clarification_response(intent_name, issues)
        else:
            # 信息完备，生成最终执行指令
            return {
                "status": "execution_ready",
                "intent": intent_name,
                "params": cleaned_params,
                "timestamp": "2023-10-27T10:00:00Z" # 实际应使用 datetime.utcnow()
            }

    except SemanticValidationError as e:
        logger.error(f"语义处理错误: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception("处理过程中发生未预期异常")
        return {"status": "system_error", "message": "内部处理失败"}

# --- 模块执行入口 ---
if __name__ == "__main__":
    # 模拟 AGI 系统接收到一段模糊的自然语言解析结果
    print("--- 测试场景：模糊意图处理 ---")
    print(f"原始输入: {_MOCK_LLM_RAW_OUTPUT}")
    
    result = process_user_intent(_MOCK_LLM_RAW_OUTPUT)
    
    print("\n--- 处理结果 ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 预期结果应包含：
    # 1. 缺失 'origin' 的提示
    # 2. 'date' 格式错误的提示 (明天 vs YYYY-MM-DD)
    # 3. 'passengers' 被清洗为整数 3