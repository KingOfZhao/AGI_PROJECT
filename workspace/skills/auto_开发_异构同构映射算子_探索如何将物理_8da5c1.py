"""
Module: heterogeneous_isomorphic_mapping_operator
Description: Implements the 'Heterogeneous Isomorphic Mapping Operator'.
             This module facilitates the mapping of continuous manifold states
             from a physical space to discrete lattice points in a code state space.
             It is designed to address blind test feedback quantization issues
             referenced in td_4_Q3_0_7680.

Author: AGI System
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class PhysicalState:
    """
    Represents a continuous state vector in physical space (Manifold).
    
    Attributes:
        coordinates (List[float]): A list of continuous values representing 
                                   dimensions on the manifold (e.g., position, velocity).
        timestamp (float): The time at which this state was observed.
    """
    coordinates: List[float]
    timestamp: float

@dataclass
class CodeStateLattice:
    """
    Represents a discrete point in the code state space (Lattice).
    
    Attributes:
        indices (Tuple[int, ...]): Discrete integer coordinates in the code space.
        hash_value (str): A unique identifier for the state, often used for lookups.
    """
    indices: Tuple[int, ...]
    hash_value: str

# --- Custom Exceptions ---

class MappingError(Exception):
    """Base exception for mapping errors."""
    pass

class DimensionMismatchError(MappingError):
    """Raised when input dimensions do not match configuration."""
    pass

class InvalidBoundariesError(MappingError):
    """Raised when physical boundaries are invalid."""
    pass

# --- Core Classes ---

class HeterogeneousIsomorphicMapper:
    """
    A high-level operator that maps high-dimensional continuous data 
    (Physical Manifold) to a discrete grid (Code Lattice).
    
    This implementation uses a scaled lattice approach where the resolution 
    of the mapping can be tuned per dimension to handle heterogeneous 
    data scales.
    """

    def __init__(self, 
                 dim_boundaries: List[Tuple[float, float]], 
                 resolution_levels: List[int]):
        """
        Initialize the mapper.
        
        Args:
            dim_boundaries: List of (min, max) tuples for each dimension.
            resolution_levels: List of integers defining how many discrete bins 
                               exist for each dimension.
                               
        Raises:
            InvalidBoundariesError: If boundaries are ill-defined.
            DimensionMismatchError: If input lists have different lengths.
        """
        if len(dim_boundaries) != len(resolution_levels):
            msg = "Dimension mismatch between boundaries and resolutions."
            logger.error(msg)
            raise DimensionMismatchError(msg)
        
        if not dim_boundaries:
            msg = "Dimension boundaries cannot be empty."
            logger.error(msg)
            raise ValueError(msg)

        self.dim_boundaries = dim_boundaries
        self.resolution_levels = resolution_levels
        self.dimensions = len(dim_boundaries)
        
        # Pre-calculate scaling factors
        self.scale_factors = []
        for i, (min_v, max_v) in enumerate(dim_boundaries):
            if min_v >= max_v:
                raise InvalidBoundariesError(f"Boundary min must be < max for dimension {i}")
            range_v = max_v - min_v
            self.scale_factors.append(resolution_levels[i] / range_v)
        
        logger.info(f"Mapper initialized for {self.dimensions} dimensions.")

    def _validate_input_coordinates(self, coords: List[float]) -> None:
        """
        Helper function to validate input data.
        
        Args:
            coords: List of coordinate values.
            
        Raises:
            DimensionMismatchError: If length does not match configuration.
            ValueError: If values are outside defined boundaries.
        """
        if len(coords) != self.dimensions:
            raise DimensionMismatchError(
                f"Expected {self.dimensions} dimensions, got {len(coords)}."
            )
        
        for i, val in enumerate(coords):
            min_v, max_v = self.dim_boundaries[i]
            # Allow slight epsilon tolerance for floating point errors
            epsilon = 1e-9
            if not (min_v - epsilon <= val <= max_v + epsilon):
                logger.warning(f"Value {val} in dim {i} out of bounds [{min_v}, {max_v}]. Clamping will occur.")

    def _map_continuous_to_discrete(self, value: float, dim_index: int) -> int:
        """
        Core logic: Maps a single continuous value to a discrete integer index.
        
        This implements a quantization logic suitable for 'blind test feedback'.
        
        Args:
            value: The continuous value.
            dim_index: The index of the dimension being mapped.
            
        Returns:
            The discrete integer index.
        """
        min_v, max_v = self.dim_boundaries[dim_index]
        resolution = self.resolution_levels[dim_index]
        
        # Clamp value to boundaries to prevent index overflow
        clamped_val = max(min_v, min(value, max_v))
        
        # Calculate relative position (0.0 to 1.0)
        relative_pos = (clamped_val - min_v) / (max_v - min_v)
        
        # Map to discrete bin
        index = int(relative_pos * resolution)
        
        # Handle edge case where value == max_v
        if index == resolution:
            index = resolution - 1
            
        return index

    def transform(self, physical_state: PhysicalState) -> CodeStateLattice:
        """
        Transforms a PhysicalState into a CodeStateLattice.
        
        This is the main entry point for the mapping operation.
        
        Args:
            physical_state: The input continuous state.
            
        Returns:
            CodeStateLattice: The resulting discrete state representation.
        """
        try:
            self._validate_input_coordinates(physical_state.coordinates)
            
            indices = []
            for i, val in enumerate(physical_state.coordinates):
                idx = self._map_continuous_to_discrete(val, i)
                indices.append(idx)
            
            # Generate a deterministic hash for the lattice point
            lattice_hash = self._generate_lattice_hash(indices)
            
            result = CodeStateLattice(
                indices=tuple(indices),
                hash_value=lattice_hash
            )
            
            logger.debug(f"Mapped {physical_state.coordinates} -> {result.indices}")
            return result

        except DimensionMismatchError as e:
            logger.error(f"Mapping failed: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during transformation: {e}")
            raise MappingError("Transformation failed.") from e

    def _generate_lattice_hash(self, indices: List[int]) -> str:
        """
        Helper function to generate a unique identifier for a lattice point.
        
        Args:
            indices: The list of discrete indices.
            
        Returns:
            A string hash key.
        """
        # Simple join-based hash for demonstration; 
        # could be SHA256 for cryptographic security in production AGI memory.
        return "LATTICE_" + "_".join(map(str, indices))

    def inverse_transform(self, code_state: CodeStateLattice) -> List[float]:
        """
        (Optional Feature) Reconstructs the center point of the lattice cell 
        in physical space.
        
        Args:
            code_state: The discrete state.
            
        Returns:
            List[float]: The approximate continuous coordinates (cell centers).
        """
        reconstructed_coords = []
        for i, idx in enumerate(code_state.indices):
            min_v, max_v = self.dim_boundaries[i]
            resolution = self.resolution_levels[i]
            
            # Calculate center of the bin
            step_size = (max_v - min_v) / resolution
            center_val = min_v + (idx + 0.5) * step_size
            reconstructed_coords.append(center_val)
            
        return reconstructed_coords

# --- Usage Example ---

if __name__ == "__main__":
    # Example configuration for a 3D physical space
    # Dim 0: Temperature (-10 to 40 C)
    # Dim 1: Pressure (0 to 100 kPa)
    # Dim 2: Velocity (-5 to 5 m/s)
    
    boundaries = [
        (-10.0, 40.0),  # Temp
        (0.0, 100.0),   # Pressure
        (-5.0, 5.0)     # Velocity
    ]
    
    # Resolution: How many distinct 'bins' per dimension
    resolutions = [50, 100, 20]
    
    # Initialize the Operator
    try:
        mapper = HeterogeneousIsomorphicMapper(boundaries, resolutions)
        
        # Simulate a stream of physical states
        input_states = [
            PhysicalState([25.0, 50.0, 0.0], 0.1),  # Ideal center
            PhysicalState([-10.0, 0.0, -5.0], 0.2), # Lower bounds
            PhysicalState([41.0, 101.0, 6.0], 0.3)  # Out of bounds (clamped)
        ]
        
        print("\n--- Mapping Execution ---")
        for state in input_states:
            try:
                lattice_point = mapper.transform(state)
                print(f"Input: {state.coordinates}")
                print(f"Output: {lattice_point.indices} Hash: {lattice_point.hash_value}")
                
                # Verify inverse
                approx_phys = mapper.inverse_transform(lattice_point)
                print(f"Reconstruction: {[round(x, 2) for x in approx_phys]}")
                print("-" * 40)
            except MappingError as e:
                print(f"Skipping state due to error: {e}")

    except Exception as e:
        print(f"Initialization failed: {e}")