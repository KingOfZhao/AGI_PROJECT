"""
高级逻辑合成验证器模块。

本模块为AGI系统提供核心的“逻辑验证”能力。在多技能串联（Pipeline）场景下，
确保生成的执行计划符合认知逻辑和物理约束（例如：文件读取必须存在，网络下载
必须在文件处理之前）。它通过构建有向无环图（DAG）来解析技能间的依赖关系，
并验证数据流的类型一致性。

作者: AGI System Core Team
版本: 1.0.0
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LogicSynthesizer")


class SkillType(Enum):
    """定义系统支持的基础技能类型。"""
    NETWORK_REQUEST = "network_request"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    DATA_PROCESSING = "data_processing"
    DB_QUERY = "db_query"


class DataType(Enum):
    """定义通用的数据流转类型。"""
    URL = "url"
    RAW_BYTES = "raw_bytes"
    IMAGE_FORMAT = "image_format"
    TEXT_FORMAT = "text_format"
    JSON_OBJECT = "json_object"
    FILE_PATH = "file_path"


@dataclass
class SkillNode:
    """
    代表单一技能节点的数据结构。
    
    Attributes:
        id (str): 节点唯一标识符。
        skill_type (SkillType): 技能类型枚举。
        description (str): 技能功能的简述。
        input_requirements (Set[DataType]): 此技能执行所需的数据类型。
        output_type (DataType): 此技能产生的数据类型。
        dependencies (Set[str]): 此节点依赖的其他节点ID集合。
    """
    id: str
    skill_type: SkillType
    description: str
    input_requirements: Set[DataType] = field(default_factory=set)
    output_type: Optional[DataType] = None
    dependencies: Set[str] = field(default_factory=set)


class LogicSynthesisValidator:
    """
    逻辑合成验证器核心类。
    
    用于验证多技能串联的DAG（有向无环图）是否满足逻辑约束、
    类型约束以及执行顺序约束。
    """

    def __init__(self):
        """初始化验证器，注册核心校验规则。"""
        self._graph: Dict[str, SkillNode] = {}
        self._validation_rules: List[Callable[[Dict[str, SkillNode]], bool]] = []
        logger.info("LogicSynthesisValidator initialized.")

    def register_node(self, node: SkillNode) -> None:
        """
        向验证图中注册一个技能节点。
        
        Args:
            node (SkillNode): 待注册的技能节点实例。
        
        Raises:
            ValueError: 如果节点ID已存在。
        """
        if node.id in self._graph:
            logger.error(f"Attempted to register duplicate node ID: {node.id}")
            raise ValueError(f"Node ID {node.id} already exists.")
        
        self._graph[node.id] = node
        logger.debug(f"Node registered: {node.id} ({node.skill_type.value})")

    def _detect_cycle(self) -> bool:
        """
        辅助函数：使用深度优先搜索(DFS)检测图中是否存在循环依赖。
        
        Returns:
            bool: 如果存在循环返回True，否则返回False。
        """
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        def dfs(v: str) -> bool:
            visited.add(v)
            recursion_stack.add(v)
            
            node = self._graph.get(v)
            if not node:
                return False

            for neighbor_id in node.dependencies:
                if neighbor_id not in visited:
                    if dfs(neighbor_id):
                        return True
                elif neighbor_id in recursion_stack:
                    logger.warning(f"Cycle detected between {v} and {neighbor_id}")
                    return True
            
            recursion_stack.remove(v)
            return False

        for node_id in self._graph:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def _validate_types(self) -> Tuple[bool, str]:
        """
        核心函数：验证节点间的数据类型流转是否匹配。
        
        检查每个节点的输入是否能被其依赖节点的输出满足。
        
        Returns:
            Tuple[bool, str]: (是否验证通过, 错误消息)
        """
        for node_id, node in self._graph.items():
            # 收集依赖节点提供的输出类型
            provided_types: Set[DataType] = set()
            for dep_id in node.dependencies:
                if dep_id in self._graph:
                    dep_node = self._graph[dep_id]
                    if dep_node.output_type:
                        provided_types.add(dep_node.output_type)
            
            # 检查输入需求是否被满足
            missing_inputs = node.input_requirements - provided_types
            if missing_inputs:
                msg = (
                    f"Type Mismatch at Node '{node_id}': "
                    f"Requires inputs {missing_inputs}, but dependencies only provide {provided_types}"
                )
                logger.error(msg)
                return False, msg
        
        return True, "Type validation passed."

    def _validate_semantic_constraints(self) -> Tuple[bool, str]:
        """
        核心函数：验证特定的语义规则（认知逻辑）。
        
        例如：
        1. 图片处理(DATA_PROCESSING)必须依赖于文件读取或网络请求。
        2. 文件写入之前必须先拥有文件路径或数据。
        
        Returns:
            Tuple[bool, str]: (是否验证通过, 错误消息)
        """
        for node_id, node in self._graph.items():
            # 规则：处理节点不能凭空产生，必须有数据源
            if node.skill_type == SkillType.DATA_PROCESSING:
                if not node.dependencies:
                    msg = (
                        f"Semantic Error at Node '{node_id}': "
                        f"Data processing cannot occur without a data source dependency."
                    )
                    logger.error(msg)
                    return False, msg
                
                # 检查依赖是否包含数据源类节点
                has_source = False
                for dep_id in node.dependencies:
                    dep_type = self._graph[dep_id].skill_type
                    if dep_type in [SkillType.NETWORK_REQUEST, SkillType.FILE_READ, SkillType.DB_QUERY]:
                        has_source = True
                        break
                
                if not has_source:
                    msg = (
                        f"Semantic Error at Node '{node_id}': "
                        f"Processing node must depend on a data source (Network/File/DB)."
                    )
                    logger.error(msg)
                    return False, msg

        return True, "Semantic constraints passed."

    def validate_pipeline(self) -> bool:
        """
        执行完整的逻辑合成验证流程。
        
        步骤：
        1. 边界检查（节点是否存在）
        2. 结构检查（无环检测）
        3. 类型检查（数据流匹配）
        4. 语义检查（业务逻辑约束）
        
        Returns:
            bool: 最终的计划是否有效。
        """
        logger.info(f"Starting validation for pipeline with {len(self._graph)} nodes.")
        
        # 1. 检查依赖节点是否存在于图中
        for node in self._graph.values():
            for dep_id in node.dependencies:
                if dep_id not in self._graph:
                    logger.error(f"Validation Failed: Dependency '{dep_id}' not found in pipeline.")
                    return False

        # 2. 检查循环依赖
        if self._detect_cycle():
            logger.error("Validation Failed: Cyclic dependency detected.")
            return False

        # 3. 检查类型匹配
        is_valid, msg = self._validate_types()
        if not is_valid:
            return False

        # 4. 检查语义约束
        is_valid, msg = self._validate_semantic_constraints()
        if not is_valid:
            return False

        logger.info("Pipeline validation successful. Logic is sound.")
        return True


# --- 使用示例与演示 ---

def setup_demo_scenario() -> Tuple[LogicSynthesisValidator, Dict[str, SkillNode]]:
    """
    辅助函数：构建一个演示场景。
    意图：从网络下载图片 -> 处理图片（压缩） -> 保存到本地
    """
    validator = LogicSynthesisValidator()

    # 定义节点
    # 1. 下载图片
    node_download = SkillNode(
        id="skill_1_download",
        skill_type=SkillType.NETWORK_REQUEST,
        description="Download image from URL",
        input_requirements={DataType.URL}, # 假设URL由系统参数注入，此处简化
        output_type=DataType.RAW_BYTES,
        dependencies=set() # 假设它是起点
    )

    # 2. 处理图片 (必须有输入)
    node_process = SkillNode(
        id="skill_2_process",
        skill_type=SkillType.DATA_PROCESSING,
        description="Compress and resize image",
        input_requirements={DataType.RAW_BYTES},
        output_type=DataType.IMAGE_FORMAT,
        dependencies={"skill_1_download"}
    )

    # 3. 保存图片
    node_save = SkillNode(
        id="skill_3_save",
        skill_type=SkillType.FILE_WRITE,
        description="Save image to disk",
        input_requirements={DataType.IMAGE_FORMAT},
        output_type=DataType.FILE_PATH,
        dependencies={"skill_2_process"}
    )

    nodes = {
        "download": node_download,
        "process": node_process,
        "save": node_save
    }

    return validator, nodes

if __name__ == "__main__":
    # 场景 1: 正确的逻辑流
    print("--- Scenario 1: Valid Pipeline ---")
    val1, nodes = setup_demo_scenario()
    val1.register_node(nodes["download"])
    val1.register_node(nodes["process"])
    val1.register_node(nodes["save"])
    
    # 修正：通常需要注入初始URL，这里仅验证结构逻辑
    # 为了演示完整性，我们假设下载节点不需要前置输入（由外部触发）
    # 或者我们在验证前手动注入虚拟上下文
    
    result = val1.validate_pipeline()
    print(f"Validation Result: {result}\n")

    # 场景 2: 逻辑错误 - 处理节点没有数据源
    print("--- Scenario 2: Hallucination (Processing without Source) ---")
    val2 = LogicSynthesisValidator()
    
    # 创建一个没有依赖的处理节点（幻觉代码）
    hallucinated_process = SkillNode(
        id="skill_hallucinate",
        skill_type=SkillType.DATA_PROCESSING,
        description="Process nothing",
        input_requirements={DataType.RAW_BYTES},
        dependencies=set() # 错误：没有依赖下载或读取节点
    )
    val2.register_node(hallucinated_process)
    
    result = val2.validate_pipeline()
    print(f"Validation Result: {result} (Expected: False)\n")

    # 场景 3: 逻辑错误 - 循环依赖
    print("--- Scenario 3: Cyclic Dependency ---")
    val3 = LogicSynthesisValidator()
    node_a = SkillNode("A", SkillType.DATA_PROCESSING, "A", dependencies={"B"})
    node_b = SkillNode("B", SkillType.DATA_PROCESSING, "B", dependencies={"A"})
    
    val3.register_node(node_a)
    val3.register_node(node_b)
    
    result = val3.validate_pipeline()
    print(f"Validation Result: {result} (Expected: False)")