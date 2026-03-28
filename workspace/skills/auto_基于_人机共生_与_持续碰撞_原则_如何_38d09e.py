"""
Module: cognitive_decay_engine.py

Description:
    Implements a dynamic cognitive decay mechanism based on Human-Computer Symbiosis and Continuous Collision principles.
    This engine manages knowledge node vitality, simulating human memory forgetting curves to prevent 'cognitive sclerosis'.
    Instead of deleting dormant nodes, it reduces their connection weights based on network topology and time since last verification.

Key Principles:
    1. Human-Computer Symbiosis: Decay is triggered by a lack of human interaction (verification/refutation).
    2. Continuous Collision: Active nodes reinforce neighbors; isolated nodes decay faster.
    3. Graceful Degradation: Weights are lowered, not zeroed out immediately, allowing for potential re-activation.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CognitiveDecayEngine")


class NodeState(Enum):
    """Enumeration of possible cognitive node states."""
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    SEMI_DORMANT = "SEMI_DORMANT"
    DECAYED = "DECAYED"


@dataclass
class CognitiveNode:
    """
    Represents a single knowledge node in the AGI network.
    
    Attributes:
        id: Unique identifier for the node.
        content: The knowledge content or embedding reference.
        created_at: Timestamp of creation.
        last_verified: Timestamp of last human verification/collision.
        base_weight: Initial connection strength (0.0 to 1.0).
        current_weight: Current dynamic weight.
        neighbors: Set of connected node IDs.
    """
    id: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    last_verified: datetime = field(default_factory=datetime.now)
    base_weight: float = 1.0
    current_weight: float = 1.0
    neighbors: Set[str] = field(default_factory=set)
    state: NodeState = NodeState.ACTIVE

    def __post_init__(self):
        if not 0.0 <= self.base_weight <= 1.0:
            raise ValueError("Base weight must be between 0.0 and 1.0")


class CognitiveDecayEngine:
    """
    Engine responsible for managing the lifecycle and decay of cognitive nodes.
    """

    def __init__(self, decay_rate: float = 0.15, dormant_threshold_days: int = 30):
        """
        Initialize the decay engine.
        
        Args:
            decay_rate: The lambda parameter for the exponential decay function.
            dormant_threshold_days: Days without interaction before a node is considered dormant.
        """
        self.nodes: Dict[str, CognitiveNode] = {}
        self.decay_rate = decay_rate
        self.dormant_threshold = timedelta(days=dormant_threshold_days)
        logger.info(f"CognitiveDecayEngine initialized with decay_rate={decay_rate}, dormant_threshold={dormant_threshold_days} days")

    def add_node(self, node: CognitiveNode) -> None:
        """Add a new node to the network."""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        logger.debug(f"Node {node.id} added to network.")

    def record_human_interaction(self, node_id: str, interaction_time: Optional[datetime] = None) -> bool:
        """
        Update the 'last_verified' timestamp based on human interaction (Symbiosis).
        This acts as the collision event that resets decay.
        
        Args:
            node_id: The ID of the node interacted with.
            interaction_time: Specific time of interaction, defaults to now.
        
        Returns:
            bool: True if update was successful, False otherwise.
        """
        if node_id not in self.nodes:
            logger.error(f"Interaction recording failed: Node {node_id} not found.")
            return False
        
        timestamp = interaction_time if interaction_time else datetime.now()
        self.nodes[node_id].last_verified = timestamp
        self.nodes[node_id].state = NodeState.ACTIVE
        
        # Slight weight recovery on interaction
        recovery_boost = 0.1
        self.nodes[node_id].current_weight = min(
            1.0, 
            self.nodes[node_id].current_weight + recovery_boost
        )
        
        logger.info(f"Human collision detected: Node {node_id} refreshed at {timestamp}")
        return True

    def _calculate_topology_factor(self, node_id: str) -> float:
        """
        Auxiliary function: Calculate a topology factor based on neighbor activity.
        If neighbors are active, the node resists decay (support structure).
        
        Args:
            node_id: The ID of the node to analyze.
            
        Returns:
            float: A multiplier for the decay calculation (0.0 to 1.0).
                   Lower value means more resistance to decay.
        """
        if node_id not in self.nodes:
            return 1.0
            
        node = self.nodes[node_id]
        if not node.neighbors:
            return 1.0 # No neighbors, standard decay
            
        active_neighbors = 0
        total_neighbors = len(node.neighbors)
        
        for neighbor_id in node.neighbors:
            if neighbor_id in self.nodes:
                # Check if neighbor was verified recently (e.g., half the dormant time)
                neighbor = self.nodes[neighbor_id]
                recent_window = self.dormant_threshold / 2
                if (datetime.now() - neighbor.last_verified) < recent_window:
                    active_neighbors += 1
        
        # If 50% of neighbors are active, decay resistance is high.
        # Factor ranges from 0.5 (fully supported) to 1.0 (isolated)
        isolation_ratio = 1.0 - (active_neighbors / total_neighbors)
        topology_factor = 0.5 + (0.5 * isolation_ratio)
        
        return topology_factor

    def apply_decay_cycle(self, current_time: Optional[datetime] = None) -> Dict[str, float]:
        """
        Core Function: Apply the decay logic to all nodes.
        Simulates the 'forgetting curve' based on time delta and topology.
        
        Formula: W_new = W_old * e^(-lambda * t * T_factor)
        Where t is time elapsed and T_factor is the topology modifier.
        
        Args:
            current_time: Simulation time (allows backtesting), defaults to now.
            
        Returns:
            Dict[str, float]: A report of nodes that changed state and their new weights.
        """
        if not current_time:
            current_time = datetime.now()
            
        decay_report = {}
        logger.info(f"Starting global decay cycle at {current_time}")

        for node_id, node in list(self.nodes.items()):
            try:
                # 1. Calculate Time Delta
                time_elapsed = current_time - node.last_verified
                days_elapsed = time_elapsed.total_seconds() / (24 * 3600)

                # 2. Check Dormancy
                if time_elapsed > self.dormant_threshold:
                    # 3. Calculate Decay Intensity
                    topo_factor = self._calculate_topology_factor(node_id)
                    
                    # Exponential Decay calculation
                    decay_amount = math.exp(-self.decay_rate * days_elapsed * topo_factor)
                    
                    # Update Weight
                    new_weight = node.base_weight * decay_amount
                    node.current_weight = new_weight
                    
                    # Update State
                    if new_weight < 0.2:
                        node.state = NodeState.DECAYED
                    elif new_weight < 0.5:
                        node.state = NodeState.SEMI_DORMANT
                    else:
                        node.state = NodeState.DORMANT
                    
                    decay_report[node_id] = new_weight
                    logger.debug(f"Node {node_id} decayed to {new_weight:.4f} (State: {node.state.value})")
                
            except Exception as e:
                logger.error(f"Error processing decay for node {node_id}: {e}")
                continue

        logger.info(f"Decay cycle complete. {len(decay_report)} nodes processed for decay.")
        return decay_report

    def get_network_stats(self) -> Dict[str, int]:
        """Return statistics about the current network health."""
        stats = {state.name: 0 for state in NodeState}
        for node in self.nodes.values():
            stats[node.state.name] += 1
        return stats


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Engine
    engine = CognitiveDecayEngine(decay_rate=0.05, dormant_threshold_days=10)
    
    # 2. Create Nodes (Simulating a small knowledge graph)
    node_a = CognitiveNode(id="concept_001", content="Python Best Practices")
    node_b = CognitiveNode(id="concept_002", content="PEP 8 Standards")
    node_c = CognitiveNode(id="concept_003", content="Legacy System Architecture")
    
    # 3. Define Topology (Neighbor relationships)
    node_a.neighbors.add("concept_002")
    node_b.neighbors.add("concept_001")
    # node_c is isolated
    
    # Simulate time: Node A was touched recently, others were not
    from datetime import timedelta
    old_time = datetime.now() - timedelta(days=30)
    
    node_a.last_verified = datetime.now() - timedelta(days=2) # Active
    node_b.last_verified = old_time # Dormant
    node_c.last_verified = old_time - timedelta(days=15) # Very Dormant
    
    # Add nodes
    engine.add_node(node_a)
    engine.add_node(node_b)
    engine.add_node(node_c)
    
    print(f"Initial Stats: {engine.get_network_stats()}")
    
    # 4. Run Decay Cycle
    print("\nApplying Cognitive Decay...")
    results = engine.apply_decay_cycle()
    
    # 5. Review Results
    print("\n--- Decay Results ---")
    for nid, weight in results.items():
        print(f"Node {nid}: New Weight {weight:.4f}, State: {engine.nodes[nid].state.value}")
        
    # Node B should decay slower than Node C because it is connected to Node A (Active)
    print(f"\nTopology Factor for Node B (Connected to Active): {engine._calculate_topology_factor('concept_002'):.2f}")
    print(f"Topology Factor for Node C (Isolated): {engine._calculate_topology_factor('concept_003'):.2f}")
    
    print(f"\nFinal Stats: {engine.get_network_stats()}")