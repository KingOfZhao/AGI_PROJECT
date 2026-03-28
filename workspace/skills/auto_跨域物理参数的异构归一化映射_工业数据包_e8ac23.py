"""
Module: auto_跨域物理参数的异构归一化映射_工业数据包_e8ac23
Description: Advanced Heterogeneous Normalization Mapping for Cross-Domain Industrial Data.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, Union, List
from pydantic import BaseModel, Field, ValidationError, confloat

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SensorInput(BaseModel):
    """Base model for sensor data validation."""
    timestamp: float = Field(..., description="Unix timestamp of the data point")
    quality_score: confloat(ge=0, le=1) = 1.0

class VibrationSpectrum(SensorInput):
    """Represents frequency domain vibration data."""
    fft_amplitudes: List[float] = Field(..., description="Amplitude spectrum from FFT")
    sampling_rate: int = Field(1024, description="Sampling rate in Hz")

class ThermalImage(SensorInput):
    """Represents 2D thermal imaging data."""
    grid_data: List[List[float]] = Field(..., description="2D temperature matrix")
    emissivity: float = Field(0.95, description="Emissivity setting of the camera")

class PLCTimeSeries(SensorInput):
    """Represents time-series PLC log data."""
    values: List[float] = Field(..., description="Scalar values over time window")
    tag_name: str

class PhysicalStateVector(BaseModel):
    """The unified output vector for the cognitive node."""
    unified_vector: np.ndarray
    source_weights: Dict[str, float]
    anomaly_scores: Dict[str, float]
    
    class Config:
        arbitrary_types_allowed = True

# --- Helper Functions ---

def _validate_physical_bounds(data: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """
    Clamps data to physical limits and handles NaN/Inf values.
    
    Args:
        data: Input numpy array
        min_val: Physical minimum bound
        max_val: Physical maximum bound
        
    Returns:
        Cleaned numpy array
        
    Raises:
        ValueError: If data contains no valid finite values
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)
        
    # Handle non-finite values by replacing with mean or 0
    if not np.all(np.isfinite(data)):
        logger.warning("Data contains NaN or Inf values. Applying interpolation.")
        finite_mask = np.isfinite(data)
        if not np.any(finite_mask):
            raise ValueError("Input data contains no finite values.")
        mean_val = np.mean(data[finite_mask])
        data = np.where(np.isfinite(data), data, mean_val)
        
    # Clip to physical bounds
    return np.clip(data, min_val, max_val)

def _resample_to_cognitive_window(data: np.ndarray, target_length: int = 64) -> np.ndarray:
    """
    Resamples or pads input data to a fixed cognitive window size using FFT.
    
    Args:
        data: 1D Input array
        target_length: Required dimension for the cognitive node
        
    Returns:
        Resampled array of shape (target_length,)
    """
    if len(data) == 0:
        return np.zeros(target_length)
    
    # Simple linear interpolation resampling
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, target_length)
    resampled = np.interp(x_new, x_old, data)
    return resampled

# --- Core Functions ---

def map_vibration_to_vector(spectrum: VibrationSpectrum, 
                            history_stats: Dict[str, float]) -> Tuple[np.ndarray, float]:
    """
    Maps vibration spectrum to a normalized feature vector.
    
    Extracts statistical features and normalizes them based on historical baselines.
    
    Args:
        spectrum: Validated vibration data object
        history_stats: Dictionary containing 'mean' and 'std' for baseline
        
    Returns:
        Tuple of (feature_vector, anomaly_weight)
    """
    logger.debug(f"Processing vibration data at {spectrum.timestamp}")
    raw_data = np.array(spectrum.fft_amplitudes)
    
    # 1. Validate bounds (0 to 50g typical for industrial accelerometers)
    clean_data = _validate_physical_bounds(raw_data, 0.0, 50.0)
    
    # 2. Feature Extraction (Simplified for demo: RMS, Peak, Crest Factor)
    rms = np.sqrt(np.mean(clean_data**2))
    peak = np.max(clean_data)
    crest_factor = peak / (rms + 1e-9)
    
    # Create a small feature vector from the spectrum shape (e.g., band energies)
    # Split into 8 frequency bands
    bands = np.array_split(clean_data, 8)
    band_energies = np.array([np.mean(b) for b in bands])
    
    # 3. Normalization (Z-score based on history)
    mean_val = history_stats.get('mean', 0.1)
    std_val = history_stats.get('std', 0.05)
    normalized_bands = (band_energies - mean_val) / (std_val + 1e-6)
    
    # 4. Anomaly Weight Calculation
    anomaly_score = np.linalg.norm(normalized_bands) / (len(normalized_bands) ** 0.5)
    anomaly_score = min(max(anomaly_score, 0.0), 1.0) # Clipping score
    
    # 5. Project to fixed dimension (16 dims)
    feature_vector = _resample_to_cognitive_window(normalized_bands, 16)
    
    return feature_vector, anomaly_score

