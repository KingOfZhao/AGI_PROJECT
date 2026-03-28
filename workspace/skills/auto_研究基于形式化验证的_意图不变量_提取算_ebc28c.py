"""
Module: auto_research_intent_invariant_extraction_ebc28c
Description: Advanced AGI skill module for researching and implementing intent invariant
             extraction algorithms based on formal verification, and real-time semantic
             drift measurement.

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class FormalContext:
    """Represents the state context for formal verification."""
    state_vector: List[float]
    constraints: List[str]

@dataclass
class SemanticVector:
    """Represents a high-dimensional semantic vector."""
    id: str
    values: List[float]

@dataclass
class Invariant:
    """Represents an extracted intent invariant."""
    invariant_id: str
    logic_expression: str
    confidence: float
    source_context: str

# --- Custom Exceptions ---

class InvariantExtractionError(Exception):
    """Custom exception for errors during invariant extraction."""
    pass

class DriftComputationError(Exception):
    """Custom exception for errors during semantic drift calculation."""
    pass

# --- Core Functions ---

def extract_intent_invariants(
    current_state: FormalContext,
    intent_specification: Dict[str, Any],
    threshold: float = 0.95
) -> List[Invariant]:
    """
    Extracts intent invariants from a given formal context using model checking concepts.
    
    This function simulates the process of identifying logical properties (invariants)
    that must hold true for the intent to be preserved during state transitions.

    Args:
        current_state (FormalContext): The current state of the system containing vectors and constraints.
        intent_specification (Dict[str, Any]): A dictionary describing the high-level goal.
        threshold (float): Confidence threshold for accepting an invariant (0.0 to 1.0).

    Returns:
        List[Invariant]: A list of verified intent invariants.

    Raises:
        InvariantExtractionError: If input validation fails or extraction logic encounters an error.
        ValueError: If threshold is out of bounds.
    """
    logger.info("Starting intent invariant extraction...")
    
    # Input Validation
    if not 0.0 <= threshold <= 1.0:
        logger.error(f"Invalid threshold value: {threshold}")
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    if not current_state.state_vector:
        logger.warning("Empty state vector provided.")
        return []

    try:
        extracted_invariants: List[Invariant] = []
        
        # Simulate Formal Verification Logic
        # In a real AGI system, this might interface with Z3, Coq, or internal logic solvers.
        # Here we simulate finding a property that holds across the state vector.
        
        state_sum = sum(current_state.state_vector)
        state_mean = state_sum / len(current_state.state_vector)
        
        # Generate a hypothetical invariant based on mean stability
        if state_mean > 0.5:
            logic_expr = f"MeanStateGeq({state_mean:.2f})"
            confidence = min(1.0, threshold + 0.05) # Simulated high confidence
            
            inv = Invariant(
                invariant_id=f"inv_{hash(logic_expr) % 10000}",
                logic_expression=logic_expr,
                confidence=confidence,
                source_context=intent_specification.get('description', 'general')
            )
            extracted_invariants.append(inv)
            logger.debug(f"Extracted candidate invariant: {logic_expr}")

        # Boundary check for results
        valid_invariants = [
            inv for inv in extracted_invariants 
            if _validate_invariant_structure(inv)
        ]

        logger.info(f"Successfully extracted {len(valid_invariants)} invariants.")
        return valid_invariants

    except Exception as e:
        logger.exception("Failed to extract invariants due to an unexpected error.")
        raise InvariantExtractionError(f"Extraction failed: {str(e)}")

def compute_semantic_drift(
    previous_state: SemanticVector,
    current_state: SemanticVector,
    reference_invariant: Optional[Invariant] = None
) -> float:
    """
    Computes the semantic drift between two states in real-time.
    
    This measures how far the current execution has deviated from the original
    semantic meaning or intent.

    Args:
        previous_state (SemanticVector): The semantic vector of the previous step.
        current_state (SemanticVector): The semantic vector of the current step.
        reference_invariant (Optional[Invariant]): An optional invariant to weigh the drift.

    Returns:
        float: A drift score between 0.0 (identical) and 1.0 (completely drifted/max distance).
               May exceed 1.0 if normalized differently, but here bounded [0, 1].

    Raises:
        DriftComputationError: If vectors have mismatched dimensions or invalid data.
    """
    logger.debug(f"Computing drift between state {previous_state.id} and {current_state.id}")

    # Data Validation
    if len(previous_state.values) != len(current_state.values):
        msg = "Vector dimension mismatch: cannot compute drift."
        logger.error(msg)
        raise DriftComputationError(msg)
    
    if not previous_state.values:
        return 0.0

    try:
        # Using Cosine Similarity to measure semantic alignment
        dot_product = sum(p * c for p, c in zip(previous_state.values, current_state.values))
        norm_p = math.sqrt(sum(p**2 for p in previous_state.values))
        norm_c = math.sqrt(sum(c**2 for c in current_state.values))

        if norm_p == 0 or norm_c == 0:
            logger.warning("Zero vector detected in drift computation.")
            return 1.0 # Max drift if one vector disappears

        cosine_sim = dot_product / (norm_p * norm_c)
        
        # Convert similarity [-1, 1] to distance/drift [0, 1]
        # Drift = 1 - ((Cosine + 1) / 2) or simpler 1 - Cosine for positive vectors
        # Here we assume semantic vectors are usually positive, but clamp for safety.
        drift = max(0.0, min(1.0, 1.0 - cosine_sim))

        # Apply invariant weighting if present (simulated penalty)
        if reference_invariant and reference_invariant.confidence < 0.8:
            # If invariant is weak, we penalize drift less (trust the change more)
            # Or conversely, if invariant is strong, small drifts are more significant.
            # Logic: Scale drift by confidence gap
            drift *= (1.0 + (1.0 - reference_invariant.confidence))

        logger.info(f"Computed semantic drift: {drift:.4f}")
        return drift

    except ZeroDivisionError:
        logger.error("Division by zero during drift calculation.")
        raise DriftComputationError("Calculation error: zero division.")
    except Exception as e:
        logger.exception("Unexpected error in drift computation.")
        raise DriftComputationError(str(e))

# --- Helper Functions ---

def _validate_invariant_structure(invariant: Invariant) -> bool:
    """
    Validates the internal structure of an Invariant object.
    
    Args:
        invariant (Invariant): The invariant to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(invariant, Invariant):
        return False
    if not invariant.invariant_id or not invariant.logic_expression:
        return False
    if not (0.0 <= invariant.confidence <= 1.0):
        return False
    return True

