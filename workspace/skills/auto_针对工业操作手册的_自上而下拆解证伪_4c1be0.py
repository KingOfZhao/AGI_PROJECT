"""
名称: auto_针对工业操作手册的_自上而下拆解证伪_4c1be0
描述: 针对工业操作手册的'自上而下拆解证伪'：如何将长篇大论的PDF文档解析为原子化的'动作原语'（Action Primitives），
      并自动检测其中的逻辑矛盾（如手册说'严禁带电操作'，但故障排查章节暗示需通电检测）？
领域: document_understanding
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PowerState(Enum):
    """设备电源状态的枚举"""
    ON = "通电"
    OFF = "断电"
    UNKNOWN = "未知"

class ActionType(Enum):
    """动作类型的枚举"""
    OPERATION = "操作"
    MAINTENANCE = "维护"
    TROUBLESHOOTING = "故障排查"
    SAFETY_CHECK = "安全检查"

@dataclass
class ActionPrimitive:
    """
    原子化动作原语数据结构
    """
    step_id: str
    raw_text: str
    required_state: PowerState
    action_type: ActionType
    source_section: str
    constraints: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.raw_text:
            raise ValueError("raw_text cannot be empty")

@dataclass
class LogicalContradiction:
    """逻辑矛盾检测结果的数据结构"""
    primitive_1: ActionPrimitive
    primitive_2: ActionPrimitive
    conflict_reason: str
    severity: str  # "HIGH", "MEDIUM", "LOW"

def extract_power_state(text: str) -> PowerState:
    """
    [辅助函数] 使用关键词匹配提取文本中的电源状态要求。
    
    Args:
        text (str): 原始文本片段。
        
    Returns:
        PowerState: 推断出的电源状态枚举值。
    """
    # 定义正则模式
    power_on_patterns = re.compile(
        r"(通电|带电|开启电源|电源开启|运行中|启动设备|上电)", re.IGNORECASE
    )
    power_off_patterns = re.compile(
        r"(断电|断开电源|切断电源|严禁带电|断开|拔掉电源|下电)", re.IGNORECASE
    )
    
    if power_off_patterns.search(text):
        return PowerState.OFF
    if power_on_patterns.search(text):
        return PowerState.ON
    
    return PowerState.UNKNOWN

def parse_manual_to_primitives(
    document_sections: List[Tuple[str, str]]
) -> List[ActionPrimitive]:
    """
    [核心函数 1] 将文档章节解析为动作原语列表。
    
    模拟了自上而下的拆解过程：文档 -> 章节 -> 段落 -> 动作原语。
    在实际AGI场景中，这里会接入LLM或Layout Analysis模型。
    
    Args:
        document_sections (List[Tuple[str, str]]): 包含(章节标题, 内容)的列表。
        
    Returns:
        List[ActionPrimitive]: 提取出的动作原语列表。
        
    Raises:
        ValueError: 如果输入数据格式不正确。
    """
    if not isinstance(document_sections, list):
        logger.error("Invalid input type: document_sections must be a list.")
        raise ValueError("Input must be a list of tuples.")
        
    primitives: List[ActionPrimitive] = []
    primitive_counter = 0
    
    logger.info(f"Starting decomposition of {len(document_sections)} sections...")
    
    for section_title, content in document_sections:
        # 简单的边界检查
        if not content or len(content.strip()) < 5:
            continue
            
        # 模拟拆解：按句号分割，模拟原子化过程
        sentences = re.split(r'[。\n]', content)
        
        # 推断动作类型 (简单规则，实际应用可用分类器)
        current_action_type = ActionType.OPERATION
        if "故障" in section_title or "排查" in section_title:
            current_action_type = ActionType.TROUBLESHOOTING
        elif "安全" in section_title:
            current_action_type = ActionType.SAFETY_CHECK
        elif "维护" in section_title:
            current_action_type = ActionType.MAINTENANCE
            
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5: # 过滤太短的片段
                continue
                
            primitive_counter += 1
            state = extract_power_state(sentence)
            
            # 如果无法确定状态，根据上下文推断 (这里简化处理)
            # 在AGI系统中，这里会使用上下文Embedding检索
            
            prim = ActionPrimitive(
                step_id=f"PRIM_{primitive_counter:04d}",
                raw_text=sentence,
                required_state=state,
                action_type=current_action_type,
                source_section=section_title
            )
            primitives.append(prim)
            
    logger.info(f"Decomposition complete. Generated {len(primitives)} primitives.")
    return primitives

def detect_logic_contradictions(
    primitives: List[ActionPrimitive]
) -> List[LogicalContradiction]:
    """
    [核心函数 2] 检测动作原语集合中的逻辑矛盾。
    
    主要检测场景：
    1. 安全检查要求'断电'，但故障排查步骤要求'通电'（且未特别说明）。
    2. 同一章节内的相互冲突指令。
    
    Args:
        primitives (List[ActionPrimitive]): 动作原语列表。
        
    Returns:
        List[LogicalContradiction]: 检测到的矛盾列表。
    """
    if not primitives:
        return []

    contradictions: List[LogicalContradiction] = []
    
    # 提取全局安全约束 (例如：所有 SAFETY_CHECK 类型的 OFF 状态)
    global_safety_constraints: List[ActionPrimitive] = [
        p for p in primitives 
        if p.action_type == ActionType.SAFETY_CHECK and p.required_state == PowerState.OFF
    ]
    
    # 检查操作步骤是否违反全局安全约束
    for prim in primitives:
        # 场景：如果是一个需要通电的操作
        if prim.required_state == PowerState.ON:
            for constraint in global_safety_constraints:
                # 如果这个操作没有特殊的豁免声明（这里简化为检查源章节是否不同）
                # 并且该操作属于维护或排查类（通常高风险）
                if prim.source_section != constraint.source_section:
                    conflict = LogicalContradiction(
                        primitive_1=constraint,
                        primitive_2=prim,
                        conflict_reason=(
                            f"潜在冲突：'{constraint.source_section}'要求"
                            f"'{constraint.required_state.value}'，但"
                            f"'{prim.source_section}'中的步骤暗示需要"
                            f"'{prim.required_state.value}'。"
                        ),
                        severity="HIGH"
                    )
                    contradictions.append(conflict)
                    logger.warning(f"Contradiction detected: {conflict.conflict_reason}")

    # 去重简单的重复告警 (简化逻辑)
    unique_conflicts = []
    seen_pairs = set()
    for c in contradictions:
        pair_id = tuple(sorted([c.primitive_1.step_id, c.primitive_2.step_id]))
        if pair_id not in seen_pairs:
            seen_pairs.add(pair_id)
            unique_conflicts.append(c)
            
    return unique_conflicts

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟从PDF解析出的工业手册文本片段
    sample_manual_data = [
        ("1. 安全总则", "在进行任何维修工作前，必须确保设备已完全断电。严禁带电操作，以防触电风险。"),
        ("2. 日常操作", "按下绿色启动按钮以通电启动设备。等待自检完成。"),
        ("3. 故障排查指南", "如果设备无法启动，请检查电源指示灯。若指示灯不亮，请保持通电状态使用万用表测量输入电压。")
    ]

    try:
        print("--- 开始处理工业操作手册 ---")
        
        # 步骤 1: 拆解文档
        action_primitives = parse_manual_to_primitives(sample_manual_data)
        
        print(f"\n--- 提取到 {len(action_primitives)} 个动作原语 ---")
        for p in action_primitives[:3]: # 仅展示前3个
            print(f"[{p.step_id}] Section: {p.source_section} | State: {p.required_state.value}")
            print(f"   Text: {p.raw_text}")

        # 步骤 2: 逻辑证伪/矛盾检测
        print("\n--- 开始逻辑矛盾检测 ---")
        conflicts = detect_logic_contradictions(action_primitives)
        
        if conflicts:
            print(f"检测到 {len(conflicts)} 个潜在逻辑冲突：")
            for idx, conflict in enumerate(conflicts, 1):
                print(f"\n冲突 #{idx} (严重性: {conflict.severity}):")
                print(f"原因: {conflict.conflict_reason}")
                print(f"原语A: {conflict.primitive_1.raw_text} (来自: {conflict.primitive_1.source_section})")
                print(f"原语B: {conflict.primitive_2.raw_text} (来自: {conflict.primitive_2.source_section})")
        else:
            print("未检测到明显的逻辑矛盾。")

    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)