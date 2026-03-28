"""
Module: auto_人机共生闭环_构建_意图校准反馈环_38eeb7

Description:
    This module implements an "Intent Calibration Feedback Loop" for Human-Computer
    Symbiosis (HCS). It addresses the challenge where code execution results deviate
    from the user's implicit intent.
    
    Instead of discarding the current state and regenerating code from scratch 
    (which is costly and potentially repetitive), this system identifies the 
    specific point of deviation and proposes minimal interaction corrections 
    (e.g., A/B binary choices) to update the intent model parameters dynamically.

    This creates a closed loop: Observe Result -> Detect Deviation -> Solicit 
    Minimal Feedback -> Update Model -> Patch Execution.

Domain: Human-Computer Interaction (HCI) / AGI Skill Layer
"""

import logging
import json
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class DeviationType(Enum):
    """Classification of intent deviation."""
    NONE = auto()
    PARAMETER_MISMATCH = auto()
    STYLE_INCONSISTENCY = auto()
    SCOPE_OVERFLOW = auto()
    LOGIC_ERROR = auto()

class FeedbackChoice(Enum):
    """User's binary or categorical choice."""
    OPTION_A = "Accept Original"
    OPTION_B = "Accept Correction"
    ESCALATE = "Need Human Review"

@dataclass
class ExecutionState:
    """Represents the state of a specific code execution or agent step."""
    step_id: str
    description: str
    output_data: Dict[str, Any]
    detected_deviation: DeviationType = DeviationType.NONE
    confidence_score: float = 1.0  # 0.0 to 1.0

    def is_problematic(self) -> bool:
        return self.detected_deviation != DeviationType.NONE or self.confidence_score < 0.7

@dataclass
class IntentModel:
    """
    Represents the AGI's current understanding of user intent.
    In a real system, this would be a vector or a complex graph.
    Here, we simulate it as a dictionary of weights/preferences.
    """
    user_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "verbosity": "high",
        "risk_tolerance": "low",
        "format_preference": "json",
        "target_audience": "technical"
    })
    feedback_history: List[Dict[str, str]] = field(default_factory=list)

    def update(self, key: str, value: Any, reason: str):
        """Updates the model based on feedback."""
        logger.info(f"Updating Intent Model: {key} changed to {value}. Reason: {reason}")
        self.user_preferences[key] = value
        self.feedback_history.append({"updated_key": key, "new_value": value, "reason": reason})

@dataclass
class InteractionPayload:
    """The minimal interaction object presented to the user."""
    question: str
    option_a_label: str
    option_b_label: str
    context_data: Dict[str, Any] = field(default_factory=dict)

# --- Core Functions ---

def analyze_execution_deviation(
    current_state: ExecutionState, 
    intent_model: IntentModel
) -> Tuple[DeviationType, float, Optional[str]]:
    """
    Core Function 1: Analyzes the execution state against the intent model to detect misalignment.
    
    Args:
        current_state (ExecutionState): The result of the recent code execution.
        intent_model (IntentModel): The current model of user intent.
        
    Returns:
        Tuple containing:
        - DeviationType: The type of error detected.
        - float: A confidence score (0.0-1.0) of the current execution relative to intent.
        - Optional[str]: A suggested correction key if deviation is found.
    """
    logger.info(f"Analyzing execution state {current_state.step_id}...")
    
    # Simulation logic: Check if execution matches preferences
    prefs = intent_model.user_preferences
    
    # Check 1: Format
    output_format = current_state.output_data.get("format")
    expected_format = prefs.get("format_preference")
    
    if output_format != expected_format:
        logger.warning(f"Deviation detected: Format mismatch. Expected {expected_format}, got {output_format}")
        return DeviationType.STYLE_INCONSISTENCY, 0.4, "format_preference"
        
    # Check 2: Audience Complexity
    complexity = current_state.output_data.get("complexity", 0)
    target = prefs.get("target_audience")
    
    if target == "technical" and complexity < 5:
        logger.warning("Deviation detected: Output too simple for technical audience.")
        return DeviationType.PARAMETER_MISMATCH, 0.5, "complexity_level"
        
    # Check 3: Random uncertainty simulation
    if random.random() < 0.1: # 10% chance of random low confidence
         return DeviationType.LOGIC_ERROR, 0.2, "logic_check"

    return DeviationType.NONE, 0.95, None

