"""
Module: auto_设计_最小认知颗粒度_minimum_ad467d

This module implements the 'Minimum Cognitive Granularity' (MCG) standard for AGI knowledge representation.
It addresses the issue of 'Atomic Noise' caused by over-segmentation of knowledge nodes.

Core Objectives:
1. Detect semantic redundancy in a knowledge graph.
2. Merge nodes that have extremely high semantic similarity and low distinct contextual value.
3. Optimize network topology while preserving critical information density.

Dependencies:
    - networkx: For graph manipulation.
    - numpy: For numerical operations on embeddings.
    - logging: Standard library for tracing.
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MCG_Optimizer")


@dataclass
class KnowledgeNode:
    """
    Represents a node in the semantic network.
    
    Attributes:
        id: Unique identifier.
        content: Text or semantic content.
        embedding: Vector representation of the content.
        context_id: ID of the parent context (to prevent cross-context merging).
        importance: Weight of the node (default 1.0).
    """
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    context_id: str = "default"
    importance: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCGOptimizer:
    """
    Optimizes a knowledge graph by merging semantically similar nodes 
    to achieve Minimum Cognitive Granularity.
    """

    def __init__(self, similarity_threshold: float = 0.95, min_cluster_size: int = 2):
        """
        Initialize the optimizer.

        Args:
            similarity_threshold (float): Cosine similarity threshold for merging (0.0 to 1.0).
            min_cluster_size (int): Minimum number of nodes to form a merge group.
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0.")
        
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.graph = nx.DiGraph()
        self._node_map: Dict[str, KnowledgeNode] = {}
        logger.info(f"MCGOptimizer initialized with threshold={similarity_threshold}")

    def add_nodes(self, nodes: List[KnowledgeNode]) -> None:
        """
        Load nodes into the internal graph structure.
        """
        for node in nodes:
            if not node.embedding:
                logger.warning(f"Node {node.id} missing embedding, skipping.")
                continue
            
            # Normalize embedding for cosine similarity calculation
            norm = np.linalg.norm(node.embedding)
            if norm == 0:
                continue
            node.embedding = node.embedding / norm
            
            self.graph.add_node(node.id, data=node)
            self._node_map[node.id] = node
        logger.info(f"Loaded {len(self._node_map)} nodes into the graph.")

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Helper function to calculate cosine similarity.
        Assumes vectors are already normalized.
        """
        return np.dot(vec_a, vec_b)

    def _check_contextual_distinctiveness(
        self, 
        node_a: KnowledgeNode, 
        node_b: KnowledgeNode, 
        merge_candidates: Set[str]
    ) -> bool:
        """
        Checks if two nodes have distinguishing features in their connections or metadata.
        If nodes share the same context and have no specific distinguishing attributes, 
        they are candidates for noise reduction.
        
        Returns:
            bool: True if they CAN be merged (low distinctiveness), False otherwise.
        """
        # Constraint 1: Do not merge if contexts differ
        if node_a.context_id != node_b.context_id:
            return False
            
        # Constraint 2: Check if relationships are significantly different
        # (Simplified logic: In a full AGI system, this would analyze graph neighbors)
        neighbors_a = set(self.graph.successors(node_a.id))
        neighbors_b = set(self.graph.successors(node_b.id))
        
        # If they point to completely different things, they might be distinct concepts
        # sharing similar wording but different intent.
        intersection = neighbors_a.intersection(neighbors_b)
        if len(intersection) == 0 and (len(neighbors_a) > 0 or len(neighbors_b) > 0):
            # Allow some slack if semantic similarity is extremely high, 
            # but generally keep distinct functional nodes.
            return False
            
        return True

    def detect_atomic_noise(self) -> List[Set[str]]:
        """
        Identifies clusters of nodes that represent 'Atomic Noise'.
        
        Returns:
            List[Set[str]]: A list of sets, where each set contains IDs of nodes to be merged.
        """
        logger.info("Starting atomic noise detection...")
        merge_groups: List[Set[str]] = []
        visited: Set[str] = set()
        node_ids = list(self._node_map.keys())

        for i in range(len(node_ids)):
            node_id_a = node_ids[i]
            if node_id_a in visited:
                continue
                
            current_group: Set[str] = {node_id_a}
            node_a = self._node_map[node_id_a]

            for j in range(i + 1, len(node_ids)):
                node_id_b = node_ids[j]
                if node_id_b in visited:
                    continue
                    
                node_b = self._node_map[node_id_b]
                
                # Calculate Similarity
                similarity = self._cosine_similarity(node_a.embedding, node_b.embedding)
                
                if similarity >= self.similarity_threshold:
                    # Check Contextual Value
                    if self._check_contextual_distinctiveness(node_a, node_b, current_group):
                        current_group.add(node_id_b)

            # Only register groups that actually need merging
            if len(current_group) >= self.min_cluster_size:
                merge_groups.append(current_group)
                visited.update(current_group)
        
        logger.info(f"Detected {len(merge_groups)} noise clusters.")
        return merge_groups

    def optimize_topology(self) -> nx.DiGraph:
        """
        Executes the merging process to clean up the network topology.
        Creates a new 'Meta-Node' for each cluster of noisy nodes.
        
        Returns:
            nx.DiGraph: The optimized graph.
        """
        clusters = self.detect_atomic_noise()
        optimized_graph = self.graph.copy()
        
        for cluster in clusters:
            if len(cluster) < 2:
                continue
                
            # Select a representative ID (or generate a new one)
            # Here we generate a merged ID
            merged_id = f"merged_{hashlib.md5(str(sorted(list(cluster))).encode()).hexdigest()[:8]}"
            
            # Aggregate content and embeddings
            nodes_data = [self._node_map[nid] for nid in cluster]
            avg_embedding = np.mean([n.embedding for n in nodes_data], axis=0)
            combined_content = " | ".join([n.content for n in nodes_data])
            
            # Create new merged node
            new_node = KnowledgeNode(
                id=merged_id,
                content=combined_content,
                embedding=avg_embedding,
                context_id=nodes_data[0].context_id, # Inherit context
                metadata={"merged_from": list(cluster)}
            )
            
            # Add new node to the graph structure
            optimized_graph.add_node(merged_id, data=new_node)
            
            # Re-route edges
            for old_id in cluster:
                # Predecessors (incoming)
                for pred in optimized_graph.predecessors(old_id):
                    if pred not in cluster:
                        optimized_graph.add_edge(pred, merged_id)
                
                # Successors (outgoing)
                for succ in optimized_graph.successors(old_id):
                    if succ not in cluster:
                        optimized_graph.add_edge(merged_id, succ)
                
                # Remove old node
                optimized_graph.remove_node(old_id)
            
            logger.info(f"Merged {len(cluster)} nodes into {merged_id}")

        return optimized_graph


# --- Utility Functions ---

def generate_mock_embedding(content: str, dim: int = 128) -> np.ndarray:
    """
    Generates a deterministic random vector based on content hash for simulation.
    """
    hash_val = int(hashlib.sha256(content.encode()).hexdigest(), 16)
    np.random.seed(hash_val % (2**32))
    return np.random.rand(dim)

def run_demo():
    """
    Demonstrates the usage of the MCG Optimizer.
    """
    print("-" * 50)
    print("Running MCG Optimization Demo")
    print("-" * 50)

    # 1. Create Mock Data (Simulating over-segmented knowledge)
    # "AI", "Artificial Intelligence", "AI Tech" -> Should merge (High similarity, same context)
    # "Apple (Fruit)" -> Should remain separate (Different context/semantics)
    
    nodes = [
        KnowledgeNode(
            id="n1", 
            content="Artificial Intelligence", 
            embedding=generate_mock_embedding("Artificial Intelligence"),
            context_id="tech"
        ),
        KnowledgeNode(
            id="n2", 
            content="AI", 
            embedding=generate_mock_embedding("Artificial Intelligence"), # Identical vector to simulate semantic overlap
            context_id="tech"
        ),
        KnowledgeNode(
            id="n3", 
            content="Machine Learning", 
            embedding=generate_mock_embedding("Machine Learning"), # Distinct
            context_id="tech"
        ),
        KnowledgeNode(
            id="n4", 
            content="AI Tech", 
            embedding=generate_mock_embedding("Artificial Intelligence"), # Identical
            context_id="tech"
        ),
        KnowledgeNode(
            id="n5", 
            content="Apple", 
            embedding=generate_mock_embedding("Fruit Company"), # Completely different
            context_id="business"
        ),
    ]
    
    # Force n2 embedding to be almost identical to n1
    nodes[1].embedding = nodes[0].embedding + np.random.normal(0, 0.01, 128)
    nodes[3].embedding = nodes[0].embedding + np.random.normal(0, 0.01, 128)

    # 2. Initialize Optimizer
    optimizer = MCGOptimizer(similarity_threshold=0.95, min_cluster_size=2)

    # 3. Add Nodes
    optimizer.add_nodes(nodes)

    # 4. Run Optimization
    optimized_graph = optimizer.optimize_topology()

    # 5. Results
    print(f"\nOriginal Node Count: {len(nodes)}")
    print(f"Optimized Node Count: {optimized_graph.number_of_nodes()}")
    
    print("\nRemaining Nodes in Graph:")
    for node_id, data in optimized_graph.nodes(data=True):
        node_obj = data['data']
        print(f"- ID: {node_id} | Content: {node_obj.content[:30]}... | Merged: {node_obj.metadata.get('merged_from', 'N/A')}")

if __name__ == "__main__":
    run_demo()