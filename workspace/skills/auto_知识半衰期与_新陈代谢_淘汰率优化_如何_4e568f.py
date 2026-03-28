"""
名称: auto_知识半衰期与_新陈代谢_淘汰率优化_如何_4e568f
描述: 知识半衰期与'新陈代谢'淘汰率优化模块。
     本模块实现了一个基于领域稳定性和交互验证的知识管理系统。
     它根据不同领域的特性（如医学的稳定性 vs 编程的快速迭代）设定动态半衰期，
     并通过衰减函数降低未被验证节点的置信度，最终触发归档或删除流程。
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DomainType(Enum):
    """定义领域的稳定性枚举，用于决定默认半衰期基准。"""
    HIGH_STABILITY = "high_stability"      # 如：基础数学、解剖学 - 半衰期长
    MEDIUM_STABILITY = "medium_stability"  # 如：医学临床指南、宏观经济 - 半衰期中等
    LOW_STABILITY = "low_stability"        # 如：前端框架、热门AI模型 - 半衰期短
    VOLATILE = "volatile"                  # 如：每日新闻、实时股价 - 半衰期极短

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        node_id (str): 节点唯一标识符
        content (str): 知识内容
        domain (DomainType): 所属领域类型
        confidence (float): 当前置信度 (0.0 - 1.0)
        created_at (datetime): 创建时间
        last_verified (datetime): 上次经过'人机共生'验证的时间
        half_life_days (float): 动态计算出的半衰期天数
        status (str): 当前状态 ('active', 'archived', 'deleted')
    """
    node_id: str
    content: str
    domain: DomainType
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_verified: datetime = field(default_factory=datetime.now)
    half_life_days: float = 0.0  # 将由外部计算逻辑填充
    status: str = 'active'

    def __post_init__(self):
        """数据验证。"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0到1.0之间，当前值: {self.confidence}")
        if not isinstance(self.domain, DomainType):
            raise TypeError("domain 必须是 DomainType 枚举实例")

def determine_half_life(domain: DomainType, base_factor: float = 1.0) -> float:
    """
    辅助函数：根据领域稳定性确定知识节点的半衰期。
    
    Args:
        domain (DomainType): 知识所属的领域类型。
        base_factor (float): 外部调节因子，例如系统负载或特定用户偏好。

    Returns:
        float: 半衰期天数。
        
    Raises:
        ValueError: 如果领域类型未知。
    """
    logger.debug(f"正在为领域 {domain.value} 计算半衰期...")
    
    # 核心映射逻辑：领域稳定性 -> 基础天数
    # 这里假设的数值仅作演示，实际应用中应从配置中心读取
    domain_mapping = {
        DomainType.HIGH_STABILITY: 365.0,   # 1年
        DomainType.MEDIUM_STABILITY: 90.0,  # 3个月
        DomainType.LOW_STABILITY: 30.0,     # 1个月
        DomainType.VOLATILE: 7.0            # 1周
    }
    
    if domain not in domain_mapping:
        logger.error(f"未知的领域类型: {domain}")
        raise ValueError("未知的领域类型")
        
    base_days = domain_mapping[domain]
    # 结合调节因子
    final_days = base_days * base_factor
    
    logger.info(f"领域 {domain.value} 设定半衰期为: {final_days} 天")
    return final_days

def apply_decay(
    node: KnowledgeNode, 
    current_time: datetime, 
    decay_rate_modifier: float = 1.0
) -> KnowledgeNode:
    """
    核心函数 1: 应用衰减逻辑。
    
    根据指数衰减公式更新节点的置信度。
    公式: New_Confidence = Old_Confidence * (0.5 ^ (elapsed_time / half_life))
    
    Args:
        node (KnowledgeNode): 待处理的知识节点。
        current_time (datetime): 当前系统时间。
        decay_rate_modifier (float): 衰减速度调节器，>1 加速衰减，<1 减速。

    Returns:
        KnowledgeNode: 更新后的节点对象。
    """
    if node.status != 'active':
        return node

    # 计算距离上次验证的时间差（秒 -> 天）
    elapsed_delta = current_time - node.last_verified
    elapsed_days = elapsed_delta.total_seconds() / 86400.0

    if elapsed_days < 0:
        logger.warning(f"节点 {node.node_id} 的时间逻辑异常（上次验证时间在未来）")
        return node

    if node.half_life_days <= 0:
        logger.error(f"节点 {node.node_id} 半衰期配置错误")
        return node

    # 计算衰减
    effective_half_life = node.half_life_days / decay_rate_modifier
    decay_factor = 0.5 ** (elapsed_days / effective_half_life)
    
    original_confidence = node.confidence
    node.confidence = node.confidence * decay_factor
    
    logger.info(
        f"节点 {node.node_id} 衰减完成. "
        f"历时: {elapsed_days:.2f}天, "
        f"置信度: {original_confidence:.4f} -> {node.confidence:.4f}"
    )
    
    return node

def check_metabolism(
    nodes: List[KnowledgeNode], 
    archive_threshold: float = 0.2, 
    delete_threshold: float = 0.05
) -> Dict[str, List[str]]:
    """
    核心函数 2: 检查新陈代谢状态并触发状态变更。
    
    遍历节点列表，检查置信度是否低于阈值，执行归档或删除标记。
    
    Args:
        nodes (List[KnowledgeNode]): 知识节点列表。
        archive_threshold (float): 归档阈值，低于此值进入归档流程。
        delete_threshold (float): 删除阈值，低于此值标记为删除。

    Returns:
        Dict[str, List[str]]: 包含变更报告的字典 {'archived': [...], 'deleted': [...]}.
    """
    report = {"archived": [], "deleted": []}
    
    if not nodes:
        logger.warning("输入节点列表为空")
        return report

    if not (0 <= delete_threshold <= archive_threshold <= 1):
        raise ValueError("阈值关系必须满足: 0 <= delete <= archive <= 1")

    for node in nodes:
        if node.status == 'deleted':
            continue

        # 触发删除流程
        if node.confidence <= delete_threshold:
            node.status = 'deleted'
            msg = f"节点 {node.node_id} 置信度 ({node.confidence:.4f}) 低于删除阈值 {delete_threshold}。执行逻辑删除。"
            logger.warning(msg)
            report['deleted'].append(node.node_id)
            
        # 触发归档流程 (仅当状态为 active 时)
        elif node.confidence <= archive_threshold and node.status == 'active':
            node.status = 'archived'
            msg = f"节点 {node.node_id} 置信度 ({node.confidence:.4f}) 低于归档阈值 {archive_threshold}。移入冷存储。"
            logger.info(msg)
            report['archived'].append(node.node_id)
            
    return report

class KnowledgeLifecycleManager:
    """
    管理知识生命周期的上层类，整合配置和流程。
    """
    
    def __init__(self, global_decay_modifier: float = 1.0):
        self.global_decay_modifier = global_decay_modifier
        self.nodes: Dict[str, KnowledgeNode] = {}
        
    def add_knowledge(self, node_id: str, content: str, domain: DomainType) -> None:
        """添加新知识并初始化半衰期。"""
        try:
            hl = determine_half_life(domain)
            new_node = KnowledgeNode(
                node_id=node_id,
                content=content,
                domain=domain,
                half_life_days=hl
            )
            self.nodes[node_id] = new_node
            logger.info(f"成功添加节点: {node_id}")
        except Exception as e:
            logger.error(f"添加节点 {node_id} 失败: {e}")

    def run_maintenance_cycle(self, current_time: datetime) -> Dict[str, List[str]]:
        """执行一次完整的维护周期：衰减 -> 检查 -> 清理。"""
        active_nodes = [n for n in self.nodes.values() if n.status == 'active' or n.status == 'archived']
        
        # 1. 应用衰减
        for node in active_nodes:
            apply_decay(node, current_time, self.global_decay_modifier)
            
        # 2. 执行代谢检查
        report = check_metabolism(list(self.nodes.values()))
        
        return report

    def human_machine_verification(self, node_id: str, verified_time: datetime, boost: float = 0.3) -> bool:
        """
        模拟'人机共生'验证交互。
        如果用户验证了该知识，重置其最后验证时间，并提升其置信度。
        
        Args:
            node_id (str): 节点ID
            verified_time (datetime): 验证时间
            boost (float): 置信度提升量，最高不超过1.0
        """
        if node_id not in self.nodes:
            logger.error(f"验证失败: 找不到节点 {node_id}")
            return False
            
        node = self.nodes[node_id]
        
        # 状态恢复：如果节点是归档状态，验证可以将其重新激活
        if node.status == 'archived':
            node.status = 'active'
            logger.info(f"节点 {node_id} 从归档中唤醒。")
            
        node.last_verified = verified_time
        node.confidence = min(1.0, node.confidence + boost)
        
        logger.info(f"节点 {node_id} 已通过验证。置信度提升至 {node.confidence:.2f}")
        return True

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化管理器
    manager = KnowledgeLifecycleManager(global_decay_modifier=1.0)
    
    # 2. 添加不同领域的知识
    # 医学知识（高稳定性）
    manager.add_knowledge("med_01", "阿司匹林用于抗血小板聚集", DomainType.HIGH_STABILITY)
    # 编程知识（低稳定性）
    manager.add_knowledge("code_01", "Python 3.9 使用 match case 语法", DomainType.LOW_STABILITY)
    
    # 3. 模拟时间流逝 (假设过了 40 天)
    future_time = datetime.now() + timedelta(days=40)
    
    print("\n--- 开始维护周期 (40天后) ---")
    report = manager.run_maintenance_cycle(future_time)
    
    # 4. 查看结果
    # 医学节点半衰期365天，40天后几乎无变化
    # 编程节点半衰期30天，40天后应显著衰减 (超过一个半衰期)
    
    med_node = manager.nodes["med_01"]
    code_node = manager.nodes["code_01"]
    
    print(f"医学节点置信度: {med_node.confidence:.4f} (状态: {med_node.status})")
    print(f"编程节点置信度: {code_node.confidence:.4f} (状态: {code_node.status})")
    
    # 5. 执行一次人机验证 (拯救即将过期的编程知识)
    print("\n--- 执行人机验证 ---")
    manager.human_machine_verification("code_01", future_time)
    
    # 6. 再次检查
    print(f"编程节点验证后置信度: {code_node.confidence:.4f}")