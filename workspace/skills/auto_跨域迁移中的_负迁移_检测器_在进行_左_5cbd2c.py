"""
Module: auto_跨域迁移中的_负迁移_检测器_在进行_左_5cbd2c

This module provides a mechanism to detect Negative Transfer in Cross-Domain
Transfer Learning scenarios. It specifically addresses the risk of transferring
knowledge when the source and target domains have conflicting underlying
topological structures (manifolds).

The core component is the `NegativeTransferDetector` class, which utilizes
MMD (Maximum Mean Discrepancy) to calculate a 'Domain Distance'. If the
distance or the structural discrepancy exceeds a defined threshold, the
transfer is blocked to prevent the creation of 'False Positive Nodes'
(artifacts where source knowledge incorrectly applies to target data).

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, Union
from sklearn.metrics.pairwise import rbf_kernel
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NegativeTransferDetector")


@dataclass
class DomainMetric:
    """
    Data container for domain metrics.
    
    Attributes:
        distance (float): The calculated distance between domains.
        is_negative (bool): Flag indicating if negative transfer is detected.
        message (str): Detailed status message.
    """
    distance: float
    is_negative: bool
    message: str


class NegativeTransferDetector:
    """
    A detector class for identifying negative transfer scenarios in 
    left-right cross-domain overlapping tasks.
    
    This class calculates the RBF kernel-based Maximum Mean Discrepancy (MMD)
    between source and target feature distributions. It acts as a gatekeeper,
    blocking knowledge transfer if the domains are deemed too structurally
    distinct.
    """

    def __init__(
        self, 
        distance_threshold: float = 0.5, 
        gamma: float = 1.0,
        min_samples: int = 10
    ) -> None:
        """
        Initialize the detector with configuration parameters.
        
        Args:
            distance_threshold (float): The threshold above which the domain 
                                        distance is considered too large for 
                                        safe transfer.
            gamma (float): Kernel coefficient for RBF.
            min_samples (int): Minimum number of samples required to perform 
                               validation.
        """
        if distance_threshold < 0:
            raise ValueError("Distance threshold must be non-negative.")
        if gamma <= 0:
            raise ValueError("Gamma must be positive.")
        if min_samples < 1:
            raise ValueError("Minimum samples must be at least 1.")

        self.distance_threshold = distance_threshold
        self.gamma = gamma
        self.min_samples = min_samples
        logger.info("NegativeTransferDetector initialized with threshold %.2f", distance_threshold)

    def _validate_input_data(self, source: np.ndarray, target: np.ndarray) -> None:
        """
        Helper function to validate input data shapes and types.
        
        Args:
            source (np.ndarray): Source domain data.
            target (np.ndarray): Target domain data.
            
        Raises:
            TypeError: If inputs are not numpy arrays.
            ValueError: If arrays are empty or dimensions mismatch.
        """
        if not isinstance(source, np.ndarray) or not isinstance(target, np.ndarray):
            raise TypeError("Inputs must be numpy arrays.")
        
        if source.size == 0 or target.size == 0:
            raise ValueError("Input arrays cannot be empty.")
            
        if source.ndim != target.ndim:
            raise ValueError(f"Dimension mismatch: source has {source.ndim} dims, target has {target.ndim}.")

        if source.shape[0] < self.min_samples or target.shape[0] < self.min_samples:
            raise ValueError(f"Insufficient samples. Required: {self.min_samples}.")

    def _calculate_mmd(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Helper function to calculate the squared Maximum Mean Discrepancy (MMD)
        using an RBF kernel.
        
        The MMD measures the distance between two probability distributions.
        k(x, x) + k(y, y) - 2 * k(x, y)
        
        Args:
            x (np.ndarray): Source samples (n_samples_x, n_features).
            y (np.ndarray): Target samples (n_samples_y, n_features).
            
        Returns:
            float: The calculated MMD squared value.
        """
        logger.debug("Calculating MMD for shapes %s and %s", x.shape, y.shape)
        
        xx = rbf_kernel(x, x, gamma=self.gamma)
        yy = rbf_kernel(y, y, gamma=self.gamma)
        xy = rbf_kernel(x, y, gamma=self.gamma)
        
        mmd_sq = xx.mean() + yy.mean() - 2 * xy.mean()
        
        # Handle floating point errors that might result in slightly negative numbers
        return max(0.0, mmd_sq)

    def check_transfer_safety(self, source_data: np.ndarray, target_data: np.ndarray) -> DomainMetric:
        """
        Main function to check if transfer learning should proceed.
        
        It calculates the domain distance and compares it against the threshold.
        
        Args:
            source_data (np.ndarray): Feature matrix of the source domain.
            target_data (np.ndarray): Feature matrix of the target domain.
            
        Returns:
            DomainMetric: An object containing the distance, safety status, and message.
            
        Example:
            >>> detector = NegativeTransferDetector(distance_threshold=0.1)
            >>> src = np.random.randn(50, 10)
            >>> tgt = np.random.randn(50, 10) + 0.5
            >>> result = detector.check_transfer_safety(src, tgt)
            >>> print(result.is_negative)
        """
        try:
            self._validate_input_data(source_data, target_data)
        except (TypeError, ValueError) as e:
            logger.error("Input validation failed: %s", e)
            return DomainMetric(distance=-1.0, is_negative=True, message=f"Validation Error: {e}")

        logger.info("Calculating domain topology distance...")
        
        # Calculate Domain Distance
        domain_distance = np.sqrt(self._calculate_mmd(source_data, target_data))
        
        # Logic to detect negative transfer
        is_negative = domain_distance > self.distance_threshold
        
        if is_negative:
            msg = (
                f"NEGATIVE TRANSFER DETECTED. Domain distance {domain_distance:.4f} "
                f"exceeds threshold {self.distance_threshold}. "
                f"Blocking transfer to prevent 'False Positive Nodes'."
            )
            logger.warning(msg)
        else:
            msg = (
                f"Transfer Safe. Domain distance {domain_distance:.4f} "
                f"is within acceptable limits."
            )
            logger.info(msg)

        return DomainMetric(
            distance=domain_distance,
            is_negative=is_negative,
            message=msg
        )


if __name__ == "__main__":
    # Example Usage demonstrating the functionality
    
    # 1. Generate synthetic data representing two domains
    # Source domain: Cluster centered at 0
    np.random.seed(42)
    source_domain_data = np.random.normal(loc=0, scale=1, size=(100, 5))
    
    # Target domain (Safe): Cluster slightly shifted but overlapping
    target_domain_safe = np.random.normal(loc=0.5, scale=1, size=(100, 5))
    
    # Target domain (Unsafe): Cluster very far away (different topology/logic)
    target_domain_unsafe = np.random.normal(loc=10, scale=1, size=(100, 5))
    
    # 2. Initialize the Detector
    # Threshold set to 0.5 to demonstrate detection
    detector = NegativeTransferDetector(distance_threshold=0.5, gamma=0.5)
    
    # 3. Check Safe Transfer
    print("\n--- Checking Safe Transfer Scenario ---")
    result_safe = detector.check_transfer_safety(source_domain_data, target_domain_safe)
    print(f"Result: {result_safe.message}")
    
    # 4. Check Negative Transfer (Unsafe)
    print("\n--- Checking Negative Transfer Scenario ---")
    result_unsafe = detector.check_transfer_safety(source_domain_data, target_domain_unsafe)
    print(f"Result: {result_unsafe.message}")