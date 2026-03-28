"""
Module: cognitive_entropy_router.py

This module implements a dynamic routing algorithm based on Cognitive Entropy
to optimize information flow in an AGI knowledge graph.

Design Goal:
To prevent high-value nodes from being submerged by low-value, homogenized information.
It quantifies the 'Structural Distance' of incoming information relative to the
existing topology (specifically checking for redundancy vs. structural holes).

Core Logic:
1. Redundancy Check (Low Priority): If input is highly similar to existing leaf nodes
   and does not create new paths, it is deemed low entropy-reducing.
2. Structural Hole Check (High Priority): If input connects isolated sub-graphs,
   it is deemed high entropy-reducing (increasing system complexity/order).

Dependencies:
    - networkx: For graph structure manipulation.
    - numpy: For vector operations and mathematical calculations.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents a node in the AGI knowledge graph.
    
    Attributes:
        id: Unique identifier.
        vector: High-dimensional embedding representing the semantic content.
        connections: List of connected node IDs (optional, used for construction).
    """
    id: str
    vector: List[float]
    connections: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.vector, np.ndarray):
            self.vector = np.array(self.vector, dtype=np.float32)


@dataclass
class RoutingDecision:
    """
    Contains the result of the routing algorithm.
    
    Attributes:
        accept: Whether to accept the node into the core graph.
        priority: Calculated priority score (0.0 to 1.0).
        reason: Explanation for the decision.
        entropy_delta: The calculated change in system entropy.
    """
    accept: bool
    priority: float
    reason: str
    entropy_delta: float


