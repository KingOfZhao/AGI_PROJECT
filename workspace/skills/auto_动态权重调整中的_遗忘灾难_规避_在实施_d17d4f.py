"""
Module: auto_dynamic_forgetting_catastrophe_avoidance_d17d4f
Description:
    Implements a dynamic weight adjustment mechanism with 'Catastrophic Forgetting' avoidance.
    In the context of AGI cognitive network maintenance, this module ensures that when
    nodes are pruned (forgetting), the topological integrity of the network is preserved.
    It specifically protects 'Bridge Nodes' identified via Betweenness Centrality to
    maintain cross-domain connectivity.

Domain: Network Science / AGI Cognitive Architecture
"""

import logging
import networkx as nx
from typing import List, Dict, Set, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkTopologyError(Exception):
    """Custom exception for topology violations."""
    pass


def _validate_graph_integrity(G: nx.Graph) -> None:
    """
    Helper function to validate the input graph.
    
    Args:
        G (nx.Graph): The network graph to validate.
        
    Raises:
        TypeError: If input is not a NetworkX graph.
        ValueError: If graph is empty.
    """
    if not isinstance(G, (nx.Graph, nx.DiGraph)):
        raise TypeError("Input must be a NetworkX Graph or DiGraph object.")
    if G.number_of_nodes() == 0:
        raise ValueError("Graph cannot be empty.")
    logger.debug(f"Graph validated: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")


def calculate_bridge_vulnerability_scores(
    G: nx.Graph, 
    weight_attribute: str = 'weight'
) -> Dict[Any, float]:
    """
    Calculates a vulnerability score based on Betweenness Centrality and current edge weights.
    
    Nodes with high betweenness centrality act as bridges between clusters (domains).
    This function identifies these critical nodes.
    
    Args:
        G (nx.Graph): The cognitive network graph.
        weight_attribute (str): The key for edge weight data.
        
    Returns:
        Dict[Any, float]: A dictionary mapping node IDs to their vulnerability scores.
        
    Raises:
        NetworkTopologyError: If graph validation fails.
    """
    try:
        _validate_graph_integrity(G)
    except (TypeError, ValueError) as e:
        logger.error(f"Graph validation failed: {e}")
        raise NetworkTopologyError(e)

    logger.info("Calculating betweenness centrality for bridge node detection...")
    
    # Using betweenness centrality to find bridges. 
    # k=None calculates exact centrality (computationally expensive for large graphs).
    # In production, consider sampling (k=<sample_size>) for approximation.
    try:
        # Normalize by connected components if graph is disconnected
        centrality = nx.betweenness_centrality(G, weight=weight_attribute, normalized=True)
    except Exception as e:
        logger.error(f"Failed to calculate centrality: {e}")
        raise NetworkTopologyError("Centrality calculation failed.")

    logger.info(f"Calculated centrality for {len(centrality)} nodes.")
    return centrality


