"""
模块名称: auto_自洽性闭环_针对_小摊贩认知_这类具体_e12be2
描述: 本模块实现了一个针对“小摊贩认知”的自动化小世界网络模拟器（沙盒环境）。
     它模拟了现实世界的物理限制（如库存容量、疲劳度）与经济规则（需求波动、成本计算）。
     AI Agent（或策略逻辑）在此封闭沙盒中执行“摆摊”技能，通过观察其是否能实现
     “盈利生存”来验证领域知识节点的自洽性。
     
作者: Senior Python Engineer (AGI System)
版本: 1.0.0
"""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeatherCondition(Enum):
    """枚举类：模拟天气状况，影响客流量"""
    SUNNY = 1.0    # 晴朗，标准客流
    RAINY = 0.4    # 雨天，客流减少
    HEATWAVE = 0.8 # 热浪，客流略微减少

@dataclass
class MarketParameters:
    """市场环境参数配置"""
    base_rent: float = 50.0           # 基础摊位费
    base_demand: int = 100            # 基础需求数量
    customer_price_sensitivity: float = 0.05 # 客户对价格的敏感系数
    weather: WeatherCondition = WeatherCondition.SUNNY

@dataclass
class VendorState:
    """摊贩（AI Agent）的当前状态"""
    cash: float = 500.0               # 初始资金
    inventory: int = 0                # 当前库存
    fatigue: float = 0.0              # 疲劳值 (0.0 - 1.0)
    cost_per_unit: float = 3.0        # 每单位商品的进货成本
    max_inventory: int = 200          # 物理背包限制
    is_bankrupt: bool = False         # 是否破产

    def __post_init__(self):
        """数据验证"""
        if self.cash < 0:
            raise ValueError("初始资金不能为负数")
        if self.cost_per_unit <= 0:
            raise ValueError("进货成本必须大于0")

