"""
Module: auto_动态上下文窗口的拓扑结构_意图往往依赖长_e3cea4
Description: 动态上下文窗口的拓扑结构。意图往往依赖长尾记忆和非结构化环境信息。
             如何从现有2852个节点中动态检索并构建一个‘最小充分上下文图’，
             使得LLM能基于此图生成代码，同时忽略无关的数千个节点噪点？
Domain: knowledge_graph
"""

import logging
import heapq
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    Represents a node in the knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        content: Unstructured or structured information (e.g., documentation, code snippet).
        embedding: Vector representation of the content for similarity search.
        connections: List of connected node IDs.
        metadata: Additional metadata (e.g., creation time, source).
    """
    id: str
    content: str
    embedding: Optional[List[float]] = None
    connections: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ContextGraphBuilder:
    """
    Builds a dynamic, minimal sufficient context graph from a large knowledge base.
    
    This class implements a strategy to filter thousands of nodes down to a concise 
    subgraph that captures the user's intent and necessary environmental dependencies,
    suitable for consumption by an LLM.
    """

    def __init__(self, knowledge_base: Dict[str, Node], max_nodes: int = 50):
        """
        Initialize the builder with the full knowledge base.
        
        Args:
            knowledge_base: A dictionary mapping Node IDs to Node objects.
            max_nodes: The maximum number of nodes to include in the context graph.
        
        Raises:
            ValueError: If knowledge_base is empty.
        """
        if not knowledge_base:
            logger.error("Knowledge base cannot be empty.")
            raise ValueError("Knowledge base cannot be empty.")
        
        self.knowledge_base = knowledge_base
        self.max_nodes = max_nodes
        logger.info(f"Initialized ContextGraphBuilder with {len(knowledge_base)} nodes.")

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors (Mock implementation).
        
        In a production environment, this would use numpy or an external vector DB.
        
        Args:
            vec_a: First vector.
            vec_b: Second vector.
            
        Returns:
            Similarity score between 0.0 and 1.0.
        """
        # Mock logic: Simple dot product for demonstration (assuming normalized vectors)
        # Handling dimension mismatch gracefully
        if len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        # Assuming normalized vectors for this mock, otherwise divide by magnitudes
        return dot_product

    def _expand_frontier(
        self, 
        seed_scores: Dict[str, float], 
        depth_limit: int = 3
    ) -> Dict[str, float]:
        """
        Expand the search from high-scoring seeds to include topological neighbors.
        
        This simulates retrieving "long-tail" dependencies required for code generation
        that pure semantic search might miss.
        
        Args:
            seed_scores: Dictionary of node IDs and their initial semantic scores.
            depth_limit: How many hops to traverse in the graph.
            
        Returns:
            A dictionary of accumulated scores for the candidate subgraph.
        """
        final_scores: Dict[str, float] = {}
        # Priority Queue: ( -score, depth, node_id ) - negative score for max-heap
        pq: List[Tuple[float, int, str]] = []
        
        # Initialize queue with seeds
        for node_id, score in seed_scores.items():
            heapq.heappush(pq, (-score, 0, node_id))
            
        visited: Set[str] = set()
        
        while pq:
            neg_score, depth, current_id = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            score = -neg_score
            
            # Add to final result
            final_scores[current_id] = score
            if len(final_scores) >= self.max_nodes * 2: # Over-retrieve before filtering
                break
                
            if depth < depth_limit:
                node = self.knowledge_base.get(current_id)
                if not node:
                    continue
                
                # Traverse connections
                for neighbor_id in node.connections:
                    if neighbor_id not in visited and neighbor_id in self.knowledge_base:
                        # Decay score based on depth or connection weight
                        decay_factor = 0.8 
                        new_score = score * decay_factor
                        heapq.heappush(pq, (-new_score, depth + 1, neighbor_id))
                        
        return final_scores

    def build_minimal_context_graph(
        self, 
        query_embedding: List[float], 
        intent_keywords: Optional[List[str]] = None
    ) -> List[Node]:
        """
        Main entry point to build the context graph.
        
        Steps:
        1. Semantic Retrieval: Find top-k nodes matching the query embedding.
        2. Topological Expansion: Traverse connections to find dependencies.
        3. Filtering: Prune nodes below the relevance threshold.
        
        Args:
            query_embedding: The vector representation of the user intent.
            intent_keywords: Optional list of keywords for hybrid filtering.
            
        Returns:
            A list of Node objects forming the Minimal Sufficient Context Graph.
            
        Raises:
            ValueError: If query_embedding is invalid.
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty.")

        logger.info("Starting graph construction...")
        
        # 1. Semantic Search (Mock implementation)
        # In reality, this would be a vector search (e.g., FAISS, Milvus)
        semantic_scores: Dict[str, float] = {}
        
        # Simple sampling for demo to avoid iterating 2852 nodes every time if not needed
        # But here we simulate the full scan or retrieval
        for node_id, node in self.knowledge_base.items():
            if node.embedding:
                similarity = self._cosine_similarity(query_embedding, node.embedding)
                if similarity > 0.5: # Threshold
                    semantic_scores[node_id] = similarity

        if not semantic_scores:
            logger.warning("No relevant nodes found for query.")
            return []

        # 2. Topological Expansion
        # Expand from semantically relevant nodes to include dependency context
        expanded_scores = self._expand_frontier(semantic_scores)
        
        # 3. Ranking and Filtering
        sorted_nodes = sorted(expanded_scores.items(), key=lambda item: item[1], reverse=True)
        selected_ids = [node_id for node_id, score in sorted_nodes[:self.max_nodes]]
        
        result_graph = []
        for nid in selected_ids:
            node = self.knowledge_base.get(nid)
            if node:
                result_graph.append(node)
                
        logger.info(f"Built context graph with {len(result_graph)} nodes.")
        return result_graph

# Example Usage and Data Simulation
if __name__ == "__main__":
    # 1. Setup mock data (Simulating the 2852 nodes environment)
    mock_kb: Dict[str, Node] = {}
    
    # Generate 100 mock nodes for this demo
    for i in range(100):
        node_id = f"node_{i}"
        # Mock embedding: random list of floats
        import random
        embedding = [random.random() for _ in range(10)]
        # Mock connections
        conns = set()
        if i > 0: conns.add(f"node_{i-1}")
        if i < 99: conns.add(f"node_{i+1}")
        
        mock_kb[node_id] = Node(
            id=node_id,
            content=f"Function logic or doc {i}",
            embedding=embedding,
            connections=conns
        )

    # 2. Initialize Builder
    try:
        builder = ContextGraphBuilder(knowledge_base=mock_kb, max_nodes=10)
        
        # 3. Define Intent (Mock query embedding matching node_50 roughly)
        # We make node_50's embedding slightly similar to the query
        query_vec = mock_kb["node_50"].embedding.copy()
        query_vec[0] += 0.1 # Add noise
        
        # 4. Build Graph
        context = builder.build_minimal_context_graph(query_vec)
        
        # 5. Output Results
        print(f"\n--- Generated Context Graph ({len(context)} nodes) ---")
        for node in context:
            print(f"ID: {node.id} | Content: {node.content} | Connections: {len(node.connections)}")

    except Exception as e:
        logger.error(f"Application failed: {e}")