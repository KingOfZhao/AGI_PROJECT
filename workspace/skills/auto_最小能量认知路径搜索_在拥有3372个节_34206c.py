"""
最小能量认知路径搜索模块

本模块实现了一种基于'认知阻力'（Cognitive Resistance）的寻路算法，用于在大型技能网络中
寻找解决特定问题的最优技能组合路径。该算法模拟物理能量最小化原理，在拥有3372个节点的
复杂网络中快速检索最优路径。

核心算法：
1. 认知阻力计算：基于技能相似性、使用频率和领域距离计算节点间的认知阻力
2. 能量最小化路径搜索：使用改进的Dijkstra算法，寻找总认知阻力最小的路径

数据结构：
- 节点：表示单个技能或概念，包含属性（难度、领域、使用频率等）
- 边：表示技能间的依赖关系，带有认知阻力权重
"""

import heapq
import math
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import numpy as np
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillNode:
    """技能节点数据结构"""
    id: int
    name: str
    domain: str
    difficulty: float  # 1.0-10.0
    usage_frequency: float  # 使用频率归一化值 0.0-1.0
    prerequisites: List[int]  # 前置技能ID列表


@dataclass
class PathResult:
    """路径搜索结果"""
    path: List[int]
    total_resistance: float
    execution_time: float  # 估算执行时间
    success_probability: float


