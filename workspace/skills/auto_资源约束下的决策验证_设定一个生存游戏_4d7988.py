"""
Module: auto_资源约束下的决策验证_设定一个生存游戏_4d7988
Description: [AGI SKILL] Resource-Constrained Decision Verification in a Survival Game.
             Simulates a Mars survival scenario with limited resources (Oxygen, Water, Energy).
             Compares a Myopic (Greedy) strategy against a Farsighted (Dynamic Programming/Lookahead)
             strategy to verify if the AI can sacrifice short-term gain for long-term survival.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MarsSurvivalSimulator")


# 2. Data Structures
class ActionType(Enum):
    """Available actions for the agent."""
    EXPLORE = "Explore"      # High resource cost, high reward
    CONSERVE = "Conserve"    # Low resource cost, low reward
    RECYCLE = "Recycle"      # Medium cost, restores resources


@dataclass
class GameState:
    """Represents the current state of the survival game."""
    step: int = 0
    oxygen: float = 100.0
    water: float = 100.0
    energy: float = 100.0
    survivors: int = 10
    is_alive: bool = True
    
    def resource_sum(self) -> float:
        return self.oxygen + self.water + self.energy


# 3. Core Components
class MarsSurvivalEnvironment:
    """
    Simulates the Mars environment mechanics.
    Handles state transitions based on actions and random events.
    """
    
    def __init__(self, max_steps: int = 100, disaster_probability: float = 0.05):
        self.max_steps = max_steps
        self.disaster_probability = disaster_probability
        logger.info(f"Environment initialized for {max_steps} steps.")
        
    def _apply_costs(self, state: GameState, costs: Dict[str, float]) -> None:
        """Apply resource costs to the state."""
        state.oxygen = max(0.0, state.oxygen - costs.get('oxygen', 0))
        state.water = max(0.0, state.water - costs.get('water', 0))
        state.energy = max(0.0, state.energy - costs.get('energy', 0))
        
    def _check_survival(self, state: GameState) -> bool:
        """Check if the colony survives the current state."""
        if state.oxygen <= 0 or state.water <= 0 or state.energy <= 0:
            state.is_alive = False
            # Fatalities based on deficit severity
            deficit = abs(min(state.oxygen, state.water, state.energy))
            fatalities = min(state.survivors, int(deficit / 10) + 1)
            state.survivors -= fatalities
            logger.warning(f"Step {state.step}: Critical failure! {fatalities} casualties.")
            return False
        return True
    
    def step(self, state: GameState, action: ActionType) -> Tuple[GameState, float]:
        """
        Execute one step in the environment.
        
        Args:
            state: Current game state.
            action: Action taken by the agent.
            
        Returns:
            Tuple[GameState, float]: New state and reward (survivors saved).
        """
        if not state.is_alive:
            return state, 0.0
            
        new_state = GameState(
            step=state.step + 1,
            oxygen=state.oxygen,
            water=state.water,
            energy=state.energy,
            survivors=state.survivors
        )
        
        # Define action impacts
        if action == ActionType.EXPLORE:
            costs = {'oxygen': 3.0, 'water': 3.0, 'energy': 4.0}
            reward = 2.0  # Saves 2 people potentially
        elif action == ActionType.CONSERVE:
            costs = {'oxygen': 0.5, 'water': 0.5, 'energy': 0.5}
            reward = 0.0  # Saves no one, but preserves status quo
        elif action == ActionType.RECYCLE:
            costs = {'energy': 5.0}  # consumes energy
            gains = {'oxygen': 4.0, 'water': 4.0}  # gains resources
            costs['oxygen'] = -gains['oxygen']  # negative cost = gain
            costs['water'] = -gains['water']
            reward = 0.0
        else:
            raise ValueError(f"Unknown action: {action}")

        # Apply deterministic costs
        self._apply_costs(new_state, costs)
        
        # Random Environmental Hazard (e.g., Dust Storm)
        if random.random() < self.disaster_probability:
            hazard_cost = {'oxygen': 10.0, 'energy': 10.0}
            self._apply_costs(new_state, hazard_cost)
            logger.info(f"Step {new_state.step}: Dust Storm hit!")

        # Check survival
        self._check_survival(new_state)
        
        return new_state, reward if new_state.is_alive else -10.0


class DecisionAgent:
    """
    Agents with different decision-making policies.
    """
    
    def __init__(self, policy: str = "greedy"):
        self.policy = policy
        logger.info(f"Agent created with policy: {policy}")

    def greedy_decision(self, state: GameState) -> ActionType:
        """
        Short-sighted policy: Always choose EXPLORE to maximize immediate reward.
        """
        if state.resource_sum() > 30:
            return ActionType.EXPLORE
        else:
            # Panic mode
            return ActionType.CONSERVE

    def farsighted_decision(self, state: GameState, env: MarsSurvivalEnvironment) -> ActionType:
        """
        Dynamic-Programming-inspired policy.
        Uses a simplified heuristic look-ahead:
        - If resources are abundant, explore.
        - If resources are dropping below a safety threshold relative to remaining steps, conserve/recycle.
        - Specifically tries to reach step 100.
        """
        steps_remaining = env.max_steps - state.step
        avg_consumption_per_step = 2.0  # Rough estimate for 'Explore'
        
        # Safety Margin Calculation
        safety_threshold = steps_remaining * avg_consumption_per_step
        
        current_resources = state.resource_sum()
        
        # Decision Logic
        if current_resources < safety_threshold * 1.5:
            # Resource Critical: Must Recycle/Conserve
            if state.energy > 20:
                return ActionType.RECYCLE
            else:
                return ActionType.CONSERVE
        else:
            # Resources OK: Can afford to Explore
            return ActionType.EXPLORE


# 4. Main Verification Function
def run_simulation(agent_policy: str = "farsighted", verbose: bool = False) -> Dict[str, int]:
    """
    Runs a complete 100-step simulation loop to validate the decision logic.
    
    Args:
        agent_policy (str): 'greedy' or 'farsighted'.
        verbose (bool): Enable step-by-step logging.
        
    Returns:
        Dict containing final step, survivors, and status.
    """
    env = MarsSurvivalEnvironment(max_steps=100)
    state = GameState()
    agent = DecisionAgent(policy=agent_policy)
    total_reward = 0.0
    
    logger.info(f"--- Starting Simulation: Policy={agent_policy} ---")
    
    while state.step < env.max_steps and state.is_alive:
        # Determine Action
        if agent.policy == "greedy":
            action = agent.greedy_decision(state)
        else:
            action = agent.farsighted_decision(state, env)
            
        # Execute
        prev_survivors = state.survivors
        state, reward = env.step(state, action)
        total_reward += reward
        
        if verbose:
            logger.info(
                f"Step {state.step}: Action={action.value}, "
                f"Res={state.resource_sum():.1f}, Survivors={state.survivors}"
            )
            
    result = {
        "final_step": state.step,
        "survivors": state.survivors,
        "total_reward": total_reward,
        "completed": state.step == env.max_steps
    }
    
    logger.info(f"--- Simulation End: {result} ---")
    return result


def validate_results(results: Dict[str, Dict]) -> bool:
    """
    Analyzes the results to verify if the 'farsighted' agent outperforms 'greedy'.
    
    Args:
        results: Dictionary containing results of both agents.
        
    Returns:
        True if the hypothesis is validated (Farsighted survives longer/better).
    """
    greedy_score = results['greedy']['survivors']
    smart_score = results['farsighted']['survivors']
    
    logger.info("Validation Report:")
    logger.info(f"Greedy Survivors: {greedy_score}")
    logger.info(f"Farsighted Survivors: {smart_score}")
    
    if smart_score > greedy_score:
        logger.info("SUCCESS: Dynamic planning resulted in better survival rates.")
        return True
    else:
        logger.warning("FAILURE: Greedy algorithm performed equally or better.")
        return False


# 5. Execution Block
if __name__ == "__main__":
    # Run comparison
    random.seed(42)  # For reproducibility
    
    # Test Greedy
    greedy_res = run_simulation(agent_policy="greedy", verbose=False)
    
    # Test Farsighted (Dynamic Planning)
    smart_res = run_simulation(agent_policy="farsighted", verbose=False)
    
    # Validate
    validation_data = {"greedy": greedy_res, "farsighted": smart_res}
    is_valid = validate_results(validation_data)