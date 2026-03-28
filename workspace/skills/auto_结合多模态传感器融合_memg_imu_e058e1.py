"""
Module: auto_结合多模态传感器融合_memg_imu_e058e1
Description: Advanced AGI Skill for Multimodal Sensor Fusion (MEMG/IMU) with Cognitive Friction Detection.
             This module processes physical motion data alongside physiological signals to detect
             "Cognitive Friction" — points where physical action difficulty correlates with high
             mental effort. It is designed for applications in intelligent tutoring, robotic
             skill transfer, and adaptive ergonomics.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, TypedDict
from dataclasses import dataclass, field
from enum import Enum

# --- Configuration & Constants ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Thresholds for detection logic
JERK_THRESHOLD = 15.0  # m/s^3 (Physical difficulty indicator)
MENTAL_EFFORT_THRESHOLD = 0.7  # 0.0 to 1.0 (Normalized cognitive load)
COGNITIVE_FRICTION_SCORE_MIN = 0.0
COGNITIVE_FRICTION_SCORE_MAX = 1.0


class SensorError(Exception):
    """Custom exception for sensor data anomalies."""
    pass


class SkillDifficulty(Enum):
    """Enumeration of skill difficulty levels based on friction analysis."""
    SMOOTH = "smooth"
    MODERATE = "moderate"
    HIGH_FRICTION = "high_friction"
    CRITICAL = "critical"


class SensorDataDict(TypedDict):
    """Type definition for input sensor data dictionary."""
    timestamp: List[float]  # Unix timestamps
    accel_x: List[float]    # Acceleration X (m/s^2)
    accel_y: List[float]    # Acceleration Y (m/s^2)
    accel_z: List[float]    # Acceleration Z (m/s^2)
    gyro_x: List[float]     # Gyroscope X (rad/s)
    gyro_y: List[float]     # Gyroscope Y (rad/s)
    gyro_z: List[float]     # Gyroscope Z (rad/s)
    memg_signal: List[float] # MEMG (Muscle/Electrical) signal intensity (0.0-1.0)


@dataclass
class CognitiveState:
    """Represents the analyzed cognitive and physical state at a specific moment."""
    timestamp: float
    jerk_magnitude: float
    mental_effort_index: float
    friction_score: float
    difficulty_label: SkillDifficulty
    suggestions: List[str] = field(default_factory=list)


def _validate_sensor_inputs(data: SensorDataDict) -> None:
    """
    Validates the structure and content of sensor data.
    
    Args:
        data: Dictionary containing sensor arrays.
        
    Raises:
        SensorError: If data is missing, empty, or contains non-numeric values.
        ValueError: If array lengths do not match.
    """
    if not data:
        raise SensorError("Input sensor data cannot be empty.")
    
    required_keys = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 
                     'gyro_x', 'gyro_y', 'gyro_z', 'memg_signal']
    
    lengths = []
    for key in required_keys:
        if key not in data:
            raise SensorError(f"Missing required sensor key: {key}")
        if not isinstance(data[key], list) or len(data[key]) == 0:
            raise SensorError(f"Data for key '{key}' must be a non-empty list.")
        
        # Check for numeric types
        try:
            [float(x) for x in data[key]]
        except (ValueError, TypeError):
            raise SensorError(f"Non-numeric value found in sensor stream: {key}")
            
        lengths.append(len(data[key]))
    
    if len(set(lengths)) != 1:
        raise ValueError("All sensor arrays must have the same length (sync error).")
    
    logger.debug(f"Sensor validation passed for {lengths[0]} samples.")


def calculate_motion_jerk(accel_data: np.ndarray, gyro_data: np.ndarray, dt: float = 0.01) -> np.ndarray:
    """
    Core Function 1: Calculates the magnitude of 'Jerk' (rate of change of acceleration) 
    and combines it with rotational velocity to estimate physical smoothness.
    
    Args:
        accel_data: Nx3 numpy array (X, Y, Z acceleration).
        gyro_data: Nx3 numpy array (X, Y, Z angular velocity).
        dt: Time step between samples in seconds.
        
    Returns:
        np.ndarray: 1D array of combined physical difficulty indices.
        
    Raises:
        ValueError: If dt is not positive.
    """
    if dt <= 0:
        raise ValueError("Time step (dt) must be positive.")
        
    try:
        # Calculate derivative of acceleration (Jerk)
        # Using numpy gradient for central differences
        jerk_x = np.gradient(accel_data[:, 0], dt)
        jerk_y = np.gradient(accel_data[:, 1], dt)
        jerk_z = np.gradient(accel_data[:, 2], dt)
        
        jerk_magnitude = np.sqrt(jerk_x**2 + jerk_y**2 + jerk_z**2)
        
        # Normalize gyro magnitude to combine with jerk
        gyro_mag = np.sqrt(np.sum(gyro_data**2, axis=1))
        
        # Combine: High jerk + High rotation = High physical difficulty
        # This is a simplified heuristic for "Physical Friction"
        combined_metric = jerk_magnitude + (gyro_mag * 0.5) 
        
        logger.info("Motion jerk and physical difficulty calculated.")
        return combined_metric
        
    except Exception as e:
        logger.exception("Failed to calculate motion jerk.")
        raise SensorError(f"Motion calculation error: {e}")


def detect_cognitive_friction(
    sensor_data: SensorDataDict, 
    smooth_window: int = 5
) -> List[CognitiveState]:
    """
    Core Function 2: Analyzes multimodal data to detect Cognitive Friction points.
    
    This function fuses IMU data (physical motion smoothness) with MEMG data 
    (physiological effort/attention) to identify moments where the user struggles 
    to execute a physical task.
    
    Args:
        sensor_data: Validated dictionary containing IMU and MEMG streams.
        smooth_window: Window size for moving average smoothing.
        
    Returns:
        List[CognitiveState]: A time-series of analyzed states.
        
    Example:
        >>> data = {
        ...     "timestamp": [0.0, 0.1, 0.2], 
        ...     "accel_x": [0.1, 0.2, 5.0], # Spike at 0.2
        ...     "accel_y": [0.0, 0.0, 0.0],
        ...     "accel_z": [9.8, 9.8, 9.8],
        ...     "gyro_x": [0.0, 0.0, 0.0],
        ...     "gyro_y": [0.0, 0.0, 0.0],
        ...     "gyro_z": [0.0, 0.0, 0.0],
        ...     "memg_signal": [0.2, 0.2, 0.9] # High focus at 0.2
        ... }
        >>> results = detect_cognitive_friction(data)
        >>> print(results[-1].difficulty_label)
        SkillDifficulty.HIGH_FRICTION
    """
    _validate_sensor_inputs(sensor_data)
    
    # Convert to numpy for efficiency
    accel = np.column_stack([
        sensor_data['accel_x'], 
        sensor_data['accel_y'], 
        sensor_data['accel_z']
    ])
    gyro = np.column_stack([
        sensor_data['gyro_x'], 
        sensor_data['gyro_y'], 
        sensor_data['gyro_z']
    ])
    memg = np.array(sensor_data['memg_signal'])
    timestamps = np.array(sensor_data['timestamp'])
    
    # 1. Calculate Physical Metric (Jerk)
    try:
        dt = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else 0.01
        physical_difficulty = calculate_motion_jerk(accel, gyro, dt)
    except Exception:
        # Fallback if timestamps are uniform
        physical_difficulty = calculate_motion_jerk(accel, gyro, 0.01)
    
    # 2. Smooth MEMG signal (Noise reduction)
    memg_smoothed = np.convolve(
        memg, 
        np.ones(smooth_window)/smooth_window, 
        mode='same'
    )
    
    # 3. Normalize Metrics to 0-1 range for fusion
    # Handle division by zero if signal is flat
    phys_norm = physical_difficulty / (np.max(physical_difficulty) + 1e-6)
    ment_norm = memg_smoothed / (np.max(memg_smoothed) + 1e-6)
    
    results: List[CognitiveState] = []
    
    for i in range(len(timestamps)):
        # Calculate Friction Score
        # Formula: Weighted average. High physical jerk + High mental effort = Friction
        # If physical is low but mental is high -> Curiosity/Planning (Low Friction)
        # If physical is high but mental is low -> Habitual/Risky (Medium Friction)
        
        if phys_norm[i] > 0.6 and ment_norm[i] > MENTAL_EFFORT_THRESHOLD:
            friction_score = (phys_norm[i] + ment_norm[i]) / 2.0
            difficulty = SkillDifficulty.HIGH_FRICTION
            suggestion = ["Suggest slowing down", "Check tool alignment"]
        elif phys_norm[i] > 0.8:
            friction_score = phys_norm[i]
            difficulty = SkillDifficulty.CRITICAL
            suggestion = ["Stop motion", "Safety check triggered"]
        elif phys_norm[i] > JERK_THRESHOLD / (np.max(physical_difficulty) + 1e-6):
            friction_score = phys_norm[i] * 0.8
            difficulty = SkillDifficulty.MODERATE
            suggestion = ["Maintain steady speed"]
        else:
            friction_score = phys_norm[i] * 0.5
            difficulty = SkillDifficulty.SMOOTH
            suggestion = []
            
        # Clip score
        friction_score = np.clip(friction_score, COGNITIVE_FRICTION_SCORE_MIN, COGNITIVE_FRICTION_SCORE_MAX)
        
        state = CognitiveState(
            timestamp=timestamps[i],
            jerk_magnitude=float(physical_difficulty[i]),
            mental_effort_index=float(ment_norm[i]),
            friction_score=float(friction_score),
            difficulty_label=difficulty,
            suggestions=suggestion
        )
        results.append(state)
        
    logger.info(f"Processed {len(results)} sensor frames. Detected friction events logged.")
    return results


def generate_teaching_report(analysis_results: List[CognitiveState]) -> Dict[str, str]:
    """
    Helper Function: Aggregates the analysis results into a human-readable teaching report.
    
    Args:
        analysis_results: List of CognitiveState objects from the detector.
        
    Returns:
        Dict: A summary containing total events and advice.
    """
    if not analysis_results:
        return {"status": "No data provided"}
    
    high_friction_count = sum(
        1 for state in analysis_results 
        if state.difficulty_label in [SkillDifficulty.HIGH_FRICTION, SkillDifficulty.CRITICAL]
    )
    
    total_frames = len(analysis_results)
    friction_ratio = high_friction_count / total_frames
    
    if friction_ratio > 0.3:
        overall_assessment = "Significant struggle detected. Recommend fundamental review."
    elif friction_ratio > 0.1:
        overall_assessment = "Moderate difficulty. Focus on specific transition points."
    else:
        overall_assessment = "Execution smooth. Proceed to advanced variations."
        
    return {
        "total_frames": str(total_frames),
        "high_friction_frames": str(high_friction_count),
        "friction_ratio": f"{friction_ratio:.2f}",
        "assessment": overall_assessment
    }

# ---------------------------------------------------------
# Usage Example (Runnable script)
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Simulate Sensor Data (e.g., from a pottery wheel session)
    # 100 samples, 10Hz sampling rate
    n_samples = 100
    t = np.linspace(0, 10, n_samples)
    
    # Normal motion + a "struggle" spike at t=5
    accel_x = np.sin(t) + np.random.normal(0, 0.1, n_samples)
    accel_x[45:55] += np.random.normal(5, 1, 10) # High Jerk Spike
    
    # Cognitive load (MEMG) spikes simultaneously
    memg = np.random.uniform(0.1, 0.3, n_samples)
    memg[45:55] = np.random.uniform(0.8, 1.0, 10) # High Focus/Stress
    
    dummy_data: SensorDataDict = {
        "timestamp": t.tolist(),
        "accel_x": accel_x.tolist(),
        "accel_y": np.zeros(n_samples).tolist(),
        "accel_z": np.full(n_samples, 9.8).tolist(),
        "gyro_x": np.zeros(n_samples).tolist(),
        "gyro_y": np.zeros(n_samples).tolist(),
        "gyro_z": np.random.uniform(0, 0.5, n_samples).tolist(),
        "memg_signal": memg.tolist()
    }
    
    print("Running Sensor Fusion Analysis...")
    
    try:
        # 2. Run Detection
        states = detect_cognitive_friction(dummy_data)
        
        # 3. Generate Report
        report = generate_teaching_report(states)
        
        print("\n--- Analysis Report ---")
        for k, v in report.items():
            print(f"{k.upper()}: {v}")
            
        # Display a specific high friction moment
        critical_moment = next((s for s in states if s.difficulty_label == SkillDifficulty.HIGH_FRICTION), None)
        if critical_moment:
            print(f"\nCritical Moment Detected at t={critical_moment.timestamp:.2f}s")
            print(f"Friction Score: {critical_moment.friction_score:.3f}")
            print(f"Suggestion: {critical_moment.suggestions[0]}")
            
    except (SensorError, ValueError) as e:
        print(f"System Error: {e}")