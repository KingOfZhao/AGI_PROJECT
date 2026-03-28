"""
模块: adaptive_survival_strategy_engine
名称: 自适应生存策略引擎

描述:
本模块实现了基于进化生物学（r/K选择理论）和生态学（扰动理论）的企业生存策略动态调整系统。
它允许企业在不同的发展阶段（早期、成长期、成熟期）之间平滑过渡，并自动生成对应的战略建议。

核心功能:
1. 基于企业指标（资源、竞争烈度、市场份额）计算生存策略向量。
2. 动态切换 r-strategy (探索/迭代) 与 K-strategy (巩固/壁垒)。
3. 在成熟期引入“内部扰动”机制，模拟生态扰动，防止组织僵化。

作者: AGI System
版本: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DevelopmentPhase(Enum):
    """企业生命周期阶段枚举"""
    STARTUP = auto()       # 初创期：高不确定性，资源匮乏
    GROWTH = auto()        # 成长期：快速扩张，资源积累
    MATURITY = auto()      # 成熟期：市场稳定，竞争白热化
    DECLINE = auto()       # 衰退期（本引擎主要用于防御）


class StrategyType(Enum):
    """策略类型枚举"""
    R_STRATEGY = auto()    # r-策略：快速迭代，高表型可塑性，探索生态位
    K_STRATEGY = auto()    # K-策略：生殖隔离，品牌壁垒，精细化运营
    HYBRID = auto()        # 混合策略：处于过渡期


@dataclass
class CompanyMetrics:
    """企业健康度与状态指标数据结构"""
    resource_abundance: float  # 资源充裕度 (0.0 - 1.0)
    competition_intensity: float  # 竞争烈度 (0.0 - 1.0)
    market_share: float  # 市场份额 (0.0 - 1.0)
    innovation_rate: float  # 创新速率 (0.0 - 1.0)
    organizational_rigidity: float  # 组织僵化度 (0.0 - 1.0)

    def __post_init__(self):
        """数据验证"""
        for field_name in ['resource_abundance', 'competition_intensity', 
                           'market_share', 'innovation_rate', 'organizational_rigidity']:
            value = getattr(self, field_name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{field_name} 必须在 0.0 和 1.0 之间，当前值: {value}")


class StrategyEngineError(Exception):
    """自定义策略引擎异常"""
    pass


def _calculate_perturbation_strength(rigidity: float, phase: DevelopmentPhase) -> float:
    """
    [辅助函数] 计算内部扰动的强度。
    
    基于生态学扰动理论：为了防止系统（企业）陷入完全的稳态（大公司病），
    需要引入随机扰动（内部创业/赛马机制）。
    
    Args:
        rigidity (float): 组织僵化度指标。
        phase (DevelopmentPhase): 当前发展阶段。
        
    Returns:
        float: 建议的扰动强度 (0.0 - 1.0)。
    """
    if phase != DevelopmentPhase.MATURITY:
        return 0.0
    
    # 僵化度越高，越需要强烈的内部扰动来打破平衡
    # 使用 Sigmoid 函数平滑映射
    perturbation = 1 / (1 + math.exp(-10 * (rigidity - 0.6)))
    
    logger.debug(f"计算扰动强度: 僵化度={rigidity:.2f}, 扰动强度={perturbation:.2f}")
    return perturbation


def determine_development_phase(metrics: CompanyMetrics) -> DevelopmentPhase:
    """
    [核心函数 1] 诊断企业当前所处的发展阶段。
    
    逻辑说明:
    - 初创期: 资源少，份额低。
    - 成长期: 份额上升，创新高。
    - 成熟期: 份额高，资源足，竞争烈度高。
    
    Args:
        metrics (CompanyMetrics): 包含企业各项指标的数据对象。
        
    Returns:
        DevelopmentPhase: 识别出的生命周期阶段。
        
    Raises:
        StrategyEngineError: 如果无法明确判断阶段。
    """
    logger.info("开始分析企业发展阶段...")
    
    # 简化的决策逻辑（实际场景中可能使用决策树或聚类模型）
    if metrics.market_share < 0.1 and metrics.resource_abundance < 0.3:
        logger.info("诊断结果: 初创期 (STARTUP)")
        return DevelopmentPhase.STARTUP
    elif metrics.market_share >= 0.1 and metrics.innovation_rate > 0.6 and metrics.market_share < 0.4:
        logger.info("诊断结果: 成长期 (GROWTH)")
        return DevelopmentPhase.GROWTH
    elif metrics.market_share >= 0.4 and metrics.competition_intensity > 0.5:
        logger.info("诊断结果: 成熟期 (MATURITY)")
        return DevelopmentPhase.MATURITY
    else:
        # 默认回退逻辑
        if metrics.organizational_rigidity > 0.7:
            logger.warning("指标模糊，但组织僵化严重，倾向于判定为成熟期后期")
            return DevelopmentPhase.MATURITY
        logger.warning("指标模糊，默认判定为成长期")
        return DevelopmentPhase.GROWTH


def generate_adaptive_strategy(metrics: CompanyMetrics) -> Dict[str, str]:
    """
    [核心函数 2] 生成自适应生存策略建议。
    
    根据输入的指标，结合 r/K 选择理论，输出具体的战略行动指南。
    
    输入格式: CompanyMetrics 对象
    输出格式: {
        "phase": "阶段名称",
        "strategy_type": "r/k/hybrid",
        "core_action": "核心行动建议",
        "perturbation_advice": "内部扰动建议（如果适用）"
    }
    
    Args:
        metrics (CompanyMetrics): 企业当前指标。
        
    Returns:
        Dict[str, str]: 包含详细策略建议的字典。
    """
    try:
        phase = determine_development_phase(metrics)
        strategy_info = {
            "phase": phase.name,
            "strategy_type": "",
            "core_action": "",
            "perturbation_advice": "无"
        }
        
        if phase == DevelopmentPhase.STARTUP:
            # r-策略主导：利用表型可塑性
            strategy_info["strategy_type"] = StrategyType.R_STRATEGY.name
            strategy_info["core_action"] = (
                "【表型可塑性模式】资源匮乏，建议最大化迭代速度。"
                "不要追求完美，通过MVP（最小可行性产品）快速试错，"
                "探索所有可能的生存生态位。"
            )
            
        elif phase == DevelopmentPhase.GROWTH:
            # 过渡期：混合策略
            strategy_info["strategy_type"] = StrategyType.HYBRID.name
            strategy_info["core_action"] = (
                "【资源转化模式】利用获得的资源建立初步壁垒。"
                "在保持迭代速度的同时，开始关注用户留存和品牌认知。"
            )
            
        elif phase == DevelopmentPhase.MATURITY:
            # K-策略主导：生殖隔离
            strategy_info["strategy_type"] = StrategyType.K_STRATEGY.name
            strategy_info["core_action"] = (
                "【生殖隔离模式】构建护城河。"
                "利用专利、品牌资产和网络效应阻止竞争者入侵。"
                "优化运营效率，最大化单体资源产出。"
            )
            
            # 计算内部扰动
            p_strength = _calculate_perturbation_strength(
                metrics.organizational_rigidity, 
                phase
            )
            
            if p_strength > 0.5:
                strategy_info["perturbation_advice"] = (
                    f"警告：检测到高组织僵化度({metrics.organizational_rigidity:.2f})。"
                    f"建议引入强度为 {p_strength:.2f} 的'内部灭绝风险'。"
                    "具体措施：拆分内部团队，建立竞争性内部创业项目，"
                    "主动打破舒适区以维持组织进化动力。"
                )
                logger.warning(f"触发内部扰动建议，强度: {p_strength}")
                
        return strategy_info
        
    except Exception as e:
        logger.error(f"策略生成失败: {str(e)}")
        raise StrategyEngineError(f"无法生成策略: {str(e)}")


if __name__ == "__main__":
    # 使用示例
    
    print("--- 场景 1: 初创公司 (r-策略) ---")
    startup_metrics = CompanyMetrics(
        resource_abundance=0.1,
        competition_intensity=0.3,
        market_share=0.01,
        innovation_rate=0.9,
        organizational_rigidity=0.1
    )
    strategy_1 = generate_adaptive_strategy(startup_metrics)
    for k, v in strategy_1.items():
        print(f"{k}: {v}")
    print("\n")

    print("--- 场景 2: 巨头公司，出现大公司病 (K-策略 + 扰动) ---")
    giant_metrics = CompanyMetrics(
        resource_abundance=0.9,
        competition_intensity=0.8,
        market_share=0.6,
        innovation_rate=0.2,
        organizational_rigidity=0.85  # 高度僵化
    )
    strategy_2 = generate_adaptive_strategy(giant_metrics)
    for k, v in strategy_2.items():
        print(f"{k}: {v}")