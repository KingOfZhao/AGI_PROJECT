"""
Module: skill_transfer_interface.py
Description: 构建技能迁移的通用接口，实现跨域认知模式映射。
Author: AGI System Core
Version: 1.0.0
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic
from pydantic import BaseModel, Field, validator, ValidationError
from uuid import uuid4

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义泛型类型变量
T = TypeVar('T')
R = TypeVar('R')

class SkillMetadata(BaseModel):
    """
    Skill元数据基类，定义认知模式的抽象结构。
    """
    skill_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    domain: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    core_patterns: List[str] = Field(default_factory=list)
    
    @validator('name', 'domain')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name and domain cannot be empty")
        return v

class ContextCarrier(BaseModel):
    """
    上下文载体，承载特定领域的输入输出数据。
    """
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TransferMapping(BaseModel):
    """
    迁移映射规则，定义源域到目标域的转换逻辑。
    """
    source_domain: str
    target_domain: str
    mapping_rules: Dict[str, str]
    confidence_score: float = Field(ge=0.0, le=1.0)

class AbstractSkill(ABC, Generic[T, R]):
    """
    抽象技能基类，定义通用接口。
    """
    
    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self._validate_metadata()
        
    def _validate_metadata(self) -> None:
        """验证元数据完整性"""
        if not self.metadata.core_patterns:
            logger.warning(f"Skill {self.metadata.name} has no core patterns defined")
    
    @abstractmethod
    def execute(self, input_data: T) -> R:
        """执行技能逻辑"""
        pass
    
    @abstractmethod
    def adapt_to_domain(self, target_domain: str, mapping: TransferMapping) -> 'AbstractSkill':
        """适配到新领域"""
        pass

class RecursiveThinkingSkill(AbstractSkill[ContextCarrier, ContextCarrier]):
    """
    递归思维技能实现 - 初始域: 代码编写
    """
    
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        logger.info(f"Initialized RecursiveThinkingSkill in domain: {metadata.domain}")
    
    def execute(self, input_data: ContextCarrier) -> ContextCarrier:
        """执行递归分解"""
        try:
            logger.info(f"Executing recursive thinking on: {input_data.data}")
            
            if not input_data.data:
                raise ValueError("Input data cannot be empty")
                
            # 模拟递归分解逻辑
            result = self._recursive_decompose(input_data.data)
            
            return ContextCarrier(
                data=result,
                metadata={"domain": self.metadata.domain, "processed_by": self.metadata.name}
            )
            
        except Exception as e:
            logger.error(f"Error in RecursiveThinkingSkill execution: {str(e)}")
            raise
    
    def _recursive_decompose(self, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """辅助方法：递归分解逻辑"""
        if depth > 10:  # 防止无限递归
            return data
            
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = {"_decomposed": True, **self._recursive_decompose(value, depth+1)}
            else:
                result[key] = value
        return result
    
    def adapt_to_domain(self, target_domain: str, mapping: TransferMapping) -> 'AbstractSkill':
        """适配到新领域"""
        logger.info(f"Adapting {self.metadata.name} to domain: {target_domain}")
        
        new_metadata = SkillMetadata(
            name=f"{self.metadata.name}_adapted_to_{target_domain}",
            domain=target_domain,
            description=f"Adapted from {self.metadata.domain} to {target_domain}",
            core_patterns=self.metadata.core_patterns,
            input_schema=self._transform_schema(self.metadata.input_schema, mapping),
            output_schema=self._transform_schema(self.metadata.output_schema, mapping)
        )
        
        return OrganizationDecompositionSkill(new_metadata)
    
    def _transform_schema(self, schema: Dict[str, Any], mapping: TransferMapping) -> Dict[str, Any]:
        """辅助方法：转换模式定义"""
        transformed = {}
        for key, value in schema.items():
            new_key = mapping.mapping_rules.get(key, key)
            transformed[new_key] = value
        return transformed

class OrganizationDecompositionSkill(AbstractSkill[ContextCarrier, ContextCarrier]):
    """
    组织架构拆解技能 - 目标域: 企业管理
    """
    
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        logger.info(f"Initialized OrganizationDecompositionSkill in domain: {metadata.domain}")
    
    def execute(self, input_data: ContextCarrier) -> ContextCarrier:
        """执行组织分解"""
        try:
            logger.info(f"Executing organization decomposition on: {input_data.data}")
            
            if "org_structure" not in input_data.data:
                raise ValueError("Input must contain 'org_structure' field")
                
            # 模拟组织分解逻辑
            result = self._decompose_organization(input_data.data["org_structure"])
            
            return ContextCarrier(
                data={"decomposed_org": result},
                metadata={
                    "domain": self.metadata.domain,
                    "original_patterns": self.metadata.core_patterns
                }
            )
            
        except Exception as e:
            logger.error(f"Error in OrganizationDecompositionSkill execution: {str(e)}")
            raise
    
    def _decompose_organization(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """辅助方法：组织分解逻辑"""
        result = {}
        for dept, members in org_data.items():
            if isinstance(members, dict):
                result[dept] = {
                    "sub_departments": len(members),
                    "teams": list(members.keys())
                }
            else:
                result[dept] = {"members": members}
        return result
    
    def adapt_to_domain(self, target_domain: str, mapping: TransferMapping) -> 'AbstractSkill':
        """企业管理域不需要进一步适配"""
        logger.warning("OrganizationDecompositionSkill does not support further adaptation")
        return self

class SkillTransferEngine:
    """
    技能迁移引擎，管理迁移过程
    """
    
    @staticmethod
    def transfer_skill(
        source_skill: AbstractSkill,
        target_domain: str,
        mapping_rules: Dict[str, str]
    ) -> AbstractSkill:
        """
        执行技能迁移
        
        Args:
            source_skill: 源技能实例
            target_domain: 目标领域
            mapping_rules: 映射规则字典
            
        Returns:
            适配后的新技能实例
            
        Raises:
            ValueError: 如果输入参数无效
        """
        if not mapping_rules:
            raise ValueError("Mapping rules cannot be empty")
            
        if not target_domain or not target_domain.strip():
            raise ValueError("Target domain cannot be empty")
            
        logger.info(f"Transferring skill {source_skill.metadata.name} to {target_domain}")
        
        mapping = TransferMapping(
            source_domain=source_skill.metadata.domain,
            target_domain=target_domain,
            mapping_rules=mapping_rules,
            confidence_score=0.85  # 默认置信度
        )
        
        return source_skill.adapt_to_domain(target_domain, mapping)

# 使用示例
if __name__ == "__main__":
    try:
        # 1. 创建原始技能 (代码编写域的递归思维)
        coding_skill_metadata = SkillMetadata(
            name="recursive_thinking",
            domain="software_engineering",
            description="Decompose complex problems into smaller recursive steps",
            input_schema={"code_structure": "dict"},
            output_schema={"decomposed_units": "list"},
            core_patterns=["recursive_decomposition", "base_case_identification"]
        )
        
        coding_skill = RecursiveThinkingSkill(coding_skill_metadata)
        
        # 2. 定义迁移规则
        transfer_rules = {
            "code_structure": "org_structure",
            "decomposed_units": "organizational_units",
            "function": "department",
            "module": "division"
        }
        
        # 3. 执行迁移
        mgmt_skill = SkillTransferEngine.transfer_skill(
            source_skill=coding_skill,
            target_domain="business_management",
            mapping_rules=transfer_rules
        )
        
        # 4. 使用迁移后的技能
        org_input = ContextCarrier(data={
            "org_structure": {
                "executive_team": {"CEO": 1, "CTO": 1},
                "engineering": {"backend": 10, "frontend": 5}
            }
        })
        
        result = mgmt_skill.execute(org_input)
        logger.info(f"Migration successful. Result: {result.json()}")
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")