class CognitiveEntropyRouter:
    """
    Manages the dynamic routing of information based on cognitive entropy principles.
    """

    def __init__(self, similarity_threshold: float = 0.85, alpha: float = 0.7):
        """
        Initialize the router.
        
        Args:
            similarity_threshold: Threshold above which nodes are considered semantically redundant.
            alpha: Weighting factor for balancing redundancy vs. structural value.
        """
        self.graph = nx.Graph()
        self.node_vectors: Dict[str, np.ndarray] = {}
        self.similarity_threshold = similarity_threshold
        self.alpha = alpha
        logger.info("CognitiveEntropyRouter initialized with threshold %.2f", similarity_threshold)

    def add_existing_nodes(self, nodes: List[KnowledgeNode]) -> None:
        """
        Load initial knowledge graph topology.
        
        Args:
            nodes: List of pre-existing KnowledgeNodes.
        """
        for node in nodes:
            self.graph.add_node(node.id)
            self.node_vectors[node.id] = node.vector
            for neighbor in node.connections:
                # Temporarily add edges; in production this would be more complex
                self.graph.add_edge(node.id, neighbor)
        logger.info("Loaded %d nodes into the graph.", len(nodes))

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """
        Helper function to calculate cosine similarity between two vectors.
        
        Returns:
            float: Similarity score between -1 and 1.
        """
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def _calculate_structural_distance(self, node_id: str, potential_neighbors: Set[str]) -> float:
        """
        Quantifies how 'distant' a new node is structurally.
        If it connects nodes that are currently far apart (different communities),
        the distance is high (indicating a Structural Hole bridge).
        
        Args:
            node_id: ID of the candidate node (for logging).
            potential_neighbors: IDs of nodes the new node connects to.
            
        Returns:
            float: A score representing structural value (0.0 to 1.0).
        """
        if not potential_neighbors or len(potential_neighbors) < 2:
            return 0.0

        # Check if potential neighbors belong to the same connected component
        # If they are in different components, this node creates a 'bridge' (Structural Hole)
        components = list(nx.connected_components(self.graph))
        
        connected_component_indices = set()
        
        for neighbor in potential_neighbors:
            if neighbor in self.graph:
                for i, comp in enumerate(components):
                    if neighbor in comp:
                        connected_component_indices.add(i)
                        break
        
        # The more distinct components are connected, the higher the structural value
        num_bridged_components = len(connected_component_indices)
        
        # Normalize: Bridging 2 components is significant, >5 is very high
        max_expected_bridges = 5.0
        structural_score = min(1.0, num_bridged_components / max_expected_bridges)
        
        return structural_score

    def evaluate_information(self, candidate: KnowledgeNode) -> RoutingDecision:
        """
        Core Function: Evaluates new information to determine routing priority.
        
        Algorithm:
        1. Semantic Redundancy Check: Calculate similarity with existing leaf nodes.
        2. Structural Hole Detection: Analyze connection topology.
        3. Entropy Calculation: Combine metrics to determine 'Cognitive Entropy'.
        
        Args:
            candidate: The new KnowledgeNode to evaluate.
            
        Returns:
            RoutingDecision object containing priority and metadata.
            
        Raises:
            ValueError: If input vector is empty or invalid.
        """
        # 1. Data Validation
        if candidate.vector is None or len(candidate.vector) == 0:
            logger.error("Candidate node %s has empty vector.", candidate.id)
            raise ValueError("Node vector cannot be empty.")

        logger.debug("Evaluating candidate node: %s", candidate.id)

        # 2. Semantic Redundancy Analysis
        # Find nodes most similar to the candidate
        similarities: List[Tuple[str, float]] = []
        
        # In a real AGI system with 3856+ nodes, we would use a vector DB index here.
        # For this module, we iterate for demonstration.
        for nid, vec in self.node_vectors.items():
            sim = self._cosine_similarity(candidate.vector, vec)
            similarities.append((nid, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Check against threshold
        max_sim = similarities[0][1] if similarities else 0.0
        redundant_factor = 0.0
        
        if max_sim > self.similarity_threshold:
            redundant_factor = max_sim
            logger.warning("High redundancy detected (Sim: %.3f). Potential low-value info.", max_sim)

        # 3. Structural Analysis
        # Check the connectivity of the candidate
        # We assume 'candidate.connections' implies the *intent* to connect to existing nodes
        # or we infer connections based on vector similarity to existing nodes.
        # Here we treat 'candidate.connections' as the explicit proposed edges.
        
        structural_value = self._calculate_structural_distance(
            candidate.id, 
            set(candidate.connections)
        )

        # 4. Calculate Cognitive Entropy Score (Routing Priority)
        # Formula:
        # Priority = (1 - alpha) * (1 - Redundancy) + alpha * (Structural_Value)
        # If Redundancy is high -> Priority drops.
        # If Structural Value is high (bridging holes) -> Priority rises.
        
        semantic_freshness = 1.0 - redundant_factor
        
        priority_score = (1 - self.alpha) * semantic_freshness + self.alpha * structural_value
        
        # 5. Determine Acceptance
        # Thresholds can be tuned
        is_accepted = priority_score > 0.4 
        
        reason = "Standard routing."
        if is_accepted and structural_value > 0.5:
            reason = "High Priority: Bridges structural holes."
        elif is_accepted and semantic_freshness > 0.7:
            reason = "Standard Priority: Novel semantic content."
        elif not is_accepted and redundant_factor > self.similarity_threshold:
            reason = "Low Priority: High semantic redundancy."
        
        entropy_delta = priority_score * (1.0 + structural_value)

        return RoutingDecision(
            accept=is_accepted,
            priority=priority_score,
            reason=reason,
            entropy_delta=entropy_delta
        )

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Mock Data (Simulating 3856 nodes would be heavy, using small subset)
    # Dimensions of semantic vectors
    VECTOR_DIM = 128
    
    # Create existing network
    existing_nodes = []
    
    # Cluster A: Similar vectors
    base_vec_a = np.random.rand(VECTOR_DIM).astype(np.float32)
    for i in range(5):
        noise = np.random.normal(0, 0.01, VECTOR_DIM)
        vec = base_vec_a + noise
        # Normalize
        vec = vec / np.linalg.norm(vec)
        node = KnowledgeNode(id=f"A_{i}", vector=vec, connections=[f"A_{(i+1)%5}"])
        existing_nodes.append(node)
        
    # Cluster B: Isolated cluster
    base_vec_b = np.random.rand(VECTOR_DIM).astype(np.float32)
    for i in range(5):
        noise = np.random.normal(0, 0.01, VECTOR_DIM)
        vec = base_vec_b + noise
        vec = vec / np.linalg.norm(vec)
        # Isolated (no internal connections for simplicity in this demo)
        node = KnowledgeNode(id=f"B_{i}", vector=vec, connections=[])
        existing_nodes.append(node)

    # 2. Initialize Router
    router = CognitiveEntropyRouter(similarity_threshold=0.85, alpha=0.6)
    router.add_existing_nodes(existing_nodes)

    print("\n--- SCENARIO 1: Redundant Information (Noisy Duplicate) ---")
    # Duplicate of A_0
    noise = np.random.normal(0, 0.02, VECTOR_DIM)
    dup_vec = base_vec_a + noise
    dup_vec = dup_vec / np.linalg.norm(dup_vec)
    candidate_dup = KnowledgeNode(id="C_DUP", vector=dup_vec, connections=["A_0"])
    
    decision = router.evaluate_information(candidate_dup)
    print(f"Decision: {decision.reason}")
    print(f"Priority: {decision.priority:.4f}")
    print(f"Accepted: {decision.accept}")

    print("\n--- SCENARIO 2: High Value Node (Bridge) ---")
    # Node that explicitly connects Cluster A and Cluster B
    # Vector is distinct (average of two concepts)
    bridge_vec = (base_vec_a + base_vec_b) / 2.0
    bridge_vec = bridge_vec / np.linalg.norm(bridge_vec)
    # Connecting to one node from A and one from B
    candidate_bridge = KnowledgeNode(id="C_BRIDGE", vector=bridge_vec, connections=["A_0", "B_0"])
    
    decision = router.evaluate_information(candidate_bridge)
    print(f"Decision: {decision.reason}")
    print(f"Priority: {decision.priority:.4f}")
    print(f"Accepted: {decision.accept}")
    
    print("\n--- SCENARIO 3: Novel but Isolated ---")
    # Completely random vector, no connections
    novel_vec = np.random.rand(VECTOR_DIM).astype(np.float32)
    candidate_novel = KnowledgeNode(id="C_NOVEL", vector=novel_vec, connections=[])
    
    decision = router.evaluate_information(candidate_novel)
    print(f"Decision: {decision.reason}")
    print(f"Priority: {decision.priority:.4f}")
    print(f"Accepted: {decision.accept}")