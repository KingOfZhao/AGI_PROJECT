"""
Module: auto_隐性知识的感官信号数字化表征问题_如何利_f98e65
Description: High-precision multi-modal sensor data acquisition and synchronization for digitizing tacit knowledge in craftsmanship (e.g., pottery).
"""

import logging
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SensorConfig:
    """Configuration for a specific sensor modality."""
    name: str
    type: str  # e.g., 'force', 'imu', 'thermal'
    sampling_rate: int  # Hz
    dimensions: int
    range_min: float
    range_max: float

@dataclass
class MultiModalFrame:
    """Represents a single synchronized frame of multi-modal data."""
    timestamp: float
    force_data: np.ndarray  # Shape: (force_dimensions,)
    imu_data: np.ndarray    # Shape: (imu_dimensions,)
    thermal_data: np.ndarray # Shape: (thermal_height, thermal_width)

@dataclass
class TimeSeriesTensor:
    """Container for the final high-dimensional time series tensor."""
    metadata: Dict
    force_tensor: np.ndarray     # Shape: (time_steps, force_dims)
    imu_tensor: np.ndarray       # Shape: (time_steps, imu_dims)
    thermal_tensor: np.ndarray   # Shape: (time_steps, height, width)
    validity_mask: np.ndarray    # Boolean mask indicating valid data points

