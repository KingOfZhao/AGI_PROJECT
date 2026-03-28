"""
变奏式知识演化系统

本模块实现了一个创新的知识管理系统，通过"变奏"机制复活长期未被调用的知识节点。
系统不直接删除低频使用的节点，而是提取其核心逻辑结构（动机），在新上下文中测试其适用性。

核心功能:
- 识别长期未调用的知识节点
- 提取节点的逻辑骨架（抽象核心模式）
- 在新上下文中进行变奏测试
- 成功变奏的节点获得"普适性权重"提升

数据流:
输入 -> 知识图谱 -> 长期未用节点检测 -> 逻辑抽象 -> 变奏测试 -> 更新节点状态

示例:
>>> system = VariationKnowledgeSystem()
>>> system.add_knowledge_node("node1", {"type": "protocol", "pattern": "timeout_retry"})
>>> system.perform_variation_cycle()
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from uuid import uuid4

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("knowledge_variation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("VariationKnowledgeSystem")


@dataclass
class KnowledgeNode:
    """知识节点数据结构"""
    node_id: str
    content: Dict[str, Any]
    creation_time: datetime = field(default_factory=datetime.now)
    last_invoked: datetime = field(default_factory=datetime.now)
    invoke_count: int = 0
    variation_score: float = 0.0  # 变奏适应性得分
    abstracted_core: Optional[str] = None  # 抽象后的逻辑骨架
    active: bool = True
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """初始化后处理"""
        if not isinstance(self.tags, set):
            self.tags = set(self.tags)


class VariationKnowledgeSystem:
    """
    变奏式知识演化系统主类
    
    实现知识节点的生命周期管理，特别关注长期未调用节点的复活机制。
    通过变奏测试，将旧知识迁移到新上下文中，实现知识的跨域应用。
    """
    
    def __init__(self, inactivity_threshold_days: int = 30):
        """
        初始化变奏式知识演化系统
        
        Args:
            inactivity_threshold_days: 节点被认为"长期未调用"的天数阈值
        """
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.inactivity_threshold = timedelta(days=inactivity_threshold_days)
        self.variation_history: List[Dict[str, Any]] = []
        self._initialize_core_patterns()
        
    def _initialize_core_patterns(self) -> None:
        """初始化核心抽象模式库"""
        self.core_patterns = {
            "retry": {
                "description": "重试机制模式",
                "abstraction": "当操作失败时，按策略重复尝试",
                "applicable_domains": ["network", "api", "database", "io"],
                "structure": ["failure_detection", "backoff_strategy", "max_attempts"]
            },
            "fallback": {
                "description": "降级备选模式",
                "abstraction": "主路径失败时切换到备选路径",
                "applicable_domains": ["service", "algorithm", "resource"],
                "structure": ["primary_path", "fallback_path", "switch_condition"]
            },
            "cache": {
                "description": "缓存模式",
                "abstraction": "存储计算结果以避免重复计算",
                "applicable_domains": ["computation", "data_retrieval", "rendering"],
                "structure": ["storage", "invalidation", "hit_detection"]
            },
            "state_machine": {
                "description": "状态机模式",
                "abstraction": "根据状态转换规则响应事件",
                "applicable_domains": ["protocol", "workflow", "game_logic"],
                "structure": ["states", "transitions", "events"]
            }
        }
        logger.info(f"Initialized {len(self.core_patterns)} core patterns")
    
    def add_knowledge_node(
        self,
        node_id: Optional[str],
        content: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> str:
        """
        添加知识节点到系统
        
        Args:
            node_id: 节点唯一标识，如果为None则自动生成
            content: 节点内容字典，包含知识的具体信息
            tags: 节点标签列表，用于分类和检索
            
        Returns:
            str: 新创建的节点ID
            
        Raises:
            ValueError: 如果内容为空或node_id已存在
        """
        if not content:
            raise ValueError("Node content cannot be empty")
            
        if node_id is None:
            node_id = str(uuid4())
        elif node_id in self.knowledge_graph:
            raise ValueError(f"Node {node_id} already exists")
            
        # 数据验证
        validated_content = self._validate_content(content)
        
        node = KnowledgeNode(
            node_id=node_id,
            content=validated_content,
            tags=set(tags) if tags else set()
        )
        
        self.knowledge_graph[node_id] = node
        logger.info(f"Added knowledge node: {node_id} with tags: {tags}")
        return node_id
    
    def _validate_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并清理节点内容
        
        Args:
            content: 原始内容字典
            
        Returns:
            Dict[str, Any]: 验证后的内容
            
        Raises:
            TypeError: 如果content不是字典
        """
        if not isinstance(content, dict):
            raise TypeError("Content must be a dictionary")
            
        # 确保内容可序列化
        try:
            json.dumps(content)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Content must be JSON serializable: {e}")
            
        return content.copy()
    
    def invoke_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        调用知识节点，更新其活跃状态
        
        Args:
            node_id: 要调用的节点ID
            
        Returns:
            Optional[Dict[str, Any]]: 节点内容，如果节点不存在则返回None
        """
        if node_id not in self.knowledge_graph:
            logger.warning(f"Attempted to invoke non-existent node: {node_id}")
            return None
            
        node = self.knowledge_graph[node_id]
        node.last_invoked = datetime.now()
        node.invoke_count += 1
        
        logger.debug(f"Invoked node {node_id}, total invokes: {node.invoke_count}")
        return node.content
    
    def find_inactive_nodes(self) -> List[KnowledgeNode]:
        """
        查找所有长期未调用的节点
        
        Returns:
            List[KnowledgeNode]: 长期未调用的节点列表
        """
        now = datetime.now()
        inactive_nodes = []
        
        for node in self.knowledge_graph.values():
            if not node.active:
                continue
                
            inactive_duration = now - node.last_invoked
            if inactive_duration > self.inactivity_threshold:
                inactive_nodes.append(node)
                
        logger.info(f"Found {len(inactive_nodes)} inactive nodes out of {len(self.knowledge_graph)}")
        return inactive_nodes
    
    def extract_logical_core(self, node: KnowledgeNode) -> Optional[str]:
        """
        从知识节点中提取逻辑骨架
        
        分析节点内容，识别其核心模式，返回抽象后的逻辑结构。
        
        Args:
            node: 要提取的知识节点
            
        Returns:
            Optional[str]: 抽象后的核心模式标识，如果无法提取则返回None
        """
        if node.abstracted_core:
            return node.abstracted_core
            
        # 基于内容特征匹配核心模式
        content_str = json.dumps(node.content, sort_keys=True).lower()
        best_match = None
        best_score = 0.0
        
        for pattern_id, pattern in self.core_patterns.items():
            # 计算内容与模式的匹配度
            score = self._calculate_pattern_match(content_str, pattern)
            if score > best_score and score > 0.6:  # 匹配阈值
                best_score = score
                best_match = pattern_id
                
        if best_match:
            node.abstracted_core = best_match
            logger.info(f"Extracted core pattern '{best_match}' from node {node.node_id} (score: {best_score:.2f})")
            return best_match
            
        logger.debug(f"No core pattern extracted from node {node.node_id}")
        return None
    
    def _calculate_pattern_match(self, content_str: str, pattern: Dict[str, Any]) -> float:
        """
        计算内容与模式的匹配度
        
        Args:
            content_str: 内容字符串
            pattern: 模式定义字典
            
        Returns:
            float: 匹配度分数 (0.0-1.0)
        """
        score = 0.0
        
        # 检查描述关键词
        desc_keywords = pattern["description"].lower().split()
        for keyword in desc_keywords:
            if keyword in content_str:
                score += 0.2
                
        # 检查抽象概念
        abstraction_keywords = pattern["abstraction"].lower().split()
        for keyword in abstraction_keywords:
            if keyword in content_str:
                score += 0.15
                
        # 检查结构元素
        structure = pattern.get("structure", [])
        for element in structure:
            if element.lower() in content_str:
                score += 0.1
                
        # 归一化分数
        max_possible = 0.2 * len(desc_keywords) + 0.15 * len(abstraction_keywords) + 0.1 * len(structure)
        if max_possible > 0:
            score = min(score / max_possible, 1.0)
            
        return score
    
    def perform_variation_test(
        self,
        node: KnowledgeNode,
        target_context: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        在新上下文中执行变奏测试
        
        将节点的抽象核心映射到新上下文，测试其适用性。
        
        Args:
            node: 要测试的知识节点
            target_context: 目标上下文信息
            
        Returns:
            Tuple[bool, float]: (变奏是否成功, 适应性得分)
        """
        if not node.abstracted_core:
            return False, 0.0
            
        pattern = self.core_patterns.get(node.abstracted_core)
        if not pattern:
            return False, 0.0
            
        # 检查目标上下文是否适合该模式
        target_domain = target_context.get("domain", "").lower()
        applicable_domains = pattern.get("applicable_domains", [])
        
        # 计算上下文适配度
        domain_match = target_domain in applicable_domains
        structure_compatibility = self._check_structure_compatibility(
            node.content, 
            target_context.get("required_structure", [])
        )
        
        # 变奏成功条件：域匹配且结构兼容
        variation_success = domain_match and structure_compatibility
        
        # 计算适应性得分
        adapt_score = 0.0
        if domain_match:
            adapt_score += 0.5
        if structure_compatibility:
            adapt_score += 0.3
            
        # 考虑上下文相似度
        context_similarity = self._calculate_context_similarity(
            node.content.get("original_context", {}),
            target_context
        )
        adapt_score += 0.2 * context_similarity
        
        adapt_score = min(adapt_score, 1.0)
        
        logger.info(
            f"Variation test for node {node.node_id}: "
            f"success={variation_success}, score={adapt_score:.2f}"
        )
        
        return variation_success, adapt_score
    
    def _check_structure_compatibility(
        self,
        content: Dict[str, Any],
        required_structure: List[str]
    ) -> bool:
        """
        检查内容结构与所需结构的兼容性
        
        Args:
            content: 节点内容
            required_structure: 所需的结构元素列表
            
        Returns:
            bool: 是否兼容
        """
        if not required_structure:
            return True
            
        content_keys = set(str(k).lower() for k in content.keys())
        required = set(s.lower() for s in required_structure)
        
        # 至少50%的必需结构存在
        overlap = len(content_keys & required)
        return overlap >= len(required) * 0.5
    
    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """
        计算两个上下文的相似度
        
        Args:
            context1: 第一个上下文
            context2: 第二个上下文
            
        Returns:
            float: 相似度 (0.0-1.0)
        """
        if not context1 or not context2:
            return 0.0
            
        # 使用简单的Jaccard相似度
        keys1 = set(str(k).lower() for k in context1.keys())
        keys2 = set(str(k).lower() for k in context2.keys())
        
        intersection = len(keys1 & keys2)
        union = len(keys1 | keys2)
        
        return intersection / union if union > 0 else 0.0
    
    def resurrect_node(
        self,
        node: KnowledgeNode,
        new_context: Dict[str, Any],
        adapt_score: float
    ) -> None:
        """
        复活成功的变奏节点，提升其普适性权重
        
        Args:
            node: 要复活的节点
            new_context: 新的上下文信息
            adapt_score: 适应性得分
        """
        # 更新节点状态
        node.last_invoked = datetime.now()
        node.active = True
        node.variation_score = max(node.variation_score, adapt_score)
        
        # 添加新上下文标签
        if "domain" in new_context:
            node.tags.add(f"variated:{new_context['domain']}")
            
        # 记录变奏历史
        variation_record = {
            "node_id": node.node_id,
            "timestamp": datetime.now().isoformat(),
            "new_context": new_context,
            "adapt_score": adapt_score,
            "pattern": node.abstracted_core
        }
        self.variation_history.append(variation_record)
        
        logger.info(
            f"Resurrected node {node.node_id} with variation score {node.variation_score:.2f}, "
            f"new tags: {node.tags}"
        )
    
    def perform_variation_cycle(self, target_contexts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        执行完整的变奏周期
        
        查找所有长期未调用节点，提取其核心模式，在新上下文中测试变奏。
        
        Args:
            target_contexts: 可选的目标上下文列表，如果为None则使用默认上下文
            
        Returns:
            Dict[str, Any]: 变奏周期执行结果统计
        """
        if target_contexts is None:
            target_contexts = [
                {"domain": "api", "required_structure": ["endpoint", "method", "timeout"]},
                {"domain": "database", "required_structure": ["query", "connection", "retry"]},
                {"domain": "service", "required_structure": ["request", "response", "fallback"]}
            ]
            
        stats = {
            "total_nodes": len(self.knowledge_graph),
            "inactive_nodes": 0,
            "extracted_cores": 0,
            "variation_attempts": 0,
            "successful_variations": 0,
            "resurrected_nodes": []
        }
        
        # 1. 查找长期未调用节点
        inactive_nodes = self.find_inactive_nodes()
        stats["inactive_nodes"] = len(inactive_nodes)
        
        if not inactive_nodes:
            logger.info("No inactive nodes found for variation cycle")
            return stats
            
        # 2. 对每个未调用节点执行变奏测试
        for node in inactive_nodes:
            # 提取核心模式
            core_pattern = self.extract_logical_core(node)
            if not core_pattern:
                continue
                
            stats["extracted_cores"] += 1
            
            # 在每个目标上下文中测试
            for context in target_contexts:
                stats["variation_attempts"] += 1
                success, score = self.perform_variation_test(node, context)
                
                if success and score > 0.6:
                    self.resurrect_node(node, context, score)
                    stats["successful_variations"] += 1
                    stats["resurrected_nodes"].append({
                        "node_id": node.node_id,
                        "new_domain": context.get("domain"),
                        "score": score
                    })
                    break  # 成功复活后不再测试其他上下文
                    
        logger.info(
            f"Variation cycle complete: {stats['successful_variations']}/{stats['variation_attempts']} "
            f"successful variations"
        )
        
        return stats
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        获取节点详细信息
        
        Args:
            node_id: 节点ID
            
        Returns:
            Optional[Dict[str, Any]]: 节点信息字典
        """
        if node_id not in self.knowledge_graph:
            return None
            
        node = self.knowledge_graph[node_id]
        return {
            "node_id": node.node_id,
            "content": node.content,
            "creation_time": node.creation_time.isoformat(),
            "last_invoked": node.last_invoked.isoformat(),
            "invoke_count": node.invoke_count,
            "variation_score": node.variation_score,
            "abstracted_core": node.abstracted_core,
            "active": node.active,
            "tags": list(node.tags)
        }


def main():
    """使用示例"""
    # 初始化系统
    system = VariationKnowledgeSystem(inactivity_threshold_days=30)
    
    # 添加知识节点
    network_node = system.add_knowledge_node(
        "network_retry_protocol",
        {
            "type": "protocol",
            "description": "Network connection timeout retry mechanism",
            "max_retries": 3,
            "backoff_strategy": "exponential",
            "failure_detection": "timeout",
            "original_context": {"layer": "transport", "protocol": "TCP"}
        },
        tags=["network", "reliability", "legacy"]
    )
    
    cache_node = system.add_knowledge_node(
        "dns_cache_strategy",
        {
            "type": "optimization",
            "description": "DNS query result cache with TTL invalidation",
            "storage": "memory",
            "invalidation": "ttl_based",
            "hit_detection": "hash_lookup",
            "original_context": {"service": "DNS", "layer": "application"}
        },
        tags=["cache", "dns", "performance"]
    )
    
    # 模拟节点长期未被调用
    from datetime import datetime, timedelta
    system.knowledge_graph[network_node].last_invoked = datetime.now() - timedelta(days=60)
    system.knowledge_graph[cache_node].last_invoked = datetime.now() - timedelta(days=45)
    
    # 执行变奏周期
    print("Executing variation cycle...")
    results = system.perform_variation_cycle()
    
    print(f"\nVariation Results:")
    print(f"  Total nodes: {results['total_nodes']}")
    print(f"  Inactive nodes: {results['inactive_nodes']}")
    print(f"  Extracted cores: {results['extracted_cores']}")
    print(f"  Successful variations: {results['successful_variations']}")
    
    # 查看复活节点信息
    for node_info in results['resurrected_nodes']:
        print(f"\n  Resurrected: {node_info['node_id']}")
        print(f"    New domain: {node_info['new_domain']}")
        print(f"    Adaptation score: {node_info['score']:.2f}")
        
        full_info = system.get_node_info(node_info['node_id'])
        if full_info:
            print(f"    Tags: {full_info['tags']}")


if __name__ == "__main__":
    main()