"""
Industrial Implicit Knowledge Digitization Module.

This module provides a real-time stream processing framework designed to convert
unstructured, high-frequency sensor data (vibration, acoustic, thermal) from
industrial scenarios into structured "Anomaly Pattern Vectors".

It addresses the challenge of digitizing "Tacit Knowledge" (e.g., a veteran
engineer detecting faults by ear) by implementing an adaptive, streaming
clustering algorithm (MiniBatchKMeans) with dynamic noise thresholding.

Key Features:
- Multi-modal sensor data fusion.
- Real-time streaming clustering.
- Dynamic thresholding to separate noise from weak fault signals.
- Conversion of raw waveforms into structured "Pre-node" vectors.

Author: AGI System
Version: 1.0.0
Domain: industrial_iot
"""

import logging
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SensorType(Enum):
    """Enumeration for supported industrial sensor types."""
    VIBRATION = "vibration"
    ACOUSTIC = "acoustic"
    THERMAL = "thermal"


@dataclass
class SensorConfig:
    """Configuration for a specific sensor modality."""
    sensor_id: str
    type: SensorType
    sample_rate: int
    noise_floor: float  # Baseline noise level determined by calibration
    weight: float = 1.0  # Importance weight for fusion


@dataclass
class AnomalyPatternVector:
    """
    Structured output representing a detected anomaly pattern (Pre-node).
    
    Attributes:
        vector_id: Unique identifier for the vector.
        timestamp: Detection time.
        cluster_id: The ID of the cluster this pattern belongs to.
        feature_vector: The compressed numerical representation of the anomaly.
        confidence: Detection confidence score (0.0 to 1.0).
        is_weak_signal: Flag indicating if this is a micro-signal potentially
                        missed by simple thresholding.
    """
    vector_id: str
    timestamp: float
    cluster_id: int
    feature_vector: np.ndarray
    confidence: float
    is_weak_signal: bool


