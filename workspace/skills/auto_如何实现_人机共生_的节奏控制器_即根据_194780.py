"""
Module: symbiotic_rhythm_controller

This module implements a 'Symbiotic Rhythm Controller' designed to optimize the
interaction loop between an AI system and a human user. It aims to prevent
user fatigue (avoiding the 'click slave' phenomenon) and AI hallucination
or stagnation (caused by lack of feedback).

The controller dynamically adjusts the frequency and complexity of AI requests
based on human state (fatigue, interest) and AI state (progress, urgency).

Key Concepts:
- Interaction Frequency: How often the AI prompts the user.
- Interaction Depth: The complexity of the tasks/questions presented.
- Symbiotic Balance: The equilibrium between AI autonomy and human oversight.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SymbioticRhythmController")

# --- Enums and Data Structures ---

class InteractionDepth(Enum):
    """Defines the cognitive load required for an interaction."""
    LIGHT = 1.0      # Simple Yes/No, binary choices
    MEDIUM = 2.0     # Multiple choice, simple feedback
    DEEP = 3.0       # Creative input, complex decision making

class HumanState(Enum):
    """Represents the current state of the human user."""
    HIGH_ENERGY = 1
    NORMAL = 2
    FATIGUED = 3
    OVERLOADED = 4

@dataclass
class UserStatus:
    """Data model representing the human's current condition."""
    fatigue_level: float  # 0.0 (Refreshed) to 1.0 (Exhausted)
    interest_level: float # 0.0 (Bored) to 1.0 (Highly Engaged)
    last_interaction_ts: float = field(default_factory=time.time)

    def __post_init__(self):
        if not (0.0 <= self.fatigue_level <= 1.0):
            raise ValueError("Fatigue level must be between 0.0 and 1.0")
        if not (0.0 <= self.interest_level <= 1.0):
            raise ValueError("Interest level must be between 0.0 and 1.0")

@dataclass
class AIStatus:
    """Data model representing the AI's current operational state."""
    pending_tasks: int       # Number of tasks waiting for human input
    data_accumulated: float  # Amount of new unprocessed data (0.0 - 1.0)
    confidence_score: float  # AI's current model confidence (0.0 - 1.0)

# --- Core Logic ---

