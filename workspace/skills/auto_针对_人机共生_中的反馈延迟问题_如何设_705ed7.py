"""
Module: micro_feedback_loop.py

This module implements a 'Micro-Feedback' loop mechanism for Human-Computer Symbiosis (HCS).
It addresses the feedback latency problem in long-chain reasoning by establishing
'Confirmation Points' every K steps.

The core logic relies on a Cybernetic approach: monitoring the rate of change of
'Predictive Error'. If the system detects that it is deviating from the target state
(positive feedback loop detection), it triggers an automatic correction or pause signal
before the final execution step is reached.

Author: Senior Python Engineer (AGI System)
Domain: Cybernetics / Control Theory
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MicroFeedbackSystem")


class FeedbackLoopError(Exception):
    """Custom exception for errors in the feedback loop logic."""
    pass


@dataclass
class SystemState:
    """
    Represents the current state of the AGI reasoning process.
    
    Attributes:
        step_id: Current step index in the reasoning chain.
        predicted_error: The estimated deviation from the goal at this step (0.0 to 1.0).
        actual_state_vector: A list of floats representing the current state dimensions.
        target_vector: The desired state dimensions.
    """
    step_id: int
    predicted_error: float
    actual_state_vector: List[float]
    target_vector: List[float]

    def __post_init__(self):
        """Validate data types and ranges."""
        if not 0.0 <= self.predicted_error <= 1.0:
            raise ValueError("Predicted error must be between 0.0 and 1.0.")
        if len(self.actual_state_vector) != len(self.target_vector):
            raise ValueError("State vector and Target vector must have the same dimensions.")


@dataclass
class ControllerConfig:
    """
    Configuration for the Micro-Feedback Controller.
    
    Attributes:
        k_steps: Interval steps to trigger a confirmation point.
        deviation_threshold: Maximum allowed rate of error change (delta) per step.
        correction_gain: The factor (lambda) to apply when correcting the course.
    """
    k_steps: int = 5
    deviation_threshold: float = 0.05
    correction_gain: float = 0.5


def _calculate_vector_deviation(current: List[float], target: List[float]) -> float:
    """
    Helper function: Calculates the Euclidean distance between two vectors.
    Normalizes the result based on the magnitude of the target vector.
    
    Args:
        current: Current state vector.
        target: Target state vector.
        
    Returns:
        A float representing the normalized deviation.
    """
    if not current or not target:
        return 0.0
    
    sum_sq_diff = sum((c - t) ** 2 for c, t in zip(current, target))
    distance = math.sqrt(sum_sq_diff)
    
    # Normalize by target magnitude to keep error roughly in 0-1 range (simplified)
    target_mag = math.sqrt(sum(t ** 2 for t in target))
    if target_mag == 0:
        return distance
    
    return min(distance / target_mag, 1.0)


class MicroFeedbackController:
    """
    A controller that monitors a long-running process and validates status
    at confirmation points (every K steps).
    """

    def __init__(self, config: ControllerConfig):
        self.config = config
        self._previous_error: float = 0.0
        self._is_course_corrected: bool = False
        logger.info("MicroFeedbackController initialized with K=%d", config.k_steps)

    def _analyze_error_trend(self, current_error: float) -> Tuple[bool, float]:
        """
        Core Cybernetic Logic: Analyzes the trend of the predictive error.
        
        Args:
            current_error: The calculated error at the current confirmation point.
            
        Returns:
            Tuple[bool, float]: 
                - bool: True if deviation is detected (needs correction).
                - float: The calculated error delta.
        """
        # Calculate the derivative of error (change rate)
        error_delta = current_error - self._previous_error
        
        # Check if error is increasing significantly (Positive Feedback / Divergence)
        is_diverging = error_delta > self.config.deviation_threshold
        
        logger.debug(
            f"Analyzing trend: CurrErr={current_error:.4f}, "
            f"PrevErr={self._previous_error:.4f}, Delta={error_delta:.4f}"
        )
        
        self._previous_error = current_error
        return is_diverging, error_delta

    def step_monitor(self, state: SystemState) -> Tuple[bool, str]:
        """
        Monitors the state at a specific step.
        
        Args:
            state: The current SystemState data object.
            
        Returns:
            Tuple[bool, str]: 
                - Status (True if OK, False if Critical Failure/Stop needed).
                - Message containing diagnostic info.
        """
        if state.step_id % self.config.k_steps != 0:
            return True, "Monitoring skipped (not a confirmation point)."

        try:
            # 1. Calculate actual deviation based on vectors
            current_error = _calculate_vector_deviation(
                state.actual_state_vector, 
                state.target_vector
            )
            
            # 2. Analyze trend
            is_diverging, delta = self._analyze_error_trend(current_error)
            
            if is_diverging:
                msg = (
                    f"ALERT: Divergence detected at Step {state.step_id}. "
                    f"Error Delta {delta:.4f} > Threshold {self.config.deviation_threshold}."
                )
                logger.warning(msg)
                return False, msg
            
            if current_error > 0.8: # Hard limit failure
                 return False, "Critical Error Limit Reached."

            return True, f"Checkpoint passed at Step {state.step_id}. Status: Nominal."

        except Exception as e:
            logger.error(f"Error during step monitoring: {str(e)}")
            raise FeedbackLoopError("Monitoring failure.") from e

    def apply_correction(self, state: SystemState) -> List[float]:
        """
        Applies a negative feedback correction to the state vector.
        
        Args:
            state: The current SystemState.
            
        Returns:
            A corrected state vector adjusted towards the target.
        """
        correction_factor = self.config.correction_gain
        new_vector = []
        
        for curr, targ in zip(state.actual_state_vector, state.target_vector):
            # Move current value towards target by gain factor
            diff = targ - curr
            corrected_val = curr + (diff * correction_factor)
            new_vector.append(corrected_val)
            
        logger.info(f"Applied correction with gain {correction_factor}.")
        return new_vector


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Configuration
    config = ControllerConfig(k_steps=3, deviation_threshold=0.05)
    controller = MicroFeedbackController(config)
    
    # 2. Define Target State
    target = [10.0, 10.0, 10.0] # Goal state
    
    # 3. Simulate a long reasoning chain (e.g., 10 steps)
    # We simulate a process that starts well but starts to drift away
    current_pos = [1.0, 1.0, 1.0]
    
    print(f"Starting Simulation. Target: {target}")
    
    for i in range(1, 11):
        # Simulate reasoning step logic
        # In a real scenario, the system changes state based on inference
        # Here we simulate a drift occurring after step 4
        if i > 4:
            # Introduce noise/drift
            current_pos = [x + random.uniform(0.5, 1.5) for x in current_pos]
        else:
            # Move towards target
            current_pos = [x + 1.0 for x in current_pos]
            
        # Create State Object
        # Note: predicted_error here is a placeholder, actual error is calculated from vectors
        state = SystemState(
            step_id=i,
            predicted_error=0.0, # Placeholder
            actual_state_vector=current_pos,
            target_vector=target
        )
        
        print(f"Step {i}: State { [round(x, 2) for x in current_pos] }")
        
        # 4. Run Micro-Feedback Check
        is_healthy, message = controller.step_monitor(state)
        
        if not is_healthy:
            print(f"!!! INTERVENTION REQUIRED: {message}")
            # Apply correction
            current_pos = controller.apply_correction(state)
            print(f"--> Corrected State: { [round(x, 2) for x in current_pos] }")
            # Update state for next iteration after correction
            state.actual_state_vector = current_pos
            # Reset error monitoring logic after correction if necessary
            controller._previous_error = _calculate_vector_deviation(current_pos, target)
            
        else:
            print(f"    > {message}")
            
    print("Simulation Complete.")