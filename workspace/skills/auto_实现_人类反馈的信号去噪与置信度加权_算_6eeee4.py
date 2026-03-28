"""
Module: human_feedback_denoising.py
Description: Implements signal denoising and confidence weighting algorithms for Human-Computer Interaction.
             Designed for AGI systems to handle variable quality feedback from human experts by applying
             historical accuracy, domain relevance, and confidence-based arbitration.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackSignal(Enum):
    """Enumeration of possible feedback signal types."""
    CORRECT = 1
    INCORRECT = 0
    UNCERTAIN = -1
    ERROR = -2

@dataclass
class ExpertProfile:
    """
    Represents a human expert's profile and historical performance.
    
    Attributes:
        id: Unique identifier for the expert.
        domain_expertise: A dictionary mapping domains to expertise scores (0.0 to 1.0).
        historical_accuracy: Global accuracy based on past verified feedbacks (0.0 to 1.0).
        total_feedbacks: Total number of feedbacks provided to date.
    """
    id: str
    domain_expertise: Dict[str, float] = field(default_factory=dict)
    historical_accuracy: float = 0.5
    total_feedbacks: int = 0

    def update_accuracy(self, was_correct: bool) -> None:
        """Updates the expert's accuracy incrementally."""
        if was_correct:
            self.historical_accuracy = (self.historical_accuracy * self.total_feedbacks + 1) / (self.total_feedbacks + 1)
        else:
            self.historical_accuracy = (self.historical_accuracy * self.total_feedbacks) / (self.total_feedbacks + 1)
        self.total_feedbacks += 1

@dataclass
class Feedback:
    """
    Represents a single feedback instance.
    
    Attributes:
        expert_id: ID of the expert providing feedback.
        target_node_id: ID of the AGI knowledge node or action being feedbacked.
        signal: The feedback signal (e.g., CORRECT, ERROR).
        domain: The relevant domain for this feedback.
        confidence: The expert's self-reported confidence (0.0 to 1.0).
        timestamp: Time of feedback creation.
    """
    expert_id: str
    target_node_id: str
    signal: FeedbackSignal
    domain: str
    confidence: float
    timestamp: float

class FeedbackArbitrationError(Exception):
    """Custom exception for errors during the arbitration process."""
    pass

