"""
Module: auto_continuous_evolution_knowledge_half_life.py

This module implements a dynamic forgetting mechanism for AGI systems based on
the concept of 'Knowledge Half-Life'. It addresses the limitation of cognitive
narrowness caused by finite lifespans (or storage) by implementing 'active
forgetting'.

Core Mechanism:
1.  Nodes (knowledge units) possess a 'Practical Verification Timestamp'.
2.  A decay function reduces the weight of nodes based on the time elapsed
    since their last verification or reuse.
3.  Nodes falling below a certain threshold are removed or archived to free
    up space for new, relevant knowledge.

Design Principles:
-   Time-Sensitive: Knowledge relevance degrades over time if unused.
-   Configurable: Supports custom half-life periods.
-   Safe: Includes validation to prevent critical data loss (if tagged).
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Dynamic_Forgetting")

@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the AGI's knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge content (simplified as string/struct here).
        weight: Current importance weight (0.0 to 1.0).
        last_verified: Timestamp when the node was last validated or used.
        is_protected: If True, the node is immune to automatic deletion 
                      (but still decays in weight).
        creation_time: Timestamp of node creation.
    """
    id: str
    content: str
    weight: float = 1.0
    last_verified: datetime = field(default_factory=datetime.utcnow)
    is_protected: bool = False
    creation_time: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")
        if not isinstance(self.last_verified, datetime):
            raise TypeError("last_verified must be a datetime object")


class KnowledgeHalfLifeSystem:
    """
    Manages the lifecycle of knowledge nodes using a radioactive decay model.
    
    The system automatically decays node weights based on a half-life parameter.
    If a node is not 'reused' or 'verified', its weight approaches zero.
    """

    def __init__(self, half_life_days: float = 30.0, decay_threshold: float = 0.05):
        """
        Initialize the system.
        
        Args:
            half_life_days: The number of days over which the knowledge weight halves.
            decay_threshold: The weight below which a node is considered 'dead' 
                             and subject to garbage collection.
        """
        if half_life_days <= 0:
            raise ValueError("Half-life must be positive.")
        if not 0.0 <= decay_threshold <= 1.0:
            raise ValueError("Decay threshold must be between 0 and 1.")
            
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.half_life_days = half_life_days
        self.decay_threshold = decay_threshold
        logger.info(f"System initialized with Half-Life: {half_life_days} days, Threshold: {decay_threshold}")

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a new node to the system."""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        logger.debug(f"Node added: {node.id}")

    def verify_node(self, node_id: str, current_time: datetime) -> bool:
        """
        Refresh a node's timestamp (simulate reuse/verification).
        
        This resets the decay timer and slightly boosts the weight.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found for verification.")
            return False
        
        node = self.nodes[node_id]
        node.last_verified = current_time
        # Boost weight slightly upon verification, capping at 1.0
        node.weight = min(1.0, node.weight + 0.1) 
        logger.info(f"Node {node_id} verified at {current_time}. Weight boosted to {node.weight:.4f}")
        return True

    def calculate_decay_factor(self, days_elapsed: float) -> float:
        """
        Auxiliary Function: Calculate the decay multiplier.
        
        Formula: N(t) = N0 * (1/2) ^ (t / T)
        Returns a multiplier between 0 and 1.
        """
        if days_elapsed < 0:
            return 1.0
        return 0.5 ** (days_elapsed / self.half_life_days)

    def execute_forgetting_mechanism(self, current_time: datetime) -> List[str]:
        """
        Core Function: Iterate through all nodes, apply decay, and remove dead nodes.
        
        Args:
            current_time: The reference 'now' time for calculation.
            
        Returns:
            A list of IDs of the nodes that were forgotten (deleted).
        """
        forgotten_ids = []
        active_ids = []
        
        # Create a list of items to avoid dictionary changed size during iteration
        items_to_process = list(self.nodes.items())
        
        for node_id, node in items_to_process:
            # 1. Calculate time elapsed since last verification
            delta = current_time - node.last_verified
            days_elapsed = delta.total_seconds() / (3600 * 24)
            
            # 2. Calculate new weight
            decay_multiplier = self.calculate_decay_factor(days_elapsed)
            original_weight = node.weight
            node.weight *= decay_multiplier
            
            logger.debug(
                f"Node {node_id}: {days_elapsed:.2f} days elapsed. "
                f"Weight: {original_weight:.4f} -> {node.weight:.4f}"
            )
            
            # 3. Garbage Collection Logic
            if node.weight < self.decay_threshold:
                if node.is_protected:
                    # Protected nodes are retained but logged as 'dormant'
                    logger.warning(f"Protected Node {node_id} is dormant (Weight: {node.weight:.4f}) but retained.")
                    active_ids.append(node_id)
                else:
                    # Delete node
                    del self.nodes[node_id]
                    forgotten_ids.append(node_id)
                    logger.info(f"FORGOTTEN: Node {node_id} dropped below threshold.")
            else:
                active_ids.append(node_id)
                
        return forgotten_ids

    def get_system_status(self) -> Dict[str, Union[int, float]]:
        """Return statistics about the current knowledge base."""
        if not self.nodes:
            return {"count": 0, "avg_weight": 0.0}
        
        total_weight = sum(n.weight for n in self.nodes.values())
        return {
            "count": len(self.nodes),
            "avg_weight": total_weight / len(self.nodes)
        }


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup the system with a short half-life for demonstration (e.g., 1 minute equivalent in logic, 
    # but here we use days for conceptual clarity. We will simulate time travel).
    system = KnowledgeHalfLifeSystem(half_life_days=10.0, decay_threshold=0.1)
    
    # 2. Create some knowledge nodes
    now = datetime.utcnow()
    
    node_old = KnowledgeNode(
        id="concept_python_2_7",
        content="Legacy Python Syntax",
        weight=1.0,
        last_verified=now - timedelta(days=60) # Not used for 60 days
    )
    
    node_recent = KnowledgeNode(
        id="concept_transformer_arch",
        content="Transformer Neural Network Architecture",
        weight=1.0,
        last_verified=now - timedelta(days=5) # Used 5 days ago
    )
    
    node_critical = KnowledgeNode(
        id="axiom_do_not_kill_humans",
        content="Core Safety Axiom",
        weight=1.0,
        last_verified=now - timedelta(days=100), # Very old
        is_protected=True # Protected from deletion
    )
    
    system.add_node(node_old)
    system.add_node(node_recent)
    system.add_node(node_critical)
    
    print("\n--- Initial State ---")
    print(f"Total Nodes: {len(system.nodes)}")
    
    # 3. Execute forgetting mechanism at current time
    print("\n--- Executing Evolution Cycle ---")
    forgotten = system.execute_forgetting_mechanism(now)
    
    # 4. Results
    print("\n--- Final State ---")
    print(f"Forgotten Nodes: {forgotten}")
    print(f"Remaining Nodes: {list(system.nodes.keys())}")
    
    # Check specific status
    if "concept_python_2_7" not in system.nodes:
        print("\nSuccess: Obsolete knowledge was dynamically removed.")
    
    if "axiom_do_not_kill_humans" in system.nodes:
        axiom = system.nodes["axiom_do_not_kill_humans"]
        print(f"Success: Critical Axiom retained (though weight decayed to {axiom.weight:.4f})")
