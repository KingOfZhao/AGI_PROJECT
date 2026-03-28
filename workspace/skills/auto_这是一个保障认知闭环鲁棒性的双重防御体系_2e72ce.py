"""
Module: auto_cognitive_robustness_defense.py

Description:
    A Dual-Defense System for Ensuring the Robustness of the Cognitive Closed-Loop.
    
    This system implements a sophisticated two-layer defense mechanism:
    1. Outer Layer (Semantic-Form Validation): Bridges the "semantic gap" between natural 
       language intent and executable logic. It converts fuzzy logic (e.g., "smooth", "fast") 
       into quantifiable metrics and validates structural integrity.
    2. Inner Layer (Structural Dynamics Seismic-Resistance): Inspired by earthquake-resistant 
       building design. It establishes a "Yield Mechanism" within the neural processing modules. 
       Upon encountering adversarial samples or high-noise data, it actively "fractures" or 
       "softens" non-core modules to preserve the integrity of core logic.

Author: AGI System Core Engineering
Version: 2.0 (2e72ce)
License: MIT
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# --- Configuration & Constants ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("CognitiveDefenseSystem")

# --- Data Structures ---

class DefenseAction(Enum):
    """Enumeration of possible defense actions."""
    SAFE = 0
    WARNING = 1
    SOFTEN = 2      # Reduce weights/importance of non-core modules
    FRACTURE = 3    # Temporarily isolate non-core modules
    SHUTDOWN = 4    # Critical failure

@dataclass
class SemanticSpec:
    """Specification for semantic validation."""
    intent: str
    constraints: Dict[str, Any]
    critical_fields: List[str]

@dataclass
class SystemState:
    """Represents the current state of the cognitive system modules."""
    core_load: float = 0.0          # 0.0 to 1.0
    peripheral_noise: float = 0.0   # 0.0 to 1.0
    anomaly_score: float = 0.0      # 0.0 to 1.0
    active_modules: List[str] = field(default_factory=list)

@dataclass
class DefenseReport:
    """Report generated after defense checks."""
    is_valid: bool
    action: DefenseAction
    details: str
    quantified_metrics: Dict[str, float] = field(default_factory=dict)

# --- Core Layer 1: Semantic-Form Validation ---

class SemanticValidator:
    """
    Outer Defense: Semantic-Form Validation.
    
    Transforms fuzzy natural language requirements into strict, quantifiable 
    engineering specifications and validates input data structures.
    """

    def __init__(self, mapping_rules: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initialize the validator with mapping rules.
        
        Args:
            mapping_rules: Rules to map fuzzy terms (e.g., 'fast') to values.
        """
        self.mapping_rules = mapping_rules or self._default_rules()
        logger.info("SemanticValidator initialized with %d rules.", len(self.mapping_rules))

    @staticmethod
    def _default_rules() -> Dict[str, Dict[str, float]]:
        """Default fuzzy-to-quantitative mapping."""
        return {
            "latency": {"fast": 0.05, "normal": 0.2, "slow": 1.0},
            "accuracy": {"high": 0.99, "medium": 0.95, "low": 0.80},
            "smoothness": {"fluid": 0.01, "jagged": 0.5} # Variance threshold
        }

    def _quantify_intent(self, intent_desc: str) -> Dict[str, float]:
        """
        Helper: Converts natural language intent descriptions to metrics.
        
        Args:
            intent_desc: String containing descriptors like "fast response".
            
        Returns:
            A dictionary of calculated metrics.
        """
        metrics = {}
        intent_lower = intent_desc.lower()
        
        for category, rules in self.mapping_rules.items():
            for term, value in rules.items():
                # Simple regex matching for demonstration
                if re.search(rf'\b{term}\b', intent_lower):
                    metrics[f"target_{category}"] = value
                    logger.debug(f"Mapped term '{term}' to value {value} in category '{category}'")
        
        return metrics

    def validate_structural_integrity(self, data: Dict[str, Any], spec: SemanticSpec) -> DefenseReport:
        """
        Validates data against the semantic specification.
        
        Args:
            data: The input data dictionary to validate.
            spec: The SemanticSpec object defining requirements.
            
        Returns:
            DefenseReport containing validation results.
        """
        if not isinstance(data, dict):
            return DefenseReport(False, DefenseAction.SHUTDOWN, "Input data must be a dictionary.")

        # 1. Quantify the intent
        metrics = self._quantify_intent(spec.intent)
        
        # 2. Check critical fields existence
        missing_fields = [f for f in spec.critical_fields if f not in data]
        if missing_fields:
            msg = f"Missing critical semantic fields: {missing_fields}"
            logger.warning(msg)
            return DefenseReport(False, DefenseAction.SHUTDOWN, msg, metrics)
            
        # 3. Check constraints (Boundary checks)
        for key, constraint in spec.constraints.items():
            if key in data:
                val = data[key]
                if 'min' in constraint and val < constraint['min']:
                    return DefenseReport(False, DefenseAction.FRACTURE, f"Value {val} for {key} below min threshold.", metrics)
                if 'max' in constraint and val > constraint['max']:
                     return DefenseReport(False, DefenseAction.WARNING, f"Value {val} for {key} exceeds max threshold.", metrics)

        logger.info("Semantic validation passed. Metrics: %s", metrics)
        return DefenseReport(True, DefenseAction.SAFE, "Semantic validation successful.", metrics)


