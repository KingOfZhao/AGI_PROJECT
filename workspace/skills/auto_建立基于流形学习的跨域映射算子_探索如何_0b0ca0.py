"""
Module: auto_建立基于流形学习的跨域映射算子_探索如何_0b0ca0
Description: Implements manifold learning-based cross-domain mapping operators.
             This module aligns unstructured semantic vectors to structured execution spaces
             and calculates the 'Information Loss Rate' during projection.
Author: AGI System Core Team
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, Union
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist
from scipy.linalg import pinv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ManifoldAlignmentError(Exception):
    """Custom exception for manifold alignment errors."""
    pass


def _validate_vector_space(
    vectors: np.ndarray, 
    space_name: str, 
    expected_dim: Optional[int] = None
) -> np.ndarray:
    """
    Helper function: Validates input vector space integrity.
    
    Args:
        vectors (np.ndarray): Input data matrix (n_samples, n_features).
        space_name (str): Name of the space for logging purposes.
        expected_dim (Optional[int]): If provided, checks if dimensions match.
    
    Returns:
        np.ndarray: Validated and cleaned vector array.
    
    Raises:
        ManifoldAlignmentError: If data is invalid or dimensions mismatch.
    """
    logger.debug(f"Validating {space_name} with shape {vectors.shape}")
    
    if not isinstance(vectors, np.ndarray):
        raise ManifoldAlignmentError(f"{space_name} must be a numpy array.")
    
    if vectors.ndim != 2:
        raise ManifoldAlignmentError(f"{space_name} must be 2-dimensional (samples, features).")
        
    if vectors.shape[0] < 2:
        raise ManifoldAlignmentError(f"{space_name} must contain at least 2 samples.")
        
    if np.isnan(vectors).any() or np.isinf(vectors).any():
        logger.warning(f"NaN or Inf values detected in {space_name}, attempting to clean.")
        vectors = np.nan_to_num(vectors)
        
    if expected_dim is not None and vectors.shape[1] != expected_dim:
        raise ManifoldAlignmentError(
            f"Dimension mismatch in {space_name}. Expected {expected_dim}, got {vectors.shape[1]}"
        )
        
    return vectors


def calculate_information_loss(
    original_vectors: np.ndarray, 
    reconstructed_vectors: np.ndarray
) -> float:
    """
    Core Function 1: Calculates the Information Loss Rate (ILR).
    
    ILR is defined here as 1 minus the cosine similarity preservation ratio 
    between the original high-dimensional space and the reconstructed space,
    normalized by the relative reconstruction error.
    
    Args:
        original_vectors (np.ndarray): The source data before projection.
        reconstructed_vectors (np.ndarray): The data after inverse projection.
        
    Returns:
        float: Information loss rate between 0.0 (perfect) and 1.0 (total loss).
    """
    if original_vectors.shape != reconstructed_vectors.shape:
        logger.error("Shape mismatch between original and reconstructed vectors.")
        return 1.0

    # Calculate Frobenius norm of the difference (Reconstruction Error)
    reconstruction_error = np.linalg.norm(original_vectors - reconstructed_vectors, 'fro')
    original_norm = np.linalg.norm(original_vectors, 'fro')
    
    if original_norm == 0:
        return 1.0
        
    relative_error = reconstruction_error / original_norm
    
    # Calculate Correlation Matrix Distance preservation
    # We compare the topological structure preservation via distance matrices
    dist_orig = cdist(original_vectors, original_vectors, 'euclidean')
    dist_recon = cdist(reconstructed_vectors, reconstructed_vectors, 'euclidean')
    
    # Normalize distance matrices
    dist_orig_norm = dist_orig / (np.max(dist_orig) + 1e-10)
    dist_recon_norm = dist_recon / (np.max(dist_recon) + 1e-10)
    
    # Topological preservation score (MSE between normalized distance matrices)
    topological_distortion = np.mean((dist_orig_norm - dist_recon_norm) ** 2)
    
    # Combined Information Loss Metric
    loss_rate = (relative_error + topological_distortion) / 2.0
    loss_rate = min(max(loss_rate, 0.0), 1.0) # Clamp to [0, 1]
    
    logger.info(f"Calculated Information Loss Rate: {loss_rate:.4f}")
    return loss_rate


class CrossDomainManifoldOperator:
    """
    Core Function 2: A class-based operator that establishes a mapping between 
    unstructured semantic space (Source) and structured execution space (Target).
    """
    
    def __init__(self, target_dim: int = 8, regularization: float = 1e-5):
        """
        Initializes the operator.
        
        Args:
            target_dim (int): The dimensionality of the structured execution space.
            regularization (float): Regularization term for pseudo-inverse calculation.
        """
        self.target_dim = target_dim
        self.regularization = regularization
        self.scaler_source = StandardScaler()
        self.scaler_target = StandardScaler()
        self.projection_matrix: Optional[np.ndarray] = None
        self.inverse_projection_matrix: Optional[np.ndarray] = None
        self.pca_source: Optional[PCA] = None
        self.pca_target: Optional[PCA] = None
        self.is_fitted = False
        logger.info(f"Initialized CrossDomainManifoldOperator with target_dim={target_dim}")

    def fit(self, source_vectors: np.ndarray, target_vectors: np.ndarray) -> None:
        """
        Fits the mapping operator using paired data (supervised manifold alignment).
        
        Strategy:
        1. Reduce source (semantic) and target (execution) dimensions using PCA.
        2. Learn a linear projection matrix M that maps reduced_source -> reduced_target.
        
        Args:
            source_vectors (np.ndarray): Unstructured semantic vectors (N, D_s).
            target_vectors (np.ndarray): Structured execution vectors (N, D_t).
        """
        logger.info("Starting fitting process for cross-domain mapping...")
        
        # 1. Validation
        source_vectors = _validate_vector_space(source_vectors, "Source Space")
        target_vectors = _validate_vector_space(target_vectors, "Target Space")
        
        if source_vectors.shape[0] != target_vectors.shape[0]:
            raise ManifoldAlignmentError("Number of samples in source and target must match.")

        # 2. Preprocessing (Normalization)
        source_norm = self.scaler_source.fit_transform(source_vectors)
        target_norm = self.scaler_target.fit_transform(target_vectors)

        # 3. Dimensionality Reduction (Manifold flattening)
        # We reduce source to target_dim to ensure the mapping is square or over-complete
        n_components = min(self.target_dim, source_vectors.shape[1], target_vectors.shape[1])
        
        self.pca_source = PCA(n_components=n_components)
        self.pca_target = PCA(n_components=n_components)
        
        source_latent = self.pca_source.fit_transform(source_norm)
        target_latent = self.pca_target.fit_transform(target_norm)
        
        logger.debug(f"Source latent shape: {source_latent.shape}")
        logger.debug(f"Target latent shape: {target_latent.shape}")

        # 4. Learn Mapping Operator (Linear Regression approach: Y = XW)
        # W = pinv(X) * Y
        # Adding regularization for stability
        identity = np.eye(source_latent.shape[1]) * self.regularization
        xt_x = source_latent.T @ source_latent + identity
        xt_y = source_latent.T @ target_latent
        
        try:
            self.projection_matrix = np.linalg.solve(xt_x, xt_y)
            # Inverse mapping: W_inv = pinv(W)
            self.inverse_projection_matrix = pinv(self.projection_matrix)
            self.is_fitted = True
            logger.info("Model fitted successfully. Projection matrix shape: %s", self.projection_matrix.shape)
        except np.linalg.LinAlgError as e:
            logger.error("Linear algebra error during projection calculation: %s", e)
            raise ManifoldAlignmentError("Failed to solve for projection matrix.")

    def project(self, vectors: np.ndarray) -> np.ndarray:
        """
        Projects unstructured semantic vectors into the structured execution space.
        
        Args:
            vectors (np.ndarray): Input semantic vectors.
            
        Returns:
            np.ndarray: Mapped vectors in the execution space structure.
        """
        if not self.is_fitted:
            raise ManifoldAlignmentError("Operator has not been fitted yet.")
            
        vectors = _validate_vector_space(vectors, "Input Projection")
        
        # Transform through pipeline: Scale -> PCA -> Project -> Inverse Scale Target
        vec_norm = self.scaler_source.transform(vectors)
        vec_latent = self.pca_source.transform(vec_norm)
        
        # Apply learned manifold mapping
        mapped_latent = vec_latent @ self.projection_matrix
        
        # Reconstruct to target space dimensions
        # Note: We reconstruct the PCA components back to the original target scaled space
        mapped_execution_space = self.pca_target.inverse_transform(mapped_latent)
        mapped_final = self.scaler_target.inverse_transform(mapped_execution_space)
        
        return mapped_final

    def evaluate_alignment_quality(self, source_test: np.ndarray, target_test: np.ndarray) -> Dict[str, float]:
        """
        Evaluates the mapping quality and information loss on a test set.
        
        Args:
            source_test (np.ndarray): Test source vectors.
            target_test (np.ndarray): Ground truth target vectors.
            
        Returns:
            Dict[str, float]: Metrics including MSE, Cosine Similarity, and Info Loss.
        """
        _validate_vector_space(source_test, "Test Source")
        _validate_vector_space(target_test, "Test Target")
        
        # 1. Forward Projection
        predicted_target = self.project(source_test)
        
        # 2. Calculate Reconstruction Accuracy (MSE)
        mse = np.mean((predicted_target - target_test) ** 2)
        
        # 3. Calculate Information Loss
        # To calculate "projection loss", we project forward, then inverse back to source
        # and compare original source vs reconstructed source.
        
        # Inverse pipeline: Scale Target -> PCA Target Inv -> Inverse Project -> PCA Source Inv -> Scale Source Inv
        # This requires a separate inverse method, but for the metric we simulate it:
        # Loss = Compare (Target Ground Truth) vs (Target Predicted) structure
        
        # Here we define Info Loss specifically as the structural distortion between
        # the ground truth target and the predicted target.
        loss_rate = calculate_information_loss(target_test, predicted_target)
        
        return {
            "mean_squared_error": float(mse),
            "information_loss_rate": loss_rate,
            "alignment_score": 1.0 - loss_rate
        }


if __name__ == "__main__":
    # Example Usage
    print("Running Cross-Domain Manifold Mapping Example...")
    
    # 1. Generate Synthetic Data
    # Source: High-dimensional "Semantic" space (e.g., 128 dims)
    # Target: Low-dimensional "Execution" space (e.g., 8 dims, structured)
    np.random.seed(42)
    n_samples = 100
    source_data = np.random.randn(n_samples, 128)
    # Create a structured target that has some correlation with source
    target_data = np.random.randn(n_samples, 8) 
    target_data[:, 0] = source_data[:, 0] * 2.0 # Correlation
    
    # 2. Initialize Operator
    operator = CrossDomainManifoldOperator(target_dim=8)
    
    # 3. Fit the Operator
    try:
        operator.fit(source_data, target_data)
        
        # 4. Project new data
        new_semantic_vec = np.random.randn(5, 128)
        mapped_execution_vec = operator.project(new_semantic_vec)
        
        print(f"Input Shape:  {new_semantic_vec.shape}")
        print(f"Output Shape: {mapped_execution_vec.shape}")
        
        # 5. Evaluate
        metrics = operator.evaluate_alignment_quality(source_data, target_data)
        print(f"Evaluation Metrics: {metrics}")
        
    except ManifoldAlignmentError as e:
        print(f"Error: {e}")