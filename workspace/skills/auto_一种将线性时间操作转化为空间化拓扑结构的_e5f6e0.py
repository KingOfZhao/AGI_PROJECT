"""
Module: spatio_temporal_dag.py

An advanced architectural implementation that transforms linear time operations
into a spatialized topological structure (Directed Acyclic Graph).

This system赋予 (endows) a one-way execution flow with 'Time-Axis Slicing' and
'Branch Backtracking' capabilities. It encapsulates operations (code generation,
manufacturing steps, UI design states) as independent 'Reversible Nodes'.

Upon detecting physical reference drift or logic errors, the system allows
rolling back to a specific 'Cognitive Snapshot', patching parameters, and
re-merging into the main chain, thus dynamically adapting to uncertainty.
"""

import logging
import hashlib
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SpatioTemporalDAG")

class NodeStatus(Enum):
    """Status of the execution node."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

@dataclass
class ReversibleNode:
    """
    Represents a single step in the operation chain.
    
    Attributes:
        node_id: Unique identifier.
        action_name: The name of the operation.
        params: Input parameters for the operation.
        result: Output result after execution.
        checksum: Hash of the state to detect drift.
        parent_id: ID of the previous node (None for root).
        timestamp: Creation time.
        status: Current execution status.
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    checksum: str = ""
    parent_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: NodeStatus = NodeStatus.PENDING

    def compute_checksum(self) -> str:
        """Generates a hash based on params and result to detect drift."""
        data = f"{self.params}{self.result}".encode('utf-8')
        return hashlib.sha256(data).hexdigest()

@dataclass
class CognitiveSnapshot:
    """
    A wrapper for a specific node state, allowing the system to revert.
    """
    snapshot_id: str
    node: ReversibleNode
    description: str

class SpatioTemporalTopology:
    """
    Core AGI Skill: Manages the topology of operations, allowing branching,
    backtracking, and merging similar to Git.
    """

    def __init__(self):
        self._nodes: Dict[str, ReversibleNode] = {}
        self._head: Optional[str] = None  # ID of the current active node
        self._snapshots: List[CognitiveSnapshot] = []
        logger.info("SpatioTemporalTopology System Initialized.")

    def _validate_input(self, params: Dict[str, Any], constraints: Dict[str, type]) -> None:
        """
        Helper function to validate input data types and boundaries.
        
        Args:
            params: Input parameters dictionary.
            constraints: Dictionary mapping param names to expected types.
        
        Raises:
            ValueError: If validation fails.
        """
        if not isinstance(params, dict):
            raise ValueError("Parameters must be a dictionary.")
        
        for key, expected_type in constraints.items():
            if key in params and not isinstance(params[key], expected_type):
                raise ValueError(
                    f"Parameter '{key}' must be of type {expected_type.__name__}, "
                    f"got {type(params[key]).__name__}"
                )
        logger.debug("Input validation passed.")

    def execute_operation(
        self, 
        action_func: Callable, 
        params: Dict[str, Any], 
        validation_schema: Optional[Dict[str, type]] = None
    ) -> ReversibleNode:
        """
        Core Function 1: Executes an operation and encapsulates it as a node.
        
        This extends the linear 'time' of execution by adding a spatial node
        that records the state change.
        
        Args:
            action_func: The callable function to execute.
            params: Arguments for the function.
            validation_schema: Optional type constraints for params.
            
        Returns:
            The created ReversibleNode.
        """
        if validation_schema:
            self._validate_input(params, validation_schema)

        parent_id = self._head
        node = ReversibleNode(
            action_name=action_func.__name__,
            params=deepcopy(params),
            parent_id=parent_id
        )

        try:
            logger.info(f"Executing action: {node.action_name} | ID: {node.node_id[:8]}...")
            result = action_func(**params)
            
            node.result = result
            node.status = NodeStatus.SUCCESS
            node.checksum = node.compute_checksum()
            
            # Link to chain
            self._nodes[node.node_id] = node
            self._head = node.node_id
            
            logger.info(f"Operation successful. Checksum: {node.checksum[:8]}...")
            
        except Exception as e:
            node.status = NodeStatus.FAILED
            self._nodes[node.node_id] = node # Store failed state for debug
            logger.error(f"Operation failed: {e}. Node preserved for analysis.")
            raise RuntimeError(f"Execution failed in {node.action_name}: {e}") from e

        return node

    def create_snapshot(self, description: str = "") -> CognitiveSnapshot:
        """
        Core Function 2: Captures the current state (Cognitive Snapshot).
        
        This allows the system to return to this specific point in 'time'
        if future operations cause drift.
        """
        if not self._head:
            raise ValueError("No active node to snapshot.")
            
        current_node = self._nodes[self._head]
        snapshot = CognitiveSnapshot(
            snapshot_id=str(uuid.uuid4()),
            node=deepcopy(current_node),
            description=description
        )
        self._snapshots.append(snapshot)
        logger.info(f"Snapshot created: {snapshot.snapshot_id[:8]}... at Node {current_node.node_id[:8]}...")
        return snapshot

    def backtrack_and_patch(
        self, 
        snapshot_id: str, 
        new_params: Dict[str, Any]
    ) -> ReversibleNode:
        """
        Rolls back the state to a specific snapshot, patches parameters,
        and creates a new branch.
        
        Args:
            snapshot_id: The ID of the snapshot to revert to.
            new_params: New parameters to apply to the action at that point.
            
        Returns:
            A new ReusableNode representing the patched timeline.
        """
        snapshot = next((s for s in self._snapshots if s.snapshot_id == snapshot_id), None)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found.")

        # "Rewind time" - In a real system, this would revert external state
        # Here we reset the HEAD to the snapshot's node ID conceptually
        original_node = snapshot.node
        logger.warning(
            f"BACKTRACKING: Reverting to state {snapshot.snapshot_id[:8]}... "
            f"(Action: {original_node.action_name})"
        )

        # Check for drift (if the logic context has changed since snapshot)
        if original_node.checksum != original_node.compute_checksum():
            logger.warning("Drift detected in snapshot data integrity.")

        # Create a branch
        self._head = original_node.node_id # Reset head to parent
        
        # Note: In a real implementation, we would need to re-execute the action
        # with new params. Here we simulate creating a new node based on the old action.
        # We need to retrieve the original function or assume it's passed again.
        # For this architecture demo, we return a new PENDING node attached to the snapshot parent.
        
        patched_node = ReversibleNode(
            action_name=f"{original_node.action_name}_patched",
            params=new_params,
            parent_id=original_node.parent_id # Branching off
        )
        
        # Add to topology
        self._nodes[patched_node.node_id] = patched_node
        self._head = patched_node.node_id
        
        logger.info(f"New branch created from patch. New Head: {patched_node.node_id[:8]}...")
        return patched_node

    def get_topology_history(self) -> List[Dict[str, Any]]:
        """Returns the chain of execution for visualization."""
        history = []
        current_id = self._head
        while current_id:
            node = self._nodes.get(current_id)
            if node:
                history.append({
                    "id": node.node_id,
                    "action": node.action_name,
                    "status": node.status.value,
                    "time": node.timestamp
                })
                current_id = node.parent_id
            else:
                break
        return history

# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # Mock function simulating a manufacturing or code generation step
    def generate_component(material: str, intensity: int) -> str:
        """Simulates a process that might fail or need adjustment."""
        if intensity > 100:
            raise ValueError("Intensity too high, physical limits exceeded.")
        return f"Component<{material}>[Strength:{intensity}]"

    # Initialize the system
    topo_system = SpatioTemporalTopology()

    # 1. Linear Execution Phase
    print("\n--- Phase 1: Linear Execution ---")
    try:
        # Validation schema ensures inputs are correct types
        schema = {"material": str, "intensity": int}
        
        node_1 = topo_system.execute_operation(
            generate_component, 
            {"material": "Steel", "intensity": 50}, 
            validation_schema=schema
        )
        
        # Take a snapshot before risky operation
        snap_1 = topo_system.create_snapshot("Pre-high-intensity-attempt")
        
        # 2. Error Handling & Drift Detection Phase
        print("\n--- Phase 2: Simulating Failure ---")
        try:
            # This will fail
            topo_system.execute_operation(
                generate_component, 
                {"material": "Titanium", "intensity": 150}, # Invalid
                validation_schema=schema
            )
        except RuntimeError:
            print("System caught error. Preparing to backtrack...")

        # 3. Backtracking and Patching
        print("\n--- Phase 3: Branching/Backtracking ---")
        # We revert to snap_1, adjust params, and try again
        patched_node = topo_system.backtrack_and_patch(
            snap_1.snapshot_id, 
            {"material": "Titanium", "intensity": 90} # Corrected params
        )
        
        # Execute the patched node (simulated)
        # In a real flow, the system would auto-retry the pending node
        print(f"Patched Node Status: {patched_node.status.value}")
        print(f"Patched Node Parent: {patched_node.parent_id}")

    except Exception as e:
        logger.critical(f"System Critical Failure: {e}")

    # Display history
    print("\n--- Topology History ---")
    import pprint
    pprint.pprint(topo_system.get_topology_history())