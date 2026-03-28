"""
Module: auto_实现_主动式生态位构建agent_传统_3931d5
Description: Implementation of an Active Niche Constructing Agent.
             This agent moves beyond adapting to environments to actively shaping them.
             It demonstrates how to manipulate environmental variables (perception, context)
             to make specific strategies (like premium pricing) viable.
Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of possible niche construction actions."""
    COGNITIVE_INJECTION = "cognitive_injection"  # Changing user perception
    CONTEXT_REFRAMING = "context_reframing"      # Changing the comparison set
    BUNDLING = "bundling"                        # Changing product composition


@dataclass
class MarketState:
    """Represents the current state of the market environment."""
    base_product_value: float
    customer_price_sensitivity: float  # 0.0 (insensitive) to 1.0 (very sensitive)
    competitor_price_avg: float
    current_demand: float


@dataclass
class NicheConstructionStrategy:
    """Represents a constructed niche strategy."""
    action_type: ActionType
    description: str
    modified_environment_params: Dict[str, Any]
    projected_viability_score: float  # 0.0 to 1.0
    execution_payload: Dict[str, str] = field(default_factory=dict)


class NicheConstructionAgent:
    """
    An Agent that actively modifies its operational environment to make 
    high-value strategies feasible.
    
    Instead of just competing on existing terms, it seeks to change the terms 
    (the niche) to favor its goals.
    """

    def __init__(self, target_profit_margin: float = 0.40):
        """
        Initialize the agent with a target profit margin.
        
        Args:
            target_profit_margin (float): The desired profit margin ratio.
        """
        if not 0 < target_profit_margin < 1:
            raise ValueError("Target profit margin must be between 0 and 1.")
        
        self.target_profit_margin = target_profit_margin
        self._action_history: List[Dict] = []
        logger.info(f"NicheConstructionAgent initialized with target margin: {target_profit_margin}")

    def _validate_market_state(self, state: MarketState) -> bool:
        """Helper function to validate market state data."""
        if state.customer_price_sensitivity < 0 or state.customer_price_sensitivity > 1:
            logger.error("Invalid price sensitivity range.")
            return False
        if state.base_product_value <= 0:
            logger.error("Base product value must be positive.")
            return False
        return True

    def _calculate_viability(self, state: MarketState, price: float, action: ActionType) -> float:
        """
        Helper function to calculate the viability of a price given a specific environmental modification.
        
        Viability is higher if the action successfully reduces sensitivity or increases perceived value.
        """
        perceived_value = state.base_product_value
        
        # Simulate environmental modification effects
        if action == ActionType.COGNITIVE_INJECTION:
            # E.g., Branding increases perceived value by 20%
            perceived_value *= 1.2 
        elif action == ActionType.BUNDLING:
            # Bundling reduces direct price comparison sensitivity by 30%
            effective_sensitivity = state.customer_price_sensitivity * 0.7
            # Check if price is acceptable relative to new perceived value
            gap = abs(price - perceived_value) / perceived_value
            return max(0.0, 1.0 - (gap * effective_sensitivity))
        
        # Default calculation
        effective_sensitivity = state.customer_price_sensitivity
        gap = abs(price - perceived_value) / perceived_value
        score = max(0.0, 1.0 - (gap * effective_sensitivity))
        
        return round(score, 3)

    def analyze_environment_for_niche(
        self, 
        current_state: MarketState, 
        target_price: float
    ) -> Tuple[bool, Optional[NicheConstructionStrategy]]:
        """
        Core Function 1: Analyzes the gap between current reality and target goal,
        and determines if a niche can be constructed to bridge that gap.
        
        Args:
            current_state (MarketState): The current market data.
            target_price (float): The desired price point for the product.
            
        Returns:
            Tuple[bool, Optional[NicheConstructionStrategy]]: 
                - bool: True if niche construction is successful/viable.
                - NicheConstructionStrategy: The plan to modify the environment.
        
        Example:
            >>> state = MarketState(10.0, 0.8, 12.0, 100.0)
            >>> agent = NicheConstructionAgent()
            >>> success, strategy = agent.analyze_environment_for_niche(state, 20.0)
        """
        if not self._validate_market_state(current_state):
            return False, None

        logger.info(f"Analyzing environment for target price: {target_price}")
        
        required_revenue = current_state.base_product_value * (1 + self.target_profit_margin)
        
        # If target price is naturally viable, no construction needed
        if target_price <= required_revenue:
            return True, None

        # Try different construction actions to find the best fit
        best_strategy: Optional[NicheConstructionStrategy] = None
        max_viability = 0.0

        # Strategy 1: Cognitive Injection (Marketing/Narrative)
        viability_cog = self._calculate_viability(current_state, target_price, ActionType.COGNITIVE_INJECTION)
        if viability_cog > max_viability:
            max_viability = viability_cog
            best_strategy = NicheConstructionStrategy(
                action_type=ActionType.COGNITIVE_INJECTION,
                description="Inject narrative to shift perceived value context.",
                modified_environment_params={"perceived_value_multiplier": 1.2},
                projected_viability_score=viability_cog,
                execution_payload={"slogan": "Not just water, it's hydrogen essence."}
            )

        # Strategy 2: Context Reframing (Anchoring)
        viability_ref = self._calculate_viability(current_state, target_price, ActionType.CONTEXT_REFRAMING)
        if viability_ref > max_viability:
            max_viability = viability_ref
            best_strategy = NicheConstructionStrategy(
                action_type=ActionType.CONTEXT_REFRAMING,
                description="Reframe context by anchoring against luxury competitors.",
                modified_environment_params={"anchor_price": 50.0},
                projected_viability_score=viability_ref,
                execution_payload={"display_comparison": "Competitor Luxury X ($50)"}
            )

        # Strategy 3: Bundling
        viability_bund = self._calculate_viability(current_state, target_price, ActionType.BUNDLING)
        if viability_bund > max_viability:
            max_viability = viability_bund
            best_strategy = NicheConstructionStrategy(
                action_type=ActionType.BUNDLING,
                description="Bundle with complementary goods to obscure unit cost.",
                modified_environment_params={"bundle_components": ["Product", "Service Warranty"]},
                projected_viability_score=viability_bund,
                execution_payload={"offer_text": "Get the Premium Care Package for just $5 more!"}
            )

        # Threshold for viability
        if max_viability > 0.6:
            logger.info(f"Viable niche found via {best_strategy.action_type.value} with score {max_viability}")
            return True, best_strategy
        
        logger.warning("No viable niche construction strategy found.")
        return False, None

    def execute_niche_construction(
        self, 
        strategy: NicheConstructionStrategy, 
        environment_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Core Function 2: Executes the niche construction strategy by modifying 
        the system's output parameters or configuration.
        
        This simulates the 'act' of changing the environment (e.g., updating the frontend,
        changing pricing rules).
        
        Args:
            strategy (NicheConstructionStrategy): The strategy to apply.
            environment_config (Dict): The current configuration of the environment.
            
        Returns:
            Dict[str, Any]: The modified environment configuration.
        """
        if not strategy:
            logger.error("No strategy provided for execution.")
            return environment_config

        logger.info(f"Executing construction action: {strategy.action_type.value}")
        
        modified_config = environment_config.copy()
        
        try:
            if strategy.action_type == ActionType.COGNITIVE_INJECTION:
                # Modify display logic to include narrative
                if "ui_settings" not in modified_config:
                    modified_config["ui_settings"] = {}
                modified_config["ui_settings"]["marketing_tag"] = strategy.execution_payload.get("slogan")
                modified_config["pricing_model"] = "value_based"

            elif strategy.action_type == ActionType.BUNDLING:
                # Modify product catalog logic
                if "catalog" not in modified_config:
                    modified_config["catalog"] = []
                
                bundle_item = {
                    "name": "Premium Bundle",
                    "price_modifier": 1.2,
                    "components": strategy.modified_environment_params.get("bundle_components", [])
                }
                modified_config["catalog"].append(bundle_item)
                modified_config["sales_mode"] = "bundle_first"

            elif strategy.action_type == ActionType.CONTEXT_REFRAMING:
                modified_config["display_anchor"] = strategy.modified_environment_params.get("anchor_price")
            
            # Log the history
            self._action_history.append({
                "strategy": strategy.action_type.value,
                "timestamp": "now",
                "success": True
            })
            
            return modified_config

        except Exception as e:
            logger.error(f"Error during niche construction execution: {e}")
            raise RuntimeError("Failed to modify environment configuration.") from e


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Define a difficult market scenario
    # Product cost is 10, Competitors sell at 12. We want to sell at 18.
    # Customers are highly price sensitive (0.9).
    market = MarketState(
        base_product_value=10.0,
        customer_price_sensitivity=0.9,
        competitor_price_avg=12.0,
        current_demand=50.0
    )
    
    target_price = 18.0
    
    # 2. Initialize Agent
    agent = NicheConstructionAgent(target_profit_margin=0.5)
    
    # 3. Analyze Environment to find a Niche
    is_viable, strategy = agent.analyze_environment_for_niche(market, target_price)
    
    if is_viable and strategy:
        print(f"Strategy Found: {strategy.description}")
        print(f"Action Type: {strategy.action_type.value}")
        print(f"Projected Viability: {strategy.projected_viability_score}")
        
        # 4. Execute Strategy on a dummy environment config
        current_system_config = {
            "ui_settings": {"theme": "light"},
            "catalog": [],
            "sales_mode": "standard"
        }
        
        new_config = agent.execute_niche_construction(strategy, current_system_config)
        
        print("\nModified Environment Config:")
        print(json.dumps(new_config, indent=2))
    else:
        print("Could not construct a viable niche for the target price.")