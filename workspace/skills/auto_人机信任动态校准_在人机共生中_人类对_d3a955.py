"""
Module: auto_human_ai_trust_calibration_d3a955
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
Domain: Behavioral Economics / Human-Computer Interaction

Description:
    This module implements a 'Trust Dashboard' for Human-Machine Symbiosis.
    It dynamically calibrates the 'aggressiveness' of AI suggestions based on
    a Bayesian-updated trust score derived from historical user feedback.
    
    Core Logic:
    1.  Track user feedback (Accept/Reject) regarding AI suggestions.
    2.  Calculate a dynamic 'Trust Score' using a decay-weighted success rate.
    3.  Adjust the 'AI Personality Mode':
        - High Trust: AI provides direct, actionable conclusions (Aggressive).
        - Medium Trust: AI provides analysis with hedging.
        - Low Trust: AI acts as a passive data assistant (Conservative).
    
    Input Format:
        Feedback History: List[Dict] e.g., [{'action': 'accept'}, {'action': 'reject'}]
        Current AI Confidence: float (0.0 to 1.0)
        
    Output Format:
        Dict containing 'trust_score', 'suggestion_mode', and 'response_payload'.
"""

import logging
import math
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SuggestionMode(Enum):
    """Enumeration of AI behavioral modes based on trust levels."""
    CONSERVATIVE = "conservative"  # Low trust: Only provide raw data
    BALANCED = "balanced"          # Medium trust: Provide analysis with caveats
    AGGRESSIVE = "aggressive"      # High trust: Provide direct conclusions

class TrustCalibrationError(Exception):
    """Custom exception for trust calibration errors."""
    pass

def _validate_feedback_history(history: List[Dict[str, str]]) -> bool:
    """
    Helper function to validate the integrity of the feedback history data.
    
    Args:
        history: A list of dictionaries containing user feedback.
        
    Returns:
        bool: True if valid.
        
    Raises:
        TrustCalibrationError: If data format is invalid.
    """
    if not isinstance(history, list):
        raise TrustCalibrationError("Feedback history must be a list.")
    
    valid_actions = {"accept", "reject", "ignore"}
    
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            raise TrustCalibrationError(f"Entry {i} is not a dictionary.")
        if "action" not in entry:
            raise TrustCalibrationError(f"Entry {i} missing 'action' key.")
        if entry["action"] not in valid_actions:
            raise TrustCalibrationError(
                f"Entry {i} has invalid action '{entry['action']}'. "
                f"Valid actions: {valid_actions}"
            )
    return True

def calculate_dynamic_trust_score(
    feedback_history: List[Dict[str, str]],
    decay_factor: float = 0.95,
    prior_trust: float = 0.5
) -> float:
    """
    Calculates a time-decayed trust score based on user feedback history.
    
    Recent interactions have a higher weight than older ones. This mimics
    human memory and adaptability in behavioral economics (recency bias).
    
    Args:
        feedback_history: List of feedback dicts with key 'action'.
                         'accept' increases trust, 'reject'/'ignore' decreases.
        decay_factor: Weight multiplier for older entries (0 < x < 1).
        prior_trust: Initial trust score before any data (0.0 to 1.0).
        
    Returns:
        float: The calibrated trust score between 0.0 and 1.0.
        
    Raises:
        TrustCalibrationError: If inputs are out of bounds or invalid.
    """
    logger.info("Calculating dynamic trust score...")
    
    # Input Validation
    if not 0.0 <= prior_trust <= 1.0:
        raise TrustCalibrationError("Prior trust must be between 0.0 and 1.0.")
    if not 0.0 < decay_factor < 1.0:
        raise TrustCalibrationError("Decay factor must be between 0.0 and 1.0 (exclusive).")
    
    try:
        _validate_feedback_history(feedback_history)
    except TrustCalibrationError as e:
        logger.error(f"Data validation failed: {e}")
        raise

    if not feedback_history:
        logger.warning("Empty history provided. Returning prior trust.")
        return prior_trust

    # Calculate Weighted Score
    # We treat 'accept' as 1, others as 0.
    weighted_sum = 0.0
    total_weight = 0.0
    current_weight = 1.0
    
    # Iterate from most recent to oldest (assuming history is chronological)
    # We reverse it to process recent first with highest weight, or process linear
    # with decreasing weight. Let's process linear (older -> newer) accumulating weight.
    
    # Actually, recency bias means recent items should have MORE impact.
    # Let's use a cumulative approach where the score updates iteratively.
    
    current_score = prior_trust
    alpha = 0.3  # Learning rate / smoothing factor for exponential moving average
    
    for entry in feedback_history:
        outcome = 1.0 if entry['action'] == 'accept' else 0.0
        # Simple Exponential Smoothing equivalent for trust
        current_score = (outcome * alpha) + (current_score * (1 - alpha))
        
    final_score = current_score
    
    # Boundary check
    final_score = max(0.0, min(1.0, final_score))
    
    logger.info(f"Calculated Trust Score: {final_score:.4f}")
    return final_score

