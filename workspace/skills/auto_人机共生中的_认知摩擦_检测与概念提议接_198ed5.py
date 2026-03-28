"""
Module: cognitive_friction_detector.py
Description: Implementation of the 'Cognitive Friction' detection mechanism for Human-Computer Symbiosis.
             This module serves as an interface to detect logical discontinuities or insufficient evidence
             during AI reasoning processes. Instead of hallucinating to fill gaps, it generates a
             standardized 'Human Assistance Package' to request human intervention.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
License: MIT
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, TypedDict, Union
from enum import Enum
from dataclasses import dataclass, asdict

# Configure Module Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveFrictionError(Exception):
    """Custom exception for cognitive friction detection failures."""
    pass


class FrictionType(Enum):
    """Enumeration of possible cognitive friction types."""
    LOGICAL_DISCONNECT = "logical_disconnect"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ONTOLOGY_MISMATCH = "ontology_mismatch"
    ETHICAL_BOUNDARY = "ethical_boundary"


class InterventionPriority(Enum):
    """Urgency levels for human intervention."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AttemptedPath:
    """Data structure representing a reasoning path attempted by the AI."""
    step_id: str
    description: str
    outcome: str
    confidence: float


@dataclass
class HumanAssistancePackage:
    """
    Standardized package sent to the human operator when cognitive friction is detected.
    """
    session_id: str
    timestamp: str
    friction_type: FrictionType
    context_summary: str
    reasoning_gap: str
    attempted_paths: List[AttemptedPath]
    suggested_questions: List[str]
    priority: InterventionPriority
    evidence_status: Dict[str, bool]

    def to_json(self) -> str:
        """Serialize the package to JSON format."""
        data = asdict(self)
        data['friction_type'] = self.friction_type.value
        data['priority'] = self.priority.value
        return json.dumps(data, indent=2)


class CognitiveContext(TypedDict):
    """Type definition for the cognitive context input."""
    current_goal: str
    active_graph_nodes: List[str]
    logic_state: Dict[str, Any]
    evidence_buffer: Dict[str, float]
    confidence_threshold: float


def validate_context_schema(context: Dict[str, Any]) -> CognitiveContext:
    """
    Auxiliary function to validate the input context structure.
    
    Args:
        context: Raw dictionary input containing context data.
        
    Returns:
        Validated CognitiveContext dictionary.
        
    Raises:
        CognitiveFrictionError: If required fields are missing or invalid.
    """
    required_keys = ["current_goal", "active_graph_nodes", "logic_state", "evidence_buffer", "confidence_threshold"]
    
    if not isinstance(context, dict):
        logger.error("Context validation failed: Input is not a dictionary.")
        raise CognitiveFrictionError("Context must be a dictionary.")

    missing_keys = [key for key in required_keys if key not in context]
    if missing_keys:
        logger.error(f"Context validation failed: Missing keys {missing_keys}")
        raise CognitiveFrictionError(f"Missing required context keys: {missing_keys}")

    # Boundary checks
    if not isinstance(context["confidence_threshold"], (float, int)):
        raise CognitiveFrictionError("Confidence threshold must be numeric.")
    
    if not (0.0 <= context["confidence_threshold"] <= 1.0):
        logger.warning("Confidence threshold out of standard range [0,1], normalizing logic might fail.")
    
    logger.debug("Context schema validated successfully.")
    return context  # type: ignore


def analyze_evidence_gap(
    evidence_buffer: Dict[str, float], 
    threshold: float
) -> Dict[str, bool]:
    """
    Analyze the evidence buffer against the confidence threshold.
    
    Args:
        evidence_buffer: Dictionary mapping evidence keys to confidence scores.
        threshold: The minimum confidence required.
        
    Returns:
        A dictionary mapping evidence keys to boolean validity status.
    """
    status = {}
    for key, confidence in evidence_buffer.items():
        is_valid = confidence >= threshold
        status[key] = is_valid
        if not is_valid:
            logger.info(f"Evidence gap detected for key '{key}': {confidence} < {threshold}")
    return status


