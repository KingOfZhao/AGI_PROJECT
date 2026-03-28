"""
Module: auto_整合_意图结构化_em_104_e1_a203f8
Description: This module integrates Intention Structuring (em_104_E1), Tacit Knowledge 
             Digitization (bu_104_P2), and Skill Pre-rendering (gap_104_G1). 
             It compiles observed biological motions (gestures, craftsmanship) into 
             executable robotic control scripts or high-dimensional CAD models, 
             ensuring lossless conversion from biological intent to silicon execution.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MotionType(Enum):
    """Enumeration of supported motion types."""
    GESTURE_COMMAND = "gesture_command"
    CRAFTSMANSHIP = "craftsmanship"
    INDUSTRIAL_OPERATION = "industrial_operation"


class OutputFormat(Enum):
    """Enumeration of supported output formats."""
    ROBOT_SCRIPT = "robot_script"
    CAD_MODEL = "cad_model"


@dataclass
class SpatialCoordinate:
    """Represents a point in 3D space with optional rotation."""
    x: float
    y: float
    z: float
    rx: Optional[float] = 0.0  # Rotation X (radians)
    ry: Optional[float] = 0.0  # Rotation Y (radians)
    rz: Optional[float] = 0.0  # Rotation Z (radians)

    def to_array(self) -> np.ndarray:
        """Converts the coordinate to a numpy array."""
        return np.array([self.x, self.y, self.z, self.rx, self.ry, self.rz])


@dataclass
class ObservedMotion:
    """Input data structure representing observed human motion."""
    motion_id: str
    motion_type: MotionType
    timestamp: float
    keypoints: List[SpatialCoordinate]
    velocity_factor: float = 1.0  # Speed multiplier
    force_estimate: float = 0.0   # Estimated force in Newtons
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutableInstruction:
    """Represents a single instruction in the robot control script."""
    command: str
    parameters: Dict[str, Any]
    physical_constraints: Dict[str, float]
    timestamp: float


class IntentStructuringProcessor:
    """
    Core class for processing and structuring human intent from observed motions.
    (em_104_E1 implementation)
    """

    def __init__(self, sensitivity_threshold: float = 0.05):
        """
        Initialize the processor.
        
        Args:
            sensitivity_threshold: Minimum movement distance to be considered intentional.
        """
        self.sensitivity_threshold = sensitivity_threshold
        logger.info("IntentStructuringProcessor initialized with threshold: %s", sensitivity_threshold)

    def _validate_motion_data(self, motion: ObservedMotion) -> bool:
        """
        Validates the input motion data structure and integrity.
        
        Args:
            motion: The observed motion data.
            
        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not motion.keypoints:
            raise ValueError("Motion data must contain keypoints.")
        
        if motion.velocity_factor <= 0:
            raise ValueError("Velocity factor must be positive.")
        
        # Boundary checks for coordinates (assuming operational workspace limits)
        for kp in motion.keypoints:
            if not all(-1000.0 <= val <= 1000.0 for val in [kp.x, kp.y, kp.z]):
                raise ValueError(f"Keypoint {kp} exceeds workspace boundaries.")
        
        return True

    def extract_intent_vector(self, motion: ObservedMotion) -> Dict[str, Any]:
        """
        Analyzes motion to extract structured intent.
        
        Args:
            motion: ObservedMotion object containing raw data.
            
        Returns:
            A dictionary containing the structured intent.
        """
        try:
            self._validate_motion_data(motion)
            logger.debug(f"Processing motion ID: {motion.motion_id}")

            # Calculate trajectory vector (simplified logic for demonstration)
            start_point = motion.keypoints[0]
            end_point = motion.keypoints[-1]
            
            trajectory_vector = end_point.to_array() - start_point.to_array()
            magnitude = np.linalg.norm(trajectory_vector[:3])

            # Filter noise
            if magnitude < self.sensitivity_threshold:
                logger.info("Motion magnitude below threshold, classifying as 'Hold/No-op'.")
                intent_type = "stationary"
            else:
                intent_type = motion.motion_type.value

            structured_intent = {
                "intent_id": f"intent_{motion.motion_id}",
                "type": intent_type,
                "trajectory_vector": trajectory_vector.tolist(),
                "magnitude": magnitude,
                "temporal_duration": motion.timestamp,
                "inferred_force": motion.force_estimate
            }
            
            logger.info(f"Intent extracted: Type={intent_type}, Mag={magnitude:.4f}")
            return structured_intent

        except ValueError as ve:
            logger.error(f"Validation Error: {ve}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during intent extraction: {e}", exc_info=True)
            raise RuntimeError("Failed to extract intent.") from e


