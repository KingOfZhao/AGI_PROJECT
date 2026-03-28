"""
Module: cross_domain_isomorphism_extractor.py

This module is designed for AGI systems to identify and extract structurally isomorphic
implicit knowledge nodes between two distinct craft domains (e.g., Pottery vs. Welding).
It enables skill reuse by mapping high-level procedural abstractions.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillDomain(Enum):
    """Enumeration of supported handicraft domains."""
    POTTERY = "Pottery"
    WELDING = "Welding"
    CARPENTRY = "Carpentry"
    COOKING = "Cooking"

@dataclass
class KnowledgeNode:
    """Represents a specific knowledge node in a skill graph.
    
    Attributes:
        node_id: Unique identifier for the node.
        name: Human-readable name of the skill step.
        attributes: A dictionary of physical/dynamic properties (e.g., heat_level, pressure).
        abstract_concepts: Tags describing the abstract nature of the step (e.g., 'thermal_control').
    """
    node_id: str
    name: str
    attributes: Dict[str, float]
    abstract_concepts: List[str]

    def __post_init__(self):
        if not isinstance(self.attributes, dict):
            raise ValueError("Attributes must be a dictionary.")
        if not isinstance(self.abstract_concepts, list):
            raise ValueError("Abstract concepts must be a list.")

@dataclass
class IsomorphicPair:
    """Represents a pair of isomorphic nodes found across domains."""
    source_node: KnowledgeNode
    target_node: KnowledgeNode
    similarity_score: float
    shared_concepts: List[str]

def _validate_input_graph(graph: List[KnowledgeNode], domain_name: str) -> None:
    """Validates the structure and content of a skill graph.
    
    Args:
        graph: A list of KnowledgeNodes.
        domain_name: Name of the domain for logging purposes.
        
    Raises:
        ValueError: If the graph is empty or contains invalid nodes.
    """
    if not graph:
        raise ValueError(f"Input graph for {domain_name} cannot be empty.")
    
    for node in graph:
        if not node.node_id or not node.name:
            raise ValueError(f"Invalid node detected in {domain_name}: Missing ID or Name.")
    logger.info(f"Validation passed for domain: {domain_name} with {len(graph)} nodes.")

def _calculate_semantic_overlap(concepts_a: List[str], concepts_b: List[str]) -> Tuple[float, List[str]]:
    """Calculates the Jaccard similarity between two lists of concepts.
    
    Args:
        concepts_a: List of concepts from node A.
        concepts_b: List of concepts from node B.
        
    Returns:
        A tuple containing the similarity score (0.0 to 1.0) and the set of overlapping concepts.
    """
    set_a = set(concepts_a)
    set_b = set(concepts_b)
    
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    
    if not union:
        return 0.0, []
    
    score = len(intersection) / len(union)
    return score, list(intersection)

def extract_structural_isomorphisms(
    source_domain_graph: List[KnowledgeNode],
    target_domain_graph: List[KnowledgeNode],
    similarity_threshold: float = 0.6
) -> List[IsomorphicPair]:
    """Identifies structural isomorphisms between two skill graphs based on abstract concepts.
    
    This function looks for nodes in different domains that share 'abstract_concepts', 
    such as 'heat regulation' or 'rhythmic motion', even if the physical attributes differ.
    
    Args:
        source_domain_graph: The list of nodes from the source domain (e.g., Pottery).
        target_domain_graph: The list of nodes from the target domain (e.g., Welding).
        similarity_threshold: Minimum Jaccard similarity index to consider nodes isomorphic.
        
    Returns:
        A list of IsomorphicPair objects representing the mapped skills.
        
    Raises:
        ValueError: If input graphs are invalid.
    """
    logger.info("Starting isomorphism extraction...")
    
    # Data Validation
    try:
        _validate_input_graph(source_domain_graph, "Source Domain")
        _validate_input_graph(target_domain_graph, "Target Domain")
    except ValueError as e:
        logger.error(f"Input validation failed: {e}")
        raise

    isomorphic_pairs: List[IsomorphicPair] = []
    
    # Boundary check for threshold
    if not 0.0 <= similarity_threshold <= 1.0:
        logger.warning("Threshold out of bounds [0,1]. Resetting to 0.5.")
        similarity_threshold = 0.5

    # Extraction Logic
    for s_node in source_domain_graph:
        for t_node in target_domain_graph:
            # Skip if both nodes are exactly identical (trivial match) or check for semantic overlap
            score, shared = _calculate_semantic_overlap(s_node.abstract_concepts, t_node.abstract_concepts)
            
            if score >= similarity_threshold:
                pair = IsomorphicPair(
                    source_node=s_node,
                    target_node=t_node,
                    similarity_score=score,
                    shared_concepts=shared
                )
                isomorphic_pairs.append(pair)
                logger.debug(f"Match found: {s_node.name} <-> {t_node.name} (Score: {score:.2f})")

    logger.info(f"Extraction complete. Found {len(isomorphic_pairs)} isomorphic pairs.")
    return isomorphic_pairs

def map_and_refine_skill(
    isomorphic_pair: IsomorphicPair,
    target_context: Dict[str, float]
) -> Dict[str, str]:
    """Attempts to translate specific parameters from a source node to a target context.
    
    This is a heuristic function that generates a 'transfer suggestion' based on the 
    isomorphic pair. It demonstrates how AGI might suggest reusing a skill.
    
    Args:
        isomorphic_pair: The pair of nodes identified as isomorphic.
        target_context: Physical constraints of the target environment (e.g., {'max_temp': 1500}).
        
    Returns:
        A dictionary containing the transfer strategy and status.
    """
    logger.info(f"Generating transfer strategy for pair: {isomorphic_pair.source_node.name} -> {isomorphic_pair.target_node.name}")
    
    strategy = {
        "source_skill": isomorphic_pair.source_node.name,
        "target_skill": isomorphic_pair.target_node.name,
        "transfer_status": "FEASIBLE",
        "recommendation": "",
        "shared_knowledge": ", ".join(isomorphic_pair.shared_concepts)
    }
    
    # Simple logic simulation: Check if attributes are compatible
    # Here we demonstrate handling specific abstract concepts like 'thermal_control'
    if "thermal_control" in isomorphic_pair.shared_concepts:
        source_temp = isomorphic_pair.source_node.attributes.get("temperature", 0)
        target_max = target_context.get("max_temp", float('inf'))
        
        if source_temp > target_max:
            strategy["transfer_status"] = "ADJUSTMENT_NEEDED"
            strategy["recommendation"] = f"Source temp ({source_temp}) exceeds target max ({target_max}). Requires cooling strategy."
        else:
            strategy["recommendation"] = "Direct transfer of dynamic heat control pattern is possible."
            
    return strategy

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Define Source Domain (Pottery)
    pottery_graph = [
        KnowledgeNode(
            node_id="P01", 
            name="Kiln Firing", 
            attributes={"temperature": 1200, "duration": 300}, 
            abstract_concepts=["thermal_control", "patience", "oxidization"]
        ),
        KnowledgeNode(
            node_id="P02", 
            name="Wheel Throwing", 
            attributes={"rpm": 150, "force": 10}, 
            abstract_concepts=["centrifugal_force", "moisture_control", "rhythm"]
        )
    ]

    # 2. Define Target Domain (Welding)
    welding_graph = [
        KnowledgeNode(
            node_id="W01", 
            name="Arc Welding", 
            attributes={"temperature": 3000, "voltage": 30}, 
            abstract_concepts=["thermal_control", "fusion", "eye_safety"]
        ),
        KnowledgeNode(
            node_id="W02", 
            name="Metal Grinding", 
            attributes={"rpm": 3000, "friction": 50}, 
            abstract_concepts=["centrifugal_force", "abrasion", "sparks"]
        )
    ]

    try:
        # 3. Extract Isomorphisms
        # We expect 'Kiln Firing' and 'Arc Welding' to match on 'thermal_control'
        # We expect 'Wheel Throwing' and 'Metal Grinding' to match on 'centrifugal_force'
        pairs = extract_structural_isomorphisms(
            source_domain_graph=pottery_graph,
            target_domain_graph=welding_graph,
            similarity_threshold=0.3 # Lower threshold for this small dataset
        )

        print(f"\n--- Found {len(pairs)} Transferable Pairs ---")
        for pair in pairs:
            print(f"Source: {pair.source_node.name} | Target: {pair.target_node.name}")
            print(f"   Shared Concepts: {pair.shared_concepts}")

            # 4. Generate Strategy
            strategy = map_and_refine_skill(pair, target_context={"max_temp": 3500})
            print(f"   Strategy: {strategy['recommendation']}")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")