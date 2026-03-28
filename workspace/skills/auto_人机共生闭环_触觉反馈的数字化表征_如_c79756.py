"""
Module: auto_haptic_feedback_digital_representation
Description: 
    This module implements a 'Haptic Description Language' (HDL) parser designed 
    for Human-Machine Symbiosis. It translates fuzzy, expert natural language 
    descriptions of tactile sensations (e.g., "feels a bit sticky", "very smooth") 
    into structured, executable parameter adjustment instructions for robotic 
    control or physical simulation systems.

    It serves as a bridge between human intuition and machine precision, 
    facilitating the 'AI Sorting List' process in AGI systems.
"""

import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HapticDimension(Enum):
    """Enumeration of tactile dimensions mapping to physical parameters."""
    FRICTION = "friction"
    ROUGHNESS = "roughness"
    STIFFNESS = "stiffness"
    DAMPING = "damping"
    TEXTURE_FREQ = "texture_frequency"

@dataclass
class SimulationParameters:
    """Data structure representing the target simulation parameters."""
    friction: float = 0.5
    roughness: float = 0.0
    stiffness: float = 1.0
    damping: float = 0.1
    texture_frequency: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self))

class SemanticMappingError(Exception):
    """Custom exception for errors during semantic mapping."""
    pass

class ParameterRangeError(Exception):
    """Custom exception for parameters exceeding safety bounds."""
    pass

