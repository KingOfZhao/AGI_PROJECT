"""
Module: structural_isomorphism_engine
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
Description: 【左右跨域】量化两个看似无关领域节点的'结构同构性'。
             This module provides a mechanism to quantify the structural similarity
             (isomorphism) between concepts from disparate domains (e.g., Biology vs. Software Engineering).
             It enables the discovery of innovative cross-domain analogies by comparing
             topological and attribute-based features rather than semantic keywords.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StructuralIsomorphismEngine")

# 2. Data Structures

class NodeType(Enum):
    """Enumeration of possible node types in a knowledge graph."""
    ENTITY = 1
    PROCESS = 2
    PRINCIPLE = 3
    STRUCTURE = 4

@dataclass
class KnowledgeNode:
    """
    Represents a concept node in a specific domain.
    
    Attributes:
        id: Unique identifier.
        name: Human-readable name (e.g., 'Natural Selection').
        domain: The domain of the concept (e.g., 'Biology').
        node_type: The classification of the concept (Entity, Process, etc.).
        attributes: A normalized vector (dict) representing abstract features.
                    Keys represent feature dimensions (e.g., 'complexity', 'entropy_rate'),
                    Values are floats typically between 0.0 and 1.0.
        connections: List of IDs of connected nodes (structural context).
    """
    id: str
    name: str
    domain: str
    node_type: NodeType
    attributes: Dict[str, float] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id or not self.name:
            raise ValueError("Node ID and Name cannot be empty.")
        if not isinstance(self.node_type, NodeType):
            raise TypeError("node_type must be an instance of NodeType Enum.")

@dataclass
class IsomorphismResult:
    """
    Result container for the isomorphism calculation.
    """
    node_a_id: str
    node_b_id: str
    similarity_score: float
    feature_alignment: Dict[str, float]
    type_match: bool
    details: str

# 3. Helper Functions

def _validate_attributes(attrs: Dict[str, float]) -> bool:
    """
    Validates that attribute values are numeric and within reasonable bounds.
    
    Args:
        attrs: Dictionary of attributes.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(attrs, dict):
        return False
    for k, v in attrs.items():
        if not isinstance(v, (int, float)):
            logger.error(f"Invalid attribute type for key '{k}': {type(v)}")
            return False
        # Soft check for normalization (warning only)
        if v < 0 or v > 1.5: # Allowing slight margin > 1.0
            logger.warning(f"Attribute '{k}' value {v} is outside standard normalized range [0, 1].")
    return True

def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """
    Computes cosine similarity between two sparse vectors represented as dictionaries.
    
    Args:
        vec_a: First vector.
        vec_b: Second vector.
        
    Returns:
        float: Cosine similarity score between 0.0 and 1.0.
    """
    intersection = set(vec_a.keys()) & set(vec_b.keys())
    
    # If no common dimensions, similarity is undefined/0
    if not intersection:
        return 0.0
    
    numerator = sum(vec_a[k] * vec_b[k] for k in intersection)
    
    norm_a = math.sqrt(sum(v**2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v**2 for v in vec_b.values()))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return numerator / (norm_a * norm_b)

# 4. Core Functions

def map_to_abstract_space(node: KnowledgeNode) -> Dict[str, float]:
    """
    [Core Function 1]
    Transforms a concrete domain node into a generalized abstract feature space.
    This acts as the 'translation' layer where 'DNA' and 'Source Code' map to similar
    abstract concepts like 'Information Carrier' or 'Blueprint'.
    
    Args:
        node: The concrete knowledge node.
        
    Returns:
        Dict[str, float]: A vector in the abstract feature space.
    """
    logger.debug(f"Mapping node '{node.name}' to abstract space...")
    
    # Base abstract features derived from attributes
    abstract_vector = node.attributes.copy()
    
    # Structural complexity inference (example logic)
    # If the node has many connections, it implies high centrality or complexity
    connectivity_factor = min(1.0, len(node.connections) / 10.0)
    abstract_vector['structural_connectivity'] = connectivity_factor
    
    # Type-based abstract mapping
    type_mappings = {
        NodeType.ENTITY: {"concreteness": 0.9, "dynamic": 0.2},
        NodeType.PROCESS: {"concreteness": 0.3, "dynamic": 0.9},
        NodeType.PRINCIPLE: {"concreteness": 0.1, "dynamic": 0.1},
        NodeType.STRUCTURE: {"concreteness": 0.8, "dynamic": 0.3}
    }
    
    if node.node_type in type_mappings:
        for key, val in type_mappings[node.node_type].items():
            # Weighted average if attribute already exists
            if key in abstract_vector:
                abstract_vector[key] = (abstract_vector[key] + val) / 2
            else:
                abstract_vector[key] = val
                
    return abstract_vector