def map_thermal_to_vector(thermal_data: ThermalImage,
                          baseline_temp: float) -> Tuple[np.ndarray, float]:
    """
    Maps 2D thermal grid to a normalized feature vector.
    
    Focuses on temperature gradients and hotspots relative to baseline.
    
    Args:
        thermal_data: Validated thermal image object
        baseline_temp: Expected operational temperature
        
    Returns:
        Tuple of (feature_vector, anomaly_weight)
    """
    logger.debug(f"Processing thermal data at {thermal_data.timestamp}")
    raw_grid = np.array(thermal_data.grid_data)
    
    # 1. Validate bounds (0C to 500C for industrial machinery)
    clean_grid = _validate_physical_bounds(raw_grid, 0.0, 500.0)
    
    # 2. Feature Extraction
    # Relative temperature difference
    delta_grid = clean_grid - baseline_temp
    
    # Spatial gradients (approximated)
    if clean_grid.shape[0] > 1 and clean_grid.shape[1] > 1:
        grad_x = np.mean(np.abs(np.diff(clean_grid, axis=1)))
        grad_y = np.mean(np.abs(np.diff(clean_grid, axis=0)))
    else:
        grad_x, grad_y = 0.0, 0.0
        
    max_hotspot = np.max(clean_grid)
    mean_temp = np.mean(clean_grid)
    
    # 3. Construct vector components
    # We create a vector representing the distribution characteristics
    # Flattening the center region (ROI) to capture spatial patterns
    center_roi = clean_grid[
        clean_grid.shape[0]//4:clean_grid.shape[0]//4*3,
        clean_grid.shape[1]//4:clean_grid.shape[1]//4*3
    ]
    roi_flat = center_roi.flatten()
    
    # 4. Normalization (Sigmoid-like activation for temperature)
    # Normalize relative to baseline
    normalized_roi = np.tanh((roi_flat - baseline_temp) / 20.0) # 20C scaling factor
    normalized_stats = np.tanh(np.array([grad_x/5.0, grad_y/5.0, (max_hotspot - baseline_temp)/50.0]))
    
    combined_features = np.concatenate([
        _resample_to_cognitive_window(normalized_roi, 8),
        normalized_stats
    ])
    
    # 5. Anomaly Calculation
    anomaly_score = np.tanh((max_hotspot - baseline_temp - 20.0) / 10.0) # Trigger if 20C over baseline
    anomaly_score = (anomaly_score + 1) / 2 # Scale to 0-1
    
    return combined_features, anomaly_score

# --- Main Aggregator Class ---

class HeterogeneousStateMapper:
    """
    Main class for constructing the unified Physical Entity State Vector.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.history = {} # Simplified history storage
        
    def construct_state_vector(self, 
                               vib_data: Optional[VibrationSpectrum],
                               therm_data: Optional[ThermalImage]) -> PhysicalStateVector:
        """
        Integrates heterogeneous data into a single PhysicalStateVector.
        
        Args:
            vib_data: Vibration sensor input (or None)
            therm_data: Thermal sensor input (or None)
            
        Returns:
            PhysicalStateVector object ready for the AGI node.
            
        Example:
            >>> mapper = HeterogeneousStateMapper({})
            >>> vib = VibrationSpectrum(timestamp=1.0, fft_amplitudes=[0.1]*100)
            >>> therm = ThermalImage(timestamp=1.0, grid_data=[[30]*10]*10)
            >>> state = mapper.construct_state_vector(vib, therm)
            >>> print(state.unified_vector.shape)
        """
        vectors = []
        weights = {}
        anomalies = {}
        
        # Process Vibration
        if vib_data:
            try:
                # Using dummy history stats for demonstration
                hist_stats = {'mean': 0.2, 'std': 0.1}
                vec, anom = map_vibration_to_vector(vib_data, hist_stats)
                vectors.append(vec)
                weights['vibration'] = 1.0
                anomalies['vibration'] = anom
            except Exception as e:
                logger.error(f"Failed to process vibration data: {e}")
                weights['vibration'] = 0.0
        else:
            logger.info("No vibration data provided for this cycle.")
            
        # Process Thermal
        if therm_data:
            try:
                baseline = 25.0 # Ambient/Operating baseline
                vec, anom = map_thermal_to_vector(therm_data, baseline)
                vectors.append(vec)
                weights['thermal'] = 1.0
                anomalies['thermal'] = anom
            except Exception as e:
                logger.error(f"Failed to process thermal data: {e}")
                weights['thermal'] = 0.0
        else:
            logger.info("No thermal data provided for this cycle.")
            
        # Concatenation and Final Projection
        if not vectors:
            # Return zero vector if no inputs
            final_vector = np.zeros(32) 
        else:
            # Concatenate all feature vectors
            concat_vector = np.concatenate(vectors)
            # Project to fixed cognitive node dimension (e.g., 32)
            final_vector = _resample_to_cognitive_window(concat_vector, 32)
            
        # Normalize final vector for neural network input
        norm = np.linalg.norm(final_vector)
        if norm > 0:
            final_vector = final_vector / norm
            
        return PhysicalStateVector(
            unified_vector=final_vector,
            source_weights=weights,
            anomaly_scores=anomalies
        )

# --- Execution / Usage Example ---
if __name__ == "__main__":
    # Generate synthetic data
    vib_input = VibrationSpectrum(
        timestamp=1672531200.0,
        fft_amplitudes=list(np.random.normal(0.5, 0.1, 128)),
        quality_score=0.99
    )
    
    thermal_input = ThermalImage(
        timestamp=1672531200.1,
        grid_data=[[45.0 + np.random.randn() for _ in range(10)] for _ in range(10)],
        emissivity=0.95
    )
    
    # Initialize Mapper
    mapper = HeterogeneousStateMapper(config={})
    
    # Construct State Vector
    state_vector = mapper.construct_state_vector(vib_input, thermal_input)
    
    logger.info(f"Generated State Vector Shape: {state_vector.unified_vector.shape}")
    logger.info(f"Anomaly Scores: {state_vector.anomaly_scores}")
    logger.info(f"Active Weights: {state_vector.source_weights}")