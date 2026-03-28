"""
Module: auto_跨域迁移路径_如何计算两个看似无关的节_52b2b6
Description: 【跨域迁移路径】计算两个看似无关节点间的语义测地线。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """Represents a node in the semantic network."""
    id: str
    vector: np.ndarray
    domain: str
    description: str = ""

class SemanticGeodesicFinder:
    """
    A class to calculate the semantic geodesic (shortest logical path) between 
    two seemingly unrelated concepts (e.g., 'Quantum Mechanics' and 'Supply Chain Management').
    
    This uses a hybrid approach combining vector space proximity (semantic similarity)
    and graph-based logical constraints.
    
    Attributes:
        nodes (Dict[str, Node]): A dictionary mapping node IDs to Node objects.
        adjacency_matrix (np.ndarray): Connectivity matrix for logical edges.
        embedding_dim (int): Dimension of the semantic vectors.
        
    Usage Example:
        >>> finder = SemanticGeodesicFinder(embedding_dim=128)
        >>> finder.add_node("Quantum Mechanics", qm_vector, "Physics")
        >>> finder.add_node("Superposition", sp_vector, "Physics")
        >>> finder.add_node("Inventory Logic", il_vector, "Logistics")
        >>> finder.add_node("Supply Chain", sc_vector, "Management")
        >>> # Define logical edges
        >>> finder.add_edge("Quantum Mechanics", "Superposition")
        >>> path, score = finder.find_path("Quantum Mechanics", "Supply Chain")
    """

    def __init__(self, embedding_dim: int = 768):
        """
        Initialize the SemanticGeodesicFinder.

        Args:
            embedding_dim (int): The dimensionality of the semantic vectors.
        """
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Set[str]] = {}
        self.embedding_dim = embedding_dim
        self._vector_cache: Optional[np.ndarray] = None
        logger.info(f"Initialized SemanticGeodesicFinder with dim={embedding_dim}")

    def add_node(self, node_id: str, vector: np.ndarray, domain: str, desc: str = "") -> None:
        """
        Add a node to the semantic network.

        Args:
            node_id (str): Unique identifier for the node.
            vector (np.ndarray): Semantic vector representation.
            domain (str): The domain the concept belongs to.
            desc (str): Optional description.

        Raises:
            ValueError: If vector dimension mismatches or ID exists.
        """
        if node_id in self.nodes:
            logger.error(f"Node {node_id} already exists.")
            raise ValueError(f"Node {node_id} already exists.")
        
        if vector.shape[0] != self.embedding_dim:
            logger.error(f"Vector dimension mismatch for {node_id}. Expected {self.embedding_dim}, got {vector.shape[0]}")
            raise ValueError("Vector dimension mismatch.")

        self.nodes[node_id] = Node(id=node_id, vector=vector, domain=domain, description=desc)
        self.edges[node_id] = set()
        self._vector_cache = None # Invalidate cache
        logger.debug(f"Added node: {node_id} in domain {domain}")

    def add_edge(self, u_id: str, v_id: str) -> None:
        """
        Add a logical edge between two nodes.

        Args:
            u_id (str): Source node ID.
            v_id (str): Target node ID.
        """
        self._validate_node_exists(u_id)
        self._validate_node_exists(v_id)
        self.edges[u_id].add(v_id)
        self.edges[v_id].add(u_id)
        logger.debug(f"Added edge: {u_id} <-> {v_id}")

    def _validate_node_exists(self, node_id: str) -> None:
        """Helper to check if a node exists."""
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found.")
            raise KeyError(f"Node {node_id} not found.")

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def _calculate_geodesic_step(
        self, 
        current_id: str, 
        target_vector: np.ndarray, 
        visited: Set[str], 
        depth: int,
        max_depth: int = 5
    ) -> Tuple[str, float]:
        """
        [Core Logic 1] Calculate the best next step based on a hybrid score.
        Hybrid Score = Alpha * Vector_Similarity + Beta * Logical_Centrality
        
        This is a greedy approach with depth limits to find the local best transition.
        """
        if depth > max_depth:
            return ("STOP", -1.0)

        best_next = None
        best_score = -1.0
        
        current_node = self.nodes[current_id]
        candidates = self.edges.get(current_id, set())
        
        # If no direct logical edges, search globally (slower, cross-domain jump)
        if not candidates:
            candidates = set(self.nodes.keys()) - visited
            # Limit global search for performance
            candidates = set(list(candidates)[:20]) 

        for neighbor_id in candidates:
            if neighbor_id in visited:
                continue
                
            neighbor = self.nodes[neighbor_id]
            similarity = self._cosine_similarity(neighbor.vector, target_vector)
            
            # Penalize jumps within the same domain to encourage exploration (Cross-Domain logic)
            domain_penalty = 0.0
            if neighbor.domain == current_node.domain:
                domain_penalty = 0.1 # Small penalty
            
            # Heuristic: Prefer nodes that act as bridges
            connectivity_bonus = len(self.edges[neighbor_id]) / 100.0
            
            score = similarity + connectivity_bonus - domain_penalty
            
            if score > best_score:
                best_score = score
                best_next = neighbor_id
                
        if best_next is None:
            return ("STOP", 0.0)
            
        return (best_next, best_score)

    def find_path(
        self, 
        start_id: str, 
        end_id: str, 
        max_steps: int = 10
    ) -> Tuple[List[str], float]:
        """
        [Core Logic 2] Find the semantic geodesic path from start to end.
        
        This method attempts to construct a path by iteratively moving towards 
        the semantic target while respecting logical edges.
        
        Args:
            start_id (str): Starting concept ID.
            end_id (str): Target concept ID.
            max_steps (int): Maximum path length to prevent infinite loops.
            
        Returns:
            Tuple[List[str], float]: (The path of node IDs, Total path confidence score)
            
        Raises:
            ValueError: If start or end nodes do not exist.
        """
        self._validate_node_exists(start_id)
        self._validate_node_exists(end_id)
        
        logger.info(f"Calculating geodesic from '{start_id}' to '{end_id}'...")
        
        path = [start_id]
        visited = {start_id}
        current_id = start_id
        target_vector = self.nodes[end_id].vector
        total_score = 1.0
        
        for _ in range(max_steps):
            if current_id == end_id:
                logger.info("Target reached!")
                break
                
            next_id, step_score = self._calculate_geodesic_step(
                current_id, target_vector, visited, depth=0
            )
            
            if next_id == "STOP" or next_id is None:
                logger.warning("Path exploration stopped: No valid next step found.")
                break
            
            path.append(next_id)
            visited.add(next_id)
            current_id = next_id
            total_score *= step_score # Accumulate probability/score
            
        else:
            logger.warning("Max steps reached without finding target.")
            
        return path, total_score

    def explain_path(self, path: List[str]) -> str:
        """
        [Auxiliary Function] Generate a human-readable explanation of the path.
        """
        if not path:
            return "Empty path."
        
        explanation = []
        for i in range(len(path) - 1):
            curr = self.nodes[path[i]]
            nxt = self.nodes[path[i+1]]
            explanation.append(
                f"{i+1}. [{curr.domain}] {curr.id} -> [{nxt.domain}] {nxt.id} "
                f"(Semantic shift: {self._cosine_similarity(curr.vector, nxt.vector):.4f})"
            )
        return "\n".join(explanation)

# ==========================================
# Usage Example / Test Block
# ==========================================

if __name__ == "__main__":
    # 1. Setup
    DIM = 64
    finder = SemanticGeodesicFinder(embedding_dim=DIM)
    
    # 2. Mock Data Generation
    # Helper to create random vectors
    def get_vec():
        return np.random.rand(DIM)

    # Add Nodes
    # Domain: Physics
    finder.add_node("Quantum Mechanics", get_vec(), "Physics")
    finder.add_node("Superposition", get_vec(), "Physics")
    
    # Domain: Math/Logic
    finder.add_node("Probability Theory", get_vec(), "Math")
    finder.add_node("Stochastic Processes", get_vec(), "Math")
    
    # Domain: Logistics
    finder.add_node("Inventory Forecasting", get_vec(), "Logistics")
    finder.add_node("Supply Chain Management", get_vec(), "Logistics")

    # 3. Define Logical Edges (Knowledge Graph)
    finder.add_edge("Quantum Mechanics", "Superposition")
    finder.add_edge("Superposition", "Probability Theory")
    finder.add_edge("Probability Theory", "Stochastic Processes")
    finder.add_edge("Stochastic Processes", "Inventory Forecasting")
    finder.add_edge("Inventory Forecasting", "Supply Chain Management")

    # 4. Calculate Path
    try:
        start_node = "Quantum Mechanics"
        end_node = "Supply Chain Management"
        
        path, score = finder.find_path(start_node, end_node)
        
        print(f"\nPath found ({start_node} -> {end_node}):")
        print(f"Path: {' -> '.join(path)}")
        print(f"Confidence Score: {score:.4f}")
        print("\nDetailed Explanation:")
        print(finder.explain_path(path))
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")