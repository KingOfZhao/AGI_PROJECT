"""
Module: auto_research_synaptic_consolidation.py
Description: Implements the 'Synaptic Consolidation' algorithm for AGI memory management.
             This mechanism grants 'resistance to forgetting' privileges to nodes that
             achieve a high frequency of successful invocations, allowing them to
             maintain high utility scores even during long periods of inactivity.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum

# -----------------------------------------------------------------------------
# 1. Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 2. Data Structures and Enums
# -----------------------------------------------------------------------------

class NodeStatus(Enum):
    """Status of a memory node in the system."""
    ACTIVE = 1
    DORMANT = 2
    CONSOLIDATED = 3  # Privileged status

@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge or a skill node in the AGI system.
    
    Attributes:
        id: Unique identifier for the node.
        base_utility: The intrinsic utility score (0.0 to 1.0).
        invoke_count: Number of times this node was successfully called.
        fail_count: Number of times this node failed upon invocation.
        last_updated: Timestamp of the last update (simulated here as int/float).
        decay_factor: The rate at which utility decays over time if not used.
        status: Current status of the node.
    """
    id: str
    base_utility: float = 0.5
    invoke_count: int = 0
    fail_count: int = 0
    last_updated: float = 0.0
    decay_factor: float = 0.1  # Standard decay
    status: NodeStatus = NodeStatus.ACTIVE

    def success_rate(self) -> float:
        """Calculates the success rate of invocations."""
        total = self.invoke_count + self.fail_count
        if total == 0:
            return 0.0
        return self.invoke_count / total

# -----------------------------------------------------------------------------
# 3. Core Algorithm Class
# -----------------------------------------------------------------------------

class SynapticConsolidationEngine:
    """
    Manages the lifecycle of knowledge nodes, applying synaptic consolidation logic.
    
    The core algorithm identifies high-frequency, high-success nodes and reduces their
    decay factor, effectively 'consolidating' them into long-term memory.
    """

    def __init__(
        self, 
        consolidation_threshold: int = 100, 
        min_success_rate: float = 0.9,
        consolidation_decay_multiplier: float = 0.05
    ):
        """
        Initializes the engine.
        
        Args:
            consolidation_threshold: Minimum invoke count to qualify for consolidation.
            min_success_rate: Minimum success rate (0.0-1.0) required.
            consolidation_decay_multiplier: The new decay factor for consolidated nodes.
        """
        if not (0.0 <= min_success_rate <= 1.0):
            raise ValueError("min_success_rate must be between 0.0 and 1.0")
        if consolidation_threshold < 1:
            raise ValueError("consolidation_threshold must be at least 1")
            
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.consolidation_threshold = consolidation_threshold
        self.min_success_rate = min_success_rate
        self.consolidation_decay_multiplier = consolidation_decay_multiplier
        logger.info("SynapticConsolidationEngine initialized.")

    def add_node(self, node: KnowledgeNode) -> None:
        """Adds or updates a node in the registry."""
        if not isinstance(node, KnowledgeNode):
            raise TypeError("Item must be a KnowledgeNode instance")
        
        self.nodes[node.id] = node
        logger.debug(f"Node {node.id} added to registry.")

    def record_invocation(self, node_id: str, success: bool, current_time: float) -> None:
        """
        Records an invocation event for a specific node.
        
        Args:
            node_id: The ID of the node being invoked.
            success: Whether the invocation was successful.
            current_time: The current timestamp.
        """
        if node_id not in self.nodes:
            logger.warning(f"Attempted to record invocation for unknown node: {node_id}")
            return

        node = self.nodes[node_id]
        if success:
            node.invoke_count += 1
            logger.info(f"Node {node_id} invoked successfully. Total: {node.invoke_count}")
        else:
            node.fail_count += 1
            logger.warning(f"Node {node_id} invocation failed. Total failures: {node.fail_count}")
        
        node.last_updated = current_time
        
        # Trigger check for consolidation eligibility
        self._check_and_apply_consolidation(node)

    def _check_and_apply_consolidation(self, node: KnowledgeNode) -> None:
        """
        Internal helper to check if a node qualifies for consolidation.
        Requirement: Helper function.
        """
        # Skip if already consolidated
        if node.status == NodeStatus.CONSOLIDATED:
            return

        # Validation: Check boundary conditions
        if node.invoke_count < self.consolidation_threshold:
            return

        if node.success_rate() < self.min_success_rate:
            return

        # Apply Consolidation
        self._grant_consolidation_privilege(node)

    def _grant_consolidation_privilege(self, node: KnowledgeNode) -> None:
        """
        Grants resistance to forgetting.
        
        Args:
            node: The node to upgrade.
        """
        old_decay = node.decay_factor
        node.decay_factor = self.consolidation_decay_multiplier
        node.status = NodeStatus.CONSOLIDATED
        
        logger.info(
            f"*** CONSOLIDATION ACHIEVED *** Node {node.id} granted privileges. "
            f"Decay factor reduced: {old_decay:.4f} -> {node.decay_factor:.4f}"
        )

    def apply_temporal_decay(self, current_time: float) -> None:
        """
        Applies time-based decay to all nodes.
        Consolidated nodes resist this decay due to their low decay factor.
        
        Formula: Utility = Utility * exp(-decay_factor * time_delta)
        
        Args:
            current_time: The current timestamp.
        """
        logger.info("Applying global temporal decay...")
        for node in self.nodes.values():
            if node.last_updated == 0:
                continue # Skip nodes never updated
                
            time_delta = current_time - node.last_updated
            if time_delta < 0:
                logger.warning(f"Negative time delta detected for node {node.id}. Skipping.")
                continue

            # Calculate decay magnitude
            decay_amount = math.exp(-node.decay_factor * time_delta)
            node.base_utility *= decay_amount

            # Boundary check to prevent utility from going effectively negative or too low
            if node.base_utility < 0.001:
                node.base_utility = 0.001
                
            logger.debug(
                f"Node {node.id} | Status: {node.status.name} | "
                f"New Utility: {node.base_utility:.4f}"
            )

    def get_node_state(self, node_id: str) -> Optional[Dict[str, Union[float, str]]]:
        """
        Retrieves the current state of a node for external analysis.
        
        Args:
            node_id: The ID of the node.
            
        Returns:
            A dictionary containing state summary or None if not found.
        """
        if node_id not in self.nodes:
            return None
        
        node = self.nodes[node_id]
        return {
            "id": node.id,
            "utility": node.base_utility,
            "status": node.status.name,
            "invoke_count": node.invoke_count,
            "success_rate": node.success_rate()
        }

