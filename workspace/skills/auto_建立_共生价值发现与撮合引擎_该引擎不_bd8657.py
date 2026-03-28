"""
共生价值发现与撮合引擎

该模块实现了一个基于多维度分析的价值发现系统，结合经济成本分析和生态功能互补性分析，
识别企业间、部门间或AI智能体间的潜在合作机会。

核心功能：
1. 量化共生收益
2. 识别高互补价值节点
3. 构建稳固的商业生态系统

典型使用场景：
- 企业战略联盟发现
- 跨部门资源优化
- AI智能体协作网络构建

数据格式说明：
输入: 节点列表(包含属性字典)和关系矩阵(可选)
输出: 价值评估报告(字典)和优化建议(列表)
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MIN_COMPETENCY_THRESHOLD = 0.1
MAX_ITERATIONS = 100
CONVERGENCE_THRESHOLD = 0.001

@dataclass
class Node:
    """表示系统中的参与节点"""
    id: str
    attributes: Dict[str, Union[float, str]]
    competency_score: float = 0.0
    complementarity_score: float = 0.0

class SymbioticValueEngine:
    """共生价值发现与撮合引擎"""
    
    def __init__(self, nodes: List[Node], relations: Optional[np.ndarray] = None):
        """
        初始化引擎
        
        Args:
            nodes: 参与节点列表
            relations: 节点间关系矩阵(可选)，形状为(n_nodes, n_nodes)
        """
        self.nodes = {node.id: node for node in nodes}
        self.relations = relations
        self._validate_inputs()
        logger.info("初始化共生价值引擎，包含%d个节点", len(nodes))
    
    def _validate_inputs(self) -> None:
        """验证输入数据的有效性"""
        if not self.nodes:
            raise ValueError("节点列表不能为空")
            
        for node in self.nodes.values():
            if not isinstance(node.attributes, dict):
                raise TypeError(f"节点{node.id}的属性必须是字典")
                
        if self.relations is not None:
            if self.relations.shape != (len(self.nodes), len(self.nodes)):
                raise ValueError("关系矩阵形状必须与节点数量匹配")
    
    def calculate_competency_scores(self) -> Dict[str, float]:
        """
        计算每个节点的能力得分(经济视角)
        
        基于节点的成本效益分析，量化其独立运营时的效率
        
        Returns:
            字典: {node_id: competency_score}
        """
        scores = {}
        for node_id, node in self.nodes.items():
            try:
                # 示例计算: 综合考虑收入、成本、市场份额等因素
                revenue = node.attributes.get('revenue', 0)
                cost = node.attributes.get('cost', 1)  # 避免除以0
                market_share = node.attributes.get('market_share', 0)
                
                # 确保数值有效性
                revenue = max(0, float(revenue))
                cost = max(1e-6, float(cost))  # 避免除以0
                market_share = max(0, min(1, float(market_share)))
                
                # 能力得分计算公式
                competency = (revenue / cost) * (1 + market_share)
                competency = max(MIN_COMPETENCY_THRESHOLD, competency)
                
                node.competency_score = competency
                scores[node_id] = competency
                logger.debug("节点%s能力得分: %.3f", node_id, competency)
                
            except (TypeError, ValueError) as e:
                logger.error("计算节点%s能力得分时出错: %s", node_id, str(e))
                scores[node_id] = MIN_COMPETENCY_THRESHOLD
        
        return scores
    
    def calculate_complementarity_scores(self) -> Dict[str, float]:
        """
        计算每个节点的互补性得分(生态视角)
        
        识别虽然自身效率不高但具有极高互补价值的节点
        
        Returns:
            字典: {node_id: complementarity_score}
        """
        if self.relations is None:
            logger.warning("未提供关系矩阵，使用默认互补性计算")
            return self._default_complementarity_calculation()
        
        scores = {}
        n_nodes = len(self.nodes)
        node_ids = list(self.nodes.keys())
        
        for i in range(n_nodes):
            node_id = node_ids[i]
            total_comp = 0.0
            
            for j in range(n_nodes):
                if i != j:
                    # 计算节点i与其他节点的互补性
                    relation_strength = self.relations[i, j]
                    other_node = self.nodes[node_ids[j]]
                    
                    # 互补性计算: 考虑关系强度和对方节点的能力
                    comp = relation_strength * (1 / (other_node.competency_score + 1e-6))
                    total_comp += comp
            
            # 归一化处理
            normalized_comp = total_comp / (n_nodes - 1) if n_nodes > 1 else 0
            self.nodes[node_id].complementarity_score = normalized_comp
            scores[node_id] = normalized_comp
            logger.debug("节点%s互补性得分: %.3f", node_id, normalized_comp)
        
        return scores
    
    def _default_complementarity_calculation(self) -> Dict[str, float]:
        """默认的互补性计算方法(当没有关系矩阵时使用)"""
        scores = {}
        for node_id, node in self.nodes.items():
            # 基于属性差异计算互补性
            attr_diffs = []
            for other_node in self.nodes.values():
                if other_node.id != node_id:
                    diff = self._calculate_attribute_difference(node, other_node)
                    attr_diffs.append(diff)
            
            avg_diff = np.mean(attr_diffs) if attr_diffs else 0
            node.complementarity_score = avg_diff
            scores[node_id] = avg_diff
        
        return scores
    
    def _calculate_attribute_difference(self, node1: Node, node2: Node) -> float:
        """计算两个节点间的属性差异度"""
        common_attrs = set(node1.attributes.keys()) & set(node2.attributes.keys())
        if not common_attrs:
            return 0.0
        
        total_diff = 0.0
        valid_attrs = 0
        
        for attr in common_attrs:
            try:
                val1 = float(node1.attributes[attr])
                val2 = float(node2.attributes[attr])
                
                # 归一化差异
                max_val = max(abs(val1), abs(val2))
                if max_val > 0:
                    diff = abs(val1 - val2) / max_val
                    total_diff += diff
                    valid_attrs += 1
            except (TypeError, ValueError):
                continue
        
        return total_diff / valid_attrs if valid_attrs > 0 else 0.0
    
    def identify_symbiotic_opportunities(
        self,
        min_competency: float = 0.5,
        min_complementarity: float = 0.3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        识别共生机会
        
        找出高互补性的节点对，即使某些节点自身效率不高
        
        Args:
            min_competency: 最低能力得分阈值
            min_complementarity: 最低互补性得分阈值
            
        Returns:
            字典: {
                'high_potential': [(node_id, score), ...],
                'low_competency_high_comp': [(node_id, score), ...]
            }
        """
        opportunities = {
            'high_potential': [],
            'low_competency_high_comp': []
        }
        
        for node_id, node in self.nodes.items():
            if node.complementarity_score >= min_complementarity:
                if node.competency_score >= min_competency:
                    opportunities['high_potential'].append(
                        (node_id, node.complementarity_score)
                    )
                else:
                    opportunities['low_competency_high_comp'].append(
                        (node_id, node.complementarity_score)
                    )
        
        # 按互补性得分排序
        for key in opportunities:
            opportunities[key].sort(key=lambda x: x[1], reverse=True)
        
        logger.info("识别到%d个高潜力节点和%d个低能力高互补节点",
                    len(opportunities['high_potential']),
                    len(opportunities['low_competency_high_comp']))
        
        return opportunities
    
    def generate_recommendations(self) -> List[Dict[str, Union[str, float, List[str]]]]:
        """
        生成合作建议
        
        基于能力得分和互补性分析，生成具体的合作建议
        
        Returns:
            建议列表，每个建议包含节点ID、类型和推荐合作伙伴
        """
        recommendations = []
        
        # 首先计算所有得分
        self.calculate_competency_scores()
        self.calculate_complementarity_scores()
        
        # 识别机会
        opportunities = self.identify_symbiotic_opportunities()
        
        # 为高潜力节点生成建议
        for node_id, score in opportunities['high_potential']:
            partners = self._find_best_partners(node_id)
            recommendations.append({
                'node_id': node_id,
                'type': 'high_potential',
                'complementarity_score': score,
                'recommended_partners': partners
            })
        
        # 为低能力高互补节点生成建议
        for node_id, score in opportunities['low_competency_high_comp']:
            partners = self._find_best_partners(node_id)
            recommendations.append({
                'node_id': node_id,
                'type': 'strategic_support',
                'complementarity_score': score,
                'recommended_partners': partners,
                'note': '节点自身效率低但具有高互补价值，建议重点培养'
            })
        
        return recommendations
    
    def _find_best_partners(
        self,
        node_id: str,
        top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        为给定节点找到最佳合作伙伴
        
        Args:
            node_id: 目标节点ID
            top_n: 返回的最佳合作伙伴数量
            
        Returns:
            列表: [(partner_id, synergy_score), ...]
        """
        if self.relations is None:
            return []
        
        node_idx = list(self.nodes.keys()).index(node_id)
        partners = []
        
        for i, other_id in enumerate(self.nodes.keys()):
            if i != node_idx:
                # 协同得分 = 关系强度 * 互补性
                relation_strength = self.relations[node_idx, i]
                other_comp = self.nodes[other_id].complementarity_score
                synergy = relation_strength * (1 + other_comp)
                partners.append((other_id, synergy))
        
        # 按协同得分排序并返回top_n
        partners.sort(key=lambda x: x[1], reverse=True)
        return partners[:top_n]

# 使用示例
if __name__ == "__main__":
    # 创建示例节点
    nodes = [
        Node("A", {"revenue": 1000, "cost": 500, "market_share": 0.2}),
        Node("B", {"revenue": 800, "cost": 300, "market_share": 0.15}),
        Node("C", {"revenue": 500, "cost": 400, "market_share": 0.05}),  # 低能力高互补
        Node("D", {"revenue": 1200, "cost": 800, "market_share": 0.25})
    ]
    
    # 创建示例关系矩阵 (4x4)
    relations = np.array([
        [1.0, 0.7, 0.8, 0.3],  # A与C有高互补性
        [0.7, 1.0, 0.6, 0.5],
        [0.8, 0.6, 1.0, 0.9],  # C与D有高互补性
        [0.3, 0.5, 0.9, 1.0]
    ])
    
    # 初始化引擎
    engine = SymbioticValueEngine(nodes, relations)
    
    # 计算得分
    competency_scores = engine.calculate_competency_scores()
    complementarity_scores = engine.calculate_complementarity_scores()
    
    # 识别机会
    opportunities = engine.identify_symbiotic_opportunities()
    
    # 生成建议
    recommendations = engine.generate_recommendations()
    
    # 打印结果
    print("\n能力得分:", competency_scores)
    print("\n互补性得分:", complementarity_scores)
    print("\n共生机会:", opportunities)
    print("\n合作建议:", recommendations)