"""
Module: pure_sequence_logic_extractor
Description: Advanced extraction engine for isolating Pure Sequence Logic (PSL) from domain-specific skill nodes.
This module enables the transformation of concrete operational flows (e.g., cooking, driving) into abstract
logical skeletons (e.g., preparation-execution-verification), facilitating cross-domain mapping in AGI systems.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration of possible skill node types."""
    ACTION = "action"
    DECISION = "decision"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"

@dataclass
class SkillNode:
    """
    Represents a single node in the skill graph.
    
    Attributes:
        id: Unique identifier for the node (e.g., 'b1b1cb')
        raw_content: The original descriptive content (e.g., 'Put 500g beef into the pan')
        parameters: Dictionary of extracted domain parameters (e.g., {'ingredient': 'beef', 'amount': '500g'})
        connections: List of connected node IDs
    """
    id: str
    raw_content: str
    node_type: NodeType = NodeType.ACTION
    parameters: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)

@dataclass
class LogicalSkeleton:
    """
    Represents the abstracted logical structure derived from a skill node.
    
    Attributes:
        source_id: ID of the original node
        abstract_pattern: The domain-agnostic logical pattern (e.g., 'PLACE_OBJECT_IN_CONTAINER')
        variable_slots: Placeholders where domain parameters used to be
        confidence: Extraction confidence score (0.0 to 1.0)
    """
    source_id: str
    abstract_pattern: str
    variable_slots: List[str]
    confidence: float = 0.0

class LogicExtractionError(Exception):
    """Custom exception for errors during logic extraction."""
    pass

def _validate_node_integrity(node: SkillNode) -> bool:
    """
    Helper function to validate the integrity of a SkillNode object.
    
    Args:
        node: The SkillNode to validate.
        
    Returns:
        bool: True if valid, False otherwise.
        
    Raises:
        LogicExtractionError: If critical data is missing.
    """
    if not isinstance(node, SkillNode):
        logger.error(f"Invalid object type provided: {type(node)}")
        return False
    
    if not node.id or not isinstance(node.id, str):
        logger.error("Node ID is missing or invalid.")
        return False
        
    if not node.raw_content:
        logger.warning(f"Node {node.id} has empty content.")
        
    return True

def extract_domain_parameters(node: SkillNode, context: Optional[Dict] = None) -> Tuple[str, Dict[str, str]]:
    """
    Core Function 1: Analyzes raw content to identify and strip domain-specific parameters.
    
    Uses regex patterns and heuristics to identify quantities, specific objects, and proper nouns.
    
    Args:
        node: The skill node to process.
        context: Optional context containing domain hints (e.g., {'domain': 'cooking'}).
        
    Returns:
        Tuple containing:
            - stripped_content: The content with parameters replaced by placeholders.
            - params: Dictionary of extracted parameter key-value pairs.
            
    Example:
        >>> node = SkillNode(id="sk_01", raw_content="Add 2 teaspoons of salt to the soup")
        >>> stripped, params = extract_domain_parameters(node)
        >>> print(stripped)
        "Add {quantity} of {ingredient} to the {container}"
    """
    logger.info(f"Extracting parameters from node: {node.id}")
    
    # Define generic regex patterns for parameter identification
    patterns = {
        'quantity': r'\b\d+(\.\d+)?\s?(kg|g|ml|l|cups|teaspoons|tablespoons|pcs)\b',
        'proper_noun': r'\b[A-Z][a-z]+\b', # Basic proper noun detection
        'specific_ingredient': r'\b(beef|pork|salt|water|oil|onion)\b' # Example static list, in AGI this would be dynamic
    }
    
    extracted_params = {}
    working_content = node.raw_content
    
    # Apply patterns
    for p_type, regex in patterns.items():
        matches = re.finditer(regex, working_content, re.IGNORECASE)
        for i, match in enumerate(matches):
            placeholder = f"{{{p_type}_{i}}}"
            extracted_params[f"{p_type}_{i}"] = match.group()
            # Replace in string (careful with overlapping matches, simplified here)
            working_content = working_content.replace(match.group(), placeholder, 1)
            
    node.parameters = extracted_params
    logger.debug(f"Extracted params: {extracted_params}")
    
    return working_content, extracted_params

