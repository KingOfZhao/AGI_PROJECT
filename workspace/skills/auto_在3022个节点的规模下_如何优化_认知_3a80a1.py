"""
Module: cognitive_hybrid_retrieval.py
Author: Senior Python Engineer (AGI Systems)
Description: Implements a scalable Hybrid Cognitive Retrieval system optimized for
             millisecond-level collision reasoning on large-scale graphs (3000+ nodes).

             The system utilizes a two-tier indexing strategy:
             1. Hierarchical Navigable Small World (HNSW) for dense vector similarity (Implicit associations).
             2. Inverted Index for symbolic keyword matching (Explicit relations).
             
             It supports 'collision reasoning' by dynamically re-ranking and fusing results
             from both indices to reconstruct relevant memory fragments.

Domain: Software Engineering / AGI Architecture
"""

import logging
import time
import numpy as np
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveRetrieval")

# --- Data Structures ---

class NodeSchema(BaseModel):
    """Data validation schema for a Cognitive Node."""
    node_id: str
    content: str
    embedding: List[float]
    tags: List[str] = Field(default_factory=list)

    @validator('embedding')
    def check_embedding_dim(cls, v):
        if not v:
            raise ValueError("Embedding cannot be empty")
        return v

@dataclass
class SearchResult:
    """Represents a retrieved memory fragment."""
    node_id: str
    score: float
    match_type: str  # 'vector', 'symbolic', or 'hybrid'
    content_preview: str

class HybridCognitiveIndex:
    """
    A hybrid indexing system designed for high-speed retrieval in AGI memory systems.
    
    Attributes:
        vector_dim (int): Dimensionality of the embedding vectors.
        index_m (int): Number of bi-directional links created for every new element during HNSW construction.
        ef_construction (int): Size of the dynamic candidate list for the nearest neighbors during index construction.
    """

    def __init__(self, vector_dim: int = 256, index_m: int = 16, ef_construction: int = 200):
        self.vector_dim = vector_dim
        
        # Storage
        self._node_store: Dict[str, NodeSchema] = {}  # ID -> Node Data
        self._embeddings_matrix: Optional[np.ndarray] = None # Dense matrix for fast batch ops
        
        # Indices
        # Inverted Index: Tag -> Set of Node IDs
        self._symbolic_index: Dict[str, Set[str]] = {}
        
        # Approximation parameters for HNSW-like behavior (Simplified)
        self._graph_links: Dict[str, List[str]] = {} # Simple adjacency list for graph traversal
        self._entry_point: Optional[str] = None
        
        logger.info(f"Initialized HybridCognitiveIndex with dim={vector_dim}")

    def add_node(self, node: NodeSchema) -> None:
        """
        Adds a cognitive node to the hybrid index.
        
        Args:
            node (NodeSchema): The node object containing ID, content, embedding, and tags.
        """
        try:
            if node.node_id in self._node_store:
                logger.warning(f"Node {node.node_id} already exists. Overwriting.")
            
            # Store Data
            self._node_store[node.node_id] = node
            
            # Update Symbolic Index
            for tag in node.tags:
                if tag not in self._symbolic_index:
                    self._symbolic_index[tag] = set()
                self._symbolic_index[tag].add(node.node_id)
            
            # Update Vector Index (Simplified Graph Construction)
            # In a real HNSW, this involves complex layer assignment.
            # Here we simulate connecting to nearest neighbors in a flat structure.
            self._update_vector_graph(node.node_id, np.array(node.embedding))
            
            logger.debug(f"Added node {node.node_id} to index.")
            
        except Exception as e:
            logger.error(f"Failed to add node {node.node_id}: {e}")
            raise

    def _update_vector_graph(self, node_id: str, vector: np.ndarray) -> None:
        """
        Internal helper to maintain graph connectivity (simplified).
        """
        if self._entry_point is None:
            self._entry_point = node_id
            self._graph_links[node_id] = []
            return

        # Simple heuristic: Connect to 'entry_point' and random sample for resilience
        # In production, this uses cosine similarity search to find M nearest neighbors.
        self._graph_links[node_id] = [self._entry_point]
        self._graph_links[self._entry_point].append(node_id)
        
        # Update global matrix for batch distance calculation
        # Rebuilding the matrix is inefficient for real-time adds but good for search benchmarking
        self._rebuild_embedding_matrix()

    def _rebuild_embedding_matrix(self) -> None:
        """Recreates the numpy matrix for vector search."""
        if not self._node_store:
            self._embeddings_matrix = None
            return
        
        # Ordered list of IDs
        self._id_list = list(self._node_store.keys())
        vectors = [self._node_store[nid].embedding for nid in self._id_list]
        self._embeddings_matrix = np.array(vectors)

    def retrieve(self, query_vector: List[float], query_tags: List[str], k: int = 5) -> List[SearchResult]:
        """
        Performs hybrid retrieval to support collision reasoning.
        
        Steps:
        1. Vector Search: Find nearest neighbors based on embedding similarity.
        2. Symbolic Filter: Find nodes matching specific tags.
        3. Fusion: Combine scores (Reciprocal Rank Fusion or weighted sum).
        
        Args:
            query_vector (List[float]): The embedding of the query.
            query_tags (List[str]): Symbolic constraints (e.g., 'user_profile', 'error_log').
            k (int): Number of top results to return.
            
        Returns:
            List[SearchResult]: The most relevant memory fragments.
        """
        start_time = time.perf_counter()
        
        # Validation
        if len(query_vector) != self.vector_dim:
            raise ValueError(f"Query vector dim mismatch. Expected {self.vector_dim}, got {len(query_vector)}")

        # 1. Vector Search (Approximated via Matrix Multiplication for speed)
        vector_hits: Dict[str, float] = {}
        if self._embeddings_matrix is not None:
            q = np.array(query_vector)
            # Cosine similarity (normalized dot product)
            norms = np.linalg.norm(self._embeddings_matrix, axis=1) * np.linalg.norm(q)
            # Avoid division by zero
            valid_norms = norms > 1e-6
            scores = np.zeros_like(norms)
            scores[valid_norms] = np.dot(self._embeddings_matrix[valid_norms], q) / norms[valid_norms]
            
            # Get top candidates
            # Partitioning is faster than full sort (O(N) vs O(N log N))
            if len(scores) > k:
                top_k_indices = np.argpartition(scores, -k)[-k:]
                top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]
            else:
                top_k_indices = np.argsort(scores)[::-1]

            for idx in top_k_indices:
                node_id = self._id_list[idx]
                vector_hits[node_id] = float(scores[idx])

        # 2. Symbolic Search
        symbolic_hits: Set[str] = set()
        if query_tags:
            for tag in query_tags:
                if tag in self._symbolic_index:
                    symbolic_hits.update(self._symbolic_index[tag])

        # 3. Hybrid Fusion & Collision Reasoning
        # If a node appears in both sets, it's a 'Collision' - high relevance boost.
        fused_results: Dict[str, float] = {}
        
        # Add vector scores
        for nid, score in vector_hits.items():
            base_score = score * 0.6 # Weight for implicit similarity
            collision_bonus = 1.5 if nid in symbolic_hits else 1.0
            fused_results[nid] = base_score * collision_bonus

        # Add pure symbolic scores (if not already added)
        for nid in symbolic_hits:
            if nid not in fused_results:
                fused_results[nid] = 0.8 # Base score for symbolic match
        
        # Sort and Format
        sorted_nodes = sorted(fused_results.items(), key=lambda item: item[1], reverse=True)[:k]
        
        results = []
        for nid, score in sorted_nodes:
            node = self._node_store[nid]
            match_t = "hybrid" if (nid in symbolic_hits and nid in vector_hits) else ("symbolic" if nid in symbolic_hits else "vector")
            
            results.append(SearchResult(
                node_id=nid,
                score=score,
                match_type=match_t,
                content_preview=node.content[:50] + "..."
            ))

        latency = (time.perf_counter() - start_time) * 1000
        logger.info(f"Retrieval completed in {latency:.2f}ms. Found {len(results)} collisions.")
        
        return results

