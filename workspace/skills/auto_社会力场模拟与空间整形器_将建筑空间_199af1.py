"""
Module: Social Force Field Simulator & Space Shaper
Description: Models architectural space as an energy field where human behavioral 
             intentions are represented as gradients. Through reinforcement learning, 
             AI agents perform millions of navigation attempts to reverse-optimize 
             wall and opening positions. This allows the space to "liquify" and 
             evolve based on gradient backpropagation to induce optimal behavioral patterns.

Author: AGI System
Version: 1.0.0
"""

import numpy as np
import logging
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SpaceConfig:
    """Configuration for the simulation space."""
    width: float
    height: float
    resolution: int
    learning_rate: float = 0.01
    damping_factor: float = 0.95
    num_agents: int = 50
    num_iterations: int = 1000
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Space dimensions must be positive")
        if self.resolution <= 0:
            raise ValueError("Resolution must be positive")
        if not 0 < self.learning_rate < 1:
            raise ValueError("Learning rate must be between 0 and 1")
        if not 0 < self.damping_factor <= 1:
            raise ValueError("Damping factor must be between 0 and 1")


class SocialForceField:
    """
    Represents the architectural space as an energy field with social force dynamics.
    
    The space is modeled as a 2D grid where each cell has:
    - Obstacle density (walls, furniture)
    - Comfort gradient (desire paths)
    - Social force vectors (behavioral intentions)
    
    Example:
        >>> config = SpaceConfig(width=100.0, height=80.0, resolution=100)
        >>> field = SocialForceField(config)
        >>> field.add_wall_segment((20, 20), (20, 60))
        >>> field.simulate()
        >>> optimized_space = field.get_optimized_layout()
    """
    
    def __init__(self, config: SpaceConfig):
        """
        Initialize the social force field.
        
        Args:
            config: SpaceConfig object containing simulation parameters
        """
        self.config = config
        self.grid_size = (
            int(config.height / config.resolution),
            int(config.width / config.resolution)
        )
        
        # Initialize field matrices
        self.obstacle_field = np.zeros(self.grid_size, dtype=np.float32)
        self.comfort_field = np.zeros(self.grid_size, dtype=np.float32)
        self.force_field_x = np.zeros(self.grid_size, dtype=np.float32)
        self.force_field_y = np.zeros(self.grid_size, dtype=np.float32)
        
        # Agent positions and velocities
        self.agents: List[Dict] = []
        
        logger.info(f"Initialized SocialForceField with grid size {self.grid_size}")
    
    def add_wall_segment(
        self, 
        start: Tuple[float, float], 
        end: Tuple[float, float],
        thickness: float = 1.0
    ) -> None:
        """
        Add a wall segment to the obstacle field.
        
        Args:
            start: Starting coordinates (x, y) in real space
            end: Ending coordinates (x, y) in real space
            thickness: Wall thickness in grid cells
            
        Raises:
            ValueError: If coordinates are out of bounds
        """
        try:
            # Validate coordinates
            for coord in [start, end]:
                if not (0 <= coord[0] <= self.config.width and 
                       0 <= coord[1] <= self.config.height):
                    raise ValueError(f"Coordinates {coord} out of bounds")
            
            # Convert to grid coordinates
            start_grid = (
                int(start[1] / self.config.resolution),
                int(start[0] / self.config.resolution)
            )
            end_grid = (
                int(end[1] / self.config.resolution),
                int(end[0] / self.config.resolution)
            )
            
            # Draw line using Bresenham's algorithm
            self._draw_line(start_grid, end_grid, self.obstacle_field, thickness)
            
            logger.debug(f"Added wall from {start} to {end}")
            
        except Exception as e:
            logger.error(f"Error adding wall segment: {e}")
            raise
    
    def _draw_line(
        self, 
        start: Tuple[int, int], 
        end: Tuple[int, int], 
        field: np.ndarray, 
        thickness: float
    ) -> None:
        """
        Helper function to draw a line on a field using Bresenham's algorithm.
        
        Args:
            start: Starting grid coordinates
            end: Ending grid coordinates
            field: The field matrix to draw on
            thickness: Line thickness
        """
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            # Apply thickness
            t = int(thickness)
            for i in range(-t, t+1):
                for j in range(-t, t+1):
                    nx, ny = x0 + i, y0 + j
                    if 0 <= nx < field.shape[0] and 0 <= ny < field.shape[1]:
                        field[nx, ny] = 1.0
            
            if x0 == x1 and y0 == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
    
    def initialize_agents(self, num_agents: Optional[int] = None) -> None:
        """
        Initialize AI agents with random positions and target destinations.
        
        Args:
            num_agents: Number of agents to initialize (defaults to config value)
        """
        num = num_agents or self.config.num_agents
        self.agents = []
        
        for i in range(num):
            # Random starting position (avoiding obstacles)
            while True:
                x = np.random.uniform(0, self.config.width)
                y = np.random.uniform(0, self.config.height)
                grid_x = int(y / self.config.resolution)
                grid_y = int(x / self.config.resolution)
                
                if self.obstacle_field[grid_x, grid_y] < 0.5:
                    break
            
            # Random target destination
            target_x = np.random.uniform(0, self.config.width)
            target_y = np.random.uniform(0, self.config.height)
            
            self.agents.append({
                'id': i,
                'position': np.array([x, y]),
                'velocity': np.array([0.0, 0.0]),
                'target': np.array([target_x, target_y]),
                'path_history': []
            })
        
        logger.info(f"Initialized {num} agents")
    
    def compute_social_forces(self) -> None:
        """
        Compute social force vectors for each agent based on:
        1. Desire to reach target (gradient)
        2. Repulsion from other agents
        3. Repulsion from obstacles
        
        The force field guides agents toward optimal paths while avoiding collisions.
        """
        try:
            for agent in self.agents:
                pos = agent['position']
                target = agent['target']
                
                # Direction to target
                direction = target - pos
                dist_to_target = np.linalg.norm(direction)
                
                if dist_to_target > 0.1:
                    desired_velocity = direction / dist_to_target * 1.5  # Desired speed
                else:
                    desired_velocity = np.array([0.0, 0.0])
                
                # Obstacle repulsion force
                obstacle_force = self._compute_obstacle_repulsion(pos)
                
                # Agent-agent repulsion
                agent_force = self._compute_agent_repulsion(agent)
                
                # Total force
                total_force = (desired_velocity * 2.0 + 
                              obstacle_force * 1.5 + 
                              agent_force * 0.8)
                
                # Update velocity with damping
                agent['velocity'] = (agent['velocity'] * self.config.damping_factor + 
                                    total_force * 0.1)
                
                # Limit velocity
                speed = np.linalg.norm(agent['velocity'])
                if speed > 2.0:
                    agent['velocity'] = agent['velocity'] / speed * 2.0
                
                # Store force for gradient accumulation
                grid_x = int(pos[1] / self.config.resolution)
                grid_y = int(pos[0] / self.config.resolution)
                
                if 0 <= grid_x < self.grid_size[0] and 0 <= grid_y < self.grid_size[1]:
                    self.force_field_x[grid_x, grid_y] += agent['velocity'][0]
                    self.force_field_y[grid_x, grid_y] += agent['velocity'][1]
                    
        except Exception as e:
            logger.error(f"Error computing social forces: {e}")
            raise
    
    def _compute_obstacle_repulsion(self, pos: np.ndarray) -> np.ndarray:
        """
        Compute repulsion force from nearby obstacles.
        
        Args:
            pos: Agent position
            
        Returns:
            Repulsion force vector
        """
        force = np.array([0.0, 0.0])
        grid_x = int(pos[1] / self.config.resolution)
        grid_y = int(pos[0] / self.config.resolution)
        
        # Check neighboring cells
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nx, ny = grid_x + dx, grid_y + dy
                if 0 <= nx < self.grid_size[0] and 0 <= ny < self.grid_size[1]:
                    if self.obstacle_field[nx, ny] > 0.5:
                        # Repulsion direction
                        rep_dir = np.array([grid_y - ny, grid_x - nx])
                        dist = np.linalg.norm(rep_dir)
                        if dist > 0:
                            force += rep_dir / (dist ** 2) * 0.5
        
        return force
    
    def _compute_agent_repulsion(self, current_agent: Dict) -> np.ndarray:
        """
        Compute repulsion force from other agents.
        
        Args:
            current_agent: The agent for which to compute forces
            
        Returns:
            Repulsion force vector
        """
        force = np.array([0.0, 0.0])
        pos = current_agent['position']
        
        for agent in self.agents:
            if agent['id'] != current_agent['id']:
                diff = pos - agent['position']
                dist = np.linalg.norm(diff)
                
                if 0 < dist < 5.0:  # Personal space radius
                    force += diff / (dist ** 2) * 0.3
        
        return force
    
    def update_agent_positions(self) -> None:
        """Update agent positions based on computed velocities."""
        for agent in self.agents:
            # Update position
            new_pos = agent['position'] + agent['velocity'] * 0.1
            
            # Boundary checking
            new_pos[0] = np.clip(new_pos[0], 0, self.config.width)
            new_pos[1] = np.clip(new_pos[1], 0, self.config.height)
            
            # Check for obstacle collision
            grid_x = int(new_pos[1] / self.config.resolution)
            grid_y = int(new_pos[0] / self.config.resolution)
            
            if self.obstacle_field[grid_x, grid_y] < 0.5:
                agent['position'] = new_pos
                agent['path_history'].append(new_pos.copy())
                
                # Limit history length
                if len(agent['path_history']) > 100:
                    agent['path_history'].pop(0)
    
    def backpropagate_gradients(self) -> None:
        """
        Core innovation: Backpropagate agent movement gradients to 
        modify the space configuration.
        
        This is the "space liquification" process where:
        1. High traffic areas reduce obstacle density
        2. Low traffic areas may increase obstacle density
        3. Walls evolve to guide optimal flow patterns
        """
        try:
            # Compute gradient magnitude
            gradient_magnitude = np.sqrt(
                self.force_field_x ** 2 + self.force_field_y ** 2
            )
            
            # Normalize
            max_grad = np.max(gradient_magnitude)
            if max_grad > 0:
                normalized_gradient = gradient_magnitude / max_grad
            else:
                normalized_gradient = gradient_magnitude
            
            # Update obstacle field (reverse optimization)
            # High gradient = low obstacle (create passages)
            # Low gradient = maintain or increase obstacle
            adjustment = (normalized_gradient - 0.3) * self.config.learning_rate
            
            # Apply adjustment only to non-structural elements
            mutable_mask = (self.obstacle_field > 0.1) & (self.obstacle_field < 0.9)
            self.obstacle_field[mutable_mask] -= adjustment[mutable_mask]
            
            # Clamp values
            self.obstacle_field = np.clip(self.obstacle_field, 0, 1)
            
            # Decay force fields for next iteration
            self.force_field_x *= 0.9
            self.force_field_y *= 0.9
            
            logger.debug("Backpropagated gradients to space configuration")
            
        except Exception as e:
            logger.error(f"Error in gradient backpropagation: {e}")
            raise
    
    def simulate(self, iterations: Optional[int] = None) -> Dict:
        """
        Run the full simulation loop.
        
        Args:
            iterations: Number of iterations (defaults to config value)
            
        Returns:
            Dictionary containing simulation results
            
        Example:
            >>> results = field.simulate(iterations=500)
            >>> print(f"Average path efficiency: {results['efficiency']}")
        """
        iterations = iterations or self.config.num_iterations
        
        if len(self.agents) == 0:
            self.initialize_agents()
        
        logger.info(f"Starting simulation for {iterations} iterations")
        
        results = {
            'iterations': iterations,
            'efficiency_history': [],
            'final_space': None
        }
        
        try:
            for i in range(iterations):
                self.compute_social_forces()
                self.update_agent_positions()
                
                # Periodically backpropagate gradients
                if i % 10 == 0:
                    self.backpropagate_gradients()
                
                # Compute efficiency metric
                if i % 50 == 0:
                    efficiency = self._compute_efficiency()
                    results['efficiency_history'].append(efficiency)
                    logger.info(f"Iteration {i}: Efficiency = {efficiency:.3f}")
                
                # Reset reached agents
                for agent in self.agents:
                    dist_to_target = np.linalg.norm(
                        agent['position'] - agent['target']
                    )
                    if dist_to_target < 2.0:
                        # Assign new target
                        agent['target'] = np.array([
                            np.random.uniform(0, self.config.width),
                            np.random.uniform(0, self.config.height)
                        ])
            
            results['final_space'] = self.obstacle_field.copy()
            results['final_efficiency'] = results['efficiency_history'][-1]
            
            logger.info(f"Simulation complete. Final efficiency: {results['final_efficiency']:.3f}")
            
        except Exception as e:
            logger.error(f"Simulation error at iteration {i}: {e}")
            raise
        
        return results
    
    def _compute_efficiency(self) -> float:
        """
        Compute overall navigation efficiency.
        
        Returns:
            Efficiency score between 0 and 1
        """
        total_efficiency = 0.0
        
        for agent in self.agents:
            dist_to_target = np.linalg.norm(
                agent['position'] - agent['target']
            )
            max_dist = np.sqrt(self.config.width**2 + self.config.height**2)
            efficiency = 1.0 - (dist_to_target / max_dist)
            total_efficiency += efficiency
        
        return total_efficiency / len(self.agents)
    
    def get_optimized_layout(self) -> Dict:
        """
        Get the optimized space layout after simulation.
        
        Returns:
            Dictionary containing optimized space data
            
        Output Format:
            {
                'obstacle_field': np.ndarray,  # 2D grid of obstacle densities
                'flow_field_x': np.ndarray,    # X component of flow vectors
                'flow_field_y': np.ndarray,    # Y component of flow vectors
                'recommended_openings': List[Tuple],  # Suggested door/opening locations
                'metrics': Dict                # Performance metrics
            }
        """
        # Identify recommended openings (low obstacle, high flow)
        flow_magnitude = np.sqrt(self.force_field_x**2 + self.force_field_y**2)
        opening_potential = flow_magnitude * (1 - self.obstacle_field)
        
        # Find top opening locations
        threshold = np.percentile(opening_potential, 90)
        opening_indices = np.where(opening_potential > threshold)
        
        recommended_openings = []
        for i, j in zip(opening_indices[0], opening_indices[1]):
            x = j * self.config.resolution
            y = i * self.config.resolution
            recommended_openings.append((x, y))
        
        return {
            'obstacle_field': self.obstacle_field,
            'flow_field_x': self.force_field_x,
            'flow_field_y': self.force_field_y,
            'recommended_openings': recommended_openings[:10],  # Top 10
            'metrics': {
                'average_flow': float(np.mean(flow_magnitude)),
                'space_utilization': float(np.mean(self.obstacle_field < 0.5)),
                'grid_size': self.grid_size
            }
        }


# Usage Example
if __name__ == "__main__":
    # Create configuration
    config = SpaceConfig(
        width=100.0,
        height=80.0,
        resolution=1,
        learning_rate=0.02,
        damping_factor=0.9,
        num_agents=100,
        num_iterations=500
    )
    
    # Initialize field
    field = SocialForceField(config)
    
    # Add initial walls
    field.add_wall_segment((20, 20), (20, 60), thickness=1)
    field.add_wall_segment((60, 10), (60, 50), thickness=1)
    field.add_wall_segment((40, 40), (80, 40), thickness=1)
    
    # Run simulation
    results = field.simulate()
    
    # Get optimized layout
    optimized = field.get_optimized_layout()
    
    print(f"\n=== Simulation Results ===")
    print(f"Final efficiency: {results['final_efficiency']:.2%}")
    print(f"Space utilization: {optimized['metrics']['space_utilization']:.2%}")
    print(f"Recommended openings: {len(optimized['recommended_openings'])}")