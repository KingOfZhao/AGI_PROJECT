"""
Advanced Skill Module for AGI: Top-Down Recursive Task Decomposition & Dependency Management.

This module implements a sophisticated algorithm to break down high-level objectives
(e.g., 'Build an E-commerce Website') into a structured hierarchy of atomic tasks.
It constructs a Directed Acyclic Graph (DAG) to manage dependencies between these tasks,
determining automatically when to halt decomposition based on task complexity or
availability of existing Skills.

Design Philosophy:
- Recursive Decomposition: Tasks are broken down until they meet specific "Atomic" criteria.
- Dependency Graph: Uses NetworkX to model and validate execution order.
- Heuristic Atomicity: Determines stopping conditions based on estimated complexity and available tools.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import networkx as nx
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TaskDecomposer")

class TaskComplexity(Enum):
    """Enumeration representing the complexity level of a task."""
    ATOMIC = 1       # Cannot be broken down further, directly executable
    COMPOSITE = 2    # Requires further breakdown
    UNKNOWN = 3      # Needs analysis

@dataclass
class TaskNode:
    """
    Represents a node in the task graph.
    
    Attributes:
        id: Unique identifier for the task (e.g., UUID or semantic path).
        description: Human-readable description of the task.
        complexity: Estimated complexity of the task.
        dependencies: List of TaskNode IDs that must precede this task.
        parameters: Dictionary of parameters required for execution.
        skill_name: The name of the Skill to call if the task is atomic.
    """
    id: str
    description: str
    complexity: TaskComplexity = TaskComplexity.UNKNOWN
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    skill_name: Optional[str] = None

class TaskDecomposer:
    """
    Core class responsible for decomposing high-level goals into executable DAGs.
    """

    def __init__(self, max_depth: int = 5, complexity_threshold: float = 0.3):
        """
        Initialize the decomposer.

        Args:
            max_depth (int): Maximum recursion depth to prevent infinite loops.
            complexity_threshold (float): Threshold (0.0 to 1.0) below which a task is considered atomic.
        """
        if not 0.0 <= complexity_threshold <= 1.0:
            raise ValueError("Complexity threshold must be between 0.0 and 1.0")
        
        self.max_depth = max_depth
        self.complexity_threshold = complexity_threshold
        self.task_graph = nx.DiGraph()
        self._node_registry: Dict[str, TaskNode] = {}
        
        # Mock database of existing atomic skills for simulation
        self._existing_skills_db = {
            "setup_server_environment", 
            "configure_dns",
            "install_database",
            "write_api_endpoint",
            "design_html_page",
            "write_unit_test",
            "deploy_code"
        }
        logger.info("TaskDecomposer initialized with max_depth=%d", max_depth)

    def _estimate_complexity(self, task_description: str) -> float:
        """
        Heuristic function to estimate task complexity.
        Returns a score between 0.0 (simple) and 1.0 (very complex).
        
        Args:
            task_description (str): The description of the task.
            
        Returns:
            float: Complexity score.
        """
        # Simple heuristic: longer descriptions or keywords like 'system', 'architecture' imply higher complexity
        base_score = min(len(task_description) / 100, 0.5)
        if any(kw in task_description.lower() for kw in ['architecture', 'system', 'integrate', 'end-to-end']):
            base_score += 0.4
        elif any(kw in task_description.lower() for kw in ['write', 'create', 'setup']):
            base_score += 0.1
        else:
            base_score += 0.2
        
        return min(base_score, 1.0)

    def _check_skill_availability(self, task_description: str) -> Optional[str]:
        """
        Checks if there is an existing Skill that matches the task description.
        
        Args:
            task_description (str): The task description.
            
        Returns:
            Optional[str]: The name of the skill if found, else None.
        """
        # Naive matching for simulation purposes
        desc_lower = task_description.lower()
        for skill in self._existing_skills_db:
            if skill.replace("_", " ") in desc_lower:
                return skill
        return None

    def decompose(self, root_goal: str) -> nx.DiGraph:
        """
        Public entry point for decomposition.
        
        Args:
            root_goal (str): The high-level objective.
            
        Returns:
            nx.DiGraph: The dependency graph of tasks.
        """
        logger.info(f"Starting decomposition for goal: '{root_goal}'")
        root_node = TaskNode(id="root", description=root_goal)
        self._node_registry[root_node.id] = root_node
        
        self._recursive_decompose(root_node, current_depth=0)
        
        self.task_graph.add_nodes_from(self._node_registry.keys())
        for node in self._node_registry.values():
            for dep in node.dependencies:
                self.task_graph.add_edge(dep, node.id)
        
        if not nx.is_directed_acyclic_graph(self.task_graph):
            logger.error("Generated graph contains cycles! Dependency resolution failed.")
            raise ValueError("Dependency graph validation failed: Cycle detected.")
            
        return self.task_graph

    def _recursive_decompose(self, parent_node: TaskNode, current_depth: int):
        """
        Core recursive algorithm to break down tasks.
        
        Args:
            parent_node (TaskNode): The task node to decompose.
            current_depth (int): Current recursion depth.
        """
        if current_depth >= self.max_depth:
            logger.warning(f"Max recursion depth reached at node: {parent_node.id}")
            parent_node.complexity = TaskComplexity.ATOMIC
            parent_node.skill_name = "generic_execution_skill"
            return

        # 1. Analyze complexity and skill availability
        complexity_score = self._estimate_complexity(parent_node.description)
        available_skill = self._check_skill_availability(parent_node.description)

        # 2. Determine Atomicity
        is_atomic = False
        if available_skill:
            parent_node.skill_name = available_skill
            is_atomic = True
            logger.debug(f"Atomic task found via Skill: {available_skill}")
        elif complexity_score < self.complexity_threshold:
            is_atomic = True
            parent_node.skill_name = "generic_execution_skill"
            logger.debug(f"Atomic task found via complexity threshold: {complexity_score}")

        if is_atomic:
            parent_node.complexity = TaskComplexity.ATOMIC
            return

        # 3. Decompose (Simulation of LLM-based decomposition logic)
        # In a real AGI, this step would query an LLM to generate sub-tasks.
        # Here we simulate decomposition based on the parent description.
        parent_node.complexity = TaskComplexity.COMPOSITE
        sub_tasks = self._generate_sub_tasks_logic(parent_node.description)
        
        if not sub_tasks:
            # Fallback if decomposition fails
            parent_node.complexity = TaskComplexity.ATOMIC
            return

        # 4. Link dependencies and recurse
        for i, sub_desc in enumerate(sub_tasks):
            sub_id = f"{parent_node.id}_{i+1}"
            sub_node = TaskNode(id=sub_id, description=sub_desc)
            
            # Add dependency: previous subtask must finish before next (Sequential dependency example)
            if i > 0:
                sub_node.dependencies.append(f"{parent_node.id}_{i}")
            else:
                # First subtask depends on parent's prerequisites? 
                # For simplicity in DAG, we usually map flow as Parent -> Child.
                # Here we assume the children replace the parent in the execution flow.
                pass
            
            self._node_registry[sub_id] = sub_node
            parent_node.dependencies.append(sub_id) # Parent tracks children (though execution flows through children)
            
            # Recurse
            self._recursive_decompose(sub_node, current_depth + 1)

    def _generate_sub_tasks_logic(self, description: str) -> List[str]:
        """
        Helper function to simulate the generation of sub-tasks.
        In a real system, this would be a call to an LLM or a Planning Engine.
        """
        logger.info(f"Simulating decomposition for: {description}")
        if "e-commerce" in description.lower():
            return [
                "Design system architecture",
                "Setup server environment",
                "Develop user authentication API",
                "Design product catalog database",
                "Implement shopping cart logic",
                "Deploy code to production"
            ]
        elif "setup server" in description.lower():
            return [
                "Provision virtual machine",
                "Configure DNS settings",
                "Install Docker environment"
            ]
        elif "develop user authentication" in description.lower():
            return [
                "Define user schema",
                "Write API endpoint for registration",
                "Write API endpoint for login",
                "Write unit test for auth"
            ]
        elif "design" in description.lower():
             return [] # Stop condition for simulation
        elif "deploy" in description.lower():
             return [] # Stop condition
        else:
            return []

def validate_dag(graph: nx.DiGraph) -> bool:
    """
    Validates the integrity of the task graph.
    
    Args:
        graph (nx.DiGraph): The graph to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not nx.is_directed_acyclic_graph(graph):
        return False
    if graph.number_of_nodes() == 0:
        return False
    return True

def main():
    """Usage Example"""
    # 1. Initialize Decomposer
    decomposer = TaskDecomposer(max_depth=3, complexity_threshold=0.4)
    
    # 2. Define Goal
    goal = "Build an e-commerce website"
    
    try:
        # 3. Execute Decomposition
        dag = decomposer.decompose(goal)
        
        # 4. Validate and Display
        if validate_dag(dag):
            print("\n=== Task Decomposition Successful ===")
            print(f"Total Nodes: {dag.number_of_nodes()}")
            print(f"Total Edges: {dag.number_of_edges()}")
            
            print("\n--- Execution Order (Topological Sort) ---")
            # Mapping node IDs back to descriptions for display
            sorted_nodes = list(nx.topological_sort(dag))
            for node_id in sorted_nodes:
                node = decomposer._node_registry[node_id]
                skill_info = f"[Skill: {node.skill_name}]" if node.skill_name else ""
                print(f"ID: {node_id:<20} | Desc: {node.description:<40} {skill_info}")
        else:
            print("Failed to generate a valid DAG.")
            
    except Exception as e:
        logger.error(f"An error occurred during decomposition: {e}")

if __name__ == "__main__":
    main()