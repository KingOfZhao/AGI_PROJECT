"""
Module: auto_bottom_up_redundancy_detection.py
Description: 【自下而上】基于'子图同构'的冗余检测。
             Detects redundant nodes in a knowledge graph by identifying bottom-up
             subgraph isomorphism patterns. Nodes representing similar entities are
             flagged for merging or score penalization.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GraphRedundancyDetector:
    """
    A class to detect redundancy in graphs using subgraph isomorphism.
    
    This detector uses a "bottom-up" approach by first identifying low-value nodes
    and then checking if their local neighborhoods (subgraphs) are isomorphic to
    other neighborhoods in the graph.
    """

    def __init__(self, similarity_threshold: float = 0.7, max_subgraph_size: int = 4):
        """
        Initialize the detector.

        Args:
            similarity_threshold (float): Threshold for Jaccard similarity to consider 
                                          neighborhoods as redundant.
            max_subgraph_size (int): The radius/depth of the subgraph to extract around 
                                     low-value nodes for comparison.
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        if max_subgraph_size < 1:
            raise ValueError("Max subgraph size must be at least 1")

        self.similarity_threshold = similarity_threshold
        self.max_subgraph_size = max_subgraph_size
        logger.info("GraphRedundancyDetector initialized with threshold=%.2f, size=%d",
                    self.similarity_threshold, self.max_subgraph_size)

    def _validate_graph(self, graph: nx.Graph) -> None:
        """
        Validate the input graph structure.
        
        Args:
            graph (nx.Graph): The networkx graph object.
            
        Raises:
            TypeError: If input is not a networkx Graph.
            ValueError: If graph is empty.
        """
        if not isinstance(graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)):
            raise TypeError("Input must be a NetworkX graph instance.")
        if graph.number_of_nodes() == 0:
            raise ValueError("Graph cannot be empty.")
        logger.debug("Graph validation passed. Nodes: %d", graph.number_of_nodes())

    def _get_node_signature(self, graph: nx.Graph, node: Any) -> Tuple:
        """
        Generate a structural signature for a node based on its immediate connections.
        This is a lightweight heuristic to prune comparisons before running full isomorphism.
        
        Args:
            graph (nx.Graph): The graph.
            node (Any): The node identifier.
            
        Returns:
            Tuple: A tuple containing (degree, sorted_edge_type_counts).
        """
        # Basic degree
        degree = graph.degree(node)
        
        # Advanced: Count edge types or neighbor attributes if available
        edge_types = []
        for u, v, data in graph.edges(node, data=True):
            edge_type = data.get('type', 'default')
            edge_types.append(edge_type)
        
        # Create a frequency map signature
        type_counts = tuple(sorted([(t, edge_types.count(t)) for t in set(edge_types)]))
        
        return (degree, type_counts)

    def extract_local_subgraph(self, graph: nx.Graph, center_node: Any) -> nx.Graph:
        """
        Extracts a subgraph around the center node within a specified radius (bottom-up extraction).
        
        Args:
            graph (nx.Graph): The full graph.
            center_node (Any): The node to center the subgraph on.
            
        Returns:
            nx.Graph: The extracted subgraph (ego graph).
        """
        try:
            # ego_graph extracts the neighborhood up to a radius
            sub_graph = nx.ego_graph(graph, center_node, radius=self.max_subgraph_size)
            return sub_graph
        except nx.NetworkXError as e:
            logger.error("Failed to extract subgraph for node %s: %s", center_node, e)
            return nx.Graph()

    def find_redundant_clusters(self, graph: nx.Graph, low_value_nodes: List[Any]) -> List[Set[Any]]:
        """
        Main Skill Function: Identifies clusters of redundant nodes based on subgraph isomorphism.
        
        Strategy:
        1. Extract subgraphs for all low-value nodes.
        2. Group nodes by 'structural signature' (heuristic pruning).
        3. Within groups, perform Graph Isomorphism checks.
        4. Cluster redundant nodes together.
        
        Args:
            graph (nx.Graph): The input graph.
            low_value_nodes (List[Any]): List of candidate nodes suspected to be low value.
            
        Returns:
            List[Set[Any]]: A list of sets, where each set contains nodes that are 
                            structurally redundant and should be merged.
                            
        Example:
            >>> G = nx.Graph()
            >>> G.add_edges_from([(1,2), (2,3), (10,20), (20,30)]) # Two disconnected triangles
            >>> detector = GraphRedundancyDetector()
            >>> clusters = detector.find_redundant_clusters(G, [1, 2, 10, 20])
        """
        self._validate_graph(graph)
        
        # Filter candidates actually present in graph
        valid_candidates = [n for n in low_value_nodes if n in graph]
        if not valid_candidates:
            logger.warning("No valid candidates found in graph.")
            return []

        logger.info("Analyzing %d candidates for redundancy...", len(valid_candidates))

        # Step 1: Pre-compute signatures for pruning
        signatures: Dict[Tuple, List[Any]] = defaultdict(list)
        candidate_subgraphs: Dict[Any, nx.Graph] = {}

        for node in valid_candidates:
            sig = self._get_node_signature(graph, node)
            signatures[sig].append(node)
            candidate_subgraphs[node] = self.extract_local_subgraph(graph, node)

        # Step 2: Compare within signature groups
        # Disjoint Set Union (DSU) for clustering
        parent = {n: n for n in valid_candidates}

        def find(i):
            if parent[i] != i:
                parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        # Only compare nodes with the same signature
        for sig, nodes in signatures.items():
            if len(nodes) < 2:
                continue
            
            # Compare pairs
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    u, v = nodes[i], nodes[j]
                    
                    # Optimization: If already in same cluster, skip
                    if find(u) == find(v):
                        continue

                    g_u = candidate_subgraphs[u]
                    g_v = candidate_subgraphs[v]

                    # Check Isomorphism (Bottom-Up validation)
                    # Note: For large graphs, use 'vf2pp' or limit node/edge count
                    if self._check_isomorphism(g_u, g_v):
                        logger.debug("Isomorphism found between %s and %s", u, v)
                        union(u, v)

        # Step 3: Aggregate clusters
        clusters_map = defaultdict(set)
        for node in valid_candidates:
            root = find(node)
            if root != node: # Only interested in merged groups
                clusters_map[root].add(node)
                clusters_map[root].add(root) # Ensure root is included
        
        # Clean up singletons created by DSU logic if necessary
        final_clusters = [s for s in clusters_map.values() if len(s) > 1]
        
        logger.info("Detection complete. Found %d redundant clusters.", len(final_clusters))
        return final_clusters

    def _check_isomorphism(self, g1: nx.Graph, g2: nx.Graph) -> bool:
        """
        Helper function to check isomorphism with error handling.
        
        Args:
            g1 (nx.Graph): First graph.
            g2 (nx.Graph): Second graph.
            
        Returns:
            bool: True if isomorphic, False otherwise.
        """
        # Basic size check optimization
        if g1.number_of_nodes() != g2.number_of_nodes() or \
           g1.number_of_edges() != g2.number_of_edges():
            return False

        try:
            # using is_isomorphic from networkx (VF2 algorithm usually)
            # node_match can be added if node attributes are critical
            return nx.is_isomorphic(g1, g2)
        except Exception as e:
            logger.error("Error during isomorphism check: %s", e)
            return False

