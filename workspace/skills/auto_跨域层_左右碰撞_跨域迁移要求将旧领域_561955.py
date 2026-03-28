"""
名称: auto_跨域层_左右碰撞_跨域迁移要求将旧领域_561955
描述: 【跨域层：左右碰撞】跨域迁移要求将旧领域的结构映射到新领域。
     本模块构建一个基于'功能本体'的映射器，将纺织机械中的'张力控制'节点，
     自动转化为3D打印设备中的'挤出速率控制'节点。
     核心逻辑在于理解'维持材料流动稳定性'这一抽象物理本质，而非仅仅匹配关键词。
作者: AGI System
版本: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DomainType(Enum):
    """领域类型枚举"""
    TEXTILE = "textile_mechanics"
    PRINTING_3D = "3d_printing"
    UNKNOWN = "unknown"

class PhysicalProperty(Enum):
    """抽象物理属性枚举"""
    FLOW_STABILITY = "flow_stability"  # 流动稳定性
    TENSION_DYNAMICS = "tension_dynamics"  # 张力动力学
    THERMAL_DYNAMICS = "thermal_dynamics"  # 热力学
    MECHANICAL_MOTION = "mechanical_motion"  # 机械运动

@dataclass
class OntologyNode:
    """
    本体节点数据结构
    代表特定领域内的一个功能单元或概念节点
    """
    node_id: str
    name: str
    domain: DomainType
    description: str
    input_signals: List[str] = field(default_factory=list)
    output_signals: List[str] = field(default_factory=list)
    physical_vector: Dict[PhysicalProperty, float] = field(default_factory=dict)
    # 物理向量权重示例: {FLOW_STABILITY: 0.9, TENSION_DYNAMICS: 0.8}

    def __post_init__(self):
        if not self.physical_vector:
            logger.warning(f"Node {self.node_id} initialized without physical vectors.")

class CrossDomainMapper:
    """
    跨域映射器核心类
    基于功能本体和物理本质向量进行节点映射
    """

    def __init__(self, similarity_threshold: float = 0.75):
        """
        初始化映射器
        
        Args:
            similarity_threshold (float): 映射成功的最小余弦相似度阈值
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.similarity_threshold = similarity_threshold
        logger.info(f"CrossDomainMapper initialized with threshold: {similarity_threshold}")

    def _calculate_vector_similarity(
        self, 
        vec_source: Dict[PhysicalProperty, float], 
        vec_target: Dict[PhysicalProperty, float]
    ) -> float:
        """
        辅助函数：计算两个物理向量的余弦相似度
        
        Args:
            vec_source: 源领域节点的物理属性向量
            vec_target: 目标领域节点的物理属性向量
            
        Returns:
            float: 相似度得分 (0.0 到 1.0)
        """
        if not vec_source or not vec_target:
            return 0.0
        
        # 提取共同的键
        common_keys = set(vec_source.keys()) & set(vec_target.keys())
        if not common_keys:
            return 0.0
            
        dot_product = sum(vec_source[k] * vec_target[k] for k in common_keys)
        norm_source = sum(v**2 for v in vec_source.values())**0.5
        norm_target = sum(v**2 for v in vec_target.values())**0.5
        
        if norm_source == 0 or norm_target == 0:
            return 0.0
            
        return dot_product / (norm_source * norm_target)

    def map_node(
        self, 
        source_node: OntologyNode, 
        target_domain_candidates: List[OntologyNode]
    ) -> Optional[Dict[str, Any]]:
        """
        核心函数1：执行跨域节点映射
        
        将源节点映射到目标领域中最匹配的候选节点。
        
        Args:
            source_node: 源领域节点 (例如: 纺织张力控制)
            target_domain_candidates: 目标领域的候选节点列表 (例如: 3D打印组件列表)
            
        Returns:
            Optional[Dict]: 包含映射结果和置信度的字典，若无匹配则返回None
        """
        if not target_domain_candidates:
            logger.error("Target candidates list is empty.")
            return None

        logger.info(f"Starting mapping for source node: {source_node.name}")
        
        best_match: Optional[OntologyNode] = None
        highest_score = 0.0
        
        # 检查领域是否交叉（不允许同域映射）
        if source_node.domain in [n.domain for n in target_domain_candidates]:
            logger.warning("Source and target domains appear to overlap. Cross-domain mapping skipped.")
            # 在实际AGI场景中，这可能不仅是警告，取决于具体逻辑

        for candidate in target_domain_candidates:
            # 计算物理本质相似度
            score = self._calculate_vector_similarity(
                source_node.physical_vector, 
                candidate.physical_vector
            )
            
            logger.debug(f"Comparing with {candidate.name}: Score {score:.4f}")
            
            if score > highest_score:
                highest_score = score
                best_match = candidate
        
        if highest_score < self.similarity_threshold:
            logger.warning(f"No suitable match found above threshold {self.similarity_threshold}")
            return None
            
        logger.info(f"Match found: {best_match.name} with score {highest_score:.4f}")
        
        return {
            "source_node_id": source_node.node_id,
            "target_node_id": best_match.node_id,
            "target_node_name": best_match.name,
            "confidence": highest_score,
            "abstract_bridging_concept": "Maintenance of Material Flow Stability" # 概念桥接
        }

    def generate_control_logic_transfer(self, mapping_result: Dict[str, Any]) -> str:
        """
        核心函数2：基于映射结果生成控制逻辑迁移建议
        
        根据匹配到的物理本质，生成具体的迁移策略描述。
        
        Args:
            mapping_result: map_node 函数的输出结果
            
        Returns:
            str: 控制逻辑迁移的文本建议
        """
        if not mapping_result:
            return "Unable to generate logic: Mapping failed."
            
        confidence = mapping_result.get('confidence', 0)
        logic = (
            f"Cross-Domain Logic Transfer Recommendation:\n"
            f"Based on the abstract goal of '{mapping_result['abstract_bridging_concept']}', "
            f"we map the feedback loop parameters.\n"
            f"Confidence: {confidence:.2f}\n"
            f"Action: Convert tension PID parameters to flow rate PID parameters, "
            f"adjusting for viscosity differences."
        )
        return logic

