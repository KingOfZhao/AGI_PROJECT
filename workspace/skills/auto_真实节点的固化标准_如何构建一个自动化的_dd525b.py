"""
Module: epistemic_viscosity.py

This module implements an automated 'Truth Viscosity' assessment system for AGI knowledge nodes.
It quantifies the verification strength of a piece of knowledge based on its survival history
against falsification attempts (collision tests) and simulation consistency.

Domain: Epistemology / Bayesian Inference
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VerificationType(Enum):
    """Enumeration of verification environments."""
    SIMULATION = "simulation"
    REAL_API = "real_api"
    SYNTHETIC_ADVERSARIAL = "synthetic_adversarial"


@dataclass
class FalsificationAttempt:
    """Represents a single attempt to falsify a knowledge node."""
    timestamp: datetime
    severity: float  # 0.0 to 1.0 (severity of the test)
    environment: VerificationType
    passed: bool
    error_margin: float = 0.0  # Lower is better, implies precision
    
    def __post_init__(self):
        if not (0.0 <= self.severity <= 1.0):
            raise ValueError("Severity must be between 0.0 and 1.0.")
        if self.error_margin < 0.0:
            raise ValueError("Error margin cannot be negative.")


@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge in the AGI system.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge content (e.g., logic statement, embedding).
        initial_confidence: The prior probability/confidence (0.0 to 1.0).
        creation_time: Timestamp of creation.
        verification_history: List of falsification attempts.
    """
    id: str
    content: Any
    initial_confidence: float = 0.5
    creation_time: datetime = field(default_factory=datetime.now)
    verification_history: List[FalsificationAttempt] = field(default_factory=list)

    def __post_init__(self):
        if not (0.0 <= self.initial_confidence <= 1.0):
            raise ValueError("Initial confidence must be between 0.0 and 1.0.")


def _calculate_decay_factor(
    time_diff_seconds: float, 
    decay_rate: float = 0.0001
) -> float:
    """
    Auxiliary function: Calculate time-based decay of confidence.
    
    Knowledge that hasn't been tested recently becomes less 'viscous' (stale).
    Uses an exponential decay function.
    
    Args:
        time_diff_seconds: Time elapsed since last verification.
        decay_rate: The rate at which confidence decays over time.
        
    Returns:
        A multiplier between 0 and 1.
    """
    if time_diff_seconds < 0:
        logger.warning("Negative time difference detected, returning 1.0")
        return 1.0
    
    try:
        # Exponential decay: e^(-lambda * t)
        decay = math.exp(-decay_rate * time_diff_seconds)
        return max(0.0, min(1.0, decay))
    except OverflowError:
        logger.error("Overflow in decay calculation. Returning 0.")
        return 0.0


def calculate_bayesian_update(
    node: KnowledgeNode, 
    attempt: FalsificationAttempt
) -> float:
    """
    Core Function 1: Updates the confidence of a node based on a new test result.
    
    This implements a simplified Bayesian update mechanism.
    - If passed: Confidence increases, scaled by test severity and environment weight.
    - If failed: Confidence decreases significantly.
    
    Args:
        node: The knowledge node being tested.
        attempt: The result of the falsification attempt.
        
    Returns:
        The new calculated confidence score (posterior).
        
    Raises:
        ValueError: If inputs are invalid.
    """
    logger.info(f"Processing verification for Node {node.id} in {attempt.environment.value}")
    
    # Environment weights: Real API tests are worth more than simulations
    env_weights = {
        VerificationType.REAL_API: 1.0,
        VerificationType.SYNTHETIC_ADVERSARIAL: 0.8,
        VerificationType.SIMULATION: 0.5
    }
    
    weight = env_weights.get(attempt.environment, 0.1)
    prior = node.initial_confidence if not node.verification_history else node.verification_history[-1].severity # Simplified retrieval for demo
    
    # Get current confidence (This logic would usually be stored in the node state)
    # For this function, we calculate the *delta* or new value based on prior logic
    
    # Let's assume we treat the current state as the 'prior' for this step
    # Note: In a real system, the node would store its current_belief_score
    # Here we simulate the update logic.
    
    current_belief = node.initial_confidence # Simplification for stateless function logic
    
    if attempt.passed:
        # Likelihood ratio logic: 
        # Strong test passed -> Probability of Truth given Test Passed increases
        # P(Truth|Pass) = (P(Pass|Truth) * P(Truth)) / P(Pass)
        
        # Simplified heuristic for code demonstration:
        # Increase confidence proportionally to severity and weight
        increase = (1.0 - current_belief) * attempt.severity * weight
        new_confidence = current_belief + increase
        logger.debug(f"Test passed. Confidence boost: {increase:.4f}")
    else:
        # Falsification logic: 
        # If a severe test is failed, confidence drops drastically
        decrease = current_belief * attempt.severity * weight * 1.5 # Penalty multiplier
        new_confidence = current_belief - decrease
        logger.debug(f"Test failed. Confidence penalty: {decrease:.4f}")
    
    # Clamp values
    new_confidence = max(0.0001, min(0.9999, new_confidence))
    
    return new_confidence


