"""
Advanced Semantic Collapse Detection Module for AGI Cognitive Networks.

This module implements a 'Functional Differentiation' validation mechanism to prevent
'Semantic Collapse' during the automatic expansion of cognitive networks. It ensures
that new candidate nodes provide distinct decision behaviors or utility in specific
contexts, rather than merely acting as synonyms for existing nodes.

Key Concepts:
- Semantic Collapse: When a knowledge graph grows in size but not in utility due to
  redundancy (e.g., adding "automobile" when "car" exists without distinguishing context).
- Functional Differentiation: A validation strategy where a node is accepted only if
  it alters the decision state or embedding topology significantly compared to existing nodes.

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Enumeration of possible statuses for a candidate node."""
    ACCEPTED = "accepted"
    REJECTED_COLLAPSE = "rejected_semantic_collapse"
    REJECTED_NOVELTY = "rejected_low_novelty"
    ERROR = "processing_error"


@dataclass
class CognitiveNode:
    """
    Represents a node in the cognitive network.
    
    Attributes:
        id: Unique identifier (usually UUID).
        concept: The semantic concept (e.g., "Vehicle").
        embedding: Vector representation of the concept.
        context_tags: Set of contexts where this node is active (e.g., {"transport", "logistics"}).
    """
    id: str
    concept: str
    embedding: List[float]
    context_tags: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not isinstance(self.embedding, list):
            raise TypeError("Embedding must be a list of floats.")
        if not isinstance(self.context_tags, set):
            self.context_tags = set(self.context_tags)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Helper function to calculate Cosine Similarity between two vectors.
    
    Args:
        vec_a: First vector.
        vec_b: Second vector.
        
    Returns:
        float: Cosine similarity score between -1 and 1.
        
    Raises:
        ValueError: If vectors are empty or lengths do not match.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be of the same dimension.")
    if len(vec_a) == 0:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a ** 2 for a in vec_a) ** 0.5
    norm_b = sum(b ** 2 for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def check_functional_differentiation(
    candidate_node: CognitiveNode,
    existing_nodes: List[CognitiveNode],
    similarity_threshold: float = 0.95,
    min_context_overlap: float = 0.0
) -> Tuple[bool, str]:
    """
    Core Function 1: Functional Differentiation Validator.
    
    Validates whether a candidate node functionally differs from existing nodes.
    It checks two dimensions:
    1. Semantic Distance: Is the vector representation too close to an existing node?
    2. Contextual Utility: Does it serve a different purpose or context?
    
    If a candidate is semantically similar (above threshold) AND shares context,
    it is considered "Collapsed".
    
    Args:
        candidate_node: The node proposed for addition.
        existing_nodes: List of nodes currently in the network.
        similarity_threshold: Threshold for cosine similarity to consider nodes identical (0.0 to 1.0).
        min_context_overlap: Jaccard index threshold for context similarity.
        
    Returns:
        Tuple[bool, str]: (is_valid, reason)
    """
    logger.info(f"Validating candidate node: {candidate_node.concept} (ID: {candidate_node.id})")
    
    if not existing_nodes:
        return True, "Network is empty, first node accepted."

    try:
        # Input Validation
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")

        for existing in existing_nodes:
            # 1. Calculate Semantic Similarity
            sem_sim = _cosine_similarity(candidate_node.embedding, existing.embedding)
            
            # 2. Calculate Context Overlap (Jaccard Index)
            intersection = len(candidate_node.context_tags.intersection(existing.context_tags))
            union = len(candidate_node.context_tags.union(existing.context_tags))
            ctx_sim = intersection / union if union > 0 else 0.0

            # Semantic Collapse Logic:
            # If vectors are nearly identical AND contexts are heavily overlapping,
            # the new node adds no functional value.
            if sem_sim >= similarity_threshold:
                logger.warning(f"High semantic similarity detected ({sem_sim:.4f}) with existing node '{existing.concept}'")
                
                # Exception: If contexts are very different, it might be polysemy (valid), not collapse.
                # For this strict validator, if sem_sim is high, we require ctx_sim to be LOW to accept.
                # If ctx_sim is also high, it is definitely a duplicate.
                if ctx_sim > min_context_overlap:
                    reason = (f"Semantic Collapse: Similar to '{existing.concept}' "
                              f"(Sim: {sem_sim:.2f}, Ctx: {ctx_sim:.2f})")
                    logger.info(f"Rejection: {reason}")
                    return False, reason
                
        logger.info(f"Candidate '{candidate_node.concept}' passed functional differentiation check.")
        return True, "Node provides functional differentiation."

    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return False, f"Internal Error: {str(e)}"


def integrate_node_to_network(
    candidate: CognitiveNode,
    network_graph: Dict[str, CognitiveNode],
    context_state: Dict[str, float]
) -> NodeStatus:
    """
    Core Function 2: Network Integration Manager.
    
    Attempts to integrate a validated node into the cognitive network.
    This function simulates the 'Decision Behavior' aspect. It checks if adding
    the node changes the outcome of a hypothetical query based on the current context.
    
    Args:
        candidate: The candidate CognitiveNode.
        network_graph: The current network (dictionary mapping ID to Node).
        context_state: A dictionary representing the current activation state 
                       (query context), e.g., {"medical": 0.9, "legal": 0.1}.
    
    Returns:
        NodeStatus: The outcome of the integration attempt.
    """
    logger.info(f"Attempting integration for: {candidate.concept}")
    
    # Step 1: Validate format and data integrity
    if not isinstance(candidate, CognitiveNode):
        logger.error("Invalid candidate type provided.")
        return NodeStatus.ERROR
    
    if candidate.id in network_graph:
        logger.warning(f"Node ID {candidate.id} already exists.")
        return NodeStatus.REJECTED_COLLAPSE

    # Step 2: Perform Functional Differentiation Check
    existing_list = list(network_graph.values())
    is_valid, reason = check_functional_differentiation(
        candidate, 
        existing_list,
        similarity_threshold=0.90 # High bar for AGI memory efficiency
    )

    if not is_valid:
        logger.info(f"Integration aborted: {reason}")
        return NodeStatus.REJECTED_COLLAPSE

    # Step 3: Decision Behavior Simulation (Mock)
    # We verify that the node is relevant to the current active context before adding.
    # This prevents adding nodes that are valid but irrelevant to the current AGI task loop.
    relevance_score = 0.0
    for tag in candidate.context_tags:
        if tag in context_state:
            relevance_score += context_state[tag]
    
    if relevance_score < 0.5:
        logger.info(f"Node rejected due to low relevance to current context: {relevance_score}")
        return NodeStatus.REJECTED_NOVELTY

    # Step 4: Integration
    try:
        network_graph[candidate.id] = candidate
        logger.info(f"Successfully integrated node {candidate.id} into network.")
        return NodeStatus.ACCEPTED
    except Exception as e:
        logger.critical(f"Failed to write to network graph: {e}")
        return NodeStatus.ERROR


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup initial network
    knowledge_base: Dict[str, CognitiveNode] = {}
    
    # 2. Define existing nodes
    node_car = CognitiveNode(
        id="n1",
        concept="Car",
        embedding=[0.9, 0.1, 0.1], # Simplified 3D vector
        context_tags={"transport", "personal"}
    )
    knowledge_base[node_car.id] = node_car
    
    # 3. Define current context (AGI is thinking about transport)
    current_context = {"transport": 0.8, "logistics": 0.6, "medical": 0.1}
    
    # Case A: Semantic Collapse (Synonym)
    # "Automobile" is semantically identical to "Car" and shares context
    node_auto = CognitiveNode(
        id="n2",
        concept="Automobile",
        embedding=[0.91, 0.11, 0.09], # Very close to Car
        context_tags={"transport", "personal"}
    )
    
    status = integrate_node_to_network(node_auto, knowledge_base, current_context)
    print(f"Result for '{node_auto.concept}': {status.value}") 
    # Expected: rejected_semantic_collapse

    # Case B: Functional Differentiation (Polysemy/New Concept)
    # "Bank" is being added. It is close to "Car" in embedding space (hypothetically),
    # OR completely different, but has distinct context "finance".
    node_bank = CognitiveNode(
        id="n3",
        concept="Bank",
        embedding=[0.1, 0.9, 0.1],
        context_tags={"finance", "business"}
    )
    
    # Update context to make finance relevant
    financial_context = {"finance": 0.9, "transport": 0.1}
    
    status = integrate_node_to_network(node_bank, knowledge_base, financial_context)
    print(f"Result for '{node_bank.concept}': {status.value}")
    # Expected: accepted
    
    # Case C: Low Novelty/Relevance
    # A valid node but irrelevant to current context
    node_rock = CognitiveNode(
        id="n4",
        concept="Rock",
        embedding=[0.5, 0.5, 0.0],
        context_tags={"geology"}
    )
    
    status = integrate_node_to_network(node_rock, knowledge_base, financial_context)
    print(f"Result for '{node_rock.concept}': {status.value}")
    # Expected: rejected_low_novelty (or accepted if relevance check is skipped in logic, 
    # but here it depends on context_state). Based on logic: relevance < 0.5 -> REJECTED_NOVELTY