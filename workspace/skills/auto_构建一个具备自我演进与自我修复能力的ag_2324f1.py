"""
模块名称: auto_构建一个具备自我演进与自我修复能力的ag_2324f1
描述: 构建一个具备自我演进与自我修复能力的AGI认知网络。
该架构引入【基于时序衰减与实践反馈的节点活力状态判定】机制，模拟人类记忆的遗忘与巩固过程；
结合【图拓扑结构的节点影响力与脆弱性分析】，识别认知网络中的枢纽节点以防止单点崩溃。
最关键的是，它嵌入了【'人在回路'的贝叶斯纠错更新机制】，当人类对某一节点证伪时，
系统能量化其影响并动态调整网络概率。通过【双向可解释性共生系统】，
人类的决策逻辑也作为数据流反馈给AI，实现真正的认知融合。
"""

import logging
import networkx as nx
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveNetwork:
    """
    认知网络类，实现自我演进与自我修复能力。
    
    属性:
        graph (nx.DiGraph): 有向图结构，存储认知节点及其关系
        node_vitality (Dict[str, float]): 节点活力字典，记录节点的活跃程度
        decay_rate (float): 时序衰减率
        feedback_weight (float): 实践反馈权重
    """
    
    def __init__(self, decay_rate: float = 0.95, feedback_weight: float = 0.1):
        """
        初始化认知网络。
        
        参数:
            decay_rate: 时序衰减率，控制节点活力的自然衰减
            feedback_weight: 实践反馈权重，控制反馈对节点活力的影响
        """
        self.graph = nx.DiGraph()
        self.node_vitality = {}
        self.decay_rate = decay_rate
        self.feedback_weight = feedback_weight
        self._validate_parameters()
        logger.info("认知网络初始化完成，衰减率: %.2f, 反馈权重: %.2f", decay_rate, feedback_weight)
    
    def _validate_parameters(self) -> None:
        """验证输入参数的有效性。"""
        if not (0 < self.decay_rate <= 1):
            raise ValueError("衰减率必须在(0, 1]区间内")
        if not (0 <= self.feedback_weight <= 1):
            raise ValueError("反馈权重必须在[0, 1]区间内")
    
    def add_node(self, node_id: str, initial_vitality: float = 1.0, **attrs) -> None:
        """
        添加认知节点到网络中。
        
        参数:
            node_id: 节点唯一标识符
            initial_vitality: 初始活力值，默认为1.0
            attrs: 节点的其他属性
            
        异常:
            ValueError: 当initial_vitality不在[0, 1]区间时抛出
        """
        if not (0 <= initial_vitality <= 1):
            raise ValueError("初始活力值必须在[0, 1]区间内")
            
        self.graph.add_node(node_id, **attrs)
        self.node_vitality[node_id] = initial_vitality
        logger.debug("添加节点: %s, 初始活力: %.2f", node_id, initial_vitality)
    
    def add_edge(self, source: str, target: str, weight: float = 1.0, **attrs) -> None:
        """
        添加认知关系（边）到网络中。
        
        参数:
            source: 源节点ID
            target: 目标节点ID
            weight: 边权重，默认为1.0
            attrs: 边的其他属性
            
        异常:
            ValueError: 当权重不在[0, 1]区间时抛出
            KeyError: 当源节点或目标节点不存在时抛出
        """
        if not (0 <= weight <= 1):
            raise ValueError("边权重必须在[0, 1]区间内")
        if source not in self.graph or target not in self.graph:
            raise KeyError("源节点或目标节点不存在")
            
        self.graph.add_edge(source, target, weight=weight, **attrs)
        logger.debug("添加边: %s -> %s, 权重: %.2f", source, target, weight)
    
    def update_vitality(self, feedback: Dict[str, float]) -> None:
        """
        基于时序衰减和实践反馈更新节点活力。
        
        参数:
            feedback: 节点ID到反馈值的映射，反馈值应在[-1, 1]区间内
            
        异常:
            ValueError: 当反馈值不在[-1, 1]区间时抛出
        """
        for node_id, fb_value in feedback.items():
            if node_id not in self.node_vitality:
                logger.warning("节点 %s 不存在，跳过反馈更新", node_id)
                continue
                
            if not (-1 <= fb_value <= 1):
                raise ValueError(f"节点 {node_id} 的反馈值必须在[-1, 1]区间内")
                
            # 应用时序衰减
            current_vitality = self.node_vitality[node_id]
            decayed_vitality = current_vitality * self.decay_rate
            
            # 应用实践反馈
            updated_vitality = decayed_vitality + self.feedback_weight * fb_value
            
            # 确保活力值在[0, 1]区间内
            self.node_vitality[node_id] = max(0, min(1, updated_vitality))
            logger.debug("更新节点 %s 活力: %.2f -> %.2f (反馈: %.2f)", 
                        node_id, current_vitality, self.node_vitality[node_id], fb_value)
    
    def analyze_topology(self) -> Dict[str, Dict[str, float]]:
        """
        分析图拓扑结构，识别枢纽节点和脆弱点。
        
        返回:
            包含节点中心性和脆弱性指标的字典
            
        异常:
            RuntimeError: 当网络为空时抛出
        """
        if len(self.graph) == 0:
            raise RuntimeError("网络为空，无法分析拓扑结构")
            
        result = {}
        
        # 计算节点中心性
        try:
            centrality = nx.degree_centrality(self.graph)
        except Exception as e:
            logger.error("计算节点中心性失败: %s", str(e))
            centrality = {}
        
        # 计算节点脆弱性（基于度数和邻居平均活力）
        for node in self.graph.nodes():
            neighbors = list(self.graph.predecessors(node)) + list(self.graph.successors(node))
            if len(neighbors) == 0:
                avg_neighbor_vitality = 0
            else:
                avg_neighbor_vitality = np.mean([self.node_vitality.get(n, 0) for n in neighbors])
            
            # 脆弱性指标：邻居平均活力与自身活力的差异
            vulnerability = abs(avg_neighbor_vitality - self.node_vitality.get(node, 0))
            
            result[node] = {
                "centrality": centrality.get(node, 0),
                "vulnerability": vulnerability
            }
            
            logger.debug("节点 %s - 中心性: %.3f, 脆弱性: %.3f", 
                        node, centrality.get(node, 0), vulnerability)
        
        return result
    
    def human_in_loop_correction(self, node_id: str, evidence: bool, confidence: float = 0.9) -> None:
        """
        人在回路的贝叶斯纠错更新机制。
        
        参数:
            node_id: 需要纠错的节点ID
            evidence: 人类提供的证据，True表示证实，False表示证伪
            confidence: 人类对证据的置信度，应在[0, 1]区间内
            
        异常:
            ValueError: 当置信度不在[0, 1]区间时抛出
            KeyError: 当节点不存在时抛出
        """
        if node_id not in self.node_vitality:
            raise KeyError(f"节点 {node_id} 不存在")
            
        if not (0 <= confidence <= 1):
            raise ValueError("置信度必须在[0, 1]区间内")
            
        current_vitality = self.node_vitality[node_id]
        
        # 简化的贝叶斯更新
        if evidence:  # 证实节点
            updated_vitality = current_vitality + confidence * (1 - current_vitality)
        else:  # 证伪节点
            updated_vitality = current_vitality * (1 - confidence)
        
        self.node_vitality[node_id] = max(0, min(1, updated_vitality))
        logger.info("人在回路纠错 - 节点: %s, 证据: %s, 置信度: %.2f, 更新后活力: %.2f",
                   node_id, "证实" if evidence else "证伪", confidence, self.node_vitality[node_id])
        
        # 影响相邻节点（简化模型）
        for neighbor in self.graph.successors(node_id):
            edge_weight = self.graph.edges[node_id, neighbor].get('weight', 0.5)
            self.node_vitality[neighbor] = max(0, min(1, 
                self.node_vitality[neighbor] + (0.1 * edge_weight * (1 if evidence else -1))
            ))
            logger.debug("传播影响到邻居节点 %s, 新活力: %.2f", neighbor, self.node_vitality[neighbor])
    
    def get_explanation(self, node_id: str) -> Dict[str, Any]:
        """
        双向可解释性共生系统，提供节点决策逻辑的解释。
        
        参数:
            node_id: 需要解释的节点ID
            
        返回:
            包含节点解释信息的字典
            
        异常:
            KeyError: 当节点不存在时抛出
        """
        if node_id not in self.node_vitality:
            raise KeyError(f"节点 {node_id} 不存在")
            
        explanation = {
            "node_id": node_id,
            "vitality": self.node_vitality[node_id],
            "neighbors": {
                "predecessors": list(self.graph.predecessors(node_id)),
                "successors": list(self.graph.successors(node_id))
            },
            "attributes": self.graph.nodes[node_id]
        }
        
        # 添加拓扑分析结果
        try:
            topo_analysis = self.analyze_topology()
            explanation["topology"] = topo_analysis[node_id]
        except Exception as e:
            logger.warning("无法获取拓扑分析: %s", str(e))
            explanation["topology"] = None
        
        logger.debug("生成节点 %s 的解释: %s", node_id, explanation)
        return explanation

# 使用示例
if __name__ == "__main__":
    try:
        # 创建认知网络
        network = CognitiveNetwork(decay_rate=0.9, feedback_weight=0.15)
        
        # 添加节点
        network.add_node("concept_1", initial_vitality=0.8, description="基础概念")
        network.add_node("concept_2", initial_vitality=0.6, description="进阶概念")
        network.add_node("concept_3", initial_vitality=0.7, description="高级概念")
        
        # 添加边
        network.add_edge("concept_1", "concept_2", weight=0.7, relation="依赖")
        network.add_edge("concept_2", "concept_3", weight=0.8, relation="扩展")
        
        # 模拟实践反馈
        feedback = {"concept_1": 0.3, "concept_2": -0.1}
        network.update_vitality(feedback)
        
        # 人在回路纠错
        network.human_in_loop_correction("concept_1", evidence=False, confidence=0.8)
        
        # 获取解释
        explanation = network.get_explanation("concept_1")
        print("节点解释:", explanation)
        
        # 拓扑分析
        analysis = network.analyze_topology()
        print("拓扑分析结果:", analysis)
        
    except Exception as e:
        logger.error("运行示例时发生错误: %s", str(e), exc_info=True)