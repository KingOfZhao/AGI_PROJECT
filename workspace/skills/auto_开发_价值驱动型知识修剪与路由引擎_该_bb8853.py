"""
价值驱动型知识修剪与路由引擎

该模块实现了一个模拟生物突触修剪机制的智能系统，用于优化大规模分布式知识图谱。
通过实时监控知识节点的调用频率和成功率（多巴胺奖励信号），系统能够动态调整资源分配：
- 自动降权或归档长期未使用的"僵尸节点"
- 强化高频使用且高成功率的"核心节点"
- 实现认知资源的动态优化配置

输入格式:
    知识节点数据: Dict[str, Dict] 包含节点ID和属性
    信号流数据: List[Dict] 包含节点交互记录

输出格式:
    修剪报告: Dict 包含节点状态变更和系统优化建议
    路由表: Dict[str, float] 节点权重映射表

示例:
    >>> engine = KnowledgePruningEngine()
    >>> engine.load_knowledge_graph(sample_nodes)
    >>> report = engine.process_signals(interaction_logs)
    >>> print(engine.generate_routing_table())
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KnowledgePruningEngine")

@dataclass
class KnowledgeNode:
    """知识节点数据结构"""
    node_id: str
    content: str
    creation_time: datetime
    last_accessed: datetime
    access_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    base_weight: float = 1.0
    current_weight: float = 1.0
    status: str = "active"  # active/dormant/archived
    
    def calculate_success_rate(self) -> float:
        """计算节点成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def calculate_activity_score(self) -> float:
        """计算活动分数，综合考虑访问频率和成功率"""
        freq_score = math.log1p(self.access_count)
        success_rate = self.calculate_success_rate()
        return freq_score * success_rate * self.base_weight


