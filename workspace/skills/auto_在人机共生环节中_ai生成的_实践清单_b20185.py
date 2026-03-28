"""
Module: executable_practice_validator
Description: 在人机共生环节中，AI生成的'实践清单'往往因过于抽象而难以执行。
             本模块利用已有的技能节点库，开发一个'可执行性评分器'。
             It decomposes abstract suggestions into sub-steps, retrieves existing skills,
             and assesses cognitive load to ensure tasks are immediately actionable.

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
License: MIT
"""

import logging
import dataclasses
import re
from typing import List, Dict, Optional, Tuple
from enum import Enum

# --- Configuration & Setup ---

# Setting up robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Enumeration for risk assessment levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclasses.dataclass
class SkillNode:
    """Represents a single unit of capability in the skill library.
    
    Attributes:
        id: Unique identifier for the skill.
        name: Human-readable name of the skill.
        keywords: List of keywords associated with this skill.
        difficulty: A score from 1-10 representing execution difficulty.
    """
    id: str
    name: str
    keywords: List[str]
    difficulty: float

@dataclasses.dataclass
class ActionableStep:
    """Represents a decomposed step from the abstract suggestion."""
    description: str
    required_skill_id: Optional[str]
    match_score: float
    risk_level: RiskLevel
    cognitive_load: float  # 0.0 to 1.0

@dataclasses.dataclass
class PracticeReport:
    """Final report on the executability of a practice suggestion."""
    original_suggestion: str
    is_executable: bool
    overall_score: float
    steps: List[ActionableStep]
    missing_skills: List[str]
    summary: str


class ExecutablePracticeValidator:
    """
    Validates and transforms abstract AI suggestions into actionable practice lists.
    
    This class serves as the core 'Executability Scorer'. It simulates the connection
    to a skill database and uses NLP-heuristic logic to decompose and match skills.
    """

    def __init__(self, skill_library: List[SkillNode], max_cognitive_load: float = 0.7):
        """
        Initialize the validator with a pre-existing skill library.
        
        Args:
            skill_library: A list of SkillNode objects representing the agent's capabilities.
            max_cognitive_load: The threshold above which a task is considered too demanding.
        """
        if not skill_library:
            logger.error("Skill library cannot be empty.")
            raise ValueError("Skill library must contain at least one skill node.")
        
        self.skill_library = skill_library
        self.max_cognitive_load = max_cognitive_load
        self._build_keyword_index()
        logger.info(f"Validator initialized with {len(self.skill_library)} skills.")

    def _build_keyword_index(self) -> None:
        """Builds a reverse index for faster keyword lookup (Optimization)."""
        self.keyword_index: Dict[str, List[SkillNode]] = {}
        for skill in self.skill_library:
            for kw in skill.keywords:
                if kw not in self.keyword_index:
                    self.keyword_index[kw] = []
                self.keyword_index[kw].append(skill)
        logger.debug("Keyword index constructed.")

    def _decompose_task(self, abstract_text: str) -> List[str]:
        """
        [Helper Function] Splits abstract text into logical sub-steps.
        
        This is a heuristic simulation of a planning module. In a production AGI system,
        this would interface with an LLM or a symbolic planner.
        
        Args:
            abstract_text: The raw suggestion string.
            
        Returns:
            A list of strings, each representing a sub-task.
        """
        logger.debug(f"Decomposing task: {abstract_text}")
        
        # Simple heuristic: split by conjunctions or punctuation
        # In reality, this would use semantic parsing
        separators = r'\s+and\s+|\s*;\s*|\s*。\s*|\s*然后\s*'
        raw_steps = re.split(separators, abstract_text)
        
        # Filter out very short or meaningless fragments
        valid_steps = [step.strip() for step in raw_steps if len(step.strip()) > 3]
        
        if not valid_steps:
            return [abstract_text] # Fallback
        
        return valid_steps

    def _calculate_cognitive_load(self, step_text: str, skill: Optional[SkillNode]) -> float:
        """
        [Helper Function] Estimates the cognitive load of a step.
        
        Factors:
        - Length of instruction
        - Difficulty of required skill
        - Abstractness (lack of specific verbs)
        """
        base_load = min(1.0, len(step_text) / 100.0) # Simple length proxy
        
        if skill:
            # Normalize skill difficulty (1-10) to load (0-1)
            skill_load = skill.difficulty / 10.0
            return (base_load + skill_load) / 2.0
        
        # Penalty for missing skill (high uncertainty = high load)
        return base_load + 0.3

    def _retrieve_skill(self, step_text: str) -> Tuple[Optional[SkillNode], float]:
        """
        [Core Logic] Retrieves the most relevant skill for a given step text.
        
        Args:
            step_text: The text description of the sub-task.
            
        Returns:
            A tuple of (Best Matching Skill, Match Confidence Score).
        """
        best_match: Optional[SkillNode] = None
        highest_score = 0.0
        
        # Tokenize step text for matching
        step_tokens = set(re.findall(r'\w+', step_text.lower()))
        
        # Check against keyword index
        matches = {}
        for token in step_tokens:
            if token in self.keyword_index:
                for skill in self.keyword_index[token]:
                    if skill.id not in matches:
                        matches[skill.id] = 0
                    matches[skill.id] += 1
        
        if not matches:
            return None, 0.0
            
        # Find skill with highest overlap
        best_skill_id = max(matches, key=matches.get) # type: ignore
        overlap_count = matches[best_skill_id]
        
        # Retrieve skill object
        for s in self.skill_library:
            if s.id == best_skill_id:
                best_match = s
                break
        
        # Calculate confidence based on overlap vs total keywords of the skill
        if best_match:
            score = overlap_count / len(best_match.keywords) if best_match.keywords else 0
            return best_match, score
            
        return None, 0.0

    def validate_suggestion(self, suggestion: str) -> PracticeReport:
        """
        [Core Function] Main entry point to validate a practice suggestion.
        
        It orchestrates decomposition, skill retrieval, and risk assessment.
        
        Args:
            suggestion: The abstract text suggestion from the AI.
            
        Returns:
            PracticeReport: A comprehensive object detailing executability.
            
        Raises:
            ValueError: If suggestion is empty or invalid.
        """
        if not suggestion or not isinstance(suggestion, str):
            logger.error("Invalid suggestion input.")
            raise ValueError("Suggestion must be a non-empty string.")

        logger.info(f"Starting validation for: '{suggestion[:50]}...'")
        
        # 1. Decomposition
        sub_steps_text = self._decompose_task(suggestion)
        actionable_steps: List[ActionableStep] = []
        missing_skills: List[str] = []
        total_load = 0.0
        
        # 2. Analysis per step
        for step_text in sub_steps_text:
            skill, score = self._retrieve_skill(step_text)
            
            # Determine Risk
            if skill is None:
                risk = RiskLevel.CRITICAL
                missing_skills.append(step_text)
                logger.warning(f"Missing skill for step: {step_text}")
            elif score < 0.4:
                risk = RiskLevel.HIGH
                missing_skills.append(f"Low confidence match for: {step_text}")
            elif score < 0.7:
                risk = RiskLevel.MEDIUM
            else:
                risk = RiskLevel.LOW
                
            # Calculate Load
            load = self._calculate_cognitive_load(step_text, skill)
            total_load += load
            
            step_obj = ActionableStep(
                description=step_text,
                required_skill_id=skill.id if skill else None,
                match_score=score,
                risk_level=risk,
                cognitive_load=load
            )
            actionable_steps.append(step_obj)
            
        # 3. Final Aggregation
        avg_load = total_load / len(actionable_steps) if actionable_steps else 1.0
        is_executable = (len(missing_skills) == 0) and (avg_load <= self.max_cognitive_load)
        
        final_score = 100.0
        if missing_skills:
            final_score -= len(missing_skills) * 20.0
        if avg_load > self.max_cognitive_load:
            final_score -= (avg_load - self.max_cognitive_load) * 50.0
            
        final_score = max(0, final_score)
        
        summary = (f"Task decomposed into {len(actionable_steps)} steps. "
                   f"Missing skills: {len(missing_skills)}. "
                   f"Average Cognitive Load: {avg_load:.2f}. "
                   f"Executable: {is_executable}")

        return PracticeReport(
            original_suggestion=suggestion,
            is_executable=is_executable,
            overall_score=final_score,
            steps=actionable_steps,
            missing_skills=missing_skills,
            summary=summary
        )

