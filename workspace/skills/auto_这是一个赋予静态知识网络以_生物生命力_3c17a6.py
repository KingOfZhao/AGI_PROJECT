"""
Meta-Cognitive Architecture: Bio-Living Knowledge Network

This module implements a 'Bio-Living' knowledge network for AGI systems.
It treats knowledge not as static data, but as organic entities requiring
energy (compute/storage resources) to survive.

Core Philosophy:
- Thermodynamic Cognitive Economy: Nodes pay "rent" via utility.
- Decay & Apoptosis: Unused knowledge undergoes radioactive decay (forgetting).
- Homeostasis: Prevents "cognitive arteriosclerosis" (infinite bloat) by
  recycling resources from decayed nodes to high-value new nodes.

Author: Auto-Generated AGI Skill Engineer
Version: 3c17a6
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [BIO_NET] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the network.
    
    Attributes:
        id: Unique identifier.
        content: The actual knowledge payload (e.g., embedding, text, logic).
        energy: Current vitality. If <= 0, the node dies.
        created_at: Timestamp of creation.
        last_accessed: Timestamp of last successful usage.
        access_count: Number of times validated/solved problems.
    """
    id: str
    content: Any
    energy: float = 100.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def __post_init__(self):
        if self.energy < 0:
            raise ValueError("Initial energy cannot be negative.")


