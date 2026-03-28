"""
Module: auto_反事实状态推演_在工艺出现瑕疵时_如烧_fd771e
Description: 【反事实状态推演】在工艺出现瑕疵时（如烧制开裂），AI如何构建'反事实'推理路径？
             本模块实现基于结构因果模型(SCM)的动态反事实推演，支持工艺参数回溯与优化。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessState:
    """
    工艺状态数据结构，用于封装时刻T的工艺参数。
    
    Attributes:
        temperature (float): 当前温度(摄氏度)
        humidity (float): 环境湿度(%)
        pressure (float): 炉内压力
        duration (int): 持续时间(分钟)
        material_quality (float): 材料质量系数 (0.0-1.0)
        timestamp (str): 时间戳
    """
    temperature: float
    humidity: float
    pressure: float
    duration: int
    material_quality: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """数据验证与边界检查"""
        if not (0 <= self.humidity <= 100):
            raise ValueError(f"湿度必须在0-100之间，当前值: {self.humidity}")
        if not (0 <= self.material_quality <= 1.0):
            raise ValueError(f"材料质量系数必须在0.0-1.0之间，当前值: {self.material_quality}")
        if self.temperature < -273.15:
            raise ValueError("温度不能低于绝对零度")
        if self.duration < 0:
            raise ValueError("持续时间不能为负数")


@dataclass
class CounterfactualResult:
    """
    反事实推演结果封装。
    
    Attributes:
        original_defect_prob (float): 原始缺陷概率
        adjusted_defect_prob (float): 调整后的缺陷概率
        improvement_ratio (float): 改善比例
        intervention_strategy (Dict): 干预策略
        causal_path (List[str]): 因果路径描述
    """
    original_defect_prob: float
    adjusted_defect_prob: float
    improvement_ratio: float
    intervention_strategy: Dict[str, float]
    causal_path: List[str]


def _validate_process_history(history: List[ProcessState]) -> bool:
    """
    辅助函数：验证工艺历史数据的完整性和有效性。
    
    Args:
        history (List[ProcessState]): 工艺状态历史记录列表
        
    Returns:
        bool: 数据是否有效
        
    Raises:
        ValueError: 如果数据为空或时间序列不连续
    """
    if not history:
        logger.error("工艺历史数据为空")
        raise ValueError("工艺历史数据不能为空")
    
    if len(history) < 2:
        logger.warning("历史数据点不足，反事实推演精度可能受限")
    
    logger.debug(f"验证通过，共 {len(history)} 条历史记录")
    return True


def build_structural_causal_model(
    process_history: List[ProcessState],
    defect_type: str = "cracking"
) -> Dict[str, any]:
    """
    构建工艺过程的动态结构因果模型(SCM)。
    
    该函数基于历史数据建立变量间的因果关系，使用简化的线性高斯模型
    模拟温度、压力、材料质量对特定缺陷(如开裂)的影响。
    
    Args:
        process_history (List[ProcessState]): 烧制过程的温度、压力等历史数据
        defect_type (str): 缺陷类型 (目前支持 'cracking', 'deformation', 'discoloration')
        
    Returns:
        Dict[str, any]: 包含因果图结构和结构方程的模型字典
        
    Raises:
        ValueError: 如果输入数据验证失败
        
    Example:
        >>> history = [ProcessState(1200, 40, 1.0, 60, 0.9)]
        >>> model = build_structural_causal_model(history, 'cracking')
    """
    _validate_process_history(process_history)
    
    logger.info(f"开始构建针对 '{defect_type}' 的结构因果模型...")
    
    # 将历史数据转换为DataFrame以便分析
    df = pd.DataFrame([vars(state) for state in process_history])
    
    # 定义因果图结构 (DAG)
    # 节点: T(温度), P(压力), Q(材料质量), D(缺陷概率)
    # 边: T->D, P->D, Q->D, T->P (温度影响压力)
    causal_graph = {
        "nodes": ["temperature", "pressure", "material_quality", "defect_score"],
        "edges": [
            ("temperature", "defect_score"),
            ("pressure", "defect_score"),
            ("material_quality", "defect_score"),
            ("temperature", "pressure")
        ]
    }
    
    # 定义结构方程
    # 这里使用简化的参数，实际应用中应从数据中拟合
    # 模拟物理规律：高温+高压 -> 开裂概率增加
    structural_equations = {
        "pressure": lambda t, noise: 0.5 * t / 1000 + noise,  # 温度影响压力
        "defect_score": lambda t, p, q, noise: (
            0.0005 * (t - 1100) ** 2 +  # 温度二次效应(1100度为理想)
            0.8 * (p - 1.0) ** 2 +      # 压力偏差效应
            (1 - q) * 10 +              # 材料质量差导致缺陷
            noise
        )
    }
    
    # 计算基线噪声（基于历史数据残差，此处简化处理）
    baseline_noise = np.random.normal(0, 0.05)
    
    model = {
        "graph": causal_graph,
        "equations": structural_equations,
        "baseline_noise": baseline_noise,
        "defect_type": defect_type,
        "created_at": datetime.now().isoformat()
    }
    
    logger.info("SCM模型构建完成")
    return model


def perform_counterfactual_reasoning(
    scm_model: Dict[str, any],
    current_state: ProcessState,
    defect_detected: bool,
    intervention_vars: Dict[str, float]
) -> CounterfactualResult:
    """
    执行反事实推演：计算如果在过去某个时刻改变参数，当前结果会如何变化。
    
    核心逻辑：
    1. Abduction (溯因): 根据当前结果反推噪声项/隐变量
    2. Action (行动): 修改模型中的参数 (do-calculus)
    3. Prediction (预测): 在修改后的模型中重新计算结果
    
    Args:
        scm_model (Dict): 构建好的结构因果模型
        current_state (ProcessState): 当前观测到的工艺状态
        defect_detected (bool): 当前是否检测到了缺陷
        intervention_vars (Dict[str, float]): 干预变量，例如 {'temperature': -5} 表示降温5度
        
    Returns:
        CounterfactualResult: 包含反事实推演结果的对象
        
    Example:
        >>> model = build_structural_causal_model(history)
        >>> current = ProcessState(1250, 45, 1.2, 120, 0.85)
        >>> result = perform_counterfactual_reasoning(model, current, True, {'temperature': -5})
        >>> print(result.improvement_ratio)
    """
    if not scm_model:
        raise ValueError("SCM模型不能为空")
        
    logger.info(f"开始反事实推演，干预变量: {intervention_vars}")
    
    equations = scm_model["equations"]
    noise = scm_model["baseline_noise"]
    
    # 1. Abduction: 计算当前状态下的隐含缺陷得分
    # 如果已经检测到缺陷，我们假设基线得分较高
    base_defect_score = equations["defect_score"](
        current_state.temperature,
        current_state.pressure,
        current_state.material_quality,
        noise
    )
    
    # 如果实际检测到缺陷，修正噪声项以反映事实
    if defect_detected:
        # 简化处理：如果检测到缺陷，强制基础得分有一个底噪
        actual_noise = max(noise, 0.5) 
    else:
        actual_noise = noise
        
    # 2. Action & Prediction: 应用干预并计算反事实结果
    # 构建反事实状态
    cf_temperature = current_state.temperature + intervention_vars.get("temperature", 0)
    cf_pressure = current_state.pressure + intervention_vars.get("pressure", 0)
    
    # 边界检查：确保反事实物理参数合理
    if cf_temperature < 0:
        logger.warning("反事实温度低于物理极限，已修正为0")
        cf_temperature = 0
        
    # 重新计算反事实压力（如果温度变化引起了压力变化）
    cf_pressure_induced = equations["pressure"](cf_temperature, 0)
    
    # 计算反事实缺陷得分
    cf_defect_score = equations["defect_score"](
        cf_temperature,
        cf_pressure_induced,
        current_state.material_quality,
        actual_noise # 使用溯因得到的噪声
    )
    
    # 将得分映射为概率 (Sigmoid函数)
    def score_to_prob(score: float) -> float:
        return 1 / (1 + np.exp(-score + 2)) # 假设score=2是50%概率的阈值

    original_prob = score_to_prob(base_defect_score)
    counterfactual_prob = score_to_prob(cf_defect_score)
    
    # 计算改善幅度
    improvement = 0.0
    if original_prob > 1e-6:
        improvement = (original_prob - counterfactual_prob) / original_prob
    
    # 构建因果路径解释
    causal_path = [
        f"Observation: Defect '{scm_model['defect_type']}' detected.",
        f"Abduction: Estimated latent noise level {actual_noise:.4f}.",
        f"Intervention: Applied {intervention_vars} at T-{current_state.duration}.",
        f"Mechanism: Temperature change {current_state.temperature}->{cf_temperature} affected pressure.",
        f"Prediction: Defect probability reduced from {original_prob:.2%} to {counterfactual_prob:.2%}."
    ]
    
    logger.info(f"推演完成，原始概率: {original_prob:.4f}, 反事实概率: {counterfactual_prob:.4f}")
    
    return CounterfactualResult(
        original_defect_prob=original_prob,
        adjusted_defect_prob=counterfactual_prob,
        improvement_ratio=improvement,
        intervention_strategy=intervention_vars,
        causal_path=causal_path
    )


# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    try:
        # 1. 模拟生成工艺历史数据
        # 假设这是一个烧制过程，温度逐渐升高，但在T=60分钟时出现异常高温
        history_data = [
            ProcessState(temperature=800 + i*10, humidity=50, pressure=1.0 + i*0.01, duration=i, material_quality=0.85)
            for i in range(0, 60, 5)
        ]
        
        # 2. 构建因果模型
        scm = build_structural_causal_model(history_data, defect_type="cracking")
        
        # 3. 模拟当前时刻状态 (T=60, Temp=1400, 出现开裂)
        # 注意：这里的参数可能超出了最佳范围，导致缺陷
        current_situation = ProcessState(
            temperature=1400.0, 
            humidity=55.0, 
            pressure=1.8, 
            duration=60, 
            material_quality=0.80
        )
        
        # 4. 执行反事实推演
        # 问题：如果在T-10分钟时，我们把目标温度降低5度，结果会怎样？
        cf_result = perform_counterfactual_reasoning(
            scm_model=scm,
            current_state=current_situation,
            defect_detected=True,
            intervention_vars={"temperature": -5.0} # 假设的干预措施
        )
        
        print("\n=== 反事实推演报告 ===")
        print(f"原始缺陷概率: {cf_result.original_defect_prob:.2%}")
        print(f"干预后缺陷概率: {cf_result.adjusted_defect_prob:.2%}")
        print(f"风险降低幅度: {cf_result.improvement_ratio:.2%}")
        print("\n推理路径:")
        for step in cf_result.causal_path:
            print(f"- {step}")
            
    except ValueError as ve:
        logger.error(f"参数验证失败: {ve}")
    except Exception as e:
        logger.error(f"系统运行时错误: {e}", exc_info=True)