"""
Module: inverse_dynamics_digitizer.py

Description:
    This module implements an 'Inverse Dynamics Digitizer' designed to infer
    implicit expert strategy parameters using Reinforcement Learning (RL).
    
    It simulates an environment where an agent (the digitizer) attempts to
    maximize a quality metric (e.g., weld strength) by adjusting continuous
    control parameters (e.g., travel speed, arc height). Through trial and
    error, the agent learns the non-linear coupling between these parameters
    that results in 'expert-like' stability and quality.

    The core concept is to reverse-engineer the "what" (high quality result)
    into the "how" (specific parameter curves), effectively digitizing
    human intuition.

Author: AGI System
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass, field

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
PARAM_BOUNDS = {
    'travel_speed': (1.0, 20.0),   # mm/s
    'arc_height': (1.0, 10.0),     # mm
    'current': (50.0, 200.0)       # Amperes
}

@dataclass
class SystemState:
    """Represents the current state of the simulation."""
    step: int = 0
    quality_score: float = 0.0
    params: Dict[str, float] = field(default_factory=dict)
    is_stable: bool = False

class InverseDynamicsEnvironment:
    """
    A simulated environment representing the physical process (e.g., welding).
    
    This environment takes action vectors (parameter adjustments) and returns
    a new state and a reward based on the quality of the result. It contains
    the 'hidden' physics logic that the RL agent needs to learn.
    """

    def __init__(self, max_steps: int = 100):
        """
        Initialize the environment.

        Args:
            max_steps (int): Maximum steps per episode.
        """
        self.max_steps = max_steps
        self.state = SystemState()
        self._initialize_parameters()
        logger.info("Inverse Dynamics Environment initialized.")

    def _initialize_parameters(self) -> None:
        """Reset parameters to starting baseline."""
        self.state.step = 0
        self.state.quality_score = 0.0
        # Start at mid-range
        self.state.params = {
            key: (min_val + max_val) / 2 
            for key, (min_val, max_val) in PARAM_BOUNDS.items()
        }

    def reset(self) -> np.ndarray:
        """
        Resets the environment to an initial state.

        Returns:
            np.ndarray: The initial state vector.
        """
        self._initialize_parameters()
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """Converts current state dict to a normalized observation vector."""
        obs = []
        for key, bounds in PARAM_BOUNDS.items():
            val = self.state.params.get(key, 0.0)
            # Normalize to [0, 1]
            norm_val = (val - bounds[0]) / (bounds[1] - bounds[0])
            obs.append(np.clip(norm_val, 0, 1))
        return np.array(obs, dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Executes one time step within the environment.

        Args:
            action (np.ndarray): A vector of deltas to apply to parameters.
                                 Expected range roughly [-1, 1] normalized.

        Returns:
            Tuple[np.ndarray, float, bool, Dict]: 
                - observation: New state vector.
                - reward: Calculated reward (Quality score).
                - done: Whether the episode has ended.
                - info: Diagnostic information.
        """
        self.state.step += 1
        
        # 1. Apply Action (Update Parameters)
        # Action is treated as a relative change to current params
        param_keys = list(PARAM_BOUNDS.keys())
        for i, key in enumerate(param_keys):
            delta = action[i] * 0.5 # Scale factor for stability
            min_b, max_b = PARAM_BOUNDS[key]
            current_val = self.state.params[key]
            new_val = np.clip(current_val + delta, min_b, max_b)
            self.state.params[key] = new_val

        # 2. Calculate Reward (The 'Black Box' Physics)
        # Simulating the non-linear coupling between speed, height, and current.
        # Ideal relationship: High speed requires higher arc height and specific current.
        speed = self.state.params['travel_speed']
        height = self.state.params['arc_height']
        current = self.state.params['current']
        
        # Synthetic Physics Logic:
        # Optimal height is roughly 0.5 * speed.
        # Optimal current is roughly 10 * speed + 50.
        target_height = 0.5 * speed
        target_current = 10 * speed + 50
        
        height_error = abs(height - target_height)
        current_error = abs(current - target_current) / 100.0 # Normalized
        
        # Reward is high if errors are low (Inverse Kinematics logic)
        stability_reward = np.exp(-(height_error + current_error))
        
        # Add noise to simulate real-world variance
        noise = np.random.normal(0, 0.05)
        total_reward = stability_reward + noise
        
        self.state.quality_score = total_reward
        self.state.is_stable = stability_reward > 0.8

        # 3. Check Termination
        done = self.state.step >= self.max_steps
        
        info = {
            "quality": total_reward,
            "params": self.state.params.copy(),
            "is_stable": self.state.is_stable
        }

        return self._get_observation(), total_reward, done, info

