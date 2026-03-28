"""
模块名称: auto_如何开发人机共生接口_使ai能将非结构化_a51b8a
描述: 实现人机共生接口的核心逻辑，将非结构化的故障现象文本转化为结构化的'实践清单'，
      并根据人类专家的显式反馈（采纳/修正/拒绝）动态更新知识节点的权重。
版本: 1.0.0
作者: Senior Python Engineer
"""

import logging
import re
import json
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class FeedbackType(Enum):
    """定义专家反馈类型的枚举"""
    ADOPTED = 1.0      # 采纳：增加权重
    MODIFIED = 0.1     # 修正：略微增加权重（因为节点相关但需微调）
    REJECTED = -0.5    # 拒绝：降低权重

@dataclass
class PracticeItem:
    """结构化的实践清单项"""
    id: str
    description: str
    source_node_id: str
    current_weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "source_node_id": self.source_node_id,
            "current_weight": self.current_weight
        }

@dataclass
class KnowledgeNode:
    """知识图谱中的节点，包含权重信息"""
    node_id: str
    content: str
    weight: float = 1.0
    usage_count: int = 0

# --- 核心类 ---

class HumanMachineSymbiosisInterface:
    """
    人机共生接口类。
    
    负责：
    1. 将非结构化文本转化为结构化清单。
    2. 处理人类专家反馈。
    3. 量化反馈并更新内部模型权重。
    """

    def __init__(self, initial_knowledge_base: Optional[Dict[str, KnowledgeNode]] = None):
        """
        初始化接口。
        
        Args:
            initial_knowledge_base: 初始的知识库字典 (Node ID -> KnowledgeNode)
        """
        self.knowledge_base = initial_knowledge_base if initial_knowledge_base else {}
        self._init_default_knowledge()
        logger.info("HumanMachineSymbiosisInterface initialized.")

    def _init_default_knowledge(self):
        """初始化一些默认的故障排查知识节点（模拟）"""
        default_data = {
            "node_001": KnowledgeNode("node_001", "检查服务器CPU利用率是否超过90%"),
            "node_002": KnowledgeNode("node_002", "检查磁盘空间是否已满"),
            "node_003": KnowledgeNode("node_003", "验证数据库连接字符串配置"),
            "node_004": KnowledgeNode("node_004", "查看最近的代码部署记录")
        }
        self.knowledge_base.update(default_data)

    def _extract_keywords(self, text: str) -> List[str]:
        """
        辅助函数：从非结构化文本中提取关键词。
        (这里使用简单的正则模拟，实际生产应使用NLP模型)
        
        Args:
            text: 输入的故障现象描述
            
        Returns:
            关键词列表
        """
        # 简单清洗
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        # 模拟关键词提取 (实际可用 TF-IDF, RAKE, 或 Transformer embeddings)
        stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你"}
        words = [w for w in clean_text.split() if w not in stopwords and len(w) > 1]
        logger.debug(f"Extracted keywords: {words}")
        return words

    def unstructured_to_structured_checklist(self, raw_phenomenon: str) -> List[PracticeItem]:
        """
        核心函数 1: 将非结构化的故障现象转化为结构化的'实践清单'。
        
        逻辑:
        1. 提取现象中的关键词。
        2. 匹配知识库中的节点（基于简单的包含关系或实际应使用向量检索）。
        3. 根据节点生成清单项。
        
        Args:
            raw_phenomenon: 非结构化的故障文本 (e.g., "数据库连接超时，而且CPU跑得很高")
            
        Returns:
            List[PracticeItem]: 推荐的结构化清单
        """
        if not raw_phenomenon or not isinstance(raw_phenomenon, str):
            logger.error("Invalid input: raw_phenomenon must be a non-empty string.")
            raise ValueError("Input must be a non-empty string")

        logger.info(f"Processing phenomenon: {raw_phenomenon}")
        keywords = self._extract_keywords(raw_phenomenon)
        recommendations = []

        # 模拟检索逻辑
        for node_id, node in self.knowledge_base.items():
            relevance_score = 0
            # 简单的相关性打分：如果节点内容包含关键词
            for kw in keywords:
                if kw in node.content:
                    relevance_score += 1
            
            # 如果相关，加入清单
            if relevance_score > 0:
                # 计算优先级分数 = 相关性 * 节点历史权重
                priority_score = relevance_score * node.weight
                
                item = PracticeItem(
                    id=f"task_{node_id}_{len(recommendations)}",
                    description=node.content,
                    source_node_id=node_id,
                    current_weight=priority_score
                )
                recommendations.append(item)
        
        # 按权重排序
        recommendations.sort(key=lambda x: x.current_weight, reverse=True)
        
        logger.info(f"Generated {len(recommendations)} checklist items.")
        return recommendations

    def process_expert_feedback(
        self, 
        item_id: str, 
        source_node_id: str, 
        feedback: FeedbackType,
        corrected_text: Optional[str] = None
    ) -> bool:
        """
        核心函数 2: 接收并量化人类专家的反馈，更新节点权重。
        
        Args:
            item_id: 清单项ID
            source_node_id: 关联的知识节点ID
            feedback: 反馈类型 (采纳/修正/拒绝)
            corrected_text: 如果是修正反馈，专家提供的新内容
            
        Returns:
            bool: 更新是否成功
        """
        if source_node_id not in self.knowledge_base:
            logger.error(f"Node {source_node_id} not found in knowledge base.")
            return False

        try:
            node = self.knowledge_base[source_node_id]
            node.usage_count += 1
            
            # 计算学习率衰减 (模拟，避免权重剧烈波动)
            # Learning rate decreases as we get more data on this node
            lr = 1.0 / (1 + node.usage_count * 0.1)
            
            adjustment = feedback.value * lr
            
            # 更新权重
            node.weight += adjustment
            
            # 边界检查：权重不能为负，且不应过大
            node.weight = max(0.01, min(node.weight, 10.0))
            
            log_msg = (
                f"Feedback processed for Node {source_node_id}. "
                f"Type: {feedback.name}, Adjustment: {adjustment:.4f}, New Weight: {node.weight:.4f}"
            )
            logger.info(log_msg)

            # 如果是修正，可以创建新的知识节点或标记现有节点需审查
            if feedback == FeedbackType.MODIFIED and corrected_text:
                logger.info(f"Expert modified content suggestion: {corrected_text}")
                # 这里可以触发一个微调流程，暂时仅记录日志

            return True

        except Exception as e:
            logger.exception(f"Error processing feedback: {e}")
            return False

    def export_knowledge_state(self) -> str:
        """
        辅助函数: 导出当前知识库状态为JSON。
        """
        state = {
            "nodes": [
                {
                    "id": k, 
                    "content": v.content, 
                    "weight": v.weight, 
                    "usage": v.usage_count
                } for k, v in self.knowledge_base.items()
            ]
        }
        return json.dumps(state, indent=2)

