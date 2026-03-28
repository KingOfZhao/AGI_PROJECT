"""
Module: auto_基于多模态传感器融合的微小动作数字化_如_c4ed10
Description: Captures and fuses data from high-precision motion capture gloves and FPV video
             to digitize subtle craftsmanship actions (e.g., pottery).
Author: AGI System
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class SensorConfig:
    """Configuration for sensor parameters."""
    glove_sample_rate: int = 120  # Hz
    video_fps: int = 60
    force_threshold: float = 0.05  # Minimum force to consider (0.0 to 1.0)
    joint_angle_range: Tuple[int, int] = (0, 180)  # Degrees

@dataclass
class GloveData:
    """Represents a single frame of motion capture glove data."""
    timestamp: float
    joint_angles: Dict[str, float]  # Joint name -> Angle (degrees)
    fingertip_forces: Dict[str, float]  # Finger name -> Pressure (normalized 0.0-1.0)
    valid: bool = True

@dataclass
class VideoFrame:
    """Represents a single frame of FPV video with metadata."""
    timestamp: float
    frame_data: np.ndarray  # Image data (H, W, C)
    resolution: Tuple[int, int]  # (Width, Height)

@dataclass
class FusedActionPrimitive:
    """The output data structure containing synchronized multimodal data."""
    timestamp: float
    duration: float
    trajectory_3d: List[Dict[str, float]] # List of {x, y, z} coordinates over time
    force_profile: List[float] # Force magnitude over time
    visual_embedding: Optional[List[float]] = None # Placeholder for visual features

# --- Custom Exceptions ---

class SensorFusionError(Exception):
    """Base exception for sensor fusion errors."""
    pass

class DataValidationError(SensorFusionError):
    """Raised when input data fails validation checks."""
    pass

class SynchronizationError(SensorFusionError):
    """Raised when time synchronization between sensors fails."""
    pass

# --- Core Functions ---

def validate_glove_data(data: GloveData, config: SensorConfig) -> bool:
    """
    Validates the integrity and range of glove sensor data.
    
    Args:
        data (GloveData): The input data object.
        config (SensorConfig): Configuration containing boundary limits.
        
    Returns:
        bool: True if valid.
        
    Raises:
        DataValidationError: If data is out of bounds or malformed.
    """
    if not data.valid:
        raise DataValidationError("Glove data marked as invalid by hardware.")

    # Check Joint Angles
    min_ang, max_ang = config.joint_angle_range
    for joint, angle in data.joint_angles.items():
        if not (min_ang <= angle <= max_ang):
            logger.warning(f"Joint {joint} angle {angle} out of range [{min_ang}, {max_ang}]. Clamping.")
            # Auto-correction strategy: Clamping
            data.joint_angles[joint] = np.clip(angle, min_ang, max_ang)
            
    # Check Forces
    for finger, force in data.fingertip_forces.items():
        if not (0.0 <= force <= 1.0):
            logger.error(f"Invalid force reading {force} for {finger}. Must be normalized.")
            raise DataValidationError(f"Force value {force} exceeds normalized bounds.")
            
    logger.debug("Glove data validation passed.")
    return True

def extract_visual_roi(frame: VideoFrame, roi_box: Tuple[int, int, int, int] = None) -> np.ndarray:
    """
    Extracts the Region of Interest (ROI) from the FPV frame focusing on the hand.
    
    Args:
        frame (VideoFrame): The input video frame.
        roi_box (Tuple[int, int, int, int], optional): Bounding box (x, y, w, h). 
                                                        If None, uses center crop.
        
    Returns:
        np.ndarray: The cropped image region.
    """
    if frame.frame_data is None:
        raise DataValidationError("Video frame data is None.")
        
    h, w = frame.resolution[1], frame.resolution[0]
    
    if roi_box:
        x, y, bw, bh = roi_box
        # Boundary checks for ROI
        if x < 0 or y < 0 or x + bw > w or y + bh > h:
            logger.warning("ROI box out of bounds, falling back to center crop.")
        else:
            return frame.frame_data[y:y+bh, x:x+bw]
    
    # Default: Center Crop (Simulating hand tracking focus)
    start_y = h // 4
    end_y = start_y + h // 2
    start_x = w // 4
    end_x = start_x + w // 2
    
    return frame.frame_data[start_y:end_y, start_x:end_x]

def synchronize_and_fuse(
    glove_stream: List[GloveData], 
    video_stream: List[VideoFrame], 
    config: SensorConfig
) -> List[FusedActionPrimitive]:
    """
    Aligns glove data (High Freq) and video data (Lower Freq) based on timestamps,
    extracts features, and creates action primitives.
    
    Args:
        glove_stream (List[GloveData]): Buffer of glove data.
        video_stream (List[VideoFrame]): Buffer of video frames.
        config (SensorConfig): System configuration.
        
    Returns:
        List[FusedActionPrimitive]: A list of digitized action primitives.
        
    Raises:
        SynchronizationError: If streams cannot be aligned.
    """
    if not glove_stream or not video_stream:
        logger.warning("Empty stream provided to fusion.")
        return []

    logger.info(f"Fusing {len(glove_stream)} glove samples and {len(video_stream)} video frames...")
    
    fused_primitives: List[FusedActionPrimitive] = []
    
    # Sort streams by timestamp just in case
    glove_stream.sort(key=lambda x: x.timestamp)
    video_stream.sort(key=lambda x: x.timestamp)
    
    # Time alignment strategy: Nearest Neighbor Interpolation
    # For every video frame timestamp, find the closest glove data point
    video_timestamps = np.array([f.timestamp for f in video_stream])
    
    for g_data in glove_stream:
        try:
            validate_glove_data(g_data, config)
        except DataValidationError as e:
            logger.error(f"Skipping corrupt data point at {g_data.timestamp}: {e}")
            continue
            
        # Find nearest video frame (simple implementation for logic demonstration)
        # In production, this would use interpolation between frames
        idx = np.searchsorted(video_timestamps, g_data.timestamp, side="left")
        
        # Handle edge cases for searchsorted
        if idx == len(video_timestamps):
            idx -= 1
        elif idx > 0:
            # Check if previous idx is closer
            if abs(video_timestamps[idx-1] - g_data.timestamp) < abs(video_timestamps[idx] - g_data.timestamp):
                idx -= 1
        
        # Simple logic: Only process if close enough (temporal threshold)
        time_diff = abs(video_timestamps[idx] - g_data.timestamp)
        if time_diff > (1.0 / config.video_fps):
            continue # Too desynchronized
            
        matched_frame = video_stream[idx]
        
        # Feature Extraction
        # 1. Force Magnitude
        total_force = sum(g_data.fingertip_forces.values())
        
        # 2. Visual Feature (Dummy logic: Average brightness of ROI as placeholder for CNN embedding)
        roi = extract_visual_roi(matched_frame)
        avg_brightness = np.mean(roi)
        
        # 3. Trajectory (Placeholder: using joint angles to simulate position)
        # In a real system, Forward Kinematics would be applied here.
        mock_trajectory = {
            "x": g_data.joint_angles.get("thumb_cmc", 0) / 180.0,
            "y": g_data.joint_angles.get("index_mcp", 0) / 180.0,
            "z": total_force
        }
        
        # Create Primitive
        primitive = FusedActionPrimitive(
            timestamp=g_data.timestamp,
            duration=0.0, # Instantaneous point
            trajectory_3d=[mock_trajectory],
            force_profile=[total_force],
            visual_embedding=[avg_brightness] # Simplified feature
        )
        fused_primitives.append(primitive)
        
    logger.info(f"Generated {len(fused_primitives)} fused action primitives.")
    return fused_primitives

# --- Helper Functions ---

def calculate_action_velocity(primitives: List[FusedActionPrimitive]) -> List[float]:
    """
    Calculates the velocity of the action based on trajectory changes.
    
    Args:
        primitives (List[FusedActionPrimitive]): The fused data list.
        
    Returns:
        List[float]: Velocities between consecutive primitives.
    """
    velocities = []
    for i in range(1, len(primitives)):
        p_prev = primitives[i-1]
        p_curr = primitives[i]
        
        dt = p_curr.timestamp - p_prev.timestamp
        if dt == 0:
            velocities.append(0.0)
            continue
            
        # Calculate Euclidean distance in mock 3D space
        pos_prev = p_prev.trajectory_3d[0]
        pos_curr = p_curr.trajectory_3d[0]
        
        dist = np.sqrt(
            (pos_curr['x'] - pos_prev['x'])**2 +
            (pos_curr['y'] - pos_prev['y'])**2 +
            (pos_curr['z'] - pos_prev['z'])**2
        )
        
        vel = dist / dt
        velocities.append(vel)
        
    return velocities

# --- Main Execution / Example ---

if __name__ == "__main__":
    # 1. Setup Configuration
    config = SensorConfig(glove_sample_rate=120, video_fps=60)
    
    # 2. Simulate Input Data
    # Generate 1 second of dummy data
    duration = 1.0
    t_glove = np.arange(0, duration, 1.0/config.glove_sample_rate)
    t_video = np.arange(0, duration, 1.0/config.video_fps)
    
    glove_data_list = []
    for t in t_glove:
        gd = GloveData(
            timestamp=t,
            joint_angles={
                "thumb_cmc": 20 + 10 * np.sin(t * 10),
                "index_mcp": 50 + 20 * np.cos(t * 5)
            },
            fingertip_forces={
                "thumb": 0.2 + 0.1 * np.sin(t * 20),
                "index": 0.1
            }
        )
        glove_data_list.append(gd)
        
    video_data_list = []
    for t in t_video:
        # Create a dummy black image (64x64)
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        # Simulate change in image
        frame[:,:,:] = int(255 * t) % 256 
        vf = VideoFrame(timestamp=t, frame_data=frame, resolution=(64, 64))
        video_data_list.append(vf)
        
    # 3. Run Fusion
    try:
        logger.info("Starting Multimodal Fusion Process...")
        fused_data = synchronize_and_fuse(glove_data_list, video_data_list, config)
        
        # 4. Post-Processing (Velocity)
        velocities = calculate_action_velocity(fused_data)
        
        # 5. Display Results
        if fused_data:
            print(f"\n--- Sample Fused Primitive (Index 5) ---")
            sample = fused_data[5]
            print(f"Timestamp: {sample.timestamp:.4f}s")
            print(f"Force Profile: {sample.force_profile}")
            print(f"Trajectory: {sample.trajectory_3d}")
            print(f"Visual Feature (Brightness): {sample.visual_embedding}")
            
            print(f"\nAverage Velocity: {np.mean(velocities):.4f} units/s")
            
    except SensorFusionError as e:
        logger.error(f"Failed to process action data: {e}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)