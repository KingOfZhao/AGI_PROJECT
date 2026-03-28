"""
Module: hierarchical_goal_decomposer
This module provides a robust framework for decomposing high-level, ambiguous goals
(e.g., 'Solve Global Warming') into atomic, executable nodes using a Top-Down approach.
It focuses on maintaining context consistency, preventing semantic drift, and ensuring
the resulting directed acyclic graph (DAG) remains logically valid.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import uuid
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeState(Enum):
    """Enumeration of possible states for a task node."""
    PENDING = "pending"
    ATOMIC = "atomic"  # Ready for execution
    DECOMPOSED = "decomposed"
    FAILED = "failed"


@dataclass
class GoalNode:
    """
    Represents a node in the goal decomposition graph.
    
    Attributes:
        id: Unique identifier for the node.
        description: Human-readable description of the sub-goal.
        parent_id: ID of the parent node (None for root).
        context_vector: A simplified representation of semantic context (float list).
        state: Current state of the node.
        children: List of child node IDs.
    """
    id: str
    description: str
    parent_id: Optional[str] = None
    context_vector: List[float] = field(default_factory=list)
    state: NodeState = NodeState.PENDING
    children: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, GoalNode):
            return False
        return self.id == other.id


def validate_context(context: List[float]) -> bool:
    """
    Validates the semantic context vector.
    
    Args:
        context: A list of floats representing the node's semantic context.
        
    Returns:
        True if valid, raises ValueError otherwise.
    """
    if not isinstance(context, list):
        raise ValueError("Context must be a list.")
    if not all(isinstance(x, (float, int)) for x in context):
        raise ValueError("Context vector must contain only numbers.")
    return True


def check_semantic_drift(
    parent_context: List[float], 
    child_context: List[float], 
    threshold: float = 0.15
) -> bool:
    """
    Auxiliary Function: Calculates semantic drift between parent and child.
    Uses a simplified Euclidean distance check for demonstration.
    
    Args:
        parent_context: Context vector of the parent node.
        child_context: Context vector of the generated child node.
        threshold: Maximum allowed deviation (0.0 to 1.0 normalized).
        
    Returns:
        True if drift is within acceptable limits, False otherwise.
    """
    if not parent_context or not child_context:
        return True  # Skip check if context is empty

    # Normalize lengths by padding with zeros if necessary
    max_len = max(len(parent_context), len(child_context))
    p_vec = parent_context + [0.0] * (max_len - len(parent_context))
    c_vec = child_context + [0.0] * (max_len - len(child_context))
    
    # Calculate Euclidean distance
    distance = sum((p - c) ** 2 for p, c in zip(p_vec, c_vec)) ** 0.5
    
    # Normalize distance (heuristic)
    normalized_drift = distance / (max_len * 10) # Arbitrary scaling factor
    
    if normalized_drift > threshold:
        logger.warning(f"Semantic drift detected: {normalized_drift:.4f} > {threshold}")
        return False
    return True


class HierarchicalGoalDecomposer:
    """
    Core class responsible for decomposing a macro goal into an executable DAG.
    Handles graph construction, loop detection, and context inheritance.
    """
    
    def __init__(self, root_goal: str, root_context: Optional[List[float]] = None):
        """
        Initializes the decomposer with a root goal.
        
        Args:
            root_goal: The high-level ambiguous goal string.
            root_context: Initial semantic context (optional).
        """
        self.graph: Dict[str, GoalNode] = {}
        self.root_id = str(uuid.uuid4())
        
        # Initialize Root Node
        self.graph[self.root_id] = GoalNode(
            id=self.root_id,
            description=root_goal,
            context_vector=root_context or []
        )
        logger.info(f"Initialized decomposition for goal: '{root_goal}'")

    def _detect_logic_loop(self, current_id: str, visited: Set[str]) -> bool:
        """
        Checks for circular dependencies in the graph structure.
        
        Args:
            current_id: The node ID currently being checked.
            visited: Set of visited node IDs in the current traversal path.
            
        Returns:
            True if a loop is detected, False otherwise.
        """
        if current_id in visited:
            logger.error(f"Logical loop detected at node {current_id}")
            return True
        
        node = self.graph.get(current_id)
        if not node:
            return False
            
        visited.add(current_id)
        for child_id in node.children:
            if self._detect_logic_loop(child_id, visited.copy()): # Pass a copy for path tracking
                return True
        return False

    def decompose_node(
        self, 
        parent_id: str, 
        sub_tasks: List[Dict[str, str]], 
        atomic_threshold: int = 3
    ) -> List[str]:
        """
        Core Function 1: Decomposes a specific parent node into sub-tasks.
        
        Args:
            parent_id: The ID of the node to decompose.
            sub_tasks: List of dictionaries containing {'description': str, 'context': list}.
            atomic_threshold: Depth or complexity limit to force atomicity.
            
        Returns:
            List of created child node IDs.
            
        Raises:
            ValueError: If parent does not exist or semantic drift is detected.
            RuntimeError: If decomposition creates a logical loop.
        """
        if parent_id not in self.graph:
            raise ValueError(f"Parent node {parent_id} not found in graph.")
            
        parent_node = self.graph[parent_id]
        created_ids = []
        
        logger.info(f"Decomposing node {parent_id} ('{parent_node.description[:20]}...')")
        
        for task_data in sub_tasks:
            desc = task_data.get("description", "")
            child_context = task_data.get("context", parent_node.context_vector) # Inherit if not provided
            
            # 1. Context Validation
            if not check_semantic_drift(parent_node.context_vector, child_context):
                raise ValueError(f"Semantic drift too high for sub-task: {desc}")

            # 2. Node Creation
            new_id = str(uuid.uuid4())
            new_node = GoalNode(
                id=new_id,
                description=desc,
                parent_id=parent_id,
                context_vector=child_context,
                state=NodeState.PENDING
            )
            
            # 3. Atomicity Check (Heuristic: if description is short, treat as atomic)
            is_atomic = len(desc.split()) < atomic_threshold
            
            if is_atomic:
                new_node.state = NodeState.ATOMIC
                logger.debug(f"Node {new_id} marked as ATOMIC.")
            else:
                new_node.state = NodeState.PENDING
            
            self.graph[new_id] = new_node
            parent_node.children.append(new_id)
            parent_node.state = NodeState.DECOMPOSED
            created_ids.append(new_id)
            
        # 4. Logic Loop Detection
        if self._detect_logic_loop(self.root_id, set()):
            # Rollback changes (simplified for this snippet)
            for cid in created_ids:
                self.graph.pop(cid, None)
                parent_node.children.remove(cid)
            raise RuntimeError("Decomposition aborted: Logical loop created.")
            
        return created_ids

    def merge_sub_graph(self, external_node_id: str, connection_point_id: str) -> bool:
        """
        Core Function 2: Merges a node from an external context into the current graph.
        Ensures context consistency and graph validity.
        
        Args:
            external_node_id: The ID of the node being imported (assumed to exist in 'graph').
            connection_point_id: The ID of the node in the current tree to attach to.
            
        Returns:
            True if merge successful, False otherwise.
        """
        logger.info(f"Attempting to merge node {external_node_id} to parent {connection_point_id}")
        
        if external_node_id not in self.graph:
            logger.error("External node not found.")
            return False
            
        child_node = self.graph[external_node_id]
        
        # If the connection point is actually a descendant of the external node, 
        # connecting them would create a loop.
        # Check: Is connection_point_id reachable from external_node_id?
        # Note: This requires traversing 'children'. Here we use a simplified check.
        
        # For this method, we assume the node is already in the dict but disconnected,
        # or we are establishing a link. 
        # Let's simulate connecting an existing isolated node to a parent.
        
        if connection_point_id not in self.graph:
            logger.error("Connection point not found.")
            return False
            
        parent_node = self.graph[connection_point_id]
        
        # Context Check
        if not check_semantic_drift(parent_node.context_vector, child_node.context_vector, threshold=0.3):
            logger.error("Merge failed: Semantic inconsistency.")
            return False
            
        # Link
        child_node.parent_id = connection_point_id
        parent_node.children.append(external_node_id)
        
        # Cycle Check
        if self._detect_logic_loop(self.root_id, set()):
            logger.error("Merge failed: Created cycle.")
            # Rollback
            parent_node.children.remove(external_node_id)
            child_node.parent_id = None
            return False
            
        logger.info(f"Successfully merged {external_node_id}.")
        return True

# Usage Example
if __name__ == "__main__":
    # 1. Initialize the Decomposer
    root_ctx = [0.1, 0.5, 0.2] # e.g., "Environment", "Global", "Urgent"
    decomposer = HierarchicalGoalDecomposer("Solve Global Warming", root_context=root_ctx)
    
    # 2. Define Sub-tasks (Layer 1)
    layer_1_tasks = [
        {"description": "Reduce Carbon Emissions", "context": [0.1, 0.5, 0.21]}, # High similarity
        {"description": "Develop Carbon Capture Tech", "context": [0.1, 0.5, 0.19]},
        {"description": "Plant 1 Trillion Trees", "context": [0.1, 0.5, 0.2]}
    ]
    
    try:
        child_ids = decomposer.decompose_node(decomposer.root_id, layer_1_tasks)
        print(f"Created {len(child_ids)} sub-goals.")
        
        # 3. Further Decompose one sub-task (Layer 2)
        if child_ids:
            target_node = child_ids[0] # "Reduce Carbon Emissions"
            layer_2_tasks = [
                {"description": "Switch to EVs"}, # Short enough to be Atomic
                {"description": "Shutdown Coal Plants"}
            ]
            decomposer.decompose_node(target_node, layer_2_tasks)
            
        # 4. Check Atomic Nodes
        atomic_count = sum(1 for n in decomposer.graph.values() if n.state == NodeState.ATOMIC)
        print(f"Total Atomic nodes ready for execution: {atomic_count}")
        
    except Exception as e:
        logger.error(f"Decomposition failed: {e}")