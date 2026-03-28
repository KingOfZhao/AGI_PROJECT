"""
Skill Module: Force-Semantic Alignment Model (FSAM)

This module implements a mapping mechanism between natural language descriptions
of force (e.g., "gentle", "hard") and physical torque parameters using a PID
control framework. It adheres to the "Left-Right Cross-Domain Overlap" principle,
bridging the gap between human intent (Semantic Domain) and robot execution
(Physical Domain).

Dependencies:
    - numpy: For mathematical operations and noise generation.
    - typing: For type hints.
    - logging: For operational logging.
    - dataclasses: For structured data representation.
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Classes ---

class ForceSemanticLabel(Enum):
    """Enumeration of semantic labels for force levels."""
    GENTLE = "稍微用点力"
    MODERATE = "正常力度"
    FIRM = "用点力"
    HARD = "全力"

@dataclass
class PIDParams:
    """PID Controller Parameters."""
    kp: float
    ki: float
    kd: float
    setpoint: float

@dataclass
class AlignmentResult:
    """Result of the alignment process."""
    semantic_label: str
    mapped_torque: float
    torque_std_dev: float
    pid_params: PIDParams
    confidence_score: float
    is_safe: bool

class AlignmentModelError(Exception):
    """Custom exception for alignment failures."""
    pass

# --- Core Class ---

class ForceSemanticAlignmentModel:
    """
    Maps natural language force descriptions to executable PID parameters and
    torque limits based on the 'Left-Right Cross-Domain Overlap' principle.
    
    The principle assumes that a semantic concept (Left Domain) overlaps with
    a physical parameter distribution (Right Domain) via a shared latent space
    (e.g., effort intensity).
    """

    def __init__(self, max_safe_torque: float = 10.0):
        """
        Initialize the model with safety limits and pre-defined mappings.
        
        Args:
            max_safe_torque (float): The maximum allowable torque in Newton-meters (Nm).
        """
        self.max_safe_torque = max_safe_torque
        self._semantic_map = self._build_semantic_map()
        logger.info(f"ForceSemanticAlignmentModel initialized with max torque: {max_safe_torque} Nm")

    def _build_semantic_map(self) -> Dict[ForceSemanticLabel, Dict[str, Any]]:
        """
        Internal method to define the mapping between semantics and physics.
        
        Returns:
            Dict: A dictionary mapping semantic labels to physical parameters.
        """
        # The 'overlap' is defined here: Semantic Label -> [Mean Torque, Std Dev, PID Gains]
        return {
            ForceSemanticLabel.GENTLE: {
                "mean_torque": 1.5, 
                "std_dev": 0.2, 
                "pid_gains": (0.5, 0.01, 0.1)
            },
            ForceSemanticLabel.MODERATE: {
                "mean_torque": 4.0, 
                "std_dev": 0.5, 
                "pid_gains": (1.0, 0.05, 0.2)
            },
            ForceSemanticLabel.FIRM: {
                "mean_torque": 7.0, 
                "std_dev": 0.8, 
                "pid_gains": (1.5, 0.1, 0.3)
            },
            ForceSemanticLabel.HARD: {
                "mean_torque": 9.5, 
                "std_dev": 1.0, 
                "pid_gains": (2.0, 0.2, 0.5)
            }
        }

    def _validate_input(self, semantic_input: Any) -> ForceSemanticLabel:
        """
        Helper function to validate and convert input to Enum.
        
        Args:
            semantic_input: Input string or Enum.
            
        Returns:
            ForceSemanticLabel: The validated enum member.
            
        Raises:
            AlignmentModelError: If input is invalid.
        """
        if isinstance(semantic_input, ForceSemanticLabel):
            return semantic_input
        
        if isinstance(semantic_input, str):
            for label in ForceSemanticLabel:
                if label.value == semantic_input:
                    return label
            raise AlignmentModelError(f"Unknown semantic label: {semantic_input}")
        
        raise AlignmentModelError(f"Invalid input type: {type(semantic_input)}")

    def map_semantic_to_pid(self, semantic_input: Any) -> AlignmentResult:
        """
        Core Function 1: Maps semantic language to physical PID parameters.
        
        This function performs the cross-domain mapping. It retrieves the 
        statistical properties of the force associated with the semantic label
        and constructs a PID configuration.
        
        Args:
            semantic_input: The natural language description or Enum label.
            
        Returns:
            AlignmentResult: An object containing the mapped physical parameters.
        """
        try:
            # 1. Validate Input
            label = self._validate_input(semantic_input)
            logger.info(f"Mapping semantic label: {label.value}")

            # 2. Retrieve Cross-Domain Data
            mapping_data = self._semantic_map.get(label)
            if not mapping_data:
                raise AlignmentModelError(f"No mapping found for {label}")

            target_torque = mapping_data['mean_torque']
            torque_std = mapping_data['std_dev']
            kp, ki, kd = mapping_data['pid_gains']

            # 3. Boundary Check (Safety)
            if target_torque > self.max_safe_torque:
                logger.warning(f"Target torque {target_torque} exceeds safety limit. Capping.")
                target_torque = self.max_safe_torque
                confidence = 0.5 # Low confidence due to capping
            else:
                confidence = 0.95

            # 4. Construct PID Parameters
            # Setpoint is the target torque derived from the semantic label
            pid_params = PIDParams(kp=kp, ki=ki, kd=kd, setpoint=target_torque)

            return AlignmentResult(
                semantic_label=label.value,
                mapped_torque=target_torque,
                torque_std_dev=torque_std,
                pid_params=pid_params,
                confidence_score=confidence,
                is_safe=(target_torque <= self.max_safe_torque)
            )

        except AlignmentModelError as e:
            logger.error(f"Alignment failed: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during mapping: {e}")
            raise AlignmentModelError("System failure in semantic mapping")

    def simulate_execution(self, alignment_result: AlignmentResult, steps: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Core Function 2: Simulates the force control execution based on mapped parameters.
        
        This validates if the mapped parameters produce a physical output (torque)
        that stays within the expected "Left-Right Overlap" range (Mean +/- Std Dev).
        
        Args:
            alignment_result: The result from the mapping function.
            steps: Number of simulation steps.
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Time steps and simulated torque values.
        """
        logger.info(f"Simulating execution for: {alignment_result.semantic_label}")
        
        dt = 0.01  # Time step
        time_steps = np.linspace(0, steps*dt, steps)
        
        # Initialize simulation variables
        current_torque = 0.0
        integral = 0.0
        prev_error = 0.0
        simulated_torques = []
        
        setpoint = alignment_result.pid_params.setpoint
        kp = alignment_result.pid_params.kp
        ki = alignment_result.pid_params.ki
        kd = alignment_result.pid_params.kd

        # Add noise to sensor feedback to simulate real-world conditions
        noise_level = alignment_result.torque_std_dev * 0.1

        for _ in range(steps):
            # Simple PID Loop Simulation
            # Feedback = Current Torque + Noise
            feedback = current_torque + np.random.normal(0, noise_level)
            
            error = setpoint - feedback
            integral += error * dt
            derivative = (error - prev_error) / dt
            
            # Control output
            output = (kp * error) + (ki * integral) + (kd * derivative)
            
            # Physical system response (simplified first-order system)
            # The torque approaches the control output
            current_torque += (output - current_torque) * 0.1 
            
            simulated_torques.append(current_torque)
            prev_error = error

        # Validation Check
        mean_sim_torque = np.mean(simulated_torques[-20:])
        logger.info(f"Simulation complete. Avg Torque: {mean_sim_torque:.2f} Nm (Target: {setpoint:.2f} Nm)")

        return time_steps, np.array(simulated_torques)

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the model
    try:
        model = ForceSemanticAlignmentModel(max_safe_torque=12.0)
        
        # Input: Fuzzy natural language
        user_intent = "稍微用点力"  # "Use a little force"
        
        # Step 1: Map Semantic to Physical (Cross-Domain Alignment)
        result = model.map_semantic_to_pid(user_intent)
        
        print("\n--- Alignment Result ---")
        print(f"Intent: {result.semantic_label}")
        print(f"Target Torque: {result.mapped_torque} Nm")
        print(f"Allowed Variance (StdDev): {result.torque_std_dev}")
        print(f"PID Config: P={result.pid_params.kp}, I={result.pid_params.ki}, D={result.pid_params.kd}")
        print(f"Safe: {result.is_safe}")
        
        # Step 2: Simulate to verify (Optional)
        times, torques = model.simulate_execution(result)
        
        # Basic assertion for demonstration
        assert np.mean(torques[-10:]) > (result.mapped_torque - result.torque_std_dev)
        
    except AlignmentModelError as e:
        print(f"Error: {e}")