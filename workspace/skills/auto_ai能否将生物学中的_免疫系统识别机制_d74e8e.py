"""
Bio-Inspired Network Anomaly Detection System.

This module implements an anomaly detection algorithm based on the biological
'Negative Selection Algorithm' (NSA) found in the human immune system.

Concept Mapping (Source Domain: Biology -> Target Domain: Cyber Security):
1. Self (Body Cells) -> Normal Network Traffic Patterns.
2. Non-Self (Pathogens) -> Malicious/Anomalous Traffic Patterns.
3. T-Cells (Detectors) -> Generated signature vectors.
4. Thymus Selection (Training) -> Filtering out detectors that match 'Self'.
5. Immune Response (Detection) -> Matching a detector against incoming traffic.

Domain: knowledge_transfer
"""

import logging
import random
from typing import List, Tuple, Union
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BioInspiredIDS:
    """
    A class representing an Intrusion Detection System (IDS) based on
    the biological immune system's negative selection mechanism.
    """

    def __init__(self, feature_dim: int, num_detectors: int = 100, threshold: float = 0.5):
        """
        Initialize the Bio-Inspired IDS.

        Args:
            feature_dim (int): The dimensionality of the traffic feature vectors.
            num_detectors (int): The number of mature detectors (T-cells) to generate.
            threshold (float): The affinity threshold for matching (Euclidean distance).

        Raises:
            ValueError: If feature_dim or num_detectors are not positive, or threshold is invalid.
        """
        self._validate_init_params(feature_dim, num_detectors, threshold)
        
        self.feature_dim = feature_dim
        self.num_detectors = num_detectors
        self.threshold = threshold
        self.detectors: np.ndarray = np.zeros((0, feature_dim))
        self.is_trained = False

        logger.info(f"BioInspiredIDS initialized with dim={feature_dim}, n_detectors={num_detectors}")

    def _validate_init_params(self, feature_dim: int, num_detectors: int, threshold: float) -> None:
        """Validate initialization parameters."""
        if feature_dim <= 0:
            raise ValueError("Feature dimension must be positive.")
        if num_detectors <= 0:
            raise ValueError("Number of detectors must be positive.")
        if not (0 < threshold < float('inf')):
            raise ValueError("Threshold must be a positive float.")

    def _calculate_affinity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Helper function: Calculate the affinity (Euclidean distance) between two vectors.
        
        In biology, this represents the binding strength between an antigen and a receptor.
        
        Args:
            vec1 (np.ndarray): First vector.
            vec2 (np.ndarray): Second vector.

        Returns:
            float: The Euclidean distance.
        """
        return np.linalg.norm(vec1 - vec2)

    def _validate_input_data(self, data: List[List[float]], name: str) -> np.ndarray:
        """
        Helper function: Validate and convert input data to numpy array.
        
        Args:
            data (List[List[float]]): Input data list.
            name (str): Name of the data variable for logging.

        Returns:
            np.ndarray: Validated data array.

        Raises:
            ValueError: If data is empty or dimensions mismatch.
        """
        if not data:
            raise ValueError(f"{name} cannot be empty.")
        
        data_arr = np.array(data)
        if data_arr.ndim != 2:
            raise ValueError(f"{name} must be a 2D array.")
        if data_arr.shape[1] != self.feature_dim:
            raise ValueError(
                f"{name} feature dimension {data_arr.shape[1]} does not match "
                f"initialized dimension {self.feature_dim}."
            )
        return data_arr

    def train(self, self_dataset: List[List[float]], bounds: Tuple[float, float] = (0.0, 1.0)) -> None:
        """
        Core Function 1: Mature Detectors (Negative Selection).
        
        Simulates the T-cell maturation process in the thymus. Randomly generates
        candidate detectors and discards any that match the 'Self' dataset (normal traffic).
        Only detectors that do NOT match 'Self' are kept to detect 'Non-Self'.

        Args:
            self_dataset (List[List[float]]): Normal traffic data representing 'Self'.
            bounds (Tuple[float, float]): Min/Max bounds for generating random features.

        Raises:
            RuntimeError: If training fails to generate enough detectors.
        """
        logger.info("Starting Negative Selection training process...")
        self_data = self._validate_input_data(self_dataset, "Self Dataset")
        
        mature_detectors = []
        attempts = 0
        max_attempts = self.num_detectors * 100  # Prevent infinite loops

        while len(mature_detectors) < self.num_detectors and attempts < max_attempts:
            # 1. Generate a random candidate T-cell (Detector)
            candidate = np.random.uniform(low=bounds[0], high=bounds[1], size=self.feature_dim)
            
            # 2. Check affinity with all Self cells
            # Calculate distances to all self samples
            distances = np.linalg.norm(self_data - candidate, axis=1)
            
            # 3. Negative Selection: If distance > threshold for ALL self, it survives
            if np.all(distances > self.threshold):
                mature_detectors.append(candidate)
            
            attempts += 1

        if len(mature_detectors) < self.num_detectors:
            logger.warning(
                f"Only generated {len(mature_detectors)} detectors out of {self.num_detectors} requested."
            )
        
        self.detectors = np.array(mature_detectors)
        self.is_trained = True
        logger.info(f"Training complete. {len(self.detectors)} mature detectors generated.")

    def detect(self, antigen: List[float]) -> bool:
        """
        Core Function 2: Immune Response (Anomaly Detection).
        
        Monitors incoming traffic (Antigen). If the antigen matches any of the
        mature detectors (within the threshold), it is identified as 'Non-Self' (Anomaly).

        Args:
            antigen (List[float]): A single traffic sample to test.

        Returns:
            bool: True if Anomaly (Non-Self) is detected, False if Normal (Self).

        Raises:
            RuntimeError: If the model has not been trained yet.
        """
        if not self.is_trained:
            raise RuntimeError("System must be trained before detection.")
        
        antigen_vec = np.array(antigen)
        if antigen_vec.shape != (self.feature_dim,):
            raise ValueError(f"Antigen dimension mismatch. Expected ({self.feature_dim},).")

        # Check affinity with all detectors
        # If distance < threshold, it means the detector recognizes the antigen
        distances = np.linalg.norm(self.detectors - antigen_vec, axis=1)
        
        is_anomaly = np.any(distances < self.threshold)
        
        if is_anomaly:
            logger.warning(f"Anomaly detected! Sample: {antigen}")
        else:
            logger.debug(f"Sample classified as normal. Sample: {antigen}")
            
        return is_anomaly

    def batch_detect(self, traffic_batch: List[List[float]]) -> List[bool]:
        """
        Perform detection on a batch of traffic samples.

        Args:
            traffic_batch (List[List[float]]): List of traffic samples.

        Returns:
            List[bool]: List of detection results.
        """
        traffic_arr = self._validate_input_data(traffic_batch, "Traffic Batch")
        results = []
        
        for sample in traffic_arr:
            results.append(self.detect(sample))
            
        return results


# Example Usage
if __name__ == "__main__":
    # 1. Define Environment
    # Let's assume traffic features are normalized between 0 and 1
    DIM = 5
    
    # 2. Generate 'Self' Data (Normal Traffic)
    # Normal traffic usually clusters around specific patterns
    normal_traffic = [
        [0.1, 0.1, 0.1, 0.1, 0.1],
        [0.12, 0.11, 0.09, 0.1, 0.1],
        [0.09, 0.1, 0.11, 0.1, 0.1],
        [0.5, 0.5, 0.5, 0.5, 0.5], # Another cluster of normal traffic
        [0.51, 0.49, 0.5, 0.5, 0.5]
    ]

    # 3. Initialize Immune System
    # We want detectors that are at least 0.15 units away from normal traffic
    ids = BioInspiredIDS(feature_dim=DIM, num_detectors=50, threshold=0.15)

    # 4. Train (Negative Selection)
    # The system will learn what 'Normal' looks like and generate detectors for everything else
    try:
        ids.train(normal_traffic)
    except ValueError as e:
        logger.error(f"Training failed: {e}")

    # 5. Test Detection
    # Case A: Normal Traffic (Should return False)
    test_normal = [0.1, 0.1, 0.1, 0.1, 0.1]
    result_normal = ids.detect(test_normal)
    print(f"Normal Sample Detection (Anomaly?): {result_normal}")  # Expected: False

    # Case B: Anomalous Traffic (Should return True)
    # This vector is far from the normal clusters
    test_anomaly = [0.9, 0.9, 0.9, 0.9, 0.9]
    result_anomaly = ids.detect(test_anomaly)
    print(f"Anomaly Sample Detection (Anomaly?): {result_anomaly}")  # Expected: True
    
    # Case C: Batch Detection
    batch_traffic = [
        [0.1, 0.1, 0.1, 0.1, 0.1], # Normal
        [0.9, 0.9, 0.9, 0.9, 0.9], # Anomaly
        [0.5, 0.5, 0.5, 0.5, 0.5]  # Normal
    ]
    batch_results = ids.batch_detect(batch_traffic)
    print(f"Batch Results: {batch_results}") # Expected: [False, True, False]