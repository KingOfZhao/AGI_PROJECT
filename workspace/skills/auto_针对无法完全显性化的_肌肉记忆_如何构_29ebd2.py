"""
Module: proprioceptive_feedback_loop.py

Description:
    Implements an 'Proprioceptive Error Correction Loop' for skills that rely on 
    implicit 'muscle memory' which cannot be fully codified.
    
    Instead of direct motor control, this system acts as a sensory extension,
    monitoring real-time tactile/haptic data deviations. It communicates 
    corrections via abstract, non-linguistic audio cues (rhythm/pitch) through 
    bone conduction headphones.
    
    Core Investigation:
    - Determines the delay tolerance limits for non-verbal guidance.
    - Evaluates the effectiveness boundaries of pitch-based force feedback.

Key Components:
    - TactileDataIngestion: Simulates or reads sensor data.
    - AudioFeedbackSynthesizer: Generates abstract audio cues.
    - FeedbackController: The core loop managing the symbiosis.

Author: AGI System
Version: 1.0.0
"""

import logging
import time
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Data Structures ---

class FeedbackState(Enum):
    """Enumeration for the current feedback state."""
    NOMINAL = 0       # Within tolerance
    CORRECTION = 1    # Deviation detected, sending cues
    CRITICAL = 2      # Boundary exceeded, immediate action required (simulation)

@dataclass
class SensorReading:
    """Represents a single reading from the tactile sensor."""
    timestamp: float
    pressure: float      # Range: 0.0 to 10.0 (abstract units)
    vibration: float     # Range: 0.0 to 100.0 (Hz or amplitude)
    shear_force: float   # Range: -5.0 to 5.0

@dataclass
class TargetProfile:
    """The 'Golden Standard' profile for the current muscle memory task."""
    target_pressure: float = 5.0
    pressure_tolerance: float = 0.5  # Deadband
    max_allowed_deviation: float = 2.0

@dataclass
class AudioCue:
    """Abstract representation of the audio feedback."""
    frequency_hz: float
    volume: float        # 0.0 to 1.0
    duration_ms: int
    is_beep: bool = False  # True for rhythmic pulses, False for continuous tone

class FeedbackController:
    """
    Manages the proprioceptive feedback loop.
    
    Monitors sensor input, compares it against the target profile, and generates
    abstract audio feedback to guide the user's muscle memory without explicit language.
    """

    def __init__(self, target_profile: TargetProfile, latency_budget_ms: float = 50.0):
        """
        Initialize the controller.
        
        Args:
            target_profile (TargetProfile): The baseline for the operation.
            latency_budget_ms (float): Maximum allowable system latency in milliseconds.
        """
        self.profile = target_profile
        self.latency_budget_s = latency_budget_ms / 1000.0
        self._state = FeedbackState.NOMINAL
        self._last_deviation = 0.0
        logger.info(f"Controller initialized with latency budget: {latency_budget_ms}ms")

    def _validate_reading(self, reading: SensorReading) -> bool:
        """Helper: Validates sensor data integrity."""
        if reading.timestamp < 0:
            logger.error("Invalid timestamp detected.")
            return False
        if not (0 <= reading.pressure <= 15.0): # Generous safety margin
            logger.warning(f"Pressure reading out of bounds: {reading.pressure}")
            # Clamp or handle as critical? Here we handle as valid but critical.
        return True

    def analyze_deviation(self, current: SensorReading) -> Tuple[FeedbackState, float]:
        """
        Core Logic: Analyzes the difference between current state and target.
        
        Implements a non-linear sensitivity curve to filter out micro-jitters
        but amplify significant drift.
        
        Args:
            current (SensorReading): The latest sensor data.
            
        Returns:
            Tuple[FeedbackState, float]: The current state and the normalized deviation (-1 to 1).
        """
        if not self._validate_reading(current):
            return FeedbackState.CRITICAL, 0.0

        # Calculate raw error
        error = current.pressure - self.profile.target_pressure
        
        # Apply deadband (tolerance zone)
        if abs(error) <= self.profile.pressure_tolerance:
            self._state = FeedbackState.NOMINAL
            normalized_deviation = 0.0
        else:
            # Normalize error relative to max deviation
            normalized_deviation = np.clip(
                error / self.profile.max_allowed_deviation, -1.0, 1.0
            )
            
            if abs(normalized_deviation) >= 0.9:
                self._state = FeedbackState.CRITICAL
            else:
                self._state = FeedbackState.CORRECTION

        self._last_deviation = normalized_deviation
        return self._state, normalized_deviation

    def generate_audio_cue(self, state: FeedbackState, deviation: float) -> Optional[AudioCue]:
        """
        Core Logic: Translates deviation into abstract auditory display.
        
        Strategy:
        - Pitch mapping: Higher pitch = Higher pressure (Too much force).
        - Rhythm: Pulses indicate urgency/distance from target.
        
        Args:
            state (FeedbackState): Current system state.
            deviation (float): Normalized deviation from target.
            
        Returns:
            AudioCue object or None if nominal.
        """
        if state == FeedbackState.NOMINAL:
            return None

        # Base frequency for 'Target' (e.g., 440Hz A4)
        base_freq = 440.0
        
        # Map deviation to frequency shift
        # deviation > 0 (Too hard) -> Higher Pitch
        # deviation < 0 (Too soft) -> Lower Pitch
        # Range: -1.0 -> 220Hz, +1.0 -> 880Hz
        freq_modifier = 2 ** (deviation) 
        target_freq = base_freq * freq_modifier
        
        # Urgency mapping (Volume and Rhythm)
        volume = 0.3 + (abs(deviation) * 0.6) # Louder as error grows
        
        if state == FeedbackState.CRITICAL:
            # Critical state triggers a rapid beep sequence simulation
            return AudioCue(frequency_hz=target_freq, volume=1.0, duration_ms=100, is_beep=True)
        
        return AudioCue(frequency_hz=target_freq, volume=volume, duration_ms=200, is_beep=False)

    def execute_loop_step(self, reading: SensorReading) -> Optional[AudioCue]:
        """
        High-level orchestration of one feedback cycle.
        """
        start_time = time.perf_counter()
        
        state, dev = self.analyze_deviation(reading)
        cue = self.generate_audio_cue(state, dev)
        
        processing_time = time.perf_counter() - start_time
        
        # Boundary Check: Latency
        if processing_time > self.latency_budget_s:
            logger.warning(
                f"Processing latency {processing_time*1000:.2f}ms exceeded "
                f"budget {self.latency_budget_s*1000:.2f}ms. Effectiveness reduced."
            )
            
        return cue

