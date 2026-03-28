"""
Module: intent_skill_mapper.py
Description: 【认知映射层】构建意图-技能向量索引地图，解决自然语言与函数签名之间的语义鸿沟。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import numpy as np
from pydantic import BaseModel, Field, ValidationError, validator

# Attempt to import embedding libraries, handle absence gracefully
try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# --- Data Models ---

class SkillSignature(BaseModel):
    """Represents the structural metadata of a single Skill node."""
    skill_id: str = Field(..., description="Unique identifier for the skill")
    function_name: str = Field(..., description="The actual python function name (e.g., 'calculate_tax')")
    description: str = Field(..., description="Natural language description of what the skill does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Expected parameters schema")
    tags: List[str] = Field(default_factory=list, description="Keywords associated with the skill")

    @validator('function_name')
    def validate_func_name(cls, v):
        if not v.isidentifier():
            logger.warning(f"Function name {v} might not be a valid Python identifier.")
        return v

class MappingConfig(BaseModel):
    """Configuration for the Embedding Mapper."""
    embedding_dim: int = 768
    similarity_threshold: float = 0.75
    max_results: int = 5

# --- Core Classes ---

@dataclass
class IndexedSkill:
    """Internal representation of a skill with its vector."""
    metadata: SkillSignature
    vector: np.ndarray
    combined_text: str

class SemanticGapError(Exception):
    """Custom exception for errors related to semantic mapping."""
    pass

class IntentSkillMapper:
    """
    Core class for the Cognitive Mapping Layer.
    
    Bridges the gap between user intent (Natural Language) and system capabilities (Skill Function Signatures).
    It constructs a high-dimensional vector index to enable precise semantic navigation.
    """

    def __init__(self, config: Optional[MappingConfig] = None):
        """
        Initialize the mapper with configuration.
        
        Args:
            config (MappingConfig, optional): Configuration object. Defaults to basic config.
        """
        self.config = config if config else MappingConfig()
        self.skill_index: Dict[str, IndexedSkill] = {}
        self.vector_matrix: Optional[np.ndarray] = None
        self._is_built = False
        
        # Mocking the Embedding Model interface
        # In production, this would load a fine-tuned SentenceTransformer or similar
        self.embed_model = self._mock_embedding_model
        logger.info(f"IntentSkillMapper initialized with dimension {self.config.embedding_dim}")

    def _mock_embedding_model(self, text: str) -> np.ndarray:
        """
        [Helper Function]
        Simulates a fine-tuned embedding model.
        Converts text to a deterministic normalized vector for demonstration.
        
        Production Note: Replace with actual model inference, e.g.,
        `model.encode(text)`
        """
        if not text:
            return np.zeros(self.config.embedding_dim)
        
        # Simple hash-based mock vector generation
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        # Generate deterministic pseudo-random vector from hash
        np.random.seed(int(text_hash[:8], 16))
        vector = np.random.rand(self.config.embedding_dim)
        
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _construct_semantic_payload(self, skill: SkillSignature) -> str:
        """
        [Helper Function]
        Constructs a enriched text payload for embedding.
        This is crucial for closing the 'Semantic Gap'. It combines:
        1. Functional logic (Function Name)
        2. Natural Language context (Description)
        3. Structural hints (Parameter keys)
        
        Args:
            skill (SkillSignature): The skill metadata.
            
        Returns:
            str: A concatenated string optimized for semantic search.
        """
        # Combine function name semantics with description
        # Function names like 'get_user_profile' provide strong semantic signals
        func_name_decamel = skill.function_name.replace('_', ' ')
        
        # Extract parameter names as context (e.g., 'user_id' implies specific entity)
        param_keys = " ".join(skill.parameters.keys())
        
        # Combine
        payload = f"{func_name_decamel} {skill.description} {param_keys} {' '.join(skill.tags)}"
        return payload.lower().strip()

    def build_index(self, skill_nodes: List[SkillSignature]) -> bool:
        """
        [Core Function 1]
        Builds the vector index map from a list of skill nodes.
        
        Args:
            skill_nodes (List[SkillSignature]): List of skill metadata objects.
            
        Returns:
            bool: True if index was built successfully.
            
        Raises:
            ValueError: If skill_nodes is empty.
        """
        if not skill_nodes:
            raise ValueError("Cannot build index with empty skill list.")
        
        logger.info(f"Starting index construction for {len(skill_nodes)} skills...")
        temp_vectors = []
        
        try:
            for skill in skill_nodes:
                payload = self._construct_semantic_payload(skill)
                vector = self.embed_model(payload)
                
                self.skill_index[skill.skill_id] = IndexedSkill(
                    metadata=skill,
                    vector=vector,
                    combined_text=payload
                )
                temp_vectors.append(vector)
            
            # Create matrix for efficient batch processing
            self.vector_matrix = np.array(temp_vectors)
            self._is_built = True
            logger.info("Index construction complete. Map is ready.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build index: {str(e)}")
            self._is_built = False
            raise SemanticGapError(f"Index building failed: {e}")

    def resolve_intent(self, user_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        [Core Function 2]
        Maps user intent (query) to specific Skill function signatures.
        Performs semantic search to bridge the gap between 'What was said' and 'What to run'.
        
        Args:
            user_query (str): The natural language input from the user.
            top_k (int): Number of top candidates to retrieve.
            
        Returns:
            List[Dict[str, Any]]: A list of candidate skills with similarity scores and metadata.
        """
        if not self._is_built or self.vector_matrix is None:
            raise SemanticGapError("Index not built. Please call build_index() first.")
            
        if not user_query or not isinstance(user_query, str):
            raise ValueError("User query must be a non-empty string.")

        logger.info(f"Resolving intent for query: '{user_query}'")
        
        # 1. Embed the user query
        query_vector = self.embed_model(user_query)
        
        # 2. Calculate Cosine Similarity (Batch operation)
        # query_vector reshaped to (1, dim)
        if SKLEARN_AVAILABLE:
            similarities = cosine_similarity(query_vector.reshape(1, -1), self.vector_matrix)[0]
        else:
            # Fallback manual cosine similarity if sklearn missing
            logger.warning("sklearn not found, using slow python implementation.")
            norm_q = np.linalg.norm(query_vector)
            norms_v = np.linalg.norm(self.vector_matrix, axis=1)
            dot = np.dot(self.vector_matrix, query_vector)
            similarities = dot / (norms_v * norm_q + 1e-10)

        # 3. Filter and Sort
        # Get indices of top_k highest scores
        # Using argpartition for efficiency on large N (650 is small, but good practice)
        if top_k > len(similarities):
            top_k = len(similarities)
            
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        # Sort the top_k indices by actual score
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            
            # Semantic Gap Check: Filter out low probability matches
            if score < self.config.similarity_threshold:
                continue
                
            skill_id = list(self.skill_index.keys())[idx]
            indexed_skill = self.skill_index[skill_id]
            
            result_entry = {
                "skill_id": indexed_skill.metadata.skill_id,
                "function_name": indexed_skill.metadata.function_name,
                "confidence": round(score, 4),
                "matched_text": indexed_skill.combined_text,
                "input_schema": indexed_skill.metadata.parameters
            }
            results.append(result_entry)
        
        if not results:
            logger.warning(f"No skills found above threshold {self.config.similarity_threshold}")
            
        return results

