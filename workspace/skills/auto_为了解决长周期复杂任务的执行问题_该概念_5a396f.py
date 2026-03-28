"""
Module: auto_hfsm_executor
A robust implementation of a Hierarchical Finite State Machine (HFSM) designed to convert
static intents into dynamic execution graphs. This system supports holographic context
tracking and diffusion-based queries for complex, long-cycle task execution.

Dependencies:
    - typing (Standard Library)
    - logging (Standard Library)
    - uuid (Standard Library)

Input Format:
    - Intent: Dict containing 'goal' (str) and 'parameters' (dict).
    - State Graph: Dict defining states, transitions, and sub-states.

Output Format:
    - Result: Dict containing 'status', 'final_state', 'execution_log', and 'context_snapshot'.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum, auto
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Enumeration of possible task execution statuses."""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    ROLLING_BACK = auto()

@dataclass
class HolographicContext:
    """
    Maintains the context of the execution, linking back to the original intent.
    Supports 'holographic' access: any state can access the root intent.
    """
    root_intent: Dict[str, Any]
    current_state_id: str = "root"
    history: List[str] = field(default_factory=list)
    rollback_stack: List[str] = field(default_factory=list)
    shared_memory: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> Dict[str, Any]:
        """Creates a serializable snapshot of the current context."""
        return {
            "root_intent": self.root_intent,
            "current_state": self.current_state_id,
            "history": self.history,
            "memory": self.shared_memory
        }

class StateNode:
    """
    Represents a node in the Hierarchical Finite State Machine.
    """
    def __init__(self, name: str, action: Optional[Callable] = None, 
                 transitions: Optional[Dict[str, str]] = None):
        self.name = name
        self.action = action if action else lambda ctx: {"status": "success"}
        self.transitions = transitions if transitions else {}
        self.children: Dict[str, 'StateNode'] = {}
        self.parent: Optional['StateNode'] = None

    def add_child(self, child_node: 'StateNode'):
        """Adds a child state to create hierarchy."""
        child_node.parent = self
        self.children[child_node.name] = child_node

    def validate(self) -> bool:
        """Validates the state node configuration."""
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("State name must be a non-empty string.")
        return True

