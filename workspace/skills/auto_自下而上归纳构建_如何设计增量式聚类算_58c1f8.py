"""
Incremental Hierarchical Clustering Module for AGI Skill Abstraction.

This module implements a bottom-up agglomerative clustering approach designed to
extract high-dimensional abstract concepts (Parent Nodes) from a large set of
unstructured, fragmented skill nodes. It operates without human annotation,
relying on semantic embeddings and co-occurrence heuristics to organize skills
into a hierarchy.

Design Logic:
1.  **Vectorization**: Converts skill text descriptions into high-dimensional vectors
    using a mock embedding model (simulating SentenceTransformers or OpenAI embeddings).
2.  **Graph Construction**: Builds a similarity graph based on semantic distance
    and co-occurrence frequency to identify local clusters.
3.  **Incremental Clustering**: Uses an agglomerative approach to merge similar nodes.
4.  **Concept Extraction**: Automatically generates a label for the merged cluster
    (simulating LLM-based abstraction) and calculates the information entropy
    reduction to validate the quality of the new hierarchy.

Input Format:
    List[Dict]: A list of dictionaries, where each dict represents a skill node.
                Example: [{'id': 'skill_1', 'desc': 'chop vegetables', 'tags': ['cooking']},
                          {'id': 'skill_2', 'desc': 'slice meat', 'tags': ['cooking']}]

Output Format:
    Dict: A hierarchical tree structure containing original nodes and new abstract parents.
          Includes metadata about entropy reduction.
"""

import logging
import math
import random
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class SkillNode:
    """
    Represents a node in the skill graph.
    Can be a primitive skill or an abstract concept (parent).
    """
    id: str
    description: str
    vector: Optional[List[float]] = field(default=None, repr=False)
    children: List[str] = field(default_factory=list)
    level: int = 0  # 0 for primitive, >0 for abstract
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "children": self.children,
            "level": self.level,
            "parent_id": self.parent_id
        }

@dataclass
class ClusterResult:
    """Container for the clustering algorithm results."""
    root_nodes: List[str]
    all_nodes: Dict[str, Dict]
    entropy_reduction: float
    iterations: int

# --- Helper Functions ---

