"""
Module: dynamic_semantic_topology.py

Description:
    Implements a dynamic semantic topology system for AGI contexts. It enables real-time
    identification and reconfiguration of the K-nearest neighbors based on high-dimensional
    feature vectors, simulating a 'cognitive gravity' effect akin to human associative memory.

Key Features:
    - Real-time cosine similarity calculation.
    - Dynamic graph topology updates using K-Nearest Neighbors (KNN).
    - In-memory storage optimized for vector operations using NumPy.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DynamicSemanticTopology:
    """
    A system to build and maintain a dynamic semantic graph based on vector embeddings.
    
    This class manages a set of nodes, calculates 'cognitive gravity' (semantic similarity),
    and reconstructs local topologies when new information is introduced.
    
    Attributes:
        dimension (int): The dimensionality of the feature vectors.
        nodes (Dict[str, np.ndarray]): A mapping from node ID to feature vector.
        adjacency (Dict[str, Set[str]]): An adjacency list representing the graph topology.
        k_neighbors (int): The number of neighbors to maintain for each node.
    """

    def __init__(self, dimension: int, k_neighbors: int = 5) -> None:
        """
        Initialize the topology graph.

        Args:
            dimension (int): The size of the feature vectors (must be > 0).
            k_neighbors (int): The number of nearest neighbors to connect (default 5).
        
        Raises:
            ValueError: If dimension or k_neighbors is invalid.
        """
        if dimension <= 0:
            logger.error("Invalid dimension provided: %d", dimension)
            raise ValueError("Dimension must be a positive integer.")
        if k_neighbors <= 0:
            logger.error("Invalid k_neighbors provided: %d", k_neighbors)
            raise ValueError("k_neighbors must be a positive integer.")

        self.dimension = dimension
        self.k_neighbors = k_neighbors
        self.nodes: Dict[str, np.ndarray] = {}
        self.adjacency: Dict[str, Set[str]] = {}
        
        logger.info(
            f"Initialized DynamicSemanticTopology with dimension={dimension}, k={k_neighbors}"
        )

    def _validate_vector(self, vector: np.ndarray) -> None:
        """
        Validate that a vector conforms to the required dimensionality and type.

        Args:
            vector (np.ndarray): The vector to validate.

        Raises:
            TypeError: If input is not a numpy array.
            ValueError: If vector dimensions do not match the model.
        """
        if not isinstance(vector, np.ndarray):
            raise TypeError("Input must be a numpy array.")
        if vector.shape != (self.dimension,):
            raise ValueError(
                f"Vector dimension mismatch. Expected ({self.dimension},), got {vector.shape}"
            )

    def calculate_cognitive_gravity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Calculate the 'cognitive gravity' between two vectors using Cosine Similarity.
        
        Cosine similarity measures the cosine of the angle between two vectors. 
        A value of 1 means identical semantic direction, 0 means orthogonal.

        Args:
            vec_a (np.ndarray): First vector.
            vec_b (np.ndarray): Second vector.

        Returns:
            float: Similarity score between -1 and 1.
        """
        # Norm calculation is robust against division by zero
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        similarity = np.dot(vec_a, vec_b) / (norm_a * norm_b)
        return float(similarity)

    def add_node(self, node_id: str, vector: np.ndarray, auto_restructure: bool = True) -> bool:
        """
        Add a new node to the topology and optionally restructure the graph.

        Args:
            node_id (str): Unique identifier for the node.
            vector (np.ndarray): The high-dimensional feature vector.
            auto_restructure (bool): Whether to immediately update topology links.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self._validate_vector(vector)
            
            if node_id in self.nodes:
                logger.warning(f"Node {node_id} already exists. Overwriting data.")

            self.nodes[node_id] = vector
            self.adjacency[node_id] = set() # Initialize empty connections
            
            logger.info(f"Node {node_id} added to the system.")

            if auto_restructure and len(self.nodes) > 1:
                self.restructure_topology(node_id)
            
            return True

        except (TypeError, ValueError) as e:
            logger.error(f"Failed to add node {node_id}: {str(e)}")
            return False

    def restructure_topology(self, target_node_id: str) -> None:
        """
        Reconstruct the semantic connections for a specific node based on KNN.
        
        This function finds the K nearest neighbors based on semantic similarity
        and updates the adjacency lists to form a dynamic cluster.

        Args:
            target_node_id (str): The node ID to center the restructuring around.
        """
        if target_node_id not in self.nodes:
            logger.error(f"Node {target_node_id} not found for restructuring.")
            return

        target_vec = self.nodes[target_node_id]
        similarities: List[Tuple[float, str]] = []

        # Calculate distance to all other nodes (Cognitive Gravity)
        for nid, vec in self.nodes.items():
            if nid == target_node_id:
                continue
            
            score = self.calculate_cognitive_gravity(target_vec, vec)
            similarities.append((score, nid))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[0], reverse=True)

        # Select top K neighbors
        top_k_neighbors = [nid for _, nid in similarities[:self.k_neighbors]]
        
        # Update Adjacency List (Undirected graph for semantic association)
        # Clear old connections for target
        old_neighbors = self.adjacency.get(target_node_id, set())
        
        # Remove reciprocal links from old neighbors
        for old_n in old_neighbors:
            if old_n in self.adjacency:
                self.adjacency[old_n].discard(target_node_id)

        # Create new links
        new_neighbors = set(top_k_neighbors)
        self.adjacency[target_node_id] = new_neighbors

        # Add reciprocal links
        for neighbor in new_neighbors:
            self.adjacency[neighbor].add(target_node_id)

        logger.info(
            f"Restructured topology for {target_node_id}. "
            f"New connections: {len(new_neighbors)}"
        )

    def get_neighbors(self, node_id: str) -> Optional[Set[str]]:
        """
        Retrieve the current semantic neighbors for a given node.

        Args:
            node_id (str): The ID of the node.

        Returns:
            Optional[Set[str]]: A set of neighbor node IDs or None if node not found.
        """
        return self.adjacency.get(node_id)

# --- Usage Example ---
if __name__ == "__main__":
    # Configuration
    DIM = 128  # Example dimension for feature vectors
    INITIAL_NODE_COUNT = 1622 # Simulating the existing scale mentioned in requirements
    
    # 1. Initialize System
    topology_system = DynamicSemanticTopology(dimension=DIM, k_neighbors=5)
    
    # 2. Bulk load initial data (Simulation)
    print(f"Loading initial {INITIAL_NODE_COUNT} nodes...")
    for i in range(INITIAL_NODE_COUNT):
        # Generate random normalized vector for simulation
        vec = np.random.randn(DIM)
        vec = vec / np.linalg.norm(vec)
        topology_system.add_node(f"node_{i}", vec, auto_restructure=False)
    
    # 3. Initial Topology Build (Batch processing usually done offline, simplified here)
    # In a real system, this would use KD-Tree or BallTree for efficiency.
    # Here we iterate to demonstrate the logic.
    print("Building initial topology...")
    for i in range(INITIAL_NODE_COUNT):
        if i % 500 == 0:
            topology_system.restructure_topology(f"node_{i}")
            
    # 4. Dynamic Update Scenario: Add a new node (The core requirement)
    print("\nAdding new dynamic node 'new_concept_alpha'...")
    
    # Create a vector slightly similar to node_0 to test clustering
    new_vector = topology_system.nodes["node_0"] * 0.9 + np.random.randn(DIM) * 0.1
    
    success = topology_system.add_node("new_concept_alpha", new_vector)
    
    if success:
        neighbors = topology_system.get_neighbors("new_concept_alpha")
        print(f"New node 'new_concept_alpha' automatically connected to: {neighbors}")
        
        # Verify cognitive gravity
        if "node_0" in neighbors:
            print("Success: System correctly identified semantic similarity to 'node_0'.")