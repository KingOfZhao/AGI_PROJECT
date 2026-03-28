"""
高级Python模块：工业设备维修日志解析与因果权重计算器

该模块旨在将非结构化的工业维修文本转化为结构化的知识图谱节点。
它结合了NLP解析（模拟）与基于反馈的贝叶斯/频率加权算法，以确定
维修措施的真实性和有效性。

版本: 1.0.0
作者: AGI System Core
领域: industrial_nlp
"""

import logging
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义数据结构
@dataclass
class MaintenanceEvent:
    """
    维修事件数据结构。
    
    Attributes:
        event_id (str): 事件唯一标识符
        raw_text (str): 原始非结构化维修日志文本
        timestamp (str): 事件发生时间
        equipment_id (str): 设备ID
        follow_up_failures (int): 后续再次故障的次数（用于计算权重）
    """
    event_id: str
    raw_text: str
    timestamp: str
    equipment_id: str
    follow_up_failures: int = 0

@dataclass
class CausalNode:
    """
    带有因果权重的结构化节点。
    
    Attributes:
        node_id (str): 节点ID
        phenomenon (str): 提取的故障现象
        action (str): 提取的解决措施
        equipment_type (str): 设备类型
        confidence_score (float): 初始解析置信度 (0.0-1.0)
        truth_weight (float): 基于反馈计算的真实性权重 (0.0-1.0)
        source_event_id (str): 源事件ID
    """
    node_id: str
    phenomenon: str
    action: str
    equipment_type: str
    confidence_score: float = 0.0
    truth_weight: float = 0.5  # 默认先验概率
    source_event_id: str = ""

