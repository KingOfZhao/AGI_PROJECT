"""
Module: dialectical_constraint_system.py

This module implements a Dialectical Constraint System for AGI modeling.
It reframes 'bias' as 'heuristic constraints' to optimize retrieval speed
while maintaining the ability to perform deep validation via 'cascade checks'
when critical decisions are required.

Classes:
    ConstraintConfig: Configuration model for constraints.
    DialecticalSystem: The core system managing fast/slow thinking modes.

Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DialecticalConstraintSystem")


class DecisionMode(Enum):
    """Enumeration for system operation modes."""
    HEURISTIC_FAST = "fast"  # Uses soft constraints (biases) for speed
    CRITICAL_SLOW = "slow"   # Validates against orphan data (counter-examples)


@dataclass
class ConstraintConfig:
    """
    Configuration for a specific dialectical constraint.
    
    Attributes:
        constraint_id: Unique identifier for the constraint.
        name: Human-readable name.
        target_tags: Tags to prioritize (the 'bias').
        exclusion_tags: Tags to deprioritize (creating potential 'orphans').
        threshold: Confidence threshold to trigger this constraint.
        is_active: Whether this constraint is currently enabled.
    """
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Constraint"
    target_tags: List[str] = field(default_factory=list)
    exclusion_tags: List[str] = field(default_factory=list)
    threshold: float = 0.5
    is_active: bool = True

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        if not isinstance(self.target_tags, list):
            raise TypeError("target_tags must be a list")


@dataclass
class DataNode:
    """
    Represents a unit of data in the knowledge base.
    
    Attributes:
        id: Unique ID of the node.
        content: The actual data payload.
        tags: Metadata tags used for constraint matching.
        relevance_score: Base relevance score before constraint application.
    """
    id: str
    content: Any
    tags: List[str]
    relevance_score: float = 0.0


class DialecticalSystem:
    """
    A system that balances heuristic speed (biases) with dialectical truth (counter-examples).
    
    This system allows injecting 'soft constraints' (biases) to filter data for speed.
    However, on critical decisions, it triggers a 'cascade check' to retrieve
    'orphan data' (data excluded by biases) to ensure robustness.
    """

    def __init__(self, knowledge_base: List[DataNode]):
        """
        Initialize the system with a knowledge base.
        
        Args:
            knowledge_base: A list of DataNodes to query against.
        """
        self._knowledge_base = knowledge_base
        self._constraints: Dict[str, ConstraintConfig] = {}
        self._mode = DecisionMode.HEURISTIC_FAST
        logger.info(f"DialecticalSystem initialized with {len(knowledge_base)} nodes.")

    def add_constraint(self, config: ConstraintConfig) -> str:
        """
        Add a heuristic constraint to the system.
        
        Args:
            config: The configuration object for the constraint.
            
        Returns:
            The ID of the added constraint.
        """
        if not isinstance(config, ConstraintConfig):
            raise TypeError("Invalid configuration type.")
        
        self._constraints[config.constraint_id] = config
        logger.info(f"Constraint added: {config.name} (ID: {config.constraint_id})")
        return config.constraint_id

    def _apply_heuristics(self, node: DataNode, constraint: ConstraintConfig) -> float:
        """
        Internal helper to calculate adjusted relevance based on constraints.
        Positive bias for target_tags, negative for exclusion_tags.
        """
        score = node.relevance_score
        matches = set(node.tags) & set(constraint.target_tags)
        excludes = set(node.tags) & set(constraint.exclusion_tags)
        
        # Boost score if it matches target (Heuristic advantage)
        if matches:
            score += (len(matches) * 0.5) * constraint.threshold
        
        # Penalize score if it matches exclusion (Creating Orphans)
        if excludes:
            score -= (len(excludes) * 0.5)
            
        return max(0.0, min(1.0, score))

    def retrieve(self, query_tags: List[str], critical_decision: bool = False) -> Tuple[List[DataNode], Dict[str, Any]]:
        """
        Retrieve data from the knowledge base.
        
        If critical_decision is True, performs a Cascade Check to include Orphan Data.
        
        Args:
            query_tags: Tags to search for.
            critical_decision: If True, switches to SLOW mode and validates against biases.
            
        Returns:
            A tuple of (filtered_results, meta_info).
        """
        start_time = datetime.now()
        active_constraints = [c for c in self._constraints.values() if c.is_active]
        
        if critical_decision:
            self._mode = DecisionMode.CRITICAL_SLOW
            logger.warning("CRITICAL DECISION: Switching to SLOW mode (Cascade Check).")
        else:
            self._mode = DecisionMode.HEURISTIC_FAST
            logger.info("Standard retrieval: Using FAST mode (Heuristic Constraints).")

        candidates = []
        orphan_data = []
        
        # Initial scoring
        for node in self._knowledge_base:
            # Base relevance calculation (simplified for demo)
            base_overlap = len(set(node.tags) & set(query_tags))
            node.relevance_score = min(1.0, base_overlap * 0.3)
            
            # Apply constraints logic
            is_orphan = False
            adjusted_score = node.relevance_score
            
            if self._mode == DecisionMode.HEURISTIC_FAST:
                # Apply biases
                for constraint in active_constraints:
                    adjusted_score = self._apply_heuristics(node, constraint)
                    
                # Check if filtered out by bias
                if any(set(node.tags) & set(c.exclusion_tags) for c in active_constraints):
                    if adjusted_score < 0.1: # Threshold for being 'filtered'
                        is_orphan = True
            else:
                # In SLOW mode, we identify orphans explicitly to re-evaluate them
                # Logic: Would this node be ignored in FAST mode?
                fast_score = node.relevance_score
                for constraint in active_constraints:
                    fast_score = self._apply_heuristics(node, constraint)
                
                if fast_score < 0.1 and node.relevance_score > 0:
                    is_orphan = True
                    orphan_data.append(node)

            if not is_orphan:
                candidates.append(node)

        final_results = sorted(candidates, key=lambda x: x.relevance_score, reverse=True)
        
        # Cascade Check Logic
        if self._mode == DecisionMode.CRITICAL_SLOW and orphan_data:
            logger.info(f"Cascade Check: Found {len(orphan_data)} orphan data nodes (counter-examples).")
            # In a real AGI system, this would trigger a sub-routine to analyze contradictions.
            # Here we append them with a warning flag for the user.
            for orphan in orphan_data:
                orphan.content = f"[ORPHAN/DISSENTING VIEW]: {orphan.content}"
                final_results.append(orphan)

        processing_time = (datetime.now() - start_time).total_seconds()
        meta = {
            "mode": self._mode.value,
            "constraints_applied": len(active_constraints),
            "processing_time_ms": processing_time * 1000,
            "orphans_recovered": len(orphan_data) if critical_decision else 0
        }
        
        return final_results[:10], meta # Return top 10 results

def validate_knowledge_base(data: List[Dict[str, Any]]) -> List[DataNode]:
    """
    Helper function to validate and convert raw data to DataNodes.
    
    Args:
        data: List of dictionaries containing 'id', 'content', and 'tags'.
        
    Returns:
        List of validated DataNode objects.
        
    Raises:
        ValueError: If data format is invalid.
    """
    nodes = []
    for item in data:
        if not all(k in item for k in ['id', 'content', 'tags']):
            raise ValueError(f"Missing keys in data item: {item}")
        nodes.append(DataNode(
            id=item['id'],
            content=item['content'],
            tags=item['tags']
        ))
    return nodes

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Data
    raw_data = [
        {"id": "1", "content": "Standard operating procedure A", "tags": ["ops", "safety"]},
        {"id": "2", "content": "Risky optimization method B", "tags": ["ops", "risk", "experimental"]},
        {"id": "3", "content": "Legacy system data C", "tags": ["ops", "legacy", "deprecated"]},
        {"id": "4", "content": "New advanced algorithm D", "tags": ["ops", "experimental", "fast"]}
    ]
    
    try:
        kb = validate_knowledge_base(raw_data)
        system = DialecticalSystem(kb)
        
        # 2. Define Constraints (The "Bias")
        # We want to favor safety and ignore 'experimental' stuff usually
        bias_config = ConstraintConfig(
            name="Safety First Filter",
            target_tags=["safety"],
            exclusion_tags=["experimental", "deprecated"],
            threshold=0.8
        )
        system.add_constraint(bias_config)
        
        # 3. Scenario A: Fast Retrieval (Biased)
        print("--- Fast Retrieval (Routine) ---")
        results, meta = system.retrieve(query_tags=["ops"], critical_decision=False)
        print(f"Meta: {meta}")
        for r in results:
            print(f"ID: {r.id}, Content: {r.content}")
            
        # 4. Scenario B: Critical Decision (Dialectical Check)
        print("\n--- Critical Decision (Uncovering Orphans) ---")
        results_crit, meta_crit = system.retrieve(query_tags=["ops"], critical_decision=True)
        print(f"Meta: {meta_crit}")
        for r in results_crit:
            print(f"ID: {r.id}, Content: {r.content}")

    except Exception as e:
        logger.error(f"System Error: {e}")