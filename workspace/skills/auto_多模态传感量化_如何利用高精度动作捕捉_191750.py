"""
Module: auto_多模态传感量化_如何利用高精度动作捕捉_191750
Description: Advanced AGI Skill for quantifying unstructured handicraft motions.
             Transforms high-frequency sensor data (motion capture, haptics) into
             low-dimensional manifold representations (skill primitives).
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from pydantic import BaseModel, Field, validator, ValidationError
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import KernelPCA
from scipy.signal import butter, lfilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SensorPacket(BaseModel):
    """Represents a single timestamp of multi-modal sensor data."""
    timestamp: float = Field(..., ge=0, description="Unix timestamp in seconds")
    # Motion Capture: Position (x,y,z) and Quaternion (w,x,y,z)
    hand_pose: List[float] = Field(..., min_items=7, max_items=7, description="Pose data: [tx, ty, tz, qw, qx, qy, qz]")
    # Haptic: Pressure sensors (e.g., 5 fingertips + palm)
    tactile_pressure: List[float] = Field(..., min_items=1, description="Array of pressure readings in Pascals")
    
    @validator('hand_pose', 'tactile_pressure')
    def check_finite(cls, v):
        if not all(np.isfinite(v)):
            raise ValueError("Sensor values must be finite numbers")
        return v

class ManifoldConfig(BaseModel):
    """Configuration for the dimensionality reduction."""
    sampling_rate: int = Field(120, description="Sensor sampling rate in Hz")
    lowcut: float = Field(0.5, description="High-pass filter frequency")
    highcut: float = Field(50.0, description="Low-pass filter frequency")
    manifold_dim: int = Field(8, description="Target dimension for latent representation")
    window_size: int = Field(60, description="Sliding window size in frames")

class LatentNode(BaseModel):
    """Represents a discrete 'Real Node' in the skill manifold."""
    node_id: int
    latent_vector: List[float]
    physical_metrics: Dict[str, float] # e.g., average_force, velocity


# --- Core Classes ---

class SignalPreprocessor:
    """
    Helper class for signal processing (filtering and alignment).
    """
    def __init__(self, config: ManifoldConfig):
        self.config = config
        self._build_filter()

    def _build_filter(self):
        """Constructs a Butterworth bandpass filter."""
        nyq = 0.5 * self.config.sampling_rate
        low = self.config.lowcut / nyq
        high = self.config.highcut / nyq
        self.b, self.a = butter(4, [low, high], btype='band')

    def filter_signal(self, data: np.ndarray) -> np.ndarray:
        """
        Applies bandpass filter to remove noise and drift.
        
        Args:
            data (np.ndarray): Raw signal array (samples x features).
            
        Returns:
            np.ndarray: Filtered signal.
        """
        try:
            # Apply filter along the time axis (axis 0)
            return lfilter(self.b, self.a, data, axis=0)
        except Exception as e:
            logger.error(f"Filtering failed: {e}")
            raise

class ManifoldEncoder:
    """
    Encodes high-dimensional sensor streams into a low-dimensional manifold.
    """
    def __init__(self, config: ManifoldConfig):
        self.config = config
        self.preprocessor = SignalPreprocessor(config)
        # Pipeline for non-linear dimensionality reduction
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('kpca', KernelPCA(n_components=config.manifold_dim, kernel='rbf', fit_inverse_transform=True))
        ])
        self.is_fitted = False
        logger.info("ManifoldEncoder initialized with RBF Kernel PCA.")

    def _stack_features(self, data_packets: List[SensorPacket]) -> np.ndarray:
        """
        Helper: Converts list of packets into a feature matrix.
        Extracts velocity (derivative of pos) and raw force.
        """
        poses = np.array([p.hand_pose for p in data_packets])
        forces = np.array([p.tactile_pressure for p in data_packets])
        
        # Calculate velocities (approximate derivative)
        velocities = np.gradient(poses[:, :3], axis=0)
        
        # Concatenate Pose + Velocity + Force
        features = np.hstack([poses, velocities, forces])
        return features

    def calibrate(self, calibration_data: List[SensorPacket]):
        """
        Trains the manifold encoder on calibration data to learn the skill topology.
        """
        if len(calibration_data) < self.config.window_size:
            raise ValueError("Insufficient data for calibration.")
            
        logger.info(f"Calibrating encoder with {len(calibration_data)} frames...")
        raw_features = self._stack_features(calibration_data)
        
        # Filter features
        clean_features = self.preprocessor.filter_signal(raw_features)
        
        # Fit the manifold
        self.pipeline.fit(clean_features)
        self.is_fitted = True
        logger.info("Manifold calibration complete.")

    def encode_stream(self, live_packets: List[SensorPacket]) -> LatentNode:
        """
        Core Function 1: Maps a window of physical signals to a discrete 'Real Node'.
        
        Args:
            live_packets (List[SensorPacket]): A sliding window of recent sensor data.
            
        Returns:
            LatentNode: The discrete representation of the current action state.
        """
        if not self.is_fitted:
            raise RuntimeError("Encoder must be calibrated before encoding streams.")
        
        if len(live_packets) != self.config.window_size:
            logger.warning(f"Input size {len(live_packets)} != config window {self.config.window_size}")

        # 1. Feature Engineering
        raw_features = self._stack_features(live_packets)
        clean_features = self.preprocessor.filter_signal(raw_features)
        
        # 2. Dimensionality Reduction (Map to Manifold)
        # We take the mean of the window in latent space to represent the "Current Node"
        latent_trajectory = self.pipeline.transform(clean_features)
        node_vector = np.mean(latent_trajectory, axis=0)
        
        # 3. Calculate Physical Metrics (for metadata)
        avg_force = np.mean([np.mean(p.tactile_pressure) for p in live_packets])
        avg_velocity = np.mean(np.linalg.norm(np.gradient(
            np.array([p.hand_pose[:3] for p in live_packets]), axis=0), axis=1))

        return LatentNode(
            node_id=hash(node_vector.tobytes()) % (10 ** 8), # Simple hash ID
            latent_vector=node_vector.tolist(),
            physical_metrics={
                "avg_force_pa": float(avg_force),
                "avg_velocity_ms": float(avg_velocity)
            }
        )

    def compute_manifold_distance(self, node_a: LatentNode, node_b: LatentNode) -> float:
        """
        Core Function 2: Calculates the geodesic-like distance between two nodes.
        """
        vec_a = np.array(node_a.latent_vector)
        vec_b = np.array(node_b.latent_vector)
        return float(np.linalg.norm(vec_a - vec_b))


# --- High-Level API ---

def process_craft_session(
    sensor_stream: List[Dict[str, Any]], 
    config: ManifoldConfig
) -> List[Dict[str, Any]]:
    """
    Main entry point to process a crafting session (e.g., pottery throwing).
    
    Args:
        sensor_stream: Raw list of sensor dictionaries.
        config: Configuration object for the encoder.
        
    Returns:
        List of discrete nodes representing the skill timeline.
    """
    logger.info("Starting multimodal processing session...")
    
    # 1. Validation
    try:
        validated_packets = [SensorPacket(**p) for p in sensor_stream]
    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
        return []

    encoder = ManifoldEncoder(config)
    
    # 2. Calibration (using first 20% of data as pseudo-calibration for this demo)
    split_idx = int(len(validated_packets) * 0.2)
    if split_idx < config.window_size:
        logger.error("Dataset too small for calibration split.")
        return []
        
    encoder.calibrate(validated_packets[:split_idx])
    
    # 3. Sliding Window Processing
    results = []
    window = config.window_size
    data_slice = validated_packets[split_idx:]
    
    for i in range(len(data_slice) - window):
        window_data = data_slice[i : i + window]
        
        try:
            node = encoder.encode_stream(window_data)
            results.append(node.dict())
        except Exception as e:
            logger.warning(f"Skipping window at index {i}: {e}")
            
    logger.info(f"Session processed. Generated {len(results)} latent nodes.")
    return results

# --- Usage Example ---
if __name__ == "__main__":
    # Generate Mock Data (Simulating Pottery Wheel Throwing)
    # 120Hz sampling, 5 seconds of data
    mock_data = []
    t = np.linspace(0, 5, 600)
    
    # Simulate hand moving in a circle while applying varying pressure
    for i, time in enumerate(t):
        # Pose: [tx, ty, tz, qw, qx, qy, qz]
        pose = [
            0.5 * np.sin(time * 2), 0.5 * np.cos(time * 2), 1.0, 
            1.0, 0.0, 0.0, 0.0
        ]
        # Force: Pressure varies with depth
        force = [50 + 20 * np.sin(time * 4)] * 6 
        
        mock_data.append({
            "timestamp": time,
            "hand_pose": pose,
            "tactile_pressure": force
        })

    # Configuration
    cfg = ManifoldConfig(
        sampling_rate=120,
        manifold_dim=4, # Reduce to 4 dimensions
        window_size=30  # 0.25 second windows
    )

    # Process
    skill_nodes = process_craft_session(mock_data, cfg)
    
    # Output inspection
    if skill_nodes:
        print(f"First Node: {skill_nodes[0]}")