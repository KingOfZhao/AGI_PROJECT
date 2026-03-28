"""
高级技能外脑模块：场景拓扑感知与路径预测

本模块实现了一个基于知识图谱的技能推荐系统。不同于传统的关键词搜索，
它利用图结构来表示技能、工具和知识点之间的拓扑关系。系统能够根据
用户当前在任务图中的位置（节点）和最终目标，运用启发式算法预测
下一步最可能的操作路径，并生成可视化的专家级指引。

典型应用场景：
    1. 复杂机械维修指导（如：根据故障现象推荐检查步骤）
    2. 软件开发流程辅助（如：根据当前开发阶段推荐工具链）
    3. 应急响应决策支持（如：根据灾情演变推荐处置方案）

Created by: AGI System Generator
Version: 1.0.0
"""

import logging
import heapq
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillTopologicalBrain")


class NodeType(Enum):
    """知识图谱节点类型枚举"""
    ACTION = "action"       # 操作动作
    TOOL = "tool"          # 工具
    CONCEPT = "concept"    # 知识点
    GOAL = "goal"          # 目标状态
    SYMPTOM = "symptom"    # 故障现象


@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    Attributes:
        id: 节点唯一标识符
        name: 节点显示名称
        node_type: 节点类型
        description: 详细描述
        difficulty: 难度等级 (1-10)
        dependencies: 依赖节点ID集合
        metadata: 额外元数据
    """
    id: str
    name: str
    node_type: NodeType
    description: str = ""
    difficulty: int = 5
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not self.id or not self.name:
            raise ValueError("节点ID和名称不能为空")
        if not 1 <= self.difficulty <= 10:
            raise ValueError(f"难度等级必须在1-10之间，当前: {self.difficulty}")


@dataclass
class PathResult:
    """
    路径预测结果数据结构
    
    Attributes:
        current_node: 当前节点ID
        target_node: 目标节点ID
        path: 推荐路径（节点ID列表）
        next_steps: 下一步推荐操作
        highlighted_path: 高亮显示的路径描述
        confidence: 路径置信度 (0.0-1.0)
    """
    current_node: str
    target_node: str
    path: List[str]
    next_steps: List[str]
    highlighted_path: str
    confidence: float = 0.0


class SkillTopologicalBrain:
    """
    场景拓扑感知的技能外脑核心类
    
    该类构建了一个知识图谱化的技能助手，能够：
    1. 构建技能/工具/知识点的拓扑关系图
    2. 根据当前位置和目标预测最优路径
    3. 提供专家级的直觉联想推荐
    
    Example:
        >>> brain = SkillTopologicalBrain()
        >>> brain.add_skill_node("step1", "检查电源", NodeType.ACTION)
        >>> brain.add_skill_node("step2", "更换保险丝", NodeType.ACTION)
        >>> brain.add_relation("step1", "step2")
        >>> result = brain.predict_path("step1", "repair_complete")
    """
    
    def __init__(self):
        """初始化技能外脑"""
        self.nodes: Dict[str, SkillNode] = {}
        self.adjacency: Dict[str, Set[str]] = {}  # 邻接表
        self.reverse_adjacency: Dict[str, Set[str]] = {}  # 反向邻接表（用于依赖查找）
        logger.info("技能拓扑外脑初始化完成")
    
    def add_skill_node(self, 
                       node_id: str, 
                       name: str, 
                       node_type: NodeType,
                       description: str = "",
                       difficulty: int = 5,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加技能节点到知识图谱
        
        Args:
            node_id: 节点唯一标识符
            name: 节点名称
            node_type: 节点类型
            description: 节点描述
            difficulty: 难度等级
            metadata: 额外元数据
            
        Raises:
            ValueError: 当节点已存在或参数无效时
        """
        if node_id in self.nodes:
            raise ValueError(f"节点ID '{node_id}' 已存在")
        
        try:
            node = SkillNode(
                id=node_id,
                name=name,
                node_type=node_type,
                description=description,
                difficulty=difficulty,
                metadata=metadata or {}
            )
            self.nodes[node_id] = node
            self.adjacency[node_id] = set()
            self.reverse_adjacency[node_id] = set()
            logger.debug(f"添加节点: {node_id} ({node_type.value})")
        except Exception as e:
            logger.error(f"添加节点失败: {e}")
            raise
    
    def add_relation(self, from_node: str, to_node: str, bidirectional: bool = False) -> None:
        """
        添加节点间的关系（边）
        
        Args:
            from_node: 起始节点ID
            to_node: 目标节点ID
            bidirectional: 是否双向连接
            
        Raises:
            KeyError: 当节点不存在时
        """
        self._validate_nodes_exist([from_node, to_node])
        
        self.adjacency[from_node].add(to_node)
        self.reverse_adjacency[to_node].add(from_node)
        
        if bidirectional:
            self.adjacency[to_node].add(from_node)
            self.reverse_adjacency[from_node].add(to_node)
        
        logger.debug(f"添加关系: {from_node} -> {to_node}")
    
    def predict_path(self, 
                     current_node: str, 
                     target_node: str,
                     max_depth: int = 10) -> PathResult:
        """
        核心功能：预测从当前节点到目标节点的最优路径
        
        使用A*算法进行启发式搜索，考虑节点难度和路径长度，
        预测专家级的操作步骤路径。
        
        Args:
            current_node: 当前所在节点ID
            target_node: 目标节点ID
            max_depth: 最大搜索深度（防止无限循环）
            
        Returns:
            PathResult: 包含路径、下一步操作和置信度的结果对象
            
        Raises:
            ValueError: 当参数无效时
            KeyError: 当节点不存在时
        """
        # 输入验证
        if max_depth < 1 or max_depth > 50:
            raise ValueError(f"max_depth必须在1-50之间，当前: {max_depth}")
        
        self._validate_nodes_exist([current_node, target_node])
        
        logger.info(f"开始路径预测: {current_node} -> {target_node}")
        
        # 如果已在目标节点
        if current_node == target_node:
            return PathResult(
                current_node=current_node,
                target_node=target_node,
                path=[current_node],
                next_steps=[],
                highlighted_path=f"已到达目标: {self.nodes[current_node].name}",
                confidence=1.0
            )
        
        # A*算法搜索路径
        path = self._astar_search(current_node, target_node, max_depth)
        
        if not path:
            logger.warning(f"未找到从 {current_node} 到 {target_node} 的路径")
            return PathResult(
                current_node=current_node,
                target_node=target_node,
                path=[],
                next_steps=[],
                highlighted_path="无法到达目标，请检查前置条件",
                confidence=0.0
            )
        
        # 生成下一步推荐
        next_steps = path[1:4] if len(path) > 1 else []  # 最多显示3个下一步
        
        # 生成高亮路径描述
        highlighted = self._generate_highlighted_path(path)
        
        # 计算置信度（基于路径长度和节点难度）
        confidence = self._calculate_confidence(path)
        
        result = PathResult(
            current_node=current_node,
            target_node=target_node,
            path=path,
            next_steps=next_steps,
            highlighted_path=highlighted,
            confidence=confidence
        )
        
        logger.info(f"路径预测完成，置信度: {confidence:.2f}")
        return result
    
    def _astar_search(self, start: str, goal: str, max_depth: int) -> List[str]:
        """
        A*算法实现：启发式搜索最优路径
        
        Args:
            start: 起始节点
            goal: 目标节点
            max_depth: 最大搜索深度
            
        Returns:
            节点ID列表表示的路径，若未找到返回空列表
        """
        # 优先队列: (f_score, counter, node, path)
        counter = 0
        open_set = [(0, counter, start, [start])]
        visited: Set[str] = set()
        
        while open_set and len(visited) < max_depth * 10:
            _, _, current, path = heapq.heappop(open_set)
            
            if current == goal:
                return path
            
            if current in visited:
                continue
            visited.add(current)
            
            # 防止路径过长
            if len(path) > max_depth:
                continue
            
            # 探索邻居节点
            for neighbor in self.adjacency.get(current, set()):
                if neighbor not in visited:
                    counter += 1
                    g_score = len(path)  # 实际代价
                    h_score = self._heuristic(neighbor, goal)  # 启发式代价
                    f_score = g_score + h_score
                    heapq.heappush(open_set, (f_score, counter, neighbor, path + [neighbor]))
        
        return []
    
    def _heuristic(self, node: str, goal: str) -> float:
        """
        启发式函数：估计从当前节点到目标的代价
        
        考虑因素：
        1. 节点难度（高难度节点代价更高）
        2. 是否有直接连接（简化估计）
        
        Args:
            node: 当前节点
            goal: 目标节点
            
        Returns:
            启发式代价估计值
        """
        # 基础代价
        base_cost = 1.0
        
        # 难度调整（难度越高，代价越大）
        difficulty_penalty = self.nodes[node].difficulty * 0.1
        
        # 如果有直接连接，降低代价
        if goal in self.adjacency.get(node, set()):
            direct_bonus = -0.5
        else:
            direct_bonus = 0.0
        
        return max(0.1, base_cost + difficulty_penalty + direct_bonus)
    
    def _generate_highlighted_path(self, path: List[str]) -> str:
        """
        生成高亮显示的路径描述
        
        Args:
            path: 节点ID列表
            
        Returns:
            格式化的路径描述字符串
        """
        if not path:
            return "无可用路径"
        
        descriptions = []
        for i, node_id in enumerate(path):
            node = self.nodes[node_id]
            step_num = i + 1
            
            # 根据节点类型添加图标
            icon = {
                NodeType.ACTION: "🔧",
                NodeType.TOOL: "🔨",
                NodeType.CONCEPT: "💡",
                NodeType.GOAL: "🎯",
                NodeType.SYMPTOM: "⚠️"
            }.get(node.node_type, "📌")
            
            descriptions.append(f"{step_num}. {icon} {node.name}")
        
        return "\n".join(descriptions)
    
    def _calculate_confidence(self, path: List[str]) -> float:
        """
        计算路径的置信度
        
        基于以下因素：
        1. 路径长度（越短置信度越高）
        2. 节点难度（难度越低置信度越高）
        
        Args:
            path: 节点ID列表
            
        Returns:
            置信度值 (0.0-1.0)
        """
        if not path:
            return 0.0
        
        # 路径长度因子（最长10步为基准）
        length_factor = max(0.1, 1.0 - len(path) / 10.0)
        
        # 难度因子
        avg_difficulty = sum(self.nodes[n].difficulty for n in path) / len(path)
        difficulty_factor = max(0.1, 1.1 - avg_difficulty / 10.0)
        
        confidence = (length_factor * 0.6 + difficulty_factor * 0.4)
        return min(1.0, max(0.0, confidence))
    
    def _validate_nodes_exist(self, node_ids: List[str]) -> None:
        """
        验证节点是否存在
        
        Args:
            node_ids: 需要验证的节点ID列表
            
        Raises:
            KeyError: 当节点不存在时
        """
        for node_id in node_ids:
            if node_id not in self.nodes:
                raise KeyError(f"节点 '{node_id}' 不存在于知识图谱中")
    
    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """
        辅助功能：获取节点的上下文信息
        
        包括节点详情、前置条件、后续步骤等
        
        Args:
            node_id: 节点ID
            
        Returns:
            包含上下文信息的字典
        """
        self._validate_nodes_exist([node_id])
        
        node = self.nodes[node_id]
        
        # 获取前置节点（依赖）
        prerequisites = [
            self.nodes[n].name for n in self.reverse_adjacency.get(node_id, set())
        ]
        
        # 获取后续节点
        next_nodes = [
            self.nodes[n].name for n in self.adjacency.get(node_id, set())
        ]
        
        return {
            "id": node_id,
            "name": node.name,
            "type": node.node_type.value,
            "description": node.description,
            "difficulty": node.difficulty,
            "prerequisites": prerequisites,
            "next_possible_steps": next_nodes,
            "metadata": node.metadata
        }
    
    def recommend_tools_for_path(self, path: List[str]) -> List[Dict[str, Any]]:
        """
        辅助功能：为路径推荐所需工具
        
        Args:
            path: 节点ID列表
            
        Returns:
            工具推荐列表
        """
        tools = []
        seen_tools = set()
        
        for node_id in path:
            node = self.nodes[node_id]
            
            # 检查节点元数据中的工具信息
            if "required_tools" in node.metadata:
                for tool in node.metadata["required_tools"]:
                    if tool not in seen_tools:
                        tools.append({
                            "tool": tool,
                            "used_in_step": node.name,
                            "step_id": node_id
                        })
                        seen_tools.add(tool)
            
            # 如果节点本身就是工具类型
            if node.node_type == NodeType.TOOL and node_id not in seen_tools:
                tools.append({
                    "tool": node.name,
                    "used_in_step": "直接使用",
                    "step_id": node_id
                })
                seen_tools.add(node_id)
        
        return tools


