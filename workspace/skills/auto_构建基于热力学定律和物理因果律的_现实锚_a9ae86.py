"""
Module: reality_anchor_thermodynamics.py
Description: Constructs a "Reality Anchoring Filter" based on the laws of Thermodynamics
             and Physical Causality to validate AGI-generated predictions or world states.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhysicsViolationError(Exception):
    """Custom exception for physical law violations."""
    pass


class CausalDirection(Enum):
    """Enumeration for causal time direction."""
    FORWARD = 1
    BACKWARD = -1
    ATEMPORAL = 0


@dataclass
class PhysicsState:
    """
    Represents a physical state of a system or an AGI prediction.

    Attributes:
        id (str): Unique identifier for the state.
        timestamp (float): Simulation time.
        entropy (float): Entropy value (e.g., in J/K).
        internal_energy (float): Internal energy (e.g., in Joules).
        volume (float): Volume of the system (m^3).
        mass (float): Mass of the system (kg).
        metadata (Dict[str, Any]): Additional properties.
    """
    id: str
    timestamp: float
    entropy: float
    internal_energy: float
    volume: float
    mass: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate data types and physical boundaries after initialization."""
        if self.mass < 0:
            raise ValueError(f"Mass cannot be negative (got {self.mass})")
        if self.volume < 0:
            raise ValueError(f"Volume cannot be negative (got {self.volume})")
        if self.internal_energy < 0:
            logger.warning(f"State {self.id}: Negative internal energy detected.")


class RealityAnchorFilter:
    """
    A filter mechanism to anchor AGI reasoning to physical reality constraints.
    
    Validates state transitions based on:
    1. The Second Law of Thermodynamics (Entropy of an isolated system never decreases).
    2. Conservation of Energy (First Law).
    3. Physical Causality (Temporal consistency and propagation limits).
    """

    def __init__(self, entropy_tolerance: float = 1e-3, allow_energy_fluctuation: bool = False):
        """
        Initialize the Reality Anchor.

        Args:
            entropy_tolerance (float): Delta allowed for statistical fluctuations (microscopic systems).
            allow_energy_fluctuation (bool): If True, allows small energy violations (Heisenberg uncertainty analog).
        """
        self.entropy_tolerance = entropy_tolerance
        self.allow_energy_fluctuation = allow_energy_fluctuation
        logger.info("RealityAnchorFilter initialized with strict physics mode.")

    def _calculate_entropy_change(self, state_a: PhysicsState, state_b: PhysicsState) -> float:
        """
        Helper: Calculate the change in entropy between two states.
        ΔS = S_final - S_initial
        
        Args:
            state_a (PhysicsState): Initial state.
            state_b (PhysicsState): Final state.

        Returns:
            float: The change in entropy.
        """
        delta_s = state_b.entropy - state_a.entropy
        logger.debug(f"Entropy change calculation: {delta_s}")
        return delta_s

    def validate_thermodynamics(self, initial_state: PhysicsState, final_state: PhysicsState) -> Tuple[bool, str]:
        """
        Core Function 1: Validates state transitions against Thermodynamic laws.
        
        Checks:
        - Conservation of Energy (First Law).
        - Entropy Non-Decrease (Second Law).

        Args:
            initial_state (PhysicsState): The starting physical state.
            final_state (PhysicsState): The predicted resulting state.

        Returns:
            Tuple[bool, str]: (True, "Validation Passed") if valid, (False, "Reason") otherwise.
        """
        # Check 1: Conservation of Mass (Basic sanity check)
        if not math.isclose(initial_state.mass, final_state.mass, rel_tol=1e-5):
            return False, f"Mass conservation violated: {initial_state.mass} -> {final_state.mass}"

        # Check 2: First Law (Energy Conservation)
        # In a closed system without external work/heat, energy should be constant.
        # Here we assume a closed system context for strict anchoring.
        energy_diff = abs(final_state.internal_energy - initial_state.internal_energy)
        
        if not self.allow_energy_fluctuation:
            if not math.isclose(initial_state.internal_energy, final_state.internal_energy, rel_tol=1e-5):
                return False, f"First Law Violation: Energy not conserved (Delta: {energy_diff})"
        else:
            # Allow quantum fluctuations roughly (very permissive for AGI 'imagination')
            if energy_diff > 1e-9 * initial_state.internal_energy:
                return False, "First Law Violation: Energy variance exceeded fluctuation tolerance"

        # Check 3: Second Law (Entropy)
        # Entropy of an isolated system must increase or remain constant for reversible processes.
        delta_s = self._calculate_entropy_change(initial_state, final_state)
        
        if delta_s < -self.entropy_tolerance:
            return False, f"Second Law Violation: Entropy decreased by {abs(delta_s)}"

        logger.info(f"Thermodynamic validation passed for transition {initial_state.id} -> {final_state.id}")
        return True, "Thermodynamic laws adhered to."

    def check_causality(self, cause_event: PhysicsState, effect_event: PhysicsState, max_signal_speed: float = 3.0e8) -> Tuple[bool, str]:
        """
        Core Function 2: Validates causal relationships based on time and distance (Light cone check).
        
        Ensures that 'effect' happens after 'cause' and within the bounds of the speed of light/information.

        Args:
            cause_event (PhysicsState): The causal event.
            effect_event (PhysicsState): The resulting event.
            max_signal_speed (float): Maximum speed of information propagation (default: speed of light).

        Returns:
            Tuple[bool, str]: (True, "Reason") if causal, (False, "Reason") if violation.
        """
        # Time direction check
        dt = effect_event.timestamp - cause_event.timestamp
        if dt < 0:
            return False, "Causality Violation: Effect precedes cause (Temporal inversion)."

        # Spatial distance check (assuming 1D or Euclidean distance in metadata)
        # For simplicity, we assume 'position' is in metadata['position'] as a float or coordinate
        pos_cause = cause_event.metadata.get("position", 0.0)
        pos_effect = effect_event.metadata.get("position", 0.0)
        
        # Handle potential tuple/list coordinates
        if isinstance(pos_cause, (list, tuple)) and isinstance(pos_effect, (list, tuple)):
            distance = math.sqrt(sum((c - e)**2 for c, e in zip(pos_cause, pos_effect)))
        else:
            distance = abs(pos_effect - pos_cause)

        # Light Cone Check
        # Distance <= Speed * Time
        if dt == 0:
            if distance > 0:
                return False, "Causality Violation: Instantaneous action at a distance."
        else:
            if distance / dt > max_signal_speed:
                return False, f"Causality Violation: Signal speed {distance/dt} exceeds limit {max_signal_speed}."

        logger.info(f"Causality check passed between {cause_event.id} and {effect_event.id}")
        return True, "Causal structure valid."


