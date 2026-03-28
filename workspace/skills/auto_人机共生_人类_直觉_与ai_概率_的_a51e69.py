"""
模块: intuitive_probabilistic_conflict_resolver
版本: 1.0.0
描述: 【人机共生】人类'直觉'与AI'概率'的冲突解决协议。

在人机协作场景中，AI基于历史数据生成高概率建议（如“降价促销”），
而人类专家基于隐性知识或直觉提出反对（如“损害品牌形象”）。
本模块不解决“谁对谁错”的问题，而是提供一种“元数据标记”机制，
将人类的直觉反对转化为结构化的“潜在未知变量”或“价值约束”，
并将其固化为系统中的新节点，从而实现系统的持续进化。

核心功能:
1. 冲突检测: 识别显性反对。
2. 直觉编码: 将非结构化反对意见转化为结构化约束。
3. 节点固化: 将冲突作为新特征或规则注入上下文。

Author: AGI System Core Team
"""

import logging
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- 数据结构定义 ---

class ConflictType(Enum):
    """定义冲突的类型枚举。"""
    UNKNOWN_VARIABLE = "potential_unknown_variable"  # 潜在未知变量（如市场情绪）
    VALUE_CONSTRAINT = "value_constraint"            # 价值约束（如品牌声誉、道德底线）
    DATA_SKEW = "data_skew"                         # 数据偏差（如历史数据失效）
    RISK_AVERSION = "risk_aversion"                  # 风险厌恶


class ProposalCategory(Enum):
    """AI建议的类别枚举。"""
    PRICING = "pricing"
    CONTENT_GENERATION = "content_gen"
    STRATEGY = "strategy"


@dataclass
class AIProposal:
    """AI提出的建议数据结构。"""
    proposal_id: str
    category: ProposalCategory
    action: str
    probability: float  # 0.0 到 1.0
    reasoning_data: Dict[str, Any]  # 支持建议的数据


@dataclass
class HumanObjection:
    """人类提出的反对意见数据结构。"""
    user_id: str
    reason_text: str
    intensity: float  # 0.0 到 1.0，表示反对的强烈程度


@dataclass
class ResolvedConflictNode:
    """解决冲突后生成的新节点数据结构。"""
    node_id: str
    source_conflict_type: ConflictType
    label: str
    description: str
    weight: float  # 该新节点在决策中的权重
    created_at: str
    metadata: Dict[str, Any]


class IntuitionFormatError(Exception):
    """自定义异常：直觉输入格式错误。"""
    pass


class ProposalValidationError(Exception):
    """自定义异常：建议验证失败。"""
    pass


# --- 核心函数 ---

def classify_intuition(
    proposal: AIProposal,
    objection: HumanObjection,
    context_tags: Optional[List[str]] = None
) -> ConflictType:
    """
    根据建议和反对意见的内容，通过启发式规则或NLP接口对直觉进行分类。
    
    这是一个核心认知函数，用于判断人类的直觉到底属于哪一种元数据类型。
    
    Args:
        proposal (AIProposal): AI的原始建议对象。
        objection (HumanObjection): 人类的反对意见对象。
        context_tags (Optional[List[str]]): 额外的上下文标签。
        
    Returns:
        ConflictType: 识别出的冲突类型枚举值。
        
    Raises:
        IntuitionFormatError: 如果输入文本为空或无效。
    """
    if not objection.reason_text.strip():
        logger.error("Empty objection reason provided.")
        raise IntuitionFormatError("Objection reason cannot be empty.")
    
    logger.info(f"Classifying intuition for proposal {proposal.proposal_id}...")
    
    text = objection.reason_text.lower()
    
    # 启发式规则映射表 (实际AGI场景中可能调用LLM进行分类)
    # 这里模拟了AGI理解人类语义的过程
    keyword_mapping = {
        ConflictType.VALUE_CONSTRAINT: ["品牌", "道德", "声誉", "形象", "底线", "价值观"],
        ConflictType.UNKNOWN_VARIABLE: ["直觉", "感觉", "预感", "潜在", "未知", "隐患"],
        ConflictType.RISK_AVERSION: ["风险", "不安全", "损失", "万一", "谨慎"],
        ConflictType.DATA_SKEW: ["过时", "偏差", "不准", "环境变了", "特例"]
    }
    
    # 简单的关键词匹配逻辑
    detected_type = ConflictType.UNKNOWN_VARIABLE # Default
    
    for conflict_type, keywords in keyword_mapping.items():
        if any(keyword in text for keyword in keywords):
            detected_type = conflict_type
            break
            
    logger.info(f"Intuition classified as: {detected_type.value}")
    return detected_type


