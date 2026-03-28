"""
Module: generative_evolutionary_architecture.py
Description: Implements a gradient-based generative system for architectural layout optimization.
             This module enables the automatic generation of building footprints based on
             agent flow simulation and environmental loss functions, removing the need for
             manual design iterations.

Author: AGI System
Version: 3.1.0
License: MIT
"""

import logging
import numpy as np
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ArchitecturalGrid:
    """
    Represents a continuous density grid for building layout.
    Values represent the 'solidity' or wall probability of each cell.
    """
    width: int
    height: int
    density_map: np.ndarray  # Shape: (width, height), Values: 0.0 (void) to 1.0 (wall)

    def validate(self) -> bool:
        """Validates the grid dimensions and data consistency."""
        if self.density_map.shape != (self.width, self.height):
            raise ValueError(f"Dimension mismatch: Expected {(self.width, self.height)}, got {self.density_map.shape}")
        if np.any(self.density_map < 0) or np.any(self.density_map > 1):
            raise ValueError("Density map values must be between 0.0 and 1.0")
        return True

def _compute_accessibility_gradient(map_tensor: np.ndarray, targets: List[Tuple[int, int]]) -> np.ndarray:
    """
    [Helper Function] Computes a gradient field indicating accessibility from target points.
    
    Uses a simplified distance transform approximation to determine how 'reachable' 
    each cell is from the target points (e.g., exits, windows).
    
    Args:
        map_tensor (np.ndarray): The current architectural density map.
        targets (List[Tuple[int, int]]): Coordinates of key interest points (destinations).
        
    Returns:
        np.ndarray: A gradient field where lower values indicate better accessibility.
    """
    logger.debug("Computing accessibility gradients...")
    grad_field = np.ones_like(map_tensor) * 1e6  # Initialize with high cost
    w, h = map_tensor.shape
    
    # Simple iterative propagation for distance field (Dijkstra-like logic simplified)
    # In a real scenario, this would be a differentiable A* or FMM layer.
    # Here we simulate the 'pressure' gradient pushing walls away from paths.
    
    for x, y in targets:
        # Validate targets
        if not (0 <= x < w and 0 <= y < h):
            continue
        
        # Create a distance decay from the target
        # This is a crude approximation of "flow potential"
        xx, yy = np.meshgrid(range(w), range(h), indexing='ij')
        dist = np.sqrt((xx - x)**2 + (yy - y)**2)
        
        # Walls increase the effective distance
        effective_dist = dist * (1 + map_tensor * 10) 
        
        grad_field = np.minimum(grad_field, effective_dist)
        
    return grad_field