# --- 使用示例 ---

def main():
    """
    演示如何使用 HumanMachineSymbiosisInterface。
    """
    print("--- 初始化人机共生接口 ---")
    interface = HumanMachineSymbiosisInterface()

    # 场景：运维人员输入非结构化故障描述
    raw_input = "系统非常慢，数据库好像连不上了，总是报错超时。"
    
    print(f"\n>>> 输入故障现象: '{raw_input}'")
    
    # 步骤 1: 生成结构化清单
    print("\n>>> 生成结构化实践清单:")
    checklist = interface.unstructured_to_structured_checklist(raw_input)
    
    for idx, item in enumerate(checklist):
        print(f"{idx+1}. [{item.source_node_id}] {item.description} (Weight: {item.current_weight:.2f})")

    # 步骤 2: 模拟人类专家交互反馈
    # 假设专家对第一个建议（CPU）执行了"采纳"，对第二个建议（数据库）执行了"修正"
    if len(checklist) >= 2:
        item_1 = checklist[0]
        item_2 = checklist[1]
        
        print(f"\n>>> 专家反馈: 采纳建议 '{item_1.description}'")
        interface.process_expert_feedback(
            item_id=item_1.id,
            source_node_id=item_1.source_node_id,
            feedback=FeedbackType.ADOPTED
        )
        
        print(f"\n>>> 专家反馈: 修正建议 '{item_2.description}' -> '检查连接池配置'")
        interface.process_expert_feedback(
            item_id=item_2.id,
            source_node_id=item_2.source_node_id,
            feedback=FeedbackType.MODIFIED,
            corrected_text="检查连接池配置"
        )

    # 步骤 3: 查看更新后的权重
    print("\n>>> 当前知识库状态 (权重已更新):")
    print(interface.export_knowledge_state())

if __name__ == "__main__":
    main()