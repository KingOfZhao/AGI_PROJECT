"""
Module: intention_alignment_calibration.py
Description: This module implements the 'Intention Alignment Calibration' skill for AGI systems
             within a Human-Computer Symbiosis context. It focuses on processing ambiguous or
             emotional human feedback, distinguishing between human bias and genuine system errors,
             and mapping non-structured feedback to specific parameter adjustments.

Domain: HCI (Human-Computer Interaction) / AGI
"""

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentionAlignment")


class FeedbackType(Enum):
    """Enumeration for categorized feedback types."""
    SYSTEM_ERROR = "system_error"
    HUMAN_BIAS = "human_bias"
    AMBIGUOUS = "ambiguous"
    VALID_ADJUSTMENT = "valid_adjustment"


class AlignmentError(Exception):
    """Custom exception for alignment calibration failures."""
    pass


@dataclass
class SystemState:
    """Represents the current state of the AGI system's specific node."""
    node_id: str
    confidence_score: float  # 0.0 to 1.0
    factual_grounding: float  # 0.0 to 1.0 (How much factual data supports this)
    parameters: Dict[str, Any]


@dataclass
class HumanFeedback:
    """Represents input from the human collaborator."""
    raw_text: str
    timestamp: float
    sentiment_score: float  # -1.0 (negative) to 1.0 (positive)
    context_tags: List[str]


