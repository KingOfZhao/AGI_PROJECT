"""
Module: auto_过程感知型知识图谱检索_pa_kgr_4a3647
Description: Implementation of Process-Aware Knowledge Graph Retrieval (PA-KGR).
             This module retrieves executable skill chains (paths) rather than
             isolated semantic nodes, designed for AGI skill execution.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PA_KGR_Engine")


class NodeState(Enum):
    """State of a specific node in the skill graph."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeCategory(Enum):
    """Category of the graph node."""
    CONCEPT = "concept"
    ACTION = "action"
    DECISION = "decision"
    VERIFICATION = "verification"


@dataclass
class SkillNode:
    """Represents a single node in the Process-Aware Knowledge Graph."""
    node_id: str
    label: str
    category: NodeCategory
    description: str
    dependencies: List[str] = field(default_factory=list)
    state: NodeState = NodeState.PENDING
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.node_id:
            raise ValueError("Node ID cannot be empty")


@dataclass
class RetrievalContext:
    """Context provided by the user/environment for retrieval."""
    current_node_id: Optional[str] = None
    goal_node_id: Optional[str] = None
    completed_nodes: Set[str] = field(default_factory=set)
    failed_nodes: Set[str] = field(default_factory=set)


class ProcessAwareKGR:
    """
    Process-Aware Knowledge Graph Retrieval Engine.

    This class manages a graph of operational skills and retrieves the optimal
    next steps based on the current context, ensuring valid topological paths
    (Pre-requisites -> Action -> Verification) are followed.
    """

    def __init__(self, graph_data: Optional[Dict] = None):
        """
        Initialize the PA-KGR engine.

        Args:
            graph_data (Optional[Dict]): Initial graph data to load.
        """
        self.graph: Dict[str, SkillNode] = {}
        self._adjacency_cache: Dict[str, List[str]] = {}
        if graph_data:
            self.load_graph(graph_data)
        logger.info("PA-KGR Engine initialized.")

    def load_graph(self, data: Dict) -> None:
        """
        Load and validate graph data into the engine.

        Args:
            data (Dict): Dictionary containing node definitions.

        Raises:
            ValueError: If data format is invalid.
        """
        if not isinstance(data, dict) or 'nodes' not in data:
            logger.error("Invalid graph data format provided.")
            raise ValueError("Input data must contain a 'nodes' key.")

        for node_dict in data['nodes']:
            try:
                # Data validation
                if 'id' not in node_dict or 'category' not in node_dict:
                    logger.warning(f"Skipping invalid node entry: {node_dict}")
                    continue

                node = SkillNode(
                    node_id=node_dict['id'],
                    label=node_dict.get('label', 'Untitled'),
                    category=NodeCategory(node_dict['category']),
                    description=node_dict.get('description', ''),
                    dependencies=node_dict.get('dependencies', []),
                    metadata=node_dict.get('metadata', {})
                )
                self.add_node(node)
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing node {node_dict.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Graph loaded with {len(self.graph)} nodes.")

    def add_node(self, node: SkillNode) -> None:
        """
        Add a single node to the graph.

        Args:
            node (SkillNode): The node object to add.
        """
        if node.node_id in self.graph:
            logger.warning(f"Overwriting existing node: {node.node_id}")

        self.graph[node.node_id] = node
        # Update adjacency list (simple dependency tracking)
        for dep_id in node.dependencies:
            if dep_id not in self._adjacency_cache:
                self._adjacency_cache[dep_id] = []
            self._adjacency_cache[dep_id].append(node.node_id)

    def get_node(self, node_id: str) -> Optional[SkillNode]:
        """
        Retrieve a node by ID.

        Args:
            node_id (str): The ID of the node.

        Returns:
            Optional[SkillNode]: The node object or None if not found.
        """
        return self.graph.get(node_id)

    def retrieve_process_path(self, query: str, context: RetrievalContext) -> Dict:
        """
        Core Function 1: Retrieve the optimal execution path based on query and current state.

        This method goes beyond semantic search. It calculates topological ordering
        to suggest the next actionable step.

        Args:
            query (str): The user query (e.g., "handle engine overheat").
            context (RetrievalContext): Current state of execution (where am I?).

        Returns:
            Dict: A structured response containing the immediate next step, the full path,
                  and status information.
        """
        logger.info(f"Retrieving path for query: '{query}' | Context: {context.current_node_id}")

        # 1. Identify Goal (Mock logic: In real AGI, this uses NLP to map query to goal_node)
        target_node_id = self._resolve_goal_from_query(query)
        if not target_node_id:
            return self._format_response("FAILURE", message="Goal could not be mapped to graph.")

        # 2. Pathfinding (Simplified Topological Sort / BFS for dependencies)
        try:
            execution_path = self._find_dependency_path(target_node_id, context.completed_nodes)
        except ValueError as e:
            logger.error(f"Pathfinding error: {e}")
            return self._format_response("ERROR", message=str(e))

        # 3. Determine Next Step
        next_step = None
        if execution_path:
            for node_id in execution_path:
                if node_id not in context.completed_nodes and node_id != context.current_node_id:
                    next_step = self.graph.get(node_id)
                    break
        
        # 4. Format Output
        if not next_step:
            return self._format_response("COMPLETED", message="All dependencies satisfied for goal, or goal reached.")

        return self._format_response(
            "SUCCESS",
            next_step=next_step,
            remaining_path=execution_path,
            explanation=f"Based on topology, next required step is '{next_step.label}'"
        )

    def evaluate_readiness(self, node_id: str, context: RetrievalContext) -> Dict:
        """
        Core Function 2: Evaluate if the user/system is ready to perform a specific node.

        Checks if all dependencies (Pre-requisites) are met.

        Args:
            node_id (str): The ID of the node to check.
            context (RetrievalContext): Current context containing completed nodes.

        Returns:
            Dict: Readiness status and blocking dependencies.
        """
        if node_id not in self.graph:
            raise ValueError(f"Node {node_id} does not exist.")

        node = self.graph[node_id]
        missing_deps = []
        
        for dep_id in node.dependencies:
            if dep_id not in context.completed_nodes:
                missing_deps.append(dep_id)

        is_ready = len(missing_deps) == 0
        
        return {
            "target_node": node.label,
            "is_ready": is_ready,
            "missing_dependencies": [self.graph[d].label for d in missing_deps if d in self.graph],
            "message": "Ready to execute." if is_ready else "Prerequisites missing."
        }

    # ---------------- Helper Functions ----------------

    def _resolve_goal_from_query(self, query: str) -> Optional[str]:
        """
        Helper: Map natural language query to a specific Graph Node ID.
        (Simulated implementation - assumes perfect match for demo)
        """
        # In a real system, this would use a vector index over the graph nodes.
        # Here we do a simple keyword match for robustness.
        query_hash = hashlib.md5(query.encode()).hexdigest() # Simulation
        
        # Heuristic: Check if any node matches the query description roughly
        for node_id, node in self.graph.items():
            if node.label.lower() in query.lower():
                return node_id
            if node.category == NodeCategory.VERIFICATION and "verify" in query.lower():
                return node_id
        
        # Fallback: Return the last added node as 'goal' for demo purposes
        if self.graph:
            return list(self.graph.keys())[-1]
        return None

    def _find_dependency_path(self, target_id: str, completed: Set[str]) -> List[str]:
        """
        Helper: Recursively resolve dependencies to build a linear execution path.
        Performs a topological sort limited to the dependency subtree of the target.
        """
        path = []
        visited = set()

        def dfs(node_id: str):
            if node_id in visited or node_id in completed:
                return
            if node_id not in self.graph:
                raise ValueError(f"Missing dependency node: {node_id}")
            
            visited.add(node_id)
            node = self.graph[node_id]
            
            # Visit dependencies first
            for dep_id in node.dependencies:
                dfs(dep_id)
            
            path.append(node_id)

        dfs(target_id)
        return path

    def _format_response(self, 
                         status: str, 
                         next_step: Optional[SkillNode] = None, 
                         remaining_path: List[str] = [], 
                         message: str = "") -> Dict:
        """Helper: Standardize the output format."""
        return {
            "status": status,
            "recommended_action": {
                "id": next_step.node_id,
                "label": next_step.label,
                "type": next_step.category.value,
                "instructions": next_step.description
            } if next_step else None,
            "execution_flow": remaining_path,
            "system_message": message
        }

# ---------------- Usage Example ----------------
if __name__ == "__main__":
    # 1. Define a sample Knowledge Graph (e.g., Engine Repair)
    sample_graph_data = {
        "nodes": [
            {"id": "stop_vehicle", "label": "Stop Vehicle", "category": "action", "description": "Pull over safely."},
            {"id": "open_hood", "label": "Open Hood", "category": "action", "description": "Release hood latch (requires vehicle stopped).", "dependencies": ["stop_vehicle"]},
            {"id": "check_coolant_temp", "label": "Check Coolant Temp", "category": "verification", "description": "Read temperature gauge.", "dependencies": ["stop_vehicle"]},
            {"id": "inspect_leaks", "label": "Inspect Leaks", "category": "action", "description": "Look for liquid under car.", "dependencies": ["open_hood"]},
            {"id": "refill_coolant", "label": "Refill Coolant", "category": "action", "description": "Add coolant if empty.", "dependencies": ["inspect_leaks", "check_coolant_temp"]}
        ]
    }

    # 2. Initialize Engine
    kgr_engine = ProcessAwareKGR(graph_data=sample_graph_data)

    # 3. Simulate a User Context (User has stopped the car)
    user_context = RetrievalContext(
        current_node_id="stop_vehicle",
        completed_nodes={"stop_vehicle"}
    )

    # 4. Query: "How do I fix the overheating?"
    # System should retrieve the NEXT step, not just 'stop_vehicle' again.
    result = kgr_engine.retrieve_process_path("fix overheating", user_context)

    print("-" * 50)
    print(f"Query Status: {result['status']}")
    if result['recommended_action']:
        print(f"Next Step: {result['recommended_action']['label']}")
        print(f"Instructions: {result['recommended_action']['instructions']}")
    print(f"Remaining Path: {result['execution_flow']}")
    print("-" * 50)

    # 5. Check readiness for 'refill_coolant' (Should fail initially)
    readiness = kgr_engine.evaluate_readiness("refill_coolant", user_context)
    print(f"Readiness to Refill: {readiness['is_ready']}")
    print(f"Missing: {readiness['missing_dependencies']}")