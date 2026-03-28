"""
Module: tool_cognitive_assimilation_protocol
Description: Implements the 'Tool-Cognitive Assimilation Protocol' for robotic systems.
             Enables dynamic neural plasticity by realigning self-perception models
             to include external tools and environmental features as extensions of the body.
Author: AGI System Core
Version: 3.2.1
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveAssimilation")

class AssimilationType(Enum):
    """Enumeration for different types of cognitive assimilation."""
    KINEMATIC_EXTENSION = 1
    ENVIRONMENTAL_SCAFFOLDING = 2
    SENSOR_EXPANSION = 3

@dataclass
class RigidBody:
    """Represents a physical object with spatial properties."""
    object_id: str
    position: np.ndarray  # x, y, z
    orientation: np.ndarray  # quaternion x, y, z, w
    bounding_box: np.ndarray  # 3D dimensions
    friction_coefficient: float = 0.5
    mass: float = 1.0

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Validates data integrity."""
        if self.position.shape != (3,):
            raise ValueError("Position must be a numpy array of shape (3,)")
        if self.mass <= 0:
            raise ValueError("Mass must be positive.")

@dataclass
class RobotState:
    """Current state of the robot agent."""
    base_pose: np.ndarray
    joint_positions: np.ndarray
    held_object: Optional[RigidBody] = None
    contact_points: List[np.ndarray] = field(default_factory=list)

class KinematicModel:
    """
    A simplified representation of a robot's Kinematic Model.
    In a real scenario, this would interface with MoveIt or PyBullet.
    """
    def __init__(self, initial_reach: float = 1.0):
        self.base_reach = initial_reach
        self.effective_reach = initial_reach
        self.link_lengths = [initial_reach / 2, initial_reach / 2] # Simplified 2-link arm
        self.collision_geometry = {"body": np.array([0.5, 0.5, 1.0])}

    def update_safety_bounds(self, new_geometry: Dict[str, np.ndarray]):
        """Updates the self-collision detection boundaries."""
        self.collision_geometry.update(new_geometry)
        logger.info(f"Self-collision model updated with keys: {list(new_geometry.keys())}")

