"""
Module: hierarchical_intent_hfsm.py
Author: Senior Python Engineer
Description: Implements a Hierarchical Finite State Machine (HFSM) for decomposing
             long-cycle complex intents into executable sub-states. This module
             specifically addresses the "Intent Checkpoint" mechanism to prevent
             error accumulation by validating alignment with human intent at
             critical execution junctures.

Domain: Control Theory / AGI Orchestration
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class ExecutionState(Enum):
    """Represents the status of a node in the HFSM."""
    PENDING = auto()
    RUNNING = auto()
    CHECKPOINT = auto()      # Awaiting intent validation
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class IntentContext:
    """Data structure holding the intent payload and metadata."""
    intent_id: str
    description: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validates the intent data structure."""
        if not self.intent_id or not self.description:
            logger.error("Validation Failed: Intent ID and Description are mandatory.")
            return False
        return True


@dataclass
class ExecutionResult:
    """Result object returned after state execution."""
    success: bool
    state_id: str
    output_data: Dict[str, Any]
    requires_validation: bool = False
    error_message: Optional[str] = None


class HFSMNode(ABC):
    """
    Abstract Base Class for a node in the Hierarchical Finite State Machine.
    It acts as both a State and a composite Machine (if it has children).
    """
    def __init__(self, name: str, is_checkpoint: bool = False):
        self.node_id = str(uuid.uuid4())[:8]
        self.name = name
        self.status = ExecutionState.PENDING
        self.is_checkpoint = is_checkpoint
        self.children: List['HFSMNode'] = []
        self.context: Optional[IntentContext] = None
        self._current_child_index = 0

    def add_child(self, child_node: 'HFSMNode') -> None:
        """Adds a sub-state to this node."""
        self.children.append(child_node)
        logger.debug(f"Node {self.name} added child: {child_node.name}")

    @abstractmethod
    def execute(self, shared_context: Dict[str, Any]) -> ExecutionResult:
        """
        Executes the logic of this state.
        If it has children, it delegates execution to them.
        """
        pass

    def validate_intent(self, result: ExecutionResult, human_validator: Callable) -> bool:
        """
        Core method: Intent Checkpoint Validation.
        If the state is marked as a checkpoint, invokes the validator.
        """
        if not self.is_checkpoint:
            return True

        logger.info(f"CHECKPOINT REACHED: {self.name}. Requesting intent alignment check.")
        try:
            # In a real AGI system, this would trigger a human-in-the-loop interface
            # or a high-level supervisor model.
            is_aligned = human_validator(self.context, result)
            
            if not is_aligned:
                logger.warning(f"Intent Drift Detected at {self.name}. Execution halted.")
                return False
            
            logger.info(f"Checkpoint {self.name} passed intent validation.")
            return True
        except Exception as e:
            logger.error(f"Error during intent validation: {str(e)}")
            return False


class CompositeState(HFSMNode):
    """
    A state that contains other states. It represents a complex sub-intent.
    Example: 'Develop Website' contains 'Design', 'Code', 'Deploy'.
    """
    def execute(self, shared_context: Dict[str, Any]) -> ExecutionResult:
        logger.info(f"Entering Composite State: {self.name}")
        self.status = ExecutionState.RUNNING
        
        if not self.children:
            self.status = ExecutionState.COMPLETED
            return ExecutionResult(True, self.node_id, {"info": "Leaf composite node finished"})

        while self._current_child_index < len(self.children):
            current_child = self.children[self._current_child_index]
            current_child.context = self.context
            
            logger.info(f"Executing child {current_child.name} (Index: {self._current_child_index})")
            result = current_child.execute(shared_context)
            
            if not result.success:
                self.status = ExecutionState.FAILED
                return result
            
            # If the child reached a checkpoint and requires validation
            if current_child.is_checkpoint:
                # Injected validator function for simulation
                if not self.validate_intent(result, self._mock_validator):
                    self.status = ExecutionState.FAILED
                    return ExecutionResult(False, self.node_id, {}, error="Intent validation failed")
            
            self._current_child_index += 1

        self.status = ExecutionState.COMPLETED
        return ExecutionResult(True, self.node_id, shared_context)

    def _mock_validator(self, context: Optional[IntentContext], result: ExecutionResult) -> bool:
        """Helper: Simulates a human or supervisor validation."""
        logger.info(f"-> Validating result for intent: {context.description if context else 'N/A'}")
        # Logic: If the output data contains 'error_flag', validation fails
        if result.output_data.get('error_flag'):
            return False
        return True


