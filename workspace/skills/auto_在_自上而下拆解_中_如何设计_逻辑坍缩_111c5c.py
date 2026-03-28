"""
Module: logical_collapse_detector.py
Description: Detects logical and resource deadlocks (circular dependencies) during
             the Top-Down Decomposition of AGI skill nodes.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration of skill node types."""
    COMPOSITE = "composite"
    ATOMIC = "atomic"

@dataclass
class SkillNode:
    """
    Represents a node in the skill decomposition graph.
    
    Attributes:
        id: Unique identifier for the skill node.
        node_type: Type of the node (COMPOSITE or ATOMIC).
        dependencies: List of node IDs that this node depends on directly.
        resources_provided: List of abstract resources or outputs this node generates.
        resources_required: List of abstract resources or inputs this node needs to run.
    """
    id: str
    node_type: NodeType
    dependencies: List[str] = field(default_factory=list)
    resources_provided: List[str] = field(default_factory=list)
    resources_required: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Node ID must be a non-empty string.")
        if not isinstance(self.node_type, NodeType):
            raise TypeError(f"Invalid node_type. Must be NodeType enum.")


class LogicalCollapseError(Exception):
    """Custom exception raised when a logical collapse (deadlock) is detected."""
    pass

class InputValidationError(Exception):
    """Custom exception for invalid input data."""
    pass


