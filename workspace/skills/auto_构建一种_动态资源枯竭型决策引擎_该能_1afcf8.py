"""
Module: dynamic_resource_depletion_engine
Description: Implements a bio-inspired decision engine that avoids the sunk cost fallacy.
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Enumeration for decision outcomes."""
    CONTINUE_INVESTMENT = 1
    TRIGGER_WITHDRAWAL = 2
    SEEK_NEW_OPPORTUNITY = 3

@dataclass
class ResourceContext:
    """Data class representing the state of a resource patch."""
    patch_id: str
    current_roi: float  # Current Return on Investment (0.0 to 1.0)
    investment_duration: int  # Time units spent on this patch
    accumulated_cost: float  # Total resources spent so far
    estimated_remaining_potential: float  # Estimated value left in patch
    eco_opportunity_cost: float  # Cost of not exploring other patches (e.g., market drift)

class EcoDecisionEngine:
    """
    A dynamic decision engine based on the Marginal Value Theorem.
    
    It simulates biological foraging strategies to optimize resource allocation.
    It calculates the 'Marginal Rate of Return' (MRR) and compares it against the 
    'Environmental Average' to decide whether to stay or switch contexts.
    
    Input:
        - ResourceContext objects
    Output:
        - DecisionType enum
        - Actionable recommendation
    """

    def __init__(self, average_environment_roi: float = 0.15, exploration_cost: float = 0.05):
        """
        Initialize the engine.
        
        Args:
            average_environment_roi (float): The expected average ROI of finding a new patch.
            exploration_cost (float): The cost/risk associated with moving to a new patch.
        """
        if not (0 <= average_environment_roi <= 1):
            raise ValueError("average_environment_roi must be between 0 and 1.")
        
        self.global_avg_roi = average_environment_roi
        self.exploration_cost = exploration_cost
        self.history: Dict[str, List[float]] = {}
        logger.info(f"Engine initialized with Global Avg ROI: {self.global_avg_roi}")

    def _calculate_marginal_roi(self, context: ResourceContext) -> float:
        """
        [Helper] Calculate the instantaneous marginal rate of return.
        
        Simulates the diminishing returns curve (e.g., exponential decay).
        """
        if context.investment_duration == 0:
            return float('inf')
            
        # Decay factor: ROI typically drops as easy resources are exhausted
        # Here we model: Marginal = CurrentROI * e^(-lambda * time)
        # lambda is derived from estimated potential
        decay_rate = 0.1 if context.estimated_remaining_potential <= 0 else \
                     1.0 / (context.estimated_remaining_potential * 10 + 1)
        
        marginal = context.current_roi * math.exp(-decay_rate * context.investment_duration)
        
        # Account for eco opportunity cost (the longer we stay, the more we lose externally)
        marginal -= (context.eco_opportunity_cost * 0.01)  # Scaled impact
        
        return max(0.0, marginal)

    def _validate_context(self, context: ResourceContext) -> bool:
        """Validate input data sanity."""
        if context.investment_duration < 0:
            logger.error(f"Invalid duration for {context.patch_id}")
            return False
        if context.current_roi < -1 or context.current_roi > 2:
            logger.warning(f"Unusual ROI value {context.current_roi} for {context.patch_id}")
        return True

    def evaluate_sunk_cost_trap(self, context: ResourceContext) -> DecisionType:
        """
        [Core 1] Evaluates if the system is falling into a sunk cost trap.
        
        Compares the 'Cost of Staying' vs 'Expected Value of Leaving'.
        """
        if not self._validate_context(context):
            raise ValueError("Invalid Resource Context provided")

        marginal_roi = self._calculate_marginal_roi(context)
        
        # The "Bio-Instinct" Threshold: Expected Value of Moving
        # E(Move) = Global_Avg * Success_Probability - Exploration_Cost
        expected_move_value = self.global_avg_roi - self.exploration_cost
        
        logger.debug(f"Patch {context.patch_id}: Marginal ROI={marginal_roi:.4f}, "
                     f"Threshold (E[Move])={expected_move_value:.4f}")

        # Record history for analysis
        if context.patch_id not in self.history:
            self.history[context.patch_id] = []
        self.history[context.patch_id].append(marginal_roi)

        # Decision Logic
        if marginal_roi < expected_move_value:
            logger.warning(
                f"TRIGGER: Marginal ROI ({marginal_roi:.2f}) < "
                f"Opportunity Cost ({expected_move_value:.2f}). "
                f"Abandoning patch {context.patch_id}."
            )
            return DecisionType.SEEK_NEW_OPPORTUNITY
        
        if marginal_roi < 0.01 and context.accumulated_cost > 0:
            logger.error(f"Circuit Breaker: Resource depleted on {context.patch_id}")
            return DecisionType.TRIGGER_WITHDRAWAL

        logger.info(f"Decision: Continue investment in {context.patch_id}")
        return DecisionType.CONTINUE_INVESTMENT

    def execute_transition_strategy(self, context: ResourceContext, decision: DecisionType) -> str:
        """
        [Core 2] Executes the transition logic based on the decision.
        
        Handles the graceful shutdown of current ops and initiation of search.
        """
        try:
            if decision == DecisionType.CONTINUE_INVESTMENT:
                return f"Allocating next cycle resources to {context.patch_id}"
            
            elif decision == DecisionType.TRIGGER_WITHDRAWAL:
                # Graceful shutdown logic
                recovery_val = context.estimated_remaining_potential * 0.1 # Salvage value
                return (f"Emergency withdrawal from {context.patch_id}. "
                        f"Salvaged approx value: {recovery_val}")

            elif decision == DecisionType.SEEK_NEW_OPPORTUNITY:
                # Recalibration logic
                self.global_avg_roi = (self.global_avg_roi + context.current_roi) / 2
                return (f"Pivoting from {context.patch_id}. "
                        f"Updated Global ROI Benchmark: {self.global_avg_roi:.4f}")
            
            else:
                raise ValueError("Unknown Decision Type")
                
        except Exception as e:
            logger.exception("Error during transition execution")
            return "Error: Transition failed"

# Usage Example
if __name__ == "__main__":
    # 1. Setup Engine
    engine = EcoDecisionEngine(average_environment_roi=0.2, exploration_cost=0.05)
    
    # 2. Create a scenario (simulating a project depleting resources)
    project_alpha = ResourceContext(
        patch_id="proj_alpha",
        current_roi=0.35,         # Initially high ROI
        investment_duration=5,
        accumulated_cost=10000,
        estimated_remaining_potential=0.8, # High potential initially
        eco_opportunity_cost=0.02
    )
    
    print("--- Cycle 1: High Potential ---")
    decision = engine.evaluate_sunk_cost_trap(project_alpha)
    print(engine.execute_transition_strategy(project_alpha, decision))
    
    # 3. Simulate time passing and resource depletion (Sunk Cost scenario)
    # ROI drops, duration increases, remaining potential drops
    project_alpha.current_roi = 0.10
    project_alpha.investment_duration = 20
    project_alpha.estimated_remaining_potential = 0.1
    project_alpha.accumulated_cost = 50000
    
    print("\n--- Cycle 2: Depletion & Sunk Cost ---")
    decision_2 = engine.evaluate_sunk_cost_trap(project_alpha)
    print(engine.execute_transition_strategy(project_alpha, decision_2))