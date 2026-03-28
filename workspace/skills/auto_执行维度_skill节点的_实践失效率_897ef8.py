"""
Module: auto_执行维度_skill节点的_实践失效率_897ef8
Description: Implements Statistical Process Control (SPC) for AGI Skill Nodes to track 'Practice Failure Rate'.
             This module provides a real-time feedback loop, integrating both execution errors and
             human satisfaction/goal achievement metrics to calculate failure rates. It triggers
             a deprecation mechanism when statistical confidence intervals fall below a defined threshold.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillStatus(Enum):
    ACTIVE = "ACTIVE"
    PROBATION = "PROBATION"
    DEPRECATED = "DEPRECATED"

@dataclass
class SkillObservation:
    """
    Represents a single observation of a skill execution.
    
    Attributes:
        success (bool): Technical execution success (no exceptions).
        satisfaction_score (float): Human satisfaction or goal achievement score (0.0 to 1.0).
        threshold (float): The minimum acceptable score for this specific task context.
    """
    success: bool
    satisfaction_score: float
    threshold: float = 0.6  # Default threshold if not specified

    def is_practice_failure(self) -> bool:
        """
        Determines if the observation counts as a 'practice failure'.
        A failure occurs if the execution crashes OR the satisfaction score
        falls below the required threshold.
        """
        if not self.success:
            return True
        if self.satisfaction_score < self.threshold:
            return True
        return False

@dataclass
class SkillNode:
    """
    Represents an AGI Skill Node with SPC tracking capabilities.
    """
    id: str
    name: str
    status: SkillStatus = SkillStatus.ACTIVE
    observations: List[bool] = field(default_factory=list)  # True for Failure, False for Success
    window_size: int = 30  # Rolling window for SPC calculation
    consecutive_failures: int = 0

    def add_observation(self, failed: bool) -> None:
        """Adds an observation and maintains the rolling window."""
        self.observations.append(failed)
        if len(self.observations) > self.window_size:
            self.observations.pop(0)
        
        # Update consecutive counter
        if failed:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

class SPCMonitor:
    """
    Core class for monitoring skill reliability using Statistical Process Control.
    """

    def __init__(self, deprecation_threshold: float = 0.7, confidence_level: float = 0.95):
        """
        Initialize the SPC Monitor.
        
        Args:
            deprecation_threshold (float): The minimum acceptable success rate (lower limit).
            confidence_level (float): Statistical confidence level for interval calculation.
        """
        self.skills: Dict[str, SkillNode] = {}
        self.deprecation_threshold = deprecation_threshold
        self.confidence_level = confidence_level
        logger.info(f"SPCMonitor initialized with threshold {deprecation_threshold} and confidence {confidence_level}")

    def register_skill(self, skill_id: str, name: str) -> None:
        """Registers a new skill for monitoring."""
        if skill_id not in self.skills:
            self.skills[skill_id] = SkillNode(id=skill_id, name=name)
            logger.info(f"Registered skill: {name} ({skill_id})")
        else:
            logger.warning(f"Skill {skill_id} already registered.")

    def record_outcome(self, skill_id: str, observation: SkillObservation) -> Tuple[SkillStatus, Optional[str]]:
        """
        Core Function 1: Records an execution outcome and updates the skill's reliability stats.
        
        Args:
            skill_id (str): The ID of the skill.
            observation (SkillObservation): The data object containing execution results.
            
        Returns:
            Tuple[SkillStatus, Optional[str]]: Current status and a warning message if triggered.
        """
        if skill_id not in self.skills:
            logger.error(f"Skill {skill_id} not found.")
            raise ValueError(f"Skill ID {skill_id} is not registered in the monitor.")

        skill = self.skills[skill_id]
        is_failure = observation.is_practice_failure()
        skill.add_observation(is_failure)

        logger.info(f"Recorded outcome for {skill_id}: {'FAILURE' if is_failure else 'SUCCESS'}")

        # Check for immediate deprecation based on logic
        new_status, message = self._evaluate_spc_rules(skill)
        
        if new_status != skill.status:
            skill.status = new_status
            logger.warning(f"Status change for {skill_id}: {new_status.value}. Reason: {message}")
            
        return skill.status, message

    def _calculate_wald_interval(self, successes: int, trials: int) -> Tuple[float, float]:
        """
        Helper Function: Calculates the Wilson Score confidence interval for a proportion.
        (Used here as it handles edge cases like 0% or 100% better than standard Wald).
        
        Args:
            successes (int): Number of successful observations.
            trials (int): Total number of observations.
            
        Returns:
            Tuple[float, float]: (Lower Bound, Upper Bound) of the confidence interval.
        """
        if trials == 0:
            return 0.0, 1.0

        z = 1.96  # Z-score for 95% confidence
        if self.confidence_level != 0.95:
            # Simplified lookup for common Z-scores
            z = 1.645 if self.confidence_level == 0.90 else 2.576 if self.confidence_level == 0.99 else 1.96

        phat = successes / trials
        
        # Wilson Score Interval formula
        denominator = 1 + z**2 / trials
        centre = (phat + z**2 / (2 * trials)) / denominator
        margin = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * trials)) / trials) / denominator
        
        lower = max(0.0, centre - margin)
        upper = min(1.0, centre + margin)
        
        return lower, upper

    def _evaluate_spc_rules(self, skill: SkillNode) -> Tuple[SkillStatus, str]:
        """
        Core Function 2: Evaluates SPC rules to determine if the skill should be deprecated.
        
        Logic:
        1. Calculate success rate and confidence interval over the rolling window.
        2. If the lower bound of the confidence interval < deprecation threshold, trigger warning/deprecation.
        3. If consecutive failures exceed a limit, immediate deprecation.
        """
        if len(skill.observations) < 5: # Not enough data
            return SkillStatus.ACTIVE, "Collecting data"

        # Calculate metrics
        failures = sum(skill.observations)
        successes = len(skill.observations) - failures
        success_rate = successes / len(skill.observations)
        
        # Calculate Confidence Interval
        lower_bound, upper_bound = self._calculate_wald_interval(successes, len(skill.observations))
        
        logger.debug(f"Skill {skill.id} Stats - Rate: {success_rate:.2f}, CI Lower: {lower_bound:.2f}")

        # Rule 1: Consecutive Failures (Shock detection)
        if skill.consecutive_failures >= 5:
            return (SkillStatus.DEPRECATED, 
                    f"Critical: {skill.consecutive_failures} consecutive failures detected.")

        # Rule 2: Statistical Drift (Confidence Interval Lower Bound check)
        if lower_bound < self.deprecation_threshold:
            if success_rate < 0.5: # Severe drop
                 return SkillStatus.DEPRECATED, f"Statistical deprecation: CI lower bound {lower_bound:.2f} < {self.deprecation_threshold}"
            else:
                 return SkillStatus.PROBATION, f"Performance warning: CI lower bound {lower_bound:.2f} is below threshold."

        # Recovery logic
        if skill.status == SkillStatus.PROBATION and lower_bound > (self.deprecation_threshold + 0.05):
            return SkillStatus.ACTIVE, "Performance recovered."

        return skill.status, "Within acceptable limits."

# Usage Example
if __name__ == "__main__":
    # Initialize Monitor
    monitor = SPCMonitor(deprecation_threshold=0.75, confidence_level=0.95)
    
    # Register a skill
    skill_id = "skill_123_agi_core"
    monitor.register_skill(skill_id, "AGI_Core_Reasoning")
    
    # Simulate a stream of observations
    # Scenario: High initial success, followed by degradation
    test_data = [
        (True, 0.9), (True, 0.95), (True, 0.8), (True, 0.85), (True, 0.9), # Good
        (True, 0.5), # Low satisfaction (Failure)
        (True, 0.4), # Low satisfaction
        (False, 0.0), # Crash
        (True, 0.3), # Low satisfaction
        (False, 0.0), # Crash
        (False, 0.0), # Crash
        (False, 0.0), # Crash
        (False, 0.0), # Crash
        (False, 0.0), # Crash
    ]
    
    print(f"{'Observation':<15} | {'Status':<12} | {'Message'}")
    print("-" * 60)
    
    for success, score in test_data:
        obs = SkillObservation(success=success, satisfaction_score=score)
        status, msg = monitor.record_outcome(skill_id, obs)
        print(f"Score: {score:<10} | {status.value:<12} | {msg}")
        
        if status == SkillStatus.DEPRECATED:
            print("Skill has been deprecated. Halting simulation.")
            break