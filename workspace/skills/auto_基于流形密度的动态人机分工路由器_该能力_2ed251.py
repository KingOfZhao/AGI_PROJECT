"""
Manifold Density-Based Dynamic Human-AI Allocation Router

This module implements a cognitive-inspired routing mechanism that determines 
whether a task should be processed autonomously by AI or escalated to human 
intervention based on the local density of input data within a learned 
manifold space.

Key Metaphor:
- Dense Regions = "Known Knowledge" (AI High Confidence)
- Sparse Regions = "Unknown/Edge Cases" (AI Low Confidence -> Cognitive Perplexity)

Author: AGI System Core Engineering Team
Version: 2.0.1
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pydantic import BaseModel, Field, ValidationError
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
DEFAULT_N_NEIGHBORS = 20
DEFAULT_DENSITY_THRESHOLD = 1.5  # LOF score threshold (lower means denser)
DEFAULT_CONTAMINATION = 0.1

class RouterInputSchema(BaseModel):
    """Data validation schema for router inputs using Pydantic."""
    task_id: str = Field(..., description="Unique identifier for the task")
    features: List[float] = Field(..., description="Vector representation of the task in latent space")
    metadata: Optional[Dict] = Field(default={}, description="Additional context")

class RoutingDecision(BaseModel):
    """Output schema for the routing decision."""
    task_id: str
    action: str = Field(..., description="Either 'AUTO_PROCESS' or 'HUMAN_ESCALATION'")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    density_score: float = Field(..., description="Raw manifold density metric")
    reason: str

def _validate_and_normalize_input(data: Dict) -> Tuple[np.ndarray, str]:
    """
    Auxiliary function: Validates input data structure and converts to numpy array.
    
    Args:
        data (Dict): Raw input dictionary containing 'task_id' and 'features'.
        
    Returns:
        Tuple[np.ndarray, str]: Normalized feature vector and task ID.
        
    Raises:
        ValueError: If data validation fails.
    """
    try:
        validated = RouterInputSchema(**data)
        features = np.array(validated.features).reshape(1, -1)
        
        # Check for NaN or Inf which would break distance calculations
        if not np.all(np.isfinite(features)):
            raise ValueError("Feature vector contains NaN or Infinite values.")
            
        return features, validated.task_id
    except ValidationError as e:
        logger.error(f"Input validation failed: {e}")
        raise ValueError(f"Invalid input format: {e}")

class ManifoldDensityRouter:
    """
    A router that uses Manifold Density estimation to delegate tasks.
    
    It learns the distribution of 'known' cases (training data) and calculates
    the Local Outlier Factor (LOF) for new inputs to estimate how well they
    fit into the learned distribution.
    """
    
    def __init__(self, n_neighbors: int = DEFAULT_N_NEIGHBORS, 
                 density_threshold: float = DEFAULT_DENSITY_THRESHOLD):
        """
        Initialize the Router.
        
        Args:
            n_neighbors (int): Number of neighbors to use for density estimation.
            density_threshold (float): The cutoff LOF score. 
                                       Scores > threshold trigger human escalation.
        """
        self.n_neighbors = n_neighbors
        self.density_threshold = density_threshold
        self.scaler = StandardScaler()
        # Local Outlier Factor is ideal for measuring local density deviations
        self.lof_estimator = None
        self.is_fitted = False
        logger.info(f"Router initialized with k={n_neighbors}, threshold={density_threshold}")

    def calibrate(self, historical_data: np.ndarray) -> None:
        """
        Fit the router on historical 'normal' operational data.
        
        This establishes the 'knowledge manifold' of the AI system.
        
        Args:
            historical_data (np.ndarray): Matrix of shape (n_samples, n_features)
                                          representing past successful tasks.
        """
        if historical_data.shape[0] < self.n_neighbors:
            raise ValueError(f"Insufficient historical data. Need at least {self.n_neighbors} samples.")
        
        logger.info("Calibrating router manifold space...")
        
        # Normalize data to ensure fair distance calculations
        scaled_data = self.scaler.fit_transform(historical_data)
        
        # Initialize and fit LOF
        self.lof_estimator = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            novelty=True,  # Enable prediction on new unseen data
            contamination=DEFAULT_CONTAMINATION
        )
        self.lof_estimator.fit(scaled_data)
        self.is_fitted = True
        
        logger.info("Calibration complete. Manifold density model ready.")

    def _calculate_density_score(self, features: np.ndarray) -> float:
        """
        Core internal function: Computes the density score (negative LOF).
        
        Args:
            features (np.ndarray): Scaled input features (1, n_features).
            
        Returns:
            float: Density score. Higher is denser (more confident). 
                   Negative values indicate outliers.
        """
        if not self.is_fitted:
            raise RuntimeError("Router must be calibrated before processing requests.")
            
        # decision_function gives positive for inliers, negative for outliers
        # specifically: opposite of LOF (larger is more normal)
        score = self.lof_estimator.decision_function(features)
        return float(score[0])

    def route_request(self, raw_input: Dict) -> Dict:
        """
        Main Interface: Determines the routing path for a given task.
        
        Args:
            raw_input (Dict): Dictionary containing 'task_id' and 'features'.
            
        Returns:
            Dict: Routing decision containing action, confidence, and metadata.
            
        Example:
            >>> router = ManifoldDensityRouter()
            >>> # Assume router is calibrated
            >>> input_data = {"task_id": "123", "features": [0.5, 1.2]}
            >>> result = router.route_request(input_data)
            >>> print(result['action'])
            'AUTO_PROCESS'
        """
        # 1. Input Validation
        try:
            features, task_id = _validate_and_normalize_input(raw_input)
        except ValueError as e:
            return RoutingDecision(
                task_id="UNKNOWN", 
                action="ERROR", 
                confidence_score=0.0, 
                density_score=0.0, 
                reason=str(e)
            ).dict()

        # 2. Preprocessing
        try:
            scaled_features = self.scaler.transform(features)
        except Exception as e:
            logger.error(f"Scaling transformation failed: {e}")
            raise

        # 3. Compute Density (Metacognitive Check)
        density_score = self._calculate_density_score(scaled_features)
        
        # 4. Logic Gate: Manifold Check
        # Note: LOF decision function is negative for outliers.
        # We use density_threshold to define the boundary of "I don't know".
        
        is_ambiguous = density_score < self.density_threshold
        
        # Map density to a pseudo-confidence (0.0 to 1.0)
        # This is a sigmoid-like mapping for demonstration
        confidence = 1 / (1 + np.exp(-density_score))
        
        if is_ambiguous:
            action = "HUMAN_ESCALATION"
            reason = "Cognitive Perplexity: Input located in sparse manifold region (Edge Case)."
            logger.warning(f"Task {task_id} triggered perplexity. Score: {density_score:.4f}")
        else:
            action = "AUTO_PROCESS"
            reason = "High Confidence: Input located in dense manifold region."
            logger.info(f"Task {task_id} routed to AI. Score: {density_score:.4f}")
            
        # 5. Construct Output
        decision = RoutingDecision(
            task_id=task_id,
            action=action,
            confidence_score=float(confidence),
            density_score=density_score,
            reason=reason
        )
        
        return decision.dict()

# --- Usage Example (in comments) ---
"""
if __name__ == "__main__":
    # 1. Setup dummy historical data (The AI's "Experience")
    # 100 samples, 5 features
    X_train = np.random.randn(100, 5) 
    
    # 2. Initialize and Calibrate
    router = ManifoldDensityRouter(n_neighbors=10, density_threshold=0.5)
    router.calibrate(X_train)
    
    # 3. Test Case 1: Normal data (Inside manifold)
    normal_input = {"task_id": "task_001", "features": np.random.randn(5).tolist()}
    
    # 4. Test Case 2: Outlier data (Sparse manifold)
    outlier_input = {"task_id": "task_002", "features": (np.random.randn(5) * 10).tolist()}
    
    # 5. Route
    res_normal = router.route_request(normal_input)
    res_outlier = router.route_request(outlier_input)
    
    print(f"Normal Route: {res_normal['action']}")
    print(f"Outlier Route: {res_outlier['action']}")
"""