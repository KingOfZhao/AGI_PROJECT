"""
Module: auto_如何从非结构化文本中提取高保真的_真实节_4b8fb5
Description: High-fidelity extraction of 'Real Nodes' from unstructured text and
             automatic association with existing knowledge graph nodes.

This module implements a pipeline to filter out non-falsifiable "grand narratives"
and retain only concrete, operational, causal, or entity-based statements. It then
calculates semantic distance against an existing node corpus to prevent redundancy.

Author: Senior Python Engineer (AGI System)
Domain: nlp_knowledge_engineering
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from abc import ABC, abstractmethod
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
DEFAULT_SIMILARITY_THRESHOLD = 0.85  # Threshold to consider nodes as duplicate/redundant
MIN_FACT_LENGTH = 10  # Minimum characters for a valid factual statement
MAX_FACT_LENGTH = 500  # Maximum characters to avoid processing huge blobs

@dataclass
class Node:
    """
    Represents a node in the Knowledge Graph.
    
    Attributes:
        id: Unique identifier.
        content: The text content of the node.
        embedding: Vector representation of the content (Optional).
        metadata: Additional metadata (e.g., source, timestamp).
    """
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not self.content:
            raise ValueError("Node ID and Content cannot be empty.")


class EmbeddingEngine(ABC):
    """Abstract Base Class for Embedding Engines to allow model swapping."""
    
    @abstractmethod
    def encode(self, text: str) -> np.ndarray:
        """Convert text to vector."""
        pass

    @abstractmethod
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Convert list of texts to vectors."""
        pass


class MockEmbeddingEngine(EmbeddingEngine):
    """
    A mock embedding engine for demonstration purposes.
    In production, this would wrap OpenAI, SentenceTransformers, or BERT models.
    """
    
    def encode(self, text: str) -> np.ndarray:
        # Simple hash-based mock vector for reproducibility in example
        np.random.seed(hash(text) % (2**32))
        return np.random.rand(768)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        return np.array([self.encode(t) for t in texts])


