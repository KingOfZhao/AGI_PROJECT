"""
模块: adaptive_confidence_propagation
描述: 在人机共生循环中，实现基于人类专家证伪结果的认知节点置信度反向传播算法。
      该模块通过设计差异化的损失函数，根据工业操作结果的严重程度（如效率低下 vs 机器损坏）
      动态调整系统内部认知节点的权重。
作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, validator, conlist

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型与验证 ---

class OutcomeSeverity(BaseModel):
    """定义操作结果严重程度的配置模型。"""
    severity_level: Literal["none", "low", "medium", "high", "critical"]
    impact_factor: float = Field(..., ge=0.0, le=1.0)
    description: str

    @validator('impact_factor')
    def check_impact(cls, v, values):
        if 'severity_level' in values and values['severity_level'] == 'critical' and v < 0.9:
            raise ValueError("Critical severity must have impact factor >= 0.9")
        return v

class CognitiveNode(BaseModel):
    """认知节点的数据结构。"""
    node_id: str
    description: str
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    connections: List[str] = []
    metadata: Dict = {}

class OperationalContext(BaseModel):
    """操作上下文数据。"""
    operation_id: str
    involved_nodes: List[str]
    predicted_success_prob: float
    actual_outcome: bool  # True for Success, False for Failure
    severity: OutcomeSeverity

# --- 核心类 ---

class ConfidenceBackpropagator:
    """
    实现置信度反向传播的核心算法。
    
    该类维护一个认知节点的知识图谱，并根据外部反馈更新节点的置信度。
    损失函数设计考虑了结果的严重程度和预测偏差。
    """

    def __init__(self, initial_nodes: Optional[List[CognitiveNode]] = None):
        """
        初始化传播器。
        
        Args:
            initial_nodes: 初始认知节点列表。
        """
        self.knowledge_graph: Dict[str, CognitiveNode] = {}
        self.global_learning_rate: float = 0.05
        
        if initial_nodes:
            self._load_nodes(initial_nodes)
        
        logger.info("ConfidenceBackpropagator initialized with %d nodes.", len(self.knowledge_graph))

    def _load_nodes(self, nodes: List[CognitiveNode]) -> None:
        """辅助函数：加载节点到知识图谱。"""
        for node in nodes:
            if node.node_id in self.knowledge_graph:
                logger.warning("Duplicate node ID detected: %s", node.node_id)
            self.knowledge_graph[node.node_id] = node

    def _calculate_loss_delta(self, predicted: float, actual: bool, severity: OutcomeSeverity) -> float:
        """
        核心算法：计算损失增量。
        
        损失函数 = L1_Error * Severity_Factor * Learning_Rate
        其中 Severity_Factor 根据严重程度指数增长。
        
        Args:
            predicted: 预测成功的概率 (0.0 - 1.0)
            actual: 实际结果 (True=成功, False=失败)
            severity: 结果严重程度对象
            
        Returns:
            需要调整的置信度变化量（可能是负数）。
        """
        # 基础误差
        error = (1.0 if actual else 0.0) - predicted
        
        # 严重程度加权因子
        # 如果是失败，严重程度越高，惩罚越大（负增量越大）
        # 如果是成功，严重程度（这里定义为重要性）越高，正向强化越大
        # 此处简化模型：主要关注证伪（失败）场景的惩罚
        if not actual:
            # 失败场景：根据严重程度放大负向调整
            # 例如：Critical (1.0) -> weight = 5.0, Low (0.1) -> weight = 0.5
            severity_weight = 1.0 + (severity.impact_factor * 4.0) 
            loss_delta = error * severity_weight * self.global_learning_rate
        else:
            # 成功场景：微调，防止过拟合
            loss_delta = error * self.global_learning_rate * 0.5
            
        logger.debug(f"Calc Loss: Pred={predicted:.2f}, Act={actual}, Delta={loss_delta:.4f}")
        return loss_delta

    def update_node_confidence(
        self, 
        context: OperationalContext, 
        node_specific_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        根据操作结果更新相关节点的置信度。
        
        Args:
            context: 包含操作结果和涉及节点的上下文对象。
            node_specific_weights: 可选的特定节点权重覆盖。
            
        Returns:
            更新后的节点ID与置信度映射字典。
            
        Raises:
            ValueError: 如果上下文中的节点不存在于知识图谱中。
        """
        updated_nodes: Dict[str, float] = {}
        
        # 数据验证：检查节点是否存在
        missing_nodes = [n for n in context.involved_nodes if n not in self.knowledge_graph]
        if missing_nodes:
            logger.error("Missing nodes in knowledge graph: %s", missing_nodes)
            raise ValueError(f"Unknown cognitive nodes: {missing_nodes}")

        # 计算基础损失增量
        base_delta = self._calculate_loss_delta(
            predicted=context.predicted_success_prob,
            actual=context.actual_outcome,
            severity=context.severity
        )

        logger.info(
            f"Processing Backprop | Op: {context.operation_id} | Outcome: {'Success' if context.actual_outcome else 'Fail'} | Severity: {context.severity.severity_level}"
        )

        # 更新涉及的节点
        for node_id in context.involved_nodes:
            node = self.knowledge_graph[node_id]
            
            # 应用特定节点权重（如果提供），否则平均分配影响
            weight = 1.0
            if node_specific_weights and node_id in node_specific_weights:
                weight = node_specific_weights[node_id]
            
            # 计算最终调整值
            adjustment = base_delta * weight
            
            # 更新置信度并做边界检查
            new_confidence = np.clip(node.confidence + adjustment, 0.0, 1.0)
            
            # 状态更新
            node.confidence = new_confidence
            updated_nodes[node_id] = new_confidence
            
            logger.info(f"Node '{node_id}' updated: {node.confidence - adjustment:.3f} -> {new_confidence:.3f}")

        return updated_nodes

    def get_node_state(self, node_id: str) -> Optional[CognitiveNode]:
        """获取当前节点状态。"""
        return self.knowledge_graph.get(node_id)

