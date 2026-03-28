"""
Module: auto_isomorphic_fingerprint_extractor
A high-level cognitive skill for extracting abstract "Isomorphic Fingerprints" (structured patterns)
from specific execution content to enable cross-domain transfer.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Data Structures ---

class ConstraintType(Enum):
    """Enumeration of generic constraint types found in skills."""
    FINITE_RESOURCE = "finite_capacity"
    PRIORITY_QUEUE = "ordering_logic"
    DECAY_FUNCTION = "eviction_policy"
    FEEDBACK_LOOP = "error_correction"

@dataclass
class StructuralFingerprint:
    """
    Represents the abstract structural pattern of a skill.
    
    Attributes:
        pattern_id: Unique identifier for the pattern.
        topology: Graph-like structure representing component relationships.
        constraints: List of abstract constraints (e.g., capacity limits).
        dynamics: Temporal behaviors (e.g., queue processing rates).
        source_domain: The original domain the pattern was extracted from.
    """
    pattern_id: str
    topology: Dict[str, List[str]]
    constraints: Dict[ConstraintType, Any]
    dynamics: Dict[str, str]
    source_domain: str = "unknown"

@dataclass
class SkillInstance:
    """
    Represents a concrete skill instance to be analyzed.
    
    Attributes:
        skill_id: Unique ID (e.g., 'skill_1742').
        domain: Domain of application (e.g., 'retail', 'nlp').
        raw_logic: Dictionary describing the concrete logic and variables.
    """
    skill_id: str
    domain: str
    raw_logic: Dict[str, Any]

class IsomorphicExtractionError(Exception):
    """Custom exception for errors during fingerprint extraction."""
    pass

# --- Core Functions ---

def validate_skill_instance(skill: SkillInstance) -> bool:
    """
    Validates the structure and content of a SkillInstance.
    
    Args:
        skill: The SkillInstance object to validate.
        
    Returns:
        True if valid.
        
    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if not skill.skill_id or not isinstance(skill.skill_id, str):
        raise ValueError("Invalid or missing skill_id")
    if not skill.raw_logic:
        raise ValueError(f"Skill {skill.skill_id} has empty raw_logic")
    
    logger.debug(f"Skill {skill.skill_id} passed validation.")
    return True

def extract_isomorphic_fingerprint(skill: SkillInstance) -> StructuralFingerprint:
    """
    Extracts the abstract 'Isomorphic Fingerprint' from a concrete skill instance.
    
    This function performs the core cognitive mapping:
    1.  Analyzes concrete variables (e.g., 'stall_size', 'token_limit').
    2.  Maps them to abstract concepts (e.g., 'FINITE_RESOURCE').
    3.  Identifies the control flow topology.
    
    Args:
        skill: A validated SkillInstance object.
        
    Returns:
        A StructuralFingerprint object representing the abstract pattern.
        
    Raises:
        IsomorphicExtractionError: If pattern extraction fails.
    """
    try:
        logger.info(f"Starting extraction for skill: {skill.skill_id} in domain: {skill.domain}")
        
        # Step 1: Analyze Topology (Structure of interactions)
        # We look for inputs, outputs, and state management
        topology = _analyze_topological_structure(skill.raw_logic)
        
        # Step 2: Analyze Constraints (Resource limitations and rules)
        constraints = _map_constraints(skill.raw_logic)
        
        # Step 3: Analyze Dynamics (How state changes over time)
        dynamics = _infer_dynamics(skill.raw_logic)
        
        fingerprint = StructuralFingerprint(
            pattern_id=f"fp_{skill.skill_id}",
            topology=topology,
            constraints=constraints,
            dynamics=dynamics,
            source_domain=skill.domain
        )
        
        logger.info(f"Successfully extracted fingerprint {fingerprint.pattern_id}")
        return fingerprint
        
    except Exception as e:
        logger.error(f"Failed to extract fingerprint from {skill.skill_id}: {e}")
        raise IsomorphicExtractionError(f"Extraction failed: {e}") from e

