"""
Module: multimodal_craft_digital_twin.py

This module implements a sophisticated framework for the 'Multi-modal Knowledge Solidification System'.
It is designed to capture, process, and digitalize tacit knowledge in craftsmanship and industrial
processes by synthesizing biological signals (EMG/fNIRS), haptic physical data, and semantic context.

The system aims to transform non-structural, intuitive experiences (often described as 'feel' or 'muscle memory')
into high-fidelity, computable digital assets, facilitating the transfer of biological skills to silicon-based agents.

Key Features:
- Synchronization of multi-rate sensor data (Bio/Phy).
- Semantic vectorization using Sentence Transformers.
- Construction of a holographic state vector.
- Quality assurance via signal integrity checks.

Dependencies:
    - numpy
    - pandas
    - scipy
    - sentence-transformers (optional, falls back to dummy vectorization for demo)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from scipy.signal import butter, lfilter
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultimodalCraftTwin")

# --- Constants and Configuration ---
DEFAULT_SAMPLE_RATE_BIO = 1000  # Hz (e.g., EMG)
DEFAULT_SAMPLE_RATE_TACTILE = 100  # Hz (Pressure/Texture)
VECTOR_DIMENSION = 384  # Dimension for semantic embeddings (e.g., MiniLM-L6)

@dataclass
class SensorPacket:
    """Represents a single timestamped packet of multi-modal data."""
    timestamp: float
    emg_data: np.ndarray  # Shape: (channels,)
    fnirs_data: np.ndarray  # Shape: (channels,) - Oxygenation levels
    tactile_pressure: np.ndarray  # Shape: (sensors_grid_x, sensors_grid_y)
    tactile_texture_id: int  # ID representing surface friction/roughness
    semantic_context: str  # Natural language description of current action

@dataclass
class DigitalAsset:
    """The output structure representing a solidified skill segment."""
    session_id: str
    start_time: str
    feature_matrix: np.ndarray  # Unified feature set
    semantic_embedding: np.ndarray
    skill_quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class SignalProcessingError(Exception):
    """Custom exception for signal processing failures."""
    pass

class DataValidationError(Exception):
    """Custom exception for invalid input data."""
    pass

class MultimodalCraftSolidifier:
    """
    Core engine for converting raw sensory streams into a solidified digital twin of skill.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._validate_environment()
        logger.info(f"Initialized Solidifier for session {session_id}")

    def _validate_environment(self) -> None:
        """Checks for necessary libraries and hardware constraints."""
        try:
            # Attempt to import sentence_transformers, fallback if not available
            from sentence_transformers import SentenceTransformer
            self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded successfully.")
        except ImportError:
            logger.warning("sentence-transformers not found. Using dummy semantic encoder.")
            self.semantic_model = None
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            self.semantic_model = None

    @staticmethod
    def _butter_lowpass(cutoff: float, fs: float, order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Helper: Generate Butterworth lowpass filter coefficients."""
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    def _denoise_signal(self, data: np.ndarray, fs: float, cutoff: float = 20.0) -> np.ndarray:
        """
        Applies a low-pass filter to clean biological signals.
        
        Args:
            data (np.ndarray): Raw signal data.
            fs (float): Sampling frequency.
            cutoff (float): Cutoff frequency for the filter.
        
        Returns:
            np.ndarray: Filtered signal.
        """
        if data.size == 0:
            raise SignalProcessingError("Cannot denoise empty signal array.")
        
        try:
            b, a = self._butter_lowpass(cutoff, fs)
            y = lfilter(b, a, data, axis=0)
            return y
        except Exception as e:
            logger.error(f"Signal filtering failed: {e}")
            raise SignalProcessingError(f"Filtering error: {e}")

    def _vectorize_semantics(self, text: str) -> np.ndarray:
        """
        Converts natural language context into a dense vector embedding.
        
        Args:
            text (str): The context description (e.g., "Applying light pressure for polishing").
            
        Returns:
            np.ndarray: Dense vector representation.
        """
        if self.semantic_model:
            try:
                return self.semantic_model.encode(text)
            except Exception as e:
                logger.warning(f"Semantic encoding failed: {e}. Returning zero vector.")
        
        # Fallback dummy encoding for robustness
        vec = np.zeros(VECTOR_DIMENSION)
        simple_hash = sum(ord(c) for c in text) % VECTOR_DIMENSION
        vec[simple_hash % VECTOR_DIMENSION] = 1.0
        return vec

    def process_craft_segment(self, data_stream: List[SensorPacket]) -> DigitalAsset:
        """
        Main pipeline: Transforms a list of sensor packets into a solidified Digital Asset.
        
        Args:
            data_stream (List[SensorPacket]): A time-series of multi-modal observations.
            
        Returns:
            DigitalAsset: The structured digital representation of the skill segment.
            
        Raises:
            DataValidationError: If input data is empty or malformed.
            SignalProcessingError: If signal processing fails.
        """
        if not data_stream:
            raise DataValidationError("Input data stream cannot be empty.")

        logger.info(f"Processing segment with {len(data_stream)} packets.")
        
        # 1. Extract and Separate Modalities
        try:
            emg_buffer = np.array([p.emg_data for p in data_stream])
            fnirs_buffer = np.array([p.fnirs_data for p in data_stream])
            tactile_buffer = np.array([p.tactile_pressure for p in data_stream])
            semantic_text = data_stream[-1].semantic_context # Use the latest context
            timestamp_start = data_stream[0].timestamp
        except (AttributeError, IndexError) as e:
            raise DataValidationError(f"Malformed data packet structure: {e}")

        # 2. Signal Processing (The "Feel" Extraction)
        # Denoising EMG to isolate muscle activation bursts
        clean_emg = self._denoise_signal(emg_buffer, fs=DEFAULT_SAMPLE_RATE_BIO, cutoff=50.0)
        
        # Normalize fNIRS (Cognitive load)
        # Assuming baseline is the first few seconds, simple normalization
        fnirs_baseline = np.mean(fnirs_buffer[:10], axis=0)
        delta_fnirs = fnirs_buffer - fnirs_baseline
        
        # 3. Feature Engineering
        # EMG Power (Root Mean Square)
        emg_rms = np.sqrt(np.mean(np.square(clean_emg), axis=0))
        
        # Tactile Pressure Distribution (Center of Pressure)
        # Assuming tactile_buffer shape is (Time, X, Y)
        pressure_mean = np.mean(tactile_buffer, axis=0)
        total_pressure = np.sum(pressure_mean)
        
        # Calculate 2D Center of Pressure (CoP)
        if total_pressure > 0:
            x_coords = np.arange(pressure_mean.shape[0])
            y_coords = np.arange(pressure_mean.shape[1])
            cop_x = np.sum(pressure_mean * x_coords[:, None]) / total_pressure
            cop_y = np.sum(pressure_mean * y_coords[None, :]) / total_pressure
            cop_features = np.array([cop_x, cop_y, total_pressure])
        else:
            cop_features = np.zeros(3)

        # 4. Semantic Vectorization (The "Intent" Extraction)
        semantic_vector = self._vectorize_semantics(semantic_text)

        # 5. Fusion & Solidification
        # Concatenate physical features with biological features
        physical_features = np.concatenate([
            emg_rms.flatten(),          # Muscle intensity
            delta_fnirs.mean(axis=0),   # Cognitive state
            cop_features                # Touch dynamics
        ])
        
        # Calculate a 'Skill Fidelity Score' (Heuristic)
        # High score = stable EMG + consistent pressure + clear intent
        stability_score = 1.0 / (1.0 + np.std(clean_emg)) # Inverse of variance
        intensity_score = np.mean(emg_rms) / 1000.0 # Normalized intensity
        quality_score = np.clip((stability_score * 0.5 + intensity_score * 0.5), 0.0, 1.0)

        # Create the unified feature matrix (Time x Features)
        # Here we aggregate the whole segment into a single state vector for the asset
        unified_features = np.concatenate([physical_features, semantic_vector])

        # 6. Packaging
        asset = DigitalAsset(
            session_id=self.session_id,
            start_time=datetime.fromtimestamp(timestamp_start).isoformat(),
            feature_matrix=unified_features,
            semantic_embedding=semantic_vector,
            skill_quality_score=float(quality_score),
            metadata={
                "emg_channels": emg_buffer.shape[1],
                "tactile_grid": tactile_buffer.shape[1:],
                "context": semantic_text
            }
        )

        logger.info(f"Asset solidified. Quality Score: {quality_score:.4f}")
        return asset

# --- Usage Example ---
if __name__ == "__main__":
    # Mock Data Generation
    def generate_mock_data(n_samples: int = 100) -> List[SensorPacket]:
        data = []
        for i in range(n_samples):
            packet = SensorPacket(
                timestamp=1698765000.0 + i * 0.01,
                emg_data=np.random.normal(0.5, 0.1, 4), # 4 channels of muscle activity
                fnirs_data=np.random.normal(0.8, 0.05, 2), # 2 channels of O2 levels
                tactile_pressure=np.random.rand(8, 8), # 8x8 pressure grid
                tactile_texture_id=5,
                semantic_context="Gentle sanding motion on mahogany"
            )
            data.append(packet)
        return data

    try:
        # Initialize System
        solidifier = MultimodalCraftSolidifier(session_id="craft_proc_001")
        
        # Generate Input
        raw_stream = generate_mock_data(200)
        
        # Process
        digital_asset = solidifier.process_craft_segment(raw_stream)
        
        # Output Results
        print("-" * 60)
        print(f"Digital Asset Created: {digital_asset.session_id}")
        print(f"Timestamp: {digital_asset.start_time}")
        print(f"Quality Score: {digital_asset.skill_quality_score:.4f}")
        print(f"Feature Vector Dimensions: {digital_asset.feature_matrix.shape}")
        print(f"Context: {digital_asset.metadata['context']}")
        print("-" * 60)
        
    except (DataValidationError, SignalProcessingError) as e:
        logger.error(f"System failed to process craft: {e}")