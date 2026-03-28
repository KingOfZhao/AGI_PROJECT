"""
高级因果推理与反事实分析模块

该模块实现了基于结构化因果模型(SCM)的分析功能，用于区分数据相关性与真实因果关系。
通过碰撞思维识别隐藏混淆变量，并构建正确的因果有向无环图(CDAG)。

核心功能：
- 相关性与因果性自动区分
- 隐藏变量识别与因果图构建
- 反事实场景模拟与验证

Example:
    >>> analyzer = CausalReasoningEngine()
    >>> data = load_drowning_data()
    >>> result = analyzer.full_analysis(data)
    >>> print(result['causal_graph'])
    {'edges': [('Temperature', 'IceCreamSales'), ('Temperature', 'Swimming'), 
               ('Swimming', 'Drowning')], 'confounders': ['Temperature']}
"""

import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CausalGraph:
    """因果图数据结构容器"""
    nodes: List[str]
    edges: List[Tuple[str, str]]
    confounders: List[str]
    correlation_matrix: Optional[np.ndarray] = None

class DataValidationError(Exception):
    """自定义数据验证错误"""
    pass

class CausalReasoningEngine:
    """因果推理引擎核心类
    
    实现基于结构化因果模型的分析，包括：
    1. 相关性计算
    2. 混淆变量识别
    3. 因果图构建
    4. 反事实模拟
    
    Attributes:
        min_samples (int): 最小样本量要求
        significance_level (float): 统计显著性阈值
        correlation_threshold (float): 相关性判定阈值
    """
    
    def __init__(self, min_samples: int = 30, significance_level: float = 0.05,
                 correlation_threshold: float = 0.7):
        """初始化因果推理引擎
        
        Args:
            min_samples: 最小样本量，默认30
            significance_level: 统计显著性阈值，默认0.05
            correlation_threshold: 相关性判定阈值，默认0.7
        """
        self.min_samples = min_samples
        self.significance_level = significance_level
        self.correlation_threshold = correlation_threshold
        logger.info("CausalReasoningEngine initialized with thresholds: "
                   f"corr={correlation_threshold}, sig={significance_level}")

    def validate_input_data(self, data: Union[pd.DataFrame, Dict[str, List]]) -> pd.DataFrame:
        """验证输入数据格式和完整性
        
        Args:
            data: 输入数据，支持DataFrame或字典格式
            
        Returns:
            验证后的DataFrame
            
        Raises:
            DataValidationError: 当数据不满足要求时抛出
        """
        if isinstance(data, dict):
            try:
                df = pd.DataFrame(data)
            except Exception as e:
                raise DataValidationError(f"字典数据转换失败: {str(e)}")
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise DataValidationError("输入数据必须是DataFrame或字典格式")
            
        if len(df) < self.min_samples:
            raise DataValidationError(
                f"样本量不足: {len(df)} < {self.min_samples}")
            
        if df.isnull().any().any():
            missing = df.isnull().sum()
            raise DataValidationError(
                f"数据包含缺失值:\n{missing[missing > 0]}")
                
        logger.info("Input data validated successfully")
        return df

    def calculate_correlations(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算变量间相关性矩阵
        
        Args:
            df: 包含所有变量的DataFrame
            
        Returns:
            字典格式的相关性矩阵，键为'var1_var2'格式
        """
        corr_matrix = df.corr().abs()
        correlations = {}
        
        for i, var1 in enumerate(corr_matrix.columns):
            for j, var2 in enumerate(corr_matrix.columns):
                if i < j:
                    key = f"{var1}_{var2}"
                    correlations[key] = corr_matrix.loc[var1, var2]
                    
        logger.info(f"Calculated correlations between {len(correlations)} variable pairs")
        return correlations

    def identify_confounders(self, df: pd.DataFrame, 
                           target_pair: Tuple[str, str]) -> List[str]:
        """识别可能的混淆变量
        
        使用碰撞思维分析潜在混淆变量，这些变量应该与目标变量对都强相关
        
        Args:
            df: 包含所有变量的DataFrame
            target_pair: 需要分析的目标变量对
            
        Returns:
            识别出的混淆变量列表
        """
        var1, var2 = target_pair
        other_vars = [v for v in df.columns if v not in target_pair]
        confounders = []
        
        for var in other_vars:
            corr1 = abs(df[var].corr(df[var1]))
            corr2 = abs(df[var].corr(df[var2]))
            
            if (corr1 > self.correlation_threshold and 
                corr2 > self.correlation_threshold):
                confounders.append(var)
                logger.debug(f"Identified confounder: {var} (corr1={corr1:.2f}, corr2={corr2:.2f})")
                
        if confounders:
            logger.info(f"Found {len(confounders)} potential confounders for {var1}-{var2}")
        else:
            logger.warning(f"No confounders found for {var1}-{var2}")
            
        return confounders

    def build_causal_graph(self, df: pd.DataFrame, 
                          target_pair: Tuple[str, str],
                          confounders: List[str]) -> CausalGraph:
        """构建因果有向无环图(CDAG)
        
        Args:
            df: 输入数据
            target_pair: 目标变量对
            confounders: 已识别的混淆变量
            
        Returns:
            CausalGraph对象表示因果结构
        """
        nodes = list(df.columns)
        edges = []
        
        # 添加混淆变量到目标变量的边
        for conf in confounders:
            edges.append((conf, target_pair[0]))
            edges.append((conf, target_pair[1]))
            
        # 检查目标变量间的直接因果关系
        partial_corr = self._calculate_partial_correlation(
            df, target_pair[0], target_pair[1], confounders)
            
        if partial_corr < self.correlation_threshold:
            logger.info(f"No direct causal link between {target_pair} "
                       f"(partial_corr={partial_corr:.2f})")
        else:
            logger.warning(f"Possible direct causal link between {target_pair} "
                         f"(partial_corr={partial_corr:.2f})")
            edges.append((target_pair[0], target_pair[1]))
            
        return CausalGraph(nodes=nodes, edges=edges, confounders=confounders)

    def _calculate_partial_correlation(self, df: pd.DataFrame, 
                                      var1: str, var2: str, 
                                      controls: List[str]) -> float:
        """计算控制混淆变量后的偏相关系数
        
        Args:
            df: 输入数据
            var1: 变量1
            var2: 变量2
            controls: 控制变量列表
            
        Returns:
            偏相关系数值
        """
        if not controls:
            return abs(df[var1].corr(df[var2]))
            
        # 简单实现: 计算残差相关性
        from sklearn.linear_model import LinearRegression
        
        X = df[controls].values
        y1 = df[var1].values
        y2 = df[var2].values
        
        model1 = LinearRegression().fit(X, y1)
        residual1 = y1 - model1.predict(X)
        
        model2 = LinearRegression().fit(X, y2)
        residual2 = y2 - model2.predict(X)
        
        return abs(np.corrcoef(residual1, residual2)[0, 1])

    def counterfactual_analysis(self, df: pd.DataFrame, 
                               intervention: str,
                               outcome: str) -> Dict[str, float]:
        """执行反事实分析
        
        Args:
            df: 输入数据
            intervention: 干预变量
            outcome: 结果变量
            
        Returns:
            包含反事实分析结果的字典
        """
        results = {}
        
        # 计算原始相关性
        original_corr = abs(df[intervention].corr(df[outcome]))
        results['original_correlation'] = original_corr
        
        # 识别混淆变量
        confounders = self.identify_confounders(
            df, (intervention, outcome))
            
        if confounders:
            # 计算控制混淆变量后的效果
            partial_corr = self._calculate_partial_correlation(
                df, intervention, outcome, confounders)
            results['controlled_correlation'] = partial_corr
            
            # 计算因果效应衰减比例
            attenuation = (original_corr - partial_corr) / original_corr
            results['attenuation_ratio'] = attenuation
            
            logger.info(f"Counterfactual analysis: Original correlation={original_corr:.2f}, "
                       f"Controlled={partial_corr:.2f}, Attenuation={attenuation:.1%}")
        else:
            results['controlled_correlation'] = original_corr
            results['attenuation_ratio'] = 0.0
            
        return results

    def full_analysis(self, data: Union[pd.DataFrame, Dict[str, List]], 
                     target_pair: Optional[Tuple[str, str]] = None) -> Dict:
        """执行完整的因果分析流程
        
        Args:
            data: 输入数据
            target_pair: 可选的目标变量对，如果为None则自动选择
            
        Returns:
            包含完整分析结果的字典
        """
        # 数据验证
        try:
            df = self.validate_input_data(data)
        except DataValidationError as e:
            logger.error(f"Data validation failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
        # 自动选择目标变量对
        if target_pair is None:
            correlations = self.calculate_correlations(df)
            max_pair = max(correlations.items(), key=lambda x: x[1])
            target_pair = tuple(max_pair[0].split('_'))
            logger.info(f"Auto-selected target pair: {target_pair} (corr={max_pair[1]:.2f})")
            
        # 执行分析
        results = {
            'status': 'success',
            'target_pair': target_pair,
            'correlations': self.calculate_correlations(df),
            'confounders': self.identify_confounders(df, target_pair),
            'counterfactual': self.counterfactual_analysis(df, target_pair[0], target_pair[1])
        }
        
        # 构建因果图
        results['causal_graph'] = self.build_causal_graph(
            df, target_pair, results['confounders'])
            
        # 生成建议
        if results['counterfactual']['attenuation_ratio'] > 0.5:
            results['recommendation'] = (
                f"建议控制混淆变量 {results['confounders']} 而非直接干预 {target_pair[0]}")
        else:
            results['recommendation'] = (
                f"可能存在直接因果关系，但建议进一步验证")
            
        logger.info("Full causal analysis completed successfully")
        return results

def generate_sample_data(n_samples: int = 1000) -> pd.DataFrame:
    """生成示例数据: 冰淇淋销量与溺水事故
    
    Args:
        n_samples: 样本数量
        
    Returns:
        包含以下变量的DataFrame:
        - Temperature: 气温(℃)
        - IceCreamSales: 冰淇淋销量(单位)
        - Swimming: 游泳人数(千人)
        - Drowning: 溺水事故(起)
    """
    np.random.seed(42)
    
    # 生成基础温度数据 (夏季更高)
    month = np.random.randint(1, 13, n_samples)
    temperature = 20 + 15 * np.sin((month - 3) * (2 * np.pi / 12))
    temperature += np.random.normal(0, 3, n_samples)
    
    # 冰淇淋销量受温度影响
    ice_cream = 100 + 5 * temperature + np.random.normal(0, 10, n_samples)
    
    # 游泳人数受温度影响
    swimming = 50 + 3 * temperature + np.random.normal(0, 8, n_samples)
    
    # 溺水事故受游泳人数影响
    drowning = 0.5 * swimming + np.random.normal(0, 5, n_samples)
    
    return pd.DataFrame({
        'Temperature': temperature,
        'IceCreamSales': ice_cream,
        'Swimming': swimming,
        'Drowning': drowning
    })

if __name__ == "__main__":
    # 使用示例
    print("=== 因果推理引擎示例 ===")
    
    # 生成示例数据
    data = generate_sample_data(1000)
    print("\n示例数据前5行:")
    print(data.head())
    
    # 初始化引擎
    engine = CausalReasoningEngine(
        correlation_threshold=0.6,
        significance_level=0.05
    )
    
    # 执行完整分析 (自动选择最相关变量对)
    print("\n执行完整分析...")
    result = engine.full_analysis(data)
    
    # 输出结果
    print("\n=== 分析结果 ===")
    print(f"目标变量对: {result['target_pair']}")
    print(f"识别的混淆变量: {result['confounders']}")
    print(f"原始相关性: {result['counterfactual']['original_correlation']:.2f}")
    print(f"控制后相关性: {result['counterfactual']['controlled_correlation']:.2f}")
    print(f"因果效应衰减: {result['counterfactual']['attenuation_ratio']:.1%}")
    print(f"建议: {result['recommendation']}")
    
    # 输出因果图
    print("\n=== 因果图结构 ===")
    cg = result['causal_graph']
    print(f"节点: {cg.nodes}")
    print("边:")
    for edge in cg.edges:
        print(f"  {edge[0]} -> {edge[1]}")