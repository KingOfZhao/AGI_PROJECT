"""
auto_基于向量空间稀疏度的_跨域意外发现_s_86ce31

This module implements a 'Serendipity' algorithm for cross-domain discovery.
It focuses on identifying pairs of nodes that are spatially distant in a vector space
(hence sparse/different domains) but structurally similar (e.g., sharing topological
characteristics or local density), and generating hypothetical bridging concepts.

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import pairwise_distances

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SerendipitousPair:
    """Represents a pair of nodes identified for cross-domain discovery."""
    source_idx: int
    target_idx: int
    spatial_distance: float
    structural_similarity: float
    serendipity_score: float
    hypothesis_vector: Optional[np.ndarray] = None

class VectorSpaceSerendipity:
    """
    A class to perform cross-domain serendipity discovery based on vector space sparsity.
    
    This algorithm identifies "High Distance, Structural Similarity" pairs to break 
    information filter bubbles (echo chambers).
    
    Attributes:
        embeddings (np.ndarray): The matrix of node embeddings (N x D).
        n_neighbors (int): Number of neighbors to consider for structural density.
        metric (str): Distance metric for spatial calculations.
    """

    def __init__(self, embeddings: np.ndarray, n_neighbors: int = 10, metric: str = 'cosine') -> None:
        """
        Initialize the Serendipity Engine.

        Args:
            embeddings (np.ndarray): A numpy array of shape (N, D) where N is the number
                                    of nodes and D is the embedding dimension.
            n_neighbors (int): The k for k-NN density estimation.
            metric (str): The distance metric to use (e.g., 'cosine', 'euclidean').

        Raises:
            ValueError: If embeddings are invalid or n_neighbors is too large.
        """
        self._validate_inputs(embeddings, n_neighbors)
        self.embeddings = embeddings
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.n_samples, self.n_features = embeddings.shape
        
        logger.info(f"Initialized VectorSpaceSerendipity with {self.n_samples} nodes.")
        
        # Pre-compute structural properties
        self.local_densities = self._calculate_local_density()

    def _validate_inputs(self, embeddings: np.ndarray, n_neighbors: int) -> None:
        """Validates the input data."""
        if not isinstance(embeddings, np.ndarray):
            raise TypeError("Embeddings must be a numpy array.")
        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2-dimensional array.")
        if embeddings.shape[0] < 2:
            raise ValueError("Need at least 2 nodes to perform discovery.")
        if n_neighbors >= embeddings.shape[0]:
            raise ValueError("n_neighbors must be less than the number of samples.")
        if np.any(np.isnan(embeddings)):
            raise ValueError("Embeddings contain NaN values.")

    def _calculate_local_density(self) -> np.ndarray:
        """
        Calculate the structural density for each node using k-NN distance.
        
        Higher density implies the node is in a 'crowded' area of the concept space.
        
        Returns:
            np.ndarray: Array of local densities for each node.
        """
        logger.debug("Calculating local densities...")
        try:
            nbrs = NearestNeighbors(n_neighbors=self.n_neighbors, metric=self.metric).fit(self.embeddings)
            distances, _ = nbrs.kneighbors(self.embeddings)
            
            # Density is inverse of average distance to neighbors
            avg_distances = np.mean(distances, axis=1)
            # Avoid division by zero
            avg_distances = np.where(avg_distances == 0, 1e-9, avg_distances)
            densities = 1.0 / avg_distances
            
            # Normalize densities to [0, 1]
            min_d, max_d = np.min(densities), np.max(densities)
            if max_d - min_d > 1e-9:
                normalized_densities = (densities - min_d) / (max_d - min_d)
            else:
                normalized_densities = np.ones_like(densities)
                
            return normalized_densities
        except Exception as e:
            logger.error(f"Error calculating local density: {e}")
            raise

    def _generate_hypothesis_vector(self, vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
        """
        Generates a hypothetical vector representing the bridge between two concepts.
        
        Uses a weighted average based on the midpoint, but could be extended to use
        generative models.
        """
        # Simple interpolation (midpoint)
        return (vec_a + vec_b) / 2.0

    def discover_serendipitous_pairs(
        self, 
        top_k: int = 5, 
        min_distance_threshold: float = 0.5
    ) -> List[SerendipitousPair]:
        """
        Main algorithm: Find pairs of nodes that are distant but structurally similar.
        
        Strategy:
        1. Compute pairwise spatial distances (Sparsity/Difference).
        2. Compare local densities (Structural Similarity).
        3. Score pairs based on (High Distance * Density Similarity).
        
        Args:
            top_k (int): Number of top serendipitous pairs to return.
            min_distance_threshold (float): Minimum normalized distance to consider
                                            nodes as being in different 'domains'.
        
        Returns:
            List[SerendipitousPair]: List of discovered pairs, sorted by serendipity score.
        """
        logger.info("Starting serendipity discovery process...")
        
        # 1. Calculate Distance Matrix
        dist_matrix = pairwise_distances(self.embeddings, metric=self.metric)
        
        # Normalize distances to [0, 1] for scoring consistency
        min_val, max_val = dist_matrix.min(), dist_matrix.max()
        if max_val - min_val > 1e-9:
            norm_dist_matrix = (dist_matrix - min_val) / (max_val - min_val)
        else:
            norm_dist_matrix = np.zeros_like(dist_matrix)

        candidates = []
        
        # 2. Scan for candidates
        # We iterate through the upper triangle of the distance matrix
        for i in range(self.n_samples):
            for j in range(i + 1, self.n_samples):
                dist = norm_dist_matrix[i, j]
                
                # Filter: Must be cross-domain (distant)
                if dist < min_distance_threshold:
                    continue
                
                # Calculate Structural Similarity (based on density difference)
                density_diff = abs(self.local_densities[i] - self.local_densities[j])
                structural_sim = 1.0 - density_diff
                
                # Serendipity Score: High Distance AND High Structural Similarity
                # Formula: Spatial_Distance * Structural_Similarity
                score = dist * structural_sim
                
                if score > 0:
                    pair = SerendipitousPair(
                        source_idx=i,
                        target_idx=j,
                        spatial_distance=dist,
                        structural_similarity=structural_sim,
                        serendipity_score=score
                    )
                    candidates.append(pair)

        if not candidates:
            logger.warning("No serendipitous pairs found with current thresholds.")
            return []

        # 3. Sort and Select Top K
        candidates.sort(key=lambda x: x.serendipity_score, reverse=True)
        top_candidates = candidates[:top_k]
        
        # 4. Generate Hypothesis Vectors for top candidates
        for pair in top_candidates:
            vec_a = self.embeddings[pair.source_idx]
            vec_b = self.embeddings[pair.target_idx]
            pair.hypothesis_vector = self._generate_hypothesis_vector(vec_a, vec_b)
            
            logger.debug(
                f"Found pair: {pair.source_idx}-{pair.target_idx} | "
                f"Score: {pair.serendipity_score:.4f} | "
                f"Dist: {pair.spatial_distance:.2f} | Struct: {pair.structural_similarity:.2f}"
            )
            
        logger.info(f"Discovered {len(top_candidates)} serendipitous pairs.")
        return top_candidates

# --- Usage Example ---
if __name__ == "__main__":
    # Generate synthetic data representing 719 nodes
    # Cluster 1: Biological concepts (Dense)
    # Cluster 2: Computer Science concepts (Dense)
    # Random noise (Sparse)
    np.random.seed(42)
    
    n_nodes = 719
    # Create two distinct clusters to simulate domains
    cluster_1 = np.random.normal(0, 0.5, (n_nodes // 2, 128))
    cluster_2 = np.random.normal(5, 0.5, (n_nodes // 2, 128))
    # Mix them to create some overlap/distance
    embeddings_data = np.vstack([cluster_1, cluster_2])
    
    # Initialize system
    try:
        serendipity_engine = VectorSpaceSerendipity(
            embeddings=embeddings_data, 
            n_neighbors=15, 
            metric='cosine'
        )
        
        # Discover pairs
        # We set min_distance high to ensure we find pairs connecting the two clusters
        results = serendipity_engine.discover_serendipitous_pairs(
            top_k=3, 
            min_distance_threshold=0.8
        )
        
        print("\n--- Discovery Report ---")
        for res in results:
            print(f"Pair: Node {res.source_idx} <--> Node {res.target_idx}")
            print(f"  Serendipity Score: {res.serendipity_score:.4f}")
            print(f"  Spatial Distance:  {res.spatial_distance:.4f} (High = Different Domains)")
            print(f"  Structural Sim:    {res.structural_similarity:.4f} (High = Similar Topology)")
            if res.hypothesis_vector is not None:
                print(f"  Hypothesis Vector Norm: {np.linalg.norm(res.hypothesis_vector):.4f}")
            print("-" * 40)
            
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")