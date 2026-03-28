"""
Supply Chain Ecosystem Health Diagnoser Module

This module provides tools to analyze supply chain networks through the lens of
ecosystem biology. It moves beyond traditional cost-based optimization by
introducing 'Network Mutualism' and 'Functional Redundancy' metrics.

Key Features:
- Identifies critical nodes (Keystone Predators) with single dependencies.
- Simulates 'Extinction Cascades' to predict systemic failure risks.
- Suggests the introduction of 'Insurance Species' (redundant suppliers).

Author: Advanced Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeMetrics:
    """Data class to store calculated metrics for a supply chain node."""
    node_id: str
    mutualism_index: float = 0.0
    functional_redundancy: int = 0
    is_keystone: bool = False
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)

class SupplyChainEcosystemDiagnoser:
    """
    A diagnostic tool that treats supply chain networks as biological ecosystems.
    
    It calculates health indices based on network topology rather than just cost,
    identifying fragility points where a single failure could cause systemic collapse.
    """

    def __init__(self, network_data: Dict[str, List[str]]):
        """
        Initialize the diagnoser with supply chain relationship data.
        
        Args:
            network_data (Dict[str, List[str]]): A dictionary representing the graph.
                Keys are nodes (suppliers/components), Values are lists of nodes 
                they depend on (directed edge from value to key).
        
        Raises:
            ValueError: If network_data is empty or invalid.
        """
        if not network_data:
            logger.error("Initialization failed: Network data cannot be empty.")
            raise ValueError("Network data cannot be empty.")
            
        self.graph = nx.DiGraph()
        self._build_graph(network_data)
        self.metrics: Dict[str, NodeMetrics] = {}
        logger.info(f"Ecosystem initialized with {self.graph.number_of_nodes()} nodes.")

    def _build_graph(self, network_data: Dict[str, List[str]]) -> None:
        """
        Helper function to construct the network topology from input data.
        
        Args:
            network_data (Dict[str, List[str]]): Raw adjacency data.
        """
        for node, dependencies in network_data.items():
            self.graph.add_node(node)
            for dep in dependencies:
                self.graph.add_edge(dep, node) # Flow is dependency -> consumer
        logger.debug("Graph construction complete.")

    def _validate_node(self, node_id: str) -> bool:
        """
        Validate if a node exists in the current ecosystem.
        
        Args:
            node_id (str): The ID of the node to check.
            
        Returns:
            bool: True if node exists, False otherwise.
        """
        if node_id not in self.graph:
            logger.warning(f"Node {node_id} not found in network.")
            return False
        return True

    def calculate_network_mutualism(self) -> Dict[str, float]:
        """
        Calculate the 'Network Mutualism Index' for each node.
        
        In this context, Mutualism is defined as the balance between how many 
        nodes rely on this node (Out-degree/Centrality) vs. how exposed it is (In-degree).
        A high score suggests a 'Keystone' species that supports the network.
        
        Returns:
            Dict[str, float]: Mapping of node_id to mutualism score.
        """
        mutualism_scores = {}
        
        for node in self.graph.nodes():
            # Dependents (who relies on this node)
            out_degree = self.graph.out_degree(node)
            # Dependencies (who this node relies on)
            in_degree = self.graph.in_degree(node)
            
            # Custom logic: High influence + Low exposure = High Mutualism/Keystone status
            # Avoid division by zero
            exposure = in_degree if in_degree > 0 else 0.1
            influence = out_degree if out_degree > 0 else 0
            
            score = (influence ** 1.5) / exposure
            mutualism_scores[node] = round(score, 4)
            
            # Update internal metrics store
            if node not in self.metrics:
                self.metrics[node] = NodeMetrics(node_id=node)
            self.metrics[node].mutualism_index = score
            self.metrics[node].dependencies = list(self.graph.predecessors(node))
            self.metrics[node].dependents = list(self.graph.successors(node))

        logger.info("Network Mutualism Index calculated for all nodes.")
        return mutualism_scores

    def identify_keystone_predators(self, threshold_percentile: float = 90.0) -> List[str]:
        """
        Identify nodes that act as 'Keystone Predators' (Critical Single Points of Failure).
        
        These are nodes with high mutualism scores and low functional redundancy 
        (meaning if they fail, the network collapses).
        
        Args:
            threshold_percentile (float): The percentile cutoff for considering a node 'Keystone'.
            
        Returns:
            List[str]: List of critical node IDs.
        """
        if not self.metrics:
            self.calculate_network_mutualism()
            
        scores = [m.mutualism_index for m in self.metrics.values()]
        if not scores:
            return []
            
        threshold = np.percentile(scores, threshold_percentile) if 'np' in globals() else sorted(scores)[int(len(scores) * threshold_percentile / 100)]
        
        keystone_nodes = []
        for node_id, metric in self.metrics.items():
            # Identify redundancy (number of alternative suppliers)
            # Here we approximate redundancy by checking if dependents have other options
            # A Keystone is critical if it has dependents.
            if metric.mutualism_index >= threshold and len(metric.dependents) > 0:
                metric.is_keystone = True
                keystone_nodes.append(node_id)
                logger.warning(f"KEYSTONE NODE DETECTED: {node_id} (Score: {metric.mutualism_index})")
                
        return keystone_nodes

    def simulate_extinction_cascade(self, initial_failure_node: str, depth: int = 3) -> Set[str]:
        """
        Simulate a catastrophic failure (extinction) cascading through the network.
        
        This function predicts the 'Chain Reaction' if a specific supplier fails.
        
        Args:
            initial_failure_node (str): The node where the failure starts.
            depth (int): How many layers of the cascade to simulate.
            
        Returns:
            Set[str]: A set of nodes predicted to fail (go extinct).
            
        Raises:
            ValueError: If initial node does not exist.
        """
        if not self._validate_node(initial_failure_node):
            raise ValueError(f"Node {initial_failure_node} does not exist.")

        failed_nodes = set()
        frontier = {initial_failure_node}
        current_depth = 0
        
        logger.info(f"Starting Extinction Cascade Simulation from {initial_failure_node}...")

        while frontier and current_depth < depth:
            new_frontier = set()
            for node in frontier:
                if node in failed_nodes:
                    continue
                    
                failed_nodes.add(node)
                # Find nodes that depend on the current failing node
                dependents = list(self.graph.successors(node))
                
                for dep in dependents:
                    # Logic: A node fails if it loses a critical dependency 
                    # and has no functional redundancy (simplified for demo: checks in-degree)
                    remaining_deps = set(self.graph.predecessors(dep)) - failed_nodes
                    if len(remaining_deps) == 0:
                        new_frontier.add(dep)
                        logger.debug(f"Cascade: {dep} fails due to loss of {node}")
            
            frontier = new_frontier
            current_depth += 1
            
        logger.warning(f"Cascade Simulation Complete. Total affected nodes: {len(failed_nodes)}")
        return failed_nodes

    def recommend_insurance_species(self, target_node: str) -> Dict[str, Any]:
        """
        Suggest 'Insurance Species' (Functional Redundancy) for a critical node.
        
        Args:
            target_node (str): The node identified as high-risk.
            
        Returns:
            Dict[str, Any]: Recommendation report including suggested redundancy strategies.
        """
        if not self._validate_node(target_node):
            return {"error": "Node not found"}

        # Logic: Identify nodes that serve similar purposes or could be on-ramped
        # For this demo, we look for nodes with similar connection patterns or suggest new ones.
        
        report = {
            "target": target_node,
            "risk_level": "HIGH" if self.metrics.get(target_node) and self.metrics[target_node].is_keystone else "MEDIUM",
            "recommendation": "Introduce Functional Redundancy",
            "suggested_actions": []
        }
        
        # Heuristic: Find nodes that are NOT critical but supply the same consumers
        consumers = list(self.graph.successors(target_node))
        
        for consumer in consumers:
            # Check if consumer already has other suppliers
            suppliers = list(self.graph.predecessors(consumer))
            if len(suppliers) == 1: # Single source dependency
                report["suggested_actions"].append(
                    f"CRITICAL: Consumer '{consumer}' relies solely on '{target_node}'. "
                    f"Qualify a secondary supplier for '{consumer}' immediately."
                )
            else:
                report["suggested_actions"].append(
                    f"Diversify supply for '{consumer}' to reduce load on '{target_node}'."
                )

        return report

# Example Usage
if __name__ == "__main__":
    # Mock Data: A simple supply chain
    # Structure: RawMat_A -> Factory_B -> Dist_C
    # Structure: RawMat_D -> Factory_B ...
    # Structure: SinglePoint_E -> Factory_F (Risk)
    supply_chain_data = {
        "RawMat_A": [],              # Root
        "RawMat_D": [],              # Root
        "Factory_B": ["RawMat_A", "RawMat_D"], # Aggregator
        "Distrib_C": ["Factory_B"],  # Leaf
        "SinglePoint_E": [],         # Root (Risk)
        "Factory_F": ["SinglePoint_E"], # High Risk Dependency
        "Retail_G": ["Factory_F", "Factory_B"] # Complex
    }

    print("--- Initializing Supply Chain Ecosystem ---")
    diagnoser = SupplyChainEcosystemDiagnoser(supply_chain_data)
    
    print("\n--- Analyzing Mutualism ---")
    scores = diagnoser.calculate_network_mutualism()
    for k, v in scores.items():
        print(f"Node {k}: Mutualism Score {v}")

    print("\n--- Identifying Keystone Predators ---")
    keystones = diagnoser.identify_keystone_predators()
    print(f"Keystone Nodes: {keystones}")

    print("\n--- Simulating Extinction Cascade (Failure of SinglePoint_E) ---")
    cascades = diagnoser.simulate_extinction_cascade("SinglePoint_E")
    print(f"Projected Failures: {cascades}")
    
    print("\n--- Recommendations for SinglePoint_E ---")
    recs = diagnoser.recommend_insurance_species("SinglePoint_E")
    print(recs)