def _validate_input_bounds(value: float, name: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
    """
    Helper function to validate that a numeric input is within specific bounds.
    
    Args:
        value: The numeric value to check.
        name: The name of the variable (for error messages).
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
        
    Raises:
        ValueError: If value is out of bounds.
    """
    if not (min_val <= value <= max_val):
        logger.error(f"Validation Error: {name} must be between {min_val} and {max_val}. Got {value}.")
        raise ValueError(f"{name} must be between {min_val} and {max_val}.")

def calculate_expert_weight(expert: ExpertProfile, domain: str) -> float:
    """
    Core Function 1: Calculates the dynamic weight of an expert's feedback.
    
    The weight is a product of the expert's global historical accuracy and their
    specific expertise in the relevant domain.
    
    Args:
        expert: The ExpertProfile object.
        domain: The domain context of the current feedback.
        
    Returns:
        A float representing the weight (0.0 to 1.0+).
        
    Raises:
        ValueError: If profile data is invalid.
    """
    logger.debug(f"Calculating weight for expert {expert.id} in domain {domain}")
    
    # Data Validation
    _validate_input_bounds(expert.historical_accuracy, "historical_accuracy")
    
    # Get domain score, default to 0.1 (novice) if domain is unknown for this expert
    domain_score = expert.domain_expertise.get(domain, 0.1)
    _validate_input_bounds(domain_score, f"domain_expertise[{domain}]")

    # Weighting Algorithm: 
    # We prioritize domain expertise slightly higher if accuracy is high.
    # Weight = (Accuracy * 0.6) + (Domain_Match * 0.4) * Accuracy_Modifier
    # Simplified for robustness: Weight = Accuracy * (0.5 + 0.5 * Domain_Score)
    
    weight = expert.historical_accuracy * (0.5 + 0.5 * domain_score)
    
    logger.info(f"Expert {expert.id} calculated weight: {weight:.4f}")
    return weight

def process_feedback_signal(
    feedback: Feedback, 
    expert: ExpertProfile, 
    node_confidence: float
) -> Tuple[str, Optional[str]]:
    """
    Core Function 2: Processes a feedback signal to determine system action.
    
    Implements the denoising logic. If a feedback signal conflicts with a high-confidence
    system node but comes from a low-weight source, it triggers arbitration.
    
    Args:
        feedback: The Feedback object.
        expert: The profile of the expert giving feedback.
        node_confidence: The current confidence of the AGI system regarding the target node (0.0-1.0).
        
    Returns:
        A tuple (Action, Reason).
        Action can be: 'APPLY_FEEDBACK', 'IGNORE_NOISE', 'TRIGGER_ARBITRATION'.
        
    Raises:
        FeedbackArbitrationError: If inputs are invalid.
    """
    logger.info(f"Processing feedback {feedback.target_node_id} from {feedback.expert_id}")
    
    # 1. Input Validation
    try:
        _validate_input_bounds(node_confidence, "node_confidence")
        _validate_input_bounds(feedback.confidence, "feedback.confidence")
    except ValueError as e:
        raise FeedbackArbitrationError(f"Invalid input data: {e}")

    # 2. Calculate Source Credibility
    expert_weight = calculate_expert_weight(expert, feedback.domain)
    
    # 3. Denoising Logic
    # Thresholds
    HIGH_SYSTEM_THRESHOLD = 0.85
    LOW_EXPERT_THRESHOLD = 0.4
    
    action = "IGNORE_NOISE"
    reason = "Default state"

    # Case A: Feedback confirms the system (Positive Reinforcement)
    if feedback.signal == FeedbackSignal.CORRECT:
        action = "APPLY_FEEDBACK"
        reason = "Positive reinforcement accepted."
        logger.info(f"Feedback accepted: Reinforces node {feedback.target_node_id}")
        
    # Case B: Feedback marks system as 'ERROR'
    elif feedback.signal == FeedbackSignal.ERROR:
        # Scenario: High system confidence vs. Low Expert Weight
        if node_confidence > HIGH_SYSTEM_THRESHOLD and expert_weight < LOW_EXPERT_THRESHOLD:
            # Conflict Resolution: Do not modify directly, request arbitration
            action = "TRIGGER_ARBITRATION"
            reason = (f"Conflict detected: System Confidence ({node_confidence:.2f}) "
                      f"vs Low Expert Weight ({expert_weight:.2f}). Triggering arbitration.")
            logger.warning(f"Arbitration triggered for node {feedback.target_node_id}")
            
        # Scenario: Expert is highly credible or System is unsure
        elif expert_weight >= LOW_EXPERT_THRESHOLD or node_confidence <= HIGH_SYSTEM_THRESHOLD:
            action = "APPLY_FEEDBACK"
            reason = f"Credible error report received (Weight: {expert_weight:.2f})."
            logger.info(f"Feedback accepted: Correcting node {feedback.target_node_id}")
            
        else:
            action = "IGNORE_NOISE"
            reason = "Expert weight too low to overturn high system confidence."
            logger.info(f"Feedback ignored: Noise detected from {feedback.expert_id}")

    # Case C: Uncertainty
    else:
        action = "IGNORE_NOISE"
        reason = "Feedback signal is uncertain or not actionable."

    return action, reason

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Setup Expert Profiles
    expert_john = ExpertProfile(
        id="expert_001",
        domain_expertise={"physics": 0.9, "chemistry": 0.4},
        historical_accuracy=0.95
    )
    
    expert_novice = ExpertProfile(
        id="expert_002",
        domain_expertise={"physics": 0.2},
        historical_accuracy=0.55
    )
    
    # 2. Define System State
    # The AGI thinks a physics equation is correct with 98% certainty
    current_node_confidence = 0.98
    target_node = "node_phys_101"
    
    # 3. Scenario 1: High Expertise Expert challenges the node
    print("--- Scenario 1: Expert Challenge ---")
    feedback_pro = Feedback(
        expert_id="expert_001",
        target_node_id=target_node,
        signal=FeedbackSignal.ERROR,
        domain="physics",
        confidence=0.9,
        timestamp=1678900000
    )
    
    try:
        action, reason = process_feedback_signal(feedback_pro, expert_john, current_node_confidence)
        print(f"Action: {action}")
        print(f"Reason: {reason}")
    except FeedbackArbitrationError as e:
        print(f"Error: {e}")

    # 4. Scenario 2: Novice User challenges the same high-confidence node
    print("\n--- Scenario 2: Novice Noise / Conflict ---")
    feedback_novice = Feedback(
        expert_id="expert_002",
        target_node_id=target_node,
        signal=FeedbackSignal.ERROR,
        domain="physics",
        confidence=0.6,
        timestamp=1678900005
    )
    
    try:
        action, reason = process_feedback_signal(feedback_novice, expert_novice, current_node_confidence)
        print(f"Action: {action}")
        print(f"Reason: {reason}")
    except FeedbackArbitrationError as e:
        print(f"Error: {e}")