"""
Module: language_shard_recombination_engine
Description: Implements a 'Language Shard Recombination Engine'. 
             When humans obtain vague, unstructured insights ('language shards') 
             in practice, this engine maps them to existing knowledge graph nodes 
             or forcibly inserts a 'grayscale node' with a confidence score.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents a node in the knowledge network.
    
    Attributes:
        id (str): Unique identifier.
        content (str): The semantic content of the node.
        embedding (Optional[List[float]]): Vector representation of the content.
        neighbors (Set[str]): IDs of connected nodes.
        created_at (str): Timestamp of creation.
    """
    id: str
    content: str
    embedding: Optional[List[float]] = None
    neighbors: Set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "neighbors": list(self.neighbors),
            "created_at": self.created_at
        }

@dataclass
class LanguageShard:
    """
    Represents the raw, unstructured input from human practice.
    
    Attributes:
        raw_text (str): The input text.
        context (Optional[Dict]): Additional context (e.g., timestamp, user mood).
        vector (Optional[List[float]]): Processed vector representation.
    """
    raw_text: str
    context: Optional[Dict] = None
    vector: Optional[List[float]] = None

@dataclass
class RecombinationResult:
    """
    Result of the recombination process.
    """
    status: str  # 'mapped', 'inserted_grayscale', 'rejected'
    node_id: Optional[str] = None
    confidence: float = 0.0
    details: str = ""

# --- Core Engine Class ---

