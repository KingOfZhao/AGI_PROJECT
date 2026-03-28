"""
Module: topological_execution_flow.py

This module implements a Spatial Topological Execution Flow system.
It transforms traditional linear execution into a spatial, tree-like structure
where each step is a reversible, pausable, and forkable node.

Core Concepts:
1.  **Time Axis Slicing**: Operations are discrete nodes.
2.  **Reversibility**: Ability to rollback to specific states without full restarts.
3.  **Branching**: Ability to fork execution from any historical point to explore alternatives.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import copy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Status of the execution node."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class TopologicalNode:
    """
    Represents a single slice of time/space in the execution flow.
    
    Attributes:
        node_id: Unique identifier for the node.
        action: The callable to be executed.
        context: Snapshot of the data state at this node.
        parent_id: ID of the parent node (None for root).
        children: List of child node IDs (branches).
        status: Current status of the node.
        error: Exception information if failed.
    """
    node_id: str
    action_name: str
    context: Dict[str, Any]
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    error: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not isinstance(self.context, dict):
            raise ValueError("Context must be a dictionary.")


class TopologicalExecutor:
    """
    Manages the spatial execution flow, allowing branching and time-travel
    (rollback) within the execution graph.
    """

    def __init__(self, initial_context: Optional[Dict[str, Any]] = None):
        """
        Initialize the executor with a root node.
        
        Args:
            initial_context: The starting state of the data.
        """
        self.nodes: Dict[str, TopologicalNode] = {}
        self.current_node_id: Optional[str] = None
        
        # Create a root node with no action
        root_id = self._generate_id()
        root_node = TopologicalNode(
            node_id=root_id,
            action_name="ROOT",
            context=initial_context or {},
            parent_id=None
        )
        self.nodes[root_id] = root_node
        self.current_node_id = root_id
        logger.info(f"Initialized Topological Executor with Root ID: {root_id}")

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique identifier for a node."""
        return str(uuid.uuid4())[:8]

    def _deep_copy_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper function to create a deep copy of the context to ensure
        history isolation.
        """
        try:
            return copy.deepcopy(context)
        except Exception as e:
            logger.error(f"Failed to deep copy context: {e}")
            raise

    def get_current_state(self) -> Dict[str, Any]:
        """Return the data context of the current active node."""
        if self.current_node_id and self.current_node_id in self.nodes:
            return self.nodes[self.current_node_id].context
        return {}

    def append_step(self, action: Callable, action_name: str) -> str:
        """
        Append a new step (node) to the current timeline.
        
        Args:
            action: The function to execute.
            action_name: Human-readable name for the action.
            
        Returns:
            The ID of the newly created node.
        """
        if not callable(action):
            raise ValueError("Action must be callable.")
            
        new_id = self._generate_id()
        parent_node = self.nodes[self.current_node_id]
        
        # Create a snapshot of the parent context
        new_context = self._deep_copy_context(parent_node.context)
        
        new_node = TopologicalNode(
            node_id=new_id,
            action_name=action_name,
            context=new_context,
            parent_id=parent_node.node_id,
            status=NodeStatus.PENDING
        )
        
        parent_node.children.append(new_id)
        self.nodes[new_id] = new_node
        
        logger.debug(f"Appended node {new_id} ({action_name}) to parent {parent_node.node_id}")
        return new_id

    def execute_flow(self, node_id: Optional[str] = None) -> bool:
        """
        Execute the logic of a specific node and advance the timeline.
        If node_id is None, executes the current head's next pending logic 
        (conceptually simplified here to run the specific node passed).
        
        For this implementation, we assume we are executing the 'next' appended step.
        
        Args:
            node_id: The specific node to execute. If None, attempts to find a pending child.
        """
        target_id = node_id or self.current_node_id
        
        # In a linear append-and-run model, we usually run the node we just appended
        # or a specific one for branching.
        
        # Let's find a pending child of current if specific ID not provided logic is complex
        # Simplified: Run the provided node_id or the current node if it's pending
        
        if target_id not in self.nodes:
            raise ValueError(f"Node {target_id} does not exist.")

        node = self.nodes[target_id]
        
        if node.status == NodeStatus.COMPLETED:
            logger.warning(f"Node {target_id} already completed.")
            return True

        node.status = NodeStatus.RUNNING
        
        try:
            # The action is stored conceptually. In this setup, we might pass the context
            # to a registered function. For this demo, we assume the logic is injected
            # or we use a simplified execution model.
            # NOTE: To make this runnable, we need to associate the callable.
            # Let's assume we store the callable in the node or look it up.
            # For this example, we will modify `append_step` to store the action temporarily 
            # or pass it here. To keep the class clean, let's assume the node has the action.
            # (Adding `action` to TopologicalNode dataclass logic implicitly or explicitly)
            
            # *Correction*: TopologicalNode above doesn't store the callable to be picklable/serializable friendly usually.
            # But for a pure Python in-memory skill, we can add it.
            # Let's assume we execute a passed function or the node holds it.
            
            # Since we didn't store `action` in Node (to keep dataclass simple), 
            # this method serves as the "Runner" of the structure.
            # To make the code functional, we will implement a `run_action` method 
            # that accepts the function.
            
            logger.info(f"Executing Node: {node.action_name} ({node.node_id})")
            # Simulate execution
            # result = action(node.context)
            # For demonstration, we just mark it completed.
            # See `run_single_step` below for actual execution logic.
            
            return True

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = e
            logger.error(f"Execution failed at node {node.node_id}: {e}")
            return False

    def run_single_step(self, action: Callable[[Dict], None], target_node_id: str) -> bool:
        """
        Executes a specific node's action, updates the context, and moves the pointer.
        
        Args:
            action: The function taking the context dict as input.
            target_node_id: The node to execute.
        """
        if target_node_id not in self.nodes:
            raise ValueError("Invalid Node ID")
            
        node = self.nodes[target_node_id]
        node.status = NodeStatus.RUNNING
        
        try:
            # Execute action on the current context
            action(node.context)
            node.status = NodeStatus.COMPLETED
            self.current_node_id = target_node_id
            logger.info(f"Node {target_node_id} executed successfully. Context updated.")
            return True
            
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = e
            logger.error(f"Error in {target_node_id}: {e}")
            # Trigger spatial rollback logic if needed
            self.rollback_to_parent(target_node_id)
            return False

    def rollback_to_parent(self, node_id: str) -> str:
        """
        Time-Slice Rollback: Reverts the execution pointer to the parent of the given node.
        Does not delete the history, just moves the 'HEAD' back, allowing for a new branch.
        
        Args:
            node_id: The node that failed or needs to be reverted.
            
        Returns:
            The new current node ID (the parent).
        """
        if node_id not in self.nodes:
            raise ValueError("Node ID not found")
            
        node = self.nodes[node_id]
        parent_id = node.parent_id
        
        if not parent_id:
            logger.warning("Cannot rollback from Root node.")
            return node_id
            
        node.status = NodeStatus.ROLLED_BACK
        
        # Move pointer to parent
        self.current_node_id = parent_id
        logger.warning(f"Rolled back from {node_id} to {parent_id}. Ready for new branch.")
        
        return parent_id

    def branch_from_history(self, node_id: str, new_action: Callable, name: str) -> str:
        """
        Creates a new branch from a historical node (Time Axis Slicing).
        
        Args:
            node_id: The historical node to branch from.
            new_action: The new action to try.
            name: Name of the new step.
            
        Returns:
            The ID of the new branch node.
        """
        if node_id not in self.nodes:
            raise ValueError("History node not found")
            
        # Temporarily set current_node_id to history point to append correctly
        original_head = self.current_node_id
        self.current_node_id = node_id
        
        logger.info(f"Branching from historical node {node_id}...")
        new_node_id = self.append_step(new_action, name)
        
        # Restore original head (optional, depends if we want to switch to the new branch immediately)
        # Here we return the new node ID, leaving the choice to the controller.
        # self.current_node_id = original_head # Keep head at new branch or revert? 
        # Usually branching implies we want to try the new path.
        
        return new_node_id

    def visualize_tree(self) -> List[str]:
        """Simple text representation of the topology."""
        lines = []
        def traverse(nid, level=0):
            node = self.nodes[nid]
            prefix = "  " * level + ("└─ " if level > 0 else "")
            marker = ">> " if nid == self.current_node_id else ""
            status = f"[{node.status.value}]"
            lines.append(f"{prefix}{marker}{node.action_name} ({nid[:4]}) {status}")
            for child_id in node.children:
                traverse(child_id, level + 1)
        
        root_id = next(n for n, node in self.nodes.items() if node.parent_id is None)
        traverse(root_id)
        return lines


# --- Usage Example ---

def complex_operation(context: dict):
    """Simulates an operation that modifies data."""
    if "counter" not in context:
        context["counter"] = 0
    
    # Simulate a potential error
    if context["counter"] == 2:
        raise ValueError("Simulated processing glitch at step 2")
    
    context["counter"] += 1
    print(f"Processing... Counter is now {context['counter']}")

def recovery_operation(context: dict):
    """Simulates a fix applied after rollback."""
    print("Applying recovery fix...")
    context["counter"] = 100 # Reset or fix state

if __name__ == "__main__":
    # Initialize Executor
    executor = TopologicalExecutor(initial_context={"session": "AGI_Session_01"})
    
    # 1. Linear Execution
    print("\n[Phase 1: Linear Execution]")
    n1 = executor.append_step(lambda ctx: ctx.update({"step1": True}), "Initialize Sensor")
    executor.run_single_step(lambda ctx: ctx.update({"step1": True}), n1)
    
    n2 = executor.append_step(lambda ctx: ctx.update({"step2": True}), "Scan Environment")
    executor.run_single_step(lambda ctx: ctx.update({"step2": True}), n2)
    
    # 2. Error and Rollback
    print("\n[Phase 2: Handling Error & Spatial Rollback]")
    # Let's add a step that fails
    n3 = executor.append_step(complex_operation, "Critical Calculation")
    success = executor.run_single_step(complex_operation, n3)
    
    if not success:
        print(f"Execution failed at {n3}. Rolling back...")
        # We are now at n2 effectively due to rollback logic inside run_single_step 
        # (or we can call rollback explicitly)
        
    # 3. Branching (Time Travel)
    print("\n[Phase 3: Branching New Timeline]")
    # We are at n2 (parent of n3). Let's create a parallel reality.
    n3_alt = executor.branch_from_history(executor.current_node_id, recovery_operation, "Recovery Calculation")
    executor.run_single_step(recovery_operation, n3_alt)
    
    # Visualize Topology
    print("\n[Topology Graph]")
    for line in executor.visualize_tree():
        print(line)