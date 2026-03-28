"""
Module: auto_具身认知的sim_to_real_ga_a0adcd
Description: Implementation for bridging the Sim-to-Real gap in Embodied Cognition systems.
             This module handles the discrepancy between idealized physics in simulation
             (e.g., robot calligraphy) and the stochastic nature of the physical world
             (e.g., paper absorbency, friction). It employs a hybrid approach using
             Domain Randomization and a Human-in-the-Loop 'Cementing' strategy.
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Sim2Real_Bridge")

class SkillStatus(Enum):
    """Status of the Skill Node."""
    SIMULATED = 1
    CALIBRATING = 2
    CEMENTED = 3
    FAILED = 4

@dataclass
class PhysicsState:
    """Represents a physical state vector (e.g., joint angles, velocities)."""
    timestamp: float
    joint_positions: np.ndarray
    joint_velocities: np.ndarray
    external_force: Optional[np.ndarray] = None

    def __post_init__(self):
        """Validate data types."""
        if not isinstance(self.joint_positions, np.ndarray):
            self.joint_positions = np.array(self.joint_positions)
        if not isinstance(self.joint_velocities, np.ndarray):
            self.joint_velocities = np.array(self.joint_velocities)

@dataclass
class Trajectory:
    """A sequence of PhysicsStates representing a skill motion."""
    name: str
    states: List[PhysicsState] = field(default_factory=list)
    domain_params: Dict[str, float] = field(default_factory=dict)

    def add_state(self, state: PhysicsState):
        self.states.append(state)

class SimToRealGapError(Exception):
    """Custom exception for critical failures in Sim-to-Real transfer."""
    pass

class RealityGapBridge:
    """
    Manages the transfer of a skill from simulation to reality.
    
    This class handles the 'Reality Gap' by detecting discrepancies between
    simulated expectations and real-world sensor data, and applying corrections.
    It specifically implements the 'Human Micro-Adjustment' strategy for cementing.
    """

    def __init__(self, 
                 sim_trajectory: Trajectory, 
                 variance_threshold: float = 0.05,
                 learning_rate: float = 0.1):
        """
        Initialize the bridge.
        
        Args:
            sim_trajectory: The trajectory generated in the simulation environment.
            variance_threshold: Maximum allowed Euclidean distance deviation.
            learning_rate: Rate at which the system adapts to human corrections.
        """
        self.sim_trajectory = sim_trajectory
        self.variance_threshold = variance_threshold
        self.learning_rate = learning_rate
        self.status = SkillStatus.SIMULATED
        self._calibration_offset = np.zeros_like(sim_trajectory.states[0].joint_positions)
        logger.info(f"RealityGapBridge initialized for skill: {sim_trajectory.name}")

    def _calculate_deviation(self, 
                             expected: np.ndarray, 
                             observed: np.ndarray) -> float:
        """
        Helper: Calculate Euclidean distance between expected and observed states.
        """
        if expected.shape != observed.shape:
            raise ValueError("Shape mismatch between expected and observed states.")
        
        return np.linalg.norm(expected - observed)

    def inject_domain_randomization(self) -> Dict[str, float]:
        """
        Simulate 'micro-deviations' in physics parameters (Friction, Mass, Damping).
        This represents the 'virtual training' side of the gap.
        
        Returns:
            Dict of randomized physics parameters.
        """
        # Randomize friction and mass within 10% deviation
        friction = np.random.uniform(0.9, 1.1) * 0.5  # Base friction 0.5
        mass = np.random.uniform(0.9, 1.1) * 1.0      # Base mass 1.0
        
        params = {'friction': friction, 'mass': mass}
        logger.debug(f"Injected Domain Randomization: {params}")
        return params

    def execute_with_adaptation(self, 
                                real_time_state: PhysicsState, 
                                step_index: int) -> Tuple[np.ndarray, bool]:
        """
        Core Function 1: Real-time execution with anomaly detection.
        
        Compares the current real-world state against the simulation reference.
        If deviation exceeds threshold, it flags the need for intervention.
        
        Args:
            real_time_state: Current sensor readings from the robot.
            step_index: Current step in the trajectory execution.
            
        Returns:
            Tuple[corrected_joint_positions, needs_human_help]
        """
        if step_index >= len(self.sim_trajectory.states):
            raise IndexError("Step index out of bounds for trajectory.")

        reference_state = self.sim_trajectory.states[step_index]
        expected_pos = reference_state.joint_positions
        
        # Calculate the gap
        deviation = self._calculate_deviation(expected_pos, real_time_state.joint_positions)
        
        if deviation > self.variance_threshold:
            logger.warning(f"Reality Gap detected at step {step_index}: {deviation:.4f}")
            # Apply a simple PD correction or flag for help
            correction = (expected_pos - real_time_state.joint_positions) * self.learning_rate
            adjusted_target = expected_pos + correction + self._calibration_offset
            return adjusted_target, True # Needs human help
        
        logger.info(f"Step {step_index} within tolerance: {deviation:.4f}")
        return expected_pos + self._calibration_offset, False

    def human_cementing_process(self, 
                                human_correction_delta: np.ndarray, 
                                step_index: int) -> bool:
        """
        Core Function 2: Human-in-the-loop 'Cementing'.
        
        Accepts a 'micro-adjustment' vector from a human operator (e.g., via teleop).
        This adjustment permanently updates the skill node to fix the physical gap
        (e.g., accounting for ink absorbency or table unevenness).
        
        Args:
            human_correction_delta: The adjustment vector provided by the human.
            step_index: The step where the adjustment occurred.
            
        Returns:
            Success status of the cementing operation.
        """
        try:
            if np.linalg.norm(human_correction_delta) > 1.0:
                raise SimToRealGapError("Human correction magnitude dangerously high!")
            
            # Update a global offset or a local waypoint modification
            self._calibration_offset += human_correction_delta * 0.5 # Damped integration
            
            # Update the internal reference trajectory for future runs
            # This is the 'Symbiosis' moment: Human intuition becomes code.
            self.sim_trajectory.states[step_index].joint_positions += human_correction_delta
            
            self.status = SkillStatus.CEMENTED
            logger.info(f"Skill CEMENTED at step {step_index} with delta {human_correction_delta}")
            return True

        except SimToRealGapError as e:
            logger.critical(f"Safety Stop: {e}")
            self.status = SkillStatus.FAILED
            return False
        except Exception as e:
            logger.error(f"Unexpected error during cementing: {e}")
            return False

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Create a dummy simulated trajectory (e.g., writing the character 'A')
    dummy_states = [
        PhysicsState(t, np.array([0.0, 0.0, 0.0]), np.zeros(3)) 
        for t in range(10)
    ]
    # Simulate a straight line motion in joint space
    for i, state in enumerate(dummy_states):
        state.joint_positions = np.array([float(i)*0.1, float(i)*0.1, 0.0])
    
    sim_traj = Trajectory("Write_A", dummy_states)

    # 2. Initialize the Bridge
    bridge = RealityGapBridge(sim_traj, variance_threshold=0.15)

    # 3. Simulate Real-world execution with noise (The Gap)
    # Simulating paper absorbency causing the pen to sink lower than expected
    physical_noise = np.array([0.0, 0.0, 0.2]) 

    print("--- Starting Execution ---")
    for i in range(10):
        # Robot senses current state
        current_real_pos = sim_traj.states[i].joint_positions + physical_noise
        current_real_state = PhysicsState(float(i), current_real_pos, np.zeros(3))
        
        # System tries to execute
        target, needs_help = bridge.execute_with_adaptation(current_real_state, i)
        
        if needs_help:
            print(f"! Step {i}: Gap detected. Requesting human micro-adjustment...")
            # Human pushes the pen back up slightly
            human_fix = np.array([0.0, 0.0, -0.15]) 
            success = bridge.human_cementing_process(human_fix, i)
            if not success:
                print("Execution Halted.")
                break
        
    print(f"Final Status: {bridge.status}")