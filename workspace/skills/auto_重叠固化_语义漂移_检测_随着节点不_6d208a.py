"""
Module: auto_重叠固化_语义漂移_检测_随着节点不_6d208a

Description:
    This module implements semantic drift detection for AGI system nodes.
    It calculates the angular difference between the current state of a node's
    vector and its initial "固化" (solidified) state to determine if uncontrolled
    semantic drift has occurred.

    Domain: semantic_analysis
    Key Concept: Measuring the deviation of a node's meaning from its core definition
                 as it gets updated with new data over time.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SemanticDriftResult:
    """
    Data class representing the result of a semantic drift detection operation.
    
    Attributes:
        node_id: Identifier of the analyzed node.
        drift_score: Calculated drift score (angle in degrees or cosine distance).
        is_drifted: Boolean flag indicating if drift exceeded the threshold.
        message: Human-readable status message.
    """
    node_id: str
    drift_score: float
    is_drifted: bool
    message: str

def validate_vector(vector: np.ndarray, name: str = "vector") -> None:
    """
    Auxiliary function to validate input vector integrity.
    
    Args:
        vector (np.ndarray): The vector to validate.
        name (str): Name of the vector for error messages.
        
    Raises:
        TypeError: If input is not a numpy array.
        ValueError: If vector is empty or contains non-numeric types (NaN/Inf).
    """
    if not isinstance(vector, np.ndarray):
        raise TypeError(f"{name} must be a numpy array, got {type(vector)}")
    
    if vector.size == 0:
        raise ValueError(f"{name} cannot be empty")
    
    if not np.isfinite(vector).all():
        raise ValueError(f"{name} contains invalid values (NaN or Inf)")

def calculate_cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        v1: First vector.
        v2: Second vector.
        
    Returns:
        float: Cosine similarity score between -1 and 1.
    """
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    return np.dot(v1, v2) / (norm_v1 * norm_v2)

def calculate_angular_distance(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Calculate the angular distance (in degrees) between two vectors.
    This is the core metric for semantic drift.
    
    Args:
        v1: The initial/foundational vector (e.g., 'Agile Development').
        v2: The current/updated vector.
        
    Returns:
        float: Angle in degrees (0 to 180).
    """
    # Validate inputs
    validate_vector(v1, "Initial Vector")
    validate_vector(v2, "Current Vector")
    
    if v1.shape != v2.shape:
        raise ValueError(f"Vector dimension mismatch: {v1.shape} vs {v2.shape}")
    
    similarity = calculate_cosine_similarity(v1, v2)
    
    # Clamp similarity to avoid floating point errors with arccos
    similarity = np.clip(similarity, -1.0, 1.0)
    
    # Calculate angle in radians then convert to degrees
    angle_rad = np.arccos(similarity)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg

def detect_semantic_drift(
    node_id: str,
    initial_vector: np.ndarray,
    current_vector: np.ndarray,
    threshold_degrees: float = 25.0,
    metadata: Optional[Dict[str, Any]] = None
) -> SemanticDriftResult:
    """
    Detects if a node has undergone semantic drift based on vector angular distance.
    
    This function compares the current state of a node against its 'solidified'
    initial state. If the angle exceeds the threshold, it suggests the node's
    core meaning has shifted (e.g., from "Agile Methodology" to "Scrum Meeting Notes").
    
    Args:
        node_id (str): Unique identifier for the node.
        initial_vector (np.ndarray): The foundational embedding vector.
        current_vector (np.ndarray): The current updated embedding vector.
        threshold_degrees (float): Maximum allowable drift angle in degrees.
        metadata (Optional[Dict]): Additional context for logging.
        
    Returns:
        SemanticDriftResult: Object containing drift analysis results.
        
    Raises:
        ValueError: If threshold is negative.
    """
    # Input boundary checks
    if threshold_degrees < 0:
        raise ValueError("Threshold cannot be negative")
    
    logger.info(f"Analyzing semantic drift for Node ID: {node_id}")
    
    try:
        # Core Calculation
        drift_angle = calculate_angular_distance(initial_vector, current_vector)
        
        # Determine status
        is_drifted = drift_angle > threshold_degrees
        
        # Construct result message
        if is_drifted:
            msg = (f"Drift DETECTED. Angle {drift_angle:.2f}° exceeds "
                   f"threshold {threshold_degrees}°.")
            logger.warning(f"[{node_id}] {msg}")
        else:
            msg = (f"Node stable. Angle {drift_angle:.2f}° is within "
                   f"threshold {threshold_degrees}°.")
            logger.info(f"[{node_id}] {msg}")
            
        return SemanticDriftResult(
            node_id=node_id,
            drift_score=drift_angle,
            is_drifted=is_drifted,
            message=msg
        )
        
    except Exception as e:
        logger.error(f"Error processing node {node_id}: {str(e)}")
        raise

def run_drift_detection_pipeline(
    nodes_data: Dict[str, Dict[str, np.ndarray]],
    global_threshold: float = 30.0
) -> Dict[str, SemanticDriftResult]:
    """
    Processes a batch of nodes to detect semantic drift across the system.
    
    Args:
        nodes_data: Dictionary where keys are node IDs and values contain
                    'initial' and 'current' vectors.
                    Format: { 'node_1': {'initial': vec, 'current': vec}, ... }
        global_threshold: Default threshold for all nodes.
        
    Returns:
        Dict mapping node IDs to their Drift Results.
    """
    results = {}
    
    for node_id, vectors in nodes_data.items():
        try:
            if 'initial' not in vectors or 'current' not in vectors:
                logger.error(f"Missing vector data for node {node_id}")
                continue
                
            result = detect_semantic_drift(
                node_id=node_id,
                initial_vector=vectors['initial'],
                current_vector=vectors['current'],
                threshold_degrees=global_threshold
            )
            results[node_id] = result
            
        except Exception:
            continue
            
    return results

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Simulating a scenario:
    # Node 'Agile_Core' started as a broad concept of Agile.
    # After ingesting many meeting notes, its vector shifts towards "Scrum Meetings".
    
    # 1. Setup Mock Data (768 dimensions is standard for many LLM embeddings)
    dim = 768
    np.random.seed(42)
    
    # The original broad vector
    agile_initial = np.random.rand(dim)
    
    # Slight variation - acceptable update
    agile_updated_acceptable = agile_initial + (np.random.rand(dim) * 0.1)
    
    # Drastic variation - semantic drift
    # Adding a large noise vector simulates the topic changing significantly
    agile_updated_drifted = agile_initial + (np.random.rand(dim) * 2.0)
    
    # 2. Run Detection
    print("--- Running Drift Detection ---")
    
    # Case A: Stable Update
    result_stable = detect_semantic_drift(
        node_id="Agile_Core_v2",
        initial_vector=agile_initial,
        current_vector=agile_updated_acceptable,
        threshold_degrees=15.0
    )
    print(f"Result (Stable): {result_stable.message}")
    
    # Case B: Drifted Update
    result_drifted = detect_semantic_drift(
        node_id="Agile_Core_v3",
        initial_vector=agile_initial,
        current_vector=agile_updated_drifted,
        threshold_degrees=15.0
    )
    print(f"Result (Drifted): {result_drifted.message}")