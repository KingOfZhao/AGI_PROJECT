"""
Module: macro_event_causal_chain
Description: AGI Skill for constructing multi-level causal chains for complex macro events.
             This module differentiates between 'Established' facts and 'Hypothetical' inferences.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import json
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Data Structures and Enums

class NodeType(Enum):
    """Enumeration for the type of causal node."""
    ESTABLISHED = "Established"  # Verified, historical facts
    HYPOTHETICAL = "Hypothetical"  # Speculative, inferred causes/effects

class NodeCategory(Enum):
    """Category of the event node."""
    TRIGGER = "Trigger"
    MECHANISM = "Mechanism"
    OUTCOME = "Outcome"
    CONTEXT = "Context"

@dataclass
class CausalNode:
    """Represents a single node in the causal graph."""
    node_id: str
    label: str
    type: NodeType
    category: NodeCategory
    description: str
    confidence: float = 1.0  # 1.0 for Established, 0.0-1.0 for Hypothetical
    parent_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence for node {self.node_id} must be between 0.0 and 1.0.")
        if self.type == NodeType.ESTABLISHED and self.confidence != 1.0:
            logger.warning(f"Established node {self.node_id} usually has confidence 1.0.")

@dataclass
class CausalChainGraph:
    """Container for the entire causal analysis graph."""
    event_name: str
    analysis_timestamp: str
    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    
    def add_node(self, node: CausalNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"Node ID {node.node_id} already exists.")
        self.nodes[node.node_id] = node

# 3. Core Functions

def validate_macro_event_input(event_description: str) -> bool:
    """
    Helper function to validate the input event description.
    
    Args:
        event_description (str): The raw text description of the event.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(event_description, str):
        logger.error("Input must be a string.")
        return False
    if len(event_description.strip()) < 10:
        logger.error("Input description is too short for meaningful analysis.")
        return False
    return True

def construct_causal_chain(event_description: str, max_depth: int = 3) -> CausalChainGraph:
    """
    Constructs a multi-level causal chain graph for a given macro event.
    
    In a real AGI system, this would interface with a Knowledge Graph or LLM.
    Here, we simulate the logic for a specific scenario (Stock Market Crash).
    
    Args:
        event_description (str): The complex macro event (e.g., "2024 Global Market Correction").
        max_depth (int): Maximum depth of the causal chain hierarchy.
        
    Returns:
        CausalChainGraph: The constructed graph object.
        
    Raises:
        ValueError: If input validation fails.
    """
    logger.info(f"Starting causal analysis for: {event_description}")
    
    # Input Validation
    if not validate_macro_event_input(event_description):
        raise ValueError("Invalid input event description provided.")

    # Initialize Graph
    graph = CausalChainGraph(
        event_name=event_description,
        analysis_timestamp=datetime.utcnow().isoformat()
    )

    try:
        # --- Layer 0: The Core Event (Root) ---
        # This is the anchor, always Established if analyzing a historical event
        root_node = CausalNode(
            node_id="E0",
            label="Global Tech Index Crashes 15%",
            type=NodeType.ESTABLISHED,
            category=NodeCategory.OUTCOME,
            description="Sudden massive sell-off in technology stocks.",
            confidence=1.0
        )
        graph.add_node(root_node)

        # --- Layer 1: Immediate Triggers ---
        # Directly observable market behaviors causing the crash
        node_l1_1 = CausalNode(
            node_id="L1_1",
            label="Mass Algorithmic Sell-off",
            type=NodeType.ESTABLISHED,
            category=NodeCategory.TRIGGER,
            description="High-frequency trading bots hit stop-loss limits simultaneously.",
            confidence=1.0,
            parent_ids=["E0"]
        )
        graph.add_node(node_l1_1)

        node_l1_2 = CausalNode(
            node_id="L1_2",
            label="Liquidity Dry Up",
            type=NodeType.ESTABLISHED,
            category=NodeCategory.MECHANISM,
            description="Market makers withdrew buy orders causing slippage.",
            confidence=0.95,
            parent_ids=["E0"]
        )
        graph.add_node(node_l1_2)

        # --- Layer 2: Underlying Causes (Mixed) ---
        # Why did the algorithms sell? (Hypothesis vs Fact)
        node_l2_1 = CausalNode(
            node_id="L2_1",
            label="Fed Interest Rate Hike",
            type=NodeType.ESTABLISHED,
            category=NodeCategory.TRIGGER,
            description="Central bank raised rates by 50bps unexpectedly.",
            confidence=1.0,
            parent_ids=["L1_1"]
        )
        graph.add_node(node_l2_1)

        node_l2_2 = CausalNode(
            node_id="L2_2",
            label="Rumored Major Hedge Fund Insolvency",
            type=NodeType.HYPOTHETICAL,
            category=NodeCategory.TRIGGER,
            description="Unverified reports of a major fund liquidating positions.",
            confidence=0.65,
            parent_ids=["L1_1", "L1_2"]
        )
        graph.add_node(node_l2_2)

        # --- Layer 3: Deep Structural Factors ---
        # Long-term context
        node_l3_1 = CausalNode(
            node_id="L3_1",
            label="Overvalued Market P/E Ratios",
            type=NodeType.ESTABLISHED,
            category=NodeCategory.CONTEXT,
            description="Market P/E ratios were historically high prior to crash.",
            confidence=1.0,
            parent_ids=["L2_1"]
        )
        graph.add_node(node_l3_1)
        
        node_l3_2 = CausalNode(
            node_id="L3_2",
            label="Shadow Banking System Instability",
            type=NodeType.HYPOTHETICAL,
            category=NodeCategory.CONTEXT,
            description="Theoretical model suggesting leverage buildup in unregulated sectors.",
            confidence=0.45,
            parent_ids=["L2_2"]
        )
        graph.add_node(node_l3_2)

        logger.info(f"Successfully constructed graph with {len(graph.nodes)} nodes.")
        
    except Exception as e:
        logger.error(f"Error during graph construction: {str(e)}")
        raise RuntimeError("Failed to construct causal graph.") from e

    return graph

