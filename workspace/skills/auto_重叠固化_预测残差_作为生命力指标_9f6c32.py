"""
Module: auto_重叠固化_预测残差_作为生命力指标_9f6c32
Description: Implements a vitality assessment mechanism based on prediction residuals.
             In an AGI or complex adaptive system, a node's "liveness" or "health"
             is defined by its ability to accurately anticipate future inputs.
             This module calculates residuals between predicted and actual values,
             updating a vitality score. Nodes with deteriorating prediction accuracy
             (expanding residuals) are flagged for retirement.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from collections import deque
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type aliases for clarity
Vector = Union[List[float], np.ndarray]
NodeID = str


class PredictionNode:
    """
    Represents a cognitive node in the system that generates predictions.
    It maintains a history of errors to calculate vitality.
    """
    def __init__(self, node_id: NodeID, history_length: int = 10, penalty_factor: float = 1.5):
        """
        Initialize the PredictionNode.
        
        Args:
            node_id (NodeID): Unique identifier for the node.
            history_length (int): Size of the sliding window for calculating moving average error.
            penalty_factor (float): Multiplier for increasing vitality penalty when errors grow.
        """
        self.node_id = node_id
        self.history_length = history_length
        self.penalty_factor = penalty_factor
        
        # State variables
        self._error_history: deque = deque(maxlen=history_length)
        self._vitality_score: float = 100.0  # Start with full health
        self._last_prediction: Optional[float] = None
        self._is_active: bool = True
        
        logger.debug(f"Node {node_id} initialized with vitality {self._vitality_score}")

    @property
    def vitality(self) -> float:
        """Returns the current vitality score."""
        return self._vitality_score

    @property
    def is_active(self) -> bool:
        """Returns whether the node is still considered active."""
        return self._is_active

    def update_state(self, prediction: float, actual: float) -> float:
        """
        Core function to update the node's state based on prediction performance.
        
        Args:
            prediction (float): The value predicted by the node.
            actual (float): The actual observed value.
            
        Returns:
            float: The calculated residual (absolute error).
        """
        if not self._is_active:
            logger.warning(f"Attempted to update inactive node {self.node_id}")
            return 0.0

        # 1. Calculate Residual
        residual = abs(prediction - actual)
        self._error_history.append(residual)
        
        # 2. Update Vitality Score
        self._calculate_vitality()
        
        logger.info(
            f"Node {self.node_id} | Pred: {prediction:.2f} | Actual: {actual:.2f} | "
            f"Residual: {residual:.4f} | Vitality: {self._vitality_score:.2f}"
        )
        
        return residual

    def _calculate_vitality(self) -> None:
        """
        Internal helper to adjust vitality based on error trends.
        
        Logic:
        - Calculate Mean Absolute Error (MAE) trend.
        - If recent errors are higher than older errors, decrease vitality significantly.
        - If errors are stable or decreasing, recover vitality slowly.
        """
        if len(self._error_history) < 3:
            return  # Not enough data to determine trend

        errors = np.array(self._error_history)
        
        # Split history into two halves to compare trend
        mid = len(errors) // 2
        old_avg = np.mean(errors[:mid])
        new_avg = np.mean(errors[mid:])
        
        # Calculate trend direction (positive means worsening errors)
        error_delta = new_avg - old_avg
        
        if error_delta > 0:
            # Worsening predictions: Penalize heavily
            penalty = error_delta * self.penalty_factor
            self._vitality_score -= penalty
            logger.debug(f"Node {self.node_id} worsening. Penalty: {penalty:.2f}")
        else:
            # Improving/Stable predictions: Recover slightly
            recovery = 0.5  # Flat recovery rate for stability
            self._vitality_score += recovery
            logger.debug(f"Node {self.node_id} stable/improving. Recovery: {recovery:.2f}")

        # Boundary Checks
        self._vitality_score = max(0.0, min(100.0, self._vitality_score))
        
        # Check for deactivation
        if self._vitality_score <= 0:
            self._deactivate()

    def _deactivate(self) -> None:
        """
        Marks the node for retirement.
        """
        self._is_active = False
        logger.warning(f"NODE TERMINATED: {self.node_id} vitality dropped to zero.")


def validate_input_data(data: Dict[str, Tuple[float, float]]) -> bool:
    """
    Validates the structure and content of the input data batch.
    
    Args:
        data (Dict): Dictionary mapping node_id to (prediction, actual) tuples.
        
    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary.")
    
    for node_id, values in data.items():
        if not isinstance(values, (tuple, list)) or len(values) != 2:
            raise ValueError(f"Data for node {node_id} must be a tuple of (prediction, actual).")
        
        pred, act = values
        if not (isinstance(pred, (int, float)) and isinstance(act, (int, float))):
            raise ValueError(f"Values for node {node_id} must be numeric.")
            
        if np.isnan(pred) or np.isnan(act) or np.isinf(pred) or np.isinf(act):
            raise ValueError(f"Values for node {node_id} contain NaN or Infinity.")
            
    return True


