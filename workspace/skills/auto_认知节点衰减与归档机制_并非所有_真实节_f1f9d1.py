"""
认知节点衰减与归档机制

该模块实现了一套用于AGI系统的认知节点（记忆/技能）生命周期管理机制。
核心功能是根据时间推移、调用频率以及环境上下文的变化，动态调整节点的权重。
对于长期未使用且环境已发生巨变的节点，系统将自动降低其权重或进行归档处理，
以保持认知图谱的轻量化和时效性。

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CognitiveNode:
    """
    认知节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识符。
        content (str): 节点内容描述（如 '软盘修复技能'）。
        initial_weight (float): 初始权重 (0.0 到 1.0)。
        current_weight (float): 当前权重。
        creation_time (datetime): 创建时间。
        last_accessed_time (datetime): 最后一次被调用的时间。
        last_context_vector (Dict[str, float]): 创建或最后更新时的环境上下文特征向量。
        is_archived (bool): 是否已归档。
        decay_rate (float): 基础衰减率（半衰期相关系数）。
    """
    id: str
    content: str
    initial_weight: float = 1.0
    current_weight: float = 1.0
    creation_time: datetime = field(default_factory=datetime.now)
    last_accessed_time: datetime = field(default_factory=datetime.now)
    last_context_vector: Dict[str, float] = field(default_factory=dict)
    is_archived: bool = False
    decay_rate: float = 0.05  # 默认衰减率，值越大衰减越快

    def __post_init__(self):
        """数据验证和初始化后处理。"""
        if not (0.0 <= self.initial_weight <= 1.0):
            raise ValueError(f"初始权重必须在0.0和1.0之间，得到: {self.initial_weight}")
        if not self.id:
            raise ValueError("节点ID不能为空")


class CognitiveDecayManager:
    """
    认知节点衰减与归档管理器。
    
    负责计算节点的衰减程度，评估环境变化，并执行归档操作。
    """

    def __init__(self, archive_threshold: float = 0.1, context_shift_sensitivity: float = 0.5):
        """
        初始化管理器。
        
        Args:
            archive_threshold (float): 触发归档的权重阈值。
            context_shift_sensitivity (float): 环境变化对衰减的加成系数 (0.0 到 1.0)。
        """
        self.archive_threshold = archive_threshold
        self.context_shift_sensitivity = context_shift_sensitivity
        logger.info(f"CognitiveDecayManager initialized with threshold={archive_threshold}")

    def calculate_environmental_drift(
        self, 
        current_context: Dict[str, float], 
        node_context: Dict[str, float]
    ) -> float:
        """
        辅助函数：计算环境上下文漂移程度。
        
        使用余弦相似度来衡量当前环境与节点记录环境之间的差异。
        差异越大，返回值越高（0到1），表示环境变化越剧烈。
        
        Args:
            current_context (Dict[str, float]): 当前环境特征向量。
            node_context (Dict[str, float]): 节点存储时的环境特征向量。
            
        Returns:
            float: 环境漂移系数 (0.0 表示无变化, 1.0 表示完全巨变)。
        """
        if not current_context or not node_context:
            return 0.0

        # 提取共同的键以对齐向量
        common_keys = set(current_context.keys()) & set(node_context.keys())
        if not common_keys:
            return 1.0  # 没有共同特征，视为完全巨变

        # 构建向量
        v_curr = [current_context[k] for k in common_keys]
        v_node = [node_context[k] for k in common_keys]

        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(v_curr, v_node))
        norm_curr = math.sqrt(sum(a**2 for a in v_curr))
        norm_node = math.sqrt(sum(b**2 for b in v_node))

        if norm_curr == 0 or norm_node == 0:
            return 0.0

        similarity = dot_product / (norm_curr * norm_node)
        
        # 将相似度 ( -1 到 1 ) 转换为漂移系数 ( 0 到 1 )
        # 相似度越高，漂移越低
        drift = (1.0 - similarity) / 2.0
        return max(0.0, min(1.0, drift))

    def apply_temporal_decay(
        self, 
        node: CognitiveNode, 
        current_time: datetime
    ) -> float:
        """
        核心函数1：应用基于时间的指数衰减算法。
        
        公式: W(t) = W_0 * e^(-lambda * t)
        其中 lambda 是衰减率，t 是时间间隔。
        
        Args:
            node (CognitiveNode): 待处理的认知节点。
            current_time (datetime): 当前系统时间。
            
        Returns:
            float: 衰减后的新权重。
        """
        if node.is_archived:
            return node.current_weight

        time_delta = current_time - node.last_accessed_time
        hours_passed = time_delta.total_seconds() / 3600.0

        if hours_passed < 0:
            logger.warning(f"Negative time delta detected for node {node.id}")
            return node.current_weight

        # 指数衰减计算
        decay_factor = math.exp(-node.decay_rate * hours_passed)
        new_weight = node.initial_weight * decay_factor
        
        logger.debug(f"Node {node.id} decayed: {node.current_weight:.4f} -> {new_weight:.4f}")
        return new_weight

    def process_node_lifecycle(
        self, 
        node: CognitiveNode, 
        current_context: Dict[str, float],
        current_time: Optional[datetime] = None
    ) -> Tuple[float, bool]:
        """
        核心函数2：综合处理节点的生命周期（时间衰减 + 环境适应 + 归档判断）。
        
        1. 计算时间衰减。
        2. 计算环境漂移，如果环境巨变，额外扣除权重。
        3. 更新节点权重。
        4. 判断是否需要归档。
        
        Args:
            node (CognitiveNode): 待处理的节点。
            current_context (Dict[str, float]): 当前环境上下文。
            current_time (Optional[datetime]): 指定当前时间，默认为系统时间。
            
        Returns:
            Tuple[float, bool]: (更新后的权重, 是否触发了归档动作)
        """
        if current_time is None:
            current_time = datetime.now()

        if node.is_archived:
            return (node.current_weight, False)

        # 1. 时间衰减
        temporal_weight = self.apply_temporal_decay(node, current_time)

        # 2. 环境漂移惩罚
        env_drift = self.calculate_environmental_drift(current_context, node.last_context_vector)
        
        # 环境惩罚：如果漂移严重，权重进一步降低
        # 惩罚公式: W_final = W_temporal * (1 - (drift * sensitivity))
        environmental_penalty = 1.0 - (env_drift * self.context_shift_sensitivity)
        final_weight = temporal_weight * max(0.0, environmental_penalty)

        # 边界检查
        final_weight = max(0.0, min(1.0, final_weight))
        node.current_weight = final_weight

        # 3. 归档判断
        should_archive = False
        if final_weight < self.archive_threshold:
            self._archive_node(node)
            should_archive = True
            logger.info(f"Node {node.id} ('{node.content}') has been archived due to low weight: {final_weight:.4f}")
        else:
            # 更新节点的环境快照（可选：让节点"适应"新环境，减少未来惩罚）
            # node.last_context_vector = current_context 
            pass

        return (final_weight, should_archive)

    def _archive_node(self, node: CognitiveNode) -> None:
        """
        内部辅助函数：执行归档操作。
        
        将节点标记为非活跃状态，模拟移入冷存储。
        """
        node.is_archived = True
        # 在实际系统中，这里可能涉及将节点移动到数据库的归档表
        logger.info(f"Node {node.id} moved to archive storage.")


# ================= 使用示例 =================

if __name__ == "__main__":
    # 1. 初始化环境
    manager = CognitiveDecayManager(archive_threshold=0.15, context_shift_sensitivity=0.8)
    
    # 模拟过去的时间点（比如3年前）
    three_years_ago = datetime.now() - timedelta(days=365*3)
    
    # 2. 创建一个旧节点（例如：软盘修复技能）
    # 假设当时的环境上下文强调 "物理存储介质" 和 "Windows 98"
    old_context = {"physical_media": 0.9, "legacy_os": 0.8, "internet": 0.2}
    
    floppy_skill = CognitiveNode(
        id="skill_001",
        content="Floppy Disk Data Recovery",
        creation_time=three_years_ago,
        last_accessed_time=three_years_ago, # 自那以后没再用过
        last_context_vector=old_context,
        decay_rate=0.001  # 设定一个较低的衰减率，但时间很久
    )

    # 3. 模拟当前环境
    # 现在的环境强调 "云存储", "SSD", "Linux"
    current_modern_context = {"cloud_storage": 0.9, "ssd_tech": 0.8, "internet": 0.9, "physical_media": 0.1}
    
    print(f"--- Processing Node: {floppy_skill.content} ---")
    print(f"Initial Weight: {floppy_skill.current_weight}")
    
    # 4. 执行生命周期处理
    new_weight, is_archived = manager.process_node_lifecycle(
        node=floppy_skill,
        current_context=current_modern_context
    )
    
    print(f"New Weight: {new_weight:.4f}")
    print(f"Is Archived: {is_archived}")
    print(f"Node Status: {'Archived' if floppy_skill.is_archived else 'Active'}")

    # 5. 测试一个仍然活跃的节点
    print("\n--- Testing Active Node ---")
    coding_skill = CognitiveNode(
        id="skill_002",
        content="Python Coding",
        last_accessed_time=datetime.now() - timedelta(hours=5), # 5小时前刚用过
        last_context_vector={"cloud_storage": 0.8, "linux": 0.9},
        decay_rate=0.01
    )
    
    new_weight_2, is_archived_2 = manager.process_node_lifecycle(
        node=coding_skill,
        current_context=current_modern_context
    )
    print(f"Python Skill New Weight: {new_weight_2:.4f} (Archived: {is_archived_2})")