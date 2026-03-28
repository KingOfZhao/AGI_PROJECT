"""
Module: auto_认知自洽性的_逻辑应力测试_设计一种自_426654
Domain: logic_reasoning

Description:
    该模块实现了一个认知自洽性的逻辑应力测试引擎。它模拟AGI系统中的认知网络，
    通过随机选取节点进行逻辑推导，旨在发现潜在的逻辑悖论（如矛盾关系）。
    系统基于经典逻辑中的“对当方阵”原理来检测全称肯定、全称否定、特称肯定
    和特称否定命题之间的冲突，并生成修正提案。

Input Format:
    认知网络由一组 'Proposition' 对象组成，每个对象包含：
    - id (str): 节点唯一标识符
    - subject (str): 主语
    - predicate (str): 谓语
    - p_type (PropositionType): 命题类型 (A, E, I, O)
    - confidence (float): 信念强度 (0.0 - 1.0)

Output Format:
    返回一个包含冲突报告的字典列表，每个报告包含：
    - conflict_pair (Tuple[str, str]): 冲突节点ID
    - description (str): 冲突描述
    - proposal (str): 修正提案
"""

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropositionType(Enum):
    """定义四种基本的直言命题类型（基于逻辑方阵）。"""
    UNIVERSAL_POSITIVE = "A"  # 所有X都是Y
    UNIVERSAL_NEGATIVE = "E"  # 所有X都不是Y
    PARTICULAR_POSITIVE = "I"  # 存在X是Y
    PARTICULAR_NEGATIVE = "O"  # 存在X不是Y


