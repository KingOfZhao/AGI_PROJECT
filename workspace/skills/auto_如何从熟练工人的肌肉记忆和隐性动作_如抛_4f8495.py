"""
Module: kinetic_param_extractor.py
Description: Extracts explicit kinetic parameters from human demonstration data.
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MotionLabel(Enum):
    """Classification labels for motion primitives."""
    EFFECTIVE_CUTTING = "effective_cutting"
    EFFECTIVE_POLISHING = "effective_polishing"
    IDLE_TRANSITION = "idle_transition"
    NOISE = "noise"


@dataclass
class SensorFrame:
    """Represents a single timestamped sensor reading.
    
    Attributes:
        timestamp: Time in seconds since start.
        acc: Acceleration vector (x, y, z) in m/s^2.
        gyro: Angular velocity vector (x, y, z) in rad/s.
        quat: Orientation quaternion (w, x, y, z).
        position: 3D position from visual capture (x, y, z) in meters.
        force: Estimated contact force in Newtons (optional).
    """
    timestamp: float
    acc: np.ndarray
    gyro: np.ndarray
    quat: np.ndarray
    position: np.ndarray
    force: Optional[float] = 0.0

    def __post_init__(self):
        """Validate data types and shapes after initialization."""
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("Timestamp must be a non-negative number.")
        for vec, name, shape in [(self.acc, 'acc', (3,)), 
                                 (self.gyro, 'gyro', (3,)), 
                                 (self.quat', 'quat', (4,)), 
                                 (self.position, 'position', (3,))]:
            if not isinstance(vec, np.ndarray):
                raise TypeError(f"{name} must be a numpy array.")
            if vec.shape != shape:
                raise ValueError(f"{name} must have shape {shape}, got {vec.shape}")


@dataclass
class MotionPrimitive:
    """Represents a discrete, reusable unit of motion.
    
    Attributes:
        start_time: Start timestamp of the primitive.
        end_time: End timestamp of the primitive.
        label: Classification of the motion type.
        avg_force: Average force applied during the segment.
        avg_speed: Average speed of the end-effector.
        trajectory: List of positions (for visualization/replay).
        dynamics_params: Extracted kinetic features (frequency, peak acc, etc.).
    """
    start_time: float
    end_time: float
    label: MotionLabel
    avg_force: float
    avg_speed: float
    trajectory: List[np.ndarray] = field(default_factory=list)
    dynamics_params: Dict[str, float] = field(default_factory=dict)


def _calculate_magnitude(vec: np.ndarray) -> float:
    """Helper: Calculates the Euclidean magnitude of a vector.
    
    Args:
        vec: Input numpy vector.
        
    Returns:
        float: Magnitude of the vector.
        
    Raises:
        ValueError: If vector is empty.
    """
    if vec.size == 0:
        logger.warning("Attempted to calculate magnitude of empty vector.")
        return 0.0
    return float(np.linalg.norm(vec))


def segment_and_extract_primitives(
    data_stream: List[SensorFrame],
    stillness_threshold: float = 0.1,
    min_segment_duration: float = 0.2
) -> List[MotionPrimitive]:
    """Segments continuous sensor data into discrete motion primitives.
    
    This function identifies transition points (zero-velocity crossing or force changes)
    to slice the continuous stream. It then calculates kinetic parameters for each slice.
    
    Args:
        data_stream (List[SensorFrame]): List of synchronized IMU and Vision data.
        stillness_threshold (float): Threshold for velocity/acc magnitude to detect IDLE state.
        min_segment_duration (float): Minimum time in seconds for a valid segment.
        
    Returns:
        List[MotionPrimitive]: A list of extracted, labeled motion primitives.
        
    Raises:
        ValueError: If input list is empty or data is invalid.
    """
    if not data_stream:
        logger.error("Input data stream is empty.")
        raise ValueError("Data stream cannot be empty.")
    
    logger.info(f"Processing {len(data_stream)} frames of sensor data.")
    
    primitives = []
    current_segment_indices: List[int] = []
    
    # State machine variables
    is_active = False
    segment_start_time = 0.0
    
    for i, frame in enumerate(data_stream):
        # Calculate instantaneous dynamics
        acc_mag = _calculate_magnitude(frame.acc)
        vel_mag = _calculate_magnitude(frame.gyro) # Simplified: using gyro rate as movement proxy
        movement_intensity = acc_mag + vel_mag
        
        # State Transition Logic
        if movement_intensity > stillness_threshold:
            if not is_active:
                # Start of a new segment
                is_active = True
                segment_start_time = frame.timestamp
                current_segment_indices = [i]
                logger.debug(f"Segment started at {frame.timestamp:.3f}s")
            else:
                current_segment_indices.append(i)
        else:
            if is_active:
                # End of segment
                is_active = False
                end_frame = data_stream[i-1]
                duration = end_frame.timestamp - segment_start_time
                
                if duration >= min_segment_duration:
                    # Extract Primitive
                    segment_frames = [data_stream[idx] for idx in current_segment_indices]
                    primitive = _analyze_segment(
                        segment_frames, 
                        segment_start_time, 
                        end_frame.timestamp
                    )
                    primitives.append(primitive)
                    logger.info(f"Extracted primitive: {primitive.label.value} ({duration:.2f}s)")
                else:
                    logger.debug(f"Discarding short segment ({duration:.3f}s)")
                
                current_segment_indices = []

    # Handle loop ending while active
    if is_active and current_segment_indices:
        segment_frames = [data_stream[idx] for idx in current_segment_indices]
        primitives.append(_analyze_segment(
            segment_frames, 
            segment_start_time, 
            data_stream[-1].timestamp
        ))

    logger.info(f"Extraction complete. Total primitives: {len(primitives)}")
    return primitives


def _analyze_segment(
    frames: List[SensorFrame], 
    start_t: float, 
    end_t: float
) -> MotionPrimitive:
    """Core logic to analyze a segment of data and extract features.
    
    Calculates average force, speed, and determines if the motion was 
    effective (working) or redundant (movement without work).
    
    Args:
        frames: List of SensorFrame belonging to the segment.
        start_t: Start timestamp.
        end_t: End timestamp.
        
    Returns:
        MotionPrimitive: The processed data object.
    """
    forces = [f.force for f in frames if f.force is not None]
    avg_force = np.mean(forces) if forces else 0.0
    
    # Calculate trajectory length and speed
    total_dist = 0.0
    speeds = []
    for i in range(1, len(frames)):
        delta_pos = _calculate_magnitude(frames[i].position - frames[i-1].position)
        delta_t = frames[i].timestamp - frames[i-1].timestamp
        if delta_t > 0:
            speed = delta_pos / delta_t
            speeds.append(speed)
            total_dist += delta_pos
            
    avg_speed = np.mean(speeds) if speeds else 0.0
    
    # Determine Label: Heuristic for "Effective" vs "Redundant"
    # If force is applied > 0.5N and speed is controlled (< 0.5 m/s), assume effective work
    label = MotionLabel.NOISE
    if avg_force > 0.5 and avg_speed < 0.5:
        label = MotionLabel.EFFECTIVE_POLISHING
    elif avg_speed > 0.1 and avg_force < 0.5:
        label = MotionLabel.IDLE_TRANSITION
    elif avg_force > 0.5:
        label = MotionLabel.EFFECTIVE_CUTTING
        
    # Extract high-level dynamics
    acc_data = np.array([f.acc for f in frames])
    peak_acc = np.max(np.linalg.norm(acc_data, axis=1)) if acc_data.size > 0 else 0.0
    
    dynamics_params = {
        "peak_acceleration": peak_acc,
        "trajectory_length": total_dist,
        "duration": end_t - start_t
    }
    
    return MotionPrimitive(
        start_time=start_t,
        end_time=end_t,
        label=label,
        avg_force=avg_force,
        avg_speed=avg_speed,
        trajectory=[f.position for f in frames],
        dynamics_params=dynamics_params
    )


# =========================================================
# Usage Example
# =========================================================
if __name__ == "__main__":
    # Generate synthetic data simulating a worker polishing
    synthetic_data = []
    t = 0.0
    
    # Phase 1: Idle (0s - 1s)
    for i in range(10):
        synthetic_data.append(SensorFrame(
            timestamp=t, 
            acc=np.random.normal(0, 0.05, 3), 
            gyro=np.random.normal(0, 0.01, 3),
            quat=np.array([1, 0, 0, 0]), 
            position=np.array([i*0.01, 0, 0]),
            force=0.0
        ))
        t += 0.1
        
    # Phase 2: Effective Polishing (1s - 3s)
    # High acceleration variance, low speed, high force
    for i in range(20):
        synthetic_data.append(SensorFrame(
            timestamp=t, 
            acc=np.array([np.sin(i), np.cos(i), 0.2]), # Vibratory motion
            gyro=np.random.normal(0, 0.05, 3),
            quat=np.array([1, 0, 0, 0]), 
            position=np.array([0.1, 0.01*i, 0]), # Slow progression
            force=5.0 # Contact force
        ))
        t += 0.1

    # Phase 3: Retract (3s - 4s)
    for i in range(10):
        synthetic_data.append(SensorFrame(
            timestamp=t, 
            acc=np.array([0.5, 0, 0]), 
            gyro=np.array([0, 0, 0.2]),
            quat=np.array([1, 0, 0, 0]), 
            position=np.array([0.1 + i*0.05, 0.2, 0]), # Fast movement
            force=0.0
        ))
        t += 0.1

    try:
        # Run extraction
        logger.info("Starting extraction process...")
        primitives = segment_and_extract_primitives(synthetic_data, stillness_threshold=0.2)
        
        # Output results
        print(f"\n{'='*10} RESULTS {'='*10}")
        print(f"Found {len(primitives)} motion primitives.")
        for p in primitives:
            print(f"  - Type: {p.label.value:<20} | Time: {p.start_t:.1f}s-{p.end_t:.1f}s | Force: {p.avg_force:.1f}N")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")