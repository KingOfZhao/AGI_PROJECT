"""
模块名称: auto_开发_动态认知噪音门_系统_借鉴音乐中和_6b17eb
描述: 开发‘动态认知噪音门’系统。
借鉴音乐中和弦紧张度的释放机制，为算法知识库设计‘半衰期’参数。
当一个解决方案（节点）在特定时间窗口（如一个‘乐句周期’）未被复用，
系统自动将其从‘主调性知识库’（高权重）移至‘属调/离调知识库’（归档区）。
若再次被唤醒，需经过‘转调验证’（重新测试），通过后方能重新进入主库。
这防止了过时信息污染当前决策，实现了知识图谱的‘节奏型’自我清洗。
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DynamicCognitiveNoiseGate")


class TonalState(Enum):
    """定义知识节点的调性状态（认知层级）。"""
    TONIC = 1       # 主调：高权重，当前活跃的核心知识
    DOMINANT = 2    # 属调/离调：归档区，潜在有用但当前非核心
    DISSONANT = 3   # 不协和：待废弃或需重构


@dataclass
class CognitiveNode:
    """认知知识节点，包含内容、状态和时间戳信息。"""
    node_id: str
    content: Any
    state: TonalState = TonalState.TONIC
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    resolution_score: float = 1.0  # 解决方案的初始得分

    def update_access(self):
        """更新节点访问时间和计数。"""
        self.last_accessed = time.time()
        self.access_count += 1


class DynamicCognitiveNoiseGateSystem:
    """
    动态认知噪音门系统。
    
    该系统管理知识节点，根据其活跃度（半衰期）自动在主库和归档区之间移动节点。
    借鉴音乐理论，将知识分为'主调'（活跃）、'属调'（归档）等状态，
    实现'节奏型'自我清洗，防止过时信息污染决策。
    
    输入格式:
        - 添加节点: (node_id: str, content: Any)
        - 验证函数: Callable[[Any], bool] 返回True表示验证通过
    
    输出格式:
        - 查询结果: Optional[CognitiveNode]
        - 系统状态: Dict[str, Any]
    """

    def __init__(
        self, 
        phrase_cycle: float = 3600.0, 
        half_life_threshold: float = 0.5,
        verification_func: Optional[Callable[[Any], bool]] = None
    ):
        """
        初始化系统。
        
        Args:
            phrase_cycle (float): 乐句周期（秒），定义时间窗口。默认3600秒(1小时)。
            half_life_threshold (float): 半衰期阈值系数。若 (当前时间 - 上次访问) > (phrase_cycle * half_life_threshold)
                                          则触发降级。
            verification_func (Callable): 转调验证函数，用于唤醒节点时验证其有效性。
        """
        if phrase_cycle <= 0:
            raise ValueError("phrase_cycle 必须为正数")
        if not 0 < half_life_threshold <= 1:
            raise ValueError("half_life_threshold 必须在 (0, 1] 范围内")

        self.phrase_cycle = phrase_cycle
        self.half_life_threshold = half_life_threshold
        self._verification_func = verification_func if verification_func else self._default_verification
        self._knowledge_base: Dict[str, CognitiveNode] = {}
        logger.info(f"系统初始化完成. 乐句周期: {phrase_cycle}s, 半衰期系数: {half_life_threshold}")

    def _default_verification(self, content: Any) -> bool:
        """默认验证逻辑：简单检查内容非空。"""
        return content is not None

    def add_node(self, node_id: str, content: Any) -> bool:
        """
        添加一个新的认知节点到主调性知识库。
        
        Args:
            node_id (str): 节点唯一标识符。
            content (Any): 节点包含的知识/解决方案内容。
        
        Returns:
            bool: 是否成功添加。
        """
        if not node_id:
            logger.error("添加失败: node_id 不能为空")
            return False
        
        if node_id in self._knowledge_base:
            logger.warning(f"节点 {node_id} 已存在，执行更新操作。")
            self._knowledge_base[node_id].content = content
            self._knowledge_base[node_id].update_access()
            self._knowledge_base[node_id].state = TonalState.TONIC # 重置为主调
            return True

        new_node = CognitiveNode(node_id=node_id, content=content)
        self._knowledge_base[node_id] = new_node
        logger.info(f"新节点 [{node_id}] 已加入主调性知识库 (TONIC)。")
        return True

    def _calculate_decay_factor(self, node: CognitiveNode) -> float:
        """
        辅助函数：计算节点的衰减因子。
        基于时间差与乐句周期的比例。
        """
        current_time = time.time()
        time_diff = current_time - node.last_accessed
        # 简单的线性衰减模型用于演示，实际可使用指数衰减
        return max(0.0, 1.0 - (time_diff / self.phrase_cycle))

    def enforce_rhythm_cycle(self) -> Tuple[int, int]:
        """
        核心函数 1: 执行'节奏型'自我清洗。
        
        遍历所有节点，检查其是否超过'乐句周期'未活跃。
        若超过，将其从'主调'(TONIC)移至'属调'(DOMINANT)。
        
        Returns:
            Tuple[int, int]: (降级节点数, 保持活跃节点数)
        """
        current_time = time.time()
        demoted_count = 0
        active_count = 0
        threshold_time = self.phrase_cycle * self.half_life_threshold

        logger.info("开始执行认知节奏清洗 (Rhythm Cycle Enforcement)...")

        for node_id, node in list(self._knowledge_base.items()):
            time_since_access = current_time - node.last_accessed

            # 检查是否需要降级
            if node.state == TonalState.TONIC and time_since_access > threshold_time:
                node.state = TonalState.DOMINANT
                logger.debug(f"节点 [{node_id}] 已超时 ({time_since_access:.2f}s > {threshold_time:.2f}s)，移至属调区域 (DOMINANT)。")
                demoted_count += 1
            elif node.state == TonalState.TONIC:
                active_count += 1
        
        logger.info(f"清洗完成。降级节点: {demoted_count}, 活跃主调节点: {active_count}")
        return demoted_count, active_count

    def retrieve_knowledge(self, node_id: str) -> Optional[CognitiveNode]:
        """
        核心函数 2: 检索知识并进行'转调验证'。
        
        尝试获取知识节点。如果节点在'属调'(DOMINANT)，必须先通过验证（测试）
        才能重新进入'主调'(TONIC)并返回。如果验证失败，则标记为不协和或删除。
        
        Args:
            node_id (str): 节点ID。
            
        Returns:
            Optional[CognitiveNode]: 验证通过返回节点对象，否则返回None。
        """
        if node_id not in self._knowledge_base:
            logger.warning(f"知识检索失败: 节点 [{node_id}] 不存在。")
            return None

        node = self._knowledge_base[node_id]
        
        # 主调知识直接返回
        if node.state == TonalState.TONIC:
            node.update_access()
            logger.info(f"检索成功: 节点 [{node_id}] 来自主调库 (TONIC)。")
            return node

        # 属调知识需要转调验证
        if node.state == TonalState.DOMINANT:
            logger.info(f"节点 [{node_id}] 位于属调库 (DOMINANT)，正在进行转调验证...")
            try:
                # 执行验证逻辑
                is_valid = self._verification_func(node.content)
                
                if is_valid:
                    node.state = TonalState.TONIC
                    node.update_access()
                    logger.info(f"验证通过！节点 [{node_id}] 已转回调主库 (TONIC)。")
                    return node
                else:
                    node.state = TonalState.DISSONANT
                    logger.error(f"验证失败。节点 [{node_id}] 被标记为不协和 (DISSONANT)，拒绝访问。")
                    return None
            except Exception as e:
                logger.error(f"验证过程中发生异常: {e}")
                return None
        
        # 不协和知识直接拒绝
        if node.state == TonalState.DISSONANT:
            logger.warning(f"拒绝访问: 节点 [{node_id}] 处于不协和状态 (DISSONANT)。")
            return None

        return None

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息。"""
        stats = {
            "total_nodes": len(self._knowledge_base),
            "tonic_count": 0,
            "dominant_count": 0,
            "dissonant_count": 0
        }
        for node in self._knowledge_base.values():
            if node.state == TonalState.TONIC:
                stats["tonic_count"] += 1
            elif node.state == TonalState.DOMINANT:
                stats["dominant_count"] += 1
            elif node.state == TonalState.DISSONANT:
                stats["dissonant_count"] += 1
        return stats

