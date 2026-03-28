"""
Skill Module: auto_collision_solidification_storage_layer_real_node_55030d
Description: Manages the lifecycle of 'Real Nodes' in an AGI knowledge graph.
             Implements a Bayesian updating system for weight adjustment based on
             'Human-Machine Collision' (interaction/validation events).
             Determines whether nodes should be downgraded, split, or archived
             based on their version evolution and verification history.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Enumeration of possible lifecycle states for a Real Node."""
    ACTIVE = "active"          # Normal operation, high confidence
    SUSPECT = "suspect"        # Under scrutiny, potentially unstable
    ARCHIVED = "archived"      # Deprecated, low confidence/obsolete
    SPLIT = "split"            # Transformed into child nodes


@dataclass
class CollisionRecord:
    """Represents a single interaction/validation event (Human-Machine Collision)."""
    timestamp: datetime
    is_supportive: bool        # True if validation supports the node
    source_id: str             # Identifier for the human or system source
    confidence: float = 1.0    # Confidence of the source


@dataclass
class RealNode:
    """
    Represents a 'Real Node' in the knowledge graph.
    
    Attributes:
        node_id: Unique identifier.
        content: The semantic content or data payload.
        version: Current version number.
        alpha: Bayesian alpha parameter (count of supportive evidence).
        beta: Bayesian beta parameter (count of refuting evidence).
        status: Current lifecycle status.
        history: Log of collision events.
        decay_factor: Time decay factor for weight calculation.
    """
    node_id: str
    content: str
    version: int = 1
    alpha: float = 1.0  # Prior pseudo-count for positive evidence
    beta: float = 1.0   # Prior pseudo-count for negative evidence
    status: NodeStatus = NodeStatus.ACTIVE
    history: List[CollisionRecord] = field(default_factory=list)
    decay_factor: float = 0.95
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def current_weight(self) -> float:
        """
        Calculates the current weight/confidence of the node using Bayesian mean.
        Formula: E[theta] = alpha / (alpha + beta)
        """
        return self.alpha / (self.alpha + self.beta)


class NodeLifecycleManager:
    """
    Manages the storage and lifecycle transitions of Real Nodes based on
    collision events.
    """

    def __init__(self, archive_threshold: float = 0.2, split_threshold: float = 0.45):
        """
        Initialize the manager.

        Args:
            archive_threshold: Weight below which a node is archived.
            split_threshold: Weight below which a node is considered for splitting.
        """
        self.archive_threshold = archive_threshold
        self.split_threshold = split_threshold
        self._node_store: Dict[str, RealNode] = {}
        logger.info("NodeLifecycleManager initialized with thresholds: Archive=%s, Split=%s",
                    archive_threshold, split_threshold)

    def process_collision(self, node_id: str, is_supportive: bool, source_id: str) -> NodeStatus:
        """
        Core Function 1: Processes a collision event and updates node weight.

        Args:
            node_id: ID of the node to update.
            is_supportive: Result of the collision (True if verified, False if falsified).
            source_id: Identifier of the validating agent.

        Returns:
            The new status of the node after processing.

        Raises:
            ValueError: If node_id does not exist.
        """
        if node_id not in self._node_store:
            logger.error("Attempted to process collision for non-existent node: %s", node_id)
            raise ValueError(f"Node {node_id} not found.")

        node = self._node_store[node_id]
        logger.info("Processing collision for Node %s. Supportive: %s", node_id, is_supportive)

        # Record the event
        record = CollisionRecord(
            timestamp=datetime.now(),
            is_supportive=is_supportive,
            source_id=source_id
        )
        node.history.append(record)

        # Bayesian Update
        if is_supportive:
            node.alpha += 1.0
        else:
            node.beta += 1.0

        logger.debug("Node %s updated weights -> Alpha: %.2f, Beta: %.2f, Weight: %.4f",
                     node_id, node.alpha, node.beta, node.current_weight)

        # Trigger Lifecycle Evaluation
        return self._evaluate_lifecycle_transition(node)

    def _evaluate_lifecycle_transition(self, node: RealNode) -> NodeStatus:
        """
        Auxiliary Function: Evaluates node state and determines lifecycle action.
        
        Internal logic:
        1. If weight drops below archive threshold -> ARCHIVE.
        2. If weight drops below split threshold -> SPLIT (simulate complexity).
        3. If weight is high but fluctuates -> SUSPECT.
        4. Otherwise -> ACTIVE.
        """
        current_weight = node.current_weight
        previous_status = node.status

        if current_weight < self.archive_threshold:
            node.status = NodeStatus.ARCHIVED
            logger.warning("Node %s weight %.4f < %.4f. Status changed to ARCHIVED.",
                           node.node_id, current_weight, self.archive_threshold)
        
        elif current_weight < self.split_threshold:
            # In a real system, this would trigger a splitting mechanism.
            # Here we mark it for splitting logic demonstration.
            node.status = NodeStatus.SPLIT
            logger.info("Node %s weight %.4f < %.4f. Marked for SPLITTING.",
                        node.node_id, current_weight, self.split_threshold)

        elif node.beta > (node.alpha * 0.5) and node.status == NodeStatus.ACTIVE:
            # If there's significant negative pressure
            node.status = NodeStatus.SUSPECT
            logger.info("Node %s marked as SUSPECT due to high beta count.", node.node_id)
            
        else:
            node.status = NodeStatus.ACTIVE
            # Only log if status changed back to active or was active
            if previous_status != NodeStatus.ACTIVE:
                logger.info("Node %s stabilized to ACTIVE.", node.node_id)

        return node.status

    def create_child_nodes_from_split(self, parent_node: RealNode) -> List[RealNode]:
        """
        Core Function 2: Handles the 'Split' decision by generating child nodes.
        
        This simulates the refactoring of a fuzzy/low-confidence concept into
        more specific, higher-confidence sub-concepts.
        
        Args:
            parent_node: The node to be split.
            
        Returns:
            A list of new RealNode objects derived from the parent.
        """
        if parent_node.status != NodeStatus.SPLIT:
            logger.warning("Attempted to split node %s which is not in SPLIT status.", parent_node.node_id)
            return []

        logger.info("Splitting node %s ('%s')...", parent_node.node_id, parent_node.content)
        
        # Mock splitting logic: Divide content into parts and reset priors
        # In a real AGI system, this would use an LLM or clustering algorithm.
        base_content = parent_node.content
        new_nodes = []
        
        # Generate two hypothetical sub-nodes
        for i in range(1, 3):
            child_id = f"{parent_node.node_id}_sub_{i}"
            child_content = f"Refined aspect {i} of [{base_content}]"
            
            # Children start with fresh, slightly optimistic priors based on parent context
            new_node = RealNode(
                node_id=child_id,
                content=child_content,
                version=parent_node.version + 1,
                alpha=1.5, # Optimistic start
                beta=0.5,
                status=NodeStatus.ACTIVE
            )
            new_nodes.append(new_node)
            self._node_store[child_id] = new_node
            logger.debug("Created child node: %s", child_id)

        # Archive parent after split
        parent_node.status = NodeStatus.ARCHIVED
        logger.info("Parent node %s archived after successful split.", parent_node.node_id)
        
        return new_nodes

    def add_node(self, node: RealNode) -> None:
        """Helper to add a node to the store."""
        if not isinstance(node, RealNode):
            raise TypeError("Invalid node type.")
        if node.node_id in self._node_store:
            raise ValueError(f"Duplicate node ID: {node.node_id}")
        
        self._node_store[node.node_id] = node
        logger.info("Added new node: %s", node.node_id)