class KnowledgePruningEngine:
    """价值驱动型知识修剪与路由引擎"""
    
    def __init__(self, 
                 decay_rate: float = 0.95, 
                 pruning_threshold: float = 0.1,
                 archive_threshold: float = 0.05,
                 time_window: int = 30):
        """
        初始化知识修剪引擎
        
        参数:
            decay_rate: 权重衰减率 (0-1)
            pruning_threshold: 修剪阈值 (0-1)
            archive_threshold: 归档阈值 (0-1)
            time_window: 分析时间窗口(天)
        """
        self._validate_init_params(decay_rate, pruning_threshold, archive_threshold, time_window)
        
        self.decay_rate = decay_rate
        self.pruning_threshold = pruning_threshold
        self.archive_threshold = archive_threshold
        self.time_window = timedelta(days=time_window)
        
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.routing_table: Dict[str, float] = {}
        self.pruning_history: List[Dict] = []
        self._initialized_at = datetime.now()
        
        logger.info(f"KnowledgePruningEngine initialized with decay_rate={decay_rate}, "
                   f"pruning_threshold={pruning_threshold}")
    
    def _validate_init_params(self, decay_rate: float, pruning_threshold: float, 
                             archive_threshold: float, time_window: int) -> None:
        """验证初始化参数"""
        if not 0 < decay_rate <= 1:
            raise ValueError("Decay rate must be in range (0, 1]")
        if not 0 <= pruning_threshold <= 1:
            raise ValueError("Pruning threshold must be in range [0, 1]")
        if not 0 <= archive_threshold <= pruning_threshold:
            raise ValueError("Archive threshold must be in [0, pruning_threshold]")
        if time_window <= 0:
            raise ValueError("Time window must be positive integer")
    
    def load_knowledge_graph(self, nodes: Dict[str, Dict]) -> None:
        """
        加载知识图谱数据
        
        参数:
            nodes: 知识节点字典 {node_id: {attributes}}
        
        异常:
            ValueError: 如果节点数据格式无效
        """
        if not nodes:
            logger.warning("Empty knowledge graph loaded")
            return
            
        processed = 0
        for node_id, attrs in nodes.items():
            try:
                # 数据验证
                if not isinstance(attrs, dict):
                    raise ValueError(f"Invalid node attributes for {node_id}")
                
                # 解析时间字段
                creation_time = self._parse_datetime(attrs.get('creation_time'))
                last_accessed = self._parse_datetime(attrs.get('last_accessed', creation_time))
                
                # 创建知识节点
                node = KnowledgeNode(
                    node_id=node_id,
                    content=attrs.get('content', ''),
                    creation_time=creation_time,
                    last_accessed=last_accessed,
                    access_count=int(attrs.get('access_count', 0)),
                    success_count=int(attrs.get('success_count', 0)),
                    failure_count=int(attrs.get('failure_count', 0)),
                    base_weight=float(attrs.get('base_weight', 1.0)),
                    status=attrs.get('status', 'active')
                )
                node.current_weight = node.base_weight
                
                self.knowledge_graph[node_id] = node
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process node {node_id}: {str(e)}")
                continue
                
        logger.info(f"Loaded {processed}/{len(nodes)} nodes into knowledge graph")
        self._update_routing_table()
    
    def _parse_datetime(self, dt_input: any) -> datetime:
        """解析日期时间输入"""
        if isinstance(dt_input, datetime):
            return dt_input
        elif isinstance(dt_input, str):
            return datetime.fromisoformat(dt_input)
        else:
            return datetime.now()
    
    def process_signals(self, signals: List[Dict]) -> Dict:
        """
        处理交互信号流，更新节点状态并执行修剪
        
        参数:
            signals: 交互信号列表 [{node_id, success, timestamp}]
        
        返回:
            处理报告字典
        
        异常:
            ValueError: 如果信号数据格式无效
        """
        if not signals:
            logger.warning("Empty signal list received")
            return {"processed": 0, "pruned": 0, "archived": 0}
            
        report = {
            "processed": 0,
            "pruned": 0,
            "archived": 0,
            "activated": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 按时间排序信号
        sorted_signals = sorted(signals, key=lambda x: x.get('timestamp', ''))
        
        for signal in sorted_signals:
            try:
                node_id = signal.get('node_id')
                if not node_id or node_id not in self.knowledge_graph:
                    continue
                    
                node = self.knowledge_graph[node_id]
                success = bool(signal.get('success', False))
                timestamp = self._parse_datetime(signal.get('timestamp'))
                
                # 更新节点统计
                node.access_count += 1
                if success:
                    node.success_count += 1
                else:
                    node.failure_count += 1
                
                node.last_accessed = timestamp
                report["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing signal {signal}: {str(e)}")
                continue
        
        # 执行修剪操作
        pruned, archived, activated = self._perform_pruning()
        report.update({
            "pruned": pruned,
            "archived": archived,
            "activated": activated
        })
        
        self.pruning_history.append(report)
        self._update_routing_table()
        return report
    
    def _perform_pruning(self) -> Tuple[int, int, int]:
        """
        执行修剪操作，返回修剪、归档和激活的节点数量
        
        返回:
            Tuple[int, int, int]: (pruned_count, archived_count, activated_count)
        """
        pruned_count = 0
        archived_count = 0
        activated_count = 0
        now = datetime.now()
        
        for node_id, node in self.knowledge_graph.items():
            # 计算时间衰减因子
            time_since_access = (now - node.last_accessed).total_seconds()
            decay_factor = self.decay_rate ** (time_since_access / (24 * 3600))  # 每天衰减
            
            # 计算活动分数
            activity_score = node.calculate_activity_score() * decay_factor
            
            # 状态转换逻辑
            if node.status == "active":
                if activity_score < self.archive_threshold:
                    node.status = "archived"
                    archived_count += 1
                    logger.info(f"Archived node {node_id} (score: {activity_score:.4f})")
                elif activity_score < self.pruning_threshold:
                    node.status = "dormant"
                    pruned_count += 1
                    logger.debug(f"Pruned node {node_id} (score: {activity_score:.4f})")
                    
            elif node.status == "dormant":
                if activity_score >= self.pruning_threshold:
                    node.status = "active"
                    activated_count += 1
                    logger.info(f"Reactivated node {node_id} (score: {activity_score:.4f})")
                elif activity_score < self.archive_threshold:
                    node.status = "archived"
                    archived_count += 1
                    logger.info(f"Archived node {node_id} (score: {activity_score:.4f})")
                    
            elif node.status == "archived":
                if activity_score >= self.pruning_threshold:
                    node.status = "active"
                    activated_count += 1
                    logger.info(f"Restored node {node_id} (score: {activity_score:.4f})")
            
            # 更新节点权重
            node.current_weight = activity_score
        
        return pruned_count, archived_count, activated_count
    
    def _update_routing_table(self) -> None:
        """更新路由表，基于当前节点权重"""
        self.routing_table = {
            node_id: node.current_weight 
            for node_id, node in self.knowledge_graph.items() 
            if node.status == "active"
        }
        
        # 归一化权重
        total = sum(self.routing_table.values())
        if total > 0:
            self.routing_table = {
                k: v/total for k, v in self.routing_table.items()
            }
    
    def generate_routing_table(self) -> Dict[str, float]:
        """
        生成当前的路由表
        
        返回:
            Dict[str, float]: 节点ID到权重值的映射
        """
        return self.routing_table.copy()
    
    def get_node_status(self, node_id: str) -> Optional[Dict]:
        """
        获取节点状态详情
        
        参数:
            node_id: 节点ID
            
        返回:
            节点状态字典，如果节点不存在则返回None
        """
        node = self.knowledge_graph.get(node_id)
        if not node:
            return None
            
        return {
            "node_id": node.node_id,
            "status": node.status,
            "current_weight": node.current_weight,
            "access_count": node.access_count,
            "success_rate": node.calculate_success_rate(),
            "last_accessed": node.last_accessed.isoformat(),
            "activity_score": node.calculate_activity_score()
        }
    
    def get_pruning_report(self) -> List[Dict]:
        """获取修剪历史报告"""
        return self.pruning_history.copy()


# 示例用法
if __name__ == "__main__":
    # 示例知识节点数据
    sample_nodes = {
        "node1": {
            "content": "机器学习基础知识",
            "creation_time": "2023-01-01T00:00:00",
            "access_count": 100,
            "success_count": 90,
            "failure_count": 10,
            "status": "active"
        },
        "node2": {
            "content": "过时的算法",
            "creation_time": "2022-01-01T00:00:00",
            "access_count": 5,
            "success_count": 1,
            "failure_count": 4,
            "status": "active"
        }
    }
    
    # 示例交互信号
    sample_signals = [
        {"node_id": "node1", "success": True, "timestamp": "2023-10-01T10:00:00"},
        {"node_id": "node1", "success": True, "timestamp": "2023-10-01T11:00:00"},
        {"node_id": "node2", "success": False, "timestamp": "2023-10-01T12:00:00"},
    ]
    
    # 初始化并运行引擎
    engine = KnowledgePruningEngine()
    engine.load_knowledge_graph(sample_nodes)
    report = engine.process_signals(sample_signals)
    
    print("\nPruning Report:")
    print(report)
    
    print("\nRouting Table:")
    for node_id, weight in engine.generate_routing_table().items():
        print(f"{node_id}: {weight:.4f}")
    
    print("\nNode Status:")
    print(engine.get_node_status("node1"))