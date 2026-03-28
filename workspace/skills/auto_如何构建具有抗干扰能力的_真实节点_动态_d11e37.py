"""
Module: real_node_dynamic_scorer
Description: Implements an entropy-reducing, anti-interference dynamic scoring algorithm
             for 'Real Nodes' in an AGI cognitive system. It prioritizes nodes validated
             through human-machine symbiotic loops over purely logical derivations.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RealNodeScorer")


@dataclass
class CognitiveNode:
    """
    Represents a single node in the cognitive graph.
    
    Attributes:
        id: Unique identifier for the node.
        creation_time: Timestamp when the node was created.
        last_validated_time: Timestamp of the last successful human validation.
        validation_count: Number of successful human validations (positive feedback).
        falsification_count: Number of failed validations (negative feedback).
        derivation_depth: Logical steps from an axiom (0 = axiom/observed, >0 = derived).
        base_weight: Initial logical weight.
    """
    id: str
    creation_time: datetime
    last_validated_time: Optional[datetime] = None
    validation_count: int = 0
    falsification_count: int = 0
    derivation_depth: int = 0
    base_weight: float = 0.5


class EntropyScoringEngine:
    """
    Calculates dynamic weights for nodes using an entropy-decreasing mechanism.
    
    This engine prioritizes nodes that have survived 'falsification' attempts in 
    real-world scenarios (Human-AI loops) and penalizes unverified logical derivations.
    """

    def __init__(self, 
                 decay_rate: float = 0.05, 
                 trust_threshold: float = 1.5,
                 max_entropy: float = 2.0):
        """
        Initialize the engine.
        
        Args:
            decay_rate: Lambda for time decay calculation.
            trust_threshold: Multiplier for validation impact.
            max_entropy: Maximum entropy penalty cap.
        """
        if decay_rate <= 0 or trust_threshold <= 0:
            raise ValueError("Parameters must be positive.")
        self.decay_rate = decay_rate
        self.trust_threshold = trust_threshold
        self.max_entropy = max_entropy
        logger.info("EntropyScoringEngine initialized with decay=%f", decay_rate)

    def _calculate_time_decay(self, last_time: Optional[datetime], current_time: datetime) -> float:
        """
        Helper function to calculate time-based decay factor.
        Returns a value between 0 and 1. Recent activity -> 1, Old activity -> 0.
        """
        if last_time is None:
            return 0.1  # Minimal baseline for never-validated nodes
        
        delta_seconds = (current_time - last_time).total_seconds()
        if delta_seconds < 0:
            logger.warning("Future timestamp detected for validation time.")
            return 1.0
            
        # Exponential decay: e^(-lambda * t)
        decay_factor = math.exp(-self.decay_rate * (delta_seconds / 3600)) # normalized by hour
        return max(0.0, min(1.0, decay_factor))

    def _calculate_entropy_penalty(self, node: CognitiveNode) -> float:
        """
        Helper function to calculate entropy based on derivation depth.
        Purely derived nodes have higher entropy (uncertainty).
        """
        # Entropy grows logarithmically with depth
        penalty = math.log1p(node.derivation_depth)
        return min(self.max_entropy, penalty)

    def calculate_dynamic_weight(self, 
                                 node: CognitiveNode, 
                                 current_time: datetime,
                                 context_boost: float = 1.0) -> float:
        """
        Core Function 1: Computes the final anti-interference weight for a node.
        
        Formula:
        W = (Base * Context) * (Validation_Score / (Entropy + 1)) * Time_Decay
        
        Args:
            node: The CognitiveNode to evaluate.
            current_time: The reference time 'now'.
            context_boost: A multiplier based on current task context (default 1.0).
            
        Returns:
            float: The normalized dynamic weight (0.0 to 10.0).
        
        Raises:
            ValueError: If node data is invalid.
        """
        if node.validation_count < 0 or node.falsification_count < 0:
            logger.error("Negative counts detected in node %s", node.id)
            raise ValueError("Validation counts cannot be negative")

        # 1. Validation Score: Bayesian-like confidence
        # We add a small epsilon to avoid division by zero
        total_interactions = node.validation_count + node.falsification_count + 1e-5
        success_ratio = node.validation_count / total_interactions
        
        # Interaction volume bonus (logarithmic scaling)
        volume_bonus = math.log1p(node.validation_count)
        
        val_score = success_ratio * (1 + volume_bonus) * self.trust_threshold

        # 2. Entropy Penalty
        entropy = self._calculate_entropy_penalty(node)
        
        # 3. Time Decay
        recency = self._calculate_time_decay(node.last_validated_time, current_time)
        
        # 4. Synthesis
        # We divide by (entropy + 1) to ensure we don't boost bad nodes, but penalize uncertain ones.
        raw_weight = (node.base_weight * context_boost) * (val_score / (entropy + 1.0))
        
        # Apply time decay to the final result
        final_weight = raw_weight * recency
        
        # Boundary Check
        final_weight = max(0.0, min(10.0, final_weight))
        
        logger.debug(f"Node {node.id}: ValScore={val_score:.2f}, Entropy={entropy:.2f}, Recency={recency:.2f}, Final={final_weight:.2f}")
        return final_weight

    def update_graph_weights(self, 
                             graph: Dict[str, CognitiveNode], 
                             current_time: datetime,
                             active_context_ids: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Core Function 2: Iterates over a graph of nodes and updates their weights.
        
        This mimics the 'Global Cognitive Update' cycle.
        
        Args:
            graph: A dictionary mapping node IDs to CognitiveNode objects.
            current_time: Current timestamp.
            active_context_ids: List of node IDs relevant to the current context.
            
        Returns:
            Dict[str, float]: A mapping of Node ID -> Updated Dynamic Weight.
        """
        if not graph:
            logger.warning("Empty graph provided for update.")
            return {}

        updated_weights: Dict[str, float] = {}
        active_set = set(active_context_ids or [])

        logger.info(f"Starting weight update for {len(graph)} nodes.")
        
        for node_id, node in graph.items():
            try:
                # Determine context boost
                boost = 1.5 if node_id in active_set else 1.0
                
                weight = self.calculate_dynamic_weight(node, current_time, boost)
                updated_weights[node_id] = weight
                
            except Exception as e:
                logger.error(f"Failed to update node {node_id}: {e}")
                # Fallback to base weight or 0
                updated_weights[node_id] = node.base_weight

        logger.info("Graph weight update complete.")
        return updated_weights


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Engine
    engine = EntropyScoringEngine(decay_rate=0.1)
    
    # 2. Create Mock Data
    now = datetime.now()
    
    # Node A: Validated frequently by humans (High Trust)
    node_a = CognitiveNode(
        id="skill_python_101",
        creation_time=now - timedelta(days=30),
        last_validated_time=now - timedelta(hours=1),
        validation_count=150,
        falsification_count=5,
        derivation_depth=0,
        base_weight=1.0
    )
    
    # Node B: Purely derived logic, never tested (High Entropy)
    node_b = CognitiveNode(
        id="concept_theoretical_physics_x",
        creation_time=now - timedelta(days=10),
        last_validated_time=None, # Never validated
        validation_count=0,
        falsification_count=0,
        derivation_depth=10, # Deeply derived
        base_weight=1.0
    )
    
    # Node C: Validated long time ago (Time Decay)
    node_c = CognitiveNode(
        id="legacy_system_rule",
        creation_time=now - timedelta(days=365),
        last_validated_time=now - timedelta(days=300),
        validation_count=50,
        falsification_count=2,
        derivation_depth=2,
        base_weight=1.0
    )
    
    graph = {
        node_a.id: node_a,
        node_b.id: node_b,
        node_c.id: node_c
    }
    
    # 3. Run Update
    # Assume Node A is currently in 'context' (user is coding)
    context = ["skill_python_101"]
    scores = engine.update_graph_weights(graph, now, context)
    
    # 4. Output Results
    print("\n--- Dynamic Scoring Results ---")
    for nid, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        print(f"Node: {nid:<30} | Score: {score:.4f}")
    
    # Expected: Node A (High validation, low entropy, context boost) > Node C > Node B (High entropy, no validation)