"""
Module: auto_oscillation_analyzer
A high-quality skill module for an AGI system to analyze the 'oscillation effects'
(i.e., ripple impact) when a core knowledge node undergoes a version iteration.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 1. Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Oscillation_Analyzer")


# 2. Data Structures and Enums
class NodeChangeType(Enum):
    """Defines the type of change a node underwent."""
    PATCH = 1       # Bug fix, backward compatible
    MINOR = 2       # New features, backward compatible
    MAJOR = 3       # Breaking changes (e.g., Newton -> Relativity)


class ImpactLevel(Enum):
    """Categorizes the severity of impact on downstream nodes."""
    SAFE = 0            # No action needed
    WARNING = 1         # Logic deprecation, needs review
    CRITICAL = 2        # Logic broken, requires refactoring
    CATASTROPHIC = 3    # Fundamental axiom conflict, system halt


@dataclass
class KnowledgeNode:
    """Represents a node in the AGI Knowledge Graph."""
    node_id: str
    version: str
    dependencies: Set[str] = field(default_factory=set)
    description: str = ""
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class RefactoringTask:
    """Represents a generated task to fix a broken node."""
    node_id: str
    reason: str
    impact_level: ImpactLevel
    suggested_action: str


# 3. Core Class
class OscillationAnalyzer:
    """
    Analyzes the ripple effects of version updates in a knowledge graph.
    
    This class simulates the propagation of 'truth' changes through a 
    dependency graph to determine which downstream nodes (derived concepts, 
    logic modules) become invalid or require updates.
    """

    def __init__(self, knowledge_base: Dict[str, KnowledgeNode]):
        """
        Initialize with a flat dictionary of knowledge nodes.
        
        Args:
            knowledge_base (Dict[str, KnowledgeNode]): Map of node_id to Node objects.
        """
        self.knowledge_base = knowledge_base
        self._dependency_graph = self._build_reverse_graph()
        logger.info(f"OscillationAnalyzer initialized with {len(knowledge_base)} nodes.")

    def _build_reverse_graph(self) -> Dict[str, Set[str]]:
        """
        Internal helper to build a reverse dependency graph (Parent -> Children).
        Helps in traversing downstream effects efficiently.
        """
        reverse_graph: Dict[str, Set[str]] = {}
        for node_id, node in self.knowledge_base.items():
            for dep_id in node.dependencies:
                if dep_id not in reverse_graph:
                    reverse_graph[dep_id] = set()
                reverse_graph[dep_id].add(node_id)
        return reverse_graph

    def _calculate_severity(self, change_type: NodeChangeType, depth: int) -> ImpactLevel:
        """
        Helper function to determine impact severity based on change type and distance.
        
        Args:
            change_type (NodeChangeType): The type of version iteration.
            depth (int): How many hops away the dependent node is.
            
        Returns:
            ImpactLevel: Calculated severity.
        """
        if change_type == NodeChangeType.PATCH:
            return ImpactLevel.SAFE
        
        if change_type == NodeChangeType.MAJOR:
            # Direct dependency on a breaking change is Critical
            if depth == 1:
                return ImpactLevel.CRITICAL
            # Indirect dependency might still be Warning or Critical depending on logic
            return ImpactLevel.WARNING if depth > 3 else ImpactLevel.CRITICAL
        
        # MINOR changes usually just need review
        return ImpactLevel.WARNING

    def analyze_oscillation(
        self, 
        target_node_id: str, 
        change_type: NodeChangeType
    ) -> Tuple[List[RefactoringTask], Dict[str, ImpactLevel]]:
        """
        Core Function 1: Triggers the impact analysis.
        
        Calculates the 'shockwave' of a node update through the system.
        
        Args:
            target_node_id (str): The ID of the node being updated (e.g., 'physics.gravity').
            change_type (NodeChangeType): The nature of the update.
            
        Returns:
            Tuple: A list of RefactoringTasks and a map of affected node IDs to their ImpactLevels.
        
        Raises:
            ValueError: If target_node_id is not found in knowledge base.
        """
        if target_node_id not in self.knowledge_base:
            logger.error(f"Node {target_node_id} not found.")
            raise ValueError(f"Node ID {target_node_id} does not exist.")

        logger.info(f"Starting oscillation analysis for {target_node_id} (Change: {change_type.name})")

        impact_map: Dict[str, ImpactLevel] = {}
        task_list: List[RefactoringTask] = []
        
        # BFS Queue: (node_id, current_depth)
        queue: List[Tuple[str, int]] = [(target_node_id, 0)]
        visited: Set[str] = {target_node_id}

        while queue:
            current_id, depth = queue.pop(0)
            
            # Find children (nodes that depend on current_id)
            children = self._dependency_graph.get(current_id, set())
            
            for child_id in children:
                if child_id in visited:
                    continue
                
                visited.add(child_id)
                new_depth = depth + 1
                
                # Calculate Impact
                severity = self._calculate_severity(change_type, new_depth)
                impact_map[child_id] = severity
                
                # Generate Task if not SAFE
                if severity != ImpactLevel.SAFE:
                    node = self.knowledge_base[child_id]
                    task = RefactoringTask(
                        node_id=child_id,
                        reason=f"Dependency '{current_id}' updated (v{change_type.name})",
                        impact_level=severity,
                        suggested_action=f"Verify logic in '{node.description}' against new axioms."
                    )
                    task_list.append(task)
                    logger.warning(f"Impact detected: {child_id} | Severity: {severity.name}")
                
                # Propagate wave (even if safe, we might want to track ripples, 
                # but for efficiency we stop traversing if impact is negligible? 
                # No, let's traverse full graph for this demo).
                queue.append((child_id, new_depth))
                
        return task_list, impact_map

    def generate_refactoring_report(self, tasks: List[RefactoringTask]) -> str:
        """
        Core Function 2: Generates a formatted report for the engineering/AGI team.
        
        Args:
            tasks (List[RefactoringTask]): List of tasks generated by the analysis.
            
        Returns:
            str: A formatted string report.
        """
        if not tasks:
            return "✅ Oscillation Analysis Complete: No refactoring required."

        report_lines = [
            "⚠️ OSCILLATION IMPACT REPORT ⚠️",
            "="*40,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Nodes Affected: {len(tasks)}",
            "-"*40
        ]

        # Sort tasks by severity
        sorted_tasks = sorted(tasks, key=lambda t: t.impact_level.value, reverse=True)

        for task in sorted_tasks:
            level_icon = "🔴" if task.impact_level == ImpactLevel.CRITICAL else "🟠"
            report_lines.append(
                f"{level_icon} [{task.impact_level.name}] {task.node_id}\n"
                f"   Reason: {task.reason}\n"
                f"   Action: {task.suggested_action}"
            )
        
        report_lines.append("="*40)
        return "\n".join(report_lines)


# 4. Usage Example
if __name__ == "__main__":
    # Mock Data: Simulating a Physics Knowledge Graph
    # Newtonian Mechanics is the 'Truth'
    node_physics = KnowledgeNode(
        node_id="mechanics.newton", 
        version="1.0", 
        description="Classical Mechanics"
    )
    
    # Engineering depends on Newton
    node_engineering = KnowledgeNode(
        node_id="eng.civil", 
        version="1.0", 
        dependencies={"mechanics.newton"}, 
        description="Bridge Design Principles"
    )
    
    # Space Flight depends on Newton
    node_space = KnowledgeNode(
        node_id="eng.space", 
        version="1.0", 
        dependencies={"mechanics.newton"}, 
        description="Orbital Mechanics"
    )
    
    # GPS depends on Space Flight
    node_gps = KnowledgeNode(
        node_id="tech.gps", 
        version="1.0", 
        dependencies={"eng.space"}, 
        description="Global Positioning System"
    )

    kb = {
        "mechanics.newton": node_physics,
        "eng.civil": node_engineering,
        "eng.space": node_space,
        "tech.gps": node_gps
    }

    # Initialize System
    analyzer = OscillationAnalyzer(kb)

    # SCENARIO: We update 'mechanics.newton' to 'mechanics.relativity' (Major Breaking Change)
    # This is the "Newton -> Einstein" paradigm shift.
    try:
        print("\n--- Simulating Version Iteration: mechanics.newton -> v2.0 (Relativity) ---\n")
        
        # Execute Analysis
        refactoring_tasks, impact_map = analyzer.analyze_oscillation(
            target_node_id="mechanics.newton",
            change_type=NodeChangeType.MAJOR
        )
        
        # Generate Report
        report = analyzer.generate_refactoring_report(refactoring_tasks)
        print(report)

    except ValueError as e:
        print(f"Simulation Error: {e}")