# --- Mock Data & Usage Example ---

def get_mock_skill_library() -> List[SkillNode]:
    """Generates a mock library of 1554 skills (simulated here with 5 for brevity)."""
    return [
        SkillNode("SK_001", "Python Basic Syntax", ["python", "variable", "syntax", "coding"], 2.0),
        SkillNode("SK_002", "API Integration", ["api", "rest", "http", "request", "json"], 5.5),
        SkillNode("SK_003", "Data Visualization", ["plot", "graph", "chart", "visualize", "data"], 6.0),
        SkillNode("SK_004", "System Debugging", ["debug", "error", "fix", "log", "trace"], 7.5),
        SkillNode("SK_005", "Report Writing", ["write", "document", "report", "summary"], 3.0)
    ]

if __name__ == "__main__":
    # 1. Initialize System
    mock_skills = get_mock_skill_library()
    validator = ExecutablePracticeValidator(skill_library=mock_skills)
    
    # 2. Define an abstract suggestion (Typical AI Output)
    ai_suggestion = "Connect to the client API and visualize the user growth data."
    
    # 3. Execute Validation
    try:
        report = validator.validate_suggestion(ai_suggestion)
        
        # 4. Display Results
        print("\n" + "="*40)
        print(f"VALIDATION REPORT")
        print("="*40)
        print(f"Original: {report.original_suggestion}")
        print(f"Score:    {report.overall_score:.1f}/100")
        print(f"Status:   {'READY TO EXECUTE' if report.is_executable else 'NEEDS INTERVENTION'}")
        print("-" * 40)
        print("Breakdown:")
        for i, step in enumerate(report.steps, 1):
            skill_info = step.required_skill_id if step.required_skill_id else "NO SKILL FOUND"
            print(f"{i}. {step.description}")
            print(f"   -> Skill: {skill_info} (Risk: {step.risk_level.value})")
        
        if report.missing_skills:
            print("\n[WARNING] The following gaps were detected:")
            for gap in report.missing_skills:
                print(f" - {gap}")
                
    except Exception as e:
        logger.exception("Error during validation execution.")