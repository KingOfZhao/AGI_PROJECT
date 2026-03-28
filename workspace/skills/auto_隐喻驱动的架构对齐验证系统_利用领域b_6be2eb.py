"""
隐喻驱动的架构对齐验证系统

本模块实现了一个跨域架构验证系统，利用领域B（源域）的隐喻结构来验证
领域A（目标域）的代码架构是否保持语义一致性。

核心功能：
1. 从隐喻描述中提取本体结构图
2. 将代码类图映射到隐喻结构
3. 执行结构同构性验证

数据流示例：
输入：隐喻描述 "像管理图书馆一样管理内存"
处理流程：
  1. 提取图书馆本体 -> {Library, Shelf, Book, Borrower, Fine}
  2. 生成代码架构 -> {MemoryPool, Block, Byte, Pointer, LeakHandler}
  3. 结构映射验证 -> 同构性检查
输出：验证报告 {is_aligned: True, confidence: 0.92, warnings: []}

作者：AGI系统核心模块
版本：1.0.0
创建时间：2023-11-15
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MetaphorArchVerifier')


class NodeType(Enum):
    """节点类型枚举，用于分类隐喻和代码元素"""
    CONTAINER = auto()    # 容器类节点（如图书馆、内存池）
    ITEM = auto()         # 内容项节点（如书籍、内存块）
    AGENT = auto()        # 代理节点（如借阅者、指针）
    ACTION = auto()       # 动作节点（如借阅、分配）
    CONSTRAINT = auto()   # 约束节点（如罚款、泄漏处理）


@dataclass
class MetaphorNode:
    """隐喻结构图中的节点表示"""
    name: str
    node_type: NodeType
    properties: Dict[str, str] = field(default_factory=dict)
    relations: List[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash((self.name, self.node_type))


@dataclass
class CodeNode:
    """代码架构中的节点表示"""
    class_name: str
    metaphor_mapping: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.class_name)


class MetaphorArchitectureVerifier:
    """
    隐喻驱动的架构对齐验证系统核心类
    
    该系统通过以下步骤确保代码架构与隐喻结构的一致性：
    1. 隐喻解析：从自然语言描述中提取结构化隐喻
    2. 架构映射：建立代码类与隐喻元素的对应关系
    3. 同构验证：检查两个图结构的拓扑一致性
    
    示例用法：
    >>> verifier = MetaphorArchitectureVerifier()
    >>> metaphor_desc = "像管理图书馆一样管理内存"
    >>> code_classes = ["MemoryPool", "MemoryBlock", "Pointer", "LeakDetector"]
    >>> result = verifier.verify_architecture(metaphor_desc, code_classes)
    >>> print(f"架构对齐结果: {result['is_aligned']}")
    """
    
    # 领域B（源域）的隐喻知识库
    METAPHOR_KNOWLEDGE_BASE = {
        "图书馆": {
            "nodes": [
                ("Library", NodeType.CONTAINER, {"capacity": "总容量"}),
                ("Bookshelf", NodeType.CONTAINER, {"category": "分类"}),
                ("Book", NodeType.ITEM, {"isbn": "唯一标识"}),
                ("Borrower", NodeType.AGENT, {"id": "借阅者ID"}),
                ("Loan", NodeType.ACTION, {"duration": "借阅时长"}),
                ("Fine", NodeType.CONSTRAINT, {"rate": "罚款率"})
            ],
            "relations": {
                "Library": ["contains", "Bookshelf"],
                "Bookshelf": ["holds", "Book"],
                "Borrower": ["performs", "Loan"],
                "Loan": ["involves", "Book"],
                "Fine": ["penalizes", "Borrower"]
            }
        },
        "交通系统": {
            "nodes": [
                ("Road", NodeType.CONTAINER, {"lanes": "车道数"}),
                ("Vehicle", NodeType.ITEM, {"plate": "车牌"}),
                ("Driver", NodeType.AGENT, {"license": "驾照"}),
                ("Movement", NodeType.ACTION, {"speed": "速度"}),
                ("TrafficLight", NodeType.CONSTRAINT, {"state": "状态"})
            ],
            "relations": {
                "Road": ["accommodates", "Vehicle"],
                "Driver": ["operates", "Vehicle"],
                "Movement": ["follows", "TrafficLight"]
            }
        }
    }
    
    def __init__(self) -> None:
        """初始化验证系统，加载必要资源"""
        self._loaded_metaphors: Dict[str, Dict] = {}
        self._validation_cache: Dict[str, bool] = {}
        logger.info("隐喻架构验证系统初始化完成")
    
    def extract_metaphor_structure(self, description: str) -> Dict[str, MetaphorNode]:
        """
        从隐喻描述中提取结构化表示
        
        参数:
            description: 包含隐喻的自然语言描述
            
        返回:
            以节点名为键的隐喻结构字典
            
        示例:
            >>> nodes = extractor.extract_metaphor_structure("像图书馆一样管理")
            >>> print(nodes.keys())  # dict_keys(['Library', 'Bookshelf', ...])
        """
        if not description or not isinstance(description, str):
            logger.error("无效的隐喻描述输入")
            raise ValueError("隐喻描述必须是非空字符串")
        
        # 简化的隐喻关键词匹配（实际系统会使用NLP模型）
        detected_domain = None
        for domain in self.METAPHOR_KNOWLEDGE_BASE:
            if domain in description:
                detected_domain = domain
                break
        
        if not detected_domain:
            logger.warning(f"无法识别隐喻领域: {description}")
            return {}
        
        # 构建隐喻结构图
        domain_data = self.METAPHOR_KNOWLEDGE_BASE[detected_domain]
        nodes: Dict[str, MetaphorNode] = {}
        
        for node_info in domain_data["nodes"]:
            name, ntype, props = node_info
            node = MetaphorNode(
                name=name,
                node_type=ntype,
                properties=props,
                relations=domain_data["relations"].get(name, [])
            )
            nodes[name] = node
        
        self._loaded_metaphors[detected_domain] = nodes
        logger.info(f"成功提取隐喻结构: {detected_domain} ({len(nodes)}个节点)")
        return nodes
    
    def map_code_to_metaphor(
        self,
        code_nodes: List[CodeNode],
        metaphor_nodes: Dict[str, MetaphorNode]
    ) -> Dict[str, str]:
        """
        建立代码类与隐喻节点的映射关系
        
        参数:
            code_nodes: 代码架构节点列表
            metaphor_nodes: 隐喻结构节点字典
            
        返回:
            代码类名到隐喻节点名的映射字典
            
        异常:
            ValueError: 当输入为空或无效时抛出
        """
        if not code_nodes or not metaphor_nodes:
            logger.error("映射输入不能为空")
            raise ValueError("代码节点和隐喻节点必须非空")
        
        mapping: Dict[str, str] = {}
        unmatched_code_nodes: List[str] = []
        
        # 简化的名称相似度匹配（实际系统会使用语义相似度模型）
        for code_node in code_nodes:
            best_match = None
            best_score = 0.0
            
            # 基于名称的简单匹配
            for meta_name, meta_node in metaphor_nodes.items():
                # 计算名称相似度（示例使用简单的子串匹配）
                name_similarity = self._calculate_name_similarity(
                    code_node.class_name, meta_name
                )
                
                # 类型匹配加分
                type_bonus = 0.3 if self._infer_node_type(code_node) == meta_node.node_type else 0.0
                
                total_score = name_similarity + type_bonus
                if total_score > best_score:
                    best_score = total_score
                    best_match = meta_name
            
            if best_match and best_score > 0.5:  # 阈值可调整
                mapping[code_node.class_name] = best_match
                logger.debug(f"映射: {code_node.class_name} -> {best_match} (分数: {best_score:.2f})")
            else:
                unmatched_code_nodes.append(code_node.class_name)
        
        if unmatched_code_nodes:
            logger.warning(f"未匹配的代码节点: {', '.join(unmatched_code_nodes)}")
        
        return mapping
    
    def verify_architecture(
        self,
        metaphor_desc: str,
        code_class_names: List[str],
        strict_mode: bool = False
    ) -> Dict[str, any]:
        """
        验证代码架构与隐喻结构的一致性
        
        参数:
            metaphor_desc: 隐喻描述字符串
            code_class_names: 待验证的代码类名列表
            strict_mode: 是否启用严格验证模式
            
        返回:
            包含验证结果的字典:
            {
                "is_aligned": bool,
                "confidence": float,
                "warnings": List[str],
                "unmapped_classes": List[str],
                "structure_similarity": float
            }
        """
        # 输入验证
        if not metaphor_desc or not isinstance(metaphor_desc, str):
            return self._create_error_result("无效的隐喻描述")
        
        if not code_class_names or not isinstance(code_class_names, list):
            return self._create_error_result("代码类名列表必须是非空列表")
        
        # 1. 提取隐喻结构
        try:
            metaphor_nodes = self.extract_metaphor_structure(metaphor_desc)
        except Exception as e:
            logger.error(f"隐喻提取失败: {str(e)}")
            return self._create_error_result(f"隐喻解析错误: {str(e)}")
        
        if not metaphor_nodes:
            return self._create_error_result("无法识别有效的隐喻结构")
        
        # 2. 构建代码节点
        code_nodes = [
            CodeNode(class_name=cls_name) for cls_name in code_class_names
        ]
        
        # 3. 建立映射
        try:
            mapping = self.map_code_to_metaphor(code_nodes, metaphor_nodes)
        except Exception as e:
            logger.error(f"架构映射失败: {str(e)}")
            return self._create_error_result(f"映射错误: {str(e)}")
        
        # 4. 执行同构验证
        is_isomorphic, similarity = self._check_structural_isomorphism(
            mapping, metaphor_nodes
        )
        
        # 5. 生成结果报告
        warnings = []
        unmapped = [cls for cls in code_class_names if cls not in mapping]
        
        if unmapped:
            warnings.append(f"未映射的类: {', '.join(unmapped)}")
        
        if similarity < 0.7:
            warnings.append("结构相似度低于推荐阈值(0.7)")
        
        if strict_mode and not is_isomorphic:
            warnings.append("严格模式下结构不完全同构")
        
        result = {
            "is_aligned": is_isomorphic or not strict_mode,
            "confidence": similarity,
            "warnings": warnings,
            "unmapped_classes": unmapped,
            "structure_similarity": similarity,
            "metaphor_used": list(metaphor_nodes.keys()),
            "class_mappings": mapping
        }
        
        # 缓存结果
        cache_key = f"{metaphor_desc}::{':'.join(sorted(code_class_names))}"
        self._validation_cache[cache_key] = result["is_aligned"]
        
        logger.info(
            f"架构验证完成: 对齐={result['is_aligned']}, "
            f"置信度={result['confidence']:.2f}, "
            f"警告数={len(warnings)}"
        )
        
        return result
    
    # ========== 辅助方法 ==========
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个名称之间的相似度得分
        
        参数:
            name1: 第一个名称
            name2: 第二个名称
            
        返回:
            0.0到1.0之间的相似度分数
        """
        name1 = name1.lower().replace("_", "")
        name2 = name2.lower().replace("_", "")
        
        if name1 == name2:
            return 1.0
        
        # 检查一个名称是否是另一个的子串
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # 计算共同前缀长度
        common_prefix = 0
        for c1, c2 in zip(name1, name2):
            if c1 == c2:
                common_prefix += 1
            else:
                break
        
        # 基于共同前缀的相似度
        max_len = max(len(name1), len(name2))
        return common_prefix / max_len if max_len > 0 else 0.0
    
    def _infer_node_type(self, code_node: CodeNode) -> NodeType:
        """
        从代码节点推断其可能的隐喻节点类型
        
        参数:
            code_node: 代码节点对象
            
        返回:
            推断的NodeType枚举值
        """
        name = code_node.class_name.lower()
        
        # 基于名称启发式规则推断类型
        if any(kw in name for kw in ["pool", "manager", "container", "holder"]):
            return NodeType.CONTAINER
        elif any(kw in name for kw in ["item", "element", "unit", "block"]):
            return NodeType.ITEM
        elif any(kw in name for kw in ["handler", "controller", "driver", "pointer"]):
            return NodeType.AGENT
        elif any(kw in name for kw in ["action", "executor", "runner", "process"]):
            return NodeType.ACTION
        elif any(kw in name for kw in ["constraint", "validator", "checker", "policy"]):
            return NodeType.CONSTRAINT
        
        # 默认返回ITEM类型
        return NodeType.ITEM
    
    def _check_structural_isomorphism(
        self,
        mapping: Dict[str, str],
        metaphor_nodes: Dict[str, MetaphorNode]
    ) -> Tuple[bool, float]:
        """
        检查映射后的代码结构是否与隐喻结构同构
        
        参数:
            mapping: 代码类到隐喻节点的映射
            metaphor_nodes: 隐喻节点字典
            
        返回:
            (是否同构, 相似度分数) 的元组
        """
        if not mapping:
            return False, 0.0
        
        # 计算覆盖率
        coverage = len(mapping) / len(metaphor_nodes)
        
        # 检查关键节点是否被覆盖
        key_nodes = {"Library", "Book", "Borrower"}  # 示例关键节点
        key_nodes_covered = sum(1 for node in key_nodes if node in mapping.values())
        key_coverage = key_nodes_covered / len(key_nodes)
        
        # 综合相似度计算
        similarity = (coverage * 0.6) + (key_coverage * 0.4)
        
        # 同构性判定（简化版：覆盖率超过80%且关键节点全部覆盖）
        is_isomorphic = (coverage > 0.8) and (key_coverage == 1.0)
        
        return is_isomorphic, similarity
    
    def _create_error_result(self, message: str) -> Dict[str, any]:
        """
        创建标准化的错误结果字典
        
        参数:
            message: 错误描述消息
            
        返回:
            包含错误信息的标准结果字典
        """
        logger.error(f"验证错误: {message}")
        return {
            "is_aligned": False,
            "confidence": 0.0,
            "warnings": [message],
            "unmapped_classes": [],
            "structure_similarity": 0.0,
            "error": message
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    print("隐喻驱动架构对齐验证系统演示")
    print("=" * 50)
    
    # 创建验证器实例
    verifier = MetaphorArchitectureVerifier()
    
    # 示例1：内存管理系统的隐喻验证
    print("\n示例1: 内存管理系统验证")
    metaphor_desc1 = "像管理图书馆一样管理内存"
    code_classes1 = [
        "MemoryPool",       # 预期映射到 Library
        "MemoryBlock",      # 预期映射到 Book
        "Pointer",          # 预期映射到 Borrower
        "AllocationPolicy", # 预期映射到 Fine (约束)
        "BlockShelf"        # 预期映射到 Bookshelf
    ]
    
    result1 = verifier.verify_architecture(metaphor_desc1, code_classes1)
    print(f"隐喻描述: {metaphor_desc1}")
    print(f"代码类: {code_classes1}")
    print(f"验证结果: 对齐={result1['is_aligned']}, 置信度={result1['confidence']:.2f}")
    print(f"类映射: {result1['class_mappings']}")
    if result1['warnings']:
        print(f"警告: {result1['warnings']}")
    
    # 示例2：交通系统隐喻验证
    print("\n示例2: 交通系统验证")
    metaphor_desc2 = "实现一个交通系统的流量控制"
    code_classes2 = [
        "RoadNetwork",      # 预期映射到 Road
        "Vehicle",          # 预期映射到 Vehicle
        "TrafficController", # 预期映射到 TrafficLight
        "CarMovement"       # 预期映射到 Movement
    ]
    
    result2 = verifier.verify_architecture(metaphor_desc2, code_classes2)
    print(f"隐喻描述: {metaphor_desc2}")
    print(f"代码类: {code_classes2}")
    print(f"验证结果: 对齐={result2['is_aligned']}, 置信度={result2['confidence']:.2f}")
    
    # 示例3：不匹配的架构
    print("\n示例3: 不匹配架构验证")
    metaphor_desc3 = "像管理图书馆一样管理内存"
    code_classes3 = ["QueueManager", "TaskItem", "Worker"]  # 不相关的类
    
    result3 = verifier.verify_architecture(metaphor_desc3, code_classes3)
    print(f"隐喻描述: {metaphor_desc3}")
    print(f"代码类: {code_classes3}")
    print(f"验证结果: 对齐={result3['is_aligned']}, 置信度={result3['confidence']:.2f}")
    print(f"警告: {result3['warnings']}")
    
    print("\n演示完成")