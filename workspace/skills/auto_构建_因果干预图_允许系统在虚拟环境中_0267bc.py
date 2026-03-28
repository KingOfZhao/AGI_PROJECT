"""
Module: auto_构建_因果干预图_允许系统在虚拟环境中_0267bc

This module provides a robust framework for creating and simulating Causal
Intervention Graphs within a virtual environment. It is designed to allow
an AGI system to safely simulate the effects of modifying specific parameters
(do-calculus) and observe downstream consequences without risking real-world
state.

Key Features:
- Definition of Causal Nodes and Edges.
- Virtual environment isolation.
- Simulation of interventions (do(x)).
- Structural validation and cycle detection.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type aliases for clarity
NodeId = str
Probability = float

@dataclass
class CausalNode:
    """
    Represents a node in the causal graph.
    
    Attributes:
        id (NodeId): Unique identifier for the node.
        name (str): Human-readable name.
        value (float): Current value of the node (probability, scalar, etc.).
        min_val (float): Minimum allowed value.
        max_val (float): Maximum allowed value.
    """
    id: NodeId
    name: str
    value: float = 0.0
    min_val: float = 0.0
    max_val: float = 1.0
    
    def __post_init__(self):
        self._validate_value()
        
    def _validate_value(self):
        """Ensure value is within bounds."""
        if not (self.min_val <= self.value <= self.max_val):
            raise ValueError(f"Value {self.value} out of bounds [{self.min_val}, {self.max_val}] for node {self.id}")

@dataclass
class CausalEdge:
    """
    Represents a directed edge in the causal graph.
    
    Attributes:
        source (NodeId): ID of the parent node.
        target (NodeId): ID of the child node.
        weight (float): Strength of the causal relationship.
        transformation (str): Mathematical relationship type (linear, threshold, etc.).
    """
    source: NodeId
    target: NodeId
    weight: float = 1.0
    transformation: str = "linear" # linear, sigmoid, threshold

class VirtualEnvironment:
    """
    A sandbox environment that holds a copy of the causal graph.
    Modifications here do not affect the 'real' graph unless explicitly committed.
    """
    
    def __init__(self, graph: 'CausalGraph'):
        self.graph = graph.clone()
        logger.info("VirtualEnvironment initialized with graph snapshot.")

class CausalGraph:
    """
    Manages the structure and simulation logic of the causal graph.
    
    This class implements the core logic for causal inference, allowing
    for topological sorting, cycle detection, and intervention simulation.
    """
    
    def __init__(self):
        self.nodes: Dict[NodeId, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self.adjacency: Dict[NodeId, List[NodeId]] = {} # Adjacency list for graph traversal
        
    def add_node(self, node: CausalNode) -> None:
        """Adds a node to the graph with validation."""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        self.adjacency[node.id] = []
        logger.debug(f"Node added: {node.id}")
        
    def add_edge(self, edge: CausalEdge) -> None:
        """
        Adds a directed edge to the graph.
        
        Validates:
        1. Source and Target nodes exist.
        2. Weight is numeric.
        3. Cycle detection (to maintain DAG property).
        """
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge references non-existent nodes: {edge.source} -> {edge.target}")
        
        if not isinstance(edge.weight, (int, float)):
            raise TypeError("Edge weight must be numeric.")
            
        # Add to adjacency list
        self.adjacency[edge.source].append(edge.target)
        
        # Check for cycles
        if self._has_cycle():
            self.adjacency[edge.source].remove(edge.target) # Rollback
            raise ValueError(f"Adding edge {edge.source}->{edge.target} creates a cycle. Graph must be a DAG.")
            
        self.edges.append(edge)
        logger.debug(f"Edge added: {edge.source} -> {edge.target}")

    def _has_cycle(self) -> bool:
        """Helper function to detect cycles using DFS."""
        visited: Set[NodeId] = set()
        recursion_stack: Set[NodeId] = set()
        
        def dfs(v: NodeId) -> bool:
            visited.add(v)
            recursion_stack.add(v)
            for neighbour in self.adjacency.get(v, []):
                if neighbour not in visited:
                    if dfs(neighbour):
                        return True
                elif neighbour in recursion_stack:
                    return True
            recursion_stack.remove(v)
            return False
            
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def clone(self) -> 'CausalGraph':
        """Creates a deep copy of the graph for simulation."""
        import copy
        new_graph = CausalGraph()
        new_graph.nodes = copy.deepcopy(self.nodes)
        new_graph.edges = copy.deepcopy(self.edges)
        new_graph.adjacency = copy.deepcopy(self.adjacency)
        return new_graph

    def calculate_transformation(self, source_val: float, weight: float, transform: str) -> float:
        """Applies causal logic to determine influence."""
        if transform == "linear":
            return source_val * weight
        elif transform == "sigmoid":
            return 1 / (1 + math.exp(-source_val * weight))
        elif transform == "threshold":
            return weight if source_val > 0.5 else 0.0
        return source_val * weight

    def run_simulation(self, interventions: Dict[NodeId, float]) -> Dict[NodeId, float]:
        """
        Simulates the graph with interventions (do-calculus).
        
        Args:
            interventions (Dict[NodeId, float]): A map of Node IDs to forced values.
        
        Returns:
            Dict[NodeId, float]: The state of all nodes after simulation.
        """
        # 1. Apply Interventions (do(x))
        for node_id, value in interventions.items():
            if node_id in self.nodes:
                self.nodes[node_id].value = value
                self.nodes[node_id].min_val = min(self.nodes[node_id].min_val, value)
                self.nodes[node_id].max_val = max(self.nodes[node_id].max_val, value)
                logger.info(f"INTERVENTION: Set {node_id} to {value}")
            else:
                logger.warning(f"Intervention node {node_id} not found.")

        # 2. Topological Sort (Simple recursive approach for DAG)
        sorted_nodes = self._topological_sort()
        
        # 3. Propagate values
        # Note: In a real complex graph, we might handle convergence loops here.
        # For this DAG simulation, we flow downstream.
        
        # Reset downstream nodes that aren't intervened? 
        # In 'do' calculus, we cut incoming edges to intervened nodes.
        # We calculate values for non-intervened nodes.
        
        for node_id in sorted_nodes:
            if node_id in interventions:
                continue # Intervened nodes are fixed
                
            # Calculate incoming influence
            incoming_val = 0.0
            has_parents = False
            
            for edge in self.edges:
                if edge.target == node_id:
                    has_parents = True
                    source_val = self.nodes[edge.source].value
                    incoming_val += self.calculate_transformation(
                        source_val, edge.weight, edge.transformation
                    )
            
            if has_parents:
                # Simple aggregation (sum). Clamped to bounds.
                new_val = incoming_val
                node = self.nodes[node_id]
                node.value = max(node.min_val, min(node.max_val, new_val))
                logger.debug(f"Updated {node_id} to {node.value}")

        return {k: v.value for k, v in self.nodes.items()}

    def _topological_sort(self) -> List[NodeId]:
        """Returns nodes in topological order."""
        visited = set()
        order = []
        
        def visit(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            for neighbor in self.adjacency.get(node_id, []):
                visit(neighbor)
            order.append(node_id)
            
        for node_id in self.nodes:
            visit(node_id)
            
        return order[::-1]

def create_virtual_experiment(graph: CausalGraph, interventions: Dict[NodeId, float]) -> Tuple[bool, Dict[NodeId, float]]:
    """
    High-level function to orchestrate a safe virtual experiment.
    
    This acts as the Interface for the AGI system.
    
    Args:
        graph (CausalGraph): The master causal graph.
        interventions (Dict[NodeId, float]): Parameters to modify in the virtual env.
        
    Returns:
        Tuple[bool, Dict]: Success status and the resulting graph state.
    """
    logger.info("Initializing virtual experiment...")
    
    # 1. Create Virtual Environment
    virtual_env = VirtualEnvironment(graph)
    
    # 2. Run Simulation
    try:
        results = virtual_env.graph.run_simulation(interventions)
        return True, results
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return False, {}

# ---------------------------------------------------------
# Example Usage
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Initialize the Causal Graph
    causal_system = CausalGraph()

    # 2. Define Nodes (Variables)
    # Example: Marketing Budget -> Ad Views -> Website Traffic -> Sales
    n_budget = CausalNode(id="budget", name="Marketing Budget", value=1000, min_val=0, max_val=5000)
    n_ad_views = CausalNode(id="ad_views", name="Ad Views", value=0, min_val=0, max_val=100000)
    n_traffic = CausalNode(id="traffic", name="Website Traffic", value=0, min_val=0, max_val=50000)
    n_sales = CausalNode(id="sales", name="Sales Units", value=0, min_val=0, max_val=1000)

    for n in [n_budget, n_ad_views, n_traffic, n_sales]:
        causal_system.add_node(n)

    # 3. Define Edges (Causal Relationships)
    # Budget affects Ad Views (approx 50 views per dollar)
    causal_system.add_edge(CausalEdge("budget", "ad_views", weight=50, transformation="linear"))
    
    # Ad Views affect Traffic (approx 2% click rate)
    causal_system.add_edge(CausalEdge("ad_views", "traffic", weight=0.02, transformation="linear"))
    
    # Traffic affects Sales (approx 0.5% conversion)
    causal_system.add_edge(CausalEdge("traffic", "sales", weight=0.005, transformation="linear"))

    print("--- Baseline Simulation ---")
    # Initial state
    success, baseline = create_virtual_experiment(causal_system, {})
    if success:
        print(f"Baseline Sales: {baseline['sales']}")

    print("\n--- Intervention Simulation ---")
    # What if we increase budget to 2000?
    intervention = {"budget": 2000.0}
    success, intervention_result = create_virtual_experiment(causal_system, intervention)
    
    if success:
        print(f"Intervention Sales (Budget=2000): {intervention_result['sales']}")
        print(f"Intervention Traffic: {intervention_result['traffic']}")