"""
Module: implicit_error_detector
A predictive analytics module for detecting implicit human errors through 
analysis of micro-expressions, micro-action latencies, and other non-explicit data.

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Enumeration of risk levels for predicted errors."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class OperatorState:
    """Data class representing the current state of a human operator.
    
    Attributes:
        eye_saccade_rate (float): Frequency of rapid eye movements per second.
        blink_rate (int): Blinks per minute.
        facial_tension_score (float): A score from 0.0 to 1.0 indicating facial muscle tension.
        action_latency_ms (int): Delay in milliseconds between stimulus and response.
        timestamp (float): Unix timestamp of the data capture.
    """
    eye_saccade_rate: float
    blink_rate: int
    facial_tension_score: float
    action_latency_ms: int
    timestamp: float = time.time()


@dataclass
class PredictionResult:
    """Data class representing the prediction result.
    
    Attributes:
        is_error_predicted (bool): Whether an error is predicted.
        risk_level (RiskLevel): The severity of the predicted error.
        confidence (float): Confidence score of the prediction (0.0 to 1.0).
        indicators (Dict[str, float]): Key indicators that triggered the prediction.
    """
    is_error_predicted: bool
    risk_level: RiskLevel
    confidence: float
    indicators: Dict[str, float]


class ImplicitErrorDetector:
    """
    Analyzes non-explicit behavioral data to predict operational errors 
    before they manifest consciously.
    
    This class uses weighted heuristics to detect deviations from a baseline
    that typically precede human error in high-stakes environments.
    """

    def __init__(self, 
                 latency_threshold_ms: int = 300, 
                 tension_threshold: float = 0.7,
                 history_window_size: int = 5):
        """
        Initialize the detector with specific thresholds.
        
        Args:
            latency_threshold_ms (int): Threshold for action latency to trigger alert.
            tension_threshold (float): Threshold for facial tension (0.0-1.0).
            history_window_size (int): Number of recent samples to consider for smoothing.
        """
        self.latency_threshold = latency_threshold_ms
        self.tension_threshold = tension_threshold
        self.history_window_size = history_window_size
        self._state_history: List[OperatorState] = []
        logger.info("ImplicitErrorDetector initialized with latency=%dms, tension=%.2f", 
                    latency_threshold_ms, tension_threshold)

    def _validate_state(self, state: OperatorState) -> bool:
        """Validate the input data integrity and boundaries.
        
        Args:
            state (OperatorState): The state object to validate.
            
        Returns:
            bool: True if valid, raises ValueError otherwise.
            
        Raises:
            ValueError: If data is out of bounds or missing.
        """
        if not 0.0 <= state.facial_tension_score <= 1.0:
            raise ValueError(f"Invalid facial tension score: {state.facial_tension_score}")
        if state.action_latency_ms < 0:
            raise ValueError("Action latency cannot be negative")
        if state.blink_rate < 0:
            raise ValueError("Blink rate cannot be negative")
        return True

    def update_baseline(self, state: OperatorState) -> None:
        """Update the internal history buffer with the latest state.
        
        Maintains a sliding window of states for trend analysis.
        
        Args:
            state (OperatorState): The latest captured state.
        """
        try:
            self._validate_state(state)
            self._state_history.append(state)
            if len(self._state_history) > self.history_window_size:
                self._state_history.pop(0)
            logger.debug("State history updated. Current size: %d", len(self._state_history))
        except ValueError as ve:
            logger.error("Validation failed during baseline update: %s", ve)

    def analyze_cognitive_load(self) -> float:
        """
        Calculate a proxy for cognitive load based on recent history.
        
        High blink rate combined with high latency often indicates cognitive overload.
        
        Returns:
            float: A normalized cognitive load score (0.0 to 1.0).
        """
        if not self._state_history:
            return 0.0

        # Simple moving average of latency and blink rate
        avg_latency = sum(s.action_latency_ms for s in self._state_history) / len(self._state_history)
        
        # Normalize latency (assuming 500ms is high load)
        load_score = min(avg_latency / 500.0, 1.0)
        return load_score

    def predict_error_probability(self, current_state: OperatorState) -> PredictionResult:
        """
        Core Function 1: Predict the probability of an imminent error.
        
        Analyzes micro-expressions (tension) and micro-delays (latency) against
        established thresholds to forecast mistakes.
        
        Args:
            current_state (OperatorState): Real-time data of the operator.
            
        Returns:
            PredictionResult: The prediction object containing risk details.
        """
        try:
            self._validate_state(current_state)
        except ValueError as e:
            logger.warning("Prediction aborted due to invalid data: %s", e)
            return PredictionResult(False, RiskLevel.LOW, 0.0, {"error": str(e)})

        self.update_baseline(current_state)
        indicators: Dict[str, float] = {}
        risk_accumulator = 0.0

        # Check 1: Micro-action latency (Hesitation)
        if current_state.action_latency_ms > self.latency_threshold:
            deviation = (current_state.action_latency_ms - self.latency_threshold) / self.latency_threshold
            indicators['latency_deviation'] = deviation
            risk_accumulator += 0.4 * min(deviation, 1.0)
            logger.info("High latency detected: %dms", current_state.action_latency_ms)

        # Check 2: Facial micro-tension (Stress/Focus loss)
        if current_state.facial_tension_score > self.tension_threshold:
            indicators['tension_level'] = current_state.facial_tension_score
            risk_accumulator += 0.3 * current_state.facial_tension_score

        # Check 3: Cognitive Load Trend
        cog_load = self.analyze_cognitive_load()
        if cog_load > 0.8:
            indicators['cognitive_load'] = cog_load
            risk_accumulator += 0.3 * cog_load

        # Determine Risk Level
        if risk_accumulator > 0.9:
            level = RiskLevel.CRITICAL
        elif risk_accumulator > 0.6:
            level = RiskLevel.HIGH
        elif risk_accumulator > 0.3:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        is_error = risk_accumulator > 0.5
        
        return PredictionResult(
            is_error_predicted=is_error,
            risk_level=level,
            confidence=min(risk_accumulator, 1.0),
            indicators=indicators
        )

    def generate_intervention_signal(self, prediction: PredictionResult) -> Optional[str]:
        """
        Core Function 2: Generate an actionable intervention signal.
        
        Decides what kind of warning or system lock to engage based on risk.
        
        Args:
            prediction (PredictionResult): The result from the prediction engine.
            
        Returns:
            Optional[str]: A command string or None if no action needed.
        """
        if not prediction.is_error_predicted:
            return None

        command = ""
        if prediction.risk_level == RiskLevel.CRITICAL:
            command = "SYSTEM_HALT_TRIGGERED"
            logger.critical("Critical error risk detected! Triggering system halt.")
        elif prediction.risk_level == RiskLevel.HIGH:
            command = "AUDITORY_ALERT_HIGH"
            logger.warning("High error risk. Issuing auditory alert.")
        elif prediction.risk_level == RiskLevel.MEDIUM:
            command = "VISUAL_CUE_YELLOW"
            logger.info("Moderate risk. Displaying visual caution cue.")
        
        return command


# --- Usage Example ---
if __name__ == "__main__":
    # Initialize detector
    detector = ImplicitErrorDetector(latency_threshold_ms=250, tension_threshold=0.6)
    
    # Simulate a stream of operator states
    # Scenario 1: Normal operation
    state_1 = OperatorState(
        eye_saccade_rate=3.5, 
        blink_rate=15, 
        facial_tension_score=0.2, 
        action_latency_ms=180
    )
    
    # Scenario 2: Stressful operation (High latency + High tension)
    state_2 = OperatorState(
        eye_saccade_rate=5.0, 
        blink_rate=22, 
        facial_tension_score=0.85, # High tension
        action_latency_ms=450      # High latency (hesitation)
    )

    print("--- Processing State 1 (Normal) ---")
    result_1 = detector.predict_error_probability(state_1)
    signal_1 = detector.generate_intervention_signal(result_1)
    print(f"Prediction: {result_1.is_error_predicted}, Risk: {result_1.risk_level.name}")
    print(f"Intervention: {signal_1}")

    print("\n--- Processing State 2 (Stress) ---")
    result_2 = detector.predict_error_probability(state_2)
    signal_2 = detector.generate_intervention_signal(result_2)
    print(f"Prediction: {result_2.is_error_predicted}, Risk: {result_2.risk_level.name}")
    print(f"Intervention: {signal_2}")