class CognitiveAssimilationProtocol:
    """
    Core protocol for modifying the robot's self-image and kinematic awareness
    based on tool interaction and environmental contact.
    
    Attributes:
        robot_state (RobotState): The current state of the robot.
        kinematic_model (KinematicModel): The mutable internal model of the robot's body.
    """

    def __init__(self, initial_state: RobotState, initial_model: KinematicModel):
        self.robot_state = initial_state
        self.kinematic_model = initial_model
        self._assimilation_history: List[Dict[str, Any]] = []
        logger.info("Cognitive Assimilation Protocol Initialized.")

    def assimilate_tool(self, tool: RigidBody, grip_offset: np.ndarray) -> bool:
        """
        Assimilates a grasped tool into the robot's self-model.
        
        This function extends the robot's kinematic chain and updates collision
        detection models to include the tool's volume.
        
        Args:
            tool (RigidBody): The physical object being grasped.
            grip_offset (np.ndarray): The position of the grip relative to the end-effector.
        
        Returns:
            bool: True if assimilation was successful, False otherwise.
        
        Raises:
            ValueError: If tool data is invalid.
        """
        if tool.mass > 10.0:
            logger.warning(f"Tool mass {tool.mass} exceeds safe payload. Assimilation aborted.")
            return False

        try:
            logger.info(f"Starting assimilation for tool: {tool.object_id}")
            
            # 1. Extend Kinematic Chain (Neural Plasticity Simulation)
            # We treat the tool as a new link in the kinematic chain
            tool_length = np.max(tool.bounding_box)
            self.kinematic_model.link_lengths.append(tool_length)
            self.kinematic_model.effective_reach += tool_length
            
            # 2. Update Self-Collision Model
            # The robot must now avoid hitting itself with the tool
            new_geometry = {
                "tool_tip": tool.bounding_box,
                "tool_shaft": np.array([tool_length * 0.8, 0.1, 0.1])
            }
            self.kinematic_model.update_safety_bounds(new_geometry)
            
            # 3. Update Robot State
            self.robot_state.held_object = tool
            
            # Record the event
            self._record_assimilation_event(AssimilationType.KINEMATIC_EXTENSION, tool.object_id)
            
            logger.info(f"Assimilation complete. New effective reach: {self.kinematic_model.effective_reach}")
            return True

        except Exception as e:
            logger.error(f"Critical failure during tool assimilation: {e}")
            return False

    def assimilate_environmental_scaffold(self, contact_point: np.ndarray, surface_normal: np.ndarray) -> Optional[np.ndarray]:
        """
        Assimilates an environmental feature (like a wall or table) as a temporary 
        support structure to extend cognitive processing and stability.
        
        This realizes 'Environment as Computation' by treating the wall as a 
        kinematic constraint or a force closure point.
        
        Args:
            contact_point (np.ndarray): World coordinates of the contact.
            surface_normal (np.ndarray): Normal vector of the surface.
            
        Returns:
            Optional[np.ndarray]: A computed virtual support vector or plan adjustment.
        """
        # Input Validation
        if not self._validate_vector(contact_point, 3) or not self._validate_vector(surface_normal, 3):
            logger.error("Invalid contact point or normal vector provided.")
            return None

        logger.info(f"Assimilating environment at {contact_point} for structural support.")
        
        # Check stability: Is the surface suitable for leaning/support?
        # Surface normal should be roughly opposing the gravity vector (Z-axis) or perpendicular
        gravity_vector = np.array([0, 0, -1])
        alignment = np.dot(surface_normal, gravity_vector)
        
        if alignment > 0.7:
            logger.info("Surface identified as stable floor/platform.")
            # Logic to adjust posture to utilize this surface
            adjustment = self._calculate_posture_adjustment(contact_point, "support")
            return adjustment
            
        elif alignment > -0.1 and alignment < 0.1:
            logger.info("Surface identified as vertical wall. Engaging 'Wall-Pushing' strategy.")
            # Treat wall as a temporary joint (pseudo-kinematic link)
            self._record_assimilation_event(AssimilationType.ENVIRONMENTAL_SCAFFOLDING, "WALL")
            adjustment = self._calculate_posture_adjustment(contact_point, "lateral_support")
            return adjustment
            
        else:
            logger.warning("Surface geometry unsuitable for scaffolding.")
            return None

    def _calculate_posture_adjustment(self, target: np.ndarray, mode: str) -> np.ndarray:
        """
        Helper function to calculate the necessary adjustments in the robot's 
        control loop based on the assimilated element.
        
        Args:
            target (np.ndarray): The target point for adjustment.
            mode (str): Type of adjustment ('support' or 'lateral_support').
            
        Returns:
            np.ndarray: A vector representing the adjustment delta.
        """
        # Simplified logic: return a vector moving the center of mass towards the support
        current_com = self.robot_state.base_pose[:3]
        delta = (target - current_com) * 0.1 # Move 10% closer to the support point
        logger.debug(f"Calculated posture adjustment: {delta}")
        return delta

    def _record_assimilation_event(self, type_: AssimilationType, target_id: str):
        """Records the assimilation event for learning and debugging."""
        event = {
            "type": type_,
            "target": target_id,
            "timestamp": np.datetime64('now')
        }
        self._assimilation_history.append(event)

    def _validate_vector(self, vec: np.ndarray, dim: int) -> bool:
        """Validates that a numpy array is a vector of specific dimension."""
        return isinstance(vec, np.ndarray) and vec.shape == (dim,)

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Initialize System
    initial_joints = np.array([0.0, 0.5, 0.0])
    base_pose = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) # Pos + Orientation
    state = RobotState(base_pose=base_pose, joint_positions=initial_joints)
    model = KinematicModel(initial_reach=1.5)
    protocol = CognitiveAssimilationProtocol(state, model)

    print("--- Scenario 1: Tool Assimilation ---")
    # Define a long pole
    pole = RigidBody(
        object_id="long_pole_01",
        position=np.array([1.0, 0.0, 0.5]),
        orientation=np.array([0.0, 0.0, 0.0, 1.0]),
        bounding_box=np.array([1.2, 0.05, 0.05]), # Length 1.2m
        mass=0.5
    )

    # Robot grabs the pole
    success = protocol.assimilate_tool(pole, grip_offset=np.array([0, 0, 0.1]))
    if success:
        print(f"New Reach: {protocol.kinematic_model.effective_reach}")
        print(f"Collision Geometry: {protocol.kinematic_model.collision_geometry.keys()}")

    print("\n--- Scenario 2: Environmental Scaffolding ---")
    # Robot touches a wall
    wall_contact = np.array([1.0, 0.5, 0.0])
    wall_normal = np.array([0.0, 1.0, 0.0]) # Normal pointing away from wall
    
    adjustment = protocol.assimilate_environmental_scaffold(wall_contact, wall_normal)
    if adjustment is not None:
        print(f"Posture Adjustment Vector: {adjustment}")