class LanguageRecombinationEngine:
    """
    Engine responsible for processing language shards and integrating them 
    into the existing knowledge graph.
    """

    def __init__(self, similarity_threshold: float = 0.85, grayscale_threshold: float = 0.6):
        """
        Initialize the engine.
        
        Args:
            similarity_threshold (float): Threshold above which a shard maps to an existing node.
            grayscale_threshold (float): Threshold below which a shard is rejected as noise.
        """
        if not (0.0 <= similarity_threshold <= 1.0 and 0.0 <= grayscale_threshold <= 1.0):
            raise ValueError("Thresholds must be between 0.0 and 1.0.")
            
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.similarity_threshold = similarity_threshold
        self.grayscale_threshold = grayscale_threshold
        logger.info("LanguageRecombinationEngine initialized.")

    def _validate_vector(self, vector: List[float]) -> bool:
        """Helper: Validate vector format."""
        if not isinstance(vector, list) or not all(isinstance(x, (float, int)) for x in vector):
            return False
        if len(vector) == 0:
            return False
        return True

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Helper: Calculate cosine similarity between two vectors.
        (Mock implementation for demonstration; in production use numpy/torch)
        """
        if len(vec_a) != len(vec_b):
            logger.error("Vector dimension mismatch.")
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a**2 for a in vec_a) ** 0.5
        norm_b = sum(b**2 for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def _mock_embedding_engine(self, text: str) -> List[float]:
        """
        Helper: Simulate an embedding model (e.g., BERT/OpenAI).
        Converts text to a deterministic vector based on character sums for demo.
        """
        # Simple hash-like embedding for reproducibility in this example
        base_val = sum(ord(c) for c in text) % 100 + 1
        # Normalize to create a unit vector roughly
        return [float(base_val) / 100.0] * 128

    def find_best_match(self, shard_vector: List[float]) -> Tuple[Optional[KnowledgeNode], float]:
        """
        Core Function 1: Search the knowledge graph for the best semantic match.
        
        Args:
            shard_vector (List[float]): The vector representation of the language shard.
            
        Returns:
            Tuple[Optional[KnowledgeNode], float]: The best matching node and the similarity score.
        """
        if not self._validate_vector(shard_vector):
            raise ValueError("Invalid shard vector provided.")

        best_node = None
        best_score = -1.0

        for node in self.knowledge_graph.values():
            if node.embedding is None:
                continue
            
            score = self._cosine_similarity(shard_vector, node.embedding)
            if score > best_score:
                best_score = score
                best_node = node
        
        return best_node, best_score

    def insert_grayscale_node(self, shard: LanguageShard, related_nodes: List[str], confidence: float) -> KnowledgeNode:
        """
        Core Function 2: Force insert a new 'grayscale' node between existing nodes.
        
        Args:
            shard (LanguageShard): The original shard data.
            related_nodes (List[str]): IDs of nodes to link to.
            confidence (float): The calculated confidence score (0.0-1.0).
            
        Returns:
            KnowledgeNode: The newly created grayscale node.
        """
        new_id = f"gray_{uuid.uuid4().hex[:8]}"
        
        # Create new node
        new_node = KnowledgeNode(
            id=new_id,
            content=shard.raw_text,
            embedding=shard.vector,
            neighbors=set(related_nodes)
        )
        
        # Update neighbors (bi-directional linking)
        for node_id in related_nodes:
            if node_id in self.knowledge_graph:
                self.knowledge_graph[node_id].neighbors.add(new_id)
        
        self.knowledge_graph[new_id] = new_node
        logger.info(f"Inserted grayscale node {new_id} with confidence {confidence:.2f}")
        
        return new_node

    def process_shard(self, shard: LanguageShard) -> RecombinationResult:
        """
        Main Pipeline: Processes a language shard and integrates it.
        
        Args:
            shard (LanguageShard): Input data.
            
        Returns:
            RecombinationResult: Object describing the outcome.
        """
        try:
            # 1. Data Validation & Preprocessing
            if not shard.raw_text:
                return RecombinationResult(status="rejected", details="Empty text")
            
            # Generate vector if not present
            if shard.vector is None:
                shard.vector = self._mock_embedding_engine(shard.raw_text)
            
            # 2. Search for existing matches
            best_match, score = self.find_best_match(shard.vector)
            
            # 3. Decision Logic
            if best_match and score >= self.similarity_threshold:
                # Case A: Exact Mapping
                return RecombinationResult(
                    status="mapped",
                    node_id=best_match.id,
                    confidence=score,
                    details=f"Mapped to existing node with high confidence."
                )
            
            elif score >= self.grayscale_threshold:
                # Case B: Grayscale Insertion
                # We link to the closest match even if it wasn't a perfect fit
                related_ids = [best_match.id] if best_match else []
                
                new_node = self.insert_grayscale_node(
                    shard=shard, 
                    related_nodes=related_ids, 
                    confidence=score
                )
                
                return RecombinationResult(
                    status="inserted_grayscale",
                    node_id=new_node.id,
                    confidence=score,
                    details="Inserted as new fuzzy concept."
                )
            
            else:
                # Case C: Rejection (Noise)
                return RecombinationResult(
                    status="rejected",
                    confidence=score,
                    details="Similarity too low, treated as noise."
                )

        except Exception as e:
            logger.error(f"Error processing shard: {e}", exc_info=True)
            return RecombinationResult(status="error", details=str(e))

# --- Utility Functions ---

def load_knowledge_base(base_data: List[Dict[str, str]]) -> Dict[str, KnowledgeNode]:
    """
    Helper: Load initial knowledge base from a list of dicts.
    
    Args:
        base_data (List[Dict]): List of objects containing 'id' and 'content'.
        
    Returns:
        Dict[str, KnowledgeNode]: A dictionary map of nodes.
    """
    graph = {}
    for item in base_data:
        if 'id' in item and 'content' in item:
            # Create embedding for existing nodes
            # (Using the mock logic inline for initialization)
            base_val = sum(ord(c) for c in item['content']) % 100 + 1
            vec = [float(base_val) / 100.0] * 128
            
            node = KnowledgeNode(
                id=item['id'],
                content=item['content'],
                embedding=vec
            )
            graph[item['id']] = node
    return graph

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Initialize Engine
    engine = LanguageRecombinationEngine(similarity_threshold=0.85, grayscale_threshold=0.5)
    
    # 2. Load Initial Knowledge (Mock Data)
    existing_knowledge = [
        {"id": "node_1", "content": "Machine learning is a field of AI."},
        {"id": "node_2", "content": "Python is a programming language."}
    ]
    engine.knowledge_graph = load_knowledge_base(existing_knowledge)
    print(f"Initialized graph with {len(engine.knowledge_graph)} nodes.")

    # 3. Process Shards
    # Scenario A: High similarity (Should map to node_2)
    shard_python = LanguageShard(raw_text="Python code")
    res_a = engine.process_shard(shard_python)
    print(f"\nProcessing 'Python code': {res_a.status} (Conf: {res_a.confidence:.2f})")

    # Scenario B: Medium similarity (Should create Grayscale Node)
    shard_new_concept = LanguageShard(raw_text="Neural networks for deep learning") # Content varies enough
    res_b = engine.process_shard(shard_new_concept)
    print(f"Processing 'Neural networks...': {res_b.status} (ID: {res_b.node_id})")
    
    # Scenario C: Low similarity (Noise)
    shard_noise = LanguageShard(raw_text="asdfghjkl") # Random chars
    res_c = engine.process_shard(shard_noise)
    print(f"Processing 'asdfghjkl': {res_c.status}")