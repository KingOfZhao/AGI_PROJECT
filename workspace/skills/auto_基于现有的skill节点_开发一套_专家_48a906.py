"""
Expert Intuition Extraction System - Decision Keyframe Detector

This module provides algorithms to automatically identify 'Implicit Decision Keyframes'
from sensor data (eye-tracking and motion/force sensors) during skilled task replay.
It addresses the problem of manual annotation by detecting physiological and kinematic
anomalies that correlate with cognitive decision-making moments.

Domain: cognitive_science
Author: Senior Python Engineer for AGI System
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from scipy.signal import find_peaks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SensorFrame:
    """
    Represents a single frame of synchronized sensor data.
    
    Attributes:
        timestamp (float): Timestamp in milliseconds.
        pupil_diameter (float): Pupil diameter in mm (proxy for cognitive load).
        gaze_x (float): Gaze X coordinate.
        gaze_y (float): Gaze Y coordinate.
        force (float): Applied force/pressure by the artisan.
        velocity (float): Movement velocity of the tool/hand.
    """
    timestamp: float
    pupil_diameter: float
    gaze_x: float
    gaze_y: float
    force: float
    velocity: float


class DecisionKeyframeDetector:
    """
    Detects decision keyframes based on multi-modal signal analysis.
    
    The algorithm hypothesizes that decision points are characterized by:
    1. A spike in cognitive load (pupil dilation).
    2. A shift in attention (saccade/rapid gaze movement).
    3. A change in motor output (force/velocity inflection).
    """

    def __init__(self, sampling_rate: float = 60.0):
        """
        Initialize the detector.
        
        Args:
            sampling_rate (float): Sampling rate of the sensor data in Hz.
        """
        self.sampling_rate = sampling_rate
        self._validate_init_params()

    def _validate_init_params(self) -> None:
        """Validate initialization parameters."""
        if self.sampling_rate <= 0:
            raise ValueError("Sampling rate must be positive.")

    def _validate_input_data(self, data: List[SensorFrame]) -> None:
        """
        Validate the input sensor data stream.
        
        Args:
            data (List[SensorFrame]): List of sensor frames.
            
        Raises:
            ValueError: If data is empty, not sorted, or contains invalid values.
        """
        if not data:
            raise ValueError("Input data list cannot be empty.")
        
        # Check for monotonic timestamps
        timestamps = [frame.timestamp for frame in data]
        if not all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1)):
            raise ValueError("Timestamps must be monotonically increasing.")
            
        # Check for NaN/Inf in critical fields
        for i, frame in enumerate(data):
            if not np.isfinite([frame.pupil_diameter, frame.force, frame.velocity]).all():
                logger.warning(f"Frame {i} contains non-finite values. Skipping or handling might be required.")

    def _calculate_gaze_velocity(self, data: List[SensorFrame]) -> np.ndarray:
        """
        Calculate the magnitude of gaze velocity (saccade detection).
        
        Args:
            data (List[SensorFrame]): Sensor data.
            
        Returns:
            np.ndarray: Array of gaze velocities.
        """
        n = len(data)
        gaze_vel = np.zeros(n)
        
        for i in range(1, n):
            dt = (data[i].timestamp - data[i-1].timestamp) / 1000.0  # ms to s
            if dt == 0:
                continue
                
            dx = data[i].gaze_x - data[i-1].gaze_x
            dy = data[i].gaze_y - data[i-1].gaze_y
            dist = np.sqrt(dx**2 + dy**2)
            gaze_vel[i] = dist / dt
            
        return gaze_vel

    def _calculate_cognitive_arousal_index(self, data: List[SensorFrame]) -> np.ndarray:
        """
        Core Function 1: Calculate a composite index representing cognitive arousal.
        
        Combines pupil dilation (cognitive load) and gaze velocity (attention shift).
        
        Args:
            data (List[SensorFrame]): Sensor data.
            
        Returns:
            np.ndarray: Normalized cognitive arousal index.
        """
        pupil_signal = np.array([f.pupil_diameter for f in data])
        gaze_vel_signal = self._calculate_gaze_velocity(data)
        
        # Normalize signals to 0-1 range to handle different units
        def normalize(sig):
            min_val, max_val = np.min(sig), np.max(sig)
            if max_val - min_val == 0:
                return np.zeros_like(sig)
            return (sig - min_val) / (max_val - min_val)

        norm_pupil = normalize(pupil_signal)
        norm_gaze = normalize(gaze_vel_signal)
        
        # Weighted sum: Pupil dilation is a stronger indicator of decision load
        arousal_index = 0.7 * norm_pupil + 0.3 * norm_gaze
        
        logger.info("Cognitive arousal index calculated successfully.")
        return arousal_index

    def detect_decision_keyframes(
        self, 
        data: List[SensorFrame], 
        arousal_threshold: float = 0.75,
        force_change_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Core Function 2: Identify keyframes where implicit decisions likely occurred.
        
        A keyframe is identified if there is a peak in cognitive arousal 
        coinciding with a significant change in force or velocity (motor execution change).
        
        Args:
            data (List[SensorFrame]): List of sensor frames.
            arousal_threshold (float): Percentile threshold (0.0-1.0) for arousal peaks.
            force_change_threshold (float): Threshold for force derivative to consider it a 'shift'.
            
        Returns:
            List[Dict[str, Any]]: List of detected keyframes containing timestamp, 
                                  confidence score, and context.
        """
        self._validate_input_data(data)
        
        n = len(data)
        if n < 5:
            logger.warning("Data sequence too short for reliable detection.")
            return []

        # 1. Calculate Cognitive Arousal
        arousal = self._calculate_cognitive_arousal_index(data)
        
        # 2. Calculate Kinematic Derivatives (Force and Velocity changes)
        force_signal = np.array([f.force for f in data])
        # Simple derivative approximation
        force_diff = np.abs(np.diff(force_signal, prepend=force_signal[0]))
        
        # 3. Find Peaks in Cognitive Arousal
        # Use a dynamic height threshold based on the arousal_threshold percentile
        min_height = np.percentile(arousal, arousal_threshold * 100)
        peaks, properties = find_peaks(arousal, height=min_height, distance=int(self.sampling_rate * 0.5))
        
        keyframes = []
        
        for peak_idx in peaks:
            # 4. Contextual Validation: Check if there is a motor change near the cognitive peak
            # Look in a small window around the peak (e.g., +/- 200ms)
            window = int(self.sampling_rate * 0.2)
            start = max(0, peak_idx - window)
            end = min(n, peak_idx + window)
            
            local_force_change = np.max(force_diff[start:end])
            
            # Decision Logic: High Mental Load + Motor Adjustment = Decision Point
            if local_force_change > force_change_threshold:
                confidence = (arousal[peak_idx] + min(local_force_change, 1.0)) / 2.0
                
                keyframe = {
                    "timestamp_ms": data[peak_idx].timestamp,
                    "frame_index": peak_idx,
                    "confidence": round(float(confidence), 3),
                    "arousal_level": round(float(arousal[peak_idx]), 3),
                    "force_change_rate": round(float(local_force_change), 3),
                    "reason": "High cognitive load coinciding with force adjustment"
                }
                keyframes.append(keyframe)
                logger.debug(f"Keyframe detected at {data[peak_idx].timestamp}ms with confidence {confidence}")

        logger.info(f"Detection complete. Found {len(keyframes)} decision keyframes.")
        return keyframes


