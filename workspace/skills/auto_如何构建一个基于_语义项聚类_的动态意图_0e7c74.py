"""
Module: semantic_intent_skeletonizer.py

A high-level cognitive science module designed to transform fuzzy, discrete natural language
inputs into a structured, hierarchical 'Intent Tree'. This system leverages semantic vector
clustering to map non-linear human thought processes (often discrete and跳跃的/jumping)
into a constrained JSON/Graph framework suitable for downstream AGI code generation or
task planning.

Dependencies:
    - numpy
    - scikit-learn
    - networkx (for graph structure)

Author: AGI System Core
Version: 1.0.0
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class IntentNode:
    """
    Represents a single node in the Intent Tree.
    
    Attributes:
        id: Unique identifier for the graph node.
        label: The semantic label (keyword or topic) derived from clustering.
        raw_terms: Original raw terms associated with this cluster.
        parent_id: ID of the parent node in the hierarchy.
        embedding_vector: The centroid or representative vector (excluded from JSON output).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    raw_terms: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    embedding_vector: Optional[np.ndarray] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the node to a dictionary, excluding the vector."""
        return {
            "id": self.id,
            "label": self.label,
            "raw_terms": self.raw_terms,
            "parent_id": self.parent_id
        }

@dataclass
class IntentSkeleton:
    """
    The final output structure containing the graph definition.
    """
    root_id: str
    nodes: List[Dict[str, Any]]
    adjacency_list: Dict[str, List[str]]
    metadata: Dict[str, Any]

# --- Core Logic ---

class SemanticIntentSkeletonizer:
    """
    Dynamically generates an intent skeleton by clustering input tokens
    based on their semantic similarity.
    """

    def __init__(self, min_cluster_size: int = 2, max_hierarchy_depth: int = 3):
        """
        Initializes the skeletonizer.

        Args:
            min_cluster_size: Minimum number of items to form a distinct cluster.
            max_hierarchy_depth: Safety limit for recursive clustering depth.
        """
        self.min_cluster_size = min_cluster_size
        self.max_hierarchy_depth = max_hierarchy_depth
        logger.info("SemanticIntentSkeletonizer initialized.")

    def _get_mock_embedding(self, term: str) -> np.ndarray:
        """
        [HELPER FUNCTION]
        Generates a deterministic mock embedding vector for a given term.
        In a production environment, this would call an embedding model (e.g., SentenceTransformer, OpenAI).
        
        Args:
            term: The input string term.
            
        Returns:
            A normalized numpy array representing the term.
        """
        # Using a simple hash-based projection to simulate semantic space
        # Hash values determine the vector components to ensure determinism
        base_vec = np.zeros(128)
        term_hash = hash(term)
        
        # Seed random for reproducibility based on the term
        rng = np.random.RandomState(term_hash % (2**32))
        vec = rng.randn(128)
        
        # Normalize to unit length (Cosine similarity range)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return base_vec
        return vec / norm

    def _extract_terms_from_text(self, text: str) -> List[str]:
        """
        Extracts potential intent tokens from a raw text string.
        Simple tokenizer that removes stopwords and punctuation.
        """
        # Basic cleaning
        text = text.lower().replace("'", "").replace("-", " ")
        tokens = text.split()
        
        # Filter out very short tokens or basic connectors (mock stopword list)
        stopwords = {"a", "an", "the", "is", "are", "of", "for", "to", "that", "this", "it"}
        filtered = [t for t in tokens if len(t) > 2 and t not in stopwords]
        
        if not filtered:
            logger.warning("Tokenization resulted in empty list, returning raw split.")
            return tokens
            
        return filtered

    def _recursive_clustering(
        self, 
        terms: List[str], 
        vectors: np.ndarray, 
        parent_id: Optional[str], 
        graph: nx.DiGraph, 
        current_depth: int
    ) -> None:
        """
        [CORE FUNCTION]
        Recursively clusters terms to build a hierarchy.
        
        Args:
            terms: List of string terms in the current scope.
            vectors: Matrix of embeddings corresponding to terms.
            parent_id: The ID of the parent node to attach new clusters to.
            graph: The NetworkX graph object being constructed.
            current_depth: Current recursion depth.
        """
        if current_depth > self.max_hierarchy_depth:
            logger.warning(f"Max recursion depth reached at parent {parent_id}")
            return

        # Determine optimal number of clusters (k) - simplified logic
        n_samples = len(terms)
        if n_samples < self.min_cluster_size:
            # Treat as a leaf node group or individual nodes
            for term in terms:
                node_id = str(uuid.uuid4())
                graph.add_node(node_id, label=term, raw_terms=[term])
                if parent_id:
                    graph.add_edge(parent_id, node_id)
            return

        # Dynamic k calculation: sqrt(n/2), capped at n
        k = max(2, min(int(np.sqrt(n_samples / 2)), n_samples - 1))
        
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)
            logger.info(f"Depth {current_depth}: Clustered {n_samples} items into {k} groups.")
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return

        # Process each cluster
        for cluster_idx in range(k):
            # Get indices of items in this cluster
            indices = np.where(labels == cluster_idx)[0]
            cluster_terms = [terms[i] for i in indices]
            cluster_vectors = vectors[indices]
            
            # Determine representative label (closest to centroid)
            centroid = kmeans.cluster_centers_[cluster_idx]
            similarities = cosine_similarity([centroid], cluster_vectors)[0]
            best_idx_in_cluster = np.argmax(similarities)
            representative_label = cluster_terms[best_idx_in_cluster]

            # Create cluster node
            cluster_node_id = str(uuid.uuid4())
            graph.add_node(cluster_node_id, label=representative_label, raw_terms=cluster_terms)
            
            if parent_id:
                graph.add_edge(parent_id, cluster_node_id)
            
            # Recurse
            self._recursive_clustering(
                cluster_terms, 
                cluster_vectors, 
                cluster_node_id, 
                graph, 
                current_depth + 1
            )

    def generate_skeleton(self, raw_input: str) -> IntentSkeleton:
        """
        [CORE FUNCTION]
        Main entry point. Transforms fuzzy input into a structured Intent Skeleton.
        
        Args:
            raw_input: A fuzzy natural language string (e.g., "apple user experience minimalist design fast").
            
        Returns:
            IntentSkeleton: A dataclass containing the graph structure.
        
        Raises:
            ValueError: If input is empty or invalid.
        """
        if not raw_input or not isinstance(raw_input, str):
            raise ValueError("Input must be a non-empty string.")

        logger.info(f"Processing intent: '{raw_input}'")

        # 1. Tokenization
        tokens = self._extract_terms_from_text(raw_input)
        if not tokens:
            raise ValueError("No valid terms extracted from input.")

        # 2. Vectorization (Mocked)
        vectors = np.array([self._get_mock_embedding(t) for t in tokens])

        # 3. Initialize Graph
        intent_graph = nx.DiGraph()
        
        # Create a Root Node
        root_id = str(uuid.uuid4())
        intent_graph.add_node(root_id, label="ROOT_INTENT", raw_terms=tokens)

        # 4. Build Hierarchy
        self._recursive_clustering(tokens, vectors, root_id, intent_graph, current_depth=1)

        # 5. Format Output
        node_list = []
        for node_id, data in intent_graph.nodes(data=True):
            node_obj = IntentNode(
                id=node_id,
                label=data.get("label", ""),
                raw_terms=data.get("raw_terms", []),
                parent_id=None  # Set below
            )
            node_list.append(node_obj.to_dict())

        # Map parents based on edges
        adj_list = {}
        for u, v in intent_graph.edges():
            # u is parent, v is child
            if u not in adj_list:
                adj_list[u] = []
            adj_list[u].append(v)
            
            # Update parent_id in node list
            for node_dict in node_list:
                if node_dict["id"] == v:
                    node_dict["parent_id"] = u

        return IntentSkeleton(
            root_id=root_id,
            nodes=node_list,
            adjacency_list=adj_list,
            metadata={
                "input_terms_count": len(tokens),
                "total_nodes": len(node_list),
                "technique": "kmeans_semantic_clustering"
            }
        )

# --- Usage Example ---

if __name__ == "__main__":
    # Example Input: A fuzzy set of requirements resembling a user's scattered thoughts
    fuzzy_intent = (
        "像苹果那样的用户体验 极简主义设计 快速响应 " # Apple-like UX, minimalist, fast response
        "dashboard analytics user management " # Functional modules
        "secure login postgresql database cloud " # Infrastructure
        "mobile react native python backend" # Tech stack
    )

    try:
        skeletonizer = SemanticIntentSkeletonizer(min_cluster_size=2, max_hierarchy_depth=4)
        result_skeleton = skeletonizer.generate_skeleton(fuzzy_intent)

        print("\n=== Generated Intent Skeleton (JSON) ===")
        # Pretty print the JSON structure
        output_json = json.dumps(asdict(result_skeleton), indent=2, ensure_ascii=False)
        print(output_json)

    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}", exc_info=True)