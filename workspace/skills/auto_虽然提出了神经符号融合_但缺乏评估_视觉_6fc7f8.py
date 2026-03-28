"""
Neuro-Symbolic Alignment Evaluator Module

This module provides a toolkit to quantify the semantic alignment between
visual features (e.g., patches from a monitoring video) and logical concepts
(e.g., textual nodes in a knowledge graph like 'Slip Risk').

It addresses the challenge of evaluating Neuro-Symbolic fusion by proposing
a unified metric in a cross-modal embedding space.

Key Features:
- Cross-modal embedding projection.
- Semantic distance calculation (Euclidean and Cosine).
- Probabilistic alignment scoring.

Domain: General / Computer Vision / Neuro-Symbolic AI
"""

import logging
import numpy as np
from typing import Tuple, List, Dict, Optional, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AlignmentResult:
    """Container for alignment evaluation results."""
    concept_id: str
    distance_score: float
    alignment_probability: float
    is_aligned: bool

class EmbeddingSpaceError(Exception):
    """Custom exception for errors related to embedding dimensions or validity."""
    pass

def _validate_embedding(vector: np.ndarray, name: str) -> None:
    """
    Helper function to validate the integrity of input vectors.
    
    Args:
        vector (np.ndarray): The vector to validate.
        name (str): Name of the variable for error messages.
        
    Raises:
        EmbeddingSpaceError: If vector is not 1D, empty, or contains NaN/Inf.
    """
    if vector.ndim != 1:
        raise EmbeddingSpaceError(f"{name} must be a 1-dimensional array. Got shape: {vector.shape}")
    if vector.size == 0:
        raise EmbeddingSpaceError(f"{name} cannot be empty.")
    if not np.isfinite(vector).all():
        raise EmbeddingSpaceError(f"{name} contains NaN or Inf values.")

