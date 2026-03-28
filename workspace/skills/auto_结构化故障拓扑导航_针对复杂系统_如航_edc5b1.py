"""
Module: auto_structured_fault_topology_navigation_edc4b1
Description: Advanced AGI Skill for Structured Fault Topology Navigation.
             Designed for complex systems (e.g., Aero Engines, Data Centers).
             Uses a Graph-Based Cognitive Path approach to guide repairs,
             minimizing unnecessary teardowns via logical verification nodes.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import heapq
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Enumeration for the operational status of a component node."""
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    UNKNOWN = "UNKNOWN"


class NodeType(Enum):
    """Enumeration for the type of node in the topology."""
    SYMPTOM = "SYMPTOM"
    ROOT_CAUSE = "ROOT_CAUSE"
    INTERMEDIATE = "INTERMEDIATE"


@dataclass(order=True)
class TopologyNode:
    """
    Represents a node in the Fault Topology Graph.

    Attributes:
        id: Unique identifier for the node.
        name: Human-readable name of the component/symptom.
        type: The type of node (Symptom, Intermediate, Root Cause).
        description: Detailed description of the state.
        verification_steps: Instructions to verify the status of this node.
        cost: Estimated time/effort to inspect this node (used for pathfinding).
        status: Current known status of the node (default UNKNOWN).
    """
    id: str
    name: str
    type: NodeType
    description: str = ""
    verification_steps: str = ""
    cost: int = 10
    status: NodeStatus = NodeStatus.UNKNOWN
    # Used for priority queue sorting (lower cost = higher priority)
    sort_key: int = field(init=False, repr=True)

    def __post_init__(self):
        # We want to prioritize nodes that are "cheaper" to verify
        self.sort_key = self.cost


class FaultTopologyGraph:
    """
    A directed graph representing the causal relationships of system failures.
    """
    def __init__(self):
        self.nodes: Dict[str, TopologyNode] = {}
        # Adjacency list: Parent -> List of Children (Propagation direction)
        self.adjacency: Dict[str, List[str]] = {}
        # Reverse Adjacency: Child -> List of Parents (Diagnostic direction)
        self.reverse_adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: TopologyNode):
        """Adds a node to the graph."""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []
        if node.id not in self.reverse_adjacency:
            self.reverse_adjacency[node.id] = []

    def add_edge(self, parent_id: str, child_id: str):
        """
        Adds a directed edge representing fault propagation.
        parent_id -> child_id means 'Parent failure causes Child failure'.
        """
        if parent_id not in self.nodes or child_id not in self.nodes:
            raise ValueError("Both nodes must exist before adding an edge.")
        
        self.adjacency[parent_id].append(child_id)
        self.reverse_adjacency[child_id].append(parent_id)
        logger.debug(f"Edge added: {parent_id} -> {child_id}")

    def get_children(self, node_id: str) -> List[str]:
        return self.adjacency.get(node_id, [])

    def get_parents(self, node_id: str) -> List[str]:
        return self.reverse_adjacency.get(node_id, [])


