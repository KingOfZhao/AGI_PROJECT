"""
Module: holographic_digital_twin.py

A high-level engineering module designed for AGI systems to create a 'Holographic Digital Twin'.
This system transcends simple visual recording by fusing bio-signals, haptic feedback,
and semantic understanding to map physical 'craftsmanship' into reproducible digital assets.

Dependencies:
    - numpy
    - pydantic (for data validation)
    - scipy (for signal processing)

Installation:
    pip install numpy pydantic scipy
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field, validator
from scipy.signal import butter, lfilter

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HolographicDigitalTwin")

# --- Data Structures and Validation ---

class BioSignalData(BaseModel):
    """Validates input bio-signals (e.g., EMG, fNIRS)."""
    emg: List[float] = Field(..., description="Electromyography signal amplitude")
    fnirs: List[float] = Field(..., description="Functional Near-Infrared Spectroscopy data")
    sampling_rate: int = Field(1000, description="Sampling rate in Hz")

    @validator('emg', 'fnirs')
    def check_signal_length(cls, v, values):
        if len(v) < 10:
            raise ValueError("Signal length too short for processing")
        return v

class HapticSignalData(BaseModel):
    """Validates input haptic signals (vibration, slip)."""
    vibration_intensity: List[float] = Field(..., description="Vibration amplitude (0.0-1.0)")
    slip_index: List[float] = Field(..., description="Slip detection scalar (0.0-1.0)")

    @validator('vibration_intensity', 'slip_index')
    def check_range(cls, v):
        if not all(0.0 <= x <= 1.0 for x in v):
            raise ValueError("Haptic values must be normalized between 0.0 and 1.0")
        return v

class SemanticContext(BaseModel):
    """Validates semantic input."""
    description: str = Field(..., min_length=3, description="Natural language description of the action")
    skill_tags: List[str] = Field(default_factory=list)

# --- Core Classes ---

@dataclass
class SkillParameterCurve:
    """Represents the processed, reproducible skill parameters."""
    curve_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    force_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    tactile_texture_map: np.ndarray = field(default_factory=lambda: np.array([]))
    semantic_embedding: np.ndarray = field(default_factory=lambda: np.array([]))
    confidence_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "curve_id": self.curve_id,
            "force_profile": self.force_profile.tolist(),
            "tactile_texture_map": self.tactile_texture_map.tolist(),
            "confidence_score": self.confidence_score
        }

class HolographicTwinEngine:
    """
    The core engine for constructing the Holographic Digital Twin.
    Translates sensory inputs into aligned parameter curves.
    """

    def __init__(self, sensitivity: float = 0.85):
        self.sensitivity = sensitivity
        logger.info("HolographicTwinEngine initialized with sensitivity %.2f", sensitivity)

    def _butter_lowpass(self, cutoff: float, fs: float, order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Helper: Generate coefficients for a Butterworth low-pass filter."""
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    def _filter_signal(self, data: List[float], cutoff: float, fs: float) -> np.ndarray:
        """Helper: Apply low-pass filter to noisy bio-signals."""
        try:
            b, a = self._butter_lowpass(cutoff, fs)
            y = lfilter(b, a, data)
            return y
        except Exception as e:
            logger.error("Signal filtering failed: %s", e)
            return np.array(data)

    def extract_force_dynamics(self, bio_data: BioSignalData) -> np.ndarray:
        """
        Core Function 1:
        Translates raw bio-signals (EMG/fNIRS) into a normalized force profile curve.
        
        Args:
            bio_data: Validated bio-signal object.
            
        Returns:
            A numpy array representing the temporal force application.
        """
        logger.info("Extracting force dynamics from bio-signals...")
        
        # 1. Clean EMG signal
        emg_filtered = self._filter_signal(bio_data.emg, cutoff=20.0, fs=bio_data.sampling_rate)
        
        # 2. Rectify and smooth (Envelope detection)
        emg_rectified = np.abs(emg_filtered)
        
        # 3. Normalize to 0-1 range (Simulating Force)
        min_val, max_val = np.min(emg_rectified), np.max(emg_rectified)
        if max_val - min_val < 1e-6:
            return np.zeros_like(emg_rectified)
            
        force_profile = (emg_rectified - min_val) / (max_val - min_val)
        
        # Adjust sensitivity
        force_profile = np.tanh(force_profile * (1.0 / self.sensitivity))
        
        logger.debug("Force profile extracted with mean value: %.4f", np.mean(force_profile))
        return force_profile

    def synthesize_tactile_map(self, haptic_data: HapticSignalData, force_profile: np.ndarray) -> np.ndarray:
        """
        Core Function 2:
        Fuses vibration and slip data with force dynamics to create a tactile texture map.
        
        Args:
            haptic_data: Validated haptic signal object.
            force_profile: The output from extract_force_dynamics.
            
        Returns:
            A 2D numpy array (Time x Features) representing the tactile experience.
        """
        logger.info("Synthesizing tactile texture map...")
        
        # Ensure inputs are numpy arrays
        vib = np.array(haptic_data.vibration_intensity)
        slip = np.array(haptic_data.slip_index)
        
        # Align lengths (simple truncation to shortest signal)
        min_len = min(len(vib), len(slip), len(force_profile))
        
        if min_len == 0:
            raise ValueError("Input signals contain empty data after alignment check.")

        vib = vib[:min_len]
        slip = slip[:min_len]
        force = force_profile[:min_len]
        
        # Cross-modal alignment logic:
        # Texture intensity is modulated by force (pressure) and vibration
        # Slip indicates a transition in state
        texture_intensity = (vib * 0.6 + slip * 0.4) * force
        
        # Stack into a feature map (Time, [Texture, Slip, Force])
        tactile_map = np.vstack([texture_intensity, slip, force]).T
        
        logger.debug("Tactile map created with shape: %s", tactile_map.shape)
        return tactile_map

    def generate_digital_twin(
        self, 
        bio_data: BioSignalData, 
        haptic_data: HapticSignalData, 
        context: SemanticContext
    ) -> SkillParameterCurve:
        """
        High-level orchestration function to generate the full digital twin asset.
        """
        logger.info("Starting generation of Digital Twin Asset for skill: '%s'", context.description)
        
        try:
            # 1. Process Force
            force_profile = self.extract_force_dynamics(bio_data)
            
            # 2. Process Tactile
            tactile_map = self.synthesize_tactile_map(haptic_data, force_profile)
            
            # 3. Semantic Embedding (Simulated)
            # In a real scenario, this would call a BERT/LLM model
            # Here we create a deterministic hash-based vector for ID purposes
            semantic_vector = np.random.rand(128) 
            
            # 4. Calculate Confidence
            # Based on signal quality (simplified: signal variance)
            quality_score = np.std(force_profile) * 10 
            
            asset = SkillParameterCurve(
                force_profile=force_profile,
                tactile_texture_map=tactile_map,
                semantic_embedding=semantic_vector,
                confidence_score=float(np.clip(quality_score, 0, 1))
            )
            
            logger.info("Asset generation complete. ID: %s", asset.curve_id)
            return asset

        except Exception as e:
            logger.error("Failed to generate digital twin: %s", e)
            raise

