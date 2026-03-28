"""
Module: fuzzy_intent_quantifier.py

This module implements the 'Fuzzy Intent Quantification Interface' for Human-Computer
Symbiosis (HCS). It addresses the challenge of 'Implicit Knowledge' by monitoring
human behavioral signals—specifically hesitation dynamics and interaction latency—to
quantify ambiguous user intentions.

The system converts continuous, non-structured biological/behavioral feedback into
discrete, structured 'Pseudo-Nodes' (hypotheses) that can be validated by the AGI system.

Domain: Human-Computer Interaction (HCI) / Cognitive Computing
Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HCI_Symbiosis_Loop")


class IntentConfidence(Enum):
    """Classification of intent certainty levels."""
    SPECIFIC = 1.0      # Explicit command
    AMBIGUOUS = 0.6     # Needs clarification
    TACIT = 0.3         # Highly implicit, derived from behavior only
    NOISE = 0.0         # Unintentional input


@dataclass
class BehavioralSignal:
    """
    Input data container for human behavioral cues.
    
    Attributes:
        timestamp: Unix timestamp of the signal capture.
        cursor_velocity: Current speed of cursor movement (0.0 to 1.0 normalized).
        click_frequency: Clicks per second in the current session.
        pause_duration: Time elapsed since last significant action (seconds).
        eye_tracking_deviation: Variance in gaze focus (0.0 to 1.0, optional).
        bio_feedback: Placeholder for biological metrics (e.g., heart rate variability).
    """
    timestamp: float
    cursor_velocity: float = 0.0
    click_frequency: float = 0.0
    pause_duration: float = 0.0
    eye_tracking_deviation: Optional[float] = None
    bio_feedback: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """Validate data ranges after initialization."""
        if not (0.0 <= self.cursor_velocity <= 1.0):
            raise ValueError("cursor_velocity must be normalized between 0.0 and 1.0")
        if self.pause_duration < 0:
            raise ValueError("pause_duration cannot be negative")


@dataclass
class PseudoNode:
    """
    Output data structure representing a structured intent hypothesis.
    
    Attributes:
        node_id: Unique identifier for the hypothesis.
        intent_vector: A dictionary representing potential intent categories and their weights.
        entropy_score: A measure of uncertainty derived from the behavioral signal (0.0 to 1.0).
        confidence: The calculated confidence level (Enum).
        requires_validation: Flag indicating if the AGI needs to prompt the user.
        context_snapshot: Contextual data at the time of inference.
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_vector: Dict[str, float] = field(default_factory=dict)
    entropy_score: float = 0.0
    confidence: IntentConfidence = IntentConfidence.AMBIGUOUS
    requires_validation: bool = True
    context_snapshot: Dict[str, Any] = field(default_factory=dict)


