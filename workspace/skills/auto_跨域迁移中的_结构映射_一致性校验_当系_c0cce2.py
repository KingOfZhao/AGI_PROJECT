"""
模块名称: auto_跨域迁移中的_结构映射_一致性校验_当系_c0cce2
描述: 本模块实现了跨域迁移中的'结构映射'一致性校验算法。
      旨在评估源域（如'小摊贩博弈'）与目标域（如'企业资源规划'）之间的结构相似度。
      核心逻辑遵循结构映射理论：如果属性相似但底层关系逻辑冲突，则应阻断迁移，
      以防止负迁移。
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class CognitiveNode:
    """
    认知节点类，代表领域中的一个概念或实体。
    
    Attributes:
        id (str): 节点唯一标识符
        label (str): 节点标签（如 'Street_Vendor', 'ERP_System'）
        attributes (Dict[str, Any]): 节点的静态属性（如 'color', 'size'）
        relations (Dict[str, str]): 节点参与的关系映射 {关系名称: 目标节点ID}
    """
    id: str
    label: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, str] = field(default_factory=dict)

@dataclass
class MappingResult:
    """
    校验结果数据类。
    
    Attributes:
        is_consistent (bool): 结构是否一致，是否允许迁移
        similarity_score (float): 结构相似度得分 (0.0 - 1.0)
        conflicts (List[str]): 检测到的具体冲突描述
        message (str): 给系统的反馈信息
    """
    is_consistent: bool
    similarity_score: float
    conflicts: List[str] = field(default_factory=list)
    message: str = ""

# --- 辅助函数 ---

def _calculate_attribute_similarity(
    source_attrs: Dict[str, Any], 
    target_attrs: Dict[str, Any]
) -> float:
    """
    辅助函数：计算两个节点属性集合的杰卡德相似度。
    仅用于表面特征的初步筛选，不决定最终的结构一致性。
    
    Args:
        source_attrs (Dict[str, Any]): 源节点属性
        target_attrs (Dict[str, Any]): 目标节点属性
        
    Returns:
        float: 相似度得分
        
    Raises:
        TypeError: 如果输入不是字典
    """
    if not isinstance(source_attrs, dict) or not isinstance(target_attrs, dict):
        logger.error("属性输入必须为字典类型")
        raise TypeError("Attributes must be dictionaries")

    if not source_attrs and not target_attrs:
        return 1.0
    
    source_keys = set(source_attrs.keys())
    target_keys = set(target_attrs.keys())
    
    intersection = source_keys.intersection(target_keys)
    union = source_keys.union(target_keys)
    
    if not union:
        return 0.0
        
    # 简单的键匹配相似度，实际场景可扩展为值匹配
    return len(intersection) / len(union)

def _validate_node_integrity(node: CognitiveNode) -> bool:
    """
    辅助函数：验证节点数据的完整性。
    
    Args:
        node (CognitiveNode): 待验证的节点
        
    Returns:
        bool: 数据是否有效
    """
    if not node.id or not isinstance(node.id, str):
        logger.warning(f"节点ID无效: {node}")
        return False
    if not node.label or not isinstance(node.label, str):
        logger.warning(f"节点Label无效: {node.id}")
        return False
    return True

# --- 核心函数 ---

def analyze_structural_isomorphism(
    source_node: CognitiveNode,
    target_node: CognitiveNode,
    critical_relations: Optional[Set[str]] = None
) -> Tuple[bool, float, List[str]]:
    """
    核心函数1：分析源节点与目标节点的结构同构性。
    重点关注关系的映射逻辑，而非属性本身。
    
    Args:
        source_node (CognitiveNode): 源域节点（如：小摊贩）
        target_node (CognitiveNode): 目标域节点（如：ERP模块）
        critical_relations (Optional[Set[str]]): 必须存在且一致的关键关系列表
        
    Returns:
        Tuple[bool, float, List[str]]: 
            - 结构是否兼容
            - 关系重合度得分
            - 冲突详情列表
            
    Example:
        >>> s_node = CognitiveNode("s1", "Vendor", relations={"pay": "bank"})
        >>> t_node = CognitiveNode("t1", "ERP", relations={"pay": "finance_mod"})
        >>> is_iso, score, conf = analyze_structural_isomorphism(s_node, t_node)
    """
    if not _validate_node_integrity(source_node) or not _validate_node_integrity(target_node):
        raise ValueError("输入节点数据完整性校验失败")

    logger.info(f"开始分析结构映射: {source_node.label} -> {target_node.label}")
    
    conflicts = []
    source_rels = set(source_node.relations.keys())
    target_rels = set(target_node.relations.keys())
    
    # 1. 检查关键关系是否存在
    if critical_relations:
        missing_in_target = critical_relations - target_rels
        if missing_in_target:
            msg = f"目标域缺失关键关系: {missing_in_target}"
            conflicts.append(msg)
            logger.warning(msg)
    
    # 2. 检查关系的方向性和逻辑
    # 这里模拟结构映射理论中的 "Role binding" 检查
    # 如果源域有一个 'bargain' (讨价还价) 关系，而目标域没有或变成了 'fixed_price'
    # 这将被视为结构冲突
    for rel, target_id in source_node.relations.items():
        if rel in target_node.relations:
            # 这里可以添加更深层的目标节点类型检查
            # 简化版：假设只要关系存在即结构兼容（实际需要检查目标节点的语义类型）
            pass
        else:
            # 检查是否存在语义对立的关系
            # 假设：如果源有 'negotiate'，目标有 'execute_command'，视为冲突
            if rel == "negotiate_price" and "fixed_protocol" in target_rels:
                conflicts.append(f"关系冲突: 源域'{rel}'暗示灵活性，目标域存在'fixed_protocol'暗示刚性")
    
    # 计算结构重合度
    intersection = source_rels.intersection(target_rels)
    union = source_rels.union(target_rels)
    structure_score = len(intersection) / len(union) if union else 0.0
    
    # 如果有结构性冲突，强制得分降低
    if conflicts:
        structure_score *= 0.5
        
    return (len(conflicts) == 0, structure_score, conflicts)

def validate_transfer_consistency(
    source_node: CognitiveNode,
    target_node: CognitiveNode,
    similarity_threshold: float = 0.6
) -> MappingResult:
    """
    核心函数2：执行完整的跨域迁移一致性校验。
    整合属性相似度与结构一致性的综合判断。
    
    逻辑:
    1. 如果属性相似度低，迁移基础弱（直接通过或忽略，视业务逻辑而定）。
    2. 如果属性相似度高，但结构冲突 -> 阻断迁移 (防止负迁移)。
    3. 如果属性相似度高，且结构兼容 -> 允许迁移。
    
    Args:
        source_node (CognitiveNode): 源节点
        target_node (CognitiveNode): 目标节点
        similarity_threshold (float): 判定为“高相似”的阈值
        
    Returns:
        MappingResult: 包含最终决策和详细信息的对象
    """
    try:
        logger.info(f"校验迁移: {source_node.id} -> {target_node.id}")
        
        # 1. 数据边界检查
        if not source_node or not target_node:
            return MappingResult(False, 0.0, message="输入节点为空")
            
        # 2. 计算属性相似度 (Surface Similarity)
        attr_sim = _calculate_attribute_similarity(source_node.attributes, target_node.attributes)
        
        # 3. 分析结构一致性 (Deep Structure)
        # 设定关键关系，例如 'transaction', 'inventory'
        critical_rels = {"manage", "transaction"}
        is_iso, struct_score, conflicts = analyze_structural_isomorphism(
            source_node, target_node, critical_rels
        )
        
        # 4. 综合决策逻辑
        # 如果属性很像（容易混淆），但结构不对，必须阻断
        if attr_sim > similarity_threshold and not is_iso:
            msg = (f"阻断迁移：高属性相似度({attr_sim:.2f})但结构冲突。"
                   f"源域关系逻辑不适用于目标域。冲突: {conflicts}")
            logger.warning(msg)
            return MappingResult(
                is_consistent=False,
                similarity_score=(attr_sim + struct_score) / 2,
                conflicts=conflicts,
                message=msg
            )
            
        # 如果结构兼容，或者属性很不相似（此时迁移可能是探索性的）
        if is_iso:
            msg = f"迁移通过：结构兼容。结构分: {struct_score:.2f}"
            logger.info(msg)
            return MappingResult(
                is_consistent=True,
                similarity_score=struct_score,
                message=msg
            )
        else:
            # 属性不相似，结构也有冲突，通常不建议迁移，但风险较低
            msg = f"迁移不建议：低相似度且存在结构差异。"
            logger.info(msg)
            return MappingResult(
                is_consistent=False, # 保守策略：阻断
                similarity_score=struct_score,
                conflicts=conflicts,
                message=msg
            )

    except Exception as e:
        logger.error(f"迁移校验过程中发生异常: {str(e)}")
        return MappingResult(False, 0.0, message=f"System Error: {str(e)}")

# --- 使用示例与主程序 ---

if __name__ == "__main__":
    # 模拟场景：将'小摊贩博弈'技能迁移至'企业ERP'
    
    # 1. 定义源域节点：小摊贩
    # 特点：灵活定价，非正规交易
    vendor_node = CognitiveNode(
        id="Node_Street_Vendor",
        label="Street_Vendor_Game",
        attributes={"scale": "small", "flexibility": "high", "location": "outdoor"},
        relations={
            "negotiate_price": "Customer", # 讨价还价
            "manage_inventory": "Cart",    # 管理推车
            "transaction": "Cash"          # 现金交易
        }
    )
    
    # 2. 定义目标域节点：ERP系统
    # 特点：固定流程，正规交易
    erp_node_compatible = CognitiveNode(
        id="Node_ERP_Finance",
        label="ERP_System",
        attributes={"scale": "large", "flexibility": "low", "location": "datacenter"},
        relations={
            "fixed_protocol": "Supplier",  # 固定协议
            "manage_inventory": "Database", # 管理数据库
            "transaction": "Digital"        # 数字交易
        }
    )
    
    # 3. 执行校验
    print("--- 执行跨域迁移校验 ---")
    result = validate_transfer_consistency(vendor_node, erp_node_compatible)
    
    print(f"结果: {'允许迁移' if result.is_consistent else '阻断迁移'}")
    print(f"综合得分: {result.similarity_score:.4f}")
    print(f"详细信息: {result.message}")
    if result.conflicts:
        print(f"冲突详情: {result.conflicts}")

    # 演示边界检查
    print("\n--- 测试异常处理 ---")
    bad_node = CognitiveNode(id="", label="") # 无效节点
    try:
        validate_transfer_consistency(bad_node, erp_node_compatible)
    except ValueError as e:
        print(f"成功捕获预期错误: {e}")