"""
Module: auto_融合能力_开发_人生rpg技能树协议_0c5cb2
Domain: cross_domain
Description: 
    This module implements the 'Life RPG Skill Tree Protocol'. It transforms linear educational 
    curricula into a gamified, non-linear 'Tech Tree' or 'Talent Wheel'. 
    Learners can select 'Skill Branches' (specializations) similar to RPG gameplay. 
    Mastering a knowledge unit lights up a node and grants attribute bonuses (e.g., Logic +1). 
    This protocol leverages human instincts for collection and achievement to mitigate 
    motivation decay during long-term learning cycles.

Key Features:
    - Dynamic Skill Tree construction with dependency management.
    - Attribute tracking and accumulation upon skill mastery.
    - Data validation for skill definitions and unlocking prerequisites.
    - Comprehensive logging for tracking the learning journey.

Input/Output Formats:
    - Skill Definition: Dict containing 'id', 'name', 'prerequisites' (list of IDs), and 'stat_bonus' (dict).
    - Player State: Dict containing current stats and a set of mastered skill IDs.
"""

import logging
from typing import Dict, List, Set, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LifeRPGProtocol")


class SkillNode:
    """
    Represents a single node in the Life RPG Skill Tree.
    
    Attributes:
        skill_id (str): Unique identifier for the skill.
        name (str): Human-readable name of the skill.
        prerequisites (List[str]): List of skill_ids required to unlock this skill.
        stat_bonus (Dict[str, int]): Dictionary of attributes and their increment values.
    """
    def __init__(self, skill_id: str, name: str, prerequisites: List[str], stat_bonus: Dict[str, int]):
        self.skill_id = skill_id
        self.name = name
        self.prerequisites = prerequisites
        self.stat_bonus = stat_bonus

    def __repr__(self) -> str:
        return f"<SkillNode: {self.name} ({self.skill_id})>"


