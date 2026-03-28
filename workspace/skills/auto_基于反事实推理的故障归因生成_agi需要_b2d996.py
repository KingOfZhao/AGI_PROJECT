"""
高级AGI技能模块：基于反事实推理的故障归因生成

该模块实现了从历史时序数据中自动构建因果图，并利用反事实逻辑计算
最小干预集，以实现设备故障的精准根源分析。

版本: 1.0.0
作者: AGI System Core
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Set, Tuple, Any
from itertools import combinations
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CausalGraph:
    """
    因果图数据结构，用于存储变量间的依赖关系。
    
    Attributes:
        nodes (Set[str]): 图中所有节点的集合。
        edges (Set[Tuple[str, str]]): 有向边的集合 (cause, effect)。
        adjacency_matrix (Optional[np.ndarray]): 邻接矩阵表示。
    """
    nodes: Set[str] = field(default_factory=set)
    edges: Set[Tuple[str, str]] = field(default_factory=set)
    adjacency_matrix: Optional[np.ndarray] = field(default=None, init=False)
    
    def add_edge(self, cause: str, effect: str) -> None:
        """添加因果关系边"""
        self.nodes.add(cause)
        self.nodes.add(effect)
        self.edges.add((cause, effect))
        logger.debug(f"Added causal edge: {cause} -> {effect}")


class FaultAttributionEngine:
    """
    故障归因引擎。
    
    使用PC算法简化版构建因果骨架，并基于反事实推理逻辑寻找最小干预集。
    核心逻辑：如果“移除X会导致Y不再发生”，则X是Y的必要原因。
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        初始化引擎。
        
        Args:
            significance_level (float): 统计显著性水平，用于条件独立性检验。
        """
        if not 0 < significance_level < 1:
            raise ValueError("Significance level must be between 0 and 1")
        self.significance_level = significance_level
        self._graph: Optional[CausalGraph] = None
        
    def _validate_input_data(self, data: pd.DataFrame) -> None:
        """
        辅助函数：验证输入数据的完整性和格式。
        
        Args:
            data (pd.DataFrame): 输入的时序数据。
            
        Raises:
            ValueError: 如果数据包含NaN或非数值类型。
        """
        if data.isnull().values.any():
            raise ValueError("Input data contains NaN values. Please impute or drop them.")
        if not all(data.dtypes.apply(lambda x: np.issubdtype(x, np.number))):
            raise ValueError("Input data must contain only numeric types.")
        if len(data) < 10:
            logger.warning("Sample size is very small, causal inference may be unreliable.")

    def build_causal_graph_from_data(self, data: pd.DataFrame) -> CausalGraph:
        """
        核心函数1：从历史时序数据中自动生成因果图。
        
        基于简化的PC算法逻辑：通过条件独立性检验（偏相关系数）剔除无连接的边，
        并利用时序约束（因前果后）确定因果方向。
        
        Args:
            data (pd.DataFrame): 历史时序数据，列名为传感器/组件名，索引为时间戳。
            
        Returns:
            CausalGraph: 构建完成的因果图对象。
            
        Example:
            >>> engine = FaultAttributionEngine()
            >>> df = pd.DataFrame(np.random.randn(100, 3), columns=['A', 'B', 'C'])
            >>> graph = engine.build_causal_graph_from_data(df)
        """
        logger.info("Starting causal graph construction...")
        self._validate_input_data(data)
        
        self._graph = CausalGraph(nodes=set(data.columns))
        nodes = list(data.columns)
        n_nodes = len(nodes)
        
        # 1. 构建全连接图 (骨架)
        # 2. 剔除非独立边 (简化：使用相关系数矩阵 + 阈值判定)
        # 注意：实际AGI场景应使用PC算法或Granger Causality，此处为演示核心逻辑
        corr_matrix = data.corr().abs()
        threshold = 0.6 # 简化的阈值
        
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                col_i, col_j = nodes[i], nodes[j]
                # 简化逻辑：如果相关性高，则假设存在因果边
                if corr_matrix.iloc[i, j] > threshold:
                    # 在真实时序数据中，通常利用滞后相关性判定方向
                    # 这里假设索引顺序或领域知识已暗示方向，或随机指派模拟不确定性
                    # 模拟：假设列顺序代表了某种潜在因果层级
                    self._graph.add_edge(col_i, col_j)
        
        logger.info(f"Causal graph constructed with {len(self._graph.edges)} edges.")
        return self._graph

    def calculate_minimal_intervention_set(
        self, 
        target_fault: str, 
        hypothesis_space: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        核心函数2：计算最小干预集。
        
        基于反事实原则：寻找一组变量集合S，使得对S进行干预（设为正常值）
        能够最大程度地阻断指向Target的因果流。
        
        Args:
            target_fault (str): 需要分析的故障节点（例如：'Main_Pump_Failure'）。
            hypothesis_space (Optional[Set[str]]): 待验证的潜在原因集合。如果为None，则搜索所有祖先节点。
            
        Returns:
            Set[str]: 推荐的最小干预集。
            
        Raises:
            ValueError: 如果未构建因果图或目标节点不存在。
        """
        if self._graph is None:
            raise RuntimeError("Causal graph not built. Call build_causal_graph_from_data first.")
        if target_fault not in self._graph.nodes:
            raise ValueError(f"Target fault {target_fault} not found in causal graph nodes.")

        logger.info(f"Calculating Minimal Intervention Set for: {target_fault}")
        
        # 获取直接原因
        direct_causes = {src for (src, dst) in self._graph.edges if dst == target_fault}
        
        if not direct_causes:
            logger.warning(f"No direct causes found for {target_fault}. Returning empty set.")
            return set()

        # 反事实验证逻辑 (模拟)：
        # 检查每个原因是否是"必要"原因。
        # 在真实AGI系统中，这会调用仿真器或对比历史数据库。
        # 这里我们模拟一个评分过程：基于连接强度或节点度数
        
        candidates = list(direct_causes)
        minimal_set = set()
        
        # 贪心算法寻找最小集合：优先选择能够"解释"最多的异常传导路径的节点
        # 简单策略：如果只有一个直接原因，它就是最小干预集
        if len(candidates) == 1:
            minimal_set.add(candidates[0])
        else:
            # 模拟反事实评分：选择连接度最高的节点作为关键干预点
            # (模拟逻辑：如果是关键节点，阻断它能切断大部分下游影响)
            node_connectivity = {}
            for node in candidates:
                # 计算该节点作为原因出现的频率
                count = sum(1 for (src, _) in self._graph.edges if src == node)
                node_connectivity[node] = count
            
            # 选择连接度最高的节点作为最小干预集的一部分
            sorted_candidates = sorted(node_connectivity.items(), key=lambda x: x[1], reverse=True)
            
            # 假设我们只需要干预最关键的一个节点即可阻断故障（最小集假设）
            if sorted_candidates:
                minimal_set.add(sorted_candidates[0][0])
        
        logger.info(f"Calculated Minimal Intervention Set: {minimal_set}")
        return minimal_set

    def generate_counterfactual_hypothesis(self, intervention_set: Set[str]) -> List[str]:
        """
        辅助函数：生成自然语言描述的反事实假设。
        
        Args:
            intervention_set (Set[str]): 干预集。
            
        Returns:
            List[str]: 假设陈述列表。
        """
        hypotheses = []
        if not intervention_set:
            return ["No specific interventions identified."]
            
        for node in intervention_set:
            hypothesis = (
                f"Hypothesis: If '{node}' had been in a normal state, "
                f"would the system failure have been prevented?"
            )
            hypotheses.append(hypothesis)
        return hypotheses


