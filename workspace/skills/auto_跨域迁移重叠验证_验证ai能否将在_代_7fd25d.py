"""
Module: auto_cross_domain_isomorphism_validator.py
Description: 【跨域迁移重叠验证】验证AI能否将在‘代码优化’领域中的‘重构’节点，迁移应用到‘文学写作’领域的‘文章精简’任务中。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationType(Enum):
    """定义同构操作的类型"""
    REDUNDANCY_REMOVAL = "redundancy_removal"
    LOGIC_PRESERVATION = "logic_preservation"
    STRUCTURE_SIMPLIFICATION = "structure_simplification"
    VARIABLE_RENAMING = "variable_renaming"  # 对应文学中的词汇润色


@dataclass
class DomainContext:
    """领域上下文数据结构"""
    domain_name: str
    task_name: str
    core_intent: str
    constraints: List[str] = field(default_factory=list)


@dataclass
class OperationGuide:
    """跨域操作指南数据结构"""
    source_concept: str
    target_concept: str
    isomorphic_rationale: str
    transferability_score: float  # 0.0 to 1.0
    steps: List[str] = field(default_factory=list)


def validate_input_data(data: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    辅助函数：验证输入数据是否包含必需的键。
    
    Args:
        data (Dict[str, Any]): 待验证的字典数据。
        required_keys (List[str]): 必须存在的键列表。
        
    Returns:
        bool: 如果验证通过返回True，否则抛出ValueError。
        
    Raises:
        ValueError: 当缺少必要字段或数据类型错误时。
    """
    if not isinstance(data, dict):
        logger.error("Input data must be a dictionary.")
        raise ValueError("Input data must be a dictionary.")
        
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        logger.error(f"Missing required keys: {missing_keys}")
        raise ValueError(f"Missing required keys: {missing_keys}")
    
    logger.debug("Input data validation passed.")
    return True


def extract_isomorphic_structure(source_context: DomainContext, target_context: DomainContext) -> Dict[OperationType, str]:
    """
    核心函数1：识别并提取源领域（代码重构）与目标领域（文章精简）之间的同构结构。
    
    此函数模拟AGI认知核心，通过比对核心意图来映射操作。
    
    Args:
        source_context (DomainContext): 源领域上下文（如代码重构）。
        target_context (DomainContext): 目标领域上下文（如文章精简）。
        
    Returns:
        Dict[OperationType, str]: 映射字典，描述源操作如何对应到目标操作。
    """
    logger.info(f"Analyzing isomorphism between {source_context.domain_name} and {target_context.domain_name}")
    
    mapping = {}
    
    # 模拟认知映射逻辑：检测意图重叠
    if "simplify" in source_context.core_intent.lower() and "conciseness" in target_context.core_intent.lower():
        mapping[OperationType.REDUNDANCY_REMOVAL] = (
            "Code 'Dead Code Elimination' maps to Text 'Redundant Phrase Removal'"
        )
        
    if "logic" in source_context.core_intent.lower() or "semantics" in target_context.core_intent.lower():
        mapping[OperationType.LOGIC_PRESERVATION] = (
            "Code 'Refactoring Pre/Post Conditions' maps to Text 'Meaning Preservation Constraints'"
        )
        
    if "structure" in source_context.core_intent.lower():
         mapping[OperationType.STRUCTURE_SIMPLIFICATION] = (
            "Code 'Loop Unrolling' maps to Text 'Sentence Splitting/Combining'"
        )

    if not mapping:
        logger.warning("No significant isomorphic structures found.")
    else:
        logger.info(f"Found {len(mapping)} isomorphic mappings.")
        
    return mapping


