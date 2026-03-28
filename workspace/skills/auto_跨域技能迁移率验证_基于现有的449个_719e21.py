"""
名称: auto_跨域技能迁移率验证_基于现有的449个_719e21
描述: 【跨域技能迁移率验证】基于现有的449个技能节点，AI能否通过‘结构映射’将‘摊煎饼’
      （已验证技能）中的面糊流体控制经验，迁移到‘制作宣纸’或‘刮腻子’等涉及流体涂层
      的陌生领域？这需要验证认知网络中的‘流体力学控制’抽象节点是否具备普适性。
领域: transfer_learning
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 技能唯一标识符
        name (str): 技能名称
        domain (str): 所属领域
        attributes (Dict[str, float]): 技能属性特征向量（如粘度控制、厚度均匀性等）
        verified (bool): 是否已验证
    """
    id: str
    name: str
    domain: str
    attributes: Dict[str, float]
    verified: bool = False
    
    def __post_init__(self):
        """数据验证"""
        if not self.id or not self.name:
            raise ValueError("Skill ID and Name cannot be empty")
        if not isinstance(self.attributes, dict):
            raise TypeError("Attributes must be a dictionary")


@dataclass
class TransferResult:
    """
    迁移验证结果数据结构。
    
    Attributes:
        source_skill (str): 源技能名称
        target_skill (str): 目标技能名称
        similarity_score (float): 结构相似度得分 (0.0 - 1.0)
        transferable (bool): 是否可迁移
        confidence (float): 置信度 (0.0 - 1.0)
        mapping_details (Dict): 映射详情
    """
    source_skill: str
    target_skill: str
    similarity_score: float
    transferable: bool
    confidence: float
    mapping_details: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def validate_skill_graph(skill_graph: Dict[str, SkillNode]) -> bool:
    """
    辅助函数：验证技能图谱数据的完整性和一致性。
    
    Args:
        skill_graph (Dict[str, SkillNode]): 技能图谱字典
        
    Returns:
        bool: 数据是否有效
        
    Raises:
        ValueError: 如果数据验证失败
    """
    if not isinstance(skill_graph, dict):
        raise TypeError("Skill graph must be a dictionary")
    
    if len(skill_graph) < 1:
        raise ValueError("Skill graph cannot be empty")
    
    required_attributes = [
        'viscosity_control', 'thickness_uniformity', 
        'drying_speed_control', 'tool_pressure'
    ]
    
    for node_id, node in skill_graph.items():
        if not isinstance(node, SkillNode):
            raise TypeError(f"Node {node_id} is not a SkillNode instance")
        
        # 检查关键属性是否存在
        for attr in required_attributes:
            if attr not in node.attributes:
                logger.warning(f"Node {node_id} missing key attribute: {attr}")
                
    logger.info(f"Validated skill graph with {len(skill_graph)} nodes.")
    return True


def calculate_structural_mapping_similarity(
    source: SkillNode, 
    target: SkillNode,
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, float]]:
    """
    核心函数：计算源技能与目标技能之间的结构映射相似度。
    
    基于属性向量的加权欧几里得距离计算相似度，模拟认知网络中的
    '结构映射'过程。
    
    Args:
        source (SkillNode): 源技能节点（如'摊煎饼'）
        target (SkillNode): 目标技能节点（如'制作宣纸'）
        weights (Optional[Dict[str, float]]): 属性权重配置
        
    Returns:
        Tuple[float, Dict[str, float]]: 
            - 相似度得分 (0.0 - 1.0)
            - 各维度的详细相似度映射
        
    Example:
        >>> source = SkillNode("001", "摊煎饼", "cuisine", {"viscosity_control": 0.9})
        >>> target = SkillNode("002", "刮腻子", "construction", {"viscosity_control": 0.85})
        >>> score, details = calculate_structural_mapping_similarity(source, target)
    """
    if weights is None:
        # 默认权重配置，强调流体控制特性
        weights = {
            'viscosity_control': 0.3,       # 粘度控制（核心）
            'thickness_uniformity': 0.3,    # 厚度均匀性（核心）
            'drying_speed_control': 0.2,    # 干燥速度控制
            'tool_pressure': 0.1,           # 工具压力
            'area_coverage': 0.1            # 覆盖面积
        }
    
    total_distance = 0.0
    total_weight = 0.0
    dimension_details = {}
    
    # 归一化权重
    weight_sum = sum(weights.values())
    normalized_weights = {k: v/weight_sum for k, v in weights.items()}
    
    for attr, weight in normalized_weights.items():
        source_val = source.attributes.get(attr, 0.0)
        target_val = target.attributes.get(attr, 0.0)
        
        # 边界检查
        source_val = max(0.0, min(1.0, source_val))
        target_val = max(0.0, min(1.0, target_val))
        
        # 计算归一化距离
        distance = abs(source_val - target_val)
        weighted_distance = distance * weight
        
        total_distance += weighted_distance
        total_weight += weight
        
        # 记录维度详情
        dimension_details[attr] = {
            'source_value': source_val,
            'target_value': target_val,
            'distance': distance,
            'contribution': weighted_distance
        }
    
    # 转换为相似度得分 (1 - normalized_distance)
    similarity_score = 1.0 - (total_distance / total_weight if total_weight > 0 else 0)
    
    # 边界保护
    similarity_score = max(0.0, min(1.0, similarity_score))
    
    return similarity_score, dimension_details