# 示例使用
if __name__ == "__main__":
    # 1. 构造模拟工业设备数据
    # 假设有3个组件：Voltage_Sensor, Current_Sensor, Motor_Temp
    # 逻辑：电压异常 -> 电流异常 -> 电机过热
    np.random.seed(42)
    size = 1000
    voltage = np.random.normal(220, 5, size)
    # 电流依赖电压
    current = 0.5 * voltage + np.random.normal(0, 1, size)
    # 温度依赖电流
    temp = 0.8 * current + np.random.normal(0, 2, size)
    
    # 制造故障数据注入 (模拟相关性)
    data = pd.DataFrame({
        'Voltage_Sensor': voltage,
        'Current_Sensor': current,
        'Motor_Temp': temp
    })
    
    try:
        # 2. 初始化引擎
        engine = FaultAttributionEngine(significance_level=0.05)
        
        # 3. 构建因果图
        graph = engine.build_causal_graph_from_data(data)
        print(f"Identified Causal Edges: {graph.edges}")
        
        # 4. 计算故障归因 (假设 Motor_Temp 异常)
        target = 'Motor_Temp'
        intervention_set = engine.calculate_minimal_intervention_set(target)
        
        # 5. 生成反事实假设
        hypotheses = engine.generate_counterfactual_hypothesis(intervention_set)
        
        print("\n--- Fault Attribution Report ---")
        print(f"Target Fault: {target}")
        print(f"Root Cause Candidates (Minimal Intervention Set): {intervention_set}")
        print("Counterfactual Reasoning:")
        for h in hypotheses:
            print(f"- {h}")
            
    except Exception as e:
        logger.error(f"System Error: {str(e)}", exc_info=True)