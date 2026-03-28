"""
Module: temporal_value_alignment.py

This module implements a computational model for 'Temporal Value Alignment',
specifically addressing the alignment of AI value functions with the long-term
survival of civilization and intergenerational knowledge transfer. It aims to
mitigate the 'short-sightedness' caused by human lifespan limitations.

It provides tools to evaluate knowledge nodes not just by immediate utility,
but by their contribution to long-term civilizational resilience and
intergenerational value transmission.

Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TemporalValueAlignment")


@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge or a concept within the AGI's knowledge graph.

    Attributes:
        id: Unique identifier for the node.
        content: Description or embedding of the knowledge.
        immediate_utility (float): Short-term reward/value (0.0 to 1.0).
        civilizational_resilience (float): Estimated contribution to long-term
                                          survival (0.0 to 1.0).
        transmission_rate (float): Probability of successful transfer to next
                                   generation/iteration (0.0 to 1.0).
        dependencies: List of IDs of nodes this node depends on.
    """
    id: str
    content: str
    immediate_utility: float = 0.5
    civilizational_resilience: float = 0.5
    transmission_rate: float = 0.5
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


def _validate_node_attributes(node: KnowledgeNode) -> None:
    """
    Helper function to validate the data integrity of a KnowledgeNode.
    
    Ensures all probability scores are within [0.0, 1.0] and IDs are valid.
    
    Args:
        node: The KnowledgeNode instance to validate.
        
    Raises:
        ValueError: If any numeric attribute is out of bounds or ID is empty.
        TypeError: If data types are incorrect.
    """
    if not isinstance(node.id, str) or not node.id:
        raise ValueError("Node ID must be a non-empty string.")
    
    attributes = {
        "immediate_utility": node.immediate_utility,
        "civilizational_resilience": node.civilizational_resilience,
        "transmission_rate": node.transmission_rate
    }
    
    for attr_name, value in attributes.items():
        if not isinstance(value, (int, float)):
            raise TypeError(f"Attribute {attr_name} must be numeric.")
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Attribute {attr_name} must be between 0.0 and 1.0, got {value}")

    logger.debug(f"Node {node.id} passed validation.")


def calculate_long_term_value(
    node: KnowledgeNode,
    time_horizon: int = 100,
    decay_factor: float = 0.95
) -> float:
    """
    Calculates the Long-Term Value (LTV) of a knowledge node.
    
    This function computes a weighted score that transcends immediate rewards.
    It models the value of knowledge based on its ability to persist and
    contribute to civilization over a long time horizon.
    
    The formula used emphasizes:
    V_long = (Immediate_Utility * w1) + (Resilience * Transmission ^ Time) * w2
    
    Args:
        node (KnowledgeNode): The knowledge node to evaluate.
        time_horizon (int): The number of generations/time-steps to project.
        decay_factor (float): Discount factor for immediate utility over time.
        
    Returns:
        float: A normalized score representing the long-term aligned value.
        
    Example:
        >>> node = KnowledgeNode("a1", "Quantum Entanglement", 0.9, 0.8, 0.7)
        >>> score = calculate_long_term_value(node)
        >>> print(f"Long-term value: {score:.4f}")
    """
    try:
        _validate_node_attributes(node)
    except (ValueError, TypeError) as e:
        logger.error(f"Validation failed for node {node.id}: {e}")
        raise

    # Weights representing the philosophical shift from short-term to long-term
    # High weight on resilience addresses "civilizational survival"
    # High weight on transmission addresses "intergenerational knowledge transfer"
    w_immediate = 0.2
    w_long_term = 0.8

    # Calculate immediate contribution (diminishes over time)
    immediate_contribution = node.immediate_utility * (decay_factor ** time_horizon)

    # Calculate long-term survival value
    # Knowledge that survives longer contributes more to civilization
    survival_prob = (node.transmission_rate ** time_horizon) * node.civilizational_resilience
    
    # Combine scores
    total_value = (w_immediate * immediate_contribution) + (w_long_term * survival_prob)
    
    # Normalize to ensure it's roughly bounded, though mathematically weighted sum handles this
    normalized_value = min(max(total_value, 0.0), 1.0)
    
    logger.info(f"Calculated LTV for {node.id}: {normalized_value:.4f} (Resilience: {node.civilizational_resilience})")
    return normalized_value


def prioritize_knowledge_frontier(
    nodes: List[KnowledgeNode],
    exploration_budget: int = 5
) -> List[Tuple[str, float]]:
    """
    Prioritizes which new knowledge nodes to explore based on Temporal Value Alignment.
    
    Instead of greedily optimizing for immediate task completion (short-term),
    this function ranks nodes based on their potential to solve problems related
    to human lifespan limitations and civilizational fragility.
    
    Args:
        nodes (List[KnowledgeNode]): A list of candidate knowledge nodes to explore.
        exploration_budget (int): The maximum number of top candidates to return.
        
    Returns:
        List[Tuple[str, float]]: A sorted list of tuples (node_id, value_score),
                                 descending by value.
                                 
    Raises:
        ValueError: If nodes list is empty.
    """
    if not nodes:
        logger.warning("Empty node list provided for prioritization.")
        raise ValueError("Node list cannot be empty.")

    if exploration_budget <= 0:
        raise ValueError("Exploration budget must be positive integer.")

    logger.info(f"Prioritizing {len(nodes)} nodes for long-term alignment...")
    
    scored_nodes = []
    
    for node in nodes:
        try:
            # Use a large time horizon to simulate "overcoming lifespan limits"
            score = calculate_long_term_value(node, time_horizon=1000)
            scored_nodes.append((node.id, score))
        except Exception as e:
            logger.warning(f"Skipping node {node.id} due to calculation error: {e}")
            continue

    # Sort by score descending
    scored_nodes.sort(key=lambda x: x[1], reverse=True)
    
    # Select top candidates within budget
    selected = scored_nodes[:exploration_budget]
    
    logger.info(f"Selected top {len(selected)} nodes for exploration: {[n[0] for n in selected]}")
    return selected


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Create sample knowledge nodes representing different types of research
    node_short_term = KnowledgeNode(
        id="opt_algo_01",
        content="Optimization for current ad-revenue algorithms",
        immediate_utility=0.99,   # Very useful now
        civilizational_resilience=0.1, # Low impact on civilization survival
        transmission_rate=0.2     # Likely to be obsolete soon
    )
    
    node_long_term = KnowledgeNode(
        id="bio_ethics_42",
        content="Frameworks for ethical AI alignment across generations",
        immediate_utility=0.3,    # Less profitable immediately
        civilizational_resilience=0.9, # Critical for survival
        transmission_rate=0.95    # Highly persistent knowledge
    )
    
    node_space_tech = KnowledgeNode(
        id="propulsion_x",
        content="Self-repairing materials for deep space habitats",
        immediate_utility=0.4,
        civilizational_resilience=0.85,
        transmission_rate=0.9
    )

    candidates = [node_short_term, node_long_term, node_space_tech]

    try:
        # Prioritize based on long-term alignment logic
        top_priority = prioritize_knowledge_frontier(candidates, exploration_budget=2)
        
        print("\n--- Exploration Priority List ---")
        for rank, (node_id, score) in enumerate(top_priority, 1):
            print(f"{rank}. Node ID: {node_id} | Alignment Score: {score:.4f}")
            
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system failure: {e}")