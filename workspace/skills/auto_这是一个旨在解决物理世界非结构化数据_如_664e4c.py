"""
Module: ontological_suture_protocol.py

This module implements the 'Ontological Suture' protocol, a high-level cognitive
interface designed to bridge the gap between the physical world's unstructured
data (vibrations, resistance, haptic feedback) and the digital world's discrete
symbolic logic.

It facilitates a bidirectional flow:
1. Input (Sensory Transduction): Converting continuous analog signals into discrete
   cognitive symbols (e.g., mapping vibration frequencies to 'UNSTABLE' or 'SAFE').
2. Output (Motor Actuation): Mapping symbolic decisions back into precise physical
   correction parameters.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import math
import random
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OntologicalSuture")

class SymbolicState(Enum):
    """Enumeration of discrete cognitive states derived from physical phenomena."""
    NULL = 0
    RESISTANCE_HIGH = 1
    VIBRATION_ANOMALY = 2
    THERMAL_WARNING = 3
    OPTIMAL_OPERATION = 4
    UNKNOWN_HAZARD = 99

class PhysicalSensoryInput:
    """
    Represents a standardized container for raw physical data.
    This acts as the 'sense organ' data structure.
    """
    def __init__(self, 
                 vibration_hz: float, 
                 resistance_newtons: float, 
                 temp_celsius: float, 
                 acoustic_db: float):
        self.vibration_hz = vibration_hz
        self.resistance_newtons = resistance_newtons
        self.temp_celsius = temp_celsius
        self.acoustic_db = acoustic_db

    def validate(self) -> bool:
        """Validates that sensor readings are within plausible physical bounds."""
        if not (0 <= self.vibration_hz <= 20000): raise ValueError("Vibration out of bounds")
        if not (0 <= self.resistance_newtons <= 10000): raise ValueError("Resistance out of bounds")
        if not (-273.15 <= self.temp_celsius <= 1000): raise ValueError("Temperature out of bounds")
        return True

class ActuationOutput:
    """
    Represents the physical parameters to be executed by the machine.
    This acts as the 'motor command' structure.
    """
    def __init__(self, 
                 torque_adjustment: float, 
                 speed_factor: float, 
                 coolant_flow_rate: float):
        self.torque_adjustment = torque_adjustment
        self.speed_factor = speed_factor
        self.coolant_flow_rate = coolant_flow_rate

    def __repr__(self) -> str:
        return (f"<ActuationOutput Torque:{self.torque_adjustment:.2f} | "
                f"Speed:{self.speed_factor:.2f} | Coolant:{self.coolant_flow_rate:.2f}>")

def _calculate_signal_deviation(signal: PhysicalSensoryInput, 
                                baseline: Dict[str, float]) -> float:
    """
    [Helper Function] Calculates the Euclidean norm of the deviation between
    current signal and a baseline 'ideal' state.
    
    Args:
        signal (PhysicalSensoryInput): The current sensor readings.
        baseline (Dict[str, float]): The expected baseline values.
        
    Returns:
        float: A scalar value representing total deviation magnitude.
    """
    try:
        dv = (signal.vibration_hz - baseline.get('vibration', 0)) ** 2
        dr = (signal.resistance_newtons - baseline.get('resistance', 0)) ** 2
        dt = (signal.temp_celsius - baseline.get('temp', 20)) ** 2
        
        # Normalize and calculate norm
        deviation = math.sqrt(dv + dr + dt)
        logger.debug(f"Calculated signal deviation: {deviation:.4f}")
        return deviation
    except Exception as e:
        logger.error(f"Error calculating deviation: {e}")
        return float('inf')

def transduce_signal_to_symbol(signal: PhysicalSensoryInput) -> SymbolicState:
    """
    [Core Function 1] Converts continuous analog physical data into a discrete
    cognitive SymbolicState.
    
    This simulates the 'Perception' phase of the AGI loop.
    
    Args:
        signal (PhysicalSensoryInput): Validated physical sensor data.
        
    Returns:
        SymbolicState: The cognitive representation of the physical state.
    """
    if not isinstance(signal, PhysicalSensoryInput):
        logger.critical("Invalid input type for transduction.")
        raise TypeError("Input must be PhysicalSensoryInput instance")
    
    try:
        signal.validate()
        logger.info(f"Transducing signal: Vib={signal.vibration_hz}Hz, Res={signal.resistance_newtons}N")
        
        # Heuristic logic for symbol compilation
        if signal.temp_celsius > 85:
            return SymbolicState.THERMAL_WARNING
        if signal.resistance_newtons > 500:
            return SymbolicState.RESISTANCE_HIGH
        if signal.vibration_hz > 120 and signal.acoustic_db > 60:
            return SymbolicState.VIBRATION_ANOMALY
        if signal.vibration_hz < 50 and signal.resistance_newtons < 100:
            return SymbolicState.OPTIMAL_OPERATION
            
        return SymbolicState.NULL
        
    except ValueError as ve:
        logger.warning(f"Signal validation failed: {ve}")
        return SymbolicState.UNKNOWN_HAZARD
    except Exception as e:
        logger.error(f"Unexpected error during transduction: {e}")
        return SymbolicState.UNKNOWN_HAZARD

def map_symbol_to_actuation(symbol: SymbolicState, 
                            current_load: float = 1.0) -> ActuationOutput:
    """
    [Core Function 2] Maps a discrete cognitive symbol to precise physical
    correction parameters.
    
    This simulates the 'Action' phase of the AGI loop.
    
    Args:
        symbol (SymbolicState): The cognitive state to address.
        current_load (float): A multiplier representing the current system load (0.0 to 2.0).
        
    Returns:
        ActuationOutput: The executable parameters for the physical machinery.
    """
    logger.info(f"Mapping symbol {symbol.name} to actuation parameters.")
    
    # Default safe parameters
    torque = 0.0
    speed = 1.0
    coolant = 0.1
    
    if symbol == SymbolicState.OPTIMAL_OPERATION:
        torque = 0.0
        speed = 1.0
        coolant = 0.1
        
    elif symbol == SymbolicState.THERMAL_WARNING:
        # Reduce speed, increase coolant
        torque = -0.2 * current_load
        speed = 0.5
        coolant = 1.0
        logger.warning("Thermal warning detected. Activating cooling protocol.")
        
    elif symbol == SymbolicState.RESISTANCE_HIGH:
        # Increase torque momentarily to overcome resistance or break through
        torque = 0.5 * current_load
        speed = 0.8
        coolant = 0.2
        
    elif symbol == SymbolicState.VIBRATION_ANOMALY:
        # Dampen speed significantly to stabilize
        torque = 0.0
        speed = 0.1
        coolant = 0.1
        logger.error("Vibration anomaly detected. Engaging stabilization mode.")
        
    else:
        # Unknown hazard: Full stop
        torque = 0.0
        speed = 0.0
        coolant = 0.0
        logger.critical("Unknown hazard or NULL state. Stopping system.")

    # Boundary checks for output parameters
    speed = max(0.0, min(speed, 2.0))
    coolant = max(0.0, min(coolant, 1.5))
    
    return ActuationOutput(torque, speed, coolant)

class OntologicalLoop:
    """
    Encapsulates the entire closed-loop cycle: 
    Physical Input -> Symbol Compilation -> Virtual Trial -> Physical Correction.
    """
    def __init__(self):
        self.history: List[Dict[str, Union[SymbolicState, ActuationOutput]]] = []
        self.baseline = {'vibration': 30, 'resistance': 50, 'temp': 25}

    def execute_cycle(self, sensor_data: PhysicalSensoryInput) -> ActuationOutput:
        """
        Executes one full cycle of the Ontological Suture.
        """
        logger.info("--- Starting Ontological Cycle ---")
        
        # 1. Perception: Analog to Symbol
        symbol = transduce_signal_to_symbol(sensor_data)
        
        # 2. Internal Processing: Check deviation (Virtual Trial logic)
        deviation = _calculate_signal_deviation(sensor_data, self.baseline)
        load_factor = 1.0 + (deviation / 100.0) # Simplified load calculation
        
        # 3. Action: Symbol to Analog
        actuation = map_symbol_to_actuation(symbol, load_factor)
        
        self.history.append({
            'input': sensor_data, 
            'symbol': symbol, 
            'output': actuation
        })
        
        logger.info(f"Cycle Complete. Symbol: {symbol.name}, Action: {actuation}")
        return actuation

# Example Usage
if __name__ == "__main__":
    # Initialize the loop
    loop = OntologicalLoop()
    
    # Simulate 3 different physical scenarios
    scenarios = [
        # Scenario 1: Normal operation
        PhysicalSensoryInput(vibration_hz=35.5, resistance_newtons=45.0, 
                             temp_celsius=40.0, acoustic_db=30.0),
        
        # Scenario 2: High Resistance (e.g., material hardness spike)
        PhysicalSensoryInput(vibration_hz=60.0, resistance_newtons=850.0, 
                             temp_celsius=50.0, acoustic_db=45.0),
                             
        # Scenario 3: Thermal Warning
        PhysicalSensoryInput(vibration_hz=40.0, resistance_newtons=60.0, 
                             temp_celsius=95.0, acoustic_db=35.0)
    ]

    print(f"{'SCENARIO':<10} | {'SYMBOL':<20} | {'TORQUE':<10} | {'SPEED':<10} | {'COOLANT':<10}")
    print("-" * 70)
    
    for i, data in enumerate(scenarios):
        result = loop.execute_cycle(data)
        print(f"{i+1:<10} | {transduce_signal_to_symbol(data).name:<20} | "
              f"{result.torque_adjustment:<10.2f} | {result.speed_factor:<10.2f} | "
              f"{result.coolant_flow_rate:<10.2f}")