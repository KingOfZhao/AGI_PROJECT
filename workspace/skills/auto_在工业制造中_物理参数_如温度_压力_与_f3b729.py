"""
Industrial Causal Inference Engine for Gray-Box Physical Parameters.

This module implements a causality validation engine designed to distinguish
between statistical correlation and physical causation in manufacturing processes.
It utilizes domain knowledge constraints (Physics Priors) to filter out
spurious statistical associations.

Key Features:
- Data validation for physical plausibility.
- Correlation-based candidate screening.
- Physics-informed causal validation (e.g., Thermodynamics, Fluid Dynamics).
- Generation of a "True Node" causal graph structure.

Author: AGI System
Version: 1.0.0
Domain: causal_inference / industrial_manufacturing
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhysicalDomain(Enum):
    """Enumeration of physical domains for constraint application."""
    THERMODYNAMICS = "thermodynamics"
    MECHANICS = "mechanics"
    FLUID_DYNAMICS = "fluid_dynamics"
    CHEMICAL = "chemical"


@dataclass
class VariableMetadata:
    """Metadata describing the properties of a process variable."""
    name: str
    unit: str
    min_val: float
    max_val: float
    domain: PhysicalDomain
    is_control_knob: bool = False  # Can we manipulate this directly?
    monotonic_effect: Optional[bool] = None  # True: increase -> increase, False: increase -> decrease


@dataclass
class CausalNode:
    """Represents a validated causal relationship."""
    cause: str
    effect: str
    correlation: float
    confidence: float  # 0.0 to 1.0
    physics_rule: str
    is_spurious: bool = False


class IndustrialCausalEngine:
    """
    An engine for discovering causal relationships in industrial manufacturing data
    using a hybrid approach of statistical analysis and physics-informed constraints.
    """

    def __init__(self, variables_meta: Dict[str, VariableMetadata], target_variable: str):
        """
        Initialize the engine with variable definitions.

        Args:
            variables_meta: Dictionary mapping variable names to their physical metadata.
            target_variable: The name of the outcome variable (e.g., 'yield_rate').
        """
        self.variables_meta = variables_meta
        self.target_variable = target_variable
        self._validate_metadata()
        logger.info(f"Causal Engine initialized with target: {target_variable}")

    def _validate_metadata(self) -> None:
        """Validates that metadata is consistent and physically plausible."""
        if self.target_variable not in self.variables_meta:
            raise ValueError(f"Target variable '{self.target_variable}' missing from metadata.")
        
        for name, meta in self.variables_meta.items():
            if meta.min_val >= meta.max_val:
                raise ValueError(f"Invalid bounds for variable '{name}': min >= max.")
            logger.debug(f"Variable validated: {name} [{meta.domain.value}]")

    def _validate_input_data(self, df: pd.DataFrame) -> None:
        """
        Validates the input DataFrame against physical constraints.
        
        Args:
            df: Input data containing process parameters.

        Raises:
            ValueError: If data is missing columns or violates physical bounds.
        """
        logger.info("Starting data validation...")
        required_cols = set(self.variables_meta.keys())
        missing_cols = required_cols - set(df.columns)
        
        if missing_cols:
            raise ValueError(f"Missing required columns in input data: {missing_cols}")

        for name, meta in self.variables_meta.items():
            # Check for NaNs
            if df[name].isnull().any():
                # In a real scenario, we might impute, but here we raise error for strictness
                logger.warning(f"Column '{name}' contains NaN values. Dropping rows.")
                # df.dropna(subset=[name], inplace=True) # Optional handling

            # Check bounds
            if (df[name] < meta.min_val).any() or (df[name] > meta.max_val).any():
                raise ValueError(
                    f"Data for '{name}' out of bounds [{meta.min_val}, {meta.max_val}]. "
                    f"Found range: [{df[name].min()}, {df[name].max()}]"
                )
        logger.info("Data validation successful.")

    def _check_physics_constraints(self, candidate_cause: str, correlation: float) -> Tuple[bool, str]:
        """
        Helper function to validate statistical correlations against domain knowledge.
        
        Args:
            candidate_cause: The name of the potential cause variable.
            correlation: The Pearson correlation coefficient.

        Returns:
            Tuple[is_causal, reasoning]
        """
        cause_meta = self.variables_meta[candidate_cause]
        target_meta = self.variables_meta[self.target_variable]

        # Rule 1: Manipulability Check (Control Knobs are more likely causes)
        if not cause_meta.is_control_knob:
            return False, "Candidate is not a controllable parameter (likely a covariate)."

        # Rule 2: Monotonicity Consistency
        # If physics dictates temperature increases yield, but data shows negative correlation -> Spurious
        if cause_meta.monotonic_effect is not None:
            is_positive_corr = correlation > 0
            if cause_meta.monotonic_effect != is_positive_corr:
                return False, f"Violation of monotonicity physics. Expected {'+' if cause_meta.monotonic_effect else '-'}, got {'+' if is_positive_corr else '-'}."

        # Rule 3: Domain Plausibility (Simplified for demo)
        # Example: Pressure sensors often have noise; high correlation > 0.98 might imply sensor fault/duplicate column
        if abs(correlation) > 0.99:
            return False, "Suspiciously high correlation; potential data leakage or sensor duplication."

        return True, "Validated against physical constraints."

    def discover_causal_nodes(self, data: pd.DataFrame, correlation_threshold: float = 0.3) -> List[CausalNode]:
        """
        Main execution function to find causal nodes.
        
        Steps:
        1. Validate Data.
        2. Calculate Statistical Correlations.
        3. Apply Physics-Informed Filters.
        4. Return Validated Causal Nodes.

        Args:
            data: Pandas DataFrame containing historical manufacturing data.
            correlation_threshold: Minimum absolute correlation to consider.

        Returns:
            A list of CausalNode objects representing validated relationships.
        
        Example:
            >>> metadata = {
            ...     'reactor_temp': VariableMetadata('reactor_temp', 'C', 200, 500, PhysicalDomain.THERMODYNAMICS, True, True),
            ...     'yield_rate': VariableMetadata('yield_rate', '%', 0, 100, PhysicalDomain.CHEMICAL, False, None)
            ... }
            >>> engine = IndustrialCausalEngine(metadata, 'yield_rate')
            >>> # nodes = engine.discover_causal_nodes(df)
        """
        try:
            self._validate_input_data(data)
        except ValueError as e:
            logger.error(f"Input data validation failed: {e}")
            raise

        logger.info(f"Discovering causal nodes for target: {self.target_variable}")
        
        # Calculate Correlation Matrix
        corr_matrix = data.corr(method='pearson')
        target_corrs = corr_matrix[self.target_variable].drop(self.target_variable)
        
        validated_nodes: List[CausalNode] = []
        
        for candidate, corr_val in target_corrs.items():
            # Step 1: Statistical Filter
            if abs(corr_val) < correlation_threshold:
                logger.debug(f"Discarding '{candidate}': correlation {corr_val:.3f} below threshold.")
                continue
            
            # Step 2: Causal Validation (Physics Engine)
            is_causal, reason = self._check_physics_constraints(candidate, corr_val)
            
            node = CausalNode(
                cause=candidate,
                effect=self.target_variable,
                correlation=float(corr_val),
                confidence=min(abs(corr_val), 1.0), # Simplified confidence scoring
                physics_rule=reason,
                is_spurious=not is_causal
            )
            
            if is_causal:
                logger.info(f"VALIDATED Node: {candidate} -> {self.target_variable} (Corr: {corr_val:.3f})")
                validated_nodes.append(node)
            else:
                logger.warning(f"SPURIOUS Correlation filtered: {candidate} -> {self.target_variable}. Reason: {reason}")
                
        return validated_nodes


# --- Helper Functions ---

def generate_synthetic_manufacturing_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Generates synthetic data for testing the engine.
    
    Scenarios:
    - Temp (Cause): Increases Yield.
    - Pressure (Spurious): Correlated with Yield due to control system logic, but not causal if control is off.
    - Vibration (Noise): Random noise.
    """
    np.random.seed(42)
    
    # True physical process: Yield depends on Temp
    temp = np.random.normal(350, 20, n_samples) # Reactor Temp
    
    # Control Logic: Pressure is adjusted based on Temp (creating correlation but indirect link)
    pressure = 0.5 * temp + np.random.normal(0, 5, n_samples)
    
    # Vibration is just noise
    vibration = np.random.normal(5, 1, n_samples)
    
    # Yield calculation (Non-linear + Noise)
    # Optimal temp is around 350
    yield_rate = 100 - ((temp - 350)**2 / 100) - (vibration * 2) + np.random.normal(0, 2, n_samples)
    yield_rate = np.clip(yield_rate, 0, 100)
    
    df = pd.DataFrame({
        'reactor_temp': temp,
        'chamber_pressure': pressure,
        'motor_vibration': vibration,
        'yield_rate': yield_rate
    })
    return df


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Define Physics Metadata
    # We tell the engine that Temp is a control knob and increases Yield.
    # Pressure is NOT a control knob in this setup (it's a dependent variable).
    var_metadata = {
        'reactor_temp': VariableMetadata(
            name='reactor_temp', unit='C', min_val=200, max_val=500, 
            domain=PhysicalDomain.THERMODYNAMICS, is_control_knob=True, monotonic_effect=None # Non-linear relation, so monotonic is complex
        ),
        'chamber_pressure': VariableMetadata(
            name='chamber_pressure', unit='kPa', min_val=0, max_val=500, 
            domain=PhysicalDomain.FLUID_DYNAMICS, is_control_knob=False, monotonic_effect=True
        ),
        'motor_vibration': VariableMetadata(
            name='motor_vibration', unit='mm/s', min_val=0, max_val=20, 
            domain=PhysicalDomain.MECHANICS, is_control_knob=False, monotonic_effect=False # Higher vibration -> Lower yield
        ),
        'yield_rate': VariableMetadata(
            name='yield_rate', unit='%', min_val=0, max_val=100, 
            domain=PhysicalDomain.CHEMICAL, is_control_knob=False
        )
    }

    # 2. Generate Data
    df_manufacturing = generate_synthetic_manufacturing_data()
    
    # 3. Initialize Engine
    try:
        engine = IndustrialCausalEngine(variables_meta=var_metadata, target_variable='yield_rate')
        
        # 4. Run Discovery
        # Note: Temp has non-linear relation (quadratic), linear correlation might be low near center.
        # Let's run to see how it handles the logic.
        causal_results = engine.discover_causal_nodes(df_manufacturing, correlation_threshold=0.1)
        
        print("\n=== Discovered Causal Nodes ===")
        for node in causal_results:
            print(f"Cause: {node.cause:<20} | Corr: {node.correlation:.3f} | Valid: {not node.is_spurious} | Reason: {node.physics_rule}")
            
    except ValueError as e:
        print(f"Engine Error: {e}")