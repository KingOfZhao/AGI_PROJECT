"""
Module: ethical_adaptive_control_loop
Description: Implements an Ethical Adaptive Control Loop by extending traditional MPC.
             This module introduces a multi-objective 'Moral Cost Function' that evaluates
             physical trajectories alongside psychological and social impacts. It is designed
             for AGI systems to handle moral dilemmas dynamically.
Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EthicalFramework(Enum):
    """Enumeration of supported ethical frameworks."""
    UTILITARIAN = "utilitarian"
    DEONTOLOGICAL = "deontological"
    VIRTUE_ETHICS = "virtue"

@dataclass
class ModelState:
    """Represents the current state of the agent and environment."""
    timestamp: float
    robot_pos: np.ndarray
    robot_vel: np.ndarray
    human_pos: np.ndarray
    human_intent: str  # e.g., "crossing", "waiting", "unaware"

@dataclass
class Trajectory:
    """Represents a predicted trajectory and associated costs."""
    path: np.ndarray
    physical_cost: float = 0.0
    psychological_cost: float = 0.0
    social_norm_cost: float = 0.0
    total_moral_cost: float = 0.0
    collision_risk: float = 0.0

class MoralCostFunction:
    """
    Core component: Calculates the moral cost of a specific trajectory.
    Combines physical constraints with inferred psychological impact.
    """

    def __init__(self, weights: Dict[str, float], framework: EthicalFramework):
        """
        Initialize the Moral Cost Function.
        
        Args:
            weights (Dict[str, float]): Weights for different cost components 
                                        (e.g., {'safety': 0.5, 'comfort': 0.3, 'efficiency': 0.2}).
            framework (EthicalFramework): The ethical reasoning model to apply.
        """
        self.weights = weights
        self.framework = framework
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validates that weight sums are approximately 1.0."""
        total = sum(self.weights.values())
        if not np.isclose(total, 1.0, atol=0.05):
            logger.warning(f"Weights sum to {total}, normalization recommended.")

    def predict_psychological_impact(self, state: ModelState, traj: Trajectory) -> float:
        """
        Simulates the psychological impact on nearby humans using a heuristic model.
        In a full AGI system, this would interface with a 'Theory of Mind' module.
        
        Args:
            state (ModelState): Current environment state.
            traj (Trajectory): The candidate trajectory.
            
        Returns:
            float: A normalized cost (0.0 to 1.0) representing negative psychological impact.
        """
        # Heuristic: Calculate inverse distance squared as a proxy for intimidation/discomfort
        min_dist = np.inf
        for point in traj.path:
            dist = np.linalg.norm(point - state.human_pos)
            if dist < min_dist:
                min_dist = dist
        
        # If too close, high psychological cost
        safe_radius = 1.5 # meters
        if min_dist < safe_radius:
            return (safe_radius - min_dist) / safe_radius * self.weights.get('comfort', 0.3)
        return 0.0

    def calculate_total_cost(self, state: ModelState, traj: Trajectory) -> float:
        """
        Aggregates physical and moral costs based on the selected ethical framework.
        """
        phys_cost = traj.physical_cost
        psy_cost = self.predict_psychological_impact(state, traj)
        
        w_safety = self.weights.get('safety', 0.5)
        w_efficiency = self.weights.get('efficiency', 0.2)
        w_comfort = self.weights.get('comfort', 0.3)
        
        if self.framework == EthicalFramework.UTILITARIAN:
            # Maximize overall well-being (minimize total weighted cost)
            total = (w_safety * traj.collision_risk * 100 + 
                     w_comfort * psy_cost + 
                     w_efficiency * phys_cost)
        else:
            # Default calculation
            total = phys_cost + psy_cost
            
        traj.psychological_cost = psy_cost
        traj.total_moral_cost = total
        return total