def run_redundancy_check(graph_data: Dict, candidates: List[str]) -> Dict[str, Any]:
    """
    Skill Entry Point: Executes the redundancy detection pipeline.
    
    Input Format:
        graph_data: A dictionary representing adjacency list or nodes/edges.
                    {'nodes': [{'id': 1, 'val': 0.1}, ...], 'edges': [{'u':1, 'v':2}, ...]}
        candidates: List of node IDs identified as low value.
        
    Output Format:
        A dictionary containing:
        {
            'status': 'success',
            'clusters': [[id1, id2], [id3, id4, id5]],
            'recommendation': 'merge'
        }
    """
    try:
        # 1. Construct Graph
        G = nx.Graph()
        
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        if not nodes or not edges:
            return {"status": "error", "message": "Invalid graph data format"}

        G.add_nodes_from([(n['id'], n) for n in nodes])
        G.add_edges_from([(e['u'], e['v'], e) for e in edges])
        
        # 2. Initialize Detector
        detector = GraphRedundancyDetector(similarity_threshold=0.8, max_subgraph_size=2)
        
        # 3. Run Detection
        # We focus on the provided candidates
        raw_clusters = detector.find_redundant_clusters(G, candidates)
        
        # 4. Format Output
        # Convert sets to lists for JSON serialization
        serializable_clusters = [list(c) for c in raw_clusters]
        
        return {
            "status": "success",
            "clusters": serializable_clusters,
            "total_redundant_nodes": sum(len(c) for c in raw_clusters),
            "recommendation": "merge_clusters" if raw_clusters else "no_action"
        }
        
    except Exception as e:
        logger.exception("Failed to execute redundancy check")
        return {"status": "error", "message": str(e)}

# Example Usage
if __name__ == "__main__":
    # Mock Data: Two similar structures that might represent duplicate entities
    # Cluster A: 1 -> 2 -> 3
    # Cluster B: 10 -> 20 -> 30
    # Unrelated: 99
    
    mock_nodes = [
        {'id': 1, 'type': 'entity', 'value': 0.1},
        {'id': 2, 'type': 'property', 'value': 0.5},
        {'id': 3, 'type': 'property', 'value': 0.5},
        {'id': 10, 'type': 'entity', 'value': 0.1}, # Duplicate of 1
        {'id': 20, 'type': 'property', 'value': 0.5},
        {'id': 30, 'type': 'property', 'value': 0.5},
        {'id': 99, 'type': 'unique', 'value': 0.9}
    ]
    
    mock_edges = [
        {'u': 1, 'v': 2}, {'u': 2, 'v': 3},
        {'u': 10, 'v': 20}, {'u': 20, 'v': 30},
        {'u': 99, 'v': 1} # Connects unique to cluster A
    ]
    
    data = {'nodes': mock_nodes, 'edges': mock_edges}
    low_value_candidates = [1, 10, 99] # 99 is low value but unique structure
    
    result = run_redundancy_check(data, low_value_candidates)
    print("--- Detection Result ---")
    print(f"Status: {result['status']}")
    print(f"Redundant Clusters: {result['clusters']}")
    print(f"Recommendation: {result['recommendation']}")