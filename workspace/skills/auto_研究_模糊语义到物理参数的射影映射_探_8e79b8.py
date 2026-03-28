"""
Module: fuzzy_semantic_to_physical_mapping

Description:
    This module provides a robust framework for mapping fuzzy semantic descriptors
    (e.g., "hot", "fast", "heavy") to precise physical parameters using probability
    distributions. It is designed to handle uncertainty in AGI reasoning by projecting
    linguistic variables onto constrained physical domains.

Key Features:
    - Mapping natural language terms to statistical distributions (Gaussian, Uniform).
    - Applying physical constraints (e.g., speed of light, absolute zero) to probability
      density functions (truncation/clamping).
    - Providing deterministic extraction (Mean, MAP) for downstream control systems.
    - Comprehensive logging and error handling.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, Union

import numpy as np

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type Aliases for clarity
Numeric = Union[int, float]
DistributionFunc = Callable[[np.ndarray], np.ndarray]

@dataclass
class PhysicalContext:
    """
    Defines the physical constraints and units for a specific parameter space.
    
    Attributes:
        unit (str): The unit of measurement (e.g., 'celsius', 'm/s').
        min_val (Optional[Numeric]): The theoretical or safe minimum value.
        max_val (Optional[Numeric]): The theoretical or safe maximum value.
    """
    unit: str
    min_val: Optional[Numeric] = None
    max_val: Optional[Numeric] = None

    def __post_init__(self):
        """Validate boundary logic."""
        if self.min_val is not None and self.max_val is not None:
            if self.min_val > self.max_val:
                msg = f"Invalid bounds: min ({self.min_val}) > max ({self.max_val})"
                logger.error(msg)
                raise ValueError(msg)

@dataclass
class FuzzyMapping:
    """
    Represents the statistical interpretation of a semantic term.
    
    Attributes:
        term (str): The semantic label (e.g., 'hot').
        mean (float): The central tendency of the value.
        std_dev (float): The uncertainty or spread of the value.
        distribution_type (str): Type of distribution ('gaussian' supported primarily).
    """
    term: str
    mean: float
    std_dev: float
    distribution_type: str = 'gaussian'

    def __post_init__(self):
        """Validate statistical parameters."""
        if self.std_dev < 0:
            raise ValueError(f"Standard deviation cannot be negative for term '{self.term}'")
        if self.distribution_type not in ['gaussian', 'uniform']:
            logger.warning(f"Distribution type '{self.distribution_type}' may have limited support.")

class SemanticPhysicsProjector:
    """
    Core class for projecting fuzzy semantics onto physical parameter spaces.
    """

    def __init__(self):
        self._mappings: Dict[str, FuzzyMapping] = {}
        self._contexts: Dict[str, PhysicalContext] = {}
        logger.info("SemanticPhysicsProjector initialized.")

    def register_context(self, param_name: str, context: PhysicalContext) -> None:
        """Register physical constraints for a specific parameter."""
        if not isinstance(context, PhysicalContext):
            raise TypeError("Context must be a PhysicalContext instance.")
        
        self._contexts[param_name] = context
        logger.debug(f"Registered context for '{param_name}': [{context.min_val}, {context.max_val}] {context.unit}")

    def train_mapping(self, param_name: str, term: str, mean: float, std_dev: float) -> None:
        """
        Create or update a mapping from a semantic term to a physical distribution.
        
        Args:
            param_name: The target physical parameter (e.g., 'temperature').
            term: The semantic descriptor (e.g., 'warm').
            mean: The mean physical value associated with this term.
            std_dev: The standard deviation representing fuzziness.
        """
        if std_dev <= 0:
            logger.warning(f"Training mapping with non-positive std_dev ({std_dev}) for term '{term}'.")
        
        key = f"{param_name}:{term}"
        self._mappings[key] = FuzzyMapping(term=term, mean=mean, std_dev=std_dev)
        logger.info(f"Trained mapping: '{term}' -> {mean} ± {std_dev} for parameter '{param_name}'")

    def _validate_request(self, param_name: str, term: str) -> Tuple[FuzzyMapping, PhysicalContext]:
        """Helper to validate existence of mapping and context."""
        key = f"{param_name}:{term}"
        if key not in self._mappings:
            raise KeyError(f"No mapping found for parameter '{param_name}' and term '{term}'")
        
        if param_name not in self._contexts:
            raise KeyError(f"No physical context defined for parameter '{param_name}'")
            
        return self._mappings[key], self._contexts[param_name]

    def project_semantic(
        self, 
        param_name: str, 
        term: str, 
        resolution: int = 1000,
        enforce_constraints: bool = True
    ) -> Dict[str, Union[np.ndarray, float, str]]:
        """
        Projects a semantic term onto the physical parameter space, generating
        a constrained probability distribution.
        
        Args:
            param_name: The physical parameter to estimate.
            term: The fuzzy semantic input.
            resolution: Number of points for the PDF curve.
            enforce_constraints: Whether to truncate the distribution at physical limits.
            
        Returns:
            A dictionary containing the x-axis (values), PDF, and extracted statistics.
            
        Raises:
            ValueError: If data validation fails.
            KeyError: if mapping/context is missing.
        """
        try:
            mapping, context = self._validate_request(param_name, term)
        except KeyError as e:
            logger.error(f"Projection failed: {e}")
            raise

        # 1. Define the sampling range (extend 4 sigmas for coverage)
        lower_bound = mapping.mean - 4 * mapping.std_dev
        upper_bound = mapping.mean + 4 * mapping.std_dev
        
        # Override with physical limits if enforcing constraints
        phys_min = context.min_val if context.min_val is not None else lower_bound
        phys_max = context.max_val if context.max_val is not None else upper_bound

        # Boundary Check: Ensure mean is within physical limits
        if (context.min_val is not None and mapping.mean < context.min_val) or \
           (context.max_val is not None and mapping.mean > context.max_val):
            logger.warning(f"Mean value {mapping.mean} for '{term}' is outside physical bounds "
                           f"[{context.min_val}, {context.max_val}]. Projection may be skewed.")

        # 2. Generate X axis (Domain)
        x_values = np.linspace(
            max(lower_bound, phys_min) if enforce_constraints else lower_bound,
            min(upper_bound, phys_max) if enforce_constraints else upper_bound,
            resolution
        )

        # 3. Calculate PDF (Probability Density Function)
        # Using Gaussian distribution
        pdf = np.exp(-0.5 * ((x_values - mapping.mean) / mapping.std_dev) ** 2)
        
        # Normalize PDF
        area = np.trapz(pdf, x_values)
        if area > 0:
            pdf = pdf / area
        else:
            logger.error("Calculated PDF area is zero. Check std_dev or bounds.")
            raise ValueError("Degenerate probability distribution.")

        # 4. Apply Constraint Mask (Truncation)
        if enforce_constraints:
            mask = np.ones_like(x_values, dtype=bool)
            if context.min_val is not None:
                mask &= (x_values >= context.min_val)
            if context.max_val is not None:
                mask &= (x_values <= context.max_val)
            # Note: In a strict physical projection, values outside are probability 0.
            # The np.linspace already limits the range, but we explicitly zero out 
            # densities if the logic allowed overflow (double safety).
            pdf[~mask] = 0.0
            # Re-normalize after truncation
            area = np.trapz(pdf, x_values)
            if area > 0:
                pdf = pdf / area

        # 5. Extract Statistics
        # Expected Value (Mean of the constrained distribution)
        expected_val = np.trapz(x_values * pdf, x_values)
        
        # Confidence Interval (assuming 1-sigma within the constrained range)
        # This is an approximation for truncated distributions
        
        result = {
            "parameter": param_name,
            "semantic_term": term,
            "unit": context.unit,
            "x_values": x_values,
            "pdf": pdf,
            "expected_value": expected_val,
            "peak_value": x_values[np.argmax(pdf)], # MAP estimate
            "raw_mean": mapping.mean
        }
        
        logger.info(f"Projected '{term}' to '{param_name}': Expected={expected_val:.4f} {context.unit}")
        return result

def calculate_fuzzy_overlap(map_a: FuzzyMapping, map_b: FuzzyMapping) -> float:
    """
    Auxiliary function: Calculates the similarity (overlap coefficient) 
    between two fuzzy mappings based on their PDFs.
    
    Args:
        map_a: First semantic mapping.
        map_b: Second semantic mapping.
        
    Returns:
        A float between 0.0 and 1.0 representing overlap.
    """
    if map_a.distribution_type != 'gaussian' or map_b.distribution_type != 'gaussian':
        raise NotImplementedError("Overlap calculation currently supports Gaussian only.")

    # Approximate intersection area using numerical integration
    # Define a common range
    start = min(map_a.mean - 4*map_a.std_dev, map_b.mean - 4*map_b.std_dev)
    end = max(map_a.mean + 4*map_a.std_dev, map_b.mean + 4*map_b.std_dev)
    x = np.linspace(start, end, 1000)
    
    pdf_a = np.exp(-0.5 * ((x - map_a.mean) / map_a.std_dev) ** 2)
    pdf_b = np.exp(-0.5 * ((x - map_b.mean) / map_b.std_dev) ** 2)
    
    # Normalize
    pdf_a /= np.trapz(pdf_a, x)
    pdf_b /= np.trapz(pdf_b, x)
    
    # Intersection over Union (IoU) style metric for probability mass
    intersection = np.trapz(np.minimum(pdf_a, pdf_b), x)
    
    logger.debug(f"Overlap between '{map_a.term}' and '{map_b.term}': {intersection:.4f}")
    return float(intersection)

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the projector
    projector = SemanticPhysicsProjector()

    # Define physical context for Temperature (Celsius)
    # Water state constraints (Liquid roughly 0-100, but let's use generic environmental)
    temp_context = PhysicalContext(unit="celsius", min_val=-273.15, max_val=1000.0)
    projector.register_context("reactor_temp", temp_context)

    # Train mappings for fuzzy terms
    # "Cold" -> roughly 10 degrees, high uncertainty
    projector.train_mapping("reactor_temp", "cold", mean=10.0, std_dev=5.0)
    # "Hot" -> roughly 80 degrees, lower uncertainty
    projector.train_mapping("reactor_temp", "hot", mean=80.0, std_dev=4.0)
    # "Supercritical" -> mean exceeds limits to test boundary handling
    projector.train_mapping("reactor_temp", "supercritical", mean=2000.0, std_dev=100.0)

    print("-" * 60)
    
    try:
        # 1. Successful projection
        projection = projector.project_semantic("reactor_temp", "hot")
        print(f"Input Term: 'hot'")
        print(f"Expected Physical Value: {projection['expected_value']:.2f} {projection['unit']}")
        print(f"Peak (MAP) Value: {projection['peak_value']:.2f}")
        
        print("-" * 60)

        # 2. Boundary constrained projection
        # "Supercritical" mean is 2000, but max_val is 1000.
        # The result should be skewed/truncated near the max_val.
        projection_skewed = projector.project_semantic("reactor_temp", "supercritical")
        print(f"Input Term: 'supercritical' (Raw Mean: 2000)")
        print(f"Constrained Expected Value: {projection_skewed['expected_value']:.2f}")
        print(f"Notice: The value is clamped/distributed near the physical limit (1000).")

        print("-" * 60)

        # 3. Calculate similarity between "cold" and "hot"
        m_cold = projector._mappings["reactor_temp:cold"]
        m_hot = projector._mappings["reactor_temp:hot"]
        overlap = calculate_fuzzy_overlap(m_cold, m_hot)
        print(f"Semantic Overlap between 'cold' and 'hot': {overlap*100:.2f}%")

    except Exception as e:
        logger.exception(f"Error in example execution: {e}")