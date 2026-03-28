"""
Module: auto_认知自洽性破坏检测器_在进行跨域迁移时_8cb22a
Description: 认知自洽性破坏检测器：用于在跨域迁移（如从生物学到社会学）时，
             检测逻辑谬误和伦理冲突，防止破坏目标领域的内部自洽性。
Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConflictLevel(Enum):
    """冲突等级枚举"""
    SAFE = "safe"                 # 安全
    LOW = "low"                   # 低风险
    MEDIUM = "medium"             # 中风险
    HIGH = "high"                 # 高风险
    CRITICAL = "critical"         # 极高风险

class ConflictType(Enum):
    """冲突类型枚举"""
    LOGICAL_FALLACY = "logical_fallacy"       # 逻辑谬误（如范畴错误）
    ETHICAL_VIOLATION = "ethical_violation"   # 伦理违规（如侵犯主体权利）
    ONONTOLOGICAL_MISMATCH = "ontological"    # 本体论不匹配（如对象属性冲突）

@dataclass
class DomainContext:
    """领域上下文数据结构"""
    domain_name: str
    core_values: Set[str]           # 核心价值观 (如: "survival", "equity")
    protected_entities: Set[str]    # 受保护实体 (如: "human_rights", "weak_groups")
    logic_rules: Set[str]           # 逻辑规则 (如: "causality", "non-contradiction")

@dataclass
class MigrationWarning:
    """迁移警告数据结构"""
    is_violation: bool
    level: ConflictLevel
    conflict_type: ConflictType
    description: str
    suggestion: str

def _validate_input_non_empty(data: Dict, field_name: str) -> None:
    """
    辅助函数：验证输入数据字典是否包含特定字段且非空
    
    Args:
        data: 输入数据字典
        field_name: 必须包含的字段名称
        
    Raises:
        ValueError: 如果字段缺失或为空
    """
    if field_name not in data or not data[field_name]:
        error_msg = f"输入验证失败: 缺失必要字段或字段为空 '{field_name}'"
        logger.error(error_msg)
        raise ValueError(error_msg)

def _build_domain_context(domain_data: Dict) -> DomainContext:
    """
    辅助函数：从字典构建领域上下文对象
    
    Args:
        domain_data: 包含领域信息的字典
        
    Returns:
        DomainContext 实例
    """
    logger.debug(f"正在构建领域上下文: {domain_data.get('name', 'Unknown')}")
    return DomainContext(
        domain_name=domain_data.get("name", "unknown"),
        core_values=set(domain_data.get("core_values", [])),
        protected_entities=set(domain_data.get("protected_entities", [])),
        logic_rules=set(domain_data.get("logic_rules", []))
    )

def check_logic_coherence(
    source_domain: Dict, 
    target_domain: Dict
) -> Tuple[bool, List[str]]:
    """
    核心函数 1: 检查跨域迁移的逻辑自洽性
    
    分析源领域的逻辑规则是否与目标领域的本体论结构冲突。
    例如：将“随机性”规则迁移到“精密工程”领域可能导致逻辑崩塌。
    
    Args:
        source_domain: 源领域数据字典
        target_domain: 目标领域数据字典
        
    Returns:
        Tuple[bool, List[str]]: 
            - bool: 是否通过逻辑自洽性检查 (True为通过)
            - List[str]: 发现的逻辑冲突描述列表
            
    Raises:
        ValueError: 输入数据验证失败
    """
    # 1. 数据验证
    _validate_input_non_empty(source_domain, "name")
    _validate_input_non_empty(target_domain, "name")
    
    logger.info(f"开始逻辑自洽性检查: {source_domain['name']} -> {target_domain['name']}")
    
    # 2. 构建上下文
    source_ctx = _build_domain_context(source_domain)
    target_ctx = _build_domain_context(target_domain)
    
    conflicts = []
    
    # 3. 检查核心逻辑互斥性
    # 假设规则：如果源领域包含 'competition' 且目标领域包含 'equality' 作为核心价值观，
    # 且目标领域有 'vulnerable_groups' 保护，则存在潜在逻辑张力。
    if "competition" in source_ctx.core_values:
        if "equality" in target_ctx.core_values and \
           "vulnerable_groups" in target_ctx.protected_entities:
            conflict_msg = (
                "逻辑张力警告: 源领域的'竞争机制'可能与目标领域的'平等价值观'及"
                "'弱势群体保护'产生逻辑互斥。"
            )
            conflicts.append(conflict_msg)
            logger.warning(conflict_msg)

    # 4. 检查本体论映射错误
    if "biological_determinism" in source_ctx.logic_rules and \
       "free_will" in target_ctx.core_values:
        conflict_msg = "本体论冲突: 源领域的'生物决定论'否认目标领域的'自由意志'核心假设。"
        conflicts.append(conflict_msg)

    is_coherent = len(conflicts) == 0
    if is_coherent:
        logger.info("逻辑自洽性检查通过。")
    
    return is_coherent, conflicts

def detect_ethical_violations(
    source_domain: Dict, 
    target_domain: Dict, 
    migration_intent: str
) -> MigrationWarning:
    """
    核心函数 2: 检测伦理违规与自洽性破坏
    
    专门用于检测将自然规律（如优胜劣汰）强行迁移到人类社会系统时
    可能导致的伦理灾难。
    
    Args:
        source_domain: 源领域数据字典
        target_domain: 目标领域数据字典
        migration_intent: 描述迁移意图的字符串
        
    Returns:
        MigrationWarning: 包含详细风险级别和建议的警告对象
        
    Example Input:
        source_domain = {
            "name": "evolutionary_biology",
            "core_values": ["survival", "reproduction"],
            "protected_entities": [],
            "logic_rules": ["natural_selection"]
        }
        target_domain = {
            "name": "social_welfare",
            "core_values": ["compassion", "equity"],
            "protected_entities": ["elderly", "disabled"],
            "logic_rules": ["human_rights"]
        }
        migration_intent = "Optimize resource allocation based on fitness"
    """
    # 边界检查
    if not migration_intent:
        logger.error("迁移意图(migration_intent)不能为空")
        raise ValueError("Migration intent cannot be empty")

    logger.info(f"正在检测伦理违规: 意图 '{migration_intent}'")
    
    target_ctx = _build_domain_context(target_domain)
    source_ctx = _build_domain_context(source_domain)
    
    # 默认为安全
    warning = MigrationWarning(
        is_violation=False,
        level=ConflictLevel.SAFE,
        conflict_type=ConflictType.LOGICAL_FALLACY,
        description="未检测到明显的伦理冲突。",
        suggestion="可以执行迁移，但建议保持人工监督。"
    )
    
    # 核心检测逻辑：自然选择 vs 社会福利
    is_bio_source = "natural_selection" in source_ctx.logic_rules
    is_social_target = "human_rights" in target_ctx.logic_rules
    
    if is_bio_source and is_social_target:
        # 检查是否涉及牺牲弱者
        if "survival_of_fittest" in migration_intent.lower() or \
           "efficiency_over_fairness" in migration_intent.lower():
            
            warning = MigrationWarning(
                is_violation=True,
                level=ConflictLevel.CRITICAL,
                conflict_type=ConflictType.ETHICAL_VIOLATION,
                description=(
                    "严重伦理冲突: 试图将生物界的'自然选择'机制应用于"
                    "具有'人权'保障的社会领域。这违反了目标领域的自洽性，"
                    "可能导致对弱势群体的系统性伤害。"
                ),
                suggestion="中止迁移。请重新设计算法，使其符合'公平性'和'人类尊严'原则。"
            )
            logger.critical(f"检测到严重伦理违规: {warning.description}")
            
        elif "optimization" in migration_intent.lower():
            warning = MigrationWarning(
                is_violation=True,
                level=ConflictLevel.HIGH,
                conflict_type=ConflictType.ONONTOLOGICAL_MISMATCH,
                description=(
                    "本体论错位: 生物学的'优化'通常意味着淘汰不适者，"
                    "而社会学中的'优化'必须包含道德约束。"
                ),
                suggestion="引入伦理约束层，确保不侵犯目标领域的受保护实体。"
            )
            logger.warning(f"检测到高风险冲突: {warning.description}")
            
    return warning

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例数据定义
    bio_domain = {
        "name": "evolutionary_biology",
        "core_values": ["survival", "genetic_fitness"],
        "protected_entities": [],  # 生物界通常无特定的伦理保护实体
        "logic_rules": ["natural_selection", "mutation"]
    }

    social_domain = {
        "name": "social_welfare_system",
        "core_values": ["justice", "equity", "care"],
        "protected_entities": ["elderly", "children", "disabled"],
        "logic_rules": ["human_rights", "redistribution"]
    }

    print("-" * 30)
    print("场景 1: 检测逻辑自洽性")
    print("-" * 30)
    
    # 检查逻辑冲突
    is_logic_safe, logic_conflicts = check_logic_coherence(bio_domain, social_domain)
    
    print(f"逻辑检查通过: {is_logic_safe}")
    if not is_logic_safe:
        print("发现冲突:")
        for conflict in logic_conflicts:
            print(f"- {conflict}")

    print("\n" + "-" * 30)
    print("场景 2: 检测具体迁移意图的伦理风险")
    print("-" * 30)

    # 意图 1: 高风险意图
    bad_intent = "Allocate medical resources based on genetic fitness and survival probability."
    warning_result = detect_ethical_violations(bio_domain, social_domain, bad_intent)
    
    print(f"检测到违规: {warning_result.is_violation}")
    print(f"风险等级: {warning_result.level.value}")
    print(f"描述: {warning_result.description}")
    print(f"建议: {warning_result.suggestion}")