def calculate_structural_isomorphism(
    node_a: KnowledgeNode, 
    node_b: KnowledgeNode, 
    weights: Optional[Dict[str, float]] = None
) -> IsomorphismResult:
    """
    [Core Function 2]
    Calculates the 'Structural Isomorphism' score between two nodes from potentially
    different domains.
    
    Logic:
    1. Validate inputs.
    2. Check for Type Compatibility (Hard constraint or High weight).
    3. Map both nodes to Abstract Feature Space.
    4. Calculate Cosine Similarity in Abstract Space.
    5. Adjust score based on structural patterns (e.g., hierarchy depth if available).
    
    Args:
        node_a: First node (e.g., from Biology).
        node_b: Second node (e.g., from Software Engineering).
        weights: Optional weights for different feature categories.
        
    Returns:
        IsomorphismResult: Object containing score and analysis.
    """
    
    # 1. Validation
    if not isinstance(node_a, KnowledgeNode) or not isinstance(node_b, KnowledgeNode):
        logger.error("Invalid input types provided.")
        raise TypeError("Inputs must be KnowledgeNode instances.")
        
    logger.info(f"Calculating Isomorphism: '{node_a.name}' <-> '{node_b.name}'")
    
    # 2. Type Matching Check
    # In structuralism, comparing an Entity to a Process is rarely isomorphic
    type_match = (node_a.node_type == node_b.node_type)
    type_score = 1.0 if type_match else 0.2 # Severe penalty for type mismatch
    
    # 3. Abstract Mapping
    vec_a = map_to_abstract_space(node_a)
    vec_b = map_to_abstract_space(node_b)
    
    # 4. Feature Similarity Calculation
    # Use Cosine Similarity for directional alignment
    feature_sim = _cosine_similarity(vec_a, vec_b)
    
    # 5. Structural Pattern Matching (Simplified)
    # Compare connectivity density
    conn_a = len(node_a.connections)
    conn_b = len(node_b.connections)
    diff = abs(conn_a - conn_b)
    structural_sim = 1.0 / (1.0 + diff) # Inverse distance
    
    # 6. Aggregation
    # Final Score Formula: Weighted combination
    # If domains are different, we value the structural similarity higher
    domain_penalty = 0.0 if node_a.domain != node_b.domain else -0.2 # Slight penalty for same domain (seeking cross-pollination)
    
    w_feature = 0.6
    w_struct = 0.2
    w_type = 0.2
    
    final_score = (
        (w_feature * feature_sim) + 
        (w_struct * structural_sim) + 
        (w_type * type_score) + 
        domain_penalty
    )
    
    # Clamp score between 0 and 1
    final_score = max(0.0, min(1.0, final_score))
    
    # Determine alignment details
    common_features = set(vec_a.keys()) & set(vec_b.keys())
    alignment = {k: abs(vec_a[k] - vec_b[k]) for k in common_features}
    
    details = f"Type Match: {type_match}. Feature Sim: {feature_sim:.2f}. Structure Sim: {structural_sim:.2f}."
    
    return IsomorphismResult(
        node_a_id=node_a.id,
        node_b_id=node_b.id,
        similarity_score=final_score,
        feature_alignment=alignment,
        type_match=type_match,
        details=details
    )

# 5. Main Execution / Usage Example

if __name__ == "__main__":
    # Example Usage: Comparing 'Natural Selection' with 'Genetic Algorithm'
    
    # Node A: Biology Domain
    natural_selection = KnowledgeNode(
        id="bio_001",
        name="Natural Selection",
        domain="Biology",
        node_type=NodeType.PROCESS,
        attributes={
            "adaptation_rate": 0.8,
            "entropy_reduction": 0.9,
            "information_preservation": 0.7
        },
        connections=["bio_002", "bio_003", "bio_004", "bio_005"] # Connected to Mutation, Environment, etc.
    )
    
    # Node B: Computer Science Domain
    genetic_algorithm = KnowledgeNode(
        id="cs_101",
        name="Genetic Algorithm",
        domain="Computer Science",
        node_type=NodeType.PROCESS, # Both are processes
        attributes={
            "adaptation_rate": 0.7,
            "entropy_reduction": 0.8,
            "information_preservation": 0.9,
            "computational_cost": 0.6 # Unique attribute
        },
        connections=["cs_102", "cs_103"] # Fitness Function, Crossover
    )
    
    # Node C: Irrelevant Node (Entity vs Process)
    cat = KnowledgeNode(
        id="bio_999",
        name="Cat",
        domain="Biology",
        node_type=NodeType.ENTITY,
        attributes={"softness": 0.9},
        connections=[]
    )
    
    try:
        # Calculate Similarity
        result_1 = calculate_structural_isomorphism(natural_selection, genetic_algorithm)
        result_2 = calculate_structural_isomorphism(natural_selection, cat)
        
        print("-" * 50)
        print(f"Comparison A: {natural_selection.name} vs {genetic_algorithm.name}")
        print(f"Isomorphism Score: {result_1.similarity_score:.4f}")
        print(f"Details: {result_1.details}")
        print(f"Feature Alignment (Diff): {result_1.feature_alignment}")
        print("-" * 50)
        
        print(f"Comparison B: {natural_selection.name} vs {cat.name}")
        print(f"Isomorphism Score: {result_2.similarity_score:.4f}")
        print(f"Details: {result_2.details}")
        
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")