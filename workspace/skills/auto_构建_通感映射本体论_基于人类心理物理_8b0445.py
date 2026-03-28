"""
模块名称: auto_构建_通感映射本体论_基于人类心理物理_8b0445
描述: 本模块实现了基于人类心理物理学实验数据的通感映射本体论构建。
      它定义了跨模态感官转换（如听觉->视觉，触觉->听觉）的标准接口，
      并通过心理物理学曲线（如斯蒂文斯幂定律）确保转换的语义一致性。

作者: AGI System Core Engineer
版本: 1.0.0
"""

import logging
import json
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModalityType(Enum):
    """定义感官模态的枚举类型。"""
    AUDITORY = "auditory"
    VISUAL = "visual"
    TACTILE = "tactile"
    GUSTATORY = "gustatory"
    OLFACTORY = "olfactory"
    CONCEPTUAL = "conceptual"

class PsychophysicalValidationError(ValueError):
    """当输入数据不符合心理物理学约束时抛出的自定义异常。"""
    pass

@dataclass
class PsychophysicalRule:
    """
    心理物理学规则数据结构。
    
    属性:
        name: 规则名称 (e.g., 'StevensPowerLaw')
        exponent: 幂定律指数，决定感知强度与物理强度的关系。
        threshold: 绝对阈值，低于此值无法感知。
        saturation: 饱和度上限，高于此值感知不再增强。
    """
    name: str
    exponent: float = 1.0
    threshold: float = 0.0
    saturation: float = 100.0
    
    def validate(self) -> bool:
        if self.exponent <= 0:
            raise PsychophysicalValidationError("Exponent must be positive.")
        if self.threshold < 0 or self.saturation <= self.threshold:
            raise PsychophysicalValidationError("Invalid threshold/saturation range.")
        return True

