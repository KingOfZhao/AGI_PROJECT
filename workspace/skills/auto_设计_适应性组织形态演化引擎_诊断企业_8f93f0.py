"""
适应性组织形态演化引擎

该模块旨在根据企业当前的市场环境密度与增长阶段，自动诊断并建议
相应的组织策略。基于生态学中的r/K选择理论，帮助企业在“野蛮生长”
与“基业长青”之间进行自动化策略切换。

核心逻辑：
1. 诊断阶段：分析市场饱和度、资源可用性和增长率。
2. 策略生成：
   - r策略 (早期/环境空旷): 快速迭代、高容错、抢占市场。
   - K策略 (成熟期/环境拥挤): 提升质量、运营效率、客户留存。
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """定义演化策略类型枚举"""
    R_STRATEGY = "r_strategy"  # 繁殖优先，适用于早期
    K_STRATEGY = "k_strategy"  # 生存优先，适用于成熟期
    TRANSITION = "transition"  # 过渡期


class AdaptiveOrganizationEvolutionEngine:
    """
    适应性组织形态演化引擎。

    该类负责诊断企业环境并生成相应的演化策略。
    """

    def __init__(self, saturation_threshold: float = 0.6, growth_threshold: float = 0.2):
        """
        初始化演化引擎。

        Args:
            saturation_threshold (float): 判断市场拥挤的饱和度阈值 (0.0 - 1.0)。
            growth_threshold (float): 判断高增长的阈值 (0.0 - 1.0)。
        """
        self.saturation_threshold = saturation_threshold
        self.growth_threshold = growth_threshold
        logger.info("Evolution Engine initialized with thresholds: "
                    f"saturation={saturation_threshold}, growth={growth_threshold}")

    def _validate_metrics(self, metrics: Dict[str, float]) -> None:
        """
        辅助函数：验证输入指标的合法性和边界。

        Args:
            metrics (Dict[str, float]): 包含环境指标的字典。

        Raises:
            ValueError: 如果指标缺失或超出范围。
        """
        required_keys = ['market_saturation', 'resource_availability', 'growth_rate']
        for key in required_keys:
            if key not in metrics:
                raise ValueError(f"Missing required metric: {key}")

            value = metrics[key]
            if not isinstance(value, (int, float)):
                raise TypeError(f"Metric {key} must be a number.")
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Metric {key} must be between 0.0 and 1.0, got {value}")

        logger.debug("Metrics validation passed.")

    def diagnose_environment(self, metrics: Dict[str, float]) -> StrategyType:
        """
        核心函数：诊断企业当前所处的环境状态。

        根据市场饱和度和增长率判断企业处于早期（空旷）还是成熟期（拥挤）。

        Args:
            metrics (Dict[str, float]): 环境指标字典。
                - market_saturation: 市场饱和度 (0.0 - 1.0)
                - resource_availability: 资源可用性 (0.0 - 1.0)
                - growth_rate: 增长率 (0.0 - 1.0)

        Returns:
            StrategyType: 诊断出的策略类型。

        Example:
            >>> engine = AdaptiveOrganizationEvolutionEngine()
            >>> engine.diagnose_environment({'market_saturation': 0.2, 'resource_availability': 0.9, 'growth_rate': 0.8})
            <StrategyType.R_STRATEGY: 'r_strategy'>
        """
        try:
            self._validate_metrics(metrics)
        except (ValueError, TypeError) as e:
            logger.error(f"Metrics validation failed: {e}")
            raise

        saturation = metrics['market_saturation']
        growth = metrics['growth_rate']

        # 逻辑判断：如果市场不拥挤且增长迅速，判定为早期环境
        if saturation < self.saturation_threshold and growth > self.growth_threshold:
            logger.info("Diagnosis: Early stage environment detected (Sparse).")
            return StrategyType.R_STRATEGY
        # 如果市场拥挤或增长停滞，判定为成熟期环境
        elif saturation >= self.saturation_threshold or growth < self.growth_threshold:
            logger.info("Diagnosis: Mature stage environment detected (Crowded).")
            return StrategyType.K_STRATEGY
        else:
            logger.info("Diagnosis: Transition phase detected.")
            return StrategyType.TRANSITION

    def generate_strategy(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """
        核心函数：根据诊断结果生成具体的执行策略。

        Args:
            strategy_type (StrategyType): 策略类型。

        Returns:
            Dict[str, Any]: 包含策略名称、优先级和具体行动建议的字典。

        Example:
            >>> engine = AdaptiveOrganizationEvolutionEngine()
            >>> engine.generate_strategy(StrategyType.R_STRATEGY)
            {'strategy_name': 'r_strategy', 'focus': 'Market Penetration', 'actions': [...]}
        """
        strategy_plan: Dict[str, Any] = {}

        if strategy_type == StrategyType.R_STRATEGY:
            strategy_plan = {
                "strategy_name": "r_strategy",
                "focus": "Market Penetration & Iteration",
                "priority": "Speed over Perfection",
                "actions": [
                    "Launch Minimum Viable Products (MVP) rapidly.",
                    "High tolerance for failure in exploration.",
                    "Aggressive marketing to capture market share.",
                    "Decentralized decision making for speed."
                ],
                "kpi_focus": ["User Acquisition", "Market Share", "Iteration Speed"]
            }
            logger.info("Generated r_strategy: Focus on rapid expansion.")

        elif strategy_type == StrategyType.K_STRATEGY:
            strategy_plan = {
                "strategy_name": "k_strategy",
                "focus": "Efficiency & Retention",
                "priority": "Quality & Stability",
                "actions": [
                    "Optimize operational workflows and reduce costs.",
                    "Enhance customer service and support systems.",
                    "Focus on customer lifetime value (LTV) and retention.",
                    "Standardize processes to ensure consistency."
                ],
                "kpi_focus": ["Customer Retention", "Profit Margin", "NPS Score"]
            }
            logger.info("Generated k_strategy: Focus on efficiency and stability.")

        else:
            strategy_plan = {
                "strategy_name": "transition",
                "focus": "Balanced Approach",
                "actions": [
                    "Maintain growth while stabilizing core operations.",
                    "Prepare infrastructure for scaling.",
                    "Shift culture from exploration to exploitation."
                ]
            }
            logger.info("Generated transition strategy.")

        return strategy_plan

    def run_evolution_cycle(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        执行完整的演化诊断与策略生成流程。

        Args:
            metrics (Dict[str, float]): 输入指标。

        Returns:
            Dict[str, Any]: 包含诊断结果和策略建议的完整报告。
        """
        logger.info("Starting evolution cycle...")
        try:
            diagnosis = self.diagnose_environment(metrics)
            strategy = self.generate_strategy(diagnosis)
            
            report = {
                "input_metrics": metrics,
                "diagnosis": diagnosis.value,
                "recommended_strategy": strategy
            }
            logger.info("Evolution cycle completed successfully.")
            return report
        except Exception as e:
            logger.error(f"Error during evolution cycle: {e}")
            return {"error": str(e)}


# 使用示例
if __name__ == "__main__":
    # 模拟一个处于早期阶段的企业（市场空旷，高增长）
    early_stage_metrics = {
        "market_saturation": 0.15,  # 15% 饱和度
        "resource_availability": 0.85, # 资源丰富
        "growth_rate": 0.50  # 50% 增长率
    }

    # 模拟一个处于成熟阶段的企业（市场拥挤，低增长）
    mature_stage_metrics = {
        "market_saturation": 0.85,  # 85% 饱和度
        "resource_availability": 0.30, # 资源稀缺
        "growth_rate": 0.05  # 5% 增长率
    }

    engine = AdaptiveOrganizationEvolutionEngine()

    print("--- Early Stage Diagnosis ---")
    result_early = engine.run_evolution_cycle(early_stage_metrics)
    for k, v in result_early['recommended_strategy'].items():
        print(f"{k}: {v}")

    print("\n--- Mature Stage Diagnosis ---")
    result_mature = engine.run_evolution_cycle(mature_stage_metrics)
    for k, v in result_mature['recommended_strategy'].items():
        print(f"{k}: {v}")