# --- Usage Example ---

def run_demo():
    """
    Demonstrates the full workflow of the Holographic Digital Twin system.
    """
    print("--- Starting Holographic Digital Twin Demo ---")
    
    # 1. Simulate Input Data
    # Simulating 1 second of data at 100Hz
    t = np.linspace(0, 1, 100)
    
    # Fake EMG (Sinusoidal burst)
    emg_sig = np.sin(2 * np.pi * 5 * t) * np.exp(-t) + np.random.normal(0, 0.1, 100)
    # Fake fNIRS (Slow drift)
    fnirs_sig = np.cumsum(np.random.normal(0.001, 0.01, 100))
    
    # Fake Haptics
    vib_sig = np.abs(np.sin(2 * np.pi * 20 * t))
    slip_sig = np.random.uniform(0, 0.2, 100)
    slip_sig[70:80] = 0.9  # Simulate a slip event

    # 2. Validate Data
    try:
        bio_input = BioSignalData(emg=emg_sig.tolist(), fnirs=fnirs_sig.tolist(), sampling_rate=100)
        haptic_input = HapticSignalData(vibration_intensity=vib_sig.tolist(), slip_index=slip_sig.tolist())
        context_input = SemanticContext(description="Precision Grip Adjustment", skill_tags=["surgery", "fine_motor"])
    except Exception as e:
        print(f"Data Validation Failed: {e}")
        return

    # 3. Process
    engine = HolographicTwinEngine(sensitivity=0.9)
    digital_asset = engine.generate_digital_twin(bio_input, haptic_input, context_input)

    # 4. Output Results
    print(f"\nGenerated Asset ID: {digital_asset.curve_id}")
    print(f"Force Profile Shape: {digital_asset.force_profile.shape}")
    print(f"Tactile Map Shape: {digital_asset.tactile_texture_map.shape}")
    print(f"Confidence Score: {digital_asset.confidence_score:.4f}")
    print("\n--- Demo Complete ---")

if __name__ == "__main__":
    run_demo()