class HapticDescriptionParser:
    """
    Parses natural language descriptions of haptic sensations into structured 
    simulation parameters.
    
    Attributes:
        intensity_modifiers (Dict): Keywords mapping to intensity multipliers.
        dimension_keywords (Dict): Keywords mapping to physical dimensions.
        safety_bounds (Dict): Min/Max bounds for each parameter.
    """

    def __init__(self):
        """Initialize the parser with linguistic rules and safety bounds."""
        self.intensity_modifiers = {
            'very': 1.5,
            'extremely': 2.0,
            'super': 2.0,
            'slightly': 0.5,
            'a bit': 0.5,
            'somewhat': 0.7,
            'little': 0.5,
            'kind of': 0.6
        }
        
        self.dimension_keywords = {
            'rough': HapticDimension.ROUGHNESS,
            'bumpy': HapticDimension.ROUGHNESS,
            'gritty': HapticDimension.ROUGHNESS,
            'smooth': HapticDimension.FRICTION,  # Smooth often implies low friction
            'slippery': HapticDimension.FRICTION,
            'sticky': HapticDimension.FRICTION,
            'oily': HapticDimension.FRICTION,
            'dry': HapticDimension.FRICTION,
            'hard': HapticDimension.STIFFNESS,
            'soft': HapticDimension.STIFFNESS,
            'spongy': HapticDimension.STIFFNESS,
            'stiff': HapticDimension.STIFFNESS,
            'damping': HapticDimension.DAMPING,
            'mushy': HapticDimension.DAMPING,
            'tight': HapticDimension.DAMPING
        }

        # Safety bounds for physical simulation (prevent physics engine explosion)
        self.safety_bounds = {
            HapticDimension.FRICTION: (0.0, 1.0),
            HapticDimension.ROUGHNESS: (0.0, 100.0),
            HapticDimension.STIFFNESS: (0.0, 1000.0),
            HapticDimension.DAMPING: (0.0, 10.0),
            HapticDimension.TEXTURE_FREQ: (0.0, 50.0)
        }
        
        self.default_base_values = {
            HapticDimension.ROUGHNESS: 20.0,
            HapticDimension.FRICTION: 0.8, # Base for 'sticky'
            HapticDimension.STIFFNESS: 500.0,
            HapticDimension.DAMPING: 1.0
        }

    def _extract_modifiers(self, text: str) -> Tuple[float, str]:
        """
        Helper function to extract intensity modifiers and clean the text.
        
        Args:
            text (str): The raw natural language input.
            
        Returns:
            Tuple[float, str]: Intensity multiplier and cleaned keyword string.
        """
        text = text.lower().strip()
        multiplier = 1.0
        
        for word, mod in sorted(self.intensity_modifiers.items(), key=lambda x: -len(x[0])):
            if text.startswith(word):
                multiplier = mod
                text = text.replace(word, '').strip()
                logger.debug(f"Detected modifier '{word}' with multiplier {mod}")
                break
                
        return multiplier, text

    def _map_keyword_to_delta(self, keyword: str) -> Dict[HapticDimension, float]:
        """
        Maps a clean keyword to a dictionary of parameter changes (deltas).
        
        Args:
            keyword (str): The core adjective (e.g., 'sticky', 'smooth').
            
        Returns:
            Dict mapping Dimensions to float values.
            
        Raises:
            SemanticMappingError: If keyword cannot be mapped.
        """
        if keyword in ['smooth']:
            # 'Smooth' usually means reducing friction and roughness
            return {
                HapticDimension.FRICTION: -0.3,
                HapticDimension.ROUGHNESS: -20.0
            }
        elif keyword in ['sticky', 'oily']:
            return {HapticDimension.FRICTION: 0.8} # High friction
        elif keyword in ['rough', 'bumpy', 'gritty']:
            return {HapticDimension.ROUGHNESS: 30.0}
        elif keyword in ['hard', 'stiff']:
            return {HapticDimension.STIFFNESS: 300.0}
        elif keyword in ['soft', 'spongy']:
            return {HapticDimension.STIFFNESS: -400.0}
        elif keyword in ['mushy']:
            return {HapticDimension.DAMPING: 2.0}
        else:
            raise SemanticMappingError(f"Unknown haptic keyword: '{keyword}'")

    def parse_to_parameters(
        self, 
        description: str, 
        current_params: Optional[SimulationParameters] = None
    ) -> SimulationParameters:
        """
        Core Function: Parses a haptic description string into a SimulationParameters object.
        
        This function handles the NLP pipeline: Tokenization -> Modifier Extraction ->
        Semantic Mapping -> Parameter Application -> Validation.
        
        Args:
            description (str): Natural language description (e.g., "very sticky").
            current_params (Optional[SimulationParameters]): Existing state to modify. 
                If None, starts from default.
                
        Returns:
            SimulationParameters: The updated physical parameters.
            
        Raises:
            ParameterRangeError: If calculated parameters violate safety bounds.
            SemanticMappingError: If text cannot be interpreted.
        """
        if not description or not isinstance(description, str):
            raise ValueError("Description must be a non-empty string.")

        logger.info(f"Parsing haptic feedback instruction: '{description}'")
        
        # Initialize state
        params = current_params if current_params else SimulationParameters()
        
        # Simple sentence segmentation (split by commas/and)
        segments = re.split(r',|\band\b', description)
        
        for segment in segments:
            segment = segment.strip()
            if not segment: continue
            
            # 1. Extract Modifiers
            multiplier, clean_keyword = self._extract_modifiers(segment)
            
            # 2. Semantic Mapping
            try:
                deltas = self._map_keyword_to_delta(clean_keyword)
            except SemanticMappingError as e:
                logger.warning(f"Skipping segment '{segment}': {e}")
                continue

            # 3. Apply changes to the data structure
            for dim, value in deltas.items():
                target_value = value * multiplier
                
                # Apply based on dimension
                if dim == HapticDimension.FRICTION:
                    params.friction = max(0, min(1.0, params.friction + target_value))
                elif dim == HapticDimension.ROUGHNESS:
                    params.roughness = max(0, params.roughness + target_value)
                elif dim == HapticDimension.STIFFNESS:
                    params.stiffness = max(0.1, params.stiffness + target_value)
                elif dim == HapticDimension.DAMPING:
                    params.damping = max(0, params.damping + target_value)
                    
        # 4. Final Validation
        self.validate_parameters(params)
        logger.info(f"Generated parameters: {params.to_json()}")
        return params

    def validate_parameters(self, params: SimulationParameters) -> bool:
        """
        Secondary Function: Validates that simulation parameters are within physical safety bounds.
        
        Args:
            params (SimulationParameters): The parameters to check.
            
        Returns:
            bool: True if valid.
            
        Raises:
            ParameterRangeError: If bounds are exceeded.
        """
        checks = [
            (params.friction, HapticDimension.FRICTION),
            (params.roughness, HapticDimension.ROUGHNESS),
            (params.stiffness, HapticDimension.STIFFNESS),
            (params.damping, HapticDimension.DAMPING)
        ]
        
        for val, dim in checks:
            min_v, max_v = self.safety_bounds[dim]
            if not (min_v <= val <= max_v):
                # Clamp correction logic could go here, but we raise error for AGI feedback loop
                raise ParameterRangeError(
                    f"Parameter {dim.value} value {val} out of bounds [{min_v}, {max_v}]"
                )
        return True

# Usage Example
if __name__ == "__main__":
    # Initialize the parser
    haptic_ai = HapticDescriptionParser()
    
    # Scenario 1: Expert feedback on a surface simulation
    expert_feedback = "feels a bit slippery, but very stiff"
    
    try:
        # Convert natural language to parameters
        new_params = haptic_ai.parse_to_parameters(expert_feedback)
        
        print(f"Input: '{expert_feedback}'")
        print(f"Output JSON: {new_params.to_json()}")
        print(f"Friction: {new_params.friction}")
        print(f"Stiffness: {new_params.stiffness}")
        
    except (SemanticMappingError, ParameterRangeError) as e:
        logger.error(f"Processing failed: {e}")

    # Scenario 2: Handling complex feedback
    complex_feedback = "slightly rough, and kind of mushy"
    updated_params = haptic_ai.parse_to_parameters(complex_feedback)
    print(f"\nInput: '{complex_feedback}'")
    print(f"Roughness: {updated_params.roughness}, Damping: {updated_params.damping}")