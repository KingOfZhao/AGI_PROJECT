"""
Module: auto_skill_aggregation.py

This module implements a sophisticated algorithm for Bottom-Up Inductive Construction
of Meta-Skills. It addresses the problem of 'Skill Fragmentation' by automatically
clustering similar skill nodes into generalized 'Meta-Skills'.

In an AGI system with thousands of skills (e.g., 1761 skills), many are merely
variations of a core capability (e.g., 'open_chrome', 'open_firefox', 'open_safari'
-> 'open_browser'). This module identifies these relationships using semantic
embeddings and density-based clustering, raising the system's abstraction level.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

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
    Represents a primitive skill node in the AGI system graph.
    
    Attributes:
        id: Unique identifier of the skill.
        description: Natural language description of the skill functionality.
        embedding: Vector representation of the description (Semantic projection).
        usage_count: Statistical frequency of skill usage (for weighting).
    """
    id: str
    description: str
    embedding: Optional[np.ndarray] = None
    usage_count: int = 0

    def __post_init__(self):
        """Validate data types after initialization."""
        if not isinstance(self.id, str) or not isinstance(self.description, str):
            raise ValueError("Skill ID and Description must be strings.")
        if self.embedding is not None and not isinstance(self.embedding, np.ndarray):
            raise TypeError("Embedding must be a numpy ndarray.")


@dataclass
class MetaSkill:
    """
    Represents an aggregated, higher-level skill abstraction.
    """
    id: str
    name: str
    component_skill_ids: List[str]
    centroid_description: str
    cohesion_score: float = 0.0


class SkillAggregationError(Exception):
    """Custom exception for errors during skill aggregation."""
    pass


# --- Core Functions ---

def validate_and_prepare_matrix(skill_nodes: List[SkillNode]) -> Tuple[np.ndarray, List[str]]:
    """
    Helper function: Validates input skills and prepares the embedding matrix.
    
    Args:
        skill_nodes: List of SkillNode objects.
        
    Returns:
        A tuple containing the embedding matrix (N x D) and a list of valid IDs.
        
    Raises:
        SkillAggregationError: If inputs are invalid or embeddings are missing.
    """
    if not skill_nodes:
        raise SkillAggregationError("Input skill list cannot be empty.")
    
    logger.info(f"Validating {len(skill_nodes)} skill nodes...")
    
    valid_nodes = []
    for i, skill in enumerate(skill_nodes):
        if skill.embedding is None:
            logger.warning(f"Skill {skill.id} missing embedding. Skipping.")
            continue
        if skill.embedding.ndim != 1:
             raise SkillAggregationError(f"Skill {skill.id} has invalid embedding dimensions.")
        valid_nodes.append(skill)
    
    if not valid_nodes:
        raise SkillAggregationError("No valid skills with embeddings found.")

    # Stack embeddings into matrix
    embeddings = np.vstack([s.embedding for s in valid_nodes])
    ids = [s.id for s in valid_nodes]
    
    # Data normalization check
    norms = np.linalg.norm(embeddings, axis=1)
    if np.any(norms == 0):
        raise ValueError("Zero-vector embeddings detected, which causes division by zero in cosine similarity.")

    return embeddings, ids


def detect_skill_clusters(
    skill_nodes: List[SkillNode],
    eps: float = 0.15,
    min_samples: int = 2,
    metric: str = "cosine"
) -> Dict[int, List[str]]:
    """
    Core Function 1: Detects clusters of fragmented skills based on semantic similarity.
    
    Uses DBSCAN (Density-Based Spatial Clustering of Applications with Noise) to 
    group skills that are semantically close. Unlike K-Means, DBSCAN does not 
    require specifying the number of clusters upfront and can identify noise.
    
    Args:
        skill_nodes: List of SkillNode objects containing embeddings.
        eps: The maximum distance between two samples for one to be considered 
             as in the neighborhood of the other. For cosine distance, 0.15 is a 
             typical starting point for high similarity.
        min_samples: The number of samples in a neighborhood for a point to be 
                     considered as a core point.
        metric: The metric to use for distance calculation. 'cosine' is recommended.

    Returns:
        A dictionary mapping cluster labels to lists of Skill IDs.
        Label -1 represents noise (unique skills that don't cluster well).
        
    Example:
        >>> clusters = detect_skill_clusters(skills, eps=0.2)
        >>> print(clusters)
        {0: ['skill_open_chrome', 'skill_open_firefox'], 1: ['skill_type_text', 'skill_input_text']}
    """
    try:
        embeddings, ids = validate_and_prepare_matrix(skill_nodes)
    except SkillAggregationError as e:
        logger.error(f"Preparation failed: {e}")
        return {}

    logger.info(f"Starting clustering on {embeddings.shape[0]} samples with eps={eps}...")
    
    # DBSCAN with cosine distance (1 - cosine similarity)
    db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
    labels = db.fit_predict(embeddings)
    
    # Group skills by cluster label
    clusters: Dict[int, List[str]] = {}
    unique_labels = set(labels)
    
    for label in unique_labels:
        if label == -1:
            # Noise points are not aggregated in this step
            continue
        
        indices = np.where(labels == label)[0]
        cluster_ids = [ids[i] for i in indices]
        clusters[label] = cluster_ids
        
    logger.info(f"Found {len(clusters)} potential meta-skill clusters.")
    return clusters


