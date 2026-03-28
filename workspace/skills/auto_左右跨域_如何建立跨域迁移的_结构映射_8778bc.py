"""
Module: auto_左右跨域_如何建立跨域迁移的_结构映射_8778bc
Description: 
    Implements a structural mapping algorithm for cross-domain cognitive transfer.
    This module identifies isomorphisms between different skill domains by ignoring
    surface features (e.g., 'vegetables' vs 'data packets') and extracting underlying
    control structures (e.g., 'restock threshold' vs 'auto-scaling policy').

Domain: cognitive_science
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class StructuralNode:
    """
    Represents an abstract node in the cognitive structure.
    Surface features are stripped away to reveal the cognitive role.
    """
    id: str
    abstract_type: str  # e.g., "Resource", "Controller", "Threshold"
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CognitiveGraph:
    """
    Represents the directed graph structure of a domain.
    """
    nodes: Dict[str, StructuralNode] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)  # (from_id, to_id, relation_type)

# --- Helper Function ---

def _abstract_surface_feature(surface_label: str, context: Dict[str, Any]) -> str:
    """
    Helper function to map surface features to abstract cognitive types.
    
    This simulates the cognitive process of ignoring irrelevant details (vegetables vs data)
    and focusing on functional roles (consumable resource).
    
    Args:
        surface_label: The concrete name of the entity (e.g., "tomato", "packet").
        context: Additional context about the entity.
        
    Returns:
        The abstract cognitive type (e.g., "Resource").
    """
    # A simplified abstraction dictionary for demonstration
    abstraction_rules = {
        # Inventory Domain
        "vegetable": "Resource",
        "fruit": "Resource",
        "stock": "Resource",
        "vendor": "Controller",
        "restock_action": "RegulationAction",
        "low_stock_threshold": "Threshold",
        
        # Server Domain
        "data_packet": "Resource",
        "request": "Resource",
        "cpu_time": "Resource",
        "load_balancer": "Controller",
        "scale_up_action": "RegulationAction",
        "high_load_threshold": "Threshold",
        
        # Generic
        "money": "Resource",
        "energy": "Resource"
    }
    
    # Normalize input
    label_key = surface_label.lower().replace(" ", "_")
    
    # Check direct mapping
    if label_key in abstraction_rules:
        return abstraction_rules[label_key]
    
    # Heuristic based on context
    if "consumable" in context or "depletes" in context:
        return "Resource"
    if "manages" in context or "controls" in context:
        return "Controller"
    if "limit" in context or "boundary" in context:
        return "Threshold"
        
    logger.warning(f"Unknown surface feature '{surface_label}', defaulting to 'GenericEntity'")
    return "GenericEntity"

# --- Core Functions ---

def extract_cognitive_structure(domain_data: Dict[str, Any]) -> CognitiveGraph:
    """
    Core Function 1: Parses raw domain data into an abstract CognitiveGraph.
    
    This function validates the input, abstracts surface features, and builds
    the structural representation required for cross-domain comparison.
    
    Args:
        domain_data: A dictionary containing 'nodes' and 'edges'.
            Example:
            {
                "nodes": [{"id": "n1", "label": "vegetable", "props": {"type": "consumable"}}],
                "edges": [{"from": "n1", "to": "n2", "relation": "consumed_by"}]
            }
            
    Returns:
        CognitiveGraph: The abstracted structural representation.
        
    Raises:
        ValueError: If input data format is invalid.
    """
    logger.info("Starting extraction of cognitive structure...")
    
    # Data Validation
    if not isinstance(domain_data, dict):
        raise ValueError("domain_data must be a dictionary.")
    if "nodes" not in domain_data or "edges" not in domain_data:
        raise ValueError("domain_data must contain 'nodes' and 'edges' keys.")
    if not isinstance(domain_data["nodes"], list) or not isinstance(domain_data["edges"], list):
        raise ValueError("'nodes' and 'edges' must be lists.")

    graph = CognitiveGraph()
    
    # Process Nodes
    for node_data in domain_data["nodes"]:
        try:
            node_id = node_data["id"]
            surface_label = node_data.get("label", "unknown")
            context = node_data.get("props", {})
            
            # Perform Abstraction
            abstract_type = _abstract_surface_feature(surface_label, context)
            
            new_node = StructuralNode(
                id=node_id,
                abstract_type=abstract_type,
                attributes=context
            )
            graph.nodes[node_id] = new_node
            logger.debug(f"Abstracted node {node_id}: '{surface_label}' -> '{abstract_type}'")
            
        except KeyError as e:
            logger.error(f"Node data missing key: {e}")
            raise ValueError(f"Invalid node data format: {e}")

    # Process Edges
    for edge_data in domain_data["edges"]:
        try:
            u = edge_data["from"]
            v = edge_data["to"]
            rel = edge_data.get("relation", "related_to")
            
            # Boundary Check
            if u not in graph.nodes or v not in graph.nodes:
                logger.warning(f"Edge references non-existent node: {u} -> {v}. Skipping.")
                continue
                
            graph.edges.append((u, v, rel))
        except KeyError as e:
            logger.error(f"Edge data missing key: {e}")
            raise ValueError(f"Invalid edge data format: {e}")

    logger.info(f"Extraction complete. Graph contains {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    return graph

def compute_structural_mapping(source_graph: CognitiveGraph, target_graph: CognitiveGraph) -> Dict[str, str]:
    """
    Core Function 2: Identifies isomorphic mappings between source and target graphs.
    
    It calculates a similarity score based on node types and structural roles (neighbors).
    This allows mapping 'Vendor Inventory' to 'Server Capacity' despite different labels.
    
    Args:
        source_graph: The abstracted graph of the known domain.
        target_graph: The abstracted graph of the new domain.
        
    Returns:
        A dictionary mapping source_node_id -> target_node_id representing the best structural fit.
    """
    logger.info("Computing structural mapping between domains...")
    
    mapping_result = {}
    
    # Build adjacency lists for structural comparison
    def get_neighbors(graph: CognitiveGraph, node_id: str) -> List[str]:
        return [t for (f, t, _) in graph.edges if f == node_id] + \
               [f for (f, t, _) in graph.edges if t == node_id]

    # Greedy matching algorithm based on structural signatures
    # Signature = (AbstractType, Number of Incoming Edges, Number of Outgoing Edges)
    
    source_signatures = {}
    for nid, node in source_graph.nodes.items():
        in_deg = sum(1 for (_, t, _) in source_graph.edges if t == nid)
        out_deg = sum(1 for (f, _, _) in source_graph.edges if f == nid)
        source_signatures[nid] = (node.abstract_type, in_deg, out_deg)
        
    target_signatures = {}
    for nid, node in target_graph.nodes.items():
        in_deg = sum(1 for (_, t, _) in target_graph.edges if t == nid)
        out_deg = sum(1 for (f, _, _) in target_graph.edges if f == nid)
        target_signatures[nid] = (node.abstract_type, in_deg, out_deg)

    matched_target_ids = set()
    
    # Iterate through source nodes to find best match in target
    for s_id, s_sig in source_signatures.items():
        best_match_id = None
        best_score = -1
        
        for t_id, t_sig in target_signatures.items():
            if t_id in matched_target_ids:
                continue
                
            # Calculate similarity score
            score = 0
            # 1. Type Match (Weight: 2)
            if s_sig[0] == t_sig[0]:
                score += 2
            # 2. Structural Degree Match (Weight: 1)
            degree_diff = abs(s_sig[1] - t_sig[1]) + abs(s_sig[2] - t_sig[2])
            score -= degree_diff
            
            if score > best_score:
                best_score = score
                best_match_id = t_id
        
        if best_match_id and best_score >= 0: # Threshold to ensure minimum quality
            mapping_result[s_id] = best_match_id
            matched_target_ids.add(best_match_id)
            logger.info(f"Mapping established: {s_id} ({source_graph.nodes[s_id].abstract_type}) "
                        f"-> {best_match_id} ({target_graph.nodes[best_match_id].abstract_type})")
        else:
            logger.warning(f"No suitable structural match found for source node {s_id}")

    return mapping_result

# --- Usage Example ---

if __name__ == "__main__":
    # Example 1: Street Vendor Domain (Source)
    vendor_domain = {
        "nodes": [
            {"id": "v1", "label": "vegetable_stock", "props": {"type": "consumable"}},
            {"id": "v2", "label": "vendor", "props": {"role": "manager"}},
            {"id": "v3", "label": "restock_trigger", "props": {"type": "threshold"}}
        ],
        "edges": [
            {"from": "v1", "to": "v2", "relation": "monitored_by"},
            {"from": "v1", "to": "v3", "relation": "triggers"},
            {"from": "v3", "to": "v2", "relation": "alerts"}
        ]
    }

    # Example 2: Server Resource Domain (Target)
    server_domain = {
        "nodes": [
            {"id": "s1", "label": "data_packet_buffer", "props": {"type": "consumable"}},
            {"id": "s2", "label": "load_balancer", "props": {"role": "manager"}},
            {"id": "s3", "label": "cpu_threshold", "props": {"type": "threshold"}}
        ],
        "edges": [
            {"from": "s1", "to": "s2", "relation": "monitored_by"},
            {"from": "s1", "to": "s3", "relation": "triggers"},
            {"from": "s3", "to": "s2", "relation": "alerts"}
        ]
    }

    try:
        # 1. Extract Structures
        g_vendor = extract_cognitive_structure(vendor_domain)
        g_server = extract_cognitive_structure(server_domain)

        # 2. Compute Mapping
        mapping = compute_structural_mapping(g_vendor, g_server)

        print("\n--- Final Mapping Result ---")
        for src, tgt in mapping.items():
            print(f"Source Node '{src}' maps to Target Node '{tgt}'")
            
        # Expected: v1->s1 (Resource), v2->s2 (Controller), v3->s3 (Threshold)
        
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")