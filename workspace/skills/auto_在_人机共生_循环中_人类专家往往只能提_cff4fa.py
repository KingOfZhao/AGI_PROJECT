"""
Advanced Skill Module: Counterfactual Boundary Reconstruction from Failure Cases

This module implements a sophisticated AGI skill for "Human-AI Symbiosis" loops.
It addresses the scenario where human experts typically provide only "failure cases"
(samples that led to scrap/rejection). Using "Counterfactual Reasoning", this module
aims to reverse-engineer the boundary conditions of "success states" solely from
these negative samples, enabling the autonomous update of Skill nodes.

Key Concepts:
- Boundary Extrapolation: Estimating the success region by calculating the centroid
  of failure and projecting in the opposite direction.
- Latent Space Manipulation: Assumes inputs are feature vectors (or embeddings).
- Confidence Scording: Weights new boundaries based on the density of failure evidence.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Union
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI.CounterfactualSkill")

# --- Data Models ---

class FailureCase(BaseModel):
    """Represents a single failure sample provided by a human expert."""
    sample_id: str
    features: List[float] = Field(..., description="Feature vector representing the state.")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Metadata or context.")

class SkillBoundary(BaseModel):
    """Represents the geometric definition of a Skill's success boundary."""
    center: List[float]
    radius: float
    version: str = "1.0"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

# --- Custom Exceptions ---

class DimensionalityError(ValueError):
    """Raised when input vectors have mismatched dimensions."""
    pass

class InsufficientDataError(ValueError):
    """Raised when not enough data is provided to perform reasoning."""
    pass

# --- Core Functions ---

def calculate_failure_centroid(failures: List[FailureCase]) -> np.ndarray:
    """
    Calculates the geometric center of the provided failure cases.
    
    This point represents the 'Epicenter of Failure' in the latent space.
    
    Args:
        failures: A list of FailureCase objects.
        
    Returns:
        A numpy array representing the centroid vector.
        
    Raises:
        InsufficientDataError: If the list is empty.
        DimensionalityError: If vectors have different lengths.
    """
    if not failures:
        raise InsufficientDataError("Cannot calculate centroid of empty failure list.")
    
    logger.info(f"Processing {len(failures)} failure cases to determine centroid.")
    
    try:
        matrix = np.array([f.features for f in failures])
        # Check for consistent dimensionality
        if matrix.ndim != 2:
            raise DimensionalityError("Inconsistent feature dimensions in failure cases.")
            
        centroid = np.mean(matrix, axis=0)
        logger.debug(f"Calculated failure centroid: {centroid[:3]}... (truncated)")
        return centroid
    except Exception as e:
        logger.error(f"Error during centroid calculation: {str(e)}")
        raise

def infer_success_boundary(
    current_skill: SkillBoundary,
    failure_cases: List[FailureCase],
    learning_rate: float = 0.1,
    push_force: float = 2.0
) -> SkillBoundary:
    """
    Core AGI Reasoning Function: Infers the 'Success Boundary' via Counterfactual Push.
    
    Logic:
    1. Calculate the Centroid of Failure (CoF).
    2. Determine the vector from Current Skill Center -> CoF.
    3. Move the Skill Center in the OPPOSITE direction (Counterfactual Push).
    4. Adjust the boundary radius based on the spread of failure cases.
    
    Args:
        current_skill: The current definition of the skill boundary.
        failure_cases: List of negative samples.
        learning_rate: How drastically to update the boundary (0.0 to 1.0).
        push_force: Multiplier for how far to push the boundary away from failures.
        
    Returns:
        A new SkillBoundary object representing the updated skill definition.
    """
    logger.info("Starting Counterfactual Boundary Inference...")
    
    # 1. Validation
    if not failure_cases:
        logger.warning("No failure cases provided. Returning current skill unchanged.")
        return current_skill
    
    dim = len(current_skill.center)
    for case in failure_cases:
        if len(case.features) != dim:
            raise DimensionalityError(
                f"Feature mismatch: Skill dim is {dim}, but case {case.sample_id} is {len(case.features)}"
            )

    # 2. Analyze Failures
    failure_centroid = calculate_failure_centroid(failure_cases)
    current_center = np.array(current_skill.center)
    
    # 3. Calculate Counterfactual Vector (The "Push")
    # Vector points FROM failure TO current center (We want to move AWAY from failure)
    # Ideally, we assume success is "opposite" to the failure cluster relative to current boundary
    delta_vector = current_center - failure_centroid
    distance_to_failure = np.linalg.norm(delta_vector)
    
    if distance_to_failure < 1e-6:
        logger.warning("Current skill center is identical to failure centroid. Random perturbation applied.")
        delta_vector = np.random.randn(dim)
        distance_to_failure = np.linalg.norm(delta_vector)

    # Normalize and scale
    direction = delta_vector / distance_to_failure
    
    # The further the failure, the less we need to move? 
    # Or implies the current boundary is completely wrong?
    # Here we use a heuristic: Move proportional to the learning rate and distance.
    move_magnitude = learning_rate * push_force * distance_to_failure
    shift_vector = direction * move_magnitude
    
    # 4. Compute New Center
    new_center = current_center + shift_vector
    
    # 5. Update Radius (Shrink to avoid the failure cluster)
    # Calculate spread of failures
    failure_matrix = np.array([f.features for f in failure_cases])
    avg_dist_to_centroid = np.mean(np.linalg.norm(failure_matrix - failure_centroid, axis=1))
    
    # New radius logic: 
    # We want the radius to be strictly smaller than the distance to the new failure frontier.
    # Heuristic: Distance to failure centroid minus average spread, scaled by safety factor.
    new_dist_to_failure_cluster = np.linalg.norm(new_center - failure_centroid)
    safe_radius = max(0.1, (new_dist_to_failure_cluster - avg_dist_to_centroid * 1.5))
    
    # Smooth update for radius
    new_radius = (1 - learning_rate) * current_skill.radius + (learning_rate * safe_radius)
    
    logger.info(f"Inference complete. Center shifted by {np.linalg.norm(shift_vector):.4f}")

    return SkillBoundary(
        center=new_center.tolist(),
        radius=float(new_radius),
        version=f"{current_skill.version}+cf",
        confidence=min(1.0, current_skill.confidence + 0.05) # Slight confidence boost from update
    )