def generate_calibration_interaction(
    deviation_type: DeviationType, 
    correction_key: Optional[str],
    state: ExecutionState
) -> Optional[InteractionPayload]:
    """
    Core Function 2: Constructs a minimal A/B interaction payload to resolve the ambiguity.
    
    Instead of asking "What do you want?", it asks "I noticed X, should I do Y instead?"
    
    Args:
        deviation_type (DeviationType): The type of issue found.
        correction_key (Optional[str]): The specific key to adjust.
        state (ExecutionState): The context of the execution.
        
    Returns:
        InteractionPayload: The structured question for the user.
    """
    if deviation_type == DeviationType.NONE:
        return None
        
    logger.info(f"Generating calibration UI for deviation: {deviation_type.name}")
    
    if deviation_type == DeviationType.STYLE_INCONSISTENCY and correction_key == "format_preference":
        return InteractionPayload(
            question="The output format seems to differ from your usual preference. Should I standardize it?",
            option_a_label="Keep current output (Text)",
            option_b_label="Convert to JSON",
            context_data={"step_id": state.step_id}
        )
        
    elif deviation_type == DeviationType.PARAMETER_MISMATCH and correction_key == "complexity_level":
        return InteractionPayload(
            question="The solution seems simplified. Should I increase technical depth?",
            option_a_label="Keep simple",
            option_b_label="Increase depth",
            context_data={"step_id": state.step_id}
        )
        
    else:
        # Generic fallback
        return InteractionPayload(
            question="I'm unsure about this result. Is this acceptable?",
            option_a_label="Yes, proceed",
            option_b_label="No, revise",
            context_data={"step_id": state.step_id}
        )

# --- Helper Functions ---

def apply_feedback_to_model(
    choice: FeedbackChoice, 
    payload: InteractionPayload, 
    intent_model: IntentModel,
    correction_key: str
) -> bool:
    """
    Helper Function: Processes the user's input and updates the intent model.
    
    Args:
        choice (FeedbackChoice): The user's selection.
        payload (InteractionPayload): The question that was asked.
        intent_model (IntentModel): The model to update.
        correction_key (str): The internal key being calibrated.
        
    Returns:
        bool: True if model was updated, False otherwise.
    """
    if choice == FeedbackChoice.OPTION_A:
        logger.info("User confirmed original path. No model update required, reinforcing current state.")
        return False
        
    elif choice == FeedbackChoice.OPTION_B:
        # Logic to map the specific question to a model update
        if "JSON" in payload.option_b_label:
            intent_model.update("format_preference", "json", "User selected JSON conversion")
        elif "depth" in payload.option_b_label:
            intent_model.update("target_audience", "expert", "User requested more depth")
        else:
            intent_model.update("general_preference", "revised", "Generic revision request")
        return True
        
    elif choice == FeedbackChoice.ESCALATE:
        logger.warning("User escalated issue. Flagging for human review.")
        return False
        
    return False

def validate_input_data(data: Dict[str, Any]) -> bool:
    """
    Helper Function: Validates input structure before processing.
    """
    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary.")
    if "step_id" not in data or "output_data" not in data:
        raise ValueError("Missing required fields: step_id, output_data")
    return True

# --- Main Execution Loop (Example) ---

def run_calibration_loop(
    execution_data: Dict[str, Any], 
    user_intent: IntentModel,
    mock_user_choice: FeedbackChoice = FeedbackChoice.OPTION_B
) -> Dict[str, Any]:
    """
    Orchestrates the full calibration cycle.
    
    Args:
        execution_data: Raw data from code execution.
        user_intent: The current user model.
        mock_user_choice: Simulates user input for the example.
        
    Returns:
        Updated report.
    """
    try:
        # 1. Validate Input
        validate_input_data(execution_data)
        
        # 2. Wrap in State Object
        state = ExecutionState(
            step_id=execution_data["step_id"],
            description=execution_data.get("description", ""),
            output_data=execution_data["output_data"]
        )
        
        # 3. Analyze
        deviation, confidence, key = analyze_execution_deviation(state, user_intent)
        state.detected_deviation = deviation
        state.confidence_score = confidence
        
        # 4. Check if interaction is needed
        if state.is_problematic():
            payload = generate_calibration_interaction(deviation, key, state)
            
            if payload:
                print(f"\n>>> SYSTEM INTERACTION: {payload.question}")
                print(f">>> [A] {payload.option_a_label}")
                print(f">>> [B] {payload.option_b_label}")
                
                # Simulating User Interaction
                print(f">>> USER INPUT (Simulated): {mock_user_choice.value}")
                
                # 5. Update Model
                updated = apply_feedback_to_model(mock_user_choice, payload, user_intent, key or "generic")
                
                return {
                    "status": "calibrated",
                    "model_updated": updated,
                    "new_preferences": user_intent.user_preferences
                }
        
        return {
            "status": "success",
            "model_updated": False,
            "message": "Execution aligned with intent."
        }
        
    except Exception as e:
        logger.error(f"Critical failure in calibration loop: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Example Usage
    
    # 1. Initialize Intent Model
    user_model = IntentModel()
    
    # 2. Simulate Code Execution Result (Deviation: Format is XML, Model expects JSON)
    execution_result = {
        "step_id": "exec_1024",
        "description": "Data export task",
        "output_data": {
            "format": "xml",  # Mismatch with intent model (json)
            "content": "<data>value</data>",
            "complexity": 3
        }
    }
    
    print("--- Starting Symbiosis Loop ---")
    result = run_calibration_loop(execution_result, user_model, mock_user_choice=FeedbackChoice.OPTION_B)
    
    print("\n--- Final Report ---")
    print(json.dumps(result, indent=2))