def compute_truth_viscosity(node: KnowledgeNode) -> Dict[str, Any]:
    """
    Core Function 2: Computes the final 'Truth Viscosity' score for a node.
    
    Truth Viscosity represents the resistance of knowledge to change and its
    reliability. It aggregates historical survival data, time decay, and
    error margins.
    
    Formula (Conceptual):
    Viscosity = (Accumulated_Survival_Score * Precision_Factor) * Time_Decay
    
    Args:
        node: The knowledge node to evaluate.
        
    Returns:
        A dictionary containing:
        - 'viscosity_score': float (0.0 to 1.0)
        - 'status': str ('Solid', 'Liquid', 'Gas')
        - 'last_verified': Optional[datetime]
    """
    if not node.verification_history:
        logger.warning(f"Node {node.id} has no verification history. Returning base viscosity.")
        return {
            "viscosity_score": 0.0,
            "status": "Unverified",
            "last_verified": None
        }
    
    accumulated_score = 0.0
    total_weight = 0.0
    
    now = datetime.now()
    
    for attempt in node.verification_history:
        # 1. Calculate Time Relevance
        time_delta = (now - attempt.timestamp).total_seconds()
        time_relevance = _calculate_decay_factor(time_delta)
        
        # 2. Calculate Environment Weight
        env_weight = 1.0
        if attempt.environment == VerificationType.REAL_API:
            env_weight = 2.0
        elif attempt.environment == VerificationType.SYNTHETIC_ADVERSARIAL:
            env_weight = 1.5
        
        # 3. Survival Score
        survival_value = 1.0 if attempt.passed else -0.5 # Penalty for failure
        
        # 4. Error Margin Factor (Lower error = higher viscosity)
        precision_factor = 1.0 / (1.0 + attempt.error_margin)
        
        # Aggregate
        weighted_score = (
            survival_value * 
            attempt.severity * 
            env_weight * 
            time_relevance * 
            precision_factor
        )
        
        accumulated_score += weighted_score
        total_weight += (attempt.severity * env_weight)
    
    # Normalize Score
    if total_weight == 0:
        normalized_score = 0.0
    else:
        # Use sigmoid or simple normalization to keep it bounded
        # Here we use a simple bounded accumulation logic
        raw_viscosity = accumulated_score / total_weight
        # Normalize -1.0 to 1.0 range into 0.0 to 1.0
        normalized_score = (math.tanh(raw_viscosity) + 1) / 2
    
    # Determine State
    if normalized_score > 0.8:
        status = "Solid (Highly Reliable)"
    elif normalized_score > 0.4:
        status = "Liquid (Provisional)"
    else:
        status = "Gas (Speculative/Unreliable)"
        
    last_verified = max(node.verification_history, key=lambda x: x.timestamp).timestamp
    
    logger.info(f"Node {node.id} Viscosity: {normalized_score:.4f} ({status})")
    
    return {
        "viscosity_score": round(normalized_score, 4),
        "status": status,
        "last_verified": last_verified
    }


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Create a Knowledge Node
    node_id = "KN_001_Physics_Gravity"
    hypothesis = "Objects fall at 9.8 m/s^2 regardless of mass (in vacuum)"
    gravity_node = KnowledgeNode(
        id=node_id, 
        content=hypothesis, 
        initial_confidence=0.6
    )
    print(f"Created Node: {gravity_node.id}")

    # 2. Simulate Falsification Attempts (Collision)
    
    # Attempt 1: Basic Simulation
    sim_test = FalsificationAttempt(
        timestamp=datetime.now(),
        severity=0.5,
        environment=VerificationType.SIMULATION,
        passed=True,
        error_margin=0.01
    )
    gravity_node.verification_history.append(sim_test)
    
    # Attempt 2: Real World API Test (High Severity)
    real_test = FalsificationAttempt(
        timestamp=datetime.now(),
        severity=0.9,
        environment=VerificationType.REAL_API,
        passed=True,
        error_margin=0.001
    )
    gravity_node.verification_history.append(real_test)
    
    # Attempt 3: Adversarial Test (Edge Case)
    adv_test = FalsificationAttempt(
        timestamp=datetime.now(),
        severity=0.8,
        environment=VerificationType.SYNTHETIC_ADVERSARIAL,
        passed=True,
        error_margin=0.05
    )
    gravity_node.verification_history.append(adv_test)
    
    # 3. Compute Viscosity
    result = compute_truth_viscosity(gravity_node)
    
    print("\n--- Evaluation Results ---")
    print(f"Knowledge: {hypothesis}")
    print(f"Viscosity Score: {result['viscosity_score']}")
    print(f"Status: {result['status']}")
    print(f"Last Verified: {result['last_verified']}")
    
    # 4. Demonstrate Failure Case
    print("\n--- Simulating Failed Test ---")
    fail_test = FalsificationAttempt(
        timestamp=datetime.now(),
        severity=1.0, # Critical test
        environment=VerificationType.REAL_API,
        passed=False, # Falsified!
        error_margin=0.0
    )
    gravity_node.verification_history.append(fail_test)
    
    result_fail = compute_truth_viscosity(gravity_node)
    print(f"New Viscosity Score: {result_fail['viscosity_score']}")
    print(f"New Status: {result_fail['status']}")