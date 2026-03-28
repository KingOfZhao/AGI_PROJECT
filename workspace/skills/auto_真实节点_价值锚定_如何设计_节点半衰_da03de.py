"""
Module: auto_真实节点_价值锚定_如何设计_节点半衰_da03de
Description: [Real Node - Value Anchoring] Designing a 'Node Half-Life' algorithm
             to mitigate knowledge aging in AGI systems.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """
    Represents a knowledge node in the AGI graph.

    Attributes:
        node_id: Unique identifier for the node.
        content: The actual knowledge content (e.g., Python 2.7 syntax).
        last_verified_time: Timestamp when the node was last confirmed true.
        creation_time: Timestamp when the node was created.
        reference_count: Number of times other nodes/processes refer to this.
        neighbor_ids: List of IDs of connected nodes.
        initial_confidence: Starting confidence score (0.0 to 1.0).
    """
    node_id: str
    content: str
    last_verified_time: datetime
    creation_time: datetime
    reference_count: int
    neighbor_ids: List[str]
    initial_confidence: float = 1.0


class NodeDecayManager:
    """
    Manages the lifecycle and decay of knowledge nodes.
    """

    def __init__(self, decay_rate_config: Optional[Dict] = None):
        """
        Initialize the manager with decay parameters.

        Args:
            decay_rate_config: Configuration for half-life calculations.
        """
        self.config = decay_rate_config or {
            "base_half_life_days": 365,      # Standard knowledge (1 year)
            "tech_stack_penalty": 0.5,       # Tech stacks rot faster
            "reference_boost_factor": 0.1,   # How much引用 slows decay
            "neighbor_weight": 0.3           # Impact of neighbor survival rate
        }
        logger.info("NodeDecayManager initialized with config: %s", self.config)

    def _validate_node(self, node: KnowledgeNode) -> bool:
        """
        Validate node data integrity.

        Args:
            node: The node to validate.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not node.node_id:
            raise ValueError("Node ID cannot be empty")
        if node.initial_confidence < 0 or node.initial_confidence > 1:
            raise ValueError(f"Invalid confidence {node.initial_confidence} for node {node.node_id}")
        if node.last_verified_time > datetime.now():
            raise ValueError(f"Future verification time detected for node {node.node_id}")
        return True

    def calculate_time_decay_factor(self, node: KnowledgeNode) -> float:
        """
        Core Function 1: Calculate decay based on time and引用 frequency.
        
        Formula:
        decay = 0.5 ^ (elapsed_time / effective_half_life)
        where effective_half_life = base_half_life * (1 + log(ref_count))

        Args:
            node: The target knowledge node.

        Returns:
            A float representing the time-based decay multiplier (0.0 to 1.0).
        """
        try:
            self._validate_node(node)
            
            now = datetime.now()
            elapsed_seconds = (now - node.last_verified_time).total_seconds()
            elapsed_days = elapsed_seconds / (60 * 60 * 24)
            
            # Prevent division by zero or log of zero
            safe_ref_count = max(1, node.reference_count)
            
            # Calculate dynamic half-life based on引用 frequency
            # High引用 count increases half-life (knowledge stays relevant longer)
            dynamic_half_life = self.config['base_half_life_days'] * (
                1 + math.log10(safe_ref_count) * self.config['reference_boost_factor']
            )
            
            if dynamic_half_life <= 0:
                logger.warning(f"Calculated negative half-life for node {node.node_id}, defaulting to base.")
                dynamic_half_life = self.config['base_half_life_days']

            decay_factor = 0.5 ** (elapsed_days / dynamic_half_life)
            
            logger.debug(f"Time decay for {node.node_id}: {decay_factor:.4f} (Days: {elapsed_days:.1f})")
            return decay_factor

        except ValueError as ve:
            logger.error(f"Validation failed for node {node.node_id}: {ve}")
            return 0.0 # Return 0 confidence for invalid data
        except Exception as e:
            logger.exception(f"Unexpected error calculating time decay for {node.node_id}: {e}")
            raise

    def calculate_neighbor_survival_factor(self, node: KnowledgeNode, global_graph: Dict[str, float]) -> float:
        """
        Core Function 2: Adjust decay based on the 'health' of surrounding nodes.
        
        If neighbors (context) are decaying, this node likely should too.

        Args:
            node: The target node.
            global_graph: A dictionary mapping all node_ids to their current confidence scores.

        Returns:
            A float representing the context-based multiplier (0.0 to 1.0).
        """
        if not node.neighbor_ids:
            return 1.0 # No neighbors, no context penalty

        total_neighbors = len(node.neighbor_ids)
        active_neighbors = 0
        sum_confidence = 0.0

        for neighbor_id in node.neighbor_ids:
            neighbor_score = global_graph.get(neighbor_id)
            if neighbor_score is not None and neighbor_score > 0.1: # Threshold for 'alive'
                active_neighbors += 1
                sum_confidence += neighbor_score

        survival_rate = active_neighbors / total_neighbors
        avg_confidence = sum_confidence / active_neighbors if active_neighbors > 0 else 0.0
        
        # Combine survival rate and average confidence
        context_factor = (survival_rate + avg_confidence) / 2.0
        
        # Apply weight
        weighted_factor = 1.0 - (self.config['neighbor_weight'] * (1.0 - context_factor))
        
        logger.debug(f"Neighbor factor for {node.node_id}: {weighted_factor:.4f} (Rate: {survival_rate:.2f})")
        return max(0.0, min(1.0, weighted_factor))

    def compute_final_confidence(self, node: KnowledgeNode, global_graph: Dict[str, float]) -> float:
        """
        Helper Function: Aggregates time decay and context factors.
        
        Args:
            node: The target node.
            global_graph: The current state of the knowledge graph.

        Returns:
            The final adjusted confidence score.
        """
        try:
            time_decay = self.calculate_time_decay_factor(node)
            neighbor_factor = self.calculate_neighbor_survival_factor(node, global_graph)
            
            final_score = node.initial_confidence * time_decay * neighbor_factor
            
            logger.info(f"Final Confidence for {node.node_id}: {final_score:.4f}")
            return final_score
        except Exception as e:
            logger.error(f"Failed to compute final confidence: {e}")
            return 0.0


