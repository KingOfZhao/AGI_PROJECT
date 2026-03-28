"""
Module: auto_semantic_boundary_detection_3daaea3
Description: 【语义向量空间的重叠边界探测】
Author: Senior Python Engineer (AGI System)
Version: 1.0.0

This module implements algorithms to quantify relationships between domain clusters
in a high-dimensional semantic vector space. It calculates a 'Semantic Osmotic Pressure'
to detect potential cross-domain knowledge migration opportunities.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SemanticNode:
    """Data class representing a node in the semantic space."""
    node_id: str
    domain: str
    vector: np.ndarray
    
    def __post_init__(self):
        if not isinstance(self.vector, np.ndarray):
            raise TypeError("Vector must be a numpy array.")
        if self.vector.ndim != 1:
            raise ValueError("Vector must be a 1-dimensional array.")

@dataclass
class DomainCluster:
    """Represents a collection of nodes belonging to a specific domain."""
    domain_name: str
    nodes: List[SemanticNode] = field(default_factory=list)
    centroid: Optional[np.ndarray] = field(default=None, init=False)
    covariance: Optional[np.ndarray] = field(default=None, init=False)

    def add_node(self, node: SemanticNode):
        if node.domain != self.domain_name:
            raise ValueError(f"Node domain {node.domain} does not match cluster {self.domain_name}")
        self.nodes.append(node)
    
    def compute_statistics(self):
        """Calculates geometric properties of the cluster."""
        if not self.nodes:
            raise ValueError(f"Cluster {self.domain_name} is empty.")
        
        vectors = np.array([n.vector for n in self.nodes])
        self.centroid = np.mean(vectors, axis=0)
        
        # Calculate covariance matrix for shape analysis
        # Regularization added for numerical stability with low sample counts
        if vectors.shape[0] > 1:
            self.covariance = np.cov(vectors, rowvar=False) + np.eye(vectors.shape[1]) * 1e-6
        else:
            # Fallback for single-node clusters
            self.covariance = np.eye(vectors.shape[1]) * 1e-6
        
        logger.debug(f"Cluster '{self.domain_name}' stats computed. Centroid norm: {np.linalg.norm(self.centroid):.4f}")

class SemanticSpaceAnalyzer:
    """
    Analyzes the semantic vector space to detect overlapping boundaries 
    and calculate semantic osmotic pressure between domains.
    """

    def __init__(self, embedding_dim: int = 768, pressure_threshold: float = 0.6):
        """
        Initialize the analyzer.

        Args:
            embedding_dim (int): Dimensionality of the semantic vectors.
            pressure_threshold (float): Threshold above which domains are considered 
                                        to have significant semantic interaction.
        """
        self.embedding_dim = embedding_dim
        self.pressure_threshold = pressure_threshold
        self.clusters: Dict[str, DomainCluster] = {}
        logger.info(f"SemanticSpaceAnalyzer initialized with dim={embedding_dim}, threshold={pressure_threshold}")

    def load_nodes(self, nodes: List[Dict[str, Union[str, np.ndarray]]]) -> None:
        """
        Load and validate nodes into the analyzer.

        Args:
            nodes: List of dictionaries containing 'id', 'domain', and 'vector'.
        
        Raises:
            ValueError: If input data is malformed.
        """
        logger.info(f"Loading {len(nodes)} nodes...")
        for i, node_data in enumerate(nodes):
            try:
                node = SemanticNode(
                    node_id=node_data['id'],
                    domain=node_data['domain'],
                    vector=node_data['vector']
                )
                
                if node.vector.shape[0] != self.embedding_dim:
                    raise ValueError(f"Vector dimension mismatch for node {node.node_id}")

                if node.domain not in self.clusters:
                    self.clusters[node.domain] = DomainCluster(domain_name=node.domain)
                
                self.clusters[node.domain].add_node(node)

            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Skipping invalid node at index {i}: {e}")
                continue
        
        # Compute stats for all loaded clusters
        for cluster in self.clusters.values():
            try:
                cluster.compute_statistics()
            except ValueError as e:
                logger.warning(f"Could not compute stats for domain {cluster.domain_name}: {e}")

    def _calculate_boundary_proximity(self, cluster_a: DomainCluster, cluster_b: DomainCluster) -> float:
        """
        Helper function to calculate the geometric proximity between two cluster centroids.
        Returns a normalized score [0, 1] based on cosine similarity.
        """
        if cluster_a.centroid is None or cluster_b.centroid is None:
            return 0.0
        
        # Reshape for sklearn
        vec_a = cluster_a.centroid.reshape(1, -1)
        vec_b = cluster_b.centroid.reshape(1, -1)
        
        similarity = cosine_similarity(vec_a, vec_b)[0][0]
        # Normalize from [-1, 1] to [0, 1] for easier pressure calculation
        normalized_score = (similarity + 1) / 2
        return normalized_score

    def calculate_semantic_osmotic_pressure(self, domain_a: str, domain_b: str) -> Tuple[float, Dict]:
        """
        Core Algorithm: Calculates 'Semantic Osmotic Pressure' between two domains.
        
        This metric combines geometric proximity (centroid distance) with structural 
        compatibility (covariance alignment) to determine if concepts can easily 
        'flow' from one domain to another.

        Args:
            domain_a (str): Name of the first domain.
            domain_b (str): Name of the second domain.

        Returns:
            Tuple[float, Dict]: Pressure score and detailed metrics.
        """
        if domain_a not in self.clusters or domain_b not in self.clusters:
            logger.error(f"One or both domains not found: {domain_a}, {domain_b}")
            raise ValueError("Domain not found in loaded data.")

        c_a = self.clusters[domain_a]
        c_b = self.clusters[domain_b]

        # 1. Geometric Proximity (Centroid Similarity)
        proximity = self._calculate_boundary_proximity(c_a, c_b)

        # 2. Structural Overlap (Mahalanobis-like boundary check)
        # We check how much the centroid of A falls within the distribution of B
        # Using a simplified variance-weighted distance
        try:
            diff_vector = c_a.centroid - c_b.centroid
            # Calculate normalized variance product overlap
            var_a = np.diag(c_a.covariance)
            var_b = np.diag(c_b.covariance)
            
            # Intersection over Union of variance ranges (simplified heuristic)
            # High score implies shapes overlap significantly in high-dimensional space
            variance_overlap_score = np.mean(2 * np.minimum(var_a, var_b) / (var_a + var_b + 1e-9))
        except Exception as e:
            logger.warning(f"Error calculating structural overlap: {e}")
            variance_overlap_score = 0.0

        # 3. Calculate Final Pressure
        # Weighted combination: Proximity is primary, variance alignment is secondary
        pressure_score = (proximity * 0.7) + (variance_overlap_score * 0.3)
        
        metrics = {
            'centroid_proximity': float(proximity),
            'variance_overlap': float(variance_overlap_score),
            'raw_pressure': float(pressure_score)
        }

        return pressure_score, metrics

    def detect_migration_candidates(self) -> List[Dict]:
        """
        Scans all domain pairs to find those exceeding the semantic pressure threshold.
        
        Returns:
            List of dictionaries containing potential cross-domain mappings.
        """
        candidates = []
        domain_names = list(self.clusters.keys())
        n_domains = len(domain_names)
        
        logger.info(f"Scanning {n_domains} domains for migration candidates...")

        for i in range(n_domains):
            for j in range(i + 1, n_domains):
                d_a = domain_names[i]
                d_b = domain_names[j]
                
                try:
                    pressure, metrics = self.calculate_semantic_osmotic_pressure(d_a, d_b)
                    
                    if pressure > self.pressure_threshold:
                        candidate = {
                            'source_domain': d_a,
                            'target_domain': d_b,
                            'semantic_osmotic_pressure': pressure,
                            'details': metrics,
                            'suggestion': f"High potential for concept migration between '{d_a}' and '{d_b}'"
                        }
                        candidates.append(candidate)
                        logger.info(f"Candidate found: {d_a} <-> {d_b} (Pressure: {pressure:.4f})")
                
                except Exception as e:
                    logger.error(f"Error processing pair ({d_a}, {d_b}): {e}")
                    continue

        # Sort by pressure score descending
        candidates.sort(key=lambda x: x['semantic_osmotic_pressure'], reverse=True)
        return candidates

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate Mock Data
    # Simulating 3 domains: 'Biology', 'Computer Science', 'Cooking'
    # Biology and CS are closer in semantic space (conceptually) than Cooking
    
    def generate_cluster_data(domain_name, center, n_samples, dim=768):
        data = []
        # Add some noise to the center
        cov = np.eye(dim) * 0.1
        vectors = np.random.multivariate_normal(center, cov, n_samples)
        for i, vec in enumerate(vectors):
            data.append({
                'id': f"{domain_name}_{i}",
                'domain': domain_name,
                'vector': vec
            })
        return data

    # Create distinct centroids
    dim = 128 # Using lower dim for mock example speed
    bio_center = np.random.rand(dim) * 0.5
    cs_center = bio_center + (np.random.rand(dim) * 0.1) # CS is close to Biology
    cook_center = np.random.rand(dim) * 5.0 # Cooking is far away

    nodes_bio = generate_cluster_data("Bio_Evolution", bio_center, 50, dim)
    nodes_cs = generate_cluster_data("CS_Algorithms", cs_center, 50, dim)
    nodes_cook = generate_cluster_data("Cooking_Recipes", cook_center, 20, dim)
    
    all_nodes = nodes_bio + nodes_cs + nodes_cook

    # 2. Initialize Analyzer
    analyzer = SemanticSpaceAnalyzer(embedding_dim=dim, pressure_threshold=0.5)

    # 3. Load Data
    analyzer.load_nodes(all_nodes)

    # 4. Detect Candidates
    print("\n--- Scanning for Semantic Overlaps ---")
    results = analyzer.detect_migration_candidates()

    print(f"\nFound {len(results)} high-potential cross-domain links:")
    for res in results:
        print(f"Source: {res['source_domain']}")
        print(f"Target: {res['target_domain']}")
        print(f"Pressure: {res['semantic_osmotic_pressure']:.4f}")
        print(f"Suggestion: {res['suggestion']}")
        print("-" * 30)