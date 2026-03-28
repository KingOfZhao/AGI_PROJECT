"""
Skill Module: Cross-Domain Concept Overlap Detection & Consolidation

This module implements a cognitive mechanism to detect conceptual overlaps
between disparate domains (e.g., Industrial Manufacturing, Software Engineering,
Cognitive Science) and consolidate them into a generalized AGI skill node.

The core algorithm relies on vector-based semantic similarity and structural
attribute mapping to validate if concepts like 'Tolerance' (Manufacturing)
can map to 'Error Rate' (Software) or 'Fuzzy Logic' (Cognitive Science).
"""

import logging
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Skill_Migration")


@dataclass
class DomainConcept:
    """
    Represents a concept node within a specific domain.
    
    Attributes:
        id: Unique identifier for the concept.
        name: Human-readable name (e.g., "Tolerance").
        domain: The source domain (e.g., "Industrial_Manufacturing").
        attributes: Key properties defining the concept (e.g., {"threshold": 0.05}).
        embedding: A simplified vector representation for similarity calculation.
    """
    id: str
    name: str
    domain: str
    attributes: Dict[str, Any]
    embedding: List[float]


@dataclass
class UnifiedSkillNode:
    """
    Represents a newly generated cross-domain skill node.
    """
    node_id: str
    unified_name: str
    source_concepts: List[str]
    generalized_attributes: Dict[str, Any]
    creation_timestamp: str
    validation_score: float