# --- Auxiliary Functions ---

def validate_input_vectors(cases: List[FailureCase], expected_dim: int) -> bool:
    """
    Validates that all input vectors match the expected dimensionality.
    
    Args:
        cases: List of failure cases.
        expected_dim: The required vector size.
        
    Returns:
        True if valid.
        
    Raises:
        ValueError if dimensions mismatch.
    """
    logger.debug("Validating input vector dimensions...")
    for case in cases:
        if len(case.features) != expected_dim:
            msg = (f"Dimension mismatch in case {case.sample_id}. "
                   f"Expected {expected_dim}, got {len(case.features)}")
            logger.error(msg)
            raise ValueError(msg)
    return True

def format_boundary_for_export(boundary: SkillBoundary) -> Dict[str, Any]:
    """
    Helper to serialize the boundary for external systems or storage.
    
    Args:
        boundary: The SkillBoundary object.
        
    Returns:
        A dictionary suitable for JSON serialization.
    """
    return {
        "skill_metadata": {
            "type": "CounterfactualBoundary",
            "version": boundary.version,
            "confidence_score": boundary.confidence
        },
        "geometry": {
            "center_vector": boundary.center,
            "influence_radius": boundary.radius
        }
    }

# --- Usage Example ---

if __name__ == "__main__":
    # Seed for reproducibility
    np.random.seed(42)
    
    # 1. Setup Initial Skill State
    # Let's assume we are tuning a "Grasping Force" skill in latent space (dim=5)
    initial_center = [0.5, 0.5, 0.5, 0.5, 0.5]
    initial_skill = SkillBoundary(
        center=initial_center, 
        radius=1.0, 
        version="v1.0", 
        confidence=0.6
    )
    
    print(f"Initial Skill Center: {initial_skill.center}")
    
    # 2. Simulate Human Expert Input (Failure Cases)
    # Failures are clustered around [0.9, 0.9, 0.9, 0.9, 0.9] (Too much force/slip)
    failure_data = [
        {"sample_id": "fail_001", "features": [0.88, 0.92, 0.85, 0.91, 0.89]},
        {"sample_id": "fail_002", "features": [0.91, 0.89, 0.94, 0.90, 0.88]},
        {"sample_id": "fail_003", "features": [0.85, 0.95, 0.90, 0.93, 0.92]},
    ]
    
    failure_cases = [FailureCase(**data) for data in failure_data]
    
    try:
        # 3. Validate Data
        validate_input_vectors(failure_cases, expected_dim=5)
        
        # 4. Run Counterfactual Inference
        updated_skill = infer_success_boundary(
            current_skill=initial_skill,
            failure_cases=failure_cases,
            learning_rate=0.3,
            push_force=1.5
        )
        
        # 5. Output Results
        print("\n--- Skill Update Complete ---")
        print(f"New Center: {[round(x, 3) for x in updated_skill.center]}")
        print(f"New Radius: {round(updated_skill.radius, 3)}")
        print(f"New Confidence: {updated_skill.confidence}")
        
        # Expected result: Center should have shifted *away* from 0.9 towards lower values
        # (e.g., towards 0.2 or 0.3) and radius might shrink to exclude the 0.9 cluster.
        
        export_data = format_boundary_for_export(updated_skill)
        logger.info(f"Export Payload: {export_data}")
        
    except (ValidationError, ValueError) as e:
        logger.error(f"Processing failed: {e}")