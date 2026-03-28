"""
模块名称: dynamic_skill_graph_pathfinding
描述: 实现AGI系统中的动态技能图谱上下文寻路算法。
      该模块提供了一个基于启发式评分和图遍历的轻量级引擎，
      用于在庞大的技能节点网络中，根据当前用户意图和上下文，
      规划出最优的执行技能序列（路径）。
"""

import logging
import heapq
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名
SkillID = str
ContextDict = Dict[str, float]

@dataclass(order=True)
class SkillNode:
    """
    报价技能节点数据结构。
    
    Attributes:
        id (SkillID): 技能的唯一标识符。
        description (str): 技能功能的简短描述，用于相似度计算。
        dependencies (Set[SkillID]): 执行此技能前必须完成的先决技能ID集合。
        impact_weight (float): 该技能在通用场景下的权重/重要性 (0.0 - 1.0)。
    """
    id: SkillID
    description: str
    dependencies: Set[SkillID] = field(default_factory=set)
    impact_weight: float = 1.0
    
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, SkillNode):
            return False
        return self.id == other.id


class DynamicSkillGraph:
    """
    动态技能图谱类。
    
    管理所有技能节点，并提供基于上下文的寻路功能。
    """
    
    def __init__(self, initial_nodes: Optional[List[SkillNode]] = None):
        """
        初始化图谱。
        
        Args:
            initial_nodes (Optional[List[SkillNode]]): 初始加载的技能节点列表。
        """
        self.nodes: Dict[SkillID, SkillNode] = {}
        if initial_nodes:
            self.load_nodes(initial_nodes)
        logger.info(f"DynamicSkillGraph initialized with {len(self.nodes)} nodes.")

    def load_nodes(self, nodes: List[SkillNode]) -> None:
        """
        批量加载技能节点。
        
        Args:
            nodes (List[SkillNode]): 技能节点列表。
        
        Raises:
            ValueError: 如果节点ID重复或数据无效。
        """
        for node in nodes:
            if not isinstance(node, SkillNode):
                raise ValueError(f"Invalid node type: {type(node)}")
            if node.id in self.nodes:
                logger.warning(f"Duplicate node ID detected: {node.id}. Overwriting.")
            self.nodes[node.id] = node
        logger.info(f"Loaded {len(nodes)} nodes into the graph.")

    def get_node(self, node_id: SkillID) -> Optional[SkillNode]:
        """安全获取节点"""
        return self.nodes.get(node_id)

    def _calculate_contextual_relevance(self, skill_desc: str, current_context: ContextDict) -> float:
        """
        [辅助函数] 计算技能描述与当前上下文的相关性得分。
        
        这是一个简化的启发式函数。在实际AGI系统中，这里会调用向量数据库
        或LLM来计算语义相似度。此处我们模拟关键词匹配和权重计算。
        
        Args:
            skill_desc (str): 技能描述文本。
            current_context (ContextDict): 上下文字典，key为关键词，value为重要性权重。
            
        Returns:
            float: 相关性得分 (0.0 - 1.0)。
        """
        if not current_context:
            return 0.1 # 默认低相关性

        score = 0.0
        desc_lower = skill_desc.lower()
        
        # 模拟：如果上下文关键词出现在描述中，则累加权重
        for keyword, weight in current_context.items():
            if keyword.lower() in desc_lower:
                score += weight
        
        # 归一化处理，防止超过1.0
        return min(max(score / sum(current_context.values()), 0.0), 1.0)

    def find_optimal_path(
        self, 
        start_node_id: SkillID, 
        goal_node_id: SkillID, 
        context: ContextDict,
        max_depth: int = 5
    ) -> Tuple[List[SkillID], float]:
        """
        [核心函数] 基于A*算法思想的上下文寻路。
        
        在巨大的组合空间中，不进行全图遍历，而是利用上下文相关性作为启发式函数，
        引导搜索向最相关的依赖链延伸。
        
        Args:
            start_node_id (SkillID): 起始技能ID（通常是当前状态）。
            goal_node_id (SkillID): 目标技能ID（通常是用户意图的最终执行点）。
            context (ContextDict): 当前对话或环境的上下文特征。
            max_depth (int): 最大搜索深度，防止无限递归或组合爆炸。
            
        Returns:
            Tuple[List[SkillID], float]: 
                - 技能ID的执行路径列表。
                - 路径的总置信度得分。
                
        Raises:
            ValueError: 如果起点或终点不存在。
            RuntimeError: 如果无法找到路径。
        """
        # 1. 数据验证
        if start_node_id not in self.nodes:
            raise ValueError(f"Start node '{start_node_id}' not found in graph.")
        if goal_node_id not in self.nodes:
            raise ValueError(f"Goal node '{goal_node_id}' not found in graph.")
        
        logger.info(f"Pathfinding initiated: {start_node_id} -> {goal_node_id} | Context keys: {list(context.keys())}")

        # 优先队列: (累计代价, 当前节点ID, 路径列表)
        # 代价 = (1.0 - 累计相关性得分)，因为我们希望相关性高的排在前面（小顶堆）
        pq = [(0.0, start_node_id, [start_node_id])]
        visited: Set[SkillID] = set()
        
        while pq:
            current_cost, current_id, path = heapq.heappop(pq)
            
            # 成功找到目标
            if current_id == goal_node_id:
                logger.info(f"Path found with cost {current_cost}: {path}")
                return path, 1.0 - (current_cost / len(path)) if path else 0.0

            if len(path) > max_depth:
                logger.debug(f"Max depth reached at node {current_id}, pruning branch.")
                continue
                
            if current_id in visited:
                continue
            visited.add(current_id)
            
            current_node = self.nodes[current_id]
            
            # 获取邻居：这里主要查找依赖（前向链接）或被依赖（后向链接）
            # 为了构建执行流，我们查找当前节点的"下游"节点（或者说是由当前技能可能触发的技能）
            # 在依赖图谱中，这通常需要反向索引，这里简化为遍历所有节点检查依赖关系（实际应用需优化索引）
            neighbors = self._get_potential_next_steps(current_id)
            
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                    
                neighbor_node = self.nodes[neighbor_id]
                
                # 计算启发式得分：上下文相关性
                relevance = self._calculate_contextual_relevance(neighbor_node.description, context)
                
                # 综合权重：结合节点自身权重和上下文相关性
                step_score = (neighbor_node.impact_weight + relevance) / 2.0
                
                # 防止得分为0导致无法优先
                if step_score < 0.01:
                    step_score = 0.01
                
                # 代价累积 (负对数似然风格，或者简单的 1-score)
                # 使用 1/score 会让高得分的代价更低
                new_cost = current_cost + (1.0 / step_score)
                
                new_path = path + [neighbor_id]
                heapq.heappush(pq, (new_cost, neighbor_id, new_path))
                
        logger.warning(f"No path found between {start_node_id} and {goal_node_id}")
        raise RuntimeError("Pathfinding failed: No valid path exists within constraints.")

    def _get_potential_next_steps(self, current_id: SkillID) -> List[SkillID]:
        """
        [核心函数/内部逻辑] 获取潜在的下一步技能。
        
        在真实场景中，这会查询图数据库的边。
        这里模拟：查找依赖于当前节点的其他节点。
        """
        next_steps = []
        # 模拟逻辑：如果在真实场景，会有反向索引 adjacency_list
        # 此处为了演示完整代码，做低效遍历
        for node_id, node in self.nodes.items():
            if current_id in node.dependencies:
                next_steps.append(node_id)
        return next_steps

