"""
Module: tacit_skill_digitizer.py

This module implements the 'TacitSkillDigitizer' system, a cognitive-physical conversion
framework designed to map unstructured, implicit human craftsmanship skills (e.g., kneading 
dough, heat control) into machine-executable, interpretable digital 'True Nodes'.

It creates a closed-loop system involving:
1. Multi-modal sensory data acquisition (Simulated EMG/IMU).
2. Spatiotemporal dimensionality reduction (Mapping).
3. Micro-action correction based on Temporal Difference (TD) feedback.

Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("TacitSkillDigitizer")

class SensorType(Enum):
    """Enumeration for supported sensor types."""
    EMG = "Electromyography"
    IMU = "InertialMeasurementUnit"
    FORCE = "ForceTorque"
    TEMP = "Thermocouple"

@dataclass
class SensoryPacket:
    """Data structure for a single timestamp of multi-modal sensor data."""
    timestamp: float
    emg_data: np.ndarray       # Shape: (n_channels,), e.g., muscle activity
    imu_data: np.ndarray       # Shape: (6,) - Accel(X,Y,Z) + Gyro(X,Y,Z)
    force_scalar: float        # Scalar value of applied force
    
    def validate(self) -> bool:
        """Validates the data shapes and types."""
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("Timestamp must be a non-negative number.")
        if self.emg_data.shape != (8,): # Assuming 8-channel EMG
            raise ValueError(f"Expected EMG shape (8,), got {self.emg_data.shape}")
        if self.imu_data.shape != (6,):
            raise ValueError(f"Expected IMU shape (6,), got {self.imu_data.shape}")
        if self.force_scalar < 0:
            logger.warning("Negative force detected, clamping to 0.")
            self.force_scalar = 0.0
        return True

@dataclass
class SkillNode:
    """Represents a digitized, executable skill unit (The 'True Node')."""
    node_id: str
    latent_vector: np.ndarray  # The compressed skill representation
    execution_params: Dict[str, float]
    alignment_score: float     # Confidence score (0.0 to 1.0)

class DataIngestionError(Exception):
    """Custom exception for errors during sensory data ingestion."""
    pass

class DimensionalityMapError(Exception):
    """Custom exception for errors in the embedding process."""
    pass

class TacitSkillDigitizer:
    """
    A system to convert implicit human motor skills into machine-executable digital nodes.
    
    This class handles the pipeline from raw sensor input to a refined skill vector,
    utilizing a simulated Temporal Difference (TD) learning loop for alignment.
    
    Attributes:
        history_window (int): Size of the sliding window for temporal context.
        latent_dim (int): Target dimensionality for the skill embedding.
        _sensor_buffer (List[SensoryPacket]): Buffer for storing recent sensory data.
    """

    def __init__(self, history_window: int = 64, latent_dim: int = 12):
        """
        Initialize the SkillDigitizer.
        
        Args:
            history_window (int): Number of timesteps to consider for temporal features.
            latent_dim (int): Size of the compressed feature vector.
        """
        if history_window < 10:
            raise ValueError("History window must be at least 10 timesteps.")
        self.history_window = history_window
        self.latent_dim = latent_dim
        self._sensor_buffer: List[SensoryPacket] = []
        # Simulated projection matrix for dimensionality reduction
        self._projection_matrix = np.random.randn(15, self.latent_dim) # 8 EMG + 6 IMU + 1 Force
        logger.info(f"TacitSkillDigitizer initialized with window={history_window}, dim={latent_dim}")

    def ingest_sensory_stream(self, packet: SensoryPacket) -> None:
        """
        Ingests a single frame of multi-modal sensor data.
        
        Args:
            packet (SensoryPacket): The sensory data packet.
        
        Raises:
            DataIngestionError: If data validation fails.
        """
        try:
            packet.validate()
            self._sensor_buffer.append(packet)
            # Maintain sliding window
            if len(self._sensor_buffer) > self.history_window:
                self._sensor_buffer.pop(0)
            logger.debug(f"Ingested packet at t={packet.timestamp:.4f}")
        except ValueError as e:
            logger.error(f"Data validation failed: {e}")
            raise DataIngestionError(f"Invalid packet data: {e}")
        except Exception as e:
            logger.critical(f"Unexpected error during ingestion: {e}")
            raise DataIngestionError("Critical ingestion failure.")

    def _extract_features(self) -> np.ndarray:
        """
        Helper function to extract statistical features from the buffer.
        
        Returns:
            np.ndarray: A flattened array of aggregated features (Mean, Std, Max).
        """
        if not self._sensor_buffer:
            return np.zeros(15) # Dummy data if empty

        # Stack data for vectorized operations
        emg_stack = np.array([p.emg_data for p in self._sensor_buffer])
        imu_stack = np.array([p.imu_data for p in self._sensor_buffer])
        force_stack = np.array([p.force_scalar for p in self._sensor_buffer])

        # Feature Engineering: Aggregating time-series into feature vector
        # [Mean, Std Dev, Max] for each channel
        emg_feats = np.concatenate([
            np.mean(emg_stack, axis=0), 
            np.std(emg_stack, axis=0), 
            np.max(emg_stack, axis=0)
        ])
        
        imu_feats = np.concatenate([
            np.mean(imu_stack, axis=0), 
            np.std(imu_stack, axis=0)
        ])
        
        force_feats = np.array([np.mean(force_stack), np.max(force_stack), np.std(force_stack)])
        
        # Selection/Subsampling to match projection matrix input dim (15)
        # Simplified logic: taking mean and std of first channels
        combined = np.concatenate([
            np.mean(emg_stack, axis=0), # 8
            np.mean(imu_stack, axis=0), # 6
            [np.mean(force_stack)]      # 1
        ])
        return combined

    def map_to_latent_space(self) -> Tuple[np.ndarray, float]:
        """
        Maps the current sensory history to a lower-dimensional 'Skill Vector'.
        
        This represents the translation from high-bandwidth sensor noise to a 
        semantic 'intent' vector.
        
        Returns:
            Tuple[np.ndarray, float]: (Latent vector, Reconstruction error proxy)
        
        Raises:
            DimensionalityMapError: If buffer is insufficient or mapping fails.
        """
        if len(self._sensor_buffer) < self.history_window // 2:
            raise DimensionalityMapError("Insufficient history to map to latent space.")
        
        try:
            features = self._extract_features()
            # Apply simulated projection
            latent_vector = np.dot(features, self._projection_matrix)
            
            # Normalize vector
            norm = np.linalg.norm(latent_vector)
            if norm > 1e-6:
                latent_vector = latent_vector / norm
            
            # Simulated reconstruction error (confidence metric)
            error = np.random.uniform(0.01, 0.05) # Placeholder for actual autoencoder loss
            logger.info(f"Mapped to latent space. Shape: {latent_vector.shape}")
            return latent_vector, error
            
        except Exception as e:
            logger.error(f"Mapping failed: {e}")
            raise DimensionalityMapError(f"Latent mapping computation error: {e}")

    def run_td_alignment_loop(self, target_params: Dict[str, float], iterations: int = 10) -> SkillNode:
        """
        Executes a Temporal Difference (TD) style loop to refine the digital node.
        
        This simulates the machine 'practicing' the move mentally (or in sim) to 
        align the latent vector with physical execution parameters (e.g., desired torque).
        
        Args:
            target_params (Dict[str, float]): The target physical outcome (e.g., {'force': 10.0}).
            iterations (int): Number of refinement steps.
        
        Returns:
            SkillNode: The finalized digital skill node.
        """
        logger.info(f"Starting TD Alignment for targets: {target_params}")
        
        # Initialize with current observation
        current_latent, _ = self.map_to_latent_space()
        current_params = self._latent_to_params(current_latent)
        
        for i in range(iterations):
            # Calculate Reward (Negative MSE between current and target)
            reward = -sum((current_params.get(k, 0) - v)**2 for k, v in target_params.items())
            
            # Simulated Update Step (Gradient ascent on reward)
            # In a real scenario, this involves a neural network update
            delta = 0.05 * (reward + 0.9 * np.max(current_latent)) # Simplified TD error usage
            
            # Perturb latent vector towards better alignment
            noise = np.random.randn(self.latent_dim) * 0.01
            current_latent += (noise * delta)
            current_latent = current_latent / np.linalg.norm(current_latent) # Re-normalize
            
            # Update params based on new latent
            current_params = self._latent_to_params(current_latent)
            logger.debug(f"Iter {i}: Reward={reward:.4f}, Delta={delta:.4f}")

        # Final alignment score calculation
        final_error = sum((current_params.get(k, 0) - v)**2 for k, v in target_params.items())
        alignment_score = np.exp(-final_error) # Score between 0 and 1

        node = SkillNode(
            node_id=f"skill_{hash(current_latent.tobytes())}",
            latent_vector=current_latent,
            execution_params=current_params,
            alignment_score=alignment_score
        )
        logger.info(f"Node created. ID: {node.node_id}, Score: {alignment_score:.3f}")
        return node

    def _latent_to_params(self, latent: np.ndarray) -> Dict[str, float]:
        """Decodes latent vector to execution parameters (Simulated Decoder)."""
        # Simple linear mapping simulation
        return {
            "force": float(np.mean(latent[:4]) * 20), # Scale up
            "velocity": float(np.mean(latent[4:8]) * 5),
            "stiffness": float(np.mean(latent[8:12]) * 10)
        }

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Initialize System
    digitizer = TacitSkillDigitizer(history_window=32, latent_dim=16)
    
    # 2. Simulate Human Craftsmanship Data Stream (e.g., Kneading Dough)
    # Filling the buffer with simulated data
    print("Simulating skill recording...")
    for t in range(40):
        # Simulate EMG (muscle activity) and IMU (motion)
        # Sinusoidal pattern to simulate rhythmic kneading
        base_signal = np.sin(t / 5.0)
        
        packet = SensoryPacket(
            timestamp=float(t),
            emg_data=np.array([base_signal + np.random.normal(0, 0.1) for _ in range(8)]),
            imu_data=np.array([base_signal*0.5 + np.random.normal(0, 0.05) for _ in range(6)]),
            force_scalar=10.0 + base_signal * 5.0 # Force varying between 5 and 15
        )
        digitizer.ingest_sensory_stream(packet)
        
    # 3. Define Target 'Ideal' Parameters (The explicit goal)
    target_specs = {"force": 12.5, "velocity": 1.2, "stiffness": 5.0}
    
    # 4. Run the Alignment Loop (The Cognitive-Physical Conversion)
    try:
        skill_node = digitizer.run_td_alignment_loop(target_specs, iterations=20)
        
        # 5. Output Result
        print("\n=== Generated Digital Skill Node ===")
        print(f"Node ID: {skill_node.node_id}")
        print(f"Alignment Score: {skill_node.alignment_score:.4f}")
        print(f"Execution Parameters: {skill_node.execution_params}")
        print(f"Latent Vector (First 5): {skill_node.latent_vector[:5]}")
        
    except (DataIngestionError, DimensionalityMapError) as e:
        print(f"System failed: {e}")