"""
名称: auto_跨域迁移能力验证_验证_左右跨域重叠_51a9e9
描述: 【跨域迁移能力验证】验证'左右跨域重叠'的认知能力。随机抽取两个极不相关的已有节点（例如'微服务架构'与'番茄种植'），要求AI构建一个有实际商业价值的融合创新方案（如'基于植物生长节律的自愈型微服务'）。评估该方案是否包含具体的'真实节点'而非空洞的比喻。
领域: cognitive_science
"""

import logging
import json
import random
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识
        name (str): 节点名称
        domain (str): 所属领域
        attributes (List[str]): 节点的具体属性或机制列表
        created_at (str): 创建时间
    """
    id: str
    name: str
    domain: str
    attributes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "attributes": self.attributes,
            "created_at": self.created_at
        }

@dataclass
class FusionScheme:
    """
    融合方案数据结构。
    
    Attributes:
        source_nodes (Tuple[str, str]): 参与融合的两个源节点名称
        scheme_name (str): 新方案的名称
        description (str): 详细描述
        core_mechanisms (List[str]): 核心机制（必须包含具体属性）
        commercial_value (str): 商业价值描述
        is_valid (bool): 是否通过验证
        reason (str): 验证结果原因
    """
    source_nodes: Tuple[str, str]
    scheme_name: str
    description: str
    core_mechanisms: List[str]
    commercial_value: str
    is_valid: bool = False
    reason: str = ""

class CrossDomainValidator:
    """
    跨域迁移能力验证器。
    
    用于评估系统在两个极不相关概念之间构建实质性创新方案的能力。
    验证核心在于确保方案包含'真实节点'（具体机制）而非空洞比喻。
    
    Usage Example:
        >>> validator = CrossDomainValidator()
        >>> node_a = KnowledgeNode("1", "微服务架构", "CS", ["服务发现", "熔断降级"])
        >>> node_b = KnowledgeNode("2", "番茄种植", "Agriculture", ["光合作用", "根系压力"])
        >>> validator.load_concepts([node_a, node_b])
        >>> result = validator.validate_fusion("植物微服务", "利用光合作用机制...", ["根系服务发现"])
        >>> print(result.is_valid)
    """
    
    def __init__(self, min_attribute_length: int = 3):
        """
        初始化验证器。
        
        Args:
            min_attribute_length (int): 属性描述的最小长度，用于过滤空洞词汇
        """
        self.knowledge_base: List[KnowledgeNode] = []
        self.min_attr_len = min_attribute_length
        self._stopwords = {"的", "和", "与", "及", "等", "了", "在", "是", "一种", "一个"}
        logger.info("CrossDomainValidator initialized.")

    def load_concepts(self, concepts: List[KnowledgeNode]) -> None:
        """
        加载知识概念节点库。
        
        Args:
            concepts (List[KnowledgeNode]): 知识节点列表
            
        Raises:
            ValueError: 如果概念列表为空或无效
        """
        if not concepts or not isinstance(concepts, list):
            error_msg = "Concepts list cannot be empty and must be a list."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.knowledge_base = concepts
        logger.info(f"Loaded {len(concepts)} concepts into knowledge base.")

    def select_disparate_nodes(self) -> Tuple[KnowledgeNode, KnowledgeNode]:
        """
        随机选择两个领域差异最大的节点。
        
        Returns:
            Tuple[KnowledgeNode, KnowledgeNode]: 两个不相关的知识节点
            
        Raises:
            ValueError: 如果知识库中节点不足
        """
        if len(self.knowledge_base) < 2:
            error_msg = "Insufficient nodes in knowledge base for selection."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 简单的随机抽取，实际应用中可引入向量嵌入计算领域距离
        samples = random.sample(self.knowledge_base, 2)
        logger.info(f"Selected nodes: '{samples[0].name}' ({samples[0].domain}) and '{samples[1].name}' ({samples[1].domain})")
        return samples[0], samples[1]

    def _extract_real_nodes(self, text: str, source_attrs: List[str]) -> List[str]:
        """
        辅助函数：提取文本中映射到的具体属性（真实节点）。
        
        Args:
            text (str): 待分析的文本
            source_attrs (List[str]): 源节点的属性列表
            
        Returns:
            List[str]: 匹配到的真实属性列表
        """
        found_attrs = []
        # 模拟NLP匹配过程：检查源属性是否显式出现在文本中
        # 或者检查文本中的名词短语是否具有具体含义（简化为长度和停用词检查）
        
        # 1. 直接属性匹配
        for attr in source_attrs:
            if attr in text:
                found_attrs.append(attr)
        
        # 2. 提取引号或特定格式的内容作为具体机制
        # 这里模拟AI生成方案时对具体机制的格式化输出
        # 假设具体机制通常包含具体的动词或名词，而非抽象概念
        return list(set(found_attrs))

    def validate_fusion(
        self, 
        scheme_name: str, 
        description: str, 
        core_mechanisms: List[str],
        commercial_value: str
    ) -> FusionScheme:
        """
        验证融合方案的质量。
        
        核心逻辑：
        1. 检查方案是否包含源领域的具体属性（非比喻）。
        2. 检查商业价值描述是否具体。
        
        Args:
            scheme_name (str): 方案名称
            description (str): 方案描述
            core_mechanisms (List[str]): 提出的核心机制列表
            commercial_value (str): 商业价值描述
            
        Returns:
            FusionScheme: 包含验证结果的对象
        """
        if not self.knowledge_base:
            logger.warning("Validation attempted with empty knowledge base.")
            return FusionScheme(
                ("N/A", "N/A"), scheme_name, description, core_mechanisms, 
                commercial_value, False, "Knowledge base empty"
            )

        # 获取源节点的所有属性用于验证
        all_source_attrs = []
        for node in self.knowledge_base:
            all_source_attrs.extend(node.attributes)

        # 数据清洗：过滤掉过短或停用词的机制
        valid_mechanisms = [
            m for m in core_mechanisms 
            if len(m) >= self.min_attr_len and m not in self._stopwords
        ]

        # 检查是否有实质性内容
        if not valid_mechanisms:
            return FusionScheme(
                tuple(n.name for n in self.knowledge_base[:2]),
                scheme_name, description, core_mechanisms, commercial_value,
                False, "Core mechanisms are empty or only contain stop words."
            )

        # 验证"真实节点"：检查核心机制是否引用了具体的源属性或具体的实现逻辑
        # 这里简化为检查是否包含源属性词汇，或者是否有具体的复合词
        has_real_connection = False
        detected_real_nodes = []
        
        full_text = f"{description} {' '.join(core_mechanisms)}"
        
        for attr in all_source_attrs:
            if attr in full_text:
                has_real_connection = True
                detected_real_nodes.append(attr)
        
        # 简单的启发式规则：如果没有任何源领域的具体术语，可能只是空洞的比喻
        if not has_real_connection:
            # 也可以检查是否有具体的数字、代码名等，这里略过
            reason = "No specific attributes from source domains were mapped. The scheme appears abstract."
            logger.warning(f"Validation Failed: {reason}")
            return FusionScheme(
                tuple(n.name for n in self.knowledge_base[:2]),
                scheme_name, description, core_mechanisms, commercial_value,
                False, reason
            )

        # 检查商业价值是否具体（不能只是"很有用"）
        if len(commercial_value) < 20:
            reason = "Commercial value description is too vague."
            logger.warning(f"Validation Failed: {reason}")
            return FusionScheme(
                tuple(n.name for n in self.knowledge_base[:2]),
                scheme_name, description, core_mechanisms, commercial_value,
                False, reason
            )

        logger.info(f"Validation Passed for scheme: {scheme_name}")
        return FusionScheme(
            tuple(n.name for n in self.knowledge_base[:2]),
            scheme_name, description, core_mechanisms, commercial_value,
            True, "Valid fusion with concrete node mapping."
        )

# 示例数据与使用演示
if __name__ == "__main__":
    # 1. 准备极不相关的知识节点
    node_cs = KnowledgeNode(
        id="cs_01", 
        name="微服务架构", 
        domain="Computer Science",
        attributes=["服务熔断", "独立部署", "API网关", "去中心化", "负载均衡"]
    )
    
    node_bio = KnowledgeNode(
        id="bio_01", 
        name="番茄种植", 
        domain="Agriculture",
        attributes=["根系透气", "光合作用", "打顶修剪", "病虫害抗性", "水肥一体化"]
    )
    
    node_finance = KnowledgeNode(
        id="fin_01",
        name="高频交易",
        domain="Finance",
        attributes=["延迟套利", "订单簿深度", "波动率", "流动性挖矿"]
    )

    # 2. 初始化验证器
    validator = CrossDomainValidator()
    validator.load_concepts([node_cs, node_bio, node_finance])
    
    # 3. 模拟生成与验证过程
    
    # 案例A: 一个高质量的融合方案（包含真实节点映射）
    # 概念：微服务 + 番茄种植
    # 思路：利用"打顶修剪"概念优化微服务数量，利用"根系透气"优化数据库连接池
    good_scheme_name = "生态自适应微服务治理系统"
    good_desc = "借鉴番茄种植中的'打顶修剪'机制，自动识别并关闭冗余的微服务实例以节省资源。同时引入'根系透气'概念优化数据库连接池。"
    good_mechanisms = [
        "基于打顶修剪的服务实例裁剪算法",
        "模拟根系透气的高并发连接池管理"
    ]
    good_value = "预计降低30%的计算资源浪费，并在高负载下保持数据库连接的稳定性。"
    
    print("\n--- Testing Good Scheme ---")
    result_good = validator.validate_fusion(
        good_scheme_name, good_desc, good_mechanisms, good_value
    )
    print(f"Result: {result_good.is_valid}, Reason: {result_good.reason}")
    
    # 案例B: 一个低质量的融合方案（空洞比喻）
    bad_scheme_name = "像种番茄一样写代码"
    bad_desc = "让代码像植物一样生长，充满生命力，只要浇水就能跑。"
    bad_mechanisms = ["生命力驱动", "自然生长"]
    bad_value = "让开发过程更快乐。"
    
    print("\n--- Testing Bad Scheme ---")
    result_bad = validator.validate_fusion(
        bad_scheme_name, bad_desc, bad_mechanisms, bad_value
    )
    print(f"Result: {result_bad.is_valid}, Reason: {result_bad.reason}")