class SmallWorldSimulator:
    """
    小世界网络模拟器核心类。
    
    负责维护模拟世界的状态，处理经济交易，物理限制检查，
    以及评估AI策略的自洽性（是否盈利生存）。
    """
    
    def __init__(self, market_params: MarketParameters, initial_state: VendorState):
        """
        初始化模拟器。
        
        Args:
            market_params: 市场环境参数。
            initial_state: 摊贩的初始状态。
        """
        self.market = market_params
        self.state = initial_state
        self.history: List[Dict] = []
        logger.info("模拟器初始化完成。市场参数: %s", self.market)

    def _calculate_daily_demand(self, price: float) -> int:
        """
        辅助函数：根据价格和天气计算每日实际需求。
        
        模拟逻辑：
        1. 基础需求受天气影响系数调节。
        2. 价格越高，需求按指数衰减。
        
        Args:
            price: 商品的单价
            
        Returns:
            int: 当天的模拟需求数量
        """
        if price <= 0:
            return 0
            
        # 天气影响
        weather_factor = self.market.weather.value
        
        # 价格弹性影响
        price_factor = 1.0 - (price - self.state.cost_per_unit) * self.market.customer_price_sensitivity
        price_factor = max(0, price_factor) # 确保非负
        
        final_demand = int(self.market.base_demand * weather_factor * price_factor)
        
        # 添加随机噪声 (小世界网络的不确定性)
        noise = random.randint(-5, 5)
        return max(0, final_demand + noise)

    def execute_day_cycle(self, pricing_strategy: float, restock_amount: int) -> Tuple[bool, Dict]:
        """
        核心函数1：执行完整的一天模拟循环。
        
        包含进货（物理限制检查）、销售（经济规则）、结算（生存判定）。
        
        Args:
            pricing_strategy: AI决定的销售单价
            restock_amount: AI决定的进货数量
            
        Returns:
            Tuple[bool, Dict]: (是否存活, 当天详细数据报表)
        """
        if self.state.is_bankrupt:
            logger.warning("模拟终止：摊贩已破产。")
            return False, {}

        # 1. 物理规则检查：进货与库存限制
        total_inventory = self.state.inventory + restock_amount
        if total_inventory > self.state.max_inventory:
            # 强制修正：只能带得动那么多
            actual_restock = self.state.max_inventory - self.state.inventory
            logger.warning(f"进货量超过物理上限，自动修正为: {actual_restock}")
        else:
            actual_restock = restock_amount
            
        # 扣除进货成本
        purchase_cost = actual_restock * self.state.cost_per_unit
        if self.state.cash < purchase_cost:
            actual_restock = int(self.state.cash / self.state.cost_per_unit)
            purchase_cost = actual_restock * self.state.cost_per_unit
            logger.warning(f"资金不足，进货量修正为: {actual_restock}")

        self.state.cash -= purchase_cost
        self.state.inventory += actual_restock
        
        # 2. 经济规则：市场交互
        demand = self._calculate_daily_demand(pricing_strategy)
        sales_volume = min(demand, self.state.inventory)
        revenue = sales_volume * pricing_strategy
        
        self.state.inventory -= sales_volume
        self.state.cash += revenue
        
        # 3. 生存成本与疲劳（物理/生理规则）
        daily_expenses = self.market.base_rent + (actual_restock * 0.1) # 搬运费等
        self.state.cash -= daily_expenses
        
        # 疲劳累积（简化模型）
        self.state.fatigue += 0.1 
        if self.state.fatigue > 1.0:
            self.state.fatigue = 1.0
            # 疲劳导致次日租金增加（效率下降或医疗费）
            self.market.base_rent *= 1.05 

        # 4. 状态判定
        self.state.is_bankrupt = self.state.cash < 0
        
        daily_report = {
            "sales": sales_volume,
            "revenue": revenue,
            "cost": purchase_cost + daily_expenses,
            "profit": revenue - (purchase_cost + daily_expenses),
            "remaining_cash": self.state.cash,
            "bankrupt": self.state.is_bankrupt
        }
        self.history.append(daily_report)
        
        logger.info(f"日报 -> 营收: {revenue:.2f}, 利润: {daily_report['profit']:.2f}, 现金: {self.state.cash:.2f}")
        return not self.state.is_bankrupt, daily_report

    def evaluate_consistency(self, days: int = 30) -> bool:
        """
        核心函数2：评估“小摊贩认知”的自洽性。
        
        通过运行一个预设的基准策略（Baseline），如果在标准环境下无法生存，
        说明环境参数设置过难（不自洽）；如果生存且盈利，说明环境逻辑闭环。
        
        Args:
            days: 模拟的天数
            
        Returns:
            bool: 系统是否通过自洽性验证
        """
        logger.info(f"开始自洽性验证循环，模拟时长: {days}天")
        
        # 简单的基准策略：成本加成定价，保持库存
        for day in range(days):
            # 模拟天气随机变化
            self.market.weather = random.choice(list(WeatherCondition))
            
            # 简单策略逻辑
            target_price = self.state.cost_per_unit * 2.0
            target_restock = max(0, 50 - self.state.inventory)
            
            survived, _ = self.execute_day_cycle(target_price, target_restock)
            
            if not survived:
                logger.error(f"自洽性验证失败：Agent在第{day+1}天破产。")
                return False

        # 检查最终是否盈利
        final_profit = self.state.cash - 500.0 # 初始资金比较
        if final_profit > 0:
            logger.info(f"自洽性验证成功。最终利润: {final_profit:.2f}")
            return True
        else:
            logger.warning(f"自洽性验证通过（生存），但未盈利。最终利润: {final_profit:.2f}")
            return False

# 使用示例
if __name__ == "__main__":
    try:
        # 1. 初始化环境和状态
        market_config = MarketParameters(base_rent=30.0, base_demand=80)
        initial_vendor_state = VendorState(cash=1000.0, cost_per_unit=5.0)
        
        # 2. 实例化模拟器
        simulator = SmallWorldSimulator(market_config, initial_vendor_state)
        
        # 3. 运行自洽性测试（验证这个世界规则是否逻辑自洽）
        is_consistent = simulator.evaluate_consistency(days=10)
        
        if is_consistent:
            print("\n=== 模拟结果 ===")
            print("沙盒环境自洽，Agent可以在该规则下生存。")
            print("该领域知识节点（小摊贩经济学）验证通过。")
        else:
            print("\n=== 模拟结果 ===")
            print("沙盒环境过于恶劣或逻辑有误，请检查参数。")

    except ValueError as ve:
        logger.error(f"参数验证错误: {ve}")
    except Exception as e:
        logger.critical(f"模拟器发生未预期崩溃: {e}", exc_info=True)