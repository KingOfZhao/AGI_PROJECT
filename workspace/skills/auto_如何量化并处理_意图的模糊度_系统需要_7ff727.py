"""
Module: auto_如何量化并处理_意图的模糊度_系统需要_7ff727

This module provides a robust framework for quantifying the ambiguity of user intents
in AGI systems. It calculates a scalar score (0-1) representing the clarity of input
and determines whether the system has sufficient information to generate deterministic
code. If the ambiguity exceeds a specified threshold, it triggers a clarification
subprocess instead of hallucinating code.

Classes:
    IntentContext: Data structure holding context features.
    AmbiguityQuantifier: Core engine for scoring intent ambiguity.

Functions:
    calculate_feature_weights: Helper to normalize and validate weights.
    trigger_clarification_protocol: Action to handle high-ambiguity scenarios.

Author: Senior Python Engineer
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_AMBIGUITY_THRESHOLD = 0.35
EPSILON = 1e-6  # To prevent division by zero

@dataclass
class IntentContext:
    """
    Represents the parsed features of a user input used for ambiguity calculation.
    
    Attributes:
        entities_identified: Number of distinct entities (variables, objects) found.
        action_verbs: Number of action verbs identified.
        missing_parameters: Count of parameters required by the identified intent but missing in input.
        linguistic_complexity: Syntactic complexity score (0.0 to 1.0, higher means more complex/confusing).
        domain_specificity: How specific the domain terms are (0.0 generic to 1.0 specific).
        referential_ambiguity: Score (0.0 to 1.0) indicating unclear references (e.g., "it", "that").
    """
    entities_identified: int = 0
    action_verbs: int = 0
    missing_parameters: int = 0
    linguistic_complexity: float = 0.0
    domain_specificity: float = 0.5  # Default to neutral
    referential_ambiguity: float = 0.0

    def __post_init__(self):
        """Validate data types and ranges after initialization."""
        if not isinstance(self.entities_identified, int) or self.entities_identified < 0:
            raise ValueError("entities_identified must be a non-negative integer")
        if not (0.0 <= self.linguistic_complexity <= 1.0):
            raise ValueError("linguistic_complexity must be between 0 and 1")
        # Add other validations as needed


def calculate_feature_weights(features: Dict[str, float]) -> Dict[str, float]:
    """
    Helper function to normalize feature weights and ensure they sum to 1.0.
    
    Args:
        features: A dictionary mapping feature names to their raw importance weights.
        
    Returns:
        A dictionary with normalized weights.
        
    Raises:
        ValueError: If input contains negative weights or is empty.
    """
    if not features:
        raise ValueError("Feature dictionary cannot be empty")
    
    total = sum(features.values())
    if total <= 0:
        raise ValueError("Sum of weights must be positive")

    normalized = {k: v / total for k, v in features.items()}
    logger.debug(f"Weights normalized: {normalized}")
    return normalized


class AmbiguityQuantifier:
    """
    Core engine to calculate the ambiguity score of an intent.
    
    This class uses a weighted heuristic model to combine various linguistic 
    and semantic features into a single ambiguity scalar.
    """

    def __init__(self, 
                 threshold: float = DEFAULT_AMBIGUITY_THRESHOLD, 
                 custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialize the Quantifier.
        
        Args:
            threshold: The cutoff score (0-1). Above this, clarification is needed.
            custom_weights: Optional dict to override default feature weights.
        """
        self.threshold = self._validate_threshold(threshold)
        
        # Default weights (heuristic)
        self.weights = {
            'missing_params': 0.4,     # High impact
            'ref_ambiguity': 0.3,      # High impact
            'low_specificity': 0.15,   # Moderate impact
            'ling_complexity': 0.15    # Moderate impact
        }
        
        if custom_weights:
            try:
                self.weights = calculate_feature_weights(custom_weights)
            except ValueError as e:
                logger.error(f"Invalid custom weights provided: {e}. Using defaults.")

    @staticmethod
    def _validate_threshold(value: float) -> float:
        """Ensure threshold is strictly between 0 and 1."""
        if not (0.0 < value < 1.0):
            raise ValueError("Threshold must be strictly between 0.0 and 1.0")
        return value

    def compute_ambiguity_score(self, context: IntentContext) -> float:
        """
        Computes the scalar ambiguity score based on the IntentContext.
        
        The scoring logic:
        - More missing parameters increase ambiguity.
        - Higher referential ambiguity increases score.
        - Lower domain specificity (more generic) increases ambiguity.
        - Higher linguistic complexity increases ambiguity.
        
        Args:
            context: The IntentContext object containing parsed features.
            
        Returns:
            float: A score between 0.0 (Clear) and 1.0 (Totally Ambiguous).
        """
        logger.info("Computing ambiguity score...")
        
        # 1. Missing Parameters Component (Normalized sigmoid-like response)
        # If missing params > 0, significant penalty.
        miss_p = 1.0 - math.exp(-0.5 * context.missing_parameters)
        
        # 2. Referential Ambiguity Component
        ref_amb = context.referential_ambiguity
        
        # 3. Domain Specificity Component (Inverted: low specificity = high ambiguity)
        spec_score = 1.0 - context.domain_specificity
        
        # 4. Linguistic Complexity Component
        ling_score = context.linguistic_complexity
        
        # Weighted Sum
        score = (
            (self.weights['missing_params'] * miss_p) +
            (self.weights['ref_ambiguity'] * ref_amb) +
            (self.weights['low_specificity'] * spec_score) +
            (self.weights['ling_complexity'] * ling_score)
        )
        
        # Clamp result to [0, 1] strictly
        final_score = max(0.0, min(1.0, score))
        logger.info(f"Computed Ambiguity Score: {final_score:.4f}")
        return final_score

    def evaluate(self, context: IntentContext) -> Tuple[float, bool]:
        """
        Evaluates the context and decides if clarification is needed.
        
        Args:
            context: The context to evaluate.
            
        Returns:
            Tuple[float, bool]: (The ambiguity score, True if clarification needed else False).
        """
        score = self.compute_ambiguity_score(context)
        needs_clarification = score > self.threshold
        
        if needs_clarification:
            logger.warning(f"Ambiguity score {score:.4f} exceeds threshold {self.threshold}.")
        else:
            logger.info("Intent is clear enough for processing.")
            
        return score, needs_clarification


