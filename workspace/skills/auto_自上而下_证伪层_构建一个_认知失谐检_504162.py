"""
Module Name: cognitive_dissonance_detector.py
Description: 【自上而下-证伪层】构建一个'认知失谐检测器'算法。
             用于监控AI生成的建议与人类专家实践之间的偏差，自动标记冲突节点，
             并区分'人类的随机错误'与'AI模型的认知局限'。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import random
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConflictType(Enum):
    """冲突类型的枚举类。"""
    RANDOM_HUMAN_ERROR = "Random Human Error"
    AI_MODEL_LIMITATION = "AI Model Limitation"
    UNKNOWN = "Unknown"

@dataclass
class NodeRecord:
    """用于存储节点数据的单一记录类。"""
    node_id: str
    ai_suggestion: float  # AI建议的数值或概率 (0.0 - 1.0)
    human_action: float   # 人类实际行为的数值或概率 (0.0 - 1.0)
    error_margin: float = 0.05  # 允许的误差范围

@dataclass
class ConflictReport:
    """冲突检测报告的数据结构。"""
    node_id: str
    conflict_score: float
    classification: ConflictType
    details: str

class CognitiveDissonanceDetector:
    """
    认知失谐检测器核心类。
    
    该类实现了一个自上而下的证伪层逻辑，用于比较AI生成的逻辑图谱与人类实际操作数据。
    它旨在识别两者之间的显著偏差，并利用统计方法将偏差归类为人类的随机噪声或AI的认知缺陷。
    """

    def __init__(self, sensitivity_threshold: float = 0.2, noise_tolerance: float = 0.1):
        """
        初始化检测器。

        Args:
            sensitivity_threshold (float): 触发冲突检测的最小偏差阈值。
            noise_tolerance (float): 区分随机错误和系统错误的容错范围。
        """
        if not (0.0 <= sensitivity_threshold <= 1.0):
            raise ValueError("Sensitivity threshold must be between 0 and 1.")
        if not (0.0 <= noise_tolerance <= 1.0):
            raise ValueError("Noise tolerance must be between 0 and 1.")
            
        self.sensitivity_threshold = sensitivity_threshold
        self.noise_tolerance = noise_tolerance
        logger.info("CognitiveDissonanceDetector initialized with threshold: %.2f", sensitivity_threshold)

    def _calculate_deviation(self, val1: float, val2: float) -> float:
        """
        辅助函数：计算两个数值之间的绝对偏差。
        
        Args:
            val1 (float): 第一个值 (e.g., AI suggestion).
            val2 (float): 第二个值 (e.g., Human action).
            
        Returns:
            float: 绝对差值。
        """
        return abs(val1 - val2)

    def _classify_conflict_source(self, node_history: List[NodeRecord]) -> ConflictType:
        """
        辅助函数：基于历史数据分布对冲突源进行分类。
        
        逻辑：
        如果人类的行为呈现高方差，倾向于认为是人类随机错误。
        如果人类的行为呈现低方差（稳定）但与AI一致偏离，倾向于认为是AI认知局限。
        
        Args:
            node_history (List[NodeRecord]): 该节点的历史记录列表。
            
        Returns:
            ConflictType: 分类的结果。
        """
        if len(node_history) < 3:
            return ConflictType.UNKNOWN

        # 提取人类行为的历史偏差（相对于AI建议）
        deviations = [self._calculate_deviation(rec.ai_suggestion, rec.human_action) for rec in node_history]
        
        # 计算偏差的统计特性
        stdev = statistics.stdev(deviations)
        mean_dev = statistics.mean(deviations)
        
        logger.debug(f"Node {node_history[0].node_id} Deviation Stats - Mean: {mean_dev:.3f}, Stdev: {stdev:.3f}")

        # 判别逻辑
        if stdev > self.noise_tolerance:
            # 高方差表明人类行为不稳定，可能是随机错误
            return ConflictType.RANDOM_HUMAN_ERROR
        elif mean_dev > self.sensitivity_threshold:
            # 低方差且均值偏差大，表明人类有一致的不同做法，可能是AI模型局限
            return ConflictType.AI_MODEL_LIMITATION
        else:
            return ConflictType.UNKNOWN

    def monitor_and_detect(self, current_state: List[NodeRecord], history_data: Optional[Dict[str, List[NodeRecord]]] = None) -> List[ConflictReport]:
        """
        核心函数1：监控并检测认知失谐。
        
        分析当前输入的节点状态，识别出AI建议与人类行为存在显著差异的节点。
        
        Args:
            current_state (List[NodeRecord]): 当前批次的节点数据列表。
            history_data (Optional[Dict]): 历史数据字典，用于辅助分类。
            
        Returns:
            List[ConflictReport]: 包含所有被标记为冲突的节点的报告列表。
        """
        if not current_state:
            logger.warning("Empty current state provided for monitoring.")
            return []

        conflict_reports: List[ConflictReport] = []
        
        for record in current_state:
            deviation = self._calculate_deviation(record.ai_suggestion, record.human_action)
            
            # 边界检查
            if not (0 <= record.ai_suggestion <= 1 and 0 <= record.human_action <= 1):
                logger.error(f"Data out of bounds for node {record.node_id}")
                continue

            # 如果偏差超过敏感度阈值，触发深度分析
            if deviation > self.sensitivity_threshold:
                logger.info(f"Conflict detected at node {record.node_id}. Deviation: {deviation:.3f}")
                
                # 获取历史数据以进行分类
                node_history = []
                if history_data and record.node_id in history_data:
                    node_history = history_data[record.node_id]
                
                # 添加当前记录到历史中以进行分析（如果是首次检测，列表可能很短）
                analysis_sample = node_history + [record]
                
                conflict_type = self._classify_conflict_source(analysis_sample)
                
                report = ConflictReport(
                    node_id=record.node_id,
                    conflict_score=deviation,
                    classification=conflict_type,
                    details=f"AI: {record.ai_suggestion:.2f} vs Human: {record.human_action:.2f}"
                )
                conflict_reports.append(report)
                
        return conflict_reports

    def update_model_weights(self, reports: List[ConflictReport]) -> Dict[str, float]:
        """
        核心函数2：根据冲突报告更新模型权重（模拟）。
        
        这是一个反馈机制。如果检测到AI模型局限，降低对应节点的置信度权重。
        
        Args:
            reports (List[ConflictReport]): 监控函数产生的冲突报告。
            
        Returns:
            Dict[str, float]: 需要调整的节点权重映射 {node_id: new_weight}。
        """
        weight_adjustments: Dict[str, float] = {}
        
        for report in reports:
            if report.classification == ConflictType.AI_MODEL_LIMITATION:
                # 惩罚AI模型，降低权重
                new_weight = max(0.1, 1.0 - report.conflict_score)
                weight_adjustments[report.node_id] = new_weight
                logger.warning(f"Adjusting weight for node {report.node_id} to {new_weight:.2f} due to AI limitation.")
            elif report.classification == ConflictType.RANDOM_HUMAN_ERROR:
                # 忽略随机错误，保持权重或微调
                weight_adjustments[report.node_id] = 1.0 # 保持信任AI
                logger.info(f"Maintaining weight for node {report.node_id}. Deviation classified as human error.")
                
        return weight_adjustments

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 模拟生成528个节点的基础数据
    NUM_NODES = 528
    node_ids = [f"node_{i}" for i in range(NUM_NODES)]
    
    # 模拟历史数据（为了演示分类逻辑，给特定节点构造历史模式）
    mock_history: Dict[str, List[NodeRecord]] = {
        "node_1": [NodeRecord("node_1", 0.9, 0.2) for _ in range(5)], # 稳定偏离 -> AI局限
        "node_2": [NodeRecord("node_2", 0.9, random.choice([0.1, 0.8, 0.9, 0.2])) for _ in range(5)], # 不稳定 -> 人类错误
    }

    # 模拟当前批次数据
    current_batch = [
        NodeRecord("node_1", 0.9, 0.15), # 显著偏离
        NodeRecord("node_2", 0.9, 0.1),  # 显著偏离
        NodeRecord("node_3", 0.5, 0.5),  # 正常
        NodeRecord("node_4", 0.8, 0.79), # 正常范围内
        NodeRecord("node_5", 0.7, 0.1),  # 无历史的新冲突
    ]

    # 初始化检测器
    detector = CognitiveDissonanceDetector(sensitivity_threshold=0.2, noise_tolerance=0.15)

    print("--- Starting Cognitive Dissonance Detection ---")
    
    # 1. 监控检测
    reports = detector.monitor_and_detect(current_batch, mock_history)
    
    print(f"\n--- Detected {len(reports)} Conflicts ---")
    for r in reports:
        print(f"Node: {r.node_id} | Type: {r.classification.value} | Score: {r.conflict_score:.2f}")

    # 2. 反馈/更新
    adjustments = detector.update_model_weights(reports)
    
    print("\n--- Weight Adjustments ---")
    for nid, weight in adjustments.items():
        print(f"Node: {nid} -> New Weight: {weight:.2f}")