"""
Meta-Skill Extractor Module for AGI Cognitive Architecture.

This module implements a bottom-up hierarchical clustering approach to analyze
a large corpus of specific skill nodes (e.g., 'Python Crawler', 'Excel Pivot Table')
and inductively constructs higher-level abstract meta-skills (e.g., 'Data Cleaning',
'Structured Thinking').

It utilizes NLP embedding techniques to vectorize skill descriptions and
agglomerative clustering to group them into a skill tree.

Author: AGI System
Version: 1.0.0
Domain: machine_learning
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# Attempt to import standard data science libraries.
# In a production environment, ensure these are installed.
try:
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_similarity
    LIBRARIES_AVAILABLE = True
except ImportError:
    LIBRARIES_AVAILABLE = False
    # Mock classes for demonstration if libraries are missing
    np = None
    AgglomerativeClustering = None
    cosine_similarity = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# --- Data Structures ---

@dataclass
class SkillNode:
    """Represents a single node in the skill graph."""
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the node, excluding the embedding for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags
        }


@dataclass
class MetaSkill:
    """Represents an induced higher-level skill."""
    id: str
    name: str  # Generated name based on common keywords
    level: int
    child_ids: List[str]
    keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "child_ids": self.child_ids,
            "keywords": self.keywords
        }


class MetaSkillExtractor:
    """
    Extracts meta-skills from a collection of specific skill nodes using
    hierarchical agglomerative clustering.
    """

    def __init__(self, distance_threshold: float = 0.35, min_cluster_size: int = 2):
        """
        Initializes the extractor.

        Args:
            distance_threshold (float): The linkage distance threshold for clustering.
                                        Lower values result in tighter clusters.
            min_cluster_size (int): Minimum number of nodes to form a meta-skill.
        """
        if not LIBRARIES_AVAILABLE:
            logger.warning(
                "Critical libraries (numpy, sklearn) not found. "
                "Running in simulation/mock mode."
            )
        
        self.distance_threshold = distance_threshold
        self.min_cluster_size = min_cluster_size
        self._skill_corpus: List[SkillNode] = []

    def _validate_input_data(self, raw_data: List[Dict[str, Any]]) -> List[SkillNode]:
        """
        Validates and converts raw dictionary data into SkillNode objects.

        Args:
            raw_data: List of dictionaries containing skill info.

        Returns:
            List of validated SkillNode objects.
        
        Raises:
            ValueError: If data format is invalid.
        """
        if not isinstance(raw_data, list):
            raise ValueError("Input data must be a list of dictionaries.")
        
        validated_nodes = []
        for idx, item in enumerate(raw_data):
            if not isinstance(item, dict):
                logger.error(f"Item at index {idx} is not a dictionary. Skipping.")
                continue
            
            node_id = item.get('id', f"gen_id_{idx}")
            name = item.get('name')
            desc = item.get('description', '')

            if not name:
                logger.warning(f"Node {node_id} missing 'name'. Skipping.")
                continue

            # Basic sanitization
            name = str(name).strip()
            desc = str(desc).strip()

            node = SkillNode(
                id=str(node_id),
                name=name,
                description=desc,
                tags=item.get('tags', [])
            )
            validated_nodes.append(node)
        
        logger.info(f"Validated {len(validated_nodes)} skill nodes from input.")
        return validated_nodes

    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Helper function to generate vector embeddings for text.
        In a real AGI system, this would call an Embedding Model (e.g., BERT, OpenAI Ada).
        
        For this code context, we use a deterministic mock vector based on character codes
        to ensure the code runs anywhere, while maintaining the logic structure.
        """
        if not LIBRARIES_AVAILABLE:
            # Return a mock numpy array
            return np.random.rand(128) # type: ignore

        # NOTE: Replace this block with actual model inference in production.
        # Example logic: Simple character frequency vector (normalized)
        # This is purely for demonstration of the pipeline logic.
        vec = np.zeros(128) # type: ignore
        for char in text.lower():
            if char.isalpha():
                vec[ord(char) % 128] += 1
        
        norm = np.linalg.norm(vec) # type: ignore
        if norm == 0:
            return vec
        return vec / norm

    def _extract_keywords_from_cluster(self, nodes: List[SkillNode]) -> List[str]:
        """
        Analyzes a cluster of nodes to find common significant keywords
        to name the Meta-Skill.
        """
        word_freq: Dict[str, int] = {}
        stop_words = {"the", "a", "in", "of", "and", "to", "for", "with", "on", "using"}
        
        for node in nodes:
            # Combine name and description for analysis
            text = f"{node.name} {node.description}".lower()
            # Simple tokenization
            words = re.findall(r'\b[a-z]{4,}\b', text) # Words with 4+ letters
            
            for word in words:
                if word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 keywords
        return [w[0] for w in sorted_words[:3]]

    def fit_predict(self, raw_skills: List[Dict[str, Any]]) -> Tuple[List[MetaSkill], List[SkillNode]]:
        """
        Main execution pipeline. Processes raw skills, clusters them, and
        generates Meta-Skills.

        Args:
            raw_skills: List of raw skill dictionaries.

        Returns:
            A tuple containing (List of generated MetaSkills, List of processed SkillNodes).
        """
        logger.info("Starting Meta-Skill Extraction pipeline...")
        
        # 1. Validation
        self._skill_corpus = self._validate_input_data(raw_skills)
        if len(self._skill_corpus) < self.min_cluster_size:
            logger.warning("Not enough skills to perform clustering.")
            return [], self._skill_corpus

        # 2. Vectorization
        logger.info("Vectorizing skill descriptions...")
        embeddings = []
        for node in self._skill_corpus:
            emb = self._generate_embedding(f"{node.name} {node.description}")
            node.embedding = emb # type: ignore
            embeddings.append(emb)
        
        # Stack into matrix (N, D)
        try:
            X = np.vstack(embeddings) # type: ignore
        except Exception as e:
            logger.error(f"Failed to stack embeddings: {e}")
            return [], self._skill_corpus

        # 3. Hierarchical Clustering
        # We use cosine affinity and average linkage for semantic grouping
        logger.info(f"Performing Agglomerative Clustering (threshold={self.distance_threshold})...")
        
        if LIBRARIES_AVAILABLE:
            clustering_model = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=self.distance_threshold,
                metric='cosine',
                linkage='average'
            )
            labels = clustering_model.fit_predict(X)
        else:
            # Mock labels for demo
            labels = np.random.randint(0, 5, size=len(self._skill_corpus)) # type: ignore

        # 4. Inductive Construction (Grouping)
        clusters: Dict[int, List[SkillNode]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(self._skill_corpus[idx])

        # 5. Meta-Skill Generation
        meta_skills: List[MetaSkill] = []
        meta_id_counter = 0

        for cluster_id, nodes in clusters.items():
            if len(nodes) < self.min_cluster_size:
                continue # Treat as noise or isolated skill
            
            keywords = self._extract_keywords_from_cluster(nodes)
            meta_name = " / ".join(keywords[:2]).title() if keywords else f"Meta Cluster {cluster_id}"
            
            meta_skill = MetaSkill(
                id=f"meta_{cluster_id}_{meta_id_counter}",
                name=meta_name,
                level=1, # 1 level above base skills
                child_ids=[n.id for n in nodes],
                keywords=keywords
            )
            meta_skills.append(meta_skill)
            meta_id_counter += 1

        logger.info(f"Extraction complete. Discovered {len(meta_skills)} Meta-Skills.")
        return meta_skills, self._skill_corpus


# --- Usage Example ---

if __name__ == "__main__":
    # Mock Data representing the 1693 nodes
    mock_skill_data = [
        {"id": "s1", "name": "Python Pandas", "description": "Data manipulation library for Python"},
        {"id": "s2", "name": "Python Numpy", "description": "Numerical computing in Python"},
        {"id": "s3", "name": "Excel Pivot Tables", "description": "Data summarization tool in Excel"},
        {"id": "s4", "name": "VLOOKUP Excel", "description": "Data retrieval function in Excel"},
        {"id": "s5", "name": "Creative Writing", "description": "Writing fiction and stories"},
        {"id": "s6", "name": "Copywriting", "description": "Writing text for advertising"},
        {"id": "s7", "name": "Data Cleaning", "description": "Fixing dirty data in Python"},
    ]

    # Initialize Extractor
    extractor = MetaSkillExtractor(distance_threshold=0.6, min_cluster_size=2)

    # Run Extraction
    try:
        discovered_meta_skills, processed_nodes = extractor.fit_predict(mock_skill_data)

        print("\n=== Discovered Meta-Skills ===")
        for ms in discovered_meta_skills:
            print(f"ID: {ms.id}")
            print(f"Name: {ms.name}")
            print(f"Keywords: {ms.keywords}")
            print(f"Children: {ms.child_ids}")
            print("-" * 30)
            
    except ValueError as ve:
        logger.error(f"Input Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)