"""
Incremental Few-Shot Skill Acquisition Module.

This module implements a meta-learning capability for an AGI system. It allows the
system to learn new skills (represented as graph nodes) from a very small number
of demonstrations (1-3 shots) by leveraging a large existing knowledge base of
skill nodes as prior knowledge.

The core mechanism involves:
1.  Feature Extraction: Embedding demonstrations into latent vectors.
2.  Prior Alignment: Comparing new features against existing skill prototypes
    to determine novelty.
3.  Prototype Generation: Creating a robust representation from few examples.
4.  Node Integration: Adding the new skill to the cognitive graph.

Typical usage example:
    # Initialize the learner with existing knowledge graph
    graph = SkillGraph(size=638)
    learner = IncrementalFewShotLearner(knowledge_base=graph)
    
    # Simulate a new skill demonstration (e.g., a new weaving pattern)
    demo_data = [np.random.rand(128) for _ in range(2)] # 2-shot examples
    
    # Learn and generate new node
    new_skill_node = learner.learn_new_skill(demonstrations=demo_data, skill_name="weaving_v2")
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
VECTOR_DIMENSION = 128
MIN_DEMONSTRATIONS = 1
MAX_DEMONSTRATIONS = 3
SIMILARITY_THRESHOLD = 0.85  # Threshold to consider a skill as "existing"
LEARNING_RATE_META = 0.01

@dataclass
class SkillNode:
    """
    Represents a single node in the AGI Cognitive Skill Graph.
    
    Attributes:
        id: Unique identifier for the skill node.
        name: Human-readable name of the skill.
        prototype: The latent vector representing the core features of the skill.
        created_at: Timestamp of creation.
        metadata: Additional properties or parameters.
    """
    id: str
    name: str
    prototype: np.ndarray
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.prototype, np.ndarray):
            raise TypeError("Prototype must be a numpy array.")
        if self.prototype.shape != (VECTOR_DIMENSION,):
            raise ValueError(f"Prototype vector must have dimension {VECTOR_DIMENSION}.")


class KnowledgeBase:
    """
    Simulates the existing database of 638 SKILL nodes.
    In a real AGI system, this would interface with a Vector Database.
    """
    def __init__(self, initial_size: int = 638):
        self.nodes: Dict[str, SkillNode] = {}
        self._initialize_prior_knowledge(initial_size)
        logger.info(f"Knowledge Base initialized with {len(self.nodes)} prior skills.")

    def _initialize_prior_knowledge(self, count: int):
        # Generate synthetic prior skills for simulation
        for i in range(count):
            vec = np.random.normal(0, 1, VECTOR_DIMENSION)
            # Normalize to unit vector for cosine similarity
            vec = vec / np.linalg.norm(vec)
            node = SkillNode(
                id=f"skill_prior_{i}",
                name=f"PriorSkill_{i}",
                prototype=vec
            )
            self.nodes[node.id] = node

    def get_all_prototypes(self) -> np.ndarray:
        """Returns a matrix of all existing skill prototypes."""
        if not self.nodes:
            return np.array([])
        return np.array([n.prototype for n in self.nodes.values()])

    def add_node(self, node: SkillNode):
        self.nodes[node.id] = node
        logger.info(f"New skill node added to Knowledge Base: {node.id}")


def _cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Auxiliary function: Calculate Cosine Similarity between two vectors.
    
    Args:
        v1: First vector.
        v2: Second vector.
        
    Returns:
        Similarity score between -1 and 1.
    """
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(v1, v2) / (norm1 * norm2)


def _encode_demonstration(raw_data: Any) -> np.ndarray:
    """
    Auxiliary function: Mock Encoder.
    
    Simulates a perception module that converts raw sensory input 
    (e.g., video of weaving) into a feature embedding.
    """
    # For this simulation, we assume raw_data is already a processed vector
    # or random noise representing the embedding.
    if isinstance(raw_data, np.ndarray) and raw_data.shape == (VECTOR_DIMENSION,):
        return raw_data
    return np.random.normal(0, 1, VECTOR_DIMENSION)


