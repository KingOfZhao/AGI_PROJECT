"""
Module: auto_collision_fusion.py
Author: Senior Python Engineer (AGI System Component)
Description: Implements 'Collision Fusion' logic for knowledge graph evolution.
             Handles conflicts between new high-efficiency nodes (e.g., GenAI SQL)
             and legacy validated nodes (e.g., Manual SQL) by extracting safety
             constraints ('Cognitive Antibodies') and determining merge/replace strategies.
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI.Skill.CollisionFusion")

class ConflictStrategy(Enum):
    """Enumeration of possible resolution strategies for node conflicts."""
    REPLACE = "REPLACE"               # Completely replace old with new
    MERGE = "MERGE"                   # Combine attributes
    PRESERVE_OLD = "PRESERVE_OLD"     # Reject new node
    QUARANTINE = "QUARANTINE"         # Move new node to quarantine for review

@dataclass
class SkillNode:
    """
    Represents a node in the Knowledge Graph.
    
    Attributes:
        id: Unique identifier (hash).
        name: Human-readable name.
        functionality: Description of what the node does.
        performance_score: Efficiency metric (0.0 to 1.0).
        constraints: List of safety/validation rules (Cognitive Antibodies).
        metadata: Additional properties.
    """
    id: str
    name: str
    functionality: str
    performance_score: float = 0.0
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(self.name.encode()).hexdigest()[:8]

def _validate_node_integrity(node: SkillNode) -> bool:
    """
    [Helper] Validates the data structure of a skill node.
    
    Args:
        node: The SkillNode object to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(node, SkillNode):
        logger.error(f"Invalid type: Expected SkillNode, got {type(node)}")
        return False
    if not node.id or not node.name:
        logger.error("Node missing required fields: id or name")
        return False
    if not (0.0 <= node.performance_score <= 1.0):
        logger.warning(f"Node {node.id} performance score out of bounds [0,1]. Clamping recommended.")
        # Auto-fix for robustness
        node.performance_score = max(0.0, min(1.0, node.performance_score))
    return True

def extract_cognitive_antibodies(legacy_node: SkillNode) -> List[Dict[str, Any]]:
    """
    [Core] Extracts safety constraints and validation logic from the legacy node.
    
    This function simulates the analysis of a node's code/configuration to find
    'Safety Patterns' (e.g., SQL injection checks, input sanitization).
    
    Args:
        legacy_node: The old node being deprecated or merged.
        
    Returns:
        A list of constraint dictionaries representing 'Cognitive Antibodies'.
        
    Example:
        >>> antibodies = extract_cognitive_antibodies(old_sql_node)
        >>> print(antibodies[0]['type'])
        'SQL_INJECTION_DEFENSE'
    """
    logger.info(f"Extracting antibodies from legacy node: {legacy_node.name} ({legacy_node.id})")
    
    # Simulation of static analysis / pattern matching
    extracted = []
    for constraint in legacy_node.constraints:
        # We only extract 'HARD' constraints (Safety) and ignore 'SOFT' (Preferences) for antibodies
        if constraint.get("priority") == "CRITICAL" or constraint.get("type") == "SAFETY":
            extracted.append(constraint)
            logger.debug(f"Extracted antibody: {constraint.get('description')}")
            
    # Check for implicit constraints in metadata (e.g., allowed domains)
    if "allowed_domains" in legacy_node.metadata:
        extracted.append({
            "type": "DOMAIN_RESTRICTION",
            "value": legacy_node.metadata["allowed_domains"],
            "source": "LEGACY_METADATA"
        })
        
    return extracted

