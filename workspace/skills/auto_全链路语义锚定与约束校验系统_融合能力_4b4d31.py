"""
全链路语义锚定与约束校验系统

该模块实现了一个融合能力系统，用于在多轮代码生成对话中建立统一的‘注意力-约束图谱’。
它将代码生成的‘变量作用域’与对话的‘语境记忆’合并处理，确保当用户修改特定变量时，
系统不仅解析指代关系，还能自动激活并校验该变量关联的所有隐式约束（如性能、范围限制）。

版本: 1.0.0
作者: AGI System
"""

import logging
import hashlib
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticAnchoringSystem")

class ConstraintType(Enum):
    """约束类型的枚举"""
    PERFORMANCE = "performance"  # 性能约束，如不超时
    SCOPE_LIMIT = "scope_limit"  # 范围约束，如处理行数限制
    DATA_TYPE = "data_type"      # 数据类型约束
    BUSINESS_LOGIC = "business_logic" # 业务逻辑约束

@dataclass
class ConstraintNode:
    """表示一个具体的约束节点"""
    constraint_id: str
    constraint_type: ConstraintType
    description: str
    is_active: bool = True
    related_variable_ids: Set[str] = field(default_factory=set)

    def validate(self, current_value: Any) -> bool:
        """校验当前值是否满足约束（此处为演示逻辑）"""
        logger.debug(f"Validating constraint {self.constraint_id} for value {current_value}")
        return True

@dataclass
class ContextVariable:
    """语境变量，包含其当前值和关联的约束"""
    var_name: str
    var_id: str
    value: Any
    source_domain: str  # 例如 'domain_A' 或 'domain_B'
    attached_constraints: Set[str] = field(default_factory=set) # 存储约束ID

