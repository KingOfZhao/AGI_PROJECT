"""
名称: auto_跨域迁移中的_结构一致性_校验器_当系统_1fd67e
描述: 跨域迁移中的'结构一致性'校验器。本模块实现了认知科学中的结构映射理论，
     用于评估源域到目标域的迁移可行性。
"""

import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DomainSpace:
    """
    定义一个认知域的数据结构。
    
    Attributes:
        name (str): 域名称
        entities (Set[str]): 该域内的实体集合
        relations (Dict[str, List[Tuple[str, str]]]): 该域内的关系结构
            Key: 关系名称, Value: (主体, 客体) 元组列表
    """
    name: str
    entities: Set[str]
    relations: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证：确保实体是集合，关系字典格式正确"""
        if not isinstance(self.entities, set):
            self.entities = set(self.entities)
        if not isinstance(self.relations, dict):
            raise ValueError("Relations must be a dictionary.")

class StructureConsistencyValidator:
    """
    结构一致性校验器。
    
    基于 Structure Mapping Theory (结构映射理论)，不仅仅比较实体的语义相似度，
    重点关注属性和一阶/二阶关系的同构性。
    """
    
    def __init__(self, snr_threshold: float = 0.65):
        """
        初始化校验器。
        
        Args:
            snr_threshold (float): 结构映射的信噪比阈值，低于此值将终止迁移。
        """
        if not 0.0 <= snr_threshold <= 1.0:
            raise ValueError("SNR threshold must be between 0.0 and 1.0")
        self.snr_threshold = snr_threshold
        logger.info(f"Validator initialized with SNR threshold: {self.snr_threshold}")

    def _calculate_graph_hash(self, domain: DomainSpace) -> str:
        """
        [辅助函数] 计算域结构的哈希指纹，用于快速比对结构性特征。
        
        Args:
            domain (DomainSpace): 待计算的域对象
            
        Returns:
            str: MD5哈希值
        """
        structure_str = ""
        # 排序以确保顺序一致性
        sorted_rels = sorted(domain.relations.keys())
        for rel in sorted_rels:
            pairs = sorted(domain.relations[rel])
            structure_str += f"{rel}::{pairs}|"
        
        return hashlib.md5(structure_str.encode('utf-8')).hexdigest()

    def _validate_mapping_inputs(self, source: DomainSpace, target: DomainSpace) -> None:
        """
        [数据验证] 检查输入数据的完整性和边界条件。
        
        Args:
            source (DomainSpace): 源域
            target (DomainSpace): 目标域
            
        Raises:
            ValueError: 如果数据为空或结构无效
        """
        if not source.entities or not source.relations:
            logger.error("Source domain is empty or lacks structural relations.")
            raise ValueError("Source domain must contain entities and relations for migration.")
        
        if len(source.relations) > 100 or len(target.relations) > 100:
            logger.warning("Large domain size detected, processing might be slow.")

    def analyze_structural_isomorphism(self, source: DomainSpace, target: DomainSpace) -> Tuple[float, Dict[str, Any]]:
        """
        [核心函数 1] 分析两个域之间的结构同构性。
        
        算法逻辑：
        1. 提取源域和目标域的关系键集合。
        2. 计算关系名称的重叠度（语义层面简化处理）。
        3. 计算关系元组的结构模式匹配度（拓扑层面）。
        4. 综合计算信噪比 (SNR)。
        
        Args:
            source (DomainSpace): 迁移的源域 (A域)
            target (DomainSpace): 迁移的目标域 (B域)
            
        Returns:
            Tuple[float, Dict]: 
                - float: 结构一致性得分 (0.0 - 1.0)
                - Dict: 详细的匹配报告
        """
        self._validate_mapping_inputs(source, target)
        
        # 1. 关系类型交集 (假设关系名称具有通用语义，如 'causes', 'contains')
        s_rels = set(source.relations.keys())
        t_rels = set(target.relations.keys())
        
        if not s_rels or not t_rels:
            return 0.0, {"error": "Empty relations"}

        # 关键：结构映射不仅看名字，更看“关系的深度”和“连通性”
        # 这里使用简化模型：计算共有关系类型的占比 (Jaccard 相似度)
        common_relations = s_rels.intersection(t_rels)
        relation_overlap = len(common_relations) / len(s_rels) if s_rels else 0
        
        # 2. 结构连通性比对
        # 检查在共有关系中，连接模式的相似度
        # 简化指标：比较每个关系的平均度数或模式结构
        structure_score = 0.0
        matched_pairs = 0
        
        for rel in common_relations:
            # 比较该关系下的连接密度
            s_density = len(source.relations[rel]) / (len(source.entities) ** 2) if source.entities else 0
            t_density = len(target.relations[rel]) / (len(target.entities) ** 2) if target.entities else 0
            
            # 密度越接近，结构分越高
            max_density = max(s_density, t_density)
            if max_density > 0:
                similarity = 1 - abs(s_density - t_density) / max_density
            else:
                similarity = 1.0
            
            structure_score += similarity
            matched_pairs += 1
            
        avg_structure_score = structure_score / len(common_relations) if common_relations else 0
        
        # 3. 计算最终信噪比 (SNR)
        # 权重：关系类型重叠 (40%) + 内部结构一致性 (60%)
        final_snr = (relation_overlap * 0.4) + (avg_structure_score * 0.6)
        
        report = {
            "source_hash": self._calculate_graph_hash(source),
            "target_hash": self._calculate_graph_hash(target),
            "common_relations": list(common_relations),
            "relation_overlap": relation_overlap,
            "structure_pattern_score": avg_structure_score,
            "final_snr": final_snr
        }
        
        logger.info(f"Isomorphism analysis complete. SNR: {final_snr:.4f}")
        return final_snr, report

    def check_migration_feasibility(self, source: DomainSpace, target: DomainSpace) -> bool:
        """
        [核心函数 2] 执行迁移可行性检查。
        
        若结构映射的信噪比低于阈值，则终止迁移以防幻觉。
        
        Args:
            source (DomainSpace): 源域
            target (DomainSpace): 目标域
            
        Returns:
            bool: True 表示允许迁移，False 表示应终止
            
        Raises:
            RuntimeError: 如果系统检测到高风险的结构冲突
        """
        logger.info(f"Checking migration from '{source.name}' to '{target.name}'...")
        
        try:
            snr_score, report = self.analyze_structural_isomorphism(source, target)
            
            if snr_score < self.snr_threshold:
                logger.warning(
                    f"Migration BLOCKED. SNR {snr_score:.4f} below threshold {self.snr_threshold}. "
                    f"Reason: Low structural consistency. Risk of Hallucination."
                )
                return False
            
            # 二次检查：如果结构一致但实体规模差异过大，也可能是伪映射
            size_ratio = len(source.entities) / len(target.entities) if target.entities else 999
            if size_ratio > 5.0 or size_ratio < 0.2:
                logger.warning(f"Migration WARN. Entity scale mismatch ratio: {size_ratio:.2f}")
                # 这里不直接终止，但在实际AGI中可能需要人工介入
                pass
                
            logger.info("Migration APPROVED. Structural mapping valid.")
            return True

        except Exception as e:
            logger.error(f"Error during migration check: {str(e)}")
            return False

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 定义源域 A: 简单的力学系统 (太阳系模型)
    solar_system_relations = {
        "orbits": [("Earth", "Sun"), ("Mars", "Sun")],
        "attracts": [("Sun", "Earth"), ("Sun", "Mars")]
    }
    domain_a = DomainSpace(
        name="SolarSystem", 
        entities={"Sun", "Earth", "Mars"}, 
        relations=solar_system_relations
    )

    # 2. 定义目标域 B: 原子模型 (电子绕原子核)
    # 结构高度相似：电子之于原子核，如行星之于太阳
    atom_relations = {
        "orbits": [("Electron", "Nucleus")],
        "attracts": [("Nucleus", "Electron")] # 注意：引力方向可能不同，但关系结构存在
    }
    domain_b = DomainSpace(
        name="AtomModel", 
        entities={"Nucleus", "Electron"}, 
        relations=atom_relations
    )

    # 3. 定义目标域 C: 不相关的域 (例如：购物车)
    cart_relations = {
        "contains": [("User", "Item")],
        "pays_for": [("User", "Item")]
    }
    domain_c = DomainSpace(
        name="ShoppingCart", 
        entities={"User", "Item"}, 
        relations=cart_relations
    )

    # 4. 初始化校验器
    validator = StructureConsistencyValidator(snr_threshold=0.5)

    print("--- Test Case 1: Valid Migration (Solar -> Atom) ---")
    is_valid = validator.check_migration_feasibility(domain_a, domain_b)
    print(f"Result: {'PASS' if is_valid else 'FAIL'}\n")

    print("--- Test Case 2: Invalid Migration (Solar -> Shopping) ---")
    is_valid_2 = validator.check_migration_feasibility(domain_a, domain_c)
    print(f"Result: {'PASS' if is_valid_2 else 'FAIL'}\n")