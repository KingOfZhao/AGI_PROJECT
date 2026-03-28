"""
Module: implicit_concept_solidification.py

This module implements the 'Concept Solidification' protocol for Human-Computer Symbiosis.
It translates implicit human feedback (emotional valence, hesitation time, correction amplitude)
into quantifiable parameter adjustments for AGI skill nodes.

The core logic follows the equation:
    Update_Signal = (Valence_Factor) * (Hesitation_Scale) * (Correction_Scale)

Author: AGI System Core Team
Version: 3f24df.1.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackSentiment(Enum):
    """Enumeration for implicit feedback sentiment categories."""
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1


@dataclass
class ImplicitFeedbackSignal:
    """
    Data structure representing a single unit of implicit human feedback.

    Attributes:
        node_id: The identifier of the SKILL node being interacted with.
        hesitation_ms: Time in milliseconds the user took before making a decision.
        correction_delta: The magnitude of change made by the user (0.0 to 1.0).
        biometric_valence: Emotional state indicator (-1.0 negative to 1.0 positive).
        timestamp: Unix timestamp of the event.
    """
    node_id: str
    hesitation_ms: float
    correction_delta: float
    biometric_valence: float
    timestamp: float


@dataclass
class SkillNode:
    """
    Represents a node in the AGI Skill Graph.
    
    Attributes:
        node_id: Unique identifier.
        weight: The current confidence or importance weight (0.0 to 1.0).
        bias: A bias term adjusted by user preference.
        version: Version control for the node.
    """
    node_id: str
    weight: float = 0.5
    bias: float = 0.0
    version: int = 1


class ConceptSolidificationProtocol:
    """
    Handles the transformation of implicit feedback into node updates.
    """

    def __init__(self, 
                 hesitation_threshold_ms: float = 2000.0, 
                 learning_rate: float = 0.1,
                 max_nodes: int = 1000):
        """
        Initialize the protocol.
        
        Args:
            hesitation_threshold_ms: Threshold above which hesitation indicates confusion.
            learning_rate: The step size for gradient updates.
            max_nodes: Maximum capacity of the skill node registry.
        """
        self.hesitation_threshold = hesitation_threshold_ms
        self.learning_rate = learning_rate
        self.max_nodes = max_nodes
        self._node_registry: Dict[str, SkillNode] = {}
        logger.info("ConceptSolidificationProtocol initialized with LR: %s", learning_rate)

    def _validate_signal(self, signal: ImplicitFeedbackSignal) -> bool:
        """
        Validate input data boundaries and integrity.
        
        Args:
            signal: The feedback signal to validate.
            
        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not signal.node_id:
            raise ValueError("Signal missing node_id")
        if signal.hesitation_ms < 0:
            raise ValueError("Hesitation time cannot be negative")
        if not (0.0 <= signal.correction_delta <= 1.0):
            raise ValueError(f"Correction delta {signal.correction_delta} out of bounds [0, 1]")
        if not (-1.0 <= signal.biometric_valence <= 1.0):
            raise ValueError(f"Biometric valence {signal.biometric_valence} out of bounds [-1, 1]")
        
        logger.debug("Signal for node %s validated successfully.", signal.node_id)
        return True

    def _calculate_hesitation_factor(self, hesitation_ms: float) -> float:
        """
        Helper function to map hesitation time to a cognitive load factor.
        High hesitation often implies confusion or deep thought (negative or exploratory signal).
        
        Args:
            hesitation_ms: Hesitation time in milliseconds.
            
        Returns:
            A normalized factor between 0.5 and 1.5.
        """
        # Sigmoid-like normalization based on threshold
        normalized = hesitation_ms / self.hesitation_threshold
        # If hesitation is high, we increase the impact magnitude (uncertainty)
        # Cap the factor to prevent explosion
        factor = 1.0 + (math.tanh(normalized - 1.0) * 0.5)
        return min(max(factor, 0.5), 1.5)

    def process_implicit_feedback(self, 
                                  signals: List[ImplicitFeedbackSignal], 
                                  apply_update: bool = True) -> Dict[str, float]:
        """
        Core Function 1: Processes a batch of implicit signals and calculates update gradients.
        
        This function aggregates fuzzy human inputs into precise parameter shifts.
        
        Args:
            signals: List of implicit feedback signals.
            apply_update: Whether to immediately apply changes to the registry.
            
        Returns:
            A dictionary mapping node_ids to their calculated weight adjustment delta.
            
        Raises:
            ValueError: If input data is invalid.
            RuntimeError: If internal processing fails.
        """
        update_deltas: Dict[str, float] = {}
        
        logger.info("Processing batch of %d implicit signals...", len(signals))
        
        for signal in signals:
            try:
                self._validate_signal(signal)
                
                # 1. Analyze Hesitation (Confusion/Confidence indicator)
                h_factor = self._calculate_hesitation_factor(signal.hesitation_ms)
                
                # 2. Analyze Correction (Explicit error signal implicit in magnitude)
                # If user corrects heavily (high delta), the node weight should decrease (negative feedback)
                correction_signal = -signal.correction_delta
                
                # 3. Analyze Emotion (Valence)
                # Negative valence reinforces the negative update, positive valence mitigates it
                valence_weight = signal.biometric_valence
                
                # 4. Combined Gradient Calculation
                # Formula: ΔW = LR * (Valence * 0.2 + Correction * Hesitation_Factor)
                # Note: We weight correction heavily if hesitation is high (confused correction)
                raw_gradient = (valence_weight * 0.2) + (correction_signal * h_factor)
                delta = self.learning_rate * raw_gradient
                
                update_deltas[signal.node_id] = delta
                
                if apply_update:
                    self._update_node(signal.node_id, delta)
                    
            except ValueError as ve:
                logger.warning("Skipping invalid signal: %s", ve)
                continue
            except Exception as e:
                logger.error("Critical error processing signal for %s: %s", signal.node_id, e)
                raise RuntimeError("Processing pipeline failure") from e
                
        return update_deltas

    def _update_node(self, node_id: str, delta: float) -> None:
        """
        Internal helper to apply delta to the node registry with boundary checks.
        """
        if node_id not in self._node_registry:
            if len(self._node_registry) >= self.max_nodes:
                logger.error("Node registry full. Cannot add new node %s", node_id)
                return
            self._node_registry[node_id] = SkillNode(node_id=node_id)
            logger.info("Created new Skill Node: %s", node_id)
            
        node = self._node_registry[node_id]
        new_weight = node.weight + delta
        
        # Boundary Check [0.0, 1.0]
        if new_weight < 0.0:
            new_weight = 0.0
            logger.warning("Weight for node %s hit lower bound.", node_id)
        elif new_weight > 1.0:
            new_weight = 1.0
            logger.warning("Weight for node %s hit upper bound.", node_id)
            
        # Check for significant drift
        if abs(delta) > 0.05:
            logger.info("Significant concept drift detected for node %s. Version bumping.", node_id)
            node.version += 1
            
        node.weight = new_weight
        logger.debug("Updated node %s: Weight=%.4f (Delta=%.4f)", node_id, new_weight, delta)

    def get_solidified_nodes(self, threshold: float = 0.0) -> List[SkillNode]:
        """
        Core Function 2: Retrieves nodes that have been 'solidified' or updated 
        based on the processed feedback.
        
        Args:
            threshold: Minimum weight for a node to be considered relevant.
            
        Returns:
            List of SkillNode objects meeting the criteria.
        """
        solidified = [
            node for node in self._node_registry.values() 
            if node.weight >= threshold
        ]
        logger.info("Retrieved %d nodes above threshold %.2f", len(solidified), threshold)
        return solidified


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize the Protocol
    protocol = ConceptSolidificationProtocol(learning_rate=0.15)
    
    # 2. Simulate Implicit Feedback Data
    # Scenario: User is frustrated (valence -0.8), took a long time (3000ms), 
    # and made a large correction (0.9) to a specific AI output.
    feedback_data = [
        ImplicitFeedbackSignal(
            node_id="skill_gen_creative_writing_01",
            hesitation_ms=3000.0,
            correction_delta=0.9,
            biometric_valence=-0.8,
            timestamp=1678900000.0
        ),
        ImplicitFeedbackSignal(
            node_id="skill_gen_code_refactor_02",
            hesitation_ms=500.0,  # Quick decision
            correction_delta=0.1, # Small correction
            biometric_valence=0.5, # Positive mood
            timestamp=1678900005.0
        )
    ]
    
    # 3. Process Feedback
    print("--- Processing Implicit Feedback ---")
    deltas = protocol.process_implicit_feedback(feedback_data)
    print(f"Calculated Deltas: {deltas}")
    
    # 4. Retrieve Updated Nodes
    print("\n--- Solidified Nodes ---")
    nodes = protocol.get_solidified_nodes()
    for n in nodes:
        print(f"Node: {n.node_id} | Weight: {n.weight:.4f} | Version: {n.version}")