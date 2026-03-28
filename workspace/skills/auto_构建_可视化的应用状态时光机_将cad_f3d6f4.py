"""
Module: cad_state_time_machine.py

Description:
    Implements a prototype for a 'Visual Application State Time Machine' inspired by CAD Feature History Trees.
    
    This module translates the concept of parametric CAD modeling (features, rollback, regeneration)
    into the domain of application state management. Instead of mutating state directly, user actions
    or API calls generate 'Feature Nodes'. These nodes are stored in a linear Directed Acyclic Graph (DAG).
    
    Developers can 'Rollback' the state to a specific point, modify feature parameters (parametric editing),
    and 'Regenerate' the application state. This allows for runtime debugging, low-code logic adjustment,
    and detailed auditing of state transitions.

Domain: Cross-Domain (CAD Parametric Design + App State Management + Low-Code)

Author: AGI System
Version: 1.0.0
"""

import logging
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import copy

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class FeatureNode:
    """
    Represents a single atomic operation in the state history tree.
    Analagous to a 'Feature' in CAD (e.g., Extrude, Fillet).
    """
    id: str
    operation_type: str
    params: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    is_applied: bool = False

    def __post_init__(self):
        logger.debug(f"FeatureNode created: {self.id} ({self.operation_type})")

@dataclass
class AppState:
    """
    Represents the accumulated state of the application.
    Analagous to the 3D Model Body in CAD.
    """
    data: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = ""

    def update(self, key: str, value: Any):
        self.data[key] = value
        self.last_updated = datetime.utcnow().isoformat()

# --- Core Classes ---

class StateTimeMachine:
    """
    Manages the sequence of features and the current state of the application.
    Supports rollback, parametric updates, and state regeneration.
    """

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self.history: List[FeatureNode] = []
        self.current_state = AppState(data=initial_state or {})
        self.cursor_index: int = -1 # Points to the last applied feature
        self._operation_registry: Dict[str, Callable[[AppState, Dict], None]] = {}
        
        logger.info("StateTimeMachine initialized.")

    def register_operation(self, op_name: str, func: Callable[[AppState, Dict], None]):
        """Registers a function that modifies state."""
        self._operation_registry[op_name] = func
        logger.info(f"Operation registered: {op_name}")

    def add_feature(self, operation_type: str, params: Dict[str, Any], description: str = "") -> FeatureNode:
        """
        Core Function 1: Appends a new feature to the history and applies it.
        
        Args:
            operation_type: The type of operation (must be registered).
            params: Parameters for the operation.
            description: Human readable description.
        
        Returns:
            The created FeatureNode.
        
        Raises:
            ValueError: If operation_type is not registered.
        """
        if operation_type not in self._operation_registry:
            msg = f"Unknown operation type: {operation_type}"
            logger.error(msg)
            raise ValueError(msg)

        # If we are in a rolled-back state, new features usually truncate the "future" history
        # (Linear history model, similar to git rebase/reset)
        if self.cursor_index < len(self.history) - 1:
            logger.warning(f"History truncation: Removing {len(self.history) - 1 - self.cursor_index} future features.")
            self.history = self.history[:self.cursor_index + 1]

        feature_id = f"feat_{len(self.history) + 1}_{datetime.utcnow().timestamp()}"
        
        node = FeatureNode(
            id=feature_id,
            operation_type=operation_type,
            params=params,
            description=description
        )
        
        self.history.append(node)
        self._apply_feature(node)
        self.cursor_index = len(self.history) - 1
        
        logger.info(f"Feature added and applied: {node.id}")
        return node

    def _apply_feature(self, feature: FeatureNode):
        """Internal helper to execute the feature logic."""
        op_func = self._operation_registry[feature.operation_type]
        try:
            op_func(self.current_state, feature.params)
            feature.is_applied = True
        except Exception as e:
            logger.error(f"Error applying feature {feature.id}: {e}")
            feature.is_applied = False
            raise

    def rollback_to(self, target_index: int) -> bool:
        """
        Core Function 2: Rolls back the state to a specific point in history.
        
        Args:
            target_index: The index in the history list to roll back to.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self._validate_index(target_index):
            return False

        logger.info(f"Rolling back state to index {target_index}...")
        
        # Reset to base state (deep copy of initial empty state logic)
        # In a real CAD system, this regenerates from the base feature.
        base_data = {} # Assume empty base for this demo
        self.current_state = AppState(data=base_data)
        
        # Re-apply features up to target_index
        for i in range(target_index + 1):
            feature = self.history[i]
            self._apply_feature(feature)
            logger.debug(f"Re-applied {feature.id}")
            
        self.cursor_index = target_index
        logger.info("Rollback complete.")
        return True

    def modify_feature_params(self, feature_id: str, new_params: Dict[str, Any]) -> bool:
        """
        Aux Function: Modifies parameters of an existing feature and regenerates the state.
        (Parametric Editing).
        """
        feature_idx = -1
        for i, f in enumerate(self.history):
            if f.id == feature_id:
                feature_idx = i
                break
        
        if feature_idx == -1:
            logger.error(f"Feature {feature_id} not found.")
            return False
            
        # Update params
        self.history[feature_idx].params.update(new_params)
        logger.info(f"Updated params for {feature_id}. Regenerating...")
        
        # Regenerate from that point forward
        return self.rollback_to(len(self.history) - 1)

    def _validate_index(self, index: int) -> bool:
        """Boundary check for history indices."""
        if index < -1 or index >= len(self.history):
            logger.error(f"Index {index} out of bounds (History size: {len(self.history)})")
            return False
        return True

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Returns a deep copy of the current state."""
        return copy.deepcopy(self.current_state.data)

