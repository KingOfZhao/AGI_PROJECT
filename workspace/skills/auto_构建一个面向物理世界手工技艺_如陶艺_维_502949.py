"""
Module: artisan_skill_digitalizer
A high-precision pipeline for digitizing physical craftsmanship skills (e.g., pottery, repair).
"""

import logging
import numpy as np
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ArtisanSkillDigitalizer")

class SensorType(Enum):
    """Enumeration of supported sensor modalities."""
    VISION_RGB = "vision_rgb"
    TACTILE_PRESSURE = "tactile_pressure"
    TACTILE_VIBRATION = "tactile_vibration"
    FORCE_TORQUE = "force_torque"

@dataclass
class TactileSample:
    """Represents a single timestamped multi-modal sensor reading."""
    timestamp: float
    pressure_matrix: np.ndarray  # Shape: (H, W), values in Pascals
    vibration_freq: float        # Frequency in Hz
    force_vector: np.ndarray     # 6-axis Force/Torque [Fx, Fy, Fz, Tx, Ty, Tz]
    visual_frame_id: str         # Reference to visual keyframe

@dataclass
class SkillPrimitive:
    """
    Represents a parameterized, reusable unit of craftsmanship.
    This is the 'Skill Gene' extracted from raw data.
    """
    name: str
    start_time: float
    end_time: float
    avg_force: np.ndarray
    force_profile_signature: np.ndarray # Compressed representation
    vibration_harmonics: np.ndarray
    success_metric: float # Estimated probability of successful execution [0.0, 1.0]