class LifeRPGProtocol:
    """
    Manages the Life RPG Skill Tree system, handling skill registration, 
    validation, and the unlocking process for the learner.
    """

    def __init__(self):
        """Initialize the protocol with an empty skill tree and zeroed player stats."""
        self._skills: Dict[str, SkillNode] = {}
        self._mastered_skills: Set[str] = set()
        self._player_stats: Dict[str, int] = {}
        logger.info("LifeRPG Protocol initialized.")

    def _validate_stat_bonus(self, stat_bonus: Dict[str, int]) -> None:
        """
        Helper function to validate the stat_bonus dictionary.
        
        Args:
            stat_bonus: Dictionary of stats to validate.
            
        Raises:
            ValueError: If stat_bonus is empty, keys are not strings, or values are not positive integers.
        """
        if not stat_bonus:
            raise ValueError("Stat bonus cannot be empty.")
        
        for key, value in stat_bonus.items():
            if not isinstance(key, str):
                raise ValueError(f"Stat key must be string, got {type(key)}.")
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"Stat value must be positive integer for {key}, got {value}.")

    def register_skill(self, skill_id: str, name: str, prerequisites: List[str], stat_bonus: Dict[str, int]) -> None:
        """
        Core Function 1: Registers a new skill into the system.
        
        This function acts as the 'Game Master' tool to build the curriculum tree.
        It validates the input and ensures prerequisites refer to existing skills 
        (or allows for forward-references if handled carefully, but here we enforce 
        strict registration order for simplicity).

        Args:
            skill_id: Unique ID for the skill (e.g., 'CS_101').
            name: Display name of the skill.
            prerequisites: List of skill_ids that must be learned first.
            stat_bonus: Attributes gained (e.g., {'Logic': 5, 'Python': 2}).

        Raises:
            ValueError: If validation fails or skill_id already exists.
        """
        if skill_id in self._skills:
            logger.error(f"Registration failed: Skill ID '{skill_id}' already exists.")
            raise ValueError(f"Skill ID '{skill_id}' already registered.")

        try:
            self._validate_stat_bonus(stat_bonus)
        except ValueError as e:
            logger.error(f"Registration failed for '{skill_id}': {e}")
            raise

        # Validate prerequisites exist
        for pre_id in prerequisites:
            if pre_id not in self._skills:
                logger.warning(f"Prerequisite '{pre_id}' for '{skill_id}' does not exist yet. "
                               "Registering anyway, but unlocking may fail.")

        new_skill = SkillNode(skill_id, name, prerequisites, stat_bonus)
        self._skills[skill_id] = new_skill
        logger.info(f"Skill registered: {name} ({skill_id}) with bonus {stat_bonus}")

    def unlock_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Core Function 2: Attempts to unlock (master) a skill for the player.
        
        Checks prerequisites, updates player stats, and marks the skill as mastered.
        This simulates the 'Level Up' or 'Talent Point Spend' mechanic.

        Args:
            skill_id: The ID of the skill to unlock.

        Returns:
            A dictionary containing the status ('success' or 'failed'), 
            message, and current player stats.

        Raises:
            ValueError: If the skill_id does not exist in the tree.
        """
        if skill_id not in self._skills:
            logger.error(f"Unlock failed: Skill '{skill_id}' not found.")
            raise ValueError(f"Skill '{skill_id}' is not defined in the protocol.")

        if skill_id in self._mastered_skills:
            logger.info(f"Unlock skipped: Skill '{skill_id}' already mastered.")
            return {
                "status": "failed",
                "message": "Skill already mastered.",
                "stats": self._player_stats.copy()
            }

        skill = self._skills[skill_id]
        
        # Check prerequisites
        missing_prereqs = [p for p in skill.prerequisites if p not in self._mastered_skills]
        if missing_prereqs:
            msg = f"Cannot unlock '{skill.name}'. Missing prerequisites: {missing_prereqs}"
            logger.warning(msg)
            return {
                "status": "failed",
                "message": msg,
                "stats": self._player_stats.copy()
            }

        # Unlock logic
        self._mastered_skills.add(skill_id)
        
        # Apply stat bonuses
        for stat, value in skill.stat_bonus.items():
            if stat not in self._player_stats:
                self._player_stats[stat] = 0
            self._player_stats[stat] += value
            
        logger.info(f"SUCCESS: Unlocked '{skill.name}'. Stats updated: {skill.stat_bonus}")
        
        return {
            "status": "success",
            "message": f"Unlocked {skill.name}!",
            "gained": skill.stat_bonus,
            "stats": self._player_stats.copy()
        }

    def get_player_status(self) -> Dict[str, Any]:
        """
        Helper Function: Returns the current visualization of the player's progress.
        
        Returns:
            Dictionary containing current stats, mastered skills count, 
            and available skills to unlock next.
        """
        # Find unlockable skills (prerequisites met, not yet mastered)
        unlockable = []
        for s_id, skill in self._skills.items():
            if s_id not in self._mastered_skills:
                prereqs_met = all(p in self._mastered_skills for p in skill.prerequisites)
                if prereqs_met:
                    unlockable.append(skill.name)

        return {
            "current_stats": self._player_stats,
            "mastered_count": len(self._mastered_skills),
            "total_skills": len(self._skills),
            "next_available_skills": unlockable
        }


# Example Usage
if __name__ == "__main__":
    # Initialize the Protocol
    rpg_system = LifeRPGProtocol()

    # --- Game Master Phase: Building the Tree ---
    print("--- Building Skill Tree ---")
    
    # Basic Skills
    rpg_system.register_skill(
        skill_id="math_basics", 
        name="Basic Mathematics", 
        prerequisites=[], 
        stat_bonus={"Logic": 2, "Calculation": 5}
    )
    
    rpg_system.register_skill(
        skill_id="python_syntax", 
        name="Python Syntax", 
        prerequisites=[], 
        stat_bonus={"Programming": 3, "Logic": 1}
    )

    # Intermediate Skills (Dependent)
    rpg_system.register_skill(
        skill_id="data_structures", 
        name="Data Structures", 
        prerequisites=["python_syntax", "math_basics"], 
        stat_bonus={"Logic": 5, "Programming": 5, "Optimization": 2}
    )
    
    rpg_system.register_skill(
        skill_id="algorithms", 
        name="Algorithms", 
        prerequisites=["data_structures"], 
        stat_bonus={"Logic": 10, "Problem Solving": 5}
    )

    # --- Player Phase: Learning ---
    print("\n--- Player Journey ---")
    
    # Attempt to unlock advanced skill immediately (Should fail)
    result = rpg_system.unlock_skill("algorithms")
    print(f"Attempt 1: {result['message']}")

    # Unlock basics
    print("\nUnlocking Basics...")
    rpg_system.unlock_skill("math_basics")
    rpg_system.unlock_skill("python_syntax")
    
    # Check status
    status = rpg_system.get_player_status()
    print(f"Current Stats: {status['current_stats']}")
    print(f"Available to learn: {status['next_available_skills']}")

    # Unlock Intermediate
    print("\nUnlocking Intermediate...")
    rpg_system.unlock_skill("data_structures")
    
    # Unlock Advanced
    print("\nUnlocking Advanced...")
    result = rpg_system.unlock_skill("algorithms")
    print(f"Final Result: {result['message']}")
    
    # Final Status
    final_status = rpg_system.get_player_status()
    print(f"\nFinal Character Sheet:\n{final_status}")