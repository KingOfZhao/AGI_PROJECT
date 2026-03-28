"""
Module: cognitive_boundary_radar.py

Description:
    This module implements the 'auto_基于实践落差的认知边界雷达' (Auto-Cognitive Boundary Radar).
    It identifies high-risk cognitive voids by analyzing the dynamic discrepancy between
    system intent (static vector projection) and execution performance (confidence drops/error rates).
    
    When a cognitive void is detected (simulating an apprentice's uncertainty or 'hand tremor'),
    the system triggers a 'Master Request' protocol for human intervention rather than
    proceeding with blind generation.

Author: AGI System Core Engineering
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Enumeration for alert severity levels."""
    SAFE = 0
    WARNING = 1
    HIGH_RISK_VOID = 2


@dataclass
class IntentVector:
    """Represents the high-dimensional intent vector of the system."""
    vector_id: str
    projection: np.ndarray  # High-dimensional static projection
    magnitude: float
    domain_tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not isinstance(self.projection, np.ndarray):
            raise ValueError("Projection must be a numpy array.")
        if len(self.projection) == 0:
            raise ValueError("Projection vector cannot be empty.")


@dataclass
class ExecutionFeedback:
    """Represents feedback from the execution layer."""
    sample_id: str
    confidence_score: float  # 0.0 to 1.0
    error_rate: float        # 0.0 to 1.0
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0 and 1.")
        if not (0.0 <= self.error_rate <= 1.0):
            raise ValueError("Error rate must be between 0 and 1.")


@dataclass
class CognitiveRadarConfig:
    """Configuration for the Cognitive Boundary Radar."""
    confidence_threshold: float = 0.6
    error_rate_threshold: float = 0.3
    vector_sparsity_threshold: float = 0.85
    void_detection_window: int = 5  # Number of recent samples to analyze


class CognitiveBoundaryRadar:
    """
    Core class for detecting cognitive voids based on intent-execution gaps.
    """

    def __init__(self, config: CognitiveRadarConfig):
        self.config = config
        self._feedback_buffer: List[ExecutionFeedback] = []
        logger.info("Cognitive Boundary Radar initialized with config: %s", config)

    def _analyze_vector_sparsity(self, vector: np.ndarray) -> float:
        """
        Helper function to calculate the sparsity of the intent vector.
        High sparsity often indicates specific, niche knowledge retrieval.
        """
        if vector.size == 0:
            return 0.0
        
        zero_elements = np.count_nonzero(vector == 0)
        sparsity = zero_elements / float(vector.size)
        return sparsity

    def _analyze_execution_dynamics(self, recent_feedback: List[ExecutionFeedback]) -> Tuple[float, float]:
        """
        Analyzes the recent execution feedback for confidence drops and error spikes.
        
        Returns:
            Tuple[float, float]: (average_confidence, max_error_rate)
        """
        if not recent_feedback:
            return 1.0, 0.0

        confidences = [fb.confidence_score for fb in recent_feedback]
        errors = [fb.error_rate for fb in recent_feedback]

        avg_conf = np.mean(confidences)
        max_err = np.max(errors)

        return float(avg_conf), float(max_err)

    def scan_boundary(self, intent: IntentVector, feedback: ExecutionFeedback) -> Dict[str, Any]:
        """
        Main entry point to scan for cognitive voids.
        
        Args:
            intent (IntentVector): The current system intent.
            feedback (ExecutionFeedback): The real-time execution feedback.
        
        Returns:
            Dict[str, Any]: Diagnostic report including alert level and action.
        """
        # 1. Validate Inputs
        if not isinstance(intent, IntentVector) or not isinstance(feedback, ExecutionFeedback):
            logger.error("Invalid input types provided to scan_boundary.")
            raise TypeError("Invalid input types.")

        # Update buffer
        self._feedback_buffer.append(feedback)
        if len(self._feedback_buffer) > self.config.void_detection_window:
            self._feedback_buffer.pop(0)

        logger.debug(f"Scanning boundary for Intent ID: {intent.vector_id}")

        # 2. Static Analysis: Vector Sparsity
        sparsity = self._analyze_vector_sparsity(intent.projection)
        
        # 3. Dynamic Analysis: Execution Gap
        recent_window = self._feedback_buffer[-self.config.void_detection_window:]
        avg_conf, max_err = self._analyze_execution_dynamics(recent_window)

        # 4. Logic: Detect Void
        # Condition: High sparsity (niche intent) AND (Low confidence OR High error)
        is_sparse = sparsity > self.config.vector_sparsity_threshold
        is_unstable = (avg_conf < self.config.confidence_threshold) or \
                      (max_err > self.config.error_rate_threshold)

        alert_level = AlertLevel.SAFE
        action = "CONTINUE_GENERATION"
        diagnosis = "Operation within known cognitive boundaries."

        if is_sparse and is_unstable:
            alert_level = AlertLevel.HIGH_RISK_VOID
            action = "TRIGGER_MASTER_REQUEST"
            diagnosis = (
                f"Cognitive Void Detected. High sparsity ({sparsity:.2f}) "
                f"met with low confidence ({avg_conf:.2f}) and high error rate ({max_err:.2f})."
            )
            logger.warning(diagnosis)
        elif is_unstable:
            alert_level = AlertLevel.WARNING
            action = "RECALIBRATE"
            diagnosis = "Execution instability detected, but within dense vector space."
            logger.info(diagnosis)

        return {
            "intent_id": intent.vector_id,
            "timestamp": feedback.metadata.get("timestamp", "N/A"),
            "metrics": {
                "vector_sparsity": sparsity,
                "avg_confidence": avg_conf,
                "max_error_rate": max_err
            },
            "alert_level": alert_level.name,
            "action_required": action,
            "diagnosis": diagnosis
        }


