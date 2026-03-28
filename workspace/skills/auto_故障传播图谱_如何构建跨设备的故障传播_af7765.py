"""
Module: auto_故障传播图谱_如何构建跨设备的故障传播_af7765

Description:
    This module implements a Fault Propagation Directed Graph (FPDG) designed for
    AGI systems. It moves beyond simple error reporting by establishing logical
    causal links between non-adjacent nodes across devices.
    
    It allows the system to deduce downstream consequences (e.g., 'Product Shrinkage
    Increase') from an upstream anomaly (e.g., 'Injection Temperature Anomaly')
    based on historical propagation logic.

Key Features:
    - Construction of a directed graph for fault propagation.
    - Support for non-adjacent node inference (transitive closure).
    - Data validation and graph integrity checks.
    - Detailed logging and error handling.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type Aliases for clarity
NodeID = str
EdgeWeight = float  # Probability or Impact Score

class FaultPropagationGraph:
    """
    A class to represent a Fault Propagation Directed Graph.

    This class manages nodes (devices/states) and edges (causal links),
    allowing for the prediction of downstream failures.

    Attributes:
        nodes (Set[NodeID]): A set of all unique node identifiers.
        adj_list (Dict[NodeID, List[Tuple[NodeID, EdgeWeight]]]): Adjacency list representing edges.
    """

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.nodes: Set[NodeID] = set()
        self.adj_list: Dict[NodeID, List[Tuple[NodeID, EdgeWeight]]] = {}
        logger.info("Initialized empty FaultPropagationGraph.")

    def add_node(self, node_id: NodeID, description: Optional[str] = None) -> None:
        """
        Add a node to the graph if it doesn't exist.

        Args:
            node_id (NodeID): Unique identifier for the node (e.g., "DeviceA_TempHigh").
            description (Optional[str]): Human-readable description of the fault state.
        """
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("Node ID must be a non-empty string.")
        
        if node_id not in self.nodes:
            self.nodes.add(node_id)
            self.adj_list[node_id] = []
            logger.debug(f"Node added: {node_id}")

    def add_edge(
        self, 
        source: NodeID, 
        target: NodeID, 
        weight: EdgeWeight = 1.0
    ) -> None:
        """
        Add a directed edge representing a causal link.

        Args:
            source (NodeID): The originating fault node.
            target (NodeID): The resulting fault node.
            weight (EdgeWeight): The likelihood or impact strength (0.0 to 1.0).

        Raises:
            ValueError: If weight is out of bounds or nodes do not exist.
        """
        # Data Validation
        if not (0.0 <= weight <= 1.0):
            raise ValueError("Edge weight must be between 0.0 and 1.0.")
        
        if source not in self.nodes:
            raise ValueError(f"Source node '{source}' does not exist.")
        if target not in self.nodes:
            raise ValueError(f"Target node '{target}' does not exist.")

        # Check for duplicate edges (simple check)
        existing_targets = [t for t, w in self.adj_list[source]]
        if target in existing_targets:
            logger.warning(f"Edge from {source} to {target} already exists. Skipping.")
            return

        self.adj_list[source].append((target, weight))
        logger.info(f"Edge added: {source} -> {target} (Weight: {weight})")

    def build_transitive_logic(self) -> None:
        """
        (Helper/Advanced)
        Pre-calculates transitive paths if needed for optimization.
        Currently, we use BFS for dynamic traversal in `predict_propagation`.
        """
        # Placeholder for potential optimization logic (e.g., Floyd-Warshall)
        pass

    def predict_propagation(
        self, 
        start_node: NodeID, 
        depth_limit: int = 5
    ) -> Dict[NodeID, List[str]]:
        """
        Core Function: Predicts all downstream effects from a starting fault.
        
        Uses Breadth-First Search (BFS) to traverse non-adjacent nodes recursively.

        Args:
            start_node (NodeID): The initial fault event.
            depth_limit (int): Maximum propagation depth to prevent infinite loops.

        Returns:
            Dict[NodeID, List[str]]: A dictionary mapping affected nodes to their 
                                     propagation path logic.

        Example:
            >>> graph.predict_propagation("Temp_Anomaly")
            {'Cooling_Extend': ['Temp_Anomaly -> Cooling_Extend'], ...}
        """
        if start_node not in self.nodes:
            logger.error(f"Start node {start_node} not found in graph.")
            return {}

        visited: Set[NodeID] = {start_node}
        queue: deque[Tuple[NodeID, int, str]] = deque([(start_node, 0, start_node)])
        results: Dict[NodeID, List[str]] = {}

        logger.info(f"Starting propagation analysis from: {start_node}")

        while queue:
            current_node, current_depth, path = queue.popleft()

            if current_depth >= depth_limit:
                continue

            # Explore neighbors
            for neighbor, weight in self.adj_list.get(current_node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = f"{path} -> {neighbor}"
                    
                    # Record result
                    results[neighbor] = [new_path, f"Impact: {weight}"]
                    
                    # Enqueue for further traversal
                    queue.append((neighbor, current_depth + 1, new_path))
                    
        return results


def validate_graph_data(raw_data: Dict) -> bool:
    """
    Helper Function: Validates the input data structure before graph construction.

    Args:
        raw_data (Dict): Dictionary containing 'nodes' and 'edges' lists.

    Returns:
        bool: True if data is valid.
    
    Raises:
        KeyError: If required keys are missing.
        TypeError: If data types are incorrect.
    """
    if "nodes" not in raw_data or "edges" not in raw_data:
        raise KeyError("Input data must contain 'nodes' and 'edges' keys.")
    
    if not isinstance(raw_data["nodes"], list) or not isinstance(raw_data["edges"], list):
        raise TypeError("'nodes' and 'edges' must be lists.")
    
    logger.debug("Input data structure validated.")
    return True


# --- Usage Example and Execution ---

if __name__ == "__main__":
    # 1. Define Input Data (Simulating historical data analysis result)
    # Domain: Injection Molding Machine Faults
    manufacturing_data = {
        "nodes": [
            {"id": "A", "desc": "Injection Temp High"},
            {"id": "B", "desc": "Cooling System Overload"},
            {"id": "C", "desc": "Cycle Time Extended"},
            {"id": "D", "desc": "Product Shrinkage Rate High"},
            {"id": "E", "desc": "Packaging Line Jam Risk"}
        ],
        "edges": [
            {"src": "A", "dst": "B", "weight": 0.9},
            {"src": "B", "dst": "C", "weight": 0.85},
            {"src": "C", "dst": "D", "weight": 0.6}, # Non-adjacent logic: Cycle time affects quality
            {"src": "A", "dst": "D", "weight": 0.3}, # Direct but weaker link
            {"src": "D", "dst": "E", "weight": 0.4}
        ]
    }

    try:
        # 2. Validate Data
        validate_graph_data(manufacturing_data)

        # 3. Build Graph
        fpg = FaultPropagationGraph()
        
        # Add Nodes
        for node in manufacturing_data["nodes"]:
            fpg.add_node(node["id"], node.get("desc"))

        # Add Edges (Cross-device logic)
        for edge in manufacturing_data["edges"]:
            fpg.add_edge(edge["src"], edge["dst"], edge.get("weight", 1.0))

        # 4. Execute Prediction (Reasoning)
        # Scenario: Sensor detects 'Injection Temp High' (Node A)
        start_event = "A"
        prediction = fpg.predict_propagation(start_event)

        print(f"\n=== Fault Propagation Report for Node {start_event} ===")
        if not prediction:
            print("No downstream effects detected.")
        else:
            for affected_node, details in prediction.items():
                print(f"Affected Node: {affected_node}")
                print(f"  Propagation Path: {details[0]}")
                print(f"  Metrics: {details[1]}")
                print("-" * 40)

    except ValueError as ve:
        logger.error(f"Data Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"System Error: {e}", exc_info=True)