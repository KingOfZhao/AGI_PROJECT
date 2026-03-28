"""
Module: multimodal_tactile_skill_encoder
Description: Captures non-structured physical actions (e.g., pottery throwing) via multimodal sensors
             and maps them to a 'Physical Operation' vector space within an AGI Skill System.
Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configurations ---
class SensorType(str, Enum):
    MOTION_CAPTURE = "mocap"
    EMG = "emg"
    TACTILE_GLOVE = "tactile"

EMG_SAMPLE_RATE = 1000  # Hz
MOCAP_SAMPLE_RATE = 120 # Hz
TACTILE_SAMPLE_RATE = 100 # Hz
TARGET_EMBEDDING_DIM = 128  # Dimension of the Skill Node Vector Space
SKILL_NODE_COUNT = 983      # Total number of existing skill nodes

# --- Data Models ---

class SensorReading(BaseModel):
    """Validates the structure of incoming sensor data."""
    timestamp: float = Field(..., ge=0)
    sensor_type: SensorType
    data: List[float]  # Flattened array of sensor values

    class Config:
        use_enum_values = True

class TimeSeriesTensor(BaseModel):
    """Container for processed time-series data."""
    features: np.ndarray
    original_dim: int
    sequence_len: int

    class Config:
        arbitrary_types_allowed = True

class SkillMappingResult(BaseModel):
    """Result of the mapping to the Skill Node space."""
    skill_vector: np.ndarray
    closest_node_id: int
    similarity_score: float

# --- Helper Functions ---

def _resample_signal(data: List[List[float]], original_rate: float, target_rate: float) -> np.ndarray:
    """
    Resamples a 2D time-series data array (timesteps x features) to a target rate.
    
    Args:
        data: List of lists containing sensor readings.
        original_rate: The sampling rate of the input data in Hz.
        target_rate: The desired sampling rate in Hz.
        
    Returns:
        np.ndarray: Resampled data array.
        
    Raises:
        ValueError: If data is empty or rates are invalid.
    """
    if not data:
        raise ValueError("Input data cannot be empty for resampling.")
    if original_rate <= 0 or target_rate <= 0:
        raise ValueError("Sampling rates must be positive values.")

    arr = np.array(data)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array for resampling, got {arr.ndim} dimensions.")

    num_samples = arr.shape[0]
    duration = num_samples / original_rate
    target_samples = int(duration * target_rate)
    
    # Simple linear interpolation (for production, consider scipy.signal.resample)
    indices = np.linspace(0, num_samples - 1, target_samples)
    resampled = np.array([np.interp(indices, np.arange(num_samples), arr[:, i]) 
                          for i in range(arr.shape[1])]).T
    
    logger.debug(f"Resampled signal from {num_samples} to {target_samples} points.")
    return resampled

# --- Core Functions ---

def ingest_and_fuse_sensors(
    raw_data_stream: Dict[str, List[List[float]]],
    target_fps: int = 60
) -> TimeSeriesTensor:
    """
    Fuses multi-modal sensor data (MoCap, EMG, Tactile) into a unified time-series tensor.
    
    Process:
    1. Validate incoming data structure.
    2. Synchronize timestamps (Temporal Alignment).
    3. Resample all modalities to a common target FPS.
    4. Concatenate feature vectors.
    
    Args:
        raw_data_stream: Dictionary where keys are sensor names and values are 
                         lists of frames (list of floats).
        target_fps: The unified frame rate for the output tensor.
        
    Returns:
        TimeSeriesTensor: Validated and fused tensor data.
        
    Example:
        >>> data = {
        ...     "mocap": [[0.0, 0.1, 0.2]], # Mock data
        ...     "emg": [[0.5, 0.6]]
        ... }
        >>> tensor = ingest_and_fuse_sensors(data, target_fps=60)
    """
    logger.info(f"Starting ingestion of {len(raw_data_stream)} sensor streams.")
    
    fused_features = []
    expected_length = None
    
    # Define sensor specific configurations (could be moved to config file)
    sensor_rates = {
        SensorType.MOTION_CAPTURE: MOCAP_SAMPLE_RATE,
        SensorType.EMG: EMG_SAMPLE_RATE,
        SensorType.TACTILE_GLOVE: TACTILE_SAMPLE_RATE
    }

    for sensor_key, frames in raw_data_stream.items():
        try:
            # Validate sensor type
            s_type = SensorType(sensor_key)
            
            if not frames:
                logger.warning(f"Sensor {sensor_key} has no data. Skipping.")
                continue
                
            # Resample to target FPS
            original_rate = sensor_rates.get(s_type, 100)
            resampled = _resample_signal(frames, original_rate, target_fps)
            
            # Ensure all modalities have same sequence length after resampling
            if expected_length is None:
                expected_length = resampled.shape[0]
            elif resampled.shape[0] != expected_length:
                # In a real system, we would pad or truncate strictly here
                logger.warning(f"Resampled length mismatch for {sensor_key}. Adjusting...")
                min_len = min(expected_length, resampled.shape[0])
                resampled = resampled[:min_len, :]
                # Update expected_length if this is the shorter sequence?
                # For now, we assume the first valid stream dictates length or error.
                # Let's proceed with truncation for robustness.
            
            fused_features.append(resampled)
            logger.info(f"Processed {sensor_key}: shape {resampled.shape}")
            
        except ValueError as e:
            logger.error(f"Data validation error for {sensor_key}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing {sensor_key}: {e}")
            continue

    if not fused_features:
        raise ValueError("No valid sensor data available for fusion.")

    # Concatenate along feature dimension (axis=1)
    try:
        final_tensor = np.concatenate(fused_features, axis=1)
        logger.info(f"Fusion complete. Final Tensor Shape: {final_tensor.shape}")
        
        return TimeSeriesTensor(
            features=final_tensor,
            original_dim=final_tensor.shape[1],
            sequence_len=final_tensor.shape[0]
        )
    except Exception as e:
        logger.critical(f"Failed to concatenate features: {e}")
        raise

def map_to_skill_space(
    fused_tensor: TimeSeriesTensor,
    skill_node_space: np.ndarray,
    encoder_weights: Optional[np.ndarray] = None
) -> SkillMappingResult:
    """
    Maps the raw fused tensor to the 'Physical Operation' skill vector space.
    
    This function simulates an encoding process (e.g., a learned neural projection)
    that projects high-dimensional sensor data into the skill embedding space,
    then finds the nearest existing skill node.
    
    Args:
        fused_tensor: The output from ingest_and_fuse_sensors.
        skill_node_space: Matrix (N, D) representing the 983 existing skill nodes.
        encoder_weights: Optional projection matrix. If None, PCA-like projection is simulated.
        
    Returns:
        SkillMappingResult: Contains the vector and the closest matching node ID.
        
    Raises:
        ValueError: If dimensions mismatch.
    """
    logger.info("Mapping sensor tensor to skill vector space...")
    
    # Input validation
    if fused_tensor.features.size == 0:
        raise ValueError("Fused tensor is empty.")
    if skill_node_space.shape[0] != SKILL_NODE_COUNT:
        logger.warning(f"Skill node space size {skill_node_space.shape[0]} != expected {SKILL_NODE_COUNT}")
    
    # 1. Flatten temporal dimension (Simple Global Average Pooling for this example)
    # In production, this would be an RNN or Transformer encoder.
    feature_vector = np.mean(fused_tensor.features, axis=0)
    
    # 2. Project to Skill Dimension (Simulation)
    input_dim = feature_vector.shape[0]
    target_dim = skill_node_space.shape[1] # D dimension
    
    if encoder_weights is None:
        # Generate a deterministic random projection for reproducibility in this example
        np.random.seed(42)
        encoder_weights = np.random.randn(input_dim, target_dim) * 0.01
        
    # Projection
    skill_vector = np.dot(feature_vector, encoder_weights)
    
    # Normalize vector for cosine similarity
    skill_vector_norm = skill_vector / (np.linalg.norm(skill_vector) + 1e-8)
    skill_node_norms = skill_node_space / (np.linalg.norm(skill_node_space, axis=1, keepdims=True) + 1e-8)
    
    # 3. Find Nearest Neighbor in Skill Space
    similarities = np.dot(skill_node_norms, skill_vector_norm)
    closest_idx = np.argmax(similarities)
    max_similarity = similarities[closest_idx]
    
    logger.info(f"Matched Skill Node ID: {closest_idx} with similarity: {max_similarity:.4f}")
    
    return SkillMappingResult(
        skill_vector=skill_vector,
        closest_node_id=int(closest_idx),
        similarity_score=float(max_similarity)
    )

# --- Main Execution Guard ---

if __name__ == "__main__":
    # Mock Data Generation
    logger.info("Generating mock sensor data for demonstration...")
    
    duration_sec = 2.0
    
    # Mock MoCap (22 joints * 3 coords = 66 dims)
    mock_mocap = np.random.rand(int(MOCAP_SAMPLE_RATE * duration_sec), 66).tolist()
    
    # Mock EMG (8 channels)
    # EMG usually has higher sample rate
    mock_emg = np.random.rand(int(EMG_SAMPLE_RATE * duration_sec), 8).tolist()
    
    # Mock Tactile (10 pressure sensors)
    mock_tactile = np.random.rand(int(TACTILE_SAMPLE_RATE * duration_sec), 10).tolist()
    
    raw_stream = {
        "mocap": mock_mocap,
        "emg": mock_emg,
        "tactile": mock_tactile
    }
    
    # Mock Skill Node Space (983 nodes, 128 dims)
    mock_skill_nodes = np.random.rand(SKILL_NODE_COUNT, TARGET_EMBEDDING_DIM)
    
    try:
        # Step 1: Fuse Sensors
        ts_tensor = ingest_and_fuse_sensors(raw_stream, target_fps=60)
        
        # Step 2: Map to Skill Space
        result = map_to_skill_space(ts_tensor, mock_skill_nodes)
        
        print("\n=== Processing Result ===")
        print(f"Closest Skill Node: {result.closest_node_id}")
        print(f"Similarity Score: {result.similarity_score:.4f}")
        print(f"Vector Dimension: {result.skill_vector.shape}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")