def generate_cross_domain_guide(
    source_domain: str,
    source_task: str,
    target_domain: str, 
    target_task: str,
    mappings: Dict[OperationType, str]
) -> OperationGuide:
    """
    核心函数2：基于同构性分析，生成具体的跨域操作指南。
    
    Args:
        source_domain (str): 源领域名称。
        source_task (str): 源任务名称。
        target_domain (str): 目标领域名称。
        target_task (str): 目标任务名称。
        mappings (Dict[OperationType, str]): 来自提取函数的映射关系。
        
    Returns:
        OperationGuide: 包含具体迁移步骤的操作指南对象。
    """
    logger.info("Generating Cross-Domain Operation Guide...")
    
    # 基础检查
    if not mappings:
        raise ValueError("Cannot generate guide without isomorphic mappings.")

    steps = []
    score = 0.0
    
    # 生成具体的迁移步骤
    if OperationType.REDUNDANCY_REMOVAL in mappings:
        steps.append(
            "1. [Import from Coding] Apply 'Dead Code Elimination' logic: "
            "Identify paragraphs or sentences that do not contribute to the central theme (dead logic)."
        )
        score += 0.4
        
    if OperationType.LOGIC_PRESERVATION in mappings:
        steps.append(
            "2. [Import from Coding] Apply 'Unit Testing' concept: "
            "Before simplifying, extract the core semantic propositions (assertions) to ensure they remain true after editing."
        )
        steps.append(
            "3. [Import from Coding] Apply 'Regression Check': "
            "Verify that the tone and intent of the text remain unchanged."
        )
        score += 0.3
        
    if OperationType.STRUCTURE_SIMPLIFICATION in mappings:
        steps.append(
            "4. [Import from Coding] Apply 'Extract Method': "
            "Replace repetitive descriptions with a single, strong noun or metaphor (function call)."
        )
        score += 0.2

    # 边界检查：分数归一化
    final_score = min(max(score, 0.0), 1.0)
    
    rationale = (
        f"Both '{source_task}' and '{target_task}' aim to increase information density "
        f"while maintaining functional/semantic correctness."
    )
    
    guide = OperationGuide(
        source_concept=f"{source_domain}::{source_task}",
        target_concept=f"{target_domain}::{target_task}",
        isomorphic_rationale=rationale,
        transferability_score=final_score,
        steps=steps
    )
    
    logger.info(f"Guide generated successfully with score: {final_score}")
    return guide


def run_validation_process(config: Dict[str, Any]) -> Optional[OperationGuide]:
    """
    执行完整的验证流程：输入验证 -> 同构提取 -> 指南生成 -> 结果输出。
    
    Args:
        config (Dict[str, Any]): 包含源领域和目标领域配置的字典。
        
    Returns:
        Optional[OperationGuide]: 生成的操作指南，如果失败则返回None。
        
    Example:
        >>> config = {
        ...     "source": {"domain": "Software", "task": "Refactoring", "intent": "Optimize structure"},
        ...     "target": {"domain": "Literature", "task": "Simplification", "intent": "Reduce word count"}
        ... }
        >>> guide = run_validation_process(config)
    """
    try:
        # 1. 数据验证
        logger.info("Starting validation process...")
        validate_input_data(config, ["source", "target"])
        validate_input_data(config["source"], ["domain", "task", "intent"])
        validate_input_data(config["target"], ["domain", "task", "intent"])
        
        # 2. 构建上下文对象
        src_ctx = DomainContext(
            domain_name=config["source"]["domain"],
            task_name=config["source"]["task"],
            core_intent=config["source"]["intent"]
        )
        
        tgt_ctx = DomainContext(
            domain_name=config["target"]["domain"],
            task_name=config["target"]["task"],
            core_intent=config["target"]["intent"]
        )
        
        # 3. 执行同构分析
        mappings = extract_isomorphic_structure(src_ctx, tgt_ctx)
        
        if not mappings:
            logger.warning("Validation Failed: No transferable skills found.")
            return None
            
        # 4. 生成指南
        guide = generate_cross_domain_guide(
            source_domain=src_ctx.domain_name,
            source_task=src_ctx.task_name,
            target_domain=tgt_ctx.domain_name,
            target_task=tgt_ctx.task_name,
            mappings=mappings
        )
        
        return guide

    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
        return None
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)
        return None


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 模拟AGI系统的输入配置
    test_config = {
        "source": {
            "domain": "Code Optimization",
            "task": "Refactoring",
            "intent": "Improving code structure and reducing redundancy while preserving logic (Dead Code Elimination)"
        },
        "target": {
            "domain": "Literature Writing",
            "task": "Article Simplification",
            "intent": "Reducing word count and removing fluff while preserving core meaning (Conciseness)"
        }
    }

    print("--- Starting Cross-Domain Migration Validation ---")
    
    result_guide = run_validation_process(test_config)
    
    if result_guide:
        print("\n=== Operation Guide Generated ===")
        print(f"Source: {result_guide.source_concept}")
        print(f"Target: {result_guide.target_concept}")
        print(f"Score: {result_guide.transferability_score}")
        print("Rationale:")
        print(result_guide.isomorphic_rationale)
        print("\nActionable Steps:")
        for step in result_guide.steps:
            print(f"- {step}")
            
        # 输出JSON格式以模拟API返回
        print("\n--- JSON Output ---")
        print(json.dumps(asdict(result_guide), indent=2))
    else:
        print("Process failed to generate a guide.")