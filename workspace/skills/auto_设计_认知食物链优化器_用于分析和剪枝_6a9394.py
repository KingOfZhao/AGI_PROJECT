"""
模块: cognitive_food_chain_optimizer
描述: 设计'认知食物链优化器'。用于分析和剪枝AGI的认知网络结构。
      该能力模拟生态系统能量流动，计算高级概念（顶级捕食者）对基础数据（生产者）的依赖路径长度，
      识别'能量损耗过大'的复杂逻辑链，并自动寻找'短路'路径或淘汰'虚胖'概念。
作者: AGI System Core
版本: 1.0.0
"""

import logging
import heapq
from typing import Dict, List, Set, Tuple, Optional, Any
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
    认知网络节点类。
    
    属性:
        id: 节点唯一标识符
        node_type: 节点类型 ('producer', 'consumer', 'apex_predator')
        complexity: 维持该节点计算成本/复杂度 (0.0 to 1.0)
        value_density: 该节点对最终输出的价值贡献 (0.0 to 1.0)
        inputs: 依赖的上游节点ID列表
    """
    id: str
    node_type: str
    complexity: float = 0.5
    value_density: float = 0.5
    inputs: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.node_type not in ['producer', 'consumer', 'apex_predator']:
            raise ValueError(f"Invalid node type: {self.node_type}")
        if not (0.0 <= self.complexity <= 1.0):
            raise ValueError("Complexity must be between 0.0 and 1.0")
        if not (0.0 <= self.value_density <= 1.0):
            raise ValueError("Value density must be between 0.0 and 1.0")

class CognitiveFoodChainOptimizer:
    """
    认知食物链优化器。
    
    使用生态学隐喻分析AGI认知网络，识别并优化低效的逻辑链。
    """
    
    def __init__(self, nodes: List[CognitiveNode], metabolic_rate: float = 0.1):
        """
        初始化优化器。
        
        参数:
            nodes: 认知节点列表
            metabolic_rate: 能量在每层传递中的损耗率 (default: 0.1)
        """
        self.nodes: Dict[str, CognitiveNode] = {n.id: n for n in nodes}
        self.metabolic_rate = metabolic_rate
        self.adjacency_list = self._build_adjacency_list()
        logger.info(f"Initialized optimizer with {len(nodes)} nodes.")
        
    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """
        辅助函数：构建反向邻接表（依赖关系图）。
        
        返回:
            字典，键为节点ID，值为该节点依赖的输入节点ID列表。
        """
        adj_list = {n_id: [] for n_id in self.nodes}
        for node in self.nodes.values():
            for input_id in node.inputs:
                if input_id in self.nodes:
                    adj_list[node.id].append(input_id)
                else:
                    logger.warning(f"Node {node.id} depends on non-existent node {input_id}. Skipping.")
        return adj_list

    def calculate_trophic_path_lengths(self) -> Dict[str, Tuple[int, float]]:
        """
        核心函数：计算每个节点的营养级路径长度和累积能量成本。
        
        模拟生态学中的营养级。基础数据（生产者）为0级。
        能量成本随着路径长度和节点自身复杂度的增加而指数级上升。
        
        返回:
            Dict: {
                node_id: (path_length, accumulated_energy_cost)
            }
        """
        logger.info("Calculating trophic path lengths and energy costs...")
        path_data: Dict[str, Tuple[int, float]] = {}
        
        # 拓扑排序逻辑 (这里简化为递归深度计算，带有记忆化)
        memo: Dict[str, Tuple[int, float]] = {}
        
        def dfs(node_id: str) -> Tuple[int, float]:
            if node_id in memo:
                return memo[node_id]
            
            node = self.nodes.get(node_id)
            if not node:
                return (0, 0.0)
            
            # 生产者节点
            if node.node_type == 'producer':
                result = (0, node.complexity)
                memo[node_id] = result
                return result
            
            # 消费者/捕食者节点
            if not node.inputs:
                # 孤立的非生产者节点
                result = (0, node.complexity) 
                memo[node_id] = result
                return result

            max_input_length = 0
            base_energy = 0.0
            
            # 寻找最长的依赖链（决定营养级）和最大的输入能量
            for input_id in node.inputs:
                in_len, in_cost = dfs(input_id)
                if in_len > max_input_length:
                    max_input_length = in_len
                    base_energy = max(base_energy, in_cost)
            
            # 计算能量损耗：每层传递损耗 metabolic_rate，加上自身的复杂度惩罚
            # Energy = (Input_Energy / (1 - loss)) + Self_Complexity
            transfer_factor = 1.0 / (1.0 - self.metabolic_rate) if self.metabolic_rate < 1.0 else float('inf')
            current_energy = (base_energy * transfer_factor) + node.complexity
            
            result = (max_input_length + 1, current_energy)
            memo[node_id] = result
            return result

        for node_id in self.nodes:
            path_data[node_id] = dfs(node_id)
            
        return path_data

    def identify_inefficient_concepts(self, cost_threshold: float = 5.0, roi_threshold: float = 0.2) -> List[Dict[str, Any]]:
        """
        核心函数：识别“虚胖”的高级概念。
        
        筛选标准：能量成本极高，但对最终系统的价值贡献（ROI）极低。
        
        参数:
            cost_threshold: 累积能量成本的阈值，超过此值视为高成本
            roi_threshold: 投资回报率阈值
        
        返回:
            List: 包含低效节点详细信息的字典列表
        """
        logger.info(f"Scanning for inefficient concepts (Cost > {cost_threshold}, ROI < {roi_threshold})...")
        
        trophic_data = self.calculate_trophic_path_lengths()
        inefficient_nodes = []
        
        for node_id, (path_len, energy_cost) in trophic_data.items():
            node = self.nodes[node_id]
            
            # 计算ROI：价值密度 / 能量成本
            # 防止除以0
            roi = node.value_density / energy_cost if energy_cost > 0 else float('inf')
            
            # 检查是否为“虚胖”节点
            # 条件：不是基础生产者 && 成本过高 && 价值过低
            if node.node_type != 'producer' and energy_cost > cost_threshold and roi < roi_threshold:
                logger.warning(f"Identified inefficient node: {node_id} (Cost: {energy_cost:.2f}, ROI: {roi:.3f})")
                inefficient_nodes.append({
                    "node_id": node_id,
                    "type": node.node_type,
                    "path_length": path_len,
                    "energy_cost": energy_cost,
                    "value_density": node.value_density,
                    "roi": roi,
                    "recommendation": "PRUNE_OR_SHORTCIRCUIT"
                })
                
        return inefficient_nodes

    def suggest_short_circuits(self, target_node_id: str) -> Optional[str]:
        """
        辅助函数：为特定的高成本节点寻找“短路”路径。
        
        策略：寻找是否存在一个“祖先”节点，它能够提供与当前直接输入相似的价值，
        但处于更底层的营养级（成本更低）。这类似于用“昆虫蛋白”代替“牛肉”来喂养顶级捕食者。
        
        参数:
            target_node_id: 目标节点ID
            
        返回:
            str: 建议的替代上游节点ID，如果无则返回None
        """
        if target_node_id not in self.nodes:
            logger.error(f"Target node {target_node_id} not found.")
            return None

        node = self.nodes[target_node_id]
        if not node.inputs:
            return None

        # 获取所有祖先节点（BFS遍历依赖树）
        visited: Set[str] = set()
        queue: List[str] = list(node.inputs)
        ancestors: Set[str] = set()
        
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if curr in self.nodes:
                ancestors.add(curr)
                queue.extend(self.nodes[curr].inputs)
        
        # 移除直接父节点，只看更远的祖先
        ancestors.difference_update(set(node.inputs))
        
        # 寻找性价比最高的祖先（价值/成本最高）
        best_alternative = None
        best_ratio = -1.0
        
        all_paths = self.calculate_trophic_path_lengths()
        
        for anc_id in ancestors:
            anc_node = self.nodes[anc_id]
            cost = all_paths[anc_id][1]
            value = anc_node.value_density
            
            # 简单的启发式：寻找成本显著低于当前输入，但价值保留较多的节点
            # 这里简化为寻找 ROI (value/cost) 最高的祖先
            ratio = value / cost if cost > 0 else float('inf')
            if ratio > best_ratio:
                best_ratio = ratio
                best_alternative = anc_id
                
        if best_alternative:
            logger.info(f"Short circuit suggestion for {target_node_id}: Connect directly to {best_alternative} (Ratio: {best_ratio:.3f})")
            
        return best_alternative

# 使用示例
if __name__ == "__main__":
    # 1. 构建模拟的认知网络
    # 生产者
    n_raw_data = CognitiveNode("raw_sensor_data", "producer", complexity=0.1, value_density=0.9)
    # 中间消费者 (基础处理)
    n_clean_data = CognitiveNode("clean_data", "consumer", complexity=0.2, value_density=0.85, inputs=["raw_sensor_data"])
    # 中间消费者 (特征提取)
    n_features = CognitiveNode("basic_features", "consumer", complexity=0.3, value_density=0.7, inputs=["clean_data"])
    # 高级消费者 (复杂逻辑 - 虚胖节点)
    # 假设这里有一个极其复杂的中间层，并没有增加太多价值
    n_complex_logic = CognitiveNode(
        "over_engineered_logic", 
        "consumer", 
        complexity=0.9, 
        value_density=0.6, 
        inputs=["basic_features"]
    )
    # 顶级捕食者 (决策)
    n_decision = CognitiveNode(
        "final_decision", 
        "apex_predator", 
        complexity=0.5, 
        value_density=0.95, 
        inputs=["over_engineered_logic"]
    )
    
    nodes_list = [n_raw_data, n_clean_data, n_features, n_complex_logic, n_decision]

    # 2. 初始化优化器
    optimizer = CognitiveFoodChainOptimizer(nodes_list, metabolic_rate=0.15)
    
    # 3. 分析营养级和成本
    path_info = optimizer.calculate_trophic_path_lengths()
    print("\n--- Trophic Analysis ---")
    for nid, (length, cost) in path_info.items():
        print(f"Node: {nid:<20} | Level: {length} | Energy Cost: {cost:.4f}")

    # 4. 识别低效概念
    print("\n--- Inefficiency Scan ---")
    inefficient = optimizer.identify_inefficient_concepts(cost_threshold=2.0, roi_threshold=0.3)
    for item in inefficient:
        print(f"Pruning candidate: {item['node_id']}, ROI: {item['roi']:.4f}")

    # 5. 寻找短路路径
    print("\n--- Short Circuit Suggestion ---")
    # 尝试为决策节点寻找更直接的输入源，跳过虚胖层
    suggestion = optimizer.suggest_short_circuits("final_decision")
    if suggestion:
        print(f"Suggested direct input for 'final_decision': {suggestion}")
    else:
        print("No better short-circuit path found.")