# --- 使用示例与辅助函数 ---

def create_default_industrial_knowledge_base() -> List[CognitiveNode]:
    """
    辅助函数：创建默认的工业认知节点知识库。
    """
    return [
        CognitiveNode(
            node_id="vision_sensor_01", 
            description="Main visual sensor for object detection",
            confidence=0.95,
            connections=["gripper_control_01"]
        ),
        CognitiveNode(
            node_id="gripper_control_01",
            description="Hydraulic gripper control module",
            confidence=0.80,
            connections=[]
        ),
        CognitiveNode(
            node_id="path_planner_v2",
            description="Dynamic path planning algorithm",
            confidence=0.60
        )
    ]

def run_simulation():
    """
    运行一个完整的模拟场景：演示机器损坏时的反向传播。
    """
    # 1. 初始化系统
    nodes = create_default_industrial_knowledge_base()
    system = ConfidenceBackpropagator(initial_nodes=nodes)
    
    print("\n--- Initial State ---")
    for n in nodes:
        print(f"{n.node_id}: {n.confidence:.2f}")

    # 2. 定义场景：预测成功，但实际发生严重故障
    # 场景：机械臂移动，预测成功率 90%，但实际导致机器碰撞
    failure_context = OperationalContext(
        operation_id="op_move_123",
        involved_nodes=["vision_sensor_01", "gripper_control_01", "path_planner_v2"],
        predicted_success_prob=0.90,
        actual_outcome=False, # 失败
        severity=OutcomeSeverity(
            severity_level="critical",
            impact_factor=1.0,
            description="Machine collision causing hardware damage."
        )
    )
    
    # 3. 执行反向传播更新
    print("\n--- Processing Critical Failure Feedback ---")
    try:
        updates = system.update_node_confidence(failure_context)
    except ValueError as e:
        print(f"Error during update: {e}")
        return

    # 4. 输出结果
    print("\n--- State After Backpropagation ---")
    for node_id, conf in updates.items():
        print(f"{node_id}: {conf:.4f}")
        
    # 预期结果：由于是Critical级别的失败，且预测成功率很高(0.9)，
    # 损失函数会产生一个较大的负增量，显著降低节点置信度。

if __name__ == "__main__":
    run_simulation()