class IntentionCalibrator:
    """
    Core class for calibrating human intentions and aligning them with system parameters.
    Handles the disambiguation of 'noisy' human feedback.
    """

    def __init__(self, error_threshold: float = 0.3, bias_detection_sensitivity: float = 0.7):
        """
        Initialize the calibrator.

        Args:
            error_threshold (float): The confidence level below which feedback is likely a system error.
            bias_detection_sensitivity (float): Threshold for sentiment volatility to detect bias.
        """
        self.error_threshold = error_threshold
        self.bias_detection_sensitivity = bias_detection_sensitivity
        logger.info("IntentionCalibrator initialized with thresholds.")

    def _clean_and_tokenize(self, text: str) -> List[str]:
        """
        Helper function to preprocess text feedback.
        Normalizes text and removes noise.
        """
        if not isinstance(text, str):
            raise AlignmentError("Input feedback must be a string.")
        
        # Basic normalization
        text = text.lower().strip()
        # Remove special characters but keep punctuation that might denote emotion (!?)
        text = re.sub(r'[^a-z0-9\s!?\']', '', text)
        tokens = text.split()
        logger.debug(f"Tokenized feedback: {tokens}")
        return tokens

    def _check_system_validity(self, system_state: SystemState) -> bool:
        """
        Helper to determine if the system node is objectively trustworthy.
        Returns True if the system is likely correct, False if likely erroneous.
        """
        # Logic: If confidence and factual grounding are high, the system is likely correct.
        is_valid = (system_state.confidence_score > self.error_threshold and 
                    system_state.factual_grounding > self.error_threshold)
        return is_valid

    def analyze_feedback_source(
        self, 
        feedback: HumanFeedback, 
        system_state: SystemState
    ) -> FeedbackType:
        """
        Distinguishes between 'Human Bias' and 'System Error'.
        
        Strategy:
        1. If System Confidence is LOW -> User is likely pointing out a SYSTEM_ERROR.
        2. If System Confidence is HIGH but User Sentiment is EXTREME NEGATIVE -> Potential HUMAN_BIAS.
        3. If specific trigger words exist (e.g., 'parameters', 'change') -> VALID_ADJUSTMENT.
        
        Args:
            feedback (HumanFeedback): The human input object.
            system_state (SystemState): The current state of the relevant node.
            
        Returns:
            FeedbackType: The classified category of the feedback.
        """
        logger.info(f"Analyzing feedback: '{feedback.raw_text}'")
        
        tokens = self._clean_and_tokenize(feedback.raw_text)
        system_is_reliable = self._check_system_validity(system_state)
        
        # Check for objective system failure first
        if not system_is_reliable:
            logger.warning("System state is unreliable. Classifying feedback as SYSTEM_ERROR.")
            return FeedbackType.SYSTEM_ERROR

        # Check for emotional volatility vs factual critique
        # If sentiment is very negative but system is reliable, check for bias indicators
        if feedback.sentiment_score < -0.5:
            # Simple heuristic: Does the feedback contain specific technical critique?
            technical_keywords = {'data', 'logic', 'format', 'parameter', 'value', 'incorrect'}
            if not set(tokens).intersection(technical_keywords):
                logger.info("High emotion, low technical specificity. Classifying as HUMAN_BIAS.")
                return FeedbackType.HUMAN_BIAS
        
        # Default to valid adjustment if it looks constructive
        return FeedbackType.VALID_ADJUSTMENT

    def map_feedback_to_parameters(
        self, 
        feedback: HumanFeedback, 
        feedback_type: FeedbackType,
        current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Maps non-structured feedback to specific parameter adjustments.
        
        Args:
            feedback (HumanFeedback): The raw feedback.
            feedback_type (FeedbackType): The classified type of feedback.
            current_params (Dict): The current parameter set of the node.
            
        Returns:
            Dict[str, Any]: The updated parameter set.
            
        Raises:
            AlignmentError: If mapping fails or data is invalid.
        """
        if feedback_type == FeedbackType.HUMAN_BIAS:
            logger.info("Feedback identified as bias. No parameter changes applied.")
            return current_params

        if feedback_type == FeedbackType.SYSTEM_ERROR:
            logger.info("System error acknowledged. Triggering fallback parameters.")
            # Example logic: Reset to safe defaults or reduce weights
            return {"weight": 0.0, "status": "needs_review"}

        # Attempt to parse specific instructions from natural language
        # e.g., "Make it stricter" -> increase threshold
        tokens = self._clean_and_tokenize(feedback.raw_text)
        updated_params = current_params.copy()

        if 'stricter' in tokens or 'conservative' in tokens:
            if 'threshold' in updated_params:
                old_val = updated_params['threshold']
                updated_params['threshold'] = min(1.0, old_val + 0.1)
                logger.info(f"Adjusted 'threshold' from {old_val} to {updated_params['threshold']}")

        elif 'relax' in tokens or 'looser' in tokens:
            if 'threshold' in updated_params:
                old_val = updated_params['threshold']
                updated_params['threshold'] = max(0.0, old_val - 0.1)
                logger.info(f"Adjusted 'threshold' from {old_val} to {updated_params['threshold']}")
        
        else:
            # Generic ambiguous handling
            logger.warning("Ambiguous instructions received. Flagging for clarification.")
            updated_params['pending_clarification'] = True

        return updated_params

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup System State and Calibrator
    node_state = SystemState(
        node_id="decision_node_42",
        confidence_score=0.95,  # High confidence implies system thinks it is right
        factual_grounding=0.90,
        parameters={"threshold": 0.5, "mode": "auto"}
    )
    
    calibrator = IntentionCalibrator()

    # Scenario A: Human Bias (Emotional rejection of a correct fact)
    # Human says "This is garbage!" but system is 95% sure.
    print("\n--- Scenario A: Potential Bias ---")
    human_input_biased = HumanFeedback(
        raw_text="This is total garbage!",
        timestamp=1678900000,
        sentiment_score=-0.9, # Very negative
        context_tags=["review"]
    )
    
    f_type = calibrator.analyze_feedback_source(human_input_biased, node_state)
    print(f"Detected Type: {f_type.value}")
    
    new_params = calibrator.map_feedback_to_parameters(human_input_input, f_type, node_state.parameters)
    print(f"Updated Params: {new_params}")

    # Scenario B: System Error Detection
    # System is failing (low confidence), Human says "It's wrong".
    print("\n--- Scenario B: System Error ---")
    failing_node = SystemState(
        node_id="vision_node_12",
        confidence_score=0.15, # Low confidence
        factual_grounding=0.20,
        parameters={"threshold": 0.5}
    )
    human_input_error = HumanFeedback(
        raw_text="This doesn't look right.",
        timestamp=1678900001,
        sentiment_score=-0.4,
        context_tags=["debug"]
    )
    
    f_type_error = calibrator.analyze_feedback_source(human_input_error, failing_node)
    print(f"Detected Type: {f_type_error.value}")
    
    new_params_error = calibrator.map_feedback_to_parameters(human_input_error, f_type_error, failing_node.parameters)
    print(f"Updated Params: {new_params_error}")