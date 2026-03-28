"""
企业生态位动态优化引擎

该模块基于生态学‘性状置换’模型，为企业业务板块提供战略优化建议。
不同于传统的ROI导向分析，本系统模拟生物群落中的竞争与共生关系。
当监测到业务板块处于高竞争密度（红海）时，系统计算‘性状漂移’向量，
建议企业通过微创新或转型占据新的生态位，从而实现可持续共生。

输入格式:
    BusinessMetrics (Dataclass): 包含市场占有率、竞争密度、市场重叠度、
                                 创新潜力指数及当前ROI等字段。

输出格式:
    Dict[str, Any]: 包含战略建议、建议的生态位漂移向量、预期生态位宽度及风险等级。
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Tuple, Any, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BusinessMetrics:
    """业务生态指标数据类"""
    market_share: float  # 市场占有率 (0.0 - 1.0)
    competitor_density: float  # 竞争者密度 (0.0 - 1.0), 1.0表示极度拥挤
    market_overlap: float  # 与主要竞争对手的业务重叠度 (0.0 - 1.0)
    innovation_capacity: float  # 内部创新潜力/研发能力 (0.0 - 1.0)
    current_roi: float  # 当前投资回报率 (百分比, e.g., 15.5 for 15.5%)


def _validate_metrics(metrics: BusinessMetrics) -> None:
    """
    辅助函数：验证输入数据的边界和有效性。

    Args:
        metrics: 业务生态指标对象

    Raises:
        ValueError: 如果任何指标超出预期的逻辑范围
    """
    if not (0.0 <= metrics.market_share <= 1.0):
        raise ValueError("市场占有率必须在0.0到1.0之间")
    if not (0.0 <= metrics.competitor_density <= 1.0):
        raise ValueError("竞争者密度必须在0.0到1.0之间")
    if not (0.0 <= metrics.market_overlap <= 1.0):
        raise ValueError("市场重叠度必须在0.0到1.0之间")
    if not (0.0 <= metrics.innovation_capacity <= 1.0):
        raise ValueError("创新潜力指数必须在0.0到1.0之间")
    if metrics.current_roi < -100.0:
        raise ValueError("ROI不能小于-100%")
    
    logger.debug("指标验证通过。")


def calculate_competition_pressure(metrics: BusinessMetrics) -> float:
    """
    辅助函数：计算生态竞争压力指数。
    
    基于竞争密度和市场重叠度计算压力值。模拟生态学中的环境容纳量压力。

    Args:
        metrics: 业务生态指标对象

    Returns:
        float: 竞争压力指数 (0.0 - 1.0)
    """
    # 权重：密度比重叠度更能反映资源稀缺性
    pressure = (metrics.competitor_density * 0.6) + (metrics.market_overlap * 0.4)
    logger.info(f"计算竞争压力: {pressure:.2f}")
    return pressure


def simulate_character_displacement(metrics: BusinessMetrics) -> Dict[str, float]:
    """
    核心函数1：模拟性状置换。
    
    当竞争压力过大时，计算业务‘性状’（如产品特性、目标人群）的漂移方向。
    漂移方向应指向竞争较小且企业有能力（创新潜力）到达的区域。

    Args:
        metrics: 业务生态指标对象

    Returns:
        Dict[str, float]: 包含漂移向量和漂移幅度的字典
    """
    pressure = calculate_competition_pressure(metrics)
    
    # 只有当压力超过阈值（生态位饱和）时才发生显著漂移
    threshold = 0.7
    drift_magnitude = 0.0
    
    if pressure > threshold:
        # 漂移幅度与压力成正比，但受限于创新容量
        excess_pressure = pressure - threshold
        drift_magnitude = min(excess_pressure * 1.5, metrics.innovation_capacity)
        logger.info(f"触发性状置换模拟。漂移幅度: {drift_magnitude:.2f}")
    else:
        logger.info("竞争压力适中，无需剧烈性状置换。")

    # 模拟漂移向量 (简化为二维空间：差异化程度 vs 市场下沉程度)
    # 逻辑：高重叠 -> 向差异化漂移；高密度 -> 向细分/下沉或高端漂移
    diff_drift = metrics.market_overlap * drift_magnitude
    niche_drift = metrics.competitor_density * drift_magnitude * 0.5

    return {
        "differentiation_vector": diff_drift,  # 差异化向量
        "niche_shift_vector": niche_drift,    # 细分市场转移向量
        "total_displacement": drift_magnitude
    }


def optimize_ecological_niche(metrics: BusinessMetrics) -> Dict[str, Any]:
    """
    核心函数2：企业生态位动态优化引擎主逻辑。
    
    综合分析竞争压力、ROI和性状置换模拟结果，生成战略建议。
    决策逻辑：
    1. 高竞争 + 低ROI -> 建议撤资或彻底转型（生态位逃逸）
    2. 高竞争 + 高ROI + 高创新 -> 建议微创新/性状漂移（生态位分化）
    3. 低竞争 -> 建议扩张/维持（生态位占据）

    Args:
        metrics: 业务生态指标对象

    Returns:
        Dict[str, Any]: 优化策略报告，包含建议类型、风险评级和具体参数。
    """
    try:
        _validate_metrics(metrics)
    except ValueError as e:
        logger.error(f"输入数据无效: {e}")
        return {"status": "error", "message": str(e)}

    pressure = calculate_competition_pressure(metrics)
    displacement = simulate_character_displacement(metrics)
    
    strategy = ""
    risk_level = "LOW"
    action_params = {}

    # 决策矩阵
    if pressure > 0.8 and metrics.current_roi < 5.0:
        # 红海中的低效业务
        strategy = "ECOLOGICAL_EXIT"  # 生态位退出
        risk_level = "HIGH"
        action_params = {
            "reason": "资源竞争过度且回报低下，建议撤资以止损",
            "suggested_action": "liquidate_or_pivot"
        }
        logger.warning("建议策略：生态位退出（撤资）")
        
    elif pressure > 0.6 and metrics.innovation_capacity > 0.5:
        # 有能力进行性状置换
        strategy = "CHARACTER_DISPLACEMENT"  # 性状置换
        risk_level = "MEDIUM"
        action_params = {
            "reason": "竞争激烈但具备创新潜力，建议通过差异化占据新生态位",
            "innovation_focus": "product_differentiation" if displacement['differentiation_vector'] > displacement['niche_shift_vector'] else "market_segmentation",
            "drift_vector": displacement
        }
        logger.info("建议策略：性状置换（微创新/转型）")
        
    else:
        # 舒适区或无力转型
        strategy = "MAINTENANCE_OR_EXPANSION"  # 维持或扩张
        risk_level = "LOW"
        action_params = {
            "reason": "当前生态位相对安全或缺乏转型能力，建议维持现状或温和扩张",
            "focus_area": "market_share_growth"
        }
        logger.info("建议策略：维持或扩张")

    return {
        "strategy_type": strategy,
        "risk_level": risk_level,
        "competition_pressure": round(pressure, 3),
        "details": action_params
    }


# 使用示例
if __name__ == "__main__":
    # 示例1：红海竞争，高创新潜力（触发性状置换）
    red_sea_metrics = BusinessMetrics(
        market_share=0.15,
        competitor_density=0.9,  # 密度极高
        market_overlap=0.85,     # 同质化严重
        innovation_capacity=0.8,  # 研发能力强
        current_roi=12.0
    )
    
    print("--- 场景1：红海中的高潜力企业 ---")
    result1 = optimize_ecological_niche(red_sea_metrics)
    for k, v in result1.items():
        print(f"{k}: {v}")

    print("\n--- 场景2：红海中的低效企业 ---")
    # 示例2：红海竞争，低ROI，低创新（触发撤资建议）
    dying_metrics = BusinessMetrics(
        market_share=0.05,
        competitor_density=0.95,
        market_overlap=0.9,
        innovation_capacity=0.2,
        current_roi=-5.0
    )
    result2 = optimize_ecological_niche(dying_metrics)
    for k, v in result2.items():
        print(f"{k}: {v}")