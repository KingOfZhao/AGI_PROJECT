"""
Module: context_universality_filter
Description: Implements algorithms to evaluate and prune 'narrow' cognitive nodes
             based on Context Universality Scores. This module aims to identify
             and filter out overfitted nodes that act as 'isolated islands' by
             calculating semantic entropy and cross-domain reusability.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeDomain(Enum):
    """Enumeration of possible cognitive domains for nodes."""
    LOGIC = "logic"
    LANGUAGE = "language"
    SPATIAL = "spatial"
    EMOTION = "emotion"
    GENERAL = "general"
    UNKNOWN = "unknown"


@dataclass
class CognitiveNode:
    """
    Represents a node in the cognitive graph.
    
    Attributes:
        id: Unique identifier for the node.
        semantic_vector: A list of floats representing the node's semantic meaning.
        activation_history: A list of domain enums where this node was activated.
        connections: IDs of connected nodes.
    """
    id: str
    semantic_vector: List[float]
    activation_history: List[NodeDomain] = field(default_factory=list)
    connections: Set[str] = field(default_factory=set)
    _entropy: Optional[float] = field(default=None, init=False)
    _reusability: Optional[float] = field(default=None, init=False)

    def __post_init__(self):
        """Validate data after initialization."""
        if not isinstance(self.semantic_vector, list) or not all(isinstance(x, (float, int)) for x in self.semantic_vector):
            raise ValueError(f"Node {self.id}: semantic_vector must be a list of numbers.")
        if not isinstance(self.activation_history, list):
            raise ValueError(f"Node {self.id}: activation_history must be a list.")

    @property
    def domain_count(self) -> int:
        """Returns the number of unique domains the node has been activated in."""
        return len(set(self.activation_history))


def _calculate_shannon_entropy(data: List[NodeDomain]) -> float:
    """
    [Helper] Calculate the Shannon entropy of the domain distribution.
    
    High entropy indicates the node is active across many different contexts (General).
    Low entropy indicates the node is active in few specific contexts (Narrow).
    
    Args:
        data: List of domains where the node was activated.
        
    Returns:
        float: The entropy value.
    """
    if not data:
        return 0.0
    
    frequency: Dict[NodeDomain, int] = {}
    for domain in data:
        frequency[domain] = frequency.get(domain, 0) + 1
    
    total = len(data)
    entropy = 0.0
    for count in frequency.values():
        probability = count / total
        if probability > 0:
            entropy -= probability * math.log2(probability)
            
    return entropy


def calculate_contextual_metrics(node: CognitiveNode) -> Dict[str, float]:
    """
    Calculate the semantic entropy and cross-domain reusability for a single node.
    
    This function computes metrics to quantify how 'general' a node is.
    1. Semantic Entropy: Measures the unpredictability of the node's context.
    2. Reusability Score: A normalized score (0-1) of how many unique domains use this node.
    
    Args:
        node: The CognitiveNode to evaluate.
        
    Returns:
        Dict[str, float]: A dictionary containing 'entropy' and 'reusability'.
        
    Raises:
        ValueError: If the node data is invalid.
    """
    logger.debug(f"Calculating metrics for node {node.id}")
    
    try:
        # 1. Calculate Entropy
        entropy = _calculate_shannon_entropy(node.activation_history)
        
        # 2. Calculate Reusability
        # Normalized by the maximum possible entropy (log2(N domains))
        unique_domains = len(set(node.activation_history))
        max_possible_domains = len(NodeDomain) - 1 # Exclude UNKNOWN
        
        # Reusability formula: Combination of domain spread and consistency
        # Here we use a simplified heuristic: 
        # Score = (Unique Domains / Max Possible) * (Log base 2 of Total Activations)
        # This balances breadth (domains) with utility (activations).
        domain_ratio = unique_domains / max_possible_domains if max_possible_domains > 0 else 0
        
        # Penalize nodes with very few total activations (statistical insignificance)
        activation_weight = min(1.0, len(node.activation_history) / 10.0) 
        
        reusability = domain_ratio * activation_weight
        
        logger.info(f"Node {node.id}: Entropy={entropy:.4f}, Reusability={reusability:.4f}")
        
        return {
            "entropy": entropy,
            "reusability": reusability
        }
        
    except Exception as e:
        logger.error(f"Error calculating metrics for node {node.id}: {e}")
        raise


def filter_narrow_nodes(
    nodes: List[CognitiveNode], 
    entropy_threshold: float = 1.5, 
    reusability_threshold: float = 0.2
) -> List[CognitiveNode]:
    """
    Filters and eliminates narrow (overfitted) nodes based on context universality.
    
    A node is considered 'narrow' (an island) if:
    - Its semantic entropy is below the threshold (too predictable/specific).
    - Its reusability score is below the threshold (rarely reused across domains).
    
    Args:
        nodes: A list of CognitiveNode objects to filter.
        entropy_threshold: Minimum entropy required to survive (default: 1.5).
        reusability_threshold: Minimum reusability score required (default: 0.2).
        
    Returns:
        List[CognitiveNode]: A filtered list containing only high-quality, general nodes.
    """
    if not nodes:
        logger.warning("Input node list is empty.")
        return []
        
    filtered_nodes: List[CognitiveNode] = []
    rejected_count = 0
    
    logger.info(f"Starting filtering process on {len(nodes)} nodes.")
    logger.info(f"Thresholds -> Entropy: {entropy_threshold}, Reusability: {reusability_threshold}")
    
    for node in nodes:
        try:
            metrics = calculate_contextual_metrics(node)
            
            # Filtering Logic
            if metrics['entropy'] < entropy_threshold:
                logger.debug(f"Node {node.id} rejected: Low Entropy ({metrics['entropy']:.2f})")
                rejected_count += 1
                continue
                
            if metrics['reusability'] < reusability_threshold:
                logger.debug(f"Node {node.id} rejected: Low Reusability ({metrics['reusability']:.2f})")
                rejected_count += 1
                continue
                
            filtered_nodes.append(node)
            
        except Exception as e:
            logger.error(f"Skipping node {node.id} due to processing error: {e}")
            rejected_count += 1
            
    logger.info(f"Filtering complete. Survivors: {len(filtered_nodes)}, Rejected: {rejected_count}")
    return filtered_nodes


# --- Usage Example ---
if __name__ == "__main__":
    # Create mock data representing nodes with different behaviors
    
    # 1. General Node: High Entropy, used everywhere
    general_history = [NodeDomain.LOGIC, NodeDomain.LANGUAGE, NodeDomain.SPATIAL] * 5
    node_general = CognitiveNode(
        id="node_001_general",
        semantic_vector=[0.9, 0.1, 0.5],
        activation_history=general_history
    )
    
    # 2. Narrow Node (Overfitted): Low Entropy, used only in Logic
    narrow_history = [NodeDomain.LOGIC] * 15
    node_narrow = CognitiveNode(
        id="node_002_narrow",
        semantic_vector=[0.1, 0.8, 0.2],
        activation_history=narrow_history
    )
    
    # 3. Island Node (No reuse): Low Reusability, barely used
    island_history = [NodeDomain.SPATIAL] # Only once
    node_island = CognitiveNode(
        id="node_003_island",
        semantic_vector=[0.5, 0.5, 0.5],
        activation_history=island_history
    )

    all_nodes = [node_general, node_narrow, node_island]
    
    print("-" * 60)
    print("Running Context Universality Filter...")
    print("-" * 60)
    
    # Run the filter
    survivors = filter_narrow_nodes(all_nodes, entropy_threshold=1.0, reusability_threshold=0.3)
    
    print("\nSurviving Nodes:")
    for n in survivors:
        print(f"- ID: {n.id}")

    # Expected Output:
    # Running Context Universality Filter...
    # ... (logs) ...
    # Surviving Nodes:
    # - ID: node_001_general
    # (The narrow and island nodes should be filtered out)