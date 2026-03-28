"""
Module: harmonic_entropy_decay_engine
Description: Implements an advanced memory management system for AGI contexts.
             It decays memory nodes based on 'dissonance' (logical conflict) with
             the active context, simulating the physical tendency of dominant
             seventh chords to resolve to the tonic.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HarmonicEntropyDecayEngine")


@dataclass
class KnowledgeNode:
    """
    Represents a unit of information in the AGI knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        embedding: Vector representation of the concept (logic/semantics).
        timestamp: Last access or update time (epoch).
        weight: Current importance/relevance score (0.0 to 1.0).
        resonance_factor: How well it aligns with the current context (updated dynamically).
    """
    id: str
    embedding: List[float]
    timestamp: float
    weight: float = 1.0
    resonance_factor: float = 0.5  # Default neutral resonance

    def __post_init__(self):
        if not isinstance(self.embedding, list):
            raise ValueError("Embedding must be a list of floats.")
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError("Weight must be between 0.0 and 1.0.")


class HarmonicEntropyDecayEngine:
    """
    An engine that manages the lifecycle of memory nodes by calculating
    their 'harmonic entropy'. Nodes that create logical dissonance with
    the active context decay faster than those that are merely old.
    """

    def __init__(self, dissonance_sensitivity: float = 1.5, base_decay_rate: float = 0.01):
        """
        Initialize the engine.

        Args:
            dissonance_sensitivity: Exponent factor to amplify dissonance impact.
            base_decay_rate: The standard linear decay rate applied to time.
        """
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._dissonance_sensitivity = dissonance_sensitivity
        self._base_decay_rate = base_decay_rate
        logger.info("HarmonicEntropyDecayEngine initialized.")

    def add_node(self, node: KnowledgeNode) -> None:
        """Add or update a node in the knowledge network."""
        if not node.id:
            raise ValueError("Node ID cannot be empty.")
        self._nodes[node.id] = node
        logger.debug(f"Node {node.id} added/updated in engine.")

    def calculate_dissonance(self, node_embedding: List[float], context_embedding: List[float]) -> float:
        """
        Calculate the dissonance (conflict/distance) between a node and the current context.
        Uses Cosine Similarity. Low similarity = High dissonance.
        
        Args:
            node_embedding: Vector of the target node.
            context_embedding: Vector of the current active context.

        Returns:
            float: Dissonance score (0.0 to ~infinity).
        """
        if not node_embedding or not context_embedding:
            return 0.0

        dot_product = sum(a * b for a, b in zip(node_embedding, context_embedding))
        norm_a = math.sqrt(sum(a * a for a in node_embedding))
        norm_b = math.sqrt(sum(b * b for b in context_embedding))
        
        if norm_a == 0 or norm_b == 0:
            return 1.0  # Max dissonance for zero vectors

        similarity = dot_product / (norm_a * norm_b)
        
        # Convert similarity (-1 to 1) to dissonance (0 to 2)
        # Similarity 1 -> Dissonance 0
        # Similarity -1 -> Dissonance 2
        dissonance = (1 - similarity) / 2
        return dissonance

    def apply_harmonic_decay(self, context_embedding: List[float], current_time: float) -> List[str]:
        """
        Core function: Updates weights of all nodes based on time and harmonic tension.
        
        Formula:
        Decay_Factor = Base_Decay + (Dissonance ^ Sensitivity)
        New_Weight = Old_Weight * (1 - Decay_Factor * Time_Delta)

        Args:
            context_embedding: The vector representing the current active thought/context.
            current_time: The current timestamp.

        Returns:
            List of IDs for nodes that have decayed below threshold and were removed.
        """
        removed_nodes = []
        
        if not context_embedding:
            logger.warning("Context embedding is empty, skipping decay cycle.")
            return []

        node_ids = list(self._nodes.keys())
        
        for node_id in node_ids:
            node = self._nodes[node_id]
            
            try:
                # 1. Calculate Time Component
                time_delta = max(0, current_time - node.timestamp)
                time_penalty = time_delta * self._base_decay_rate

                # 2. Calculate Harmonic Component (Dissonance)
                dissonance = self.calculate_dissonance(node.embedding, context_embedding)
                
                # 3. Apply Exponential Acceleration based on Tension
                # High dissonance causes exponential decay speed-up
                harmonic_penalty = math.pow(dissonance, self._dissonance_sensitivity)
                
                total_decay = time_penalty + harmonic_penalty
                
                # 4. Update Weight
                new_weight = node.weight - total_decay
                node.weight = max(0.0, min(1.0, new_weight))
                
                logger.debug(f"Node {node_id}: Dissonance={dissonance:.4f}, Decay={total_decay:.6f}, NewWeight={node.weight:.4f}")

                # 5. Garbage Collection
                if node.weight < 0.01:  # Threshold for oblivion
                    removed_nodes.append(node_id)
                    del self._nodes[node_id]
                    logger.info(f"Node {node_id} resolved (decayed) due to high entropy/low weight.")

            except Exception as e:
                logger.error(f"Error processing node {node_id}: {e}")
                continue

        return removed_nodes

    def get_node_state(self, node_id: str) -> Optional[Dict]:
        """Helper to inspect a node's current state."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            return {
                "id": node.id,
                "weight": node.weight,
                "last_update": node.timestamp
            }
        return None


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Setup Engine
    engine = HarmonicEntropyDecayEngine(dissonance_sensitivity=2.0, base_decay_rate=0.001)
    
    # 2. Create Mock Data (Simulating AGI concepts)
    # Node A: Relevant concept (aligned with context)
    node_a = KnowledgeNode(
        id="concept_alpha",
        embedding=[1.0, 0.9, 0.8],  # High alignment
        timestamp=time.time() - 100
    )
    
    # Node B: Conflicting concept (dissonant with context)
    node_b = KnowledgeNode(
        id="concept_beta_dissonant",
        embedding=[-1.0, -0.9, -0.8],  # High conflict
        timestamp=time.time() - 100
    )
    
    engine.add_node(node_a)
    engine.add_node(node_b)
    
    # 3. Define Current Context (Target: [1, 1, 1])
    # This context aligns with Node A but conflicts with Node B
    current_context = [1.0, 1.0, 1.0]
    
    print("--- Before Decay Cycle ---")
    print(f"Node A Weight: {engine.get_node_state('concept_alpha')['weight']}")
    print(f"Node B Weight: {engine.get_node_state('concept_beta_dissonant')['weight']}")
    
    # 4. Apply Decay
    removed = engine.apply_harmonic_decay(current_context, time.time())
    
    print("\n--- After Decay Cycle ---")
    print(f"Node A Weight: {engine.get_node_state('concept_alpha')['weight']} (Should be stable)")
    state_b = engine.get_node_state('concept_beta_dissonant')
    print(f"Node B Weight: {state_b['weight'] if state_b else 'REMOVED'} (Should be significantly decayed or removed)")
    print(f"Removed Nodes: {removed}")