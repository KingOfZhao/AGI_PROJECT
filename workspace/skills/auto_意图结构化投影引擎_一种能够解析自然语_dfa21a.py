"""
意图结构化投影引擎

该模块实现了一个能够解析自然语言中隐含隐喻结构，
并将其转化为可执行代码形式化约束（Z-Spec风格）的引擎。
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectionError(Exception):
    """自定义异常：投影过程中出现的错误"""
    pass

class MetaphorDomain(Enum):
    """隐喻域枚举"""
    LIBRARY = "library"
    BANK = "bank"
    TRAFFIC = "traffic"
    UNKNOWN = "unknown"

@dataclass
class StructuralMapping:
    """结构映射数据类"""
    source_concept: str
    target_concept: str
    relations: Dict[str, str] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)

@dataclass
class FormalSpecification:
    """形式化规格说明数据类"""
    schema_name: str
    state_variables: Dict[str, str]
    operations: Dict[str, Dict[str, Any]]
    invariants: List[str]

def detect_metaphor_domain(description: str) -> MetaphorDomain:
    """
    辅助函数：从自然语言描述中检测隐喻域
    
    Args:
        description: 自然语言描述字符串
        
    Returns:
        MetaphorDomain: 检测到的隐喻域枚举值
        
    Example:
        >>> detect_metaphor_domain("像管理图书馆一样管理内存")
        <MetaphorDomain.LIBRARY: 'library'>
    """
    domain_keywords = {
        MetaphorDomain.LIBRARY: ['图书馆', '借阅', '归还', '书籍', '书架', '借书证'],
        MetaphorDomain.BANK: ['银行', '存款', '取款', '账户', '利息', '贷款'],
        MetaphorDomain.TRAFFIC: ['交通', '红绿灯', '车辆', '道路', '拥堵', '导航']
    }
    
    description_lower = description.lower()
    
    for domain, keywords in domain_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            logger.info(f"检测到隐喻域: {domain.value}")
            return domain
            
    logger.warning("未检测到明确的隐喻域")
    return MetaphorDomain.UNKNOWN

def extract_structural_relations(
    domain: MetaphorDomain, 
    description: str
) -> List[StructuralMapping]:
    """
    核心函数1：提取隐喻结构关系
    
    从给定的隐喻域和描述中提取结构关系映射。
    
    Args:
        domain: 隐喻域枚举值
        description: 自然语言描述
        
    Returns:
        List[StructuralMapping]: 结构映射列表
        
    Raises:
        ProjectionError: 当无法提取结构关系时抛出
    """
    if domain == MetaphorDomain.UNKNOWN:
        raise ProjectionError("无法从未知隐喻域提取结构关系")
    
    logger.info(f"开始从'{domain.value}'域提取结构关系...")
    
    # 预定义的结构映射模板
    mapping_templates = {
        MetaphorDomain.LIBRARY: [
            StructuralMapping(
                source_concept="book_borrowing",
                target_concept="memory_allocation",
                relations={
                    "borrow": "allocate",
                    "return": "free",
                    "overdue": "leak",
                    "library_card": "pointer"
                },
                constraints=[
                    "每个指针必须指向已分配的内存",
                    "内存使用完毕必须释放",
                    "长时间未释放的内存视为泄漏"
                ]
            ),
            StructuralMapping(
                source_concept="book_reservation",
                target_concept="memory_locking",
                relations={
                    "reserve": "lock",
                    "cancel": "unlock",
                    "waitlist": "queue"
                }
            )
        ],
        MetaphorDomain.BANK: [
            StructuralMapping(
                source_concept="deposit_withdraw",
                target_concept="data_io",
                relations={
                    "deposit": "write",
                    "withdraw": "read",
                    "balance": "data_size",
                    "interest": "data_growth"
                },
                constraints=[
                    "写入数据不能超过存储容量",
                    "读取数据必须存在",
                    "数据增长率有上限"
                ]
            )
        ]
    }
    
    mappings = mapping_templates.get(domain, [])
    
    # 动态提取额外的关系（简单实现）
    if "像" in description and "一样" in description:
        pattern = r"像(.*?)一样(.*?)"
        match = re.search(pattern, description)
        if match:
            source_domain = match.group(1)
            target_domain = match.group(2)
            logger.info(f"检测到隐喻映射: {source_domain} -> {target_domain}")
            
            # 添加动态映射
            dynamic_mapping = StructuralMapping(
                source_concept=f"{source_domain}_concept",
                target_concept=f"{target_domain}_concept",
                relations={"implicit_mapping": "derived_from_context"}
            )
            mappings.append(dynamic_mapping)
    
    if not mappings:
        raise ProjectionError("无法从描述中提取任何结构关系")
    
    logger.info(f"成功提取{len(mappings)}个结构映射")
    return mappings

def generate_formal_specification(
    mappings: List[StructuralMapping],
    target_system: str = "GenericSystem"
) -> FormalSpecification:
    """
    核心函数2：生成形式化规格说明
    
    将结构映射转换为Z-Spec风格的形式化规格说明。
    
    Args:
        mappings: 结构映射列表
        target_system: 目标系统名称
        
    Returns:
        FormalSpecification: 形式化规格说明对象
        
    Raises:
        ValueError: 当输入映射为空时抛出
    """
    if not mappings:
        raise ValueError("输入映射列表不能为空")
    
    logger.info("开始生成形式化规格说明...")
    
    # 初始化规格说明组件
    state_variables = {}
    operations = {}
    invariants = []
    
    for idx, mapping in enumerate(mappings, 1):
        schema_name = f"{target_system}_{mapping.target_concept}_{idx}"
        
        # 添加状态变量
        for src_rel, tgt_rel in mapping.relations.items():
            var_name = f"{tgt_rel}_state"
            if var_name not in state_variables:
                state_variables[var_name] = "Set[Entity]"
        
        # 生成操作
        op_name = f"Op_{mapping.target_concept}"
        operations[op_name] = {
            "inputs": {"request": "RequestType"},
            "outputs": {"response": "ResponseType"},
            "preconditions": [
                f"{src} -> {tgt} mapping defined" 
                for src, tgt in mapping.relations.items()
            ],
            "postconditions": [
                f"{tgt} state updated according to {src} rules"
                for src, tgt in mapping.relations.items()
            ]
        }
        
        # 添加约束
        invariants.extend(mapping.constraints)
        invariants.append(f"Consistency between {mapping.source_concept} and {mapping.target_concept} maintained")
    
    # 添加全局约束
    invariants.extend([
        "All operations maintain system integrity",
        "No resource leaks allowed",
        "All state transitions are atomic"
    ])
    
    spec = FormalSpecification(
        schema_name=f"{target_system}_Specification",
        state_variables=state_variables,
        operations=operations,
        invariants=list(set(invariants))  # 去重
    )
    
    logger.info("形式化规格说明生成完成")
    return spec

def validate_specification(spec: FormalSpecification) -> bool:
    """
    数据验证函数：验证形式化规格说明的完整性
    
    Args:
        spec: 形式化规格说明对象
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ProjectionError: 当规格说明无效时抛出
    """
    if not spec.schema_name:
        raise ProjectionError("规格说明缺少架构名称")
    
    if not spec.state_variables:
        logger.warning("规格说明缺少状态变量定义")
    
    if not spec.operations:
        raise ProjectionError("规格说明必须包含至少一个操作定义")
    
    if not spec.invariants:
        raise ProjectionError("规格说明必须包含约束条件")
    
    logger.info("规格说明验证通过")
    return True

# 使用示例
if __name__ == "__main__":
    try:
        # 示例1: 图书馆隐喻处理
        print("=" * 60)
        print("示例1: 图书馆隐喻 -> 内存管理")
        print("=" * 60)
        
        description1 = "像管理图书馆一样管理内存"
        domain1 = detect_metaphor_domain(description1)
        mappings1 = extract_structural_relations(domain1, description1)
        spec1 = generate_formal_specification(mappings1, "MemoryManager")
        validate_specification(spec1)
        
        print(f"\n检测到的隐喻域: {domain1.value}")
        print(f"\n结构映射数量: {len(mappings1)}")
        print("\n形式化规格说明(Z-Spec风格):")
        print(json.dumps({
            "schema_name": spec1.schema_name,
            "state_variables": spec1.state_variables,
            "operations": list(spec1.operations.keys()),
            "invariants": spec1.invariants[:3]  # 只显示部分约束
        }, indent=2, ensure_ascii=False))
        
        # 示例2: 银行隐喻处理
        print("\n" + "=" * 60)
        print("示例2: 银行隐喻 -> 数据IO")
        print("=" * 60)
        
        description2 = "像银行存取款一样处理数据IO"
        domain2 = detect_metaphor_domain(description2)
        mappings2 = extract_structural_relations(domain2, description2)
        spec2 = generate_formal_specification(mappings2, "DataIOSystem")
        
        print(f"\n检测到的隐喻域: {domain2.value}")
        print("\n生成的操作列表:")
        for op_name, op_def in spec2.operations.items():
            print(f"- {op_name}: {len(op_def['preconditions'])} 前置条件, {len(op_def['postconditions'])} 后置条件")
        
        print("\n系统约束条件:")
        for idx, inv in enumerate(spec2.invariants[:5], 1):
            print(f"{idx}. {inv}")
            
    except ProjectionError as pe:
        logger.error(f"投影处理错误: {pe}")
    except Exception as e:
        logger.error(f"系统错误: {e}", exc_info=True)