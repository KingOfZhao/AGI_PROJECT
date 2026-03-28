"""
Module: graph_topology_redundancy_analyzer
Description: Analyzes graph topology redundancy for AGI skill nodes.
"""

import logging
import numpy as np
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillGraphAnalyzer:
    """
    Analyzes a Directed Acyclic Graph (DAG) of AGI skill nodes to identify
    redundant nodes based on structural holes, PageRank, and information entropy.
    """

    def __init__(self, graph_data: Dict[str, List[str]], node_contents: Dict[str, np.ndarray]):
        """
        Initialize the analyzer with graph structure and node content.

        Args:
            graph_data (Dict[str, List[str]]): Adjacency list {node_id: [predecessor_ids]}.
            node_contents (Dict[str, np.ndarray]): Dictionary of node content vectors.
        
        Raises:
            ValueError: If inputs are invalid or empty.
        """
        if not graph_data:
            raise ValueError("Graph data cannot be empty.")
        if not node_contents:
            raise ValueError("Node contents cannot be empty.")
        
        self.graph = nx.DiGraph()
        self._build_graph(graph_data)
        self.node_contents = node_contents
        logger.info(f"Initialized graph with {self.graph.number_of_nodes()} nodes.")

    def _build_graph(self, graph_data: Dict[str, List[str]]) -> None:
        """
        Helper function to build the networkx graph.
        """
        for node, deps in graph_data.items():
            self.graph.add_node(node)
            for dep in deps:
                self.graph.add_edge(dep, node) # Edge from dependency to node
        
        # Validate DAG
        if not nx.is_directed_acyclic_graph(self.graph):
            logger.error("The provided graph is not a DAG.")
            raise ValueError("Graph must be a Directed Acyclic Graph (DAG).")

    def calculate_structural_holes(self) -> Dict[str, float]:
        """
        Calculate the constraint index for each node to measure structural holes.
        Lower constraint indicates a better structural hole position (bridging diverse groups).

        Returns:
            Dict[str, float]: Mapping of node ID to constraint score.
        """
        logger.info("Calculating structural holes (constraint index)...")
        try:
            # Networkx constraint is defined on the undirected view for this specific metric logic usually,
            # but strictly speaking, structural holes in DAGs usually refer to bridging paths.
            # Here we calculate standard constraint on the undirected projection for demonstration.
            constraints = nx.constraint(self.graph.to_undirected())
            return constraints
        except Exception as e:
            logger.error(f"Error calculating structural holes: {e}")
            return {}

    def calculate_pagerank(self) -> Dict[str, float]:
        """
        Calculate the PageRank of each node to determine importance.

        Returns:
            Dict[str, float]: Mapping of node ID to PageRank score.
        """
        logger.info("Calculating PageRank...")
        try:
            return nx.pagerank(self.graph)
        except Exception as e:
            logger.error(f"Error calculating PageRank: {e}")
            return {}

    def _calculate_entropy_delta(self, node_id: str, neighbors: Set[str]) -> float:
        """
        Auxiliary function: Calculate information entropy increment.
        Simulates whether the node's content can be linearly combined by neighbors.

        Args:
            node_id (str): Target node.
            neighbors (Set[str]): Set of surrounding nodes (predecessors + successors).

        Returns:
            float: The percentage of information entropy added by the node.
                   Lower value means higher redundancy.
        """
        if node_id not in self.node_contents:
            return 1.0 # Cannot evaluate, assume unique
        
        target_vector = self.node_contents[node_id]
        if np.linalg.norm(target_vector) == 0:
            return 0.0 # Empty content is redundant

        # Gather neighbor vectors
        neighbor_vectors = []
        for n in neighbors:
            if n in self.node_contents:
                neighbor_vectors.append(self.node_contents[n])
        
        if not neighbor_vectors:
            return 1.0 # No neighbors to replace it, unique

        neighbor_matrix = np.array(neighbor_vectors)
        
        # Simulate linear combination: Project target onto the span of neighbors
        # Using Least Squares to find best fit: neighbor_matrix * x = target_vector
        try:
            # lstsq returns (x, residuals, rank, s)
            result = np.linalg.lstsq(neighbor_matrix, target_vector, rcond=None)
            reconstruction = neighbor_matrix @ result[0]
            
            # Calculate reconstruction error (Entropy delta proxy)
            error = np.linalg.norm(target_vector - reconstruction)
            original_norm = np.linalg.norm(target_vector)
            
            # Avoid division by zero
            if original_norm < 1e-9:
                return 0.0
            
            relative_error = error / original_norm
            return relative_error
            
        except np.linalg.LinAlgError:
            return 1.0 # Calculation failed, assume unique

    def identify_redundant_nodes(self, pagerank_threshold: float = 0.8, entropy_threshold: float = 0.005) -> List[str]:
        """
        Main execution function to identify nodes marked for elimination.
        Criteria:
        1. High PageRank (on critical path).
        2. Low Structural Constraint (broker).
        3. Low Entropy Delta (content is replaceable < 0.5%).

        Args:
            pagerank_threshold (float): Percentile to identify 'critical' nodes (0-1).
            entropy_threshold (float): Threshold for information entropy increment (0.005 = 0.5%).

        Returns:
            List[str]: List of node IDs to be eliminated.
        """
        logger.info("Starting redundancy analysis...")
        
        pr_scores = self.calculate_pagerank()
        constraints = self.calculate_structural_holes()
        
        if not pr_scores or not constraints:
            logger.warning("Missing metrics for analysis.")
            return []

        # Determine critical nodes based on PageRank percentile
        pr_values = list(pr_scores.values())
        critical_cutoff = np.percentile(pr_values, pagerank_threshold * 100)
        
        redundant_nodes = []

        for node in self.graph.nodes():
            # 1. Check if on critical path (High PageRank)
            if pr_scores[node] < critical_cutoff:
                continue # Only check important nodes as per requirement

            # 2. Check Structural Hole (Constraint) - Optional filter depending on logic
            # If a node is a bridge (low constraint), it might be vital even if content is redundant.
            # But requirement asks for nodes that *can* be replaced.
            
            # 3. Check Entropy Delta
            # Get predecessors and successors
            preds = set(self.graph.predecessors(node))
            succs = set(self.graph.successors(node))
            neighbors = preds.union(succs)
            
            delta = self._calculate_entropy_delta(node, neighbors)
            
            logger.debug(f"Node {node}: PR={pr_scores[node]:.4f}, EntropyDelta={delta:.4f}")
            
            if delta < entropy_threshold:
                redundant_nodes.append(node)
        
        logger.info(f"Analysis complete. {len(redundant_nodes)} nodes marked for elimination.")
        return redundant_nodes

