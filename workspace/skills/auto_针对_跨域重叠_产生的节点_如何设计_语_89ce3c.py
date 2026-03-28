"""
Module: semantic_drift_detector.py

This module provides a mechanism to detect semantic drift when a concept node
is migrated across different domains (e.g., from Biology to Product Management).

It implements a vector-space-based monitoring system. If the semantic offset
exceeds a specific threshold (jeopardizing logical self-consistency), the system
automatically triggers the creation of a forked node rather than overwriting
the original definition.

Author: AGI System Core Engineer
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents a concept node in the knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        term: The term or phrase (e.g., "Evolution").
        domain: The original domain context (e.g., "Biology").
        vector: The embedding vector representing the semantic meaning.
        created_at: Timestamp of creation.
        is_fork: Boolean indicating if this is a branched node.
    """
    id: str
    term: str
    domain: str
    vector: np.ndarray
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_fork: bool = False

@dataclass
class DriftReport:
    """
    Contains the analysis result of a semantic drift check.
    """
    original_node_id: str
    new_context: str
    drift_score: float
    threshold: float
    is_consistent: bool
    action_taken: str
    new_node_id: Optional[str] = None

# --- Custom Exceptions ---

class VectorDimensionError(ValueError):
    """Raised when vector dimensions do not match."""
    pass

class InvalidThresholdError(ValueError):
    """Raised when threshold is not between 0 and 1."""
    pass

# --- Core Functions ---

def calculate_semantic_drift(
    base_vector: np.ndarray, 
    target_vector: np.ndarray, 
    metric: str = 'cosine'
) -> float:
    """
    Calculates the semantic distance (drift) between two vectors.
    
    Args:
        base_vector: The original node's embedding.
        target_vector: The new context's embedding.
        metric: Distance metric ('cosine' or 'euclidean').
        
    Returns:
        float: The distance score. For cosine, 0 means identical, 1 means orthogonal.
        
    Raises:
        VectorDimensionError: If vectors have different shapes.
    """
    # Input Validation
    if base_vector.shape != target_vector.shape:
        msg = f"Dimension mismatch: {base_vector.shape} vs {target_vector.shape}"
        logger.error(msg)
        raise VectorDimensionError(msg)
    
    if metric == 'cosine':
        dot_product = np.dot(base_vector, target_vector)
        norm_base = np.linalg.norm(base_vector)
        norm_target = np.linalg.norm(target_vector)
        
        if norm_base == 0 or norm_target == 0:
            return 1.0 # Max distance if vector is zero
            
        similarity = dot_product / (norm_base * norm_target)
        # Drift is defined here as 1 - similarity
        drift = 1.0 - similarity
        return float(np.clip(drift, 0.0, 1.0))
    
    elif metric == 'euclidean':
        return float(np.linalg.norm(base_vector - target_vector))
    
    else:
        logger.warning(f"Unknown metric {metric}, defaulting to cosine.")
        return calculate_semantic_drift(base_vector, target_vector, metric='cosine')

def manage_node_consistency(
    node: KnowledgeNode,
    new_context_vector: np.ndarray,
    new_domain: str,
    threshold: float = 0.25
) -> Tuple[DriftReport, KnowledgeNode]:
    """
    Monitors semantic consistency. If drift exceeds threshold, it creates a fork.
    
    This function encapsulates the logic to decide whether to update a node
    in place or branch it to preserve logical consistency across domains.
    
    Args:
        node: The existing knowledge node.
        new_context_vector: The embedding of the concept in the new domain.
        new_domain: The name of the target domain.
        threshold: The acceptable drift limit (0.0 to 1.0).
        
    Returns:
        Tuple[DriftReport, KnowledgeNode]: A report of the analysis and the 
        resulting node (either the updated original or the new fork).
    """
    # Boundary Checks
    if not 0.0 <= threshold <= 1.0:
        raise InvalidThresholdError("Threshold must be between 0.0 and 1.0")
    
    if node.vector.shape != new_context_vector.shape:
        raise VectorDimensionError("Input vector dimensions do not match node vector.")

    logger.info(f"Analyzing drift for node '{node.id}' moving to domain '{new_domain}'...")
    
    # Calculate Drift
    drift_score = calculate_semantic_drift(node.vector, new_context_vector)
    
    # Decision Logic
    if drift_score <= threshold:
        # Semantic drift is acceptable, minor update or merge logic applies
        logger.info(f"Drift {drift_score:.4f} within threshold {threshold}. Consistency maintained.")
        report = DriftReport(
            original_node_id=node.id,
            new_context=new_domain,
            drift_score=drift_score,
            threshold=threshold,
            is_consistent=True,
            action_taken="UPDATE_IN_PLACE"
        )
        # Here we simply return the original node (conceptually updating it)
        return report, node
    else:
        # Drift is too high (e.g., 'Evolution' in Biology vs 'Product Evolution')
        # Action: Create a Fork
        logger.warning(
            f"Drift {drift_score:.4f} > {threshold}. Logical consistency risk detected. "
            f"Creating fork for '{node.term}' in '{new_domain}'."
        )
        
        new_node = create_fork_node(node, new_context_vector, new_domain)
        
        report = DriftReport(
            original_node_id=node.id,
            new_context=new_domain,
            drift_score=drift_score,
            threshold=threshold,
            is_consistent=False,
            action_taken="CREATE_FORK",
            new_node_id=new_node.id
        )
        return report, new_node

# --- Helper Functions ---

def create_fork_node(
    original_node: KnowledgeNode, 
    new_vector: np.ndarray, 
    new_domain: str
) -> KnowledgeNode:
    """
    Helper to generate a new forked node instance.
    
    It generates a unique ID linking it to the parent concept but distinguishing
    it by domain.
    """
    import uuid
    new_id = f"{original_node.id}_{new_domain}_{str(uuid.uuid4())[:8]}"
    
    return KnowledgeNode(
        id=new_id,
        term=original_node.term, # Keep term, but meaning has shifted contextually
        domain=new_domain,
        vector=new_vector,
        is_fork=True
    )

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup: Simulate a Biology 'Evolution' node
    # In a real scenario, these vectors come from BERT/GPT/Word2Vec
    dim = 768
    biology_vector = np.random.rand(dim) # Simulated embedding
    biology_node = KnowledgeNode(
        id="concept_evolution_01",
        term="Evolution",
        domain="Biology",
        vector=biology_vector
    )

    # 2. Scenario A: Small Drift (e.g., History context - strictly related)
    # Simulate a very similar vector
    history_vector = biology_vector + np.random.normal(0, 0.01, dim) 
    history_vector = np.clip(history_vector, 0, 1) # Keep in reasonable range

    print("\n--- Scenario A: History Domain (Low Drift) ---")
    report_a, result_node_a = manage_node_consistency(
        biology_node, 
        history_vector, 
        "History", 
        threshold=0.1
    )
    print(f"Action: {report_a.action_taken}")
    print(f"Drift Score: {report_a.drift_score:.4f}")

    # 3. Scenario B: High Drift (e.g., Product Management context - Metaphorical)
    # Simulate a significantly different vector
    product_vector = np.random.rand(dim) 
    
    print("\n--- Scenario B: Product Domain (High Drift) ---")
    report_b, result_node_b = manage_node_consistency(
        biology_node, 
        product_vector, 
        "ProductMgmt", 
        threshold=0.1
    )
    print(f"Action: {report_b.action_taken}")
    print(f"Drift Score: {report_b.drift_score:.4f}")
    print(f"New Node ID: {result_node_b.id}")
    print(f"Is Fork: {result_node_b.is_fork}")