def safe_pruning_procedure(
    G: nx.Graph, 
    nodes_to_prune: List[Any], 
    bridge_threshold: float = 0.15,
    protection_policy: str = 'strict'
) -> Tuple[nx.Graph, Set[Any]]:
    """
    Performs dynamic weight adjustment (pruning) while avoiding catastrophic forgetting
    by protecting bridge nodes.
    
    Args:
        G (nx.Graph): The network graph.
        nodes_to_prune (List[Any]): List of node IDs targeted for removal.
        bridge_threshold (float): Centrality percentile (0.0 to 1.0) above which 
                                  a node is considered a 'Bridge Node'.
        protection_policy (str): 'strict' raises error if bridge is targeted.
                                 'skip' silently ignores bridge nodes in pruning list.
    
    Returns:
        Tuple[nx.Graph, Set[Any]]: The modified graph (copy) and the set of actually pruned nodes.
        
    Example:
        >>> import networkx as nx
        >>> G = nx.karate_club_graph()
        >>> targets = list(G.nodes())[0:5]
        >>> new_G, pruned = safe_pruning_procedure(G, targets, bridge_threshold=0.2)
        
    Raises:
        NetworkTopologyError: If protection policy is 'strict' and a bridge node is targeted.
    """
    _validate_graph_integrity(G)
    
    if not nodes_to_prune:
        logger.warning("Pruning list is empty. No action taken.")
        return G.copy(), set()

    # Data Validation: Check if nodes exist in graph
    missing_nodes = set(nodes_to_prune) - set(G.nodes())
    if missing_nodes:
        logger.warning(f"Nodes {missing_nodes} not found in graph. Skipping them.")
        nodes_to_prune = [n for n in nodes_to_prune if n in G.nodes()]

    # Step 1: Identify Bridge Nodes
    centrality_scores = calculate_bridge_vulnerability_scores(G)
    
    # Determine the threshold value based on distribution
    # Here we use a raw threshold, but could use np.percentile for dynamic adaptation
    protected_nodes = {
        node for node, score in centrality_scores.items() 
        if score >= bridge_threshold
    }
    
    logger.info(f"Identified {len(protected_nodes)} protected bridge nodes with threshold > {bridge_threshold}.")

    # Step 2: Apply Protection Logic
    final_prune_set = set()
    violations = []

    for node in nodes_to_prune:
        if node in protected_nodes:
            msg = f"Node {node} is a critical bridge (Centrality: {centrality_scores[node]:.4f}). Pruning blocked."
            if protection_policy == 'strict':
                violations.append(node)
                logger.error(msg)
            elif protection_policy == 'skip':
                logger.warning(msg + " Skipping node.")
            else:
                raise ValueError(f"Unknown protection policy: {protection_policy}")
        else:
            final_prune_set.add(node)

    if violations:
        raise NetworkTopologyError(
            f"Pruning aborted due to strict protection policy. Violations: {violations}"
        )

    # Step 3: Perform Removal (Simulated on a copy to preserve input)
    # In a real AGI system, this might modify the structure in place or return a delta
    modified_G = G.copy()
    
    # Check connectivity impact before removing (Simulated check)
    # If removing a node disconnects the graph, it implies it was a 'bridge' even if centrality was low (articulation point)
    # We add an extra safety check here for articulation points
    
    if nx.is_connected(modified_G):
        initial_components = nx.number_connected_components(modified_G)
    else:
        initial_components = nx.number_connected_components(modified_G)

    for node in final_prune_set:
        modified_G.remove_node(node)
        logger.debug(f"Node {node} removed.")
        
        # Post-removal topology check
        if nx.is_connected(modified_G) is False and initial_components == 1:
             logger.warning(f"Removal of {node} disconnected the graph. Topology integrity compromised.")
             # Logic to rollback or handle fragmentation could go here

    logger.info(f"Pruning complete. Removed {len(final_prune_set)} nodes.")
    return modified_G, final_prune_set


# ---------------------------------------------------------
# Usage Example / Self-Test
# ---------------------------------------------------------
if __name__ == "__main__":
    # Create a dummy 'Cognitive Network' (Barabasi-Albert graph mimics scale-free networks)
    # This resembles knowledge graphs where some hubs connect many clusters.
    try:
        logger.info("Starting Auto-Dynamic Weight Adjustment Demo...")
        cognitive_graph = nx.barabasi_albert_graph(n=50, m=3, seed=42)
        
        # Simulate random weights
        for u, v in cognitive_graph.edges():
            cognitive_graph[u][v]['weight'] = 1.0

        # Identify a high-centrality node to attempt to delete (Simulating a mistake)
        cent = nx.betweenness_centrality(cognitive_graph)
        target_bridge = max(cent, key=cent.get)
        
        logger.info(f"Attempting to prune critical bridge node: {target_bridge}")
        
        try:
            # This should fail in strict mode or skip in skip mode
            safe_pruning_procedure(
                cognitive_graph, 
                [target_bridge], 
                bridge_threshold=0.1, 
                protection_policy='strict'
            )
        except NetworkTopologyError as e:
            logger.info(f"System successfully prevented catastrophic forgetting: {e}")

        # Prune non-critical nodes
        leaf_nodes = [node for node, degree in cognitive_graph.degree() if degree == 1]
        logger.info(f"Attempting to prune {len(leaf_nodes)} leaf nodes.")
        
        new_graph, removed = safe_pruning_procedure(
            cognitive_graph, 
            leaf_nodes, 
            bridge_threshold=0.1,
            protection_policy='skip'
        )
        
        logger.info(f"New graph node count: {new_graph.number_of_nodes()}")
        
    except Exception as e:
        logger.critical(f"Critical failure in execution: {e}", exc_info=True)