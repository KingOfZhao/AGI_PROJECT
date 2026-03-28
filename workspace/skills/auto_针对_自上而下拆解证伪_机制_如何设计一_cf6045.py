"""
Module: top_down_decomposer.py
Description: Implements a recursive, top-down algorithm for falsifiable task decomposition.
             It bridges abstract goals with a concrete Skill Knowledge Graph (SKG) and
             identifies skill gaps required for execution.
Author: AGI System Core Team
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Status of a task node in the decomposition tree."""
    PENDING = "PENDING"
    DECOMPOSED = "DECOMPOSED"
    MAPPED = "MAPPED"
    FAILED = "FAILED"

@dataclass
class SkillNode:
    """Represents an atomic executable skill in the system."""
    skill_id: str
    name: str
    description: str
    is_atomic: bool = True
    dependencies: List[str] = field(default_factory=list)

@dataclass
class TaskNode:
    """Represents a decomposable task or sub-task."""
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    mapped_skill_id: Optional[str] = None
    sub_tasks: List['TaskNode'] = field(default_factory=list)
    falsification_notes: str = ""

class DecompositionError(Exception):
    """Custom exception for errors during task decomposition."""
    pass

class SkillRegistry:
    """
    Simulates the database of 1070 SKILL nodes.
    In a real AGI system, this would interface with a Vector Database.
    """
    def __init__(self):
        self._skills: Dict[str, SkillNode] = {}
        self._initialize_mock_skills()

    def _initialize_mock_skills(self):
        """Populate with mock data for demonstration."""
        mock_data = [
            SkillNode("SK_001", "market_sentiment_analysis", "Analyze market trends"),
            SkillNode("SK_002", "generate_ui_prototype", "Create UI code"),
            SkillNode("SK_003", "a_b_testing_engine", "Run statistical tests"),
            SkillNode("SK_004", "viral_copywriting", "Generate high CTR text"),
            SkillNode("SK_005", "user_persona_modeling", "Model user demographics"),
        ]
        for skill in mock_data:
            self._skills[skill.skill_id] = skill
        logger.info(f"Skill Registry initialized with {len(self._skills)} skills.")

    def find_matching_skill(self, task_description: str) -> Optional[SkillNode]:
        """
        Attempts to map a task description to an existing SkillNode.
        (Simulated semantic search logic)
        """
        # Simulation: Simple keyword matching for demo
        # In production: Use embeddings (e.g., task_embedding @ skill_embeddings_matrix)
        keywords = {
            "market": "SK_001",
            "trend": "SK_001",
            "ui": "SK_002",
            "interface": "SK_002",
            "test": "SK_003",
            "copywriting": "SK_004",
            "persona": "SK_005"
        }
        
        for word, skill_id in keywords.items():
            if word in task_description.lower():
                return self._skills.get(skill_id)
        
        return None

    def get_skill(self, skill_id: str) -> Optional[SkillNode]:
        return self._skills.get(skill_id)