class SemanticAttentionGraph:
    """
    核心类：注意力-约束图谱
    
    管理变量作用域与语境记忆的合并，处理指代解析与约束传播。
    """

    def __init__(self):
        self._variables: Dict[str, ContextVariable] = {}
        self._constraints: Dict[str, ConstraintNode] = {}
        self._conversation_history_hashes: List[str] = []
        logger.info("SemanticAttentionGraph initialized.")

    def register_variable(self, 
                          var_name: str, 
                          value: Any, 
                          domain: str, 
                          constraint_ids: Optional[List[str]] = None) -> str:
        """
        注册或更新一个变量，并绑定约束。
        
        Args:
            var_name (str): 变量名
            value (Any): 变量值
            domain (str): 所属领域
            constraint_ids (Optional[List[str]]): 关联的约束ID列表
            
        Returns:
            str: 生成的唯一变量ID
        """
        var_id = self._generate_id(f"{var_name}_{domain}")
        
        # 数据校验：确保约束存在
        valid_constraints = set()
        if constraint_ids:
            for cid in constraint_ids:
                if cid in self._constraints:
                    valid_constraints.add(cid)
                else:
                    logger.warning(f"Constraint ID {cid} not found. Skipping binding.")
        
        var = ContextVariable(
            var_name=var_name,
            var_id=var_id,
            value=value,
            source_domain=domain,
            attached_constraints=valid_constraints
        )
        self._variables[var_id] = var
        logger.info(f"Registered variable '{var_name}' (ID: {var_id}) in domain '{domain}'")
        return var_id

    def add_constraint(self, 
                       constraint_type: ConstraintType, 
                       description: str, 
                       related_vars: Optional[List[str]] = None) -> str:
        """
        向图谱中添加一个新的约束节点。
        
        Args:
            constraint_type (ConstraintType): 约束类型
            description (str): 约束描述
            related_vars (Optional[List[str]]): 初始关联的变量ID列表
            
        Returns:
            str: 生成的约束ID
        """
        constraint_id = self._generate_id(f"{constraint_type.value}_{description}")
        node = ConstraintNode(
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            description=description,
            related_variable_ids=set(related_vars) if related_vars else set()
        )
        self._constraints[constraint_id] = node
        logger.info(f"Added constraint node: {constraint_id}")
        return constraint_id

    def resolve_reference_and_validate(self, 
                                       reference_phrase: str, 
                                       proposed_change: Any, 
                                       current_domain: str) -> Tuple[bool, str]:
        """
        核心功能：解析指代（如'改一下它'）并校验修改是否违反隐式约束。
        
        流程：
        1. 解析 reference_phrase 找到目标变量（模拟指代消解）。
        2. 激活该变量关联的所有约束节点。
        3. 模拟应用修改并运行校验逻辑。
        4. 如果违反约束（例如修改导致处理范围扩大），阻断并报警。
        
        Args:
            reference_phrase (str): 用户的指代短语，如 "它"、"那个变量"
            proposed_change (Any): 用户提议的新值或代码逻辑
            current_domain (str): 当前对话所在的领域语境
            
        Returns:
            Tuple[bool, str]: (是否允许修改, 详细消息)
        """
        logger.info(f"Resolving reference: '{reference_phrase}' in domain '{current_domain}'")
        
        # 1. 简单的指代消解模拟（实际场景会使用NLP模型）
        target_var = self._find_variable_by_heuristic(reference_phrase, current_domain)
        
        if not target_var:
            return False, f"无法解析指代: '{reference_phrase}'"
            
        logger.info(f"Reference resolved to variable: {target_var.var_name} (ID: {target_var.var_id})")
        
        # 2. 获取关联约束
        active_constraints = self._get_constraints_for_variable(target_var.var_id)
        
        # 3. 执行校验逻辑
        # 模拟场景：如果用户说“改一下它”，且提议的修改是“处理所有行”，
        # 但变量关联了“只处理前10行”的约束。
        
        for constraint_id in active_constraints:
            node = self._constraints.get(constraint_id)
            if not node: continue
            
            # 特定业务逻辑检查：范围限制
            if node.constraint_type == ConstraintType.SCOPE_LIMIT:
                # 这是一个模拟检查。如果proposed_change暗示了范围扩大（例如字符串包含"all"或"*"）
                # 而约束描述包含"limit"或具体数字
                if self._check_scope_violation(proposed_change, node):
                    error_msg = (f"约束阻断：尝试修改 '{target_var.var_name}' 失败。"
                                 f"违反约束 [{node.constraint_id}]: {node.description}。"
                                 f"系统检测到提议的修改可能破坏原有的范围限制。")
                    logger.warning(error_msg)
                    return False, error_msg
                    
            # 特定业务逻辑检查：性能约束
            if node.constraint_type == ConstraintType.PERFORMANCE:
                if self._check_performance_risk(proposed_change, node):
                    error_msg = (f"风险警告：修改 '{target_var.var_name}' 可能导致性能问题。"
                                 f"约束 [{node.constraint_id}]: {node.description}")
                    logger.warning(error_msg)
                    # 这里可以选择返回False或者仅仅发出警告，根据需求这里设为阻断
                    return False, error_msg

        # 4. 如果通过所有检查，更新图谱状态
        self._update_variable_value(target_var.var_id, proposed_change)
        return True, f"修改成功：变量 {target_var.var_name} 已更新。"

    # ------------------- 辅助函数 -------------------

    def _generate_id(self, base_str: str) -> str:
        """生成唯一ID"""
        return hashlib.md5(base_str.encode('utf-8')).hexdigest()[:8]

    def _find_variable_by_heuristic(self, phrase: str, domain: str) -> Optional[ContextVariable]:
        """
        辅助函数：基于启发式规则查找变量。
        在真实AGI场景中，这里会接入向量数据库或上下文注意力机制。
        """
        # 模拟：如果短语是“它”，查找最近活跃的变量
        if phrase in ["它", "那个", "this"]:
            # 这里简单返回最后一个变量作为演示
            if self._variables:
                return list(self._variables.values())[-1]
        # 尝试精确匹配变量名
        for var in self._variables.values():
            if var.var_name == phrase:
                return var
        return None

    def _get_constraints_for_variable(self, var_id: str) -> List[str]:
        """获取变量绑定的所有约束ID"""
        var = self._variables.get(var_id)
        return list(var.attached_constraints) if var else []

    def _check_scope_violation(self, proposed_change: Any, constraint: ConstraintNode) -> bool:
        """
        辅助函数：检查范围违规。
        逻辑：如果提议包含扩大范围的迹象，且约束限制范围。
        """
        if isinstance(proposed_change, str):
            # 模拟：如果提议包含 "all rows" 但约束是 limit
            if "all" in proposed_change.lower() and "limit" in constraint.description.lower():
                return True
        return False

    def _check_performance_risk(self, proposed_change: Any, constraint: ConstraintNode) -> bool:
        """
        辅助函数：检查性能风险。
        """
        if isinstance(proposed_change, str):
            # 模拟：如果提议包含 "recursive" 且约束是 "timeout"
            if "recursive" in proposed_change.lower() and "timeout" in constraint.description.lower():
                return True
        return False

    def _update_variable_value(self, var_id: str, new_value: Any):
        """内部方法：更新变量值"""
        if var_id in self._variables:
            self._variables[var_id].value = new_value
            logger.info(f"Variable {var_id} updated internally.")