# 使用示例
if __name__ == "__main__":
    """
    使用示例：汽车故障诊断场景
    
    模拟一个简化的汽车启动故障诊断流程，
    展示如何构建技能拓扑图并进行路径预测。
    """
    
    # 初始化技能外脑
    brain = SkillTopologicalBrain()
    
    # 构建故障诊断知识图谱
    # 添加节点
    brain.add_skill_node(
        "symptom_car_wont_start",
        "车辆无法启动",
        NodeType.SYMPTOM,
        "发动机无法点火启动",
        difficulty=2
    )
    
    brain.add_skill_node(
        "check_battery",
        "检查蓄电池电量",
        NodeType.ACTION,
        "使用万用表检测电池电压",
        difficulty=3,
        metadata={"required_tools": ["万用表"]}
    )
    
    brain.add_skill_node(
        "check_fuse",
        "检查保险丝",
        NodeType.ACTION,
        "查看启动保险丝是否熔断",
        difficulty=2,
        metadata={"required_tools": ["保险丝夹", "备用保险丝"]}
    )
    
    brain.add_skill_node(
        "check_starter",
        "检查启动机",
        NodeType.ACTION,
        "测试启动机电磁阀",
        difficulty=6,
        metadata={"required_tools": ["测试灯", "跨接线"]}
    )
    
    brain.add_skill_node(
        "multimeter",
        "万用表",
        NodeType.TOOL,
        "电压、电流、电阻测量工具",
        difficulty=4
    )
    
    brain.add_skill_node(
        "replace_battery",
        "更换蓄电池",
        NodeType.ACTION,
        "安装新蓄电池",
        difficulty=4,
        metadata={"required_tools": ["扳手套装", "新蓄电池"]}
    )
    
    brain.add_skill_node(
        "goal_car_fixed",
        "故障排除",
        NodeType.GOAL,
        "车辆恢复正常启动",
        difficulty=1
    )
    
    # 构建关系拓扑
    brain.add_relation("symptom_car_wont_start", "check_battery")
    brain.add_relation("symptom_car_wont_start", "check_fuse")
    brain.add_relation("check_battery", "replace_battery")
    brain.add_relation("check_battery", "check_starter")
    brain.add_relation("check_fuse", "check_starter")
    brain.add_relation("replace_battery", "goal_car_fixed")
    brain.add_relation("check_starter", "goal_car_fixed")
    brain.add_relation("multimeter", "check_battery")  # 工具依赖
    
    # 场景1：预测从故障现象到排除的路径
    print("=" * 60)
    print("场景1：完整故障诊断路径预测")
    print("=" * 60)
    result = brain.predict_path("symptom_car_wont_start", "goal_car_fixed")
    
    print(f"\n置信度: {result.confidence:.2%}")
    print(f"\n推荐路径:\n{result.highlighted_path}")
    print(f"\n下一步操作: {result.next_steps}")
    
    # 获取工具推荐
    tools = brain.recommend_tools_for_path(result.path)
    print("\n所需工具:")
    for t in tools:
        print(f"  - {t['tool']} (用于: {t['used_in_step']})")
    
    # 场景2：获取当前节点的上下文
    print("\n" + "=" * 60)
    print("场景2：获取节点上下文信息")
    print("=" * 60)
    context = brain.get_node_context("check_battery")
    print(f"\n节点: {context['name']}")
    print(f"类型: {context['type']}")
    print(f"描述: {context['description']}")
    print(f"前置条件: {context['prerequisites']}")
    print(f"后续步骤: {context['next_possible_steps']}")
    
    # 场景3：中途路径调整
    print("\n" + "=" * 60)
    print("场景3：从中途节点重新预测路径")
    print("=" * 60)
    result2 = brain.predict_path("check_fuse", "goal_car_fixed")
    print(f"\n从 'check_fuse' 到目标的路径:\n{result2.highlighted_path}")