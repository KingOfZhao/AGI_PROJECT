"""
Module: implicit_knowledge_encoder.py

This module is designed to bridge the gap between human "tacit knowledge" (implicit knowledge)
and machine-executable parameters in an industrial AGI system. It specifically addresses the
challenge of translating vague, sensory-based linguistic descriptions (e.g., "the machine
sounds muffled") into precise physical feature vectors suitable for signal processing and
machine learning models.

Key Features:
1.  Fuzzy Logic Mapping: Converts natural language descriptors to numerical ranges.
2.  Signal Feature Extraction: Simulates extraction of physical features from sensor data.
3.  Knowledge Encoding: Synthesizes AGI-executable parameters from fuzzy rules and sensor inputs.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ImplicitKnowledgeEncoder")

# --- Data Structures ---

@dataclass
class PhysicalFeatures:
    """
    Represents the extracted physical features from sensor data.
    
    Attributes:
        dominant_freq (float): The dominant frequency detected (Hz).
        amplitude_db (float): The signal amplitude in decibels (dB).
        harmonics_ratio (float): The ratio of harmonic energy to fundamental energy.
        temperature (float): Operating temperature (Celsius).
    """
    dominant_freq: float
    amplitude_db: float
    harmonics_ratio: float
    temperature: float = 25.0

@dataclass
class AGIExecutableParameter:
    """
    Represents the final encoded parameter set for the AGI system.
    
    Attributes:
        feature_vector (List[float]): Normalized vector for neural network input.
        rule_confidence (float): Confidence score of the implicit rule application.
        anomaly_score (float): Calculated deviation from the "healthy" baseline.
        description (str): Human-readable interpretation of the encoding.
    """
    feature_vector: List[float]
    rule_confidence: float
    anomaly_score: float
    description: str

# --- Knowledge Base (Simulated) ---

# Defines the "Healthy" baseline for a specific industrial component (e.g., Bearing Type A)
HEALTHY_BASELINE = {
    "dominant_freq_range": (950, 1050),  # Hz
    "amplitude_db_range": (-20, -10),
    "harmonics_ratio_max": 0.2
}

# Mapping natural language descriptors to fuzzy modifications of physical constraints
# Positive values increase the threshold, negative values decrease/lower it.
LINGUISTIC_MODIFIERS = {
    "muffled": {"freq_shift": -300, "amp_shift": -3, "desc": "Frequency shifted low, amplitude drop"},
    "squealing": {"freq_shift": 800, "amp_shift": 5, "desc": "High frequency harmonic resonance"},
    "grinding": {"freq_shift": 0, "amp_shift": 2, "desc": "Broadband noise increase"},
    "hot": {"temp_shift": 30, "amp_shift": 0, "desc": "Thermal expansion effects"}
}

class ImplicitKnowledgeEncodingError(Exception):
    """Custom exception for errors during the knowledge encoding process."""
    pass

# --- Core Functions ---

def extract_physical_features(raw_sensor_data: Dict[str, Any]) -> PhysicalFeatures:
    """
    Simulates the signal processing layer. In a real scenario, this would interface
    with DAQ (Data Acquisition) hardware. Here it validates and extracts features
    from raw input dictionaries.
    
    Args:
        raw_sensor_data (Dict[str, Any]): Dictionary containing raw readings.
            Expected keys: 'waveform_data', 'temp_c'.
            
    Returns:
        PhysicalFeatures: A structured object containing extracted physical parameters.
        
    Raises:
        ValueError: If input data is missing or contains invalid types.
    """
    logger.info("Starting physical feature extraction...")
    
    # Data Validation
    if not isinstance(raw_sensor_data, dict):
        raise ValueError("Input must be a dictionary.")
    
    if 'waveform_data' not in raw_sensor_data:
        raise ImplicitKnowledgeEncodingError("Missing 'waveform_data' in sensor input.")
    
    try:
        # Simulate FFT (Fast Fourier Transform) extraction
        # In reality, this processes time-series arrays. Here we simulate the result.
        mock_wave = raw_sensor_data['waveform_data']
        if not isinstance(mock_wave, (list, tuple)):
             raise TypeError("Waveform data must be a list or tuple of numbers.")
        
        # Dummy extraction logic for simulation
        # Assuming the mean of the first half represents some DC offset/Freq component
        extracted_freq = 1000.0 + (sum(mock_wave[:5]) / 5) if len(mock_wave) > 5 else 1000.0
        extracted_amp = -15.0 + (sum(mock_wave) / len(mock_wave))
        extracted_harmonics = 0.1
        temp = raw_sensor_data.get('temp_c', 25.0)

        # Boundary Checks
        if extracted_freq < 0:
            logger.warning("Negative frequency detected, clamping to 0.")
            extracted_freq = 0.0
            
        logger.info(f"Extraction complete: Freq={extracted_freq}Hz, Amp={extracted_amp}dB")
        
        return PhysicalFeatures(
            dominant_freq=extracted_freq,
            amplitude_db=extracted_amp,
            harmonics_ratio=extracted_harmonics,
            temperature=temp
        )
        
    except Exception as e:
        logger.error(f"Failed to extract features: {e}")
        raise ImplicitKnowledgeEncodingError(f"Feature extraction failed: {e}")

def encode_tacit_knowledge(
    linguistic_descriptor: str, 
    physical_features: PhysicalFeatures, 
    baseline: Dict = HEALTHY_BASELINE
) -> AGIExecutableParameter:
    """
    The core cognitive mapping function. It aligns the "fuzzy" human description
    with the "crisp" physical features to generate an AGI parameter set.
    
    This mimics the process of an expert saying "It sounds muffled," and the system
    checking if the frequency has indeed dropped relative to the baseline.
    
    Args:
        linguistic_descriptor (str): A keyword like 'muffled', 'squealing'.
        physical_features (PhysicalFeatures): The objective sensor data.
        baseline (Dict): The reference "healthy" state parameters.
        
    Returns:
        AGIExecutableParameter: The encoded object containing the anomaly score and vector.
        
    Raises:
        KeyError: If the linguistic descriptor is unknown.
    """
    logger.info(f"Encoding tacit knowledge for descriptor: '{linguistic_descriptor}'")
    
    # Normalize input
    descriptor_key = linguistic_descriptor.lower().strip()
    
    if descriptor_key not in LINGUISTIC_MODIFIERS:
        logger.warning(f"Unknown descriptor '{descriptor_key}'. Defaulting to generic analysis.")
        modifier = {"freq_shift": 0, "amp_shift": 0, "desc": "Unknown"}
    else:
        modifier = LINGUISTIC_MODIFIERS[descriptor_key]
    
    # Calculate Expected vs Actual
    # 1. Frequency Analysis
    expected_freq = baseline['dominant_freq_range'][0] + modifier['freq_shift']
    freq_deviation = physical_features.dominant_freq - expected_freq
    
    # 2. Amplitude Analysis
    expected_amp = baseline['amplitude_db_range'][0] + modifier['amp_shift']
    amp_deviation = physical_features.amplitude_db - expected_amp
    
    # 3. Calculate Anomaly Score (Euclidean distance in feature space)
    # Normalized score calculation (simplified)
    anomaly_score = (abs(freq_deviation) / 100 + abs(amp_deviation) / 5) / 2.0
    
    # Determine confidence based on how well the data matches the description
    # If deviation is low, the description matches the reality well
    if anomaly_score < 0.5:
        confidence = 0.9
        status = "CONFIRMED"
    elif anomaly_score < 1.5:
        confidence = 0.6
        status = "PARTIAL_MATCH"
    else:
        confidence = 0.2
        status = "MISMATCH"
        
    # Construct Feature Vector for AGI (normalized 0-1 range for Neural Net input)
    # Vector: [Freq_Norm, Amp_Norm, Harm_Norm, Anomaly_Score]
    feature_vector = [
        min(max(physical_features.dominant_freq / 2000.0, 0), 1),
        min(max((physical_features.amplitude_db + 50) / 50.0, 0), 1), # shifting -50..0 to 0..1
        physical_features.harmonics_ratio,
        anomaly_score
    ]
    
    description = (
        f"Status: {status}. Description '{descriptor_key}' implies "
        f"{modifier['desc']}. Actual Freq: {physical_features.dominant_freq}Hz."
    )
    
    return AGIExecutableParameter(
        feature_vector=feature_vector,
        rule_confidence=confidence,
        anomaly_score=anomaly_score,
        description=description
    )

# --- Helper Functions ---

def validate_sensor_input(data: Dict[str, Any]) -> bool:
    """
    Validates the structure and content of the raw sensor data.
    
    Args:
        data (Dict[str, Any]): Raw input data.
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If validation fails.
    """
    if 'waveform_data' not in data:
        raise ValueError("Missing key 'waveform_data'")
    if not isinstance(data['waveform_data'], list):
        raise ValueError("'waveform_data' must be a list")
    if len(data['waveform_data']) == 0:
        raise ValueError("'waveform_data' cannot be empty")
    
    # Check for numeric types
    for i, val in enumerate(data['waveform_data']):
        if not isinstance(val, (int, float)):
            raise ValueError(f"Value at index {i} is not numeric.")
            
    return True

# --- Main Execution / Example ---

if __name__ == "__main__":
    # Example Usage
    
    # Scenario: An old craftsman says "The bearing sounds muffled."
    # We need to translate this "muffled" concept into a machine parameter.
    
    # 1. Simulate Sensor Data (e.g., from a vibration sensor)
    # This data represents a bearing that is indeed running at a lower frequency (worn out)
    sensor_data = {
        "waveform_data": [-10, -12, -11, -9, -10], # Simulating lower amplitude/energy
        "temp_c": 45.0
    }
    
    print("-" * 60)
    print("AGI Tacit Knowledge Encoder System")
    print("-" * 60)
    
    try:
        # Step 1: Validate Input
        validate_sensor_input(sensor_data)
        
        # Step 2: Extract Physical Features (Signal Processing)
        features = extract_physical_features(sensor_data)
        
        # Step 3: Encode Tacit Knowledge (The "Muffled" description)
        # Passing "muffled" maps to the linguistic modifier for low freq
        agi_params = encode_tacit_knowledge("muffled", features)
        
        # Output the results
        print(f"\nInput Description: 'muffled'")
        print(f"Detected Physical Features: {features}")
        print(f"Encoded AGI Parameters: {agi_params}")
        
        print("\nFeature Vector for ML Model:")
        print(agi_params.feature_vector)
        
        print("\nDiagnostics:")
        print(agi_params.description)
        
    except (ValueError, ImplicitKnowledgeEncodingError) as e:
        logger.error(f"System halted due to error: {e}")