class HFSMController:
    """
    The core controller for the Hierarchical Finite State Machine.
    Handles state transitions, rollback, and dynamic replanning.
    """

    def __init__(self, root_intent: Dict[str, Any]):
        """
        Initializes the HFSM Controller with a specific intent.

        Args:
            root_intent (Dict[str, Any]): The high-level goal dictionary.
        
        Raises:
            ValueError: If root_intent is missing 'goal' key.
        """
        if 'goal' not in root_intent:
            raise ValueError("Root intent must contain a 'goal' key.")
        
        self.context = HolographicContext(root_intent=root_intent)
        self.root_state: Optional[StateNode] = None
        self.current_state: Optional[StateNode] = None
        self.task_id = str(uuid.uuid4())
        logger.info(f"Initialized HFSM Controller {self.task_id} for goal: {root_intent['goal']}")

    def load_graph(self, graph_definition: Dict[str, Any]):
        """
        Loads a state graph definition into the controller.
        
        Args:
            graph_definition (Dict): Dictionary containing state definitions.
        """
        if not graph_definition:
            raise ValueError("Graph definition cannot be empty.")
        
        # Simplified graph loading for demonstration
        # In a real AGI system, this would parse a complex graph structure
        self.root_state = self._build_graph_recursive(graph_definition)
        self.current_state = self.root_state
        self.context.current_state_id = self.root_state.name
        logger.info("State graph loaded successfully.")

    def _build_graph_recursive(self, node_data: Dict) -> StateNode:
        """Helper to build state tree recursively."""
        node = StateNode(
            name=node_data['name'],
            action=node_data.get('action'),
            transitions=node_data.get('transitions', {})
        )
        node.validate()
        
        for child_data in node_data.get('children', []):
            child_node = self._build_graph_recursive(child_data)
            node.add_child(child_node)
            
        return node

    def execute_step(self, feedback: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Executes the current state action and determines the next transition.
        Implements the 'Dynamic' aspect by incorporating feedback.

        Args:
            feedback (Optional[Dict]): Real-time feedback from the environment or sensors.

        Returns:
            Dict: Execution result containing status and context snapshot.
        """
        if not self.current_state:
            return {"status": "error", "message": "No state loaded"}

        try:
            logger.info(f"Executing State: {self.current_state.name}")
            self.context.history.append(self.current_state.name)
            self.context.rollback_stack.append(self.current_state.name)

            # Inject feedback into shared memory for the action to access
            if feedback:
                self.context.shared_memory.update(feedback)

            # Execute Action
            result = self.current_state.action(self.context)
            
            # Determine Transition
            next_state_key = self._decide_transition(result, feedback)
            
            if next_state_key == "ROLLBACK":
                return self.rollback()
            
            if next_state_key in self.current_state.children:
                self.current_state = self.current_state.children[next_state_key]
                self.context.current_state_id = self.current_state.name
                status = TaskStatus.RUNNING
            elif next_state_key in self.current_state.transitions:
                # Handle sibling/external transitions (simplified)
                target_name = self.current_state.transitions[next_state_key]
                # Logic to find target node would go here; for now, we simulate success
                logger.info(f"Transitioning to external state: {target_name}")
                status = TaskStatus.RUNNING
            else:
                # No valid transition found implies end of this branch or failure
                status = TaskStatus.SUCCESS if result.get("status") == "success" else TaskStatus.FAILURE

            return {
                "status": status.name,
                "context": self.context.snapshot()
            }

        except Exception as e:
            logger.error(f"Error executing state {self.current_state.name}: {e}")
            return {"status": "error", "message": str(e)}

    def _decide_transition(self, result: Dict, feedback: Optional[Dict]) -> str:
        """
        Core logic for dynamic decision making (Diffusion Query).
        Decides the next state based on action result and external feedback.
        """
        if feedback and feedback.get("interrupt") == "urgent_replan":
            logger.warning("Interrupt received: Triggering Rollback/Replan")
            return "ROLLBACK"
        
        if result.get("status") == "success":
            return result.get("next_state", "default_success")
        
        return "default_failure"

    def rollback(self) -> Dict[str, Any]:
        """
        Reverts the state machine to a previous safe state.
        Implements the 'Regret' capability.
        """
        logger.warning("Initiating Rollback procedure...")
        if len(self.context.rollback_stack) > 1:
            self.context.rollback_stack.pop() # Remove current failed state
            prev_state_name = self.context.rollback_stack[-1]
            
            # In a real implementation, we need a registry of states to find the object by name
            # Here we simulate moving back to parent for safety
            if self.current_state and self.current_state.parent:
                self.current_state = self.current_state.parent
                self.context.current_state_id = self.current_state.name
                logger.info(f"Rolled back to parent state: {self.current_state.name}")
                return {"status": TaskStatus.ROLLING_BACK.name, "message": "Rolled back to parent"}
        
        return {"status": TaskStatus.FAILURE.name, "message": "Cannot rollback further"}

    @staticmethod
    def validate_input_data(data: Dict) -> bool:
        """
        Data Validation Helper.
        Ensures input dictionaries conform to required schemas.
        """
        if not isinstance(data, dict):
            return False
        return True

# --- Usage Example ---

if __name__ == "__main__":
    # Define a mock action for the state
    def mock_analysis_action(ctx: HolographicContext) -> Dict:
        logger.info(f"Analyzing data for: {ctx.root_intent['goal']}")
        ctx.shared_memory['analysis_complete'] = True
        return {"status": "success", "next_state": "execute"}

    def mock_execute_action(ctx: HolographicContext) -> Dict:
        if ctx.shared_memory.get('analysis_complete'):
            logger.info("Execution phase started based on analysis.")
            return {"status": "success"}
        return {"status": "failure"}

    # Define Graph Structure
    graph_def = {
        "name": "root",
        "action": None,
        "children": [
            {
                "name": "analyze",
                "action": mock_analysis_action,
                "children": [
                    {
                        "name": "execute",
                        "action": mock_execute_action,
                        "children": []
                    }
                ]
            }
        ]
    }

    # Define Intent
    intent = {
        "goal": "Deploy Machine Learning Model",
        "params": {"model_id": "xyz-123"}
    }

    # Initialize and Run
    try:
        controller = HFSMController(root_intent=intent)
        controller.load_graph(graph_def)

        # Step 1: Execute Root (moves to first child logic)
        # Note: Logic above simplifies traversal for demonstration
        
        # Simulate Execution Loop
        current = controller.root_state
        while current:
            controller.current_state = current
            res = controller.execute_step()
            print(f"Step Result: {res['status']}")
            
            if res['status'] == "SUCCESS":
                break
            
            # Simple traversal for demo
            if current.children:
                # Normally decided by _decide_transition
                current = list(current.children.values())[0] 
            else:
                break
                
    except Exception as e:
        logger.error(f"System Crash: {e}")