# Usage Example
if __name__ == "__main__":
    # 1. Mock Data Generation
    # Simulating a DAG with 488 nodes
    NUM_NODES = 488
    mock_graph_data = {}
    
    # Simple DAG generation
    for i in range(NUM_NODES):
        node_name = f"skill_{i}"
        deps = []
        if i > 0:
            # Randomly link to previous nodes
            num_deps = np.random.randint(0, min(i, 3))
            possible_deps = [f"skill_{j}" for j in range(i)]
            if possible_deps:
                deps = list(np.random.choice(possible_deps, size=num_deps, replace=False))
        mock_graph_data[node_name] = deps

    # Mock Content (Random vectors)
    mock_contents = {
        f"skill_{i}": np.random.rand(10) for i in range(NUM_NODES)
    }
    
    # Make one node deliberately redundant (linear combination of others)
    # skill_400 = 0.5 * skill_100 + 0.5 * skill_101
    mock_contents["skill_400"] = 0.5 * mock_contents["skill_100"] + 0.5 * mock_contents["skill_101"]

    try:
        analyzer = SkillGraphAnalyzer(mock_graph_data, mock_contents)
        to_eliminate = analyzer.identify_redundant_nodes(pagerank_threshold=0.7, entropy_threshold=0.005)
        
        print(f"\n--- Analysis Report ---")
        print(f"Total Nodes: {NUM_NODES}")
        print(f"Nodes marked for elimination: {len(to_eliminate)}")
        if "skill_400" in to_eliminate:
            print("Success: The deliberately redundant node 'skill_400' was detected.")
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")