# -----------------------------------------------------------------------------
# 4. Usage Example
# -----------------------------------------------------------------------------

def run_simulation():
    """
    Demonstrates the Synaptic Consolidation algorithm.
    """
    print("\n--- Starting Synaptic Consolidation Simulation ---\n")
    
    # Initialize Engine
    engine = SynapticConsolidationEngine(
        consolidation_threshold=5, # Low threshold for demo purposes
        min_success_rate=0.8
    )

    # Create Nodes
    # Node A: Will become consolidated (High frequency, high success)
    node_a = KnowledgeNode(id="skill_python_coding", base_utility=0.9, decay_factor=0.5)
    
    # Node B: Regular node (Low frequency or low success)
    node_b = KnowledgeNode(id="skill_cobol_maintenance", base_utility=0.6, decay_factor=0.5)
    
    engine.add_node(node_a)
    engine.add_node(node_b)

    # Simulate Time: t=0 to t=10
    current_time = 0.0
    
    # Simulate Invocations for Node A (Successful)
    for _ in range(5):
        current_time += 1
        engine.record_invocation("skill_python_coding", success=True, current_time=current_time)

    # Simulate Invocations for Node B (Mixed)
    for _ in range(2):
        current_time += 1
        engine.record_invocation("skill_cobol_maintenance", success=True, current_time=current_time)
        engine.record_invocation("skill_cobol_maintenance", success=False, current_time=current_time)

    print("\n--- State after Invocations (t=20) ---")
    print(f"Node A State: {engine.get_node_state('skill_python_coding')}")
    print(f"Node B State: {engine.get_node_state('skill_cobol_maintenance')}")

    # Simulate long passage of time (Forgetting curve)
    # t=20 -> t=120 (100 units of time)
    print("\n--- Simulating long period of inactivity (100 time units) ---")
    engine.apply_temporal_decay(current_time=120.0)

    print("\n--- State after Decay ---")
    state_a = engine.get_node_state('skill_python_coding')
    state_b = engine.get_node_state('skill_cobol_maintenance')
    
    print(f"Node A (Consolidated) Utility: {state_a['utility']:.4f} (Resisted decay)")
    print(f"Node B (Normal) Utility: {state_b['utility']:.4f} (Decayed significantly)")

    # Verification
    assert state_a['status'] == 'CONSOLIDATED'
    assert float(state_a['utility']) > float(state_b['utility']), "Consolidated node should retain higher utility"
    
    print("\n--- Simulation Completed Successfully ---")

if __name__ == "__main__":
    run_simulation()