class IncrementalFewShotLearner:
    """
    Core class for incremental few-shot learning.
    
    Handles the logic of comparing new inputs to prior knowledge and 
    generating new cognitive nodes.
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def _validate_input(self, demonstrations: List[Any]) -> Tuple[bool, str]:
        """Validates the input demonstrations."""
        if not demonstrations:
            return False, "No demonstrations provided."
        if len(demonstrations) > MAX_DEMONSTRATIONS:
            return False, f"Too many demonstrations. Max allowed: {MAX_DEMONSTRATIONS}."
        if len(demonstrations) < MIN_DEMONSTRATIONS:
            return False, f"Too few demonstrations. Min required: {MIN_DEMONSTRATIONS}."
        return True, "Valid"

    def _calculate_novelty(self, feature_vector: np.ndarray) -> Tuple[bool, Optional[str], float]:
        """
        Checks if the feature vector is novel compared to existing skills.
        
        Returns:
            Tuple[is_novel, matched_node_id, max_similarity]
        """
        existing_prototypes = self.knowledge_base.get_all_prototypes()
        if existing_prototypes.size == 0:
            return True, None, 0.0

        # Vectorized cosine similarity calculation
        # (N, D) dot (D, 1) -> (N, 1)
        dots = existing_prototypes @ feature_vector
        norms = np.linalg.norm(existing_prototypes, axis=1) * np.linalg.norm(feature_vector)
        
        # Avoid division by zero
        sims = np.divide(dots, norms, out=np.zeros_like(dots), where=norms!=0)
        
        max_sim_idx = np.argmax(sims)
        max_sim_score = sims[max_sim_idx]

        if max_sim_score > SIMILARITY_THRESHOLD:
            matched_id = list(self.knowledge_base.nodes.keys())[max_sim_idx]
            return False, matched_id, max_sim_score
        
        return True, None, max_sim_score

    def learn_new_skill(
        self, 
        demonstrations: List[np.ndarray], 
        skill_name: str = "New_Craft_Skill"
    ) -> Optional[SkillNode]:
        """
        Main Learning Function.
        
        Processes 1-3 demonstrations, extracts features, checks for novelty,
        and generates a new skill node if the skill is distinct.
        
        Args:
            demonstrations: A list of raw data or embeddings representing the skill.
            skill_name: Proposed name for the new skill.
            
        Returns:
            A SkillNode object if successful, None otherwise.
            
        Raises:
            ValueError: If input validation fails.
        """
        # 1. Data Validation
        is_valid, msg = self._validate_input(demonstrations)
        if not is_valid:
            logger.error(f"Input validation failed: {msg}")
            raise ValueError(msg)

        logger.info(f"Processing {len(demonstrations)} demonstration(s) for skill: {skill_name}")

        # 2. Feature Extraction (Embedding)
        try:
            feature_vectors = [_encode_demonstration(d) for d in demonstrations]
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

        # 3. Prototype Generation (Average Embedding Strategy)
        # In advanced AGI, this would use an LSTM or Prototypical Network
        stacked_features = np.stack(feature_vectors)
        prototype_vector = np.mean(stacked_features, axis=0)
        
        # Normalize prototype
        prototype_vector = prototype_vector / np.linalg.norm(prototype_vector)

        # 4. Novelty Detection vs Prior Knowledge (638 nodes)
        is_novel, existing_id, sim_score = self._calculate_novelty(prototype_vector)

        if not is_novel:
            logger.warning(
                f"Skill '{skill_name}' is not novel. "
                f"Matches existing node {existing_id} with similarity {sim_score:.4f}. "
                "Skipping node creation."
            )
            # Here we might update the existing node, but per requirements we 'extract new'
            return None

        logger.info(f"Novelty confirmed. Highest similarity to priors: {sim_score:.4f}")

        # 5. Node Generation
        new_node_id = f"skill_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            new_skill = SkillNode(
                id=new_node_id,
                name=skill_name,
                prototype=prototype_vector,
                metadata={
                    "source": "few_shot_demonstration",
                    "sample_count": len(demonstrations)
                }
            )
        except Exception as e:
            logger.error(f"Failed to instantiate SkillNode: {e}")
            return None

        # 6. Integration (Cognitive Growth)
        self.knowledge_base.add_node(new_skill)
        
        return new_skill

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup the AGI Knowledge Base with 638 prior skills
    kb = KnowledgeBase(initial_size=638)
    
    # 2. Initialize the Learner
    learner = IncrementalFewShotLearner(knowledge_base=kb)
    
    # 3. Simulate a 'Craftsman' demonstrating a new technique (1-shot)
    # We create a vector that is somewhat noisy but distinct from the random priors
    new_weaving_pattern = np.random.normal(0.5, 0.1, VECTOR_DIMENSION) 
    
    try:
        print("-" * 50)
        print("Attempting to learn a new 1-shot skill...")
        node = learner.learn_new_skill([new_weaving_pattern], skill_name="Macro_Weaving")
        
        if node:
            print(f"SUCCESS: Created Node ID: {node.id}")
            print(f"Node Prototype Norm: {np.linalg.norm(node.prototype):.4f}")
        
        print("-" * 50)
        print("Attempting to learn an existing skill (noise from prior distribution)...")
        # This should fail novelty check as it looks like the prior random data
        duplicate_pattern = np.random.normal(0, 1, VECTOR_DIMENSION)
        node_dup = learner.learn_new_skill([duplicate_pattern], skill_name="Duplicate_Skill")
        
        if not node_dup:
            print("SUCCESS: System correctly identified duplicate/existing pattern.")
            
    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except Exception as e:
        print(f"Unexpected Error: {e}")