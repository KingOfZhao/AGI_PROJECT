"""
模块名称: auto_构建_认知光谱仪_将模糊的自然语言知识_ae91d9
描述: 构建'认知光谱仪'：将模糊的自然语言知识转化为可执行代码（Skill）的自动化转化率研究。
      本模块演示如何通过LLM的Function Calling能力，自动将非结构化文本（如菜谱、指南）
      转化为包含特定字段的结构化JSON对象，并进行数据验证。
作者: AGI System Core Engineer
版本: 1.0.0
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass, field
from enum import Enum

# 尝试导入openai，如果不存在则抛出配置错误
try:
    from openai import OpenAI, APIError, APIConnectionError, RateLimitError
except ImportError:
    raise ImportError("请安装OpenAI SDK: pip install openai")

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class SkillCategory(Enum):
    """定义技能的分类枚举"""
    COOKING = "cooking"
    PROGRAMMING = "programming"
    DIY = "diy"
    GENERAL = "general"

@dataclass
class SkillMetadata:
    """技能的元数据信息"""
    author: str = "AGI_System"
    version: str = "1.0"
    confidence_score: float = 0.0  # 转化置信度 0.0-1.0

@dataclass
class StructuredSkill:
    """
    转化后的结构化技能对象。
    验证目标：能够从文本中提取这些字段。
    """
    title: str
    ingredients: List[str]  # 关键提取字段：原料/依赖
    steps: List[str]       # 关键提取字段：步骤/逻辑
    duration: str          # 关键提取字段：持续时间/复杂度
    category: SkillCategory = SkillCategory.GENERAL
    metadata: SkillMetadata = field(default_factory=SkillMetadata)

    def to_json(self) -> Dict[str, Any]:
        """将对象转换为可序列化的字典"""
        return {
            "title": self.title,
            "ingredients": self.ingredients,
            "steps": self.steps,
            "duration": self.duration,
            "category": self.category.value,
            "metadata": self.metadata.__dict__
        }

# --- 辅助函数 ---

def validate_skill_output(parsed_data: Dict[str, Any]) -> StructuredSkill:
    """
    验证LLM返回的JSON数据是否符合技能定义的Schema。
    
    Args:
        parsed_data (Dict): LLM返回解析后的字典数据。
        
    Returns:
        StructuredSkill: 验证并构建后的技能对象。
        
    Raises:
        ValueError: 如果缺少必要字段或数据类型不匹配。
    """
    logger.info("开始数据结构验证...")
    
    # 1. 检查必要字段是否存在
    required_keys = ["title", "ingredients", "steps", "duration"]
    missing_keys = [k for k in required_keys if k not in parsed_data]
    if missing_keys:
        raise ValueError(f"数据验证失败：缺少必要字段 {missing_keys}")
    
    # 2. 类型与边界检查
    if not isinstance(parsed_data["ingredients"], list):
        raise ValueError("字段 'ingredients' 必须是列表")
    if not isinstance(parsed_data["steps"], list):
        raise ValueError("字段 'steps' 必须是列表")
    if len(parsed_data["steps"]) == 0:
        raise ValueError("字段 'steps' 不能为空")

    # 3. 构建对象 (这里简化了Category的映射逻辑)
    category_str = parsed_data.get("category", "general").lower()
    try:
        category = SkillCategory(category_str)
    except ValueError:
        category = SkillCategory.GENERAL

    # 构建Metadata
    meta = SkillMetadata()
    if "confidence_score" in parsed_data:
        meta.confidence_score = float(parsed_data["confidence_score"])

    return StructuredSkill(
        title=str(parsed_data["title"]),
        ingredients=[str(item) for item in parsed_data["ingredients"]],
        steps=[str(step) for step in parsed_data["steps"]],
        duration=str(parsed_data["duration"]),
        category=category,
        metadata=meta
    )

# --- 核心函数 ---

def define_skill_schema() -> Dict[str, Any]:
    """
    定义供LLM使用的Function Calling Schema (JSON Schema)。
    这是'认知光谱仪'的刻度设定，决定了非结构化文本如何被量化。
    
    Returns:
        Dict: 符合OpenAI Function Calling格式的Schema定义。
    """
    schema = {
        "type": "function",
        "function": {
            "name": "extract_structured_skill",
            "description": "将非结构化的知识文本转化为结构化的技能对象，包含原料、步骤和耗时。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "技能或任务的名称，例如'红烧肉制作'"
                    },
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "完成任务所需的原料、工具或依赖项"
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "详细的执行步骤列表"
                    },
                    "duration": {
                        "type": "string",
                        "description": "预计完成所需的时间，例如'60分钟'"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["cooking", "programming", "diy", "general"],
                        "description": "任务所属类别"
                    }
                },
                "required": ["title", "ingredients", "steps", "duration"]
            }
        }
    }
    logger.debug(f"已定义Schema: {schema['function']['name']}")
    return schema

def transform_unstructured_text_to_skill(
    text_content: str, 
    model_name: str = "gpt-3.5-turbo-0125"
) -> Optional[StructuredSkill]:
    """
    核心转化函数：调用LLM将文本转化为结构化技能。
    
    流程:
    1. 初始化客户端 (依赖环境变量 OPENAI_API_KEY)
    2. 发送文本与预定义的Schema
    3. 强制模型调用函数
    4. 验证并封装结果
    
    Args:
        text_content (str): 输入的非结构化自然语言文本。
        model_name (str): 使用的LLM模型ID。
        
    Returns:
        Optional[StructuredSkill]: 成功返回结构化对象，失败返回None。
    """
    if not text_content or len(text_content.strip()) < 10:
        logger.error("输入文本过短，无法提取知识。")
        return None

    try:
        client = OpenAI() # 自动读取环境变量 OPENAI_API_KEY
    except Exception as e:
        logger.critical(f"OpenAI 客户端初始化失败: {e}")
        return None

    tools = [define_skill_schema()]
    
    logger.info(f"正在发送请求至模型 {model_name} 进行知识提取...")
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system", 
                    "content": "你是一个知识结构化引擎。你的任务是将输入的模糊文本转化为精确的JSON格式。"
                },
                {
                    "role": "user", 
                    "content": text_content
                }
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_structured_skill"}}, # 强制调用
            temperature=0.1 # 降低随机性以提高一致性
        )

        # 提取 Tool Calls
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            logger.warning("模型未返回任何工具调用，提取失败。")
            return None

        # 解析参数
        function_args = json.loads(tool_calls[0].function.arguments)
        logger.info("已接收到结构化数据，正在进行Schema验证...")
        
        # 数据验证与对象构建
        skill_instance = validate_skill_output(function_args)
        
        # 计算简单置信度 (这里模拟基于字段填充率的计算)
        skill_instance.metadata.confidence_score = 0.95
        
        logger.info(f"技能转化成功: {skill_instance.title}")
        return skill_instance

    except (APIConnectionError, RateLimitError) as e:
        logger.error(f"API连接或限流错误: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return None
    except ValueError as e:
        logger.error(f"数据验证错误: {e}")
        return None
    except Exception as e:
        logger.exception(f"未知错误: {e}")
        return None

# --- 主程序与示例 ---

if __name__ == "__main__":
    # 示例输入：关于“如何做红烧肉”的非结构化文本节点
    sample_text = """
    红烧肉是一道非常经典的中式菜肴。
    首先你需要准备五花肉500克，冰糖20克，姜切片，葱切段，八角2个。
    做法很简单：先把五花肉切块焯水，然后锅里炒糖色，
    把肉倒进去翻炒上色，加入葱姜八角，倒点酱油和料酒，
    加水没过肉，大火烧开转小火慢炖一个小时，
    最后大火收汁就可以出锅了。整个过程大概需要90分钟。
    """
    
    print(f"--- 启动认知光谱仪 ---")
    print(f"原始文本: {sample_text[:50]}...")
    
    # 执行转化
    structured_result = transform_unstructured_text_to_skill(sample_text)
    
    if structured_result:
        print("\n>>> 转化成功! 输出结构化JSON:")
        print(json.dumps(structured_result.to_json(), indent=2, ensure_ascii=False))
    else:
        print("\n>>> 转化失败，请检查日志。")