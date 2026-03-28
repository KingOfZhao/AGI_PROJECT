"""
Module: belief_radar.py
Description: 建立'信念溯源与证伪雷达'。
             在人机共生中，本模块不仅存储结论，更严格存储'认知路径'。
             支持溯源、证伪触发以及全链路'认知自愈'（级联更新）。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ContextData:
    """环境与情绪上下文数据结构"""
    timestamp: str
    user_emotion: str  # e.g., 'neutral', 'anxious', 'confident'
    env_tags: List[str]  # e.g., ['high_pressure', 'market_volatility']

@dataclass
class BeliefNode:
    """
    信念节点数据结构。
    包含结论、来源、推理逻辑及上下文。
    """
    belief_id: str
    content: str
    status: str = "active"  # active, deprecated, debunked
    source_ids: List[str] = field(default_factory=list)  # 数据源头 (Data Lineage)
    logic_chain: List[str] = field(default_factory=list) # 推理逻辑 (ETL steps)
    context: Optional[Dict[str, Any]] = None # 当时的环境变量/情绪
    derived_beliefs: Set[str] = field(default_factory=set) # 衍生出的子信念ID
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典以便序列化"""
        return asdict(self)

class BeliefRadarSystem:
    """
    信念溯源与证伪雷达系统。
    
    负责管理信念的生命周期，包括基于数据谱系的溯源、
    自动化的证伪检测以及级联式的认知自愈。
    
    Usage Example:
        >>> radar = BeliefRadarSystem()
        >>> # 1. 录入原始信念
        >>> b1 = radar.add_belief(
        ...     content="Project A will succeed", 
        ...     source_ids=["data_point_1"], 
        ...     logic=["infer_success_from_metrics"]
        ... )
        >>> # 2. 基于b1建立衍生信念
        >>> b2 = radar.add_belief(
        ...     content="Increase budget for Project A", 
        ...     source_ids=[b1.belief_id], 
        ...     logic=["derive_budget_strategy"]
        ... )
        >>> # 3. 模拟源头证伪
        >>> radar.report_source_compromised("data_point_1", "Sensor malfunction")
        >>> # 4. 检查结果
        >>> assert radar.get_belief(b2.belief_id).status == 'debunked'
    """

    def __init__(self):
        self.belief_graph: Dict[str, BeliefNode] = {}
        self.source_index: Dict[str, Set[str]] = {} # 映射: source_id -> set(belief_ids)
        logger.info("BeliefRadarSystem initialized. Cognitive Radar online.")

    def _generate_id(self, content: str) -> str:
        """辅助函数：生成唯一的信念ID"""
        return hashlib.md5((content + datetime.now().isoformat()).encode()).hexdigest()[:12]

    def add_belief(
        self, 
        content: str, 
        source_ids: List[str], 
        logic_chain: List[str],
        context: Optional[Dict] = None
    ) -> BeliefNode:
        """
        核心函数：添加一个新的信念节点到认知图谱中。
        
        Args:
            content (str): 信念的具体内容/结论。
            source_ids (List[str]): 该信念依赖的源头（可以是原始数据ID或其他信念ID）。
            logic_chain (List[str]): 推理过程描述（ETL逻辑）。
            context (Optional[Dict]): 生成该信念时的环境上下文。
            
        Returns:
            BeliefNode: 创建成功的信念节点。
            
        Raises:
            ValueError: 如果输入数据无效。
        """
        if not content or not isinstance(content, str):
            logger.error("Invalid content provided for belief.")
            raise ValueError("Content must be a non-empty string.")
        
        if not source_ids:
            logger.warning(f"Creating belief '{content}' without sources. May lack traceability.")

        b_id = self._generate_id(content)
        
        # 构建上下文
        final_context = context if context else {}
        final_context['timestamp'] = datetime.now().isoformat()
        
        node = BeliefNode(
            belief_id=b_id,
            content=content,
            source_ids=source_ids,
            logic_chain=logic_chain,
            context=final_context
        )
        
        self.belief_graph[b_id] = node
        
        # 更新反向索引，记录谁依赖了这些源头
        for src in source_ids:
            if src not in self.source_index:
                self.source_index[src] = set()
            self.source_index[src].add(b_id)
            
        # 如果source_ids包含其他信念ID，更新父信念的衍生记录
        for src in source_ids:
            if src in self.belief_graph:
                parent_node = self.belief_graph[src]
                parent_node.derived_beliefs.add(b_id)
                
        logger.info(f"New Belief Anchored: ID={b_id} | Content='{content}'")
        return node

    def trace_lineage(self, belief_id: str) -> Dict[str, Any]:
        """
        核心函数：溯源。
        回溯指定信念的完整认知路径、源头和逻辑链。
        
        Args:
            belief_id (str): 目标信念ID。
            
        Returns:
            Dict[str, Any]: 包含完整血缘关系的树状结构。
        """
        if belief_id not in self.belief_graph:
            logger.error(f"Trace failed: Belief {belief_id} not found.")
            return {"error": "Belief not found"}

        logger.info(f"Initiating trace for belief {belief_id}...")
        visited = set()
        path = self._recursive_trace(belief_id, visited)
        return path

    def _recursive_trace(self, current_id: str, visited: Set[str]) -> Dict[str, Any]:
        """辅助函数：递归构建溯源树"""
        if current_id in visited:
            return {"cycle_detected": current_id}
        
        visited.add(current_id)
        node = self.belief_graph.get(current_id)
        
        if not node:
            return {"external_source": current_id}

        tree = {
            "id": current_id,
            "content": node.content,
            "logic": node.logic_chain,
            "status": node.status,
            "context": node.context,
            "sources": []
        }
        
        for src_id in node.source_ids:
            tree["sources"].append(self._recursive_trace(src_id, visited))
            
        return tree

    def report_source_compromised(self, source_id: str, reason: str) -> List[str]:
        """
        证伪触发与认知自愈。
        当一个源头被证伪时，触发全链路级联更新。
        
        Args:
            source_id (str): 被证伪的源头ID（数据点或原始信念）。
            reason (str): 证伪原因。
            
        Returns:
            List[str]: 受到影响（被修正/标记为失效）的信念ID列表。
        """
        if source_id not in self.source_index:
            logger.warning(f"Source {source_id} not tracked in index. No impact.")
            return []

        logger.critical(f"⚠️ ALERT: Source {source_id} COMPROMISED. Reason: {reason}. Initiating Cascade Update...")
        
        affected_nodes = []
        queue = list(self.source_index.get(source_id, set()))
        
        # 广度优先搜索处理级联失效
        while queue:
            current_b_id = queue.pop(0)
            
            if current_b_id not in self.belief_graph:
                continue
                
            node = self.belief_graph[current_b_id]
            
            # 只有当前活跃的信念才需要处理
            if node.status == "active":
                node.status = "debunked"
                node.context = node.context or {}
                node.context["debunk_reason"] = reason
                node.context["debunk_time"] = datetime.now().isoformat()
                
                affected_nodes.append(current_b_id)
                logger.info(f" -> Belief '{current_b_id}' auto-updated to 'debunked'.")
                
                # 将该信念的衍生信念加入队列继续传播
                if current_b_id in self.source_index:
                    queue.extend(self.source_index[current_b_id])
        
        logger.info(f"Cognitive Self-Healing Complete. Total beliefs updated: {len(affected_nodes)}")
        return affected_nodes

    def get_belief(self, belief_id: str) -> Optional[BeliefNode]:
        """获取信念对象"""
        return self.belief_graph.get(belief_id)

