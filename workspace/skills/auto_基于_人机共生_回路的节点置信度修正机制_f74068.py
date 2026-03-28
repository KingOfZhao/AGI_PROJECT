"""
模块名称: auto_基于_人机共生_回路的节点置信度修正机制_f74068
描述: 实现基于"AI梳理清单→人类证伪"闭环的贝叶斯置信度更新算法。
      该模块维护节点的认知状态，当人类反馈与AI生成内容存在偏差时，
      动态调整节点置信度，并在置信度低于阈值时标记为"待重构"。
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态枚举"""
    ACTIVE = "active"           # 正常运行
    SUSPICIOUS = "suspicious"   # 可疑，需观察
    REFACTOR = "refactor"       # 待重构
    OBSOLETE = "obsolete"       # 废弃

@dataclass
class CognitiveNode:
    """
    认知节点数据结构
    Attributes:
        node_id: 节点唯一标识
        content: 节点生成的内容/清单
        confidence: 当前置信度 (0.0 - 1.0)
        alpha: 贝叶斯先验成功参数
        beta: 贝叶斯先验失败参数
        status: 当前节点状态
        total_attempts: 总尝试次数
        rejection_count: 拒绝/修改次数
    """
    node_id: str
    content: str
    confidence: float = 0.95
    # 贝叶斯先验参数，初始值设为1.0表示无信息先验
    alpha: float = 1.0  
    beta: float = 1.0
    status: NodeStatus = NodeStatus.ACTIVE
    total_attempts: int = 0
    rejection_count: int = 0

    def __post_init__(self):
        self._validate_parameters()

    def _validate_parameters(self):
        """验证数据边界"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0-1之间，当前值: {self.confidence}")
        if self.alpha < 0 or self.beta < 0:
            raise ValueError("贝叶斯参数alpha和beta必须为非负数")

class ConfidenceCorrectionSystem:
    """
    基于"人机共生"回路的置信度修正系统
    """
    
    # 状态转换阈值
    CONFIDENCE_THRESHOLD_SUSPICIOUS = 0.70
    CONFIDENCE_THRESHOLD_REFACTOR = 0.40
    
    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}
        logger.info("人机共生置信度修正系统已初始化")

    def register_node(self, node: CognitiveNode) -> bool:
        """
        注册一个新的认知节点
        
        Args:
            node: 待注册的节点对象
            
        Returns:
            bool: 注册是否成功
        """
        try:
            if node.node_id in self.nodes:
                logger.warning(f"节点ID {node.node_id} 已存在，执行覆盖更新")
            
            self.nodes[node.node_id] = node
            logger.info(f"节点 {node.node_id} 注册成功，初始置信度: {node.confidence:.4f}")
            return True
        except Exception as e:
            logger.error(f"节点注册失败: {str(e)}")
            return False

    def update_confidence_bayesian(
        self, 
        node_id: str, 
        is_accepted: bool, 
        modification_intensity: float = 0.0
    ) -> Optional[float]:
        """
        核心函数1: 基于贝叶斯后验概率更新节点置信度
        
        参数说明:
            node_id: 目标节点ID
            is_accepted: 人类是否直接接受清单
            modification_intensity: 如果被修改，修改的幅度 (0.0-1.0)
            
        返回:
            更新后的置信度，如果节点不存在则返回None
            
        算法逻辑:
            1. 如果人类接受：增加Alpha (成功参数)
            2. 如果人类拒绝/修改：增加Beta (失败参数)，强度取决于修改幅度
            3. 计算后验期望: E[p] = alpha / (alpha + beta)
        """
        if node_id not in self.nodes:
            logger.error(f"节点 {node_id} 未找到")
            return None
            
        node = self.nodes[node_id]
        node.total_attempts += 1
        
        try:
            if is_accepted:
                # 成功案例：增加alpha
                # 使用1.0作为标准增量，也可以根据任务重要性加权
                node.alpha += 1.0
                logger.debug(f"节点 {node_id} 获得正向反馈，Alpha更新为 {node.alpha}")
            else:
                # 失败案例：增加beta
                # 修改强度越大，惩罚越重
                penalty = 1.0 + (modification_intensity * 2.0) 
                node.beta += penalty
                node.rejection_count += 1
                logger.debug(f"节点 {node_id} 遭遇负向反馈，Beta更新为 {node.beta}")
            
            # 计算贝叶斯后验期望
            # 避免除以零的边界检查
            denominator = node.alpha + node.beta
            if denominator <= 0:
                denominator = 1e-8
                
            new_confidence = node.alpha / denominator
            node.confidence = new_confidence
            
            # 触发状态流转检查
            self._check_and_update_status(node)
            
            logger.info(f"节点 {node_id} 置信度更新为: {new_confidence:.4f}, 状态: {node.status.value}")
            return new_confidence
            
        except Exception as e:
            logger.error(f"更新置信度时发生错误: {str(e)}")
            return None

    def _check_and_update_status(self, node: CognitiveNode) -> None:
        """
        辅助函数: 检查置信度并更新节点状态
        """
        current_status = node.status
        
        if node.confidence < self.CONFIDENCE_THRESHOLD_REFACTOR:
            node.status = NodeStatus.REFACTOR
            if current_status != NodeStatus.REFACTOR:
                logger.warning(f"节点 {node.node_id} 已标记为 '待重构'！需要人工介入检查。")
                
        elif node.confidence < self.CONFIDENCE_THRESHOLD_SUSPICIOUS:
            node.status = NodeStatus.SUSPICIOUS
            if current_status != NodeStatus.SUSPICIOUS:
                logger.warning(f"节点 {node.node_id} 进入 '可疑' 状态。")
        
        else:
            # 如果置信度恢复，回到活跃状态
            node.status = NodeStatus.ACTIVE

    def get_refactor_candidates(self) -> List[CognitiveNode]:
        """
        核心函数2: 获取当前所有需要重构的节点列表
        
        Returns:
            待重构节点列表
        """
        candidates = [
            node for node in self.nodes.values() 
            if node.status == NodeStatus.REFACTOR
        ]
        logger.info(f"当前共有 {len(candidates)} 个节点等待重构")
        return candidates

    def system_health_report(self) -> Dict[str, float]:
        """
        辅助函数: 生成系统健康报告
        """
        if not self.nodes:
            return {"avg_confidence": 0.0, "refactor_rate": 0.0}
            
        total_conf = sum(n.confidence for n in self.nodes.values())
        avg_conf = total_conf / len(self.nodes)
        
        refactor_count = len(self.get_refactor_candidates())
        refactor_rate = refactor_count / len(self.nodes)
        
        return {
            "avg_confidence": round(avg_conf, 4),
            "refactor_rate": round(refactor_rate, 4),
            "total_nodes": len(self.nodes)
        }

# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 初始化系统
    system = ConfidenceCorrectionSystem()
    
    # 2. 创建节点 (模拟AI生成的清单)
    node_task_a = CognitiveNode(
        node_id="task_gen_001", 
        content="生成每日代码审查清单",
        confidence=0.90
    )
    system.register_node(node_task_a)
    
    # 3. 模拟人机交互回路
    print("\n--- 开始模拟交互 ---")
    
    # 场景 A: 人类完全接受
    system.update_confidence_bayesian("task_gen_001", is_accepted=True)
    
    # 场景 B: 人类进行了少量修改 (modification_intensity=0.3)
    system.update_confidence_bayesian("task_gen_001", is_accepted=False, modification_intensity=0.3)
    
    # 场景 C: 连续遭受大量否决 (模拟节点退化)
    for _ in range(5):
        system.update_confidence_bayesian("task_gen_001", is_accepted=False, modification_intensity=0.8)
        
    # 4. 检查结果
    final_node = system.nodes["task_gen_001"]
    print(f"\n最终状态: {final_node.status.value}")
    print(f"最终置信度: {final_node.confidence:.4f}")
    print(f"Alpha/Beta: {final_node.alpha:.2f} / {final_node.beta:.2f}")
    
    # 5. 获取重构列表
    refactor_list = system.get_refactor_candidates()
    if refactor_list:
        print(f"警告：节点 {refactor_list[0].node_id} 需要重构！")