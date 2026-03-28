"""
Module: auto_构建_语境敏感的原子技能网络_每个sk_da1ecd
Description: 构建'语境敏感的原子技能网络'。
             每个Skill节点不仅是代码片段，还是一个'语用学单元'。
             拆解时，不仅分析物理动作，还保留'前件'和'后件'的逻辑约束。
             例如，'旋紧'节点自带'对齐'的前置约束和'防松'的后置语境。
             这能解决Skill复用中的'语境丢失'问题，实现真正的'积木式'重组。
Author: AGI System Generator
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillState(Enum):
    """技能节点状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class ContextualConstraint:
    """
    语境约束数据结构。
    用于定义技能执行的前件或后件。
    """
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    validation_logic: Optional[Callable[[Dict], bool]] = None  # 验证函数的占位符

@dataclass
class PragmaticSkillNode:
    """
    语用学技能节点。
    
    Attributes:
        skill_id (str): 唯一标识符
        name (str): 技能名称 (e.g., '旋紧', '抓取')
        action_code (str): 物理动作执行的代码逻辑或指令
        preconditions (List[ContextualConstraint]): 前件约束列表 (必须满足的语境)
        postconditions (List[ContextualConstraint]): 后件语境列表 (执行后的状态改变)
        context_tags (Set[str]): 语境标签，用于快速检索和分类
        state (SkillState): 当前执行状态
        rollback_logic (Optional[str]): 失败时的回滚逻辑
    """
    skill_id: str = field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:6]}")
    name: str = "Undefined Skill"
    action_code: str = ""
    preconditions: List[ContextualConstraint] = field(default_factory=list)
    postconditions: List[ContextualConstraint] = field(default_factory=list)
    context_tags: Set[str] = field(default_factory=set)
    state: SkillState = SkillState.PENDING
    rollback_logic: Optional[str] = None

    def to_dict(self) -> Dict:
        """将节点序列化为字典，便于JSON传输或存储"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "action_code": self.action_code,
            "preconditions": [asdict(c) for c in self.preconditions],
            "postconditions": [asdict(c) for c in self.postconditions],
            "context_tags": list(self.context_tags),
            "state": self.state.value,
            "rollback_logic": self.rollback_logic
        }

class ContextualSkillNetwork:
    """
    语境敏感的原子技能网络。
    
    管理技能节点的构建、连接、验证和执行。
    确保'积木式'重组时的逻辑一致性。
    """

    def __init__(self, network_name: str = "DefaultNetwork"):
        self.network_name = network_name
        self.nodes: Dict[str, PragmaticSkillNode] = {}
        self.adjacency_list: Dict[str, List[str]] = {} # 邻接表表示的有向图
        logger.info(f"Initialized Contextual Skill Network: {network_name}")

    def add_skill_node(self, node: PragmaticSkillNode) -> bool:
        """
        核心函数1: 添加一个新的语用学技能节点到网络中。
        
        Args:
            node (PragmaticSkillNode): 待添加的技能节点
            
        Returns:
            bool: 添加是否成功
            
        Raises:
            ValueError: 如果节点ID已存在或数据无效
        """
        if not isinstance(node, PragmaticSkillNode):
            logger.error("Invalid node type provided.")
            raise TypeError("Input must be an instance of PragmaticSkillNode")
        
        if node.skill_id in self.nodes:
            logger.warning(f"Skill ID {node.skill_id} already exists.")
            return False
            
        # 边界检查：确保核心属性不为空
        if not node.name or not node.action_code:
            logger.error("Skill name and action_code cannot be empty.")
            raise ValueError("Skill name and action code are mandatory fields")

        self.nodes[node.skill_id] = node
        self.adjacency_list[node.skill_id] = []
        logger.info(f"Added skill node: {node.name} (ID: {node.skill_id})")
        return True

    def link_skills(self, source_id: str, target_id: str, check_logic: bool = True) -> bool:
        """
        核心函数2: 连接两个技能节点，并自动检查语境兼容性。
        
        验证源节点的后件是否满足目标节点的前件（语义接口匹配）。
        
        Args:
            source_id (str): 源节点ID
            target_id (str): 目标节点ID
            check_logic (bool): 是否进行逻辑约束检查
            
        Returns:
            bool: 连接是否成功且逻辑兼容
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.error("One or both skill IDs not found in network.")
            return False

        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]

        # 模拟语境兼容性检查 (Pragmatic Interface Check)
        # 在实际AGI系统中，这里会使用推理引擎或LLM进行语义比对
        is_compatible = self._validate_contextual_transition(source_node, target_node)
        
        if check_logic and not is_compatible:
            logger.warning(
                f"Link failed: Post-conditions of '{source_node.name}' "
                f"do not satisfy Pre-conditions of '{target_node.name}'"
            )
            return False

        self.adjacency_list[source_id].append(target_id)
        logger.info(f"Successfully linked {source_node.name} -> {target_node.name}")
        return True

    def _validate_contextual_transition(self, source: PragmaticSkillNode, target: PragmaticSkillNode) -> bool:
        """
        辅助函数: 验证两个节点之间的语境转换逻辑。
        
        检查源节点的Post-condition标签是否覆盖目标节点的Pre-condition标签需求。
        这是一个简化的逻辑推理实现。
        """
        # 提取源节点的输出语境（后件）
        source_post_contexts = {pc.name for pc in source.postconditions}
        # 提取目标节点的输入语境需求（前件）
        target_pre_contexts = {pc.name for pc in target.preconditions}

        # 检查是否包含：这里使用简单的子集检查作为示例
        # 实际场景可能需要更复杂的逻辑包含检查
        missing_contexts = target_pre_contexts - source_post_contexts
        
        if missing_contexts:
            logger.debug(f"Missing contexts for transition: {missing_contexts}")
            # 如果目标节点没有前件要求，默认通过
            if not target_pre_contexts:
                return True
            return False
        
        return True

    def execute_skill_chain(self, start_node_id: str, runtime_context: Dict[str, Any]) -> bool:
        """
        执行从指定节点开始的技能链。
        
        Args:
            start_node_id (str): 起始节点ID
            runtime_context (Dict): 运行时环境变量
            
        Returns:
            bool: 整个链是否执行成功
        """
        if start_node_id not in self.nodes:
            logger.error(f"Start node {start_node_id} not found.")
            return False
            
        # 简单的DFS执行演示
        visited = set()
        stack = [start_node_id]
        
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
                
            node = self.nodes[current_id]
            logger.info(f"Executing Skill: {node.name}...")
            
            # 模拟执行动作代码
            try:
                # 在真实环境中，这里通过沙箱执行 action_code
                node.state = SkillState.RUNNING
                logger.debug(f"Running code: {node.action_code[:50]}...")
                # 假设执行总是成功
                node.state = SkillState.SUCCESS
                visited.add(current_id)
                
                # 将后件添加到运行时语境
                for post in node.postconditions:
                    runtime_context[post.name] = True
                    
            except Exception as e:
                node.state = SkillState.FAILED
                logger.error(f"Skill {node.name} failed: {str(e)}")
                return False
                
            # 添加后续节点到栈
            for neighbor_id in self.adjacency_list[current_id]:
                if neighbor_id not in visited:
                    stack.append(neighbor_id)
                    
        return True