def trigger_clarification_protocol(score: float, context: IntentContext) -> str:
    """
    Action function: Generates a clarification question or prompt based on the ambiguity source.
    
    Args:
        score: The calculated ambiguity score.
        context: The context data causing the ambiguity.
        
    Returns:
        str: A human-readable clarification question.
    """
    logger.info("Triggering Clarification Protocol...")
    
    reasons = []
    if context.missing_parameters > 0:
        reasons.append(f"{context.missing_parameters} required parameters are missing")
    if context.referential_ambiguity > 0.5:
        reasons.append("References like 'it' or 'that' are unclear")
    if context.domain_specificity < 0.3:
        reasons.append("The request is too generic")
        
    reason_text = " and ".join(reasons) if reasons else "General ambiguity"
    
    # Simple template generation
    response = (
        f"System Analysis (Ambiguity Score: {score:.2f}): "
        f"I am uncertain about your request. Specifically: {reason_text}. "
        "Could you please provide more specific details?"
    )
    return response


# --- Usage Example ---
if __name__ == "__main__":
    # Example 1: Clear Intent
    clear_context = IntentContext(
        entities_identified=3,
        action_verbs=1,
        missing_parameters=0,
        domain_specificity=0.9,
        referential_ambiguity=0.0
    )

    # Example 2: Ambiguous Intent (e.g., "Make it better")
    vague_context = IntentContext(
        entities_identified=0,
        action_verbs=1,
        missing_parameters=2,  # e.g., target object, criteria for "better"
        domain_specificity=0.1,
        referential_ambiguity=0.8, # "it" is undefined
        linguistic_complexity=0.4
    )

    # Initialize system
    quantifier = AmbiguityQuantifier(threshold=0.35)

    # Process Clear Intent
    print("--- Processing Clear Intent ---")
    score_1, trigger_1 = quantifier.evaluate(clear_context)
    if trigger_1:
        print(trigger_clarification_protocol(score_1, clear_context))
    else:
        print(f"Code Generation Permitted. Score: {score_1:.4f}")

    # Process Vague Intent
    print("\n--- Processing Vague Intent ---")
    score_2, trigger_2 = quantifier.evaluate(vague_context)
    if trigger_2:
        print(trigger_clarification_protocol(score_2, vague_context))
    else:
        print(f"Code Generation Permitted. Score: {score_2:.4f}")