"""
Module: natural_language_strategy_corrector.py

This module implements a Natural Language Strategy Correction Interface.
It bridges the gap between high-level human semantic instructions and
low-level AGI physical control parameters.

Author: Senior Python Engineer
Version: 1.0.0
Domain: Human-Computer Interaction (HCI)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configurations ---
MAX_DAMPING_VALUE = 1.0
MIN_DAMPING_VALUE = 0.0
MAX_VELOCITY = 5.0
JOINT_MAPPING = {
    "wrist": "joint_6",
    "elbow": "joint_5",
    "shoulder": "joint_4",
    "base": "joint_1"
}

@dataclass
class ControlParameters:
    """
    Represents the mutable control parameters of the AGI agent.
    
    Attributes:
        joint_dampings (Dict[str, float]): Damping ratios for joints (0.0 to 1.0).
        velocity_limits (Dict[str, float]): Max velocity for joints.
        smoothing_factor (float): Trajectory smoothing intensity.
    """
    joint_dampings: Dict[str, float] = field(default_factory=lambda: {
        "joint_1": 0.5, "joint_4": 0.5, "joint_5": 0.5, "joint_6": 0.5
    })
    velocity_limits: Dict[str, float] = field(default_factory=lambda: {
        "joint_1": 1.0, "joint_4": 1.0, "joint_5": 1.0, "joint_6": 1.0
    })
    smoothing_factor: float = 0.5

    def update_damping(self, joint_key: str, value: float) -> None:
        """Updates a specific joint's damping with boundary checks."""
        if joint_key in self.joint_dampings:
            clamped_value = max(MIN_DAMPING_VALUE, min(MAX_DAMPING_VALUE, value))
            self.joint_dampings[joint_key] = clamped_value
            logger.info(f"Updated {joint_key} damping to {clamped_value}")
        else:
            logger.error(f"Attempted to update non-existent joint: {joint_key}")

@dataclass
class CorrectionIntent:
    """
    Structured representation of a natural language command.
    
    Attributes:
        target_component (str): The hardware component identified (e.g., 'joint_5').
        action_type (str): The type of adjustment (e.g., 'stabilize', 'speed_up').
        intensity (float): A normalized magnitude of change (-1.0 to 1.0).
        raw_text (str): Original user input.
    """
    target_component: str
    action_type: str
    intensity: float = 0.0
    raw_text: str = ""

class SemanticParsingError(Exception):
    """Custom exception for errors during NLU parsing."""
    pass

class ParameterApplicationError(Exception):
    """Custom exception for errors applying parameters to the control system."""
    pass