# --- Utility Functions ---

def generate_mock_data(num_nodes: int, vector_dim: int) -> List[NodeSchema]:
    """
    Helper function to generate synthetic cognitive nodes for testing.
    
    Args:
        num_nodes (int): Number of nodes to generate (e.g., 3022).
        vector_dim (int): Dimension of the embedding vector.
        
    Returns:
        List[NodeSchema]: List of valid node objects.
    """
    logger.info(f"Generating {num_nodes} mock nodes...")
    nodes = []
    for i in range(num_nodes):
        node = NodeSchema(
            node_id=f"cog_node_{i}",
            content=f"Memory fragment regarding concept {i} and related context.",
            embedding=np.random.randn(vector_dim).tolist(), # Random normalized vectors
            tags=[f"concept_{i % 50}", f"category_{i % 10}"] # Create some tag overlaps
        )
        nodes.append(node)
    return nodes

# --- Main Execution Block ---

if __name__ == "__main__":
    # Configuration
    NODE_COUNT = 3022
    DIM = 64
    K = 5
    
    # 1. System Setup
    index_system = HybridCognitiveIndex(vector_dim=DIM)
    
    # 2. Data Ingestion
    mock_nodes = generate_mock_data(NODE_COUNT, DIM)
    
    # Batch ingestion simulation
    ingestion_start = time.time()
    for node in mock_nodes:
        index_system.add_node(node)
    logger.info(f"Ingested {NODE_COUNT} nodes in {time.time() - ingestion_start:.2f}s.")
    
    # 3. Query Phase (Simulating AGI Collision Reasoning)
    # Scenario: The AGI recalls a vague memory (Vector) but knows it relates to "concept_5" (Symbolic)
    query_vec = np.random.randn(DIM).tolist()
    query_symbols = ["concept_5"]
    
    print(f"\n--- Initiating Cognitive Retrieval (Nodes: {NODE_COUNT}) ---")
    try:
        results = index_system.retrieve(query_vec, query_symbols, k=K)
        
        print(f"\nTop {K} Relevant Fragments:")
        for res in results:
            print(f"[{res.match_type.upper()}] ID: {res.node_id} | Score: {res.score:.4f} | Content: {res.content_preview}")
            
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")