@dataclass
class Proposition:
    """表示认知网络中的一个逻辑节点。"""
    id: str
    subject: str
    predicate: str
    p_type: PropositionType
    confidence: float = 1.0

    def __post_init__(self):
        """初始化后的数据验证。"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class LogicStressTestEngine:
    """
    逻辑应力测试引擎。用于检测认知网络中的逻辑不一致性。
    """

    def __init__(self, network: List[Proposition]):
        """
        初始化引擎。

        Args:
            network: 认知网络中的命题列表。
        """
        self.network = network
        self._validate_network()

    def _validate_network(self) -> None:
        """
        辅助函数：验证输入网络的完整性。
        检查ID是否唯一，数据结构是否正确。
        """
        if not self.network:
            logger.warning("Initialized with an empty cognitive network.")
            return

        ids: Set[str] = {p.id for p in self.network}
        if len(ids) != len(self.network):
            raise ValueError("Network contains duplicate proposition IDs.")
        
        logger.info(f"Network validated successfully with {len(self.network)} nodes.")

    def _check_contradiction(self, p1: Proposition, p2: Proposition) -> bool:
        """
        核心逻辑：检查两个命题是否存在逻辑矛盾。
        基于逻辑方阵的矛盾关系：
        - A (所有S都是P) vs O (存在S不是P) -> 矛盾
        - E (所有S都不是P) vs I (存在S是P) -> 矛盾

        Args:
            p1: 第一个命题
            p2: 第二个命题

        Returns:
            bool: 如果存在矛盾返回True，否则返回False。
        """
        # 检查主语和谓语是否相同（针对同一对象的描述）
        if p1.subject != p2.subject or p1.predicate != p2.predicate:
            return False

        # 检查矛盾关系
        is_contradiction = False
        if p1.p_type == PropositionType.UNIVERSAL_POSITIVE and p2.p_type == PropositionType.PARTICULAR_NEGATIVE:
            is_contradiction = True
        elif p1.p_type == PropositionType.PARTICULAR_NEGATIVE and p2.p_type == PropositionType.UNIVERSAL_POSITIVE:
            is_contradiction = True
        elif p1.p_type == PropositionType.UNIVERSAL_NEGATIVE and p2.p_type == PropositionType.PARTICULAR_POSITIVE:
            is_contradiction = True
        elif p1.p_type == PropositionType.PARTICULAR_POSITIVE and p2.p_type == PropositionType.UNIVERSAL_NEGATIVE:
            is_contradiction = True

        if is_contradiction:
            logger.debug(f"Contradiction detected between {p1.id} and {p2.id}")

        return is_contradiction

    def generate_correction_proposal(self, p1: Proposition, p2: Proposition) -> str:
        """
        辅助函数：根据置信度生成修正提案。
        策略：建议移除置信度较低的命题，或者标记为需要人工审查。

        Args:
            p1: 冲突命题1
            p2: 冲突命题2

        Returns:
            str: 修正建议文本。
        """
        if p1.confidence > p2.confidence:
            return f"建议保留节点 {p1.id} (置信度: {p1.confidence})，移除或修正节点 {p2.id} (置信度: {p2.confidence})。"
        elif p2.confidence > p1.confidence:
            return f"建议保留节点 {p2.id} (置信度: {p2.confidence})，移除或修正节点 {p1.id} (置信度: {p1.confidence})。"
        else:
            return f"节点 {p1.id} 和 {p2.id} 置信度相同 ({p1.confidence})，建议进行人工仲裁以确定真值。"

    def run_stress_test(self, sample_size: int = 10) -> List[Dict]:
        """
        核心功能：执行逻辑应力测试。
        随机选取节点对进行逻辑推导，寻找悖论。

        Args:
            sample_size: 要测试的随机对数。如果小于1，则测试所有可能的组合。

        Returns:
            List[Dict]: 发现的冲突列表。
        """
        if len(self.network) < 2:
            logger.info("Network too small for pairwise testing.")
            return []

        conflicts_found = []
        tested_pairs: Set[Tuple[str, str]] = set()
        
        # 确定测试范围
        if sample_size < 1:
            # 全量测试
            indices = [(i, j) for i in range(len(self.network)) for j in range(i + 1, len(self.network))]
            logger.info("Running full exhaustive logic stress test.")
        else:
            # 随机采样测试
            indices = []
            attempts = 0
            max_attempts = sample_size * 10 # 防止无限循环
            
            while len(indices) < sample_size and attempts < max_attempts:
                i, j = random.sample(range(len(self.network)), 2)
                pair_id = tuple(sorted((self.network[i].id, self.network[j].id)))
                if pair_id not in tested_pairs:
                    indices.append((i, j))
                    tested_pairs.add(pair_id)
                attempts += 1
            
            logger.info(f"Running random logic stress test with {len(indices)} samples.")

        # 执行检查
        for i, j in indices:
            p1 = self.network[i]
            p2 = self.network[j]
            
            try:
                if self._check_contradiction(p1, p2):
                    proposal = self.generate_correction_proposal(p1, p2)
                    report = {
                        "conflict_pair": (p1.id, p2.id),
                        "description": f"节点 {p1.id} ('{p1.subject} {p1.p_type.value} {p1.predicate}') "
                                       f"与 节点 {p2.id} ('{p2.subject} {p2.p_type.value} {p2.predicate}') 存在逻辑矛盾。",
                        "proposal": proposal
                    }
                    conflicts_found.append(report)
                    logger.warning(f"Conflict Found: {report['description']}")
            except Exception as e:
                logger.error(f"Error processing pair ({p1.id}, {p2.id}): {e}")

        return conflicts_found


# 使用示例
if __name__ == "__main__":
    # 构建一个包含潜在矛盾的测试网络
    test_network = [
        Proposition(id="N1", subject="AI", predicate="Safe", p_type=PropositionType.UNIVERSAL_POSITIVE, confidence=0.9),
        Proposition(id="N2", subject="AI", predicate="Safe", p_type=PropositionType.PARTICULAR_NEGATIVE, confidence=0.4), # 与N1矛盾
        Proposition(id="N3", subject="Human", predicate="Mortal", p_type=PropositionType.UNIVERSAL_POSITIVE, confidence=1.0),
        Proposition(id="N4", subject="Robot", predicate="Alive", p_type=PropositionType.UNIVERSAL_NEGATIVE, confidence=0.8),
        Proposition(id="N5", subject="Robot", predicate="Alive", p_type=PropositionType.PARTICULAR_POSITIVE, confidence=0.2), # 与N4矛盾
    ]

    try:
        # 初始化引擎
        engine = LogicStressTestEngine(test_network)
        
        # 运行测试（全量扫描以确保发现所有矛盾）
        results = engine.run_stress_test(sample_size=-1)
        
        # 输出结果
        print("\n=== 逻辑应力测试报告 ===")
        if not results:
            print("未发现逻辑冲突。网络自洽性良好。")
        else:
            print(f"发现 {len(results)} 处逻辑冲突：")
            for idx, conflict in enumerate(results, 1):
                print(f"\n[冲突 {idx}]")
                print(f"涉及节点: {conflict['conflict_pair']}")
                print(f"描述: {conflict['description']}")
                print(f"修正提案: {conflict['proposal']}")
                
    except Exception as e:
        logger.critical(f"System failure during stress test: {e}")