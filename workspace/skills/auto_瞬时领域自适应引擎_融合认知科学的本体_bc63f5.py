"""
名称: auto_瞬时领域自适应引擎_融合认知科学的本体_bc63f5
描述: 【瞬时领域自适应引擎】融合认知科学的本体映射能力，使AI在面对完全陌生的技术栈时，
      能像人类专家一样进行‘类比推理’。通过构建'源域->目标域'的功能映射图，实现零样本
      环境下的快速适应。
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from difflib import SequenceMatcher

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OntologyNode:
    """
    本体节点数据结构，用于表示源域或目标域中的概念。
    
    Attributes:
        id (str): 节点唯一标识符
        name (str): 概念名称
        category (str): 概念类别 (如 'data_structure', 'operator', 'interface')
        properties (Dict[str, Any]): 概念的属性集合
        description (str): 概念描述
        embedding (Optional[List[float]]): 概念的向量嵌入 (用于相似度计算)
    """
    id: str
    name: str
    category: str
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        """数据验证"""
        if not self.id or not self.name:
            raise ValueError("节点ID和名称不能为空")
        if not isinstance(self.properties, dict):
            raise TypeError("属性必须是字典类型")

@dataclass
class MappingResult:
    """
    映射结果数据结构，包含源域到目标域的映射信息。
    
    Attributes:
        source_node (OntologyNode): 源域节点
        target_node (OntologyNode): 目标域节点
        similarity_score (float): 相似度得分 [0.0, 1.0]
        mapping_type (str): 映射类型 ('direct', 'structural', 'functional')
        confidence (float): 映射置信度
        reasoning_path (List[str]): 推理路径描述
    """
    source_node: OntologyNode
    target_node: OntologyNode
    similarity_score: float
    mapping_type: str
    confidence: float
    reasoning_path: List[str] = field(default_factory=list)

    def __post_init__(self):
        """数据验证和边界检查"""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError("相似度得分必须在 [0.0, 1.0] 范围内")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("置信度必须在 [0.0, 1.0] 范围内")
        if self.mapping_type not in ['direct', 'structural', 'functional']:
            raise ValueError("无效的映射类型")

class CognitiveOntologyEngine:
    """
    瞬时领域自适应引擎，融合认知科学的本体映射能力。
    
    该引擎通过类比推理机制，在零样本环境下实现跨领域知识迁移。
    核心功能包括：
    1. 本体结构相似度计算
    2. 基于认知科学的类比推理
    3. 源域到目标域的功能映射
    
    Example:
        >>> engine = CognitiveOntologyEngine()
        >>> source_knowledge = engine.load_knowledge_base("quantum_computing.json")
        >>> target_api = engine.parse_new_api("new_quantum_sdk_docs")
        >>> mappings = engine.adapt_domain(source_knowledge, target_api)
        >>> for mapping in mappings:
        ...     print(f"{mapping.source_node.name} -> {mapping.target_node.name}")
    """
    
    def __init__(self, similarity_threshold: float = 0.6, max_mappings: int = 10):
        """
        初始化自适应引擎。
        
        Args:
            similarity_threshold (float): 相似度阈值，低于此值的映射将被过滤
            max_mappings (int): 最大返回映射数量
        """
        self.similarity_threshold = similarity_threshold
        self.max_mappings = max_mappings
        self._knowledge_cache: Dict[str, Any] = {}
        self._mapping_history: List[MappingResult] = []
        
        logger.info(f"初始化认知本体引擎，相似度阈值: {similarity_threshold}")

    def load_knowledge_base(self, source_data: Dict[str, Any]) -> List[OntologyNode]:
        """
        加载源域知识库，构建本体节点列表。
        
        Args:
            source_data (Dict): 包含知识库数据的字典，格式如下：
                {
                    "concepts": [
                        {
                            "id": "qubit",
                            "name": "量子比特",
                            "category": "data_structure",
                            "properties": {"stateful": True, "quantum": True},
                            "description": "量子计算的基本单位"
                        },
                        ...
                    ]
                }
        
        Returns:
            List[OntologyNode]: 本体节点列表
            
        Raises:
            ValueError: 如果输入数据格式无效
        """
        if not source_data or "concepts" not in source_data:
            raise ValueError("无效的知识库数据格式")
        
        nodes = []
        for concept in source_data["concepts"]:
            try:
                node = OntologyNode(
                    id=concept.get("id", self._generate_id(concept["name"])),
                    name=concept["name"],
                    category=concept.get("category", "unknown"),
                    properties=concept.get("properties", {}),
                    description=concept.get("description", ""),
                    embedding=concept.get("embedding")
                )
                nodes.append(node)
            except (KeyError, ValueError) as e:
                logger.warning(f"跳过无效概念节点: {e}")
                continue
        
        # 缓存知识库
        cache_key = self._generate_cache_key(source_data)
        self._knowledge_cache[cache_key] = nodes
        logger.info(f"成功加载 {len(nodes)} 个本体节点到知识库")
        
        return nodes

    def adapt_domain(
        self,
        source_nodes: List[OntologyNode],
        target_nodes: List[OntologyNode],
        context: Optional[Dict[str, Any]] = None
    ) -> List[MappingResult]:
        """
        执行领域自适应，构建源域到目标域的本体映射。
        
        这是核心函数，通过三阶段处理实现认知映射：
        1. 结构分析：分析源域和目标域的本体结构
        2. 类比推理：基于认知科学原理进行相似度计算
        3. 映射构建：生成高置信度的映射关系
        
        Args:
            source_nodes (List[OntologyNode]): 源域本体节点列表
            target_nodes (List[OntologyNode]): 目标域本体节点列表
            context (Optional[Dict]): 上下文信息，可能影响映射策略
            
        Returns:
            List[MappingResult]: 排序后的映射结果列表
            
        Raises:
            ValueError: 如果输入节点列表为空
        """
        if not source_nodes or not target_nodes:
            raise ValueError("源域和目标域节点列表不能为空")
        
        logger.info(f"开始领域自适应: 源域 {len(source_nodes)} 节点, 目标域 {len(target_nodes)} 节点")
        
        # 阶段1: 结构分析
        source_structure = self._analyze_ontology_structure(source_nodes)
        target_structure = self._analyze_ontology_structure(target_nodes)
        
        # 阶段2: 类比推理
        candidate_mappings = []
        
        for s_node in source_nodes:
            for t_node in target_nodes:
                # 计算综合相似度
                similarity = self._calculate_similarity(s_node, t_node, source_structure, target_structure)
                
                if similarity >= self.similarity_threshold:
                    # 确定映射类型
                    mapping_type = self._determine_mapping_type(s_node, t_node, similarity)
                    
                    # 生成推理路径
                    reasoning_path = self._generate_reasoning_path(s_node, t_node, mapping_type)
                    
                    # 计算置信度
                    confidence = self._calculate_confidence(s_node, t_node, similarity, context)
                    
                    mapping = MappingResult(
                        source_node=s_node,
                        target_node=t_node,
                        similarity_score=similarity,
                        mapping_type=mapping_type,
                        confidence=confidence,
                        reasoning_path=reasoning_path
                    )
                    candidate_mappings.append(mapping)
        
        # 阶段3: 映射优化和排序
        optimized_mappings = self._optimize_mappings(candidate_mappings)
        
        # 记录映射历史
        self._mapping_history.extend(optimized_mappings[:self.max_mappings])
        
        logger.info(f"生成 {len(optimized_mappings)} 个有效映射")
        return optimized_mappings[:self.max_mappings]

    def _calculate_similarity(
        self,
        source: OntologyNode,
        target: OntologyNode,
        source_structure: Dict,
        target_structure: Dict
    ) -> float:
        """
        计算两个本体节点之间的综合相似度。
        
        综合考虑以下因素：
        1. 名称相似度 (基于字符串匹配)
        2. 类别匹配度
        3. 属性重合度
        4. 上下文结构相似度
        
        Args:
            source (OntologyNode): 源域节点
            target (OntologyNode): 目标域节点
            source_structure (Dict): 源域结构分析结果
            target_structure (Dict): 目标域结构分析结果
            
        Returns:
            float: 综合相似度得分 [0.0, 1.0]
        """
        # 1. 名称相似度 (权重: 0.3)
        name_similarity = SequenceMatcher(None, source.name.lower(), target.name.lower()).ratio()
        
        # 2. 类别匹配度 (权重: 0.25)
        category_similarity = 1.0 if source.category == target.category else 0.0
        
        # 3. 属性重合度 (权重: 0.25)
        source_props = set(source.properties.keys())
        target_props = set(target.properties.keys())
        
        if source_props or target_props:
            property_similarity = len(source_props & target_props) / len(source_props | target_props)
        else:
            property_similarity = 0.0
        
        # 4. 结构上下文相似度 (权重: 0.2)
        structure_similarity = self._calculate_structural_similarity(
            source, target, source_structure, target_structure
        )
        
        # 加权综合
        weights = [0.3, 0.25, 0.25, 0.2]
        similarities = [name_similarity, category_similarity, property_similarity, structure_similarity]
        
        total_similarity = sum(w * s for w, s in zip(weights, similarities))
        
        logger.debug(
            f"相似度计算: {source.name} vs {target.name} -> "
            f"名称:{name_similarity:.2f}, 类别:{category_similarity:.2f}, "
            f"属性:{property_similarity:.2f}, 结构:{structure_similarity:.2f}, "
            f"综合:{total_similarity:.2f}"
        )
        
        return total_similarity

    def _analyze_ontology_structure(self, nodes: List[OntologyNode]) -> Dict[str, Any]:
        """
        分析本体结构，提取统计特征和关系模式。
        
        Args:
            nodes (List[OntologyNode]): 本体节点列表
            
        Returns:
            Dict: 结构分析结果，包含：
                - category_distribution: 类别分布
                - property_patterns: 属性模式
                - complexity_metrics: 复杂度指标
        """
        category_dist = {}
        property_patterns = {}
        total_properties = 0
        
        for node in nodes:
            # 统计类别分布
            category = node.category
            category_dist[category] = category_dist.get(category, 0) + 1
            
            # 统计属性模式
            for prop in node.properties.keys():
                property_patterns[prop] = property_patterns.get(prop, 0) + 1
                total_properties += 1
        
        # 计算复杂度指标
        avg_properties = total_properties / len(nodes) if nodes else 0
        
        return {
            "category_distribution": category_dist,
            "property_patterns": property_patterns,
            "complexity_metrics": {
                "total_nodes": len(nodes),
                "avg_properties": avg_properties,
                "unique_categories": len(category_dist)
            }
        }

    def _calculate_structural_similarity(
        self,
        source: OntologyNode,
        target: OntologyNode,
        source_structure: Dict,
        target_structure: Dict
    ) -> float:
        """
        计算结构上下文相似度，基于节点在各自领域中的位置和关系。
        
        Args:
            source, target: 待比较的节点
            source_structure, target_structure: 结构分析结果
            
        Returns:
            float: 结构相似度 [0.0, 1.0]
        """
        # 比较节点在各自类别中的普遍性
        source_cat_freq = source_structure["category_distribution"].get(source.category, 0)
        target_cat_freq = target_structure["category_distribution"].get(target.category, 0)
        
        max_freq = max(
            max(source_structure["category_distribution"].values()),
            max(target_structure["category_distribution"].values())
        ) if source_structure["category_distribution"] else 1
        
        # 归一化频率差异
        freq_diff = abs(source_cat_freq - target_cat_freq) / max_freq
        freq_similarity = 1.0 - freq_diff
        
        # 比较属性模式相似性
        source_props = set(source.properties.keys())
        target_props = set(target.properties.keys())
        
        common_props = source_props & target_props
        all_props = source_props | target_props
        
        if all_props:
            pattern_similarity = len(common_props) / len(all_props)
        else:
            pattern_similarity = 0.5  # 无属性时的中性值
        
        return (freq_similarity + pattern_similarity) / 2

    def _determine_mapping_type(self, source: OntologyNode, target: OntologyNode, similarity: float) -> str:
        """
        根据节点特征和相似度确定映射类型。
        
        Args:
            source, target: 映射的源节点和目标节点
            similarity: 相似度得分
            
        Returns:
            str: 映射类型 ('direct', 'structural', 'functional')
        """
        # 高相似度且类别相同 -> 直接映射
        if similarity > 0.85 and source.category == target.category:
            return "direct"
        
        # 结构特征相似 -> 结构映射
        source_prop_count = len(source.properties)
        target_prop_count = len(target.properties)
        
        if abs(source_prop_count - target_prop_count) <= 1:
            return "structural"
        
        # 其他情况 -> 功能映射
        return "functional"

    def _generate_reasoning_path(self, source: OntologyNode, target: OntologyNode, mapping_type: str) -> List[str]:
        """
        生成人类可读的推理路径，解释为什么这两个概念可以映射。
        
        Args:
            source, target: 映射的节点
            mapping_type: 映射类型
            
        Returns:
            List[str]: 推理步骤列表
        """
        path = []
        
        # 步骤1: 识别共同点
        common_category = source.category == target.category
        if common_category:
            path.append(f"识别到相同类别: '{source.category}'")
        
        # 步骤2: 属性对比
        common_props = set(source.properties.keys()) & set(target.properties.keys())
        if common_props:
            path.append(f"共享属性: {', '.join(common_props)}")
        
        # 步骤3: 类比推理
        if mapping_type == "direct":
            path.append(f"直接类比: '{source.name}' 在目标域中对应 '{target.name}'")
        elif mapping_type == "structural":
            path.append(f"结构类比: '{source.name}' 和 '{target.name}' 具有相似的结构角色")
        else:
            path.append(f"功能类比: '{source.name}' 的功能可由 '{target.name}' 实现")
        
        # 步骤4: 上下文推断
        if source.description and target.description:
            path.append("基于描述语义的相似性进行映射")
        
        return path

    def _calculate_confidence(
        self,
        source: OntologyNode,
        target: OntologyNode,
        similarity: float,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """
        计算映射的置信度，考虑证据强度和上下文支持。
        
        Args:
            source, target: 映射的节点
            similarity: 相似度得分
            context: 可选的上下文信息
            
        Returns:
            float: 置信度 [0.0, 1.0]
        """
        # 基础置信度 = 相似度
        confidence = similarity
        
        # 证据强度调整
        evidence_strength = 0.0
        
        # 有描述信息增加置信度
        if source.description and target.description:
            evidence_strength += 0.1
        
        # 有属性信息增加置信度
        if source.properties and target.properties:
            evidence_strength += 0.1
        
        # 类别匹配增加置信度
        if source.category == target.category:
            evidence_strength += 0.15
        
        # 上下文支持
        if context and "supporting_evidence" in context:
            evidence_strength += context["supporting_evidence"].get(f"{source.id}_{target.id}", 0)
        
        # 综合置信度 (限制在 [0, 1])
        confidence = min(1.0, confidence + evidence_strength)
        
        return round(confidence, 3)

    def _optimize_mappings(self, mappings: List[MappingResult]) -> List[MappingResult]:
        """
        优化映射结果，去除冲突并保持一致性。
        
        Args:
            mappings (List[MappingResult]): 候选映射列表
            
        Returns:
            List[MappingResult]: 优化后的映射列表
        """
        # 按相似度和置信度排序
        sorted_mappings = sorted(
            mappings,
            key=lambda m: (m.similarity_score * 0.6 + m.confidence * 0.4),
            reverse=True
        )
        
        # 去重: 每个源节点只保留最佳映射
        seen_sources = set()
        unique_mappings = []
        
        for mapping in sorted_mappings:
            if mapping.source_node.id not in seen_sources:
                unique_mappings.append(mapping)
                seen_sources.add(mapping.source_node.id)
        
        return unique_mappings

    def _generate_id(self, name: str) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().isoformat()
        hash_input = f"{name}_{timestamp}".encode()
        return hashlib.md5(hash_input).hexdigest()[:12]

    def _generate_cache_key(self, data: Dict) -> str:
        """生成缓存键"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def export_mappings(self, format: str = "json") -> str:
        """
        导出映射历史记录。
        
        Args:
            format (str): 导出格式 ('json', 'csv')
            
        Returns:
            str: 格式化的映射数据
        """
        if format == "json":
            export_data = []
            for mapping in self._mapping_history:
                export_data.append({
                    "source": asdict(mapping.source_node),
                    "target": asdict(mapping.target_node),
                    "similarity": mapping.similarity_score,
                    "type": mapping.mapping_type,
                    "confidence": mapping.confidence,
                    "reasoning": mapping.reasoning_path
                })
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

