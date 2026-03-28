"""
名称: auto_基于_人机共生_频率的节点半衰期衰减机制_5aff85
描述: 基于‘人机共生’频率的节点半衰期衰减机制。
      该模块实现了一个动态权重调整系统，根据知识节点的验证频率（人机交互频次）
      和未被访问的时间跨度，利用半衰期衰减算法动态调整其真实性权重。
      当权重低于阈值时，自动触发重检流程，以维护知识库的时效性和准确性。
领域: knowledge_management
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    知识节点的数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        content (str): 知识内容或摘要。
        truth_weight (float): 当前真实性权重 (0.0 到 1.0)。
        last_verified_time (datetime): 上次被验证（访问/使用）的时间。
        total_verifications (int): 累计被验证的次数。
        is_active (bool): 节点是否处于活跃状态（未被归档）。
    """
    node_id: str
    content: str
    truth_weight: float = 1.0
    last_verified_time: datetime = field(default_factory=datetime.now)
    total_verifications: int = 0
    is_active: bool = True

    def __post_init__(self):
        """数据验证和边界检查"""
        if not 0.0 <= self.truth_weight <= 1.0:
            logger.error(f"Node {self.node_id}: 初始权重必须在0.0到1.0之间。")
            raise ValueError("truth_weight must be between 0.0 and 1.0")
        if self.last_verified_time > datetime.now():
            logger.error(f"Node {self.node_id}: 验证时间不能是未来时间。")
            raise ValueError("last_verified_time cannot be in the future")

class KnowledgeDecaySystem:
    """
    实现基于人机共生频率的半衰期衰减机制。
    
    该系统管理知识节点，根据交互频率动态计算半衰期，
    并随时间推移降低节点的真实性权重。
    """
    
    # 系统常量
    BASE_HALF_LIFE_DAYS = 30.0  # 基础半衰期（天）
    MIN_HALF_LIFE_DAYS = 7.0    # 最小半衰期（高频交互节点）
    MAX_HALF_LIFE_DAYS = 365.0  # 最大半衰期（低频交互节点）
    DECAY_THRESHOLD = 0.5       # 触发重检的权重阈值
    VERIFICATION_SCALING_FACTOR = 0.1 # 验证次数对半衰期的影响系数

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}

    def add_node(self, node: KnowledgeNode) -> None:
        """添加一个新的知识节点到系统中。"""
        if node.node_id in self.nodes:
            logger.warning(f"节点 {node.node_id} 已存在，将被覆盖。")
        self.nodes[node.node_id] = node
        logger.info(f"节点 {node.node_id} 已添加到知识库。")

    def calculate_dynamic_half_life(self, node: KnowledgeNode) -> float:
        """
        核心函数1: 计算节点的动态半衰期。
        
        基础半衰期受验证次数（人机共生频率）影响。
        验证次数越多，说明该知识在人类实践中越重要且准确，
        因此其半衰期越长，衰减越慢。
        
        Formula: HalfLife = Base * (1 + log(1 + Verifications * Scale))
        
        Args:
            node (KnowledgeNode): 待计算的知识节点。
            
        Returns:
            float: 动态计算出的半衰期（天数）。
        """
        try:
            # 使用对数函数使验证次数的影响呈现边际效应递减
            freq_factor = math.log(1 + node.total_verifications * self.VERIFICATION_SCALING_FACTOR)
            dynamic_hl = self.BASE_HALF_LIFE_DAYS * (1 + freq_factor)
            
            # 边界检查
            clamped_hl = max(self.MIN_HALF_LIFE_DAYS, min(dynamic_hl, self.MAX_HALF_LIFE_DAYS))
            
            logger.debug(f"Node {node.node_id} Dynamic Half-Life: {clamped_hl:.2f} days")
            return clamped_hl
        except Exception as e:
            logger.error(f"计算半衰期时出错 Node {node.node_id}: {e}")
            return self.BASE_HALF_LIFE_DAYS

    def apply_decay_to_node(self, node_id: str, current_time: datetime) -> Optional[Dict[str, Any]]:
        """
        核心函数2: 对指定节点应用衰减逻辑并更新权重。
        
        根据经过的时间和动态半衰期，使用指数衰减公式更新权重。
        Weight_new = Weight_old * (1/2)^(elapsed_time / half_life)
        
        Args:
            node_id (str): 节点ID。
            current_time (datetime): 当前系统时间。
            
        Returns:
            Optional[Dict]: 如果触发重检流程，返回包含重检信息的字典；否则返回None。
        """
        if node_id not in self.nodes:
            logger.warning(f"Node {node_id} 未找到。")
            return None

        node = self.nodes[node_id]
        
        if not node.is_active:
            return None

        try:
            # 计算时间差（转换为天数，包含小数以获得更高精度）
            time_elapsed = current_time - node.last_verified_time
            elapsed_days = time_elapsed.total_seconds() / (3600 * 24)

            if elapsed_days < 0:
                logger.error(f"Node {node.node_id}: 检测到时间倒流。")
                return None

            half_life = self.calculate_dynamic_half_life(node)
            
            # 指数衰减公式
            decay_factor = 0.5 ** (elapsed_days / half_life)
            new_weight = node.truth_weight * decay_factor
            
            # 数据校验
            new_weight = max(0.0, min(new_weight, 1.0))
            
            # 更新节点状态
            old_weight = node.truth_weight
            node.truth_weight = new_weight
            
            logger.info(f"Node {node_id} 衰减更新: {old_weight:.4f} -> {new_weight:.4f}")

            # 触发重检逻辑
            if new_weight < self.DECAY_THRESHOLD and old_weight >= self.DECAY_THRESHOLD:
                return self._trigger_revalidation(node, current_time)
            
            return None

        except Exception as e:
            logger.exception(f"处理节点 {node_id} 衰减时发生严重错误: {e}")
            return None

    def _trigger_revalidation(self, node: KnowledgeNode, trigger_time: datetime) -> Dict[str, Any]:
        """
        辅助函数: 触发并构造重检流程数据包。
        
        当节点权重跌破阈值时调用，生成一个标准的重检请求对象。
        
        Args:
            node (KnowledgeNode): 需要重检的节点。
            trigger_time (datetime): 触发时间。
            
        Returns:
            Dict[str, Any]: 重检任务描述。
        """
        revalidation_task = {
            "task_type": "KNOWLEDGE_REVALIDATION",
            "node_id": node.node_id,
            "current_weight": node.truth_weight,
            "trigger_reason": "WEIGHT_DECAY_BELOW_THRESHOLD",
            "message": f"节点 '{node.content[:20]}...' 权重低于 {self.DECAY_THRESHOLD}，需要人工或AGI校验。",
            "timestamp": trigger_time.isoformat()
        }
        logger.warning(f"触发重检流程: Node {node.node_id} | Weight: {node.truth_weight:.4f}")
        return revalidation_task

    def record_verification(self, node_id: str, access_time: datetime) -> bool:
        """
        记录一次新的人机交互验证，重置衰减并增加权重。
        
        Args:
            node_id (str): 节点ID。
            access_time (datetime): 访问时间。
            
        Returns:
            bool: 是否成功更新。
        """
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        node.total_verifications += 1
        node.last_verified_time = access_time
        
        # 简单的权重恢复逻辑：每次验证增加一定权重，最高为1.0
        # 这里的逻辑可以根据实际业务调整，例如直接重置为1.0
        recovery_amount = 0.1 
        node.truth_weight = min(1.0, node.truth_weight + recovery_amount)
        
        logger.info(f"Node {node_id} 被验证。Verifications: {node.total_verifications}, New Weight: {node.truth_weight:.4f}")
        return True

