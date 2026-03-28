"""
Module: auto_小摊贩认知自洽性_构建一个完全封闭的微_133a90
Description: 
    Implements a closed micro-economic simulation (Lemonade Stand) to validate 
    AGI 'Cognitive Consistency'. The AI agent must utilize pre-defined Skill 
    nodes (Inventory Management, Dynamic Pricing, Marketing) to maintain a 
    coherent internal state and maximize profit within a finite state space.
    
    The system enforces a feedback loop where decisions alter the environment, 
    and the altered environment feeds back into the decision matrix.
    
Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import random
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# --- Configuration & Constants ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s.%(funcName)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

MAX_INVENTORY = 100
MAX_PRICE = 20.0
MIN_PRICE = 1.0
INITIAL_CAPITAL = 100.0
UNIT_COST = 2.0  # Cost to make one unit of lemonade

class ActionType(Enum):
    """Enumeration of valid Skill actions the Agent can perform."""
    RESTOCK = auto()
    SET_PRICE = auto()
    ADVERTISE = auto()
    PASS = auto()

@dataclass
class MarketState:
    """Represents the external environment and internal status of the stall."""
    weather_score: float = 1.0  # 0.0 (Rain) to 2.0 (Heatwave), affects demand
    inventory: int = 10
    capital: float = INITIAL_CAPITAL
    price: float = 5.0
    reputation: float = 0.5  # 0.0 to 1.0
    day: int = 0

@dataclass
class ActionPlan:
    """Data transfer object for Agent's decision."""
    action_type: ActionType
    value: Optional[float] = None  # e.g., amount to restock or new price

class EconomicSimulator:
    """
    Core simulation engine handling the physics of the micro-economy.
    It processes actions and calculates the resulting state transitions.
    """

    def __init__(self):
        self._state: MarketState = MarketState()
        self.history: List[Dict] = []
        logger.info("Economic Simulator Initialized. Environment sealed.")

    def _validate_state(self) -> bool:
        """Ensures state integrity (Boundary Checks)."""
        if not (0 <= self._state.weather_score <= 2.0):
            logger.error("Invalid weather score detected.")
            return False
        if self._state.inventory < 0 or self._state.inventory > MAX_INVENTORY:
            logger.error("Inventory bounds violated.")
            return False
        return True

    def process_step(self, plan: ActionPlan) -> Tuple[MarketState, float]:
        """
        Processes an agent's action plan and advances the simulation by one step.
        
        Args:
            plan (ActionPlan): The action chosen by the AI agent.
            
        Returns:
            Tuple[MarketState, float]: The new observable state and the profit/loss for this step.
        
        Raises:
            ValueError: If action parameters are invalid.
        """
        current_profit = 0.0
        
        # 1. Execute Action (Pre-Market)
        if plan.action_type == ActionType.RESTOCK:
            amount = int(plan.value) if plan.value else 0
            cost = amount * UNIT_COST
            if self._state.capital >= cost and self._state.inventory + amount <= MAX_INVENTORY:
                self._state.inventory += amount
                self._state.capital -= cost
                logger.info(f"Action: Restocked {amount} units. Cost: ${cost:.2f}")
            else:
                logger.warning("Restock failed: Insufficient capital or storage.")

        elif plan.action_type == ActionType.SET_PRICE:
            if plan.value and MIN_PRICE <= plan.value <= MAX_PRICE:
                self._state.price = plan.value
                logger.info(f"Action: Price set to ${self._state.price:.2f}")
            else:
                logger.warning(f"Invalid price set attempt: {plan.value}")

        elif plan.action_type == ActionType.ADVERTISE:
            cost = 5.0
            if self._state.capital >= cost:
                self._state.capital -= cost
                self._state.reputation = min(1.0, self._state.reputation + 0.1)
                logger.info("Action: Advertised. Reputation boosted.")
        
        # 2. Simulate Market Forces (Randomness + Demand Logic)
        # Weather changes stochastically
        self._state.weather_score = max(0.0, min(2.0, self._state.weather_score + random.gauss(0, 0.2)))
        
        # Calculate Demand based on Price, Weather, Reputation
        base_demand = 20.0
        price_elasticity = 1.5 * (10.0 / max(0.1, self._state.price))  # Cheaper = More demand
        demand_factor = base_demand * self._state.weather_score * price_elasticity * (0.5 + self._state.reputation)
        demand = int(demand_factor)
        
        # 3. Execute Sales
        sales = min(self._state.inventory, demand)
        revenue = sales * self._state.price
        self._state.inventory -= sales
        self._state.capital += revenue
        current_profit = revenue
        
        # Reputation decay
        self._state.reputation = max(0.1, self._state.reputation - 0.05) 
        
        self._state.day += 1
        
        if not self._validate_state():
            raise RuntimeError("Simulation State Corrupted")

        self._record_history(sales, revenue)
        return self._state, current_profit

    def _record_history(self, sales: int, revenue: float):
        """Helper to record step data for analysis."""
        record = {
            "day": self._state.day,
            "capital": round(self._state.capital, 2),
            "inventory": self._state.inventory,
            "price": self._state.price,
            "sales": sales,
            "revenue": revenue
        }
        self.history.append(record)

    def get_current_state(self) -> MarketState:
        return self._state

