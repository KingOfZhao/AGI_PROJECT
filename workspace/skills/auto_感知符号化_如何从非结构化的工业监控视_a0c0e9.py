"""
Module: industrial_perception_symbolization
Description: This module implements the "Perception-to-Symbol" translation layer for AGI systems
             in industrial automation scenarios. It converts unstructured, continuous time-series
             data (simulating video/vibration signals) into discrete, cognitive atomic events
             (symbolic nodes) suitable for knowledge graph construction.

Domain: Industrial Automation / AGI Perception
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

# --- Configuration & Setup ---

# Setting up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialPerceptionSymbolizer")

class EventType(Enum):
    """Enumeration of discrete cognitive symbols representing atomic events."""
    NORMAL_OPERATION = "normal_state"
    SPATTER_BURST = "welding_spatter_burst"   # Welding specific: High-frequency light intensity variance
    THERMAL_ANOMALY = "thermal_runaway"       # Welding specific: Sustained high intensity
    VIBRATION_SHOCK = "cnc_shock_event"       # CNC specific: Sudden acceleration spike
    DRIFT_DETECTED = "equipment_drift"        # CNC specific: Slow deviation from baseline
    UNKNOWN = "raw_noise"

@dataclass
class TimeSeriesFrame:
    """Represents a single frame or snapshot of sensor data."""
    timestamp: float
    sensor_id: str
    signal_value: float
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class CognitiveSymbol:
    """Represents the discrete output symbol for AGI processing."""
    event_id: str
    event_type: EventType
    start_time: float
    end_time: float
    magnitude: float
    features: Dict[str, float] = field(default_factory=dict)
    context: str = "industrial_monitoring"

# --- Helper Functions ---

def _validate_input_data(data_stream: List[TimeSeriesFrame]) -> bool:
    """
    Validates the input data stream for integrity and chronological order.
    
    Args:
        data_stream: A list of TimeSeriesFrame objects.
        
    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if not data_stream:
        logger.error("Input data stream is empty.")
        raise ValueError("Input data stream cannot be empty.")
    
    # Check chronological order
    timestamps = [frame.timestamp for frame in data_stream]
    if timestamps != sorted(timestamps):
        logger.warning("Data stream is not strictly chronological. Sorting might be required.")
        # In a real system, we might auto-sort, but here we flag it for strict validation
    
    # Check for missing values (represented as NaN)
    for frame in data_stream:
        if np.isnan(frame.signal_value):
            raise ValueError(f"NaN value detected in sensor {frame.sensor_id} at {frame.timestamp}")
            
    logger.debug(f"Validated {len(data_stream)} frames successfully.")
    return True

def _calculate_derivative(signal: List[float]) -> List[float]:
    """
    Calculates the simple rate of change (velocity) of the signal.
    Helper function for feature extraction.
    """
    if len(signal) < 2:
        return [0.0]
    return [signal[i+1] - signal[i] for i in range(len(signal)-1)]

# --- Core Logic ---