class PrimitiveState(HFSMNode):
    """
    A leaf state representing a specific action.
    Example: 'Buy Domain', 'Setup AWS'.
    """
    def __init__(self, name: str, action_logic: Callable, is_checkpoint: bool = False):
        super().__init__(name, is_checkpoint)
        self.action_logic = action_logic

    def execute(self, shared_context: Dict[str, Any]) -> ExecutionResult:
        logger.info(f"Executing Primitive Action: {self.name}")
        self.status = ExecutionState.RUNNING
        
        try:
            # Perform the action
            output = self.action_logic(shared_context)
            self.status = ExecutionState.COMPLETED
            
            return ExecutionResult(
                True, 
                self.node_id, 
                output, 
                requires_validation=self.is_checkpoint
            )
        except Exception as e:
            logger.error(f"Action {self.name} failed: {str(e)}")
            self.status = ExecutionState.FAILED
            return ExecutionResult(False, self.node_id, {}, error=str(e))


class HFSMController:
    """
    The main controller that builds and runs the Hierarchical FSM.
    """
    def __init__(self, root_intent: IntentContext):
        self.root_intent = root_intent
        self.root_node: Optional[HFSMNode] = None
        self.shared_memory: Dict[str, Any] = {}

    def build_graph(self, structure_definition: List[Dict[str, Any]]) -> HFSMNode:
        """
        Recursive helper to build the tree structure.
        Input Format: List of dicts {name, type, logic, is_checkpoint, children}
        """
        # This is a simplified builder for the example
        # In production, this would recursively parse the definition
        pass 


# --- Example Usage ---

def logic_design(data: Dict) -> Dict:
    """Mock logic for Design phase."""
    logger.info("...Designing website layout...")
    return {"design_status": "completed"}

def logic_code(data: Dict) -> Dict:
    """Mock logic for Coding phase."""
    logger.info("...Writing backend code...")
    return {"code_status": "completed"}

def logic_review(data: Dict) -> Dict:
    """Mock logic for Review phase (Checkpoint)."""
    logger.info("...Running automated tests...")
    # Simulating a potential issue that needs checking
    return {"tests_passed": True, "coverage": "85%"}

def logic_deploy(data: Dict) -> Dict:
    """Mock logic for Deployment."""
    logger.info("...Deploying to production...")
    return {"url": "https://my-agi-site.com"}

def main():
    """
    Demonstrates how to decompose 'Develop and Operate Website' into HFSM.
    """
    logger.info("Initializing HFSM System")
    
    # 1. Define Intent
    intent = IntentContext(
        intent_id="intent_001",
        description="Develop and Deploy Personal Blog",
        parameters={"stack": "Python/FastAPI"}
    )
    
    # 2. Construct HFSM Tree
    # Root: Develop Website
    # Children: Design -> Code -> Review (Checkpoint) -> Deploy
    
    # Leaf Nodes
    design_node = PrimitiveState("Design Phase", logic_design)
    code_node = PrimitiveState("Coding Phase", logic_code)
    review_node = PrimitiveState("Code Review", logic_review, is_checkpoint=True) # Checkpoint!
    deploy_node = PrimitiveState("Deployment", logic_deploy)
    
    # Sub-Composite (Optional, but showing hierarchy)
    dev_process = CompositeState("Development Cycle")
    dev_process.add_child(design_node)
    dev_process.add_child(code_node)
    dev_process.add_child(review_node)
    
    # Root Composite
    project_root = CompositeState("Project: Personal Blog")
    project_root.add_child(dev_process)
    project_root.add_child(deploy_node)
    
    # Link intent to root
    project_root.context = intent
    
    # 3. Run Execution
    logger.info("--- Starting Execution ---")
    shared_context = {}
    result = project_root.execute(shared_context)
    
    if result.success:
        logger.info(f"--- Execution Successful. Final State: {result.output_data} ---")
    else:
        logger.error(f"--- Execution Failed. Reason: {result.error_message} ---")

if __name__ == "__main__":
    main()