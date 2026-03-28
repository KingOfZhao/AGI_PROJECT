"""
Module: tacit_knowledge_digitizer
This system converts human unstructured, body-based tacit knowledge
(e.g., 'feel', 'force' in craftsmanship) into structured, computable data.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TactileFrame:
    """
    Represents a single frame of multi-modal sensory data.
    
    Attributes:
        timestamp (float): Time in seconds.
        position (Tuple[float, float, float]): Spatial coordinates (x, y, z).
        force_vector (Tuple[float, float, float]): Force vector (Fx, Fy, Fz).
        grip_pressure (float): Scalar pressure value (0.0 to 1.0).
    """
    timestamp: float
    position: Tuple[float, float, float]
    force_vector: Tuple[float, float, float]
    grip_pressure: float

    def __post_init__(self):
        """Validate data types and ranges after initialization."""
        if not (0.0 <= self.grip_pressure <= 1.0):
            raise ValueError(f"Grip pressure must be between 0 and 1, got {self.grip_pressure}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp cannot be negative, got {self.timestamp}")

@dataclass
class SkillModel:
    """
    Structured representation of a learned skill.
    
    Attributes:
        name (str): Name of the skill.
        duration (float): Total duration of the recorded action.
        keyframes (List[TactileFrame]): List of critical frames defining the skill.
        avg_force (float): Calculated average force magnitude.
    """
    name: str
    duration: float
    keyframes: List[TactileFrame] = field(default_factory=list)
    avg_force: float = 0.0

def _calculate_vector_magnitude(vector: Tuple[float, float, float]) -> float:
    """
    Auxiliary function: Calculates the Euclidean magnitude of a 3D vector.
    
    Args:
        vector (Tuple[float, float, float]): A tuple representing (x, y, z).
        
    Returns:
        float: The magnitude of the vector.
        
    Raises:
        TypeError: If input is not a tuple or list of 3 numbers.
    """
    if len(vector) != 3:
        raise ValueError("Vector must have exactly 3 dimensions.")
    return np.sqrt(sum(p**2 for p in vector))

def extract_micro_motion_trajectory(
    raw_sensory_stream: List[Dict], 
    sensitivity_threshold: float = 0.01
) -> List[TactileFrame]:
    """
    Core Function 1: Processes raw sensory streams into structured TactileFrames.
    
    It filters noise and maps unstructured sensor readings to the 
    TactileFrame data structure, focusing on significant micro-motions.
    
    Args:
        raw_sensory_stream (List[Dict]): Raw input data. Each dict contains 
                                         'ts', 'pos', 'force', 'pressure'.
        sensitivity_threshold (float): Minimum movement magnitude to record.
        
    Returns:
        List[TactileFrame]: A time-series of structured sensory data.
        
    Example:
        >>> raw_data = [{'ts': 0.1, 'pos': [0,0,0], 'force': [0,0,0.1], 'pressure': 0.5}]
        >>> frames = extract_micro_motion_trajectory(raw_data)
    """
    structured_frames = []
    last_pos = None
    
    logger.info(f"Starting extraction of {len(raw_sensory_stream)} raw frames.")
    
    for i, sample in enumerate(raw_sensory_stream):
        try:
            # Input Validation
            if not all(k in sample for k in ['ts', 'pos', 'force', 'pressure']):
                logger.warning(f"Frame {i} missing keys, skipping.")
                continue
                
            current_pos = tuple(sample['pos'])
            
            # Boundary check for motion significance
            if last_pos is not None:
                delta = _calculate_vector_magnitude(
                    (current_pos[0]-last_pos[0], 
                     current_pos[1]-last_pos[1], 
                     current_pos[2]-last_pos[2])
                )
                if delta < sensitivity_threshold:
                    continue  # Skip static noise

            frame = TactileFrame(
                timestamp=float(sample['ts']),
                position=current_pos,
                force_vector=tuple(sample['force']),
                grip_pressure=float(sample['pressure'])
            )
            structured_frames.append(frame)
            last_pos = current_pos
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing frame {i}: {e}")
            continue
            
    logger.info(f"Extraction complete. Structured frames: {len(structured_frames)}")
    return structured_frames

def build_skill_state_space(
    frames: List[TactileFrame], 
    skill_name: str
) -> SkillModel:
    """
    Core Function 2: Constructs a computational model from the trajectory.
    
    This function analyzes the force and spatial data to create a 'digital twin'
    of the specific craftsmanship moment, calculating statistics and key poses.
    
    Args:
        frames (List[TactileFrame]): The processed sensory frames.
        skill_name (str): Identifier for the skill being modeled.
        
    Returns:
        SkillModel: The structured skill object containing features.
        
    Raises:
        ValueError: If frames list is empty.
    """
    if not frames:
        raise ValueError("Cannot build model from empty frame list.")
        
    logger.info(f"Building state space model for skill: {skill_name}")
    
    total_duration = frames[-1].timestamp - frames[0].timestamp
    force_magnitudes = [_calculate_vector_magnitude(f.force_vector) for f in frames]
    avg_force = np.mean(force_magnitudes)
    
    # Identify keyframes (peaks in force or pressure)
    # For simplicity, we take frames where force > average force
    keyframes = [
        f for f, fm in zip(frames, force_magnitudes) 
        if fm > avg_force
    ]
    
    model = SkillModel(
        name=skill_name,
        duration=total_duration,
        keyframes=keyframes,
        avg_force=avg_force
    )
    
    logger.info(f"Model created. Duration: {total_duration:.2f}s, Avg Force: {avg_force:.2f}N")
    return model

if __name__ == "__main__":
    # Usage Example
    # Simulating a stream of data from a sensor glove or AR capture
    mock_sensor_data = [
        {'ts': 0.0, 'pos': [0.0, 0.0, 0.0], 'force': [0.0, 0.0, 0.0], 'pressure': 0.0},
        {'ts': 0.1, 'pos': [0.0, 0.1, 0.0], 'force': [0.0, 1.2, 0.0], 'pressure': 0.4},
        {'ts': 0.2, 'pos': [0.0, 0.1, 0.0], 'force': [0.0, 4.5, 0.0], 'pressure': 0.8}, # Peak force
        {'ts': 0.3, 'pos': [0.0, 0.2, 0.0], 'force': [0.0, 2.1, 0.0], 'pressure': 0.6},
        {'ts': 0.4, 'pos': [0.0, 0.2, 0.0], 'force': [0.0, 0.5, 0.0], 'pressure': 0.2},
    ]

    print("--- Starting Tacit Knowledge Processing ---")
    
    # 1. Extract and Clean
    trajectory = extract_micro_motion_trajectory(mock_sensor_data)
    
    # 2. Analyze and Model
    try:
        skill_model = build_skill_state_space(trajectory, "Ceramic_Potting_Pull")
        print(f"Skill Acquired: {skill_model.name}")
        print(f"Average Force: {skill_model.avg_force:.2f} N")
        print(f"Keyframes detected: {len(skill_model.keyframes)}")
    except ValueError as e:
        print(f"Failed to build model: {e}")