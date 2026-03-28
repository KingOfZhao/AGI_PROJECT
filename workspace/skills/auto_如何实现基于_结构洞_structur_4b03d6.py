"""
Module: structural_hole_node_elimination
Description: Implements a topology-aware node elimination algorithm based on Structural Hole theory.
             Distinguishes between high-value 'Bridge Nodes' and low-value 'Island Nodes'.
Author: Senior Python Engineer (AGI System)
"""

import logging
import networkx as nx
from typing import Dict, List, Set, Tuple, Any, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeEliminationError(Exception):
    """Custom exception for node elimination errors."""
    pass


def validate_graph(graph: nx.Graph) -> None:
    """
    Validates the input graph to ensure it meets the algorithm requirements.
    
    Args:
        graph (nx.Graph): The network graph to validate.
        
    Raises:
        NodeEliminationError: If the graph is empty or invalid.
    """
    if not isinstance(graph, (nx.Graph, nx.DiGraph)):
        raise NodeEliminationError("Input must be a NetworkX Graph or DiGraph object.")
    
    if graph.number_of_nodes() == 0:
        raise NodeEliminationError("Graph cannot be empty.")
    
    logger.debug(f"Graph validated: {graph.number_of_nodes()} nodes, {graph.number_of_nodes()} edges.")


def calculate_structural_hole_metrics(graph: nx.Graph) -> Dict[Any, Dict[str, float]]:
    """
    Core Function 1: Calculates metrics relevant to Structural Hole theory.
    
    Focuses on:
    1. Constraint (Constraint Score): High constraint = Few structural holes = Redundant connections.
       Low constraint = High structural hole potential.
    2. Edge Weight/Importance: Proxy for semantic density or interaction strength.
    
    Args:
        graph (nx.Graph): Network graph. Can be weighted.
        
    Returns:
        Dict[Any, Dict[str, float]]: A dictionary mapping node IDs to their metrics.
    """
    metrics = {}
    
    # NetworkX constraint calculation is O(N^2) or O(N*E) depending on implementation.
    # It measures the extent to which a node's contacts are connected to one another.
    # Low constraint indicates the node acts as a bridge between unconnected parties.
    try:
        constraint_scores = nx.constraint(graph)
    except Exception as e:
        logger.error(f"Failed to calculate constraint scores: {e}")
        constraint_scores = {n: 0.0 for n in graph.nodes()}
        
    for node in graph.nodes():
        # Semantic density proxy: Degree or Sum of weights
        degree = graph.degree(node, weight='weight')
        
        metrics[node] = {
            'constraint': constraint_scores.get(node, 0.0),
            'degree': degree,
            'is_island': degree <= 1 # Simple heuristic for island detection
        }
        
    logger.info(f"Calculated structural metrics for {len(metrics)} nodes.")
    return metrics


def identify_elimination_candidates(
    graph: nx.Graph, 
    metrics: Dict[Any, Dict[str, float]], 
    constraint_threshold: float = 0.4,
    degree_threshold: int = 2
) -> Tuple[List[Any], List[Any]]:
    """
    Core Function 2: Classifies nodes into 'Bridge Nodes' (Keep) and 'Island Nodes' (Eliminate).
    
    Logic:
    - Bridge Node (Structural Hole): Low constraint (connects disparate groups) AND sufficient degree.
    - Island Node (Isolate): Low degree (edge of network) OR High constraint but low value.
    
    Args:
        graph (nx.Graph): The network graph.
        metrics (Dict): Pre-calculated metrics from calculate_structural_hole_metrics.
        constraint_threshold (float): Nodes with constraint below this are potential bridges.
        degree_threshold (int): Minimum degree to not be considered an island immediately.
        
    Returns:
        Tuple[List[Any], List[Any]]: (list_of_bridge_nodes, list_of_island_nodes_to_eliminate)
    """
    bridge_nodes = []
    island_nodes = []
    
    for node, data in metrics.items():
        node_constraint = data['constraint']
        node_degree = data['degree']
        
        # Case 1: True Bridge (Structural Hole)
        # Low constraint means the node connects clusters that don't connect to each other directly.
        # Even if semantic content is low (not handled here, but assumed), topology dictates keeping it.
        if node_constraint < constraint_threshold and node_degree >= degree_threshold:
            bridge_nodes.append(node)
            logger.debug(f"Node {node} identified as BRIDGE (Constraint: {node_constraint:.3f})")
            
        # Case 2: Island / Peripheral Node
        # Degree 1 usually means a leaf node. If it's not part of a dense core, it's an island.
        # Also, if a node has very high degree but is extremely redundant (high constraint),
        # it might be a candidate for pruning in some contexts, but here we focus on Islands.
        elif node_degree < degree_threshold:
            island_nodes.append(node)
            logger.debug(f"Node {node} identified as ISLAND (Degree: {node_degree})")
            
        # Case 3: The Middle Ground (Standard nodes)
        # Not a critical bridge, not an island. Keep by default.
        else:
            pass

    logger.info(f"Classification complete. Bridges: {len(bridge_nodes)}, Islands: {len(island_nodes)}")
    return bridge_nodes, island_nodes


