"""
Skill Module: Industrial Dynamic Environment Adaptation & OOD Detection
=======================================================================

This module implements an AGI-level cognitive skill for handling high dynamism 
in industrial scenarios (e.g., tool wear, raw material batch variations).

Core Functionality:
1. Detects Out-of-Distribution (OOD) states in real-time sensor data.
2. Evaluates the validity of existing 'Knowledge Nodes' (cognitive models).
3. Triggers a 'Self-Destruct and Reconstruct' cycle (Bottom-Up Knowledge Building) 
   when model drift is detected.

Author: AGI System Core Team
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

# --- Configuration & Logging ---

# Setting up robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IndustrialCognitiveCore")


# --- Data Models ---

class SensorReading(BaseModel):
    """
    Represents a single reading from an industrial sensor.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    vibration: float = Field(..., description="Vibration amplitude in mm/s")
    temperature: float = Field(..., description="Temperature in Celsius")
    acoustic_emission: float = Field(..., description="Acoustic emission level in dB")
    batch_id: str = Field(..., description="Identifier for the raw material batch")

    @validator('vibration', 'temperature', 'acoustic_emission')
    def check_positive(cls, v):
        if v < 0:
            raise ValueError("Sensor values must be positive")
        return v


class KnowledgeNode(BaseModel):
    """
    Represents a 'True Node' in the AGI's cognitive framework.
    Contains the statistical baseline for 'Normal' operation.
    """
    node_id: str
    version: float = 1.0
    feature_stats: Dict[str, Dict[str, float]] = Field(
        ..., 
        description="Statistics e.g., {'vibration': {'mean': 10, 'std': 1}}"
    )
    is_active: bool = True
    last_validated: datetime = Field(default_factory=datetime.now)


class ReconstructionRequest(BaseModel):
    """
    Request payload for triggering new knowledge building.
    """
    failed_node_id: str
    trigger_cause: str
    anomaly_data: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)


# --- Core Classes ---

class OODDetector:
    """
    Implements Out-of-Distribution detection using statistical distance.
    """
    
    @staticmethod
    def calculate_mahalanobis_distance(
        data_point: np.ndarray, 
        mean: np.ndarray, 
        cov_inv: np.ndarray
    ) -> float:
        """
        Calculate the Mahalanobis distance between a point and a distribution.
        
        Args:
            data_point (np.ndarray): The observed data (1D array).
            mean (np.ndarray): The mean of the training distribution.
            cov_inv (np.ndarray): Inverse of the covariance matrix.
        
        Returns:
            float: The Mahalanobis distance.
        """
        diff = data_point - mean
        md = np.sqrt(np.dot(np.dot(diff, cov_inv), diff.T))
        return float(md)

    def check_distribution_shift(
        self, 
        reading: SensorReading, 
        node: KnowledgeNode, 
        threshold: float = 3.0
    ) -> Tuple[bool, float]:
        """
        Determines if the current reading is OOD relative to the Knowledge Node.
        
        Args:
            reading (SensorReading): Current sensor input.
            node (KnowledgeNode): The current active cognitive node.
            threshold (float): Sensitivity threshold (sigma levels).
            
        Returns:
            Tuple[bool, float]: (Is OOD, Score)
        """
        try:
            # Extract features in order
            feature_keys = ['vibration', 'temperature', 'acoustic_emission']
            observed_values = np.array([getattr(reading, k) for k in feature_keys])
            
            # Extract node statistics
            means = np.array([node.feature_stats[k]['mean'] for k in feature_keys])
            stds = np.array([node.feature_stats[k]['std'] for k in feature_keys])
            
            # Simplified diagonal covariance for robustness in this example
            # In production, full covariance matrix should be used
            cov_inv = np.diag(1.0 / (stds ** 2))
            
            score = self.calculate_mahalanobis_distance(observed_values, means, cov_inv)
            
            is_ood = score > threshold
            
            if is_ood:
                logger.warning(f"OOD Detected! Score: {score:.2f} (Threshold: {threshold})")
            
            return is_ood, score
            
        except KeyError as e:
            logger.error(f"Missing feature in Knowledge Node: {e}")
            return False, 0.0
        except Exception as e:
            logger.error(f"Error during OOD check: {e}")
            return False, 0.0