# Usage Example
if __name__ == "__main__":
    # Initialize the anchor filter
    anchor = RealityAnchorFilter(entropy_tolerance=0.01)

    # Define a valid physical transition (e.g., gas expansion)
    state_t0 = PhysicsState(
        id="sys_001_t0",
        timestamp=0.0,
        entropy=10.0,
        internal_energy=100.0,
        volume=1.0,
        mass=1.0,
        metadata={"position": 0.0}
    )

    # Predicted future state (Valid: Entropy increases, Energy conserved)
    state_t1_valid = PhysicsState(
        id="sys_001_t1",
        timestamp=1.0,
        entropy=12.0,  # Entropy increases
        internal_energy=100.0,  # Energy conserved
        volume=1.2,
        mass=1.0,
        metadata={"position": 0.5}  # Moved slow (sub-light)
    )

    # Predicted future state (Invalid: Entropy decreases - "Time Crystal" false positive)
    state_t1_invalid = PhysicsState(
        id="sys_001_t1_bad",
        timestamp=1.0,
        entropy=9.0,  # Decreased!
        internal_energy=100.0,
        volume=1.0,
        mass=1.0,
        metadata={"position": 0.0}
    )

    print("--- Running Thermodynamic Validation ---")
    
    # Test Valid Case
    is_valid, msg = anchor.validate_thermodynamics(state_t0, state_t1_valid)
    print(f"Valid State Check: {is_valid} | {msg}")

    # Test Invalid Case
    is_valid_bad, msg_bad = anchor.validate_thermodynamics(state_t0, state_t1_invalid)
    print(f"Invalid State Check: {is_valid_bad} | {msg_bad}")

    print("\n--- Running Causality Check ---")
    
    # Test Causality (Valid)
    is_causal, c_msg = anchor.check_causality(state_t0, state_t1_valid)
    print(f"Valid Causality Check: {is_causal} | {c_msg}")

    # Test FTL (Faster Than Light) Violation
    state_ftl = PhysicsState(
        id="sys_002",
        timestamp=1.0,
        entropy=15.0,
        internal_energy=100.0,
        volume=1.0,
        mass=1.0,
        metadata={"position": 5.0e8}  # Moved 500 million meters in 1 second (c ~ 3e8)
    )
    is_causal_ftl, c_msg_ftl = anchor.check_causality(state_t0, state_ftl)
    print(f"FTL Causality Check: {is_causal_ftl} | {c_msg_ftl}")