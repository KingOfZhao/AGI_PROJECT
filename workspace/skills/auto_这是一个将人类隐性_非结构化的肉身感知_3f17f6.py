"""
Module: implicit_knowledge_digitizer.py

This module provides a system engineering approach to convert human implicit, 
unstructured somatic perceptions (such as tactile feel, auditory feedback, 
and muscle micromovements) into machine-readable, quantifiable parameters.

It establishes a 'Sensory-Semantic Mapping', translating vague descriptions 
or biological signals into precise physical execution parameters (e.g., torque, speed).
"""

import logging
import json
import re
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerceptionDomain(Enum):
    """Enumeration of sensory domains for implicit knowledge."""
    TACTILE = "tactile"
    AUDITORY = "auditory"
    MUSCULAR = "muscular"

@dataclass
class ExecutionParameter:
    """Data structure for machine execution parameters."""
    parameter_name: str
    value: float
    unit: str
    confidence_score: float  # 0.0 to 1.0

@dataclass
class SensoryInput:
    """Data structure for raw or semantic sensory input."""
    domain: PerceptionDomain
    raw_data: Optional[Dict[str, Any]] = None  # e.g., {"emg_voltage": 0.05}
    semantic_description: Optional[str] = None # e.g., "slightly tight"

class PerceptionNormalizationError(Exception):
    """Custom exception for errors during perception normalization."""
    pass