class RLAgent:
    """
    A Simple Policy Gradient Agent (REINFORCE-like) acting as the Digitizer.
    
    It explores the parameter space to maximize the reward signal provided
    by the environment, effectively 'learning' the inverse dynamics.
    """

    def __init__(self, param_dims: int, learning_rate: float = 0.01):
        """
        Initialize the Agent.

        Args:
            param_dims (int): Number of parameters to control.
            learning_rate (float): Step size for policy updates.
        """
        self.param_dims = param_dims
        self.lr = learning_rate
        
        # Simple Linear Policy: Weights for state->action mapping + Bias
        # State is observation (normalized params), Action is delta
        self.weights = np.random.randn(param_dims, param_dims) * 0.1
        self.bias = np.zeros(param_dims)
        
        # Memory for trajectory
        self.states: List[np.ndarray] = []
        self.actions: List[np.ndarray] = []
        self.rewards: List[float] = []
        
        logger.info(f"RL Agent initialized with {param_dims} dimensions.")

    def select_action(self, state: np.ndarray) -> np.ndarray:
        """
        Selects an action based on the current policy (deterministic + noise).
        
        Args:
            state (np.ndarray): Current environment observation.
            
        Returns:
            np.ndarray: Action vector (parameter deltas).
        """
        # Linear response
        mean_action = np.dot(state, self.weights) + self.bias
        
        # Add exploration noise (Gaussian)
        exploration_noise = np.random.normal(0, 0.2, size=self.param_dims)
        action = mean_action + exploration_noise
        return action.astype(np.float32)

    def store_transition(self, state: np.ndarray, action: np.ndarray, reward: float) -> None:
        """Stores a single step transition in memory."""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)

    def update_policy(self) -> float:
        """
        Updates the policy weights based on collected rewards (Backprop).
        Uses a simplified Monte Carlo Policy Gradient approach.
        
        Returns:
            float: The magnitude of the weight update (for logging).
        """
        if not self.rewards:
            return 0.0

        # Calculate discounted returns (baseline)
        T = len(self.rewards)
        returns = np.zeros(T)
        G = 0
        for t in reversed(range(T)):
            G = self.rewards[t] + 0.9 * G # Discount factor gamma = 0.9
            returns[t] = G
            
        # Normalize returns to reduce variance
        returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-9)
        
        # Gradient approximation update (Hebbian-like with reward modulation)
        # This is a simplified numerical update for demonstration
        total_update = 0.0
        for i in range(T):
            state = self.states[i]
            action = self.actions[i]
            G = returns[i]
            
            # Pseudo-gradient: move weights towards action taken if G > 0
            # d_log_prob approx
            grad = np.outer(state, (action - (np.dot(state, self.weights) + self.bias)))
            self.weights += self.lr * grad * G
            self.bias += self.lr * (action - (np.dot(state, self.weights) + self.bias)) * G
            total_update += np.sum(np.abs(grad))
            
        # Clear memory
        self.states, self.actions, self.rewards = [], [], []
        return total_update

def train_digitizer_agent(episodes: int = 50) -> Dict[str, Any]:
    """
    Helper function to orchestrate the training loop.
    
    Args:
        episodes (int): Number of training episodes to run.
        
    Returns:
        Dict: Training history and final learned parameters.
    """
    logger.info("Starting Inverse Dynamics Digitizer Training...")
    
    # 1. Setup
    param_keys = list(PARAM_BOUNDS.keys())
    env = InverseDynamicsEnvironment()
    agent = RLAgent(param_dims=len(param_keys))
    
    history = []
    
    # 2. Training Loop
    for ep in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0
        
        while not done:
            action = agent.select_action(state)
            next_state, reward, done, info = env.step(action)
            
            agent.store_transition(state, action, reward)
            state = next_state
            total_reward += reward
            
        # 3. Optimization
        update_magnitude = agent.update_policy()
        history.append({"episode": ep, "reward": total_reward, "update": update_magnitude})
        
        if ep % 10 == 0:
            logger.info(
                f"Episode {ep}: Total Reward={total_reward:.2f}, "
                f"Update Magnitude={update_magnitude:.4f}"
            )
            
    # 4. Final Inference (Digitizing the Expert Strategy)
    # Run one final deterministic pass to get the 'stable' parameters
    state = env.reset()
    done = False
    final_params_trajectory = []
    
    while not done:
        # Use deterministic policy (no noise)
        mean_action = np.dot(state, agent.weights) + agent.bias
        state, _, done, info = env.step(mean_action)
        if info['is_stable']:
            final_params_trajectory.append(info['params'])
            
    logger.info("Training complete. Expert parameters digitized.")
    
    return {
        "history": history,
        "final_stable_params": final_params_trajectory[-1] if final_params_trajectory else None
    }

if __name__ == "__main__":
    # Example Usage
    print("--- Inverse Dynamics Digitizer Simulation ---")
    results = train_digitizer_agent(episodes=30)
    
    print("\nFinal Digitized Stable Parameters (Target Expert Strategy):")
    if results['final_stable_params']:
        for k, v in results['final_stable_params'].items():
            print(f"  - {k}: {v:.4f}")
    else:
        print("  Agent failed to converge to a stable state.")