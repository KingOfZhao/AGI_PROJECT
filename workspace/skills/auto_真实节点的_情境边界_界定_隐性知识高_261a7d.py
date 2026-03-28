"""
Skill Module: Contextual Boundary Detector for Tacit Knowledge Nodes

This module implements a validity boundary detection system for "Real Nodes" (solidified
knowledge instances, e.g., specific temperature control curves). Tacit knowledge often
relies heavily on implicit context (e.g., "add more fire on cloudy days"). This system
constructs an "Validity Boundary Detector" for each node to determine if current
environmental parameters fall within the node's applicability scope, preventing
misapplication of knowledge in incorrect contexts.

Key Features:
- Multivariate Gaussian Boundary Modeling.
- Mahalanobis Distance calculation for outlier detection.
- Dynamic thresholding for context validity.
- Drift detection and logging.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class EnvironmentParameters(BaseModel):
    """
    Input schema for current environment parameters.
    Validates data types and ranges before processing.
    """
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity percentage")
    temperature: float = Field(..., ge=-50, le=200, description="Ambient temperature in Celsius")
    material_density: float = Field(..., ge=0, description="Density coefficient of the material batch")
    # Extensible to other parameters like pressure, wind speed, etc.

    class Config:
        schema_extra = {
            "example": {
                "humidity": 65.0,
                "temperature": 25.0,
                "material_density": 1.2
            }
        }

@dataclass
class ValidityBoundary:
    """
    Represents the mathematical boundary of a specific 'Real Node'.
    Encapsulates the statistical properties of the context where this knowledge is valid.
    """
    node_id: str
    feature_names: List[str]
    mean_vector: np.ndarray
    covariance_matrix: np.ndarray
    threshold: float = Field(default=3.0, description="Mahalanobis distance threshold for validity")
    samples_count: int = 0

    def __post_init__(self):
        if len(self.feature_names) != len(self.mean_vector):
            raise ValueError("Feature names length must match mean vector dimensions.")

# --- Core Functions ---

def train_boundary_detector(
    node_id: str,
    historical_contexts: List[Dict[str, float]],
    sensitivity: float = 0.95
) -> Optional[ValidityBoundary]:
    """
    Trains a Validity Boundary Detector based on historical successful contexts.
    
    This function calculates the mean and covariance matrix of the historical data
    to define the 'valid region' for this specific knowledge node.

    Args:
        node_id (str): Unique identifier for the Real Node.
        historical_contexts (List[Dict[str, float]]): A list of parameter dicts
                                                      representing past successful applications.
        sensitivity (float): The percentile for determining the threshold (0.0 to 1.0).

    Returns:
        ValidityBoundary: An object containing the mathematical definition of the boundary.

    Raises:
        ValueError: If input data is insufficient or contains NaN values.
    """
    if len(historical_contexts) < 5:
        logger.error(f"Insufficient data to train boundary for node {node_id}. Need >= 5, got {len(historical_contexts)}")
        return None

    try:
        # Extract feature names from the first entry
        feature_names = list(historical_contexts[0].keys())
        
        # Convert list of dicts to numpy matrix
        data_matrix = np.array([
            [ctx.get(name, 0.0) for name in feature_names] 
            for ctx in historical_contexts
        ])

        # Data Validation
        if np.isnan(data_matrix).any():
            raise ValueError("Historical data contains NaN values.")

        # Statistical Calculation
        mean_vec = np.mean(data_matrix, axis=0)
        cov_mat = np.cov(data_matrix, rowvar=False)
        
        # Regularization to ensure matrix is invertible (handle linear dependencies)
        cov_mat += np.eye(cov_mat.shape[1]) * 1e-6

        # Calculate initial threshold based on training data distribution
        # We assume a Chi-squared distribution for Mahalanobis distance squared
        # Here we empirically set threshold based on provided sensitivity
        dists = _calculate_mahalanobis_matrix(data_matrix, mean_vec, cov_mat)
        calculated_threshold = np.percentile(dists, sensitivity * 100)
        
        logger.info(f"Boundary trained for node {node_id} with threshold {calculated_threshold:.4f}")

        return ValidityBoundary(
            node_id=node_id,
            feature_names=feature_names,
            mean_vector=mean_vec,
            covariance_matrix=cov_mat,
            threshold=calculated_threshold,
            samples_count=len(historical_contexts)
        )

    except Exception as e:
        logger.exception(f"Failed to train boundary for {node_id}: {str(e)}")
        return None

def check_context_validity(
    current_params: Dict[str, float],
    boundary: ValidityBoundary
) -> Tuple[bool, float, Dict[str, float]]:
    """
    Checks if the current environment parameters fall within the ValidityBoundary.
    
    It calculates the Mahalanobis distance between the current point and the
    distribution center of the valid contexts.

    Args:
        current_params (Dict[str, float]): Current sensor readings or environment state.
        boundary (ValidityBoundary): The trained boundary object.

    Returns:
        Tuple[bool, float, Dict[str, float]]:
            - is_valid (bool): True if within boundary, False otherwise.
            - distance (float): The calculated deviation distance.
            - contributions (Dict): Feature-wise contribution to the deviation.
    """
    try:
        # Validate input structure against trained features
        input_vector = np.array([current_params.get(f, 0.0) for f in boundary.feature_names])
        
        # Validate input data presence
        if None in input_vector:
            missing = [f for f in boundary.feature_names if f not in current_params]
            raise KeyError(f"Missing features in input: {missing}")

        # Calculate Mahalanobis Distance
        delta = input_vector - boundary.mean_vector
        
        # Use pseudo-inverse for stability against singular matrices
        cov_pinv = np.linalg.pinv(boundary.covariance_matrix)
        
        # Distance calculation: sqrt((x-mu)^T * Sigma^-1 * (x-mu))
        m_dist_sq = np.dot(np.dot(delta, cov_pinv), delta)
        m_dist = np.sqrt(m_dist_sq)
        
        # Analyze contributions (which parameter caused the drift?)
        contributions = _analyze_deviation_contributions(delta, cov_pinv, boundary.feature_names)

        is_valid = m_dist <= boundary.threshold
        
        if not is_valid:
            logger.warning(
                f"Context Drift Detected for Node {boundary.node_id}. "
                f"Distance: {m_dist:.4f} > Threshold: {boundary.threshold:.4f}. "
                f"Top Contributor: {max(contributions, key=contributions.get)}"
            )
        
        return is_valid, float(m_dist), contributions

    except Exception as e:
        logger.error(f"Error checking validity: {str(e)}")
        # Fail-safe: Return False to prevent potential misuse of knowledge
        return False, float('inf'), {}

# --- Helper Functions ---

def _calculate_mahalanobis_matrix(
    data: np.ndarray, 
    mean: np.ndarray, 
    cov: np.ndarray
) -> np.ndarray:
    """
    Helper: Calculates Mahalanobis distance for a matrix of data points.
    """
    delta = data - mean
    cov_pinv = np.linalg.pinv(cov)
    dists = np.sqrt(np.sum(np.dot(delta, cov_pinv) * delta, axis=1))
    return dists

def _analyze_deviation_contributions(
    delta: np.ndarray, 
    cov_inv: np.ndarray, 
    features: List[str]
) -> Dict[str, float]:
    """
    Helper: Decomposes the distance to find which features contribute most to the deviation.
    Useful for debugging or explaining *why* the context is invalid.
    """
    # Simple contribution score: weighted absolute deviation
    # This is an approximation for explanation purposes
    weighted_delta = np.abs(np.dot(delta, cov_inv))
    
    # Normalize to sum to 1 (relative contribution)
    total_weight = np.sum(weighted_delta)
    if total_weight == 0:
        return {f: 0.0 for f in features}
    
    contributions = weighted_delta / total_weight
    return {f: float(c) for f, c in zip(features, contributions)}

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Simulate Historical Data (The 'Tacit Knowledge' Context)
    # Scenario: A kiln firing curve that works well in dry, moderate conditions.
    # Mean: Humidity 40%, Temp 25C, Density 1.5
    np.random.seed(42)
    
    # Generate synthetic training data (Cluster around the ideal point)
    base_data = np.array([40.0, 25.0, 1.5])
    noise = np.random.normal(0, 1, (50, 3)) * np.array([5.0, 2.0, 0.1]) # Vary std per feature
    
    training_data_raw = base_data + noise
    training_dicts = [
        {"humidity": d[0], "temperature": d[1], "material_density": d[2]} 
        for d in training_data_raw
    ]

    print(f"--- Training Boundary Detector for Kiln Curve 'FireCurve_001' ---")
    
    # 2. Train the Detector
    boundary_detector = train_boundary_detector(
        node_id="FireCurve_001", 
        historical_contexts=training_dicts
    )

    if boundary_detector:
        print(f"Boundary Established. Threshold: {boundary_detector.threshold:.4f}")

        # 3. Case 1: Valid Context (Inside the cluster)
        valid_context = {"humidity": 42.0, "temperature": 24.5, "material_density": 1.55}
        is_ok, dist, contrib = check_context_validity(valid_context, boundary_detector)
        print(f"\n[Test 1 - Normal Day] Valid: {is_ok}, Distance: {dist:.4f}")

        # 4. Case 2: Invalid Context (The 'Cloudy/Rainy' scenario described in the prompt)
        # High humidity pushes the point outside the cluster
        rainy_context = {"humidity": 85.0, "temperature": 20.0, "material_density": 1.5}
        is_ok, dist, contrib = check_context_validity(rainy_context, boundary_detector)
        print(f"[Test 2 - Rainy Day] Valid: {is_ok}, Distance: {dist:.4f}")
        print(f"Deviation Analysis: {contrib}") 
        # Expect 'humidity' to have high contribution score