def analyze_graph_integrity(graph: CausalChainGraph) -> Dict[str, Union[int, float, List[str]]]:
    """
    Analyzes the constructed graph for integrity, depth, and hypothesis ratio.
    
    Args:
        graph (CausalChainGraph): The graph object to analyze.
        
    Returns:
        Dict: A summary report containing metrics about the causal chain.
    """
    logger.info("Analyzing graph integrity...")
    
    total_nodes = len(graph.nodes)
    if total_nodes == 0:
        return {"status": "empty"}

    established_nodes = []
    hypothetical_nodes = []
    isolated_nodes = []

    for node_id, node in graph.nodes.items():
        # Categorize by type
        if node.type == NodeType.ESTABLISHED:
            established_nodes.append(node_id)
        else:
            hypothetical_nodes.append(node_id)
            
        # Check connectivity (excluding root)
        if not node.parent_ids and node_id != "E0":
            isolated_nodes.append(node_id)
            logger.warning(f"Node {node_id} is isolated (no parents).")

    report = {
        "total_nodes": total_nodes,
        "established_count": len(established_nodes),
        "hypothetical_count": len(hypothetical_nodes),
        "hypothesis_ratio": round(len(hypothetical_nodes) / total_nodes, 2),
        "isolated_nodes": isolated_nodes,
        "max_depth_achieved": 3,  # Simulated logic
        "status": "valid" if not isolated_nodes else "warning"
    }
    
    logger.info(f"Analysis complete. Hypothesis Ratio: {report['hypothesis_ratio']}")
    return report

# 4. Utility and Output

def export_chain_to_json(graph: CausalChainGraph, file_path: Optional[str] = None) -> str:
    """
    Exports the causal chain to a JSON string or file.
    
    Args:
        graph (CausalChainGraph): The graph to export.
        file_path (Optional[str]): If provided, saves to file.
        
    Returns:
        str: JSON string representation.
    """
    logger.info("Exporting graph to JSON...")
    
    # Convert dataclasses to dicts
    graph_dict = {
        "event_name": graph.event_name,
        "timestamp": graph.analysis_timestamp,
        "nodes": [asdict(node) for node in graph.nodes.values()]
    }
    
    json_str = json.dumps(graph_dict, indent=4, default=str)
    
    if file_path:
        try:
            with open(file_path, 'w') as f:
                f.write(json_str)
            logger.info(f"Graph saved to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save file: {e}")
            
    return json_str

# 5. Main Execution / Example

if __name__ == "__main__":
    # Example Usage
    input_event = "The 'Black Swan' Market Correction of 2024"
    
    try:
        # Step 1: Construct the chain
        causal_graph = construct_causal_chain(input_event)
        
        # Step 2: Analyze integrity
        integrity_report = analyze_graph_integrity(causal_graph)
        print(f"\n--- Integrity Report ---\n{json.dumps(integrity_report, indent=2)}")
        
        # Step 3: Visualize/Output (Console)
        print("\n--- Causal Chain Structure ---")
        for node_id, node in causal_graph.nodes.items():
            prefix = "[FACT]" if node.type == NodeType.ESTABLISHED else "[HYPOTHESIS]"
            parents = ", ".join(node.parent_ids) if node.parent_ids else "ROOT"
            print(f"{prefix} ID: {node_id} | Label: {node.label} | Parents: [{parents}]")

        # Step 4: Export
        # export_chain_to_json(causal_graph, "causal_chain.json")
        
    except Exception as e:
        logger.critical(f"Application failed: {e}")