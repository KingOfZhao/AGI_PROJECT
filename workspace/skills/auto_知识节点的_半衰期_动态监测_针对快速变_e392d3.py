"""
Knowledge Node Half-Life Dynamic Monitor for Fast-Changing Domains.

This module provides functionality to monitor the 'half-life' of knowledge nodes
in rapidly evolving fields (e.g., AI tools). It calculates obsolescence rates
based on activity time-series data and detects semantic drift using vector
embeddings.

Input/Output Formats:
    - Time Series Data: List[Tuple[datetime, float]]
      (Timestamp, Activity Score/Commit Count)
    - Semantic Data: List[Tuple[datetime, numpy.ndarray]]
      (Timestamp, Embedding Vector)

Example:
    >>> monitor = KnowledgeNodeMonitor()
    >>> # Simulate activity data (decaying)
    >>> dates = [datetime.now() - timedelta(days=i) for i in range(100, 0, -1)]
    >>> activity = [100 * math.exp(-0.01 * i) for i in range(100)]
    >>> half_life = monitor.calculate_half_life(list(zip(dates, activity)))
    >>> print(f"Estimated Half-Life: {half_life:.2f} days")
"""

import logging
import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Union

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KnowledgeNodeMonitor:
    """
    A class to monitor the half-life and semantic drift of knowledge nodes.
    """

    def __init__(self, drift_threshold: float = 0.7):
        """
        Initialize the monitor.

        Args:
            drift_threshold (float): Cosine similarity threshold below which
                                     semantic drift is considered significant.
                                     Range (0, 1). Default is 0.7.
        """
        self.drift_threshold = drift_threshold
        self._validate_threshold(drift_threshold)

    def _validate_threshold(self, threshold: float) -> None:
        """Validate the drift threshold parameter."""
        if not 0 < threshold < 1:
            logger.error("Drift threshold must be between 0 and 1.")
            raise ValueError("Drift threshold must be between 0 and 1.")

    def _validate_time_series(self, data: List[Tuple[datetime, float]]) -> None:
        """
        Validate input time series data.

        Args:
            data: List of (timestamp, value) tuples.

        Raises:
            ValueError: If data is empty, unsorted, or contains invalid values.
        """
        if not data:
            raise ValueError("Input data cannot be empty.")

        if len(data) < 2:
            raise ValueError("At least two data points are required for calculation.")

        timestamps = [d[0] for d in data]
        values = [d[1] for d in data]

        # Check sorting
        if timestamps != sorted(timestamps):
            raise ValueError("Data must be sorted chronologically.")

        # Check for NaN or negative values (assuming activity counts)
        if any(v < 0 or math.isnan(v) for v in values):
            raise ValueError("Values must be non-negative and finite.")

    def calculate_half_life(
        self, activity_data: List[Tuple[datetime, float]]
    ) -> Optional[float]:
        """
        Calculate the half-life of a knowledge node based on activity decay.

        Fits an exponential decay model N(t) = N0 * e^(-lambda * t) to the data.
        Half-life T = ln(2) / lambda.

        Args:
            activity_data: Chronologically sorted list of (timestamp, activity_score).

        Returns:
            Estimated half-life in days. Returns None if the trend is growth
            or cannot be calculated.
        """
        try:
            self._validate_time_series(activity_data)
        except ValueError as e:
            logger.error(f"Data validation failed: {e}")
            return None

        # Convert timestamps to days relative to the first point
        start_time = activity_data[0][0]
        x_days = np.array([(d[0] - start_time).total_seconds() / 86400.0 for d in activity_data])
        y_values = np.array([d[1] for d in activity_data])

        # Avoid log(0) by adding a small epsilon or filtering zeros
        y_values = np.where(y_values == 0, 1e-9, y_values)
        log_y = np.log(y_values)

        # Linear regression: log(y) = log(N0) - lambda * t
        # polyfit returns [slope, intercept]
        try:
            coefficients = np.polyfit(x_days, log_y, 1)
            slope = coefficients[0]
        except np.linalg.LinAlgError:
            logger.error("Singular matrix encountered during regression.")
            return None

        # lambda is the negative of the slope
        decay_rate = -slope

        # If slope is positive, the activity is growing, not decaying
        if decay_rate <= 0:
            logger.info("Activity is trending upwards or stable. No half-life calculated.")
            return None

        half_life = math.log(2) / decay_rate
        logger.info(f"Calculated half-life: {half_life:.2f} days (Decay rate: {decay_rate:.4f})")
        return half_life

    def detect_semantic_drift(
        self, semantic_data: List[Tuple[datetime, np.ndarray]]
    ) -> Tuple[bool, float]:
        """
        Detect semantic drift by comparing the oldest and newest embeddings.

        Args:
            semantic_data: List of (timestamp, embedding_vector).

        Returns:
            A tuple (is_drifted, similarity_score).
            is_drifted is True if similarity < threshold.
        """
        if len(semantic_data) < 2:
            logger.warning("Insufficient semantic data for drift detection.")
            return False, 1.0

        # Compare the first (oldest) and last (newest) vectors
        vec_start = semantic_data[0][1]
        vec_end = semantic_data[-1][1]

        if vec_start.shape != vec_end.shape:
            logger.error("Embedding dimensions do not match.")
            raise ValueError("Embedding dimensions must be consistent.")

        # Calculate Cosine Similarity
        dot_product = np.dot(vec_start, vec_end)
        norm_a = np.linalg.norm(vec_start)
        norm_b = np.linalg.norm(vec_end)

        if norm_a == 0 or norm_b == 0:
            logger.warning("Zero vector encountered in embeddings.")
            return False, 0.0

        similarity = dot_product / (norm_a * norm_b)
        
        # Clamp value to handle floating point errors slightly outside [-1, 1]
        similarity = max(min(similarity, 1.0), -1.0)

        is_drifted = similarity < self.drift_threshold
        
        status = "DRIFTED" if is_drifted else "STABLE"
        logger.info(f"Semantic Analysis: {status} (Similarity: {similarity:.4f})")

        return is_drifted, similarity


# Example Usage
if __name__ == "__main__":
    # 1. Setup Monitor
    monitor = KnowledgeNodeMonitor(drift_threshold=0.8)

    # 2. Generate Synthetic Activity Data (Exponential Decay)
    # Simulating a tool that was popular but is dying out
    base_time = datetime.now()
    time_points = [base_time - timedelta(days=i) for i in range(30, 0, -1)]
    
    # N(t) = 100 * e^(-0.05 * t) -> Half-life should be approx 13.86 days
    activity_scores = [100 * math.exp(-0.05 * i) + np.random.normal(0, 2) for i in range(30)]
    
    activity_dataset = list(zip(time_points, activity_scores))
    
    # 3. Calculate Half-Life
    print("--- Half-Life Calculation ---")
    hl = monitor.calculate_half_life(activity_dataset)
    if hl:
        print(f"Result: The knowledge node has a half-life of {hl:.2f} days.")
    else:
        print("Result: Node is stable or growing.")

    # 4. Generate Synthetic Semantic Data (Drifting)
    # Start with vector [1, 0], end with vector [0, 1] (Orthogonal -> Similarity 0)
    semantic_dataset = []
    for i, t in enumerate(time_points):
        # Linearly interpolate vector components
        val = i / 30.0
        vec = np.array([1 - val, val])
        semantic_dataset.append((t, vec))

    # 5. Detect Semantic Drift
    print("\n--- Semantic Drift Detection ---")
    drifted, score = monitor.detect_semantic_drift(semantic_dataset)
    print(f"Result: Drift Detected? {drifted}, Similarity Score: {score:.4f}")