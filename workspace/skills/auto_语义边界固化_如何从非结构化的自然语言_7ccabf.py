"""
Module: semantic_boundary_solidification.py
Description: 实现【语义边界固化】功能。
             将非结构化、模糊的自然语言意图通过概率映射和逻辑推断，
             转化为具备严格类型定义的JSON Schema对象。
Author: AGI System
Version: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 常量与配置 ---
CONFIDENCE_THRESHOLD = 0.6  # 语义推断置信度阈值

class SchemaTypeEnum(Enum):
    """扩展的Schema类型枚举，用于内部映射"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "string"  # 带格式约束

@dataclass
class EntityField:
    """描述提取出的实体字段及其元数据"""
    name: str
    type_hint: str
    description: str
    confidence: float
    required: bool = True

def _normalize_text(text: str) -> str:
    """
    辅助函数：清洗和规范化输入文本。
    
    Args:
        text (str): 原始输入文本。
        
    Returns:
        str: 清洗后的文本（小写、去多余空格）。
    """
    if not text or not isinstance(text, str):
        return ""
    # 去除特殊字符，保留中文、英文、数字
    cleaned = re.sub(r'[^\w\u4e00-\u9fa5\s]', '', text)
    return " ".join(cleaned.lower().split())

def extract_core_entities(user_prompt: str) -> List[EntityField]:
    """
    核心函数1：从自然语言中提取核心实体。
    
    此函数模拟NLP解析过程，通过关键词匹配和概率推断识别意图中的关键变量。
    在生产环境中应替换为LLM调用或NLP模型推理。
    
    Args:
        user_prompt (str): 用户的非结构化输入（例如："帮我搞个好看的销售分析，按地区分组"）。
        
    Returns:
        List[EntityField]: 提取出的实体字段列表。
        
    Raises:
        ValueError: 如果输入文本过短或无法解析。
    """
    normalized_input = _normalize_text(user_prompt)
    if len(normalized_input) < 5:
        logger.warning(f"Input text too short: {user_prompt}")
        raise ValueError("输入文本过短，无法提取有效语义")
        
    logger.info(f"Extracting entities from: {normalized_input}")
    
    entities = []
    
    # 模拟：基于规则的意图识别 (Mock Logic)
    # 实际场景应使用 embedding 相似度匹配
    
    # 规则1: 识别"分析"类意图
    if "分析" in normalized_input or "report" in normalized_input:
        # 推断：通常需要时间范围
        entities.append(EntityField(
            name="time_range",
            type_hint=SchemaTypeEnum.STRING.value,
            description="数据的时间筛选范围",
            confidence=0.8,
            required=True
        ))
        
        # 推断：如果有"按...分组"，提取维度
        match = re.search(r"按\s*(\w+)\s*分组", normalized_input)
        if match:
            dim_name = match.group(1)
            entities.append(EntityField(
                name="dimension",
                type_hint=SchemaTypeEnum.STRING.value,
                description=f"分析维度，例如: {dim_name}",
                confidence=0.95,
                required=True
            ))
        else:
            # 模糊推断：没说按什么分，可能是整体分析
            entities.append(EntityField(
                name="dimension",
                type_hint=SchemaTypeEnum.STRING.value,
                description="可选的分析维度",
                confidence=0.5,
                required=False
            ))

    # 规则2: 识别"好看" -> 图表类型推断
    if "好看" in normalized_input or "可视化" in normalized_input:
        entities.append(EntityField(
            name="chart_type",
            type_hint=SchemaTypeEnum.STRING.value,
            description="可视化的图表类型",
            confidence=0.7,
            required=False
        ))
        
    # 规则3: 识别"前N个" -> 数量限制
    match_top_n = re.search(r"前\s*(\d+)\s*个", normalized_input)
    if match_top_n:
        entities.append(EntityField(
            name="limit",
            type_hint=SchemaTypeEnum.INTEGER.value,
            description="返回数据的数量限制",
            confidence=0.99,
            required=True
        ))
        
    if not entities:
        logger.error("No entities could be extracted with confidence.")
        raise ValueError("无法从语义中提取有效实体")

    return entities