class GrandNarrativeFilter:
    """
    Filters out abstract, subjective, or non-falsifiable statements (Grand Narratives).
    Retains high-fidelity 'Real Nodes' (Concrete facts, Operations, Causality).
    """

    # Regex patterns for vague or subjective language
    VAGUE_PATTERNS = [
        r'\b(philosophy|spiritual|essence|fundamentally|generally|usually)\b',
        r'\b(believe|think|feel|might|could|perhaps)\b',
        r'\b(great|amazing|terrible|huge|big)\b(?! \d)',  # Vague adjectives without numbers
    ]

    # Patterns for high-fidelity content (Units, Specific Actions, Code, Causal links)
    CONCRETE_PATTERNS = [
        r'\b\d+(\.\d+)?\s*(kg|mb|gb|ms|percent|%|dollars|units)\b', # Measurements
        r'\b(if|when|because|therefore|execute|run|create|delete|update)\b', # Logic/Action
        r'\b(http|https|www|api|class|def|function)\b', # Technical entities
    ]

    def filter_text(self, text: str) -> Tuple[bool, float]:
        """
        Analyzes text to determine if it is a high-fidelity fact.

        Args:
            text: The input text segment.

        Returns:
            Tuple[bool, float]: (is_valid_fact, confidence_score)
        """
        if not isinstance(text, str):
            logger.error(f"Invalid input type: {type(text)}")
            return False, 0.0

        text = text.strip()
        if len(text) < MIN_FACT_LENGTH or len(text) > MAX_FACT_LENGTH:
            return False, 0.0

        # Check for vague content (Negative signals)
        vague_matches = 0
        for pattern in self.VAGUE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                vague_matches += 1

        # Check for concrete content (Positive signals)
        concrete_matches = 0
        for pattern in self.CONCRETE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                concrete_matches += 1

        # Heuristic Scoring
        # If vague language is dominant, reject
        if vague_matches > 1 and concrete_matches == 0:
            return False, 0.2
        
        # If concrete indicators exist, accept
        if concrete_matches > 0:
            return True, 0.9
        
        # Default: Neutral check (Length based basic validity)
        return True, 0.5


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    Helper function.
    """
    if vec_a is None or vec_b is None:
        return 0.0
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(vec_a, vec_b) / (norm_a * norm_b)


def extract_and_associate_nodes(
    raw_text: str,
    existing_nodes: List[Node],
    embedding_engine: EmbeddingEngine,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> List[Node]:
    """
    Main pipeline: Extracts real nodes from text and associates them with the graph.
    
    Strategy:
    1. Segment text into candidate sentences.
    2. Filter candidates using GrandNarrativeFilter.
    3. Vectorize valid candidates.
    4. Check against existing nodes to ensure novelty.
    5. Return list of new, high-fidelity nodes.

    Args:
        raw_text (str): Unstructured input text.
        existing_nodes (List[Node]): List of nodes already in the KG.
        embedding_engine (EmbeddingEngine): Engine to generate vectors.
        similarity_threshold (float): Threshold for semantic deduplication.

    Returns:
        List[Node]: A list of new nodes ready to be added to the graph.
    """
    logger.info(f"Starting extraction from text (length: {len(raw_text)})")
    
    # 1. Pre-processing and Segmentation
    # Simple sentence splitting (regex based for robustness in this demo)
    candidates = re.split(r'(?<=[.!?])\s+', raw_text.strip())
    candidates = [c for c in candidates if len(c) > MIN_FACT_LENGTH]
    
    logger.info(f"Segmented into {len(candidates)} candidates.")

    # 2. Filtering High-Fidelity Facts
    filter_engine = GrandNarrativeFilter()
    valid_facts = []
    
    for candidate in candidates:
        is_valid, score = filter_engine.filter_text(candidate)
        if is_valid and score > 0.6:  # Confidence threshold
            valid_facts.append(candidate)
            
    logger.info(f"Identified {len(valid_facts)} high-fidelity facts.")

    if not valid_facts:
        return []

    # 3. Embedding Generation
    try:
        # Vectorize new candidates
        new_embeddings = embedding_engine.encode_batch(valid_facts)
        
        # Vectorize existing nodes if missing (optimization: assume pre-computed in real scenario)
        existing_embeddings = np.array([
            n.embedding for n in existing_nodes if n.embedding is not None
        ])
        
        if len(existing_embeddings) == 0 and len(existing_nodes) > 0:
            # Fallback: compute on fly if missing (slow)
            logger.warning("Existing nodes lack embeddings. Computing on the fly.")
            existing_embeddings = embedding_engine.encode_batch([n.content for n in existing_nodes])

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return []

    # 4. Deduplication and Association
    new_nodes_to_add = []
    
    for i, fact in enumerate(valid_facts):
        candidate_vector = new_embeddings[i]
        
        # Check for duplicates in existing nodes
        is_duplicate = False
        if len(existing_embeddings) > 0:
            # Calculate distances (Vectorized operation would be faster for large scale)
            # Here iterating for clarity
            for j, existing_vec in enumerate(existing_embeddings):
                sim = cosine_similarity(candidate_vector, existing_vec)
                if sim >= similarity_threshold:
                    logger.debug(f"Skipping '{fact[:30]}...' due to high similarity ({sim:.2f}) with existing node.")
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            # Create new Node
            node_id = f"node_{int(time.time() * 1000)}_{i}"
            new_node = Node(
                id=node_id,
                content=fact,
                embedding=candidate_vector,
                metadata={"source": "auto_extraction", "timestamp": time.time()}
            )
            new_nodes_to_add.append(new_node)

    logger.info(f"Extraction complete. Generated {len(new_nodes_to_add)} new unique nodes.")
    return new_nodes_to_add


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Mock Data
    sample_text = """
    The fundamental essence of the universe is derived from cosmic consciousness. 
    This is a grand narrative that we should ignore.
    
    However, to install the library, run 'pip install agi-core==1.2.4'.
    This is a specific operation.
    
    The system processes 5000 requests per second using 4 CPU cores.
    This is a high-fidelity entity description with measurements.
    
    I believe that eventually things will get better. 
    This is subjective speculation.
    """
    
    # Existing nodes in the KG (Simulating the 1425 nodes context)
    existing_data = [
        Node(id="n1", content="User must execute 'sudo apt-get update' to refresh packages.", embedding=MockEmbeddingEngine().encode("sudo apt-get update")),
        Node(id="n2", content="The API server listens on port 8080 by default.", embedding=MockEmbeddingEngine().encode("port 8080"))
    ]

    # 2. Initialize Engine
    engine = MockEmbeddingEngine()

    # 3. Run Extraction
    print("--- Starting Extraction Process ---")
    new_nodes = extract_and_associate_nodes(
        raw_text=sample_text,
        existing_nodes=existing_data,
        embedding_engine=engine,
        similarity_threshold=0.85
    )

    # 4. Display Results
    print(f"\n--- Extracted {len(new_nodes)} New Nodes ---")
    for node in new_nodes:
        print(f"ID: {node.id}")
        print(f"Content: {node.content}")
        print("-" * 20)