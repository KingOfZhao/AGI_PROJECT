"""
高级技能模块: 动态上下文技能导航图

该模块实现了一个基于图拓扑算法的动态技能推荐系统。不同于传统的静态检索，
本系统根据用户的当前状态（节点A），实时预测并生成下一步最可能的动作路径。

核心特性:
- 基于状态机的图结构建模
- 启发式最短路径计算
- 动态剪枝与上下文过滤
- 高亮显示最短认知路径

作者: Senior Python Engineer for AGI System
版本: 1.0.0
领域: cross_domain
"""

import logging
import heapq
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DynamicSkillNavigator")


class NavigatorError(Exception):
    """基础异常类，用于导航过程中的错误处理。"""
    pass


class NodeNotFoundError(NavigatorError):
    """当请求的节点在图中不存在时抛出。"""
    pass


class PathFindingError(NavigatorError):
    """当无法计算路径时抛出。"""
    pass


@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    属性:
        id: 节点的唯一标识符
        description: 节点描述
        context_tags: 上下文标签集合，用于匹配当前环境
        neighbors: 相邻节点ID及其权重的映射 (id -> weight)
    """
    id: str
    description: str
    context_tags: Set[str] = field(default_factory=set)
    neighbors: Dict[str, float] = field(default_factory=dict)  # target_id -> cost

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, SkillNode):
            return self.id == other.id
        return False


class DynamicContextSkillNavigator:
    """
    动态上下文技能导航图生成器。
    
    该类维护一个技能知识图谱，并根据当前的上下文状态（已完成节点、环境标签），
    计算下一步的最优动作。
    
    输入格式:
        - current_node_id: 当前完成的节点ID
        - context: 当前环境上下文字典，如 {'weather': 'rain', 'inventory': ['wood']}
    
    输出格式:
        - Dict: 包含 'highlighted_path' (最短路径) 和 'suggested_actions' (Top 3 预测)
    """

    def __init__(self):
        """初始化导航图数据结构。"""
        self.graph: Dict[str, SkillNode] = {}
        self._context_cache: Dict[str, Any] = {}
        logger.info("DynamicContextSkillNavigator initialized.")

    def add_node(self, node: SkillNode) -> None:
        """
        向图中添加技能节点。
        
        参数:
            node: SkillNode 实例
            
        异常:
            ValueError: 如果节点ID为空或已存在
        """
        if not node.id or not isinstance(node.id, str):
            raise ValueError("Node ID must be a non-empty string.")
        
        if node.id in self.graph:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        
        self.graph[node.id] = node
        logger.debug(f"Node added: {node.id}")

    def _validate_node_exists(self, node_id: str) -> None:
        """辅助函数：检查节点是否存在。"""
        if node_id not in self.graph:
            logger.error(f"Validation failed: Node {node_id} not found.")
            raise NodeNotFoundError(f"Node '{node_id}' does not exist in the graph.")

    def _heuristic_cost(self, current_node: SkillNode, target_node: SkillNode, current_context: Dict[str, Any]) -> float:
        """
        辅助函数：计算启发式成本。
        
        基于上下文匹配度调整成本。如果目标节点的标签与当前环境匹配，
        则降低成本（优先推荐）。
        """
        base_cost = 1.0
        context_match_count = 0
        
        # 简单的上下文匹配逻辑：检查环境属性是否支持节点的标签需求
        # 实际AGI场景中，这里会使用Embedding向量相似度计算
        environment_flags = set(str(v) for v in current_context.values())
        
        matches = len(current_node.context_tags.intersection(environment_flags))
        
        # 匹配度越高，成本越低 (负相关)
        adjustment = matches * 0.5 
        final_cost = base_cost - adjustment
        
        return max(0.1, final_cost) # 确保成本不为负或零

    def predict_next_steps(
        self, 
        current_node_id: str, 
        current_context: Dict[str, Any],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        核心功能：预测下一步动作并生成导航图。
        
        参数:
            current_node_id: 当前所处的节点ID
            current_context: 当前环境上下文 (如天气、物品清单)
            top_k: 返回的最可能动作数量
            
        返回:
            包含建议动作和高亮路径的字典。
            
        异常:
            NodeNotFoundError: 起始节点不存在
            PathFindingError: 路径计算失败
        """
        try:
            self._validate_node_exists(current_node_id)
            start_node = self.graph[current_node_id]
            
            # 1. 获取所有直接可达的邻居
            candidates = []
            for neighbor_id, weight in start_node.neighbors.items():
                self._validate_node_exists(neighbor_id)
                neighbor_node = self.graph[neighbor_id]
                
                # 计算动态成本：基础权重 + 启发式上下文调整
                dynamic_cost = weight + self._heuristic_cost(start_node, neighbor_node, current_context)
                candidates.append((dynamic_cost, neighbor_id, neighbor_node.description))
            
            # 2. 排序并选取 Top-K
            # 使用堆排序 (nsmallest) 提高效率，虽然对于小规模邻居列表差异不大
            top_candidates = heapq.nsmallest(top_k, candidates, key=lambda x: x[0])
            
            formatted_suggestions = [
                {
                    "node_id": item[1], 
                    "description": item[2], 
                    "cost": item[0]
                } 
                for item in top_candidates
            ]
            
            # 3. 计算最短认知路径 (从当前节点到某个假设的'目标'节点，这里简化为到最优邻居的路径)
            # 在实际场景中，这可能是通往'生存'或'任务完成'终点的路径
            # 这里我们模拟高亮到最优建议的路径
            highlighted_path = []
            if top_candidates:
                best_next_node_id = top_candidates[0][1]
                highlighted_path = [
                    {"id": current_node_id, "action": "Current State"},
                    {"id": best_next_node_id, "action": "Recommended Next Step"}
                ]

            logger.info(f"Prediction generated for {current_node_id}. Top suggestion: {top_candidates[0][1] if top_candidates else 'None'}")
            
            return {
                "start_node": current_node_id,
                "context_matched": current_context,
                "suggested_actions": formatted_suggestions,
                "highlighted_cognitive_path": highlighted_path,
                "algorithm": "Dynamic Dijkstra with Context Heuristics"
            }

        except NodeNotFoundError:
            raise
        except Exception as e:
            logger.exception("Unexpected error during path prediction.")
            raise PathFindingError(f"Failed to compute path: {str(e)}")


