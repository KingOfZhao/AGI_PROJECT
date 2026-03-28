"""
Module: node_quality_assessor.py

This module provides tools for assessing the quality of knowledge graph nodes
based on the conflict rate observed during the 'Overlapping Solidification'
fusion process.

Author: Senior Python Engineer (AGI System Component)
Domain: knowledge_graph_fusion
"""

import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class NodeDefinition(BaseModel):
    """
    Represents the definition of a single node in the knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        domain: The specific domain the node belongs to (e.g., 'physics', 'biology').
        attributes: A dictionary containing the defining properties of the node.
        scope_score: A pre-calculated score (0.0 to 1.0) indicating scope breadth.
    """
    id: str
    domain: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    scope_score: float = Field(default=0.5, ge=0.0, le=1.0)


class FusionReport(BaseModel):
    """
    Represents the result of an attempted fusion between two nodes.
    
    Attributes:
        node_a_id: ID of the first parent node.
        node_b_id: ID of the second parent node.
        total_properties: Total unique properties considered in the fusion.
        conflicting_properties: Properties that required modification/resolution.
        modification_depth: A metric indicating how much the original definition changed.
    """
    node_a_id: str
    node_b_id: str
    total_properties: int
    conflicting_properties: int
    modification_depth: float = Field(ge=0.0, le=1.0)


# --- Core Functions ---

def calculate_conflict_rate(report: FusionReport) -> float:
    """
    Calculates the conflict rate based on a fusion report.

    The conflict rate is defined as the ratio of conflicting properties to
    total properties, weighted by the modification depth required to resolve
    the conflict.

    Args:
        report: A FusionReport object containing fusion details.

    Returns:
        A float between 0.0 and 1.0 representing the conflict rate.
    
    Raises:
        ValueError: If total_properties is zero (division by zero).
    """
    if report.total_properties == 0:
        logger.warning(f"Fusion report between {report.node_a_id} and {report.node_b_id} has zero properties.")
        return 0.0
    
    base_conflict_ratio = report.conflicting_properties / report.total_properties
    
    # Weighted conflict rate considering the depth of modification
    # If modification_depth is high, even a few conflicts are significant
    weighted_rate = base_conflict_ratio * (1 + report.modification_depth)
    
    # Normalize to ensure it stays within 0.0 - 1.0 bounds
    normalized_rate = min(max(weighted_rate / 2.0, 0.0), 1.0)
    
    logger.debug(f"Calculated conflict rate for {report.node_a_id}+{report.node_b_id}: {normalized_rate:.4f}")
    return normalized_rate


def evaluate_node_quality(
    node: NodeDefinition, 
    fusion_history: List[FusionReport], 
    threshold: float = 0.5
) -> Tuple[bool, float]:
    """
    Evaluates the quality of a node based on its fusion conflict history.

    If a node consistently causes high conflict rates (requiring >50% modification
    of definitions) when fusing with nodes from other domains, it is flagged as
    low quality or having an overly narrow scope.

    Args:
        node: The node to evaluate.
        fusion_history: A list of past FusionReport objects involving this node.
        threshold: The conflict rate threshold above which a node is considered low quality.

    Returns:
        A tuple (is_high_quality, average_conflict_score).
        is_high_quality: True if the node meets quality standards.
        average_conflict_score: The mean conflict score across fusion attempts.
    """
    if not fusion_history:
        logger.info(f"No fusion history available for node {node.id}. Defaulting to high quality.")
        return True, 0.0

    total_conflict_score = 0.0
    relevant_fusions = 0

    for report in fusion_history:
        # Only consider fusions where this node was involved
        if report.node_a_id == node.id or report.node_b_id == node.id:
            rate = calculate_conflict_rate(report)
            total_conflict_score += rate
            relevant_fusions += 1

    if relevant_fusions == 0:
        return True, 0.0

    avg_score = total_conflict_score / relevant_fusions
    
    is_high_quality = avg_score <= threshold
    
    if not is_high_quality:
        logger.warning(
            f"Node Quality Alert: Node '{node.id}' (Domain: {node.domain}) "
            f"has high conflict rate {avg_score:.2f} (Threshold: {threshold}). "
            f"Indicates potential narrow scope or low definition quality."
        )
    else:
        logger.info(f"Node '{node.id}' passed quality check with score {avg_score:.2f}.")

    return is_high_quality, avg_score


# --- Helper Functions ---

def simulate_fusion_process(node_a: NodeDefinition, node_b: NodeDefinition) -> FusionReport:
    """
    Helper function to simulate a fusion process between two nodes.
    
    In a real AGI system, this would involve complex logic to merge ontologies.
    Here, we simulate it based on attribute overlap and scope scores.
    
    Args:
        node_a: First node.
        node_b: Second node.

    Returns:
        A FusionReport object simulating the result.
    """
    logger.info(f"Simulating fusion: {node_a.id} + {node_b.id}")
    
    all_keys = set(node_a.attributes.keys()) | set(node_b.attributes.keys())
    total_props = len(all_keys)
    conflicts = 0
    
    # Simple simulation: if values differ for same key, it's a conflict
    for key in all_keys:
        val_a = node_a.attributes.get(key)
        val_b = node_b.attributes.get(key)
        if val_a and val_b and val_a != val_b:
            conflicts += 1
            
    # If nodes are from different domains and have low scope scores, increase modification depth
    domain_distance = 0.0 if node_a.domain == node_b.domain else 0.5
    scope_penalty = (2.0 - node_a.scope_score - node_b.scope_score) / 2.0
    
    modification_depth = min(0.5 + domain_distance + scope_penalty, 1.0)
    
    return FusionReport(
        node_a_id=node_a.id,
        node_b_id=node_b.id,
        total_properties=total_props if total_props > 0 else 1,
        conflicting_properties=conflicts,
        modification_depth=modification_depth
    )

# --- Usage Example ---
if __name__ == "__main__":
    # Example Usage
    
    # 1. Define Nodes
    node_physics = NodeDefinition(
        id="n_energy_01",
        domain="physics",
        attributes={"definition": "capacity to do work", "unit": "joules", "conservation": "constant"},
        scope_score=0.8
    )
    
    # A potentially low-quality or narrowly defined node
    node_bio_poor = NodeDefinition(
        id="n_energy_bio_02",
        domain="biology",
        attributes={"definition": "feeling of wakefulness", "source": "coffee"}, # Narrow scope
        scope_score=0.2
    )
    
    # 2. Simulate Fusion History
    # Try to fuse physics node with the 'poor' biology node
    report_1 = simulate_fusion_process(node_physics, node_bio_poor)
    
    # Create a dummy history
    history = [report_1]
    
    # 3. Evaluate Quality
    is_quality, score = evaluate_node_quality(node_bio_poor, history, threshold=0.5)
    
    print(f"Node {node_bio_poor.id} Quality Check: {'PASS' if is_quality else 'FAIL'} (Score: {score:.2f})")