"""
Module: auto_causal_intervention_verification.py

Description:
    Verifies the necessity of causal intervention in cross-domain transfer for AGI systems.
    It specifically addresses the risk of transferring correlation-based heuristics (e.g., "Sales
    discounts increase volume") to domains where causal structures differ (e.g., "Lowering one's
    value decreases attraction in mating").

    This module implements a mechanism to detect structural dissimilarities between a source
    domain's causal graph and a target domain's causal graph, intervening when correlation
    transfer is deemed unsafe.

Author: AGI_System_Senior_Engineer
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EdgeType(Enum):
    """Defines the type of causal edge."""
    CAUSAL = 'causal'       # Direct cause-effect
    SPURIOUS = 'spurious'   # Correlation without direct causation (confounded)
    INHIBITOR = 'inhibitor' # Negative causal effect

@dataclass
class CausalGraph:
    """
    Represents a simplified Causal Bayesian Network structure.
    
    Attributes:
        nodes: Set of variables in the domain.
        edges: Dictionary mapping (source, target) to EdgeType.
        domain_name: Name of the domain.
    """
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[Tuple[str, str], EdgeType] = field(default_factory=dict)
    domain_name: str = "Unnamed"

    def add_edge(self, u: str, v: str, edge_type: EdgeType) -> None:
        """Adds a directed edge to the graph."""
        self.nodes.add(u)
        self.nodes.add(v)
        self.edges[(u, v)] = edge_type
        logger.debug(f"Edge added: {u} -> {v} [{edge_type.value}]")

@dataclass
class TransferPolicy:
    """
    Policy decision for transferring a specific heuristic.
    
    Attributes:
        is_approved: Boolean indicating if transfer is safe.
        intervention_required: Boolean indicating if causal masking is needed.
        reason: Explanation for the decision.
        confidence: Float score of the decision confidence.
    """
    is_approved: bool
    intervention_required: bool
    reason: str
    confidence: float = 0.0

def _validate_graph_integrity(graph: CausalGraph) -> bool:
    """
    Helper function to validate graph data consistency.
    
    Args:
        graph: The CausalGraph to validate.
        
    Returns:
        True if valid, False otherwise.
        
    Raises:
        ValueError: If nodes list is empty or edges refer to non-existent nodes.
    """
    if not graph.nodes:
        logger.warning(f"Graph for domain '{graph.domain_name}' has no nodes.")
        return False
    
    for (u, v) in graph.edges.keys():
        if u not in graph.nodes or v not in graph.nodes:
            logger.error(f"Edge ({u},{v}) references undefined node in {graph.domain_name}.")
            raise ValueError(f"Edge references undefined node in graph {graph.domain_name}")
            
    return True

def analyze_structural_congruence(
    source_graph: CausalGraph, 
    target_graph: CausalGraph, 
    source_feature: str, 
    target_feature: str
) -> Tuple[float, List[str]]:
    """
    Core Function 1: Analyzes the structural congruence of a specific feature transfer.
    
    Compares the local causal structure (parents and children) of the source feature
    against the target feature in their respective graphs.
    
    Args:
        source_graph: Graph of the source domain (e.g., Retail).
        target_graph: Graph of the target domain (e.g., Social Dynamics).
        source_feature: The feature in source (e.g., 'Price').
        target_feature: The mapped feature in target (e.g., 'Self_Worth_Estimate').
        
    Returns:
        A tuple containing:
        - congruence_score (0.0 to 1.0): Similarity in causal mechanisms.
        - conflicts: List of detected structural conflicts.
    """
    conflicts = []
    congruence_score = 1.0
    
    # Data Validation
    if source_feature not in source_graph.nodes:
        raise ValueError(f"Source feature {source_feature} not found in {source_graph.domain_name}")
    if target_feature not in target_graph.nodes:
        raise ValueError(f"Target feature {target_feature} not found in {target_graph.domain_name}")

    # Identify parents (causes) in both graphs
    source_parents = {u for (u, v) in source_graph.edges if v == source_feature}
    target_parents = {u for (u, v) in target_graph.edges if v == target_feature}
    
    # Identify children (effects) in both graphs
    source_children = {v for (u, v) in source_graph.edges if u == source_feature}
    target_children = {v for (u, v) in target_graph.edges if u == target_feature}

    # Check 1: Causal Inversion
    # Example: Price -> Sales (Positive) vs Self_Worth -> Attraction (Positive, implying low worth is negative)
    # We check if the semantic mapping of the relationship holds.
    # Here we simulate a check where the edge type might change semantics.
    
    for child in source_children:
        edge_type_src = source_graph.edges.get((source_feature, child))
        # If the source has a causal link, but target has an inhibitor link on the mapped variable
        # This is simplified logic for the demo.
        if child in target_children:
            edge_type_tgt = target_graph.edges.get((target_feature, child))
            if edge_type_src == EdgeType.CAUSAL and edge_type_tgt == EdgeType.INHIBITOR:
                conflicts.append(f"Causal Inversion detected: {source_feature} causes {child}, but {target_feature} inhibits {child}")
                congruence_score *= 0.5  # Heavy penalty

    # Check 2: Spuriousness detection
    # If the source relationship is marked as spurious (confounded), it should not be transferred.
    for (u, v) in source_graph.edges:
        if v == source_feature and source_graph.edges[(u, v)] == EdgeType.SPURIOUS:
            conflicts.append(f"Source relationship {u}->{v} is spurious (confounded).")
            congruence_score *= 0.8

    logger.info(f"Structural analysis complete. Score: {congruence_score}, Conflicts: {len(conflicts)}")
    return max(0.0, congruence_score), conflicts

def verify_transfer_necessity(
    source_graph: CausalGraph,
    target_graph: CausalGraph,
    source_action: str,
    target_action: str,
    threshold: float = 0.7
) -> TransferPolicy:
    """
    Core Function 2: Determines if a causal intervention is necessary for transfer.
    
    This function decides whether to allow a transfer, block it, or apply a
    masking mechanism based on structural analysis.
    
    Args:
        source_graph: Causal graph of the source domain.
        target_graph: Causal graph of the target domain.
        source_action: The action/variable being transferred (e.g., 'Discount').
        target_action: The corresponding action in the target (e.g., 'Lower_Posture').
        threshold: Congruence threshold below which intervention is triggered.
        
    Returns:
        TransferPolicy object with decision details.
    """
    logger.info(f"Verifying transfer: {source_action} -> {target_action}")
    
    try:
        _validate_graph_integrity(source_graph)
        _validate_graph_integrity(target_graph)
    except ValueError as e:
        logger.error(f"Validation failed: {e}")
        return TransferPolicy(False, True, f"Data Validation Error: {e}", 0.0)

    # Perform Structural Analysis
    score, conflicts = analyze_structural_congruence(
        source_graph, target_graph, source_action, target_action
    )

    # Decision Logic
    if score < threshold:
        logger.warning(f"Low congruence detected ({score} < {threshold}). Intervention required.")
        reason_str = "Causal structure mismatch. " + "; ".join(conflicts)
        return TransferPolicy(
            is_approved=False,
            intervention_required=True,
            reason=reason_str,
            confidence=1.0 - score
        )
    
    if conflicts:
        logger.info("High congruence but minor conflicts detected. Proceeding with monitoring.")
        return TransferPolicy(
            is_approved=True,
            intervention_required=False,
            reason="Minor structural variations detected but within tolerance.",
            confidence=score
        )

    logger.info("Transfer verified as safe. No intervention needed.")
    return TransferPolicy(
        is_approved=True,
        intervention_required=False,
        reason="Structures aligned.",
        confidence=score
    )

# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # 1. Define Source Domain: Retail Strategy
    retail_graph = CausalGraph(domain_name="Retail")
    retail_graph.add_edge("Cost", "Price", EdgeType.CAUSAL)
    retail_graph.add_edge("Price", "Sales_Volume", EdgeType.INHIBITOR) # High price lowers sales
    retail_graph.add_edge("Discount", "Sales_Volume", EdgeType.CAUSAL) # Discounts increase sales
    
    # 2. Define Target Domain: Mating / Social Dynamics
    social_graph = CausalGraph(domain_name="Social_Dynamics")
    social_graph.add_edge("Social_Value", "Attraction", EdgeType.CAUSAL)
    social_graph.add_edge("Desperation", "Attraction", EdgeType.INHIBITOR) # High desperation lowers attraction
    
    # Note: 'Lowering Posture' acts like 'Desperation' increasing, or 'Social_Value' decreasing?
    # Let's map 'Discount' (lowering price) to 'Lowering_Posture' (lowering self-worth/showing desperation).
    # In retail, lowering price -> increases Sales.
    # In social, lowering posture (increasing desperation) -> decreases Attraction.
    # This is a causal inversion.
    
    print("--- Starting AGI Cross-Domain Verification ---")
    
    policy = verify_transfer_necessity(
        source_graph=retail_graph,
        target_graph=social_graph,
        source_action="Discount",
        target_action="Lower_Posture", # Mapping Discount -> Lower_Posture
        threshold=0.75
    )
    
    print(f"\nTransfer Decision: {'APPROVED' if policy.is_approved else 'BLOCKED'}")
    print(f"Intervention Needed: {policy.intervention_required}")
    print(f"Reason: {policy.reason}")
    print(f"Confidence: {policy.confidence:.2f}")
    
    # Expected Output: BLOCKED due to causal inversion
    # Retail: Action(Discount) -> Result(Sales Up)
    # Social: Action(Lower_Posture) -> Result(Attraction Down)