def _format_drift_report(drift_score: float, threshold: float = 0.15) -> str:
    """
    Formats a human-readable report based on the drift score.
    
    Args:
        drift_score (float): The calculated drift.
        threshold (float): The acceptable limit for drift.
        
    Returns:
        str: A formatted status string.
    """
    status = "NOMINAL" if drift_score <= threshold else "WARNING: DRIFT DETECTED"
    return f"[{status}] Current Drift: {drift_score:.4f} (Limit: {threshold})"

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Context
    state_data = [0.6, 0.8, 0.7, 0.9] # Example normalized state data
    context = FormalContext(state_vector=state_data, constraints=["safety_check"])
    intent = {"description": "Maintain system stability", "priority": 1}

    try:
        # 2. Extract Invariants
        invariants = extract_intent_invariants(context, intent)
        
        if invariants:
            print(f"Found Invariant: {invariants[0].logic_expression}")
            
            # 3. Simulate State Transition & Measure Drift
            prev_vec = SemanticVector(id="v1", values=[0.1, 0.2, 0.3, 0.4])
            curr_vec = SemanticVector(id="v2", values=[0.1, 0.21, 0.29, 0.4]) # Slight change
            
            drift = compute_semantic_drift(prev_vec, curr_vec, invariants[0])
            print(_format_drift_report(drift))
            
            # Simulate high drift
            high_drift_vec = SemanticVector(id="v3", values=[0.9, 0.8, 0.1, 0.0])
            drift_high = compute_semantic_drift(prev_vec, high_drift_vec)
            print(_format_drift_report(drift_high))

    except (InvariantExtractionError, DriftComputationError) as e:
        print(f"Operational Error: {e}")