def verify_cross_domain_transfer(
    skill_graph: Dict[str, SkillNode],
    source_skill_id: str,
    target_skill_ids: List[str],
    threshold: float = 0.75
) -> List[TransferResult]:
    """
    核心函数：验证跨域技能迁移的可行性。
    
    该函数模拟AGI系统中的'跨域迁移'过程，验证流体力学控制等抽象节点
    是否能在不同领域间泛化。
    
    Args:
        skill_graph (Dict[str, SkillNode]): 完整的技能图谱（包含449个节点）
        source_skill_id (str): 源技能ID（如'摊煎饼'的ID）
        target_skill_ids (List[str]): 目标技能ID列表
        threshold (float): 迁移可行性的判定阈值
        
    Returns:
        List[TransferResult]: 迁移验证结果列表
        
    Raises:
        KeyError: 如果源技能ID不存在
        ValueError: 如果输入参数无效
        
    Data Format:
        Input:
            skill_graph: {"id1": SkillNode, "id2": SkillNode, ...}
        Output:
            [TransferResult, TransferResult, ...]
            
    Example:
        >>> graph = {
        ...     "s1": SkillNode("s1", "摊煎饼", "cuisine", {...}, True),
        ...     "s2": SkillNode("s2", "制作宣纸", "craft", {...}, False)
        ... }
        >>> results = verify_cross_domain_transfer(graph, "s1", ["s2"])
    """
    # 输入验证
    if not isinstance(skill_graph, dict):
        raise TypeError("skill_graph must be a dictionary")
    
    if source_skill_id not in skill_graph:
        raise KeyError(f"Source skill {source_skill_id} not found in graph")
    
    if not isinstance(target_skill_ids, list) or len(target_skill_ids) == 0:
        raise ValueError("target_skill_ids must be a non-empty list")
    
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    # 验证图谱数据
    try:
        validate_skill_graph(skill_graph)
    except Exception as e:
        logger.error(f"Skill graph validation failed: {e}")
        raise
    
    source_node = skill_graph[source_skill_id]
    results = []
    
    logger.info(f"Starting cross-domain transfer verification from '{source_node.name}'")
    logger.info(f"Target skills count: {len(target_skill_ids)}, Threshold: {threshold}")
    
    for target_id in target_skill_ids:
        try:
            # 边界检查：目标是否存在
            if target_id not in skill_graph:
                logger.warning(f"Target skill {target_id} not found, skipping")
                continue
            
            target_node = skill_graph[target_id]
            
            # 计算结构映射相似度
            similarity, details = calculate_structural_mapping_similarity(
                source_node, target_node
            )
            
            # 计算置信度（基于领域距离和属性覆盖度）
            domain_penalty = 0.1 if source_node.domain != target_node.domain else 0.0
            attribute_coverage = len(details) / 5.0  # 假设5个核心属性
            confidence = (similarity * 0.7 + attribute_coverage * 0.3) - domain_penalty
            confidence = max(0.0, min(1.0, confidence))
            
            # 判定是否可迁移
            transferable = similarity >= threshold and confidence >= 0.5
            
            # 构建结果对象
            result = TransferResult(
                source_skill=source_node.name,
                target_skill=target_node.name,
                similarity_score=round(similarity, 4),
                transferable=transferable,
                confidence=round(confidence, 4),
                mapping_details={
                    'dimension_breakdown': details,
                    'domain_gap': source_node.domain != target_node.domain,
                    'source_verified': source_node.verified
                }
            )
            
            results.append(result)
            
            # 日志记录
            status = "SUCCESS" if transferable else "FAILED"
            logger.info(
                f"Transfer {source_node.name} -> {target_node.name}: "
                f"{status} (Sim: {similarity:.2f}, Conf: {confidence:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Error processing target {target_id}: {e}")
            continue
    
    # 统计摘要
    successful = sum(1 for r in results if r.transferable)
    logger.info(
        f"Verification complete: {successful}/{len(results)} "
        f"skills are transferable ({successful/len(results)*100:.1f}%)"
    )
    
    return results