# ==============================
# 使用示例 / Usage Example
# ==============================
if __name__ == "__main__":
    # 设置一个很短的周期用于演示 (5秒)
    # Set a short cycle for demo purposes (5 seconds)
    demo_cycle = 5.0
    
    # 自定义验证函数：如果内容包含 "valid" 则通过
    # Custom verification: passes if content contains "valid"
    def custom_verify(content: Any) -> bool:
        return "valid" in str(content)

    # 初始化系统
    system = DynamicCognitiveNoiseGateSystem(
        phrase_cycle=demo_cycle,
        half_life_threshold=0.8, # 超过 4秒 未使用即降级
        verification_func=custom_verify
    )

    print("\n--- 步骤 1: 添加知识 ---")
    system.add_node("sol_001", "solution_a_valid") # 这是一个有效的方案
    system.add_node("sol_002", "solution_b_outdated") # 这是一个过时方案
    print(f"当前状态: {system.get_system_stats()}")

    print("\n--- 步骤 2: 立即检索 (应都在主库) ---")
    node = system.retrieve_knowledge("sol_001")
    print(f"获取 'sol_001': {'成功' if node else '失败'}")
    
    print("\n--- 步骤 3: 模拟时间流逝 (等待半衰期) ---")
    print(f"等待 {demo_cycle * 0.9} 秒...")
    time.sleep(demo_cycle * 0.9) # 等待足够长时间使其降级

    print("\n--- 步骤 4: 执行节奏清洗 ---")
    system.enforce_rhythm_cycle()
    print(f"清洗后状态: {system.get_system_stats()}") # 此时应该都在 DOMINANT

    print("\n--- 步骤 5: 再次检索 (触发转调验证) ---")
    # sol_001 内容包含 "valid"，验证应通过，重回主库
    print("尝试唤醒 'sol_001'...")
    node1 = system.retrieve_knowledge("sol_001")
    
    # sol_002 内容不包含 "valid"，验证应失败，变为不协和
    print("尝试唤醒 'sol_002'...")
    node2 = system.retrieve_knowledge("sol_002")
    
    print("\n--- 步骤 6: 最终状态 ---")
    print(f"最终状态: {system.get_system_stats()}")