# ------------------- 使用示例 -------------------

if __name__ == "__main__":
    # 初始化系统
    system = SemanticAttentionGraph()
    
    # 1. 定义约束（隐式语境规则）
    # 规则A：数据处理不能超过前10行（领域A的参数约束）
    limit_constraint_id = system.add_constraint(
        ConstraintType.SCOPE_LIMIT, 
        "Limit processing to the first 10 rows to ensure quick response."
    )
    
    # 规则B：操作不能导致超时（领域A的性能约束）
    perf_constraint_id = system.add_constraint(
        ConstraintType.PERFORMANCE, 
        "Operation must not exceed 200ms timeout."
    )

    # 2. 注册变量（代码生成 + 语境记忆）
    # 假设我们有一个数据框变量 df，用户之前设定了只处理头部
    # 将变量与约束绑定
    var_id = system.register_variable(
        var_name="df_processed", 
        value="df.head(10)", 
        domain="data_processing",
        constraint_ids=[limit_constraint_id, perf_constraint_id]
    )

    print("\n--- Test Case 1: Valid Modification ---")
    # 用户说：“把 df_processed 改成倒序”
    # 解析：用户意图是修改 df_processed，但保持原有约束
    success, msg = system.resolve_reference_and_validate(
        reference_phrase="df_processed",
        proposed_change="df.head(10).sort_values(desc=True)",
        current_domain="data_processing"
    )
    print(f"Result: {success} | Message: {msg}")

    print("\n--- Test Case 2: Violation of Scope (Implicit 'Change it') ---")
    # 用户说：“改一下它，我要处理全部数据”
    # 系统解析：“它” -> 指向 df_processed (最近变量)
    # 系统检测：proposed_change 包含 "all"，违反 limit_constraint
    success, msg = system.resolve_reference_and_validate(
        reference_phrase="它",
        proposed_change="process_all_rows(df)", 
        current_domain="chat_interface" # 跨领域对话
    )
    print(f"Result: {success} | Message: {msg}")

    print("\n--- Test Case 3: Violation of Performance ---")
    # 用户说：“改一下它，用递归处理”
    # 系统检测：proposed_change 包含 "recursive"，触发 perf_constraint 警报
    success, msg = system.resolve_reference_and_validate(
        reference_phrase="它",
        proposed_change="recursive_clean(df)", 
        current_domain="chat_interface"
    )
    print(f"Result: {success} | Message: {msg}")