# 使用示例
if __name__ == "__main__":
    # 1. 初始化网络
    net = ContextualSkillNetwork("Assembly_Line_A")

    # 2. 定义原子技能节点
    # 节点A: 对齐部件
    skill_align = PragmaticSkillNode(
        name="Align_Component",
        action_code="robot.move_to(x,y,z); robot.vision_align();",
        preconditions=[
            ContextualConstraint(name="Component_Present", description="部件必须在工作区")
        ],
        postconditions=[
            ContextualConstraint(name="Component_Aligned", description="部件已对齐螺丝孔")
        ],
        context_tags={"assembly", "precision"}
    )

    # 节点B: 旋紧螺丝
    skill_tighten = PragmaticSkillNode(
        name="Tighten_Screw",
        action_code="screwdriver.rotate(360, torque=5);",
        preconditions=[
            ContextualConstraint(name="Component_Aligned", description="必须先对齐") # 依赖A的后件
        ],
        postconditions=[
            ContextualConstraint(name="Joint_Secured", description="连接已紧固")
        ],
        rollback_logic="screwdriver.reverse(360);"
    )

    # 节点C: 防松标记 - 这是一个逻辑检查节点
    skill_mark = PragmaticSkillNode(
        name="Mark_Secure",
        action_code="painter.mark('blue');",
        preconditions=[
            ContextualConstraint(name="Joint_Secured", description="必须先旋紧") # 依赖B的后件
        ],
        postconditions=[]
    )

    # 3. 构建网络 (添加节点)
    net.add_skill_node(skill_align)
    net.add_skill_node(skill_tighten)
    net.add_skill_node(skill_mark)

    # 4. 连接节点 (构建语境链)
    # 这一步会自动验证 A 的后件是否满足 B 的前件
    link1_success = net.link_skills(skill_align.skill_id, skill_tighten.skill_id)
    print(f"Link Align->Tighten: {'Success' if link1_success else 'Failed (Context Mismatch)'}")

    link2_success = net.link_skills(skill_tighten.skill_id, skill_mark.skill_id)
    print(f"Link Tighten->Mark: {'Success' if link2_success else 'Failed (Context Mismatch)'}")

    # 5. 尝试错误的连接
    # 如果我们尝试直接连接 Align -> Mark，应该会失败，因为缺少 "Joint_Secured" 语境
    # (这里为了演示，我们需要先添加节点，如果上面没添加的话)
    print("\nAttempting invalid link (Skipping logic check for demo):")
    # net.link_skills(skill_align.skill_id, skill_mark.skill_id) # 这会返回 False
    
    # 6. 序列化输出
    print("\nNetwork Serialization (JSON):")
    print(json.dumps(skill_tighten.to_dict(), indent=2))