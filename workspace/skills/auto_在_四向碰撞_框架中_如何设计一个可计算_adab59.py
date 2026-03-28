"""
Module: cross_domain_isomorphism.py

This module implements a computable 'Cross-Domain Abstraction Metric' within a 
'Four-Way Collision' cognitive framework. It is designed to quantify the structural 
alignment potential between two heterogeneous domain nodes (e.g., Biological Cells 
vs. Software Microservices).

The core philosophy is to move beyond simple semantic keyword matching and instead
focus on 'Structural Isomorphism'—measuring how similarly two entities behave,
connect, and function within their respective environments.

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Boundaries ---
SIMILARITY_MIN = 0.0
SIMILARITY_MAX = 1.0
WEIGHT_DEFAULT = 1.0
VECTOR_DIMENSION = 8  # Dimensionality of the structural embedding space


@dataclass
class DomainNode:
    """
    Represents a node in a specific knowledge domain.
    
    Attributes:
        id: Unique identifier for the node.
        domain: The domain this node belongs to (e.g., 'biology', 'software').
        features: A dictionary of quantitative structural features.
        connections: List of connected node IDs (for structure analysis).
        semantic_vector: An optional high-dimensional vector representing semantic meaning.
    """
    id: str
    domain: str
    features: Dict[str, float] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)
    semantic_vector: Optional[List[float]] = field(default=None)

    def __post_init__(self):
        """Validate data types after initialization."""
        if not isinstance(self.features, dict):
            raise ValueError("Features must be a dictionary.")
        if not isinstance(self.connections, list):
            raise ValueError("Connections must be a list.")


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Helper function to normalize a value between 0 and 1.
    
    Args:
        value: The value to normalize.
        min_val: The minimum possible value.
        max_val: The maximum possible value.
        
    Returns:
        Normalized float between 0 and 1.
    """
    if max_val <= min_val:
        return 0.0
    clamped_val = max(min_val, min(value, max_val))
    return (clamped_val - min_val) / (max_val - min_val)


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Helper function to calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector.
        vec2: Second vector.
        
    Returns:
        Cosine similarity score between -1 and 1 (clamped to 0-1 for distance).
    """
    if len(vec1) != len(vec2):
        logger.error("Vector dimension mismatch in cosine similarity calculation.")
        raise ValueError("Vectors must be of the same dimension.")
    
    dot_product = sum(p * q for p, q in zip(vec1, vec2))
    magnitude = math.sqrt(sum(p**2 for p in vec1)) * math.sqrt(sum(q**2 for q in vec2))
    
    if magnitude == 0:
        return 0.0
    
    # Normalize to 0-1 range (since we care about alignment, not direction opposition)
    return (dot_product / magnitude + 1) / 2


def calculate_structural_isomorphism(node_a: DomainNode, node_b: DomainNode) -> float:
    """
    Calculates the structural similarity between two nodes based on their topological 
    and functional features.
    
    This function extracts normalized features (e.g., 'connectivity_degree', 
    'centrality', 'entropy') and computes a weighted similarity score. It ignores 
    the 'semantic' meaning and focuses on the 'shape' of the knowledge.
    
    Args:
        node_a: The first domain node.
        node_b: The second domain node.
        
    Returns:
        A float score between 0.0 and 1.0 representing structural alignment.
        
    Raises:
        KeyError: If required structural features are missing.
    """
    logger.info(f"Calculating structural isomorphism between {node_a.id} and {node_b.id}")
    
    # Define weights for different structural aspects
    # These could be dynamic in a full AGI system
    feature_weights = {
        'connectivity_ratio': 0.4,
        'internal_complexity': 0.3,
        'interaction_frequency': 0.3
    }
    
    total_score = 0.0
    total_weight = 0.0
    
    try:
        for feature, weight in feature_weights.items():
            val_a = node_a.features.get(feature)
            val_b = node_b.features.get(feature)
            
            if val_a is None or val_b is None:
                logger.warning(f"Missing feature '{feature}' for comparison. Skipping.")
                continue
                
            # Calculate absolute difference (lower is better), then invert to similarity
            # diff is 0.0 (identical) to 1.0 (max different)
            diff = abs(val_a - val_b) 
            similarity = 1.0 - diff
            
            total_score += similarity * weight
            total_weight += weight
            
    except Exception as e:
        logger.error(f"Error during structural calculation: {e}")
        raise

    if total_weight == 0:
        return 0.0
    
    normalized_score = total_score / total_weight
    return normalized_score


def compute_cross_domain_abstraction(
    source_node: DomainNode, 
    target_node: DomainNode, 
    context_vectors: Optional[Dict[str, List[float]]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Main AGI Skill Function: Computes the 'Cross-Domain Abstraction Metric'.
    
    This metric quantifies the potential for 'Left-Right Cross-Domain Overlap' within 
    the Four-Way Collision framework. It combines structural isomorphism (shape) with 
    optional semantic alignment vectors (if provided).
    
    The formula is roughly:
    Score = w1 * Structural_Isomorphism + w2 * Semantic_Alignment
    
    Args:
        source_node: The node from the source domain (e.g., Biology).
        target_node: The node from the target domain (e.g., Software).
        context_vectors: Optional dictionary containing alignment vectors for context.
        
    Returns:
        A tuple containing:
        - metric_score (float): The final cross-domain potential score (0.0 to 1.0).
        - metadata (Dict): Diagnostic information explaining the score.
        
    Example:
        >>> bio_node = DomainNode(id="cell_1", domain="bio", features={"connectivity_ratio": 0.8})
        >>> soft_node = DomainNode(id="service_1", domain="it", features={"connectivity_ratio": 0.75})
        >>> score, meta = compute_cross_domain_abstraction(bio_node, soft_node)
        >>> print(f"Abstraction Potential: {score:.3f}")
    """
    logger.info(f"Initiating Cross-Domain Abstraction calculation: {source_node.id} -> {target_node.id}")
    
    # 1. Input Validation
    if not isinstance(source_node, DomainNode) or not isinstance(target_node, DomainNode):
        logger.error("Invalid input types provided.")
        raise TypeError("Inputs must be DomainNode instances.")
        
    metadata = {
        "source_id": source_node.id,
        "target_id": target_node.id,
        "source_domain": source_node.domain,
        "target_domain": target_node.domain,
        "components": {}
    }
    
    # 2. Calculate Structural Component (The 'Form')
    try:
        struct_score = calculate_structural_isomorphism(source_node, target_node)
        metadata["components"]["structural_isomorphism"] = struct_score
    except Exception:
        logger.warning("Structural calculation failed, defaulting to 0.")
        struct_score = 0.0
        metadata["components"]["structural_isomorphism"] = "Error"

    # 3. Calculate Semantic/Vector Component (The 'Meaning')
    semantic_score = 0.0
    if source_node.semantic_vector and target_node.semantic_vector:
        try:
            # In a real AGI system, this would check for analogical bridges
            semantic_score = _cosine_similarity(source_node.semantic_vector, target_node.semantic_vector)
            metadata["components"]["semantic_alignment"] = semantic_score
        except Exception:
            logger.warning("Semantic vector calculation failed.")

    # 4. Synthesize Final Metric
    # We prioritize Structure for "Insight" potential over pure semantics
    # Structure (Isomorphism) weight: 0.7, Semantic weight: 0.3
    final_score = (struct_score * 0.7) + (semantic_score * 0.3)
    
    # Boundary Checks
    final_score = max(SIMILARITY_MIN, min(final_score, SIMILARITY_MAX))
    
    metadata["final_score"] = final_score
    
    # 5. Generate Insight Tag
    if final_score > 0.8:
        metadata["insight_potential"] = "High (Isomorphic Match)"
        logger.info(f"High potential collision detected: {source_node.id} <-> {target_node.id}")
    elif final_score > 0.5:
        metadata["insight_potential"] = "Medium"
    else:
        metadata["insight_potential"] = "Low"
        
    return final_score, metadata