def main():
    """
    Usage Example
    """
    # 1. Setup Data
    now = datetime.now()
    
    # Node A: Old, high reference, verified long ago (Obsolete Tech)
    node_a = KnowledgeNode(
        node_id="tech_flash_2010",
        content="Flash Player Optimization Techniques",
        last_verified_time=now - timedelta(days=3650), # 10 years ago
        creation_time=now - timedelta(days=5000),
        reference_count=50,
        neighbor_ids=["html4", "actionscript"],
        initial_confidence=1.0
    )

    # Node B: Recent, low reference (New Theory)
    node_b = KnowledgeNode(
        node_id="llm_transformer_2023",
        content="Attention Mechanism Basics",
        last_verified_time=now - timedelta(days=30), # 1 month ago
        creation_time=now - timedelta(days=60),
        reference_count=5,
        neighbor_ids=["pytorch", "nlp_basics"],
        initial_confidence=1.0
    )
    
    # Simulate Global Graph State (Neighbors are dead for A, alive for B)
    mock_graph_state = {
        "html4": 0.1,
        "actionscript": 0.05,
        "pytorch": 0.95,
        "nlp_basics": 0.90
    }

    # 2. Initialize Manager
    manager = NodeDecayManager(decay_rate_config={
        "base_half_life_days": 730, # 2 years base half-life
        "reference_boost_factor": 0.2,
        "neighbor_weight": 0.4
    })

    # 3. Calculate Scores
    print("--- Processing Old Node ---")
    score_a = manager.compute_final_confidence(node_a, mock_graph_state)
    print(f"Node: {node_a.node_id} | Final Score: {score_a:.4f}")
    
    print("\n--- Processing New Node ---")
    score_b = manager.compute_final_confidence(node_b, mock_graph_state)
    print(f"Node: {node_b.node_id} | Final Score: {score_b:.4f}")

if __name__ == "__main__":
    main()