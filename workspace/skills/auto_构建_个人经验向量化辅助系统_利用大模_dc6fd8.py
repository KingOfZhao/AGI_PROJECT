"""
Module: personal_intuition_vectorizer.py

Description:
    Implements the 'Personal Experience Vectorization System'.
    This system transforms user experiences, reading habits, and social data
    into a high-dimensional vector space using Large Models (LLM/Embeddings).
    It facilitates 'Digital Intuition' by performing approximate nearest neighbor
    searches to simulate non-linear, subconscious associations.

Key Features:
    - Generates vector embeddings from unstructured text memories.
    - Handles storage and indexing using a vector store abstraction.
    - Performs 'intuitive jumps' via similarity search to externalize subconscious preferences.

Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Mocking LLM/Embedding Libraries for standalone execution
# In production, replace with: from openai import OpenAI, from langchain.embeddings...
import numpy as np

# --- Configuration & Setup ---

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IntuitionVectorizer")

# --- Data Structures ---

@dataclass
class ExperienceEntry:
    """
    Represents a single unit of personal experience.
    
    Attributes:
        content (str): The raw text description of the experience/memory.
        category (str): Type of memory (e.g., 'life_event', 'book_excerpt', 'social_log').
        timestamp (str): ISO format datetime.
        metadata (Dict): Additional structured data (emotions, people involved).
    """
    content: str
    category: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not isinstance(self.content, str):
            raise ValueError("Content must be a non-empty string.")
        if not self.category:
            raise ValueError("Category cannot be empty.")


class VectorStore:
    """
    A mock Vector Database interface simulating FAISS, Pinecone, or ChromaDB.
    Stores vectors in memory for demonstration purposes.
    """
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}
        logger.info(f"Initialized VectorStore with dimension {dimension}")

    def add_vector(self, id: str, vector: List[float], payload: Dict) -> bool:
        """Adds a vector and its payload to the store."""
        if len(vector) != self.dimension:
            logger.error(f"Dimension mismatch: expected {self.dimension}, got {len(vector)}")
            return False
        self.vectors[id] = np.array(vector)
        self.metadata[id] = payload
        return True

    def search_similar(self, query_vector: List[float], k: int = 5) -> List[Dict]:
        """Performs a brute-force nearest neighbor search."""
        if not self.vectors:
            return []
        
        query_vec = np.array(query_vector)
        # Normalize for Cosine Similarity
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
        
        scores = []
        for id, vec in self.vectors.items():
            vec_norm = vec / (np.linalg.norm(vec) + 1e-9)
            score = np.dot(query_norm, vec_norm)
            scores.append((id, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for id, score in scores[:k]:
            res = {
                "id": id,
                "score": float(score),
                "metadata": self.metadata[id]
            }
            results.append(res)
        return results


class EmbeddingEngine:
    """
    Mock interface for an LLM Embedding Model (e.g., OpenAI text-embedding-3-small).
    Simulates the conversion of text to semantic vectors.
    """
    def __init__(self, model_name: str = "text-mock-embedding-v1"):
        self.model_name = model_name
        self.vector_dim = 1536
        logger.info(f"Embedding Engine initialized with model: {model_name}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generates a deterministic mock vector based on text hash.
        Ensures same text gets same vector, similar texts... well, in mock it's random.
        """
        if not text:
            raise ValueError("Cannot embed empty text.")
        
        # Simulate vector generation
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (10 ** 8)
        rng = np.random.default_rng(seed)
        vector = rng.random(self.vector_dim).tolist()
        return vector


# --- Core Logic ---

