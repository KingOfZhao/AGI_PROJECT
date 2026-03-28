"""
Module: embodied_cognition_interface
A high-fidelity Digital Twin Interface for mapping human implicit embodied cognition
(such as tactile feel, resistance, and pain) to quantifiable digital parameters using
multimodal sensors (MEMG, IMU, Vision).
"""

import logging
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmbodiedCognitionInterface")

class SensorType(Enum):
    """Enumeration of supported sensor modalities."""
    MEMG = "Micro-Electro-Mechanical-Gyroscope"
    IMU = "Inertial Measurement Unit"
    VISION = "Computer Vision"

class CognitionDimension(Enum):
    """Dimensions of human embodied cognition to map."""
    TACTILE_PRESSURE = "Tactile Pressure"
    MUSCLE_TENSION = "Muscle Tension"
    PAIN_THRESHOLD = "Pain Threshold"
    VIBRATION = "Vibration Sensation"

@dataclass
class SensorReading:
    """Data structure for a single sensor reading."""
    sensor_type: SensorType
    timestamp: float
    raw_data: np.ndarray
    confidence: float = 1.0
    
    def validate(self) -> bool:
        """Validate sensor reading data."""
        if not isinstance(self.raw_data, np.ndarray):
            logger.error("Invalid data type: raw_data must be numpy array")
            return False
        if self.confidence < 0 or self.confidence > 1:
            logger.error("Confidence must be between 0 and 1")
            return False
        if self.timestamp < 0:
            logger.error("Timestamp cannot be negative")
            return False
        return True

@dataclass
class EmbodiedMapping:
    """Configuration for mapping sensor data to cognition dimensions."""
    dimension: CognitionDimension
    input_sensors: List[SensorType]
    calibration_matrix: np.ndarray
    threshold_range: Tuple[float, float]
    description: str = ""

