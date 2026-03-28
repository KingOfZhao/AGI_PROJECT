"""
Time Compression Simulator for AGI Long-Term Reasoning

This module addresses the limitation of human lifespan by providing a mechanism
to simulate long-term sociological changes (50+ years) that are otherwise
imperceptible to human cognition. It implements a Monte Carlo simulation
engine to project the probability distribution of future societal states based
on current parameters.

Key Features:
- Monte Carlo simulation for probabilistic forecasting.
- Data validation for societal state nodes.
- Categorization of future scenarios (Collapse, Stagnation, Prosperity).
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FutureScenario(Enum):
    """Enumeration of potential long-term societal outcomes."""
    COLLAPSE = "Civilizational Collapse"
    STAGNATION = "Technological Stagnation"
    PROSPERITY = "Sustainable Prosperity"
    TRANS_HUMANIST = "Post-Scarcity / Trans-Humanist"


@dataclass
class SocialStateNode:
    """
    Represents the state of a society at a specific point in time.

    Attributes:
        tech_index (float): 0.0 to 10.0, representing technological capability.
        resource_scarcity (float): 0.0 (abundant) to 1.0 (depleted).
        social_cohesion (float): 0.0 (anarchy) to 1.0 (utopian unity).
        year (int): The current simulation year.
    """
    tech_index: float
    resource_scarcity: float
    social_cohesion: float
    year: int

    def __post_init__(self):
        """Validate initial data upon creation."""
        self.validate()

    def validate(self) -> None:
        """
        Validates the data integrity of the social state node.

        Raises:
            ValueError: If any attribute is out of its expected bounds.
        """
        if not 0.0 <= self.tech_index <= 20.0:
            raise ValueError(f"Tech index {self.tech_index} out of bounds [0, 20]")
        if not 0.0 <= self.resource_scarcity <= 1.0:
            raise ValueError(f"Resource scarcity {self.resource_scarcity} out of bounds [0, 1]")
        if not 0.0 <= self.social_cohesion <= 1.0:
            raise ValueError(f"Social cohesion {self.social_cohesion} out of bounds [0, 1]")
        if self.year < 0:
            raise ValueError(f"Year {self.year} cannot be negative")


def _apply_societal_dynamics(state: SocialStateNode) -> SocialStateNode:
    """
    Helper function to calculate the next state based on non-linear dynamics.

    This function simulates the interaction between technology, resources,
    and social cohesion over a single time step (e.g., 1 year).

    Logic:
    - Technology grows exponentially but is hindered by low cohesion.
    - Resources are consumed by high technology but improved by tech efficiency.
    - Cohesion drops if resources become too scarce.

    Args:
        state (SocialStateNode): Current state.

    Returns:
        SocialStateNode: Next year's state.
    """
    # Random shocks (wars, discoveries, pandemics)
    shock_tech = random.uniform(-0.1, 0.2)
    shock_resource = random.uniform(-0.05, 0.05)
    shock_cohesion = random.uniform(-0.1, 0.1)

    # Dynamics
    tech_growth_rate = 0.05 * state.social_cohesion
    new_tech = state.tech_index * (1 + tech_growth_rate) + shock_tech
    new_tech = max(0.0, new_tech)

    # Resource consumption vs efficiency gains
    consumption = 0.02 * state.tech_index
    efficiency_gain = 0.01 * (state.tech_index ** 1.2)
    new_scarcity = state.resource_scarcity + (consumption - efficiency_gain) + shock_resource
    new_scarcity = max(0.0, min(1.0, new_scarcity))

    # Social stability depends on resource availability
    cohesion_decay = 0.01 if new_scarcity > 0.8 else 0.0
    new_cohesion = state.social_cohesion - cohesion_decay + shock_cohesion
    new_cohesion = max(0.0, min(1.0, new_cohesion))

    return SocialStateNode(
        tech_index=new_tech,
        resource_scarcity=new_scarcity,
        social_cohesion=new_cohesion,
        year=state.year + 1
    )


def run_time_compression_simulation(
    initial_state: SocialStateNode,
    target_years: int = 50,
    monte_carlo_runs: int = 1000
) -> List[SocialStateNode]:
    """
    Core Function 1: Runs the time compression simulation.

    Simulates multiple timelines (Monte Carlo) to project the state of society
    `target_years` into the future. This compresses decades of complex
    interactions into a computational result.

    Args:
        initial_state (SocialStateNode): The starting point of the simulation.
        target_years (int): Number of years to simulate forward. Default 50.
        monte_carlo_runs (int): Number of parallel timelines to simulate. Default 1000.

    Returns:
        List[SocialStateNode]: A list of final states for each simulation run.

    Raises:
        ValueError: If target_years or monte_carlo_runs are non-positive.
    """
    logger.info(f"Starting time compression: {target_years} years over {monte_carlo_runs} runs.")

    if target_years <= 0:
        raise ValueError("Target years must be positive")
    if monte_carlo_runs <= 0:
        raise ValueError("Monte Carlo runs must be positive")

    final_states: List[SocialStateNode] = []

    for i in range(monte_carlo_runs):
        try:
            current_state = initial_state
            # Simulate year by year
            for _ in range(target_years):
                current_state = _apply_societal_dynamics(current_state)
            final_states.append(current_state)
        except Exception as e:
            logger.error(f"Simulation run {i} failed: {e}")
            # Continue with other runs to ensure robustness

    logger.info(f"Simulation complete. Generated {len(final_states)} future data points.")
    return final_states


def analyze_probability_distribution(future_states: List[SocialStateNode]) -> Dict[FutureScenario, float]:
    """
    Core Function 2: Analyzes the simulation results to determine outcome probabilities.

    Categorizes the final states into distinct scenarios and calculates the
    probability of each occurring.

    Args:
        future_states (List[SocialStateNode]): List of states returned by the simulator.

    Returns:
        Dict[FutureScenario, float]: A dictionary mapping scenarios to their probability (0.0 to 1.0).
    """
    if not future_states:
        logger.warning("No future states provided for analysis.")
        return {}

    counts: Dict[FutureScenario, int] = {scenario: 0 for scenario in FutureScenario}
    total_runs = len(future_states)

    for state in future_states:
        # Classification Logic
        if state.resource_scarcity >= 0.95 or state.social_cohesion < 0.2:
            counts[FutureScenario.COLLAPSE] += 1
        elif state.tech_index > 15.0 and state.resource_scarcity < 0.3:
            counts[FutureScenario.TRANS_HUMANIST] += 1
        elif state.tech_index > 5.0 and state.social_cohesion > 0.6:
            counts[FutureScenario.PROSPERITY] += 1
        else:
            counts[FutureScenario.STAGNATION] += 1

    # Calculate probabilities
    probabilities = {
        scenario: (count / total_runs) for scenario, count in counts.items()
    }

    logger.info("Probability distribution calculated.")
    return probabilities


# Example Usage
if __name__ == "__main__":
    # Define the current state of the world (Input)
    current_world = SocialStateNode(
        tech_index=1.0,          # Modern industrial era
        resource_scarcity=0.3,   # Some strain on resources
        social_cohesion=0.6,     # Moderate stability
        year=2024
    )

    try:
        # Run the simulation (Core Function 1)
        futures = run_time_compression_simulation(
            initial_state=current_world,
            target_years=50,
            monte_carlo_runs=2000
        )

        # Analyze results (Core Function 2)
        outcomes = analyze_probability_distribution(futures)

        # Output results
        print("\n--- 50-Year AGI Projection Report ---")
        for scenario, prob in outcomes.items():
            print(f"{scenario.value}: {prob:.2%}")

    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system failure: {e}")