def export_results_to_json(results: List[TransferResult], filepath: str) -> None:
    """
    辅助函数：将迁移验证结果导出为JSON格式。
    
    Args:
        results (List[TransferResult]): 验证结果列表
        filepath (str): 输出文件路径
    """
    try:
        output_data = {
            "metadata": {
                "total_evaluations": len(results),
                "successful_transfers": sum(1 for r in results if r.transferable),
                "export_timestamp": datetime.now().isoformat()
            },
            "results": [
                {
                    "source": r.source_skill,
                    "target": r.target_skill,
                    "similarity_score": r.similarity_score,
                    "transferable": r.transferable,
                    "confidence": r.confidence,
                    "details": r.mapping_details
                }
                for r in results
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results exported to {filepath}")
        
    except IOError as e:
        logger.error(f"Failed to export results: {e}")
        raise


# ============================================================
# 使用示例 / USAGE EXAMPLE
# ============================================================
if __name__ == "__main__":
    """
    使用示例：模拟基于449个技能节点的跨域迁移验证
    
    场景：验证'摊煎饼'技能中的流体控制经验能否迁移到其他领域
    """
    
    # 1. 构建模拟技能图谱（简化示例，实际应包含449个节点）
    mock_skill_graph = {
        "skill_001": SkillNode(
            id="skill_001",
            name="摊煎饼",
            domain="cuisine",
            attributes={
                "viscosity_control": 0.92,
                "thickness_uniformity": 0.88,
                "drying_speed_control": 0.75,
                "tool_pressure": 0.80,
                "area_coverage": 0.95
            },
            verified=True
        ),
        "skill_002": SkillNode(
            id="skill_002",
            name="制作宣纸",
            domain="craft",
            attributes={
                "viscosity_control": 0.85,
                "thickness_uniformity": 0.92,
                "drying_speed_control": 0.65,
                "tool_pressure": 0.70,
                "area_coverage": 0.90
            },
            verified=False
        ),
        "skill_003": SkillNode(
            id="skill_003",
            name="刮腻子",
            domain="construction",
            attributes={
                "viscosity_control": 0.80,
                "thickness_uniformity": 0.85,
                "drying_speed_control": 0.50,
                "tool_pressure": 0.90,
                "area_coverage": 0.88
            },
            verified=False
        ),
        "skill_004": SkillNode(
            id="skill_004",
            name="巧克力调温",
            domain="cuisine",
            attributes={
                "viscosity_control": 0.95,
                "thickness_uniformity": 0.70,
                "drying_speed_control": 0.85,
                "tool_pressure": 0.40,
                "area_coverage": 0.60
            },
            verified=False
        )
    }
    
    # 2. 执行跨域迁移验证
    print("=" * 60)
    print("跨域技能迁移率验证系统")
    print("=" * 60)
    
    try:
        results = verify_cross_domain_transfer(
            skill_graph=mock_skill_graph,
            source_skill_id="skill_001",  # 摊煎饼
            target_skill_ids=["skill_002", "skill_003", "skill_004"],
            threshold=0.75
        )
        
        # 3. 打印详细结果
        print("\n验证结果详情:")
        print("-" * 60)
        for result in results:
            print(f"\n源技能: {result.source_skill}")
            print(f"目标技能: {result.target_skill}")
            print(f"结构相似度: {result.similarity_score:.2%}")
            print(f"置信度: {result.confidence:.2%}")
            print(f"可迁移: {'✓ 是' if result.transferable else '✗ 否'}")
            print(f"领域跨越: {'是' if result.mapping_details.get('domain_gap') else '否'}")
        
        # 4. 导出结果
        export_results_to_json(results, "transfer_verification_results.json")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")