def detect_cognitive_friction(
    context: Dict[str, Any],
    session_id: str,
    current_logic_chain: Optional[List[Dict]] = None
) -> Optional[HumanAssistancePackage]:
    """
    Core function: Detects if the current reasoning state warrants human intervention.
    
    This function implements the 'Human Practice Falsification' trigger logic. It checks for:
    1. Logical discontinuities in the reasoning chain.
    2. Evidence support falling below the confidence threshold.
    3. Explicit contradictions in the logic state.
    
    Args:
        context: The current cognitive context containing state, evidence, and goals.
        session_id: Unique identifier for the current interaction session.
        current_logic_chain: Optional list of steps representing the current reasoning path.
        
    Returns:
        HumanAssistancePackage if friction is detected, otherwise None.
        
    Raises:
        CognitiveFrictionError: If internal processing fails.
    """
    try:
        # Step 1: Validate Input
        valid_context = validate_context_schema(context)
        logger.info(f"Analyzing cognitive state for session {session_id}...")

        threshold = valid_context["confidence_threshold"]
        evidence_status = analyze_evidence_gap(valid_context["evidence_buffer"], threshold)
        
        # Determine if there are gaps
        has_gaps = any(not status for status in evidence_status.values())
        logic_state = valid_context["logic_state"]
        
        # Trigger Logic: Check for contradictions or gaps
        is_contradiction = logic_state.get("has_contradiction", False)
        disconnect_detected = False
        
        # Simple heuristic for logical disconnect (for demonstration)
        if current_logic_chain:
            for i, step in enumerate(current_logic_chain[:-1]):
                next_step = current_logic_chain[i + 1]
                # If the conclusion of step i is not the premise of step i+1 (simulated)
                if step.get("conclusion_id") != next_step.get("premise_id"):
                    disconnect_detected = True
                    logger.warning(f"Logical disconnect found between step {i} and {i+1}")
                    break

        # Decision Matrix
        if not (has_gaps or is_contradiction or disconnect_detected):
            logger.info("Cognitive friction check passed. Proceeding autonomously.")
            return None

        # Step 2: Construct the Assistance Package
        logger.warning(f"Cognitive friction detected! Halting computation for session {session_id}.")
        
        # Map detection to Friction Type
        if is_contradiction:
            f_type = FrictionType.LOGICAL_DISCONNECT
            priority = InterventionPriority.HIGH
            gap_desc = "Contradiction detected in logic state."
        elif disconnect_detected:
            f_type = FrictionType.LOGICAL_DISCONNECT
            priority = InterventionPriority.MEDIUM
            gap_desc = "Broken reasoning chain detected."
        else:
            f_type = FrictionType.INSUFFICIENT_EVIDENCE
            priority = InterventionPriority.MEDIUM
            gap_desc = "Evidence confidence below operational threshold."

        # Format attempted paths
        attempted = []
        if current_logic_chain:
            for idx, step in enumerate(current_logic_chain):
                attempted.append(AttemptedPath(
                    step_id=f"step_{idx}",
                    description=step.get("description", "N/A"),
                    outcome=step.get("outcome", "processing"),
                    confidence=step.get("confidence", 0.0)
                ))

        package = HumanAssistancePackage(
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            friction_type=f_type,
            context_summary=valid_context["current_goal"],
            reasoning_gap=gap_desc,
            attempted_paths=attempted,
            suggested_questions=["Can you verify the premise for step 2?", "Is there external data for X?"],
            priority=priority,
            evidence_status=evidence_status
        )

        return package

    except Exception as e:
        logger.critical(f"System failure during friction detection: {str(e)}")
        raise CognitiveFrictionError(f"Failed to process cognitive context: {str(e)}")


# --- Usage Example ---
if __name__ == "__main__":
    # Simulate a scenario where the AI encounters a gap
    sample_context = {
        "current_goal": "Determine if User X is eligible for Service Y",
        "active_graph_nodes": ["user_profile", "policy_check", "risk_assessment"],
        "logic_state": {
            "has_contradiction": False,
            "current_step": "risk_assessment"
        },
        "evidence_buffer": {
            "credit_score": 0.95,
            "identity_verification": 0.98,
            "behavioral_pattern": 0.42  # This is below threshold
        },
        "confidence_threshold": 0.85
    }

    # Simulate a broken logic chain
    logic_chain = [
        {"premise_id": "start", "conclusion_id": "A", "description": "Fetched User Profile", "confidence": 0.9},
        {"premise_id": "B", "conclusion_id": "C", "description": "Applied Policy Check", "confidence": 0.88} 
        # Note: Conclusion 'A' != Premise 'B', creating a disconnect
    ]

    print("--- Running Cognitive Friction Detector ---")
    
    try:
        result = detect_cognitive_friction(
            context=sample_context,
            session_id="sess_198ed5_alpha",
            current_logic_chain=logic_chain
        )

        if result:
            print("\n!!! HUMAN INTERVENTION REQUIRED !!!")
            print(result.to_json())
        else:
            print("\nSystem operating within parameters.")

    except CognitiveFrictionError as e:
        print(f"Error: {e}")