class CognitivePathFinder:
    """
    最小能量认知路径搜索器
    
    在复杂技能网络中，基于认知阻力计算最优技能组合路径。
    认知阻力模拟人类学习新技能时的认知负荷，综合考虑：
    1. 技能难度差异
    2. 领域跨度
    3. 使用频率
    4. 先验知识依赖
    
    示例用法:
    >>> finder = CognitivePathFinder()
    >>> finder.load_skill_network("skills.json")
    >>> result = finder.find_optimal_path(start_id=42, goal_id=1024)
    >>> print(f"最优路径: {result.path}")
    """
    
    def __init__(self):
        self.nodes: Dict[int, SkillNode] = {}
        self.edges: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.skill_embeddings: Optional[np.ndarray] = None
        self.domain_similarity: Dict[str, Dict[str, float]] = {}
        self._initialized = False
        
    def load_skill_network(self, file_path: str) -> bool:
        """
        从JSON文件加载技能网络数据
        
        参数:
            file_path: JSON文件路径，格式要求:
                {
                    "nodes": [{"id": 1, "name": "...", "domain": "...", ...}],
                    "edges": [{"source": 1, "target": 2, "weight": 0.5}, ...]
                }
        
        返回:
            bool: 加载是否成功
        """
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 验证数据完整性
            if not self._validate_network_data(data):
                logger.error("Invalid network data format")
                return False
                
            # 加载节点
            for node_data in data["nodes"]:
                node = SkillNode(
                    id=node_data["id"],
                    name=node_data["name"],
                    domain=node_data["domain"],
                    difficulty=node_data["difficulty"],
                    usage_frequency=node_data["usage_frequency"],
                    prerequisites=node_data.get("prerequisites", [])
                )
                self.nodes[node.id] = node
                
            # 加载边
            for edge in data["edges"]:
                source = edge["source"]
                target = edge["target"]
                weight = edge.get("weight", self._default_edge_weight(source, target))
                self.edges[source][target] = weight
                
            # 计算领域相似度矩阵
            self._calculate_domain_similarity()
            
            self._initialized = True
            logger.info(f"Loaded skill network with {len(self.nodes)} nodes and {sum(len(e) for e in self.edges.values())} edges")
            return True
            
        except Exception as e:
            logger.error(f"Error loading skill network: {str(e)}")
            return False
    
    def find_optimal_path(
        self, 
        start_id: int, 
        goal_id: int,
        max_depth: int = 15,
        resistance_threshold: float = 50.0
    ) -> Optional[PathResult]:
        """
        寻找从起始技能到目标技能的最小认知阻力路径
        
        参数:
            start_id: 起始技能节点ID
            goal_id: 目标技能节点ID
            max_depth: 最大搜索深度（防止无限循环）
            resistance_threshold: 认知阻力阈值，超过此值的路径将被剪枝
            
        返回:
            PathResult: 包含最优路径信息，如果找不到则返回None
        """
        if not self._initialized:
            logger.error("Skill network not initialized. Call load_skill_network() first.")
            return None
            
        if start_id not in self.nodes or goal_id not in self.nodes:
            logger.error("Invalid start or goal node ID")
            return None
            
        if start_id == goal_id:
            return PathResult(
                path=[start_id],
                total_resistance=0.0,
                execution_time=self._estimate_execution_time([start_id]),
                success_probability=1.0
            )
        
        # 改进的Dijkstra算法，考虑认知阻力
        heap = []
        heapq.heappush(heap, (0.0, start_id, [start_id]))
        
        visited = set()
        resistances = {node_id: float('inf') for node_id in self.nodes}
        resistances[start_id] = 0.0
        
        best_path = None
        best_resistance = float('inf')
        
        while heap:
            current_resistance, current_id, path = heapq.heappop(heap)
            
            if current_id == goal_id:
                if current_resistance < best_resistance:
                    best_resistance = current_resistance
                    best_path = path.copy()
                continue
                
            if current_id in visited or len(path) > max_depth:
                continue
                
            visited.add(current_id)
            
            for neighbor_id, edge_weight in self.edges[current_id].items():
                if neighbor_id in visited:
                    continue
                    
                # 计算认知阻力（考虑多种因素）
                resistance = self._calculate_cognitive_resistance(
                    current_id, neighbor_id, path
                )
                
                new_resistance = current_resistance + resistance
                
                # 剪枝：跳过阻力过大的路径
                if new_resistance > resistance_threshold:
                    continue
                    
                if new_resistance < resistances[neighbor_id]:
                    resistances[neighbor_id] = new_resistance
                    heapq.heappush(heap, (new_resistance, neighbor_id, path + [neighbor_id]))
        
        if best_path:
            return PathResult(
                path=best_path,
                total_resistance=best_resistance,
                execution_time=self._estimate_execution_time(best_path),
                success_probability=self._calculate_success_probability(best_path)
            )
        
        logger.warning(f"No path found from {start_id} to {goal_id}")
        return None
    
    def find_skill_combinations(
        self, 
        problem_description: str, 
        max_results: int = 5
    ) -> List[PathResult]:
        """
        基于问题描述自动发现最佳技能组合
        
        参数:
            problem_description: 问题描述文本
            max_results: 返回的最大结果数
            
        返回:
            List[PathResult]: 排序后的最优技能组合列表
        """
        if not self._initialized:
            logger.error("Skill network not initialized")
            return []
            
        # 简化版：使用关键词匹配找到相关技能
        keywords = set(problem_description.lower().split())
        candidate_skills = []
        
        for node_id, node in self.nodes.items():
            skill_keywords = set(node.name.lower().split())
            overlap = len(keywords & skill_keywords)
            if overlap > 0:
                candidate_skills.append((node_id, overlap))
        
        # 按关键词重叠度排序
        candidate_skills.sort(key=lambda x: -x[1])
        top_candidates = [cs[0] for cs in candidate_skills[:10]]
        
        # 在候选技能之间寻找最优路径
        results = []
        for i in range(len(top_candidates)):
            for j in range(i+1, min(i+3, len(top_candidates))):
                path_result = self.find_optimal_path(
                    top_candidates[i], 
                    top_candidates[j],
                    max_depth=10
                )
                if path_result:
                    results.append(path_result)
        
        # 按总阻力排序
        results.sort(key=lambda x: x.total_resistance)
        return results[:max_results]
    
    def _calculate_cognitive_resistance(
        self, 
        source_id: int, 
        target_id: int,
        current_path: List[int]
    ) -> float:
        """
        计算两个技能节点间的认知阻力
        
        参数:
            source_id: 源节点ID
            target_id: 目标节点ID
            current_path: 当前路径（用于上下文计算）
            
        返回:
            float: 认知阻力值
        """
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        
        # 基础阻力：技能难度差异
        difficulty_diff = abs(source.difficulty - target.difficulty)
        
        # 领域跨度阻力
        domain_resistance = 1.0 - self.domain_similarity.get(source.domain, {}).get(target.domain, 0.0)
        
        # 使用频率因子（高频技能阻力小）
        frequency_factor = 1.0 / (0.1 + min(source.usage_frequency, target.usage_frequency))
        
        # 路径上下文因子（避免重复访问相似领域）
        context_factor = 1.0
        if len(current_path) > 2:
            recent_domains = [self.nodes[nid].domain for nid in current_path[-2:]]
            if target.domain in recent_domains:
                context_factor = 0.7  # 相同领域奖励
        
        # 计算总阻力（类似物理能量）
        total_resistance = (
            difficulty_diff * 0.4 + 
            domain_resistance * 0.3 + 
            frequency_factor * 0.2 +
            context_factor * 0.1
        ) * self.edges[source_id].get(target_id, 1.0)
        
        return total_resistance
    
    def _validate_network_data(self, data: dict) -> bool:
        """验证网络数据完整性"""
        if not isinstance(data, dict):
            return False
        if "nodes" not in data or "edges" not in data:
            return False
        if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
            return False
            
        # 检查节点数据
        required_node_fields = ["id", "name", "domain", "difficulty", "usage_frequency"]
        for node in data["nodes"]:
            if not all(field in node for field in required_node_fields):
                logger.error(f"Missing required fields in node: {node}")
                return False
            if not (0 <= node["usage_frequency"] <= 1):
                logger.error(f"Invalid usage_frequency in node {node['id']}")
                return False
            if not (1 <= node["difficulty"] <= 10):
                logger.error(f"Invalid difficulty in node {node['id']}")
                return False
                
        return True
    
    def _calculate_domain_similarity(self) -> None:
        """计算领域相似度矩阵"""
        domains = set(node.domain for node in self.nodes.values())
        self.domain_similarity = {domain: {} for domain in domains}
        
        # 简化版：基于领域名称相似度
        for d1 in domains:
            for d2 in domains:
                if d1 == d2:
                    self.domain_similarity[d1][d2] = 1.0
                else:
                    # 简单字符串相似度
                    common = len(set(d1.split('_')) & set(d2.split('_')))
                    total = len(set(d1.split('_')) | set(d2.split('_')))
                    self.domain_similarity[d1][d2] = common / max(total, 1)
    
    def _default_edge_weight(self, source_id: int, target_id: int) -> float:
        """计算默认边权重"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return 1.0
        return 0.5 + 0.5 * abs(self.nodes[source_id].difficulty - self.nodes[target_id].difficulty)
    
    def _estimate_execution_time(self, path: List[int]) -> float:
        """估算路径执行时间（基于难度和长度）"""
        if not path:
            return 0.0
        total_difficulty = sum(self.nodes[node_id].difficulty for node_id in path)
        return total_difficulty * 0.5  # 简单估算模型
    
    def _calculate_success_probability(self, path: List[int]) -> float:
        """计算路径执行成功概率"""
        if not path:
            return 0.0
            
        probability = 1.0
        for node_id in path:
            node = self.nodes[node_id]
            # 使用频率高的技能成功率更高
            probability *= (0.5 + 0.5 * node.usage_frequency)
        
        return min(probability, 1.0)


# 示例用法
if __name__ == "__main__":
    # 创建测试数据
    test_data = {
        "nodes": [
            {"id": 1, "name": "python基础", "domain": "programming", "difficulty": 3.0, "usage_frequency": 0.9},
            {"id": 2, "name": "数据结构", "domain": "computer_science", "difficulty": 5.0, "usage_frequency": 0.8},
            {"id": 3, "name": "机器学习", "domain": "ai", "difficulty": 7.0, "usage_frequency": 0.7},
            {"id": 4, "name": "神经网络", "domain": "ai", "difficulty": 8.0, "usage_frequency": 0.6},
            {"id": 5, "name": "深度学习", "domain": "ai", "difficulty": 9.0, "usage_frequency": 0.5},
        ],
        "edges": [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 3, "target": 4},
            {"source": 4, "target": 5},
            {"source": 1, "target": 3, "weight": 1.5},
            {"source": 2, "target": 4, "weight": 1.2},
        ]
    }
    
    # 保存测试数据
    import json
    with open("test_skills.json", "w") as f:
        json.dump(test_data, f)
    
    # 使用示例
    finder = CognitivePathFinder()
    if finder.load_skill_network("test_skills.json"):
        # 查找从Python基础到深度学习的最优路径
        result = finder.find_optimal_path(start_id=1, goal_id=5)
        if result:
            print(f"最优路径: {[finder.nodes[nid].name for nid in result.path]}")
            print(f"总认知阻力: {result.total_resistance:.2f}")
            print(f"估算执行时间: {result.execution_time:.2f}")
            print(f"成功概率: {result.success_probability:.2f}")
        
        # 自动发现技能组合
        combinations = finder.find_skill_combinations("我想学习人工智能")
        print("\n推荐技能组合:")
        for i, res in enumerate(combinations, 1):
            print(f"{i}. {[finder.nodes[nid].name for nid in res.path]}")