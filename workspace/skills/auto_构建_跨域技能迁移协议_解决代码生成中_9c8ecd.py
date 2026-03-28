"""
跨域技能迁移协议模块

本模块实现了跨域技能迁移协议，用于解决代码生成中的参数缺省问题。
当人类意图涉及未知领域时（如'像处理文本一样处理音频'），系统需提取源领域
（文本处理）的拓扑结构，并将其映射到目标领域（音频）。重点在于验证抽象逻辑
（如Map-Reduce）能否在不同数据模态的节点间自动迁移并生成可执行代码。

主要功能:
- 提取源领域技能的拓扑结构
- 将技能映射到目标领域
- 生成可执行代码
- 验证迁移后的技能

作者: AGI System
版本: 1.0.0
创建时间: 2023-11-15
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto
import inspect
import textwrap
import json
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skill_transfer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataModality(Enum):
    """数据模态枚举，定义不同的数据类型"""
    TEXT = auto()
    AUDIO = auto()
    IMAGE = auto()
    VIDEO = auto()
    TABULAR = auto()
    TIME_SERIES = auto()
    GRAPH = auto()
    UNKNOWN = auto()

@dataclass
class SkillParameter:
    """技能参数数据结构"""
    name: str
    param_type: str
    default_value: Any = None
    description: str = ""
    required: bool = True
    validation_rules: Optional[Dict[str, Any]] = None

@dataclass
class SkillNode:
    """技能节点数据结构"""
    name: str
    description: str
    input_modality: DataModality
    output_modality: DataModality
    parameters: List[SkillParameter]
    dependencies: List[str]  # 依赖的其他技能节点名称
    implementation_hint: Optional[str] = None

class SkillTransferProtocol:
    """
    跨域技能迁移协议主类
    
    该类实现了从源领域到目标领域的技能迁移逻辑，包括:
    1. 技能拓扑结构的提取
    2. 参数映射和缺省值处理
    3. 跨域映射逻辑
    4. 可执行代码生成
    
    示例:
        >>> protocol = SkillTransferProtocol()
        >>> source_skill = SkillNode(...)
        >>> target_modality = DataModality.AUDIO
        >>> transferred_skill = protocol.transfer_skill(source_skill, target_modality)
    """
    
    def __init__(self):
        """初始化技能迁移协议"""
        self.modality_mapping_rules = self._initialize_modality_mapping_rules()
        self.parameter_adapters = self._initialize_parameter_adapters()
        self.skill_registry = defaultdict(dict)
        logger.info("SkillTransferProtocol initialized successfully")
    
    def _initialize_modality_mapping_rules(self) -> Dict[Tuple[DataModality, DataModality], Dict]:
        """
        初始化模态间的映射规则
        
        返回:
            Dict: 模态映射规则字典，格式为 {(源模态, 目标模态): 映射规则}
        """
        rules = {
            (DataModality.TEXT, DataModality.AUDIO): {
                'tokenization': 'audio_segmentation',
                'vocabulary': 'frequency_bins',
                'embedding': 'spectrogram',
                'sequence_length': 'audio_duration',
                'padding': 'silence_padding',
                'normalization': 'audio_normalization'
            },
            (DataModality.TEXT, DataModality.IMAGE): {
                'tokenization': 'image_segmentation',
                'vocabulary': 'color_histogram',
                'embedding': 'feature_map',
                'sequence_length': 'image_size',
                'padding': 'border_padding',
                'normalization': 'pixel_normalization'
            },
            # 可以添加更多模态间的映射规则
        }
        logger.debug("Modality mapping rules initialized")
        return rules
    
    def _initialize_parameter_adapters(self) -> Dict[str, Callable]:
        """
        初始化参数适配器，用于处理不同模态间的参数转换
        
        返回:
            Dict: 参数适配器字典，格式为 {参数名: 适配函数}
        """
        adapters = {
            'sequence_length': self._adapt_sequence_length,
            'vocabulary_size': self._adapt_vocabulary_size,
            'embedding_dim': self._adapt_embedding_dim,
            'batch_size': self._adapt_batch_size,
            'normalization': self._adapt_normalization
        }
        logger.debug("Parameter adapters initialized")
        return adapters
    
    def _adapt_sequence_length(self, source_value: int, source_modality: DataModality, 
                              target_modality: DataModality) -> Union[int, float]:
        """
        适配序列长度参数到目标模态
        
        参数:
            source_value: 源模态的序列长度值
            source_modality: 源数据模态
            target_modality: 目标数据模态
            
        返回:
            Union[int, float]: 适配后的序列长度值
            
        异常:
            ValueError: 如果模态组合不受支持
        """
        if source_modality == DataModality.TEXT and target_modality == DataModality.AUDIO:
            # 将文本长度转换为音频持续时间（假设平均每秒2.5个词）
            return source_value / 2.5
        elif source_modality == DataModality.TEXT and target_modality == DataModality.IMAGE:
            # 将文本长度转换为图像尺寸（正方形图像的边长）
            return int(source_value ** 0.5) + 1
        else:
            logger.warning(f"No adaptation rule for sequence_length from {source_modality} to {target_modality}")
            return source_value
    
    def _adapt_vocabulary_size(self, source_value: int, source_modality: DataModality, 
                              target_modality: DataModality) -> int:
        """适配词汇表大小参数到目标模态"""
        if source_modality == DataModality.TEXT and target_modality == DataModality.AUDIO:
            # 将词汇表大小转换为频率箱数量
            return min(source_value * 10, 4096)  # 上限4096个频率箱
        elif source_modality == DataModality.TEXT and target_modality == DataModality.IMAGE:
            # 将词汇表大小转换为颜色直方图箱数
            return min(source_value * 3, 256)  # 上限256个颜色箱
        else:
            logger.warning(f"No adaptation rule for vocabulary_size from {source_modality} to {target_modality}")
            return source_value
    
    def _adapt_embedding_dim(self, source_value: int, source_modality: DataModality, 
                            target_modality: DataModality) -> int:
        """适配嵌入维度参数到目标模态"""
        if source_modality == DataModality.TEXT and target_modality == DataModality.AUDIO:
            # 将文本嵌入维度转换为频谱图维度
            return source_value * 2
        elif source_modality == DataModality.TEXT and target_modality == DataModality.IMAGE:
            # 将文本嵌入维度转换为特征图通道数
            return min(source_value * 4, 512)  # 上限512个通道
        else:
            logger.warning(f"No adaptation rule for embedding_dim from {source_modality} to {target_modality}")
            return source_value
    
    def _adapt_batch_size(self, source_value: int, source_modality: DataModality, 
                         target_modality: DataModality) -> int:
        """适配批量大小参数到目标模态"""
        # 通常批量大小可以保持不变，但某些模态可能需要调整
        if target_modality in [DataModality.VIDEO, DataModality.AUDIO]:
            # 音频和视频处理可能需要较小的批量大小
            return min(source_value, 32)
        return source_value
    
    def _adapt_normalization(self, source_value: str, source_modality: DataModality, 
                           target_modality: DataModality) -> str:
        """适配归一化参数到目标模态"""
        norm_mapping = {
            (DataModality.TEXT, DataModality.AUDIO): {
                'layer_norm': 'instance_norm',
                'batch_norm': 'batch_norm',
                'min_max': 'log_scaling'
            },
            (DataModality.TEXT, DataModality.IMAGE): {
                'layer_norm': 'batch_norm',
                'batch_norm': 'instance_norm',
                'min_max': 'min_max'
            }
        }
        
        key = (source_modality, target_modality)
        if key in norm_mapping and source_value in norm_mapping[key]:
            return norm_mapping[key][source_value]
        return source_value
    
    def _extract_skill_topology(self, skill: SkillNode) -> Dict:
        """
        提取技能的拓扑结构
        
        参数:
            skill: 要提取拓扑结构的技能节点
            
        返回:
            Dict: 技能的拓扑结构表示，包括:
                - name: 技能名称
                - description: 技能描述
                - input_modality: 输入模态
                - output_modality: 输出模态
                - parameters: 参数字典
                - dependencies: 依赖列表
        """
        if not isinstance(skill, SkillNode):
            logger.error("Invalid skill type provided")
            raise TypeError("Expected SkillNode instance")
            
        topology = {
            'name': skill.name,
            'description': skill.description,
            'input_modality': skill.input_modality,
            'output_modality': skill.output_modality,
            'parameters': {p.name: {
                'type': p.param_type,
                'default': p.default_value,
                'description': p.description,
                'required': p.required,
                'validation': p.validation_rules
            } for p in skill.parameters},
            'dependencies': skill.dependencies,
            'implementation_hint': skill.implementation_hint
        }
        
        logger.debug(f"Extracted topology for skill '{skill.name}'")
        return topology
    
    def _map_parameters(self, source_params: Dict[str, Any], 
                       source_modality: DataModality, 
                       target_modality: DataModality) -> Dict[str, Any]:
        """
        将参数从源模态映射到目标模态
        
        参数:
            source_params: 源模态的参数字典
            source_modality: 源数据模态
            target_modality: 目标数据模态
            
        返回:
            Dict: 映射后的参数字典
            
        异常:
            ValueError: 如果模态组合不受支持或参数无效
        """
        mapped_params = {}
        
        for param_name, param_value in source_params.items():
            if param_name in self.parameter_adapters:
                try:
                    adapter = self.parameter_adapters[param_name]
                    if callable(adapter):
                        mapped_params[param_name] = adapter(
                            param_value, source_modality, target_modality
                        )
                        logger.debug(f"Adapted parameter '{param_name}': {param_value} -> {mapped_params[param_name]}")
                except Exception as e:
                    logger.error(f"Error adapting parameter '{param_name}': {str(e)}")
                    mapped_params[param_name] = param_value  # 保持原值作为回退
            else:
                # 对于没有特定适配器的参数，保持原值
                mapped_params[param_name] = param_value
                logger.debug(f"Kept original value for parameter '{param_name}'")
        
        return mapped_params
    
    def _validate_parameters(self, params: Dict[str, Any], 
                            validation_rules: Dict[str, Dict]) -> bool:
        """
        验证参数是否符合给定的验证规则
        
        参数:
            params: 要验证的参数字典
            validation_rules: 验证规则字典
            
        返回:
            bool: 参数是否有效
        """
        for param_name, rules in validation_rules.items():
            if param_name not in params:
                if rules.get('required', False):
                    logger.error(f"Missing required parameter: {param_name}")
                    return False
                continue
                
            param_value = params[param_name]
            
            # 类型检查
            if 'type' in rules and not isinstance(param_value, eval(rules['type'])):
                logger.error(f"Parameter '{param_name}' has wrong type. Expected {rules['type']}, got {type(param_value)}")
                return False
                
            # 范围检查
            if 'min' in rules and param_value < rules['min']:
                logger.error(f"Parameter '{param_name}' is below minimum value {rules['min']}")
                return False
                
            if 'max' in rules and param_value > rules['max']:
                logger.error(f"Parameter '{param_name}' exceeds maximum value {rules['max']}")
                return False
                
            # 正则表达式检查
            if 'regex' in rules and isinstance(param_value, str):
                if not re.match(rules['regex'], param_value):
                    logger.error(f"Parameter '{param_name}' does not match required pattern")
                    return False
        
        return True
    
    def transfer_skill(self, source_skill: SkillNode, 
                      target_modality: DataModality,
                      custom_mappings: Optional[Dict[str, Any]] = None) -> SkillNode:
        """
        将技能从源模态迁移到目标模态
        
        参数:
            source_skill: 源技能节点
            target_modality: 目标数据模态
            custom_mappings: 自定义参数映射规则 (可选)
            
        返回:
            SkillNode: 迁移后的技能节点
            
        异常:
            ValueError: 如果技能迁移失败
        """
        logger.info(f"Transferring skill '{source_skill.name}' from {source_skill.input_modality} to {target_modality}")
        
        try:
            # 1. 提取源技能的拓扑结构
            topology = self._extract_skill_topology(source_skill)
            
            # 2. 映射参数
            source_params = {p.name: p.default_value for p in source_skill.parameters}
            mapped_params = self._map_parameters(
                source_params, 
                source_skill.input_modality, 
                target_modality
            )
            
            # 应用自定义映射（如果有）
            if custom_mappings:
                mapped_params.update(custom_mappings)
                logger.debug("Applied custom parameter mappings")
            
            # 3. 创建迁移后的技能节点
            transferred_skill = SkillNode(
                name=f"{source_skill.name}_for_{target_modality.name}",
                description=f"{source_skill.description} (Adapted for {target_modality.name})",
                input_modality=target_modality,
                output_modality=source_skill.output_modality,  # 通常保持输出模态不变
                parameters=[
                    SkillParameter(
                        name=name,
                        param_type=topology['parameters'][name]['type'],
                        default_value=value,
                        description=topology['parameters'][name]['description'],
                        required=topology['parameters'][name]['required'],
                        validation_rules=topology['parameters'][name]['validation']
                    )
                    for name, value in mapped_params.items()
                ],
                dependencies=source_skill.dependencies.copy(),
                implementation_hint=source_skill.implementation_hint
            )
            
            # 4. 验证迁移后的技能
            if not self._validate_parameters(
                mapped_params,
                {p.name: p.validation_rules for p in transferred_skill.parameters if p.validation_rules}
            ):
                logger.error("Parameter validation failed for transferred skill")
                raise ValueError("Parameter validation failed")
            
            # 5. 注册迁移后的技能
            self.skill_registry[target_modality][transferred_skill.name] = transferred_skill
            logger.info(f"Successfully transferred skill to {transferred_skill.name}")
            
            return transferred_skill
            
        except Exception as e:
            logger.error(f"Skill transfer failed: {str(e)}")
            raise ValueError(f"Skill transfer failed: {str(e)}")
    
    def generate_code(self, skill: SkillNode, 
                     template: Optional[str] = None) -> str:
        """
        根据技能节点生成可执行代码
        
        参数:
            skill: 要生成代码的技能节点
            template: 自定义代码模板 (可选)
            
        返回:
            str: 生成的可执行代码字符串
            
        异常:
            ValueError: 如果代码生成失败
        """
        logger.info(f"Generating code for skill '{skill.name}'")
        
        # 默认模板
        default_template = textwrap.dedent("""
        def {function_name}(input_data, {parameters}):
            \"\"\"
            {description}
            
            输入:
                input_data: {input_type}
                {param_docs}
                
            输出:
                {output_type}
            \"\"\"
            # 实现提示: {implementation_hint}
            {implementation_code}
            
            return result
        """)
        
        template = template or default_template
        
        try:
            # 准备参数字符串和文档字符串
            params_str = ", ".join(
                f"{p.name}={repr(p.default_value)}" if p.default_value is not None else p.name
                for p in skill.parameters
            )
            
            param_docs = "\n    ".join(
                f"{p.name} ({p.param_type}): {p.description}"
                for p in skill.parameters
            )
            
            # 生成实现代码（这里简化处理，实际实现可能需要更复杂的逻辑）
            impl_code = self._generate_implementation_code(skill)
            
            # 填充模板
            code = template.format(
                function_name=skill.name,
                parameters=params_str,
                description=skill.description,
                input_type=skill.input_modality.name,
                param_docs=param_docs,
                output_type=skill.output_modality.name,
                implementation_hint=skill.implementation_hint or "Not specified",
                implementation_code=impl_code
            )
            
            logger.info(f"Successfully generated code for skill '{skill.name}'")
            return code
            
        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")
            raise ValueError(f"Code generation failed: {str(e)}")
    
    def _generate_implementation_code(self, skill: SkillNode) -> str:
        """
        为技能节点生成实现代码（内部辅助方法）
        
        参数:
            skill: 技能节点
            
        返回:
            str: 生成的实现代码字符串
        """
        # 这里简化处理，实际实现可能需要根据技能类型和模态生成不同的代码
        if skill.implementation_hint:
            return f"# 自定义实现:\n{skill.implementation_hint}"
        
        # 默认实现
        impl = [
            "# 自动生成的实现",
            "result = None",
            "# 处理输入数据",
            f"# 将 {skill.input_modality.name} 转换为内部表示",
            "# 应用技能逻辑",
            "# 转换为输出格式",
            f"# 生成 {skill.output_modality.name} 输出"
        ]
        
        # 添加参数处理
        for param in skill.parameters:
            if param.default_value is not None:
                impl.append(f"# 使用参数 {param.name} (默认值: {param.default_value})")
            else:
                impl.append(f"# 使用参数 {param.name} (必须提供)")
        
        return "\n".join(impl)

# 示例用法
if __name__ == "__main__":
    # 创建技能迁移协议实例
    protocol = SkillTransferProtocol()
    
    # 定义源技能（文本处理技能）
    text_skill = SkillNode(
        name="text_processor",
        description="Process text data using tokenization and embedding",
        input_modality=DataModality.TEXT,
        output_modality=DataModality.TEXT,
        parameters=[
            SkillParameter(
                name="sequence_length",
                param_type="int",
                default_value=128,
                description="Maximum sequence length for text processing",
                required=False,
                validation_rules={'min': 1, 'max': 1024}
            ),
            SkillParameter(
                name="vocabulary_size",
                param_type="int",
                default_value=30000,
                description="Size of the vocabulary",
                required=False,
                validation_rules={'min': 100, 'max': 100000}
            ),
            SkillParameter(
                name="embedding_dim",
                param_type="int",
                default_value=300,
                description="Dimension of word embeddings",
                required=False,
                validation_rules={'min': 50, 'max': 1024}
            ),
            SkillParameter(
                name="normalization",
                param_type="str",
                default_value="layer_norm",
                description="Type of normalization to apply",
                required=False,
                validation_rules={'regex': r'^(layer_norm|batch_norm|min_max)$'}
            )
        ],
        dependencies=["tokenizer", "embedder"],
        implementation_hint="tokenize(text) -> embed(tokens) -> normalize(embeddings)"
    )
    
    # 将技能迁移到音频模态
    audio_skill = protocol.transfer_skill(text_skill, DataModality.AUDIO)
    
    # 为迁移后的技能生成代码
    code = protocol.generate_code(audio_skill)
    
    # 打印结果
    print("\n=== 迁移后的技能 ===")
    print(f"名称: {audio_skill.name}")
    print(f"描述: {audio_skill.description}")
    print(f"输入模态: {audio_skill.input_modality.name}")
    print(f"输出模态: {audio_skill.output_modality.name}")
    print("\n=== 参数 ===")
    for param in audio_skill.parameters:
        print(f"{param.name} ({param.param_type}): {param.description}")
        print(f"  默认值: {param.default_value}")
    
    print("\n=== 生成的代码 ===")
    print(code)