"""
Module: auto_证伪反馈闭环_人机共生中_人类实践证伪_a444dc

This module implements a structured 'Falsification Feedback Loop' for AGI systems.
It addresses the challenge of mapping unstructured physical execution failures
(backpropagated from humans) to the cognitive network (Knowledge Graph).

Core Mechanism:
Instead of simple negative sampling (which treats data as binary T/F), this module
performs 'Structural Weakening'. It parses failure reasons, locates the specific
nodes (concepts/skills) in the graph, and precisely attenuates edge weights or
prunes connections based on the severity of the failure.

Author: Senior Python Engineer
License: MIT
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_DECAY_RATE = 0.85  # Factor by which weight is reduced
PRUNE_THRESHOLD = 0.05    # Weight below which edge is severed
MAX_REASON_LENGTH = 1000

@dataclass
class CognitiveNode:
    """Represents a node in the cognitive network."""
    id: str
    concept_type: str
    truth_weight: float = 1.0  # 1.0 = Absolute Truth, 0.0 = Absolute Falsehood
    metadata: Dict = field(default_factory=dict)

@dataclass
class CognitiveEdge:
    """Represents a connection between nodes."""
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0  # Strength of correlation

class CognitiveNetwork:
    """
    A mock representation of an AGI's Knowledge Graph.
    In a real scenario, this would interface with a vector DB or Graph DB.
    """
    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}
        self.edges: List[CognitiveEdge] = []
        self._initialize_mock_network()

    def _initialize_mock_network(self):
        """Initialize with some dummy data for demonstration."""
        # Nodes
        self.nodes["skill_grasp"] = CognitiveNode("skill_grasp", "skill")
        self.nodes["obj_cup"] = CognitiveNode("obj_cup", "entity")
        self.nodes["prop_fragile"] = CognitiveNode("prop_fragile", "property")
        self.nodes["context_water_boiling"] = CognitiveNode("context_water_boiling", "context")
        
        # Edges (Relationships)
        self.edges.append(CognitiveEdge("skill_grasp", "obj_cup", "applicable_to", 1.0))
        self.edges.append(CognitiveEdge("obj_cup", "prop_fragile", "has_property", 0.8))
        self.edges.append(CognitiveEdge("context_water_boiling", "prop_fragile", "increases_risk", 0.5))

    def find_nodes_by_keywords(self, keywords: List[str]) -> List[str]:
        """Simple keyword matching for node retrieval."""
        # In production, use semantic search/embeddings
        found_ids = []
        for node_id, node in self.nodes.items():
            for kw in keywords:
                if kw.lower() in node_id.lower():
                    found_ids.append(node_id)
        return list(set(found_ids))

    def update_node_truth(self, node_id: str, penalty: float):
        """Decreases the truth weight of a node."""
        if node_id in self.nodes:
            old_weight = self.nodes[node_id].truth_weight
            new_weight = max(0.0, old_weight - penalty)
            self.nodes[node_id].truth_weight = new_weight
            logger.info(f"Node '{node_id}' weight updated: {old_weight:.2f} -> {new_weight:.2f}")

    def attenuate_edge(self, source_id: str, target_id: str, factor: float):
        """Reduces the weight of a specific connection."""
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                old_weight = edge.weight
                edge.weight *= factor
                if edge.weight < PRUNE_THRESHOLD:
                    edge.weight = 0.0
                    logger.warning(f"Edge pruned: {source_id}->{target_id} (Weight dropped to 0)")
                else:
                    logger.info(f"Edge attenuated: {source_id}->{target_id} ({old_weight:.2f}->{edge.weight:.2f})")
                return
        logger.warning(f"Edge not found: {source_id}->{target_id}")

# --- Core Functions ---

def parse_unstructured_failure(failure_log: str, network_context: Optional[List[str]] = None) -> Dict:
    """
    Parses unstructured failure text into structured feedback entities.
    
    Uses rule-based extraction (simulated NLP) to identify:
    1. Error Type (e.g., 'Physical Damage', 'Logic Error')
    2. Severity (0.0 to 1.0)
    3. Suspected Nodes (keywords mapped to graph IDs)
    
    Args:
        failure_log (str): The raw text description of why the skill failed.
        network_context (Optional[List[str]]): IDs of nodes involved in the original plan.
        
    Returns:
        Dict: Structured feedback payload.
    """
    if not failure_log or len(failure_log) > MAX_REASON_LENGTH:
        raise ValueError("Invalid failure log input.")
        
    logger.info(f"Parsing failure log: '{failure_log}'")
    
    # 1. Severity Analysis
    severity = 0.5 # Default
    if "catastrophic" in failure_log.lower() or "broken" in failure_log.lower():
        severity = 1.0
    elif "minor" in failure_log.lower() or "inefficient" in failure_log.lower():
        severity = 0.2
    
    # 2. Keyword Extraction (Mock NLP)
    # Map words to potential node IDs
    keywords = re.findall(r'\b\w+\b', failure_log.lower())
    suspected_node_ids = []
    
    # Simple heuristic mapping
    mapping = {
        "cup": "obj_cup",
        "grasp": "skill_grasp",
        "fragile": "prop_fragile",
        "boiling": "context_water_boiling"
    }
    
    for word in keywords:
        if word in mapping:
            suspected_node_ids.append(mapping[word])
            
    # If context is provided, prioritize intersection
    if network_context:
        suspected_node_ids = [nid for nid in suspected_node_ids if nid in network_context]

    return {
        "raw_text": failure_log,
        "severity": severity,
        "suspected_nodes": list(set(suspected_node_ids)),
        "error_category": "execution_failure"
    }

def apply_falsification_to_network(
    network: CognitiveNetwork, 
    structured_feedback: Dict,
    decay_rate: float = DEFAULT_DECAY_RATE
) -> bool:
    """
    Applies the structured feedback to the cognitive network.
    
    This is the core 'Self-Correction' mechanism. It weakens the weights of
    nodes and edges associated with the failure.
    
    Args:
        network (CognitiveNetwork): The AGI knowledge graph instance.
        structured_feedback (Dict): The output from `parse_unstructured_failure`.
        decay_rate (float): How much to weaken the connections (0.0 to 1.0).
        
    Returns:
        bool: True if updates were successfully applied.
    """
    if not (0.0 < decay_rate < 1.0):
        logger.error(f"Invalid decay rate: {decay_rate}")
        return False
        
    severity = structured_feedback.get("severity", 0.5)
    target_nodes = structured_feedback.get("suspected_nodes", [])
    
    if not target_nodes:
        logger.warning("No target nodes identified for falsification.")
        return False

    penalty = severity * (1.0 - decay_rate)
    
    logger.info(f"Applying Falsification: Severity={severity}, Penalty={penalty:.3f}")
    
    for node_id in target_nodes:
        # 1. Weaken the Node itself (The concept might be false)
        network.update_node_truth(node_id, penalty)
        
        # 2. Weaken associated edges (The context might be wrong)
        # Find edges connected to this node
        for edge in network.edges:
            if edge.source_id == node_id or edge.target_id == node_id:
                # Attenuate connection strength
                network.attenuate_edge(edge.source_id, edge.target_id, decay_rate)
                
    return True

# --- Helper Functions ---

def visualize_impact(network: CognitiveNetwork):
    """
    Helper to visualize the current state of the network (Text-based).
    """
    print("\n--- Cognitive Network Status ---")
    print("Nodes (Truth Weights):")
    for nid, node in network.nodes.items():
        status = "OK" if node.truth_weight > 0.5 else "DUBIOUS"
        print(f"  [{status}] {nid}: {node.truth_weight:.2f}")
    
    print("\nEdges (Connection Strength):")
    for edge in network.edges:
        status = "ACTIVE" if edge.weight > PRUNE_THRESHOLD else "SEVERED"
        print(f"  [{status}] {edge.source_id} -> {edge.relation} -> {edge.target_id} ({edge.weight:.2f})")
    print("--------------------------------")

# --- Main Execution / Usage Example ---

if __name__ == "__main__":
    # Initialize the Cognitive Network
    kn = CognitiveNetwork()
    
    print("Initial State:")
    visualize_impact(kn)
    
    # SCENARIO: Human attempts to grasp a cup.
    # The AI assumed a standard grasp (skill_grasp -> obj_cup).
    # It failed because the water was boiling and the cup was fragile,
    # causing the cup to break.
    
    failure_description = """
    The execution failed catastrophically. The robot tried to perform a 'grasp' 
    on the 'cup', but the 'boiling' water made it slip, and the 'fragile' 
    nature of the cup caused it to break.
    """
    
    involved_context = ["skill_grasp", "obj_cup", "context_water_boiling"]
    
    try:
        # Step 1: Map unstructured failure to structured data
        feedback_data = parse_unstructured_failure(
            failure_log=failure_description,
            network_context=involved_context
        )
        
        print(f"\nParsed Feedback: {feedback_data}")
        
        # Step 2: Apply falsification (Backpropagation of Error)
        success = apply_falsification_to_network(
            network=kn, 
            structured_feedback=feedback_data,
            decay_rate=0.7 # Reduce weight by 30% based on severity
        )
        
        if success:
            print("\nFalsification applied successfully.")
            visualize_impact(kn)
        else:
            print("\nFailed to apply falsification.")
            
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)