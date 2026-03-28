"""
工业制造多阶段工艺跨域因果链分析模块

本模块实现了针对热处理->机加工->装配等复杂工业场景的因果发现和反事实推理功能。
通过构建结构因果模型(SCM)识别产品缺陷与上游工艺参数之间的真实因果关系，
并具备反事实推理能力以避免伪关联。

核心功能：
1. 基于工艺流程的因果图构建
2. 混合数据类型的因果发现算法
3. 反事实推理引擎
4. 伪关联检测与消除

输入数据格式要求：
- 工艺参数数据：DataFrame，包含各阶段工艺参数和时间戳
- 质量数据：DataFrame，包含最终产品缺陷指标
- 维护记录：DataFrame，包含设备维护时间信息
"""

import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.stats import pearsonr
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessStage:
    """工艺阶段数据结构"""
    name: str
    parameters: List[str]
    time_column: str = "timestamp"
    maintenance_column: Optional[str] = None


class IndustrialCausalAnalyzer:
    """
    工业制造多阶段工艺因果分析器
    
    功能：
    1. 构建跨工艺阶段的因果图
    2. 执行因果发现算法识别真实因果关系
    3. 执行反事实推理评估参数影响
    4. 检测并消除由维护周期等造成的伪关联
    
    示例用法：
    >>> analyzer = IndustrialCausalAnalyzer(
    ...     stages=[
    ...         ProcessStage("热处理", ["temperature", "duration"]),
    ...         ProcessStage("机加工", ["speed", "feed_rate"]),
    ...         ProcessStage("装配", ["torque", "alignment"])
    ...     ],
    ...     quality_metrics=["defect_size", "crack_depth"]
    ... )
    >>> causal_graph = analyzer.build_causal_graph(process_data, quality_data)
    >>> interventions = analyzer.perform_counterfactual_analysis(
    ...     {"热处理.temperature": 850},
    ...     baseline_data=process_data
    ... )
    """
    
    def __init__(self, 
                 stages: List[ProcessStage],
                 quality_metrics: List[str],
                 correlation_threshold: float = 0.7,
                 significance_level: float = 0.05):
        """
        初始化因果分析器
        
        参数:
            stages: 工艺阶段定义列表
            quality_metrics: 最终产品质量指标列表
            correlation_threshold: 相关性阈值用于初步筛选
            significance_level: 统计显著性水平
        """
        self.stages = stages
        self.quality_metrics = quality_metrics
        self.correlation_threshold = correlation_threshold
        self.significance_level = significance_level
        self.causal_graph = None
        self._validate_inputs()
        
    def _validate_inputs(self) -> None:
        """验证输入参数的有效性"""
        if not self.stages:
            raise ValueError("至少需要一个工艺阶段")
            
        if not self.quality_metrics:
            raise ValueError("至少需要一个质量指标")
            
        if not 0 <= self.correlation_threshold <= 1:
            raise ValueError("相关性阈值必须在0-1之间")
            
        if not 0 <= self.significance_level <= 1:
            raise ValueError("显著性水平必须在0-1之间")
            
        logger.info("输入参数验证通过")
    
    def build_causal_graph(self, 
                          process_data: pd.DataFrame,
                          quality_data: pd.DataFrame,
                          maintenance_data: Optional[pd.DataFrame] = None) -> Dict[str, List[str]]:
        """
        构建跨工艺阶段的因果图
        
        参数:
            process_data: 包含各工艺阶段参数的DataFrame
            quality_data: 包含最终产品质量指标的DataFrame
            maintenance_data: 设备维护记录DataFrame(可选)
            
        返回:
            因果图字典，格式为 {结果变量: [原因变量列表]}
            
        异常:
            ValueError: 如果输入数据缺少必要列
        """
        self._validate_data_inputs(process_data, quality_data, maintenance_data)
        
        logger.info("开始构建因果图...")
        
        # 合并工艺和质量数据
        merged_data = self._merge_process_quality_data(process_data, quality_data)
        
        # 初步相关性分析
        potential_causes = self._identify_potential_causes(merged_data)
        
        # 因果方向推断
        causal_graph = self._infer_causal_directions(merged_data, potential_causes)
        
        # 如果有维护数据，检测并消除伪关联
        if maintenance_data is not None:
            causal_graph = self._eliminate_spurious_correlations(
                causal_graph, merged_data, maintenance_data
            )
        
        self.causal_graph = causal_graph
        logger.info("因果图构建完成")
        return causal_graph
    
    def perform_counterfactual_analysis(self,
                                      intervention: Dict[str, Union[float, int]],
                                      baseline_data: pd.DataFrame,
                                      num_samples: int = 1000) -> Dict[str, Dict[str, float]]:
        """
        执行反事实推理分析
        
        参数:
            intervention: 干预变量及其目标值，如 {"热处理.temperature": 850}
            baseline_data: 基线数据用于反事实推理
            num_samples: 用于反事实推理的样本数量
            
        返回:
            反事实推理结果，格式为 {质量指标: {"expected_value": 预期值, "change": 变化量}}
            
        异常:
            ValueError: 如果因果图未构建或干预变量无效
        """
        if self.causal_graph is None:
            raise RuntimeError("必须先构建因果图才能执行反事实分析")
            
        if not intervention:
            raise ValueError("干预变量不能为空")
            
        logger.info(f"开始反事实分析，干预变量: {intervention}")
        
        # 验证干预变量
        self._validate_intervention(intervention, baseline_data)
        
        # 执行反事实推理
        results = {}
        for metric in self.quality_metrics:
            # 这里简化实现，实际应用中应使用更复杂的因果模型
            expected_value = self._estimate_counterfactual(
                metric, intervention, baseline_data, num_samples
            )
            baseline_value = baseline_data[metric].mean()
            results[metric] = {
                "expected_value": expected_value,
                "change": expected_value - baseline_value,
                "percent_change": (expected_value - baseline_value) / baseline_value * 100
            }
        
        logger.info("反事实分析完成")
        return results
    
    def _validate_data_inputs(self,
                            process_data: pd.DataFrame,
                            quality_data: pd.DataFrame,
                            maintenance_data: Optional[pd.DataFrame]) -> None:
        """验证输入数据完整性"""
        required_columns = []
        for stage in self.stages:
            required_columns.extend(stage.parameters)
            required_columns.append(stage.time_column)
            
        missing_process_cols = set(required_columns) - set(process_data.columns)
        if missing_process_cols:
            raise ValueError(f"工艺数据缺少必要列: {missing_process_cols}")
            
        missing_quality_cols = set(self.quality_metrics) - set(quality_data.columns)
        if missing_quality_cols:
            raise ValueError(f"质量数据缺少必要列: {missing_quality_cols}")
            
        if maintenance_data is not None:
            for stage in self.stages:
                if stage.maintenance_column and stage.maintenance_column not in maintenance_data.columns:
                    raise ValueError(f"维护数据缺少列: {stage.maintenance_column}")
    
    def _merge_process_quality_data(self,
                                  process_data: pd.DataFrame,
                                  quality_data: pd.DataFrame) -> pd.DataFrame:
        """合并工艺和质量数据"""
        # 简化实现，实际应用中可能需要更复杂的时间对齐
        merged = pd.concat([process_data, quality_data], axis=1)
        return merged.loc[:, ~merged.columns.duplicated()]
    
    def _identify_potential_causes(self, data: pd.DataFrame) -> Dict[str, List[str]]:
        """通过相关性分析识别潜在原因变量"""
        potential_causes = defaultdict(list)
        
        for metric in self.quality_metrics:
            for stage in self.stages:
                for param in stage.parameters:
                    corr, p_value = pearsonr(data[metric], data[param])
                    if abs(corr) > self.correlation_threshold and p_value < self.significance_level:
                        potential_causes[metric].append(param)
                        logger.debug(
                            f"发现潜在因果关系: {param} -> {metric} "
                            f"(相关系数: {corr:.3f}, p值: {p_value:.4f})"
                        )
        
        return potential_causes
    
    def _infer_causal_directions(self,
                               data: pd.DataFrame,
                               potential_causes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """推断因果方向(简化实现)"""
        # 实际应用中应使用更复杂的因果发现算法
        causal_graph = {}
        
        for effect, causes in potential_causes.items():
            # 这里简化处理，实际应考虑时间顺序和领域知识
            valid_causes = []
            for cause in causes:
                # 检查是否是前面阶段的参数
                cause_stage = next(
                    (s for s in self.stages if cause in s.parameters), None
                )
                if cause_stage:
                    valid_causes.append(cause)
            
            if valid_causes:
                causal_graph[effect] = valid_causes
        
        return causal_graph
    
    def _eliminate_spurious_correlations(self,
                                       causal_graph: Dict[str, List[str]],
                                       data: pd.DataFrame,
                                       maintenance_data: pd.DataFrame) -> Dict[str, List[str]]:
        """检测并消除由维护周期等造成的伪关联"""
        refined_graph = {}
        
        for effect, causes in causal_graph.items():
            valid_causes = []
            for cause in causes:
                # 检查是否与维护周期相关
                is_spurious = False
                for stage in self.stages:
                    if cause in stage.parameters and stage.maintenance_column:
                        # 简化检查，实际应更复杂
                        maint_corr, _ = pearsonr(
                            data[cause], 
                            maintenance_data[stage.maintenance_column]
                        )
                        if abs(maint_corr) > 0.5:  # 与维护强相关可能是伪关联
                            is_spurious = True
                            logger.warning(
                                f"检测到潜在伪关联: {cause} -> {effect} "
                                f"(与维护相关系数: {maint_corr:.3f})"
                            )
                            break
                
                if not is_spurious:
                    valid_causes.append(cause)
            
            if valid_causes:
                refined_graph[effect] = valid_causes
        
        return refined_graph
    
    def _validate_intervention(self,
                             intervention: Dict[str, Union[float, int]],
                             data: pd.DataFrame) -> None:
        """验证干预变量的有效性"""
        for var in intervention.keys():
            if var not in data.columns:
                raise ValueError(f"干预变量 {var} 不在数据中")
                
            # 检查是否是工艺参数
            is_process_param = any(
                var in stage.parameters for stage in self.stages
            )
            if not is_process_param:
                raise ValueError(f"干预变量 {var} 不是有效的工艺参数")
    
    def _estimate_counterfactual(self,
                               metric: str,
                               intervention: Dict[str, Union[float, int]],
                               data: pd.DataFrame,
                               num_samples: int) -> float:
        """
        估计反事实结果(简化实现)
        
        实际应用中应使用更复杂的因果模型，如:
        1. 结构方程模型(SEM)
        2. 潜在结果框架
        3. 因果森林等高级方法
        """
        # 这里简化处理，使用线性近似
        baseline_value = data[metric].mean()
        total_effect = 0.0
        
        for cause, value in intervention.items():
            if cause in self.causal_graph.get(metric, []):
                # 简单线性效应估计
                effect_size = np.polyfit(data[cause], data[metric], 1)[0]
                total_effect += effect_size * (value - data[cause].mean())
        
        return baseline_value + total_effect


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000
    
    # 热处理阶段数据
    temp = np.random.normal(800, 50, n_samples)
    duration = np.random.normal(60, 10, n_samples)
    timestamp = pd.date_range("2023-01-01", periods=n_samples, freq="H")
    
    # 机加工阶段数据
    speed = np.random.normal(1200, 100, n_samples)
    feed_rate = np.random.normal(0.5, 0.1, n_samples)
    
    # 装配阶段数据
    torque = np.random.normal(50, 5, n_samples)
    alignment = np.random.normal(0.1, 0.02, n_samples)
    
    # 质量指标(与某些工艺参数相关)
    defect_size = 0.5 * temp + 0.3 * speed + np.random.normal(0, 10, n_samples)
    crack_depth = 0.7 * duration - 0.2 * alignment + np.random.normal(0, 5, n_samples)
    
    # 创建DataFrame
    process_data = pd.DataFrame({
        "热处理.temperature": temp,
        "热处理.duration": duration,
        "机加工.speed": speed,
        "机加工.feed_rate": feed_rate,
        "装配.torque": torque,
        "装配.alignment": alignment,
        "timestamp": timestamp
    })
    
    quality_data = pd.DataFrame({
        "defect_size": defect_size,
        "crack_depth": crack_depth
    })
    
    # 创建维护数据(模拟维护周期影响)
    maintenance_data = pd.DataFrame({
        "热处理.maintenance": np.random.choice([0, 1], size=n_samples, p=[0.9, 0.1]),
        "机加工.maintenance": np.random.choice([0, 1], size=n_samples, p=[0.95, 0.05])
    })
    
    # 定义工艺阶段
    stages = [
        ProcessStage("热处理", ["热处理.temperature", "热处理.duration"], maintenance_column="热处理.maintenance"),
        ProcessStage("机加工", ["机加工.speed", "机加工.feed_rate"], maintenance_column="机加工.maintenance"),
        ProcessStage("装配", ["装配.torque", "装配.alignment"])
    ]
    
    # 创建分析器实例
    analyzer = IndustrialCausalAnalyzer(
        stages=stages,
        quality_metrics=["defect_size", "crack_depth"]
    )
    
    # 构建因果图
    causal_graph = analyzer.build_causal_graph(process_data, quality_data, maintenance_data)
    print("发现的因果关系:", causal_graph)
    
    # 执行反事实分析
    intervention = {"热处理.temperature": 850}
    results = analyzer.perform_counterfactual_analysis(intervention, process_data)
    print("\n反事实分析结果:")
    for metric, values in results.items():
        print(f"{metric}: 预期值={values['expected_value']:.2f}, 变化={values['change']:.2f} ({values['percent_change']:.1f}%)")