# 示例用法
if __name__ == "__main__":
    # 初始化系统
    kds = KnowledgeDecaySystem()
    
    # 1. 创建知识节点
    node1 = KnowledgeNode(
        node_id="kns_001",
        content="Python 3.9 于 2020 年 10 月发布。",
        truth_weight=1.0,
        last_verified_time=datetime(2023, 1, 1), # 假设上次验证是很久以前
        total_verifications=5
    )
    
    node2 = KnowledgeNode(
        node_id="kns_002",
        content="地球是圆的。",
        truth_weight=1.0,
        last_verified_time=datetime(2023, 1, 1),
        total_verifications=5000 # 高频验证的知识
    )
    
    kds.add_node(node1)
    kds.add_node(node2)
    
    # 2. 模拟时间流逝 - 假设现在是 2024 年 1 月 1 日 (过去了一年)
    simulated_now = datetime(2024, 1, 1)
    
    print("\n--- 开始计算衰减 ---")
    # 对 node1 (低频验证) 进行衰减计算
    result1 = kds.apply_decay_to_node("kns_001", simulated_now)
    if result1:
        print(f"任务生成: {result1}")
        
    # 对 node2 (高频验证) 进行衰减计算
    # 由于验证次数高，半衰期更长，权重衰减应该更慢
    result2 = kds.apply_decay_to_node("kns_002", simulated_now)
    if result2:
        print(f"任务生成: {result2}")
        
    # 3. 展示人机共生频率对权重的影响
    print(f"\nNode 'kns_001' (Low Freq) Current Weight: {kds.nodes['kns_001'].truth_weight:.4f}")
    print(f"Node 'kns_002' (High Freq) Current Weight: {kds.nodes['kns_002'].truth_weight:.4f}")
    
    # 预期结果：node2 的权重明显高于 node1，因为它的半衰期更长。