class DiagnosticNavigator:
    """
    The core logic class that performs the Cognitive Path Navigation.
    It mimics an expert engineer's thought process: 
    "If A is faulty, check its children. If A is fine, check siblings or other parents."
    """

    def __init__(self, graph: FaultTopologyGraph):
        self.graph = graph
        self.visited_nodes: Set[str] = set()

    def _validate_node(self, node_id: str) -> TopologyNode:
        """Helper function to validate node existence."""
        if node_id not in self.graph.nodes:
            logger.error(f"Node ID {node_id} not found in topology.")
            raise ValueError(f"Invalid Node ID: {node_id}")
        return self.graph.nodes[node_id]

    def find_optimal_diagnostic_path(
        self, 
        start_symptom_id: str, 
        depth_limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Generates a structured diagnostic path using a modified Best-First Search.
        
        This algorithm prioritizes paths based on verification cost to ensure
        the "Logical Shortest Path".
        
        Args:
            start_symptom_id: The ID of the observed symptom node.
            depth_limit: Maximum depth to traverse to prevent infinite loops.
            
        Returns:
            A list of steps (dicts) representing the repair guide.
            
        Raises:
            ValueError: If start node is invalid.
            RecursionError: If depth limit is exceeded (handled internally).
        """
        logger.info(f"Starting navigation from symptom: {start_symptom_id}")
        start_node = self._validate_node(start_symptom_id)
        
        path_guide = []
        self.visited_nodes = set()
        
        # Priority Queue stores tuples: (cumulative_cost, node_id, path_history)
        # We use a priority queue to always explore the "cheapest" verification path first.
        pq: List[Tuple[int, str, List[str]]] = []
        heapq.heappush(pq, (start_node.cost, start_node.id, []))
        
        while pq:
            current_cost, current_id, history = heapq.heappop(pq)
            
            if current_id in self.visited_nodes:
                continue
            
            self.visited_nodes.add(current_id)
            current_node = self.graph.nodes[current_id]
            
            # Generate Guidance for this step
            step_info = {
                "step_id": f"STEP_{len(path_guide) + 1}",
                "target_node": current_node.name,
                "action": "VERIFY",
                "instruction": current_node.verification_steps,
                "logic": self._generate_logic_string(current_node)
            }
            path_guide.append(step_info)
            
            # Termination condition: Found a Root Cause
            if current_node.type == NodeType.ROOT_CAUSE:
                logger.info(f"Root Cause identified: {current_node.name}")
                step_info["action"] = "REPAIR_ROOT_CAUSE"
                break
            
            # Expand search to children (propagation path)
            # If this node IS faulty, we go deeper. 
            # In a real scenario, this expansion happens based on the result of the verification.
            # Here we simulate the "Faulty Branch" path.
            children = self.graph.get_children(current_id)
            
            for child_id in children:
                if child_id not in self.visited_nodes:
                    child_node = self.graph.nodes[child_id]
                    new_cost = current_cost + child_node.cost
                    heapq.heappush(pq, (new_cost, child_id, history + [current_id]))
            
            if len(path_guide) > depth_limit * 2:
                logger.warning("Depth limit reached. Truncating search.")
                break
                
        return path_guide

    def _generate_logic_string(self, node: TopologyNode) -> str:
        """
        Helper function to generate contextual logic instructions.
        Input: TopologyNode
        Output: Logic string (e.g., "If voltage < 5V, proceed to check PowerSupply")
        """
        parents = self.graph.get_parents(node.id)
        logic = f"Check {node.name}. "
        
        if node.type == NodeType.ROOT_CAUSE:
            logic += "If abnormal, replace or repair this component."
        elif parents:
            logic += f"If abnormal, this is likely caused by issues in: {', '.join([self.graph.nodes[p].name for p in parents])}."
        else:
            logic += "If abnormal, proceed to downstream components."
            
        return logic


def build_aero_engine_demo_graph() -> FaultTopologyGraph:
    """
    Helper function to construct a demo graph for an Aero Engine system.
    
    Topology:
    High Vibration (Symptom) -> Bearing Wear (Inter) -> Oil Debris (Root)
    High Vibration (Symptom) -> Blade Damage (Inter) -> FOD (Root)
    """
    graph = FaultTopologyGraph()
    
    # Define Nodes
    # Symptom
    n1 = TopologyNode(
        id="SYM_01", name="High Engine Vibration", 
        type=NodeType.SYMPTOM, cost=5,
        verification_steps="Check Cockpit Vibration Gauge indicator > 2.5 units.",
        description="Excessive shaking detected by sensors."
    )
    # Intermediate
    n2 = TopologyNode(
        id="INT_01", name="Main Bearing Assembly", 
        type=NodeType.INTERMEDIATE, cost=20,
        verification_steps="Perform Spectral Analysis of vibration frequency (Look for 50Hz signature).",
        description="Friction in main rotation axis."
    )
    # Root Cause 1
    n3 = TopologyNode(
        id="ROOT_01", name="Oil System Contamination", 
        type=NodeType.ROOT_CAUSE, cost=15,
        verification_steps="Inspect Oil Filter for metal shavings.",
        description="Metal debris in oil damaging bearings."
    )
    # Intermediate 2
    n4 = TopologyNode(
        id="INT_02", name="Fan Blade Assembly", 
        type=NodeType.INTERMEDIATE, cost=15,
        verification_steps="Perform Borescope inspection of Fan Blades.",
        description="Physical damage to fan blades causing imbalance."
    )
    # Root Cause 2
    n5 = TopologyNode(
        id="ROOT_02", name="Foreign Object Debris (FOD)", 
        type=NodeType.ROOT_CAUSE, cost=10,
        verification_steps="Visual inspection of runway and intake.",
        description="Object ingested into engine."
    )

    # Add Nodes
    for n in [n1, n2, n3, n4, n5]:
        graph.add_node(n)

    # Add Edges (Causal Links: Cause -> Effect)
    # FOD -> Blade Damage -> Vibration
    graph.add_edge("ROOT_02", "INT_02")
    graph.add_edge("INT_02", "SYM_01")
    
    # Oil Debris -> Bearing Wear -> Vibration
    graph.add_edge("ROOT_01", "INT_01")
    graph.add_edge("INT_01", "SYM_01")
    
    return graph


if __name__ == "__main__":
    # Example Usage
    print("--- Initializing AGI Fault Navigation System ---")
    
    # 1. Build Knowledge Base
    aero_graph = build_aero_engine_demo_graph()
    
    # 2. Initialize Navigator
    navigator = DiagnosticNavigator(aero_graph)
    
    # 3. Trigger Navigation based on Symptom
    symptom_id = "SYM_01" # High Vibration
    
    try:
        print(f"\n>>> Diagnosing Symptom: {symptom_id}")
        repair_path = navigator.find_optimal_diagnostic_path(symptom_id)
        
        print("\n=== Generated Maintenance Guide ===")
        for step in repair_path:
            print(f"\n[{step['step_id']}] Target: {step['target_node']}")
            print(f"   Action: {step['action']}")
            print(f"   Instruction: {step['instruction']}")
            print(f"   Logic: {step['logic']}")
            
    except ValueError as e:
        logger.error(f"Navigation failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)