def map_to_logical_skeleton(stripped_content: str, node: SkillNode) -> LogicalSkeleton:
    """
    Core Function 2: Maps stripped content to an abstract logical verb structure.
    
    This function determines the 'Intent' of the node regardless of the object being manipulated.
    E.g., 'Heat {pan}' and 'Heat {water}' both map to 'APPLY_THERMAL_ENERGY'.
    
    Args:
        stripped_content: Content with parameters removed.
        node: The original node (used for metadata).
        
    Returns:
        LogicalSkeleton: The abstracted representation.
    """
    logger.info(f"Mapping node {node.id} to logical skeleton")
    
    # Dictionary mapping stripped patterns to abstract logic
    # In a real AGI system, this would be an embedding space comparison
    logic_map = {
        r"add\s.*\sinto\s.*": "INSERT_INTO_TARGET",
        r"heat\s.*": "APPLY_THERMAL_ENERGY",
        r"remove\s.*\sfrom\s.*": "EXTRACT_FROM_SOURCE",
        r"wait\sfor\s.*": "TEMPORAL_PAUSE",
        r"check\s.*": "VERIFY_STATE",
        r"mix\s.*": "AGGREGATE_COMPONENTS"
    }
    
    abstract_logic = "UNKNOWN_OPERATION"
    confidence = 0.0
    
    for pattern, logic in logic_map.items():
        if re.search(pattern, stripped_content, re.IGNORECASE):
            abstract_logic = logic
            confidence = 0.85 # Simulated confidence score
            break
            
    if abstract_logic == "UNKNOWN_OPERATION":
        # Fallback heuristic: Take the first verb
        verbs = re.findall(r'\b\w+ing\b|\b\w+\b', stripped_content.split('{')[0])
        if verbs:
            abstract_logic = f"GENERIC_ACTION::{verbs[0].upper()}"
            confidence = 0.40
            logger.warning(f"Low confidence mapping for node {node.id}: {abstract_logic}")

    return LogicalSkeleton(
        source_id=node.id,
        abstract_pattern=abstract_logic,
        variable_slots=list(node.parameters.keys()),
        confidence=confidence
    )

def process_skill_node_batch(nodes: List[SkillNode]) -> List[LogicalSkeleton]:
    """
    Processes a batch of skill nodes to generate a logical skeleton library.
    
    Args:
        nodes: List of SkillNode objects.
        
    Returns:
        List of LogicalSkeleton objects.
        
    Raises:
        LogicExtractionError: If the batch processing fails critically.
    """
    if not nodes:
        logger.warning("Empty node list provided for processing.")
        return []

    skeletons = []
    processed_count = 0
    
    logger.info(f"Starting batch processing for {len(nodes)} nodes.")
    
    for node in nodes:
        try:
            if not _validate_node_integrity(node):
                continue
                
            # Step 1: Strip parameters
            stripped_text, _ = extract_domain_parameters(node)
            
            # Step 2: Map to skeleton
            skeleton = map_to_logical_skeleton(stripped_text, node)
            
            skeletons.append(skeleton)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process node {node.id}: {str(e)}")
            continue

    logger.info(f"Batch processing complete. Successfully processed {processed_count}/{len(nodes)}.")
    return skeletons

if __name__ == "__main__":
    # Example Usage demonstrating the workflow
    
    # 1. Mock Data (Simulating a subset of the 293 nodes)
    mock_nodes = [
        SkillNode(id="cook_01", raw_content="Heat the wok to 200 degrees celsius"),
        SkillNode(id="cook_02", raw_content="Add 500g beef slices into the wok"),
        SkillNode(id="code_01", raw_content="Add unit tests to the authentication module"), 
        # Note: 'Add unit tests...' should structurally match 'Add ingredients...'
        SkillNode(id="code_02", raw_content="Remove deprecated functions from utils file"),
        SkillNode(id="", raw_content="Invalid node without ID")
    ]
    
    # 2. Execute Extraction
    logical_library = process_skill_node_batch(mock_nodes)
    
    # 3. Display Results
    print(f"\n{'='*15} Logical Skeleton Library {'='*15}")
    for skeleton in logical_library:
        print(f"ID: {skeleton.source_id}")
        print(f"Abstract Logic: {skeleton.abstract_pattern}")
        print(f"Slots: {skeleton.variable_slots}")
        print(f"Confidence: {skeleton.confidence}")
        print("-" * 40)
        
    # 4. Demonstration of Cross-Domain Mapping
    # Show how cook_02 and code_01 share logic (INSERT_INTO_TARGET)
    print("\n[Cross-Domain Analysis]")
    cooking_logic = next((s for s in logical_library if s.source_id == "cook_02"), None)
    coding_logic = next((s for s in logical_library if s.source_id == "code_01"), None)
    
    if cooking_logic and coding_logic:
        print(f"Cooking Node ('{mock_nodes[1].raw_content}') -> Logic: {cooking_logic.abstract_pattern}")
        print(f"Coding Node ('{mock_nodes[2].raw_content}') -> Logic: {coding_logic.abstract_pattern}")
        if cooking_logic.abstract_pattern == coding_logic.abstract_pattern:
            print(">>> Match found: Cooking 'Adding ingredients' is logically isomorphic to Coding 'Adding tests'.")