def run_elimination_pipeline(
    graph: nx.Graph, 
    constraint_threshold: float = 0.4, 
    degree_threshold: int = 2
) -> nx.Graph:
    """
    Helper Function: Orchestrates the full elimination pipeline.
    
    Args:
        graph (nx.Graph): Input graph.
        constraint_threshold (float): Threshold for structural hole detection.
        degree_threshold (int): Threshold for island detection.
        
    Returns:
        nx.Graph: The pruned graph with island nodes removed.
    """
    try:
        validate_graph(graph)
    except NodeEliminationError as e:
        logger.error(f"Pipeline halted due to validation error: {e}")
        raise

    # 1. Calculate Metrics
    metrics = calculate_structural_hole_metrics(graph)
    
    # 2. Identify Candidates
    bridges, islands = identify_elimination_candidates(
        graph, 
        metrics, 
        constraint_threshold, 
        degree_threshold
    )
    
    # 3. Execute Elimination (Create a copy to preserve original)
    pruned_graph = graph.copy()
    pruned_graph.remove_nodes_from(islands)
    
    logger.info(f"Removed {len(islands)} nodes. New graph size: {pruned_graph.number_of_nodes()}")
    
    return pruned_graph


# --- Usage Example and Demonstration ---
if __name__ == "__main__":
    # Create a dummy graph representing a scenario
    # Cluster A: 1-2-3
    # Cluster B: 4-5-6
    # Bridge Node: 0 (Connects A and B)
    # Island Node: 99 (Connects only to 1)
    
    G = nx.Graph()
    
    # Cluster A
    G.add_edges_from([(1, 2), (2, 3), (3, 1)]) 
    # Cluster B
    G.add_edges_from([(4, 5), (5, 6), (6, 4)])
    
    # Bridge Connections (Node 0 connects A and B)
    G.add_edges_from([(0, 1), (0, 4)])
    
    # Island Connection (Node 99 is an outlier)
    G.add_edge(1, 99)
    
    # Add some random noise to make it realistic
    G.add_edge(10, 11) # Another small island component
    
    print(f"Original Graph Nodes: {G.nodes()}")
    print(f"Original Graph Edges: {G.edges()}")
    
    # Run the pipeline
    try:
        # Expecting Node 0 to be kept (Bridge)
        # Expecting Node 99 and 10, 11 to be removed (Islands)
        pruned_G = run_elimination_pipeline(G, constraint_threshold=0.5, degree_threshold=2)
        
        print("\n--- Results ---")
        print(f"Remaining Nodes: {pruned_G.nodes()}")
        
        # Verify Node 0 is still there
        assert 0 in pruned_G.nodes(), "Bridge node 0 was incorrectly eliminated!"
        
        # Verify Node 99 is gone
        assert 99 not in pruned_G.nodes(), "Island node 99 was incorrectly preserved!"
        
        print("Test passed: Bridge preserved, Islands removed.")
        
    except NodeEliminationError as e:
        print(f"Algorithm failed: {e}")