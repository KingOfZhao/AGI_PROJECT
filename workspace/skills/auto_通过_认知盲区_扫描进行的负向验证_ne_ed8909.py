"""
Name: auto_通过_认知盲区_扫描进行的负向验证_ne_ed8909
Description: Negative Verification via Cognitive Blind Spot Scanning.
Domain: information_retrieval
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveBlindSpotScanner")


@dataclass
class KnowledgeNode:
    """
    知识网络中的节点数据结构。
    
    Attributes:
        node_id (str): 节点唯一标识符
        content (str): 节点内容描述
        node_type (str): 节点类型 ('rule', 'fact', 'anomaly')
        confidence (float): 节点的置信度 [0.0, 1.0]
        conditions (List[str]): 解释该节点的条件节点ID列表
        created_at (datetime): 创建时间
    """
    node_id: str
    content: str
    node_type: str
    confidence: float = 1.0
    conditions: List[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # 数据验证
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


class CognitiveBlindSpotScanner:
    """
    通过'认知盲区'扫描进行的负向验证。
    
    该类实现了一种算法，用于检测AI系统中的确认偏误。
    它专门搜索反驳现有假设的反例，并在发现足够证据时创建异常节点。
    
    Attributes:
        knowledge_base (Dict[str, KnowledgeNode]): 知识节点存储
        counter_example_threshold (int): 触发异常节点创建的反例数量阈值
        anomaly_counter (int): 异常节点ID计数器
    """

    def __init__(self, counter_example_threshold: int = 3):
        """
        初始化扫描器。
        
        Args:
            counter_example_threshold (int): 触发异常所需的最小反例数量
        """
        if counter_example_threshold < 1:
            raise ValueError("Threshold must be at least 1")
        
        self.knowledge_base: Dict[str, KnowledgeNode] = {}
        self.counter_example_threshold = counter_example_threshold
        self.anomaly_counter = 0
        logger.info("CognitiveBlindSpotScanner initialized with threshold %d", counter_example_threshold)

    def add_knowledge_node(self, node: KnowledgeNode) -> None:
        """添加知识节点到知识库"""
        if not isinstance(node, KnowledgeNode):
            raise TypeError("Input must be a KnowledgeNode instance")
        
        self.knowledge_base[node.node_id] = node
        logger.debug("Added node %s: %s", node.node_id, node.content)

    def _construct_negative_query(self, rule_node: KnowledgeNode) -> Optional[str]:
        """
        [辅助函数] 根据规则节点构建否定查询语句。
        
        这是一个简化的自然语言处理模拟，实际应用中应接入NLP引擎。
        例如：将 'A causes B' 转换为 'A present AND B absent' 的查询逻辑。
        
        Args:
            rule_node (KnowledgeNode): 包含因果规则的节点
            
        Returns:
            Optional[str]: 生成的查询字符串，如果无法解析则返回None
        """
        if not rule_node.content:
            logger.warning("Node %s has empty content", rule_node.node_id)
            return None

        # 简单的规则解析模拟 (实际项目中应使用NLP或知识图谱解析)
        # 假设格式为 "A causes B" 或 "If A then B"
        content_lower = rule_node.content.lower()
        
        if " causes " in content_lower:
            parts = content_lower.split(" causes ")
            cause = parts[0].strip()
            effect = parts[1].strip()
            # 构建寻找反例的查询：存在原因，但结果未发生
            query = f"SELECT * FROM observations WHERE event='{cause}' AND outcome!='{effect}'"
            logger.debug("Generated negative query: %s", query)
            return query
        elif " if " in content_lower and " then " in content_lower:
            parts = content_lower.split(" then ")
            condition = parts[0].replace("if ", "").strip()
            consequence = parts[1].strip()
            query = f"SELECT * FROM observations WHERE condition='{condition}' AND result!='{consequence}'"
            logger.debug("Generated negative query: %s", query)
            return query
        
        logger.warning("Could not parse rule format for node %s", rule_node.node_id)
        return None

    def scan_for_blind_spots(self, rule_node_id: str, simulated_db: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        [核心函数 1] 扫描特定规则节点的认知盲区。
        
        在数据库中检索反例，验证规则的普适性。
        
        Args:
            rule_node_id (str): 要验证的规则节点ID
            simulated_db (List[Dict]): 模拟的观察数据库记录
            
        Returns:
            Tuple[bool, Optional[str]]: 
                - bool: 是否发现严重的认知盲区（超过阈值）
                - Optional[str]: 如果发现盲区，返回新创建的异常节点ID
        """
        if rule_node_id not in self.knowledge_base:
            logger.error("Node ID %s not found", rule_node_id)
            raise ValueError(f"Node ID {rule_node_id} not found in knowledge base")

        rule_node = self.knowledge_base[rule_node_id]
        
        # 步骤 1: 构建反向查询
        query = self._construct_negative_query(rule_node)
        if not query:
            return False, None

        # 步骤 2: 模拟检索反例 (模拟数据库操作)
        # 在实际应用中，这里会连接向量数据库或SQL数据库
        counter_examples = []
        try:
            # 简单的内存模拟匹配逻辑
            target_cause = rule_node.content.split(" causes ")[0].strip().lower()
            target_effect = rule_node.content.split(" causes ")[1].strip().lower()
            
            for record in simulated_db:
                # 检查是否满足 'A发生'
                cause_present = target_cause in record.get('event', '').lower()
                # 检查是否满足 'B未发生'
                effect_absent = target_effect not in record.get('outcome', '').lower()
                
                if cause_present and effect_absent:
                    counter_examples.append(record)
                    
        except Exception as e:
            logger.error("Error during database scan: %s", e)
            return False, None

        logger.info("Found %d counter-examples for rule %s", len(counter_examples), rule_node_id)

        # 步骤 3: 阈值判断与异常处理
        if len(counter_examples) >= self.counter_example_threshold:
            is_explainable = self._check_existing_explanations(rule_node, counter_examples)
            
            if not is_explainable:
                anomaly_id = self.create_anomaly_node(rule_node, counter_examples)
                return True, anomaly_id

        return False, None

    def _check_existing_explanations(self, rule_node: KnowledgeNode, examples: List[Dict]) -> bool:
        """
        [辅助函数] 检查反例是否可以被现有的条件节点解释。
        
        简单模拟：如果反例中包含特定的context，且该context存在于规则的条件中，
        则认为是可以解释的。
        """
        # 这里仅作演示，实际逻辑更复杂
        if "exception" in rule_node.conditions:
            logger.info("Counter-examples are explained by existing exception conditions.")
            return True
        return False

    def create_anomaly_node(self, original_node: KnowledgeNode, counter_examples: List[Dict]) -> str:
        """
        [核心函数 2] 在知识网络中创建异常节点。
        
        当反例数量超过阈值且无法解释时，生成一个警示节点。
        
        Args:
            original_node (KnowledgeNode): 被验证的原始规则节点
            counter_examples (List[Dict]): 触发创建的反例列表
            
        Returns:
            str: 新创建的异常节点ID
        """
        self.anomaly_counter += 1
        anomaly_id = f"anomaly_{self.anomaly_counter}_{original_node.node_id}"
        
        # 降低原节点的置信度
        original_node.confidence *= 0.5
        
        description = (
            f"Anomaly detected for rule '{original_node.content}'. "
            f"Found {len(counter_examples)} counter-examples. "
            f"Original confidence reduced to {original_node.confidence:.2f}."
        )
        
        anomaly_node = KnowledgeNode(
            node_id=anomaly_id,
            content=description,
            node_type='anomaly',
            confidence=1.0,  # 异常节点本身是高置信度的观测事实
            conditions=[original_node.node_id],  # 指向引发问题的规则
            created_at=datetime.now()
        )
        
        self.knowledge_base[anomaly_id] = anomaly_node
        
        logger.warning(
            "CREATED ANOMALY NODE: %s for rule %s. Evidence: %s", 
            anomaly_id, 
            original_node.node_id,
            [ex.get('id') for ex in counter_examples[:3]] # 只记录前3个ID
        )
        
        return anomaly_id

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 初始化系统
    scanner = CognitiveBlindSpotScanner(counter_example_threshold=2)
    
    # 2. 创建知识节点 (假设: "下雨导致地面湿")
    # 在实际AGI系统中，这通常是自动生成的
    rule_node = KnowledgeNode(
        node_id="rule_001",
        content="Rain causes WetGround",
        node_type="rule",
        confidence=0.95
    )
    scanner.add_knowledge_node(rule_node)
    
    # 3. 模拟数据库检索结果 (模拟现实世界的观察数据)
    # 包含了反例：下雨了，但地面没湿（可能因为有遮蔽物，但系统目前不知道）
    mock_database_records = [
        {"id": "rec1", "event": "Heavy Rain", "outcome": "WetGround"},
        {"id": "rec2", "event": "Light Rain", "outcome": "WetGround"},
        # 反例 1
        {"id": "rec3", "event": "Rain", "outcome": "DryGround (Under Shelter)"}, 
        {"id": "rec4", "event": "Storm", "outcome": "WetGround"},
        # 反例 2
        {"id": "rec5", "event": "Rain", "outcome": "DryGround (Covered)"}, 
        # 反例 3
        {"id": "rec6", "event": "Rain", "outcome": "DryGround"},
    ]
    
    # 4. 执行扫描
    print(f"Scanning rule: {rule_node.content}...")
    has_blind_spot, anomaly_id = scanner.scan_for_blind_spots(
        rule_node_id="rule_001", 
        simulated_db=mock_database_records
    )
    
    # 5. 结果处理
    if has_blind_spot:
        print(f"[ALERT] Cognitive Blind Spot Detected!")
        print(f"Anomaly Node Created: {anomaly_id}")
        print(f"Original Rule Confidence Downgraded to: {rule_node.confidence}")
        print(f"Anomaly Details: {scanner.knowledge_base[anomaly_id].content}")
    else:
        print("Rule verified successfully with current data.")