class IntuitionEngine:
    """
    The main system class that orchestrates the transformation of experiences
    into a vector space and performs intuitive searches.
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_engine = EmbeddingEngine()
        logger.info("IntuitionEngine initialized successfully.")

    def _validate_entry(self, entry: Union[Dict, ExperienceEntry]) -> ExperienceEntry:
        """
        Helper function to validate and normalize input data.
        
        Args:
            entry: Raw data dictionary or ExperienceEntry object.
            
        Returns:
            Validated ExperienceEntry object.
            
        Raises:
            ValueError: If data is invalid.
        """
        if isinstance(entry, ExperienceEntry):
            return entry
        
        if isinstance(entry, dict):
            try:
                return ExperienceEntry(**entry)
            except TypeError as e:
                logger.error(f"Missing fields in entry: {e}")
                raise ValueError(f"Invalid entry structure: {e}")
        
        raise TypeError("Entry must be a Dict or ExperienceEntry instance.")

    def ingest_experience(self, experience: Union[Dict, ExperienceEntry]) -> str:
        """
        Ingests a single personal experience into the vector database.
        
        This function extracts semantic meaning from the text and stores it
        along with context metadata.
        
        Args:
            experience (Union[Dict, ExperienceEntry]): The data to ingest.
            
        Returns:
            str: The unique ID of the stored vector.
        """
        try:
            # 1. Validation
            valid_entry = self._validate_entry(experience)
            logger.info(f"Ingesting experience: {valid_entry.category} - {valid_entry.content[:30]}...")

            # 2. Generate Embedding
            vector = self.embedding_engine.embed_text(valid_entry.content)
            
            # 3. Generate ID
            entry_id = str(uuid.uuid4())
            
            # 4. Store
            payload = {
                "content": valid_entry.content,
                "category": valid_entry.category,
                "timestamp": valid_entry.timestamp,
                "metadata": valid_entry.metadata
            }
            
            success = self.vector_store.add_vector(entry_id, vector, payload)
            if not success:
                raise RuntimeError("Failed to write to vector store.")
                
            logger.info(f"Experience stored successfully with ID: {entry_id}")
            return entry_id

        except Exception as e:
            logger.exception("Error during experience ingestion.")
            raise

    def query_intuition(self, context: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs an 'Intuitive Search' against the personal vector space.
        
        Instead of logical query parsing, this uses pure vector similarity
        to find memories or preferences that 'feel' related to the input context.
        
        Args:
            context (str): The new situation or thought to match against.
            top_k (int): Number of nearest neighbors to retrieve.
            
        Returns:
            List[Dict]: A list of matching experiences with similarity scores.
        """
        if not context or not isinstance(context, str):
            raise ValueError("Query context must be a non-empty string.")
        
        if top_k < 1:
            top_k = 1
            
        logger.info(f"Querying intuition for context: '{context}'")
        
        try:
            # 1. Convert query to vector
            query_vector = self.embedding_engine.embed_text(context)
            
            # 2. Search
            results = self.vector_store.search_similar(query_vector, k=top_k)
            
            # 3. Format Output
            if not results:
                logger.warning("No intuitive matches found.")
                return []
            
            logger.info(f"Found {len(results)} intuitive links.")
            return results

        except Exception as e:
            logger.exception("Error during intuitive query.")
            raise

# --- Usage Example ---

if __name__ == "__main__":
    # Initialize the system
    system = IntuitionEngine()
    
    # Sample Data: Diverse experiences to form a 'Digital Subconscious'
    sample_experiences = [
        {
            "content": "Spent childhood summers by the lake, fascinated by how water ripples interact.",
            "category": "life_event",
            "metadata": {"emotion": "curious", "tags": ["nature", "physics", "childhood"]}
        },
        {
            "content": "Read 'Chaos: Making a New Science' by James Gleick, deeply interested in the butterfly effect.",
            "category": "reading",
            "metadata": {"emotion": "intellectual_spark", "tags": ["science", "systems"]}
        },
        {
            "content": "Had a debate with friend Mark about how stock markets mimic natural tidal movements.",
            "category": "social",
            "metadata": {"emotion": "engaged", "tags": ["finance", "patterns"]}
        }
    ]
    
    print("\n--- Ingesting Experiences ---")
    for exp in sample_experiences:
        try:
            system.ingest_experience(exp)
        except ValueError as e:
            print(f"Skipping invalid entry: {e}")
            
    print("\n--- Testing Digital Intuition ---")
    
    # New Situation: A complex system design problem
    # Logic might look for 'software architecture', but intuition should find 'ripples' and 'chaos'
    query_context = "Designing a distributed server system where small failures can cascade."
    
    print(f"Input Context: {query_context}")
    
    try:
        intuitive_links = system.query_intuition(query_context, top_k=2)
        
        print("\n>>> Intuition Matches (Digital Gut Feeling):")
        for i, match in enumerate(intuitive_links, 1):
            print(f"{i}. Score: {match['score']:.4f}")
            print(f"   Memory: {match['metadata']['content']}")
            print(f"   Origin: {match['metadata']['category']}")
            
    except Exception as e:
        print(f"System failed to process intuition: {e}")