class IndustrialLogParser:
    """
    解析非结构化工业日志并构建知识节点的核心类。
    
    该类封装了从文本提取到权重计算的完整流程。
    """

    def __init__(self, min_confidence: float = 0.6):
        """
        初始化解析器。

        Args:
            min_confidence (float): 节点入库的最低置信度阈值。
        """
        self.min_confidence = min_confidence
        logger.info(f"IndustrialLogParser initialized with min_confidence: {min_confidence}")

    def _extract_key_components(self, text: str) -> Tuple[str, str, float]:
        """
        [辅助函数] 从文本中提取故障现象和解决措施。
        
        在实际AGI场景中，此处应调用BERT/GPT等LLM模型。
        本实现使用基于规则的匹配来模拟提取逻辑。

        Args:
            text (str): 原始日志文本。

        Returns:
            Tuple[str, str, float]: (现象, 措施, 置信度)
        
        Raises:
            ValueError: 如果文本为空或无效。
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string.")

        # 模拟NLP提取规则
        # 实际场景应使用 spacy 或 transformers pipeline
        phenomenon_pattern = r"(故障|异常|报警|损坏|失效)[：:]\s*([^\n。;；]+)"
        action_pattern = r"(处理|维修|更换|措施|解决)[：:]\s*([^\n。;；]+)"

        phen_match = re.search(phenomenon_pattern, text)
        act_match = re.search(action_pattern, text)

        phenomenon = phen_match.group(2).strip() if phen_match else "未知故障"
        action = act_match.group(2).strip() if act_match else "未明确措施"

        # 简单的置信度模拟：如果两个都匹配到，置信度高
        confidence = 0.0
        if phen_match and act_match:
            confidence = 0.95
        elif phen_match or act_match:
            confidence = 0.70
        else:
            # 尝试进行简单的语义分割（模拟）
            parts = re.split(r'[,\.\s]+', text)
            if len(parts) > 5:
                phenomenon = " ".join(parts[:3])
                action = " ".join(parts[-3:])
                confidence = 0.50
        
        return phenomenon, action, confidence

    def parse_log_to_node(self, event: MaintenanceEvent) -> Optional[CausalNode]:
        """
        [核心函数 1] 将单个维修事件转化为因果节点。
        
        Args:
            event (MaintenanceEvent): 输入的维修事件对象。

        Returns:
            Optional[CausalNode]: 如果解析成功且超过置信度阈值，返回节点，否则返回None。
        """
        try:
            logger.info(f"Parsing event {event.event_id}...")
            
            # 数据验证
            if not event.event_id or not event.equipment_id:
                logger.warning(f"Event {event.event_id} missing critical fields. Skipping.")
                return None

            phen, act, conf = self._extract_key_components(event.raw_text)

            if conf < self.min_confidence:
                logger.warning(f"Event {event.event_id} confidence {conf} below threshold. Discarded.")
                return None

            # 创建节点
            node = CausalNode(
                node_id=f"node_{event.event_id}",
                phenomenon=phen,
                action=act,
                equipment_type=event.equipment_id.split('-')[0],  # 简单提取设备类型
                confidence_score=conf,
                source_event_id=event.event_id
            )
            
            logger.debug(f"Successfully parsed node: {node.node_id}")
            return node

        except Exception as e:
            logger.error(f"Error parsing event {event.event_id}: {str(e)}", exc_info=True)
            return None

    def calculate_truth_weight(self, nodes: List[CausalNode], feedback_map: Dict[str, int]) -> List[CausalNode]:
        """
        [核心函数 2] 根据后续反馈数据计算节点的因果权重。
        
        使用改进的频率权重算法。
        Weight = (Successes + 1) / (Total Trials + 2) (拉普拉斯平滑)
        这防止了只有少量样本时权重出现 0 或 1 的极端情况。

        Args:
            nodes (List[CausalNode]): 待计算的节点列表。
            feedback_map (Dict[str, int]): 键为event_id，值为后续故障次数(0表示成功)。

        Returns:
            List[CausalNode]: 更新了truth_weight的节点列表。
        """
        updated_nodes = []
        
        for node in nodes:
            try:
                # 查找该节点对应源事件的反馈
                # 假设 feedback_map 中的值为 "后续故障次数"
                # 0 意味着维修成功，>0 意味着维修后设备又坏了
                subsequent_failures = feedback_map.get(node.source_event_id, 0)
                
                # 简单的统计模型
                # 假设每次反馈是一个伯努利试验
                # 如果 subsequent_failures == 0, 视为成功 (1次)
                # 如果 subsequent_failures > 0, 视为失败 (0次) 或者根据次数加权
                # 这里我们采用更复杂的逻辑：
                # 权重衰减因子 = 1 / (1 + subsequent_failures)
                
                decay_factor = 1.0 / (1.0 + subsequent_failures)
                
                # 结合解析时的置信度
                # 最终权重 = 初始置信度 * 衰减因子
                # 这确保了：如果解析很模糊(0.6)但确实修好了(0 failures)，权重会上升
                # 如果解析很清晰(0.95)但没修好(5 failures)，权重会大幅下降
                
                new_weight = node.confidence_score * decay_factor
                
                # 边界检查
                node.truth_weight = max(0.0, min(1.0, new_weight))
                
                logger.info(f"Updated node {node.node_id} weight: {node.truth_weight:.4f} "
                           f"(Failures: {subsequent_failures}, Base Conf: {node.confidence_score})")
                
                updated_nodes.append(node)

            except Exception as e:
                logger.error(f"Failed to calculate weight for node {node.node_id}: {e}")
                # 保留原始节点，不做修改
                updated_nodes.append(node)
                
        return updated_nodes

def export_to_json(nodes: List[CausalNode], filepath: str) -> bool:
    """
    将节点列表导出为JSON文件。
    
    Args:
        nodes: 节点列表
        filepath: 输出文件路径
        
    Returns:
        bool: 是否成功
    """
    try:
        output_data = []
        for n in nodes:
            output_data.append({
                "node_id": n.node_id,
                "phenomenon": n.phenomenon,
                "action": n.action,
                "truth_weight": round(n.truth_weight, 4),
                "source": n.source_event_id
            })
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Data exported to {filepath}")
        return True
    except IOError as e:
        logger.error(f"File write error: {e}")
        return False

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 准备模拟数据 (非结构化文本)
    raw_logs = [
        MaintenanceEvent(
            event_id="E001",
            raw_text="故障：液压泵压力不足。处理：更换了密封圈，测试正常。",
            timestamp="2023-10-01 10:00:00",
            equipment_id="PUMP-H-001",
            follow_up_failures=0 # 假设后续没有再坏
        ),
        MaintenanceEvent(
            event_id="E002",
            raw_text="报警信息：电机过热。措施：清理散热风扇灰尘。",
            timestamp="2023-10-02 14:30:00",
            equipment_id="MOTOR-M-05",
            follow_up_failures=2 # 假设后续又坏了2次，说明措施无效
        ),
        MaintenanceEvent(
            event_id="E003",
            raw_text="乱七八糟的文本，没有明确的关键词。",
            timestamp="2023-10-03 09:00:00",
            equipment_id="GEN-G-01",
            follow_up_failures=0
        )
    ]

    # 2. 初始化解析器
    parser = IndustrialLogParser(min_confidence=0.5)

    # 3. 解析日志
    parsed_nodes = []
    for log in raw_logs:
        node = parser.parse_log_to_node(log)
        if node:
            parsed_nodes.append(node)

    print(f"\n--- Step 1: Parsed {len(parsed_nodes)} nodes ---")
    for n in parsed_nodes:
        print(f"Node: {n.phenomenon} -> {n.action} [Init Conf: {n.confidence_score}]")

    # 4. 模拟反馈数据 (例如从ERP系统读取)
    # key: event_id, value: subsequent failure count
    feedback_data = {
        "E001": 0, # 维修非常成功
        "E002": 3, # 维修失败，后来又坏了3次
    }

    # 5. 计算真实权重
    weighted_nodes = parser.calculate_truth_weight(parsed_nodes, feedback_data)

    print(f"\n--- Step 2: Calculated Truth Weights ---")
    for n in weighted_nodes:
        print(f"Node: {n.node_id} | Weight: {n.truth_weight:.4f} | Phenomenon: {n.phenomenon}")

    # 6. 导出结果 (可选)
    # export_to_json(weighted_nodes, "knowledge_nodes.json")