class CognitiveAgent:
    """
    The 'Brain' of the operation. 
    Analyzes the MarketState and constructs an ActionPlan using specific Skill functions.
    This class represents the AGI's decision-making logic.
    """

    def __init__(self):
        self.internal_memory: Dict[str, float] = {"last_profit": 0.0, "trend": 0.0}
        logger.info("Cognitive Agent Online. Skills loaded.")

    def skill_perceive(self, state: MarketState) -> Dict[str, float]:
        """
        SKILL 1: Perception & Feature Extraction.
        Transforms raw state into normalized cognitive features.
        """
        features = {
            "inventory_ratio": state.inventory / MAX_INVENTORY,
            "price_efficiency": UNIT_COST / state.price if state.price > 0 else 0,
            "market_mood": state.weather_score / 2.0,
            "brand_strength": state.reputation
        }
        return features

    def skill_decide(self, features: Dict[str, float], state: MarketState) -> ActionPlan:
        """
        SKILL 2: Decision Logic.
        Uses heuristics (mimicking a simple neural net) to select actions.
        """
        inv_ratio = features["inventory_ratio"]
        mood = features["market_mood"]
        
        # Priority 1: Inventory Check
        if inv_ratio < 0.2:
            amount_to_buy = int((1.0 - inv_ratio) * MAX_INVENTORY * 0.5)
            # Can we afford it?
            max_afford = state.capital // UNIT_COST
            final_amount = min(amount_to_buy, max_afford)
            return ActionPlan(ActionType.RESTOCK, value=float(final_amount))

        # Priority 2: Pricing Strategy based on Weather
        if mood > 0.8:  # Good weather
            target_price = 6.0 + (mood * 2.0)
            return ActionPlan(ActionType.SET_PRICE, value=min(target_price, MAX_PRICE))
        elif mood < 0.4:  # Bad weather
            target_price = 3.0
            return ActionPlan(ActionType.SET_PRICE, value=max(target_price, MIN_PRICE))
            
        # Priority 3: Marketing if Capital is high but reputation low
        if state.capital > 50 and features["brand_strength"] < 0.6:
            return ActionPlan(ActionType.ADVERTISE)

        return ActionPlan(ActionType.PASS)

    def execute_cycle(self, current_state: MarketState) -> ActionPlan:
        """
        Main entry point for the agent. Runs the cognitive loop.
        """
        try:
            features = self.skill_perceive(current_state)
            plan = self.skill_decide(features, current_state)
            return plan
        except Exception as e:
            logger.critical(f"Cognitive Failure: {e}")
            return ActionPlan(ActionType.PASS)  # Fail-safe

# --- Main Execution / Usage Example ---
def run_simulation(cycles: int = 20):
    """
    Orchestrates the simulation between the Environment and the Agent.
    """
    env = EconomicSimulator()
    agent = CognitiveAgent()
    
    print(f"{'DAY':<5} | {'CAPITAL':<10} | {'INV':<5} | {'PRICE':<6} | {'ACTION':<15} | {'RESULT'}")
    print("-" * 70)
    
    for _ in range(cycles):
        # 1. Agent observes and decides
        current_state = env.get_current_state()
        plan = agent.execute_cycle(current_state)
        
        # 2. Environment updates
        new_state, profit = env.process_step(plan)
        
        # 3. Logging/Display
        action_str = f"{plan.action_type.name}: {plan.value:.1f}" if plan.value else plan.action_type.name
        print(f"{new_state.day:<5} | ${new_state.capital:<9.2f} | {new_state.inventory:<5} | ${new_state.price:<5.2f} | {action_str:<15} | +${profit:.2f}")

if __name__ == "__main__":
    run_simulation(30)