# --- Mock Operations for Demonstration ---

def op_add_user(state: AppState, params: Dict):
    """Mock operation: Adds a user object."""
    user_id = params.get('id')
    name = params.get('name', 'Unknown')
    if not user_id:
        raise ValueError("User ID required")
    
    state.update(f"user_{user_id}", {'id': user_id, 'name': name, 'role': 'guest'})
    logger.info(f" -> Op Executed: Added user {name}")

def op_grant_admin(state: AppState, params: Dict):
    """Mock operation: Modifies user role."""
    user_id = params.get('user_id')
    key = f"user_{user_id}"
    if key not in state.data:
        raise ValueError(f"User {user_id} does not exist")
    
    state.data[key]['role'] = 'admin'
    state.last_updated = datetime.utcnow().isoformat()
    logger.info(f" -> Op Executed: Granted admin to {user_id}")

def op_api_request_sim(state: AppState, params: Dict):
    """Mock operation: Simulates an API call modifying state."""
    endpoint = params.get('endpoint')
    data = params.get('data', {})
    state.update(f"cache_{endpoint}", data)
    logger.info(f" -> Op Executed: Cached data for {endpoint}")

# --- Main Execution / Usage Example ---

if __name__ == "__main__":
    # Setup
    machine = StateTimeMachine(initial_state={"meta": "v1.0"})
    machine.register_operation("ADD_USER", op_add_user)
    machine.register_operation("GRANT_ADMIN", op_grant_admin)
    machine.register_operation("API_CALL", op_api_request_sim)

    print("\n--- [1] Building Initial State (Features Creation) ---")
    # Feature 1: Add User
    f1 = machine.add_feature("ADD_USER", {"id": 101, "name": "Alice"}, "Create Alice")
    
    # Feature 2: Add Another User
    f2 = machine.add_feature("ADD_USER", {"id": 102, "name": "Bob"}, "Create Bob")
    
    # Feature 3: Promote Alice
    f3 = machine.add_feature("GRANT_ADMIN", {"user_id": 101}, "Promote Alice")
    
    print(f"Current State: {json.dumps(machine.get_state_snapshot(), indent=2)}")

    print("\n--- [2] Time Travel: Rolling Back to Index 1 (Before Promote) ---")
    # Rollback to when only Alice and Bob existed, Alice was not admin
    machine.rollback_to(1)
    print(f"State after rollback: {json.dumps(machine.get_state_snapshot(), indent=2)}")
    # Check Alice role
    print(f"Alice Role: {machine.current_state.data['user_101']['role']}") # Should be 'guest'

    print("\n--- [3] Parametric Modification: Changing Bob's Name ---")
    # We are at index 1. Let's modify F2 (Bob) even though we are "in the past".
    # In a linear model, modifying a past node usually requires regeneration up to current cursor.
    # But here we modify the node definition itself.
    
    # Let's fast forward to end first to show full regeneration
    machine.rollback_to(2) 
    
    # Now modify Feature 2 (Bob) parameters
    machine.modify_feature_params(f2.id, {"id": 102, "name": "Robert"})
    
    print(f"State after parametric update: {json.dumps(machine.get_state_snapshot(), indent=2)}")
    print(f"Bob's Name: {machine.current_state.data['user_102']['name']}")

    print("\n--- [4] Error Handling: Invalid Operation ---")
    try:
        machine.add_feature("DELETE_EVERYTHING", {}) # Unregistered op
    except ValueError as e:
        print(f"Caught expected error: {e}")
