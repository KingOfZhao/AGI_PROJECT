"""
动态知识图谱的'真实节点'固化协议 (Dynamic Knowledge Graph Node Solidification Protocol)

该模块实现了一套算法机制，旨在人机共生环境中（AI建议 -> 人类实践 -> 人类反馈），
识别闭环完成的时刻，并将经过验证的临时信息转化为永久的、高权重的“真实节点”。

核心功能：
1. 量化实践验证权重。
2. 防止低质量或错误数据污染核心网络。
3. 动态调整节点的不可篡改性。

作者: AGI System
版本: 1.0.0
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, TypedDict, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NodeSolidificationProtocol")

class NodeType(Enum):
    """节点类型枚举"""
    TEMPORARY = "temporary"   # 临时节点，待验证
    CANDIDATE = "candidate"   # 候选节点，正在验证中
    SOLID = "solid"           # 固化节点，高可信度
    CORE = "core"             # 核心节点，不可变

class FeedbackMetric(TypedDict):
    """人类反馈指标结构"""
    success_rate: float       # 实践成功率 (0.0 - 1.0)
    consistency_score: float  # 与现有知识的一致性 (0.0 - 1.0)
    feedback_count: int       # 反馈数量
    last_updated: str         # ISO格式时间戳

class KnowledgeNode:
    """
    知识图谱节点类
    """
    def __init__(self, node_id: str, content: str, initial_trust: float = 0.1):
        self.node_id = node_id
        self.content = content
        self.node_type = NodeType.TEMPORARY
        self.trust_score = initial_trust  # 综合信任分值
        self.feedback_data: FeedbackMetric = {
            "success_rate": 0.0,
            "consistency_score": 0.0,
            "feedback_count": 0,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.immutable_hash: Optional[str] = None
        logger.debug(f"Initialized node {node_id} with type {self.node_type.value}")

    def generate_hash(self) -> str:
        """生成节点内容的不可变哈希指纹"""
        data_payload = {
            "id": self.node_id,
            "content": self.content,
            "trust": round(self.trust_score, 4),
            "type": self.node_type.value
        }
        payload_str = json.dumps(data_payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

    def update_feedback(self, success: bool, consistency: float):
        """更新反馈指标"""
        current = self.feedback_data
        total_count = current['feedback_count'] + 1
        
        # 增量更新成功率
        old_success_count = current['success_rate'] * current['feedback_count']
        new_success_count = old_success_count + (1.0 if success else 0.0)
        new_success_rate = new_success_count / total_count
        
        # 增量更新一致性
        old_consistency_sum = current['consistency_score'] * current['feedback_count']
        new_consistency = (old_consistency_sum + consistency) / total_count
        
        self.feedback_data = {
            "success_rate": new_success_rate,
            "consistency_score": new_consistency,
            "feedback_count": total_count,
            "last_updated": datetime.utcnow().isoformat()
        }

class SolidificationProtocol:
    """
    固化协议主类
    
    负责管理节点的生命周期，评估验证权重，并执行固化操作。
    """
    
    # 固化阈值常量
    MIN_FEEDBACK_THRESHOLD = 5        # 最小反馈样本数
    MIN_TRUST_SCORE_THRESHOLD = 0.85  # 成为Solid节点的信任分阈值
    CORE_TRUST_THRESHOLD = 0.95       # 成为Core节点的信任分阈值
    
    def __init__(self):
        self.node_registry: Dict[str, KnowledgeNode] = {}
        
    def add_node(self, node: KnowledgeNode) -> bool:
        """添加节点到协议监控中"""
        if not isinstance(node, KnowledgeNode):
            logger.error("Invalid node type provided.")
            return False
        
        if node.node_id in self.node_registry:
            logger.warning(f"Node {node.node_id} already exists.")
            return False
            
        self.node_registry[node.node_id] = node
        logger.info(f"Node {node.node_id} added to protocol.")
        return True

    def calculate_verification_weight(self, node: KnowledgeNode) -> float:
        """
        [核心函数 1]
        计算节点的实践验证权重。
        
        算法逻辑：
        1. 基础分 = 实践成功率 * 权重(0.6)
        2. 一致性分 = 一致性分数 * 权重(0.4)
        3. 样本置信度惩罚 = 如果样本量少于阈值，则线性降低权重
        
        Args:
            node (KnowledgeNode): 待评估的节点
            
        Returns:
            float: 0.0 到 1.0 之间的综合权重分
        """
        metrics = node.feedback_data
        
        # 边界检查
        if metrics['feedback_count'] == 0:
            return 0.0
            
        # 基础加权分
        score = (metrics['success_rate'] * 0.6) + (metrics['consistency_score'] * 0.4)
        
        # 样本置信度惩罚
        # 如果反馈数量少于最小阈值，应用惩罚因子
        if metrics['feedback_count'] < self.MIN_FEEDBACK_THRESHOLD:
            penalty_factor = metrics['feedback_count'] / self.MIN_FEEDBACK_THRESHOLD
            score *= penalty_factor
            
        logger.debug(f"Calculated weight for {node.node_id}: {score:.4f}")
        return round(score, 4)

    def attempt_solidification(self, node_id: str) -> bool:
        """
        [核心函数 2]
        尝试将节点状态升级并固化。
        
        验证逻辑：
        1. 检查样本量是否足够
        2. 计算当前验证权重
        3. 决定是否提升状态 (TEMPORARY -> CANDIDATE -> SOLID -> CORE)
        4. 如果达到SOLID状态，生成不可变哈希
        
        Args:
            node_id (str): 节点ID
            
        Returns:
            bool: 如果状态发生改变返回 True，否则 False
        """
        if node_id not in self.node_registry:
            logger.error(f"Node {node_id} not found in registry.")
            return False
            
        node = self.node_registry[node_id]
        current_type = node.node_type
        
        # 1. 样本量检查
        if node.feedback_data['feedback_count'] < self.MIN_FEEDBACK_THRESHOLD:
            logger.info(f"Node {node_id} needs more feedback ({node.feedback_data['feedback_count']}/{self.MIN_FEEDBACK_THRESHOLD})")
            return False
            
        # 2. 计算最新权重
        new_trust_score = self.calculate_verification_weight(node)
        node.trust_score = new_trust_score
        
        # 3. 状态转移逻辑
        new_type = current_type
        
        if new_trust_score >= self.CORE_TRUST_THRESHOLD:
            new_type = NodeType.CORE
        elif new_trust_score >= self.MIN_TRUST_SCORE_THRESHOLD:
            new_type = NodeType.SOLID
        elif new_trust_score >= 0.5:
            new_type = NodeType.CANDIDATE
        else:
            # 如果分数过低，甚至可能降级（此处略，主要关注固化）
            pass
            
        # 4. 执行固化
        if new_type != current_type:
            node.node_type = new_type
            logger.info(f"Node {node_id} status upgraded: {current_type.value} -> {new_type.value}")
            
            if new_type in [NodeType.SOLID, NodeType.CORE]:
                self._lock_node(node)
            return True
            
        return False

    def _lock_node(self, node: KnowledgeNode) -> None:
        """
        [辅助函数]
        锁定节点，生成哈希指纹，防止篡改。
        """
        node.immutable_hash = node.generate_hash()
        logger.warning(f"NODE LOCKED: {node.node_id} is now {node.node_type.value}. Hash: {node.node_hash[:16]}...")

    def inject_feedback_loop(self, node_id: str, is_success: bool, consistency: float) -> Dict[str, Union[str, float]]:
        """
        模拟外部调用接口：注入一次完整的人机反馈循环结果。
        
        Args:
            node_id: 节点ID
            is_success: 人类实践是否成功
            consistency: 与现有知识库的一致性检查结果 (0.0-1.0)
            
        Returns:
            包含更新后状态的字典
        """
        if node_id not in self.node_registry:
            return {"error": "Node not found"}
            
        # 数据校验
        consistency = max(0.0, min(1.0, consistency))
        
        node = self.node_registry[node_id]
        node.update_feedback(is_success, consistency)
        
        # 触发固化检查
        changed = self.attempt_solidification(node_id)
        
        return {
            "node_id": node_id,
            "new_trust_score": node.trust_score,
            "current_type": node.node_type.value,
            "status_changed": changed,
            "is_locked": node.immutable_hash is not None
        }

# ================= 使用示例 =================
if __name__ == "__main__":
    # 初始化协议
    protocol = SolidificationProtocol()
    
    # 场景：AI建议一个代码优化策略
    node_content = "建议在循环中使用局部变量引用来优化Python性能"
    test_node = KnowledgeNode(node_id="opt_py_loop_01", content=node_content)
    protocol.add_node(test_node)
    
    print(f"--- 开始模拟人机共生循环 for {test_node.node_id} ---")
    
    # 模拟 1: 少量反馈，不足以固化
    for _ in range(3):
        result = protocol.inject_feedback_loop("opt_py_loop_01", is_success=True, consistency=0.9)
    
    print(f"Status after 3 loops: {result['current_type']}, Trust: {result['new_trust_score']}")
    
    # 模拟 2: 大量高质量反馈，触发固化
    for _ in range(10):
        result = protocol.inject_feedback_loop("opt_py_loop_01", is_success=True, consistency=0.95)
        
    print(f"Status after 13 loops: {result['current_type']}, Trust: {result['new_trust_score']}")
    
    # 模拟 3: 极高信任，成为核心
    for _ in range(20):
        result = protocol.inject_feedback_loop("opt_py_loop_01", is_success=True, consistency=0.99)
        
    print(f"Final Status: {result['current_type']}, Trust: {result['new_trust_score']}")
    if result['is_locked']:
        print(f"Node is now IMMUTABLE with hash.")