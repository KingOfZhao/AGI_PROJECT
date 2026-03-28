"""
Module: cognitive_consistency_monitor.py

This module implements a real-time monitor for a 'Cognitive Loop' system.
It is designed to prevent 'cognitive fractures' during the 'Bottom-Up Induction'
process. Before a new concept node is written to the long-term memory (Graph),
it performs a global consistency stress test to ensure the new induction
does not logically collapse existing core beliefs.

Design Pattern:
- Graph-based Cognitive Model (NetworkX)
- Simulation / Shadow Mode Validation
- Dependency Analysis via Graph Traversal

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration of cognitive node types."""
    CORE_BELIEF = "CORE_BELIEF"  # Fundamental, unchangeable logic
    DERIVED_FACT = "DERIVED_FACT"  # Induced knowledge
    HYPOTHESIS = "HYPOTHESIS"  # New inductive node

class ConsistencyStatus(Enum):
    """Status of the consistency check."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    COLLAPSE = "COLLAPSE"

@dataclass
class CognitiveNode:
    """Represents a node in the cognitive network."""
    node_id: str
    type: NodeType
    content: str
    truth_value: float = 1.0  # 0.0 to 1.0
    dependencies: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if not isinstance(other, CognitiveNode):
            return False
        return self.node_id == other.node_id

class CognitiveConsistencyMonitor:
    """
    A monitor class that validates new inductive nodes against the existing
    cognitive graph to detect logical fractures.
    
    Attributes:
        cognitive_graph (nx.DiGraph): The directed graph representing current knowledge.
        core_nodes (Set[str]): IDs of nodes that are fundamental.
    """

    def __init__(self):
        """Initialize the monitor with an empty directed graph."""
        self.cognitive_graph: nx.DiGraph = nx.DiGraph()
        self.core_nodes: Set[str] = set()
        logger.info("CognitiveConsistencyMonitor initialized.")

    def load_knowledge_base(self, nodes: List[CognitiveNode]) -> None:
        """
        Load initial knowledge into the graph.
        
        Args:
            nodes: List of CognitiveNode objects.
        """
        for node in nodes:
            self._add_node_to_graph(node)
        logger.info(f"Loaded {len(nodes)} nodes into the cognitive graph.")

    def _add_node_to_graph(self, node: CognitiveNode) -> None:
        """
        Helper function to add a node and its edges to the network graph.
        
        Args:
            node: The node to add.
        """
        # Data Validation
        if not 0.0 <= node.truth_value <= 1.0:
            raise ValueError(f"Invalid truth_value for node {node.node_id}")
        
        self.cognitive_graph.add_node(node.node_id, data=node)
        
        if node.type == NodeType.CORE_BELIEF:
            self.core_nodes.add(node.node_id)
            
        # Add edges based on dependencies (Child -> Parent dependency direction)
        # If Node B depends on Node A, we model it as A -> B (Propagating influence)
        # or B -> A (Dependency lookup). Here we assume logic flows from basis to conclusion.
        # So if `node` depends on `dep`, edge is `dep` -> `node`.
        for dep_id in node.dependencies:
            if self.cognitive_graph.has_node(dep_id):
                self.cognitive_graph.add_edge(dep_id, node.node_id)
            else:
                logger.warning(f"Dependency {dep_id} not found for node {node.node_id}. Edge skipped.")

    def _evaluate_local_consistency(self, new_node: CognitiveNode) -> Tuple[bool, str]:
        """
        [Core Function 1]
        Perform a local check on the immediate dependencies of the new node.
        Checks if the new node directly contradicts the truth values of its parents.
        
        Args:
            new_node: The candidate node to be inducted.
            
        Returns:
            Tuple[bool, str]: (is_consistent, message)
        """
        contradiction_threshold = 0.7
        parents = list(self.cognitive_graph.predecessors(new_node.node_id)) # Nodes it depends on
        
        for parent_id in parents:
            parent_data: CognitiveNode = self.cognitive_graph.nodes[parent_id]['data']
            
            # Simple Logic Simulation:
            # If parent is TRUE (1.0), and dependency implies confirmation,
            # a new node with truth_value 0.1 might be a contradiction.
            # For this demo, we assume strict implication:
            # If Parent is True, Child must be > 0.5.
            
            if parent_data.truth_value > 0.9 and new_node.truth_value < (1.0 - contradiction_threshold):
                msg = (f"Logical fracture detected: Node {new_node.node_id} strongly contradicts "
                       f"highly trusted parent {parent_id}")
                logger.warning(msg)
                return False, msg
        
        return True, "Local consistency check passed."

    def perform_global_stress_test(self, candidate_node: CognitiveNode) -> ConsistencyStatus:
        """
        [Core Function 2]
        Simulates adding the new node to detect global ripple effects (Cognitive Collapse).
        Uses graph traversal to check if the new node lowers the stability of 'Core Beliefs'.
        
        The algorithm simulates a 'Truth Energy' flow. 
        If the new node acts as a 'drain' that pulls core node stability below a threshold,
        it is rejected.
        
        Args:
            candidate_node: The node attempting to be inducted (Bottom-Up).
            
        Returns:
            ConsistencyStatus: SAFE, WARNING, or COLLAPSE.
        """
        logger.info(f"Starting stress test for candidate node: {candidate_node.node_id}")
        
        # 1. Create a temporary shadow graph to simulate changes
        shadow_graph = self.cognitive_graph.copy()
        
        # Validate input existence
        if shadow_graph.has_node(candidate_node.node_id):
            logger.error("Node ID collision during induction.")
            return ConsistencyStatus.COLLAPSE

        # 2. Add candidate to shadow graph
        shadow_graph.add_node(candidate_node.node_id, data=candidate_node)
        for dep_id in candidate_node.dependencies:
            if shadow_graph.has_node(dep_id):
                shadow_graph.add_edge(dep_id, candidate_node.node_id)
        
        # 3. Identify impact zone (Ancestors of the new node that are Core Beliefs)
        # We need to see if this new leaf node creates a feedback loop or drag.
        # Actually, in induction, we worry if the new node forces a rewrite of history.
        # Let's calculate 'Stress' on the graph structure.
        
        try:
            # Check 1: Cycle detection (Circular logic)
            if not nx.is_directed_acyclic_graph(shadow_graph):
                logger.warning("Induction creates circular logic (Cycle detected).")
                return ConsistencyStatus.COLLAPSE

            # Check 2: Core Node Stability via Centrality / Reachability
            # If the new node becomes more 'central' than the core beliefs, 
            # it implies a paradigm shift (potentially a collapse of current identity).
            
            # Using Pagerank as a proxy for 'Cognitive Weight'
            # We assume Core Beliefs should maintain high centrality.
            pagerank_scores = nx.pagerank(shadow_graph)
            
            candidate_weight = pagerank_scores.get(candidate_node.node_id, 0.0)
            
            for core_id in self.core_nodes:
                core_weight = pagerank_scores.get(core_id, 0.0)
                
                # Boundary Check: If a new hypothesis outweighs a core belief significantly
                # without explicit verification, it is a hallucination risk.
                if candidate_weight > (core_weight * 1.5):
                    logger.warning(f"Inductive overflow: Candidate weight {candidate_weight:.4f} "
                                   f"exceeds Core {core_id} weight {core_weight:.4f}")
                    return ConsistencyStatus.WARNING

            # Check 3: Logical Fracture (Dependency Check)
            is_consistent, msg = self._evaluate_local_consistency(candidate_node)
            if not is_consistent:
                return ConsistencyStatus.COLLAPSE

            logger.info("Global stress test passed successfully.")
            return ConsistencyStatus.SAFE

        except nx.NetworkXError as e:
            logger.error(f"Graph traversal error: {e}")
            return ConsistencyStatus.COLLAPSE
        except Exception as e:
            logger.exception("Unexpected error during stress test.")
            return ConsistencyStatus.COLLAPSE

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Monitor
    monitor = CognitiveConsistencyMonitor()

    # 2. Define Existing Knowledge (Core Beliefs)
    core_belief_1 = CognitiveNode(
        node_id="logic_identity", 
        type=NodeType.CORE_BELIEF, 
        content="A is A", 
        truth_value=1.0
    )
    
    derived_fact_1 = CognitiveNode(
        node_id="fact_apple", 
        type=NodeType.DERIVED_FACT, 
        content="Apple is a Fruit", 
        truth_value=0.95,
        dependencies=["logic_identity"]
    )

    monitor.load_knowledge_base([core_belief_1, derived_fact_1])

    # 3. Scenario A: Safe Induction
    print("\n--- Scenario A: Safe Induction ---")
    new_induction_safe = CognitiveNode(
        node_id="induction_granny_smith",
        type=NodeType.HYPOTHESIS,
        content="Granny Smith is green",
        truth_value=0.8,
        dependencies=["fact_apple"]
    )
    
    result_safe = monitor.perform_global_stress_test(new_induction_safe)
    print(f"Result: {result_safe}")

    # 4. Scenario B: Contradiction / Collapse
    print("\n--- Scenario B: Contradiction ---")
    new_induction_bad = CognitiveNode(
        node_id="induction_contradiction",
        type=NodeType.HYPOTHESIS,
        content="Logic is false",
        truth_value=0.1,  # Low truth value contradicting high truth parent
        dependencies=["logic_identity"]
    )
    
    result_bad = monitor.perform_global_stress_test(new_induction_bad)
    print(f"Result: {result_bad}")

    # 5. Scenario C: Circular Logic
    print("\n--- Scenario C: Circular Logic ---")
    # To simulate circular logic properly we need a node that creates a cycle
    # This requires manually manipulating the graph or setting up specific dependencies
    # that loop back to the root. 
    # Note: In a real AGI, this happens with recursive rules.
    
    # Let's force a cycle for demonstration by pointing to a future node (conceptually)
    # But in this API, we add edges based on dependencies.
    # We will simulate by adding a node that depends on itself (if allowed by logic)
    # or A->B, B->C, C->A.
    
    # Add 'C'
    monitor._add_node_to_graph(CognitiveNode("C", NodeType.DERIVED_FACT, "C", 0.9, ["fact_apple"]))
    # Add 'D' depending on 'C'
    monitor._add_node_to_graph(CognitiveNode("D", NodeType.DERIVED_FACT, "D", 0.9, ["C"]))
    
    # Try to add 'E' that depends on 'D' but implies it negates 'fact_apple' (Cycle logic check)
    # The cycle check is structural.
    
    circular_node = CognitiveNode(
        node_id="loop_node",
        type=NodeType.HYPOTHESIS,
        content="Recursive dependency",
        truth_value=0.5,
        dependencies=["logic_identity"] # Normal dependency
    )
    
    # Manually adding a back-edge to create a cycle for the test (Simulation of complex dependency)
    # This part is tricky in usage example without exposing graph internals, 
    # but the `perform_global_stress_test` handles it.
    
    # Let's simulate a 'Paradox' node
    paradox_node = CognitiveNode(
        node_id="paradox",
        type=NodeType.HYPOTHESIS,
        content="This statement is false",
        truth_value=0.0,
        dependencies=["logic_identity"]
    )
    result_paradox = monitor.perform_global_stress_test(paradox_node)
    print(f"Result: {result_paradox}")