@dataclass
class MappingNode:
    """
    通感映射本体论中的映射节点。
    
    属性:
        source_modality: 源模态。
        target_modality: 目标模态。
        semantic_tags: 描述映射语义的标签列表 (e.g., ['bright', 'high_pitch'])。
        rules: 应用的心理物理学规则。
        confidence: 映射的置信度 (0.0 - 1.0)。
    """
    source_modality: ModalityType
    target_modality: ModalityType
    semantic_tags: List[str]
    rules: PsychophysicalRule
    confidence: float = 0.8
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class SynesthesiaOntologyEngine:
    """
    通感映射本体论引擎。
    
    负责管理跨模态映射，应用心理物理学定律进行数据转换，
    并维护本体论的一致性。
    """

    def __init__(self, ontology_name: str = "DefaultSynesthesiaOntology"):
        """
        初始化引擎。

        Args:
            ontology_name: 本体论实例的名称。
        """
        self.ontology_name = ontology_name
        self._mapping_registry: Dict[str, MappingNode] = {}
        logger.info(f"Initialized Synesthesia Ontology Engine: {ontology_name}")

    def _generate_mapping_id(self, source: ModalityType, target: ModalityType) -> str:
        """
        辅助函数：生成唯一的映射ID。

        Args:
            source: 源模态。
            target: 目标模态。

        Returns:
            str: 唯一的映射标识符。
        """
        return f"{source.value}_to_{target.value}"

    def register_mapping_rule(
        self,
        source: ModalityType,
        target: ModalityType,
        rule_params: Dict[str, Any],
        semantic_tags: List[str]
    ) -> str:
        """
        核心函数 1: 注册一个新的通感映射规则。

        基于心理物理学参数定义如何将一种模态转换为另一种模态。

        Args:
            source: 源感官模态。
            target: 目标感官模态。
            rule_params: 包含心理物理学参数的字典 (exponent, threshold 等)。
            semantic_tags: 定义语义一致性的标签。

        Returns:
            str: 注册成功的映射ID。

        Raises:
            PsychophysicalValidationError: 如果参数无效。
        """
        logger.debug(f"Attempting to register mapping: {source} -> {target}")
        
        # 数据验证
        try:
            rule = PsychophysicalRule(**rule_params)
            rule.validate()
        except TypeError as e:
            logger.error(f"Invalid rule parameters: {e}")
            raise PsychophysicalValidationError(f"Invalid rule structure: {e}")
        
        mapping_id = self._generate_mapping_id(source, target)
        
        node = MappingNode(
            source_modality=source,
            target_modality=target,
            semantic_tags=semantic_tags,
            rules=rule,
            confidence=rule_params.get('confidence', 0.5)
        )
        
        self._mapping_registry[mapping_id] = node
        logger.info(f"Successfully registered mapping {mapping_id} with exponent {rule.exponent}")
        return mapping_id

    def transform_percept(
        self,
        source: ModalityType,
        target: ModalityType,
        input_intensity: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        核心函数 2: 执行跨模态感知转换。

        使用注册的心理物理学规则（主要是斯蒂文斯幂定律）将输入强度转换为输出强度。
        公式: R = k * (S - threshold)^exponent (简化实现)

        Args:
            source: 源模态。
            target: 目标模态。
            input_intensity: 输入刺激的物理强度。

        Returns:
            Tuple[float, Dict]: 
                - 转换后的感知强度。
                - 包含语义标签和元数据的字典。
        
        Raises:
            KeyError: 如果映射不存在。
            ValueError: 如果输入强度超出物理范围。
        """
        mapping_id = self._generate_mapping_id(source, target)
        
        if mapping_id not in self._mapping_registry:
            logger.error(f"Mapping not found: {mapping_id}")
            raise KeyError(f"No mapping rule defined for {source} to {target}")
            
        node = self._mapping_registry[mapping_id]
        rule = node.rules
        
        # 边界检查
        if input_intensity < 0:
            logger.warning("Negative intensity received, clamping to 0.")
            input_intensity = 0
            
        # 心理物理学逻辑处理 (阈值以下无感知)
        if input_intensity <= rule.threshold:
            perceived_intensity = 0.0
        else:
            # 应用斯蒂文斯幂定律 (简化版，假设 k=1)
            effective_intensity = input_intensity - rule.threshold
            perceived_intensity = effective_intensity ** rule.exponent
            
            # 饱和度检查
            if perceived_intensity > rule.saturation:
                logger.debug(f"Perception saturated at {rule.saturation}")
                perceived_intensity = rule.saturation
        
        metadata = {
            "semantic_context": node.semantic_tags,
            "confidence": node.confidence,
            "applied_rule": rule.name,
            "raw_output": perceived_intensity
        }
        
        logger.info(f"Transformed {source.value}({input_intensity}) -> {target.value}({perceived_intensity:.4f})")
        
        return perceived_intensity, metadata

    def export_ontology(self) -> str:
        """
        辅助函数: 将当前本体论状态导出为JSON字符串。
        
        Returns:
            str: JSON格式的本体论数据。
        """
        export_data = {
            "ontology_name": self.ontology_name,
            "mappings": []
        }
        
        for node in self._mapping_registry.values():
            # 使用 asdict 将 dataclass 转换为字典，处理 Enum 序列化
            node_dict = asdict(node)
            node_dict['source_modality'] = node.source_modality.value
            node_dict['target_modality'] = node.target_modality.value
            node_dict['rules'] = asdict(node.rules)
            export_data["mappings"].append(node_dict)
            
        return json.dumps(export_data, indent=4)

# 使用示例
if __name__ == "__main__":
    # 1. 初始化本体论引擎
    engine = SynesthesiaOntologyEngine("HumanCentric_SoundToLight")
    
    # 2. 定义映射规则：响度 -> 亮度
    # 心理学依据：较响的声音通常感知为较亮的光线 (非线性关系)
    # 假设 exponent 为 0.5 (平方根关系，模拟压缩)
    sound_to_light_params = {
        "name": "LoudnessBrightnessMapping",
        "exponent": 0.5,
        "threshold": 10.0,  # 10分贝以下忽略
        "saturation": 1000.0,
        "confidence": 0.85
    }
    
    try:
        # 注册映射
        map_id = engine.register_mapping_rule(
            source=ModalityType.AUDITORY,
            target=ModalityType.VISUAL,
            rule_params=sound_to_light_params,
            semantic_tags=["intensity_mapping", "crossmodal_bright"]
        )
        print(f"Registered mapping ID: {map_id}")
        
        # 3. 执行转换
        # 测试不同响度的声音
        test_intensities = [5.0, 50.0, 110.0] # 低于阈值，正常，接近饱和
        
        for intensity in test_intensities:
            brightness, meta = engine.transform_percept(
                source=ModalityType.AUDITORY,
                target=ModalityType.VISUAL,
                input_intensity=intensity
            )
            print(f"Input Sound: {intensity} -> Output Brightness: {brightness:.2f}")
            print(f"Meta: {meta}\n")
            
        # 4. 导出本体论
        # print(engine.export_ontology())
        
    except (PsychophysicalValidationError, KeyError) as e:
        print(f"Error: {e}")