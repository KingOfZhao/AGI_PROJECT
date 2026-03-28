"""
Module: auto_cross_domain_abstraction_ladder.py

This module implements an 'Abstraction Ladder' Locator for Cross-Domain Transfer in AGI systems.
It addresses the 'Curse of Dimensionality' caused by mismatched abstraction levels during knowledge transfer.

Core Philosophy:
Knowledge transfer is most effective when the source and target domains align on a specific 
abstraction layer (e.g., transferring 'Natural Selection' to 'Genetic Algorithms' at the 
'Optimization Strategy' layer, rather than the 'Biological' or 'Bit-string' layers).

Key Components:
1. Hierarchical Knowledge Representation.
2. Semantic Similarity Calculator.
3. Optimal Transfer Level Locator.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AbstractionLadderLocator")


class AbstractionError(Exception):
    """Custom exception for abstraction hierarchy errors."""
    pass


class NodeSemantics(Enum):
    """Semantic types for nodes."""
    CONCRETE_INSTANCE = 1
    FUNCTIONAL_PROCESS = 2
    ABSTRACT_PRINCIPLE = 3
    MATHEMATICAL_AXIOM = 4


@dataclass
class KnowledgeNode:
    """
    Represents a node in the knowledge graph.
    
    Attributes:
        id: Unique identifier.
        label: Human-readable label.
        level: Abstraction level (0=Concrete, Higher=More Abstract).
        vector: Semantic vector representation (mocked dimensions for logic demo).
        domain: The domain this node belongs to (e.g., 'biology', 'cs').
    """
    id: str
    label: str
    level: int
    vector: List[float]
    domain: str
    semantics: NodeSemantics = NodeSemantics.CONCRETE_INSTANCE

    def __post_init__(self):
        if self.level < 0:
            raise ValueError("Abstraction level cannot be negative.")
        if not self.vector:
            raise ValueError("Semantic vector cannot be empty.")


@dataclass
class TransferResult:
    """
    Result of the abstraction transfer analysis.
    """
    optimal_level: int
    source_node: KnowledgeNode
    target_node: KnowledgeNode
    similarity_score: float
    transferability_index: float
    message: str


def _calculate_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    [Helper Function] Calculates cosine similarity between two vectors.
    Used to determine semantic closeness regardless of specific domain terms.
    
    Args:
        v1: Vector 1
        v2: Vector 2
        
    Returns:
        float: Similarity score between 0.0 and 1.0.
    """
    if len(v1) != len(v2):
        logger.error("Vector dimension mismatch in similarity calculation.")
        raise ValueError("Vectors must be of the same dimension")
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def project_node_to_level(node: KnowledgeNode, target_level: int, hierarchy_graph: Dict[str, List[str]]) -> KnowledgeNode:
    """
    [Core Function 1] Projects a concrete node up/down the abstraction ladder.
    
    In a real AGI system, this would query a knowledge graph (like ConceptNet or an internal 
    Knowledge Graph) to find the parent or child concept at the target level.
    
    Args:
        node: The original knowledge node.
        target_level: The desired abstraction level.
        hierarchy_graph: A simplified graph representation {node_id: [parent_ids]}.
        
    Returns:
        A new KnowledgeNode representing the concept at the target level.
        
    Raises:
        AbstractionError: If projection is impossible (e.g., level too high).
    """
    logger.info(f"Projecting node '{node.label}' from L{node.level} to L{target_level}")
    
    current_node = node
    visited = set()
    
    # Simplified logic: traverse up or down. 
    # Real implementation would use embedding interpolation or graph traversal.
    if target_level > current_node.level:
        # Move Up (Generalization)
        steps = target_level - current_node.level
        # Mock logic: In reality, lookup hierarchy_graph
        # Here we simulate the semantic vector becoming sparser/more abstract
        new_vector = [v * (0.9 ** steps) for v in current_node.vector] # Decay specifics
        
        return KnowledgeNode(
            id=f"{node.id}_proj_L{target_level}",
            label=f"Abstracted_{node.label}",
            level=target_level,
            vector=new_vector,
            domain=node.domain,
            semantics=NodeSemantics.ABSTRACT_PRINCIPLE
        )
    elif target_level < current_node.level:
        # Move Down (Specialization) - usually harder, requires context
        steps = current_node.level - target_level
        new_vector = [v * (1.1 ** steps) for v in current_node.vector] # Add specifics (mock)
        
        return KnowledgeNode(
            id=f"{node.id}_proj_L{target_level}",
            label=f"Specialized_{node.label}",
            level=target_level,
            vector=new_vector,
            domain=node.domain,
            semantics=NodeSemantics.CONCRETE_INSTANCE
        )
    else:
        return node