class TacitKnowledgeDigitizer:
    """
    System for acquiring, synchronizing, and processing multi-modal sensor data
    to digitize tacit knowledge in craftsmanship.
    """

    def __init__(self, configs: List[SensorConfig]):
        """
        Initialize the digitizer with sensor configurations.
        
        Args:
            configs: List of sensor configurations
        """
        self.configs = {cfg.name: cfg for cfg in configs}
        self._validate_configs()
        logger.info(f"Initialized TacitKnowledgeDigitizer with {len(configs)} sensors")

    def _validate_configs(self) -> None:
        """Validate sensor configurations."""
        required_sensors = {'force_glove', 'imu_suite', 'thermal_cam'}
        if not required_sensors.issubset(self.configs.keys()):
            missing = required_sensors - set(self.configs.keys())
            raise ValueError(f"Missing required sensor configs: {missing}")

    def _validate_sensor_data(self, sensor_name: str, data: np.ndarray) -> bool:
        """
        Validate sensor data against configuration bounds.
        
        Args:
            sensor_name: Name of the sensor
            data: Numpy array containing sensor data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        cfg = self.configs[sensor_name]
        if data.shape[-1] != cfg.dimensions:
            logger.error(f"Dimension mismatch for {sensor_name}. Expected {cfg.dimensions}, got {data.shape[-1]}")
            return False
        
        if np.any(data < cfg.range_min) or np.any(data > cfg.range_max):
            logger.warning(f"Data out of bounds for {sensor_name}. Range: [{cfg.range_min}, {cfg.range_max}]")
            # We don't invalidate the data, but flag it for post-processing
        
        return True

    def _synchronize_data(
        self,
        force_data: List[Tuple[float, np.ndarray]],
        imu_data: List[Tuple[float, np.ndarray]],
        thermal_data: List[Tuple[float, np.ndarray]]
    ) -> List[MultiModalFrame]:
        """
        Synchronize multi-modal data streams to a common timebase.
        
        Args:
            force_data: List of (timestamp, data) tuples from force sensors
            imu_data: List of (timestamp, data) tuples from IMU
            thermal_data: List of (timestamp, data) tuples from thermal camera
            
        Returns:
            List of synchronized MultiModalFrames
        """
        # Find common time range
        all_timestamps = []
        for dataset in [force_data, imu_data, thermal_data]:
            if dataset:
                all_timestamps.extend([t for t, _ in dataset])
        
        if not all_timestamps:
            return []
            
        min_time = min(all_timestamps)
        max_time = max(all_timestamps)
        
        # Create interpolated timebase
        # Use the highest sampling rate as reference
        max_rate = max(cfg.sampling_rate for cfg in self.configs.values())
        num_steps = int((max_time - min_time) * max_rate)
        timebase = np.linspace(min_time, max_time, num_steps)
        
        synchronized_frames = []
        
        for t in timebase:
            # Find closest force data
            force_idx = np.argmin([abs(t - ft) for ft, _ in force_data])
            force_val = force_data[force_idx][1]
            
            # Find closest IMU data
            imu_idx = np.argmin([abs(t - it) for it, _ in imu_data])
            imu_val = imu_data[imu_idx][1]
            
            # Find closest thermal data
            thermal_idx = np.argmin([abs(t - tt) for tt, _ in thermal_data])
            thermal_val = thermal_data[thermal_idx][1]
            
            frame = MultiModalFrame(
                timestamp=t,
                force_data=force_val,
                imu_data=imu_val,
                thermal_data=thermal_val
            )
            synchronized_frames.append(frame)
        
        logger.info(f"Synchronized {len(synchronized_frames)} frames")
        return synchronized_frames

    def acquire_data(
        self,
        duration_sec: float,
        force_callback: callable,
        imu_callback: callable,
        thermal_callback: callable
    ) -> TimeSeriesTensor:
        """
        Acquire data from all sensors for specified duration.
        
        Args:
            duration_sec: Duration of data acquisition in seconds
            force_callback: Function that returns (timestamp, force_data)
            imu_callback: Function that returns (timestamp, imu_data)
            thermal_callback: Function that returns (timestamp, thermal_data)
            
        Returns:
            TimeSeriesTensor containing synchronized data
            
        Example:
            >>> def mock_force():
            ...     return time.time(), np.random.randn(6) * 10  # 6-axis force
            >>> digitizer = TacitKnowledgeDigitizer(default_configs())
            >>> tensor = digitizer.acquire_data(5.0, mock_force, mock_imu, mock_thermal)
        """
        if duration_sec <= 0:
            raise ValueError("Duration must be positive")
        
        logger.info(f"Starting data acquisition for {duration_sec} seconds")
        
        force_data = []
        imu_data = []
        thermal_data = []
        
        start_time = time.time()
        end_time = start_time + duration_sec
        
        try:
            while time.time() < end_time:
                current_time = time.time()
                
                # Acquire force data
                if current_time - start_time >= 1.0/self.configs['force_glove'].sampling_rate:
                    ts, data = force_callback()
                    if self._validate_sensor_data('force_glove', data):
                        force_data.append((ts, data))
                
                # Acquire IMU data
                if current_time - start_time >= 1.0/self.configs['imu_suite'].sampling_rate:
                    ts, data = imu_callback()
                    if self._validate_sensor_data('imu_suite', data):
                        imu_data.append((ts, data))
                
                # Acquire thermal data
                if current_time - start_time >= 1.0/self.configs['thermal_cam'].sampling_rate:
                    ts, data = thermal_callback()
                    if self._validate_sensor_data('thermal_cam', data):
                        thermal_data.append((ts, data))
                
                time.sleep(0.001)  # Prevent CPU overload
                
        except Exception as e:
            logger.error(f"Data acquisition failed: {str(e)}")
            raise RuntimeError(f"Data acquisition error: {str(e)}")
        
        # Synchronize data streams
        synchronized = self._synchronize_data(force_data, imu_data, thermal_data)
        
        # Convert to tensors
        return self._create_tensor(synchronized)

    def _create_tensor(self, frames: List[MultiModalFrame]) -> TimeSeriesTensor:
        """
        Convert synchronized frames to tensor format.
        
        Args:
            frames: List of synchronized MultiModalFrames
            
        Returns:
            TimeSeriesTensor containing all data
        """
        if not frames:
            return TimeSeriesTensor(
                metadata={},
                force_tensor=np.array([]),
                imu_tensor=np.array([]),
                thermal_tensor=np.array([]),
                validity_mask=np.array([])
            )
        
        # Initialize arrays
        num_frames = len(frames)
        force_dims = frames[0].force_data.shape[0]
        imu_dims = frames[0].imu_data.shape[0]
        thermal_shape = frames[0].thermal_data.shape
        
        force_tensor = np.zeros((num_frames, force_dims))
        imu_tensor = np.zeros((num_frames, imu_dims))
        thermal_tensor = np.zeros((num_frames, *thermal_shape))
        validity_mask = np.ones(num_frames, dtype=bool)
        
        # Fill arrays
        for i, frame in enumerate(frames):
            force_tensor[i] = frame.force_data
            imu_tensor[i] = frame.imu_data
            thermal_tensor[i] = frame.thermal_data
            
            # Mark invalid frames (if any sensor data is out of bounds)
            for sensor_name, data in [
                ('force_glove', frame.force_data),
                ('imu_suite', frame.imu_data),
                ('thermal_cam', frame.thermal_data)
            ]:
                if not self._validate_sensor_data(sensor_name, data):
                    validity_mask[i] = False
        
        metadata = {
            'num_frames': num_frames,
            'duration_sec': frames[-1].timestamp - frames[0].timestamp,
            'sensors': {name: cfg.__dict__ for name, cfg in self.configs.items()},
            'valid_frames': int(np.sum(validity_mask))
        }
        
        return TimeSeriesTensor(
            metadata=metadata,
            force_tensor=force_tensor,
            imu_tensor=imu_tensor,
            thermal_tensor=thermal_tensor,
            validity_mask=validity_mask
        )

    def export_tensor(self, tensor: TimeSeriesTensor, filepath: str) -> None:
        """
        Export tensor data to file.
        
        Args:
            tensor: TimeSeriesTensor to export
            filepath: Path to save the tensor data
        """
        try:
            np.savez_compressed(
                filepath,
                metadata=np.array(tensor.metadata),
                force_tensor=tensor.force_tensor,
                imu_tensor=tensor.imu_tensor,
                thermal_tensor=tensor.thermal_tensor,
                validity_mask=tensor.validity_mask
            )
            logger.info(f"Tensor exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export tensor: {str(e)}")
            raise IOError(f"Tensor export failed: {str(e)}")

def default_configs() -> List[SensorConfig]:
    """Generate default sensor configurations."""
    return [
        SensorConfig(
            name='force_glove',
            type='force',
            sampling_rate=100,  # 100Hz
            dimensions=6,       # 6-axis force/torque
            range_min=-100.0,
            range_max=100.0
        ),
        SensorConfig(
            name='imu_suite',
            type='imu',
            sampling_rate=200,  # 200Hz
            dimensions=9,       # 3x accel, 3x gyro, 3x mag
            range_min=-32768.0,
            range_max=32767.0
        ),
        SensorConfig(
            name='thermal_cam',
            type='thermal',
            sampling_rate=30,   # 30Hz
            dimensions=65536,   # 256x256 thermal image
            range_min=20.0,     # 20°C
            range_max=500.0     # 500°C
        )
    ]

# Example usage
if __name__ == "__main__":
    # Create mock sensor callbacks
    def mock_force_sensor():
        return time.time(), np.random.randn(6) * 10  # 6-axis force
    
    def mock_imu_sensor():
        return time.time(), np.random.randn(9) * 100  # 9-axis IMU
    
    def mock_thermal_sensor():
        return time.time(), np.random.rand(256, 256) * 400 + 20  # Thermal image
    
    # Initialize digitizer
    configs = default_configs()
    digitizer = TacitKnowledgeDigitizer(configs)
    
    # Acquire data for 3 seconds
    try:
        tensor = digitizer.acquire_data(
            duration_sec=3.0,
            force_callback=mock_force_sensor,
            imu_callback=mock_imu_sensor,
            thermal_callback=mock_thermal_sensor
        )
        
        # Print tensor info
        print(f"Acquired {tensor.metadata['num_frames']} frames")
        print(f"Valid frames: {tensor.metadata['valid_frames']}")
        print(f"Force tensor shape: {tensor.force_tensor.shape}")
        print(f"IMU tensor shape: {tensor.imu_tensor.shape}")
        print(f"Thermal tensor shape: {tensor.thermal_tensor.shape}")
        
        # Export tensor
        digitizer.export_tensor(tensor, "craftsmanship_data.npz")
        
    except Exception as e:
        print(f"Error: {str(e)}")