class IndustrialKnowledgeDigitizer:
    """
    Transforms unstructured industrial sensor streams into structured anomaly vectors.
    
    This class implements a streaming pipeline that:
    1. Extracts features from raw waveform chunks.
    2. Filters noise using a dynamic threshold mechanism.
    3. Clusters features into "Pattern Pre-nodes".
    4. Identifies weak signals that deviate from noise but haven't formed major clusters.
    """

    def __init__(self, 
                 configs: List[SensorConfig], 
                 n_clusters: int = 15, 
                 buffer_size: int = 100,
                 sensitivity: float = 1.5):
        """
        Initialize the digitizer.
        
        Args:
            configs: List of sensor configurations.
            n_clusters: Number of micro-clusters for pattern recognition.
            buffer_size: Size of the sliding window for batch processing.
            sensitivity: Multiplier for dynamic threshold calculation (Sigma * sensitivity).
        """
        self.configs = {cfg.sensor_id: cfg for cfg in configs}
        self.n_clusters = n_clusters
        self.buffer_size = buffer_size
        self.sensitivity = sensitivity
        
        # Core algorithm components
        self.scaler = StandardScaler()
        # MiniBatchKMeans is chosen for streaming capability
        self.model = MiniBatchKMeans(
            n_clusters=n_clusters, 
            random_state=42, 
            batch_size=buffer_size,
            n_init='auto'
        )
        
        self.feature_buffer: List[np.ndarray] = []
        self.is_model_warmed_up: bool = False
        self.global_noise_baseline: float = 0.0
        
        logger.info(f"IndustrialKnowledgeDigitizer initialized with {n_clusters} target clusters.")

    def _extract_features(self, raw_data: np.ndarray, sensor_id: str) -> np.ndarray:
        """
        [Helper] Extracts statistical and spectral features from a raw waveform chunk.
        
        Args:
            raw_data: 1D array of raw sensor values.
            sensor_id: ID of the sensor source.
            
        Returns:
            A 1D numpy array containing extracted features (RMS, Peak, Kurtosis, etc.).
        """
        if raw_data.ndim != 1:
            raise ValueError("Input raw_data must be a 1D array.")

        # Basic Statistical Features
        rms = np.sqrt(np.mean(raw_data**2))
        peak = np.max(np.abs(raw_data))
        crest_factor = peak / rms if rms > 1e-6 else 0.0
        kurtosis = self._calculate_kurtosis(raw_data)
        
        # Simple Frequency Domain Feature (Energy in high band - placeholder)
        # In a real scenario, this would involve FFT
        spectral_centroid = np.mean(np.abs(np.diff(raw_data))) 

        # Combine features
        features = np.array([rms, peak, crest_factor, kurtosis, spectral_centroid])
        
        # Normalize based on sensor specific noise floor if available
        cfg = self.configs.get(sensor_id)
        if cfg:
            features[0] /= (cfg.noise_floor + 1e-6) # Normalize RMS
            
        return features

    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of the signal (sensitivity to impulses)."""
        if len(data) < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std < 1e-6:
            return 0.0
        return np.mean(((data - mean) / std)**4) - 3.0

    def process_stream_chunk(self, 
                             data_chunk: Dict[str, np.ndarray], 
                             timestamp: float) -> List[AnomalyPatternVector]:
        """
        Process a single time-window of multi-modal sensor data.
        
        This is the core perception function. It converts unstructured chunks
        into structured vectors or filters them as noise.
        
        Args:
            data_chunk: Dictionary mapping sensor_id -> raw waveform array.
            timestamp: Current timestamp of the chunk.
            
        Returns:
            A list of AnomalyPatternVector objects detected in this chunk.
        """
        if not isinstance(data_chunk, dict):
            raise TypeError("data_chunk must be a dictionary.")

        fused_features = []
        valid_sensors = 0
        
        # 1. Feature Extraction & Fusion
        for sensor_id, raw_wave in data_chunk.items():
            if sensor_id not in self.configs:
                logger.warning(f"Unknown sensor ID: {sensor_id}")
                continue
            
            try:
                # Ensure input validity
                if not isinstance(raw_wave, np.ndarray) or len(raw_wave) == 0:
                    continue
                    
                features = self._extract_features(raw_wave, sensor_id)
                weight = self.configs[sensor_id].weight
                fused_features.append(features * weight)
                valid_sensors += 1
            except Exception as e:
                logger.error(f"Error processing sensor {sensor_id}: {e}")
                continue

        if valid_sensors == 0:
            return []

        # Average features across sensors (Simple Fusion)
        current_feature_vector = np.mean(fused_features, axis=0)
        
        # 2. Noise Filtering & Dynamic Thresholding
        # We maintain a running estimate of the 'normal' background signal
        current_norm = np.linalg.norm(current_feature_vector)
        
        detected_patterns = []
        
        # Adaptive Logic: Update baseline if quiet, detect if loud
        if len(self.feature_buffer) < self.buffer_size:
            # Learning phase: accumulate data
            self.feature_buffer.append(current_feature_vector)
            self.global_noise_baseline = np.mean([np.linalg.norm(f) for f in self.feature_buffer])
            
            # Warm up the scaler and model
            if len(self.feature_buffer) == self.buffer_size:
                logger.info("Buffer full. Warming up model...")
                X = np.array(self.feature_buffer)
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                self.model.partial_fit(X_scaled)
                self.is_model_warmed_up = True
                logger.info("Model warm-up complete.")
                
        else:
            # Operational Phase
            # Update baseline slowly (EMA)
            ema_alpha = 0.05
            self.global_noise_baseline = (1 - ema_alpha) * self.global_noise_baseline + ema_alpha * current_norm
            
            # Check against dynamic threshold
            threshold = self.global_noise_baseline * self.sensitivity
            
            if current_norm > threshold:
                # This is a significant event
                scaled_vec = self.scaler.transform([current_feature_vector])
                cluster_id = self.model.predict(scaled_vec)[0]
                
                # Continuous learning: update the cluster center
                self.model.partial_fit(scaled_vec)
                
                # Determine if it's a weak signal (close to threshold but distinct)
                is_weak = (current_norm < threshold * 1.5)
                
                pattern = AnomalyPatternVector(
                    vector_id=f"vec_{int(timestamp * 1000)}_{cluster_id}",
                    timestamp=timestamp,
                    cluster_id=int(cluster_id),
                    feature_vector=current_feature_vector,
                    confidence=min(1.0, current_norm / threshold),
                    is_weak_signal=is_weak
                )
                detected_patterns.append(pattern)
                
                logger.debug(f"Detected pattern: Cluster {cluster_id}, Weak: {is_weak}")
            
            # Keep buffer sliding (optional, as MiniBatch handles streaming well)
            # Here we just keep the baseline dynamic
            
        return detected_patterns

    def get_structured_knowledge_state(self) -> Dict[str, Any]:
        """
        Returns the current structured state of the knowledge base (Cluster centers).
        
        This represents the 'Explicit Knowledge' derived from the stream.
        """
        if not self.is_model_warmed_up:
            return {"status": "warming_up"}
            
        return {
            "status": "active",
            "n_patterns": self.n_clusters,
            "pattern_centers": self.model.cluster_centers_.tolist(),
            "current_noise_baseline": self.global_noise_baseline
        }

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Setup Configuration
    # Simulating a vibration sensor and an acoustic sensor
    vibration_cfg = SensorConfig(
        sensor_id="acc_01", 
        type=SensorType.VIBRATION, 
        sample_rate=10000, 
        noise_floor=0.05,
        weight=1.2
    )
    acoustic_cfg = SensorConfig(
        sensor_id="mic_01", 
        type=SensorType.ACOUSTIC, 
        sample_rate=44100, 
        noise_floor=0.02,
        weight=0.8
    )
    
    # 2. Initialize System
    digitizer = IndustrialKnowledgeDigitizer(
        configs=[vibration_cfg, acoustic_cfg],
        n_clusters=5,
        buffer_size=10, # Small buffer for demo
        sensitivity=2.0
    )
    
    print("--- Starting Industrial Stream Simulation ---")
    
    # 3. Simulate Stream
    # First 10 iterations fill the buffer (Noise only)
    for i in range(10):
        noise_vib = np.random.normal(0, 0.05, 100)
        noise_mic = np.random.normal(0, 0.02, 100)
        
        chunk = {"acc_01": noise_vib, "mic_01": noise_mic}
        digitizer.process_stream_chunk(chunk, time.time())
        
    # 4. Inject Anomaly (Simulating a 'Loose Bolt' vibration)
    print("\n--- Injecting Anomaly ---")
    for i in range(5):
        # Normal noise
        noise_vib = np.random.normal(0, 0.05, 100)
        noise_mic = np.random.normal(0, 0.02, 100)
        
        # Inject impulse (High Kurtosis)
        if i == 2:
            noise_vib += np.random.normal(0, 0.8, 100) # Spike
            print(f" > Injected mechanical impulse at step {i+11}")
        
        chunk = {"acc_01": noise_vib, "mic_01": noise_mic}
        patterns = digitizer.process_stream_chunk(chunk, time.time())
        
        if patterns:
            for p in patterns:
                print(f"DETECTED: {p.vector_id} | Cluster: {p.cluster_id} | "
                      f"Weak Signal: {p.is_weak_signal} | Conf: {p.confidence:.2f}")

    # 5. Check Final Knowledge State
    print("\n--- Final Knowledge State ---")
    state = digitizer.get_structured_knowledge_state()
    print(f"System Status: {state['status']}")
    print(f"Learned Patterns: {state['n_patterns']}")