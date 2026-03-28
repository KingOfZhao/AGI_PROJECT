"""
Module: auto_latent_boundary_discovery
Description: AGI Skill for discovering expert decision boundaries from multimodal sensor data
             using unsupervised learning techniques.
"""

import logging
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from typing import Dict, Tuple, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LatentBoundaryDetector:
    """
    Discovers latent decision boundaries in high-dimensional sensor data 
    corresponding to implicit expert knowledge (e.g., "perfect cooking state").
    
    Input Format:
        - sensor_data: Dict[str, np.ndarray] where keys are sensor names 
                       and values are time-series data (samples x features).
    Output Format:
        - Dict containing cluster labels, centroids, and confidence scores.
    """

    def __init__(self, n_components: int = 2, min_clusters: int = 2, max_clusters: int = 10, random_state: int = 42):
        """
        Initialize the detector with configuration parameters.
        
        Args:
            n_components: Dimensions for PCA reduction.
            min_clusters: Minimum number of clusters to try.
            max_clusters: Maximum number of clusters to try.
            random_state: Random seed for reproducibility.
        """
        if min_clusters < 2:
            raise ValueError("min_clusters must be at least 2")
        if max_clusters <= min_clusters:
            raise ValueError("max_clusters must be greater than min_clusters")
            
        self.n_components = n_components
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components, random_state=random_state)
        self.model = None
        self.best_k = 0
        logger.info("LatentBoundaryDetector initialized with PCA components=%d, cluster range=[%d, %d]",
                    n_components, min_clusters, max_clusters)

    def _validate_input(self, sensor_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Validates and concatenates multimodal sensor data.
        
        Args:
            sensor_data: Dictionary of sensor arrays.
            
        Returns:
            Concatenated and validated feature matrix.
            
        Raises:
            ValueError: If data is invalid or shapes mismatch.
        """
        if not sensor_data:
            raise ValueError("sensor_data dictionary cannot be empty")
            
        concat_data = []
        base_samples = -1
        
        for name, data in sensor_data.items():
            if not isinstance(data, np.ndarray):
                raise TypeError(f"Data for sensor {name} must be a numpy array")
            if data.ndim != 2:
                raise ValueError(f"Data for sensor {name} must be 2D (samples, features)")
            if base_samples == -1:
                base_samples = data.shape[0]
            elif data.shape[0] != base_samples:
                raise ValueError(f"Sample count mismatch for sensor {name}")
                
            concat_data.append(data)
            logger.debug(f"Validated sensor: {name}, Shape: {data.shape}")
            
        return np.hstack(concat_data)

    def preprocess(self, raw_features: np.ndarray) -> np.ndarray:
        """
        Scales and reduces dimensionality of the raw features.
        
        Args:
            raw_features: Concatenated high-dimensional features.
            
        Returns:
            Transformed low-dimensional manifold representation.
        """
        if raw_features.shape[0] < self.n_components:
             raise ValueError(f"Need at least {self.n_components} samples for PCA, got {raw_features.shape[0]}")

        logger.info("Starting preprocessing: Scaling and PCA reduction.")
        scaled_data = self.scaler.fit_transform(raw_features)
        reduced_data = self.pca.fit_transform(scaled_data)
        logger.info("Preprocessing complete. Explained variance ratio: %s", 
                    np.sum(self.pca.explained_variance_ratio_))
        return reduced_data

    def fit_predict(self, sensor_data: Dict[str, np.ndarray]) -> Dict[str, any]:
        """
        Main entry point. Finds the optimal clustering to approximate expert boundaries.
        
        Args:
            sensor_data: Multimodal sensor inputs.
            
        Returns:
            A dictionary containing:
            - 'labels': Cluster assignment for each sample.
            - 'centroids': Coordinates of cluster centers in PCA space.
            - 'optimal_k': The selected number of clusters.
            - 'confidence': Silhouette score of the clustering.
        """
        try:
            # 1. Validation and Concatenation
            raw_X = self._validate_input(sensor_data)
            
            # 2. Preprocessing
            X_reduced = self.preprocess(raw_X)
            
            # 3. Find optimal clusters using Silhouette Score
            best_score = -1.0
            best_model = None
            
            logger.info("Starting unsupervised cluster search range [%d, %d]...", 
                        self.min_clusters, self.max_clusters)
            
            for k in range(self.min_clusters, self.max_clusters + 1):
                # Using Gaussian Mixture Model for soft boundaries
                gmm = GaussianMixture(
                    n_components=k, 
                    covariance_type='full', 
                    random_state=self.random_state,
                    n_init=5
                )
                labels = gmm.fit_predict(X_reduced)
                
                # Handle cases where only one cluster might be found or errors occur
                if len(np.unique(labels)) < 2:
                    continue
                    
                score = silhouette_score(X_reduced, labels)
                logger.debug(f"K={k}, Silhouette Score={score:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_model = gmm
                    self.best_k = k

            if best_model is None:
                raise RuntimeError("Failed to find a valid clustering solution.")

            self.model = best_model
            final_labels = self.model.predict(X_reduced)
            
            # Get centroids in PCA space
            centroids = self.model.means_
            
            result = {
                "labels": final_labels,
                "centroids": centroids,
                "optimal_k": self.best_k,
                "confidence": best_score,
                "pca_components": self.pca.components_
            }
            
            logger.info(f"Discovered {self.best_k} latent states with confidence {best_score:.4f}")
            return result

        except Exception as e:
            logger.error(f"Error during boundary discovery: {str(e)}")
            raise

# ==============================================================================
# Usage Example
# ==============================================================================
if __name__ == "__main__":
    # 1. Generate synthetic multimodal data (simulating temperature, spectral, sound)
    np.random.seed(42)
    n_samples = 500
    
    # Cluster 1: "Raw State" (Lower temp, specific spectral signature)
    temp_1 = np.random.normal(25, 2, (n_samples // 2, 1))
    spec_1 = np.random.normal(0.1, 0.05, (n_samples // 2, 10))
    sound_1 = np.random.normal(20, 5, (n_samples // 2, 1))
    
    # Cluster 2: "Ready State" (Higher temp, shifted spectral, different sound)
    temp_2 = np.random.normal(80, 5, (n_samples // 2, 1))
    spec_2 = np.random.normal(0.8, 0.1, (n_samples // 2, 10))
    sound_2 = np.random.normal(60, 10, (n_samples // 2, 1))
    
    # Combine and shuffle to simulate streaming data without labels
    data_temp = np.vstack([temp_1, temp_2])
    data_spec = np.vstack([spec_1, spec_2])
    data_sound = np.vstack([sound_1, sound_2])
    
    sensor_input = {
        "temperature_array": data_temp,
        "spectral_scan": data_spec,
        "acoustic_signature": data_sound
    }
    
    # 2. Initialize and Run Detector
    detector = LatentBoundaryDetector(n_components=5, min_clusters=2, max_clusters=5)
    
    try:
        result = detector.fit_predict(sensor_input)
        
        print("\n=== Discovery Result ===")
        print(f"Detected Latent States (K): {result['optimal_k']}")
        print(f"Boundary Confidence (Silhouette): {result['confidence']:.4f}")
        print(f"Label Distribution: {np.bincount(result['labels'])}")
        
        # 3. Interpretation
        # If K matches expert intuition (e.g., 2 states: Raw vs Ready), 
        # the AI has successfully reconstructed the latent decision boundary.
        
    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except RuntimeError as re:
        print(f"Runtime Error: {re}")