def validate_decomposed_graph(nodes: List[SkillNode]) -> None:
    """
    Helper function to validate the structure of the decomposed graph.
    
    Args:
        nodes: List of SkillNode objects.
        
    Raises:
        InputValidationError: If the graph is empty or contains duplicate IDs.
    """
    if not nodes:
        raise InputValidationError("Node list cannot be empty.")
    
    node_ids = [node.id for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = set([x for x in node_ids if node_ids.count(x) > 1])
        raise InputValidationError(f"Duplicate node IDs detected: {duplicates}")
    
    logger.debug(f"Graph validation passed for {len(nodes)} nodes.")


def build_resource_dependency_graph(nodes: List[SkillNode]) -> Dict[str, Set[str]]:
    """
    Constructs an adjacency list representing dependencies based on resource flow.
    
    Logic:
    If Node A requires Resource X, and Node B provides Resource X, 
    then A depends on B (A -> B). We construct this mapping to detect 
    deadlocks caused by circular resource requirements.

    Args:
        nodes: List of SkillNode objects.

    Returns:
        A dictionary mapping Node ID to a set of Node IDs it depends on.
    """
    # Map resource name -> provider node ID
    # Note: This assumes one primary provider per resource for simplicity in this context.
    # In complex AGI, multiple providers might exist, requiring conflict resolution.
    resource_map: Dict[str, str] = {}
    
    for node in nodes:
        for res in node.resources_provided:
            resource_map[res] = node.id
            
    dependency_graph: Dict[str, Set[str]] = {node.id: set() for node in nodes}
    
    for node in nodes:
        # Add explicit dependencies
        for dep_id in node.dependencies:
            if dep_id in dependency_graph:
                dependency_graph[node.id].add(dep_id)
        
        # Add implicit resource dependencies
        for req in node.resources_required:
            if req in resource_map:
                provider_id = resource_map[req]
                if provider_id != node.id: # Self-dependency check
                    dependency_graph[node.id].add(provider_id)
                    
    return dependency_graph


def detect_circular_dependencies(
    node_id: str, 
    graph: Dict[str, Set[str]], 
    visited: Set[str], 
    recursion_stack: Set[str],
    path: List[str]
) -> Optional[List[str]]:
    """
    Recursive helper function using DFS to detect cycles.
    
    Args:
        node_id: Current node being visited.
        graph: Adjacency list of the graph.
        visited: Set of globally visited nodes.
        recursion_stack: Set of nodes in the current recursion stack (path).
        path: Current path taken (for error reporting).
        
    Returns:
        A list representing the cycle path if found, otherwise None.
    """
    visited.add(node_id)
    recursion_stack.add(node_id)
    path.append(node_id)

    for neighbor in graph.get(node_id, set()):
        if neighbor not in visited:
            result = detect_circular_dependencies(neighbor, graph, visited, recursion_stack, path)
            if result:
                return result
        elif neighbor in recursion_stack:
            # Cycle detected
            cycle_start_index = path.index(neighbor)
            return path[cycle_start_index:] + [neighbor]
            
    recursion_stack.remove(node_id)
    path.pop()
    return None


def analyze_logical_collapse(decomposed_nodes: List[SkillNode]) -> Dict[str, Any]:
    """
    Main entry point. Analyzes a set of decomposed nodes for logical collapse.
    
    Logical collapse is defined here as a state where atomic nodes cannot be executed
    because they are stuck in a dependency loop (Deadlock).
    
    Args:
        decomposed_nodes: A list of SkillNode objects resulting from decomposition.
        
    Returns:
        A dictionary containing:
        - 'is_valid': Boolean indicating if the logic is sound.
        - 'deadlock_path': List of node IDs forming the cycle (if any).
        - 'message': Status message.
        
    Raises:
        InputValidationError: If input data is invalid.
        
    Example:
        >>> nodes = [
        ...     SkillNode("A", NodeType.ATOMIC, resources_provided=["data1"], resources_required=["data2"]),
        ...     SkillNode("B", NodeType.ATOMIC, resources_provided=["data2"], resources_required=["data1"])
        ... ]
        >>> result = analyze_logical_collapse(nodes)
        >>> print(result['is_valid'])
        False
    """
    try:
        logger.info("Starting logical collapse analysis...")
        
        # 1. Validate Inputs
        validate_decomposed_graph(decomposed_nodes)
        
        # 2. Build Dependency Graph (Topological context)
        dep_graph = build_resource_dependency_graph(decomposed_nodes)
        
        # 3. Check for Cycles (Deadlocks)
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        
        for node in decomposed_nodes:
            if node.id not in visited:
                cycle = detect_circular_dependencies(
                    node.id, dep_graph, visited, recursion_stack, []
                )
                if cycle:
                    err_msg = f"Logical collapse detected! Cycle found: {' -> '.join(cycle)}"
                    logger.error(err_msg)
                    return {
                        "is_valid": False,
                        "deadlock_path": cycle,
                        "message": err_msg
                    }
        
        logger.info("Analysis complete. No logical deadlocks detected.")
        return {
            "is_valid": True,
            "deadlock_path": None,
            "message": "Decomposition logic is valid."
        }

    except InputValidationError as ive:
        logger.error(f"Input validation failed: {ive}")
        raise
    except Exception as e:
        logger.exception("Unexpected error during collapse analysis.")
        raise RuntimeError(f"Analysis failed: {e}")


if __name__ == "__main__":
    # --- Usage Example ---
    
    # Scenario: A web scraping skill decomposed into two atomic tasks that depend on each other incorrectly.
    # Task A needs the output of Task B, but Task B needs the config from Task A.
    
    try:
        print("--- Running Logical Collapse Detector Example ---")
        
        # 1. Define nodes with circular dependency
        node_fetch = SkillNode(
            id="fetch_data",
            node_type=NodeType.ATOMIC,
            resources_provided=["raw_html"],
            resources_required=["parsed_url"]  # Needs B's output
        )
        
        node_parse = SkillNode(
            id="parse_url",
            node_type=NodeType.ATOMIC,
            resources_provided=["parsed_url"],
            resources_required=["raw_html"]   # Needs A's output
        )
        
        # 2. Run analysis
        result = analyze_logical_collapse([node_fetch, node_parse])
        
        if not result['is_valid']:
            print(f"Validation Failed: {result['message']}")
            print(f"Deadlock involved nodes: {result['deadlock_path']}")
        else:
            print("System is stable.")
            
        # 3. Example of valid graph
        print("\n--- Testing Valid Graph ---")
        node_a = SkillNode("start", NodeType.ATOMIC, resources_provided=["init"])
        node_b = SkillNode("process", NodeType.ATOMIC, resources_required=["init"], resources_provided=["result"])
        
        valid_result = analyze_logical_collapse([node_a, node_b])
        print(f"Result: {valid_result['message']}")

    except Exception as e:
        print(f"Critical Error: {e}")