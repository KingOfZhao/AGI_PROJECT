"""
Module: auto_falsification_boundary.py
Description: Implements dynamic algorithms to define the 'Minimum Executable Unit' (MEU)
             during top-down task decomposition. It ensures the decomposition granularity
             aligns with the existing SKILL library (approx. 132 skills) to prevent
             execution failures (too coarse) or resource waste (too fine).
Author: Senior Python Engineer (AGI Systems)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FalsificationBoundary")

class SkillType(Enum):
    """Classification of skills available in the library."""
    ATOMIC = "ATOMIC"       # Non-decomposable actions
    COMPOSITE = "COMPOSITE" # Actions made of other skills
    ABSTRACT = "ABSTRACT"   # High-level concepts requiring decomposition

@dataclass
class Skill:
    """Represents a single unit of capability within the AGI system."""
    id: str
    name: str
    type: SkillType
    keywords: List[str]
    complexity: float  # 0.0 (simple) to 1.0 (complex)
    description: str = ""

@dataclass
class TaskNode:
    """Represents a node in the task decomposition tree."""
    id: str
    name: str
    description: str
    depth: int = 0
    is_executable: bool = False
    children: List['TaskNode'] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)

class FalsificationBoundaryError(Exception):
    """Custom exception for boundary determination failures."""
    pass

class AutoFalsificationBoundary:
    """
    Determines the optimal stopping condition (falsification boundary) for task decomposition.
    
    This class analyzes the semantic distance between a generated sub-task and the 
    existing Skill Library. It calculates a 'Specificity Score' to decide if a task
    is specific enough to match an existing skill (stopping decomposition) or if 
    it requires further breakdown.
    """

    def __init__(self, skill_library: List[Skill], max_depth: int = 5):
        """
        Initialize with the available skill set.
        
        Args:
            skill_library (List[Skill]): The list of available skills (the 132 SKILLs).
            max_depth (int): Safety limit to prevent infinite recursion.
        """
        if not skill_library:
            raise FalsificationBoundaryError("Skill library cannot be empty.")
        
        self.skill_library = skill_library
        self.max_depth = max_depth
        self._index_skills()
        logger.info(f"Initialized Falsification Boundary with {len(skill_library)} skills.")

    def _index_skills(self) -> None:
        """Builds a lookup index for skills based on keywords for fast retrieval."""
        self.keyword_index: Dict[str, List[Skill]] = {}
        for skill in self.skill_library:
            for kw in skill.keywords:
                if kw not in self.keyword_index:
                    self.keyword_index[kw] = []
                self.keyword_index[kw].append(skill)

    def _calculate_semantic_coverage(self, task_desc: str) -> Tuple[float, Optional[Skill]]:
        """
        Helper: Calculates how well the task description matches existing skills.
        
        Uses a simple keyword overlap heuristic (Jaccard index variant) for demonstration.
        In production, this would use vector embeddings.
        
        Args:
            task_desc (str): The description of the task node.
            
        Returns:
            Tuple[float, Optional[Skill]]: Coverage score (0.0-1.0) and the best matching skill.
        """
        tokens = set(task_desc.lower().split())
        if not tokens:
            return 0.0, None
            
        best_match: Optional[Skill] = None
        max_score = 0.0
        
        # Identify candidate skills
        candidate_skills = set()
        for token in tokens:
            if token in self.keyword_index:
                candidate_skills.update(self.keyword_index[token])
        
        if not candidate_skills:
            return 0.0, None

        # Score candidates
        for skill in candidate_skills:
            skill_tokens = set(skill.name.lower().split()) | set(skill.keywords)
            intersection = len(tokens & skill_tokens)
            union = len(tokens | skill_tokens)
            score = intersection / union if union > 0 else 0.0
            
            # Weight by complexity penalty (prefer simpler skills for execution)
            adjusted_score = score * (1.1 - skill.complexity)
            
            if adjusted_score > max_score:
                max_score = adjusted_score
                best_match = skill
                
        return max_score, best_match

    def determine_meu(self, task: TaskNode) -> TaskNode:
        """
        Core Function: Recursively analyzes a task tree to determine the Minimum Executable Unit.
        
        It traverses the tree. If a node matches a skill sufficiently, it marks it as executable
        and prunes further decomposition (Falsification Boundary). If not, it expects children
        or flags an error if max depth is reached without a match.
        
        Args:
            task (TaskNode): The root task node to analyze.
            
        Returns:
            TaskNode: The processed node with executable flags set.
        """
        logger.debug(f"Analyzing Task: {task.name} (Depth: {task.depth})")
        
        # Boundary Check 1: Max Depth reached
        if task.depth > self.max_depth:
            logger.warning(f"Max depth reached for task {task.name}. Forcing boundary check.")
            task.is_executable = False # Needs to be handled by fallback
            return task

        # Calculate Match
        coverage, matched_skill = self._calculate_semantic_coverage(task.description)
        
        # Dynamic Threshold: Deeper tasks need higher specificity to stop decomposition
        # This prevents stopping too early at high levels.
        dynamic_threshold = 0.6 + (task.depth * 0.05) 
        
        if coverage >= dynamic_threshold and matched_skill:
            # Found a match in the skill library -> This is an MEU
            task.is_executable = True
            task.required_skills = [matched_skill.id]
            logger.info(f"BOUNDARY HIT: Task '{task.name}' matches Skill '{matched_skill.name}' (Score: {coverage:.2f})")
            # Prune children if they exist (conceptually, we stop here)
            task.children = [] 
            return task
            
        # If no match, we need to decompose. 
        # In a real AGI system, this would call a Planner. Here we simulate by checking children.
        if not task.children:
            # Falsification: We cannot execute this, and we cannot decompose it.
            logger.error(f"FALSIFICATION: Task '{task.name}' cannot be matched (Score: {coverage:.2f}) and has no sub-tasks.")
            task.is_executable = False
        else:
            # Continue decomposition recursion
            task.is_executable = True # Assume true, verify children
            processed_children = []
            for child in task.children:
                child.depth = task.depth + 1
                processed_child = self.determine_meu(child)
                processed_children.append(processed_child)
                if not processed_child.is_executable:
                    task.is_executable = False # Parent fails if child is unexecutable
            task.children = processed_children
            
        return task

    def validate_decomposition(self, root_task: TaskNode) -> Dict[str, bool]:
        """
        Core Function: Validates the entire decomposition tree against the skill library.
        
        Args:
            root_task (TaskNode): The root of the task tree.
            
        Returns:
            Dict[str, bool]: Report containing 'is_valid' and 'has_warnings'.
        """
        logger.info(f"Starting validation for root task: {root_task.name}")
        
        processed_root = self.determine_meu(root_task)
        
        # Collect stats
        total_nodes = 0
        executable_nodes = 0
        
        def traverse(node: TaskNode):
            nonlocal total_nodes, executable_nodes
            total_nodes += 1
            if node.is_executable and not node.children: # Leaf node executable
                executable_nodes += 1
            for child in node.children:
                traverse(child)
        
        traverse(processed_root)
        
        is_valid = executable_nodes > 0 and all(
            traverse_and_check(processed_root)
        )
        
        return {
            "is_valid": is_valid,
            "total_nodes": total_nodes,
            "executable_leaves": executable_nodes,
            "coverage_ratio": executable_nodes / total_nodes if total_nodes > 0 else 0
        }

def traverse_and_check(node: TaskNode) -> bool:
    """Helper generator to check validity of all nodes."""
    if not node.is_executable and not node.children:
        return False
    for child in node.children:
        if not traverse_and_check(child):
            return False
    return True

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Setup Mock Skill Library (Simulating the 132 skills)
    mock_skills = [
        Skill("S01", "WriteFile", SkillType.ATOMIC, ["write", "save", "file"], 0.2),
        Skill("S02", "ReadFile", SkillType.ATOMIC, ["read", "load", "file"], 0.1),
        Skill("S03", "GenerateText", SkillType.ATOMIC, ["generate", "create", "text", "content"], 0.4),
        Skill("S04", "AnalyzeData", SkillType.COMPOSITE, ["analyze", "process", "data"], 0.8),
        Skill("S05", "PlotGraph", SkillType.ATOMIC, ["plot", "graph", "chart", "visualize"], 0.3),
        Skill("S06", "SendEmail", SkillType.ATOMIC, ["send", "email", "notify"], 0.2),
    ]

    # 2. Initialize System
    boundary_system = AutoFalsificationBoundary(skill_library=mock_skills)

    # 3. Define a Complex Task Tree (Top-Down Decomposition)
    # Root: "Analyze sales data and email report"
    # L1: "Load data", "Process data", "Send email"
    # L2 (under Process): "Calculate stats", "Plot graph"
    
    root = TaskNode(
        id="T0",
        name="Complex Analysis Workflow",
        description="Analyze sales data and email report",
        children=[
            TaskNode(id="T1", name="Load Phase", description="Read file from disk"),
            TaskNode(id="T2", name="Analysis Phase", description="Process data and generate insights", children=[
                TaskNode(id="T2.1", name="Math", description="Calculate statistics"),
                TaskNode(id="T2.2", name="Viz", description="Plot graph"),
            ]),
            TaskNode(id="T3", name="Notification Phase", description="Send email to user")
        ]
    )

    # 4. Run Validation and Boundary Detection
    report = boundary_system.validate_decomposition(root)

    print("\n--- Validation Report ---")
    print(f"Valid Decomposition: {report['is_valid']}")
    print(f"Executable Leaves: {report['executable_leaves']}/{report['total_nodes']}")
    print(f"Coverage Ratio: {report['coverage_ratio']:.2f}")