def locate_optimal_transfer_level(
    source_node: KnowledgeNode, 
    target_node: KnowledgeNode, 
    max_search_depth: int = 5
) -> TransferResult:
    """
    [Core Function 2] Locates the optimal abstraction level for cross-domain transfer.
    
    Logic:
    1. Iterate through possible abstraction levels (L0 to L_max).
    2. Project both source and target nodes to this common level.
    3. Calculate semantic similarity and 'Dimensionality Penalty'.
    4. Determine the 'Transferability Index' (high similarity + low dimensionality penalty).
    
    Args:
        source_node: The node from the source domain (e.g., 'Darwinian Evolution').
        target_node: The node from the target domain (e.g., 'Gradient Descent').
        max_search_depth: How high up the abstraction ladder to search.
        
    Returns:
        TransferResult: Contains the best level and the projected nodes.
    """
    logger.info(f"Starting transfer analysis: Source '{source_node.label}' -> Target '{target_node.label}'")
    
    best_score = -1.0
    best_level = 0
    best_source_proj = source_node
    best_target_proj = target_node
    
    # Determine the maximum possible level based on inputs
    max_level = max(source_node.level, target_node.level) + max_search_depth
    
    # Mock hierarchy graph for projection logic
    mock_hierarchy = {} 
    
    for level in range(max_level + 1):
        try:
            # Project both nodes to the current level 'level'
            s_proj = project_node_to_level(source_node, level, mock_hierarchy)
            t_proj = project_node_to_level(target_node, level, mock_hierarchy)
            
            # Calculate Semantic Similarity
            similarity = _calculate_cosine_similarity(s_proj.vector, t_proj.vector)
            
            # Dimensionality Penalty: 
            # If we go too abstract (high level), we lose specific utility (Curse of Generality).
            # If we stay too low, domains are incompatible (Curse of Dimensionality).
            # We model this as a bell curve preference for mid-levels or specific alignment.
            level_penalty = math.exp(-0.1 * abs(level - 3)) # Arbitrary preference for mid-levels for this demo
            
            transferability = similarity * level_penalty
            
            logger.debug(f"Level {level}: Sim={similarity:.3f}, Penalty={level_penalty:.3f}, Score={transferability:.3f}")
            
            if transferability > best_score:
                best_score = transferability
                best_level = level
                best_source_proj = s_proj
                best_target_proj = t_proj
                
        except AbstractionError as e:
            logger.warning(f"Projection failed at level {level}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error at level {level}: {e}")
            continue

    return TransferResult(
        optimal_level=best_level,
        source_node=best_source_proj,
        target_node=best_target_proj,
        similarity_score=best_score,
        transferability_index=best_score,
        message=f"Optimal transfer found at Abstraction Level {best_level}."
    )

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Define Source Domain Node (Biology)
    # Vector represents semantic features (e.g., [reproduction, mutation, survival, time])
    bio_vector = [0.9, 0.8, 0.7, 0.2] 
    evolution_node = KnowledgeNode(
        id="bio_001",
        label="Biological Evolution",
        level=0, # Concrete Instance/Process
        vector=bio_vector,
        domain="biology"
    )

    # 2. Define Target Domain Node (Computer Science)
    # Vector represents semantic features (e.g., [iteration, random_noise, objective_function, compute])
    cs_vector = [0.1, 0.2, 0.9, 0.8]
    gradient_node = KnowledgeNode(
        id="cs_101",
        label="Genetic Algorithm",
        level=0, # Concrete Implementation
        vector=cs_vector,
        domain="computer_science"
    )

    print("-" * 60)
    print("Cross-Domain Transfer Analysis")
    print("-" * 60)

    try:
        # Run the locator
        result = locate_optimal_transfer_level(evolution_node, gradient_node)

        print(f"\nSource Domain: {result.source_node.domain} ({evolution_node.label})")
        print(f"Target Domain: {result.target_node.domain} ({gradient_node.label})")
        print(f"\n>>> RESULT: {result.message}")
        print(f">>> Optimal Level: L{result.optimal_level}")
        print(f">>> Projected Source Concept: {result.source_node.label}")
        print(f">>> Projected Target Concept: {result.target_node.label}")
        print(f">>> Transferability Index: {result.transferability_index:.4f}")
        
    except ValueError as ve:
        logger.error(f"Input validation failed: {ve}")
    except Exception as e:
        logger.critical(f"System failure during transfer: {e}")