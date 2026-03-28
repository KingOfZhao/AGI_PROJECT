"""
模块名称: cognitive_entropy_dynamics
描述: 实现基于热力学熵减原则的认知节点动态遗忘与固化机制。
      该系统模拟人类记忆的巩固与修剪过程，通过动态调整节点连接权重来防止'认知僵化'。
"""

import logging
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CognitiveNode:
    """
    认知节点数据结构
    
    属性:
        node_id: 节点唯一标识符
        creation_time: 创建时间
        last_interaction: 最后交互时间
        interaction_count: 人机交互频率
        falsification_count: 连续证伪失败次数
        weight: 连接权重 (0.0-1.0)
        status: 节点状态 ('active', 'dormant', 'pending_prune')
        cross_domain_value: 跨域价值评分 (0.0-1.0)
    """
    node_id: str
    creation_time: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0
    falsification_count: int = 0
    weight: float = 1.0
    status: str = 'active'
    cross_domain_value: float = 0.5
    
    def __post_init__(self):
        """初始化后验证数据"""
        if not 0 <= self.weight <= 1:
            raise ValueError(f"权重必须在0.0-1.0之间，当前值: {self.weight}")
        if self.interaction_count < 0:
            raise ValueError("交互计数不能为负数")
        if self.falsification_count < 0:
            raise ValueError("证伪计数不能为负数")


