"""
Module: cognitive_metabolism.py

This module implements a metabolic regulation mechanism for Cognitive Networks 
based on the principles of the Second Law of Thermodynamics (Entropy).

In the context of AGI, knowledge structures (nodes) tend to accumulate (entropy increase).
Without a catabolic process to degrade obsolete or low-value information, the system
suffers from 'Cognitive Rigidity'. This module provides algorithms to monitor node
'activity' and 'validity', degrading outdated nodes (e.g., 'Floppy Disk Storage')
into cold storage (historical indices) to maintain system homeostasis and efficiency.

Author: Senior Python Engineer (AGI Systems Architecture)
Version: 1.0.0
"""

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveMetabolism")


class NodeStatus(Enum):
    """Enumeration of possible states for a cognitive node."""
    ACTIVE = auto()         # Currently used in reasoning
    DORMANT = auto()        # Rarely used, pending review
    DEGRADED = auto()       # Moved to history index, not active reasoning
    PURGED = auto()         # Removed entirely (extreme entropy)


@dataclass
class CognitiveNode:
    """
    Represents a single unit of knowledge in the cognitive network.
    
    Attributes:
        id: Unique identifier.
        concept: The semantic content (e.g., "Floppy Disk").
        energy: Internal potential energy (decreases over time without use).
        last_accessed: Timestamp of last invocation.
        success_rate: Float (0.0 to 1.0) representing empirical validity.
        status: Current lifecycle status.
    """
    id: str
    concept: str
    energy: float = 100.0
    last_accessed: float = field(default_factory=time.time)
    success_rate: float = 1.0
    status: NodeStatus = NodeStatus.ACTIVE

    def update_validity(self, outcome: bool) -> None:
        """Updates the success rate based on reasoning outcome."""
        # Simple moving average approximation for validity
        self.success_rate = (self.success_rate * 0.9) + (1.0 if outcome else 0.0) * 0.1


