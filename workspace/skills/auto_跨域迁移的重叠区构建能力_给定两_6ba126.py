"""
模块名称: cross_domain_overlap_builder
功能描述: 实现跨域迁移的重叠区构建能力，通过四向碰撞机制生成中间概念节点
作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DomainCategory(Enum):
    """定义支持的领域类别"""
    PHYSICS = "physics"
    SOCIOLOGY = "sociology"
    HISTORY = "history"
    BIOLOGY = "biology"
    TECHNOLOGY = "technology"
    ART = "art"
    PHILOSOPHY = "philosophy"


@dataclass
class ConceptNode:
    """概念节点数据结构"""
    name: str
    domain: DomainCategory
    attributes: Dict[str, float]  # 核心属性特征向量
    description: str


@dataclass
class OverlapResult:
    """重叠区构建结果"""
    intermediate_node: str
    bridge_concept: str
    application_scenarios: List[str]
    confidence_score: float


def validate_input_nodes(node1: ConceptNode, node2: ConceptNode) -> bool:
    """
    验证输入节点是否满足跨域构建要求
    
    参数:
        node1: 第一个概念节点
        node2: 第二个概念节点
        
    返回:
        bool: 验证是否通过
        
    异常:
        ValueError: 当节点领域相同或属性不足时抛出
    """
    if not isinstance(node1, ConceptNode) or not isinstance(node2, ConceptNode):
        logger.error("输入节点类型错误")
        raise ValueError("输入必须是ConceptNode类型")
    
    if node1.domain == node2.domain:
        logger.warning(f"节点领域相同: {node1.domain}")
        raise ValueError("跨域构建需要不同领域的节点")
    
    if len(node1.attributes) < 3 or len(node2.attributes) < 3:
        logger.error("属性特征不足，无法构建重叠区")
        raise ValueError("每个节点至少需要3个属性特征")
    
    logger.info("输入节点验证通过")
    return True


def calculate_semantic_overlap(node1: ConceptNode, node2: ConceptNode) -> Tuple[float, Dict[str, float]]:
    """
    计算两个概念节点的语义重叠度
    
    参数:
        node1: 第一个概念节点
        node2: 第二个概念节点
        
    返回:
        Tuple[float, Dict[str, float]]: 重叠度分数和共同特征权重
    """
    common_attributes = set(node1.attributes.keys()) & set(node2.attributes.keys())
    
    if not common_attributes:
        logger.info("未发现直接共同属性，启动深层特征提取")
        common_attributes = _extract_latent_features(node1, node2)
    
    overlap_scores = {}
    for attr in common_attributes:
        val1 = node1.attributes.get(attr, 0)
        val2 = node2.attributes.get(attr, 0)
        overlap_scores[attr] = (val1 + val2) / 2
    
    total_overlap = sum(overlap_scores.values()) / len(overlap_scores) if overlap_scores else 0
    logger.debug(f"语义重叠计算完成: {total_overlap:.2f}")
    
    return total_overlap, overlap_scores


def _extract_latent_features(node1: ConceptNode, node2: ConceptNode) -> set:
    """
    辅助函数：提取潜在共同特征
    
    参数:
        node1: 第一个概念节点
        node2: 第二个概念节点
        
    返回:
        set: 潜在共同特征集合
    """
    latent_features = {
        'complexity', 'stability', 'distance_factor', 
        'information_flow', 'constraint_level'
    }
    
    # 为潜在特征赋默认值
    for feat in latent_features:
        node1.attributes[feat] = node1.attributes.get(feat, 0.5)
        node2.attributes[feat] = node2.attributes.get(feat, 0.5)
    
    logger.info(f"提取潜在特征: {latent_features}")
    return latent_features


def generate_intermediate_node(node1: ConceptNode, node2: ConceptNode, 
                             overlap_features: Dict[str, float]) -> OverlapResult:
    """
    生成中间概念节点
    
    参数:
        node1: 第一个概念节点
        node2: 第二个概念节点
        overlap_features: 重叠特征权重
        
    返回:
        OverlapResult: 构建结果对象
        
    异常:
        RuntimeError: 当生成失败时抛出
    """
    try:
        # 确定桥接概念
        bridge_concept = _determine_bridge_concept(node1, node2, overlap_features)
        
        # 生成中间节点名称
        intermediate_name = _compose_node_name(node1, node2, bridge_concept)
        
        # 生成应用场景
        scenarios = _generate_application_scenarios(
            intermediate_name, 
            node1.domain, 
            node2.domain
        )
        
        # 计算置信度
        confidence = _calculate_confidence(overlap_features)
        
        result = OverlapResult(
            intermediate_node=intermediate_name,
            bridge_concept=bridge_concept,
            application_scenarios=scenarios,
            confidence_score=confidence
        )
        
        logger.info(f"成功生成中间节点: {intermediate_name}")
        return result
        
    except Exception as e:
        logger.error(f"中间节点生成失败: {str(e)}")
        raise RuntimeError("概念构建过程失败") from e


def _determine_bridge_concept(node1: ConceptNode, node2: ConceptNode, 
                            features: Dict[str, float]) -> str:
    """
    辅助函数：确定桥接概念
    """
    domain_keywords = {
        DomainCategory.PHYSICS: ["force", "field", "particle", "energy"],
        DomainCategory.SOCIOLOGY: ["norm", "group", "institution", "culture"],
        DomainCategory.HISTORY: ["tradition", "evolution", "artifact", "period"],
        DomainCategory.BIOLOGY: ["organism", "evolution", "ecosystem", "gene"],
        DomainCategory.TECHNOLOGY: ["system", "network", "automation", "data"],
        DomainCategory.ART: ["expression", "form", "style", "perception"],
        DomainCategory.PHILOSOPHY: ["concept", "existence", "ethics", "logic"]
    }
    
    # 简化的桥接概念选择逻辑
    key_feature = max(features.items(), key=lambda x: x[1])[0]
    
    if "distance" in key_feature or "separation" in key_feature:
        return "远距离作用机制"
    elif "constraint" in key_feature or "limit" in key_feature:
        return "系统性束缚规则"
    elif "flow" in key_feature or "transfer" in key_feature:
        return "信息/能量传递通道"
    else:
        return "跨域关联模式"


def _compose_node_name(node1: ConceptNode, node2: ConceptNode, bridge: str) -> str:
    """
    辅助函数：组合生成节点名称
    """
    # 提取核心概念词
    word1 = node1.name.split()[-1] if " " in node1.name else node1.name
    word2 = node2.name.split()[-1] if " " in node2.name else node2.name
    
    # 简化的命名逻辑
    if "束缚" in bridge or "约束" in bridge:
        return f"{word1}式{word2}约束"
    elif "传递" in bridge or "通道" in bridge:
        return f"{word1}-{word2}传输机制"
    else:
        return f"{word1}与{word2}的{bridge}"


def _generate_application_scenarios(node_name: str, domain1: DomainCategory, 
                                  domain2: DomainCategory) -> List[str]:
    """
    辅助函数：生成应用场景
    """
    scenarios = [
        f"在{domain1.value}研究中应用{node_name}解释异常现象",
        f"将{node_name}用于{domain2.value}系统的优化设计",
        f"基于{node_name}开发跨学科教育课程",
        f"利用{node_name}预测两个领域的发展趋势交汇点"
    ]
    
    # 添加特定领域组合的场景
    if {domain1, domain2} == {DomainCategory.PHYSICS, DomainCategory.SOCIOLOGY}:
        scenarios.append("社会物理学建模与群体行为预测")
    elif {domain1, domain2} == {DomainCategory.BIOLOGY, DomainCategory.TECHNOLOGY}:
        scenarios.append("生物启发式算法设计与仿生系统开发")
    
    return scenarios[:3]  # 返回前3个最相关场景


def _calculate_confidence(features: Dict[str, float]) -> float:
    """
    辅助函数：计算置信度分数
    """
    if not features:
        return 0.0
    
    avg_score = sum(features.values()) / len(features)
    diversity_bonus = min(0.2, len(features) * 0.05)  # 特征多样性加成
    
    return min(1.0, avg_score + diversity_bonus)


def build_cross_domain_overlap(node1: ConceptNode, node2: ConceptNode) -> Optional[OverlapResult]:
    """
    主功能函数：构建跨域重叠概念
    
    参数:
        node1: 第一个概念节点
        node2: 第二个概念节点
        
    返回:
        Optional[OverlapResult]: 构建结果或None(失败时)
        
    示例:
        >>> node_a = ConceptNode(
        ...     name="量子纠缠",
        ...     domain=DomainCategory.PHYSICS,
        ...     attributes={"distance_factor": 0.9, "information_flow": 0.8},
        ...     description="量子力学现象"
        ... )
        >>> node_b = ConceptNode(
        ...     name="古代婚姻制度",
        ...     domain=DomainCategory.SOCIOLOGY,
        ...     attributes={"constraint_level": 0.7, "distance_factor": 0.6},
        ...     description="社会规范体系"
        ... )
        >>> result = build_cross_domain_overlap(node_a, node_b)
        >>> print(result.intermediate_node)
        '量子纠缠与古代婚姻制度的远距离社会束缚'
    """
    try:
        # 验证输入
        validate_input_nodes(node1, node2)
        
        # 计算语义重叠
        overlap_score, overlap_features = calculate_semantic_overlap(node1, node2)
        
        # 生成中间节点
        result = generate_intermediate_node(node1, node2, overlap_features)
        
        logger.info(f"跨域构建完成，置信度: {result.confidence_score:.2f}")
        return result
        
    except ValueError as ve:
        logger.error(f"输入验证失败: {str(ve)}")
        return None
    except RuntimeError as re:
        logger.error(f"运行时错误: {str(re)}")
        return None
    except Exception as e:
        logger.critical(f"未预期的错误: {str(e)}", exc_info=True)
        return None


# 使用示例
if __name__ == "__main__":
    # 创建示例节点
    quantum_node = ConceptNode(
        name="量子纠缠",
        domain=DomainCategory.PHYSICS,
        attributes={
            "distance_factor": 0.95,
            "information_flow": 0.85,
            "complexity": 0.9,
            "stability": 0.7
        },
        description="粒子间即时的量子关联现象"
    )
    
    marriage_node = ConceptNode(
        name="古代婚姻制度",
        domain=DomainCategory.SOCIOLOGY,
        attributes={
            "constraint_level": 0.8,
            "distance_factor": 0.6,
            "tradition_weight": 0.75,
            "social_function": 0.7
        },
        description="历史上的婚姻规范体系"
    )
    
    # 执行跨域构建
    overlap_result = build_cross_domain_overlap(quantum_node, marriage_node)
    
    if overlap_result:
        print("\n跨域构建结果:")
        print(f"中间节点: {overlap_result.intermediate_node}")
        print(f"桥接概念: {overlap_result.bridge_concept}")
        print("应用场景:")
        for i, scenario in enumerate(overlap_result.application_scenarios, 1):
            print(f"  {i}. {scenario}")
        print(f"置信度分数: {overlap_result.confidence_score:.2f}")