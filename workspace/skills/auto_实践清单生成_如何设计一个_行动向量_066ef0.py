"""
模块名称: auto_实践清单生成_如何设计一个_行动向量_066ef0
描述: 【实践清单生成】如何设计一个'行动向量'映射函数
版本: 1.0.0
作者: Senior Python Engineer (AGI System Component)

该模块实现了将抽象的语义节点转化为具体物理世界可执行的微行动指令的功能。
它综合考量了时间、资源、人体工程学等物理约束，是连接AI认知与人类实践的桥梁。
"""

import logging
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnergyLevel(Enum):
    """能量/体力水平枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class DifficultyLevel(Enum):
    """任务难度枚举"""
    EASY = 1
    MEDIUM = 2
    HARD = 3

@dataclass
class SemanticNode:
    """
    抽象语义节点数据结构。
    代表AI规划中的一个意图或概念。
    
    Attributes:
        node_id (str): 节点唯一标识符
        description (str): 节点的自然语言描述 (例如: "锻炼身体")
        intent_type (str): 意图类型 (例如: "physical_activity", "cognitive_task")
        estimated_difficulty (DifficultyLevel): 预估难度
        context_tags (Dict[str, Any]): 上下文标签 (如地点、工具需求)
    """
    node_id: str
    description: str
    intent_type: str
    estimated_difficulty: DifficultyLevel
    context_tags: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PhysicalConstraints:
    """
    物理约束条件数据结构。
    定义了人类执行者当前的状态和环境限制。
    
    Attributes:
        current_time (datetime.time): 当前时间
        available_duration_minutes (int): 可用时长（分钟）
        current_energy (EnergyLevel): 当前体能水平
        location (str): 当前位置
        tools_available (List[str]): 可用工具列表
    """
    current_time: datetime.time
    available_duration_minutes: int
    current_energy: EnergyLevel
    location: str
    tools_available: List[str] = field(default_factory=list)

@dataclass
class MicroAction:
    """
    微行动指令数据结构。
    这是输出给人类执行者的具体指令。
    
    Attributes:
        action_id (str): 行动ID
        parent_node_id (str): 关联的父节点ID
        instruction (str): 具体的执行指令
        duration_minutes (int): 预计耗时
        ergo_risk_score (float): 人体工程学风险评分 (0.0-1.0, 越高越危险)
        required_tools (List[str]): 所需工具
        execution_sequence (int): 执行顺序
    """
    action_id: str
    parent_node_id: str
    instruction: str
    duration_minutes: int
    ergo_risk_score: float
    required_tools: List[str]
    execution_sequence: int

def validate_inputs(node: SemanticNode, constraints: PhysicalConstraints) -> bool:
    """
    辅助函数：验证输入数据的完整性和合法性。
    
    Args:
        node (SemanticNode): 待验证的语义节点
        constraints (PhysicalConstraints): 待验证的物理约束
    
    Returns:
        bool: 如果验证通过返回 True
    
    Raises:
        ValueError: 如果数据缺失或不合规
    """
    if not node.node_id or not node.description:
        logger.error("节点验证失败: 缺少ID或描述")
        raise ValueError("节点必须包含ID和描述")
    
    if constraints.available_duration_minutes <= 0:
        logger.warning("可用时长为0或负数，将生成空指令集")
        return False
        
    logger.debug(f"输入验证通过: Node {node.node_id}")
    return True

def calculate_ergonomic_risk(action_intensity: DifficultyLevel, energy: EnergyLevel) -> float:
    """
    辅助函数：计算人体工程学风险评分。
    
    基于任务强度与当前体能的匹配度计算风险。
    
    Args:
        action_intensity (DifficultyLevel): 动作强度
        energy (EnergyLevel): 当前体能
    
    Returns:
        float: 风险评分 (0.1 到 1.0)
    """
    # 将枚举转换为数值进行计算
    intensity_val = action_intensity.value
    energy_val = energy.value
    
    # 如果任务强度 > 体能，风险较高
    if intensity_val > energy_val:
        risk = 0.5 + (intensity_val - energy_val) * 0.25
    else:
        risk = 0.1 + (intensity_val / 10.0)
    
    # 边界检查
    return min(max(risk, 0.0), 1.0)

def generate_action_vector(
    target_node: SemanticNode, 
    current_constraints: PhysicalConstraints
) -> List[MicroAction]:
    """
    核心函数：生成行动向量。
    
    将抽象节点映射为具体的微行动列表。该函数包含核心逻辑：
    1. 约束检查 (时间、资源)
    2. 指令分解 (将抽象描述转化为具体步骤)
    3. 人体工程学适配 (调整强度)
    
    Args:
        target_node (SemanticNode): 抽象的目标节点
        current_constraints (PhysicalConstraints): 当前物理约束
    
    Returns:
        List[MicroAction]: 可执行的微行动指令列表
    
    Example:
        >>> node = SemanticNode("001", "阅读技术文档", "cognitive", DifficultyLevel.MEDIUM)
        >>> constraints = PhysicalConstraints(datetime.time(14, 0), 30, EnergyLevel.MEDIUM, "Office")
        >>> actions = generate_action_vector(node, constraints)
    """
    try:
        if not validate_inputs(target_node, current_constraints):
            return []
            
        logger.info(f"开始为节点 '{target_node.description}' 生成行动向量...")
        
        action_plan: List[MicroAction] = []
        
        # 简单的分解逻辑示例 (实际AGI系统此处会接入LLM或规划引擎)
        # 根据意图类型生成模版指令
        base_instructions = []
        
        if target_node.intent_type == "physical_activity":
            base_instructions = ["准备装备", "进行热身", "执行核心动作", "整理放松"]
        elif target_node.intent_type == "cognitive_task":
            base_instructions = ["准备环境", "阅读/分析", "记录要点", "总结复盘"]
        else:
            base_instructions = ["开始任务", "执行中", "结束任务"]

        # 根据可用时间调整步骤粒度
        time_per_step = current_constraints.available_duration_minutes // len(base_instructions)
        if time_per_step < 5:
            logger.warning("时间过短，已压缩行动步骤")
            base_instructions = base_instructions[:2] # 压缩步骤
            
        # 生成具体指令
        for idx, instruction_template in enumerate(base_instructions):
            # 计算风险
            risk = calculate_ergonomic_risk(target_node.estimated_difficulty, current_constraints.current_energy)
            
            # 动态调整指令内容
            specific_instruction = f"[{target_node.context_tags.get('focus', '通用')}] {instruction_template}"
            
            # 检查工具可用性
            needed_tools = []
            if "tools_required" in target_node.context_tags:
                needed_tools = [t for t in target_node.context_tags["tools_required"] if t in current_constraints.tools_available]
                if len(needed_tools) < len(target_node.context_tags["tools_required"]):
                    logger.warning(f"步骤 {idx+1}: 缺少部分推荐工具")

            action = MicroAction(
                action_id=f"{target_node.node_id}_act_{idx}",
                parent_node_id=target_node.node_id,
                instruction=specific_instruction,
                duration_minutes=time_per_step,
                ergo_risk_score=risk,
                required_tools=needed_tools,
                execution_sequence=idx + 1
            )
            action_plan.append(action)
            
        logger.info(f"成功生成 {len(action_plan)} 个微行动指令")
        return action_plan

    except Exception as e:
        logger.error(f"生成行动向量时发生严重错误: {str(e)}", exc_info=True)
        return []

def optimize_sequence(action_list: List[MicroAction]) -> List[MicroAction]:
    """
    核心函数：优化行动序列。
    
    根据人体工程学和依赖关系对生成的行动列表进行重排序或合并。
    此处实现一个简单的 "低能耗优先" 排序示例。
    
    Args:
        action_list (List[MicroAction]): 原始行动列表
    
    Returns:
        List[MicroAction]: 优化后的行动列表
    """
    if not action_list:
        return []
        
    logger.info("正在优化行动序列...")
    
    # 这里示例按风险评分排序，优先做风险低（轻松）的事，或者根据特定逻辑
    # 注意：实际生产环境中，这里会涉及复杂的依赖图分析
    # 此处仅演示对列表的处理能力
    
    # 模拟优化：给用户一个缓冲期，如果第一个动作风险 > 0.7，插入一个准备动作
    if action_list[0].ergo_risk_score > 0.7:
        warm_up = MicroAction(
            action_id="pre_check",
            parent_node_id=action_list[0].parent_node_id,
            instruction="深度呼吸与心理准备",
            duration_minutes=2,
            ergo_risk_score=0.1,
            required_tools=[],
            execution_sequence=0
        )
        action_list.insert(0, warm_up)
        # 重新编号
        for i, action in enumerate(action_list):
            action.execution_sequence = i + 1
            
    return action_list

# ==========================================
# 使用示例与模块测试
# ==========================================
if __name__ == "__main__":
    # 1. 定义输入数据
    sample_node = SemanticNode(
        node_id="NODE_2023_X92",
        description="进行高强度的代码重构",
        intent_type="cognitive_task",
        estimated_difficulty=DifficultyLevel.HARD,
        context_tags={
            "focus": "Python后端", 
            "tools_required": ["Laptop", "IDE", "Coffee"]
        }
    )
    
    sample_constraints = PhysicalConstraints(
        current_time=datetime.time(14, 30),
        available_duration_minutes=45,
        current_energy=EnergyLevel.MEDIUM, # 能量中等，但任务很难
        location="Home Office",
        tools_available=["Laptop", "IDE", "Water"] # 缺少 Coffee
    )
    
    # 2. 生成行动向量
    print("--- 正在生成行动向量 ---")
    raw_actions = generate_action_vector(sample_node, sample_constraints)
    
    # 3. 优化序列
    print("--- 正在优化序列 ---")
    optimized_actions = optimize_sequence(raw_actions)
    
    # 4. 打印结果
    print("\n=== 最终行动清单 ===")
    for action in optimized_actions:
        print(f"[{action.execution_sequence}] {action.instruction}")
        print(f"   - 耗时: {action.duration_minutes}分钟")
        print(f"   - 风险: {action.ergo_risk_score:.2f}")
        print(f"   - 工具: {action.required_tools}")