"""
Module: auto_技能组合爆炸规避_如何评估复杂_ski_8c95df
Description: Advanced Skill Dependency Analysis & Pruning System for AGI
Author: Senior Python Engineer (AGI Division)
Version: 1.0.0
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillNode:
    """
    Represents a node in the Skill Graph.
    
    Attributes:
        id: Unique identifier for the skill.
        is_atomic: Boolean flag indicating if the skill is a primitive/base action.
        sub_skills: List of IDs representing the sequence of skills this skill depends on.
                    Empty if is_atomic is True.
        usage_count: Frequency of usage in historical data (for weight calculation).
    """
    id: str
    is_atomic: bool = False
    sub_skills: List[str] = field(default_factory=list)
    usage_count: int = 0

    def __post_init__(self):
        """Validate data integrity after initialization."""
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Skill ID must be a non-empty string.")
        if self.is_atomic and self.sub_skills:
            logger.warning(f"Atomic skill {self.id} initialized with sub_skills. Clearing them.")
            self.sub_skills = []


class SkillGraphPruner:
    """
    Analyzes a library of skills to detect and prune redundant composite skills 
    to prevent combinatorial explosion in AGI planning search spaces.
    """

    def __init__(self, skills: List[SkillNode]):
        """
        Initializes the pruner with a list of skill nodes.
        
        Args:
            skills: A list of SkillNode objects.
        """
        if not skills:
            raise ValueError("Skills list cannot be empty.")
        
        self.skills: Dict[str, SkillNode] = {s.id: s for s in skills}
        self._validate_graph_integrity()
        
        # Cache for calculated metrics
        self._depth_cache: Dict[str, int] = {}
        self._substitutability_cache: Dict[str, float] = {}

    def _validate_graph_integrity(self):
        """Ensures all sub-skill references exist in the main skill dictionary."""
        logger.info("Validating skill graph integrity...")
        all_ids = set(self.skills.keys())
        for skill in self.skills.values():
            for sub_id in skill.sub_skills:
                if sub_id not in all_ids:
                    raise ValueError(f"Integrity Error: Skill '{skill.id}' references missing sub-skill '{sub_id}'")
        logger.info("Graph integrity validation passed.")

    def _calculate_recursive_depth(self, skill_id: str, visited: Set[str]) -> int:
        """
        Helper function to calculate the depth of a skill recursively.
        Depth = The longest path of execution from this node to a primitive node.
        
        Args:
            skill_id: The ID of the skill to analyze.
            visited: Set of visited nodes to detect cycles.
            
        Returns:
            int: The dependency depth.
        """
        if skill_id in self._depth_cache:
            return self._depth_cache[skill_id]

        if skill_id not in self.skills:
            raise KeyError(f"Skill ID {skill_id} not found in graph.")

        node = self.skills[skill_id]
        
        # Base case: Atomic skills have depth 0
        if node.is_atomic:
            return 0

        # Cycle detection
        if skill_id in visited:
            logger.error(f"Cyclic dependency detected at skill: {skill_id}")
            raise RecursionError(f"Cyclic dependency detected at skill: {skill_id}")

        visited.add(skill_id)
        
        max_sub_depth = 0
        if not node.sub_skills:
            # Treat empty composite skills as depth 0 or error? 
            # Here we treat as 0 (leaf composite)
            depth = 0
        else:
            for sub_id in node.sub_skills:
                sub_depth = self._calculate_recursive_depth(sub_id, visited.copy())
                if sub_depth > max_sub_depth:
                    max_sub_depth = sub_depth
            
            # Depth is max depth of children + 1 (for the current node)
            depth = max_sub_depth + 1

        self._depth_cache[skill_id] = depth
        return depth

    def calculate_dependency_depths(self) -> Dict[str, int]:
        """
        Public interface to calculate depths for all skills.
        
        Returns:
            Dict mapping skill_id to its dependency depth.
        """
        logger.info("Calculating dependency depths for all skills...")
        depths = {}
        for skill_id in self.skills:
            depths[skill_id] = self._calculate_recursive_depth(skill_id, set())
        
        logger.info(f"Depth calculation complete. Max depth found: {max(depths.values())}")
        return depths

    def evaluate_substitutability(self, skill_id: str) -> float:
        """
        Calculates the "Substitutability Index" (0.0 to 1.0).
        High score (near 1.0) means the skill is easily replaced by its sequence 
        without significant planning overhead.
        
        Formula simplified for example:
        Substitutability = (1 / (1 + Depth)) * (Sequence_Length / Total_Complexity)
        
        For this implementation, we define "Pseudo-High" substitutability if:
        1. The skill is a direct sequence of ATOMIC skills (Depth = 1).
        2. The skill is never used as a sub-component by OTHER complex skills (Low coupling).
        
        Returns:
            float: Score between 0.0 and 1.0.
        """
        if skill_id in self._substitutability_cache:
            return self._substitutability_cache[skill_id]

        node = self.skills[skill_id]
        
        if node.is_atomic:
            return 0.0 # Atomic skills are never redundant

        # Heuristic 1: Depth Check
        # If depth > 1, it aggregates complex logic, harder to replace manually in search
        depth = self._calculate_recursive_depth(skill_id, set())
        if depth > 2:
            return 0.1 

        # Heuristic 2: Component Usage (Coupling)
        # If this skill is used by many other skills, it is a useful abstraction
        usage_as_component = 0
        for s in self.skills.values():
            if skill_id in s.sub_skills:
                usage_as_component += 1
        
        if usage_as_component > 0:
            # It's a useful building block, low substitutability (keep it)
            return 0.2 

        # Heuristic 3: "Pseudo-High" Detection
        # If it's just a wrapper for atomic actions and rarely used as a module
        # It creates search space bloat.
        
        # Check if all children are atomic
        all_children_atomic = all(
            self.skills[sub_id].is_atomic for sub_id in node.sub_skills
        )
        
        if all_children_atomic and len(node.sub_skills) > 1:
            # This is a "Macro" of basic actions. 
            # High candidate for deletion if search space is an issue.
            score = 0.9 
        else:
            score = 0.3

        self._substitutability_cache[skill_id] = score
        return score

    def identify_redundant_skills(self, threshold: float = 0.8) -> List[Tuple[str, float, str]]:
        """
        Identifies skills that should be pruned.
        
        Args:
            threshold: Substitutability score above which a skill is considered redundant.
            
        Returns:
            List of Tuples: (skill_id, score, reason)
        """
        redundant_skills = []
        logger.info(f"Scanning for redundant skills with threshold > {threshold}...")
        
        for skill_id, node in self.skills.items():
            if node.is_atomic:
                continue

            score = self.evaluate_substitutability(skill_id)
            
            if score >= threshold:
                reason = (
                    f"High Substitutability ({score:.2f}). "
                    f"Depth: {self._depth_cache.get(skill_id, 0)}. "
                    f"Composed of atomic sequence."
                )
                redundant_skills.append((skill_id, score, reason))
        
        logger.info(f"Found {len(redundant_skills)} redundant skills.")
        return redundant_skills


# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Define Sample Data
    # Atomic Skills (Primitives)
    skill_data = [
        SkillNode(id="move_arm", is_atomic=True, usage_count=500),
        SkillNode(id="open_gripper", is_atomic=True, usage_count=500),
        SkillNode(id="close_gripper", is_atomic=True, usage_count=500),
        SkillNode(id="identify_object", is_atomic=True, usage_count=200),
        
        # Useful Composite Skill (Abstracts complex logic, used by others) -> KEEP
        SkillNode(id="pick_up_object", sub_skills=["move_arm", "close_gripper"], usage_count=100),
        
        # "Pseudo-Advanced" Skill (Just a sequence of atomics, not reused) -> PRUNE CANDIDATE
        SkillNode(id="wave_hand", sub_skills=["move_arm", "move_arm", "move_arm"], usage_count=5),
        
        # Deep Skill (Aggregates composites) -> KEEP
        SkillNode(id="relocate_item", sub_skills=["pick_up_object", "move_arm", "pick_up_object"], usage_count=10)
    ]

    try:
        # 2. Initialize System
        pruner = SkillGraphPruner(skill_data)
        
        # 3. Analyze Depths
        depths = pruner.calculate_dependency_depths()
        print("\n--- Skill Depths ---")
        for k, v in depths.items():
            print(f"{k}: {v}")

        # 4. Identify Redundancies
        print("\n--- Pruning Analysis ---")
        redundants = pruner.identify_redundant_skills(threshold=0.8)
        
        if redundants:
            print("Recommended for Deletion:")
            for sid, score, reason in redundants:
                print(f"ID: {sid} | Score: {score} | Reason: {reason}")
        else:
            print("No redundant skills found.")

    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)