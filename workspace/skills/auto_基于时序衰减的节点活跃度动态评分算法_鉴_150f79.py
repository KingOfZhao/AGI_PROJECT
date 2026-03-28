"""
名称: auto_基于时序衰减的节点活跃度动态评分算法_鉴_150f79
描述: 本模块实现了一个基于时序衰减的节点活跃度动态评分系统。
      通过模拟放射性衰减机制，节点的'能量值'随时间自动降低，
      仅在发生交互（调用、修正、证伪）时获得能量注入。
      旨在帮助AGI系统识别'僵尸节点'，区分'沉淀资产'与'历史包袱'。
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Node:
    """
    节点数据结构。
    
    Attributes:
        id (str): 节点的唯一标识符。
        energy (float): 当前的活跃度能量值，默认为1.0（满能量）。
        last_interaction_time (datetime): 最后一次交互的时间戳。
        total_hits (int): 总命中次数。
        is_zombie (bool): 是否被标记为僵尸节点。
    """
    id: str
    energy: float = 1.0
    last_interaction_time: datetime = field(default_factory=datetime.now)
    total_hits: int = 0
    is_zombie: bool = False


class NodeActivityScorer:
    """
    基于时序衰减的节点活跃度评分器。
    
    算法核心：
    1. 能量衰减遵循指数函数：E(t) = E0 * e^(-λt)，其中λ = ln(2) / T_half。
    2. 交互注入：当节点被触达时，能量值增加固定量（受上限约束）。
    3. 僵尸判定：当能量值低于特定阈值时，判定为僵尸节点。
    
    输入格式说明:
        - node_dict: 包含节点ID和最后交互时间的字典或对象。
        
    输出格式说明:
        - 返回更新后的节点对象及当前能量值。
        - 返回僵尸节点列表。
    """
    
    def __init__(self, 
                 half_life_days: float = 30.0, 
                 initial_energy: float = 100.0, 
                 injection_amount: float = 50.0,
                 zombie_threshold: float = 5.0,
                 max_energy: float = 100.0):
        """
        初始化评分器。
        
        Args:
            half_life_days (float): 半衰期（天）。默认30天。
            initial_energy (float): 新节点的初始能量。默认100。
            injection_amount (float): 单次交互注入的能量。默认50。
            zombie_threshold (float): 僵尸节点的能量阈值。默认5。
            max_energy (float): 节点能量的最大值。默认100。
        """
        if half_life_days <= 0:
            raise ValueError("半衰期必须大于0")
        if initial_energy < 0 or injection_amount < 0:
            raise ValueError("能量值不能为负数")
            
        self.half_life_days = half_life_days
        self.decay_lambda = math.log(2) / half_life_days  # 衰减常数 λ
        self.initial_energy = initial_energy
        self.injection_amount = injection_amount
        self.zombie_threshold = zombie_threshold
        self.max_energy = max_energy
        
        logger.info(f"评分器初始化完成: 半衰期={half_life_days}天, 衰减常数λ={self.decay_lambda:.6f}")

    def _calculate_decay_factor(self, days_elapsed: float) -> float:
        """
        辅助函数：计算衰减因子。
        
        公式: e^(-λ * t)
        
        Args:
            days_elapsed (float): 经过的时间（天）。
            
        Returns:
            float: 衰减因子（0到1之间）。
        """
        if days_elapsed < 0:
            logger.warning("经过的时间为负数，将视为0处理")
            days_elapsed = 0
        return math.exp(-self.decay_lambda * days_elapsed)

    def calculate_current_energy(self, node: Node, current_time: datetime) -> float:
        """
        核心函数1：计算节点在当前时刻的实时能量值（仅计算，不更新状态）。
        
        Args:
            node (Node): 节点对象。
            current_time (datetime): 当前时间。
            
        Returns:
            float: 计算出的当前能量值。
        """
        if node.last_interaction_time > current_time:
            logger.error(f"节点 {node.id} 的最后交互时间晚于当前时间，数据异常")
            # 容错处理：假定刚刚发生交互
            return node.energy

        time_delta = current_time - node.last_interaction_time
        days_elapsed = time_delta.total_seconds() / (3600 * 24)
        
        decay_factor = self._calculate_decay_factor(days_elapsed)
        current_energy = node.energy * decay_factor
        
        # 边界检查
        return max(0.0, min(current_energy, self.max_energy))

    def inject_energy(self, node: Node, current_time: datetime) -> Node:
        """
        核心函数2：模拟人机交互，注入能量并更新节点状态。
        
        流程:
        1. 计算衰减后的当前能量。
        2. 增加注入量。
        3. 更新最后交互时间。
        4. 重新评估僵尸状态。
        
        Args:
            node (Node): 节点对象。
            current_time (datetime): 交互发生的时间。
            
        Returns:
            Node: 更新后的节点对象。
        """
        # 1. 先结算截止目前的衰减
        decayed_energy = self.calculate_current_energy(node, current_time)
        
        # 2. 注入能量
        new_energy = decayed_energy + self.injection_amount
        
        # 3. 边界检查（上限）
        if new_energy > self.max_energy:
            logger.debug(f"节点 {node.id} 能量溢出，截断至 {self.max_energy}")
            new_energy = self.max_energy
            
        # 更新状态
        node.energy = new_energy
        node.last_interaction_time = current_time
        node.total_hits += 1
        node.is_zombie = False  # 只要被激活，就不再是僵尸
        
        logger.info(f"节点 {node.id} 被命中。能量: {decayed_energy:.2f} -> {new_energy:.2f}")
        return node

    def update_system_status(self, nodes: List[Node], current_time: datetime) -> Tuple[List[Node], List[str]]:
        """
        批量更新系统状态并识别僵尸节点。
        
        Args:
            nodes (List[Node]): 系统中所有节点的列表。
            current_time (datetime): 当前系统时间。
            
        Returns:
            Tuple[List[Node], List[str]]: 更新后的节点列表，僵尸节点ID列表。
        """
        zombie_ids = []
        updated_nodes = []
        
        for node in nodes:
            # 仅计算当前能量，不修改最后交互时间（交互才修改时间）
            real_time_energy = self.calculate_current_energy(node, current_time)
            
            # 检查僵尸阈值
            if real_time_energy < self.zombie_threshold:
                if not node.is_zombie:
                    logger.warning(f"检测到僵尸节点: {node.id} (能量: {real_time_energy:.4f})")
                node.is_zombie = True
                zombie_ids.append(node.id)
            
            # 注意：这里不修改node.energy，因为那是持久化的状态，
            # 除非我们决定定期持久化衰减后的状态。
            # 本算法设计为实时计算，只有在inject时才写状态。
            updated_nodes.append(node)
            
        return updated_nodes, zombie_ids


def run_demo():
    """
    使用示例：演示算法的工作流程。
    """
    print("--- 开始运行算法演示 ---")
    
    # 1. 初始化系统
    # 假设半衰期为10天
    scorer = NodeActivityScorer(half_life_days=10, zombie_threshold=10.0)
    
    # 2. 创建模拟节点
    now = datetime.now()
    
    # 节点A: 刚刚创建的活跃节点
    node_a = Node(id="skill_001", last_interaction_time=now - timedelta(hours=1))
    
    # 节点B: 30天前活跃的老节点（如果是10天半衰期，能量应该非常低了）
    node_b = Node(id="legacy_002", last_interaction_time=now - timedelta(days=30))
    
    # 节点C: 5天前活跃的节点
    node_c = Node(id="data_003", last_interaction_time=now - timedelta(days=5))
    
    all_nodes = [node_a, node_b, node_c]
    
    # 3. 扫描系统状态
    print(f"\n[系统扫描] 当前时间: {now}")
    for n in all_nodes:
        e = scorer.calculate_current_energy(n, now)
        print(f"节点 {n.id}: 存储能量={n.energy:.2f}, 实时衰减能量={e:.2f}, 最后交互={n.last_interaction_time.date()}")

    # 4. 识别僵尸节点
    _, zombies = scorer.update_system_status(all_nodes, now)
    print(f"\n[识别结果] 僵尸节点列表: {zombies}")
    
    # 5. 模拟交互：有人调用了节点B（老节点）
    print(f"\n[交互事件] 正在激活僵尸节点 {node_b.id} ...")
    node_b = scorer.inject_energy(node_b, now)
    
    # 6. 再次检查状态
    print(f"\n[交互后检查] 节点 {node_b.id} 能量已恢复至: {node_b.energy:.2f}, 是否僵尸: {node_b.is_zombie}")
    
    # 7. 验证半衰期计算
    # 如果半衰期是10天，5天后的能量应该是 100 * e^(-ln(2) * 5/10) = 100 * e^(-0.693*0.5) ≈ 70.7
    energy_5_days = scorer.calculate_current_energy(Node(id="test", energy=100.0, last_interaction_time=now - timedelta(days=5)), now)
    print(f"\n[算法验证] 半衰期10天下，5天后的剩余能量比例: {energy_5_days/100.0:.4f} (理论值约0.707)")

if __name__ == "__main__":
    run_demo()