def build_meta_skills(
    skill_nodes: List[SkillNode],
    clusters: Dict[int, List[str]]
) -> List[MetaSkill]:
    """
    Core Function 2: Constructs Meta-Skill objects from detected clusters.
    
    This function calculates the "Concept Centroid" for each cluster to generate
    a representative description and calculates a cohesion score to ensure quality.
    
    Args:
        skill_nodes: The original list of skills.
        clusters: The output from `detect_skill_clusters`.
        
    Returns:
        A list of validated MetaSkill objects.
    """
    meta_skills: List[MetaSkill] = []
    
    # Create lookup dictionary for speed
    skill_map = {s.id: s for s in skill_nodes}
    
    logger.info("Constructing meta-skill nodes...")
    
    for cluster_id, skill_ids in clusters.items():
        if len(skill_ids) < 2:
            continue # Should be filtered by DBSCAN min_samples, but double check
            
        # Retrieve constituent skills
        constituents = [skill_map[uid] for uid in skill_ids if uid in skill_map]
        if not constituents:
            continue
            
        # Calculate Cluster Centroid (Average Embedding)
        constituent_embeddings = np.vstack([s.embedding for s in constituents])
        centroid = np.mean(constituent_embeddings, axis=0)
        
        # Calculate Cohesion Score (Average pairwise cosine similarity within cluster)
        # Note: High cohesion means skills are very similar
        sim_matrix = cosine_similarity(constituent_embeddings)
        # Extract upper triangle without diagonal
        upper_tri_indices = np.triu_indices_from(sim_matrix, k=1)
        cohesion = np.mean(sim_matrix[upper_tri_indices])
        
        # Naming Heuristic (Simple): 
        # Find the shortest description (often the most abstract) or common tokens.
        # For this demo, we use the description of the most used skill.
        most_used_skill = max(constituents, key=lambda x: x.usage_count)
        
        meta_id = f"meta_skill_{cluster_id}"
        
        meta = MetaSkill(
            id=meta_id,
            name=f"Aggregated Capability {cluster_id}",
            component_skill_ids=skill_ids,
            centroid_description=most_used_skill.description, # In real AGI, use LLM to summarize
            cohesion_score=float(cohesion)
        )
        meta_skills.append(meta)
        
    logger.info(f"Successfully constructed {len(meta_skills)} meta-skills.")
    return meta_skills


# --- Example Usage and Demonstration ---

def generate_mock_embeddings(text: str, dim: int = 128) -> np.ndarray:
    """
    Helper: Generates deterministic random vectors for demonstration.
    Real implementation would use OpenAI embeddings or SentenceTransformers.
    """
    np.random.seed(hash(text) % (2**32))
    return np.random.rand(dim)

def main():
    """
    Usage Example:
    Demonstrates the flow from raw fragmented skills to aggregated meta-skills.
    """
    print("--- Starting Auto Skill Aggregation Process ---")
    
    # 1. Define Fragmented Skills (Simulating a subset of 1761 skills)
    # Group 1: Browser related
    # Group 2: File I/O related
    # Group 3: Unrelated (Noise)
    raw_skills_data = [
        SkillNode("s1", "Open Google Chrome browser", generate_mock_embeddings("browser")),
        SkillNode("s2", "Open Firefox browser", generate_mock_embeddings("browser")),
        SkillNode("s3", "Launch Safari web browser", generate_mock_embeddings("browser")),
        
        SkillNode("s4", "Read text file from disk", generate_mock_embeddings("file io")),
        SkillNode("s5", "Write data to CSV file", generate_mock_embeddings("file io")),
        SkillNode("s6", "Save log file locally", generate_mock_embeddings("file io")),
        
        SkillNode("s7", "Play jazz music", generate_mock_embeddings("music audio")),
        SkillNode("s8", "Calculate fibonacci sequence", generate_mock_embeddings("math recursive")),
    ]
    
    # Add slight noise to embeddings to simulate real variance
    for s in raw_skills_data:
        s.embedding += np.random.normal(0, 0.05, s.embedding.shape)

    # 2. Detect Clusters
    # eps=0.5 allows for slightly looser clustering due to noise added above
    clusters = detect_skill_clusters(raw_skills_data, eps=0.5, min_samples=2)
    
    # 3. Build Meta Skills
    meta_skills = build_meta_skills(raw_skills_data, clusters)
    
    # 4. Output Results
    print(f"\n--- Aggregation Report ---")
    print(f"Total Primitive Skills: {len(raw_skills_data)}")
    print(f"Identified Meta Skills: {len(meta_skills)}")
    
    for ms in meta_skills:
        print(f"\nMeta-Skill ID: {ms.id}")
        print(f"  Cohesion Score: {ms.cohesion_score:.4f}")
        print(f"  Representative Desc: {ms.centroid_description}")
        print(f"  Merged Skills ({len(ms.component_skill_ids)}): {ms.component_skill_ids}")

if __name__ == "__main__":
    main()