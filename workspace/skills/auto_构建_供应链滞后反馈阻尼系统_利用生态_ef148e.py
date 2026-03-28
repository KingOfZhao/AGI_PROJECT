"""
Module: auto_build_supply_chain_damping_ef148e
Description: Constructs a 'Supply Chain Lag Feedback Damping System'.
             Utilizes phase plane analysis from ecological predator-prey models
             to predict the Bullwhip Effect in supply chains.
             Incorporates ecological 'density dependence' factors to automatically
             smooth order fluctuations and maintain system homeostasis.
"""

import logging
import numpy as np
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SystemState:
    """
    Represents the current state of the supply chain ecosystem.
    
    Attributes:
        prey (float): Represents terminal demand (analogous to prey population).
        predator (float): Represents inventory/production capacity (analogous to predator population).
        time_step (int): Current simulation step.
    """
    prey: float
    predator: float
    time_step: int = 0

class SupplyChainEcosystem:
    """
    Simulates a supply chain using ecological dynamics (Lotka-Volterra variants)
    to dampen the Bullwhip Effect.
    
    The system treats Demand as Prey and Inventory/Capacity as Predator.
    It introduces density-dependent damping (carrying capacity) to prevent
    uncontrolled oscillations caused by demand shocks.
    """

    def __init__(self, alpha: float, beta: float, gamma: float, delta: float, carrying_capacity: float):
        """
        Initialize the ecosystem parameters.
        
        Args:
            alpha (float): Intrinsic growth rate of demand (prey max growth).
            beta (float): Capture rate (demand depletion rate per inventory unit).
            gamma (float): Production efficiency (conversion of demand to inventory).
            delta (float): Inventory depreciation/demand fulfillment rate.
            carrying_capacity (float): Maximum sustainable demand limit (density dependence).
        """
        if not all(isinstance(v, (int, float)) and v >= 0 for v in [alpha, beta, gamma, delta, carrying_capacity]):
            raise ValueError("All parameters must be non-negative numbers.")
        
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.K = carrying_capacity # Density dependence factor
        self.history: List[SystemState] = []
        logger.info("SupplyChainEcosystem initialized with damping factor K=%.2f", self.K)

    def _validate_input_data(self, current_demand: float, current_inventory: float) -> None:
        """
        Helper function to validate input data boundaries.
        
        Args:
            current_demand (float): Current observed market demand.
            current_inventory (float): Current available stock/capacity.
        
        Raises:
            ValueError: If inputs are negative or invalid.
        """
        if current_demand < 0 or current_inventory < 0:
            logger.error("Invalid negative values detected: Demand=%s, Inventory=%s", current_demand, current_inventory)
            raise ValueError("Demand and Inventory must be non-negative.")
        logger.debug("Input validation passed.")

    def calculate_phase_derivative(self, state: SystemState) -> Tuple[float, float]:
        """
        Core Function 1: Calculates the rate of change (derivatives) for the ecosystem.
        
        Implements a modified Lotka-Volterra equation with logistic growth (density dependence):
        dPrey/dt = alpha * Prey * (1 - Prey/K) - beta * Prey * Predator
        dPredator/dt = delta * Prey * Predator - gamma * Predator
        
        Args:
            state (SystemState): Current state of the system.
            
        Returns:
            Tuple[float, float]: (d_demand, d_inventory) representing the velocity in phase space.
        """
        prey, pred = state.prey, state.predator
        
        # Density-dependent growth (logistic term) acts as the damper
        growth_term = self.alpha * prey * (1 - prey / self.K)
        interaction_term = self.beta * prey * pred
        
        # Demand change (Prey dynamics)
        d_prey = growth_term - interaction_term
        
        # Inventory/Order change (Predator dynamics)
        d_pred = (self.delta * prey * pred) - (self.gamma * pred)
        
        logger.debug(f"Derivatives calculated: dDemand={d_prey:.4f}, dInventory={d_pred:.4f}")
        return d_prey, d_pred

    def smooth_order_signal(self, observed_demand: float, current_inventory: float, dt: float = 0.1) -> float:
        """
        Core Function 2: Generates a damped order signal based on ecosystem dynamics.
        
        Instead of reacting linearly to demand (which causes Bullwhip), this function
        uses the phase derivative to propose a stable production order rate.
        
        Args:
            observed_demand (float): The latest market demand signal.
            current_inventory (float): Current stock level.
            dt (float): Time step for integration (default 0.1).
            
        Returns:
            float: The smoothed production/order quantity recommendation.
        
        Raises:
            ValueError: If input validation fails.
        """
        try:
            self._validate_input_data(observed_demand, current_inventory)
        except ValueError as e:
            logger.warning(f"Input validation failed: {e}. Returning 0 order.")
            return 0.0

        current_state = SystemState(prey=observed_demand, predator=current_inventory)
        
        # Calculate the 'velocity' of the system
        d_demand, d_inventory = self.calculate_phase_derivative(current_state)
        
        # Heuristic smoothing logic:
        # If demand is growing faster than inventory can adapt, we apply a 'damping'
        # based on the carrying capacity K to prevent overshooting.
        
        # Base order required to match demand change
        base_order = observed_demand + d_demand * dt
        
        # Damping factor: Reduce the reaction if we are approaching carrying capacity
        # This mimics the biological resistance to population explosion.
        damping_ratio = 1.0
        if self.K > 0 and observed_demand > 0:
            # As demand approaches K, the damping ratio decreases
            damping_ratio = max(0.1, 1.0 - (observed_demand / self.K))
        
        # Calculate the final smoothed order quantity
        # We subtract the natural inventory change to avoid double counting
        smoothed_order = base_order * damping_ratio - (d_inventory * dt * 0.5)
        
        # Ensure orders are not negative
        final_order = max(0.0, smoothed_order)
        
        logger.info(
            f"Step {len(self.history)}: Observed={observed_demand:.2f}, "
            f"DampedOrder={final_order:.2f}, DampingRatio={damping_ratio:.2f}"
        )
        
        # Record state for history
        self.history.append(SystemState(prey=observed_demand, predator=current_inventory))
        
        return final_order

    def get_phase_trajectory(self) -> np.ndarray:
        """
        Helper Function: Returns the history of states as a numpy array for analysis.
        
        Returns:
            np.ndarray: A 2D array where columns are [Time, Demand, Inventory].
        """
        if not self.history:
            return np.array([])
        
        data = np.array([[h.time_step, h.prey, h.predator] for h in self.history])
        return data

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Initialize the system with specific ecological parameters
    # alpha=1.0 (demand growth potential)
    # beta=0.1 (demand-inventory friction)
    # gamma=0.5 (inventory depletion)
    # delta=0.05 (production efficiency)
    # K=1000 (Market saturation point / Carrying Capacity)
    
    try:
        system = SupplyChainEcosystem(
            alpha=1.0, 
            beta=0.1, 
            gamma=0.5, 
            delta=0.05, 
            carrying_capacity=1000.0
        )
        
        print(f"{'Step':<5} | {'Demand':<10} | {'Inventory':<10} | {'OrderQty':<10}")
        print("-" * 45)
        
        # Simulate a sudden demand shock (Bullwhip trigger)
        # Inventory starts at 50
        inventory_level = 50.0
        
        for t in range(10):
            # Simulate demand: sudden spike at t=2
            if t < 2:
                demand = 50.0
            elif 2 <= t < 5:
                demand = 200.0  # Spike
            else:
                demand = 80.0   # Stabilization
            
            # Get smoothed order recommendation
            order_qty = system.smooth_order_signal(demand, inventory_level)
            
            # Update inventory for simulation purposes (simple logic)
            inventory_level += order_qty - (demand * 0.8) # consume approx 80% of demand
            
            print(f"{t:<5} | {demand:<10.2f} | {inventory_level:<10.2f} | {order_qty:<10.2f}")
            
    except Exception as e:
        logger.error(f"Simulation failed: {e}")