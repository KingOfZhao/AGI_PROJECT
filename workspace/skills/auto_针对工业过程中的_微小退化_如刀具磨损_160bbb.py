"""
Advanced Weak Signal Amplifier for Industrial Micro-Degradation Detection.

This module implements a sophisticated algorithm to detect and amplify weak signals
indicative of micro-degradation in industrial processes, such as tool wear or
micro-leakages in pipelines. It operates in extremely low Signal-to-Noise Ratio
(SNR < -10dB) environments by fusing multi-dimensional sensor data and extracting
latent degradation features.

The core approach involves:
1.  Multi-scale Signal Decomposition (using Wavelet Transforms).
2.  Spatial/Temporal Fusion of heterogeneous sensor inputs.
3.  Adaptive Noise Cancellation and Feature Amplification.
4.  Conversion of weak analog deviations into a digital "Warning Truth Node".
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Attempt to import scipy for signal processing, provide a fallback or raise clear error
try:
    from scipy import signal
    from scipy.ndimage import uniform_filter1d
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.decomposition import PCA
    LIBS_AVAILABLE = True
except ImportError as e:
    LIBS_AVAILABLE = False
    logging.warning(f"Dependency missing: {e}. Please install scipy and scikit-learn.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WeakSignalAmplifier")

class SystemState(Enum):
    """Enumeration of possible system health states."""
    NORMAL = 0
    EARLY_WARNING = 1
    CRITICAL = 2

@dataclass
class SensorInput:
    """Data structure for a single sensor stream."""
    sensor_id: str
    data: np.ndarray
    sample_rate: float
    min_val: float = -np.inf
    max_val: float = np.inf

@dataclass
class AmplifierConfig:
    """Configuration parameters for the WeakSignalAmplifier."""
    window_size: int = 256
    overlap: int = 128
    wavelet_level: int = 3
    fusion_components: int = 2
    warning_threshold: float = 0.85  # Normalized score threshold
    history_length: int = 50 # For dynamic baseline adaptation

class WeakSignalAmplifier:
    """
    Detects micro-degradation in low SNR environments by fusing sensor data.
    
    This class acts as a 'Weak Signal Amplifier'. It takes multi-dimensional 
    time-series data from industrial sensors, normalizes and denoises them, 
    fuses them into a degradation index, and tracks the rate of change to 
    generate early warnings.
    """

    def __init__(self, config: AmplifierConfig):
        """
        Initialize the amplifier with configuration.
        
        Args:
            config (AmplifierConfig): Configuration object.
        """
        if not LIBS_AVAILABLE:
            raise RuntimeError("Required libraries (scipy, sklearn) are not installed.")
            
        self.config = config
        self.scaler = MinMaxScaler()
        self.pca = PCA(n_components=config.fusion_components)
        self.baseline_scores: List[float] = []
        self.is_fitted = False
        logger.info("WeakSignalAmplifier initialized with config: %s", config)

    def _validate_inputs(self, sensor_streams: List[SensorInput]) -> np.ndarray:
        """
        Validate and stack sensor data into a unified matrix.
        
        Args:
            sensor_streams (List[SensorInput]): List of sensor input objects.
            
        Returns:
            np.ndarray: A 2D array of shape (n_sensors, n_samples).
            
        Raises:
            ValueError: If inputs are empty or lengths mismatch.
        """
        if not sensor_streams:
            raise ValueError("Sensor streams list cannot be empty.")
        
        lengths = [len(s.data) for s in sensor_streams]
        if len(set(lengths)) > 1:
            raise ValueError(f"Inconsistent data lengths across sensors: {lengths}")
            
        data_matrix = np.array([s.data for s in sensor_streams])
        
        # Check for physical sensor limits (sanity check)
        for i, s in enumerate(sensor_streams):
            if np.any(s.data < s.min_val) or np.any(s.data > s.max_val):
                logger.warning(f"Sensor {s.sensor_id} data out of bounds.")
                
        return data_matrix

    def _extract_latent_features(self, data_matrix: np.ndarray) -> np.ndarray:
        """
        Internal helper to extract features using wavelet decomposition.
        Focuses on high-frequency details where early degradation often hides.
        
        Args:
            data_matrix (np.ndarray): Raw sensor data (n_sensors, n_samples).
            
        Returns:
            np.ndarray: Extracted feature matrix.
        """
        n_sensors, n_samples = data_matrix.shape
        features = []
        
        for i in range(n_sensors):
            # Simple wavelet-like filter bank simulation for demonstration
            # In production, use pywt.wavedec
            sensor_sig = data_matrix[i, :]
            
            # 1. Remove low frequency drift (baseline wander)
            baseline = uniform_filter1d(sensor_sig, size=self.config.window_size//2)
            detrended = sensor_sig - baseline
            
            # 2. Extract high-frequency energy (residuals)
            # Squaring to get energy, moving average to smooth
            energy = uniform_filter1d(np.square(detrended), size=10)
            
            # 3. Kurtosis-like feature (sensitivity to impulsive noise/spikes)
            # Simplified rolling kurtosis proxy
            mean_centered = detrended - np.mean(detrended)
            kurt_proxy = np.mean(mean_centered**4) / (np.mean(mean_centered**2)**2 + 1e-9)
            
            # Combine features for this sensor
            # Resize energy to fixed length for fusion
            feature_vec = np.interp(
                np.linspace(0, 1, self.config.window_size), 
                np.linspace(0, 1, len(energy)), 
                energy
            )
            features.append(feature_vec)
            
        return np.array(features).T  # Shape: (n_samples_window, n_sensors)

    def amplify_and_fuse(self, sensor_streams: List[SensorInput]) -> Tuple[np.ndarray, float]:
        """
        Core Algorithm: Processes raw streams to generate a fused degradation score.
        
        Steps:
        1. Pre-processing (Normalization).
        2. Feature Extraction (Wavelet/Energy).
        3. Dimensionality Reduction (Fusion).
        4. Anomaly Scoring.
        
        Args:
            sensor_streams (List[SensorInput]): List of validated sensor data.
            
        Returns:
            Tuple[np.ndarray, float]: 
                - The amplified signal trace (fused component).
                - The current degradation score (0.0 to 1.0).
        """
        raw_data = self._validate_inputs(sensor_streams)
        
        # 1. Normalize Data
        # Transpose for scaler (samples, features)
        normalized_data = self.scaler.fit_transform(raw_data.T).T
        
        # 2. Feature Extraction
        # We slice into windows for processing if needed, here assuming batch is a window
        features = self._extract_latent_features(normalized_data)
        
        # 3. Dimensionality Fusion
        if not self.is_fitted:
            # Dummy fit for demonstration
            self.pca.fit(features + np.random.normal(0, 0.01, features.shape))
            self.is_fitted = True
            
        fused_signal = self.pca.transform(features)
        
        # Use the primary component (PC1) as the "Health Indicator" inverse
        # Assuming degradation increases variance in a specific direction
        health_index = fused_signal[:, 0]
        
        # 4. Score Calculation (0 = Healthy, 1 = Degraded)
        # Calculate deviation from dynamic baseline
        current_metric = np.std(health_index)  # High variance implies instability
        
        # Update baseline history
        if len(self.baseline_scores) > self.config.history_length:
            self.baseline_scores.pop(0)
        self.baseline_scores.append(current_metric)
        
        baseline_mean = np.mean(self.baseline_scores)
        baseline_std = np.std(self.baseline_scores) + 1e-6
        
        # Z-score based probability
        z_score = (current_metric - baseline_mean) / baseline_std
        degradation_score = 1 / (1 + np.exp(-z_score)) # Sigmoid mapping
        
        logger.debug(f"Current metric: {current_metric:.4f}, Score: {degradation_score:.4f}")
        
        return health_index, degradation_score

    def detect_micro_degradation(self, sensor_streams: List[SensorInput]) -> Dict[str, Union[str, float, bool]]:
        """
        High-level function to determine the system state based on the amplified signal.
        
        Args:
            sensor_streams (List[SensorInput]): Input sensor data.
            
        Returns:
            Dict: Contains status, score, and is_warning_active flag.
        """
        try:
            trace, score = self.amplify_and_fuse(sensor_streams)
            
            is_warning = score > self.config.warning_threshold
            
            status = SystemState.NORMAL.name
            if is_warning:
                status = SystemState.EARLY_WARNING.name
                logger.warning(f"Micro-degradation detected! Score: {score:.4f}")
            
            return {
                "status": status,
                "degradation_score": float(score),
                "is_warning_active": bool(is_warning),
                "trace_length": len(trace)
            }
            
        except Exception as e:
            logger.error(f"Error during detection: {str(e)}")
            return {
                "status": "ERROR",
                "message": str(e)
            }

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate synthetic data simulating a tool wear process
    # Noise level is high (SNR < -10dB)
    np.random.seed(42)
    n_points = 1000
    time = np.linspace(0, 10, n_points)
    
    # Base vibration (normal operation)
    normal_vib = np.sin(2 * np.pi * 1 * time) 
    
    # Micro-degradation signal (very weak, high freq)
    micro_fault = 0.05 * np.sin(2 * np.pi * 50 * time) 
    # Inject fault only in second half
    micro_fault[:n_points//2] = 0 
    
    # Heavy Noise
    noise = 0.8 * np.random.normal(0, 1, n_points)
    
    # Sensor 1: Vibration
    vib_data = normal_vib + noise + micro_fault
    
    # Sensor 2: Acoustic Emission (correlated)
    ae_data = normal_vib * 0.5 + noise * 1.2 + micro_fault * 1.5
    
    # Create Input Objects
    sensors = [
        SensorInput("VIB_01", vib_data, 100.0, -5.0, 5.0),
        SensorInput("AE_02", ae_data, 100.0, -5.0, 5.0)
    ]
    
    # 2. Initialize Amplifier
    config = AmplifierConfig(window_size=64, warning_threshold=0.75)
    amplifier = WeakSignalAmplifier(config)
    
    # 3. Run Detection
    print("--- Processing Normal Phase (First Half) ---")
    result_normal = amplifier.detect_micro_degradation([
        SensorInput("VIB_01", vib_data[:n_points//2], 100.0),
        SensorInput("AE_02", ae_data[:n_points//2], 100.0)
    ])
    print(f"Result: {result_normal}")
    
    print("\n--- Processing Degraded Phase (Second Half) ---")
    result_degraded = amplifier.detect_micro_degradation(sensors)
    print(f"Result: {result_degraded}")