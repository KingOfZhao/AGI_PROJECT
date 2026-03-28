"""
Module: adaptive_cognitive_zoom_lens
Description: Implements an 'Adaptive Cognitive Zoom Lens' for AGI systems.
             This module dynamically adjusts the information granularity based on
             user cognitive load and emotional state to prevent analysis paralysis
             (anxiety) or unproductive daydreaming (lofty abstraction).

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveState(Enum):
    """Enumerates the possible cognitive states of the user."""
    ANXIOUS_OVER_FOCUS = auto()  # Too much detail, needs zoom out
    BALANCED = auto()            # Optimal focus
    ABSTRACT_UNDER_FOCUS = auto() # Too much abstraction, needs zoom in (drill down)

class GranularityLevel(Enum):
    """Defines the levels of information density."""
    HIGH_LEVEL_VISION = 1   # "Save the planet" / "Become a CTO"
    STRATEGIC_SCOPE = 2     # "Reduce carbon emissions by 20%" / "Learn System Design"
    TACTICAL_PLAN = 3       # "Switch to electric vehicles" / "Complete Course Module 1"
    ATOMIC_ACTION = 4       # "Sign up for charging station app" / "Open the textbook"

@dataclass
class UserState:
    """Represents the current biometric and behavioral state of the user."""
    cognitive_load: float  # Range 0.0 (relaxed) to 1.0 (overwhelmed)
    anxiety_index: float   # Range 0.0 (calm) to 1.0 (panicked)
    engagement_depth: float # Range 0.0 (skimming/daydreaming) to 1.0 (deep focus)

    def __post_init__(self):
        """Validate data ranges."""
        if not all(0.0 <= v <= 1.0 for v in [self.cognitive_load, self.anxiety_index, self.engagement_depth]):
            raise ValueError("User state values must be between 0.0 and 1.0")

@dataclass
class ContentChunk:
    """Represents a unit of information with specific granularity."""
    level: GranularityLevel
    content: str
    complexity_score: float # 0.0 (simple) to 1.0 (complex)

class AdaptiveCognitiveLens:
    """
    Core class implementing the Adaptive Cognitive Zoom Lens logic.
    
    Use Case:
        Ideal for complex domains like Climate Change strategy or Career Planning
        where users often get lost in details (anxiety) or float in abstractions (inaction).
    
    Example:
        >>> lens = AdaptiveCognitiveLens()
        >>> user_state = UserState(cognitive_load=0.9, anxiety_index=0.8, engagement_depth=0.9)
        >>> current_granularity = GranularityLevel.ATOMIC_ACTION
        >>> new_granularity = lens.adjust_focus(user_state, current_granularity)
        >>> print(new_granularity)
        <GranularityLevel.HIGH_LEVEL_VISION: 1> # Zoomed out to reduce anxiety
    """

    def __init__(self, zoom_sensitivity: float = 0.5):
        """
        Initialize the lens.
        
        Args:
            zoom_sensitivity (float): How aggressively the system adjusts focus (0.1 to 1.0).
        """
        if not 0.1 <= zoom_sensitivity <= 1.0:
            logger.warning("Zoom sensitivity out of bounds, defaulting to 0.5")
            zoom_sensitivity = 0.5
        
        self.zoom_sensitivity = zoom_sensitivity
        logger.info(f"AdaptiveCognitiveLens initialized with sensitivity {zoom_sensitivity}")

    def _analyze_cognitive_state(self, state: UserState) -> CognitiveState:
        """
        [Helper] Analyzes the user state to determine the cognitive equilibrium.
        
        Args:
            state (UserState): Current user metrics.
            
        Returns:
            CognitiveState: The determined state.
        """
        # Thresholds could be dynamic in a full AGI system
        ANXIETY_THRESHOLD = 0.7
        ABSTRACTION_THRESHOLD = 0.3
        
        # Logic: High Anxiety + High Engagement = Over-Focus (Anxiety)
        if state.anxiety_index > ANXIETY_THRESHOLD and state.engagement_depth > 0.6:
            logger.debug("Detected: ANXIOUS_OVER_FOCUS")
            return CognitiveState.ANXIOUS_OVER_FOCUS
        
        # Logic: Low Anxiety + Low Engagement + Low Load = Daydreaming (Under-Focus)
        if (state.engagement_depth < ABSTRACTION_THRESHOLD and 
            state.cognitive_load < 0.4):
            logger.debug("Detected: ABSTRACT_UNDER_FOCUS")
            return CognitiveState.ABSTRACT_UNDER_FOCUS
            
        logger.debug("Detected: BALANCED")
        return CognitiveState.BALANCED

    def adjust_focus(self, 
                     state: UserState, 
                     current_level: GranularityLevel) -> GranularityLevel:
        """
        [Core] Determines the optimal information granularity based on user state.
        
        Args:
            state (UserState): The current biometric/behavioral state.
            current_level (GranularityLevel): The current zoom level of the information.
            
        Returns:
            GranularityLevel: The recommended new zoom level.
        """
        try:
            cognitive_state = self._analyze_cognitive_state(state)
            current_idx = current_level.value
            
            if cognitive_state == CognitiveState.ANXIOUS_OVER_FOCUS:
                # ZOOM OUT: Reduce complexity to show "The Big Picture" (Meaning)
                # Move towards level 1 (High Level)
                new_idx = max(1, current_idx - 1)
                logger.info(f"User anxious. Zooming OUT from {current_level.name} to alleviate pressure.")
                
            elif cognitive_state == CognitiveState.ABSTRACT_UNDER_FOCUS:
                # ZOOM IN: Force specific details to ground the user (Action)
                # Move towards level 4 (Atomic Action)
                new_idx = min(4, current_idx + 1)
                logger.info(f"User daydreaming. Zooming IN from {current_level.name} to ground in reality.")
                
            else:
                # BALANCED: Maintain current course, maybe slight optimization
                new_idx = current_idx
                logger.info("User is balanced. Maintaining current cognitive focus.")
                
            return GranularityLevel(new_idx)
            
        except Exception as e:
            logger.error(f"Error adjusting focus: {e}")
            return current_level # Fail-safe to current level

    def generate_response_content(self, 
                                  topic: str, 
                                  level: GranularityLevel) -> ContentChunk:
        """
        [Core] Generates or retrieves content appropriate for the specific granularity.
        
        Args:
            topic (str): The subject matter (e.g., "Climate Change").
            level (GranularityLevel): The target zoom level.
            
        Returns:
            ContentChunk: The formatted content object.
        """
        content_map = {
            GranularityLevel.HIGH_LEVEL_VISION: f"Macro Goal: Why {topic} matters to the world.",
            GranularityLevel.STRATEGIC_SCOPE: f"Strategy: Key pillars to address {topic}.",
            GranularityLevel.TACTICAL_PLAN: f"Plan: Specific projects within {topic}.",
            GranularityLevel.ATOMIC_ACTION: f"Action: The immediate next step for {topic}."
        }
        
        content_text = content_map.get(level, "Unknown scope")
        
        # Calculate complexity score inversely proportional to granularity level
        # Level 1 (Vision) -> Low complexity (0.2), Level 4 (Action) -> High complexity (0.8)
        complexity = 0.2 * level.value 
        
        return ContentChunk(level=level, content=content_text, complexity_score=complexity)

# ---------------------------------------------------------
# Usage Example and Simulation
# ---------------------------------------------------------
if __name__ == "__main__":
    # Initialize System
    lens = AdaptiveCognitiveLens(zoom_sensitivity=0.7)
    
    # Scenario 1: User is spiraling into details about 'Career Change' (Anxiety/Over-focus)
    # Current state: High Load, High Anxiety, High Focus
    # Current Info: Atomic Action (Level 4) - e.g., "Fix typo on resume line 4"
    user_state_anxious = UserState(cognitive_load=0.85, anxiety_index=0.9, engagement_depth=0.9)
    current_info_level = GranularityLevel.ATOMIC_ACTION
    
    print("\n--- Scenario 1: Anxious Over-Focus ---")
    adjusted_level = lens.adjust_focus(user_state_anxious, current_info_level)
    response = lens.generate_response_content("Career Change", adjusted_level)
    print(f"Adjusted Level: {adjusted_level.name}")
    print(f"AI Response: {response.content}")
    print(f"Response Complexity: {response.complexity_score}")

    # Scenario 2: User is daydreaming about 'Startup Success' (Abstraction/Under-focus)
    # Current state: Low Load, Low Anxiety, Low Focus
    # Current Info: Vision (Level 1) - e.g., "We will disrupt the industry"
    user_state_dreamer = UserState(cognitive_load=0.1, anxiety_index=0.1, engagement_depth=0.2)
    current_info_level_vision = GranularityLevel.HIGH_LEVEL_VISION
    
    print("\n--- Scenario 2: Abstract Under-Focus ---")
    adjusted_level_2 = lens.adjust_focus(user_state_dreamer, current_info_level_vision)
    response_2 = lens.generate_response_content("Startup Success", adjusted_level_2)
    print(f"Adjusted Level: {adjusted_level_2.name}")
    print(f"AI Response: {response_2.content}")
    print(f"Response Complexity: {response_2.complexity_score}")