class CognitiveController:
    """
    Manages the lifecycle of Knowledge Nodes and the reconstruction loop.
    """
    
    def __init__(self, initial_node: Optional[KnowledgeNode] = None):
        self.active_node = initial_node
        self.ood_detector = OODDetector()
        self.request_queue: List[ReconstructionRequest] = []
        
    def validate_environment(self, reading: SensorReading) -> bool:
        """
        Validates current environment against the active cognitive node.
        
        Returns:
            bool: True if environment is valid/consistent, False if node is invalid.
        """
        if not self.active_node:
            logger.error("No active Knowledge Node loaded.")
            return False
            
        logger.info(f"Validating environment for Batch: {reading.batch_id}")
        
        is_ood, score = self.ood_detector.check_distribution_shift(reading, self.active_node)
        
        if is_ood:
            # Trigger the cognitive cycle: Doubt -> Failure -> Request
            return self.process_cognitive_failure(reading, score)
            
        # Update node validation timestamp
        self.active_node.last_validated = datetime.now()
        logger.info("Environment validated. Node remains active.")
        return True

    def process_cognitive_failure(self, reading: SensorReading, anomaly_score: float) -> bool:
        """
        Handles the logic for 'Self-Destruct' and 'Reconstruction Request'.
        
        Args:
            reading (SensorReading): The anomalous data.
            anomaly_score (float): The calculated OOD score.
            
        Returns:
            bool: False indicating current node is obsolete.
        """
        logger.critical(
            f"Cognitive Failure detected for Node {self.active_node.node_id}. "
            f"Anomaly Score: {anomaly_score:.4f}"
        )
        
        # 1. Deactivate old node (Symbolic 'Self-Destruct')
        self.active_node.is_active = False
        logger.info(f"Node {self.active_node.node_id} deactivated pending reconstruction.")
        
        # 2. Create Reconstruction Request (Bottom-Up request)
        request = ReconstructionRequest(
            failed_node_id=self.active_node.node_id,
            trigger_cause="Distribution Shift / Tool Wear / Batch Variance",
            anomaly_data={
                "reading": reading.dict(),
                "score": anomaly_score
            },
            priority=9  # High priority
        )
        
        # 3. Queue request
        self._queue_reconstruction_request(request)
        
        return False

    def _queue_reconstruction_request(self, request: ReconstructionRequest) -> None:
        """
        Helper function to manage internal queue.
        """
        self.request_queue.append(request)
        logger.info(f"New Reconstruction Request queued: ID {request.failed_node_id}")

    def update_active_node(self, new_node: KnowledgeNode) -> None:
        """
        Replaces the active node with a new one (Reconstruction Complete).
        """
        self.active_node = new_node
        logger.info(f"Active Node updated to: {new_node.node_id} v{new_node.version}")


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Initialize a baseline Knowledge Node (Simulating existing knowledge)
    # Represents a state where vibration is ~5, temp ~50, acoustic ~20
    baseline_stats = {
        'vibration': {'mean': 5.0, 'std': 0.5},
        'temperature': {'mean': 50.0, 'std': 2.0},
        'acoustic_emission': {'mean': 20.0, 'std': 1.0}
    }
    
    initial_node = KnowledgeNode(
        node_id="CNC_Mill_Model_01",
        feature_stats=baseline_stats
    )
    
    # 2. Initialize Cognitive Controller
    controller = CognitiveController(initial_node=initial_node)
    
    # 3. Simulate Sensor Data (Normal)
    normal_reading = SensorReading(
        vibration=5.2,
        temperature=51.0,
        acoustic_emission=20.5,
        batch_id="BATCH_A_01"
    )
    
    print("\n--- Testing Normal Scenario ---")
    controller.validate_environment(normal_reading)
    
    # 4. Simulate Industrial Dynamism (Tool Wear / Batch Change)
    # Vibration increases significantly, temperature rises
    # This represents data OUTSIDE the training distribution of the current node.
    ood_reading = SensorReading(
        vibration=12.5,  # Significant deviation (> 3 sigma)
        temperature=65.0,
        acoustic_emission=30.0,
        batch_id="BATCH_B_99"
    )
    
    print("\n--- Testing OOD Scenario (Tool Wear) ---")
    is_valid = controller.validate_environment(ood_reading)
    
    if not is_valid:
        print(f"System state invalid. Pending reconstruction: {len(controller.request_queue)} tasks.")
        
        # Simulate AGI 'Bottom-Up' Learning creating a new node
        new_stats = {
            'vibration': {'mean': 12.0, 'std': 1.0},
            'temperature': {'mean': 64.0, 'std': 2.0},
            'acoustic_emission': {'mean': 30.0, 'std': 1.5}
        }
        new_node = KnowledgeNode(
            node_id="CNC_Mill_Model_01",
            version=2.0,
            feature_stats=new_stats
        )
        
        # Update the controller
        controller.update_active_node(new_node)
        
        # Re-validate
        print("\n--- Retesting with New Model ---")
        controller.validate_environment(ood_reading)