def project_visual_to_concept_space(
    visual_feature: np.ndarray, 
    projection_matrix: np.ndarray, 
    bias: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Projects a raw visual feature vector into the shared concept embedding space.
    
    In a Neuro-Symbolic system, visual features (e.g., ResNet output) often have 
    different dimensions than Concept embeddings (e.g., Word2Vec or Graph Node Embeddings).
    This function aligns dimensions.

    Args:
        visual_feature (np.ndarray): Raw visual feature vector (e.g., shape [2048]).
        projection_matrix (np.ndarray): Trainable weight matrix W (shape [concept_dim, visual_dim]).
        bias (Optional[np.ndarray]): Optional bias vector (shape [concept_dim]).

    Returns:
        np.ndarray: Projected visual vector in the concept space.

    Example:
        >>> v_feat = np.random.rand(2048)
        >>> W = np.random.rand(300, 2048)
        >>> projected = project_visual_to_concept_space(v_feat, W)
    """
    logger.debug("Projecting visual feature to concept space...")
    
    try:
        _validate_embedding(visual_feature, "visual_feature")
        
        visual_dim = visual_feature.shape[0]
        if projection_matrix.shape[1] != visual_dim:
            raise EmbeddingSpaceError(
                f"Dimension mismatch: Matrix cols {projection_matrix.shape[1]} != Vector dims {visual_dim}"
            )
            
        projected = np.dot(projection_matrix, visual_feature)
        
        if bias is not None:
            _validate_embedding(bias, "bias")
            if bias.shape[0] != projection_matrix.shape[0]:
                 raise EmbeddingSpaceError("Bias dimension does not match projection output dimension.")
            projected += bias
            
        return projected
        
    except EmbeddingSpaceError as ese:
        logger.error(f"Projection failed: {ese}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during projection: {e}")
        raise

def calculate_semantic_distance(
    source_vector: np.ndarray, 
    target_vector: np.ndarray, 
    metric: str = 'cosine'
) -> float:
    """
    Calculates the semantic distance between two vectors in the unified space.
    
    Note: For 'cosine', we return 1 - similarity, so 0 means identical and 1 means orthogonal.
    For 'euclidean', smaller values mean closer.

    Args:
        source_vector (np.ndarray): The projected visual vector.
        target_vector (np.ndarray): The concept/logic vector (e.g., 'Slip Risk').
        metric (str): 'cosine' or 'euclidean'.

    Returns:
        float: The calculated distance.

    Example:
        >>> v1 = np.array([1.0, 0.0])
        >>> v2 = np.array([0.9, 0.1])
        >>> dist = calculate_semantic_distance(v1, v2)
    """
    _validate_embedding(source_vector, "source_vector")
    _validate_embedding(target_vector, "target_vector")
    
    if source_vector.shape != target_vector.shape:
        raise EmbeddingSpaceError(
            f"Shape mismatch: Source {source_vector.shape} vs Target {target_vector.shape}"
        )

    if metric == 'cosine':
        dot_product = np.dot(source_vector, target_vector)
        norm_source = np.linalg.norm(source_vector)
        norm_target = np.linalg.norm(target_vector)
        
        if norm_source == 0 or norm_target == 0:
            logger.warning("Zero vector detected in cosine similarity calculation.")
            return 1.0 # Maximum distance
            
        similarity = dot_product / (norm_source * norm_target)
        # Clamp similarity to [-1, 1] to avoid floating point errors
        similarity = np.clip(similarity, -1.0, 1.0)
        return 1.0 - similarity
    
    elif metric == 'euclidean':
        return np.linalg.norm(source_vector - target_vector)
    
    else:
        logger.error(f"Unsupported metric: {metric}")
        raise ValueError(f"Unsupported metric: {metric}. Choose 'cosine' or 'euclidean'.")

def evaluate_neuro_symbolic_alignment(
    visual_feature: np.ndarray,
    concept_vector: np.ndarray,
    projection_matrix: np.ndarray,
    threshold: float = 0.2
) -> AlignmentResult:
    """
    Main evaluation function. Quantifies how well a visual input aligns with a 
    specific logical concept.
    
    This simulates the scenario of detecting 'oil stains' (visual) and mapping 
    them to 'slip risk' (logic).

    Args:
        visual_feature (np.ndarray): Raw input from visual encoder.
        concept_vector (np.ndarray): The target concept node embedding.
        projection_matrix (np.ndarray): Matrix to align visual to concept space.
        threshold (float): Distance threshold to consider alignment valid (0.0 to 2.0 for cosine).

    Returns:
        AlignmentResult: Detailed results of the alignment check.
    """
    logger.info("Starting Neuro-Symbolic alignment evaluation...")
    
    # 1. Project Visual to Common Space
    try:
        projected_v = project_visual_to_concept_space(visual_feature, projection_matrix)
    except EmbeddingSpaceError:
        return AlignmentResult("unknown", -1.0, 0.0, False)

    # 2. Calculate Distance
    distance = calculate_semantic_distance(projected_v, concept_vector, metric='cosine')
    
    # 3. Convert to Probability (Simple Gaussian-like kernel mapping)
    # sigma controls how fast probability drops with distance
    sigma = 0.1 
    probability = np.exp(-(distance**2) / (2 * sigma**2))
    
    # 4. Threshold Check
    is_aligned = distance < threshold
    
    if is_aligned:
        logger.info(f"Alignment successful. Distance: {distance:.4f}")
    else:
        logger.warning(f"Alignment failed. Distance: {distance:.4f} > Threshold: {threshold}")

    return AlignmentResult(
        concept_id="slip_risk_node_01",
        distance_score=float(distance),
        alignment_probability=float(probability),
        is_aligned=is_aligned
    )

# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    # Setup dummy data dimensions
    VISUAL_DIM = 2048  # e.g., ResNet output
    CONCEPT_DIM = 300  # e.g., Word2Vec size
    
    # Generate synthetic data
    # 1. The 'Oil Spill' visual feature extracted from CCTV
    visual_input = np.random.randn(VISUAL_DIM)
    
    # 2. The 'Slip Risk' concept embedding
    concept_embedding = np.random.randn(CONCEPT_DIM)
    
    # 3. A trained projection matrix (Visual -> Concept)
    W_proj = np.random.randn(CONCEPT_DIM, VISUAL_DIM) * 0.01
    
    # Run Evaluation
    try:
        result = evaluate_neuro_symbolic_alignment(
            visual_feature=visual_input,
            concept_vector=concept_embedding,
            projection_matrix=W_proj,
            threshold=0.8 # Loose threshold for random data
        )
        
        print("\n--- Evaluation Result ---")
        print(f"Concept: {result.concept_id}")
        print(f"Semantic Distance: {result.distance_score:.4f}")
        print(f"Alignment Probability: {result.alignment_probability:.4f}")
        print(f"Is Aligned: {result.is_aligned}")
        
    except Exception as e:
        logger.critical(f"System failed during evaluation: {e}")