# Example Usage
if __name__ == "__main__":
    # Generate synthetic data for demonstration
    # Simulating a 10-second session at 60Hz
    duration_sec = 10
    rate = 60
    num_frames = duration_sec * rate
    
    synthetic_data: List[SensorFrame] = []
    
    # Base values
    base_pupil = 4.0
    base_force = 10.0
    
    for i in range(num_frames):
        t = i * (1000 / rate)
        
        # Simulate a "Decision Event" around t=5.0s
        # Event characteristics: Pupil dilates, Force changes rapidly
        is_event = 4.5 < (t / 1000.0) < 5.5
        
        current_pupil = base_pupil + (1.5 if is_event else 0.0) + np.random.normal(0, 0.1)
        
        # Force changes smoothly, then spikes during event
        current_force = base_force + np.sin(i / 20.0) * 2.0
        if is_event:
            current_force += np.sin((i - 4.5*rate) / 5.0) * 5.0 # Rapid fluctuation
            
        # Gaze moves randomly, but faster during event
        gaze_x = np.cumsum(np.random.normal(0, 0.5 if is_event else 0.1))[-1]
        gaze_y = np.cumsum(np.random.normal(0, 0.5 if is_event else 0.1))[-1]
        
        synthetic_data.append(SensorFrame(
            timestamp=t,
            pupil_diameter=current_pupil,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            force=current_force,
            velocity=abs(np.random.normal(0, 1))
        ))

    # Run Detection
    detector = DecisionKeyframeDetector(sampling_rate=rate)
    try:
        results = detector.detect_decision_keyframes(synthetic_data)
        
        print("\n=== Detected Decision Keyframes ===")
        for res in results:
            print(f"Time: {res['timestamp_ms']}ms | "
                  f"Confidence: {res['confidence']} | "
                  f"Reason: {res['reason']}")
                  
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")