def get_ai_response_strategy(
    trust_score: float,
    current_confidence: float,
    data_payload: Dict
) -> Dict:
    """
    Determines the AI's output modality based on trust and current confidence.
    
    Strategy Logic:
    1. High Trust + High Confidence -> AGGRESSIVE mode (Direct Answer).
    2. Low Trust + High Confidence -> BALANCED mode (Strong Suggestion + Source).
    3. Any Low Confidence -> CONSERVATIVE mode (Data only).
    
    Args:
        trust_score: The calculated trust score (0.0-1.0).
        current_confidence: The AI model's internal confidence for the current task (0.0-1.0).
        data_payload: The raw data or content the AI wants to present.
        
    Returns:
        Dict: A structured response containing:
            - 'mode': SuggestionMode enum
            - 'message': The formatted string for the user.
            - 'metadata': Debug info.
    """
    # Boundary checks
    trust_score = max(0.0, min(1.0, trust_score))
    current_confidence = max(0.0, min(1.0, current_confidence))
    
    mode = SuggestionMode.CONSERVATIVE
    response_prefix = ""
    
    try:
        # Decision Logic
        if current_confidence < 0.6:
            mode = SuggestionMode.CONSERVATIVE
            response_prefix = "The data suggests the following, but certainty is low:"
        elif trust_score > 0.75:
            mode = SuggestionMode.AGGRESSIVE
            if current_confidence > 0.9:
                response_prefix = "Based on analysis, the definitive course of action is:"
            else:
                mode = SuggestionMode.BALANCED # Downgrade if confidence isn't perfect
                response_prefix = "I recommend the following, though verification is advised:"
        elif trust_score > 0.4:
            mode = SuggestionMode.BALANCED
            response_prefix = "Here is an analysis based on the parameters:"
        else:
            mode = SuggestionMode.CONSERVATIVE
            response_prefix = "For your review, here is the raw data analysis. Please decide:"
            
        # Construct Payload
        output = {
            "mode": mode.value,
            "message": f"{response_prefix} {str(data_payload.get('summary', 'No data'))}",
            "metadata": {
                "trust_score": trust_score,
                "internal_confidence": current_confidence,
                "explanation": f"Mode set to {mode.value} due to trust/tradeoff logic."
            }
        }
        
        logger.debug(f"Strategy selected: {mode.value} for Trust: {trust_score}, Conf: {current_confidence}")
        return output

    except Exception as e:
        logger.critical(f"Critical error in strategy generation: {e}")
        return {
            "mode": "error",
            "message": "Unable to generate suggestion due to internal error.",
            "metadata": {}
        }

class TrustManager:
    """
    Main class wrapper to maintain state (if needed) and encapsulate the logic.
    """
    def __init__(self, initial_history: List[Dict] = None):
        self._history = initial_history if initial_history else []
        
    def record_feedback(self, action: str):
        """Record a new user interaction."""
        if action not in ["accept", "reject", "ignore"]:
            raise ValueError("Invalid action type.")
        self._history.append({"action": action})
        
    def generate_dashboard_report(self, current_confidence: float, payload: Dict) -> Dict:
        """
        High-level method to generate the full response package.
        """
        score = calculate_dynamic_trust_score(self._history)
        return get_ai_response_strategy(score, current_confidence, payload)

# Usage Example
if __name__ == "__main__":
    # Simulate a history of interactions where AI performed poorly at first, then improved
    mock_history = [
        {"action": "reject"}, # User unhappy
        {"action": "reject"}, # User unhappy
        {"action": "ignore"}, # User ignoring AI
        {"action": "accept"}, # AI starts doing better
        {"action": "accept"}, # Trust building
        {"action": "accept"}, # Trust building
        {"action": "accept"}  # High trust
    ]
    
    print("--- Initializing Trust Calibration System ---")
    
    try:
        # 1. Calculate Trust
        trust = calculate_dynamic_trust_score(mock_history)
        print(f"Current Trust Score: {trust:.2f}")
        
        # 2. Determine Strategy (High Confidence Case)
        print("\n--- Scenario A: High Confidence (0.95) ---")
        strategy_a = get_ai_response_strategy(
            trust_score=trust,
            current_confidence=0.95,
            data_payload={"summary": "Deploy system update v2.4."}
        )
        print(f"Mode: {strategy_a['mode']}")
        print(f"User Message: {strategy_a['message']}")
        
        # 3. Determine Strategy (Low Trust / High Confidence Mismatch)
        print("\n--- Scenario B: Low Confidence (0.50) ---")
        strategy_b = get_ai_response_strategy(
            trust_score=trust,
            current_confidence=0.50,
            data_payload={"summary": "Anomaly detected in sector 7."}
        )
        print(f"Mode: {strategy_b['mode']}")
        print(f"User Message: {strategy_b['message']}")

        # 4. Class Usage
        print("\n--- Scenario C: Using Class Wrapper ---")
        tm = TrustManager()
        tm.record_feedback("accept")
        tm.record_feedback("accept")
        # AI is unsure
        report = tm.generate_dashboard_report(0.6, {"summary": "Stock trend is upward."})
        print(f"Result: {report}")

    except TrustCalibrationError as e:
        print(f"Application Error: {e}")