class TopDownDecomposer:
    """
    Core algorithm for 'Top-Down Falsifiable Decomposition'.
    """

    def __init__(self, registry: SkillRegistry, max_depth: int = 5):
        self.registry = registry
        self.max_depth = max_depth
        self.skill_gaps: List[Dict[str, str]] = []

    def decompose(self, goal: str) -> Tuple[TaskNode, List[Dict[str, str]]]:
        """
        Main entry point. Recursively decomposes a goal into atomic tasks.
        
        Args:
            goal (str): The abstract high-level goal (e.g., "Build a viral product").
            
        Returns:
            Tuple[TaskNode, List[Dict]]: The root of the task tree and a report of missing skills.
        """
        logger.info(f"Starting decomposition for goal: {goal}")
        self.skill_gaps = [] # Reset gaps
        root_task = TaskNode(task_id="T_0", description=goal)
        
        try:
            self._recursive_decompose(root_task, depth=0)
        except RecursionError:
            logger.error("Max recursion depth reached during decomposition.")
            root_task.status = TaskStatus.FAILED
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            root_task.status = TaskStatus.FAILED

        return root_task, self.skill_gaps

    def _recursive_decompose(self, current_task: TaskNode, depth: int):
        """
        Recursive helper function to break down tasks.
        
        Logic:
        1. Try to map to existing skill.
        2. If fails, generate sub-tasks (LLM logic simulated).
        3. Recurse into sub-tasks.
        4. Falsification check: If sub-tasks cannot solve the problem, mark failure.
        """
        if depth > self.max_depth:
            logger.warning(f"Max depth reached at task: {current_task.description}")
            self._record_gap(current_task)
            current_task.status = TaskStatus.FAILED
            return

        # Step 1: Attempt Mapping
        matched_skill = self.registry.find_matching_skill(current_task.description)
        if matched_skill:
            logger.info(f"Mapped '{current_task.description}' to Skill '{matched_skill.name}'")
            current_task.mapped_skill_id = matched_skill.skill_id
            current_task.status = TaskStatus.MAPPED
            return

        # Step 2: Decomposition Strategy (Simulated LLM thought process)
        # In AGI: Call LLM to generate sub-steps.
        logger.info(f"Decomposing abstract task: {current_task.description}")
        sub_tasks = self._generate_sub_tasks_heuristic(current_task.description)

        if not sub_tasks:
            # Leaf node reached but no skill found -> Skill Gap
            self._record_gap(current_task)
            current_task.status = TaskStatus.FAILED
            return

        current_task.sub_tasks = sub_tasks
        current_task.status = TaskStatus.DECOMPOSED

        # Step 3: Recursion
        for sub in current_task.sub_tasks:
            self._recursive_decompose(sub, depth + 1)

        # Step 4: Falsification Check (Post-order)
        # If any critical sub-task failed, the parent logic might be invalid.
        if any(t.status == TaskStatus.FAILED for t in current_task.sub_tasks):
            current_task.falsification_notes = "Decomposition invalidated due to missing skills in sub-tree."

    def _generate_sub_tasks_heuristic(self, description: str) -> List[TaskNode]:
        """
        Helper: Simulates the 'Thinking' process to break down a task.
        This replaces an actual LLM call for deterministic testing.
        """
        # Heuristic rules for "Build a viral product"
        if "viral product" in description.lower():
            return [
                TaskNode("T_1", "Analyze market trends"),
                TaskNode("T_2", "Design user interface"),
                TaskNode("T_3", "Implement viral loop"),
                TaskNode("T_4", "Write marketing copy")
            ]
        elif "viral loop" in description.lower():
            return [
                TaskNode("T_5", "Social sharing integration"), # Gap expected
                TaskNode("T_6", "User referral reward system") # Gap expected
            ]
        return []

    def _record_gap(self, task: TaskNode):
        """
        Helper: Records a skill gap when mapping fails.
        """
        gap_report = {
            "task_description": task.description,
            "suggested_skill_type": "Atomic_Execution_Node",
            "context": "No matching skill found in current registry."
        }
        self.skill_gaps.append(gap_report)
        logger.warning(f"SKILL GAP DETECTED: {task.description}")

# --- Usage Example & Validation ---

def run_demo():
    """Demonstrates the decomposition engine."""
    # 1. Setup
    registry = SkillRegistry()
    decomposer = TopDownDecomposer(registry, max_depth=3)

    # 2. Execute
    goal = "Create a viral product"
    task_tree, gaps = decomposer.decompose(goal)

    # 3. Display Results
    print("\n--- TASK TREE REPORT ---")
    print_tree(task_tree, level=0)
    
    print("\n--- SKILL GAP REPORT ---")
    if not gaps:
        print("No gaps found. Full coverage.")
    else:
        for i, gap in enumerate(gaps, 1):
            print(f"{i}. Missing Skill for Task: '{gap['task_description']}'")
            print(f"   Action Required: Implement new skill node.")

def print_tree(node: TaskNode, level: int):
    """Helper to visualize the tree structure."""
    indent = "  " * level
    status_icon = "✅" if node.status == TaskStatus.MAPPED else "❌" if node.status == TaskStatus.FAILED else "📁"
    
    mapped_info = f" (Skill: {node.mapped_skill_id})" if node.mapped_skill_id else ""
    print(f"{indent}{status_icon} {node.description}{mapped_info}")
    
    for child in node.sub_tasks:
        print_tree(child, level + 1)

if __name__ == "__main__":
    run_demo()