def synthesize_conflict_node(
    proposal: AIProposal,
    objection: HumanObjection,
    conflict_type: ConflictType
) -> ResolvedConflictNode:
    """
    将识别出的冲突类型和原始反对意见综合为一个系统可理解的“固化节点”。
    
    该节点不再是简单的拒绝，而是变成了决策树中的一个新维度。
    
    Args:
        proposal (AIProposal): 原始AI建议。
        objection (HumanObjection): 人类反对意见。
        conflict_type (ConflictType): 识别出的冲突类型。
        
    Returns:
        ResolvedConflictNode: 包含元数据的新决策节点。
    """
    node_id = f"node-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.utcnow().isoformat()
    
    # 计算权重：人类反对越强烈，该节点的权重越高，越能抑制原始概率
    # 基础权重 + 强度修正
    base_weight = 0.5
    intensity_modifier = objection.intensity * 0.4
    final_weight = min(1.0, base_weight + intensity_modifier)
    
    # 生成描述
    description = (
        f"Human constraint on {proposal.category.value}: '{objection.reason_text}'. "
        f"Classified as {conflict_type.value}. "
        f"Original AI probability {proposal.probability} adjusted by factor {final_weight}."
    )
    
    # 构建元数据
    metadata = {
        "original_proposal_id": proposal.proposal_id,
        "intensity_score": objection.intensity,
        "heuristic_match": conflict_type.value
    }
    
    new_node = ResolvedConflictNode(
        node_id=node_id,
        source_conflict_type=conflict_type,
        label=f"Constraint:{conflict_type.value}",
        description=description,
        weight=final_weight,
        created_at=timestamp,
        metadata=metadata
    )
    
    logger.info(f"Synthesized new conflict node: {node_id} with weight {final_weight:.2f}")
    return new_node


# --- 辅助函数 ---

def validate_inputs(proposal: AIProposal, objection: HumanObjection) -> bool:
    """
    验证输入数据的完整性和边界条件。
    
    Args:
        proposal: AI建议对象。
        objection: 人类反对意见对象。
        
    Returns:
        bool: 验证通过返回True。
        
    Raises:
        ProposalValidationError: 如果概率或强度超出范围。
        IntuitionFormatError: 如果文本字段无效。
    """
    if not (0.0 <= proposal.probability <= 1.0):
        raise ProposalValidationError(f"AI probability {proposal.probability} out of range [0, 1].")
    
    if not (0.0 <= objection.intensity <= 1.0):
        raise ProposalValidationError(f"Human intensity {objection.intensity} out of range [0, 1].")
        
    if len(objection.reason_text) < 2:
        raise IntuitionFormatError("Objection reason is too short for semantic analysis.")
        
    logger.debug("Input validation passed.")
    return True


def adjust_proposal_probability(
    original_prob: float,
    constraint_node: ResolvedConflictNode
) -> float:
    """
    根据新生成的约束节点，调整原始建议的最终执行概率。
    这是一个简单的示例，展示了冲突如何影响决策。
    
    Args:
        original_prob (float): 原始概率。
        constraint_node (ResolvedConflictNode): 包含权重的约束节点。
        
    Returns:
        float: 调整后的概率。
    """
    # 如果是价值约束，且权重很高，可能直接一票否决（概率降为0）
    # 如果是未知变量，则降低概率，但不完全否决
    if constraint_node.source_conflict_type == ConflictType.VALUE_CONSTRAINT:
        if constraint_node.weight > 0.8:
            logger.warning("Hard constraint detected. Probability set to near zero.")
            return 0.05
    
    # 一般调整：概率 = 原始概率 * (1 - 约束权重)
    adjusted_prob = original_prob * (1.0 - constraint_node.weight)
    return max(0.0, min(1.0, adjusted_prob))


# --- 主逻辑与示例 ---

def resolve_human_ai_conflict(
    proposal: Dict[str, Any],
    objection: Dict[str, Any]
) -> Dict[str, Any]:
    """
    对外暴露的主接口，处理完整的冲突解决流程。
    
    Input Format:
        proposal: {
            "id": "prop-001", "cat": "pricing", "action": "cut_20%",
            "prob": 0.92, "data": {"sales_boost": "15%"}
        }
        objection: {
            "user": "manager_A", "text": "这会伤害我们的品牌形象",
            "intensity": 0.9
        }
        
    Output Format:
        {
            "status": "resolved",
            "new_node": { ... }, # ResolvedConflictNode dict
            "adjusted_probability": 0.15
        }
    """
    try:
        # 1. 数据转换与验证
        ai_proposal = AIProposal(
            proposal_id=proposal.get('id'),
            category=ProposalCategory(proposal.get('cat')),
            action=proposal.get('action'),
            probability=proposal.get('prob'),
            reasoning_data=proposal.get('data', {})
        )
        
        human_obj = HumanObjection(
            user_id=objection.get('user'),
            reason_text=objection.get('text'),
            intensity=objection.get('intensity')
        )
        
        validate_inputs(ai_proposal, human_obj)
        
        # 2. 认知分类 (分类直觉)
        conflict_type = classify_intuition(ai_proposal, human_obj)
        
        # 3. 节点固化 (生成元数据)
        new_node = synthesize_conflict_node(ai_proposal, human_obj, conflict_type)
        
        # 4. 决策调整
        final_prob = adjust_proposal_probability(ai_proposal.probability, new_node)
        
        return {
            "status": "resolved",
            "new_node": asdict(new_node),
            "adjusted_probability": final_prob,
            "message": "Intuition integrated into system as a constraint node."
        }
        
    except Exception as e:
        logger.exception("Failed to resolve conflict.")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # --- 使用示例 ---
    
    # 模拟输入数据
    sample_proposal = {
        "id": "prop-2023-10-27-01",
        "cat": "pricing",
        "action": "Decrease price by 15%",
        "prob": 0.85,
        "data": {"historical_sales_increase": 1.2}
    }
    
    sample_objection = {
        "user": "product_lead_01",
        "text": "我觉得这会有损我们的高端品牌形象，虽然数据支持降价。",
        "intensity": 0.8
    }
    
    print("--- Starting Conflict Resolution Protocol ---")
    result = resolve_human_ai_conflict(sample_proposal, sample_objection)
    
    print("\nResolution Result:")
    print(json.dumps(result, indent=2, default=str))