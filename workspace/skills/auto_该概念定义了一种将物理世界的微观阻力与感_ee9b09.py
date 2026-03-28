"""
Module: haptic_digital_twin.py

This module implements a closed-loop system for converting physical world 
micro-resistance and sensory experiences (craftsmanship feel, material texture) 
into computable digital signals. It introduces a 'Physical Loss Function' and 
utilizes a Sim-to-Real adapter to bridge the gap between simulation and reality.

Classes:
    - SensorData: Data model for high-frequency sensor inputs.
    - HapticDigitalTwin: Core system for processing and feedback control.

Functions:
    - physical_loss_function: Calculates the loss between simulated and real physics.
    - sim_to_real_adapter: Adjusts commands based on residuals.
    - validate_time_series: Helper to validate input data integrity.
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HapticDigitalTwin")

class TextureType(Enum):
    """Enumeration of standard material textures."""
    SMOOTH = 0
    ROUGH = 1
    VISCOUS = 2
    ELASTIC = 3

@dataclass
class SensorData:
    """
    Represents a time-series slice of haptic sensor data.
    
    Attributes:
        timestamp: Unix timestamp in milliseconds.
        force: Force vector [x, y, z] in Newtons.
        torque: Torque vector [x, y, z] in Newton-meters.
        position: Cartesian coordinates [x, y, z] in meters.
        texture_id: Inferred texture identifier.
    """
    timestamp: float
    force: np.ndarray
    torque: np.ndarray
    position: np.ndarray
    texture_id: TextureType = TextureType.SMOOTH

    def __post_init__(self):
        """Validate dimensions after initialization."""
        if self.force.shape != (3,) or self.torque.shape != (3,) or self.position.shape != (3,):
            raise ValueError("Force, Torque, and Position must be 3-dimensional vectors.")

def validate_time_series(data: List[SensorData], window_size: int = 10) -> bool:
    """
    Helper function: Validates the integrity and continuity of sensor data streams.
    
    Args:
        data: List of SensorData objects.
        window_size: Minimum number of data points required for processing.
        
    Returns:
        True if data is valid, raises ValueError otherwise.
    """
    if not data:
        logger.error("Input data list is empty.")
        raise ValueError("Input data list cannot be empty.")
    
    if len(data) < window_size:
        logger.warning(f"Data length {len(data)} is less than recommended window size {window_size}.")
    
    # Check temporal continuity (simplified)
    timestamps = [d.timestamp for d in data]
    if timestamps != sorted(timestamps):
        logger.error("Timestamps are not in chronological order.")
        raise ValueError("Time series data must be chronological.")
        
    return True

def physical_loss_function(
    real_force: np.ndarray, 
    sim_force: np.ndarray, 
    material_constant: float = 0.5
) -> float:
    """
    Core Function 1: Computes the physical loss between real-world haptic feedback 
    and simulated physics models.
    
    This goes beyond geometric loss by weighting the error based on material properties.
    
    Args:
        real_force: The actual force vector measured by sensors.
        sim_force: The expected force vector from the physics engine.
        material_constant: A weighting factor for sensitivity (0.0 to 1.0).
        
    Returns:
        A floating-point value representing the physical discrepancy (Loss).
    """
    if not (0.0 <= material_constant <= 1.0):
        raise ValueError("Material constant must be between 0 and 1.")
        
    try:
        # Euclidean distance weighted by material sensitivity
        delta = np.linalg.norm(real_force - sim_force)
        loss = delta * (1 + material_constant) # Simple linear scaling for demo
        logger.debug(f"Calculated Physical Loss: {loss:.4f}")
        return float(loss)
    except Exception as e:
        logger.error(f"Error calculating physical loss: {e}")
        raise

def sim_to_real_adapter(
    current_cmd: np.ndarray, 
    residual_error: np.ndarray, 
    learning_rate: float = 0.01
) -> np.ndarray:
    """
    Core Function 2: Adapts the control signal to minimize the Sim-to-Real gap.
    
    This function modifies the actuator commands to account for unmodeled 
    friction or micro-resistances detected in the physical world.
    
    Args:
        current_cmd: The original command vector calculated by the AI planner.
        residual_error: The difference between expected and actual state (Real - Sim).
        learning_rate: Adaptation step size.
        
    Returns:
        The adjusted command vector for the actuators.
    """
    # Basic gradient descent step for adaptation
    # cmd_new = cmd_old + learning_rate * error
    adjustment = residual_error * learning_rate
    adjusted_cmd = current_cmd + adjustment
    
    logger.info(f"Adapter adjusted command by norm: {np.linalg.norm(adjustment):.4f}")
    return adjusted_cmd

class HapticDigitalTwin:
    """
    Main class that orchestrates the sensory feedback loop.
    """
    
    def __init__(self, initial_model_params: Optional[dict] = None):
        """
        Initialize the Digital Twin.
        
        Args:
            initial_model_params: Dictionary containing physics engine parameters.
        """
        self.model_params = initial_model_params or {"friction": 0.5, "stiffness": 100.0}
        self.history: List[SensorData] = []
        logger.info("HapticDigitalTwin System Initialized.")

    def process_sensory_input(self, data_batch: List[SensorData]) -> Tuple[np.ndarray, float]:
        """
        Processes a batch of high-frequency sensor data to generate a state vector.
        
        Args:
            data_batch: A list of SensorData points.
            
        Returns:
            A tuple containing the feature vector and the calculated physical loss.
        """
        try:
            # 1. Validate Input
            validate_time_series(data_batch)
            
            # 2. Extract features (Simplified: Average force and position)
            forces = np.array([d.force for d in data_batch])
            positions = np.array([d.position for d in data_batch])
            
            avg_force = np.mean(forces, axis=0)
            avg_pos = np.mean(positions, axis=0)
            
            # 3. Calculate Physical Loss
            # In a real scenario, we would query a physics engine here.
            # We simulate a 'expected_force' based on position for demonstration.
            simulated_force = self._mock_physics_engine(avg_pos)
            loss = physical_loss_function(avg_force, simulated_force)
            
            # 4. Store history for temporal analysis
            self.history.extend(data_batch)
            
            feature_vector = np.concatenate([avg_force, avg_pos])
            return feature_vector, loss
            
        except Exception as e:
            logger.critical(f"Failed to process sensory input: {e}")
            raise

    def execute_closed_loop_control(self, target_state: np.ndarray, current_data: SensorData) -> np.ndarray:
        """
        Executes one cycle of the closed-loop control.
        
        Args:
            target_state: The desired state vector (e.g., position + force).
            current_data: Real-time feedback from sensors.
            
        Returns:
            Actuator command vector.
        """
        logger.info("Executing closed-loop control cycle.")
        
        # 1. Determine Residual (Real vs Target)
        current_state = np.concatenate([current_data.force, current_data.position])
        residual = target_state - current_state
        
        # 2. Basic Controller (e.g., Proportional)
        # In reality, this would be a complex policy network
        raw_command = residual * 0.5  # Simple P-gain
        
        # 3. Adapt command using Sim-to-Real Adapter
        # Here we use the residual as the error signal to adapt the raw command
        final_command = sim_to_real_adapter(raw_command, residual)
        
        return final_command

    def _mock_physics_engine(self, position: np.ndarray) -> np.ndarray:
        """Internal helper to simulate a physics engine response."""
        # Mock physics: Force = Stiffness * Position (Spring model)
        stiffness = self.model_params.get("stiffness", 100.0)
        return position * stiffness

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Create dummy sensor data
    dummy_data = [
        SensorData(
            timestamp=1678886400000.0 + i * 10,
            force=np.array([0.1, 0.0, 9.8]) + np.random.normal(0, 0.01, 3),
            torque=np.array([0.0, 0.0, 0.0]),
            position=np.array([i*0.01, 0.0, 0.1])
        )
        for i in range(10)
    ]

    # Initialize System
    twin = HapticDigitalTwin(initial_model_params={"friction": 0.4, "stiffness": 50.0})

    # 1. Process Batch Data
    try:
        features, loss = twin.process_sensory_input(dummy_data)
        print(f"Extracted Features: {features}")
        print(f"Physical Loss: {loss}")
    except ValueError as e:
        print(f"Validation Error: {e}")

    # 2. Perform Real-time Control Loop
    target = np.array([0.5, 0.0, 9.8, 0.5, 0.0, 0.5]) # Target Force + Position
    current_reading = SensorData(
        timestamp=1678886401000.0,
        force=np.array([0.2, 0.0, 9.5]),
        torque=np.zeros(3),
        position=np.array([0.3, 0.0, 0.1])
    )
    
    command = twin.execute_closed_loop_control(target, current_reading)
    print(f"Final Actuator Command: {command}")