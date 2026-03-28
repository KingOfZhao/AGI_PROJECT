"""
Module: auto_基于多模态传感器融合_触觉手套_视觉_肌_0d0513
Description: Pottery Wheel Throwing Action Segmentation via Multimodal Sensor Fusion.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum
from scipy.signal import find_peaks, butter, filtfilt
from sklearn.cluster import KMeans

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ActionPrimitive(Enum):
    """Enumeration of atomic pottery actions."""
    CENTERING = "centering"
    OPENING = "opening"
    PULLING = "pulling"
    SHAPING = "shaping"
    CUTTING = "cutting"
    IDLE = "idle"

@dataclass
class SensorConfig:
    """Configuration for sensor parameters."""
    fps: int = 30
    emg_sample_rate: int = 1000
    emg_channels: int = 8
    tactile_grid_size: Tuple[int, int] = (10, 10)
    pressure_threshold: float = 0.5
    emg_threshold: float = 0.7

@dataclass
class SensorFrame:
    """Single frame of multimodal sensor data."""
    timestamp: float
    tactile_data: np.ndarray  # Shape: (grid_size[0], grid_size[1])
    visual_feature: np.ndarray  # Shape: (feature_dim,) e.g., optical flow or pose embedding
    emg_signal: np.ndarray  # Shape: (emg_channels,)

@dataclass
class ActionSegment:
    """Represents a detected action segment."""
    start_time: float
    end_time: float
    primitive: ActionPrimitive
    confidence: float
    sensor_stats: Dict[str, float] = field(default_factory=dict)

class ButterworthFilter:
    """Helper class for signal filtering."""
    
    @staticmethod
    def low_pass(signal: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
        """
        Apply Butterworth low-pass filter.
        
        Args:
            signal: Input signal
            cutoff: Cutoff frequency in Hz
            fs: Sampling frequency in Hz
            order: Filter order
            
        Returns:
            Filtered signal
        """
        try:
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = butter(order, normal_cutoff, btype='low', analog=False)
            return filtfilt(b, a, signal)
        except Exception as e:
            logger.error(f"Filtering failed: {e}")
            return signal

def validate_sensor_data(frame: SensorFrame, config: SensorConfig) -> bool:
    """
    Validate input sensor data dimensions and values.
    
    Args:
        frame: SensorFrame to validate
        config: Sensor configuration
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if frame.tactile_data.shape != config.tactile_grid_size:
            logger.warning(f"Tactile shape mismatch: {frame.tactile_data.shape}")
            return False
            
        if len(frame.emg_signal) != config.emg_channels:
            logger.warning(f"EMG channel mismatch: {len(frame.emg_signal)}")
            return False
            
        if not (0 <= frame.tactile_data.min() <= frame.tactile_data.max() <= 1):
            logger.warning("Tactile data out of range [0, 1]")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False