# 使用示例
if __name__ == "__main__":
    # 示例: 量子计算 SDK -> 新量子 SDK 的领域自适应
    
    # 1. 初始化引擎
    engine = CognitiveOntologyEngine(similarity_threshold=0.5, max_mappings=5)
    
    # 2. 准备源域知识 (已知量子计算概念)
    source_knowledge = {
        "concepts": [
            {
                "id": "qubit",
                "name": "Quantum Bit",
                "category": "data_structure",
                "properties": {"stateful": True, "superposition": True, "entanglement": True},
                "description": "量子计算的基本信息单位"
            },
            {
                "id": "quantum_gate",
                "name": "Quantum Gate",
                "category": "operator",
                "properties": {"reversible": True, "unitary": True},
                "description": "对量子比特进行操作的基本单元"
            },
            {
                "id": "quantum_circuit",
                "name": "Quantum Circuit",
                "category": "interface",
                "properties": {"sequential": True, "composed_of_gates": True},
                "description": "量子门的序列组合"
            }
        ]
    }
    
    # 3. 准备目标域 API (新量子 SDK)
    target_api = {
        "concepts": [
            {
                "id": "qb",
                "name": "Qubit",
                "category": "data_structure",
                "properties": {"stateful": True, "quantum": True},
                "description": "新SDK中的量子比特表示"
            },
            {
                "id": "gate_op",
                "name": "Gate Operator",
                "category": "operator",
                "properties": {"reversible": True, "matrix_form": True},
                "description": "量子门操作"
            },
            {
                "id": "circuit_builder",
                "name": "Circuit Builder",
                "category": "interface",
                "properties": {"builder_pattern": True, "chainable": True},
                "description": "用于构建量子电路的接口"
            }
        ]
    }
    
    # 4. 加载知识库
    source_nodes = engine.load_knowledge_base(source_knowledge)
    target_nodes = engine.load_knowledge_base(target_api)
    
    # 5. 执行领域自适应
    mappings = engine.adapt_domain(source_nodes, target_nodes)
    
    # 6. 输出映射结果
    print("\n=== 领域自适应映射结果 ===")
    for i, mapping in enumerate(mappings, 1):
        print(f"\n映射 #{i}:")
        print(f"  源域: {mapping.source_node.name} ({mapping.source_node.category})")
        print(f"  目标域: {mapping.target_node.name} ({mapping.target_node.category})")
        print(f"  相似度: {mapping.similarity_score:.2f}")
        print(f"  置信度: {mapping.confidence:.2f}")
        print(f"  类型: {mapping.mapping_type}")
        print(f"  推理路径:")
        for step in mapping.reasoning_path:
            print(f"    - {step}")
    
    # 7. 导出映射
    print("\n=== JSON 导出 ===")
    print(engine.export_mappings())