class ArtisanDigitalizer:
    """
    Core system for converting physical craftsmanship into AI-digestible Skill Primitives.
    
    Pipeline Stages:
    1. Data Ingestion: Syncs tactile/vision/force streams.
    2. Alignment: Temporally aligns micro-actions with sensor peaks.
    3. Parameterization: Compresses continuous data into discrete 'genes'.
    """

    def __init__(self, 
                 sampling_rate_hz: int = 1000, 
                 force_threshold: float = 5.0):
        """
        Initialize the digitalization pipeline.
        
        Args:
            sampling_rate_hz: Frequency of sensor data acquisition.
            force_threshold: Minimum force magnitude (N) to consider as active contact.
        """
        self.sampling_rate = sampling_rate_hz
        self.force_threshold = force_threshold
        self._data_buffer: List[TactileSample] = []
        logger.info(f"ArtisanDigitalizer initialized with {sampling_rate_hz}Hz sampling.")

    def ingest_sensor_stream(self, 
                             raw_data: List[Dict[str, Any]], 
                             validate: bool = True) -> bool:
        """
        Ingests raw sensor logs into the internal buffer.
        
        Args:
            raw_data: List of dictionaries containing sensor readings.
            validate: Whether to perform schema validation.
            
        Returns:
            True if ingestion successful, False otherwise.
            
        Raises:
            ValueError: If data structure is invalid.
        """
        logger.info(f"Ingesting {len(raw_data)} raw data points...")
        processed_samples = []
        
        try:
            for idx, entry in enumerate(raw_data):
                if validate:
                    self._validate_entry(entry)
                
                sample = TactileSample(
                    timestamp=entry['ts'],
                    pressure_matrix=np.array(entry['pressure']),
                    vibration_freq=entry['vib_freq'],
                    force_vector=np.array(entry['force']),
                    visual_frame_id=entry['frame_id']
                )
                processed_samples.append(sample)
                
            self._data_buffer.extend(processed_samples)
            logger.info("Data ingestion complete.")
            return True

        except (KeyError, TypeError) as e:
            logger.error(f"Data validation failed at index {idx}: {e}")
            raise ValueError(f"Invalid sensor data format: {e}")
        except Exception as e:
            logger.exception("Unexpected error during ingestion.")
            return False

    def extract_skill_primitives(self, 
                                 window_size_ms: int = 100
                                 ) -> List[SkillPrimitive]:
        """
        Processes buffered data to extract discrete Skill Primitives.
        Uses sliding window analysis to identify stable force/tactile states.
        
        Args:
            window_size_ms: Time window in milliseconds to average for a primitive.
            
        Returns:
            A list of SkillPrimitive objects representing the action sequence.
        """
        if not self._data_buffer:
            logger.warning("Buffer is empty. Nothing to extract.")
            return []

        logger.info(f"Starting Skill Extraction on {len(self._data_buffer)} samples.")
        
        # Sort buffer by time just in case
        self._data_buffer.sort(key=lambda x: x.timestamp)
        
        primitives: List[SkillPrimitive] = []
        
        # Convert window size to seconds
        window_sec = window_size_ms / 1000.0
        
        # Simple segmentation based on significant force changes or time intervals
        # (Here using fixed intervals for demonstration, but logic supports dynamic segmentation)
        
        current_window: List[TactileSample] = []
        window_start_time = self._data_buffer[0].timestamp
        
        for sample in self._data_buffer:
            current_window.append(sample)
            
            # Check if window is full (time-based)
            if sample.timestamp - window_start_time >= window_sec:
                if len(current_window) > 0:
                    primitive = self._process_window(current_window)
                    if primitive:
                        primitives.append(primitive)
                
                # Reset window (with overlap logic if needed, here simple step)
                current_window = []
                window_start_time = sample.timestamp

        logger.info(f"Extraction complete. Generated {len(primitives)} primitives.")
        return primitives

    def _validate_entry(self, entry: Dict[str, Any]) -> None:
        """
        Validates the structure and boundaries of a single sensor data entry.
        
        Args:
            entry: Dictionary containing raw sensor data.
            
        Raises:
            ValueError: If boundary checks fail.
        """
        required_keys = {'ts', 'pressure', 'vib_freq', 'force', 'frame_id'}
        if not required_keys.issubset(entry.keys()):
            missing = required_keys - set(entry.keys())
            raise ValueError(f"Missing keys in entry: {missing}")

        # Boundary Checks
        if entry['ts'] < 0:
            raise ValueError("Timestamp cannot be negative.")
        
        if not (0 <= entry['vib_freq'] <= 20000): # Audio/Tactile freq limits
            logger.warning(f"Unusual vibration frequency detected: {entry['vib_freq']}")

        # Type check for force vector
        if len(entry['force']) != 6:
            raise ValueError("Force vector must have 6 components [Fx, Fy, Fz, Tx, Ty, Tz].")

    def _process_window(self, window: List[TactileSample]) -> Optional[SkillPrimitive]:
        """
        Internal helper to aggregate a time window into a single Skill Primitive.
        
        Args:
            window: List of TactileSamples within the time window.
            
        Returns:
            SkillPrimitive or None if no significant action detected.
        """
        # Filter out noise (check if any significant force is applied)
        forces = np.array([s.force_vector[:3] for s in window]) # Just linear forces
        magnitudes = np.linalg.norm(forces, axis=1)
        avg_magnitude = np.mean(magnitudes)
        
        if avg_magnitude < self.force_threshold:
            return None # Idle state, not a skill primitive

        # Extract Features
        avg_force = np.mean(np.array([s.force_vector for s in window]), axis=0)
        avg_vib = np.mean([s.vibration_freq for s in window])
        
        # Create a 'Force Signature' (simplified as FFT or just normalized vector here)
        # In a real scenario, this would be a complex vector embedding
        force_signature = (avg_force / np.linalg.norm(avg_force)) * avg_magnitude
        
        primitive = SkillPrimitive(
            name=f"primitive_{int(time.time()*1000)}",
            start_time=window[0].timestamp,
            end_time=window[-1].timestamp,
            avg_force=avg_force,
            force_profile_signature=force_signature,
            vibration_harmonics=np.array([avg_vib]),
            success_metric=1.0 # Placeholder for predictive model evaluation
        )
        
        return primitive

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate Mock Data representing a pottery crafting session
    mock_sensor_data = []
    start_ts = time.time()
    
    # Simulate 1 second of data at 100Hz (100 samples)
    # Simulating a "Pinch" action: Increasing force, stable vibration
    for i in range(100):
        force = [0, 0, (i * 0.5) + 5.0, 0, 0, 0] # Increasing Z force
        pressure = [[0, 0], [0, (i * 0.1) + 1.0]]
        
        mock_sensor_data.append({
            'ts': start_ts + (i * 0.01),
            'pressure': pressure,
            'vib_freq': 120.0 + np.random.normal(0, 2), # Slight noise
            'force': force,
            'frame_id': f"frame_{i}"
        })

    # 2. Initialize System
    pipeline = ArtisanDigitalizer(sampling_rate_hz=100, force_threshold=2.0)

    try:
        # 3. Ingest Data
        pipeline.ingest_sensor_stream(mock_sensor_data)
        
        # 4. Extract Skills
        skills = pipeline.extract_skill_primitives(window_size_ms=200)
        
        print(f"\nExtracted {len(skills)} skill primitives.")
        if skills:
            first_skill = skills[0]
            print(f"First Skill: {first_skill.name}")
            print(f"Avg Force Vector: {first_skill.avg_force}")
            
    except ValueError as e:
        print(f"Pipeline Error: {e}")