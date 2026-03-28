"""
Module: auto_语义结构映射_如何从现有2780个节点_1c2aa9
Description: [Semantic Structure Mapping] Extracts high-dimensional topological features from existing nodes
             to establish an unsupervised 'Cognitive Manifold' projection mechanism.
             
             This module maps nodes from different domains (e.g., 'cooking heat control' vs 'metallurgical temp control')
             to adjacent regions in a high-dimensional space based on structural/operational logic rather than
             raw physical attributes. This facilitates cross-domain transfer learning at the mathematical level.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union, Any
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import silhouette_score

# Attempting to import UMAP, fallback to PCA-only if not available
try:
    from umap import UMAP
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    logging.warning("UMAP library not found. Falling back to PCA for manifold projection. "
                    "Install 'umap-learn' for better topological preservation.")

# Configuring Logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# --- Constants and Configuration ---
DEFAULT_EMBEDDING_DIM = 64
RANDOM_STATE = 42

class CognitiveManifoldProjector:
    """
    Projects disparate conceptual nodes into a shared 'Cognitive Manifold'.
    
    This class handles the extraction of structural features and the projection
    into a latent space where functional similarity dictates proximity.
    """

    def __init__(self, 
                 target_dim: int = 64, 
                 n_neighbors: int = 15, 
                 min_dist: float = 0.1,
                 metric: str = 'cosine'):
        """
        Initialize the projector.

        Args:
            target_dim (int): Dimension of the output cognitive manifold.
            n_neighbors (int): Number of neighbors for UMAP local connectivity.
            min_dist (float): Minimum distance for UMAP embedding.
            metric (str): Metric used for distance calculation (e.g., 'cosine', 'euclidean').
        """
        self.target_dim = target_dim
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.metric = metric
        self.scaler_ = StandardScaler()
        self.reducer_ = None
        self.is_fitted = False
        
        logger.info(f"Initialized CognitiveManifoldProjector with target_dim={target_dim}")

    def _validate_inputs(self, X: np.ndarray, node_ids: Optional[List[str]] = None) -> None:
        """
        Validate input data shape and types.
        
        Args:
            X (np.ndarray): Input feature matrix.
            node_ids (Optional[List[str]]): Optional list of node IDs.
            
        Raises:
            ValueError: If input dimensions mismatch or data is invalid.
        """
        if not isinstance(X, np.ndarray):
            raise TypeError("Input X must be a numpy array.")
        if X.ndim != 2:
            raise ValueError(f"Input X must be 2-dimensional, got {X.ndim} dimensions.")
        if X.shape[0] < 10:
            logger.warning("Input sample size is very small (<10), manifold learning may be unstable.")
        if node_ids and len(node_ids) != X.shape[0]:
            raise ValueError(f"Number of node IDs ({len(node_ids)}) does not match samples ({X.shape[0]}).")
        
        # Check for NaN/Inf
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            raise ValueError("Input data contains NaN or Infinite values.")

    def _extract_structural_features(self, X_raw: np.ndarray) -> np.ndarray:
        """
        Helper function to normalize and preprocess features.
        Abstractly represents 'structure' extraction by normalizing scales.
        
        Args:
            X_raw (np.ndarray): Raw feature matrix.
            
        Returns:
            np.ndarray: Scaled features.
        """
        logger.debug("Scaling features to normalize structural attributes...")
        return self.scaler_.fit_transform(X_raw)

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'CognitiveManifoldProjector':
        """
        Fit the manifold model to the data.
        
        This process learns the mapping from high-dimensional attribute space 
        to the lower-dimensional cognitive space.

        Args:
            X (np.ndarray): Matrix of shape (n_samples, n_features).
            y (Optional[np.ndarray]): Ignored, present for sklearn compatibility.

        Returns:
            self: The fitted projector instance.
        """
        self._validate_inputs(X)
        logger.info(f"Starting manifold fitting on {X.shape[0]} nodes...")
        
        # Step 1: Feature Scaling (Normalization)
        X_scaled = self._extract_structural_features(X)
        
        # Step 2: Dimensionality Reduction / Manifold Learning
        if UMAP_AVAILABLE:
            logger.info("Using UMAP for topological projection.")
            self.reducer_ = UMAP(
                n_components=self.target_dim,
                n_neighbors=self.n_neighbors,
                min_dist=self.min_dist,
                metric=self.metric,
                random_state=RANDOM_STATE,
                transform_seed=RANDOM_STATE
            )
        else:
            # Fallback: PCA (Linear manifold, less ideal for 'cognitive' curves)
            logger.warning("Using PCA for linear projection (Fallback).")
            self.reducer_ = PCA(
                n_components=min(self.target_dim, X_scaled.shape[1], X_scaled.shape[0]),
                random_state=RANDOM_STATE
            )
            
        self.reducer_.fit(X_scaled)
        self.is_fitted = True
        logger.info("Manifold fitting complete.")
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Project new nodes into the cognitive manifold.
        
        Args:
            X (np.ndarray): New data points.
            
        Returns:
            np.ndarray: Coordinates in the cognitive manifold.
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call .fit() first.")
        
        self._validate_inputs(X)
        X_scaled = self.scaler_.transform(X) # Use pre-computed scaling params
        return self.reducer_.transform(X_scaled)

    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(X, y)
        return self.reducer_.embedding_ if hasattr(self.reducer_, 'embedding_') else self.transform(X)

    def analyze_cognitive_neighbors(self, 
                                    X_train: np.ndarray, 
                                    query_idx: int, 
                                    k: int = 5) -> Dict[str, Any]:
        """
        Analyze the cognitive proximity of a specific node to others.
        
        This function helps verify if 'cooking' nodes are indeed close to 'chemistry' nodes
        in the learned space.
        
        Args:
            X_train (np.ndarray): The training data used to fit (or embeddings).
            query_idx (int): Index of the node to query.
            k (int): Number of neighbors to retrieve.
            
        Returns:
            Dict containing distances and indices of neighbors.
        """
        if query_idx >= X_train.shape[0] or query_idx < 0:
            raise IndexError(f"Query index {query_idx} out of bounds.")
            
        # Ensure we are working on the manifold (embedding)
        if self.is_fitted and hasattr(self.reducer_, 'embedding_'):
            embedding = self.reducer_.embedding_
        else:
            # Fallback if checking before transform or on raw data logic
            embedding = X_train 

        nbrs = NearestNeighbors(n_neighbors=k+1, algorithm='auto', metric=self.metric).fit(embedding)
        distances, indices = nbrs.kneighbors([embedding[query_idx]])
        
        return {
            "query_index": query_idx,
            "neighbor_indices": indices[0][1:].tolist(), # Exclude self
            "distances": distances[0][1:].tolist()
        }


# --- Utility Functions ---

def generate_mock_nodes(n_samples: int = 2780, n_features: int = 128) -> pd.DataFrame:
    """
    Generates mock data representing 2780 nodes with cross-domain latent features.
    
    Simulates two domains: 'Culinary' and 'Metallurgy' with shared latent variables 
    (e.g., 'temperature_control_factor', 'timing_sensitivity').
    
    Args:
        n_samples (int): Number of nodes.
        n_features (int): Dimensionality of raw features.
        
    Returns:
        pd.DataFrame: DataFrame with features and metadata.
    """
    logger.info(f"Generating {n_samples} mock nodes for testing...")
    
    # Latent factors
    # Factor 1: Temporal Control (shared by Cooking and Chem)
    # Factor 2: Thermal Intensity (shared by Cooking and Metallurgy)
    
    # Domain A: Cooking (1500 nodes)
    n_cook = n_samples // 2
    # High temporal control, Medium thermal intensity
    cooking_base = np.random.normal(loc=0.5, scale=0.2, size=(n_cook, 2))
    
    # Domain B: Metallurgy (1280 nodes)
    n_meta = n_samples - n_cook
    # Medium temporal control, High thermal intensity
    meta_base = np.random.normal(loc=0.8, scale=0.2, size=(n_meta, 2))
    
    # Combine latent structure
    latent_core = np.vstack([cooking_base, meta_base])
    
    # Expand to high dimensions with noise (creating the 'observation' space)
    # We project the 2 latent dims up to n_features
    projection_matrix = np.random.randn(2, n_features)
    noise = np.random.normal(0, 0.1, (n_samples, n_features))
    features = np.dot(latent_core, projection_matrix) + noise
    
    # Create DataFrame
    domains = ['Culinary'] * n_cook + ['Metallurgy'] * n_meta
    ids = [f"node_{i}" for i in range(n_samples)]
    
    df = pd.DataFrame(features, columns=[f"feat_{i}" for i in range(n_features)])
    df['node_id'] = ids
    df['domain'] = domains
    
    # Shuffle
    df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    
    return df

def run_skill_example():
    """
    Example execution flow for the Semantic Structure Mapping skill.
    """
    # 1. Prepare Data
    nodes_df = generate_mock_nodes(n_samples=2780)
    feature_cols = [c for c in nodes_df.columns if 'feat_' in c]
    X_raw = nodes_df[feature_cols].values
    
    # 2. Initialize Projector
    # Target dim 64 is good for dense semantic representation
    projector = CognitiveManifoldProjector(target_dim=32, n_neighbors=20, metric='cosine')
    
    # 3. Fit Model (Learning the Cognitive Manifold)
    try:
        manifold_embeddings = projector.fit_transform(X_raw)
        print(f"Projected Shape: {manifold_embeddings.shape}")
        
        # 4. Verification: Check Cross-Domain Mapping
        # Find a Culinary node (should map close to Metallurgy if logic holds)
        # Due to our mock data generation, nodes with similar 'temporal_control' should cluster
        
        # Pick a random Culinary node
        culinary_indices = nodes_df[nodes_df['domain'] == 'Culinary'].index.tolist()
        target_idx = culinary_indices[0]
        
        analysis = projector.analyze_cognitive_neighbors(manifold_embeddings, target_idx, k=5)
        
        print(f"\n--- Analysis for Node {target_idx} ({nodes_df.loc[target_idx, 'domain']}) ---")
        
        for i, neighbor_idx in enumerate(analysis['neighbor_indices']):
            neighbor_domain = nodes_df.loc[neighbor_idx, 'domain']
            dist = analysis['distances'][i]
            print(f"Neighbor {i+1}: Domain={neighbor_domain}, Index={neighbor_idx}, Distance={dist:.4f}")
            
        # Ideally, we should see some Metallurgy nodes appearing as neighbors
        # if the 'Thermal Intensity' feature aligned them in the manifold.
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)

if __name__ == "__main__":
    run_skill_example()