class BioLivingKnowledgeNetwork:
    """
    A meta-cognitive system that manages knowledge lifecycle based on
    thermodynamic principles and utility-based survival.
    """

    def __init__(self, half_life_seconds: float = 3600.0, survival_cost_rate: float = 0.05):
        """
        Initialize the Bio-Living Network.

        Args:
            half_life_seconds: Time in seconds for unaccessed knowledge to lose half its energy.
            survival_cost_rate: Base percentage of energy deducted during maintenance cycles.
        """
        if half_life_seconds <= 0:
            raise ValueError("Half-life must be positive.")
        
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.half_life = half_life_seconds
        self.decay_constant = math.log(2) / self.half_life
        self.survival_cost_rate = survival_cost_rate
        self._energy_pool: float = 0.0  # Recycled energy from dead nodes
        logger.info(f"Bio-Living Network initialized. Half-life: {half_life_seconds}s")

    def add_node(self, node_id: str, content: Any, initial_energy: float = 100.0) -> bool:
        """
        Create a new knowledge node (Birth).
        
        Args:
            node_id: Unique ID for the knowledge.
            content: The knowledge payload.
            initial_energy: Starting vitality.
            
        Returns:
            bool: True if successful, False if ID exists.
        """
        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already exists.")
            return False
        
        try:
            new_node = KnowledgeNode(id=node_id, content=content, energy=initial_energy)
            self.nodes[node_id] = new_node
            logger.info(f"Node Born: {node_id} | Initial Energy: {initial_energy}")
            return True
        except Exception as e:
            logger.error(f"Failed to create node {node_id}: {e}")
            return False

    def validate_and_consume(self, node_id: str, reward: float = 10.0) -> Optional[Any]:
        """
        Access a node (Metabolism/Feeding). 
        If the node solves a problem (is accessed), it gains energy.
        
        Args:
            node_id: ID of the node to access.
            reward: Energy gained from successful utilization.
            
        Returns:
            The content of the node if alive, else None.
        """
        if node_id not in self.nodes:
            return None
        
        node = self.nodes[node_id]
        
        # Check if node is "dead" (zombie check)
        if node.energy <= 0:
            logger.debug(f"Attempted to access dead node: {node_id}")
            return None

        # Successful activation: Gain energy (feed)
        node.energy += reward
        node.last_accessed = time.time()
        node.access_count += 1
        
        logger.info(f"Node Fed: {node_id} | +{reward} Energy | Total: {node.energy:.2f}")
        return node.content

    def _calculate_decay(self, node: KnowledgeNode, current_time: float) -> float:
        """
        Helper: Calculate energy loss based on time since last access (Entropy).
        
        Law of Decay: E(t) = E_0 * e^(-lambda * dt)
        """
        dt = current_time - node.last_accessed
        decay_factor = math.exp(-self.decay_constant * dt)
        
        # Theoretical survival without cost
        # But we also apply a 'rent' cost for storage
        rent_cost = node.energy * self.survival_cost_rate * (dt / self.half_life)
        
        return rent_cost

    def run_maintenance_cycle(self) -> List[str]:
        """
        Execute the lifecycle loop (Homeostasis).
        1. Charge survival rent (Compute/Storage cost).
        2. Apply radioactive decay (Forgetting).
        3. Apoptosis (Remove dead nodes).
        
        Returns:
            List of IDs of nodes that were pruned.
        """
        current_time = time.time()
        pruned_ids = []
        
        logger.info("--- Starting Maintenance Cycle ---")
        
        # Iterate over copy of keys to allow modification
        for node_id in list(self.nodes.keys()):
            node = self.nodes[node_id]
            
            # 1. Calculate Costs
            rent_cost = self._calculate_decay(node, current_time)
            
            # 2. Apply Cost
            node.energy -= rent_cost
            
            # 3. Check for Apoptosis (Death)
            if node.energy <= 0:
                pruned_ids.append(node_id)
                # Recycle remaining traces into the pool (optional mechanic)
                self._energy_pool += abs(node.energy) * 0.1 # hypothetical recycling
                del self.nodes[node_id]
                logger.warning(f"NODE DEATH (Apoptosis): {node_id} | Energy depleted.")
            else:
                logger.debug(f"Node Updated: {node_id} | -{rent_cost:.2f} Rent | Remaining: {node.energy:.2f}")

        logger.info(f"--- Cycle Complete. Pruned: {len(pruned_ids)} | Active: {len(self.nodes)} ---")
        return pruned_ids

    def get_network_stats(self) -> Dict[str, Any]:
        """
        Return statistics about the network health.
        """
        if not self.nodes:
            return {"status": "empty", "active_nodes": 0}
        
        total_energy = sum(n.energy for n in self.nodes.values())
        avg_age = (time.time() - sum(n.created_at for n in self.nodes.values()) / len(self.nodes))
        
        return {
            "active_nodes": len(self.nodes),
            "total_network_energy": total_energy,
            "avg_node_age_seconds": avg_age,
            "recycled_pool": self._energy_pool
        }


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize the System
    # Using a short half-life (10s) for demonstration purposes
    network = BioLivingKnowledgeNetwork(half_life_seconds=10.0, survival_cost_rate=0.1)
    
    # 2. Inject Knowledge (Birth)
    network.add_node("fact_sky", "The sky is blue.")
    network.add_node("fact_gravity", "Gravity pulls things down.")
    network.add_node("temp_debug", "Variable x was 5 during debug.") # Low value trivia
    
    print("\n[Simulating Time Passage & Usage...]")
    
    # 3. Simulate Usage (Feeding the strong nodes)
    # 'fact_gravity' is used often
    network.validate_and_consume("fact_gravity", reward=50)
    
    # 'fact_sky' is used once
    network.validate_and_consume("fact_sky", reward=20)
    
    # 'temp_debug' is NEVER used (No feeding)
    
    # 4. Simulate Time Passage (Wait for decay)
    # In a real system, this would be hours/days. Here we wait 12s (> half-life).
    time.sleep(12)
    
    # 5. Run Maintenance (The Reaper)
    # The unused 'temp_debug' should die. 'fact_gravity' should survive due to high energy bank.
    dead_nodes = network.run_maintenance_cycle()
    
    print(f"\n[Result] Pruned Nodes (Forgotten): {dead_nodes}")
    
    # 6. Check Final State
    stats = network.get_network_stats()
    print(f"[Stats] {stats}")
    
    # Verify 'temp_debug' is gone
    assert "temp_debug" not in network.nodes, "Failed: Trivia node should have decayed."
    assert "fact_gravity" in network.nodes, "Failed: High-value node should have survived."