def simulate_agent_flow(
    layout: ArchitecturalGrid, 
    num_agents: int = 100, 
    timestep_steps: int = 50
) -> Tuple[np.ndarray, float]:
    """
    [Core Function 1] Simulates agent movement in the current layout to calculate flow efficiency.
    
    This function acts as the "Forward Pass" of the system. It spawns agents and 
    moves them towards targets while being obstructed by walls (high density values).
    
    Args:
        layout (ArchitecturalGrid): The current building layout state.
        num_agents (int): Number of virtual agents to simulate.
        timestep_steps (int): Duration of the simulation.
        
    Returns:
        Tuple[np.ndarray, float]: 
            - flow_map (np.ndarray): A heatmap of agent trajectories (accumulated gradients).
            - avg_efficiency (float): A metric of how easily agents reached targets.
    """
    logger.info(f"Simulating flow for {num_agents} agents...")
    
    try:
        layout.validate()
    except ValueError as e:
        logger.error(f"Invalid layout data: {e}")
        raise

    w, h = layout.width, layout.height
    density = layout.density_map
    
    # Initialize agents at random valid (low density) positions
    # Flatten indices, sort by density (ascending), pick top random
    flat_density = density.flatten()
    valid_spots = np.where(flat_density < 0.5)[0]
    
    if len(valid_spots) < num_agents:
        logger.warning("Not enough open space for agents. Reducing agent count.")
        num_agents = len(valid_spots)
        
    start_indices = np.random.choice(valid_spots, num_agents, replace=False)
    agent_x = start_indices // h
    agent_y = start_indices % h
    
    # Targets (e.g., Exits)
    targets = [(w-1, h//2), (0, h//2)] # Left and Right exits
    
    flow_accumulator = np.zeros((w, h))
    
    for t in range(timestep_steps):
        # Determine movement direction (towards nearest target)
        # This is a simplified vector field calculation
        move_dx = np.zeros(num_agents)
        move_dy = np.zeros(num_agents)
        
        for i in range(num_agents):
            cx, cy = int(agent_x[i]), int(agent_y[i])
            
            # Simple logic: check 4 neighbors, move to one with lowest density + distance cost
            # (Simulating gradient descent on the environment)
            neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
            
            best_score = 1000
            best_move = (0, 0)
            
            for nx, ny in neighbors:
                if 0 <= nx < w and 0 <= ny < h:
                    # Cost = Wall Density + Distance to target
                    # Note: In a true differentiable system, this argmin is relaxed.
                    cost = density[nx, ny] * 10 + np.random.rand() * 0.1 # Added noise for exploration
                    if cost < best_score:
                        best_score = cost
                        best_move = (nx - cx, ny - cy)
            
            # Apply move
            agent_x[i] += best_move[0]
            agent_y[i] += best_move[1]
            
            # Accumulate flow (gradients)
            flow_accumulator[int(agent_x[i]), int(agent_y[i])] += 1
            
    # Calculate efficiency: ratio of agents reaching targets
    final_positions = np.stack([agent_x, agent_y], axis=1)
    reached = 0
    for t_x, t_y in targets:
         # Check proximity
         dists = np.sqrt((final_positions[:, 0] - t_x)**2 + (final_positions[:, 1] - t_y)**2)
         reached += np.sum(dists < 2.0)
         
    efficiency = reached / num_agents
    logger.info(f"Simulation complete. Efficiency score: {efficiency:.4f}")
    
    return flow_accumulator, efficiency

def optimize_layout(
    initial_grid: ArchitecturalGrid,
    iterations: int = 50,
    learning_rate: float = 0.1
) -> ArchitecturalGrid:
    """
    [Core Function 2] Optimizes the architectural layout using gradient descent.
    
    This is the "Training Loop". It iteratively adjusts wall weights based on 
    the flow simulation results to minimize obstruction and maximize space utility.
    
    Args:
        initial_grid (ArchitecturalGrid): The starting layout (e.g., random noise or sketch).
        iterations (int): Number of optimization steps.
        learning_rate (float): Step size for updating density weights.
        
    Returns:
        ArchitecturalGrid: The optimized architectural layout.
    """
    logger.info("Starting Generative Evolutionary Optimization...")
    
    # Make the grid differentiable (using float)
    current_density = initial_grid.density_map.astype(np.float32)
    
    # Define fixed constraints (e.g., boundary walls must exist)
    mask = np.ones_like(current_density)
    # Allow interior to change, lock borders
    mask[1:-1, 1:-1] = 0.0 # 0 means trainable in this mask logic context (or simply apply weight update only inside)
    
    targets = [(initial_grid.width-1, initial_grid.height//2), (0, initial_grid.height//2)]

    for i in range(iterations):
        # 1. Forward Pass (Simulation)
        # In a true NN, this would be a differentiable layer. 
        # Here we use the accessibility gradient as a proxy for the "Wall Cost".
        accessibility_cost = _compute_accessibility_gradient(current_density, targets)
        
        # 2. Calculate Loss Gradients
        # We want to reduce density where it blocks flow (high accessibility cost * density)
        # And increase density where it defines space (structural logic - simplified here)
        
        # Gradient of Loss w.r.t Density:
        # If density blocks a path, gradient is positive (reduce density).
        # We use the accessibility map as a "pressure" field.
        
        # Gradient approximation: 
        # If a wall is in a high-traffic area (determined by accessibility cost), remove it.
        # flow_map, _ = simulate_agent_flow(ArchitecturalGrid(initial_grid.width, initial_grid.height, current_density))
        
        # Simplified differentiable logic:
        # Loss = Sum(density * accessibility_cost)
        # d(Loss)/d(density) = accessibility_cost
        # We want to MINIMIZE loss, so we subtract gradient.
        
        grad = accessibility_cost * current_density
        
        # 3. Update Weights (Backpropagation / Gradient Descent)
        # Only update interior cells
        current_density[1:-1, 1:-1] -= learning_rate * grad[1:-1, 1:-1]
        
        # 4. Clamping (ReLU/Sigmoid constraints)
        # Ensure values stay between 0 (void) and 1 (wall)
        current_density = np.clip(current_density, 0.0, 1.0)
        
        # Log intermediate state
        if i % 10 == 0:
            wall_ratio = np.mean(current_density)
            logger.debug(f"Iter {i}: Wall Density Ratio: {wall_ratio:.2f}")

    logger.info("Optimization complete. Generating final grid.")
    
    return ArchitecturalGrid(
        width=initial_grid.width,
        height=initial_grid.height,
        density_map=current_density
    )

# Example Usage
if __name__ == "__main__":
    try:
        # 1. Initialize a random grid
        WIDTH, HEIGHT = 20, 20
        # Random noise initialization
        initial_map = np.random.rand(WIDTH, HEIGHT) * 0.2
        # Add boundary walls
        initial_map[0, :] = 1.0
        initial_map[-1, :] = 1.0
        initial_map[:, 0] = 1.0
        initial_map[:, -1] = 1.0
        
        initial_grid = ArchitecturalGrid(WIDTH, HEIGHT, initial_map)
        
        # 2. Run Optimization
        # This will "carve" paths through the random noise based on accessibility logic
        optimized_grid = optimize_layout(initial_grid, iterations=100, learning_rate=0.05)
        
        # 3. Validate and Display
        print("\nOptimized Layout Slice (Center Row):")
        print(optimized_grid.density_map[HEIGHT//2].round(1))
        
        # 4. Run final simulation to check efficiency
        _, score = simulate_agent_flow(optimized_grid, num_agents=50)
        print(f"\nFinal Flow Efficiency Score: {score}")

    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)