# --- Usage Example ---
if __name__ == "__main__":
    # Example: Comparing a Biological Cell to a Software Microservice
    
    # 1. Define Node A: A biological T-Cell
    t_cell_features = {
        "connectivity_ratio": 0.85,    # Highly connected
        "internal_complexity": 0.60,   # Moderate internal state
        "interaction_frequency": 0.90  # Very active
    }
    t_cell_vector = [0.1, 0.8, 0.2, 0.9, 0.1, 0.7, 0.3, 0.9] # Simplified embedding
    
    node_bio = DomainNode(
        id="t_cell_42",
        domain="immunology",
        features=t_cell_features,
        semantic_vector=t_cell_vector
    )
    
    # 2. Define Node B: A Kubernetes Microservice Pod
    # Note: Different domain, similar structural dynamics
    kube_pod_features = {
        "connectivity_ratio": 0.80,    # Talks to many other services
        "internal_complexity": 0.55,   # Logic complexity
        "interaction_frequency": 0.85  # High request rate
    }
    kube_pod_vector = [0.9, 0.2, 0.8, 0.1, 0.9, 0.3, 0.8, 0.1] # Opposite semantic meaning
    
    node_soft = DomainNode(
        id="payment_service_v2",
        domain="software_engineering",
        features=kube_pod_features,
        semantic_vector=kube_pod_vector
    )
    
    # 3. Execute the Skill
    print("--- Executing AGI Skill: Cross-Domain Abstraction Metric ---")
    try:
        score, details = compute_cross_domain_abstraction(node_bio, node_soft)
        
        print(f"\nComparing: {details['source_domain']} vs {details['target_domain']}")
        print(f"Structural Similarity: {details['components']['structural_isomorphism']:.4f}")
        print(f"Semantic Alignment:    {details['components']['semantic_alignment']:.4f}")
        print(f"-------------------------------------------------------")
        print(f"Final Abstraction Score: {score:.4f}")
        print(f"Insight Potential:      {details['insight_potential']}")
        print("\nInterpretation:")
        print("Despite different semantic meanings (Biology vs IT), the high structural")
        print("score suggests these nodes play identical roles in their systems.")
        print("Insight: 'Auto-immune diseases' might be modeled as 'Service Mesh Loop errors'.")
        
    except Exception as e:
        print(f"Critical Error in Skill Execution: {e}")