class NaturalLanguageCorrector:
    """
    Main Interface Class.
    Parses natural language instructions and applies modifications to the robot's
    control strategy parameters.
    """

    def __init__(self, initial_params: Optional[ControlParameters] = None):
        """
        Initializes the corrector with default or provided control parameters.
        
        Args:
            initial_params (Optional[ControlParameters]): Initial state of the robot.
        """
        self.params = initial_params if initial_params else ControlParameters()
        logger.info("NaturalLanguageCorrector initialized.")

    def parse_semantic_instruction(self, text: str) -> CorrectionIntent:
        """
        Core Function 1:
        Converts raw natural language into a structured CorrectionIntent.
        Uses simple keyword extraction and heuristics (Mock NLP).
        
        Args:
            text (str): The user's instruction (e.g., "手肘沉下来").
            
        Returns:
            CorrectionIntent: Structured data representing the instruction.
            
        Raises:
            SemanticParsingError: If intent cannot be determined.
        """
        if not text or not isinstance(text, str):
            raise SemanticParsingError("Input text must be a non-empty string.")

        text = text.lower().strip()
        target = "unknown"
        action = "undefined"
        intensity = 0.2  # Default small adjustment

        logger.debug(f"Parsing text: {text}")

        # 1. Entity Extraction (Target)
        if "手肘" in text or "elbow" in text:
            target = JOINT_MAPPING["elbow"]
        elif "手腕" in text or "wrist" in text:
            target = JOINT_MAPPING["wrist"]
        elif "肩膀" in text or "shoulder" in text:
            target = JOINT_MAPPING["shoulder"]
        else:
            # Default to global smoothing if no specific joint mentioned
            target = "global"

        # 2. Intent Classification (Action)
        # Keywords: 抖动, 沉, 稳 -> Stabilize (Increase Damping)
        if any(w in text for w in ["抖动", "shake", "unstable", "稳", "沉", "steady"]):
            action = "stabilize"
            intensity = 0.5 # Strong increase in damping
        # Keywords: 快, 加速 -> Speed Up (Decrease Damping/Increase Limit)
        elif any(w in text for w in ["快", "fast", "speed", "敏捷"]):
            action = "speed_up"
            intensity = -0.3 # Decrease damping
        # Keywords: 慢, 轻柔 -> Slow Down
        elif any(w in text for w in ["慢", "slow", "gentle"]):
            action = "slow_down"
            intensity = 0.8 # High damping
        
        if action == "undefined":
            raise SemanticParsingError(f"Could not determine action intent from: {text}")

        return CorrectionIntent(
            target_component=target,
            action_type=action,
            intensity=intensity,
            raw_text=text
        )

    def apply_intent_to_policy(self, intent: CorrectionIntent) -> Tuple[bool, str]:
        """
        Core Function 2:
        Translates the structured intent into concrete parameter changes.
        
        Args:
            intent (CorrectionIntent): The parsed intention object.
            
        Returns:
            Tuple[bool, str]: (Success status, Message describing the change).
        """
        if not intent:
            raise ParameterApplicationError("Intent object is None")

        component = intent.target_component
        action = intent.action_type
        val = intent.intensity

        try:
            # Case 1: Global Adjustment
            if component == "global":
                if action == "stabilize":
                    self.params.smoothing_factor = min(1.0, self.params.smoothing_factor + 0.2)
                    return True, "Global smoothing increased."
                return False, "Global action not recognized."

            # Case 2: Joint-Specific Adjustment
            # We assume 'stabilize' primarily affects damping for this demo
            if action == "stabilize":
                current = self.params.joint_dampings.get(component, 0.5)
                new_val = current + val
                self.params.update_damping(component, new_val)
                return True, f"Increased damping on {component} to {new_val:.2f}."

            elif action == "speed_up":
                current = self.params.joint_dampings.get(component, 0.5)
                new_val = current + val # val is negative here
                self.params.update_damping(component, new_val)
                return True, f"Reduced damping on {component} to {new_val:.2f} for speed."
            
            elif action == "slow_down":
                current = self.params.joint_dampings.get(component, 0.5)
                new_val = current + val
                self.params.update_damping(component, new_val)
                return True, f"Slowed down {component} via damping {new_val:.2f}."

            return False, "No valid mapping found for action."

        except Exception as e:
            logger.error(f"Critical error applying intent: {e}")
            raise ParameterApplicationError(f"Failed to update parameters: {e}")

    def _diagnostic_report(self) -> Dict[str, float]:
        """
        Helper Function:
        Returns a summary of current system parameters for verification.
        """
        return {
            "avg_damping": sum(self.params.joint_dampings.values()) / len(self.params.joint_dampings),
            "smoothing": self.params.smoothing_factor
        }

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize System
    corrector = NaturalLanguageCorrector()
    
    print("--- Current State ---")
    print(corrector.params)
    
    # Scenario: AI is drawing a line but shaking
    user_input = "手肘沉下来"  # User says: "Elbow, settle down"
    
    try:
        print(f"\n>>> Processing User Input: '{user_input}'")
        
        # Step 1: Parse Language
        intent = corrector.parse_semantic_instruction(user_input)
        
        # Step 2: Apply to Policy
        success, message = corrector.apply_intent_to_policy(intent)
        
        if success:
            print(f"SUCCESS: {message}")
        else:
            print(f"FAIL: {message}")
            
        print("\n--- New State ---")
        print(corrector.params)
        
    except (SemanticParsingError, ParameterApplicationError) as e:
        print(f"Error processing request: {e}")