"""
Module: auto_左右跨域重叠_跨模态结构同构_向ai提_55ab61
Description: 【左右跨域重叠】跨模态结构同构：将复杂音乐结构（如赋格曲）映射为商业谈判流程图
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicalElementType(Enum):
    """Enumeration of musical element types that can be mapped to negotiation phases"""
    THEME = auto()
    COUNTERSUBJECT = auto()
    EPISODE = auto()
    STRETTO = auto()
    PEDAL_POINT = auto()
    CADENCE = auto()


class NegotiationPhase(Enum):
    """Enumeration of negotiation phases mapped from musical elements"""
    OPENING_OFFER = auto()
    COUNTER_PROPOSAL = auto()
    BARTERING = auto()
    PRESSURE_TACTIC = auto()
    ANCHORING = auto()
    CLOSURE = auto()


@dataclass
class MusicalElement:
    """Represents a musical element with its structural properties"""
    element_type: MusicalElementType
    start_time: float  # in beats
    duration: float    # in beats
    intensity: float   # normalized intensity (0-1)
    voice_id: int      # identifier for polyphonic voices
    pitch_range: Tuple[int, int]  # (lowest, highest) MIDI notes


@dataclass
class NegotiationStep:
    """Represents a step in the negotiation process"""
    phase: NegotiationPhase
    timestamp: float
    duration: float
    intensity: float
    participant_id: int
    leverage_level: Tuple[float, float]  # (min, max) leverage


class MusicToNegotiationMapper:
    """
    Maps musical structures to negotiation processes by preserving structural isomorphism
    while translating domain-specific elements.
    """
    
    # Mapping between musical elements and negotiation phases
    ELEMENT_MAPPING = {
        MusicalElementType.THEME: NegotiationPhase.OPENING_OFFER,
        MusicalElementType.COUNTERSUBJECT: NegotiationPhase.COUNTER_PROPOSAL,
        MusicalElementType.EPISODE: NegotiationPhase.BARTERING,
        MusicalElementType.STRETTO: NegotiationPhase.PRESSURE_TACTIC,
        MusicalElementType.PEDAL_POINT: NegotiationPhase.ANCHORING,
        MusicalElementType.CADENCE: NegotiationPhase.CLOSURE
    }
    
    def __init__(self, time_scale_factor: float = 1.0):
        """
        Initialize the mapper with time scaling factor.
        
        Args:
            time_scale_factor: Factor to convert musical beats to negotiation minutes
        """
        self.time_scale_factor = time_scale_factor
        logger.info("Initialized MusicToNegotiationMapper with time_scale_factor=%.2f", time_scale_factor)
    
    def validate_musical_element(self, element: MusicalElement) -> bool:
        """
        Validate a musical element's properties.
        
        Args:
            element: MusicalElement to validate
            
        Returns:
            bool: True if valid, raises ValueError otherwise
            
        Raises:
            ValueError: If any validation check fails
        """
        if element.start_time < 0:
            raise ValueError(f"Start time cannot be negative: {element.start_time}")
        if element.duration <= 0:
            raise ValueError(f"Duration must be positive: {element.duration}")
        if not 0 <= element.intensity <= 1:
            raise ValueError(f"Intensity must be between 0 and 1: {element.intensity}")
        if element.voice_id < 0:
            raise ValueError(f"Voice ID must be non-negative: {element.voice_id}")
        if element.pitch_range[0] > element.pitch_range[1]:
            raise ValueError(f"Invalid pitch range: {element.pitch_range}")
        
        return True
    
    def map_intensity_to_leverage(self, intensity: float) -> Tuple[float, float]:
        """
        Map musical intensity to negotiation leverage range.
        
        Args:
            intensity: Musical intensity (0-1)
            
        Returns:
            Tuple[float, float]: Leverage range (min, max)
        """
        if not 0 <= intensity <= 1:
            raise ValueError(f"Intensity must be between 0 and 1: {intensity}")
            
        # Higher intensity maps to wider leverage range (more room for negotiation)
        min_leverage = max(0, intensity - 0.2)
        max_leverage = min(1, intensity + 0.2)
        return (min_leverage, max_leverage)
    
    def map_pitch_range_to_leverage(self, pitch_range: Tuple[int, int]) -> Tuple[float, float]:
        """
        Map musical pitch range to negotiation leverage range.
        
        Args:
            pitch_range: Tuple of (lowest, highest) MIDI notes
            
        Returns:
            Tuple[float, float]: Leverage range (min, max)
        """
        # Normalize pitch range (MIDI notes 0-127)
        min_pitch, max_pitch = pitch_range
        range_width = (max_pitch - min_pitch) / 127  # Normalized width
        center = (min_pitch + max_pitch) / 254  # Normalized center
        
        # Wider pitch range maps to wider leverage range
        min_leverage = max(0, center - range_width/2)
        max_leverage = min(1, center + range_width/2)
        return (min_leverage, max_leverage)
    
    def convert_musical_element(self, element: MusicalElement) -> NegotiationStep:
        """
        Convert a single musical element to a negotiation step.
        
        Args:
            element: MusicalElement to convert
            
        Returns:
            NegotiationStep: Corresponding negotiation step
            
        Raises:
            ValueError: If element validation fails
        """
        try:
            self.validate_musical_element(element)
            
            # Get corresponding negotiation phase
            phase = self.ELEMENT_MAPPING.get(element.element_type)
            if phase is None:
                raise ValueError(f"No mapping for musical element type: {element.element_type}")
            
            # Calculate negotiation timestamp
            timestamp = element.start_time * self.time_scale_factor
            
            # Calculate leverage range
            leverage_from_intensity = self.map_intensity_to_leverage(element.intensity)
            leverage_from_pitch = self.map_pitch_range_to_leverage(element.pitch_range)
            
            # Combine both leverage calculations with weighting
            leverage = (
                0.6 * leverage_from_intensity[0] + 0.4 * leverage_from_pitch[0],
                0.6 * leverage_from_intensity[1] + 0.4 * leverage_from_pitch[1]
            )
            
            logger.debug(
                "Converted %s at %.2f to %s at %.2f",
                element.element_type.name, element.start_time,
                phase.name, timestamp
            )
            
            return NegotiationStep(
                phase=phase,
                timestamp=timestamp,
                duration=element.duration * self.time_scale_factor,
                intensity=element.intensity,
                participant_id=element.voice_id,
                leverage_level=leverage
            )
            
        except ValueError as e:
            logger.error("Validation failed for musical element: %s", str(e))
            raise
    
    def convert_musical_structure(self, elements: List[MusicalElement]) -> List[NegotiationStep]:
        """
        Convert a complete musical structure to a negotiation process.
        
        Args:
            elements: List of MusicalElements representing the musical structure
            
        Returns:
            List[NegotiationStep]: List of negotiation steps representing the process
            
        Raises:
            ValueError: If any element validation fails
        """
        if not elements:
            logger.warning("Empty musical structure provided")
            return []
            
        logger.info("Converting musical structure with %d elements", len(elements))
        
        negotiation_process = []
        for element in elements:
            try:
                step = self.convert_musical_element(element)
                negotiation_process.append(step)
            except ValueError as e:
                logger.error("Skipping invalid element: %s", str(e))
                continue
                
        # Sort negotiation steps by timestamp
        negotiation_process.sort(key=lambda x: x.timestamp)
        
        logger.info("Successfully converted %d elements to negotiation steps", len(negotiation_process))
        return negotiation_process


def analyze_structural_isomorphism(
    musical_elements: List[MusicalElement],
    negotiation_steps: List[NegotiationStep]
) -> Dict[str, float]:
    """
    Analyze the structural isomorphism between musical elements and negotiation steps.
    
    Args:
        musical_elements: List of musical elements
        negotiation_steps: List of negotiation steps
        
    Returns:
        Dict[str, float]: Dictionary of isomorphism metrics
    """
    if len(musical_elements) != len(negotiation_steps):
        logger.warning(
            "Element count mismatch: %d musical vs %d negotiation",
            len(musical_elements), len(negotiation_steps)
        )
        return {"isomorphism_score": 0.0}
    
    # Calculate time structure similarity
    musical_times = np.array([e.start_time for e in musical_elements])
    negotiation_times = np.array([s.timestamp for s in negotiation_steps])
    
    # Normalize both time series
    musical_times_norm = musical_times / np.max(musical_times) if np.max(musical_times) > 0 else musical_times
    negotiation_times_norm = negotiation_times / np.max(negotiation_times) if np.max(negotiation_times) > 0 else negotiation_times
    
    time_similarity = 1 - np.mean(np.abs(musical_times_norm - negotiation_times_norm))
    
    # Calculate intensity structure similarity
    musical_intensities = np.array([e.intensity for e in musical_elements])
    negotiation_intensities = np.array([s.intensity for s in negotiation_steps])
    
    intensity_similarity = 1 - np.mean(np.abs(musical_intensities - negotiation_intensities))
    
    # Calculate overall isomorphism score (weighted average)
    isomorphism_score = 0.6 * time_similarity + 0.4 * intensity_similarity
    
    return {
        "time_similarity": time_similarity,
        "intensity_similarity": intensity_similarity,
        "isomorphism_score": isomorphism_score
    }


# Example usage
if __name__ == "__main__":
    # Create a sample musical structure (simplified fugue excerpt)
    fugue_elements = [
        MusicalElement(MusicalElementType.THEME, 0.0, 4.0, 0.8, 0, (60, 72)),
        MusicalElement(MusicalElementType.COUNTERSUBJECT, 4.0, 4.0, 0.6, 1, (55, 67)),
        MusicalElement(MusicalElementType.EPISODE, 8.0, 8.0, 0.5, 0, (48, 60)),
        MusicalElement(MusicalElementType.THEME, 16.0, 4.0, 0.7, 1, (65, 77)),
        MusicalElement(MusicalElementType.STRETTO, 20.0, 2.0, 0.9, 0, (70, 82)),
        MusicalElement(MusicalElementType.CADENCE, 22.0, 2.0, 1.0, 0, (60, 72))
    ]
    
    # Initialize mapper
    mapper = MusicToNegotiationMapper(time_scale_factor=2.0)  # 1 beat = 2 minutes
    
    # Convert musical structure to negotiation process
    try:
        negotiation_process = mapper.convert_musical_structure(fugue_elements)
        
        print("\nNegotiation Process:")
        for i, step in enumerate(negotiation_process):
            print(
                f"Step {i+1}: {step.phase.name} at {step.timestamp:.1f} min, "
                f"duration {step.duration:.1f} min, "
                f"leverage {step.leverage_level[0]:.2f}-{step.leverage_level[1]:.2f}"
            )
        
        # Analyze structural isomorphism
        isomorphism = analyze_structural_isomorphism(fugue_elements, negotiation_process)
        print("\nStructural Isomorphism Analysis:")
        print(f"Time similarity: {isomorphism['time_similarity']:.2f}")
        print(f"Intensity similarity: {isomorphism['intensity_similarity']:.2f}")
        print(f"Overall isomorphism score: {isomorphism['isomorphism_score']:.2f}")
        
    except ValueError as e:
        print(f"Error: {str(e)}")