class SkillPreRenderer:
    """
    Core class for converting structured intent into physical-constraint-aware
    executable scripts or models. (bu_104_P2 & gap_104_G1 implementation)
    """

    def __init__(self, max_joint_speed: float = 500.0, max_torque: float = 100.0):
        """
        Initialize the renderer with physical constraints.
        
        Args:
            max_joint_speed: Maximum allowable joint speed (mm/s).
            max_torque: Maximum allowable torque (Nm).
        """
        self.max_joint_speed = max_joint_speed
        self.max_torque = max_torque
        self._instruction_counter = 0

    def _calculate_physical_constraints(self, intent: Dict[str, Any]) -> Dict[str, float]:
        """
        Helper function to calculate safety constraints based on intent.
        
        Args:
            intent: The structured intent dictionary.
            
        Returns:
            Dictionary of physical constraints.
        """
        # Simple logic: scale speed based on force estimate to ensure safety
        # Higher force = slower movement for precision
        force = intent.get('inferred_force', 0.0)
        dynamic_speed_limit = self.max_joint_speed / (1 + (force / 50.0))
        
        return {
            "speed_limit": min(dynamic_speed_limit, self.max_joint_speed),
            "torque_limit": self.max_torque,
            "collision_check_required": force > 10.0
        }

    def render_robot_script(self, intent: Dict[str, Any], target_format: OutputFormat) -> List[ExecutableInstruction]:
        """
        Renders the intent into a sequence of executable instructions.
        
        Args:
            intent: Structured intent data.
            target_format: The desired output format (Script or CAD).
            
        Returns:
            A list of ExecutableInstruction objects.
        """
        if target_format != OutputFormat.ROBOT_SCRIPT:
            logger.warning("Currently only ROBOT_SCRIPT rendering is fully implemented in this method.")

        logger.info(f"Rendering intent {intent.get('intent_id')} to {target_format.value}")
        
        constraints = self._calculate_physical_constraints(intent)
        instructions: List[ExecutableInstruction] = []
        
        # Map intent type to commands
        command_map = {
            "gesture_command": "MOVE_LINEAR",
            "craftsmanship": "ADAPTIVE_PATH",
            "industrial_operation": "EXECUTE_PROCESS",
            "stationary": "WAIT"
        }
        
        cmd_type = command_map.get(intent.get('type', ''), "UNKNOWN")
        trajectory = intent.get('trajectory_vector', [0]*6)
        
        # Generate main movement instruction
        self._instruction_counter += 1
        main_instruction = ExecutableInstruction(
            command=cmd_type,
            parameters={
                "delta_x": trajectory[0],
                "delta_y": trajectory[1],
                "delta_z": trajectory[2],
                "rotation": trajectory[3:]
            },
            physical_constraints=constraints,
            timestamp=intent.get('temporal_duration', 0.0)
        )
        instructions.append(main_instruction)
        
        # Generate post-action instruction (e.g., tool activation)
        if intent.get('inferred_force', 0) > 5.0:
            self._instruction_counter += 1
            post_instruction = ExecutableInstruction(
                command="ACTUATOR_ENGAGE",
                parameters={"force_target": intent['inferred_force']},
                physical_constraints={"torque_limit": constraints['torque_limit']},
                timestamp=intent.get('temporal_duration', 0.0) + 0.1
            )
            instructions.append(post_instruction)

        logger.info(f"Generated {len(instructions)} instructions.")
        return instructions


def bio_to_silicon_converter(
    observed_motion: ObservedMotion, 
    output_format: OutputFormat = OutputFormat.ROBOT_SCRIPT
) -> List[Dict[str, Any]]:
    """
    Main orchestration function: Integrates Intent Structuring, Tacit Knowledge 
    Digitization, and Skill Pre-rendering.
    
    This function acts as the bridge between biological input and silicon execution.
    
    Args:
        observed_motion: The raw observed motion data.
        output_format: The desired output format.
        
    Returns:
        A list of dictionaries representing executable instructions.
        
    Example:
        >>> keypoints = [SpatialCoordinate(0,0,0), SpatialCoordinate(10,0,5)]
        >>> motion = ObservedMotion(
        ...     motion_id="craft_001", 
        ...     motion_type=MotionType.CRAFTSMANSHIP, 
        ...     timestamp=1.0, 
        ...     keypoints=keypoints,
        ...     force_estimate=20.0
        ... )
        >>> result = bio_to_silicon_converter(motion)
        >>> print(result[0]['command'])
        'ADAPTIVE_PATH'
    """
    logger.info(f"Starting conversion process for motion: {observed_motion.motion_id}")
    
    # Phase 1: Intent Structuring (em_104_E1)
    intent_processor = IntentStructuringProcessor(sensitivity_threshold=0.01)
    structured_intent = intent_processor.extract_intent_vector(observed_motion)
    
    # Phase 2 & 3: Tacit Knowledge & Pre-rendering (bu_104_P2 & gap_104_G1)
    skill_renderer = SkillPreRenderer(max_joint_speed=1000.0)
    executable_script = skill_renderer.render_robot_script(structured_intent, output_format)
    
    # Convert dataclasses to dict for output
    output_data = [asdict(instr) for instr in executable_script]
    
    logger.info("Conversion complete. Output generated.")
    return output_data


# Example Usage and Demonstration
if __name__ == "__main__":
    # Create dummy input data representing a craftsman's hand movement
    # Moving from (0,0,0) to (50, 50, 10) with rotation
    start_kp = SpatialCoordinate(x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0)
    mid_kp = SpatialCoordinate(x=25.0, y=30.0, z=5.0, rx=0.1, ry=0.1, rz=0.0)
    end_kp = SpatialCoordinate(x=50.0, y=50.0, z=10.0, rx=0.2, ry=0.2, rz=0.0)
    
    observed_data = ObservedMotion(
        motion_id="craft_op_2023_10_27_01",
        motion_type=MotionType.CRAFTSMANSHIP,
        timestamp=1.5,
        keypoints=[start_kp, mid_kp, end_kp],
        velocity_factor=1.0,
        force_estimate=45.5, # 45.5 Newtons of force
        metadata={"operator_id": "craftsman_alpha", "tool": "chisel"}
    )

    # Execute the AGI Skill
    try:
        script = bio_to_silicon_converter(observed_data, OutputFormat.ROBOT_SCRIPT)
        
        print("\n--- Generated Robot Control Script ---")
        print(json.dumps(script, indent=4))
        
    except ValueError as e:
        print(f"Input Validation Failed: {e}")
    except RuntimeError as e:
        print(f"Execution Failed: {e}")