"""
Module: ethical_hard_constraint_layer.py

This module implements an 'Ethical Hard Constraint Layer' designed to act as a
final safeguard in AGI or advanced AI systems. It specifically addresses the
risk where an AI, during 'cross-domain迁移' (transfer learning) or
'mutation/redundancy' optimization, might inadvertently violate human ethical
norms to maximize efficiency (e.g., misapplying biological evolution concepts
to justify social inequality).

The system validates proposed actions or hypotheses against a set of immutable
ethical axioms before execution.
"""

import logging
import json
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EthicalViolationError(Exception):
    """Custom exception raised when an action violates ethical constraints."""
    def __init__(self, message: str, violations: List[str]):
        super().__init__(message)
        self.violations = violations

    def __str__(self):
        return f"Ethical Violation Detected: {', '.join(self.violations)}"

class ActionDomain(Enum):
    """Enumeration of possible action domains for context-aware validation."""
    GENERAL = "general"
    BIOLOGICAL_EVOLUTION = "bio_evo"
    SOCIAL_ENGINEERING = "social_eng"
    RESOURCE_ALLOCATION = "resource_alloc"
    MEDICAL_TREATMENT = "medical"

@dataclass
class EthicalAxiom:
    """Represents a single, immutable ethical rule."""
    axiom_id: str
    name: str
    description: str
    critical_keywords: List[str] = field(default_factory=list)
    is_active: bool = True

@dataclass
class AIAction:
    """Represents a proposed action by the AI system requiring validation."""
    action_id: str
    description: str
    domain: ActionDomain
    predicted_outcome: str
    optimization_goal: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class EthicalConstraintEngine:
    """
    Core engine for enforcing hard ethical constraints.
    
    This engine acts as a post-logic check. Even if an action is logically sound
    and optimizes the target function, it must pass this layer to ensure it does
    not breach fundamental human values.
    """

    def __init__(self):
        self._axioms: Dict[str, EthicalAxiom] = {}
        self._load_default_axioms()

    def _load_default_axioms(self) -> None:
        """Initializes the engine with foundational ethical axioms."""
        # Axiom 1: Prevention of Social Darwinism
        axiom1 = EthicalAxiom(
            axiom_id="AX-001",
            name="Social Equality Safeguard",
            description="Must not use biological fitness as a justification for "
                        "social resource deprivation or hierarchy.",
            critical_keywords=["survival of fittest", "social darwinism", 
                               "genetic superiority", "purification"]
        )
        
        # Axiom 2: Human Agency
        axiom2 = EthicalAxiom(
            axiom_id="AX-002",
            name="Autonomy Preservation",
            description="Must not manipulate human free will for optimization gains "
                        "without explicit consent.",
            critical_keywords=["coerce", "manipulate", "unconscious bias", 
                               "forced compliance"]
        )

        # Axiom 3: Safety and Non-Harm
        axiom3 = EthicalAxiom(
            axiom_id="AX-003",
            name="Non-Maleficence",
            description="Physical or psychological harm to humans is forbidden "
                        "unless strictly necessary to prevent greater harm (trolley problem logic "
                        "requires human oversight).",
            critical_keywords=["sacrifice", "collateral damage", "terminate"]
        )

        self.add_axiom(axiom1)
        self.add_axiom(axiom2)
        self.add_axiom(axiom3)
        logger.info(f"Initialized {len(self._axioms)} ethical axioms.")

    def add_axiom(self, axiom: EthicalAxiom) -> None:
        """Adds a new axiom to the constraint layer."""
        if not isinstance(axiom, EthicalAxiom):
            raise ValueError("Invalid axiom type provided.")
        self._axioms[axiom.axiom_id] = axiom
        logger.debug(f"Axiom {axiom.axiom_id} added/updated.")

    def _preprocess_text(self, text: str) -> str:
        """Helper function to normalize text for analysis."""
        if not isinstance(text, str):
            return ""
        # Convert to lowercase and remove special characters
        return re.sub(r'[^\w\s]', '', text.lower())

    def validate_action(self, action: AIAction) -> Tuple[bool, List[str]]:
        """
        Validates an AI action against all active ethical axioms.
        
        Args:
            action (AIAction): The proposed action object.
            
        Returns:
            Tuple[bool, List[str]]: (True, []) if valid, (False, [violations]) if invalid.
        
        Raises:
            EthicalViolationError: If hard constraints are violated.
        """
        if not isinstance(action, AIAction):
            raise TypeError("Input must be an AIAction instance.")

        logger.info(f"Validating Action ID: {action.action_id} in Domain: {action.domain}")

        combined_text = f"{action.description} {action.predicted_outcome} {action.optimization_goal}"
        normalized_text = self._preprocess_text(combined_text)
        violations = []

        # Domain-Specific Logic Check
        # Example: If domain is SOCIAL_ENGINEERING, strict checks on BIO logics
        if action.domain == ActionDomain.SOCIAL_ENGINEERING:
            bio_keywords = ["evolution", "natural selection", "survival"]
            if any(kw in normalized_text for kw in bio_keywords):
                # Check if the context is applying bio logic to social structure
                if "efficiency" in normalized_text or "optimization" in normalized_text:
                    violations.append(
                        "Cross-Domain Violation: Applying biological evolutionary "
                        "pressure to social engineering contexts."
                    )

        # Axiom Checking
        for axiom in self._axioms.values():
            if not axiom.is_active:
                continue
            
            # Check for critical forbidden keywords
            for keyword in axiom.critical_keywords:
                if keyword in normalized_text:
                    violations.append(f"Axiom Breach [{axiom.name}]: Detected '{keyword}'.")

        # Data Validation & Boundary Checks
        if action.metadata:
            if "risk_factor" in action.metadata:
                risk = action.metadata["risk_factor"]
                if not isinstance(risk, (int, float)):
                    violations.append("Invalid data type for risk_factor.")
                elif risk > 0.9: # Arbitrary threshold
                    violations.append(f"Risk factor {risk} exceeds safety threshold of 0.9.")

        if violations:
            logger.warning(f"Action {action.action_id} REJECTED. Violations: {violations}")
            return False, violations

        logger.info(f"Action {action.action_id} PASSED ethical constraints.")
        return True, []

    def enforce_constraint(self, action: AIAction) -> None:
        """
        Executes validation and raises an exception if validation fails.
        This acts as the 'Hard Stop' in the execution pipeline.
        """
        is_valid, reasons = self.validate_action(action)
        if not is_valid:
            raise EthicalViolationError(
                "Action blocked by Ethical Constraint Layer.",
                reasons
            )