class PerceptionSymbolizer:
    """
    Main class responsible for transforming continuous industrial signals into discrete symbols.
    Acts as the 'Eye' of the AGI system for numerical data.
    """

    def __init__(self, sensitivity: float = 0.5, window_size: int = 5):
        """
        Initializes the Symbolizer with specific thresholds.
        
        Args:
            sensitivity: Threshold multiplier for anomaly detection (0.0 to 1.0).
            window_size: Sliding window size for smoothing features.
        """
        if not 0.0 < sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")
        
        self.sensitivity = sensitivity
        self.window_size = window_size
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        logger.info(f"PerceptionSymbolizer initialized with sensitivity {sensitivity}")

    def calibrate_baseline(self, calibration_data: List[TimeSeriesFrame]) -> None:
        """
        Learns the 'normal' state of the equipment to detect deviations.
        Must be called before processing active streams.
        
        Args:
            calibration_data: Historical data representing normal operations.
        """
        _validate_input_data(calibration_data)
        
        # Group by sensor ID
        sensor_groups: Dict[str, List[float]] = {}
        for frame in calibration_data:
            if frame.sensor_id not in sensor_groups:
                sensor_groups[frame.sensor_id] = []
            sensor_groups[frame.sensor_id].append(frame.signal_value)
            
        for sensor_id, values in sensor_groups.items():
            avg = float(np.mean(values))
            std = float(np.std(values))
            self.baseline_stats[sensor_id] = {"mean": avg, "std": std}
            logger.info(f"Baseline calibrated for {sensor_id}: Mean={avg:.4f}, Std={std:.4f}")

    def extract_features(self, data_chunk: List[TimeSeriesFrame]) -> List[Dict]:
        """
        Core Function 1: Extracts statistical and temporal features from a window of data.
        Maps raw values to 'perceptual properties'.
        
        Args:
            data_chunk: A list of TimeSeriesFrame objects (usually a sliding window).
            
        Returns:
            A list of dictionaries containing extracted feature vectors.
        """
        if not data_chunk:
            return []

        features_list = []
        # In a real scenario, we handle different sensor types. 
        # Here we process based on the chunk provided.
        
        # Extract raw signal
        raw_values = [f.signal_value for f in data_chunk]
        
        # Feature Engineering
        mean_val = np.mean(raw_values)
        std_val = np.std(raw_values)
        max_val = np.max(raw_values)
        min_val = np.min(raw_values)
        energy = np.sum(np.square(raw_values))
        velocity = _calculate_derivative(raw_values)
        avg_velocity = np.mean(np.abs(velocity)) if velocity else 0.0

        # Aggregating metadata
        sensor_id = data_chunk[0].sensor_id
        start_time = data_chunk[0].timestamp
        end_time = data_chunk[-1].timestamp

        feature_vector = {
            "sensor_id": sensor_id,
            "start_time": start_time,
            "end_time": end_time,
            "mean": mean_val,
            "std": std_val,
            "range": max_val - min_val,
            "energy": energy,
            "instability": avg_velocity # Higher means spiky movement
        }
        
        features_list.append(feature_vector)
        return features_list

    def map_to_symbol(self, feature_vector: Dict) -> CognitiveSymbol:
        """
        Core Function 2: Maps continuous feature vectors to discrete CognitiveSymbols.
        This is the 'Symbolization' step.
        
        Args:
            feature_vector: A dictionary of extracted features.
            
        Returns:
            A CognitiveSymbol object representing the atomic event.
        """
        sensor_id = feature_vector["sensor_id"]
        stats = self.baseline_stats.get(sensor_id)
        
        if not stats:
            logger.warning(f"No baseline found for {sensor_id}, using generic thresholds.")
            stats = {"mean": 0.5, "std": 0.1} # Fallback

        # Dynamic Thresholding based on sensitivity
        # Lower sensitivity = higher threshold to trigger (less sensitive)
        threshold_sigma = 3.0 * (1.1 - self.sensitivity) 
        
        deviation = (feature_vector["mean"] - stats["mean"]) / (stats["std"] + 1e-6)
        instability = feature_vector["instability"]
        
        event_type = EventType.NORMAL_OPERATION
        magnitude = 0.0
        
        # Logic Layer: Heuristics for Symbol Mapping
        
        # Case 1: Welding Spatter (High Instability, High Energy)
        # This maps "visual noise" to a specific event node
        if instability > (0.5 * threshold_sigma) and feature_vector["energy"] > (stats["mean"] ** 2 * 10):
            event_type = EventType.SPATTER_BURST
            magnitude = instability
            
        # Case 2: CNC Shock / Abnormal Vibration (Sudden high deviation)
        elif abs(deviation) > threshold_sigma and instability > (0.2 * threshold_sigma):
            event_type = EventType.VIBRATION_SHOCK
            magnitude = abs(deviation)
            
        # Case 3: Drift (Sustained deviation but low instability)
        elif abs(deviation) > (threshold_sigma * 0.8) and instability < (0.1 * threshold_sigma):
            event_type = EventType.DRIFT_DETECTED
            magnitude = abs(deviation)
            
        # Case 4: Thermal Anomaly (Sustained high mean)
        elif feature_vector["mean"] > (stats["mean"] + threshold_sigma * stats["std"]):
            event_type = EventType.THERMAL_ANOMALY
            magnitude = feature_vector["mean"]

        # Construct the Symbol
        symbol = CognitiveSymbol(
            event_id=f"evt_{sensor_id}_{int(feature_vector['start_time']*1000)}",
            event_type=event_type,
            start_time=feature_vector["start_time"],
            end_time=feature_vector["end_time"],
            magnitude=round(magnitude, 4),
            features={
                "raw_mean": round(feature_vector["mean"], 4),
                "z_score": round(deviation, 4)
            }
        )
        
        if event_type != EventType.NORMAL_OPERATION:
            logger.info(f"Symbol Detected: {event_type.value} on {sensor_id} (Mag: {magnitude:.2f})")
        
        return symbol

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Generate Mock Data (Simulating Industrial Sensors)
    # Sensor A: Welding Camera (Intensity 0.0 to 1.0)
    # Sensor B: CNC Accelerometer (Vibration G-force)
    
    print("--- Initializing AGI Perception Module ---")
    
    # Calibration Phase (Normal Data)
    calibration_time = np.linspace(0, 10, 100)
    # Normal welding: slight fluctuation around 0.5
    normal_welding = [TimeSeriesFrame(t, "weld_cam_01", 0.5 + np.random.normal(0, 0.05)) for t in calibration_time]
    # Normal CNC: slight vibration around 0.1
    normal_cnc = [TimeSeriesFrame(t, "cnc_acc_01", 0.1 + np.random.normal(0, 0.02)) for t in calibration_time]
    
    calibration_data = normal_welding + normal_cnc
    
    # Initialize Symbolizer
    symbolizer = PerceptionSymbolizer(sensitivity=0.7, window_size=5)
    symbolizer.calibrate_baseline(calibration_data)
    
    # 2. Processing Live Stream (with Anomalies)
    live_time = np.linspace(11, 20, 50)
    live_stream = []
    
    # Injecting Anomalies
    for t in live_time:
        # Random normal data
        val_weld = 0.5 + np.random.normal(0, 0.05)
        val_cnc = 0.1 + np.random.normal(0, 0.02)
        
        # Inject Spatter burst at t=15
        if 14.9 < t < 15.1:
            val_weld = 0.9 + np.random.normal(0, 0.2) # High intensity noise
            
        # Inject CNC Shock at t=18
        if 17.9 < t < 18.1:
            val_cnc = 5.0 # Massive spike
            
        live_stream.append(TimeSeriesFrame(t, "weld_cam_01", val_weld))
        live_stream.append(TimeSeriesFrame(t, "cnc_acc_01", val_cnc))
    
    # 3. Run Perception Loop
    print("\n--- Starting Live Perception ---")
    
    # Simple sliding window processing
    window_buffer = []
    
    for frame in live_stream:
        window_buffer.append(frame)
        
        # Process when buffer is full
        if len(window_buffer) >= symbolizer.window_size:
            # Extract features
            features = symbolizer.extract_features(window_buffer)
            
            # Map to symbols
            for feat in features:
                symbol = symbolizer.map_to_symbol(feat)
                
                # Output only non-normal events for clarity
                if symbol.event_type != EventType.NORMAL_OPERATION:
                    print(f"-> ATOMIC EVENT: {symbol.event_type.value.upper()} | Time: {symbol.start_time} | Magnitude: {symbol.magnitude}")
            
            # Slide window (remove oldest element)
            window_buffer.pop(0)

    print("\n--- Perception Cycle Complete ---")