"""
Module: auto_构建_自适应心流认知引擎_这不仅是自适_50c693

Description:
    This module implements the 'Adaptive Flow Cognitive Engine'.
    It reconstructs learning content into 'gamified levels' and dynamically
    calculates the learner's 'Cognitive Load' and 'Emotional State' based on
    response time, error rates, and simulated bio-feedback.

    The engine aims to maintain a 'High Immersion Learning State' (Flow).
    - If the learner enters the 'Anxiety Zone', the system provides scaffolding
      or reduces difficulty.
    - If the learner enters the 'Boredom Zone', the system increases difficulty
      or introduces competitive modes.

Author: AGI System
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveState(Enum):
    """Enumeration of possible cognitive states in the Flow theory."""
    FLOW = auto()
    ANXIETY = auto()
    BOREDOM = auto()
    RELAXATION = auto()


class DifficultyAction(Enum):
    """Actions the engine can take to adjust the learning path."""
    INCREASE_DIFFICULTY = "Promote to higher complexity"
    DECREASE_DIFFICULTY = "Provide scaffolding or simplify"
    MAINTAIN_CURRENT = "Maintain current pace"
    TRIGGER_COMPETITIVE_MODE = "Enable speed run mode"


@dataclass
class LearnerMetrics:
    """
    Real-time metrics captured from the learner.
    
    Attributes:
        response_time: Time taken to solve the last problem (in seconds).
        accuracy_rate: Success rate of the last 10 interactions (0.0 to 1.0).
        bio_feedback_score: Simulated stress/engagement metric (0.0 to 1.0, 
                            where 0.5 is baseline, >0.5 is stress).
    """
    response_time: float
    accuracy_rate: float
    bio_feedback_score: float = 0.5

    def __post_init__(self):
        """Validate data ranges."""
        if not (0.0 <= self.accuracy_rate <= 1.0):
            raise ValueError("Accuracy rate must be between 0.0 and 1.0")
        if self.response_time <= 0:
            raise ValueError("Response time must be positive")


@dataclass
class LearningContent:
    """Represents a gamified learning unit (Level)."""
    level_id: str
    difficulty: float  # 1.0 (Easy) to 10.0 (Hard)
    concepts: List[str]
    is_scaffolded: bool = False


class AdaptiveFlowEngine:
    """
    The core engine that orchestrates the adaptive learning flow.
    
    It processes learner metrics to determine cognitive state and adjusts
    the learning content difficulty accordingly.
    """

    def __init__(self, initial_difficulty: float = 1.0):
        """
        Initialize the engine.
        
        Args:
            initial_difficulty: The starting difficulty level for the learner.
        """
        self.current_difficulty = initial_difficulty
        self.history: List[CognitiveState] = []
        logger.info(f"Engine initialized with difficulty: {initial_difficulty}")

    def _calculate_cognitive_load(self, metrics: LearnerMetrics) -> float:
        """
        Calculate a normalized cognitive load score based on metrics.
        
        High response time + low accuracy = High Load (Anxiety).
        Low response time + high accuracy = Low Load (Boredom).
        
        Args:
            metrics: The current learner metrics.
            
        Returns:
            A float representing cognitive load (0.0 to 1.0).
        """
        # Normalize response time (assuming 30s is high latency for a step)
        time_factor = min(metrics.response_time / 30.0, 1.0)
        
        # Invert accuracy (lower accuracy increases load)
        error_factor = 1.0 - metrics.accuracy_rate
        
        # Combine factors with weights
        # Bio-feedback acts as a multiplier or modifier
        load_score = (time_factor * 0.4 + error_factor * 0.6) * metrics.bio_feedback_score * 2
        
        # Clamp result
        load_score = max(0.0, min(load_score, 1.0))
        
        logger.debug(f"Calculated cognitive load: {load_score:.3f}")
        return load_score

    def _determine_state(self, cognitive_load: float) -> CognitiveState:
        """
        Map the cognitive load to a specific Flow State.
        
        Args:
            cognitive_load: The calculated load score (0.0-1.0).
            
        Returns:
            The current CognitiveState.
        """
        # Dynamic Threshold based on current difficulty
        # Higher difficulty might shift tolerance for load
        challenge_level = self.current_difficulty / 10.0
        
        # Calculate the "Flow Zone" boundaries
        # Ideally, Challenge Level ~= Skill Level (which is roughly current_difficulty)
        lower_bound = challenge_level - 0.15
        upper_bound = challenge_level + 0.15
        
        if cognitive_load > upper_bound:
            return CognitiveState.ANXIETY
        elif cognitive_load < lower_bound:
            return CognitiveState.BOREDOM
        else:
            return CognitiveState.FLOW

    def update_state_and_difficulty(
        self, 
        metrics: LearnerMetrics
    ) -> Tuple[CognitiveState, DifficultyAction]:
        """
        Core function to process metrics, update internal state, and decide action.
        
        Args:
            metrics: Current performance data from the learner.
            
        Returns:
            A tuple containing the identified CognitiveState and the recommended Action.
        """
        try:
            load = self._calculate_cognitive_load(metrics)
            state = self._determine_state(load)
            self.history.append(state)
            
            action = DifficultyAction.MAINTAIN_CURRENT
            
            if state == CognitiveState.ANXIETY:
                logger.warning("Learner entering Anxiety Zone. Reducing difficulty.")
                self.current_difficulty = max(1.0, self.current_difficulty - 0.5)
                action = DifficultyAction.DECREASE_DIFFICULTY
                
            elif state == CognitiveState.BOREDOM:
                logger.info("Learner in Boredom Zone. Increasing challenge.")
                self.current_difficulty = min(10.0, self.current_difficulty + 0.5)
                
                # Introduce gamification twist if too easy for too long
                if len(self.history) > 3 and all(s == CognitiveState.BOREDOM for s in self.history[-3:]):
                    action = DifficultyAction.TRIGGER_COMPETITIVE_MODE
                else:
                    action = DifficultyAction.INCREASE_DIFFICULTY
                    
            else:
                logger.info("Learner is in FLOW state. Maintaining course.")
                
            return state, action

        except Exception as e:
            logger.error(f"Error in engine update: {e}")
            raise

    def generate_next_content(self, base_content: LearningContent) -> LearningContent:
        """
        Modifies the learning content based on the current engine difficulty.
        
        Args:
            base_content: The raw content for the current level.
            
        Returns:
            Modified LearningContent instance.
        """
        # Adjust difficulty metadata
        base_content.difficulty = self.current_difficulty
        
        # Add scaffolding if difficulty was recently lowered significantly
        if self.current_difficulty < 2.0:
            base_content.is_scaffolded = True
            base_content.concepts.append("guided_tutorial")
            
        return base_content


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize Engine
    engine = AdaptiveFlowEngine(initial_difficulty=5.0)
    
    # 2. Simulate Learner Interactions
    
    # Scenario A: Learner is struggling (High time, Low accuracy)
    print("\n--- Scenario A: Struggling Learner ---")
    struggle_metrics = LearnerMetrics(
        response_time=45.0,  # Very slow
        accuracy_rate=0.4,   # Low accuracy
        bio_feedback_score=0.8 # High stress
    )
    state, action = engine.update_state_and_difficulty(struggle_metrics)
    print(f"State: {state.name}, Action: {action.value}")
    print(f"New Difficulty: {engine.current_difficulty}")
    
    # Scenario B: Learner is bored (Fast time, High accuracy)
    print("\n--- Scenario B: Bored Learner ---")
    bored_metrics = LearnerMetrics(
        response_time=2.0,   # Very fast
        accuracy_rate=1.0,   # Perfect
        bio_feedback_score=0.3 # Low arousal
    )
    # Run multiple times to trigger competitive mode potentially
    for _ in range(3):
        state, action = engine.update_state_and_difficulty(bored_metrics)
    
    print(f"State: {state.name}, Action: {action.value}")
    print(f"New Difficulty: {engine.current_difficulty}")
    
    # 3. Content Generation
    print("\n--- Content Generation ---")
    raw_content = LearningContent(level_id="lvl_102", difficulty=5.0, concepts=["algebra"])
    adapted_content = engine.generate_next_content(raw_content)
    print(f"Generated Content: ID={adapted_content.level_id}, Diff={adapted_content.difficulty}, Scaffolded={adapted_content.is_scaffolded}")