class FuzzyIntentQuantifier:
    """
    Core engine for quantifying fuzzy human intent.
    
    This class monitors the 'Human' side of the symbiotic loop, analyzing
    hesitation and micro-behaviors to infer what the user wants before 
    they explicitly articulate it.
    """

    def __init__(self, 
                 hesitation_threshold: float = 1.5, 
                 entropy_alpha: float = 0.05,
                 window_size: int = 5):
        """
        Initialize the quantifier.
        
        Args:
            hesitation_threshold: Seconds of pause to consider as 'hesitation'.
            entropy_alpha: Smoothing factor for entropy calculation.
            window_size: Size of the sliding window for signal smoothing.
        """
        self.hesitation_threshold = hesitation_threshold
        self.entropy_alpha = entropy_alpha
        self.window_size = window_size
        self._signal_buffer: List[BehavioralSignal] = []
        logger.info("FuzzyIntentQuantifier initialized with threshold %.2f", hesitation_threshold)

    def _calculate_hesitation_index(self, signal: BehavioralSignal) -> float:
        """
        [Helper Function]
        Calculates a normalized 'Hesitation Index' based on behavioral inputs.
        
        Logic:
        - High pause duration increases hesitation.
        - Low cursor velocity (stopping) increases hesitation.
        - Erratic eye movement (if available) increases hesitation.
        
        Args:
            signal: The current behavioral signal.
            
        Returns:
            A float between 0.0 (confident) and 1.0 (highly hesitant).
        """
        try:
            # Time component
            time_score = min(signal.pause_duration / (self.hesitation_threshold * 2), 1.0)
            
            # Motor component (inverse of velocity)
            motor_score = 1.0 - signal.cursor_velocity
            
            # Weighted average
            hesitation_raw = (time_score * 0.6) + (motor_score * 0.4)
            
            # Add noise reduction / clamping
            return max(0.0, min(1.0, hesitation_raw))
            
        except Exception as e:
            logger.error("Error calculating hesitation index: %s", e)
            return 0.0

    def analyze_behavioral_stream(self, current_signal: BehavioralSignal) -> PseudoNode:
        """
        [Core Function 1]
        Processes the incoming behavioral stream to generate a PseudoNode.
        
        This function determines if the user is 'searching' for an action
        (high hesitation) or 'executing' an action (low hesitation).
        
        Args:
            current_signal: The latest captured behavioral data.
            
        Returns:
            A PseudoNode representing the quantified intent.
        """
        # Buffer management
        self._signal_buffer.append(current_signal)
        if len(self._signal_buffer) > self.window_size:
            self._signal_buffer.pop(0)

        hesitation_idx = self._calculate_hesitation_index(current_signal)
        
        # Determine Intent Entropy (Uncertainty)
        # High hesitation correlates with high entropy in intent
        entropy = hesitation_idx * 0.8 
        
        # Determine Confidence Level
        if hesitation_idx > 0.7:
            confidence = IntentConfidence.TACIT
            logger.debug("High hesitation detected: User is uncertain or searching.")
        elif hesitation_idx > 0.3:
            confidence = IntentConfidence.AMBIGUOUS
        else:
            confidence = IntentConfidence.SPECIFIC
            
        # Generate Intent Vector (Mock logic for demonstration)
        # In a real AGI, this would connect to a Knowledge Graph
        intent_vector = self._map_signal_to_intent_vector(current_signal, hesitation_idx)
        
        # Construct the PseudoNode
        node = PseudoNode(
            entropy_score=entropy,
            confidence=confidence,
            intent_vector=intent_vector,
            requires_validation=(confidence != IntentConfidence.SPECIFIC),
            context_snapshot={"hesitation_index": hesitation_idx, "source": "bio_behavioral"}
        )
        
        logger.info(f"Generated PseudoNode {node.node_id[:8]}... | Confidence: {confidence.name} | Entropy: {entropy:.2f}")
        return node

    def _map_signal_to_intent_vector(self, signal: BehavioralSignal, hesitation: float) -> Dict[str, float]:
        """
        [Internal Helper]
        Maps raw signals to potential intent categories.
        """
        # This is a placeholder for a semantic mapping algorithm.
        # For example, if pause is high near a specific UI element, intent maps to 'info_request'.
        
        vector = {
            "action.execute": 1.0 - hesitation,
            "action.explore": hesitation * 0.5,
            "action.abort": hesitation * 0.1
        }
        return vector

    def refine_intent_boundary(self, pseudo_node: PseudoNode, user_feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        [Core Function 2]
        Refines the boundary of the fuzzy intent based on explicit user feedback 
        or subsequent actions.
        
        This closes the symbiotic loop: The AGI asks for validation -> Human responds -> Boundary updates.
        
        Args:
            pseudo_node: The previously generated hypothesis.
            user_feedback: Optional explicit string feedback from the user.
            
        Returns:
            A structured dictionary defining the updated intent boundaries.
        """
        if pseudo_node.confidence == IntentConfidence.NOISE:
            return {"status": "discarded", "reason": "noise_detected"}

        refined_boundary = {
            "node_id": pseudo_node.node_id,
            "original_entropy": pseudo_node.entropy_score,
            "refined_scope": {},
            "status": "refining"
        }

        if user_feedback:
            logger.info("Received explicit feedback for node %s", pseudo_node.node_id)
            # Simulate NLP processing of feedback
            if "help" in user_feedback.lower():
                refined_boundary["refined_scope"]["type"] = "tutorial_request"
                refined_boundary["status"] = "confirmed"
            elif "cancel" in user_feedback.lower():
                refined_boundary["refined_scope"]["type"] = "cancel_operation"
                refined_boundary["status"] = "confirmed"
            else:
                refined_boundary["refined_scope"]["type"] = "complex_query"
                refined_boundary["status"] = "pending_clarification"
        else:
            # Implicit refinement based on subsequent action speed
            if pseudo_node.entropy_score < 0.2:
                refined_boundary["refined_scope"]["type"] = "direct_manipulation"
                refined_boundary["status"] = "auto_confirmed"
            else:
                refined_boundary["refined_scope"]["type"] = "unknown"
                # Recommend intervention
                refined_boundary["intervention_suggestion"] = "Did you mean to open the settings?"

        return refined_boundary

# -------------------------
# Usage Example
# -------------------------

if __name__ == "__main__":
    # Initialize the interface
    quantifier = FuzzyIntentQuantifier(hesitation_threshold=1.2)
    
    print("\n--- Scenario 1: Confident User (Low Hesitation) ---")
    # User moves mouse fast and clicks immediately
    confident_signal = BehavioralSignal(
        timestamp=time.time(),
        cursor_velocity=0.9,
        pause_duration=0.1
    )
    node_1 = quantifier.analyze_behavioral_stream(confident_signal)
    print(f"Output Node Confidence: {node_1.confidence.name}")
    print(f"Requires Validation: {node_1.requires_validation}")
    
    print("\n--- Scenario 2: Confused User (High Hesitation/Fuzzy Intent) ---")
    # User stops moving mouse, pauses for 2 seconds (thinking)
    hesitant_signal = BehavioralSignal(
        timestamp=time.time(),
        cursor_velocity=0.05,
        pause_duration=2.5,
        eye_tracking_deviation=0.8 # Looking around
    )
    node_2 = quantifier.analyze_behavioral_stream(hesitant_signal)
    print(f"Output Node Confidence: {node_2.confidence.name}")
    print(f"Intent Vector: {node_2.intent_vector}")
    
    # System attempts to refine the boundary
    print("\n--- Refining Scenario 2 via Symbiotic Loop ---")
    # The AGI detects high entropy and prompts the user (simulation)
    # User responds: "I need help with export"
    refinement = quantifier.refine_intent_boundary(node_2, user_feedback="How do I export this?")
    print(f"Refinement Result: {refinement}")