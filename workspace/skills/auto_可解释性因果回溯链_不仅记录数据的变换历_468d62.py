"""
可解释性因果回溯链

本模块实现了一个高级的数据谱系追踪系统，专为AGI和复杂决策系统设计。
它不仅记录数据的变换历史（数据血缘），还同步捕获每一步变换背后的
'业务意图'、'假设'和'上下文'（情景记忆）。

当系统产生异常输出或偏差时，该模块允许通过 '数据血缘 + 业务语境'
重现决策现场，精确定位导致偏差的根源，实现真正的可解释AI (XAI)。
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CausalTraceChain")

@dataclass
class TraceNode:
    """
    单个追踪节点，代表决策链中的一个步骤。
    
    Attributes:
        node_id (str): 唯一标识符。
        timestamp (str): 创建时间。
        input_state (Dict[str, Any]): 该步骤的输入数据快照或引用。
        output_state (Dict[str, Any]): 该步骤的输出数据。
        transformation (str): 变换逻辑的描述（如函数名或逻辑描述）。
        intent (str): 业务意图（为什么要这样做）。
        assumptions (List[str]): 此步骤依赖的假设列表。
        confidence (float): 执行此步骤时的置信度 (0.0-1.0)。
        metadata (Dict[str, Any]): 额外的元数据。
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    input_state: Dict[str, Any] = field(default_factory=dict)
    output_state: Dict[str, Any] = field(default_factory=dict)
    transformation: str = "N/A"
    intent: str = "Undefined"
    assumptions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not isinstance(self.assumptions, list):
            raise TypeError("Assumptions must be a list of strings.")

