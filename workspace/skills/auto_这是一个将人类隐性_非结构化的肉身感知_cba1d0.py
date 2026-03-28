"""
Module: tacit_somatosensory_transducer.py

This module implements the "Tacit Somatosensory Transducer" (TST), a system designed
to convert implicit, unstructured human somatosensory perceptions (such as tactile
feel, EMG signals, force micro-adjustments) into machine-readable, quantifiable
parameters aligned with physical laws.

Core Concept:
    Sensory Axiom System -> High-Dimensional Vector Projection -> Physical Control Parameters.

Author: AGI System Core
Version: 1.0.0
"""

import logging
import math
import numpy as np
from typing import Dict, Tuple, List, Optional, Union
from pydantic import BaseModel, Field, validator, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Physical Axioms ---
PHYSICAL_CONSTRAINTS = {
    "friction_coefficient": (0.0, 2.0),  # Typical range for materials
    "stiffness": (0.0, 1e6),             # N/m
    "surface_roughness": (0.0, 100.0),   # Ra (micrometers)
    "temperature": (223.15, 373.15)      # Kelvin (-50C to 100C)
}

EMBEDDING_DIMENSION = 128

class SensoryInputModel(BaseModel):
    """
    Data model for validating raw sensory inputs.
    """
    description: str = Field(..., min_length=1, description="Natural language description of the sensation, e.g., 'slightly astringent'")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Subjective intensity scale 0.0-1.0")
    signals: Optional[List[float]] = Field(default=None, description="Optional time-series data (e.g., EMG readings)")

    @validator('description')
    def description_must_be_meaningful(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Description is too short to be meaningful")
        return v

class PhysicsParameterSet(BaseModel):
    """
    Data model for output physical parameters.
    """
    friction_coefficient: float
    stiffness: float
    surface_roughness: float
    temperature: float
    confidence_score: float

class SensoryAxiomSystem:
    """
    The core class that maintains the mapping between linguistic descriptions,
    latent vectors, and physical parameters.
    """

    def __init__(self):
        self._initialize_latent_space()
        logger.info("Sensory Axiom System Initialized with %d semantic anchors.", len(self.semantic_anchors))

    def _initialize_latent_space(self) -> None:
        """
        Initializes the semantic anchors in the latent space.
        In a real AGI system, this would be loaded from a trained model.
        Here we simulate vector embeddings for key tactile adjectives.
        """
        np.random.seed(42)
        self.semantic_anchors = {
            "rough": np.random.randn(EMBEDDING_DIMENSION) * 0.5 + 0.5,
            "smooth": np.random.randn(EMBEDDING_DIMENSION) * 0.2 + 0.1,
            "soft": np.random.randn(EMBEDDING_DIMENSION) * 0.3 - 0.2,
            "hard": np.random.randn(EMBEDDING_DIMENSION) * 0.6 + 0.8,
            "sticky": np.random.randn(EMBEDDING_DIMENSION) * 0.4 + 0.3,
            "slippery": np.random.randn(EMBEDDING_DIMENSION) * 0.2 - 0.1,
            "astringent": np.array([0.2 * math.sin(i/2) for i in range(EMBEDDING_DIMENSION)]) # Simulated complex feel
        }
        # Normalize anchors
        for k in self.semantic_anchors:
            self.semantic_anchors[k] = self.semantic_anchors[k] / np.linalg.norm(self.semantic_anchors[k])

    def _text_to_latent_vector(self, description: str) -> np.ndarray:
        """
        Helper function: Projects natural language into the latent space.
        Uses a simplified keyword matching for this demo.
        """
        desc_lower = description.lower()
        vector = np.zeros(EMBEDDING_DIMENSION)
        match_count = 0
        
        # Simple semantic composition
        for key, anchor in self.semantic_anchors.items():
            if key in desc_lower:
                vector += anchor
                match_count += 1
        
        if match_count == 0:
            logger.warning("No semantic anchors found for description: '%s'. Using default neutral vector.", description)
            return np.zeros(EMBEDDING_DIMENSION)
        
        return vector / match_count

    def parse_sensory_input(self, raw_input: Dict[str, Union[str, float, List[float]]]) -> Tuple[np.ndarray, float]:
        """
        Core Function 1: Converts raw unstructured input into a normalized latent vector.
        
        Args:
            raw_input: Dictionary containing description, intensity, and optional signals.
            
        Returns:
            A tuple of (Latent Vector, Intensity Scalar).
            
        Raises:
            ValidationError: If input data does not match the schema.
        """
        try:
            # Validate input data
            validated_data = SensoryInputModel(**raw_input)
            logger.debug(f"Processing sensory input: {validated_data.description}")
            
            # Project text to latent space
            semantic_vector = self._text_to_latent_vector(validated_data.description)
            
            # Modulate vector by intensity (Attention mechanism simulation)
            modulated_vector = semantic_vector * (1 + validated_data.intensity)
            
            # If EMG signals are present, concatenate or modulate (simplified here as a bias)
            if validated_data.signals:
                signal_avg = np.mean(validated_data.signals)
                # Normalize signal influence
                noise_bias = np.random.normal(0, 0.01, EMBEDDING_DIMENSION) * signal_avg
                modulated_vector += noise_bias
                
            return modulated_vector, validated_data.intensity
            
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during parsing: {e}", exc_info=True)
            raise

    def project_to_physics(self, latent_vector: np.ndarray, intensity: float) -> PhysicsParameterSet:
        """
        Core Function 2: Projects the latent vector into physical control parameters.
        Enforces physical laws (Axioms) and boundary checks.
        
        Args:
            latent_vector: The high-dimensional representation of the sensation.
            intensity: The magnitude of the sensation.
            
        Returns:
            A validated PhysicsParameterSet object.
        """
        logger.info("Projecting latent vector to physical domain...")
        
        # Simulation of Decoder Network
        # We map vector dimensions to physical properties via arbitrary linear transformations
        # In a real system, this would be a trained MLP (Multi-Layer Perceptron)
        
        # Dimension Slices for different properties
        slice_friction = latent_vector[:32]
        slice_stiffness = latent_vector[32:64]
        slice_roughness = latent_vector[64:96]
        slice_temp = latent_vector[96:]
        
        # Calculation (Simulated Weights)
        # Friction: range 0.0 - 2.0
        calc_friction = np.mean(slice_friction) * 2.0 + intensity
        
        # Stiffness: range 0 - 1e6
        calc_stiffness = abs(np.sum(slice_stiffness)) * 100000
        
        # Roughness: range 0 - 100
        calc_roughness = np.std(slice_roughness) * 500
        
        # Temperature: range 20 - 40 Celsius (293K - 313K)
        calc_temp = 293.15 + (np.mean(slice_temp) + 1.0) * 10

        # Apply Physical Constraints (Clamping)
        final_friction = np.clip(calc_friction, *PHYSICAL_CONSTRAINTS["friction_coefficient"])
        final_stiffness = np.clip(calc_stiffness, *PHYSICAL_CONSTRAINTS["stiffness"])
        final_roughness = np.clip(calc_roughness, *PHYSICAL_CONSTRAINTS["surface_roughness"])
        final_temp = np.clip(calc_temp, *PHYSICAL_CONSTRAINTS["temperature"])

        # Calculate confidence based on vector magnitude
        confidence = min(1.0, np.linalg.norm(latent_vector) / 2.0)
        
        params = {
            "friction_coefficient": float(final_friction),
            "stiffness": float(final_stiffness),
            "surface_roughness": float(final_roughness),
            "temperature": float(final_temp),
            "confidence_score": float(confidence)
        }
        
        try:
            return PhysicsParameterSet(**params)
        except ValidationError as e:
            logger.error(f"Generated physical parameters are invalid: {e}")
            raise RuntimeError("Failed to generate valid physical parameters.")

# --- Main Execution Logic ---

def main():
    """
    Usage Example:
    Demonstrates converting the sensation "有点涩" (slightly astringent/dry friction) 
    and muscle tension into robot control parameters.
    """
    print("--- Tacit Somatosensory Transducer Activated ---")
    
    # Initialize System
    transducer = SensoryAxiomSystem()
    
    # Example 1: Subjective description with intensity
    raw_sensation_1 = {
        "description": "slightly astringent", # "有点涩"
        "intensity": 0.6,
        "signals": [0.1, 0.2, 0.15, 0.3] # Simulated slight muscle tremor
    }
    
    try:
        # Step 1: Parse to Latent Space
        vector, intensity = transducer.parse_sensory_input(raw_sensation_1)
        print(f"Input parsed. Latent vector norm: {np.linalg.norm(vector):.4f}")
        
        # Step 2: Project to Physics
        physics_params = transducer.project_to_physics(vector, intensity)
        
        print("\nGenerated Control Parameters:")
        print(f"  Friction Coeff: {physics_params.friction_coefficient:.4f}")
        print(f"  Stiffness:      {physics_params.stiffness:.4f} N/m")
        print(f"  Surface Rough.: {physics_params.surface_roughness:.4f} Ra")
        print(f"  Temperature:    {physics_params.temperature:.2f} K")
        print(f"  Confidence:     {physics_params.confidence_score:.2f}")
        
    except (ValidationError, RuntimeError) as e:
        print(f"Error processing request: {e}")

    # Example 2: Edge Case (High Intensity)
    raw_sensation_2 = {
        "description": "hard and rough surface",
        "intensity": 1.0
    }
    
    print("\n--- Processing High Intensity Input ---")
    try:
        vec2, int2 = transducer.parse_sensory_input(raw_sensation_2)
        params2 = transducer.project_to_physics(vec2, int2)
        print(f"Target Friction: {params2.friction_coefficient}")
        print(f"Target Stiffness: {params2.stiffness}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()