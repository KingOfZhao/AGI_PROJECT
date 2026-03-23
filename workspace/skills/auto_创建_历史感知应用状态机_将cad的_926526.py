"""
Module: cad_flutter_state_machine.py

Description:
    Implements a 'History-Aware Application State Machine' (HAM).
    This system integrates CAD-like 'History Tree (Undo/Redo/Checkout)' mechanisms
    into state management logic (intended to drive a Flutter frontend via an API).

    Unlike simple linear undo/redo, this system allows users to navigate to any
    historical modification node (Snapshot), modify parameters (creating a new branch),
    and re-calculate subsequent states. This is ideal for complex form wizards,
    game level editors, or collaborative document processing.

    Data Flow:
    Input -> Command Execution -> State Snapshot -> Tree Node Creation
    API Output -> JSON serialization of Tree & State for Flutter consumption.

Author: AGI System
Version: 1.0.0
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from copy import deepcopy

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Custom Exceptions ---

class StateMachineError(Exception):
    """Base exception for the State Machine."""
    pass

class NodeNotFoundError(StateMachineError):
    """Raised when a target node ID does not exist in the tree."""
    pass

class InvalidActionError(StateMachineError):
    """Raised when an action validation fails."""
    pass

# --- Data Structures ---

@dataclass
class Action:
    """
    Represents a user action or command that triggers a state change.
    Similar to a CAD command.
    """
    action_type: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def validate(self) -> bool:
        """Basic validation to ensure action structure integrity."""
        if not self.action_type or not isinstance(self.action_type, str):
            return False
        if not isinstance(self.payload, dict):
            return False
        return True

@dataclass
class StateNode:
    """
    Represents a node in the State Tree.
    Contains the snapshot of the application state at a specific point in time.
    """
    node_id: str
    state_snapshot: Dict[str, Any]  # The actual application state
    parent_id: Optional[str]
    action: Action                  # The action that led to this state
    children: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_json(self) -> str:
        """Serializes the node to JSON for API transmission."""
        return json.dumps(asdict(self))

# --- Core Engine ---

class CADStateMachine:
    """
    The core state machine engine implementing the CAD-history-tree logic.
    """

    def __init__(self, initial_state: Dict[str, Any], reducer: Callable[[Dict, Action], Dict]):
        """
        Initializes the state machine with a root node.
        
        Args:
            initial_state (Dict): The starting state of the application.
            reducer (Callable): A function (state, action) -> new_state that handles business logic.
        """
        self.root_id = "root_node_" + str(uuid.uuid4())
        self.nodes: Dict[str, StateNode] = {}
        self.reducer = reducer
        self.current_node_id: str = ""

        # Create Root Node
        root_action = Action(action_type="INIT", payload={})
        root_node = StateNode(
            node_id=self.root_id,
            state_snapshot=deepcopy(initial_state),
            parent_id=None,
            action=root_action
        )
        self.nodes[self.root_id] = root_node
        self.current_node_id = self.root_id
        logger.info(f"State Machine initialized with Root ID: {self.root_id}")

    def _validate_state_integrity(self, state: Dict[str, Any]) -> bool:
        """
        Helper: Validates the structure of the state data.
        Ensures no corruption occurred during reduction.
        """
        if not isinstance(state, dict):
            return False
        # Example constraint: State must always have a 'version' key
        if 'version' not in state:
            logger.warning("State integrity check failed: missing 'version'")
            return False
        return True

    def execute_action(self, action: Action) -> StateNode:
        """
        Core Function 1: Executes an action based on the current cursor position.
        Creates a new node and attaches it to the current node.
        
        Args:
            action (Action): The action to execute.
            
        Returns:
            StateNode: The newly created state node.
            
        Raises:
            InvalidActionError: If action validation fails.
        """
        if not action.validate():
            raise InvalidActionError(f"Invalid action format: {action}")

        current_node = self.get_node(self.current_node_id)
        
        logger.info(f"Executing action '{action.action_type}' on Node {current_node.node_id}")
        
        try:
            # Calculate new state using the reducer
            new_state = self.reducer(current_node.state_snapshot, action)
            
            if not self._validate_state_integrity(new_state):
                raise StateMachineError("Resulting state failed integrity check.")

            new_node_id = "node_" + str(uuid.uuid4())
            new_node = StateNode(
                node_id=new_node_id,
                state_snapshot=new_state,
                parent_id=current_node.node_id,
                action=action
            )

            # Update tree structure
            current_node.children.append(new_node_id)
            self.nodes[new_node_id] = new_node
            self.current_node_id = new_node_id

            logger.info(f"New State Node created: {new_node_id}")
            return new_node

        except Exception as e:
            logger.error(f"Error executing action {action.action_id}: {e}")
            raise StateMachineError(f"Reducer failed: {e}")

    def checkout_node(self, target_node_id: str) -> Dict[str, Any]:
        """
        Core Function 2: Moves the cursor to a specific historical node (Time Travel).
        Does not delete future history, just moves the pointer (CAD style).
        
        Args:
            target_node_id (str): The ID of the node to navigate to.
            
        Returns:
            Dict[str, Any]: The state snapshot of the target node.
            
        Raises:
            NodeNotFoundError: If target ID is invalid.
        """
        logger.info(f"Attempting to checkout node: {target_node_id}")
        
        if target_node_id not in self.nodes:
            raise NodeNotFoundError(f"Node {target_node_id} not found in history.")
            
        self.current_node_id = target_node_id
        node = self.nodes[target_node_id]
        
        logger.info(f"Current cursor moved to Node {target_node_id} (Action: {node.action.action_type})")
        return node.state_snapshot

    def get_node(self, node_id: str) -> StateNode:
        """Helper: Safely retrieves a node."""
        if node_id not in self.nodes:
            raise NodeNotFoundError(f"Node {node_id} missing.")
        return self.nodes[node_id]

    def get_history_tree_metadata(self) -> List[Dict]:
        """
        Generates a simplified tree structure for the Flutter Frontend to render.
        Returns a list of nodes with essential info (id, parent, name, active).
        """
        tree_data = []
        for node_id, node in self.nodes.items():
            tree_data.append({
                "id": node.node_id,
                "parent": node.parent_id,
                "action_type": node.action.action_type,
                "is_current": node.node_id == self.current_node_id,
                "timestamp": node.created_at
            })
        return tree_data

# --- Example Usage & Mock Logic ---

def example_reducer(state: Dict[str, Any], action: Action) -> Dict[str, Any]:
    """
    Mock reducer logic (Pure function).
    In a real app, this would contain complex business logic.
    """
    new_state = deepcopy(state)
    
    if action.action_type == "ADD_SHAPE":
        shape = action.payload.get("shape")
        x = action.payload.get("x", 0)
        y = action.payload.get("y", 0)
        new_state["shapes"].append({"type": shape, "x": x, "y": y, "id": action.action_id})
        new_state["version"] += 1
        
    elif action.action_type == "UPDATE_USER":
        new_state["user"]["name"] = action.payload.get("name", "Unknown")
        new_state["version"] += 1
        
    return new_state

if __name__ == "__main__":
    # 1. Initialize System
    initial_app_state = {
        "version": 1,
        "shapes": [],
        "user": {"name": "Guest"}
    }
    
    machine = CADStateMachine(initial_app_state, reducer=example_reducer)
    
    # 2. Execute a sequence of actions
    act1 = Action("ADD_SHAPE", {"shape": "Circle", "x": 10, "y": 10})
    node1 = machine.execute_action(act1)
    
    act2 = Action("ADD_SHAPE", {"shape": "Square", "x": 50, "y": 50})
    node2 = machine.execute_action(act2)
    
    act3 = Action("UPDATE_USER", {"name": "Alice"})
    node3 = machine.execute_action(act3)
    
    print(f"Current State Version: {machine.get_node(machine.current_node_id).state_snapshot['version']}")
    
    # 3. CAD Feature: Time Travel (Undo to Node 1)
    print("\n--- Time Traveling to Node 1 (Circle added) ---")
    past_state = machine.checkout_node(node1.node_id)
    print(f"State after checkout: {past_state['shapes']}") 
    # Notice: 'Square' and 'Alice' are still in the tree memory, just not the active branch.
    
    # 4. CAD Feature: Branching History
    # From Node 1 (Circle), we add a Triangle instead of a Square.
    print("\n--- Creating Alternate Future from Node 1 ---")
    act4 = Action("ADD_SHAPE", {"shape": "Triangle", "x": 100, "y": 100})
    node4 = machine.execute_action(act4) # This attaches to Node 1
    
    print(f"New Current Node ID: {machine.current_node_id}")
    
    # 5. Output Tree Structure for Flutter
    print("\n--- History Tree Metadata (For Flutter Widget) ---")
    tree_meta = machine.get_history_tree_metadata()
    for item in tree_meta:
        prefix = "-> " if item['is_current'] else "   "
        print(f"{prefix}Node: {item['id'][:8]}... | Action: {item['action_type']} | Parent: {str(item['parent'])[:8] if item['parent'] else 'None'}")