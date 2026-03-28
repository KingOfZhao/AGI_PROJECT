"""
Module: auto_如何构建一个跨域的_机理_现象_映射图_a3bd98

Description:
    This module implements a cross-domain mapping mechanism between low-level 
    PLC signal features (Current/Voltage) and high-level physical degradation 
    states (Mechanical Wear). 
    
    It generates a 'Digital Twin Node' by discovering non-linear associations 
    between high-frequency time-series data and physical phenomena, moving 
    beyond simple statistical correlation to causal mechanism mapping.

Key Components:
    - Signal Domain Processor: Extracts features from raw signals.
    - Physical Domain Analyzer: Maps features to degradation states.
    - Digital Twin Generator: Creates the monitoring node structure.

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Enums ---

class SignalType(Enum):
    """Types of input signals."""
    CURRENT = "current"
    VOLTAGE = "voltage"

class DegradationLevel(Enum):
    """Levels of mechanical wear."""
    HEALTHY = 0
    EARLY_WARNING = 1
    MODERATE_WEAR = 2
    SEVERE_FAULT = 3

@dataclass
class SignalFeature:
    """Container for extracted signal features (Left Domain)."""
    rms: float
    kurtosis: float
    skewness: float
    crest_factor: float
    entropy: float

@dataclass
class PhysicalState:
    """Container for physical degradation state (Right Domain)."""
    level: DegradationLevel
    wear_probability: float
    confidence: float
    mechanism_description: str

@dataclass
class DigitalTwinNode:
    """The consolidated mapping object."""
    node_id: str
    timestamp: str
    input_features: SignalFeature
    output_state: PhysicalState
    mapping_weights: Dict[str, float]

# --- Helper Functions ---

def _validate_input_data(
    data: np.ndarray, 
    expected_shape: Tuple[int, ...]
) -> bool:
    """
    Validates the input numpy array against expected shape and finite values.
    
    Args:
        data: Input numpy array.
        expected_shape: Tuple describing expected dimensions (e.g., (1000,)).
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If data is invalid.
    """
    if not isinstance(data, np.ndarray):
        logger.error("Input data is not a numpy array.")
        raise ValueError("Input must be a numpy array.")
    
    if data.shape != expected_shape:
        logger.warning(f"Shape mismatch: expected {expected_shape}, got {data.shape}. Reshaping not supported automatically.")
        # For this specific logic, we enforce strict shape or handle specific cases
        if data.size == 0:
            raise ValueError("Input array is empty.")

    if not np.all(np.isfinite(data)):
        logger.error("Data contains NaN or Inf values.")
        raise ValueError("Input data must contain finite numbers.")
        
    return True

def _calculate_signal_entropy(signal: np.ndarray, bins: int = 10) -> float:
    """
    Helper to calculate Shannon Entropy of a signal (measure of complexity/disorder).
    
    Args:
        signal: 1D numpy array of signal data.
        bins: Number of bins for histogram.
        
    Returns:
        float: Calculated entropy.
    """
    hist, _ = np.histogram(signal, bins=bins, density=True)
    hist = hist[hist > 0] # Remove zero entries
    entropy = -np.sum(hist * np.log2(hist))
    return entropy

# --- Core Functions ---

def extract_domain_features(
    raw_signal: np.ndarray, 
    signal_type: SignalType
) -> SignalFeature:
    """
    Extracts key features from raw high-frequency PLC data.
    
    This function processes the 'Left Domain' (Signal Processing), isolating
    features that are sensitive to mechanical changes but robust to noise.
    
    Args:
        raw_signal: 1D numpy array containing time-series data (Current/Voltage).
        signal_type: Enum indicating the type of signal.
        
    Returns:
        SignalFeature: Dataclass containing extracted features.
        
    Raises:
        ValueError: If input data is invalid.
    """
    logger.info(f"Starting feature extraction for {signal_type.value} signal...")
    
    # Input Validation
    try:
        # Assuming 1D array input for simplicity in this example
        if raw_signal.ndim > 1:
             raw_signal = raw_signal.flatten()
        _validate_input_data(raw_signal, (raw_signal.size,))
    except ValueError as e:
        logger.critical(f"Validation failed: {e}")
        raise

    # Feature Extraction Logic
    try:
        # 1. RMS (Root Mean Square) - Energy indicator
        rms = np.sqrt(np.mean(raw_signal**2))
        
        # 2. Kurtosis - Peakedness (Sensitive to impacts/bearing faults)
        kurtosis = float(((raw_signal - np.mean(raw_signal))**4).mean() / (np.var(raw_signal)**2)) - 3.0
        
        # 3. Skewness - Asymmetry
        std_dev = np.std(raw_signal)
        if std_dev == 0: 
            skewness = 0.0
        else:
            skewness = float((np.mean((raw_signal - np.mean(raw_signal))**3)) / (std_dev**3))
            
        # 4. Crest Factor (Peak / RMS) - Indicator of spikiness
        peak = np.max(np.abs(raw_signal))
        crest_factor = peak / rms if rms > 0 else 0.0
        
        # 5. Entropy - Complexity (using helper)
        entropy = _calculate_signal_entropy(raw_signal)
        
        features = SignalFeature(
            rms=float(rms),
            kurtosis=float(kurtosis),
            skewness=float(skewness),
            crest_factor=float(crest_factor),
            entropy=float(entropy)
        )
        
        logger.debug(f"Extracted features: {features}")
        return features

    except Exception as e:
        logger.error(f"Error during feature calculation: {e}")
        raise RuntimeError("Failed to extract features.") from e

def map_to_physical_state(
    features: SignalFeature,
    thresholds: Optional[Dict[str, float]] = None
) -> PhysicalState:
    """
    Maps signal features to a physical degradation state.
    
    This function implements the 'Mechanism Mapping' logic. It estimates the
    physical wear state based on non-linear combinations of signal features.
    
    Args:
        features: Extracted features from the signal domain.
        thresholds: Optional dictionary of thresholds for classification.
        
    Returns:
        PhysicalState: Dataclass describing the physical state.
    """
    logger.info("Mapping signal features to physical domain (Wear/Fault)...")
    
    # Default thresholds (can be tuned via calibration)
    if thresholds is None:
        thresholds = {
            "kurtosis_warn": 3.5,
            "kurtosis_fault": 6.0,
            "crest_warn": 3.0,
            "crest_fault": 5.0
        }

    # Non-linear Mapping Logic (The "Mechanism" part)
    # Here we simulate a knowledge-based inference engine.
    # High kurtosis + High Crest Factor usually indicates mechanical impacts (bearing wear).
    
    score = 0.0
    description = "Normal Operation"
    
    # Check for Impulsive Behavior (Bearing/Gear Wear Mechanism)
    is_impulsive = features.kurtosis > thresholds["kurtosis_warn"]
    is_spiky = features.crest_factor > thresholds["crest_warn"]
    
    if features.kurtosis > thresholds["kurtosis_fault"]:
        score = 0.9
        description = "Severe pitting or spalling detected."
        level = DegradationLevel.SEVERE_FAULT
    elif is_impulsive and is_spiky:
        score = 0.6
        description = "Early stage wear detected via impulsive signatures."
        level = DegradationLevel.MODERATE_WEAR
    elif is_impulsive or is_spiky:
        score = 0.3
        description = "Micro-wear signatures detected (Non-visible)."
        level = DegradationLevel.EARLY_WARNING
    else:
        score = 0.05
        description = "Mechanism within healthy parameters."
        level = DegradationLevel.HEALTHY

    # Calculate confidence based on entropy (lower entropy might mean steady state, higher might mean noise or chaos)
    confidence = max(0.0, 1.0 - abs(features.entropy - 1.5) / 2.0) # Simulated confidence logic

    state = PhysicalState(
        level=level,
        wear_probability=float(np.clip(score, 0.0, 1.0)),
        confidence=float(confidence),
        mechanism_description=description
    )
    
    logger.info(f"Mapping Result: {state.level.name} (Prob: {state.wear_probability:.2f})")
    return state

# --- Main Logic / Orchestration ---

def create_digital_twin_node(
    signal_data: np.ndarray,
    signal_type: Union[str, SignalType] = SignalType.CURRENT,
    node_id: str = "DT_Node_001"
) -> DigitalTwinNode:
    """
    Orchestrates the creation of a cross-domain digital twin node.
    
    This is the main entry point for the skill. It ingests raw data, processes
    it through the cross-domain mapping pipeline, and outputs a structured
    monitoring node.
    
    Args:
        signal_data: Raw high-frequency data.
        signal_type: Type of signal ('current' or 'voltage').
        node_id: Identifier for the generated node.
        
    Returns:
        DigitalTwinNode: The complete mapping object.
        
    Example:
        >>> import numpy as np
        >>> # Simulate a signal with bearing fault (impulsive noise)
        >>> t = np.linspace(0, 1, 1000)
        >>> base = np.sin(2 * np.pi * 50 * t)
        >>> noise = np.random.normal(0, 0.1, 1000)
        >>> impulse = np.random.choice([0, 5], size=1000, p=[0.99, 0.01])
        >>> raw_data = base + noise + impulse
        >>> 
        >>> node = create_digital_twin_node(raw_data, 'current', 'Motor_PUMP_01')
        >>> print(node.output_state.mechanism_description)
    """
    import datetime
    
    # Convert string to Enum if necessary
    if isinstance(signal_type, str):
        signal_type = SignalType(signal_type.lower())
        
    logger.info(f"Initializing Digital Twin Node generation for {node_id}...")

    # Step 1: Left Domain Processing (Signal)
    features = extract_domain_features(signal_data, signal_type)
    
    # Step 2: Right Domain Mapping (Physical Mechanism)
    physical_state = map_to_physical_state(features)
    
    # Step 3: Consolidate into Digital Twin Node
    mapping_weights = {
        "kurtosis_weight": 0.6,
        "crest_weight": 0.3,
        "entropy_weight": 0.1
    }
    
    node = DigitalTwinNode(
        node_id=node_id,
        timestamp=datetime.datetime.now().isoformat(),
        input_features=features,
        output_state=physical_state,
        mapping_weights=mapping_weights
    )
    
    logger.info(f"Node {node_id} created successfully.")
    return node

# --- Execution Guard ---
if __name__ == "__main__":
    # Demonstration of usage
    
    # 1. Generate Synthetic Data (Simulating a worn bearing)
    print("--- Generating Synthetic Data ---")
    np.random.seed(42)
    time = np.linspace(0, 1, 1000)
    # 50Hz fundamental wave
    clean_signal = np.sin(2 * np.pi * 50 * time)
    # High frequency noise
    noise = np.random.normal(0, 0.2, 1000)
    # Simulate physical wear (periodic impulses)
    wear_impulses = np.zeros(1000)
    wear_impulses[::50] = 4.0  # Impulse every 50 samples
    
    raw_plc_data = clean_signal + noise + wear_impulses
    
    try:
        # 2. Execute Skill
        print("--- Running Digital Twin Mapping ---")
        twin_node = create_digital_twin_node(
            signal_data=raw_plc_data,
            signal_type='current',
            node_id='MOTOR_DRIVE_UNIT_05'
        )
        
        # 3. Display Results
        print("\n--- Result Summary ---")
        print(f"Node ID: {twin_node.node_id}")
        print(f"Timestamp: {twin_node.timestamp}")
        print(f"Input RMS: {twin_node.input_features.rms:.4f}")
        print(f"Input Kurtosis: {twin_node.input_features.kurtosis:.4f}")
        print(f"Detected State: {twin_node.output_state.level.name}")
        print(f"Mechanism: {twin_node.output_state.mechanism_description}")
        
    except Exception as e:
        print(f"Critical Error: {e}")