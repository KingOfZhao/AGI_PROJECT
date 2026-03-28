"""
模块名称: auto_非结构化文本中的隐性意图提取与结构化_针_a697c0
描述: 本模块旨在利用大语言模型（LLM）从非结构化、口语化的教学文本（特别是工匠技艺传授场景）
      中提取隐性意图，并将其转化为结构化的 <状态, 动作, 预期效果> 三元组。
      
      核心挑战在于解决自然语言的歧义性（如"感觉有点..."）与物理操作精确性之间的映射冲突。
      通过上下文语境推断和结构化数据验证，实现高鲁棒性的意图识别。

依赖:
    - pydantic: 用于数据验证和结构化
    - logging: 标准日志库
    - json: 数据处理
    - typing: 类型注解
"""

import json
import logging
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError, field_validator

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- 数据模型 ---

class CraftOperation(BaseModel):
    """
    单个工匠操作的实体类。
    对应三元组：<状态, 动作, 预期效果>
    """
    observed_state: str = Field(
        ...,
        description="当前观察到的状态或问题，通常来自感官反馈（如视觉、触觉）。",
        min_length=1
    )
    action: str = Field(
        ...,
        description="建议执行的具体物理动作或调整。",
        min_length=1
    )
    expected_outcome: str = Field(
        ...,
        description="执行动作后预期的物理状态改变。",
        min_length=1
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="模型对该提取结果的置信度 (0.0-1.0)。"
    )

    @field_validator('observed_state', 'action', 'expected_outcome')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class SkillOutput(BaseModel):
    """
    技能执行的最终输出结构。
    """
    source_text: str
    extracted_intents: List[CraftOperation]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- 辅助函数 ---

def _build_extraction_prompt(text: str) -> str:
    """
    构建发送给大语言模型的提示词。
    利用少样本学习引导模型理解工匠语境。
    
    Args:
        text (str): 原始的非结构化文本。
        
    Returns:
        str: 构建好的完整Prompt。
    """
    prompt = f"""
你是一位拥有丰富经验的工匠技艺解析专家。你的任务是从非结构化的、口语化的教学文本中提取隐性意图。
请将文本解析为结构化的JSON对象列表。每个对象包含三个字段：
1. "observed_state": 触发该操作的当前状态（通常是感官描述，如"泥硬"、"声音脆"）。
2. "action": 具体的操作指令（如"加水"、"轻敲"）。
3. "expected_outcome": 该动作旨在达到的物理效果（如"增加可塑性"、"消除气泡"）。

示例输入: "这木头感觉有点涩，推不动，稍微打点蜡或者用砂纸蹭两下，就顺滑了。"
示例输出: 
[
    {{
        "observed_state": "木头表面感觉涩，推不动",
        "action": "打蜡或用砂纸打磨",
        "expected_outcome": "表面变得顺滑，易于推动"
    }}
]

当前需要解析的文本:
"{text}"

请仅输出符合JSON格式的列表，不要包含Markdown标记或其他解释性文字。
"""
    return prompt


def _simulate_llm_response(prompt: str) -> str:
    """
    模拟大语言模型 (LLM) 的调用。
    在实际生产环境中，此处应替换为调用 OpenAI/Claude/Llama 的 API 代码。
    为了保证代码可运行，此处基于简单的关键词匹配返回模拟的 JSON 数据。
    
    Args:
        prompt (str): 输入的提示词。
        
    Returns:
        str: 模拟的 JSON 字符串响应。
    """
    logger.info("正在调用大模型进行意图提取...")
    
    # 模拟延迟或网络请求
    import time
    time.sleep(0.1)
    
    # 简单的模拟逻辑，用于演示
    if "泥" in prompt and "硬" in prompt:
        return json.dumps([{
            "observed_state": "泥土触感过硬",
            "action": "添加适量的水",
            "expected_outcome": "泥土软化，达到合适的塑性状态",
            "confidence": 0.95
        }])
    elif "火候" in prompt:
        return json.dumps([{
            "observed_state": "炉温过高，有烧焦风险",
            "action": "降低风门开度或添加冷煤",
            "expected_outcome": "炉温降低，维持还原气氛",
            "confidence": 0.88
        }])
    else:
        # 默认返回空列表或根据具体逻辑处理
        return json.dumps([])


def _clean_llm_output(raw_response: str) -> str:
    """
    清理大模型返回的原始字符串，移除可能的 Markdown 标记。
    
    Args:
        raw_response (str): 原始响应字符串。
        
    Returns:
        str: 清理后的 JSON 字符串。
    """
    # 移除常见的 Markdown 代码块标记
    cleaned = raw_response.strip()
    if cleaned.startswith("