class ConceptOverlapDetector:
    """
    Handles the logic for comparing concepts across domains and validating overlaps.
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize the detector.
        
        Args:
            similarity_threshold: The minimum cosine similarity (0.0 to 1.0) 
                                 required to consider an overlap valid.
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        self.similarity_threshold = similarity_threshold
        logger.info(f"ConceptOverlapDetector initialized with threshold: {similarity_threshold}")

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec_a: First vector.
            vec_b: Second vector.
            
        Returns:
            Similarity score between -1 and 1.
            
        Raises:
            ValueError: If vectors are empty or lengths do not match.
        """
        if not vec_a or not vec_b:
            raise ValueError("Vectors cannot be empty")
        if len(vec_a) != len(vec_b):
            logger.warning(f"Vector length mismatch: {len(vec_a)} vs {len(vec_b)}")
            # In a real scenario, we might pad or project; here we return 0
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a ** 2 for a in vec_a) ** 0.5
        norm_b = sum(b ** 2 for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def detect_overlap(self, source: DomainConcept, target: DomainConcept) -> Tuple[bool, float]:
        """
        Detects if two concepts overlap based on semantic and structural similarity.
        
        Args:
            source: The source concept.
            target: The target concept to compare against.
            
        Returns:
            A tuple (is_overlap: bool, score: float).
        """
        try:
            # 1. Semantic Similarity (Vector comparison)
            sem_score = self._cosine_similarity(source.embedding, target.embedding)
            
            # 2. Structural Similarity (Attribute key overlap - simplified)
            src_keys = set(source.attributes.keys())
            tgt_keys = set(target.attributes.keys())
            if not src_keys or not tgt_keys:
                struct_score = 0.0
            else:
                intersection = len(src_keys.intersection(tgt_keys))
                union = len(src_keys.union(tgt_keys))
                struct_score = intersection / union if union > 0 else 0.0
            
            # Weighted aggregate score
            final_score = (sem_score * 0.7) + (struct_score * 0.3)
            
            logger.debug(f"Comparing {source.name} vs {target.name}: Sem={sem_score:.2f}, Struct={struct_score:.2f}, Final={final_score:.2f}")
            
            return (final_score >= self.similarity_threshold, final_score)
            
        except Exception as e:
            logger.error(f"Error detecting overlap between {source.id} and {target.id}: {e}")
            return (False, 0.0)


class SkillConsolidator:
    """
    Responsible for merging validated overlapping concepts into a new skill node.
    """
    
    def generate_skill_node(self, concepts: List[DomainConcept], validation_score: float) -> Optional[UnifiedSkillNode]:
        """
        Generates a new generalized skill node from a list of overlapping concepts.
        
        Args:
            concepts: List of concepts that have validated overlaps.
            validation_score: The average confidence score of the overlaps.
            
        Returns:
            A UnifiedSkillNode object or None if input is invalid.
        """
        if len(concepts) < 2:
            logger.warning("Consolidation requires at least 2 concepts.")
            return None

        try:
            # Create a composite ID based on hashes of source IDs
            source_ids = [c.id for c in concepts]
            hash_input = "".join(sorted(source_ids)).encode('utf-8')
            node_hash = hashlib.md5(hash_input).hexdigest()[:8]
            node_id = f"skill_cross_{node_hash}"
            
            # Generate a name
            domains = "+".join(set(c.domain.split('_')[0] for c in concepts))
            base_names = set(c.name for c in concepts)
            unified_name = f"Generic_{domains}_Concept"
            
            # Consolidate attributes (simple merge for demo)
            merged_attrs = {}
            for c in concepts:
                merged_attrs.update(c.attributes)
            merged_attrs["scope"] = "cross_domain"
            
            timestamp = datetime.utcnow().isoformat()
            
            new_node = UnifiedSkillNode(
                node_id=node_id,
                unified_name=unified_name,
                source_concepts=source_ids,
                generalized_attributes=merged_attrs,
                creation_timestamp=timestamp,
                validation_score=validation_score
            )
            
            logger.info(f"Successfully consolidated concepts into Node ID: {node_id}")
            return new_node
            
        except Exception as e:
            logger.error(f"Failed to generate skill node: {e}")
            return None


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define Input Data (Mock Data for Demonstration)
    # In production, these embeddings would come from a large language model
    concept_manufacturing = DomainConcept(
        id="ind_tol_001",
        name="Tolerance",
        domain="Industrial_Manufacturing",
        attributes={"limit": 0.05, "type": "dimensional", "impact": "quality"},
        # Simplified vector representing "allowance/limit"
        embedding=[0.8, 0.2, 0.1, 0.5] 
    )

    concept_software = DomainConcept(
        id="soft_err_102",
        name="Error_Rate",
        domain="Software_Engineering",
        attributes={"limit": 0.01, "type": "reliability", "impact": "uptime"},
        # Similar vector direction (allowance/limit) but slightly different
        embedding=[0.75, 0.25, 0.15, 0.55] 
    )

    concept_cognitive = DomainConcept(
        id="cog_fuzz_99",
        name="Fuzzy_Logic",
        domain="Cognitive_Science",
        attributes={"type": "logic", "membership_function": "gaussian"},
        # Dissimilar vector
        embedding=[0.1, 0.9, 0.8, 0.2] 
    )

    # 2. Initialize Components
    detector = ConceptOverlapDetector(similarity_threshold=0.7)
    consolidator = SkillConsolidator()

    # 3. Execute Validation
    candidates = [concept_software, concept_cognitive]
    validated_group = [concept_manufacturing]
    
    print("-" * 50)
    print(f"Starting Cross-Domain Migration Validation for: {concept_manufacturing.name}")
    
    migration_valid = False
    avg_score = 0.0

    for candidate in candidates:
        is_overlap, score = detector.detect_overlap(concept_manufacturing, candidate)
        print(f"Checking against {candidate.name} ({candidate.domain}): Score={score:.4f}")
        
        if is_overlap:
            validated_group.append(candidate)
            migration_valid = True
            avg_score += score

    # 4. Consolidation
    if migration_valid and len(validated_group) > 1:
        avg_score /= (len(validated_group) - 1)
        new_skill = consolidator.generate_skill_node(validated_group, avg_score)
        
        if new_skill:
            print("\n>>> SUCCESS: New Skill Node Generated <<<")
            print(json.dumps(asdict(new_skill), indent=2))
    else:
        print("\n>>> FAILURE: No sufficient conceptual overlap found. <<<")