class MetabolicRegulator:
    """
    Manages the lifecycle of cognitive nodes to prevent stagnation.
    
    Implements the 'Catabolism' (breaking down) phase of the cognitive cycle.
    """

    def __init__(self, entropy_rate: float = 0.1, degradation_threshold: float = 20.0):
        """
        Initialize the regulator.
        
        Args:
            entropy_rate: The rate at which node energy naturally decays per cycle.
            degradation_threshold: Energy level below which a node is flagged for degradation.
        """
        if not 0 < entropy_rate < 1:
            raise ValueError("Entropy rate must be between 0 and 1.")
        
        self.entropy_rate = entropy_rate
        self.degradation_threshold = degradation_threshold
        self.network_graph: Dict[str, CognitiveNode] = {}
        
        logger.info("MetabolicRegulator initialized with entropy rate: %s", entropy_rate)

    def add_node(self, node: CognitiveNode) -> None:
        """Registers a node into the metabolic system."""
        if not isinstance(node, CognitiveNode):
            raise TypeError("Invalid node type.")
        
        self.network_graph[node.id] = node
        logger.debug("Node %s ('%s') added to metabolic watch.", node.id, node.concept)

    def invoke_catabolism(self, current_time: Optional[float] = None) -> Dict[str, NodeStatus]:
        """
        Core Algorithm: Applies the Second Law of Thermodynamics to the network.
        
        Iterates through all nodes, applying energy decay based on time elapsed.
        Nodes falling below the energy threshold are 'DEGRADED' (moved to history).
        
        Args:
            current_time: Simulation time (uses system time if None).
            
        Returns:
            A dictionary mapping Node IDs that changed status to their new status.
        """
        if current_time is None:
            current_time = time.time()
            
        status_changes: Dict[str, NodeStatus] = {}
        
        logger.info("Starting Catabolism Cycle...")
        
        for node_id, node in self.network_graph.items():
            if node.status == NodeStatus.PURGED:
                continue

            # 1. Calculate Time Delta (Aging)
            time_delta = current_time - node.last_accessed
            time_factor = min(time_delta / 3600, 10)  # Normalize hours, cap at 10

            # 2. Apply Entropic Decay (Energy Loss)
            # Energy decays exponentially if not used
            decay_amount = node.energy * (self.entropy_rate ** (1 + time_factor * 0.1))
            node.energy = max(0.0, node.energy - decay_amount)

            # 3. Check Validity (Contextual Obsolescence)
            # If success rate drops too low, accelerate entropy
            if node.success_rate < 0.3:
                node.energy *= 0.5  # Rapid decay for disproven concepts
                logger.warning("Node '%s' validity low (%.2f), accelerating decay.", 
                               node.concept, node.success_rate)

            # 4. State Transition Logic
            if node.status == NodeStatus.ACTIVE and node.energy < self.degradation_threshold:
                self._degrade_node(node)
                status_changes[node_id] = node.status
            
            elif node.status == NodeStatus.DORMANT and node.energy < 1.0:
                node.status = NodeStatus.PURGED
                status_changes[node_id] = node.status
                logger.critical("Node '%s' has been PURGED from the system.", node.concept)

        return status_changes

    def _degrade_node(self, node: CognitiveNode) -> None:
        """
        Internal helper to transition a node to a historical index.
        
        This acts as the 'recycling' mechanism. The node is not deleted,
        but moved to long-term storage/indexing, preventing it from
        cluttering active inference paths.
        """
        if node.status == NodeStatus.DEGRADED:
            return

        old_status = node.status
        node.status = NodeStatus.DEGRADED
        
        # In a real system, we would move the node object to a different database table
        logger.warning(
            "METABOLIC ACTION: Node '%s' (ID: %s) degraded from %s to HISTORY_INDEX. "
            "Reason: Low Activity/Validity.", 
            node.concept, node.id, old_status.name
        )

    def _boost_energy(self, node_id: str) -> None:
        """
        Auxiliary function: Reinforces a node (Anabolism).
        Called when a node is successfully used in reasoning.
        """
        if node_id in self.network_graph:
            node = self.network_graph[node_id]
            node.energy = min(100.0, node.energy + 15.0)  # Cap at 100
            node.last_accessed = time.time()
            
            # If it was degraded but proved useful again, reactivate
            if node.status == NodeStatus.DEGRADED:
                node.status = NodeStatus.ACTIVE
                logger.info("Node '%s' reactivated from history.", node.concept)
        else:
            logger.error("Attempted to boost non-existent node: %s", node_id)


# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # 1. Initialize the Metabolic System
    regulator = MetabolicRegulator(entropy_rate=0.05, degradation_threshold=25.0)

    # 2. Create Cognitive Nodes (Knowledge Base)
    node_modern = CognitiveNode(id="n1", concept="Transformer Neural Network", success_rate=0.95)
    node_legacy = CognitiveNode(id="n2", concept="Floppy Disk Storage", success_rate=0.4)
    node_obsolete = CognitiveNode(id="n3", concept="Phlogiston Theory", success_rate=0.01)

    # 3. Add to Network
    regulator.add_node(node_modern)
    regulator.add_node(node_legacy)
    regulator.add_node(node_obsolete)

    # 4. Simulate Time Passing and lack of use for Legacy/Obsolete nodes
    # We simulate that 'Floppy Disk' hasn't been used in a "long time"
    # by manually adjusting the last_accessed timestamp (e.g., 100 hours ago)
    regulator.network_graph["n2"].last_accessed = time.time() - (100 * 3600)
    regulator.network_graph["n3"].last_accessed = time.time() - (500 * 3600)

    # 5. Simulate usage of Modern node (Boosting)
    print("\n--- Simulating Active Usage of Modern Node ---")
    regulator._boost_energy("n1")

    # 6. Run the Metabolism Cycle (Catabolism)
    print("\n--- Running Metabolic Cycle ---")
    changes = regulator.invoke_catabolism()

    # 7. Verify Results
    print("\n--- Final System State ---")
    for nid, node in regulator.network_graph.items():
        print(f"Node: {node.concept:<30} | Status: {node.status.name:<10} | Energy: {node.energy:.2f}")

    # Assertions for validation
    assert regulator.network_graph["n1"].status == NodeStatus.ACTIVE
    assert regulator.network_graph["n2"].status == NodeStatus.DEGRADED