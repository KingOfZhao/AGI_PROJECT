"""
Module: auto_counterfactual_defense_ai_984463
Description: Implements Top-Down Counterfactual Reasoning and Defensive Decision Making for AGI systems.
             This module enables an AI agent to falsify its own hypothesis, predict failure probabilities
             in resource-constrained environments, and generate robust contingency plans (Plan B) alongside
             the optimal solution.
Domain: Game Theory / Cognitive Architecture
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Enumeration for risk assessment levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Action:
    """Represents a decision action with its attributes."""
    action_id: str
    estimated_success_prob: float  # 0.0 to 1.0
    resource_cost: float           # Arbitrary units
    estimated_value: float         # Expected utility if successful
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.estimated_success_prob <= 1.0:
            raise ValueError(f"Success probability must be between 0 and 1, got {self.estimated_success_prob}")
        if self.resource_cost < 0:
            raise ValueError("Resource cost cannot be negative")

@dataclass
class EnvironmentState:
    """Represents the current state of the operational environment."""
    available_resources: float
    volatility: float  # 0.0 (stable) to 1.0 (chaotic)
    hostility: float   # 0.0 (friendly) to 1.0 (hostile)
    
    def __post_init__(self):
        """Validate boundaries."""
        self.volatility = max(0.0, min(1.0, self.volatility))
        self.hostility = max(0.0, min(1.0, self.hostility))

@dataclass
class DecisionPlan:
    """The output structure containing the primary plan and contingencies."""
    primary_action: Action
    contingency_actions: List[Action]
    predicted_failure_points: List[str]
    risk_assessment: RiskLevel
    reasoning_trace: str

class CounterfactualReasoner:
    """
    Core class for performing counterfactual reasoning and defensive strategy generation.
    """
    
    def __init__(self, risk_threshold: float = 0.7):
        """
        Initialize the reasoner.
        
        Args:
            risk_threshold: The confidence threshold below which a Plan B is mandatory.
        """
        self.risk_threshold = risk_threshold
        logger.info(f"CounterfactualReasoner initialized with risk threshold: {risk_threshold}")

    def _validate_input_actions(self, actions: List[Action]) -> None:
        """Helper function to validate action lists."""
        if not actions:
            raise ValueError("Action list cannot be empty")
        for action in actions:
            if not isinstance(action, Action):
                raise TypeError(f"Invalid type in action list: {type(action)}")

    def _simulate_counterfactual(self, action: Action, state: EnvironmentState) -> Tuple[bool, str]:
        """
        Simulate a counterfactual scenario where the action fails.
        (Internal helper function)
        
        Returns:
            Tuple[is_likely_to_fail, failure_reason]
        """
        # Adjust probability based on environment hostility and volatility
        # This is a heuristic simulation of "Murphy's Law"
        failure_chance = (1.0 - action.estimated_success_prob)
        amplification_factor = 1.0 + (state.volatility * 0.5) + (state.hostility * 0.5)
        
        adjusted_failure_chance = min(1.0, failure_chance * amplification_factor)
        
        is_risky = adjusted_failure_chance > (1.0 - self.risk_threshold)
        
        failure_reason = ""
        if is_risky:
            if state.volatility > 0.7:
                failure_reason = "High environmental volatility compromises execution stability."
            elif state.hostility > 0.7:
                failure_reason = "Hostile agents likely to interfere with primary objective."
            elif action.resource_cost > state.available_resources * 0.8:
                failure_reason = "Resource consumption leaves no margin for error."
            else:
                failure_reason = "Low inherent success probability."
                
        logger.debug(f"Counterfactual sim for {action.action_id}: Risky={is_risky}, Reason='{failure_reason}'")
        return is_risky, failure_reason

    def evaluate_and_plan(
        self, 
        possible_actions: List[Action], 
        current_state: EnvironmentState
    ) -> DecisionPlan:
        """
        Main entry point. Selects the optimal action, performs counterfactual analysis 
        (asks 'what if this fails?'), and generates defensive contingencies.

        Args:
            possible_actions: List of potential actions the AI can take.
            current_state: The current context of the environment.

        Returns:
            DecisionPlan: A comprehensive plan including Plan A and Plan B.
        """
        logger.info("Starting Top-Down Counterfactual Evaluation...")
        
        # 1. Data Validation
        self._validate_input_actions(possible_actions)
        if current_state.available_resources <= 0:
            logger.warning("Resources depleted. Switching to emergency protocols.")
            # Fallback logic would go here, for now we raise error or return empty
            raise RuntimeError("Insufficient resources for planning.")

        # 2. Identify Primary Candidate (The "Optimistic" Best)
        # Sort by a simple heuristic: (Value * Prob) / Cost
        def score_action(a: Action) -> float:
            if a.resource_cost == 0: return float('inf') # Avoid div by zero
            return (a.estimated_value * a.estimated_success_prob) / a.resource_cost

        sorted_actions = sorted(possible_actions, key=score_action, reverse=True)
        primary_action = sorted_actions[0]
        
        logger.info(f"Selected Primary Action: {primary_action.action_id} (Score: {score_action(primary_action):.2f})")

        # 3. Counterfactual Reasoning (The "Pessimistic" View)
        is_risky, failure_reason = self._simulate_counterfactual(primary_action, current_state)
        
        predicted_failures = []
        contingency_actions = []
        
        if is_risky:
            predicted_failures.append(failure_reason)
            logger.warning(f"Primary action deemed risky. Reason: {failure_reason}")
            
            # 4. Generate Plan B (Defensive Decision)
            # We look for an action that:
            # a) Is different from Plan A
            # b) Has higher robustness (success prob) or lower cost
            # c) Fits within remaining resources (if Plan A commits resources)
            
            remaining_resources = current_state.available_resources - primary_action.resource_cost
            
            candidates_plan_b = [
                a for a in sorted_actions[1:] 
                if a.resource_cost <= remaining_resources or a.estimated_success_prob > primary_action.estimated_success_prob
            ]
            
            if candidates_plan_b:
                # Select the most robust (highest success probability) as Plan B
                plan_b = max(candidates_plan_b, key=lambda x: x.estimated_success_prob)
                contingency_actions.append(plan_b)
                logger.info(f"Generated Contingency (Plan B): {plan_b.action_id}")
            else:
                logger.warning("No viable Plan B found within resource constraints.")

        # 5. Determine Overall Risk Level
        if primary_action.estimated_success_prob < 0.3:
            risk_level = RiskLevel.CRITICAL
        elif is_risky:
            risk_level = RiskLevel.HIGH
        elif primary_action.estimated_success_prob < 0.7:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        reasoning = (
            f"Primary strategy '{primary_action.action_id}' selected based on utility score. "
            f"Counterfactual analysis indicates {'stability' if not is_risky else 'volatility'}. "
            f"Defensive posture: {'Active' if contingency_actions else 'Passive'}."
        )

        return DecisionPlan(
            primary_action=primary_action,
            contingency_actions=contingency_actions,
            predicted_failure_points=predicted_failures,
            risk_assessment=risk_level,
            reasoning_trace=reasoning
        )

# --- Usage Example ---
if __name__ == "__main__":
    try:
        # 1. Define the Environment
        env = EnvironmentState(
            available_resources=100.0,
            volatility=0.8,  # Very volatile environment
            hostility=0.3    # Moderately friendly
        )

        # 2. Define Possible Actions
        actions_list = [
            Action(
                action_id="alpha_strike",
                estimated_success_prob=0.6,
                resource_cost=80.0,
                estimated_value=1000.0
            ),
            Action(
                action_id="conservative_approach",
                estimated_success_prob=0.9,
                resource_cost=30.0,
                estimated_value=400.0
            ),
            Action(
                action_id="guerrilla_tactics",
                estimated_success_prob=0.75,
                resource_cost=40.0,
                estimated_value=600.0
            )
        ]

        # 3. Initialize Reasoner
        ai_reasoner = CounterfactualReasoner(risk_threshold=0.75)

        # 4. Execute Decision Process
        final_plan = ai_reasoner.evaluate_and_plan(actions_list, env)

        # 5. Output Results
        print("\n" + "="*30)
        print(f" DECISION OUTPUT: {final_plan.primary_action.action_id}")
        print("="*30)
        print(f"Risk Level: {final_plan.risk_assessment.name}")
        print(f"Plan B: {[a.action_id for a in final_plan.contingency_actions]}")
        print(f"Failure Predictions: {final_plan.predicted_failure_points}")
        print(f"Logic: {final_plan.reasoning_trace}")
        print("="*30 + "\n")

    except ValueError as ve:
        logger.error(f"Input Validation Error: {ve}")
    except RuntimeError as re:
        logger.critical(f"System Runtime Error: {re}")
    except Exception as e:
        logger.exception(f"Unexpected System Failure: {e}")