class EntropyDynamicsSystem:
    """
    基于热力学熵减原则的认知动态系统
    
    该系统实现:
    1. 动态权重调整算法
    2. 节点状态转换逻辑
    3. 记忆巩固与遗忘机制
    4. 跨域价值评估
    
    示例:
        >>> system = EntropyDynamicsSystem(total_nodes=2257)
        >>> system.update_node_interactions("node_123", interaction_count=5)
        >>> system.evaluate_node("node_123")
        >>> system.apply_entropy_dynamics()
    """
    
    def __init__(self, total_nodes: int = 2257):
        """
        初始化熵动态系统
        
        参数:
            total_nodes: 系统中的总节点数
        """
        self.total_nodes = total_nodes
        self.nodes: Dict[str, CognitiveNode] = {}
        self.time_decay_factor = 0.95  # 时间衰减因子
        self.interaction_weight = 0.7  # 交互频率的权重
        self.falsification_weight = 0.8  # 证伪失败的影响权重
        self.prune_threshold = 0.3  # 修剪阈值
        self.consolidation_threshold = 0.8  # 巩固阈值
        self.max_falsification_attempts = 5  # 最大证伪尝试次数
        
        # 初始化默认节点
        self._initialize_nodes()
    
    def _initialize_nodes(self) -> None:
        """初始化系统中的默认节点"""
        for i in range(min(100, self.total_nodes)):  # 示例中只初始化100个节点
            node_id = f"node_{i}"
            self.nodes[node_id] = CognitiveNode(
                node_id=node_id,
                cross_domain_value=np.random.uniform(0.3, 0.7)
            )
    
    def update_node_interactions(
        self, 
        node_id: str, 
        interaction_count: int = 1,
        reset_falsification: bool = False
    ) -> bool:
        """
        更新节点的交互信息
        
        参数:
            node_id: 节点ID
            interaction_count: 新增的交互次数
            reset_falsification: 是否重置证伪计数
            
        返回:
            bool: 更新是否成功
        """
        try:
            if node_id not in self.nodes:
                logger.warning(f"节点 {node_id} 不存在，创建新节点")
                self.nodes[node_id] = CognitiveNode(node_id=node_id)
            
            node = self.nodes[node_id]
            node.interaction_count += interaction_count
            node.last_interaction = datetime.now()
            
            if reset_falsification:
                node.falsification_count = 0
                
            logger.info(f"更新节点 {node_id} 交互信息: +{interaction_count} 次交互")
            return True
            
        except Exception as e:
            logger.error(f"更新节点交互信息失败: {str(e)}")
            return False
    
    def record_falsification_attempt(
        self, 
        node_id: str, 
        success: bool
    ) -> Tuple[bool, str]:
        """
        记录节点的证伪实验结果
        
        参数:
            node_id: 节点ID
            success: 证伪是否成功
            
        返回:
            Tuple[bool, str]: (操作是否成功, 状态消息)
        """
        if node_id not in self.nodes:
            return False, f"节点 {node_id} 不存在"
        
        try:
            node = self.nodes[node_id]
            
            if success:
                node.falsification_count = 0
                logger.info(f"节点 {node_id} 证伪成功，重置计数器")
                return True, "证伪成功，计数器已重置"
            else:
                node.falsification_count += 1
                logger.warning(
                    f"节点 {node_id} 证伪失败，计数器: {node.falsification_count}/{self.max_falsification_attempts}"
                )
                
                if node.falsification_count >= self.max_falsification_attempts:
                    node.status = 'pending_prune'
                    logger.warning(f"节点 {node_id} 已标记为待修剪状态")
                    return True, "节点已标记为待修剪"
                
                return True, f"证伪失败，计数器增加"
                
        except Exception as e:
            logger.error(f"记录证伪尝试失败: {str(e)}")
            return False, f"错误: {str(e)}"
    
    def _calculate_entropy_index(self, node: CognitiveNode) -> float:
        """
        计算节点的熵指数 (辅助函数)
        
        熵指数综合考虑:
        1. 时间衰减 (孤立熵增)
        2. 交互频率 (使用熵减)
        3. 证伪失败 (结构性熵增)
        4. 跨域价值 (潜在熵减)
        
        参数:
            node: 认知节点对象
            
        返回:
            float: 熵指数 (0.0-1.0)
        """
        # 计算时间衰减因子
        time_since_interaction = (datetime.now() - node.last_interaction).total_seconds() / 3600  # 小时
        time_decay = math.exp(-time_since_interaction / 24)  # 24小时半衰期
        
        # 计算交互频率因子
        interaction_factor = 1 - (1 / (1 + node.interaction_count))
        
        # 计算证伪失败因子
        falsification_factor = node.falsification_count / self.max_falsification_attempts
        
        # 综合熵指数计算
        entropy_index = (
            (1 - time_decay) * 0.4 +  # 时间衰减权重
            (1 - interaction_factor) * 0.3 +  # 交互频率权重
            falsification_factor * 0.2 +  # 证伪失败权重
            (1 - node.cross_domain_value) * 0.1  # 跨域价值权重
        )
        
        return min(max(entropy_index, 0.0), 1.0)
    
    def evaluate_node(self, node_id: str) -> Dict[str, Union[float, str]]:
        """
        评估节点状态并返回详细指标
        
        参数:
            node_id: 节点ID
            
        返回:
            Dict: 包含各项评估指标的字典
        """
        if node_id not in self.nodes:
            logger.error(f"评估失败: 节点 {node_id} 不存在")
            return {"error": "节点不存在"}
        
        node = self.nodes[node_id]
        entropy_index = self._calculate_entropy_index(node)
        
        # 计算建议权重调整
        weight_adjustment = (
            -0.1 if entropy_index > 0.7 else
            0.05 if entropy_index < 0.3 else
            0.0
        )
        
        # 确定建议状态
        suggested_status = node.status
        if entropy_index > 0.8 and node.status != 'pending_prune':
            suggested_status = 'pending_prune'
        elif entropy_index < 0.2 and node.status == 'pending_prune':
            suggested_status = 'dormant'  # 保留但降低活跃度
        elif entropy_index < 0.1 and node.status == 'dormant':
            suggested_status = 'active'
        
        evaluation_result = {
            "node_id": node_id,
            "current_weight": node.weight,
            "entropy_index": entropy_index,
            "weight_adjustment": weight_adjustment,
            "current_status": node.status,
            "suggested_status": suggested_status,
            "interaction_count": node.interaction_count,
            "falsification_count": node.falsification_count,
            "cross_domain_value": node.cross_domain_value
        }
        
        logger.info(f"节点 {node_id} 评估完成: 熵指数={entropy_index:.2f}, 建议状态={suggested_status}")
        return evaluation_result
    
    def apply_entropy_dynamics(self) -> Dict[str, int]:
        """
        应用熵动态机制到所有节点
        
        返回:
            Dict: 包含各状态节点数量的统计信息
        """
        status_counts = {
            'active': 0,
            'dormant': 0,
            'pending_prune': 0
        }
        
        for node_id, node in self.nodes.items():
            try:
                evaluation = self.evaluate_node(node_id)
                
                # 应用权重调整
                node.weight = max(0.1, min(1.0, node.weight + evaluation['weight_adjustment']))
                
                # 更新节点状态
                if evaluation['suggested_status'] != node.status:
                    old_status = node.status
                    node.status = evaluation['suggested_status']
                    logger.info(
                        f"节点 {node_id} 状态变更: {old_status} -> {node.status}"
                    )
                
                status_counts[node.status] += 1
                
            except Exception as e:
                logger.error(f"应用熵动态失败: 节点 {node_id} - {str(e)}")
                status_counts['error'] = status_counts.get('error', 0) + 1
        
        logger.info(f"熵动态应用完成: {status_counts}")
        return status_counts
    
    def get_nodes_by_status(self, status: str) -> List[str]:
        """
        获取特定状态的所有节点ID
        
        参数:
            status: 节点状态 ('active', 'dormant', 'pending_prune')
            
        返回:
            List: 节点ID列表
        """
        return [
            node_id for node_id, node in self.nodes.items()
            if node.status == status
        ]
    
    def consolidate_memory(self) -> int:
        """
        执行记忆巩固过程，增强高价值节点
        
        返回:
            int: 巩固的节点数量
        """
        consolidated_count = 0
        
        for node_id, node in self.nodes.items():
            if (node.status == 'active' and 
                node.interaction_count > 10 and 
                node.falsification_count == 0):
                
                # 增强权重
                node.weight = min(1.0, node.weight * 1.1)
                node.cross_domain_value = min(1.0, node.cross_domain_value * 1.05)
                consolidated_count += 1
                
        logger.info(f"记忆巩固完成: 增强了 {consolidated_count} 个高价值节点")
        return consolidated_count


# 使用示例
if __name__ == "__main__":
    # 初始化系统
    cognitive_system = EntropyDynamicsSystem(total_nodes=2257)
    
    # 模拟节点交互
    cognitive_system.update_node_interactions("node_0", interaction_count=15)
    cognitive_system.update_node_interactions("node_1", interaction_count=3)
    
    # 模拟证伪实验
    for _ in range(5):
        cognitive_system.record_falsification_attempt("node_2", success=False)
    
    # 评估单个节点
    evaluation = cognitive_system.evaluate_node("node_0")
    print("\n节点评估结果:")
    for key, value in evaluation.items():
        print(f"{key}: {value}")
    
    # 应用熵动态
    status_report = cognitive_system.apply_entropy_dynamics()
    print("\n系统状态报告:")
    print(status_report)
    
    # 执行记忆巩固
    consolidated = cognitive_system.consolidate_memory()
    print(f"\n巩固了 {consolidated} 个高价值节点")
    
    # 获取待修剪节点
    pending_prune_nodes = cognitive_system.get_nodes_by_status('pending_prune')
    print(f"\n待修剪节点: {pending_prune_nodes[:5]}... (共{len(pending_prune_nodes)}个)")