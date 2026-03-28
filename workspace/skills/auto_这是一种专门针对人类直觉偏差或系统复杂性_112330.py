"""
Module: cognitive_firewall.py

This module implements a defensive cognitive architecture designed to identify and
mitigate human intuition biases and system complexity blind spots.

It specifically targets "Negative Transfer" (applying knowledge inappropriately)
and "Pseudo-Falsification" (rejecting valid hypotheses based on misleading evidence).
"""

import logging
import time
import hashlib
import random
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveFirewall")

class AlertLevel(Enum):
    """Severity levels for cognitive security alerts."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class CognitiveState:
    """Represents the current state of the AGI decision-making context."""
    session_id: str
    domain: str
    proposed_action: Dict[str, Any]
    confidence_score: float
    historical_context: List[Dict] = field(default_factory=list)

@dataclass
class ValidationResult:
    """Result of the firewall validation process."""
    is_secure: bool
    alert_level: AlertLevel
    message: str
    mitigations_applied: List[str] = field(default_factory=list)
    processed_at: float = field(default_factory=time.time)

class SharedMemoryBus:
    """
    Simulates a high-throughput shared memory channel for feedback.
    Acts as the 'bottom-up' feedback mechanism.
    """
    def __init__(self):
        self._buffer: Dict[str, Any] = {}
    
    def write_metric(self, key: str, value: Any) -> None:
        self._buffer[key] = value
    
    def read_metric(self, key: str) -> Optional[Any]:
        return self._buffer.get(key)
    
    def flush(self) -> None:
        self._buffer.clear()

class IntuitionBiasDefense:
    """
    Core class implementing the defensive cognitive architecture.
    """
    
    def __init__(self, memory_bus: SharedMemoryBus, sensitivity: float = 0.8):
        """
        Initialize the defense system.
        
        Args:
            memory_bus: Instance of SharedMemoryBus for feedback.
            sensitivity: Threshold for triggering alerts (0.0 to 1.0).
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")
            
        self.bus = memory_bus
        self.sensitivity = sensitivity
        self._previous_states: Dict[str, str] = {} # For state transition checks
        logger.info(f"Cognitive Firewall initialized with sensitivity {sensitivity}")

    def _validate_input_state(self, state: CognitiveState) -> None:
        """Validates the structure and content of the input state."""
        if not state.session_id:
            raise ValueError("Session ID cannot be empty")
        if not 0 <= state.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        if not state.proposed_action:
            raise ValueError("Proposed action cannot be empty")

    def _check_negative_transfer(self, state: CognitiveState) -> Tuple[bool, str]:
        """
        Checks if the current action is misapplying rules from a different domain.
        Simulates detecting 'knowledge leakage'.
        """
        source_domain = state.proposed_action.get("source_domain")
        target_domain = state.domain
        
        # Heuristic: If source and target domains differ significantly but confidence is high
        domain_distance = self._calculate_domain_distance(source_domain, target_domain)
        
        if domain_distance > 0.7 and state.confidence_score > 0.9:
            return True, f"Suspected negative transfer: High confidence ({state.confidence_score}) " \
                         f"despite large domain distance ({domain_distance})"
        
        return False, "Negative transfer check passed"

    def _check_pseudo_falsification(self, state: CognitiveState) -> Tuple[bool, str]:
        """
        Checks if the system is rejecting a macro goal based on misleading micro failures.
        """
        # Simulate checking bottom-up feedback for transient errors vs systemic errors
        error_rate = self.bus.read_metric("subsystem_error_rate") or 0.0
        
        # If error rate is high but variance is high, it might be noise (pseudo-falsification)
        # If error rate is high and variance is low, it's a systemic issue (valid falsification)
        error_variance = self.bus.read_metric("error_variance") or 0.0
        
        if error_rate > 0.2 and error_variance > 0.5:
            return True, "Pseudo-falsification detected: High variance noise misinterpreted as systemic failure"
            
        return False, "Falsification check passed"

    def _calculate_domain_distance(self, domain_a: str, domain_b: str) -> float:
        """
        Helper function to calculate semantic distance between domains.
        In a real AGI, this would use embeddings.
        """
        if domain_a == domain_b:
            return 0.0
        
        # Simple hash-based simulation of semantic distance
        dist = abs(hash(domain_a or "none") - hash(domain_b or "none")) % 100 / 100.0
        # Add some controlled randomness to simulate complexity
        return min(1.0, dist + random.uniform(-0.1, 0.1))

    def analyze_decision(self, state: CognitiveState) -> ValidationResult:
        """
        Main entry point. Analyzes a proposed decision against cognitive biases.
        
        Args:
            state: The current cognitive state containing the proposed action.
            
        Returns:
            ValidationResult: Object containing security status and details.
        """
        try:
            self._validate_input_state(state)
            logger.info(f"Analyzing decision for session {state.session_id}")
            
            alerts = []
            mitigations = []
            is_secure = True
            max_level = AlertLevel.LOW
            
            # 1. Negative Transfer Check
            nt_detected, nt_msg = self._check_negative_transfer(state)
            if nt_detected:
                alerts.append(nt_msg)
                mitigations.append("Applying domain adaptation regularization")
                max_level = max(max_level, AlertLevel.MEDIUM)
                is_secure = False
                logger.warning(nt_msg)

            # 2. Pseudo-Falsification Check
            pf_detected, pf_msg = self._check_pseudo_falsification(state)
            if pf_detected:
                alerts.append(pf_msg)
                mitigations.append("Switching to robust estimation mode (ignoring outliers)")
                max_level = max(max_level, AlertLevel.HIGH)
                # Pseudo-falsification might not make the decision 'insecure', 
                # but requires adjustment. For this strict firewall, we flag it.
                is_secure = False
                logger.warning(pf_msg)
            
            # 3. Boundary check on confidence vs complexity
            complexity = len(state.proposed_action) + len(state.historical_context)
            if complexity > 50 and state.confidence_score > 0.95:
                msg = "Overconfidence detected in highly complex environment"
                alerts.append(msg)
                mitigations.append("Confidence calibration enforced")
                max_level = max(max_level, AlertLevel.LOW)
                logger.info(msg)

            if is_secure:
                logger.info("Decision validated successfully.")
                return ValidationResult(
                    is_secure=True, 
                    alert_level=AlertLevel.LOW, 
                    message="Action deemed safe"
                )
            else:
                full_msg = "; ".join(alerts)
                return ValidationResult(
                    is_secure=False,
                    alert_level=max_level,
                    message=full_msg,
                    mitigations_applied=mitigations
                )

        except Exception as e:
            logger.error(f"Critical error during analysis: {str(e)}")
            return ValidationResult(
                is_secure=False,
                alert_level=AlertLevel.CRITICAL,
                message=f"Internal Firewall Error: {str(e)}"
            )

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Initialize the shared memory bus
    memory_bus = SharedMemoryBus()
    
    # Simulate feedback data (Bottom-up signals)
    memory_bus.write_metric("subsystem_error_rate", 0.35)
    memory_bus.write_metric("error_variance", 0.8) # High noise
    
    # Initialize the Defense System
    firewall = IntuitionBiasDefense(memory_bus=memory_bus, sensitivity=0.75)
    
    # Case 1: Suspected Negative Transfer
    print("--- Test Case 1: Negative Transfer ---")
    suspicious_state = CognitiveState(
        session_id="sess_001",
        domain="medical_diagnosis",
        proposed_action={
            "action": "prescribe_medication", 
            "source_domain": "stock_trading", # Misapplying trading logic to medicine
            "dosage": "high_risk"
        },
        confidence_score=0.98 # Suspiciously high confidence
    )
    
    result_1 = firewall.analyze_decision(suspicious_state)
    print(f"Is Secure: {result_1.is_secure}")
    print(f"Message: {result_1.message}")
    print(f"Mitigations: {result_1.mitigations_applied}\n")

    # Case 2: Suspected Pseudo-Falsification
    print("--- Test Case 2: Pseudo-Falsification ---")
    normal_state = CognitiveState(
        session_id="sess_002",
        domain="robotic_control",
        proposed_action={"action": "adjust_grip", "force": 5},
        confidence_score=0.8,
        historical_context=[{"step": i} for i in range(10)]
    )
    
    result_2 = firewall.analyze_decision(normal_state)
    print(f"Is Secure: {result_2.is_secure}")
    print(f"Message: {result_2.message}")
    print(f"Mitigations: {result_2.mitigations_applied}\n")
    
    # Case 3: Valid Decision
    print("--- Test Case 3: Valid Decision ---")
    memory_bus.write_metric("subsystem_error_rate", 0.01) # Low error
    memory_bus.write_metric("error_variance", 0.1) # Low variance
    
    valid_state = CognitiveState(
        session_id="sess_003",
        domain="logistics",
        proposed_action={"action": "reroute", "dest": "warehouse_b"},
        confidence_score=0.85
    )
    result_3 = firewall.analyze_decision(valid_state)
    print(f"Is Secure: {result_3.is_secure}")
    print(f"Message: {result_3.message}")