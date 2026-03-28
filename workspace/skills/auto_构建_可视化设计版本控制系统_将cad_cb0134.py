"""
Module: visual_design_version_control_system.py

This module simulates a backend service for a 'Visual Design Version Control System'.
It bridges CAD geometric operations with a Flutter-based frontend state management
architecture (conceptually).

The core concept is to encapsulate CAD operations (e.g., Extrude, Fillet) as
immutable 'Action' objects. These actions form a Directed Acyclic Graph (DAG).
The system allows traversing this timeline (Time Slider) and creating branches
at any historical node for non-linear design exploration.

Author: Senior Python Engineer (AGI System)
"""

import logging
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CadOperationType(Enum):
    """Enumeration of supported CAD feature operations."""
    SKETCH = "SKETCH"
    EXTRUDE = "EXTRUDE"
    FILLET = "FILLET"
    CHAMFER = "CHAMFER"
    CUT = "CUT"
    BOOLEAN_UNION = "BOOLEAN_UNION"


@dataclass
class FlutterAction:
    """
    Represents a discrete CAD operation encapsulated as an Action object.
    
    This structure mimics a Redux/Action pattern often used in Flutter state management.
    It is serializable to be sent over a websocket or API bridge.
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = "CAD_OPERATION"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())
    previous_action_id: Optional[str] = None  # Link to previous state for DAG

    def to_json(self) -> str:
        """Serializes the action to JSON string for transmission."""
        return json.dumps(asdict(self))


class DesignVersionController:
    """
    Manages the timeline of CAD operations and handles state traversal.
    
    This class acts as the single source of truth for the design history,
    enabling the 'Time Slider' functionality on the frontend.
    """

    def __init__(self, project_id: str):
        """
        Initialize the version controller.
        
        Args:
            project_id (str): Unique identifier for the design project.
        """
        self.project_id = project_id
        self._action_history: List[FlutterAction] = []
        self._current_head_index: int = -1
        self._branches: Dict[str, List[FlutterAction]] = {}  # branch_id -> actions
        
        # Lock to prevent race conditions during complex operations
        self._is_locked: bool = False
        logger.info(f"Initialized DesignVersionController for project {project_id}")

    def commit_action(self, operation: CadOperationType, parameters: Dict[str, Any]) -> FlutterAction:
        """
        Core Function 1: Commits a new CAD operation to the history.
        
        Validates input, creates a FlutterAction, and appends it to the timeline.
        
        Args:
            operation (CadOperationType): The type of CAD feature.
            parameters (Dict[str, Any]): Parameters for the operation (e.g., height, radius).
            
        Returns:
            FlutterAction: The created action object.
            
        Raises:
            ValueError: If parameters are invalid or missing required fields.
            RuntimeError: If the controller is locked.
        """
        if self._is_locked:
            raise RuntimeError("System is currently processing a complex rollback.")

        # Data Validation
        if not isinstance(operation, CadOperationType):
            logger.error(f"Invalid operation type: {operation}")
            raise ValueError("Operation must be a valid CadOperationType enum.")

        # Boundary checks for specific operations
        if operation == CadOperationType.EXTRUDE:
            if 'height' not in parameters or parameters['height'] <= 0:
                logger.error("Extrude operation requires positive 'height'.")
                raise ValueError("Extrude height must be positive.")

        if operation == CadOperationType.FILLET:
            if 'radius' not in parameters or parameters['radius'] <= 0:
                logger.error("Fillet operation requires positive 'radius'.")
                raise ValueError("Fillet radius must be positive.")

        # Create Action
        prev_id = self._action_history[-1].action_id if self._action_history else None
        
        action = FlutterAction(
            action_type=operation.value,
            payload=parameters,
            previous_action_id=prev_id
        )

        self._action_history.append(action)
        self._current_head_index += 1
        
        logger.info(f"Committed action {action.action_id}: {operation.value}")
        return action

    def time_travel_to(self, target_index: int) -> Dict[str, Any]:
        """
        Core Function 2: Traverses the history to a specific point (Time Slider logic).
        
        In a real scenario, this would trigger a regeneration of the CAD model 
        based on the sub-sequence of actions.
        
        Args:
            target_index (int): The index of the action to jump to.
            
        Returns:
            Dict[str, Any]: A summary of the state at that point in time.
        """
        if not (0 <= target_index < len(self._action_history)):
            logger.error(f"Index {target_index} out of bounds.")
            raise IndexError("Time travel index out of range.")

        self._current_head_index = target_index
        
        # Compile state summary up to this index
        state_snapshot = {
            "current_step": target_index + 1,
            "total_steps": len(self._action_history),
            "active_operations": [act.action_type for act in self._action_history[:target_index+1]]
        }
        
        logger.info(f"Traveled to step {target_index + 1}. State reconstructed.")
        return state_snapshot

    def create_branch_from_history(self, branch_name: str, from_index: int) -> str:
        """
        Helper Function: Creates a parallel design timeline (Non-linear exploration).
        
        Copies the history state up to 'from_index' into a new branch.
        
        Args:
            branch_name (str): Name of the new design branch.
            from_index (int): The history index to branch off from.
            
        Returns:
            str: The ID of the new branch.
        """
        if not branch_name:
            raise ValueError("Branch name cannot be empty.")
            
        if from_index < 0 or from_index >= len(self._action_history):
            raise IndexError("Cannot branch from non-existent history index.")
            
        branch_id = f"branch_{uuid.uuid4().hex[:8]}"
        
        # Deep copy actions up to the index
        branch_actions = [FlutterAction(**asdict(act)) for act in self._action_history[:from_index+1]]
        
        self._branches[branch_id] = branch_actions
        logger.info(f"Created branch '{branch_name}' (ID: {branch_id}) from step {from_index + 1}")
        
        return branch_id


# --- Dependency for dataclass ---
import time

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize System
    controller = DesignVersionController(project_id="proj_cad_99")
    
    try:
        # 1. Build a model (Linear timeline)
        print("--- Building Base Model ---")
        controller.commit_action(CadOperationType.SKETCH, {"profile": "rectangle", "plane": "XY"})
        controller.commit_action(CadOperationType.EXTRUDE, {"height": 50.0, "sketch_id": "sk_1"})
        controller.commit_action(CadOperationType.FILLET, {"radius": 5.0, "edge": "e_top"})
        
        # 2. Time Travel (Visualize growth)
        print("\n--- Time Travel Simulation ---")
        state_1 = controller.time_travel_to(0) # Back to Sketch
        print(f"Step 1 State: {state_1}")
        
        state_2 = controller.time_travel_to(1) # To Extrude
        print(f"Step 2 State: {state_2}")

        # 3. Create Branch for Non-linear exploration
        print("\n--- Branching ---")
        branch_id = controller.create_branch_from_history("Alternative_Handle", from_index=1)
        print(f"Created Branch ID: {branch_id}")
        
        # 4. Error Handling Demo
        print("\n--- Testing Error Handling ---")
        try:
            controller.commit_action(CadOperationType.EXTRUDE, {"height": -10})
        except ValueError as e:
            print(f"Caught expected error: {e}")

    except Exception as e:
        logger.critical(f"System crash: {e}", exc_info=True)