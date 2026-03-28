"""
Module: auto_自下而上归纳_动态概念漂移检测与节点分_bcb6b7

Description:
    This module implements a Bottom-Up Inductive mechanism for Dynamic Concept Drift
    Detection and Node Splitting. It is designed for AGI systems to maintain an
    adaptive knowledge graph (ontology).
    
    As new practice data (vectors) flows into the system, existing concept nodes
    (e.g., 'Marketing') might become ambiguous (high internal variance). This module
    monitors the entropy (variance) of nodes and triggers an automatic splitting
    mechanism (e.g., splitting 'StreetMarketing' into 'CommunityGroupBuying' and
    'NightMarketRetail') to prevent cognitive rigidity.

    Algorithm:
        1. Inject new embeddings into existing nodes.
        2. Calculate the intra-class variance (drift score) for each node.
        3. If variance exceeds a dynamic threshold, perform K-Means clustering.
        4. If clusters are distinct, split the parent node into child nodes.

Author: Senior Python Engineer (AGI System Core)
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_distances
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """
    Represents a node in the AGI knowledge graph.
    
    Attributes:
        node_id: Unique identifier for the node.
        label: Semantic label of the concept (e.g., 'Marketing').
        vectors: List of embedding vectors associated with this concept.
        parent_id: ID of the parent node (None for root).
        variance_threshold: Dynamic threshold for triggering a split.
    """
    node_id: str
    label: str
    vectors: List[np.ndarray] = field(default_factory=list)
    parent_id: Optional[str] = None
    variance_threshold: float = 0.5
    
    @property
    def vector_matrix(self) -> np.ndarray:
        """Returns the stacked matrix of vectors."""
        if not self.vectors:
            return np.array([])
        return np.vstack(self.vectors)

    def add_vector(self, vector: np.ndarray) -> None:
        """Adds a new vector instance to the node."""
        self.vectors.append(vector)


def _calculate_weighted_variance(matrix: np.ndarray) -> float:
    """
    [Helper] Calculates the intra-cluster variance (drift indicator).
    
    Uses the average squared L2 norm distance from the centroid as a proxy for
    concept ambiguity (entropy).
    
    Args:
        matrix: np.ndarray of shape (N, D) where N is sample count, D is dimension.
        
    Returns:
        float: The calculated variance score. Returns 0.0 if empty or single sample.
    """
    if matrix.shape[0] < 2:
        return 0.0
    
    centroid = np.mean(matrix, axis=0)
    # Calculate squared Euclidean distance
    distances = np.sum((matrix - centroid) ** 2, axis=1)
    variance = np.mean(distances)
    
    return float(variance)


def detect_concept_drift(
    node: ConceptNode, 
    new_data: List[np.ndarray]
) -> Tuple[bool, float, str]:
    """
    [Core Function 1] Analyzes a node to detect if concept drift has occurred
    due to new data injection.
    
    It calculates the variance before and after adding new data. If the variance
    exceeds the node's threshold, it flags the node for splitting.
    
    Args:
        node: The ConceptNode to analyze.
        new_data: List of new embedding vectors to simulate injection.
        
    Returns:
        Tuple[bool, float, str]: 
            - needs_split (bool): True if drift exceeds threshold.
            - current_variance (float): The new calculated variance.
            - message (str): Diagnostic message.
            
    Raises:
        ValueError: If vector dimensions do not match.
    """
    if not new_data:
        return False, 0.0, "No new data provided."
    
    # Data Validation: Check dimensions
    dim_ref = len(node.vectors[0]) if node.vectors else len(new_data[0])
    for vec in new_data:
        if len(vec) != dim_ref:
            msg = f"Dimension mismatch: Node expects {dim_ref}, got {len(vec)}"
            logger.error(msg)
            raise ValueError(msg)
            
    # Simulate merged data
    temp_matrix = np.vstack([node.vector_matrix, np.vstack(new_data)])
    
    # Calculate Entropy/Variance
    variance = _calculate_weighted_variance(temp_matrix)
    
    # Boundary Check
    if variance < 0:
        logger.warning(f"Negative variance detected for node {node.node_id}, math error.")
        variance = 0.0

    needs_split = variance > node.variance_threshold
    
    if needs_split:
        msg = (f"Drift Detected in '{node.label}'! Variance {variance:.4f} > "
               f"Threshold {node.variance_threshold:.4f}")
        logger.info(msg)
        return True, variance, msg
    
    msg = f"Node '{node.label}' stable. Variance: {variance:.4f}"
    logger.debug(msg)
    return False, variance, msg


def perform_node_split(
    node: ConceptNode, 
    n_clusters: int = 2
) -> Dict[str, Any]:
    """
    [Core Function 2] Executes the splitting process using K-Means clustering.
    
    When a node is identified as "drifted", this function clusters the vectors
    to find new sub-concepts.
    
    Args:
        node: The ConceptNode to split.
        n_clusters: The number of potential child nodes to generate (default 2).
        
    Returns:
        Dict containing split metadata:
        - 'success': bool
        - 'child_nodes': List[Dict] with 'label' and 'centroid' if successful.
        - 'inertia': float (clustering inertia)
        
    Note:
        In a real AGI system, this would update the graph database. Here we return
        the structural changes.
    """
    data = node.vector_matrix
    if data.shape[0] < n_clusters:
        msg = f"Insufficient samples ({data.shape[0]}) for {n_clusters} clusters."
        logger.warning(msg)
        return {"success": False, "reason": msg}

    logger.info(f"Initiating split for node '{node.label}' into {n_clusters} sub-concepts.")
    
    try:
        # Dynamic Clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        kmeans.fit(data)
        
        clusters = kmeans.cluster_centers_
        labels = kmeans.labels_
        
        # Generate new child node data
        # In reality, an LLM would generate names based on centroids or samples.
        # Here we simulate naming.
        child_nodes = []
        for i in range(n_clusters):
            # Extract indices for this cluster
            indices = np.where(labels == i)[0]
            
            # Simulation of Semantic Naming
            new_label = f"{node.label}_SubConcept_{i+1}"
            
            child_nodes.append({
                "proposed_label": new_label,
                "centroid": clusters[i],
                "sample_count": len(indices)
            })
            
        logger.info(f"Split successful. Created proposals: {[c['proposed_label'] for c in child_nodes]}")
        
        return {
            "success": True,
            "parent_id": node.node_id,
            "child_nodes": child_nodes,
            "inertia": kmeans.inertia_
        }
        
    except Exception as e:
        logger.error(f"Clustering failed for node {node.node_id}: {str(e)}")
        return {"success": False, "reason": str(e)}


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Setup: Create a simulated node 'Marketing'
    # Vector dimension 128
    dim = 128
    # Initial data: Tight cluster around 0.1
    initial_vecs = [np.random.normal(0.1, 0.05, dim) for _ in range(50)]
    
    marketing_node = ConceptNode(
        node_id="node_001",
        label="General_Marketing",
        vectors=initial_vecs,
        variance_threshold=2.0  # Tuned threshold
    )
    
    print(f"--- Initial State: {marketing_node.label} ---")
    
    # 2. Simulate Concept Drift: Inject noisy data (Diverging concepts)
    # Group A: 'Community Buying' (center 0.8)
    # Group B: 'Night Market' (center -0.8)
    drift_data = []
    drift_data.extend([np.random.normal(0.8, 0.1, dim) for _ in range(20)]) # New Concept 1
    drift_data.extend([np.random.normal(-0.8, 0.1, dim) for _ in range(20)]) # New Concept 2
    
    print("\n--- Detecting Drift ---")
    is_drifted, var, msg = detect_concept_drift(marketing_node, drift_data)
    print(msg)
    
    # 3. Handle Drift: Split the node if drift detected
    if is_drifted:
        print("\n--- Performing Node Split ---")
        # First merge the data physically for the split calculation
        for v in drift_data:
            marketing_node.add_vector(v)
            
        result = perform_node_split(marketing_node, n_clusters=2)
        
        if result["success"]:
            print("Split Result:")
            for child in result["child_nodes"]:
                print(f" - New Concept: {child['proposed_label']}, Samples: {child['sample_count']}")
        else:
            print("Split failed:", result.get("reason"))