# --- Usage Example & Demonstration ---

def load_mock_skills(n: int = 650) -> List[SkillSignature]:
    """Generates mock skill data for demonstration."""
    skills = []
    base_skills = [
        {"id": "skill_001", "func": "calculate_compound_interest", "desc": "Calculates interest based on rate and time", "params": {"principal": "float", "rate": "float"}},
        {"id": "skill_002", "func": "search_web", "desc": "Searches the internet for information", "params": {"query": "str"}},
        {"id": "skill_003", "func": "send_email_notification", "desc": "Sends an email to a user", "params": {"to": "str", "body": "str"}},
        {"id": "skill_004", "func": "translate_language", "desc": "Translates text from one language to another", "params": {"text": "str", "target": "str"}},
        {"id": "skill_005", "func": "analyze_sentiment", "desc": "Determines if text is positive or negative", "params": {"text": "str"}},
    ]
    
    # Cycle through base skills to create N nodes (simulation of 650 nodes)
    for i in range(n):
        base = base_skills[i % len(base_skills)]
        skills.append(SkillSignature(
            skill_id=f"{base['id']}_{i}",
            function_name=base['func'],
            description=base['desc'],
            parameters=base['params'],
            tags=["finance", "communication", "nlp", "utility"][i % 4]
        ))
    return skills

if __name__ == "__main__":
    # 1. Setup Configuration
    config = MappingConfig(embedding_dim=512, similarity_threshold=0.6)
    
    # 2. Initialize Mapper
    mapper = IntentSkillMapper(config=config)
    
    # 3. Load Data (Simulating the 650 skill nodes)
    skills_db = load_mock_skills(650)
    print(f"Loaded {len(skills_db)} skills.")
    
    # 4. Build Cognitive Map
    try:
        mapper.build_index(skills_db)
        
        # 5. Resolve Intent (Test Case 1: Direct Match)
        query_1 = "I want to find information about python programming"
        matches_1 = mapper.resolve_intent(query_1)
        
        print(f"\nQuery: '{query_1}'")
        for match in matches_1:
            print(f"-> Matched: {match['function_name']} (Confidence: {match['confidence']})")
            
        # 6. Resolve Intent (Test Case 2: Semantic Gap / Indirect Mapping)
        # User says "Check how much money I will make", System maps to 'calculate_compound_interest'
        query_2 = "Check my investment growth over time"
        matches_2 = mapper.resolve_intent(query_2)
        
        print(f"\nQuery: '{query_2}'")
        for match in matches_2:
            print(f"-> Matched: {match['function_name']} (Confidence: {match['confidence']})")
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")