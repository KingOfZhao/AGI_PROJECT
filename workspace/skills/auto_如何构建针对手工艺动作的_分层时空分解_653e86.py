"""
Module: hierarchical_spatiotemporal_decomposition
Description: Implements a Hierarchical Spatiotemporal Decomposition algorithm for parsing
             continuous video streams of craftsmanship actions into semantic atomic actions.
             It focuses on detecting non-linear rhythm changes (hesitations, accelerations)
             to identify semantic boundaries.

Author: AGI System
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class Keypoint:
    """Represents a 2D/3D keypoint with confidence."""
    x: float
    y: float
    score: float = 1.0
    z: Optional[float] = None  # Depth if available

@dataclass
class PoseFrame:
    """Represents the skeleton data for a single video frame."""
    frame_id: int
    timestamp: float
    keypoints: Dict[str, Keypoint]  # Mapping of joint names to Keypoint objects

@dataclass
class AtomicAction:
    """Represents a detected atomic action segment."""
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    label: str  # e.g., 'push', 'pull', 'hold'
    features: Dict[str, Any] = field(default_factory=dict)

# --- Helper Functions ---

def validate_input_data(data_stream: List[PoseFrame]) -> bool:
    """
    Validates the input pose data stream.
    
    Args:
        data_stream (List[PoseFrame]): List of pose frames.
        
    Returns:
        bool: True if data is valid.
        
    Raises:
        ValueError: If data is empty or frames are inconsistent.
    """
    if not data_stream:
        logger.error("Input data stream is empty.")
        raise ValueError("Input data stream cannot be empty.")
    
    required_joints = {'left_wrist', 'right_wrist', 'left_elbow', 'right_elbow'}
    
    for i, frame in enumerate(data_stream):
        if not isinstance(frame, PoseFrame):
            raise TypeError(f"Frame at index {i} is not a PoseFrame instance.")
        
        # Check for monotonicity of timestamps
        if i > 0 and frame.timestamp <= data_stream[i-1].timestamp:
            logger.warning(f"Non-monotonic timestamp detected at frame {frame.frame_id}")
            
        # Check critical joints existence
        if not required_joints.issubset(frame.keypoints.keys()):
            missing = required_joints - frame.keypoints.keys()
            raise ValueError(f"Frame {frame.frame_id} missing critical joints: {missing}")
            
    logger.info("Input data validation passed.")
    return True

# --- Core Algorithms ---

def calculate_velocity_profile(data_stream: List[PoseFrame], joint_name: str = 'right_wrist') -> np.ndarray:
    """
    Calculates the velocity profile of a specific joint, including speed and direction changes.
    Normalizes time to handle variable frame rates.
    
    Args:
        data_stream (List[PoseFrame]): The sequence of pose data.
        joint_name (str): The joint to track (typically the dominant hand).
        
    Returns:
        np.ndarray: A 2D array where columns are [timestamp, speed, acceleration].
    """
    logger.info(f"Calculating velocity profile for joint: {joint_name}")
    
    velocities = []
    n = len(data_stream)
    
    # Pre-compute positions
    positions = np.array([
        [p.timestamp, p.keypoints[joint_name].x, p.keypoints[joint_name].y] 
        for p in data_stream
    ])
    
    # Calculate derivatives
    for i in range(1, n - 1):
        dt_prev = positions[i, 0] - positions[i-1, 0]
        dt_next = positions[i+1, 0] - positions[i, 0]
        
        # Prevent division by zero
        if dt_prev <= 0 or dt_next <= 0:
            continue
            
        # Central difference for velocity
        dx = (positions[i+1, 1] - positions[i-1, 1]) / (dt_prev + dt_next)
        dy = (positions[i+1, 2] - positions[i-1, 2]) / (dt_prev + dt_next)
        speed = np.sqrt(dx**2 + dy**2)
        
        velocities.append([positions[i, 0], speed])
    
    velocities_arr = np.array(velocities)
    
    # Calculate acceleration (derivative of speed) to detect rhythm changes
    if velocities_arr.shape[0] > 1:
        timestamps = velocities_arr[:, 0]
        speeds = velocities_arr[:, 1]
        
        # Smooth speed slightly to remove noise
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smoothed_speeds = np.convolve(speeds, kernel, mode='same')
        
        accels = np.gradient(smoothed_speeds, timestamps)
        
        # Stack: [Time, Speed, Acceleration]
        profile = np.column_stack((timestamps, smoothed_speeds, accels))
        return profile
    
    return np.array([])

def detect_semantic_boundaries(
    velocity_profile: np.ndarray, 
    speed_threshold: float = 0.05, 
    accel_sensitivity: float = 0.5
) -> List[int]:
    """
    Identifies keyframe indices based on non-linear velocity changes.
    This implements the 'Temporal Decomposition'.
    
    Args:
        velocity_profile (np.ndarray): Output from calculate_velocity_profile.
        speed_threshold (float): Minimum speed to consider as movement (filters noise).
        accel_sensitivity (float): Factor multiplied by std dev of acceleration to detect peaks.
        
    Returns:
        List[int]: Indices of the original data stream where actions change.
    """
    if velocity_profile.size == 0:
        return []

    logger.info("Analyzing temporal rhythm for semantic boundaries...")
    
    speeds = velocity_profile[:, 1]
    accels = np.abs(velocity_profile[:, 2])
    
    # Dynamic thresholding for hesitation/acceleration
    mean_accel = np.mean(accels)
    std_accel = np.std(accels)
    dynamic_threshold = mean_accel + (accel_sensitivity * std_accel)
    
    # Identify candidate frames where acceleration is high (changes in rhythm)
    # or speed drops near zero (potential stops/pauses)
    candidates = set()
    
    # 1. High acceleration peaks (start/stop movements)
    peak_indices = np.where(accels > dynamic_threshold)[0]
    candidates.update(peak_indices)
    
    # 2. Zero-velocity crossings (pauses)
    # We look for local minima in speed below threshold
    for i in range(1, len(speeds) - 1):
        if speeds[i] < speeds[i-1] and speeds[i] < speeds[i+1] and speeds[i] < speed_threshold:
            candidates.add(i)
            
    # Sort boundaries
    sorted_boundaries = sorted(list(candidates))
    
    # Merge boundaries that are too close (temporal clustering)
    min_gap = 5 # frames
    final_boundaries = []
    if sorted_boundaries:
        last = sorted_boundaries[0]
        final_boundaries.append(last)
        for idx in sorted_boundaries[1:]:
            if idx - last > min_gap:
                final_boundaries.append(idx)
                last = idx
    
    logger.info(f"Detected {len(final_boundaries)} semantic boundaries.")
    return final_boundaries

def classify_motion_segment(
    segment_data: List[PoseFrame], 
    joint_name: str = 'right_wrist'
) -> str:
    """
    Classifies the motion of a segment (Spatial/Semantic Analysis).
    
    Args:
        segment_data (List[PoseFrame]): Subset of frames for one action.
        joint_name (str): Tracked joint.
        
    Returns:
        str: Label ('Push', 'Pull', 'Lift', 'Press', 'Hold', 'Unknown').
    """
    if len(segment_data) < 2:
        return "Unknown"
    
    start_pos = segment_data[0].keypoints[joint_name]
    end_pos = segment_data[-1].keypoints[joint_name]
    
    # Vector calculation
    dx = end_pos.x - start_pos.x
    dy = end_pos.y - start_pos.y
    dz = 0.0
    
    if start_pos.z is not None and end_pos.z is not None:
        dz = end_pos.z - start_pos.z
        
    dist = np.sqrt(dx**2 + dy**2 + dz**2)
    
    if dist < 0.02: # Threshold for static
        return "Hold"
    
    # Determine dominant axis
    abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)
    
    if abs_dx > abs_dy and abs_dx > abs_dz:
        return "Push" if dx > 0 else "Pull"
    elif abs_dy > abs_dx and abs_dy > abs_dz:
        # In image coords, Y increases downwards usually. 
        # Assuming standard coordinates where Y up is positive.
        return "Lift" if dy < 0 else "Press" 
    else:
        return "Reach" if dz > 0 else "Retract"

def run_hierarchical_decomposition(
    video_pose_stream: List[PoseFrame], 
    dominant_hand: str = 'right'
) -> List[AtomicAction]:
    """
    Main entry point. Processes raw pose stream to generate semantic atomic actions.
    
    Args:
        video_pose_stream (List[PoseFrame]): Input data.
        dominant_hand (str): 'left' or 'right'.
        
    Returns:
        List[AtomicAction]: List of segmented and labeled actions.
        
    Example:
        >>> mock_data = [PoseFrame(frame_id=i, timestamp=i/30.0, 
        >>>               keypoints={'right_wrist': Keypoint(x=i*0.1, y=5.0)}) for i in range(100)]
        >>> actions = run_hierarchical_decomposition(mock_data)
    """
    try:
        validate_input_data(video_pose_stream)
    except (ValueError, TypeError) as e:
        logger.error(f"Input validation failed: {e}")
        return []

    joint = f'{dominant_hand}_wrist'
    logger.info(f"Starting Hierarchical Decomposition for {joint}...")

    # 1. Temporal Feature Extraction
    # Profile shape: [Time, Speed, Accel]
    profile = calculate_velocity_profile(video_pose_stream, joint_name=joint)
    
    if profile.size == 0:
        logger.warning("Insufficient data to calculate velocity profile.")
        return []

    # 2. Temporal Segmentation
    # Note: boundaries are indices relative to the profile (which is shorter than original stream)
    boundaries = detect_semantic_boundaries(profile)
    
    # Map boundaries back to original frame indices (approximate offset due to gradient)
    # Gradient reduces length by 2, central difference reduces by 1 more roughly.
    # We need to map profile index `i` to stream index `i+1`.
    
    action_segments = []
    start_idx = 0
    
    # Add start and end of video as implicit boundaries
    all_boundaries = [0] + [b + 1 for b in boundaries] + [len(video_pose_stream) - 1]
    unique_boundaries = sorted(list(set(all_boundaries)))

    for i in range(len(unique_boundaries) - 1):
        seg_start = unique_boundaries[i]
        seg_end = unique_boundaries[i+1]
        
        if seg_start >= seg_end:
            continue
            
        segment_frames = video_pose_stream[seg_start : seg_end+1]
        
        # 3. Spatial/Semantic Classification
        label = classify_motion_segment(segment_frames, joint_name=joint)
        
        # Create Action Object
        action = AtomicAction(
            start_frame=segment_frames[0].frame_id,
            end_frame=segment_frames[-1].frame_id,
            start_time=segment_frames[0].timestamp,
            end_time=segment_frames[-1].timestamp,
            label=label,
            features={
                'duration': segment_frames[-1].timestamp - segment_frames[0].timestamp,
                'dominant_hand': dominant_hand
            }
        )
        action_segments.append(action)
        
    logger.info(f"Decomposition complete. Generated {len(action_segments)} atomic actions.")
    return action_segments

# --- Main Execution (Example) ---
if __name__ == "__main__":
    # Create dummy data simulating a "Push" action followed by a "Hold"
    dummy_stream = []
    for i in range(60):
        # Frames 0-20: Move right (Push)
        x = 0.1 * i if i < 20 else 2.0
        y = 1.0
        # Add some noise
        x += np.random.normal(0, 0.01)
        
        kp = Keypoint(x=x, y=y, score=0.99)
        frame = PoseFrame(
            frame_id=i, 
            timestamp=i/30.0, 
            keypoints={
                'right_wrist': kp,
                'left_wrist': Keypoint(x=0, y=0),
                'right_elbow': Keypoint(x=1, y=1),
                'left_elbow': Keypoint(x=1, y=1)
            }
        )
        dummy_stream.append(frame)

    # Run the algorithm
    try:
        results = run_hierarchical_decomposition(dummy_stream)
        print("\n--- Detected Atomic Actions ---")
        for action in results:
            print(f"[{action.start_time:.2f}s - {action.end_time:.2f}s] : {action.label}")
    except Exception as e:
        logger.error(f"Runtime error: {e}")