# ==========================================
# 使用示例与数据模拟
# ==========================================

def run_demo():
    """
    演示如何使用 DynamicSkillGraph 进行寻路。
    """
    # 1. 构造模拟数据 (模拟AGI系统中的1775个技能的一小部分)
    skills_db = [
        SkillNode("input_parser", "解析用户输入文本", set(), 0.9),
        SkillNode("intent_recognizer", "识别用户核心意图", {"input_parser"}, 0.95),
        SkillNode("db_connector", "连接内部数据库", set(), 0.8),
        SkillNode("data_retrieval", "根据关键词检索数据", {"db_connector", "intent_recognizer"}, 0.85),
        SkillNode("summarizer", "总结长文本信息", {"data_retrieval"}, 0.7),
        SkillNode("small_talk", "处理闲聊和问候", {"intent_recognizer"}, 0.5),
        SkillNode("code_generator", "根据逻辑生成Python代码", {"intent_recognizer", "data_retrieval"}, 0.9),
        SkillNode("final_output", "格式化并输最终结果", {"summarizer", "code_generator", "small_talk"}, 1.0)
    ]

    try:
        # 2. 初始化图谱
        graph = DynamicSkillGraph(skills_db)
        
        # 3. 定义用户上下文
        # 假设用户说："帮我写一个Python脚本来处理数据。"
        # 上下文提取关键词：python, code, data, script
        user_context = {
            "python": 0.9,
            "code": 0.8,
            "data": 0.6,
            "script": 0.5
        }
        
        # 4. 执行寻路
        # 起点：解析输入
        # 终点：最终输出
        # 期望路径应偏向 code_generator 分支，而非 summarizer 或 small_talk
        print("-" * 30)
        print("开始寻路演示...")
        path, confidence = graph.find_optimal_path(
            start_node_id="input_parser",
            goal_node_id="final_output",
            context=user_context,
            max_depth=10
        )
        
        print(f"\n[成功] 找到最优路径 (Confidence: {confidence:.2f}):")
        for i, node_id in enumerate(path):
            node = graph.get_node(node_id)
            print(f"Step {i+1}: {node_id} - {node.description}")
            
        # 5. 边界情况测试：不同意图
        print("-" * 30)
        print("切换上下文演示...")
        # 用户说："你好，今天天气真不错。"
        casual_context = {
            "hello": 0.8,
            "weather": 0.6,
            "chat": 0.9
        }
        
        path2, conf2 = graph.find_optimal_path(
            start_node_id="input_parser",
            goal_node_id="final_output",
            context=casual_context
        )
        
        print(f"\n[成功] 找到闲聊路径 (Confidence: {conf2:.2f}):")
        print(" -> ".join(path2))

    except ValueError as ve:
        logger.error(f"Data validation error: {ve}")
    except RuntimeError as re:
        logger.error(f"Execution error: {re}")
    except Exception as e:
        logger.critical(f"Unexpected system failure: {e}", exc_info=True)

if __name__ == "__main__":
    run_demo()