class ImplicitKnowledgeDigitizer:
    """
    A system to transform implicit human somatic perceptions into quantifiable 
    machine parameters.
    
    This class handles the mapping of fuzzy human inputs (semantic descriptions 
    or raw bio-signals) to precise control values using calibration curves and 
    semantic dictionaries.
    
    Attributes:
        calibration_params (Dict): Stores calibration constants for different domains.
        semantic_map (Dict): Maps linguistic descriptors to numerical factors.
    
    Example:
        >>> digitizer = ImplicitKnowledgeDigitizer()
        >>> # Semantic mapping example
        >>> semantic_input = SensoryInput(
        ...     domain=PerceptionDomain.TACTILE, 
        ...     semantic_description="moderately heavy resistance"
        ... )
        >>> params = digitizer.process_perception(semantic_input)
        >>> print(params['torque'])
        
        >>> # Bio-signal mapping example
        >>> bio_input = SensoryInput(
        ...     domain=PerceptionDomain.MUSCULAR,
        ...     raw_data={"emg_amplitude": 0.85, "duration_ms": 200}
        ... )
        >>> params = digitizer.process_perception(bio_input)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the digitizer with calibration parameters and semantic mappings.
        
        Args:
            config_path (Optional[str]): Path to a JSON config file. If None, 
                                         uses default internal parameters.
        """
        self.calibration_params = self._load_default_calibration()
        self.semantic_map = self._load_default_semantics()
        
        if config_path:
            try:
                self._load_config(config_path)
                logger.info(f"Configuration loaded from {config_path}")
            except FileNotFoundError:
                logger.warning(f"Config file not found at {config_path}. Using defaults.")

        logger.info("ImplicitKnowledgeDigitizer initialized.")

    def _load_default_calibration(self) -> Dict[str, Any]:
        """Generates default calibration parameters for domains."""
        return {
            "tactile": {
                "base_force_N": 10.0,
                "sensitivity": 1.2,
                "max_limit_N": 100.0
            },
            "muscular": {
                "emg_max_volt": 1.5,
                "torque_coefficient": 50.0, # Nm per volt
                "max_limit_Nm": 150.0
            },
            "auditory": {
                "freq_reference_hz": 1000,
                "amplitude_threshold_db": 20
            }
        }

    def _load_default_semantics(self) -> Dict[str, Dict[str, float]]:
        """Generates default semantic mapping dictionary."""
        return {
            "intensity_modifiers": {
                "slightly": 0.3,
                "a bit": 0.3,
                "somewhat": 0.5,
                "moderately": 0.6,
                "medium": 0.7,
                "heavy": 0.9,
                "very": 0.9,
                "extremely": 1.0,
                "tight": 0.8,
                "loose": 0.2
            },
            "action_targets": {
                "resistance": "force",
                "tight": "torque",
                "fast": "speed"
            }
        }

    def _load_config(self, path: str) -> None:
        """Loads configuration from a JSON file."""
        with open(path, 'r') as f:
            config = json.load(f)
            if "calibration" in config:
                self.calibration_params.update(config["calibration"])
            if "semantics" in config:
                self.semantic_map.update(config["semantics"])

    def _parse_semantic_description(self, description: str) -> Tuple[float, str]:
        """
        Internal helper to parse text descriptions into intensity values and target types.
        
        Args:
            description (str): The human language description.
            
        Returns:
            Tuple[float, str]: A tuple containing the calculated intensity factor (0.0-1.0)
                               and the inferred target parameter type.
        """
        description = description.lower().strip()
        intensity = 0.5 # Default neutral intensity
        target_type = "general" # Default target
        
        # Extract intensity modifiers
        modifiers_found = []
        for word, factor in self.semantic_map["intensity_modifiers"].items():
            if word in description:
                modifiers_found.append(factor)
        
        if modifiers_found:
            # Aggregate modifiers (e.g., "very heavy" -> average or max)
            intensity = sum(modifiers_found) / len(modifiers_found)
        
        # Simple keyword detection for target
        if "tight" in description or "torque" in description:
            target_type = "torque"
        elif "resistance" in description or "force" in description:
            target_type = "force"
        elif "fast" in description or "speed" in description:
            target_type = "speed"
            
        logger.debug(f"Parsed '{description}' -> Intensity: {intensity:.2f}, Target: {target_type}")
        return intensity, target_type

    def map_semantic_to_params(self, input_data: SensoryInput) -> Dict[str, ExecutionParameter]:
        """
        Core Function 1: Maps semantic (textual) descriptions to physical parameters.
        
        This function bridges the gap between "feeling" and "doing" by translating
        adjectives into specific machine values based on calibrated baselines.
        
        Args:
            input_data (SensoryInput): Input containing a semantic description.
            
        Returns:
            Dict[str, ExecutionParameter]: A dictionary of calculated parameters.
            
        Raises:
            PerceptionNormalizationError: If the description is empty or invalid.
        """
        if not input_data.semantic_description:
            raise PerceptionNormalizationError("Semantic description is missing.")

        intensity, target = self._parse_semantic_description(input_data.semantic_description)
        
        results = {}
        
        if input_data.domain == PerceptionDomain.TACTILE:
            config = self.calibration_params["tactile"]
            base = config["base_force_N"]
            max_val = config["max_limit_N"]
            
            # Calculate specific value
            calculated_value = base * intensity * config["sensitivity"]
            # Boundary check
            final_value = min(max_val, max(0.0, calculated_value))
            
            param = ExecutionParameter(
                parameter_name="grip_force",
                value=final_value,
                unit="newtons",
                confidence_score=0.75 if intensity > 0.1 else 0.4
            )
            results["force"] = param
            
        elif input_data.domain == PerceptionDomain.MUSCULAR:
             # Semantic input for muscular usually implies desired effort
             config = self.calibration_params["muscular"]
             calculated_value = intensity * config["torque_coefficient"]
             
             param = ExecutionParameter(
                parameter_name="target_torque",
                value=calculated_value,
                unit="Nm",
                confidence_score=0.65
            )
             results["torque"] = param
             
        logger.info(f"Mapped semantic '{input_data.semantic_description}' to {len(results)} params.")
        return results

    def map_biosignal_to_params(self, input_data: SensoryInput) -> Dict[str, ExecutionParameter]:
        """
        Core Function 2: Maps raw bio-signals (EMG, EEG, etc.) to physical parameters.
        
        This function processes raw sensor data representing muscle tension or 
        micro-movements and converts them into executable commands.
        
        Args:
            input_data (SensoryInput): Input containing raw_data dictionary.
            
        Returns:
            Dict[str, ExecutionParameter]: A dictionary of calculated parameters.
            
        Raises:
            ValueError: If required raw data fields are missing.
        """
        if not input_data.raw_data:
            raise ValueError("Raw bio-signal data is missing.")

        results = {}
        
        if input_data.domain == PerceptionDomain.MUSCULAR:
            # Expecting EMG data
            emg_amp = input_data.raw_data.get("emg_amplitude")
            duration = input_data.raw_data.get("duration_ms", 100)
            
            if emg_amp is None:
                raise ValueError("Missing 'emg_amplitude' in raw_data")

            # Data Validation
            if not (0 <= emg_amp <= 5.0): # Assume 5V max safe range
                logger.warning(f"EMG amplitude {emg_amp} out of expected range [0, 5.0]. Clamping.")
                emg_amp = max(0, min(5.0, emg_amp))

            config = self.calibration_params["muscular"]
            
            # Signal Processing Logic: RMS-like approximation to Torque
            # Torque = (Amplitude / Max_Volt) * Torque_Coeff * Time_Factor
            normalized_amp = emg_amp / config["emg_max_volt"]
            time_factor = min(1.0, duration / 500.0) # Scales up to 500ms
            
            torque_val = normalized_amp * config["torque_coefficient"] * (0.5 + 0.5 * time_factor)
            
            # Boundary Check
            torque_val = min(config["max_limit_Nm"], max(0.0, torque_val))
            
            param = ExecutionParameter(
                parameter_name="actuator_torque",
                value=round(torque_val, 3),
                unit="Nm",
                confidence_score=0.90 if normalized_amp > 0.1 else 0.50
            )
            results["actuation"] = param

        elif input_data.domain == PerceptionDomain.AUDITORY:
            # Example: Mapping audio pitch/freq to speed
            freq = input_data.raw_data.get("frequency_hz", 0)
            amp_db = input_data.raw_data.get("amplitude_db", 0)
            
            config = self.calibration_params["auditory"]
            
            # Simple logic: Higher pitch = Faster speed
            speed_factor = freq / config["freq_reference_hz"]
            speed_value = speed_factor * 100 # Base speed units
            
            param = ExecutionParameter(
                parameter_name="process_speed",
                value=round(speed_value, 2),
                unit="rpm",
                confidence_score=0.80
            )
            results["speed"] = param

        logger.info(f"Mapped bio-signal to {len(results)} params.")
        return results

    def process_perception(self, input_data: SensoryInput) -> Dict[str, ExecutionParameter]:
        """
        Main pipeline method to process any type of sensory input.
        
        It automatically routes the data to the correct mapping function
        (semantic or bio-signal).
        """
        try:
            if input_data.semantic_description:
                return self.map_semantic_to_params(input_data)
            elif input_data.raw_data:
                return self.map_biosignal_to_params(input_data)
            else:
                raise PerceptionNormalizationError("Input must contain either semantic description or raw data.")
        except Exception as e:
            logger.error(f"Error processing perception: {e}")
            raise

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the system
    digitizer = ImplicitKnowledgeDigitizer()
    
    print("-" * 50)
    print("Scenario 1: Expert Craftsman Description (Semantic)")
    print("-" * 50)
    
    # Input: "Tighten it until it feels slightly tight"
    # This represents the 'implicit' knowledge
    semantic_input = SensoryInput(
        domain=PerceptionDomain.TACTILE,
        semantic_description="slightly tight"
    )
    
    try:
        params = digitizer.process_perception(semantic_input)
        for key, param in params.items():
            print(f"Output Param: {param.parameter_name}")
            print(f"Value: {param.value} {param.unit}")
            print(f"Confidence: {param.confidence_score}")
            print(f"Raw Data: {asdict(param)}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "-" * 50)
    print("Scenario 2: Wearable Sensor Input (Bio-Signal)")
    print("-" * 50)
    
    # Input: EMG sensor detects muscle tension
    # This represents the 'somatic' data
    bio_input = SensoryInput(
        domain=PerceptionDomain.MUSCULAR,
        raw_data={"emg_amplitude": 1.2, "duration_ms": 300}
    )
    
    try:
        params = digitizer.process_perception(bio_input)
        for key, param in params.items():
            print(f"Output Param: {param.parameter_name}")
            print(f"Value: {param.value} {param.unit}")
            print(f"Confidence: {param.confidence_score}")
    except Exception as e:
        print(f"Error: {e}")