def conceptual_engulfment_algorithm(
    legacy_node: SkillNode, 
    new_node: SkillNode
) -> Tuple[ConflictStrategy, SkillNode]:
    """
    [Core] Decides the fate of conflicting nodes based on performance and safety.
    
    Algorithm Logic:
    1. Safety Check: Does the new node satisfy all critical constraints of the old?
    2. Performance Check: Is the new node significantly better?
    3. Strategy:
       - If New is Safe AND Better -> MERGE (Inject antibodies, replace logic).
       - If New is NOT Safe -> QUARANTINE.
       - If New is Safe but NOT Better -> PRESERVE_OLD.
       
    Args:
        legacy_node: The existing node.
        new_node: The challenging node.
        
    Returns:
        A tuple containing the chosen Strategy and the resulting Node object.
        
    Raises:
        ValueError: If input nodes fail integrity validation.
    """
    # 1. Validation
    if not _validate_node_integrity(legacy_node) or not _validate_node_integrity(new_node):
        raise ValueError("Input node integrity check failed.")
        
    logger.info(f"Engulfment Analysis: Old [{legacy_node.name}] vs New [{new_node.name}]")
    
    # 2. Extract Antibodies from Legacy
    antibodies = extract_cognitive_antibodies(legacy_node)
    
    # 3. Simulate Compatibility Check (Can new node accept these antibodies?)
    # In a real AGI system, this would involve semantic analysis.
    # Here we check if the new node already has similar constraints or explicitly rejects them.
    compatibility_score = 1.0
    required_safety_count = len(antibodies)
    matched_safety_count = 0
    
    for ab in antibodies:
        # Simple heuristic: check if new node metadata acknowledges this safety type
        if ab['type'] in new_node.metadata.get('supported_safety_standards', []):
            matched_safety_count += 1
        else:
            # Penalty for missing safety features
            compatibility_score -= 0.2 
            
    compatibility_score = max(0.0, compatibility_score)
    
    # 4. Determine Strategy
    perf_delta = new_node.performance_score - legacy_node.performance_score
    
    # Decision Matrix
    if compatibility_score < 0.6:
        logger.warning(f"New node {new_node.name} failed safety compatibility. Strategy: QUARANTINE")
        return (ConflictStrategy.QUARANTINE, new_node)
        
    if perf_delta > 0.1:
        # Significant improvement
        logger.info(f"New node shows significant improvement (+{perf_delta:.2f}). Strategy: MERGE")
        
        # Inject Antibodies
        merged_constraints = new_node.constraints + antibodies
        # Deduplicate constraints (simple logic)
        unique_constraints = {json.dumps(c, sort_keys=True): c for c in merged_constraints}.values()
        
        merged_node = SkillNode(
            id=f"merged_{new_node.id}",
            name=new_node.name,
            functionality=new_node.functionality,
            performance_score=new_node.performance_score,
            constraints=list(unique_constraints),
            metadata={
                **new_node.metadata, 
                "engulfed_legacy_id": legacy_node.id,
                "status": "FUSED"
            }
        )
        return (ConflictStrategy.MERGE, merged_node)
        
    elif perf_delta > 0:
        # Marginal improvement
        logger.info(f"New node marginally better. Strategy: REPLACE")
        return (ConflictStrategy.REPLACE, new_node)
        
    else:
        # New node is worse or equal
        logger.info(f"Legacy node remains superior. Strategy: PRESERVE_OLD")
        return (ConflictStrategy.PRESERVE_OLD, legacy_node)

# ================= Usage Example =================
if __name__ == "__main__":
    # 1. Setup Legacy Node (The Safe, Old Way)
    legacy_sql_node = SkillNode(
        id="sql_manual_v1",
        name="Manual SQL Writer",
        functionality="Constructs SQL queries via string concatenation.",
        performance_score=0.45,
        constraints=[
            {"type": "SAFETY", "description": "Prevent SQL Injection", "priority": "CRITICAL", "code": "sanitize_input()"}
        ],
        metadata={"allowed_domains": ["internal_db"]}
    )

    # 2. Setup New Node (The Efficient, Risky Way)
    new_llm_sql_node = SkillNode(
        id="sql_llm_v1",
        name="Natural Language to SQL",
        functionality="Generates SQL from natural language using LLM.",
        performance_score=0.92,
        constraints=[], # Initially empty!
        metadata={"supported_safety_standards": []} # Assumes it supports nothing initially
    )

    print("--- Running Collision Fusion Scenario 1: Risky New Node ---")
    try:
        strategy, resulting_node = conceptual_engulfment_algorithm(legacy_sql_node, new_llm_sql_node)
        print(f"Result Strategy: {strategy.value}")
        print(f"Resulting Node ID: {resulting_node.id}")
        if strategy == ConflictStrategy.QUARANTINE:
            print("Reason: New node failed to meet safety compatibility standards.")
            
        print("\n" + "="*40 + "\n")
        
        # 3. Setup Improved New Node (Safe & Efficient)
        safe_llm_node = SkillNode(
            id="sql_llm_v2",
            name="Safe NL to SQL",
            functionality="Generates parameterized SQL via LLM.",
            performance_score=0.95,
            constraints=[],
            metadata={"supported_safety_standards": ["SAFETY"]} # Declares support for safety
        )
        
        print("--- Running Collision Fusion Scenario 2: Safe & Better Node ---")
        strategy2, merged_node = conceptual_engulfment_algorithm(legacy_sql_node, safe_llm_node)
        print(f"Result Strategy: {strategy2.value}")
        print(f"Resulting Node Constraints: {merged_node.constraints}")
        print("Antibodies Injected: " + str(len(merged_node.constraints) > 0))
        
    except ValueError as e:
        logger.error(f"Execution failed: {e}")