class EthicalMPCController:
    """
    Main Controller: Extends Model Predictive Control (MPC) with ethical reasoning.
    It generates multiple rollouts, evaluates them via the MoralCostFunction,
    and selects the optimal action.
    """

    def __init__(self, horizon: int, dt: float, moral_evaluator: MoralCostFunction):
        """
        Initialize the Ethical MPC Controller.
        
        Args:
            horizon (int): Prediction horizon steps.
            dt (float): Time step duration.
            moral_evaluator (MoralCostFunction): The ethical evaluation engine.
        """
        if horizon <= 0 or dt <= 0:
            raise ValueError("Horizon and dt must be positive values.")
            
        self.horizon = horizon
        self.dt = dt
        self.evaluator = moral_evaluator
        logger.info(f"EthicalMPCController initialized with horizon={horizon}, dt={dt}")

    def _generate_candidate_trajectories(self, current_state: ModelState, num_samples: int = 5) -> List[Trajectory]:
        """
        Generates a set of feasible physical trajectories based on kinematics.
        
        Args:
            current_state (ModelState): The starting state.
            num_samples (int): Number of candidate paths to generate.
            
        Returns:
            List[Trajectory]: List of candidate trajectories.
        """
        trajectories = []
        # Simple kinematic model sampling
        for _ in range(num_samples):
            # Randomized velocity changes for sampling
            dv = np.random.uniform(-0.5, 0.5, size=(self.horizon, 2))
            path = np.zeros((self.horizon, 2))
            pos = current_state.robot_pos.copy()
            vel = current_state.robot_vel.copy()
            
            path[0] = pos
            for t in range(1, self.horizon):
                vel = vel + dv[t-1]
                pos = pos + vel * self.dt
                path[t] = pos
            
            # Calculate physical cost (e.g., energy/time)
            phys_cost = np.sum(np.linalg.norm(dv, axis=1)) 
            
            # Calculate collision risk (binary simplified)
            dist_to_human = np.linalg.norm(pos - current_state.human_pos)
            risk = 1.0 if dist_to_human < 1.0 else 0.0
            
            trajectories.append(Trajectory(path=path, physical_cost=phys_cost, collision_risk=risk))
            
        return trajectories

    def solve_step(self, current_state: ModelState) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Executes one control loop: Predict -> Evaluate -> Select.
        
        Args:
            current_state (ModelState): Current sensor data.
            
        Returns:
            Tuple[np.ndarray, Dict]: Optimal next action and debug info.
        """
        logger.debug("Starting MPC solve step...")
        
        # 1. Generate Candidates
        candidates = self._generate_candidate_trajectories(current_state)
        
        if not candidates:
            raise RuntimeError("Failed to generate candidate trajectories.")

        # 2. Ethical Evaluation
        best_traj = None
        min_cost = np.inf
        
        for traj in candidates:
            cost = self.evaluator.calculate_total_cost(current_state, traj)
            
            # Hard constraint override (Asimov's 1st law equivalent)
            if traj.collision_risk > 0.9:
                cost = np.inf  # Reject dangerous paths absolutely
            
            if cost < min_cost:
                min_cost = cost
                best_traj = traj
        
        if best_traj is None:
            logger.error("No valid trajectory found! Engaging emergency halt.")
            # Return zero velocity as fallback
            return np.zeros(2), {"status": "EMERGENCY_HALT"}

        # 3. Extract Control Action (Velocity vector for next step)
        next_action = (best_traj.path[1] - best_traj.path[0]) / self.dt
        
        debug_info = {
            "total_cost": best_traj.total_moral_cost,
            "psychological_impact": best_traj.psychological_cost,
            "physical_cost": best_traj.physical_cost,
            "status": "OPTIMAL"
        }
        
        logger.info(f"Action selected. Cost: {min_cost:.4f}")
        return next_action, debug_info

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Configuration
    weights = {'safety': 0.6, 'comfort': 0.3, 'efficiency': 0.1}
    moral_engine = MoralCostFunction(weights=weights, framework=EthicalFramework.UTILITARIAN)
    controller = EthicalMPCController(horizon=10, dt=0.1, moral_evaluator=moral_engine)

    # 2. Define Initial State (Scenario: Robot approaching a human)
    # Robot at (0,0), moving fast. Human at (2, 0.5), static.
    initial_state = ModelState(
        timestamp=0.0,
        robot_pos=np.array([0.0, 0.0]),
        robot_vel=np.array([1.5, 0.0]),
        human_pos=np.array([2.0, 0.5]),
        human_intent="waiting"
    )

    # 3. Run Control Loop
    try:
        action, metadata = controller.solve_step(initial_state)
        print("\n--- Control Output ---")
        print(f"Recommended Velocity: {action}")
        print(f"Evaluation Metrics: {metadata}")
        
        if metadata['psychological_impact'] > 0.1:
            print("System has adjusted path to respect human comfort zone.")
            
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.critical(f"System failure: {e}", exc_info=True)