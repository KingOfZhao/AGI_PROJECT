"""
Module: intuitive_to_precise_interface.py

This module serves as a semantic projection interface designed to bridge the gap
between human fuzzy intuition (natural language descriptions) and precise machine
execution parameters. It treats natural language concepts as probability
distributions and projects them onto deterministic physical parameter vectors.

Core Concepts:
- Fuzzy Intuition: Concepts like "slightly larger", "heavy", "smooth".
- Projection Operator: A statistical mapping function (e.g., Gaussian, Beta).
- Deterministic Output: Precise floating-point values or integers for hardware control.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class ParameterConstraint:
    """Defines the boundary conditions for a physical parameter."""
    min_val: float
    max_val: float
    unit: str
    precision: int = 4  # Decimal places

@dataclass
class ProjectionResult:
    """Container for the output of the projection operator."""
    parameter_name: str
    raw_value: float
    clipped_value: float
    confidence: float  # 0.0 to 1.0, derived from probability density
    unit: str
    distribution_type: str

# --- Helper Functions ---

def _parse_adjective_scale(keyword: str) -> Tuple[float, float]:
    """
    Helper: Maps linguistic keywords to a relative mean and variance factor.
    
    Returns:
        Tuple[float, float]: (relative_mean_shift, variance_factor)
        
    Example:
        "huge" -> (0.9, 0.1) (High value, low variance/certainty)
        "slightly" -> (0.55, 0.3) (Mid-high value, high variance/uncertainty)
    """
    keyword = keyword.lower().strip()
    
    # Regex patterns for intensity
    if re.search(r"(very|super|extremely|huge|massive)", keyword):
        return (0.95, 0.05)
    elif re.search(r"(quite|rather|big|strong)", keyword):
        return (0.80, 0.10)
    elif re.search(r"(slightly|a bit|little|gentle)", keyword):
        return (0.60, 0.20)
    elif re.search(r"(medium|moderate|average)", keyword):
        return (0.50, 0.15)
    elif re.search(r"(small|tiny|low|weak)", keyword):
        return (0.20, 0.10)
    elif re.search(r"(very small|minimal|micro)", keyword):
        return (0.05, 0.05)
    else:
        # Default fallback for unknown adjectives
        logger.warning(f"Unknown adjective '{keyword}', defaulting to neutral distribution.")
        return (0.5, 0.3)

# --- Core Functions ---

class SemanticProjector:
    """
    The core interface class that transforms fuzzy natural language instructions
    into structured engineering parameters using probabilistic projection operators.
    """

    def __init__(self, constraints: Dict[str, ParameterConstraint]):
        """
        Initialize the projector with specific engineering constraints.
        
        Args:
            constraints: A dictionary mapping parameter names to their physical limits.
        """
        if not constraints:
            raise ValueError("Constraints dictionary cannot be empty.")
        self.constraints = constraints
        logger.info(f"SemanticProjector initialized with {len(constraints)} parameters.")

    def _validate_input(self, param_name: str, context: Dict[str, Any]) -> None:
        """Validates that the parameter exists and context is valid."""
        if param_name not in self.constraints:
            raise KeyError(f"Parameter '{param_name}' not found in defined constraints.")
        if not isinstance(context, dict):
            raise TypeError("Context must be a dictionary.")

    def project_gaussian(
        self, 
        param_name: str, 
        description: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ProjectionResult:
        """
        Projects a natural language description onto a parameter using a Gaussian
        (Normal) distribution model.
        
        The 'description' determines the mean (center) of the distribution relative
        to the parameter's min/max range. The 'intensity' of the word determines
        the variance (uncertainty).
        
        Args:
            param_name: The target parameter key (e.g., 'velocity', 'gripper_force').
            description: Natural language string (e.g., "very fast", "slightly open").
            context: Optional context for dynamic adjustment (not used in basic impl).
            
        Returns:
            ProjectionResult: The structured deterministic result.
            
        Raises:
            KeyError: If param_name is invalid.
            ValueError: If calculation fails.
        """
        self._validate_input(param_name, context or {})
        constraint = self.constraints[param_name]
        
        logger.debug(f"Projecting '{description}' for parameter '{param_name}'")
        
        try:
            # 1. Analyze Semantics
            rel_mean, variance_factor = _parse_adjective_scale(description)
            
            # 2. Map Relative to Absolute Range
            range_span = constraint.max_val - constraint.min_val
            abs_mean = constraint.min_val + (range_span * rel_mean)
            
            # 3. Determine Standard Deviation (Uncertainty)
            # High variance_factor = high uncertainty = wide distribution
            std_dev = range_span * variance_factor
            
            # 4. Sample / Determine Value
            # Here we take the mean as the deterministic representation, 
            # but acknowledge the std_dev in confidence.
            projected_value = abs_mean
            
            # 5. Clipping and Boundary Enforcement
            clipped_value = max(constraint.min_val, min(constraint.max_val, projected_value))
            
            # 6. Calculate Confidence
            # Simple heuristic: confidence is inversely proportional to variance relative to range
            # Also penalize if we clipped the value (meaning the intuition exceeded physical limits)
            clip_penalty = 0.0
            if clipped_value != projected_value:
                clip_penalty = 0.5
            
            confidence = round(max(0.0, 1.0 - variance_factor - clip_penalty), 4)
            
            # 7. Formatting
            final_value = round(clipped_value, constraint.precision)
            
            return ProjectionResult(
                parameter_name=param_name,
                raw_value=projected_value,
                clipped_value=final_value,
                confidence=confidence,
                unit=constraint.unit,
                distribution_type="Gaussian"
            )
            
        except Exception as e:
            logger.error(f"Projection failed for {param_name}: {e}")
            raise ValueError(f"Semantic projection failed: {e}")

    def project_beta_distribution(
        self, 
        param_name: str, 
        mode_description: str, 
        concentration: float = 2.0
    ) -> ProjectionResult:
        """
        Projects description using a Beta distribution model (bounded [0,1]).
        Useful for 'percentage' or 'ratio' based controls where hard bounds are absolute.
        
        Args:
            param_name: The target parameter key.
            mode_description: Linguistic description mapped to mode of distribution.
            concentration: Alpha/Beta concentration parameter (higher = more peaked).
            
        Returns:
            ProjectionResult: Structured result.
        """
        self._validate_input(param_name, {})
        constraint = self.constraints[param_name]
        
        # Normalize target to 0-1 range
        rel_mode, _ = _parse_adjective_scale(mode_description)
        
        # Ensure mode is within (0, 1) for Beta distribution validity
        rel_mode = max(0.01, min(0.99, rel_mode))
        
        # Approximate Beta distribution parameters (alpha, beta) from mode
        # Mode = (alpha - 1) / (alpha + beta - 2)
        # Using a simplified approximation where sum = concentration * 2
        common_val = concentration * 2
        alpha = rel_mode * common_val + 1
        beta = (1 - rel_mode) * common_val + 1
        
        # Expected Value (Mean) for Beta: alpha / (alpha + beta)
        expected_val_01 = alpha / (alpha + beta)
        
        # Map back to physical range
        range_span = constraint.max_val - constraint.min_val
        projected_value = constraint.min_val + (expected_val_01 * range_span)
        
        clipped_value = max(constraint.min_val, min(constraint.max_val, projected_value))
        
        return ProjectionResult(
            parameter_name=param_name,
            raw_value=projected_value,
            clipped_value=round(clipped_value, constraint.precision),
            confidence=round(concentration / 10.0, 4), # Heuristic confidence
            unit=constraint.unit,
            distribution_type="Beta"
        )

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define Engineering Constraints (The "Machine" Context)
    hardware_constraints = {
        "servo_speed": ParameterConstraint(0.0, 100.0, "rpm", precision=1),
        "gripper_aperture": ParameterConstraint(0.0, 150.0, "mm", precision=2),
        "led_intensity": ParameterConstraint(0.0, 1.0, "duty_cycle", precision=3)
    }

    # 2. Initialize the Interface
    projector = SemanticProjector(hardware_constraints)

    # 3. Process Human Intuition (The "Human" Input)
    human_instructions = [
        ("servo_speed", "very fast"),
        ("servo_speed", "slow and steady"),
        ("gripper_aperture", "slightly open"),
        ("gripper_aperture", "huge opening"),
        ("led_intensity", "medium brightness")
    ]

    print(f"{'Parameter':<20} | {'Input':<15} | {'Output Value':<12} | {'Unit':<5} | {'Confidence':<10}")
    print("-" * 75)

    for param, desc in human_instructions:
        try:
            # Select projection method based on parameter type
            if param == "led_intensity":
                result = projector.project_beta_distribution(param, desc)
            else:
                result = projector.project_gaussian(param, desc)
            
            print(f"{result.parameter_name:<20} | {desc:<15} | {result.clipped_value:<12} | {result.unit:<5} | {result.confidence:<10}")
        except Exception as e:
            print(f"Error processing {param}: {e}")