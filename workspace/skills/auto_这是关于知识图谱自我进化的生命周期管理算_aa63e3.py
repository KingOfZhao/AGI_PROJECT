"""
模块名称: auto_这是关于知识图谱自我进化的生命周期管理算_aa63e3
描述: 实现基于生物代谢模型的知识图谱动态演化系统
作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import networkx as nx
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import defaultdict
from datetime import datetime
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeGraphMetabolism:
    """
    知识图谱自我进化生命周期管理系统
    
    通过模拟生物新陈代谢机制实现知识图谱的动态演化：
    - 合成代谢: 从碎片数据中发现并合成新知识节点
    - 分解代谢: 识别并清理过时或低价值节点
    
    Attributes:
        graph (nx.DiGraph): 知识图谱有向图结构
        node_metadata (Dict): 节点元数据存储
        config (Dict): 系统配置参数
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化知识图谱代谢系统
        
        Args:
            config: 系统配置参数，包含:
                - anabolism_threshold: 合成代谢阈值 (默认: 0.7)
                - catabolism_threshold: 分解代谢阈值 (默认: 0.3)
                - stability_factor: 稳定性因子 (默认: 0.85)
                - max_node_age: 最大节点年龄(天) (默认: 365)
        """
        self.graph = nx.DiGraph()
        self.node_metadata = defaultdict(dict)
        
        # 默认配置
        self.config = {
            'anabolism_threshold': 0.7,
            'catabolism_threshold': 0.3,
            'stability_factor': 0.85,
            'max_node_age': 365,
            'min_confidence': 0.5,
            'co_occurrence_window': 3
        }
        
        if config:
            self._validate_config(config)
            self.config.update(config)
            
        logger.info("KnowledgeGraphMetabolism initialized with config: %s", self.config)
    
    def _validate_config(self, config: Dict) -> None:
        """验证配置参数有效性"""
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")
            
        if 'anabolism_threshold' in config and not 0 < config['anabolism_threshold'] < 1:
            raise ValueError("anabolism_threshold must be between 0 and 1")
            
        if 'catabolism_threshold' in config and not 0 < config['catabolism_threshold'] < 1:
            raise ValueError("catabolism_threshold must be between 0 and 1")
            
        if 'max_node_age' in config and config['max_node_age'] <= 0:
            raise ValueError("max_node_age must be positive")
    
    def _calculate_node_stability(self, node: str) -> float:
        """
        计算节点稳定性分数
        
        基于节点年龄、连接度和置信度计算稳定性
        
        Args:
            node: 节点ID
            
        Returns:
            float: 稳定性分数 (0-1)
        """
        if node not in self.graph:
            logger.warning("Node %s not found in graph", node)
            return 0.0
            
        metadata = self.node_metadata[node]
        age_days = (datetime.now() - metadata.get('created_at', datetime.now())).days
        max_age = self.config['max_node_age']
        
        # 年龄因子: 越老越稳定 (但不超过1)
        age_factor = min(age_days / max_age, 1.0)
        
        # 连接度因子: 连接越多越稳定
        degree = self.graph.degree(node)
        max_degree = max(dict(self.graph.degree()).values()) if self.graph.number_of_nodes() > 0 else 1
        degree_factor = degree / max_degree if max_degree > 0 else 0
        
        # 综合稳定性计算
        stability = (0.6 * age_factor + 0.4 * degree_factor) * metadata.get('confidence', 0.5)
        return min(max(stability, 0), 1)
    
    def anabolism_process(self, data_fragments: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        合成代谢过程: 从碎片数据中创建新节点
        
        通过高频共现分析识别潜在新知识节点，并评估对现有图谱的稳定性影响
        
        Args:
            data_fragments: 碎片数据列表，每个碎片包含:
                - content: 文本内容
                - timestamp: 时间戳
                - source: 数据源
                
        Returns:
            Tuple[int, int]: (成功创建的新节点数, 被拒绝的潜在节点数)
        """
        if not data_fragments:
            logger.warning("Empty data fragments provided")
            return 0, 0
            
        # 步骤1: 共现分析识别潜在节点
        potential_nodes = self._identify_potential_nodes(data_fragments)
        
        # 步骤2: 阻力检测评估稳定性影响
        created_nodes = 0
        rejected_nodes = 0
        
        for node_info in potential_nodes:
            node_id = node_info['id']
            confidence = node_info['confidence']
            
            # 计算阻力指数 (影响现有高置信度节点的程度)
            resistance = self._calculate_resistance(node_id)
            
            # 决策逻辑: 高置信度新节点且低阻力则接受
            if confidence >= self.config['anabolism_threshold'] and resistance < self.config['stability_factor']:
                self._create_node(node_id, node_info)
                created_nodes += 1
                logger.info("Created new node %s with confidence %.2f", node_id, confidence)
            else:
                rejected_nodes += 1
                logger.debug("Rejected node %s (confidence %.2f, resistance %.2f)", 
                           node_id, confidence, resistance)
                
        return created_nodes, rejected_nodes
    
    def catabolism_process(self) -> int:
        """
        分解代谢过程: 清理过时或低价值节点
        
        识别并移除:
        1. 超过最大年龄的低活跃节点
        2. 置信度低于阈值的休眠节点
        3. 孤立且无价值的节点
        
        Returns:
            int: 移除的节点数
        """
        nodes_to_remove = []
        
        for node in list(self.graph.nodes()):
            metadata = self.node_metadata[node]
            age_days = (datetime.now() - metadata.get('created_at', datetime.now())).days
            confidence = metadata.get('confidence', 0)
            degree = self.graph.degree(node)
            
            # 分解代谢条件
            if (age_days > self.config['max_node_age'] and degree < 2) or \
               (confidence < self.config['catabolism_threshold'] and degree == 0) or \
               (self._is_dormant(node)):
                nodes_to_remove.append(node)
        
        # 执行节点移除
        for node in nodes_to_remove:
            self._remove_node(node)
            logger.info("Removed node %s through catabolism process", node)
            
        return len(nodes_to_remove)
    
    def _identify_potential_nodes(self, fragments: List[Dict]) -> List[Dict]:
        """
        识别潜在新节点 (内部辅助函数)
        
        通过共现分析和聚类识别潜在知识节点
        
        Args:
            fragments: 数据碎片列表
            
        Returns:
            List[Dict]: 潜在节点列表
        """
        # 实现简化的共现分析
        term_counts = defaultdict(int)
        term_pairs = defaultdict(int)
        
        for fragment in fragments:
            content = fragment.get('content', '')
            terms = self._extract_terms(content)
            
            # 统计单个术语频率
            for term in terms:
                term_counts[term] += 1
                
            # 统计术语共现
            for i in range(len(terms)):
                for j in range(i+1, min(i+self.config['co_occurrence_window'], len(terms))):
                    pair = tuple(sorted([terms[i], terms[j]]))
                    term_pairs[pair] += 1
        
        # 识别高频术语和共现作为潜在节点
        potential_nodes = []
        total_fragments = len(fragments)
        
        for term, count in term_counts.items():
            if total_fragments > 0 and count / total_fragments >= self.config['anabolism_threshold']:
                # 计算节点置信度 (基于出现频率)
                confidence = min(count / total_fragments, 1.0)
                
                # 查找关联术语
                related_terms = []
                for (t1, t2), pair_count in term_pairs.items():
                    if term in (t1, t2) and pair_count / total_fragments >= self.config['anabolism_threshold']:
                        related_term = t2 if t1 == term else t1
                        related_terms.append(related_term)
                
                potential_nodes.append({
                    'id': term,
                    'confidence': confidence,
                    'related_terms': related_terms,
                    'created_at': datetime.now()
                })
        
        return potential_nodes
    
    def _calculate_resistance(self, new_node: str) -> float:
        """
        计算新节点对现有图谱的阻力指数
        
        评估新节点引入对高置信度节点稳定性的潜在影响
        
        Args:
            new_node: 新节点ID
            
        Returns:
            float: 阻力指数 (0-1)
        """
        if not self.graph.nodes():
            return 0.0
            
        # 模拟: 检查新节点与现有高置信度节点的潜在连接
        high_confidence_nodes = [
            node for node in self.graph.nodes()
            if self.node_metadata[node].get('confidence', 0) >= self.config['min_confidence']
        ]
        
        if not high_confidence_nodes:
            return 0.0
            
        # 计算与高置信度节点的潜在冲突 (简化实现)
        conflicts = 0
        for node in high_confidence_nodes:
            # 这里可以添加更复杂的冲突检测逻辑
            if self._has_potential_conflict(new_node, node):
                conflicts += 1
                
        return conflicts / len(high_confidence_nodes)
    
    def _has_potential_conflict(self, node1: str, node2: str) -> bool:
        """检查两个节点是否存在潜在冲突 (简化实现)"""
        # 实际实现可能包括语义相似度检查、领域重叠分析等
        return False
    
    def _is_dormant(self, node: str) -> bool:
        """检查节点是否处于休眠状态 (无活跃连接)"""
        metadata = self.node_metadata[node]
        last_accessed = metadata.get('last_accessed', datetime.now())
        inactive_days = (datetime.now() - last_accessed).days
        
        return inactive_days > 30 and self.graph.degree(node) == 0
    
    def _create_node(self, node_id: str, node_info: Dict) -> None:
        """创建新节点并添加到图谱"""
        self.graph.add_node(node_id)
        self.node_metadata[node_id] = {
            'created_at': node_info.get('created_at', datetime.now()),
            'confidence': node_info.get('confidence', 0.5),
            'last_accessed': datetime.now(),
            'source': 'anabolism_process'
        }
        
        # 创建与相关术语的连接
        for related_term in node_info.get('related_terms', []):
            self.graph.add_edge(node_id, related_term, weight=0.7)
    
    def _remove_node(self, node: str) -> None:
        """从图谱中移除节点"""
        self.graph.remove_node(node)
        self.node_metadata.pop(node, None)
    
    def _extract_terms(self, text: str) -> List[str]:
        """从文本中提取术语 (简化实现)"""
        # 实际实现可能包括NLP处理、术语识别等
        if not text:
            return []
        return list(set(text.lower().split()))
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'avg_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0,
            'high_confidence_nodes': len([
                n for n in self.graph.nodes()
                if self.node_metadata[n].get('confidence', 0) >= self.config['min_confidence']
            ])
        }

# 使用示例
if __name__ == "__main__":
    # 示例1: 初始化系统
    kgs = KnowledgeGraphMetabolism(config={
        'anabolism_threshold': 0.6,
        'catabolism_threshold': 0.25
    })
    
    # 示例2: 合成代谢过程
    fragments = [
        {"content": "AI artificial intelligence machine learning", "source": "doc1"},
        {"content": "machine learning deep learning neural networks", "source": "doc2"},
        {"content": "neural networks artificial intelligence applications", "source": "doc3"}
    ]
    
    created, rejected = kgs.anabolism_process(fragments)
    print(f"Created {created} nodes, rejected {rejected} nodes")
    
    # 示例3: 分解代谢过程
    removed = kgs.catabolism_process()
    print(f"Removed {removed} nodes")
    
    # 示例4: 获取图谱统计
    stats = kgs.get_graph_statistics()
    print("Graph statistics:", stats)