class EmbodiedCognitionInterface:
    """
    Digital Twin Interface for mapping human embodied cognition to digital parameters.
    
    This interface captures implicit human sensory experiences through multimodal sensors
    and translates them into quantifiable parameters that machines can understand and process.
    
    Attributes:
        mappings (Dict[CognitionDimension, EmbodiedMapping]): Configured cognition mappings
        buffer_size (int): Maximum number of readings to buffer
        last_readings (Dict[SensorType, List[SensorReading]]): Recent sensor readings buffer
    """
    
    def __init__(self, buffer_size: int = 100):
        """
        Initialize the Embodied Cognition Interface.
        
        Args:
            buffer_size: Maximum number of readings to store per sensor type
        """
        self.mappings: Dict[CognitionDimension, EmbodiedMapping] = {}
        self.buffer_size = buffer_size
        self.last_readings: Dict[SensorType, List[SensorReading]] = {
            st: [] for st in SensorType
        }
        logger.info("Embodied Cognition Interface initialized with buffer size %d", buffer_size)
    
    def add_mapping(self, mapping: EmbodiedMapping) -> None:
        """
        Add a new cognition dimension mapping configuration.
        
        Args:
            mapping: EmbodiedMapping configuration object
            
        Raises:
            ValueError: If mapping validation fails
        """
        self._validate_mapping(mapping)
        self.mappings[mapping.dimension] = mapping
        logger.info("Added mapping for dimension: %s", mapping.dimension.value)
    
    def process_sensor_data(self, reading: SensorReading) -> Dict[CognitionDimension, float]:
        """
        Process incoming sensor data and generate cognition dimension values.
        
        Args:
            reading: Validated SensorReading object
            
        Returns:
            Dict mapping CognitionDimension to computed float values
            
        Raises:
            ValueError: If sensor reading validation fails
        """
        if not reading.validate():
            raise ValueError("Invalid sensor reading provided")
        
        # Update reading buffer
        self._update_buffer(reading)
        
        results = {}
        for dim, mapping in self.mappings.items():
            if reading.sensor_type in mapping.input_sensors:
                try:
                    value = self._apply_mapping(reading, mapping)
                    results[dim] = value
                    logger.debug("Computed %s value: %.4f", dim.value, value)
                except Exception as e:
                    logger.error("Error processing dimension %s: %s", dim.value, str(e))
        
        return results
    
    def detect_anomalies(self, 
                        dimension: CognitionDimension,
                        window_size: int = 5) -> Optional[str]:
        """
        Detect anomalies in a specific cognition dimension based on recent readings.
        
        Args:
            dimension: Cognition dimension to analyze
            window_size: Number of recent readings to consider
            
        Returns:
            Optional warning message if anomaly detected, None otherwise
        """
        if dimension not in self.mappings:
            logger.warning("No mapping configured for dimension: %s", dimension.value)
            return None
        
        mapping = self.mappings[dimension]
        readings = []
        
        for sensor_type in mapping.input_sensors:
            readings.extend(self.last_readings[sensor_type][-window_size:])
        
        if not readings:
            return None
        
        # Simple anomaly detection based on threshold range
        for reading in readings:
            try:
                value = self._apply_mapping(reading, mapping)
                if value < mapping.threshold_range[0] or value > mapping.threshold_range[1]:
                    warning = (f"Anomaly detected in {dimension.value}: "
                              f"Value {value:.2f} outside range {mapping.threshold_range}")
                    logger.warning(warning)
                    return warning
            except Exception as e:
                logger.error("Error in anomaly detection: %s", str(e))
        
        return None
    
    def _validate_mapping(self, mapping: EmbodiedMapping) -> None:
        """
        Validate an EmbodiedMapping configuration.
        
        Args:
            mapping: EmbodiedMapping to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not mapping.input_sensors:
            raise ValueError("Mapping must specify at least one input sensor")
        
        if len(mapping.calibration_matrix.shape) != 2:
            raise ValueError("Calibration matrix must be 2-dimensional")
        
        if (mapping.threshold_range[0] >= mapping.threshold_range[1]):
            raise ValueError("Invalid threshold range: min must be less than max")
    
    def _update_buffer(self, reading: SensorReading) -> None:
        """
        Update the sensor readings buffer with a new reading.
        
        Args:
            reading: Validated SensorReading to add to buffer
        """
        sensor_buffer = self.last_readings[reading.sensor_type]
        sensor_buffer.append(reading)
        
        # Maintain buffer size
        if len(sensor_buffer) > self.buffer_size:
            sensor_buffer.pop(0)
    
    def _apply_mapping(self, 
                      reading: SensorReading, 
                      mapping: EmbodiedMapping) -> float:
        """
        Apply calibration matrix to sensor reading for a specific cognition dimension.
        
        Args:
            reading: Validated SensorReading
            mapping: EmbodiedMapping configuration
            
        Returns:
            Computed float value for the cognition dimension
        """
        # Simple linear transformation for demonstration
        # In a real system, this would be a complex transformation
        flattened_data = reading.raw_data.flatten()
        transformed = np.dot(flattened_data, mapping.calibration_matrix.flatten()[:len(flattened_data)])
        
        # Apply confidence weighting
        weighted_value = transformed * reading.confidence
        
        # Normalize to threshold range
        min_val, max_val = mapping.threshold_range
        normalized = (weighted_value - min_val) / (max_val - min_val)
        
        return float(np.clip(normalized, 0.0, 1.0))

# Example Usage
if __name__ == "__main__":
    # Initialize interface
    interface = EmbodiedCognitionInterface(buffer_size=50)
    
    # Configure a mapping for pain threshold detection
    pain_mapping = EmbodiedMapping(
        dimension=CognitionDimension.PAIN_THRESHOLD,
        input_sensors=[SensorType.MEMG, SensorType.IMU],
        calibration_matrix=np.array([[0.7, 0.3], [0.2, 0.8]]),
        threshold_range=(0.0, 1.0),
        description="Maps muscle tension and movement to pain perception"
    )
    interface.add_mapping(pain_mapping)
    
    # Simulate sensor readings
    memg_reading = SensorReading(
        sensor_type=SensorType.MEMG,
        timestamp=1625097600.0,
        raw_data=np.array([0.6, 0.4]),
        confidence=0.95
    )
    
    imu_reading = SensorReading(
        sensor_type=SensorType.IMU,
        timestamp=1625097600.1,
        raw_data=np.array([0.2, 0.9]),
        confidence=0.9
    )
    
    # Process readings
    pain_from_memg = interface.process_sensor_data(memg_reading)
    pain_from_imu = interface.process_sensor_data(imu_reading)
    
    # Detect anomalies
    anomaly_status = interface.detect_anomalies(CognitionDimension.PAIN_THRESHOLD)
    
    print(f"Pain perception from MEMG: {pain_from_memg}")
    print(f"Pain perception from IMU: {pain_from_imu}")
    print(f"Anomaly detection: {anomaly_status or 'No anomalies detected'}")