# 数据验证辅助函数
def validate_ontology_node_data(data: Dict[str, Any]) -> bool:
    """
    辅助函数：验证输入数据是否符合OntologyNode结构要求
    
    Args:
        data: 原始字典数据
        
    Returns:
        bool: 数据是否有效
    """
    required_keys = {"node_id", "name", "domain", "description"}
    if not required_keys.issubset(data.keys()):
        logger.error(f"Validation failed: Missing required keys in {data.get('node_id', 'Unknown')}")
        return False
    
    if not isinstance(data['domain'], DomainType):
        logger.error("Validation failed: Domain type must be DomainType enum.")
        return False
        
    return True

# 使用示例
if __name__ == "__main__":
    # 1. 定义源领域节点 (纺织：张力控制)
    # 物理向量含义：高流动稳定性需求，高张力动力学依赖
    textile_tension_node = OntologyNode(
        node_id="TXT-001",
        name="Yarn Tension Controller",
        domain=DomainType.TEXTILE,
        description="Adjusts motor speed to maintain constant yarn tension.",
        physical_vector={
            PhysicalProperty.FLOW_STABILITY: 0.9,
            PhysicalProperty.TENSION_DYNAMICS: 0.95,
            PhysicalProperty.MECHANICAL_MOTION: 0.6
        }
    )

    # 2. 定义目标领域候选节点 (3D打印)
    candidates = [
        OntologyNode(
            node_id="3DP-001",
            name="Z-Axis Stepper",
            domain=DomainType.PRINTING_3D,
            description="Controls the vertical movement of the build plate.",
            physical_vector={
                PhysicalProperty.MECHANICAL_MOTION: 0.9,
                PhysicalProperty.FLOW_STABILITY: 0.1
            }
        ),
        OntologyNode(
            node_id="3DP-002",
            name="Extruder Feed Rate Controller",
            domain=DomainType.PRINTING_3D,
            description="Adjusts filament feed speed to maintain constant flow.",
            physical_vector={
                PhysicalProperty.FLOW_STABILITY: 0.92, # 匹配点：维持流动
                PhysicalProperty.THERMAL_DYNAMICS: 0.7,
                PhysicalProperty.TENSION_DYNAMICS: 0.5 # 塑料在喷嘴处的粘滞力/阻力
            }
        )
    ]

    # 3. 初始化映射器
    mapper = CrossDomainMapper(similarity_threshold=0.7)

    # 4. 执行映射
    result = mapper.map_node(textile_tension_node, candidates)

    # 5. 输出结果
    if result:
        print("-" * 30)
        print("Mapping Successful!")
        print(f"Source: {textile_tension_node.name}")
        print(f"Target: {result['target_node_name']}")
        print(f"Score: {result['confidence']:.4f}")
        print("-" * 30)
        
        # 6. 生成迁移逻辑
        logic_advice = mapper.generate_control_logic_transfer(result)
        print(logic_advice)
    else:
        print("Mapping failed to find a suitable match.")