# --- Core Layer 2: Structural Dynamics Seismic-Resistance ---

class SeismicResistor:
    """
    Inner Defense: Structural Dynamics Seismic-Resistance.
    
    Monitors system stress and implements 'Yield Mechanisms'. 
    Protects core logic by sacrificing non-essential modules during high anomaly loads.
    """
    
    def __init__(self, yield_threshold: float = 0.75, fracture_threshold: float = 0.95):
        """
        Initialize the resistor.
        
        Args:
            yield_threshold: Stress level (0-1) to start softening non-core modules.
            fracture_threshold: Stress level (0-1) to cut off non-core modules.
        """
        self.yield_threshold = yield_threshold
        self.fracture_threshold = fracture_threshold
        self.non_core_modules = ["creative_gen", "long_term_memory_index", "style_transfer"]
        self.core_modules = ["logic_inference", "safety_check", "io_bindings"]
        logger.info("SeismicResistor ready. Yield: %.2f, Fracture: %.2f", yield_threshold, fracture_threshold)

    def _calculate_stress_level(self, state: SystemState) -> float:
        """
        Helper: Calculates the overall structural stress based on system state.
        
        Args:
            state: Current SystemState.
            
        Returns:
            A float representing stress level (0.0 to 1.0).
        """
        # Weighted sum of load and noise
        stress = (state.core_load * 0.5) + (state.peripheral_noise * 0.3) + (state.anomaly_score * 0.2)
        return min(max(stress, 0.0), 1.0)

    def absorb_shock(self, state: SystemState) -> DefenseReport:
        """
        Main defense logic. Determines if the system needs to yield or fracture.
        
        Args:
            state: Current SystemState containing sensor readings.
            
        Returns:
            DefenseReport recommending specific defense actions.
        """
        stress = self._calculate_stress_level(state)
        logger.info("Monitoring structural stress: %.3f", stress)

        if stress >= self.fracture_threshold:
            msg = (f"CRITICAL: Stress {stress:.2f} > Fracture Threshold. "
                   f"Isolating non-core modules: {self.non_core_modules}")
            logger.error(msg)
            return DefenseReport(
                False, 
                DefenseAction.FRACTURE, 
                msg, 
                {"active_modules": self.core_modules} # Only core remains
            )
        
        elif stress >= self.yield_threshold:
            msg = (f"WARNING: Stress {stress:.2f} > Yield Threshold. "
                   f"Softening non-core module outputs.")
            logger.warning(msg)
            return DefenseReport(
                True, 
                DefenseAction.SOFTEN, 
                msg, 
                {"reduction_factor": 0.5} # Reduce influence of non-core
            )

        return DefenseReport(True, DefenseAction.SAFE, "System operating within safe structural limits.")


# --- Main Controller ---

class CognitiveDefenseController:
    """
    Facade for the Dual-Defense System.
    """
    
    def __init__(self):
        self.validator = SemanticValidator()
        self.resistor = SeismicResistor()
        
    def process_input(self, raw_data: Dict, intent: str, sys_state: SystemState) -> Tuple[bool, str]:
        """
        Processes input through both defense layers.
        
        Args:
            raw_data: Input data.
            intent: Natural language intent.
            sys_state: Current system state object.
            
        Returns:
            Tuple of (Success Boolean, Message).
        """
        # Layer 1: Semantic Validation
        spec = SemanticSpec(
            intent=intent,
            constraints={"confidence": {"min": 0.0, "max": 1.0}},
            critical_fields=["task_id", "payload"]
        )
        
        val_report = self.validator.validate_structural_integrity(raw_data, spec)
        if not val_report.is_valid:
            return False, f"Validation Failed: {val_report.details}"
            
        # Layer 2: Structural Dynamics
        dyn_report = self.resistor.absorb_shock(sys_state)
        
        if dyn_report.action == DefenseAction.FRACTURE:
            # In a real system, this would trigger module unloading
            return False, f"Structural Failure Triggered: {dyn_report.details}"
            
        return True, f"Processing OK. Status: {dyn_report.action.name}"


# --- Usage Example ---

if __name__ == "__main__":
    # Setup logging to see output
    logging.basicConfig(level=logging.DEBUG)
    
    # 1. Initialize System
    controller = CognitiveDefenseController()
    
    # 2. Define Input Data
    user_data = {
        "task_id": "AGI-TASK-001",
        "payload": "Execute maneuver",
        "confidence": 0.98,
        "source": "user_interface"
    }
    
    # 3. Define System State (Simulating a high-noise environment)
    # Try changing anomaly_score to 0.99 to trigger FRACTURE
    current_state = SystemState(
        core_load=0.4,
        peripheral_noise=0.6,
        anomaly_score=0.2, 
        active_modules=["logic_inference", "creative_gen", "style_transfer"]
    )
    
    # 4. Run Defense System
    success, message = controller.process_input(
        raw_data=user_data,
        intent="Execute with high accuracy and fast latency",
        sys_state=current_state
    )
    
    print("-" * 60)
    print(f"Operation Success: {success}")
    print(f"System Message: {message}")
    print("-" * 60)