"""
Module: auto_开发_意外即发现_的反向归因引擎_用于分_bc975d
Description: Serendipity Discovery Engine - Analyzes execution deviations to detect
             potential unknown physical laws or hidden environmental variables.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SerendipityEngine")


class DeviationType(Enum):
    """Classification of the detected deviation."""
    SYSTEMATIC_ERROR = "Systematic Error"
    RANDOM_NOISE = "Random Noise"
    ANOMALY_PATTERN = "Anomaly Pattern"
    POTENTIAL_DISCOVERY = "Potential Discovery"


@dataclass
class PhysicalContext:
    """Defines the context of the physical execution."""
    timestamp: float
    expected_state: np.ndarray
    actual_state: np.ndarray
    environmental_variables: Dict[str, float] = field(default_factory=dict)
    known_laws_params: Dict[str, float] = field(default_factory=dict)


@dataclass
class AttributionResult:
    """Result of the reverse attribution analysis."""
    is_discovery: bool
    deviation_type: DeviationType
    confidence: float
    residual_vector: np.ndarray
    suspected_variables: List[str]
    analysis_report: str


def _validate_input_data(context: PhysicalContext) -> bool:
    """
    Helper function to validate input data integrity and dimensions.
    
    Args:
        context (PhysicalContext): The input context object.
        
    Returns:
        bool: True if validation passes.
        
    Raises:
        ValueError: If data shapes mismatch or contain invalid values.
    """
    if context.expected_state.shape != context.actual_state.shape:
        raise ValueError("State vectors must have the same dimensions.")
    
    if np.any(np.isnan(context.expected_state)) or np.any(np.isnan(context.actual_state)):
        raise ValueError("State vectors contain NaN values.")
    
    if not context.environmental_variables:
        logger.warning("No environmental variables provided. Analysis may be limited.")
        
    return True


def _calculate_residual_significance(residuals: np.ndarray, noise_threshold: float) -> Tuple[float, bool]:
    """
    Helper function to calculate statistical significance of residuals.
    
    Args:
        residuals (np.ndarray): Difference between actual and expected.
        noise_threshold (float): Threshold for noise filtering.
        
    Returns:
        Tuple[float, bool]: Magnitude and significance flag.
    """
    magnitude = np.linalg.norm(residuals)
    is_significant = magnitude > noise_threshold
    return magnitude, is_significant


class ReverseAttributionEngine:
    """
    Core engine for analyzing physical execution deviations.
    
    This engine attempts to determine if a deviation is a simple error or 
    evidence of an unknown variable/law (Serendipity).
    """
    
    def __init__(self, sensitivity: float = 0.05, history_size: int = 100):
        """
        Initialize the engine.
        
        Args:
            sensitivity (float): Detection sensitivity (0.0 to 1.0).
            history_size (int): Max history size for baseline calibration.
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0.")
            
        self.sensitivity = sensitivity
        self._residual_history: List[np.ndarray] = []
        self._history_size = history_size
        logger.info(f"ReverseAttributionEngine initialized with sensitivity {sensitivity}")

    def analyze_deviation(self, context: PhysicalContext) -> AttributionResult:
        """
        Main function to analyze a specific execution deviation.
        
        Args:
            context (PhysicalContext): Data of the physical execution.
            
        Returns:
            AttributionResult: The complete analysis result.
            
        Raises:
            RuntimeError: If analysis fails unexpectedly.
        """
        try:
            _validate_input_data(context)
            
            # 1. Calculate Base Residuals
            residuals = context.actual_state - context.expected_state
            self._update_history(residuals)
            
            # 2. Statistical Analysis
            noise_threshold = self._estimate_dynamic_noise_threshold()
            magnitude, is_significant = _calculate_residual_significance(residuals, noise_threshold)
            
            if not is_significant:
                return self._create_result(False, DeviationType.RANDOM_NOISE, 0.99, residuals)

            # 3. Pattern Matching (Reverse Attribution)
            # Check if residuals correlate with known env vars or suggest new ones
            correlation_score, suspected_vars = self._check_environmental_correlation(
                residuals, 
                context.environmental_variables
            )
            
            # 4. Determine Discovery Status
            # If magnitude is high and correlation with existing vars is low, it's a potential discovery
            is_discovery = (magnitude > (noise_threshold * 2)) and (correlation_score < 0.3)
            
            dev_type = DeviationType.POTENTIAL_DISCOVERY if is_discovery else DeviationType.SYSTEMATIC_ERROR
            
            return self._create_result(
                is_discovery, 
                dev_type, 
                min(magnitude * 10, 1.0), # Simple confidence heuristic
                residuals,
                suspected_vars
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise RuntimeError(f"Engine analysis error: {str(e)}") from e

    def _update_history(self, residuals: np.ndarray) -> None:
        """Maintains a sliding window of residuals for baseline calculation."""
        self._residual_history.append(residuals)
        if len(self._residual_history) > self._history_size:
            self._residual_history.pop(0)

    def _estimate_dynamic_noise_threshold(self) -> float:
        """
        Estimates the noise threshold based on historical data.
        Returns a default value if history is insufficient.
        """
        if len(self._residual_history) < 5:
            return 0.1 * self.sensitivity # Default baseline
            
        # Calculate standard deviation of historical norms
        norms = [np.linalg.norm(r) for r in self._residual_history]
        return np.std(norms) + (np.mean(norms) * self.sensitivity)

    def _check_environmental_correlation(self, 
                                         residuals: np.ndarray, 
                                         env_vars: Dict[str, float]) -> Tuple[float, List[str]]:
        """
        Checks if residuals can be explained by environmental variables.
        
        Returns:
            Tuple[float, List[str]]: Max correlation score and list of suspected variable keys.
        """
        if not env_vars:
            return 0.0, []
            
        max_corr = 0.0
        suspected = []
        res_norm = residuals / (np.linalg.norm(residuals) + 1e-9)
        
        # Simple projection check (mock correlation logic)
        for key, value in env_vars.items():
            # In a real scenario, this would involve vector projection or regression
            # Here we simulate a correlation score based on scalar magnitude matching
            mock_correlation = 1.0 - abs(value - np.mean(residuals)) / (abs(value) + 1e-9)
            if mock_correlation > 0.6:
                suspected.append(key)
                max_corr = max(max_corr, mock_correlation)
                
        return max_corr, suspected

    def _create_result(self, 
                       is_disc: bool, 
                       dtype: DeviationType, 
                       conf: float, 
                       res: np.ndarray, 
                       susp_vars: Optional[List[str]] = None) -> AttributionResult:
        """Constructs the result object."""
        report = (
            f"Analysis Complete. Type: {dtype.value}. "
            f"Discovery Potential: {'Yes' if is_disc else 'No'}. "
            f"Confidence: {conf:.2f}."
        )
        if susp_vars:
            report += f" Suspected factors: {', '.join(susp_vars)}."
            
        logger.info(report)
        
        return AttributionResult(
            is_discovery=is_disc,
            deviation_type=dtype,
            confidence=conf,
            residual_vector=res,
            suspected_variables=susp_vars or [],
            analysis_report=report
        )

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Engine
    engine = ReverseAttributionEngine(sensitivity=0.1)
    
    # 2. Prepare Data (Mock Data)
    # Scenario: A robot moves, but drifts consistently to the right by an unknown force
    expected = np.array([10.0, 0.0, 5.0])
    # Actual shows a z-axis deviation not explained by current model
    actual = np.array([10.0, 0.0, 5.8]) 
    env_data = {"temp": 25.0, "wind_speed": 0.5}
    
    context = PhysicalContext(
        timestamp=1678900000.0,
        expected_state=expected,
        actual_state=actual,
        environmental_variables=env_data
    )
    
    # 3. Run Analysis
    try:
        result = engine.analyze_deviation(context)
        print(f"\n--- Report ---\n{result.analysis_report}")
        print(f"Residual Norm: {np.linalg.norm(result.residual_vector):.4f}")
    except Exception as e:
        print(f"Critical Error: {e}")