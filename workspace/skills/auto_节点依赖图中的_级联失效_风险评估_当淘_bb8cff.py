"""
Module: auto_node_cascade_risk_assessment
Description: Evaluates 'Cascading Failure' risks in dependency graphs during node elimination.
             Balances node quality against structural criticality to prevent system collapse.
"""

import logging
from typing import Dict, List, Tuple, Set, Optional
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GraphNode:
    """Represents a node in the dependency graph."""
    def __init__(self, node_id: str, quality_score: float, value_score: float):
        self.id = node_id
        self.quality = max(0.0, min(1.0, quality_score))  # Normalized [0, 1]
        self.value = max(0.0, min(1.0, value_score))      # Business value [0, 1]

class DependencyGraph:
    """
    Manages the directed graph structure and risk assessment algorithms.
    
    Input Format:
    - Nodes: Dict[str, GraphNode]
    - Edges: Dict[str, List[str]] (Adjacency list: source -> [targets])
    
    Output Format:
    - Risk Report: Dict containing risk scores and recommended actions
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, List[str]] = {}  # Adjacency list
        self.reverse_edges: Dict[str, List[str]] = {}  # For dependency tracking

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph with validation."""
        if not isinstance(node, GraphNode):
            raise TypeError("Input must be a GraphNode instance")
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        self.edges[node.id] = []
        self.reverse_edges[node.id] = []

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Create a dependency edge (source -> target)."""
        self._validate_node_exists(source_id)
        self._validate_node_exists(target_id)
        
        if target_id not in self.edges[source_id]:
            self.edges[source_id].append(target_id)
            self.reverse_edges[target_id].append(source_id)
            logger.debug(f"Added edge: {source_id} -> {target_id}")

    def _validate_node_exists(self, node_id: str) -> None:
        """Check if node exists in the graph."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in graph")

    def calculate_pagerank(self, damping: float = 0.85, iterations: int = 20) -> Dict[str, float]:
        """
        Calculate a PageRank variant to determine structural importance.
        
        Args:
            damping: Probability of following a link (default: 0.85)
            iterations: Number of convergence iterations (default: 20)
            
        Returns:
            Dict mapping node IDs to their PageRank scores
        """
        if not self.nodes:
            return {}
            
        node_count = len(self.nodes)
        initial_rank = 1.0 / node_count
        ranks = {node_id: initial_rank for node_id in self.nodes}
        
        for _ in range(iterations):
            new_ranks = {}
            for node_id in self.nodes:
                # Sum ranks from incoming edges
                incoming_sum = 0.0
                for neighbor in self.reverse_edges[node_id]:
                    outgoing_count = len(self.edges[neighbor])
                    if outgoing_count > 0:
                        incoming_sum += ranks[neighbor] / outgoing_count
                
                # Apply damping factor
                new_ranks[node_id] = (1 - damping) / node_count + damping * incoming_sum
            
            ranks = new_ranks
        
        logger.info("PageRank calculation completed")
        return ranks

    def assess_cascade_risk(self, target_node_id: str, depth: int = 3) -> Dict[str, float]:
        """
        Evaluate the risk of cascading failures when removing a node.
        
        Args:
            target_node_id: Node to be removed
            depth: Maximum depth of impact analysis
            
        Returns:
            Dict containing risk scores and impact metrics
        """
        self._validate_node_exists(target_node_id)
        
        # Calculate structural importance
        pagerank_scores = self.calculate_pagerank()
        target_pagerank = pagerank_scores[target_node_id]
        
        # Find all dependent nodes (BFS traversal)
        affected_nodes = self._find_dependent_nodes(target_node_id, depth)
        total_impact = 0.0
        critical_nodes_affected = 0
        
        for node_id in affected_nodes:
            node = self.nodes[node_id]
            # Weight impact by node value and structural dependency
            impact = node.value * pagerank_scores[node_id]
            total_impact += impact
            
            if node.value > 0.7:  # Threshold for high-value nodes
                critical_nodes_affected += 1
        
        # Calculate risk score (weighted combination)
        risk_score = (
            0.4 * target_pagerank + 
            0.3 * total_impact + 
            0.2 * critical_nodes_affected / max(1, len(affected_nodes)) +
            0.1 * (1 - self.nodes[target_node_id].quality)
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_score, 
            self.nodes[target_node_id].quality,
            len(affected_nodes)
        )
        
        logger.info(f"Risk assessment completed for node {target_node_id}")
        return {
            "node_id": target_node_id,
            "risk_score": round(risk_score, 4),
            "pagerank": round(target_pagerank, 4),
            "affected_nodes": list(affected_nodes),
            "critical_nodes_affected": critical_nodes_affected,
            "recommendation": recommendation
        }

    def _find_dependent_nodes(self, start_node: str, max_depth: int) -> Set[str]:
        """
        Find all nodes that depend on the start node (downstream).
        
        Args:
            start_node: Node ID to start traversal
            max_depth: Maximum search depth
            
        Returns:
            Set of affected node IDs
        """
        visited = set()
        queue = [(start_node, 0)]
        
        while queue:
            node, depth = queue.pop(0)
            if depth > max_depth:
                continue
                
            for neighbor in self.edges[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
                    
        return visited

    def _generate_recommendation(
        self, 
        risk_score: float, 
        quality: float, 
        affected_count: int
    ) -> str:
        """
        Generate action recommendation based on risk assessment.
        
        Args:
            risk_score: Calculated risk score
            quality: Node quality score
            affected_count: Number of dependent nodes
            
        Returns:
            Recommendation string
        """
        if risk_score > 0.7:
            return "CRITICAL: Node must be preserved or carefully refactored"
        elif risk_score > 0.4 and quality < 0.5:
            return "WARNING: Consider refactoring with fallback mechanisms"
        elif affected_count > 5:
            return "CAUTION: Test thoroughly before removal"
        else:
            return "SAFE: Node can be safely removed"

def create_sample_graph() -> DependencyGraph:
    """Create a sample graph for demonstration purposes."""
    graph = DependencyGraph()
    
    # Add nodes with random quality and value scores
    nodes = [
        ("A", 0.4, 0.8),  # Low quality, high value
        ("B", 0.7, 0.5),
        ("C", 0.6, 0.9),  # High value
        ("D", 0.8, 0.3),
        ("E", 0.3, 0.6),  # Low quality
        ("F", 0.9, 0.7)
    ]
    
    for node_id, quality, value in nodes:
        graph.add_node(GraphNode(node_id, quality, value))
    
    # Add edges to create dependencies
    edges = [
        ("A", "B"), ("A", "C"),
        ("B", "D"), ("B", "E"),
        ("C", "E"), ("C", "F"),
        ("D", "F"), ("E", "F")
    ]
    
    for src, tgt in edges:
        graph.add_edge(src, tgt)
    
    return graph

if __name__ == "__main__":
    # Example usage
    try:
        logger.info("Starting cascade risk assessment demo")
        
        # Create and analyze a sample graph
        graph = create_sample_graph()
        
        # Assess risk for node A (critical node)
        risk_report = graph.assess_cascade_risk("A")
        print("\nRisk Assessment Report:")
        for key, value in risk_report.items():
            print(f"{key:>25}: {value}")
        
        # Assess risk for node D (less critical)
        print("\nSecond Assessment:")
        print(graph.assess_cascade_risk("D"))
        
    except Exception as e:
        logger.error(f"Error in demo execution: {str(e)}")
        raise