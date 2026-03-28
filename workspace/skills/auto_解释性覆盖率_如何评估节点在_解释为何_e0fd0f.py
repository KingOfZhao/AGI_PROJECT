"""
Name: auto_解释性覆盖率_如何评估节点在_解释为何_e0fd0f
Description: AGI系统解释性覆盖率评估模块。

本模块旨在量化AGI推理链中各个节点对“解释为何这样做”的贡献度。
它通过对比“推理执行图”与“解释生成图”来识别“黑盒节点”，
并计算节点的“解释贡献指数”，为AGI的可解释性优化提供数据支持。

Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    """
    用于存储单个节点的解释性指标。
    
    Attributes:
        id (str): 节点的唯一标识符。
        execution_weight (float): 该节点在推理链中的权重（基于调用频率或深度）。
        is_cited_in_explanation (bool): 该节点是否在生成解释时被引用。
        contribution_score (float): 计算后的解释贡献指数。
    """
    id: str
    execution_weight: float = 0.0
    is_cited_in_explanation: bool = False
    contribution_score: float = 0.0


class InterpretabilityCoverageEvaluator:
    """
    评估AGI节点解释性覆盖率和贡献度的核心类。
    
    该类实现了对比推理路径与解释路径的算法，能够识别高频调用但在解释中被忽略的节点，
    并据此调整节点的层级或权重。
    
    Input Data Format:
        - execution_trace: List[str] - 推理过程中经过的节点ID列表。
        - explanation_trace: List[str] - 生成解释时引用的节点ID列表。
        - node_metadata: Dict[str, Dict] - 节点的额外信息（可选），如基础权重。
    
    Output Data Format:
        - Dict[str, float]: 节点ID到其贡献指数的映射。
    """

    def __init__(self, decay_factor: float = 0.95):
        """
        初始化评估器。
        
        Args:
            decay_factor (float): 推理链中的位置衰减因子，越靠后的步骤可能权重越低，
                                  或者用于调整未引用节点的惩罚力度。
        """
        if not 0.0 < decay_factor <= 1.0:
            logger.warning("Decay factor should typically be between 0 and 1.")
        
        self.decay_factor = decay_factor
        self.metrics_db: Dict[str, NodeMetrics] = {}
        logger.info(f"InterpretabilityCoverageEvaluator initialized with decay_factor={decay_factor}")

    def _validate_trace_data(self, trace: List[str], name: str) -> bool:
        """
        辅助函数：验证输入的轨迹数据是否有效。
        
        Args:
            trace (List[str]): 待验证的ID列表。
            name (str): 数据名称（用于日志）。
            
        Returns:
            bool: 数据是否有效。
        """
        if not isinstance(trace, list):
            logger.error(f"Invalid {name}: Expected list, got {type(trace)}")
            return False
        if not all(isinstance(i, str) for i in trace):
            logger.error(f"Invalid {name}: All elements must be strings.")
            return False
        return True

    def _calculate_execution_weights(self, execution_trace: List[str]) -> Dict[str, float]:
        """
        辅助函数：根据节点在推理链中的出现频率计算执行权重。
        
        Args:
            execution_trace (List[str]): 推理路径节点列表。
            
        Returns:
            Dict[str, float]: 节点ID到归一化权重的映射。
        """
        weight_counts: Dict[str, float] = {}
        total_steps = len(execution_trace)
        
        if total_steps == 0:
            return {}

        for node_id in execution_trace:
            # 简单的频率计数，实际场景可结合位置深度加权
            weight_counts[node_id] = weight_counts.get(node_id, 0) + 1.0
            
        # 归一化处理
        normalized_weights = {
            k: v / total_steps for k, v in weight_counts.items()
        }
        return normalized_weights

    def build_evaluation_model(
        self, 
        execution_trace: List[str], 
        explanation_trace: List[str]
    ) -> None:
        """
        核心函数 1: 构建评估模型，处理推理轨迹和解释轨迹。
        
        该方法清洗数据，计算基础执行权重，并标记节点是否被解释引用。
        
        Args:
            execution_trace (List[str]): AGI推理过程中实际经过的节点ID列表。
            explanation_trace (List[str]): AGI生成解释时引用的节点ID列表。
        
        Raises:
            ValueError: 如果输入数据格式不正确。
        """
        logger.info("Building evaluation model...")
        
        # 数据验证
        if not self._validate_trace_data(execution_trace, "execution_trace") or \
           not self._validate_trace_data(explanation_trace, "explanation_trace"):
            raise ValueError("Invalid input trace data provided.")

        # 计算执行权重
        exec_weights = self._calculate_execution_weights(execution_trace)
        
        # 确定解释引用集合
        cited_nodes: Set[str] = set(explanation_trace)
        
        # 构建内部指标数据库
        self.metrics_db.clear()
        
        for node_id, weight in exec_weights.items():
            is_cited = node_id in cited_nodes
            self.metrics_db[node_id] = NodeMetrics(
                id=node_id,
                execution_weight=weight,
                is_cited_in_explanation=is_cited
            )
        
        # 处理仅在解释中出现但在执行中未出现的节点（理论上不应发生，但需防御性编程）
        for node_id in cited_nodes:
            if node_id not in self.metrics_db:
                logger.warning(f"Node {node_id} cited in explanation but not found in execution trace.")
                self.metrics_db[node_id] = NodeMetrics(
                    id=node_id,
                    execution_weight=0.0, # 视为未执行但被引用
                    is_cited_in_explanation=True
                )
                
        logger.info(f"Model built with {len(self.metrics_db)} nodes analyzed.")

    def calculate_contribution_indices(self) -> Dict[str, float]:
        """
        核心函数 2: 计算解释贡献指数。
        
        算法逻辑：
        1. 基础贡献由 execution_weight 决定。
        2. 如果节点被引用 (is_cited_in_explanation = True)，贡献指数保留正向权重。
        3. 如果节点未被引用 (is_cited_in_explanation = False)，这是一个“潜在黑盒”，
           其贡献指数变为负数（或根据业务逻辑大幅降低），表示其对可解释性的阻碍。
           
        公式示例：
        Score = (Weight * Alpha) - (Weight * (1-Cited) * Penalty)
        
        Returns:
            Dict[str, float]: 节点ID到解释贡献指数的映射字典。
        """
        if not self.metrics_db:
            logger.warning("Metrics DB is empty. Run build_evaluation_model first.")
            return {}

        results: Dict[str, float] = {}
        penalty_factor = 1.5 # 惩罚系数：未解释的高频节点具有负外部性
        
        logger.info("Calculating contribution indices...")
        
        for node_id, metrics in self.metrics_db.items():
            # 如果节点被引用，其解释贡献等于其执行权重（正向）
            if metrics.is_cited_in_explanation:
                score = metrics.execution_weight
            else:
                # 如果节点未被引用，且在推理中很重要，则是“黑盒”，得分为负
                # 这里的逻辑是：未解释的节点越重要，系统的可解释性越差
                score = - (metrics.execution_weight * penalty_factor)
            
            # 更新内部对象
            metrics.contribution_score = score
            results[node_id] = score
            
            # 记录关键决策日志
            if metrics.execution_weight > 0.1 and not metrics.is_cited_in_explanation:
                logger.warning(
                    f"Blackbox detected: Node '{node_id}' has high execution weight "
                    f"({metrics.execution_weight:.2f}) but was NOT cited in explanation. "
                    f"Score: {score:.2f}"
                )

        return results

    def suggest_hierarchy_adjustment(self, threshold: float = -0.1) -> List[str]:
        """
        辅助功能：建议需要降低层级的节点列表。
        
        Args:
            threshold (float): 贡献指数的阈值，低于此值的节点建议降级。
            
        Returns:
            List[str]: 建议降级的节点ID列表。
        """
        if not self.metrics_db:
            return []
            
        downgrade_suggestions = [
            node_id for node_id, m in self.metrics_db.items() 
            if m.contribution_score < threshold
        ]
        
        logger.info(f"Identified {len(downgrade_suggestions)} nodes for potential downgrade.")
        return downgrade_suggestions

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 模拟数据
    # 推理路径：A -> B -> C -> B -> D (B被调用了2次，权重较高)
    # 解释路径：A -> C -> D (解释中引用了A, C, D，但漏掉了高频的B)
    
    execution_path = ["node_A", "node_B", "node_C", "node_B", "node_D"]
    explanation_path = ["node_A", "node_C", "node_D"] # node_B is missing here

    print("--- Starting Interpretability Coverage Evaluation ---")
    
    try:
        evaluator = InterpretabilityCoverageEvaluator()
        
        # 1. 构建模型
        evaluator.build_evaluation_model(execution_path, explanation_path)
        
        # 2. 计算指数
        scores = evaluator.calculate_contribution_indices()
        
        print("\nEvaluation Results:")
        for node, score in sorted(scores.items(), key=lambda item: item[1]):
            status = "Cited" if evaluator.metrics_db[node].is_cited_in_explanation else "Uncited"
            print(f"Node: {node:<10} | Score: {score:<10.4f} | Status: {status}")
            
        # 3. 获取降级建议
        to_downgrade = evaluator.suggest_hierarchy_adjustment()
        if to_downgrade:
            print(f"\nRecommendation: Consider lowering hierarchy for blackbox nodes: {to_downgrade}")
        else:
            print("\nSystem interpretability is healthy.")
            
    except ValueError as e:
        print(f"Error: {e}")