def extract_features(frame: SensorFrame, config: SensorConfig) -> np.ndarray:
    """
    Extract normalized features from multimodal sensor frame.
    
    Args:
        frame: SensorFrame containing raw sensor data
        config: Sensor configuration
        
    Returns:
        Concatenated feature vector
    """
    # Tactile features: average pressure and pressure variance
    tactile_mean = np.mean(frame.tactile_data)
    tactile_var = np.var(frame.tactile_data)
    
    # EMG features: RMS and frequency domain features
    emg_rms = np.sqrt(np.mean(frame.emg_signal ** 2))
    emg_filtered = ButterworthFilter.low_pass(frame.emg_signal, 20.0, config.emg_sample_rate)
    emg_freq = np.fft.fft(emg_filtered)
    emg_power = np.abs(emg_freq[:len(emg_freq)//2])
    
    # Visual features: assume pre-computed optical flow magnitude
    visual_motion = np.linalg.norm(frame.visual_feature) if len(frame.visual_feature) > 0 else 0.0
    
    # Concatenate features
    feature_vector = np.array([
        tactile_mean,
        tactile_var,
        emg_rms,
        np.mean(emg_power),
        visual_motion
    ])
    
    return feature_vector

def detect_action_boundaries(
    frames: List[SensorFrame],
    config: SensorConfig
) -> List[Tuple[int, int, ActionPrimitive, float]]:
    """
    Core function to detect action boundaries from continuous sensor stream.
    
    Args:
        frames: List of synchronized multimodal sensor frames
        config: Sensor configuration
        
    Returns:
        List of (start_idx, end_idx, action_primitive, confidence) tuples
    """
    if not frames:
        logger.error("Empty frame list provided")
        return []
    
    logger.info(f"Processing {len(frames)} frames for action segmentation")
    
    # Feature extraction
    features = []
    valid_indices = []
    
    for idx, frame in enumerate(frames):
        if validate_sensor_data(frame, config):
            feat = extract_features(frame, config)
            features.append(feat)
            valid_indices.append(idx)
    
    if not features:
        logger.error("No valid frames found")
        return []
    
    features = np.array(features)
    
    # Normalize features
    features = (features - np.mean(features, axis=0)) / (np.std(features, axis=0) + 1e-8)
    
    # Change point detection using sliding window
    window_size = int(config.fps * 0.5)  # 0.5 second window
    change_scores = []
    
    for i in range(len(features) - window_size):
        window1 = features[i:i+window_size//2]
        window2 = features[i+window_size//2:i+window_size]
        score = np.linalg.norm(np.mean(window1, axis=0) - np.mean(window2, axis=0))
        change_scores.append(score)
    
    change_scores = np.array(change_scores)
    
    # Find peaks in change scores
    peaks, properties = find_peaks(change_scores, height=np.percentile(change_scores, 75), distance=config.fps//2)
    
    # Cluster features to assign action labels
    n_clusters = min(len(ActionPrimitive) - 1, len(features) // (config.fps * 2) + 1)
    if n_clusters < 2:
        n_clusters = 2
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(features)
    
    # Map clusters to action primitives
    cluster_to_action = {}
    for cluster_id in range(n_clusters):
        cluster_features = features[cluster_labels == cluster_id]
        avg_tactile = np.mean(cluster_features[:, 0])
        avg_emg = np.mean(cluster_features[:, 2])
        
        if avg_tactile > 0.7 and avg_emg > 0.6:
            cluster_to_action[cluster_id] = ActionPrimitive.PULLING
        elif avg_tactile > 0.5 and avg_emg > 0.4:
            cluster_to_action[cluster_id] = ActionPrimitive.SHAPING
        elif avg_tactile > 0.3:
            cluster_to_action[cluster_id] = ActionPrimitive.OPENING
        else:
            cluster_to_action[cluster_id] = ActionPrimitive.CENTERING
    
    # Build segments
    segments = []
    boundaries = [0] + list(peaks) + [len(features)-1]
    
    for i in range(len(boundaries)-1):
        start_idx = boundaries[i]
        end_idx = boundaries[i+1]
        
        segment_labels = cluster_labels[start_idx:end_idx]
        dominant_cluster = np.bincount(segment_labels).argmax()
        action = cluster_to_action.get(dominant_cluster, ActionPrimitive.IDLE)
        
        confidence = np.max(np.bincount(segment_labels)) / len(segment_labels)
        
        segments.append((
            valid_indices[start_idx],
            valid_indices[end_idx],
            action,
            confidence
        ))
    
    logger.info(f"Detected {len(segments)} action segments")
    return segments

def generate_skill_sequence(
    frames: List[SensorFrame],
    config: SensorConfig
) -> List[ActionSegment]:
    """
    Main function to generate skill sequence from sensor data.
    
    Args:
        frames: List of synchronized multimodal sensor frames
        config: Sensor configuration
        
    Returns:
        List of ActionSegment objects with semantic annotations
    """
    try:
        # Detect raw boundaries
        boundaries = detect_action_boundaries(frames, config)
        
        # Convert to ActionSegment objects
        skill_sequence = []
        
        for start_idx, end_idx, action, confidence in boundaries:
            start_time = frames[start_idx].timestamp
            end_time = frames[end_idx].timestamp
            
            # Calculate segment statistics
            segment_frames = frames[start_idx:end_idx+1]
            avg_tactile = np.mean([np.mean(f.tactile_data) for f in segment_frames])
            avg_emg = np.mean([np.sqrt(np.mean(f.emg_signal**2)) for f in segment_frames])
            
            segment = ActionSegment(
                start_time=start_time,
                end_time=end_time,
                primitive=action,
                confidence=confidence,
                sensor_stats={
                    'avg_tactile_pressure': float(avg_tactile),
                    'avg_emg_activation': float(avg_emg),
                    'duration_sec': end_time - start_time
                }
            )
            skill_sequence.append(segment)
        
        logger.info(f"Generated skill sequence with {len(skill_sequence)} primitives")
        return skill_sequence
        
    except Exception as e:
        logger.error(f"Skill sequence generation failed: {e}")
        return []

# Example usage and testing
if __name__ == "__main__":
    # Initialize configuration
    config = SensorConfig()
    
    # Generate synthetic test data
    test_frames = []
    duration_sec = 10
    n_frames = config.fps * duration_sec
    
    for i in range(n_frames):
        timestamp = i / config.fps
        
        # Simulate different phases
        phase = i // (n_frames // 4)
        
        if phase == 0:  # Centering
            tactile = np.random.rand(*config.tactile_grid_size) * 0.3
            emg = np.random.randn(config.emg_channels) * 0.2
        elif phase == 1:  # Opening
            tactile = np.random.rand(*config.tactile_grid_size) * 0.6 + 0.2
            emg = np.random.randn(config.emg_channels) * 0.5 + 0.3
        elif phase == 2:  # Pulling
            tactile = np.random.rand(*config.tactile_grid_size) * 0.4 + 0.5
            emg = np.random.randn(config.emg_channels) * 0.8 + 0.6
        else:  # Shaping
            tactile = np.random.rand(*config.tactile_grid_size) * 0.5 + 0.3
            emg = np.random.randn(config.emg_channels) * 0.4 + 0.4
        
        visual = np.random.randn(128) * (0.5 + phase * 0.2)
        
        frame = SensorFrame(
            timestamp=timestamp,
            tactile_data=tactile,
            visual_feature=visual,
            emg_signal=emg
        )
        test_frames.append(frame)
    
    # Process data
    skill_seq = generate_skill_sequence(test_frames, config)
    
    # Print results
    print("\nDetected Skill Sequence:")
    for seg in skill_seq:
        print(f"{seg.primitive.value:10} [{seg.start_time:5.2f}s - {seg.end_time:5.2f}s] "
              f"Conf: {seg.confidence:.2f} "
              f"Tactile: {seg.sensor_stats['avg_tactile_pressure']:.2f} "
              f"EMG: {seg.sensor_stats['avg_emg_activation']:.2f}")