def apply_fingerprint_to_domain(
    fingerprint: StructuralFingerprint, 
    target_domain_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies an extracted fingerprint to a new domain configuration.
    
    This is the 'Transfer' part of Cross-Domain Transfer. It instantiates
    the abstract pattern using the variables of the target domain.
    
    Args:
        fingerprint: The abstract pattern to apply.
        target_domain_config: Configuration dict of the target domain.
        
    Returns:
        A dictionary representing the instantiated logic for the target domain.
    """
    logger.info(f"Applying fingerprint {fingerprint.pattern_id} to new domain context.")
    
    instantiated_logic = {
        "meta_pattern": fingerprint.pattern_id,
        "structure": {},
        "rules": []
    }
    
    # Instantiate Topology
    for node, connections in fingerprint.topology.items():
        # In a real AGI system, this would map abstract nodes to concrete entities
        instantiated_logic["structure"][node] = {
            "type": "abstract_node",
            "connections": connections
        }
        
    # Instantiate Constraints
    for constraint_type, value in fingerprint.constraints.items():
        if constraint_type == ConstraintType.FINITE_RESOURCE:
            # Example: Mapping abstract capacity to specific target resource
            resource_key = target_domain_config.get("primary_resource", "capacity")
            instantiated_logic["rules"].append({
                "rule": "CAPACITY_LIMIT",
                "target_variable": resource_key,
                "value_relation": value # e.g., "max_items"
            })
            
    return instantiated_logic

# --- Helper Functions ---

def _analyze_topological_structure(logic: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Helper: Analyzes the graph structure of the logic.
    Identifies 'Source -> Processor -> Sink' patterns.
    """
    # Simplified heuristic: look for keys that imply flow
    nodes = {}
    inputs = logic.get("inputs", [])
    outputs = logic.get("outputs", [])
    process = logic.get("process_logic", {})
    
    if inputs and process:
        nodes["input_layer"] = ["processor"]
    if process and outputs:
        nodes["processor"] = ["output_layer"]
        
    return nodes

def _map_constraints(logic: Dict[str, Any]) -> Dict[ConstraintType, Any]:
    """
    Helper: Maps concrete logic variables to abstract ConstraintTypes.
    
    Example Mapping:
    'shelf_space' (Retail) -> FINITE_RESOURCE
    'context_window' (LLM) -> FINITE_RESOURCE
    """
    constraints = {}
    
    # Heuristic: Check for capacity-related keywords
    capacity_keywords = ['size', 'limit', 'max', 'capacity', 'window', 'space']
    logic_str = json.dumps(logic).lower()
    
    if any(keyword in logic_str for keyword in capacity_keywords):
        constraints[ConstraintType.FINITE_RESOURCE] = "hard_limit"
        
    # Heuristic: Check for ordering keywords
    if 'priority' in logic_str or 'queue' in logic_str or 'urgency' in logic_str:
        constraints[ConstraintType.PRIORITY_QUEUE] = "sorted_ingress"
        
    return constraints

def _infer_dynamics(logic: Dict[str, Any]) -> Dict[str, str]:
    """
    Helper: Infers temporal dynamics (how the system evolves).
    """
    dynamics = {}
    # Simple logic for demonstration
    if "evict" in str(logic).lower() or "remove" in str(logic).lower():
        dynamics["state_change"] = "decay_or_replacement"
    else:
        dynamics["state_change"] = "accumulative"
    return dynamics

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define Source Skill: Small Vendor Inventory Management
    vendor_skill_data = {
        "inputs": ["supplier_delivery", "customer_purchase"],
        "outputs": ["sales_record", "waste_report"],
        "process_logic": {
            "check_inventory": "daily",
            "shelf_space": 50, # Finite resource
            "evict": "expire_items" # Dynamic behavior
        }
    }
    
    source_skill = SkillInstance(
        skill_id="vendor_inventory_01",
        domain="retail",
        raw_logic=vendor_skill_data
    )

    try:
        # 2. Extract Fingerprint
        validate_skill_instance(source_skill)
        fingerprint = extract_isomorphic_fingerprint(source_skill)
        
        print(f"\n--- Extracted Fingerprint ---")
        print(f"Pattern ID: {fingerprint.pattern_id}")
        print(f"Constraints: {fingerprint.constraints}")
        print(f"Dynamics: {fingerprint.dynamics}")
        
        # 3. Define Target Context: LLM Context Window Management
        llm_config = {
            "primary_resource": "token_limit",
            "environment": "chat_interface"
        }
        
        # 4. Apply Fingerprint to Target Domain
        new_skill_logic = apply_fingerprint_to_domain(fingerprint, llm_config)
        
        print(f"\n--- Migrated Logic to LLM Domain ---")
        print(json.dumps(new_skill_logic, indent=2))
        
    except (ValueError, IsomorphicExtractionError) as e:
        logger.critical(f"Operational Error: {e}")