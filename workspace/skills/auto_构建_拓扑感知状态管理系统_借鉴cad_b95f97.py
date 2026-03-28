"""
Auto-generated Skill: 拓扑感知状态管理系统
Inspired by CAD Assembly Tree Visualization.

This module provides tools to analyze Flutter application architecture by treating
the Widget tree as a topological graph. It identifies dependencies, visualizes
state propagation paths, detects circular dependencies, and highlights potential
performance bottlenecks (e.g., excessive repainting).
"""

import logging
import json
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration of possible node types in the dependency graph."""
    WIDGET = "WIDGET"
    STATE_MANAGER = "STATE_MANAGER"
    SERVICE = "SERVICE"

@dataclass
class TopologyNode:
    """
    Represents a node in the Dependency Topology Graph.
    
    Attributes:
        id: Unique identifier for the node.
        name: Class name or identifier of the component.
        node_type: Type of the component (Widget, State, etc.).
        children: List of child node IDs.
        dependencies: List of IDs this node depends on (e.g., Provider consumption).
        render_count: Simulated metric for how often this node rebuilds.
    """
    id: str
    name: str
    node_type: NodeType
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    render_count: int = 0

class TopologyAwareStateManager:
    """
    Manages the topology of the application state and widget tree.
    
    Provides functionalities to analyze the graph structure, detect anomalies,
    and simulate state propagation.
    """

    def __init__(self):
        """Initialize the graph storage and index structures."""
        self.nodes: Dict[str, TopologyNode] = {}
        self._adjacency_cache: Optional[Dict[str, Set[str]]] = None
        logger.info("TopologyAwareStateManager initialized.")

    def _invalidate_cache(self) -> None:
        """Invalidate the adjacency cache when graph changes."""
        self._adjacency_cache = None

    def add_node(self, node: TopologyNode) -> bool:
        """
        Add a node to the topology graph.
        
        Args:
            node: The TopologyNode object to add.
            
        Returns:
            True if successful, False if node ID already exists.
        """
        if not isinstance(node, TopologyNode):
            logger.error("Invalid node type provided.")
            return False
        
        if node.id in self.nodes:
            logger.warning(f"Node ID {node.id} already exists.")
            return False
            
        self.nodes[node.id] = node
        self._invalidate_cache()
        logger.debug(f"Node added: {node.id} ({node.name})")
        return True

    def build_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        Establish a parent-child relationship (Tree edge).
        
        Args:
            parent_id: ID of the parent node.
            child_id: ID of the child node.
            
        Returns:
            True if successful, False if nodes not found.
        """
        if parent_id not in self.nodes or child_id not in self.nodes:
            logger.error(f"Cannot build relationship: Node IDs {parent_id} or {child_id} missing.")
            return False
            
        self.nodes[parent_id].children.append(child_id)
        self._invalidate_cache()
        return True

    def add_dependency(self, consumer_id: str, source_id: str) -> bool:
        """
        Establish a data dependency (Data flow edge).
        
        Args:
            consumer_id: ID of the node consuming data.
            source_id: ID of the node providing data (State).
            
        Returns:
            True if successful.
        """
        if consumer_id not in self.nodes or source_id not in self.nodes:
            return False
            
        self.nodes[consumer_id].dependencies.append(source_id)
        self._invalidate_cache()
        return True

    def analyze_circular_dependencies(self) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.
        
        Returns:
            A list of cycles found (each cycle is a list of node IDs).
        """
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        cycles: List[List[str]] = []
        
        def _dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            recursion_stack.add(node_id)
            path.append(node_id)
            
            # Check both structural children and data dependencies
            neighbors = self.nodes[node_id].children + self.nodes[node_id].dependencies
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    _dfs(neighbor, path)
                elif neighbor in recursion_stack:
                    # Cycle detected
                    cycle_start_index = path.index(neighbor)
                    cycle = path[cycle_start_index:] + [neighbor]
                    cycles.append(cycle)
                    logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            path.pop()
            recursion_stack.remove(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                _dfs(node_id, [])
                
        return cycles

    def simulate_state_change(self, source_node_id: str) -> Dict[str, Any]:
        """
        Simulate a state change and calculate the impact chain (Topological Awareness).
        
        This mimics how a CAD system highlights affected parts when a parameter changes.
        
        Args:
            source_node_id: The ID of the node where state changed.
            
        Returns:
            A dictionary containing 'affected_nodes', 'bottlenecks', and 'visualization_data'.
        """
        if source_node_id not in self.nodes:
            logger.error(f"Source node {source_node_id} not found.")
            return {}

        affected_nodes: Set[str] = set()
        bottleneck_nodes: List[Dict[str, Any]] = []
        
        # BFS to find all downstream consumers
        queue = [source_node_id]
        visited = set([source_node_id])
        
        while queue:
            current_id = queue.pop(0)
            current_node = self.nodes[current_id]
            
            # In a real scenario, this would check listeners/providers
            # Here we check if other nodes depend on this one
            for node_id, node in self.nodes.items():
                if current_id in node.dependencies and node_id not in visited:
                    visited.add(node_id)
                    queue.append(node_id)
                    affected_nodes.add(node_id)
                    
                    # Update render count for simulation
                    node.render_count += 1
                    
                    # Detect performance bottleneck (heuristic: heavy subtree or high render count)
                    subtree_size = self._calculate_subtree_size(node_id)
                    if node.render_count > 5 or subtree_size > 20:
                        bottleneck_nodes.append({
                            "node_id": node_id,
                            "reason": "High repaint frequency" if node.render_count > 5 else "Heavy subtree rebuild",
                            "render_count": node.render_count,
                            "subtree_size": subtree_size
                        })

        # Generate visualization format (e.g., for Graphviz or Flutter Canvas)
        vis_data = self._generate_graph_higlight_data(source_node_id, affected_nodes)
        
        return {
            "source": source_node_id,
            "affected_nodes": list(affected_nodes),
            "bottlenecks": bottleneck_nodes,
            "visualization": vis_data
        }

    def _calculate_subtree_size(self, node_id: str) -> int:
        """
        Helper: Recursively calculate the size of the widget subtree.
        
        Args:
            node_id: Root of the subtree.
            
        Returns:
            Total count of nodes in the subtree.
        """
        count = 1
        if node_id not in self.nodes:
            return 0
            
        for child_id in self.nodes[node_id].children:
            count += self._calculate_subtree_size(child_id)
        return count

    def _generate_graph_higlight_data(self, source_id: str, affected_ids: Set[str]) -> Dict:
        """
        Helper: Generate data structure for UI visualization.
        
        Format:
        {
            "nodes": [{"id": "x", "color": "red/grey"}, ...],
            "edges": [{"from": "a", "to": "b", "animated": true}, ...]
        }
        """
        nodes = []
        edges = []
        
        for nid, node in self.nodes.items():
            color = "grey"
            if nid == source_id:
                color = "red" # Source of change
            elif nid in affected_ids:
                color = "orange" # Impacted
                
            nodes.append({"id": nid, "label": node.name, "color": color})
            
            # Add child edges
            for child in node.children:
                edges.append({
                    "from": nid, 
                    "to": child, 
                    "animated": (nid == source_id or nid in affected_ids) and child in affected_ids
                })
            # Add dependency edges
            for dep in node.dependencies:
                edges.append({
                    "from": nid, 
                    "to": dep, 
                    "dashed": True,
                    "animated": (nid in affected_ids)
                })
                
        return {"nodes": nodes, "edges": edges}

# Usage Example
if __name__ == "__main__":
    # Initialize system
    topo_system = TopologyAwareStateManager()
    
    # Create nodes (Widgets and State)
    root = TopologyNode("1", "MyApp", NodeType.WIDGET)
    state_a = TopologyNode("2", "AppStore", NodeType.STATE_MANAGER)
    widget_list = TopologyNode("3", "UserList", NodeType.WIDGET)
    widget_item = TopologyNode("4", "UserCard", NodeType.WIDGET)
    heavy_widget = TopologyNode("5", "ComplexChart", NodeType.WIDGET)
    
    # Build tree
    topo_system.add_node(root)
    topo_system.add_node(state_a)
    topo_system.add_node(widget_list)
    topo_system.add_node(widget_item)
    topo_system.add_node(heavy_widget)
    
    topo_system.build_relationship("1", "3") # MyApp -> UserList
    topo_system.build_relationship("3", "4") # UserList -> UserCard
    topo_system.build_relationship("3", "5") # UserList -> ComplexChart
    
    # Add data dependencies
    topo_system.add_dependency("3", "2") # UserList listens to AppStore
    topo_system.add_dependency("4", "2") # UserCard listens to AppStore
    
    # Simulate a cycle for testing
    # topo_system.add_dependency("2", "4") # Bad practice: State depends on Child Widget
    
    # 1. Check for circular dependencies
    cycles = topo_system.analyze_circular_dependencies()
    print(f"Cycles found: {len(cycles)}")
    
    # 2. Simulate State Change in 'AppStore'
    print("\nSimulating state change in AppStore (ID: 2)...")
    impact = topo_system.simulate_state_change("2")
    
    print(f"Affected Nodes: {impact['affected_nodes']}")
    print(f"Bottlenecks detected: {impact['bottlenecks']}")
    
    # Output visualization data
    # print(json.dumps(impact['visualization'], indent=2))