"""
模块名称: auto_从非结构化交互日志中提取_隐含知识_的半_880bf1
领域: 数据挖掘/行为分析
描述: 本模块实现了一个半监督学习系统，旨在从非结构化的人机交互日志中提取隐含知识。
    系统通过聚类分析操作序列（如代码修改模式），自动抽象出新的概念节点（如“防御性编程”），
    并能够区分噪音与有效模式。支持通过人类反馈（半监督）来优化知识提取结果。
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImplicitKnowledgeExtractor:
    """
    从非结构化交互日志中提取隐含知识的提取器。

    该类使用序列聚类技术来识别用户行为中的重复模式，并将其抽象为概念。
    它包含处理噪音的机制，并允许通过外部反馈进行半监督微调。

    Attributes:
        vectorizer (CountVectorizer): 用于将操作序列转换为数值特征的向量化器。
        clustering_model (DBSCAN): 用于聚类和噪音检测的密度聚类模型。
        knowledge_base (Dict[str, Any]): 存储提取出的概念和模式的字典。
    """

    def __init__(self, min_pattern_freq: int = 2, eps: float = 0.5):
        """
        初始化隐含知识提取器。

        Args:
            min_pattern_freq (int): 形成一个有效概念所需的最小序列数量。
            eps (float): DBSCAN算法的邻域半径，用于控制聚类的松紧度。
        """
        self.min_pattern_freq = min_pattern_freq
        self.eps = eps
        # 使用n-gram特征提取序列模式
        self.vectorizer = CountVectorizer(tokenizer=lambda x: x, lowercase=False, token_pattern=None)
        self.clustering_model = DBSCAN(eps=eps, min_samples=min_pattern_freq, metric='cosine')
        self.knowledge_base: Dict[str, List[str]] = {}

    def _validate_logs(self, logs: List[List[str]]) -> None:
        """
        辅助函数：验证输入日志的格式和有效性。

        Args:
            logs (List[List[str]]): 交互日志列表，每个日志是一个操作字符串列表。

        Raises:
            ValueError: 如果日志为空、不是列表或包含无效数据。
        """
        if not isinstance(logs, list):
            raise ValueError("输入日志必须是一个列表。")
        if not logs:
            raise ValueError("输入日志不能为空。")
        for i, log in enumerate(logs):
            if not isinstance(log, list):
                raise ValueError(f"日志条目 {i} 必须是列表（操作序列）。")
            if not all(isinstance(action, str) for action in log):
                raise ValueError(f"日志条目 {i} 包含非字符串的操作。")

    def _preprocess_sequences(self, logs: List[List[str]]) -> np.ndarray:
        """
        辅助函数：将操作序列转换为数值特征矩阵。

        Args:
            logs (List[List[str]]): 原始操作序列。

        Returns:
            np.ndarray: 特征矩阵。
        """
        # 将列表转换为字符串以便向量化处理，或者直接使用列表作为token
        # 这里我们直接传入列表，CountVectorizer会处理
        try:
            features = self.vectorizer.fit_transform(logs)
            return features.toarray()
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            raise

    def extract_patterns(self, logs: List[List[str]]) -> Dict[int, List[int]]:
        """
        核心函数 1：从日志中提取行为模式并执行聚类。

        此函数将原始日志转换为特征，并使用DBSCAN进行聚类。
        DBSCAN能够自动将稀疏的、不常见的序列标记为噪音（标签-1）。

        Args:
            logs (List[List[str]]): 非结构化交互日志。
                格式示例: [["open_file", "edit_line", "save"], ["edit_line", "save", "run_test"]]

        Returns:
            Dict[int, List[int]]: 聚类结果，键为簇ID，值为该簇中日志的索引列表。
                噪音点的簇ID为-1。
        """
        logger.info("开始验证和预处理日志...")
        self._validate_logs(logs)

        logger.info("正在提取序列特征...")
        feature_matrix = self._preprocess_sequences(logs)

        logger.info(f"正在执行聚类分析 (eps={self.eps}, min_samples={self.min_pattern_freq})...")
        try:
            labels = self.clustering_model.fit_predict(feature_matrix)
        except Exception as e:
            logger.error(f"聚类过程中发生错误: {e}")
            raise

        # 统计聚类结果
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        logger.info(f"聚类完成: 发现 {n_clusters} 个模式簇, {n_noise} 个噪音点。")

        # 组织聚类结果
        clusters: Dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)

        return clusters

    def abstract_concepts(self, logs: List[List[str]], clusters: Dict[int, List[int]]) -> Dict[str, Any]:
        """
        核心函数 2：将聚类结果抽象为显式的“概念节点”。

        对于每个有效的簇（非噪音），分析其操作序列，生成代表性的模式描述。
        如果簇太小或被标记为噪音，则忽略。

        Args:
            logs (List[List[str]]): 原始交互日志。
            clusters (Dict[int, List[int]]): extract_patterns 的输出。

        Returns:
            Dict[str, Any]: 提取出的知识库。
                格式: {
                    "Concept_0": {"pattern": ["edit", "save", "test"], "count": 10, "type": "Standard_Workflow"},
                    ...
                }
        """
        logger.info("正在抽象概念节点...")
        new_knowledge = {}

        # 过滤掉噪音簇 (-1)
        valid_clusters = {k: v for k, v in clusters.items() if k != -1}

        if not valid_clusters:
            logger.warning("未发现有效模式簇，知识库未更新。")
            return self.knowledge_base

        for cluster_id, indices in valid_clusters.items():
            cluster_logs = [logs[i] for i in indices]
            
            # 简单的抽象逻辑：找到最常见的序列（这里简化为取簇中心的序列或第一个序列）
            # 在实际应用中，可以使用序列挖掘算法如PrefixSpan
            representative_seq = self._find_representative_sequence(cluster_logs)
            
            concept_name = f"Implicit_Pattern_{cluster_id}"
            # 尝试根据序列内容推断一个更语义化的标签（模拟）
            semantic_label = self._infer_semantic_label(representative_seq)

            new_knowledge[concept_name] = {
                "pattern": representative_seq,
                "frequency": len(indices),
                "semantic_label": semantic_label,
                "type": "Discovered_Concept"
            }
            
            logger.info(f"抽象出新概念: {concept_name} (标签: {semantic_label}), 包含 {len(indices)} 个实例。")

        self.knowledge_base.update(new_knowledge)
        return self.knowledge_base

    def incorporate_feedback(self, sequence: List[str], label: str) -> None:
        """
        核心函数 3 (半监督): 将人类反馈整合到系统中。

        允许人类专家将特定的操作序列标记为特定的概念（如“防御性编程”）。
        这会直接更新知识库，模拟半监督学习中的标签传播或修正。

        Args:
            sequence (List[str]): 操作序列。
            label (str): 人类赋予的概念标签。
        """
        logger.info(f"接收到人类反馈: 序列 {sequence} 被标记为 '{label}'")
        
        # 检查是否已存在相似概念，这里简单处理，直接添加或更新
        # 在更复杂的实现中，这可能触发模型的重训练或参数调整
        concept_key = f"Expert_Validated_{label}"
        
        if concept_key not in self.knowledge_base:
            self.knowledge_base[concept_key] = {
                "pattern": sequence,
                "frequency": 1,
                "semantic_label": label,
                "type": "Expert_Validated"
            }
        else:
            self.knowledge_base[concept_key]["frequency"] += 1
            
        logger.info("知识库已根据反馈更新。")

    def _find_representative_sequence(self, cluster_logs: List[List[str]]) -> List[str]:
        """
        辅助函数：在簇中找到最具代表性的序列。
        这里简化为返回出现频率最高的序列，或者长度中位数的序列。
        """
        # 简单策略：返回簇中第一个序列作为代表（实际中应计算质心）
        return cluster_logs[0]

    def _infer_semantic_label(self, sequence: List[str]) -> str:
        """
        辅助函数：基于序列内容推断语义标签。
        这是一个模拟函数，实际中可能需要调用LLM或规则引擎。
        """
        if "test" in sequence and "fix" in sequence:
            return "Debugging_Routine"
        elif "review" in sequence:
            return "Code_Review_Habit"
        elif "save" in sequence and "backup" in sequence:
            return "Defensive_Programming"
        else:
            return "Generic_Operational_Pattern"


# 使用示例
if __name__ == "__main__":
    # 模拟非结构化交互日志
    # 格式: List[List[str]]
    interaction_logs = [
        ["open", "edit", "save", "test"],  # 模式 A
        ["open", "edit", "save", "test"],  # 模式 A
        ["open", "edit", "save", "edit", "save", "test"],  # 模式 B (更谨慎)
        ["open", "edit", "save", "edit", "save", "test"],  # 模式 B
        ["open", "edit", "save", "edit", "save", "test"],  # 模式 B
        ["random_click", "idle", "random_click"],  # 噪音
        ["open", "review", "close"],  # 模式 C
        ["open", "review", "close"],  # 模式 C
    ]

    try:
        # 初始化提取器
        extractor = ImplicitKnowledgeExtractor(min_pattern_freq=2, eps=0.8)

        # 1. 提取模式（区分噪音）
        clusters = extractor.extract_patterns(interaction_logs)

        # 2. 抽象概念
        knowledge = extractor.abstract_concepts(interaction_logs, clusters)
        print("\n=== 自动提取的知识库 ===")
        for k, v in knowledge.items():
            print(f"{k}: {v}")

        # 3. 模拟半监督反馈
        # 人类专家指出某个特定序列是“防御性编程”
        feedback_seq = ["backup", "edit", "save", "verify"]
        extractor.incorporate_feedback(feedback_seq, "Defensive_Programming_Strategy")

        print("\n=== 引入人类反馈后的知识库 ===")
        for k, v in knowledge.items():
            print(f"{k}: {v}")

    except Exception as e:
        logger.error(f"系统运行失败: {e}")