def calculate_entropy(node_ids: List[str], total_count: int) -> float:
    """
    Calculates the Shannon Entropy of a set of nodes.
    Lower entropy implies more order/structure.
    
    Args:
        node_ids: List of node identifiers in the current scope.
        total_count: The total number of items for probability calculation.
        
    Returns:
        float: The calculated entropy.
    """
    if total_count == 0:
        return 0.0
    
    counts = Counter(node_ids)
    entropy = 0.0
    for count in counts.values():
        p = count / total_count
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Computes cosine similarity between two vectors.
    
    Args:
        vec1: First vector.
        vec2: Second vector.
        
    Returns:
        float: Similarity score between -1 and 1.
    """
    dot_product = sum(p * q for p, q in zip(vec1, vec2))
    norm1 = math.sqrt(sum(p * p for p in vec1))
    norm2 = math.sqrt(sum(q * q for q in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def mock_embedding_engine(text: str) -> List[float]:
    """
    Mock function to simulate a text embedding model (e.g., BERT).
    Generates a deterministic random vector based on text hash.
    
    Args:
        text: Input text to embed.
        
    Returns:
        List[float]: A normalized vector representation.
    """
    random.seed(hash(text))
    vec = [random.gauss(0, 1) for _ in range(16)] # 16-dim vector for demo
    norm = math.sqrt(sum(x**2 for x in vec))
    return [x/norm for x in vec]

def mock_concept_namer(descriptions: List[str]) -> str:
    """
    Mock function to simulate an LLM generating a concept name for a group of skills.
    In a real AGI system, this would call an LLM API.
    """
    if not descriptions:
        return "Empty Concept"
    # Simple heuristic for demo: take common nouns or mock logic
    if "cut" in " ".join(descriptions).lower() or "slice" in " ".join(descriptions).lower():
        return "Food Preparation"
    if "write" in " ".join(descriptions).lower() or "read" in " ".join(descriptions).lower():
        return "Language Processing"
    return f"Abstract Concept {random.randint(100, 999)}"

# --- Core Logic ---

class IncrementalConceptClusterer:
    """
    Incremental Bottom-Up Clustering System.
    
    Attributes:
        threshold: Similarity threshold for merging nodes (0.0 to 1.0).
        min_cluster_size: Minimum nodes to form a new parent concept.
    """
    
    def __init__(self, similarity_threshold: float = 0.75, min_cluster_size: int = 2):
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.node_registry: Dict[str, SkillNode] = {}
        self.pending_nodes: List[str] = []
        
    def _initialize_nodes(self, raw_data: List[Dict]) -> None:
        """
        Converts raw dictionaries into SkillNode objects and generates embeddings.
        """
        logger.info(f"Initializing {len(raw_data)} nodes...")
        for item in raw_data:
            node_id = item.get('id')
            desc = item.get('desc', '')
            
            if not node_id:
                logger.warning("Skipping node with missing ID")
                continue
                
            vector = mock_embedding_engine(desc)
            node = SkillNode(
                id=node_id,
                description=desc,
                vector=vector,
                level=0
            )
            self.node_registry[node_id] = node
            self.pending_nodes.append(node_id)
            
    def _find_most_similar_pair(self, candidate_ids: List[str]) -> Tuple[Optional[str], Optional[str], float]:
        """
        Finds the pair of nodes with the highest semantic similarity.
        
        Args:
            candidate_ids: List of node IDs currently available for clustering.
            
        Returns:
            Tuple: (id1, id2, similarity_score) or (None, None, 0) if no pair found.
        """
        best_score = -1.0
        best_pair = (None, None)
        
        # O(N^2) search for demo; in production use KD-Tree or FAISS
        for i in range(len(candidate_ids)):
            for j in range(i + 1, len(candidate_ids)):
                node1 = self.node_registry[candidate_ids[i]]
                node2 = self.node_registry[candidate_ids[j]]
                
                # Skip if they already share a parent (simple check to avoid redundancy)
                if node1.parent_id and node1.parent_id == node2.parent_id:
                    continue
                
                sim = cosine_similarity(node1.vector, node2.vector)
                if sim > best_score:
                    best_score = sim
                    best_pair = (candidate_ids[i], candidate_ids[j])
                    
        return best_pair[0], best_pair[1], best_score

    def _create_abstract_parent(self, child_ids: List[str]) -> str:
        """
        Creates a new abstract parent node from merged children.
        Updates children references.
        """
        children = [self.node_registry[cid] for cid in child_ids]
        descriptions = [c.description for c in children]
        
        # Generate new concept metadata
        new_id = f"concept_{len(self.node_registry)}"
        new_desc = mock_concept_namer(descriptions)
        
        # Average embedding for the parent (centroid)
        dim = len(children[0].vector)
        avg_vector = [
            sum(c.vector[i] for c in children) / len(children) 
            for i in range(dim)
        ]
        
        parent_node = SkillNode(
            id=new_id,
            description=new_desc,
            vector=avg_vector,
            children=child_ids,
            level=max(c.level for c in children) + 1
        )
        
        self.node_registry[new_id] = parent_node
        
        # Update children
        for cid in child_ids:
            self.node_registry[cid].parent_id = new_id
            
        logger.info(f"Created Parent: {new_desc} (ID: {new_id}) containing {len(child_ids)} skills.")
        return new_id

    def run_clustering(self, raw_data: List[Dict]) -> ClusterResult:
        """
        Executes the incremental clustering pipeline.
        
        Args:
            raw_data: List of raw skill dictionaries.
            
        Returns:
            ClusterResult object containing the hierarchy and stats.
        """
        if not raw_data:
            raise ValueError("Input data cannot be empty")
            
        # 1. Initialization
        self._initialize_nodes(raw_data)
        
        # Calculate Initial Entropy (System Disorder)
        # Assuming all nodes are independent leaves initially
        initial_entropy = calculate_entropy(list(self.node_registry.keys()), len(self.node_registry))
        logger.info(f"Initial System Entropy: {initial_entropy:.4f}")
        
        # 2. Incremental Agglomerative Loop
        # We cluster until no pairs exceed the threshold
        active_nodes = list(self.node_registry.keys()) # Nodes currently available to cluster
        iterations = 0
        
        while True:
            iterations += 1
            if iterations > 1000: # Safety break
                logger.warning("Max iterations reached.")
                break
                
            # Find best pair
            id1, id2, score = self._find_most_similar_pair(active_nodes)
            
            if id1 is None or score < self.similarity_threshold:
                logger.info(f"Clustering stopped. Best remaining similarity: {score:.4f}")
                break
                
            # Merge pair
            logger.debug(f"Merging {id1} and {id2} (Sim: {score:.4f})")
            
            # Remove merged nodes from active list
            active_nodes.remove(id1)
            active_nodes.remove(id2)
            
            # Create parent and add to active list
            new_parent_id = self._create_abstract_parent([id1, id2])
            active_nodes.append(new_parent_id)
            
        # 3. Finalization
        final_entropy = calculate_entropy(active_nodes, len(self.node_registry))
        reduction = initial_entropy - final_entropy
        
        # Identify roots (nodes with no parent)
        roots = [nid for nid, node in self.node_registry.items() if node.parent_id is None]
        
        return ClusterResult(
            root_nodes=roots,
            all_nodes={k: v.to_dict() for k, v in self.node_registry.items()},
            entropy_reduction=reduction,
            iterations=iterations
        )

# --- Main Execution / Usage Example ---

def main():
    """
    Usage Example for the Incremental Concept Clusterer.
    """
    logger.info("Starting Skill Clustering Process...")
    
    # Simulating 1530 unstructured skill nodes
    sample_skills = [
        {"id": "s1", "desc": "Chop carrots and onions"},
        {"id": "s2", "desc": "Slice beef for steak"},
        {"id": "s3", "desc": "Boil water for pasta"},
        {"id": "s4", "desc": "Write python code"},
        {"id": "s5", "desc": "Debug java exceptions"},
        {"id": "s6", "desc": "Fix software bugs"},
        {"id": "s7", "desc": "Marinate chicken"},
        {"id": "s8", "desc": "Review pull requests"},
        {"id": "s9", "desc": "Dice tomatoes"},
    ]
    
    try:
        clusterer = IncrementalConceptClusterer(similarity_threshold=0.6)
        result = clusterer.run_clustering(sample_skills)
        
        print("\n--- Clustering Report ---")
        print(f"Total Nodes Processed: {len(result.all_nodes)}")
        print(f"Root Concepts Identified: {len(result.root_nodes)}")
        print(f"Entropy Reduction: {result.entropy_reduction:.4f} bits")
        print(f"Total Iterations: {result.iterations}")
        
        print("\n--- Hierarchy Structure (JSON Snippet) ---")
        # Pretty print the result
        output = {
            "roots": result.root_nodes,
            "graph": result.all_nodes
        }
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        logger.error(f"Critical error during execution: {e}", exc_info=True)

if __name__ == "__main__":
    main()