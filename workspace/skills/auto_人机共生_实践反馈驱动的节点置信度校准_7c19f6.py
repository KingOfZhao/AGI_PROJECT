"""
名称: auto_人机共生_实践反馈驱动的节点置信度校准_7c19f6
描述: 【人机共生】实践反馈驱动的节点置信度校准。当一个节点（如‘某种销售话术’）被人类在真实世界
      证伪或验证后，如何反向传播更新该节点的权重及其相连的边缘理论？这是实现‘持续碰撞’与进化的关键机制。
领域: cognitive_science
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackSignal(Enum):
    """反馈信号枚举，定义节点验证的状态"""
    VALIDATED = 1.0      # 验证为真
    NEUTRAL = 0.5        # 无明确结论
    FALSIFIED = 0.0      # 证伪
    HIGHLY_EFFECTIVE = 1.5 # 超出预期

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识符
        concept (str): 节点代表的概念（如 '稀缺性销售话术'）
        confidence (float): 当前置信度/权重 [0.0, 1.0]
        version (int): 节点版本号，用于追踪演化
        related_edges (Set[str]): 相连的边缘理论或上下文节点ID集合
    """
    id: str
    concept: str
    confidence: float = 0.5
    version: int = 1
    related_edges: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """初始化后验证数据"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0和1.0之间，当前值: {self.confidence}")

@dataclass
class FeedbackPayload:
    """
    实践反馈载荷。
    
    Attributes:
        node_id (str): 目标节点ID
        signal (FeedbackSignal): 反馈信号类型
        intensity (float): 反馈强度/冲击力 [0.1, 2.0]
        context (Dict): 环境上下文数据（如市场波动、用户画像）
    """
    node_id: str
    signal: FeedbackSignal
    intensity: float = 1.0
    context: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not 0.1 <= self.intensity <= 2.0:
            logger.warning(f"反馈强度 {self.intensity} 超出建议范围 [0.1, 2.0]，已自动截断。")
            self.intensity = np.clip(self.intensity, 0.1, 2.0)

class CognitiveGraphManager:
    """
    认知图谱管理器：负责维护节点状态及网络拓扑结构。
    模拟人类认知结构中概念与理论的连接。
    """
    
    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self._initialize_sandbox_knowledge()
        logger.info("CognitiveGraphManager 已初始化。")

    def _initialize_sandbox_knowledge(self):
        """初始化沙盒知识库，用于演示"""
        # 模拟节点：销售话术
        self.add_node(KnowledgeNode(id="sp_001", concept="限时折扣话术", confidence=0.8))
        # 模拟节点：支撑理论（边缘理论）
        self.add_node(KnowledgeNode(id="th_001", concept="损失厌恶理论", confidence=0.9))
        # 建立连接
        self.link_nodes("sp_001", "th_001")

    def add_node(self, node: KnowledgeNode):
        """添加节点到图谱"""
        if node.id in self.nodes:
            logger.warning(f"节点 {node.id} 已存在，将覆盖。")
        self.nodes[node.id] = node
        logger.debug(f"节点 {node.id} ('{node.concept}') 已加入图谱。")

    def link_nodes(self, node_a_id: str, node_b_id: str):
        """建立双向连接"""
        if node_a_id in self.nodes and node_b_id in self.nodes:
            self.nodes[node_a_id].related_edges.add(node_b_id)
            self.nodes[node_b_id].related_edges.add(node_a_id)
            logger.debug(f"已建立连接: {node_a_id} <-> {node_b_id}")
        else:
            logger.error("无法建立连接：节点ID不存在。")

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """安全获取节点"""
        return self.nodes.get(node_id)

class FeedbackCalibrator:
    """
    核心校准器：处理现实世界的反馈，驱动认知进化。
    实现 '实践-理论' 的双向修正机制。
    """

    def __init__(self, graph_manager: CognitiveGraphManager):
        self.graph = graph_manager
        self.learning_rate = 0.1  # 学习率/遗忘率
        self.propagation_decay = 0.5 # 传播衰减因子

    def process_real_world_feedback(self, feedback: FeedbackPayload) -> bool:
        """
        [核心函数 1]
        处理单次真实世界的反馈，更新目标节点及其关联网络。
        
        Args:
            feedback (FeedbackPayload): 包含节点ID、信号强度和上下文的反馈数据
            
        Returns:
            bool: 是否成功完成校准
            
        Raises:
            ValueError: 如果节点不存在
        """
        logger.info(f"接收到反馈 -> 节点: {feedback.node_id}, 信号: {feedback.signal.name}, 强度: {feedback.intensity}")
        
        target_node = self.graph.get_node(feedback.node_id)
        if not target_node:
            logger.error(f"节点 {feedback.node_id} 未找到，反馈处理终止。")
            return False

        try:
            # 1. 更新当前节点（直接冲击）
            self._update_node_confidence(target_node, feedback)
            
            # 2. 反向传播更新关联理论（间接冲击）
            self._propagate_to_edges(target_node, feedback)
            
            return True
        except Exception as e:
            logger.exception(f"校准过程中发生异常: {e}")
            return False

    def _update_node_confidence(self, node: KnowledgeNode, feedback: FeedbackPayload):
        """
        [辅助函数]
        使用梯度下降/上升思想更新节点置信度。
        
        逻辑：
        - 如果验证成功，增加置信度，逼近1.0
        - 如果证伪，大幅降低置信度，逼近0.0
        - 包含环境上下文的微调（此处简化处理）
        """
        old_confidence = node.confidence
        target_value = feedback.signal.value
        
        # 计算差值
        error = target_value - old_confidence
        
        # 根据反馈强度和学习率调整步长
        adjustment = error * self.learning_rate * feedback.intensity
        
        # 应用S型平滑（可选，此处直接加减以保持简单）
        new_confidence = old_confidence + adjustment
        
        # 边界检查与截断
        node.confidence = np.clip(new_confidence, 0.0, 1.0)
        node.version += 1
        
        logger.info(f"节点 '{node.concept}' 置信度更新: {old_confidence:.3f} -> {node.confidence:.3f} (v{node.version})")

    def _propagate_to_edges(self, source_node: KnowledgeNode, feedback: FeedbackPayload):
        """
        [核心函数 2]
        将反馈效应传播到相连的边缘节点（理论支撑）。
        
        逻辑：
        - 如果一个应用节点（如话术）被证伪，其依赖的理论节点置信度也应下降。
        - 使用衰减因子 propagation_decay 减少对理论层的影响。
        """
        if not source_node.related_edges:
            return

        logger.info(f"开始传播反馈至 {len(source_node.related_edges)} 个关联节点...")
        
        for edge_id in source_node.related_edges:
            edge_node = self.graph.get_node(edge_id)
            if edge_node:
                # 构造衰减后的虚拟反馈
                propagated_intensity = feedback.intensity * self.propagation_decay
                
                # 只有在强烈的反向信号下才修正理论，正向信号对理论的增强有限（避免过拟合）
                if feedback.signal == FeedbackSignal.FALSIFIED:
                    # 理论被削弱
                    delta = -0.05 * propagated_intensity
                    edge_node.confidence = np.clip(edge_node.confidence + delta, 0.0, 1.0)
                    logger.info(f"关联理论 '{edge_node.concept}' 受到波及，置信度调整为: {edge_node.confidence:.3f}")
                elif feedback.signal == FeedbackSignal.HIGHLY_EFFECTIVE:
                    # 极度成功略微增强底层理论
                    delta = 0.02 * propagated_intensity
                    edge_node.confidence = np.clip(edge_node.confidence + delta, 0.0, 1.0)
                    logger.info(f"关联理论 '{edge_node.concept}' 得到强化，置信度调整为: {edge_node.confidence:.3f}")

# ----------------------------
# 使用示例与数据格式说明
# ----------------------------
if __name__ == "__main__":
    # 1. 初始化系统
    graph_manager = CognitiveGraphManager()
    calibrator = FeedbackCalibrator(graph_manager)

    # 2. 查看初始状态
    node_sp = graph_manager.get_node("sp_001")
    node_th = graph_manager.get_node("th_001")
    print(f"\n初始状态 -> 话术: {node_sp.confidence}, 理论: {node_th.confidence}")

    # 3. 模拟场景 A: 销售话术在真实世界被证伪（客户反感）
    print("\n--- 场景 A: 话术被证伪 ---")
    negative_feedback = FeedbackPayload(
        node_id="sp_001",
        signal=FeedbackSignal.FALSIFIED,
        intensity=1.2, # 强烈反馈
        context={"region": "NA", "customer_type": "Enterprise"}
    )
    calibrator.process_real_world_feedback(negative_feedback)

    # 4. 查看传播结果
    node_sp = graph_manager.get_node("sp_001")
    node_th = graph_manager.get_node("th_001")
    print(f"更新后状态 -> 话术: {node_sp.confidence}, 理论: {node_th.confidence}")
    
    # 5. 模拟场景 B: 另一种话术效果极佳
    print("\n--- 场景 B: 新话术大获成功 ---")
    # 假设我们添加一个新节点并关联到同一个理论
    graph_manager.add_node(KnowledgeNode(id="sp_002", concept="社会认同话术", confidence=0.6))
    graph_manager.link_nodes("sp_002", "th_001")
    
    positive_feedback = FeedbackPayload(
        node_id="sp_002",
        signal=FeedbackSignal.HIGHLY_EFFECTIVE,
        intensity=1.5
    )
    calibrator.process_real_world_feedback(positive_feedback)
    
    node_th = graph_manager.get_node("th_001")
    print(f"理论层最终状态 (理论: {node_th.confidence}) - 观察其恢复或增强")