def run_radar_diagnostic():
    """
    Usage Example / Test Harness
    
    Scenario:
    Simulate an AGI attempting a complex task (High Sparsity Intent).
    The execution layer returns unstable results (Low Confidence).
    The Radar should detect this as a High Risk Void.
    """
    print("--- Initializing Cognitive Boundary Radar System ---")
    
    # 1. Setup Configuration
    config = CognitiveRadarConfig(
        confidence_threshold=0.7,
        error_rate_threshold=0.2,
        vector_sparsity_threshold=0.8
    )
    radar = CognitiveBoundaryRadar(config)

    # 2. Prepare Data
    # Intent: A 100-dimensional vector, mostly zeros (sparse), representing a niche query
    intent_vector = np.zeros(100)
    intent_vector[10] = 0.9
    intent_vector[45] = 0.1 # Sparse vector
    
    intent = IntentVector(
        vector_id="intent_8a7b_complex_query",
        projection=intent_vector,
        magnitude=0.92,
        domain_tags=["physics", "quantum_mechanics", "theoretical"]
    )

    # 3. Simulate Execution Loop
    print("\n--- Simulating Execution Cycles ---")
    
    # Cycle 1: Safe execution (Dense vector, good confidence)
    # Note: For brevity, we skip this in the example output focus, 
    # but here is how a safe call looks:
    try:
        # Forcing a sparse vector scenario directly for the main test
        # Feedback simulates an 'apprentice hand tremor' (low confidence, high error)
        feedback_1 = ExecutionFeedback(
            sample_id="exec_101",
            confidence_score=0.45, # Low!
            error_rate=0.55,       # High!
            latency_ms=120,
            metadata={"timestamp": "2023-10-27T10:00:01Z"}
        )

        # 4. Run Scan
        result = radar.scan_boundary(intent, feedback_1)
        
        print(f"\nDiagnostic Result:")
        print(f"  Alert Level: {result['alert_level']}")
        print(f"  Action:      {result['action_required']}")
        print(f"  Diagnosis:   {result['diagnosis']}")
        
        if result['action_required'] == "TRIGGER_MASTER_REQUEST":
            print("\n>>> SYSTEM ACTION: Suspending generation. Sending 'Master Request' to human supervisor. <<<")
        
    except ValueError as ve:
        logger.error(f"Data validation error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected system failure: {e}")

if __name__ == "__main__":
    run_radar_diagnostic()