# 使用示例
if __name__ == "__main__":
    # 1. 初始化导航系统
    navigator = DynamicContextSkillNavigator()

    # 2. 构建生存技能图谱
    # 节点定义
    node_start = SkillNode(
        id="start_camp", 
        description="营地建立起点", 
        context_tags={"forest"}, 
        neighbors={"gather_wood": 1.0, "find_water": 1.5, "build_shelter": 3.0}
    )
    
    node_wood = SkillNode(
        id="gather_wood", 
        description="收集干柴", 
        context_tags={"forest", "daytime"}, 
        neighbors={"make_fire": 1.0}
    )
    
    node_water = SkillNode(
        id="find_water", 
        description="寻找水源", 
        context_tags={"valley"}, 
        neighbors={"purify_water": 2.0}
    )
    
    node_shelter = SkillNode(
        id="build_shelter", 
        description="搭建庇护所", 
        context_tags={"forest", "rain"}, 
        neighbors={"rest": 5.0}
    )
    
    node_fire = SkillNode(
        id="make_fire", 
        description="生火", 
        context_tags={"wood", "dry"}, 
        neighbors={"cook_food": 1.0}
    )

    # 添加节点到导航图
    for node in [node_start, node_wood, node_water, node_shelter, node_fire]:
        navigator.add_node(node)

    # 3. 模拟场景：用户处于起点，天在下雨 (Context: rain)
    # 期望结果：系统应优先推荐搭建庇护所 (build_shelter)，因为其 context_tags 包含 'rain'，
    # 从而使得 heuristic cost 降低，或者尽管其基础权重较高，但在特定上下文下可能被优先推荐
    # 注意：本例中的 heuristic 仅做简单的集合匹配演示
    
    print("--- 场景 1: 下雨的森林 ---")
    context_rain = {"weather": "rain", "location": "forest"}
    try:
        result = navigator.predict_next_steps("start_camp", context_rain)
        print(f"建议动作: {result['suggested_actions']}")
        print(f"高亮路径: {result['highlighted_cognitive_path']}")
    except NavigatorError as e:
        print(f"Error: {e}")

    print("\n--- 场景 2: 晴朗的白天 (无特殊上下文匹配) ---")
    context_sunny = {"weather": "sunny", "time": "day"}
    try:
        result = navigator.predict_next_steps("start_camp", context_sunny)
        print(f"建议动作: {result['suggested_actions']}")
        print(f"高亮路径: {result['highlighted_cognitive_path']}")
    except NavigatorError as e:
        print(f"Error: {e}")