class SymbioticRhythmController:
    """
    The main controller class that calculates the optimal interaction rhythm.
    
    Attributes:
        max_frequency_per_hour (float): Upper limit of interactions.
        min_frequency_per_hour (float): Lower limit to prevent AI stagnation.
    """

    def __init__(self, max_frequency: float = 20.0, min_frequency: float = 2.0):
        self.max_frequency_per_hour = max_frequency
        self.min_frequency_per_hour = min_frequency
        self.history: List[Dict[str, Any]] = []
        logger.info("SymbioticRhythmController initialized.")

    def _calculate_human_readiness(self, user: UserStatus) -> float:
        """
        [Helper] Calculates a normalized score (0.0-1.0) of how ready the human is 
        to interact based on fatigue and interest.
        
        Formula: (Interest * Weight) - (Fatigue * Weight) normalized.
        """
        # Interest pulls readiness up, Fatigue pulls it down
        # Weighted: High fatigue is penalized more heavily to prevent burnout
        score = (user.interest_level * 0.6) - (user.fatigue_level * 0.8)
        
        # Normalize to 0.0 - 1.0 range using sigmoid-like logic or simple clamping
        readiness = max(0.0, min(1.0, (score + 0.5))) # Centered around 0.5
        
        logger.debug(f"Human readiness calculated: {readiness:.2f} "
                     f"(Fatigue: {user.fatigue_level}, Interest: {user.interest_level})")
        return readiness

    def _calculate_ai_urgency(self, ai: AIStatus) -> float:
        """
        [Helper] Calculates how urgently the AI needs human intervention.
        
        High pending tasks + Low confidence = High Urgency.
        """
        # If confidence is high, urgency is low unless data accumulated is massive
        urgency_factor = (ai.pending_tasks * 0.1) + (ai.data_accumulated * 0.5)
        confidence_penalty = 1.0 - ai.confidence_score
        
        urgency = min(1.0, urgency_factor * (1.0 + confidence_penalty))
        logger.debug(f"AI urgency calculated: {urgency:.2f}")
        return urgency

    def determine_next_action(self, user: UserStatus, ai: AIStatus) -> Tuple[float, InteractionDepth, str]:
        """
        [Core] Determines the interaction frequency, depth, and suggested mode.
        
        Args:
            user (UserStatus): Current state of the human.
            ai (AIStatus): Current state of the AI.
            
        Returns:
            Tuple[float, InteractionDepth, str]: 
                - Recommended interactions per hour.
                - Recommended depth of next interaction.
                - Textual strategy recommendation.
        
        Raises:
            ValueError: If input data validation fails.
        """
        try:
            # 1. Validate inputs (handled by dataclasses, but double check logic)
            if user.fatigue_level > 0.9 and ai.confidence_score < 0.3:
                logger.warning("CRITICAL: User exhausted but AI is confused. "
                               "Switching to passive observation mode.")

            # 2. Calculate internal metrics
            h_readiness = self._calculate_human_readiness(user)
            a_urgency = self._calculate_ai_urgency(ai)
            
            # 3. Determine Interaction Frequency (Interactions per Hour)
            # Base frequency scales with readiness and urgency
            # If human is tired, frequency drops significantly unless urgency is critical
            freq_modifier = h_readiness * 0.7 + a_urgency * 0.3
            
            target_freq = self.min_frequency_per_hour + \
                          (self.max_frequency_per_hour - self.min_frequency_per_hour) * freq_modifier
            
            # Hard bounds
            target_freq = max(self.min_frequency_per_hour, 
                              min(self.max_frequency_per_hour, target_freq))

            # 4. Determine Interaction Depth
            # If user is tired, keep depth LOW (give them easy tasks)
            # If AI is confused (low confidence), it might need DEEP input, 
            # but if user is tired too, we must compromise.
            if user.fatigue_level > 0.7:
                depth = InteractionDepth.LIGHT
                strategy = "Reduction Mode: Minimizing cognitive load."
            elif a_urgency > 0.8 and user.interest_level > 0.6:
                depth = InteractionDepth.DEEP
                strategy = "Flow Mode: High-value deep work session."
            elif user.fatigue_level < 0.3 and user.interest_level > 0.5:
                depth = InteractionDepth.MEDIUM
                strategy = "Standard Mode: Regular collaborative pacing."
            else:
                depth = InteractionDepth.LIGHT
                strategy = "Maintenance Mode: Keeping loop alive with low effort."

            # Log the decision
            logger.info(f"Action Determined: Freq={target_freq:.1f}/hr, "
                        f"Depth={depth.name}, Strategy={strategy}")
            
            # Record history for future learning
            self.history.append({
                "timestamp": time.time(),
                "target_freq": target_freq,
                "depth": depth.name,
                "h_readiness": h_readiness,
                "a_urgency": a_urgency
            })

            return target_freq, depth, strategy

        except Exception as e:
            logger.error(f"Error in rhythm calculation: {e}")
            # Fallback to safe defaults
            return self.min_frequency_per_hour, InteractionDepth.LIGHT, "Error Fallback"

    def get_next_interaction_delay(self, target_freq: float) -> float:
        """
        [Core] Converts the target frequency into a concrete wait time (in seconds).
        
        Args:
            target_freq (float): Target interactions per hour.
            
        Returns:
            float: Seconds to wait before the next prompt.
        """
        if target_freq <= 0:
            return 3600.0 # Wait an hour if freq is 0
        
        # 3600 seconds in an hour / frequency
        interval = 3600.0 / target_freq
        
        # Add jitter (randomness) to prevent robotic predictability
        # Jitter is +/- 10%
        jitter = interval * 0.1 * ( (time.time() % 1) - 0.5 ) 
        final_delay = max(10.0, interval + jitter) # Minimum 10s delay
        
        return final_delay

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize Controller
    controller = SymbioticRhythmController()
    
    # Scenario 1: User is fresh, AI has lots of data
    # Expected: High frequency, Medium/Deep depth
    user_state_1 = UserStatus(fatigue_level=0.1, interest_level=0.9)
    ai_state_1 = AIStatus(pending_tasks=5, data_accumulated=0.8, confidence_score=0.6)
    
    freq, depth, strategy = controller.determine_next_action(user_state_1, ai_state_1)
    delay = controller.get_next_interaction_delay(freq)
    
    print(f"--- Scenario 1 ---")
    print(f"Strategy: {strategy}")
    print(f"Next prompt in: {delay:.2f} seconds")
    print(f"Depth: {depth.name}\n")

    # Scenario 2: User is exhausted, AI is confident
    # Expected: Low frequency, Light depth (Maintenance)
    user_state_2 = UserStatus(fatigue_level=0.9, interest_level=0.2)
    ai_state_2 = AIStatus(pending_tasks=1, data_accumulated=0.1, confidence_score=0.95)
    
    freq, depth, strategy = controller.determine_next_action(user_state_2, ai_state_2)
    delay = controller.get_next_interaction_delay(freq)
    
    print(f"--- Scenario 2 ---")
    print(f"Strategy: {strategy}")
    print(f"Next prompt in: {delay:.2f} seconds")
    print(f"Depth: {depth.name}")