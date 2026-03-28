"""
Module: cross_modal_sonifier.py

A high-level skill module for AGI systems designed to translate high-dimensional
proprioceptive data (specifically force/torque and vibration) into auditory signals
(Sonification). This enables a "Human-in-the-loop" training paradigm where the AI
can "hear" the nuances of force application, facilitating the learning of implicit,
"just-right" control strategies (e.g., tactile gentleness).

Domain: Cognitive Psychology / Human-Computer Interaction / Robotics
"""

import logging
import numpy as np
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossModalSonifier")


class SonificationMode(Enum):
    """Defines the strategy for mapping data to sound."""
    CONTINUOUS_TONE = 1  # Frequency modulation based on force magnitude
    SPATIAL_PANNING = 2  # Stereo position based on vibration/force direction


@dataclass
class ProprioceptiveFrame:
    """
    Input data structure representing a single timestamp of sensory input.
    
    Attributes:
        timestamp (float): Unix timestamp or relative time in seconds.
        force_vector (np.ndarray): 3D vector [Fx, Fy, Fz] representing applied force in Newtons.
        vibration_spectrum (np.ndarray): 1D array representing vibration intensity across frequency bins.
        grip_force (float): Scalar value representing normal grip force.
    """
    timestamp: float
    force_vector: np.ndarray
    vibration_spectrum: np.ndarray
    grip_force: float


