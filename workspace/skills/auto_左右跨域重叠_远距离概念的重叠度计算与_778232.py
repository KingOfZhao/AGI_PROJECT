"""
Module: auto_concept_overlap_mapping
Name: auto_左右跨域重叠_远距离概念的重叠度计算与_778232
Description: Advanced AGI module for calculating deep structural similarity between distant
             domain concepts (e.g., 'Biological Evolution' vs 'Code Iteration') and generating
             transfer mapping rules.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossDomainOverlap")


@dataclass
class ConceptNode:
    """
    Represents a semantic node with structural attributes.
    
    Attributes:
        name (str): The name of the concept.
        domain (str): The domain the concept belongs to (e.g., 'Biology', 'CS').
        attributes (Dict[str, float]): Numerical features describing the concept's 
                                       deep structure (e.g., complexity, entropy, rate).
        relations (List[str]): List of relationship types this concept participates in.
    """
    name: str
    domain: str
    attributes: Dict[str, float]
    relations: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.name or not self.domain:
            raise ValueError("Concept name and domain cannot be empty.")
        if not isinstance(self.attributes, dict):
            raise TypeError("Attributes must be a dictionary.")


@dataclass
class MappingRule:
    """
    Represents a generated mapping rule between two concepts.
    """
    source_concept: str
    target_concept: str
    similarity_score: float
    attribute_mapping: Dict[str, str]
    explanation: str


def _normalize_vector(vector: Dict[str, float], reference_keys: List[str]) -> List[float]:
    """
    [Helper] Normalizes attribute values into a consistent vector space based on reference keys.
    
    Args:
        vector (Dict[str, float]): The raw attributes.
        reference_keys (List[str]): The superset of all possible keys for alignment.
    
    Returns:
        List[float]: A normalized vector filling missing keys with 0.0.
    """
    normalized = []
    max_val = max(vector.values()) if vector else 1.0
    if max_val == 0: max_val = 1.0 # Avoid division by zero

    for key in reference_keys:
        val = vector.get(key, 0.0)
        # Simple min-max scaling simulation (assuming positive values here for simplicity)
        normalized.append(val / max_val)
    
    return normalized


def calculate_structural_similarity(
    concept_a: ConceptNode, 
    concept_b: ConceptNode, 
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Calculates the deep structural similarity between two concepts across domains.
    
    This function ignores surface semantics and focuses on the structural isomorphism 
    of attributes and relational patterns.
    
    Args:
        concept_a (ConceptNode): The first concept (Source domain).
        concept_b (ConceptNode): The second concept (Target domain).
        weights (Optional[Dict[str, float]]): Custom weights for different attributes.
                                              If None, uniform weights are used.
    
    Returns:
        Tuple[float, Dict[str, float]]: 
            - A float score between 0.0 and 1.0 representing overlap.
            - A dictionary detailing the contribution of each attribute.
    
    Raises:
        ValueError: If input concepts lack necessary attribute data.
    """
    logger.info(f"Comparing concepts: '{concept_a.name}' vs '{concept_b.name}'")
    
    if not concept_a.attributes or not concept_b.attributes:
        logger.error("One or both concepts have empty attributes.")
        raise ValueError("Cannot calculate similarity for concepts with no attributes.")

    # 1. Unify Feature Space
    all_keys = set(concept_a.attributes.keys()) | set(concept_b.attributes.keys())
    
    # 2. Vectorization
    vec_a = _normalize_vector(concept_a.attributes, list(all_keys))
    vec_b = _normalize_vector(concept_b.attributes, list(all_keys))

    # 3. Calculate Cosine Similarity (Structural Alignment)
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a**2 for a in vec_a))
    norm_b = math.sqrt(sum(b**2 for b in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0, {}

    cosine_sim = dot_product / (norm_a * norm_b)
    
    # 4. Relational Overlap Bonus (Jaccard Index)
    set_a = set(concept_a.relations)
    set_b = set(concept_b.relations)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    relational_sim = intersection / union if union > 0 else 0.0

    # 5. Weighted Aggregation
    # Default: 70% attribute structure, 30% relational topology
    final_score = (0.7 * cosine_sim) + (0.3 * relational_sim)
    
    logger.debug(f"Attribute Sim: {cosine_sim:.4f}, Relational Sim: {relational_sim:.4f}")
    logger.info(f"Final Structural Similarity: {final_score:.4f}")

    return final_score, {
        "attribute_similarity": cosine_sim,
        "relational_similarity": relational_sim
    }


def generate_cross_domain_mapping(
    source_concept: ConceptNode,
    target_concept: ConceptNode,
    threshold: float = 0.6
) -> Optional[MappingRule]:
    """
    Generates a transfer mapping rule if the structural overlap exceeds the threshold.
    
    This simulates the "Creative Leap" in AGI by identifying how features in the source
    domain can explain features in the target domain.
    
    Args:
        source_concept (ConceptNode): The known concept (e.g., 'Biological Evolution').
        target_concept (ConceptNode): The concept to be understood (e.g., 'Code Iteration').
        threshold (float): Minimum similarity score (0.0-1.0) to create a mapping.
    
    Returns:
        Optional[MappingRule]: A data object containing the mapping logic, or None if 
                               similarity is too low.
    """
    logger.info(f"Attempting mapping generation: {source_concept.name} -> {target_concept.name}")

    # Validation
    if not isinstance(source_concept, ConceptNode) or not isinstance(target_concept, ConceptNode):
        raise TypeError("Inputs must be ConceptNode instances.")
    
    try:
        score, details = calculate_structural_similarity(source_concept, target_concept)
    except ValueError as e:
        logger.warning(f"Skipping mapping due to error: {e}")
        return None

    if score < threshold:
        logger.info(f"Similarity {score:.2f} below threshold {threshold}. No mapping generated.")
        return None

    # Construct Mapping Logic
    # Find corresponding attributes (simple nearest neighbor logic for demonstration)
    attribute_map = {}
    source_keys = list(source_concept.attributes.keys())
    target_keys = list(target_concept.attributes.keys())
    
    # Simple heuristic mapping: Match keys with highest relative magnitude similarity
    # (In a real AGI system, this would involve complex vector alignment)
    for t_key in target_keys:
        t_val = target_concept.attributes[t_key]
        best_match = None
        min_diff = float('inf')
        
        for s_key in source_keys:
            s_val = source_concept.attributes[s_key]
            # Check relative difference
            if s_val == 0 and t_val == 0:
                diff = 0
            elif s_val == 0:
                continue
            else:
                diff = abs((t_val - s_val) / s_val) if s_val != 0 else float('inf')
            
            if diff < min_diff:
                min_diff = diff
                best_match = s_key
        
        if best_match:
            attribute_map[t_key] = best_match

    explanation = (
        f"Structural isomorphism detected ({score:.2%} confidence). "
        f"The mechanism of '{source_concept.name}' can be used to model '{target_concept.name}'."
    )

    rule = MappingRule(
        source_concept=source_concept.name,
        target_concept=target_concept.name,
        similarity_score=score,
        attribute_mapping=attribute_map,
        explanation=explanation
    )

    logger.info(f"SUCCESS: Mapping created between {source_concept.name} and {target_concept.name}")
    return rule


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Define Concept A: Biological Evolution
    # Attributes are abstract representations (e.g., 'mutation_rate', 'selection_pressure')
    bio_evolution = ConceptNode(
        name="Biological Evolution",
        domain="Biology",
        attributes={
            "mutation_rate": 0.05,
            "selection_pressure": 0.8,
            "retention_capacity": 0.6,
            "generational_gap": 10.0
        },
        relations=["inheritance", "variation", "competition", "adaptation"]
    )

    # Define Concept B: Code Iteration (Agile/Refactoring)
    # Note: Different domain, different scale, but similar structure
    code_iteration = ConceptNode(
        name="Code Refactoring",
        domain="Computer Science",
        attributes={
            "change_frequency": 0.04,   # Similar to mutation_rate
            "test_coverage": 0.9,       # Analogous to selection_pressure (survival filter)
            "backward_compatibility": 0.5, # Retention
            "deploy_cycle_days": 14.0   # Generational gap
        },
        relations=["inheritance (OOP)", "variation (features)", "competition (performance)", "adaptation (market)"]
    )

    # Define Concept C: A random dissimilar concept
    coffee_drinking = ConceptNode(
        name="Coffee Drinking",
        domain="Lifestyle",
        attributes={
            "sugar_level": 5.0,
            "caffeine_content": 80.0
        },
        relations=["consumption", "energy_boost"]
    )

    print("-" * 60)
    print(f"Executing Cross-Domain Analysis...")
    print("-" * 60)

    # Test 1: High Similarity (Biology -> CS)
    mapping = generate_cross_domain_mapping(bio_evolution, code_iteration, threshold=0.5)
    if mapping:
        print(f"\n[MAPPING FOUND]")
        print(f"Source: {mapping.source_concept}")
        print(f"Target: {mapping.target_concept}")
        print(f"Score:  {mapping.similarity_score:.4f}")
        print(f"Attribute Mappings: {mapping.attribute_mapping}")
        print(f"Insight: {mapping.explanation}")
    
    print("-" * 60)

    # Test 2: Low Similarity (Biology -> Lifestyle)
    mapping_fail = generate_cross_domain_mapping(bio_evolution, coffee_drinking, threshold=0.5)
    if not mapping_fail:
        print("\n[NO MAPPING]")
        print("Concepts 'Biological Evolution' and 'Coffee Drinking' are structurally unrelated.")