class InterpretabilityChain:
    """
    可解释性因果回溯链管理器。
    
    负责构建、存储和分析决策路径。它模拟人类的情景记忆，
    将单纯的'数据变换'提升为带有'业务语义'的决策步骤。
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        初始化回溯链。

        Args:
            session_id (str, optional): 会话ID。如果未提供则自动生成。
        """
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.chain: List[TraceNode] = []
        self.current_context: Dict[str, Any] = {} # 模拟当前运行上下文
        logger.info(f"Initialized InterpretabilityChain for session: {self.session_id}")

    def add_node(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        transformation: str,
        intent: str,
        assumptions: Optional[List[str]] = None,
        confidence: float = 1.0
    ) -> TraceNode:
        """
        核心函数：向链中添加一个新的决策节点。
        
        此方法是记录'情景记忆'的核心，不仅记录数据变化，还强制记录意图。

        Args:
            input_data: 输入数据字典。
            output_data: 输出数据字典。
            transformation: 描述性变换逻辑。
            intent: 业务意图描述。
            assumptions: 依赖的假设列表。
            confidence: 决策置信度。

        Returns:
            TraceNode: 创建的节点对象。
        
        Raises:
            ValueError: 如果数据验证失败。
        """
        if assumptions is None:
            assumptions = []
            
        try:
            # 创建节点
            node = TraceNode(
                input_state=self._safe_serialize(input_data),
                output_state=self._safe_serialize(output_data),
                transformation=transformation,
                intent=intent,
                assumptions=assumptions,
                confidence=confidence,
                metadata={"session_context": self.current_context}
            )
            
            self.chain.append(node)
            logger.debug(f"Added node {node.node_id} with intent: {intent}")
            return node
        except Exception as e:
            logger.error(f"Failed to add node: {str(e)}")
            raise

    def investigate_anomaly(self, anomaly_description: str) -> Dict[str, Any]:
        """
        核心函数：调查异常并回溯原因。
        
        模拟人类回忆往事的过程，通过分析意图和假设来解释偏差。

        Args:
            anomaly_description (str): 描述观察到的异常现象。

        Returns:
            Dict[str, Any]: 包含调查报告的字典，包括嫌疑节点和根本原因分析。
        """
        if not self.chain:
            return {"status": "empty_chain", "message": "No history to analyze."}

        logger.warning(f"Investigating anomaly: {anomaly_description}")
        
        # 简单的启发式分析：寻找低置信度节点或特定假设
        suspicious_nodes = []
        for node in reversed(self.chain):
            reasons = []
            if node.confidence < 0.7:
                reasons.append(f"Low confidence ({node.confidence})")
            
            # 这里可以接入LLM进行更复杂的语义分析，此处用简单的关键词匹配演示
            if any("assume" in a.lower() or "guess" in a.lower() for a in node.assumptions):
                reasons.append("Relies on unverified assumptions")
            
            if reasons:
                suspicious_nodes.append({
                    "node_id": node.node_id,
                    "intent": node.intent,
                    "transformation": node.transformation,
                    "flags": reasons,
                    "input_snapshot": node.input_state
                })

        report = {
            "session_id": self.session_id,
            "anomaly": anomaly_description,
            "total_steps": len(self.chain),
            "suspected_root_causes": suspicious_nodes,
            "conclusion": "Review the flagged steps for potential logic errors or bad data sources." if suspicious_nodes else "No obvious technical flags, check external factors."
        }
        
        return report

    def _safe_serialize(self, data: Any) -> Dict[str, Any]:
        """
        辅助函数：安全地序列化数据以用于存储或显示。
        
        处理非JSON兼容对象和大对象，防止内存溢出。
        """
        MAX_LEN = 200
        try:
            # 尝试简单转换
            if isinstance(data, dict):
                # 对过长的字符串进行截断处理
                return {k: (v if len(str(v)) < MAX_LEN else str(v)[:MAX_LEN] + "...") for k, v in data.items()}
            return {"value": data}
        except Exception:
            return {"raw": "Unserializable data"}

    def visualize_chain(self) -> str:
        """
        辅助函数：生成简单的文本可视化链条。
        """
        if not self.chain:
            return "Empty Chain"
        
        output = []
        output.append(f"--- Trace Chain (Session: {self.session_id}) ---")
        for i, node in enumerate(self.chain):
            prefix = "└──>" if i == len(self.chain) - 1 else "├──>"
            output.append(
                f"{prefix} Step {i+1}: {node.intent}\n"
                f"    Transform: {node.transformation} (Conf: {node.confidence})\n"
                f"    Assumptions: {node.assumptions}"
            )
        return "\n".join(output)

# 使用示例
if __name__ == "__main__":
    # 1. 初始化系统
    tracer = InterpretabilityChain(session_id="AGI_Task_001")
    
    # 模拟上下文
    tracer.current_context = {"user": "admin", "mode": "automation"}

    # 2. 步骤1：数据获取（记录意图）
    raw_data = {"temperature": 105, "status": "overheating"}
    cleaned_data = {"temp_c": 105, "is_alert": True}
    tracer.add_node(
        input_data=raw_data,
        output_data=cleaned_data,
        transformation="normalize_and_flag",
        intent="标准化传感器数据并标记高温警报",
        assumptions=["传感器已校准"],
        confidence=0.95
    )

    # 3. 步骤2：决策逻辑（包含潜在的错误假设）
    # 假设系统错误地认为只要温度高就需要关闭系统，忽略了可能是传感器故障
    action = {"command": "shutdown_system", "reason": "Critical temp"}
    tracer.add_node(
        input_data=cleaned_data,
        output_data=action,
        transformation="make_decision",
        intent="基于温度执行安全关闭",
        assumptions=["温度读数准确，非传感器故障", "当前负载可中断"], # 这里的假设可能是导致问题的关键
        confidence=0.65 # 这里的置信度较低
    )

    # 4. 可视化链条
    print(tracer.visualize_chain())

    # 5. 模拟异常：系统误关机，开始调查
    print("\n--- 开始回溯调查 ---")
    report = tracer.investigate_anomaly("系统在非关键时刻意外关机")
    
    print(f"调查结果: {json.dumps(report, indent=2, ensure_ascii=False)}")