# Example Usage
if __name__ == "__main__":
    # Initialize Manager
    manager = NodeLifecycleManager(archive_threshold=0.25, split_threshold=0.40)

    # Create a Node
    node_1 = RealNode(node_id="concept_001", content="The sky is green during the day")
    manager.add_node(node_1)

    # Simulate Collisions (Falsification)
    # Weight starts at 0.5 (1/2). 
    # After 3 falsifications: alpha=1, beta=4. Weight = 1/5 = 0.2 -> ARCHIVED
    try:
        print("\n--- Simulating Falsification Sequence ---")
        manager.process_collision("concept_001", is_supportive=False, source_id="user_A")
        print(f"Status 1: {node_1.status.name}, Weight: {node_1.current_weight:.3f}")
        
        manager.process_collision("concept_001", is_supportive=False, source_id="user_B")
        print(f"Status 2: {node_1.status.name}, Weight: {node_1.current_weight:.3f}")
        
        manager.process_collision("concept_001", is_supportive=False, source_id="sensor_1")
        print(f"Status 3: {node_1.status.name}, Weight: {node_1.current_weight:.3f}")
        
    except ValueError as e:
        print(f"Error: {e}")

    # Create another Node for Splitting test
    node_2 = RealNode(node_id="concept_002", content="Birds are robots")
    manager.add_node(node_2)
    
    # Simulate Collisions (Mixed results leading to Split)
    # Weight: 1/2 -> False(1/3) -> False(1/4) = 0.25. 
    # Let's make it slightly better than archive so it splits.
    # Alpha=2, Beta=1 (0.66) -> False -> 2/3 (0.66 - 0.50? No.)
    # Let's manually set weights to trigger split for demo
    node_2.alpha = 1.0
    node_2.beta = 1.5 # Weight = 1 / 2.5 = 0.4 (Borderline)
    node_2.status = NodeStatus.SPLIT # Force status for demo purpose of create_child
    
    print("\n--- Simulating Node Splitting ---")
    children = manager.create_child_nodes_from_split(node_2)
    print(f"Parent Status: {node_2.status.name}")
    print(f"Number of Children: {len(children)}")
    for child in children:
        print(f"Child ID: {child.node_id}, Content: {child.content}, Weight: {child.current_weight:.3f}")