# 示例用法与测试
if __name__ == "__main__":
    # 初始化雷达系统
    radar = BeliefRadarSystem()
    
    # 场景：基于一份市场报告建立信念链
    # 1. 原始数据录入 (Data Lineage Start)
    raw_data_node = radar.add_belief(
        content="Raw Data: Q3 Sales increased by 20%",
        source_ids=["external_api_feed_01"],
        logic_chain=["data_ingestion"],
        context={"emotion": "neutral", "env": "monthly_report_gen"}
    )
    
    # 2. 中间推理
    mid_analysis = radar.add_belief(
        content="Analysis: Market demand is surging",
        source_ids=[raw_data_node.belief_id],
        logic_chain=["statistical_analysis", "trend_fitting"],
        context={"emotion": "optimistic"}
    )
    
    # 3. 最终决策建议
    action_plan = radar.add_belief(
        content="Decision: Increase inventory by 30%",
        source_ids=[mid_analysis.belief_id],
        logic_chain=["strategy_generation", "risk_assessment"],
        context={"emotion": "confident", "env": "board_meeting_prep"}
    )
    
    print("\n--- Traceability Check ---")
    lineage = radar.trace_lineage(action_plan.belief_id)
    print(json.dumps(lineage, indent=2))
    
    print("\n--- Simulating Source Compromise ---")
    # 模拟：发现 external_api_feed_01 是被黑客篡改的虚假数据
    impacted = radar.report_source_compromised("external_api_feed_01", "Data provenance failed: Tampered feed detected")
    
    print(f"\nImpacted Belief IDs: {impacted}")
    print(f"Final Decision Status: {radar.get_belief(action_plan.belief_id).status}")