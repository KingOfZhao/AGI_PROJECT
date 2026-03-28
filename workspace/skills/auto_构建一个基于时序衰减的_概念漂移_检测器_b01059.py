"""
Module: temporal_concept_drift_detector
Description: A system for detecting concept drift in cognitive nodes using time-decay models.
             This module evaluates the validity of knowledge nodes based on temporal dynamics,
             environmental changes, and error feedback.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CognitiveNode:
    """
    Represents a unit of knowledge or a skill node in the AGI system.
    
    Attributes:
        node_id (str): Unique identifier for the node.
        last_validated (datetime): Timestamp of the last successful validation.
        creation_time (datetime): Timestamp of node creation.
        total_invocations (int): Total number of times the node was used.
        error_count (int): Number of errors encountered during usage.
        env_param_change_rate (float): Rate of change in relevant environment parameters (0.0 to 1.0).
    """
    node_id: str
    last_validated: datetime
    creation_time: datetime
    total_invocations: int
    error_count: int
    env_param_change_rate: float = 0.0

    def __post_init__(self):
        """Validate data types and constraints after initialization."""
        if not isinstance(self.last_validated, datetime):
            raise ValueError("last_validated must be a datetime object")
        if self.total_invocations < 0 or self.error_count < 0:
            raise ValueError("Invocation and error counts must be non-negative")
        if not 0.0 <= self.env_param_change_rate <= 1.0:
            raise ValueError("Environment change rate must be between 0.0 and 1.0")


class ConceptDriftDetector:
    """
    Detects concept drift in cognitive nodes based on temporal decay, environmental changes,
    and error feedback. Implements a half-life decay model to determine node obsolescence.
    """

    def __init__(self, 
                 base_half_life_days: float = 30.0, 
                 decay_threshold: float = 0.2,
                 error_weight: float = 0.5, 
                 env_weight: float = 0.5):
        """
        Initialize the detector with configuration parameters.
        
        Args:
            base_half_life_days (float): Base half-life of a node in days without modifiers.
            decay_threshold (float): The value below which a node is considered 'drifted' (0.0 to 1.0).
            error_weight (float): Weight of error frequency in reducing half-life.
            env_weight (float): Weight of environment change in reducing half-life.
        """
        if not (0.0 < base_half_life_days):
            raise ValueError("base_half_life_days must be positive")
        if not (0.0 <= decay_threshold <= 1.0):
            raise ValueError("decay_threshold must be between 0.0 and 1.0")
            
        self.base_half_life_days = base_half_life_days
        self.decay_threshold = decay_threshold
        self.error_weight = error_weight
        self.env_weight = env_weight
        logger.info(f"ConceptDriftDetector initialized with base_half_life={base_half_life_days} days")

    def _calculate_modified_half_life(self, node: CognitiveNode) -> float:
        """
        Internal helper function to calculate the effective half-life based on modifiers.
        
        The half-life is reduced if the error rate is high or if the environment is changing rapidly.
        
        Args:
            node (CognitiveNode): The node to evaluate.
            
        Returns:
            float: The modified half-life in days.
        """
        # Calculate Error Factor (ranges from 0 to 1, higher errors -> higher factor)
        # We add epsilon to avoid division by zero
        epsilon = 1e-9
        error_rate = node.error_count / (node.total_invocations + epsilon)
        error_factor = math.tanh(error_rate * 10) * self.error_weight

        # Calculate Environment Factor (direct mapping)
        env_factor = node.env_param_change_rate * self.env_weight

        # Total stress on the node reduces its half-life
        # The reduction factor is cumulative
        reduction_factor = 1.0 - min(0.9, error_factor + env_factor) # Cap reduction at 90% to avoid instant death
        
        effective_half_life = self.base_half_life_days * reduction_factor
        return max(1.0, effective_half_life) # Ensure minimum half-life of 1 day

    def calculate_reliability_score(self, 
                                    node: CognitiveNode, 
                                    current_time: datetime) -> float:
        """
        Calculates the current reliability score of a node based on the exponential decay formula.
        
        Formula: Score = e ^ (-lambda * t), where lambda = ln(2) / half_life
        
        Args:
            node (CognitiveNode): The node to evaluate.
            current_time (datetime): The current timestamp for comparison.
            
        Returns:
            float: Reliability score between 0.0 and 1.0.
            
        Raises:
            ValueError: If current_time precedes last_validated time.
        """
        if current_time < node.last_validated:
            logger.error(f"Time travel detected: current_time {current_time} < last_validated {node.last_validated}")
            raise ValueError("Current time cannot be before last validation time")

        time_diff = current_time - node.last_validated
        days_elapsed = time_diff.total_seconds() / (3600 * 24)

        half_life = self._calculate_modified_half_life(node)
        
        # Exponential Decay Formula
        # If half_life is T, then lambda = ln(2)/T
        # N(t) = N0 * e^(-lambda * t)
        try:
            decay_constant = math.log(2) / half_life
            score = math.exp(-decay_constant * days_elapsed)
        except OverflowError:
            score = 0.0
            logger.warning(f"Overflow during score calculation for node {node.node_id}")

        logger.debug(f"Node {node.node_id}: Days elapsed={days_elapsed:.2f}, Half-life={half_life:.2f}, Score={score:.4f}")
        return score

    def check_drift(self, 
                    node: CognitiveNode, 
                    current_time: datetime) -> Dict[str, Any]:
        """
        Main interface function to check if a concept drift has occurred (Circuit Breaker trigger).
        
        Args:
            node (CognitiveNode): The node to check.
            current_time (datetime): The current timestamp.
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'node_id': str
                - 'reliability_score': float
                - 'is_drifted': bool
                - 'action': str ('NONE', 'WARNING', 'CIRCUIT_BREAK')
                - 'message': str
        """
        try:
            score = self.calculate_reliability_score(node, current_time)
            is_drifted = score < self.decay_threshold
            
            action = "NONE"
            message = "Node is stable."
            
            if is_drifted:
                action = "CIRCUIT_BREAK"
                message = f"Circuit breaker triggered. Reliability {score:.4f} below threshold {self.decay_threshold}."
                logger.warning(f"DRIFT DETECTED for node {node.node_id}: {message}")
            elif score < self.decay_threshold * 1.2: # Approaching threshold
                action = "WARNING"
                message = "Node reliability is approaching critical threshold."
                logger.info(f"Warning for node {node.node_id}: Reliability low.")

            return {
                "node_id": node.node_id,
                "reliability_score": round(score, 4),
                "is_drifted": is_drifted,
                "action": action,
                "message": message,
                "timestamp": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking drift for node {node.node_id}: {str(e)}")
            return {
                "node_id": node.node_id,
                "error": str(e),
                "action": "ERROR"
            }


# --- Utility Functions ---

def create_sample_node(node_id: str, days_since_validation: int, error_count: int) -> CognitiveNode:
    """
    Helper function to create mock cognitive nodes for testing.
    
    Args:
        node_id (str): ID of the node.
        days_since_validation (int): How many days ago the node was last valid.
        error_count (int): Number of errors.
        
    Returns:
        CognitiveNode: A configured node instance.
    """
    now = datetime.now()
    return CognitiveNode(
        node_id=node_id,
        last_validated=now - timedelta(days=days_since_validation),
        creation_time=now - timedelta(days=days_since_validation + 100),
        total_invocations=1000,
        error_count=error_count,
        env_param_change_rate=0.1 # Default low change rate
    )

def batch_check_drift(nodes: List[CognitiveNode], detector: ConceptDriftDetector) -> List[Dict[str, Any]]:
    """
    Evaluates a list of nodes and returns drift reports.
    
    Args:
        nodes (List[CognitiveNode]): List of nodes to check.
        detector (ConceptDriftDetector): The detector instance.
        
    Returns:
        List[Dict[str, Any]]: List of drift reports.
    """
    results = []
    current_time = datetime.now()
    
    logger.info(f"Starting batch drift detection for {len(nodes)} nodes.")
    
    for node in nodes:
        report = detector.check_drift(node, current_time)
        results.append(report)
        
    return results


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize the detector
    # Let's say we expect nodes to be valid for about 60 days (base half life)
    # We trigger circuit breaker if reliability drops below 25%
    drift_detector = ConceptDriftDetector(
        base_half_life_days=60.0, 
        decay_threshold=0.25
    )

    # 2. Create sample data
    # Node A: Freshly updated (Should be safe)
    node_a = create_sample_node("API_V2_Call", days_since_validation=5, error_count=2)
    
    # Node B: Old but gold (Low errors, but time passed) - 60 days old
    node_b = create_sample_node("Physics_Law_Newton", days_since_validation=60, error_count=5)
    
    # Node C: High error rate (Effectively reduces half-life, causing faster drift)
    # Let's manually tweak env rate for this one
    node_c = create_sample_node("Legacy_DB_Schema", days_since_validation=30, error_count=0)
    node_c.env_param_change_rate = 0.8 # Environment (DB schema) is changing fast

    # 3. Perform detection
    nodes_to_check = [node_a, node_b, node_c]
    reports = batch_check_drift(nodes_to_check, drift_detector)

    # 4. Print Results
    print("-" * 50)
    print(f"{'NODE ID':<20} | {'SCORE':<10} | {'ACTION':<15} | {'MESSAGE'}")
    print("-" * 50)
    for report in reports:
        if 'error' not in report:
            print(f"{report['node_id']:<20} | {report['reliability_score']:<10.4f} | {report['action']:<15} | {report['message']}")
        else:
            print(f"{report['node_id']:<20} | ERROR")
    print("-" * 50)