"""
认知操作系统内核 - 混合中间表示构建模块.

该模块实现了一个支持精确逻辑与模糊语义的混合中间表示（IR）系统，
旨在实现人机共生编程：人类表达意图，IR层负责解析、编译与资源分发。

Version: 1.0.0
Author: AGI System
License: MIT
"""

import logging
import json
import uuid
import re
from typing import Dict, List, Optional, Union, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveOS.IR")


class IntentType(Enum):
    """意图类型枚举，定义IR支持的输入类别."""
    NATURAL_LANGUAGE = "text"
    CODE_SNIPPET = "code"
    STRUCTURED_DATA = "json"
    VISUAL_SKETCH = "sketch_uri"


class ExecutionMode(Enum):
    """执行模式枚举."""
    PRECISE = "precise"  # 精确逻辑执行
    FUZZY = "fuzzy"      # 模糊语义搜索/生成
    HYBRID = "hybrid"    # 混合模式


class TargetAgent(Enum):
    """目标执行代理枚举."""
    ROBOTICS = "robot_control"
    SOFTWARE_API = "api_executor"
    DATABASE = "db_query"
    SIMULATION = "env_sim"


@dataclass
class SemanticAtom:
    """语义原子：IR的最小单位，包含概念和置信度."""
    concept: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class HybridIR:
    """
    混合中间表示（Hybrid Intermediate Representation）.
    
    Attributes:
        id (str): 唯一标识符
        timestamp (str): 创建时间戳
        source_intent (str): 原始输入内容
        intent_type (IntentType): 输入类型
        semantic_graph (List[SemanticAtom]): 语义图（模糊部分）
        logic_struct (Dict[str, Any]): 逻辑结构（精确部分，如AST或JSON逻辑）
        targets (List[TargetAgent]): 目标执行代理
        priority (int): 优先级 (0-9)
    """
    id: str = field(default_factory=lambda: f"ir_{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_intent: str = ""
    intent_type: IntentType = IntentType.NATURAL_LANGUAGE
    semantic_graph: List[SemanticAtom] = field(default_factory=list)
    logic_struct: Dict[str, Any] = field(default_factory=dict)
    targets: List[TargetAgent] = field(default_factory=list)
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """将IR转换为可序列化的字典."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source_intent": self.source_intent,
            "intent_type": self.intent_type.value,
            "semantic_graph": [asdict(atom) for atom in self.semantic_graph],
            "logic_struct": self.logic_struct,
            "targets": [t.value for t in self.targets],
            "priority": self.priority
        }


def _validate_input_boundaries(raw_input: str, max_length: int = 10000) -> bool:
    """
    辅助函数：验证输入数据的边界和安全性.
    
    Args:
        raw_input (str): 原始输入字符串
        max_length (int): 允许的最大长度
        
    Returns:
        bool: 是否通过验证
        
    Raises:
        ValueError: 如果输入为空或超过长度限制
    """
    if not raw_input:
        logger.error("Input validation failed: Empty input")
        raise ValueError("Input cannot be empty")
    
    if len(raw_input) > max_length:
        logger.error(f"Input validation failed: Length {len(raw_input)} > {max_length}")
        raise ValueError(f"Input exceeds maximum allowed length of {max_length}")
        
    # 简单的注入检查（示例）
    forbidden_patterns = ["<script>", "DROP TABLE", "rm -rf"]
    for pattern in forbidden_patterns:
        if pattern in raw_input:
            logger.warning(f"Potential malicious pattern detected: {pattern}")
            # 在真实系统中这里可能会抛出安全异常
            
    return True


def parse_natural_language_to_ir(text: str, context: Optional[Dict] = None) -> HybridIR:
    """
    核心函数1：将自然语言解析为混合IR.
    
    模拟NLP解析过程，将文本拆解为语义原子和逻辑结构。
    
    Args:
        text (str): 自然语言输入字符串
        context (Optional[Dict]): 上下文信息，用于消歧
        
    Returns:
        HybridIR: 生成的混合中间表示对象
        
    Example:
        >>> ir = parse_natural_language_to_ir("把温度设置为25度并保存到数据库")
        >>> print(ir.targets)
        [<TargetAgent.ROBOTICS: 'robot_control'>, <TargetAgent.DATABASE: 'db_query'>]
    """
    _validate_input_boundaries(text)
    logger.info(f"Parsing natural language: {text[:50]}...")
    
    ir = HybridIR(source_intent=text, intent_type=IntentType.NATURAL_LANGUAGE)
    
    # 1. 模糊语义提取
    # 这里使用简单的规则模拟，实际AGI系统会使用LLM或知识图谱
    tokens = text.split()
    ir.semantic_graph = [SemanticAtom(concept=token, confidence=0.85) for token in tokens]
    
    # 2. 精确逻辑提取
    # 意图识别：设置参数
    if "设置" in text or "把" in text:
        ir.logic_struct["action"] = "SET_VALUE"
        
    # 实体识别：数值
    numbers = re.findall(r'\d+', text)
    if numbers:
        ir.logic_struct["value"] = int(numbers[0])
        
    # 3. 目标推断
    if "温度" in text or "机器人" in text:
        ir.targets.append(TargetAgent.ROBOTICS)
    if "数据库" in text or "保存" in text:
        ir.targets.append(TargetAgent.DATABASE)
        
    # 优先级计算
    if "紧急" in text or "立即" in text:
        ir.priority = 9
    else:
        ir.priority = 5
        
    logger.info(f"IR generated with {len(ir.targets)} targets.")
    return ir


def dispatch_ir_to_agents(ir: HybridIR, available_agents: List[str) -> Dict[TargetAgent, Dict]:
    """
    核心函数2：将IR分发给执行代理并处理冲突.
    
    根据IR中的目标列表，将任务分配给具体的代理。
    如果发生资源冲突（例如同时要求机器人移动和停止），此层负责解决。
    
    Args:
        ir (HybridIR): 编译后的中间表示
        available_agents (List[str]): 当前可用的代理列表（字符串形式）
        
    Returns:
        Dict[TargetAgent, Dict]: 分发结果映射，包含每个代理的指令载荷
        
    Raises:
        RuntimeError: 如果没有可用的目标代理
    """
    if not ir.targets:
        logger.warning(f"IR {ir.id} has no target agents. Dispatch aborted.")
        raise RuntimeError("Cannot dispatch IR with no target agents")
        
    dispatch_result = {}
    logger.info(f"Dispatching IR {ir.id} to agents...")
    
    # 冲突检测逻辑（简单示例）
    # 假设机器人和软件API不能同时独占资源
    has_robot = TargetAgent.ROBOTICS in ir.targets
    has_api = TargetAgent.SOFTWARE_API in ir.targets
    
    if has_robot and has_api:
        logger.warning("Resource conflict detected: Robotics vs API. Prioritizing Robotics based on safety protocols.")
        # 移除API目标以解决冲突
        ir.targets = [t for t in ir.targets if t != TargetAgent.SOFTWARE_API]

    for target in ir.targets:
        # 检查代理是否在线/可用
        if target.value not in available_agents:
            logger.error(f"Target agent {target.value} is not available.")
            continue
            
        # 构造特定代理的载荷
        payload = {}
        if target == TargetAgent.ROBOTICS:
            payload = {
                "command": ir.logic_struct.get("action", "IDLE"),
                "params": {"value": ir.logic_struct.get("value")},
                "safety_check": True
            }
        elif target == TargetAgent.DATABASE:
            payload = {
                "query": "INSERT INTO logs (intent, timestamp) VALUES (?, ?)",
                "args": [ir.source_intent, ir.timestamp]
            }
            
        dispatch_result[target] = payload
        logger.info(f"Successfully dispatched to {target.value} with payload: {str(payload)[:50]}...")
        
    return dispatch_result


class CognitiveKernel:
    """
    认知操作系统内核类，封装整个流程.
    """
    
    def __init__(self):
        self.ir_history: List[HybridIR] = []
        self.agent_pool = ["robot_control", "api_executor", "db_query"]
        logger.info("Cognitive Kernel Initialized.")

    def execute_intent(self, user_input: str) -> Tuple[str, Dict]:
        """
        执行意图的主入口.
        
        Args:
            user_input (str): 用户的原始输入
            
        Returns:
            Tuple[str, Dict]: (执行状态, 详细结果)
        """
        try:
            # 1. 编译为IR
            current_ir = parse_natural_language_to_ir(user_input)
            self.ir_history.append(current_ir)
            
            # 2. 分发
            results = dispatch_ir_to_agents(current_ir, self.agent_pool)
            
            return "SUCCESS", results
        except ValueError as ve:
            return "INPUT_ERROR", {"message": str(ve)}
        except Exception as e:
            logger.critical(f"System Error: {e}", exc_info=True)
            return "SYSTEM_FAILURE", {"message": "Internal kernel error"}

# 示例用法 (如果作为脚本运行)
if __name__ == "__main__":
    # 初始化内核
    kernel = CognitiveKernel()
    
    # 模拟用户输入
    user_command = "把车间的温度设置为25度并立即保存日志"
    
    print(f"Processing command: '{user_command}'")
    status, result = kernel.execute_intent(user_command)
    
    print(f"\nExecution Status: {status}")
    print("Dispatch Details:")
    for agent, payload in result.items():
        print(f"  Agent: {agent.value}")
        print(f"  Payload: {json.dumps(payload, indent=4)}")
        
    # 验证边界检查
    try:
        long_str = "a" * 20000
        kernel.execute_intent(long_str)
    except ValueError as e:
        print(f"\nBoundary Check Passed: {e}")