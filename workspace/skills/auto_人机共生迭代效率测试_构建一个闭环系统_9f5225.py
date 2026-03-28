"""
Module: auto_human_machine_symbiosis_efficiency_test_9f5225
Description: Implements a closed-loop system for testing the efficiency of
             Human-Computer Symbiosis in iterative craftsmanship.
             
This module simulates and validates whether AI-generated parameter variants
combined with human feedback converge faster than traditional methods.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackRating(Enum):
    """Enumeration for human feedback ratings."""
    GOOD = 1.0
    BAD = -1.0
    NEUTRAL = 0.0

@dataclass
class CraftParameters:
    """
    Represents a set of craftsmanship parameters.
    
    Attributes:
        temperature (float): Operating temperature (e.g., for kiln).
        pressure (float): Applied pressure.
        duration (float): Processing duration in minutes.
        material_ratio (float): Ratio of primary material.
    """
    temperature: float = 1000.0
    pressure: float = 1.0
    duration: float = 60.0
    material_ratio: float = 0.5

    def validate(self) -> bool:
        """Validate parameter boundaries."""
        if not (0 <= self.material_ratio <= 1):
            logger.error("Material ratio must be between 0 and 1")
            return False
        if self.temperature < 0 or self.pressure < 0 or self.duration < 0:
            logger.error("Parameters cannot be negative")
            return False
        return True

    def to_vector(self) -> List[float]:
        """Convert parameters to a numerical vector."""
        return [self.temperature, self.pressure, self.duration, self.material_ratio]

@dataclass
class IterationRecord:
    """Tracks a single iteration in the symbiosis loop."""
    iteration_id: int
    params: CraftParameters
    feedback: Optional[FeedbackRating] = None
    timestamp: float = field(default_factory=time.time)

class SymbiosisClosedLoopSystem:
    """
    Main class for the Human-Computer Symbiosis Efficiency Test.
    
    This system creates a closed loop where:
    1. AI generates parameter variants based on current knowledge.
    2. Human (simulated) tests and provides feedback.
    3. System updates its internal model to converge towards optimal parameters.
    
    The goal is to verify if this 'collision' accelerates the transformation
    of tacit knowledge into explicit knowledge compared to traditional methods.
    """

    def __init__(self, 
                 target_params: CraftParameters, 
                 convergence_threshold: float = 0.05,
                 exploration_rate: float = 0.2):
        """
        Initialize the closed-loop system.
        
        Args:
            target_params: The 'True Node' or optimal parameters to be discovered.
            convergence_threshold: Distance threshold to consider convergence.
            exploration_rate: Rate of random exploration in parameter generation.
        """
        self.target_params = target_params
        self.convergence_threshold = convergence_threshold
        self.exploration_rate = exploration_rate
        self.history: List[IterationRecord] = []
        self.current_best_params = None
        self._step_count = 0
        
        # Internal model weights (simple heuristic for this simulation)
        self._weights = {
            'temperature': 1.0,
            'pressure': 0.5,
            'duration': 0.8,
            'material_ratio': 1.2
        }

    def _calculate_distance(self, params: CraftParameters) -> float:
        """
        Calculate normalized Euclidean distance to target parameters.
        Helper function to measure how close current params are to the 'truth'.
        """
        if not params.validate():
            raise ValueError("Invalid parameters provided for distance calculation")
            
        # Normalize differences to make dimensions comparable
        t_diff = abs(params.temperature - self.target_params.temperature) / 2000.0
        p_diff = abs(params.pressure - self.target_params.pressure) / 10.0
        d_diff = abs(params.duration - self.target_params.duration) / 120.0
        m_diff = abs(params.material_ratio - self.target_params.material_ratio)
        
        return (t_diff**2 + p_diff**2 + d_diff**2 + m_diff**2) ** 0.5

    def generate_variants(self, base_params: Optional[CraftParameters] = None) -> List[CraftParameters]:
        """
        AI Core Function: Generate parameter variants based on current knowledge.
        
        Args:
            base_params: The starting point. If None, starts from current best or random.
            
        Returns:
            List[CraftParameters]: A list of suggested parameter sets.
        
        Raises:
            RuntimeError: If generation fails due to internal state errors.
        """
        try:
            variants = []
            base = base_params or self.current_best_params or self._random_params()
            
            logger.info(f"Generating variants based on base: T={base.temperature}")
            
            for _ in range(3): # Generate 3 candidates
                # Apply Gaussian noise for mutation
                new_temp = base.temperature + random.gauss(0, 50 * self.exploration_rate)
                new_pres = base.pressure + random.gauss(0, 0.5 * self.exploration_rate)
                new_dur = base.duration + random.gauss(0, 10 * self.exploration_rate)
                new_ratio = base.material_ratio + random.gauss(0, 0.1 * self.exploration_rate)
                
                # Boundary checks
                new_ratio = max(0.0, min(1.0, new_ratio))
                new_temp = max(0.0, new_temp)
                
                variant = CraftParameters(new_temp, new_pres, new_dur, new_ratio)
                if variant.validate():
                    variants.append(variant)
                    
            return variants
        except Exception as e:
            logger.error(f"Error generating variants: {e}")
            raise RuntimeError("Variant generation failed") from e

    def _random_params(self) -> CraftParameters:
        """Helper function to generate random valid parameters."""
        return CraftParameters(
            temperature=random.uniform(800, 1200),
            pressure=random.uniform(0.5, 5.0),
            duration=random.uniform(30, 90),
            material_ratio=random.uniform(0.3, 0.7)
        )

    def process_human_feedback(self, params: CraftParameters, feedback: FeedbackRating) -> bool:
        """
        Process human feedback and update internal model.
        
        Args:
            params: The parameters that were tested.
            feedback: The human's rating (GOOD/BAD).
            
        Returns:
            bool: True if the system converged to the target, False otherwise.
        """
        self._step_count += 1
        record = IterationRecord(self._step_count, params, feedback)
        self.history.append(record)
        
        distance = self._calculate_distance(params)
        
        logger.info(f"Step {self._step_count}: Feedback {feedback.name} | Distance to truth: {distance:.4f}")
        
        if feedback == FeedbackRating.GOOD:
            # Reinforce: Update current best
            if self.current_best_params is None or \
               self._calculate_distance(params) < self._calculate_distance(self.current_best_params):
                self.current_best_params = params
                logger.debug("Updated current best parameters.")
                
        # Check convergence
        if distance < self.convergence_threshold:
            logger.info(f"CONVERGENCE ACHIEVED at step {self._step_count}!")
            return True
            
        return False

    def run_simulation(self, max_steps: int = 50) -> Dict:
        """
        Runs the full Human-Machine closed-loop simulation.
        
        This simulates the 'Human' part internally for testing purposes 
        (automated unit test of the skill).
        
        Args:
            max_steps: Maximum iterations before stopping.
            
        Returns:
            Dict containing simulation statistics.
        """
        logger.info("Starting Symbiosis Simulation...")
        start_time = time.time()
        converged = False
        
        # Initial random state
        current_base = self._random_params()
        
        for step in range(max_steps):
            # 1. AI Generates
            candidates = self.generate_variants(current_base)
            if not candidates:
                continue
                
            # 2. Human (Simulated) Tests & Feedback
            # Heuristic: Choose the candidate closest to target (simulating human intuition/trial)
            # In a real scenario, this loop would wait for actual human input.
            best_candidate = min(candidates, key=lambda p: self._calculate_distance(p))
            
            # Simulate Feedback: GOOD if closer than current best, else BAD (simplified)
            dist = self._calculate_distance(best_candidate)
            if self.current_best_params is None or \
               dist < self._calculate_distance(self.current_best_params):
                rating = FeedbackRating.GOOD
                current_base = best_candidate # Human guides the next iteration
            else:
                rating = FeedbackRating.BAD
                # Keep current_base or explore randomly
                
            # 3. Update System
            if self.process_human_feedback(best_candidate, rating):
                converged = True
                break
        
        duration = time.time() - start_time
        result = {
            "converged": converged,
            "steps": self._step_count,
            "duration_sec": round(duration, 2),
            "final_distance": self._calculate_distance(current_base) if current_base else -1,
            "final_params": self.current_best_params
        }
        logger.info(f"Simulation Complete: {result}")
        return result

# Usage Example
if __name__ == "__main__":
    # Define the "Tacit Knowledge" / True Node we want to discover
    TARGET = CraftParameters(temperature=1050.0, pressure=2.5, duration=45.0, material_ratio=0.62)
    
    # Initialize System
    system = SymbiosisClosedLoopSystem(TARGET, convergence_threshold=0.05)
    
    # Run automated test to verify convergence efficiency
    stats = system.run_simulation(max_steps=100)
    
    # Output comparison logic would go here in a full benchmark suite
    print(f"Simulation Result: Converged={stats['converged']} in {stats['steps']} steps")