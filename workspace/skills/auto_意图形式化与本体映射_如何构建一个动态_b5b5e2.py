"""
模块名称: auto_意图形式化与本体映射_如何构建一个动态_b5b5e2
描述: 本模块实现了一个动态本体映射器，用于将高维、模糊的人类自然语言意图
     （如'做一个好用的后台'）实时转化为低维、结构化的中间表示（IR）。
     它通过预定义的本体规则和语义消歧机制，解决自然语言中的省略、歧义和多义性问题。
作者: AGI System Core Engineer
版本: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class IntentCategory(Enum):
    """意图类别的枚举定义"""
    DEVELOPMENT = "development"
    DATA_QUERY = "data_query"
    SYSTEM_CONFIG = "system_config"
    UNKNOWN = "unknown"

@dataclass
class OntologyConcept:
    """本体概念定义"""
    name: str
    synonyms: List[str]
    attributes: Dict[str, str]
    related_concepts: List[str]

@dataclass
class FormalizedIR:
    """
    形式化后的中间表示
    """
    original_text: str
    primary_intent: str
    category: IntentCategory
    entities: List[str]
    constraints: Dict[str, Any]
    confidence: float

@dataclass
class DynamicOntology:
    """
    动态本体数据库
    """
    concepts: Dict[str, OntologyConcept] = field(default_factory=dict)

    def add_concept(self, concept: OntologyConcept) -> None:
        self.concepts[concept.name] = concept

# --- 辅助函数 ---

def preprocess_text(text: str) -> str:
    """
    对输入文本进行预处理：去除多余空格、标点符号标准化。
    
    Args:
        text (str): 原始输入文本。
        
    Returns:
        str: 清洗后的文本。
        
    Raises:
        ValueError: 如果输入不是字符串。
    """
    if not isinstance(text, str):
        logger.error("输入类型错误: 期望字符串")
        raise ValueError("Input must be a string")
    
    # 去除首尾空格
    cleaned = text.strip()
    # 简单的标点标准化（将中文标点转英文标点，去除干扰符）
    cleaned = re.sub(r'[，。！？、；：]', lambda m: {'，': ',', '。': '.', '！': '!', '？': '?', '、': ',', '；': ';', '：': ':'}[m.group()], cleaned)
    # 多空格压缩
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    logger.debug(f"预处理结果: {cleaned}")
    return cleaned

# --- 核心类与函数 ---

class DynamicOntologyMapper:
    """
    动态本体映射器。
    负责加载本体知识，将自然语言映射到结构化IR。
    """
    
    def __init__(self):
        """初始化映射器，构建默认知识库"""
        self.ontology = DynamicOntology()
        self._initialize_default_ontology()
        logger.info("DynamicOntologyMapper 初始化完成")

    def _initialize_default_ontology(self) -> None:
        """初始化一些内置的本体概念，用于演示"""
        # 概念：后台管理系统
        backend_concept = OntologyConcept(
            name="BackendSystem",
            synonyms=["后台", "管理系统", "admin", "panel"],
            attributes={"type": "software", "tech_stack": "unknown"},
            related_concepts=["UserMgmt", "DataDashboard"]
        )
        # 概念：易用性
        usability_concept = OntologyConcept(
            name="Usability",
            synonyms=["好用", "便捷", "易操作", "user-friendly"],
            attributes={"metric": "ux_score"},
            related_concepts=["UI", "UX"]
        )
        
        self.ontology.add_concept(backend_concept)
        self.ontology.add_concept(usability_concept)

    def resolve_intent_ambiguity(self, text: str, context: Optional[Dict] = None) -> FormalizedIR:
        """
        [核心函数 1]
        解析自然语言文本，消歧并映射到本体结构，生成IR。
        
        Args:
            text (str): 输入的自然语言意图。
            context (Optional[Dict]): 上下文信息（如用户历史），用于消歧。
            
        Returns:
            FormalizedIR: 结构化的中间表示。
        """
        cleaned_text = preprocess_text(text)
        
        # 1. 实体识别与映射
        detected_entities = []
        matched_concepts = {}
        
        for key, concept in self.ontology.concepts.items():
            # 检查概念名称或同义词是否在文本中出现
            all_terms = set(concept.synonyms + [concept.name])
            for term in all_terms:
                if term in cleaned_text:
                    detected_entities.append(key)
                    matched_concepts[key] = term
                    logger.info(f"匹配到本体概念: {key} (词项: {term})")
                    break # 一个概念只匹配一次

        # 2. 意图分类 (简单的基于关键词的模拟)
        category = IntentCategory.UNKNOWN
        if "BackendSystem" in detected_entities:
            category = IntentCategory.DEVELOPMENT
        elif "DataDashboard" in detected_entities:
            category = IntentCategory.DATA_QUERY

        # 3. 约束提取 (简单的正则模拟)
        constraints = {}
        if "Usability" in detected_entities:
            constraints["ux_level"] = "high"
        
        # 4. 生成IR
        ir = FormalizedIR(
            original_text=text,
            primary_intent=matched_concepts.get(next(iter(detected_entities)), "generic_action") if detected_entities else "unknown",
            category=category,
            entities=detected_entities,
            constraints=constraints,
            confidence=0.85 if detected_entities else 0.1
        )
        
        return ir

    def map_to_logic_structure(self, ir: FormalizedIR) -> Dict[str, Any]:
        """
        [核心函数 2]
        将IR进一步转化为无歧义的逻辑结构（类似于JSON Schema或简单的DSL）。
        
        Args:
            ir (FormalizedIR): 输入的中间表示。
            
        Returns:
            Dict[str, Any]: 可执行的逻辑结构字典。
        """
        if ir.confidence < 0.5:
            logger.warning(f"IR置信度过低 ({ir.confidence})，逻辑结构可能不准确")

        logic_structure = {
            "action_type": "CREATE_OR_MODIFY",
            "target_object": None,
            "parameters": [],
            "metadata": {
                "source": "DynamicOntologyMapper",
                "confidence": ir.confidence
            }
        }

        # 根据识别出的实体构建结构
        if "BackendSystem" in ir.entities:
            logic_structure["target_object"] = "SoftwareModule::Backend"
            logic_structure["parameters"].append({
                "key": "module_type",
                "value": "admin_panel"
            })
        
        if "Usability" in ir.entities:
             logic_structure["parameters"].append({
                "key": "quality_attribute",
                "value": "high_usability",
                "validation_rules": ["ui_check", "accessibility_check"]
            })

        # 默认值处理
        if not logic_structure["target_object"]:
            logic_structure["target_object"] = "GenericTask"
            
        logger.info(f"生成逻辑结构: {logic_structure}")
        return logic_structure

# --- 使用示例 ---

if __name__ == "__main__":
    # 示例用法
    mapper = DynamicOntologyMapper()
    
    user_input = "做一个好用的后台"
    
    try:
        # 步骤 1: 意图解析与形式化
        formalized_ir = mapper.resolve_intent_ambiguity(user_input)
        print(f"--- 中间表示
        print(f"原始文本: {formalized_ir.original_text}")
        print(f"意图类别: {formalized_ir.category.value}")
        print(f"识别实体: {formalized_ir.entities}")
        
        # 步骤 2: 映射到逻辑结构
        logic_json = mapper.map_to_logic_structure(formalized_ir)
        print(f"\n--- 逻辑结构
        print(logic_json)
        
    except ValueError as ve:
        logger.error(f"参数验证失败: {ve}")
    except Exception as e:
        logger.critical(f"系统运行时错误: {e}", exc_info=True)