# --- Helper Functions ---

def simulate_sensor_stream(duration_sec: int = 5, drift_factor: float = 0.1) -> List[SensorReading]:
    """
    Helper: Generates synthetic sensor data simulating a user attempting 
    to maintain pressure but drifting.
    
    Args:
        duration_sec (int): Duration of the simulation.
        drift_factor (float): Magnitude of random fluctuation.
        
    Returns:
        List[SensorReading]: A list of simulated data points.
    """
    readings = []
    samples = duration_sec * 20 # 20 Hz sample rate
    base_pressure = 5.0
    
    logger.info(f"Generating {samples} sensor readings...")
    
    for i in range(samples):
        # Simulate drift: sinusoidal + noise
        drift = np.sin(i / 10) * 1.5 + np.random.normal(0, drift_factor)
        pressure = base_pressure + drift
        
        # Boundary check for simulation reality
        pressure = max(0, pressure)
        
        reading = SensorReading(
            timestamp=time.time() + (i * 0.05),
            pressure=pressure,
            vibration=np.random.uniform(10, 20),
            shear_force=np.random.uniform(-0.5, 0.5)
        )
        readings.append(reading)
        
    return readings

def format_cue_for_output(cue: Optional[AudioCue]) -> str:
    """
    Helper: Formats the audio cue into a readable string for logging/display.
    """
    if not cue:
        return "[Status: NOMINAL] (Silence)"
    
    mode = "PULSE" if cue.is_beep else "TONE"
    direction = "HIGH (Reduce Force)" if cue.frequency_hz > 440 else "LOW (Increase Force)"
    
    return (f"[Status: ALERT] {mode} | Freq: {cue.frequency_hz:.1f}Hz | "
            f"Vol: {cue.volume:.2f} | Hint: {direction}")

# --- Main Execution / Usage Example ---

if __name__ == "__main__":
    # 1. Setup
    profile = TargetProfile(target_pressure=5.0, pressure_tolerance=0.5)
    controller = FeedbackController(profile, latency_budget_ms=50.0)
    
    # 2. Simulate Input Data
    simulated_data = simulate_sensor_stream(duration_sec=3)
    
    print("\n--- Starting Proprioceptive Feedback Loop Simulation ---\n")
    
    # 3. Run Loop
    for reading in simulated_data:
        # Process the reading
        cue = controller.execute_loop_step(reading)
        
        # Visualize Output (In real scenario, this plays audio)
        output_str = format_cue_for_output(cue)
        
        # Only log changes or periodic updates to avoid spam
        if cue is not None or np.random.random() > 0.8:
            print(f"Pressure: {reading.pressure:.2f} -> {output_str}")
            
        time.sleep(0.05) # Simulate real-time delay

    print("\n--- Simulation Complete ---")