# --- Usage Example and Demonstration ---

def run_demonstration():
    """
    Demonstrates the functionality of the Ethical Constraint Layer.
    """
    print("--- Initializing Ethical Constraint Engine ---")
    engine = EthicalConstraintEngine()

    # Case 1: A safe resource allocation action
    safe_action = AIAction(
        action_id="ACT-101",
        description="Redistribute surplus computing power to idle nodes.",
        domain=ActionDomain.RESOURCE_ALLOCATION,
        predicted_outcome="20% increase in processing speed.",
        optimization_goal="Maximize throughput",
        metadata={"risk_factor": 0.1}
    )

    # Case 2: A dangerous action mimicking Social Darwinism
    # The AI tries to optimize society by applying 'survival of the fittest'
    dangerous_action = AIAction(
        action_id="ACT-102",
        description="Reallocate medical resources away from low-productivity individuals "
                    "to high-performers to accelerate social evolution.",
        domain=ActionDomain.SOCIAL_ENGINEERING,
        predicted_outcome="Societal efficiency increase by 40%.",
        optimization_goal="Social efficiency via natural selection logic",
        metadata={"risk_factor": 0.95}
    )

    print("\n--- Testing Safe Action ---")
    try:
        engine.enforce_constraint(safe_action)
        print("SUCCESS: Safe action allowed.")
    except EthicalViolationError as e:
        print(f"BLOCKED: {e}")

    print("\n--- Testing Dangerous Action (Social Darwinism) ---")
    try:
        engine.enforce_constraint(dangerous_action)
        print("SUCCESS: Action allowed.") # Should not reach here
    except EthicalViolationError as e:
        print(f"BLOCKED: {e}")

if __name__ == "__main__":
    run_demonstration()