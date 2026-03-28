"""
Module: auto_自上而下与自下而上的收敛验证_自上而_c7a00e
Description: Implements dynamic confidence calibration for verifying the convergence
             between top-down goal decomposition and bottom-up data induction.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    """
    Data structure to hold the outcome of the convergence verification.
    
    Attributes:
        is_converged (bool): True if goals and data align within error tolerance.
        error_score (float): The quantitative difference between target and actual.
        confidence (float): System confidence in the result (0.0 to 1.0).
        verdict (str): 'VERIFIED', 'GOAL_REJECTED', or 'DATA_INSUFFICIENT'.
        message (str): Detailed explanation of the verdict.
    """
    is_converged: bool
    error_score: float
    confidence: float
    verdict: str
    message: str

@dataclass
class SystemState:
    """
    Represents the current state of the AGI reasoning process.
    
    Attributes:
        target_vector (List[float]): The vector representing the top-down goal.
        data_vector (List[float]): The vector representing bottom-up evidence.
        history_variance (List[float]): Historical error rates for calibration.
        required_precision (float): The threshold for acceptable error.
    """
    target_vector: List[float]
    data_vector: List[float]
    history_variance: List[float] = field(default_factory=list)
    required_precision: float = 0.05  # Default 5% error margin

def _calculate_euclidean_distance(v1: List[float], v2: List[float]) -> float:
    """
    [Helper] Calculates the Euclidean distance between two vectors.
    
    Args:
        v1 (List[float]): First vector.
        v2 (List[float]): Second vector.
        
    Returns:
        float: The distance value.
        
    Raises:
        ValueError: If vectors have different dimensions.
    """
    if len(v1) != len(v2):
        logger.error("Vector dimension mismatch in distance calculation.")
        raise ValueError("Vectors must have the same dimensions.")
    
    sum_sq_diff = sum((a - b) ** 2 for a, b in zip(v1, v2))
    return math.sqrt(sum_sq_diff)

def calibrate_confidence_threshold(state: SystemState) -> float:
    """
    [Core 1] Dynamically adjusts the confidence threshold based on historical variance.
    
    This function implements the 'Dynamic Confidence Calibration Mechanism'.
    If historical errors vary wildly, the system becomes more conservative (requires higher confidence).
    If errors are stable, the system accepts lower confidence intervals.
    
    Args:
        state (SystemState): The current system state containing history.
        
    Returns:
        float: A calculated confidence threshold (0.0 to 1.0).
    """
    logger.info("Calibrating dynamic confidence threshold...")
    
    if not state.history_variance:
        logger.warning("No history available. Defaulting to strict threshold 0.8.")
        return 0.8
    
    variance = sum((x - sum(state.history_variance)/len(state.history_variance))**2 
                   for x in state.history_variance) / len(state.history_variance)
    
    # Normalize variance to a penalty factor (simplified logic for demonstration)
    # High variance -> High penalty -> Higher threshold needed
    normalized_penalty = min(variance * 10, 0.5) # Cap penalty at 0.5
    dynamic_threshold = 0.5 + normalized_penalty
    
    logger.debug(f"Variance: {variance}, Penalty: {normalized_penalty}, Threshold: {dynamic_threshold}")
    return min(dynamic_threshold, 0.99)

def verify_convergence(state: SystemState) -> VerificationResult:
    """
    [Core 2] Verifies if top-down goals and bottom-up data converge.
    
    It determines if the alignment error is within bounds. If not, it decides
    whether to reject the goal (falsification) or request more data.
    
    Logic:
    1. Calculate Error (Distance between Target and Data).
    2. Check if Error < Required Precision.
    3. If not aligned, check Data Density/Variance to determine if 
       'Data Insufficient' or 'Goal Falsified'.
       
    Args:
        state (SystemState): Contains targets, data, and constraints.
        
    Returns:
        VerificationResult: The final decision object.
    """
    logger.info("Starting convergence verification...")
    
    # 1. Input Validation
    if not state.target_vector or not state.data_vector:
        return VerificationResult(
            False, -1.0, 0.0, "ERROR", "Input vectors cannot be empty."
        )
    
    try:
        # 2. Calculate Alignment Error
        current_error = _calculate_euclidean_distance(state.target_vector, state.data_vector)
        logger.info(f"Current alignment error: {current_error:.4f}")
        
        # 3. Check for direct convergence
        if current_error <= state.required_precision:
            return VerificationResult(
                True, current_error, 1.0, "VERIFIED",
                "Top-down targets match bottom-up data within tolerance."
            )
        
        # 4. Handling Non-Convergence (Falsification vs. Data Insufficiency)
        # We calculate the spread of the data vector to estimate density.
        # If data spread is very low (flat) but far from target, the Goal is likely wrong.
        # If data spread is high (noisy), we likely need more data.
        
        mean_data = sum(state.data_vector) / len(state.data_vector)
        data_spread = sum(abs(x - mean_data) for x in state.data_vector) / len(state.data_vector)
        
        dynamic_threshold = calibrate_confidence_threshold(state)
        
        # Heuristic: High error + Low data spread = Goal Error (Falsified)
        # Heuristic: High error + High data spread = Data Insufficient
        
        is_data_sufficient = data_spread < 0.5 # Threshold for 'coherence' of data
        
        if current_error > (state.required_precision * 5) and is_data_sufficient:
            # The data is consistent, but far from the target -> Target is wrong
            return VerificationResult(
                False, current_error, dynamic_threshold, "GOAL_REJECTED",
                f"Target falsified. Data is consistent (spread {data_spread:.2f}) "
                f"but deviates significantly from target."
            )
        else:
            # Data is noisy or error is marginal -> Need more info
            return VerificationResult(
                False, current_error, dynamic_threshold, "DATA_INSUFFICIENT",
                f"Alignment failed. High variance in data suggests need for more samples. "
                f"Confidence level: {dynamic_threshold:.2f}"
            )
            
    except ValueError as ve:
        logger.error(f"Vector processing error: {ve}")
        return VerificationResult(False, -1.0, 0.0, "SYSTEM_ERROR", str(ve))
    except Exception as e:
        logger.critical(f"Unexpected error during verification: {e}", exc_info=True)
        return VerificationResult(False, -1.0, 0.0, "SYSTEM_ERROR", "Critical failure.")

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Scenario 1: Perfect Convergence
    print("--- Scenario 1: Convergence ---")
    state_1 = SystemState(
        target_vector=[1.0, 2.0, 3.0],
        data_vector=[1.01, 2.02, 2.99],
        history_variance=[0.1, 0.1, 0.1],
        required_precision=0.1
    )
    result_1 = verify_convergence(state_1)
    print(f"Verdict: {result_1.verdict} | Msg: {result_1.message}")

    # Scenario 2: Goal Falsification (Data is consistent, but target is wrong)
    print("\n--- Scenario 2: Falsification ---")
    state_2 = SystemState(
        target_vector=[10.0, 10.0, 10.0], # Far away
        data_vector=[1.0, 1.05, 0.95],    # Very consistent (low spread)
        history_variance=[0.2, 0.3],
        required_precision=0.5
    )
    result_2 = verify_convergence(state_2)
    print(f"Verdict: {result_2.verdict} | Msg: {result_2.message}")

    # Scenario 3: Data Insufficient (Noisy data)
    print("\n--- Scenario 3: Data Insufficient ---")
    state_3 = SystemState(
        target_vector=[5.0, 5.0, 5.0],
        data_vector=[1.0, 9.0, 3.0],      # Very noisy (high spread)
        history_variance=[0.1, 0.5, 0.9],
        required_precision=0.5
    )
    result_3 = verify_convergence(state_3)
    print(f"Verdict: {result_3.verdict} | Msg: {result_3.message}")