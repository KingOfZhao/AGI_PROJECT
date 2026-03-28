"""
Module: cognitive_flow_controller
A dynamic cybernetic system for human-computer interaction.

This system prioritizes maintaining the user's 'optimal cognitive experience (Flow)'
over mere information transmission efficiency. It monitors 'cognitive friction'
(such as interaction latency, error rates, physiological signals) in real-time
and constructs a bi-directional adaptive protocol.

Core Logic:
- Detects cognitive overload based on multi-modal inputs.
- Automatically adjusts output granularity (information density).
- Switches interaction modalities (e.g., from Text to Spatial Visualization).
- Uses spatial constraints to aid attention focusing when necessary.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Any

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveFlowSystem")


class Modality(Enum):
    """Enumeration of available interaction modalities."""
    TEXT_HIGH_DENSITY = auto()
    TEXT_LOW_DENSITY = auto()
    SPATIAL_VISUALIZATION = auto()
    AMBIENT_FEEDBACK = auto()


class CognitiveState(Enum):
    """Estimated state of the human user."""
    BORED = 0      # Underload
    FLOW = 1       # Optimal
    OVERLOAD = 2   # Stress/Friction


@dataclass
class BioSensorData:
    """Container for physiological sensor inputs."""
    pupil_dilation: float  # mm (normalized baseline 4.0mm)
    eye_saccade_rate: float  # Hz
    emg_stress_level: float  # Microvolts (0-100 scale)

    def is_valid(self) -> bool:
        """Validate sensor data ranges."""
        return 0 <= self.emg_stress_level <= 100 and self.pupil_dilation > 0


@dataclass
class SystemTelemetry:
    """Container for system performance metrics."""
    latency_ms: float
    error_rate: float  # 0.0 to 1.0
    complexity_score: float  # 0.0 to 1.0 (current output complexity)


class CognitiveController:
    """
    Main controller class for the Adaptive Cybernetic System.
    
    Attributes:
        history (List[Dict]): Historical logs of state transitions.
        current_modality (Modality): The active interaction mode.
        friction_threshold (float): Limit before adaptive measures trigger.
    """

    def __init__(self, friction_threshold: float = 0.75):
        """
        Initialize the controller.

        Args:
            friction_threshold (float): The cognitive load limit (0-1) before switching strategies.
        """
        if not 0 < friction_threshold < 1:
            raise ValueError("Threshold must be between 0 and 1.")
        
        self.friction_threshold = friction_threshold
        self.current_modality = Modality.TEXT_HIGH_DENSITY
        self.history: List[Dict[str, Any]] = []
        logger.info("Cognitive Controller initialized with threshold: %.2f", friction_threshold)

    def _calculate_cognitive_load(self, bio_data: BioSensorData, telemetry: SystemTelemetry) -> float:
        """
        [Internal] Calculate a normalized 'Cognitive Friction' score.
        
        Formula combines physiological stress and system friction.
        
        Args:
            bio_data (BioSensorData): User physiological state.
            telemetry (SystemTelemetry): System performance state.
            
        Returns:
            float: Normalized load score (0.0 to 1.0).
        """
        if not bio_data.is_valid():
            logger.warning("Invalid bio data received, defaulting to safe load estimate.")
            return 0.5

        # Weights for the control model
        w_physio = 0.6
        w_system = 0.4

        # Normalize physiological signals (Simple heuristic model)
        # High saccade + High EMG + Dilated pupils usually = High cognitive load
        physio_load = (bio_data.emg_stress_level / 100.0 * 0.5) + \
                      (bio_data.eye_saccade_rate / 10.0 * 0.3) + \
                      ((bio_data.pupil_dilation - 4.0) / 4.0 * 0.2)
        
        # Clamp physio load
        physio_load = max(0.0, min(1.0, physio_load))

        # System friction: Latency > 200ms + High Error Rate increases load
        latency_factor = min(telemetry.latency_ms / 500.0, 1.0) # 500ms is considered high friction
        system_load = (latency_factor + telemetry.error_rate) / 2.0

        total_load = (physio_load * w_physio) + (system_load * w_system)
        
        logger.debug(f"Load Calc: Physio={physio_load:.2f}, System={system_load:.2f}, Total={total_load:.2f}")
        return total_load

    def _determine_state(self, load_score: float) -> CognitiveState:
        """
        [Helper] Map load score to discrete Cognitive State.
        """
        if load_score > self.friction_threshold:
            return CognitiveState.OVERLOAD
        elif load_score < (self.friction_threshold * 0.5):
            return CognitiveState.BORED
        return CognitiveState.FLOW

    def adapt_output_strategy(self, bio_data: BioSensorData, telemetry: SystemTelemetry) -> Modality:
        """
        [Core] Analyzes inputs and determines the optimal interaction modality.
        
        This is the main entry point for the feedback loop. It evaluates the
        user's cognitive state and switches modalities if necessary to maintain flow.
        
        Args:
            bio_data: Current sensor readings.
            telemetry: Current system performance.
            
        Returns:
            Modality: The recommended interaction modality.
        """
        try:
            load_score = self._calculate_cognitive_load(bio_data, telemetry)
            state = self._determine_state(load_score)
            
            logger.info(f"Current Cognitive State: {state.name} (Load: {load_score:.2f})")

            new_modality = self.current_modality

            if state == CognitiveState.OVERLOAD:
                logger.warning("Cognitive Overload detected! Simplifying environment.")
                if self.current_modality == Modality.TEXT_HIGH_DENSITY:
                    new_modality = Modality.TEXT_LOW_DENSITY
                elif self.current_modality == Modality.TEXT_LOW_DENSITY:
                    # Switch modality entirely to spatial/visual to reduce linguistic processing
                    new_modality = Modality.SPATIAL_VISUALIZATION
                else:
                    # Extreme overload: restrict information to ambient cues
                    new_modality = Modality.AMBIENT_FEEDBACK

            elif state == CognitiveState.BORED:
                logger.info("User underloaded. Increasing complexity.")
                if self.current_modality == Modality.AMBIENT_FEEDBACK:
                    new_modality = Modality.SPATIAL_VISUALIZATION
                else:
                    new_modality = Modality.TEXT_HIGH_DENSITY
            
            else:
                # In Flow state, maintain current strategy unless close to boundaries
                pass

            if new_modality != self.current_modality:
                logger.info(f"Modality Switch: {self.current_modality.name} -> {new_modality.name}")
                self._record_transition(self.current_modality, new_modality, load_score)
                self.current_modality = new_modality

            return self.current_modality

        except Exception as e:
            logger.error(f"Critical error in adaptation loop: {e}")
            # Fallback to safest mode
            return Modality.AMBIENT_FEEDBACK

    def _record_transition(self, old: Modality, new: Modality, load: float) -> None:
        """
        [Helper] Records the state transition for later analysis.
        """
        entry = {
            "timestamp": time.time(),
            "from": old.name,
            "to": new.name,
            "trigger_load": load
        }
        self.history.append(entry)

    def get_flow_recommendation(self) -> str:
        """
        [Core] Generates a human-readable suggestion based on the current state.
        
        Returns:
            str: A descriptive recommendation for the UI layer.
        """
        recommendations = {
            Modality.TEXT_HIGH_DENSITY: "Detailed analytical mode. High information density.",
            Modality.TEXT_LOW_DENSITY: "Summary mode. Key points only.",
            Modality.SPATIAL_VISUALIZATION: "Visual mode. Using 3D space for context.",
            Modality.AMBIENT_FEEDBACK: "Focus mode. Minimal UI, using light/color cues."
        }
        return recommendations.get(self.current_modality, "Unknown state")


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize System
    controller = CognitiveController(friction_threshold=0.7)

    # 2. Simulate Sensor Input (Scenario: High Stress)
    # User has high muscle tension, rapid eye movement, and system is slightly lagging
    stressed_bio = BioSensorData(pupil_dilation=6.5, eye_saccade_rate=8.0, emg_stress_level=85.0)
    laggy_telemetry = SystemTelemetry(latency_ms=250, error_rate=0.05, complexity_score=0.9)

    # 3. Run Adaptation Cycle
    print("--- Cycle 1: High Stress ---")
    current_mode = controller.adapt_output_strategy(stressed_bio, laggy_telemetry)
    print(f"System Mode: {current_mode.name}")
    print(f"UI Guidance: {controller.get_flow_recommendation()}")

    # 4. Simulate Recovery (Scenario: Return to Flow)
    print("\n--- Cycle 2: Recovery ---")
    calm_bio = BioSensorData(pupil_dilation=4.2, eye_saccade_rate=2.0, emg_stress_level=20.0)
    good_telemetry = SystemTelemetry(latency_ms=50, error_rate=0.0, complexity_score=0.5)
    
    current_mode = controller.adapt_output_strategy(calm_bio, good_telemetry)
    print(f"System Mode: {current_mode.name}")
    print(f"UI Guidance: {controller.get_flow_recommendation()}")