def map_to_json_schema(entities: List[EntityField], schema_title: str = "GeneratedSchema") -> Dict[str, Any]:
    """
    核心函数2：将提取的实体列表映射为标准的JSON Schema。
    
    进行语义边界固化，将概率性的实体转化为确定性的类型定义。
    
    Args:
        entities (List[EntityField]): 提取的实体列表。
        schema_title (str): 生成Schema的标题。
        
    Returns:
        Dict[str, Any]: 完整的JSON Schema字典对象。
    """
    if not entities:
        raise ValueError("实体列表不能为空")

    logger.info(f"Mapping {len(entities)} entities to JSON Schema...")
    
    properties = {}
    required_fields = []
    
    for entity in entities:
        # 边界检查：置信度过滤
        if entity.confidence < CONFIDENCE_THRESHOLD:
            logger.warning(f"Field '{entity.name}' dropped due to low confidence: {entity.confidence}")
            continue
            
        # 构建字段定义
        field_def = {
            "type": entity.type_hint,
            "description": entity.description
        }
        
        # 针对特定类型的约束增强
        if entity.name == "time_range":
            field_def["format"] = "date-time"
        elif entity.type_hint == "string" and entity.name == "chart_type":
            field_def["enum"] = ["bar", "line", "pie", "scatter"] # 固化边界：限制可选值

        properties[entity.name] = field_def
        
        if entity.required:
            required_fields.append(entity.name)
            
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": schema_title,
        "type": "object",
        "properties": properties,
        "required": required_fields
    }
    
    logger.info("Schema generation completed.")
    return schema

def validate_instance_against_schema(instance: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    辅助工具函数：简单的Schema验证器（非完整实现，仅用于演示边界检查）。
    
    Args:
        instance (Dict): 待验证的数据实例。
        schema (Dict): JSON Schema。
        
    Returns:
        bool: 验证是否通过。
    """
    logger.debug("Validating instance against schema...")
    
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    
    # 检查必填项
    for field in required:
        if field not in instance:
            logger.error(f"Validation Failed: Missing required field '{field}'")
            return False
            
    # 检查类型匹配
    for key, value in instance.items():
        if key in properties:
            expected_type = properties[key]["type"]
            # 简单类型检查映射
            type_map = {
                "string": str,
                "integer": int,
                "boolean": bool,
                "number": (int, float),
                "array": list,
                "object": dict
            }
            if expected_type in type_map:
                if not isinstance(value, type_map[expected_type]):
                    logger.error(f"Validation Failed: Field '{key}' expected type {expected_type}, got {type(value)}")
                    return False
                    
    logger.info("Instance validation passed.")
    return True

# --- 使用示例与主程序入口 ---
if __name__ == "__main__":
    # 模拟AGI系统接收到的模糊用户指令
    fuzzy_user_input = "帮我搞个好看的销售数据分析，要看2023年的，按地区分组，只要前10个"
    
    print(f"--- 处理用户输入: '{fuzzy_user_input}' ---")
    
    try:
        # 1. 提取核心实体 (语义 -> 概率实体)
        extracted_entities = extract_core_entities(fuzzy_user_input)
        print(f"\n[Step 1] 提取到的实体:")
        for ent in extracted_entities:
            print(f" - {ent.name}: {ent.type_hint} (Confidence: {ent.confidence:.2f})")
            
        # 2. 映射为 JSON Schema (概率实体 -> 结构化定义)
        final_schema = map_to_json_schema(extracted_entities, schema_title="SalesAnalysisRequest")
        
        print(f"\n[Step 2] 生成的 JSON Schema:")
        print(json.dumps(final_schema, indent=2, ensure_ascii=False))
        
        # 3. 验证示例数据 (边界检查)
        print("\n[Step 3] 验证数据有效性:")
        valid_data = {
            "time_range": "2023-01-01 to 2023-12-31",
            "dimension": "region",
            "limit": 10,
            "chart_type": "bar"
        }
        is_valid = validate_instance_against_schema(valid_data, final_schema)
        print(f"数据校验结果: {'成功' if is_valid else '失败'}")
        
    except ValueError as ve:
        logger.error(f"处理失败: {ve}")
    except Exception as e:
        logger.exception(f"系统异常: {e}")