def system_health_check(nodes: Dict[NodeID, PredictionNode]) -> Dict[str, Union[float, List[NodeID]]]:
    """
    Aggregates the status of all nodes to determine overall system health.
    
    Args:
        nodes (Dict[NodeID, PredictionNode]): Dictionary of active node objects.
        
    Returns:
        Dict containing average vitality, active count, and list of dead nodes.
    """
    if not nodes:
        return {"avg_vitality": 0.0, "active_nodes": 0, "dead_nodes": []}

    vitalities = []
    dead_nodes = []
    
    for node_id, node in nodes.items():
        if node.is_active:
            vitalities.append(node.vitality)
        else:
            dead_nodes.append(node_id)
            
    avg_vitality = np.mean(vitalities) if vitalities else 0.0
    
    return {
        "avg_vitality": float(avg_vitality),
        "active_nodes": len(vitalities),
        "dead_nodes": dead_nodes
    }


def run_simulation_step(
    node_registry: Dict[NodeID, PredictionNode], 
    data_batch: Dict[NodeID, Tuple[float, float]]
) -> None:
    """
    Executes a single simulation step for the AGI subsystem.
    
    Args:
        node_registry (Dict): The global registry of nodes.
        data_batch (Dict): New input data (pred/actual pairs).
    """
    try:
        validate_input_data(data_batch)
    except ValueError as e:
        logger.error(f"Input validation failed: {e}")
        return

    for node_id, (pred, actual) in data_batch.items():
        if node_id in node_registry:
            node = node_registry[node_id]
            if node.is_active:
                node.update_state(pred, actual)
        else:
            logger.warning(f"Received data for unknown node: {node_id}")


# --- Usage Example ---
if __name__ == "__main__":
    # Setup
    logger.info("Initializing AGI Subsystem: Residual Vitality Monitor")
    
    # Create a registry of nodes
    registry = {
        "market_analyst_01": PredictionNode("market_analyst_01", history_length=5),
        "weather_bot_02": PredictionNode("weather_bot_02", history_length=5),
        "traffic_sensor_03": PredictionNode("traffic_sensor_03", history_length=5)
    }

    # Simulation Step 1: Good predictions
    print("\n--- Step 1: Accurate Predictions ---")
    batch_1 = {
        "market_analyst_01": (100.0, 100.5),
        "weather_bot_02": (25.0, 25.1),
        "traffic_sensor_03": (10.0, 10.0)
    }
    run_simulation_step(registry, batch_1)

    # Simulation Step 2: Market analyst starts failing
    print("\n--- Step 2: Diverging Predictions ---")
    batch_2 = {
        "market_analyst_01": (100.0, 102.0), # Residual 2.0
        "weather_bot_02": (25.0, 25.0),
        "traffic_sensor_03": (10.0, 10.2)
    }
    run_simulation_step(registry, batch_2)

    # Simulation Step 3: Market analyst fails catastrophically
    print("\n--- Step 3: Catastrophic Failure ---")
    batch_3 = {
        "market_analyst_01": (100.0, 150.0), # Residual 50.0
        "weather_bot_02": (25.0, 24.9),
        "traffic_sensor_03": (10.0, 10.1)
    }
    run_simulation_step(registry, batch_3)

    # System Health Report
    print("\n--- System Health Report ---")
    health = system_health_check(registry)
    print(f"Average Vitality: {health['avg_vitality']:.2f}")
    print(f"Active Nodes: {health['active_nodes']}")
    print(f"Terminated Nodes: {health['dead_nodes']}")