class CrossModalTranslator:
    """
    Translates high-dimensional tactile/force data into auditory parameters.
    
    This class implements the core logic of the 'Cross-Domain Translator'. It maps
    physical constraints (force magnitude, vibration frequency) to psychoacoustic
    parameters (pitch, volume, timbre) to make subtle physical interactions audible.
    """

    def __init__(self, 
                 max_force_limit: float = 100.0, 
                 sample_rate: int = 44100,
                 mode: SonificationMode = SonificationMode.CONTINUOUS_TONE):
        """
        Initialize the translator with safety limits and audio configurations.

        Args:
            max_force_limit (float): The expected maximum force for normalization.
            sample_rate (int): Audio sample rate (e.g., 44100 Hz).
            mode (SonificationMode): The type of sonification mapping.
        """
        self.max_force_limit = self._validate_positive(max_force_limit, "Max Force Limit")
        self.sample_rate = sample_rate
        self.mode = mode
        self._ prev_phase = 0.0 # For phase continuity in audio generation
        
        logger.info(f"CrossModalTranslator initialized with mode: {mode.name}")

    def _validate_positive(self, value: float, name: str) -> float:
        """Helper: Validates that a value is positive."""
        if value <= 0:
            logger.error(f"Validation Error: {name} must be positive, got {value}")
            raise ValueError(f"{name} must be positive.")
        return value

    def _normalize_data(self, data: ProprioceptiveFrame) -> Tuple[float, float, float]:
        """
        Core processing logic: Normalizes raw sensory data into abstract intensity values [0.0, 1.0].
        
        Returns:
            Tuple[float, float, float]: (ForceIntensity, VibrationComplexity, GripSafetyMargin)
        """
        # 1. Calculate Force Magnitude (Euclidean norm)
        force_mag = np.linalg.norm(data.force_vector)
        
        # Boundary check / Clipping
        normalized_force = np.clip(force_mag / self.max_force_limit, 0.0, 1.0)
        
        # 2. Calculate Vibration Complexity (Variance of the spectrum indicates 'roughness' or 'texture')
        # High variance often indicates contact or slippage
        vib_variance = np.var(data.vibration_spectrum) if len(data.vibration_spectrum) > 0 else 0.0
        normalized_vib = np.clip(np.tanh(vib_variance / 10.0), 0.0, 1.0) # Tanh for non-linear scaling
        
        # 3. Calculate Grip Safety (How close to 'breaking' vs 'crushing')
        # Here we just return raw grip for external mapping
        grip = data.grip_force
        
        logger.debug(f"Norm Force: {normalized_force:.2f}, Vib: {normalized_vib:.2f}")
        return normalized_force, normalized_vib, grip

    def generate_audio_frame(self, 
                             data_frame: ProprioceptiveFrame, 
                             frame_duration_sec: float = 0.01) -> np.ndarray:
        """
        Generates a waveform chunk (audio signal) based on the input sensory frame.
        
        This is the primary function for real-time sonification. It uses FM synthesis
        (Frequency Modulation) where Force controls the Carrier Frequency and Vibration
        controls the Modulation Index (timbre richness).

        Args:
            data_frame (ProprioceptiveFrame): The sensory input.
            frame_duration_sec (float): Duration of the audio buffer to generate.

        Returns:
            np.ndarray: A 1D array of floating-point audio samples (mono).
        """
        if not isinstance(data_frame, ProprioceptiveFrame):
             raise TypeError("Input must be a ProprioceptiveFrame instance")

        try:
            n_samples = int(self.sample_rate * frame_duration_sec)
            t = np.linspace(0, frame_duration_sec, n_samples, endpoint=False)
            
            # Extract features
            f_intensity, v_intensity, _ = self._normalize_data(data_frame)
            
            if self.mode == SonificationMode.CONTINUOUS_TONE:
                # Map Force to Pitch (Frequency): 200Hz (soft) to 2000Hz (hard)
                carrier_freq = 200 + (f_intensity * 1800)
                
                # Map Vibration to Timbre (Modulation Index)
                mod_freq = 50.0
                mod_index = v_intensity * 10.0 # Higher vibration = rougher sound
                
                # FM Synthesis: y(t) = sin(w_c*t + I*sin(w_m*t))
                # Using phase accumulation to prevent clicking between frames
                phase_carrier = 2 * np.pi * carrier_freq * t + self._prev_phase
                modulator = mod_index * np.sin(2 * np.pi * mod_freq * t)
                
                waveform = np.sin(phase_carrier + modulator)
                
                # Update phase for next chunk to ensure continuity
                self._prev_phase = phase_carrier[-1] % (2 * np.pi)
                
                # Apply Amplitude envelope based on force (optional)
                waveform *= (0.3 + 0.7 * f_intensity)
                
            else:
                # Fallback or placeholder for other modes
                waveform = np.zeros(n_samples)

            return waveform

        except Exception as e:
            logger.error(f"Error generating audio frame: {e}")
            return np.zeros(int(self.sample_rate * frame_duration_sec))

    def translate_to_visual_cue(self, data_frame: ProprioceptiveFrame) -> Dict[str, float]:
        """
        Translates sensory data into abstract visual parameters (e.g., for a HUD).
        
        Returns:
            Dict containing 'color_hue', 'opacity', and 'glow_radius'.
        """
        f_norm, v_norm, _ = self._normalize_data(data_frame)
        
        # Hue: 0.0 (Green/Safe) -> 0.33 (Yellow/Warning) -> 0.66 (Red/Danger) based on force
        hue = f_norm * 0.66 
        
        # Opacity based on vibration (presence of activity)
        opacity = 0.2 + (v_norm * 0.8)
        
        return {
            "color_hue": hue,
            "opacity": opacity,
            "glow_radius": f_norm * 100.0
        }


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    import time
    
    def run_demo():
        print("Starting Cross-Modal Translator Demo...")
        
        # 1. Initialize System
        translator = CrossModalTranslator(max_force_limit=50.0)
        
        # 2. Simulate a stream of data (e.g., a robot arm gripping an object)
        # Simulating 1 second of interaction at 100Hz
        stream_duration = 1.0
        steps = 100
        dt = stream_duration / steps
        
        print(f"Simulating {steps} frames of interaction...")
        
        for i in range(steps):
            # Simulate data: Increasing force then stabilizing
            fake_force_scalar = min(45, i * 0.8) # Force ramping up
            noise = np.random.normal(0, 0.5, 3)
            
            # Create Input Frame
            frame = ProprioceptiveFrame(
                timestamp=i * dt,
                force_vector=np.array([fake_force_scalar, 0, 0]) + noise,
                vibration_spectrum=np.random.random(10) * (fake_force_scalar / 50.0), # Vibration correlates with force
                grip_force=fake_force_scalar * 0.8
            )
            
            # 3. Translate to Audio (The core AGI Skill)
            audio_chunk = translator.generate_audio_frame(frame, frame_duration_sec=dt)
            
            # 4. Translate to Visual (Optional secondary feedback)
            visual_state = translator.translate_to_visual_cue(frame)
            
            # Log summary (In real usage, audio_chunk would go to a sound card buffer)
            if i % 20 == 0:
                print(f"Time {frame.timestamp:.2f}s | "
                      f"Force: {np.linalg.norm(frame.force_vector):.1f}N | "
                      f"Audio Freq Base: {200 + (audio_chunk.mean()*1000):.0f}Hz | "
                      f"Visual Hue: {visual_state['color_hue']:.2f}")
                       
    run_demo()