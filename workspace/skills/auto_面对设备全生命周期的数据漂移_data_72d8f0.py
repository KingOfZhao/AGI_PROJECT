"""
Module: auto_面对设备全生命周期的数据漂移_data_72d8f0

This module provides a robust framework for detecting data drift in industrial
equipment lifecycles and managing the validity of operational "nodes" (or models).
It implements a NodeDecayManager that monitors statistical distributions,
detects when a previously optimal parameter node becomes sub-optimal due to
equipment aging or environment changes, and triggers a self-healing process
(re-training or fine-tuning).

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DriftStatus(Enum):
    """Enumeration for drift status severity."""
    STABLE = "stable"
    WARNING = "warning"
    DRIFT_DETECTED = "drift_detected"


class RelearnAction(Enum):
    """Actions to take when drift is detected."""
    IGNORE = "ignore"
    FINETUNE = "finetune"
    FULL_RETRAIN = "full_retrain"


@dataclass
class NodeProfile:
    """
    Represents a snapshot of a 'Node' (e.g., a model or parameter set).
    
    Attributes:
        node_id: Unique identifier for the node.
        version: Version number of the node.
        baseline_features: Statistical properties of the training data (mean, std).
        performance_threshold: The minimum acceptable performance metric (e.g., accuracy, efficiency).
        last_performance: The most recent performance metric recorded.
        created_timestamp: Creation time (simulated here).
    """
    node_id: str
    version: str
    baseline_features: Dict[str, Tuple[float, float]]  # feature_name: (mean, std)
    performance_threshold: float = 0.85
    last_performance: float = 1.0
    created_timestamp: float = 0.0


@dataclass
class DriftReport:
    """
    Contains the results of a drift detection analysis.
    """
    status: DriftStatus
    p_value: float
    statistic: float
    recommendation: RelearnAction
    message: str


def _validate_input_data(data: np.ndarray, feature_name: str) -> np.ndarray:
    """
    Helper function to validate and clean input data.
    
    Args:
        data: Input numpy array.
        feature_name: Name of the feature for logging purposes.
        
    Returns:
        Cleaned numpy array (flattened).
        
    Raises:
        ValueError: If data is empty or contains non-numeric types.
    """
    if data is None or len(data) == 0:
        raise ValueError(f"Input data for feature '{feature_name}' cannot be empty.")
    
    # Ensure it is a flat numpy array of floats
    try:
        cleaned = np.array(data, dtype=np.float64).flatten()
    except ValueError as e:
        logger.error(f"Type conversion error in feature '{feature_name}': {e}")
        raise ValueError(f"Data for '{feature_name}' must be numeric.")
        
    # Handle NaNs or Infs if any (imputation strategy: remove or mean, here we remove)
    if np.any(np.isnan(cleaned)) or np.any(np.isinf(cleaned)):
        logger.warning(f"NaNs or Infs detected in '{feature_name}'. Filtering them out.")
        cleaned = cleaned[~np.isnan(cleaned) & ~np.isinf(cleaned)]
        
    if len(cleaned) == 0:
        raise ValueError(f"Feature '{feature_name}' became empty after cleaning.")
        
    return cleaned


def calculate_ks_drift_score(
    reference_data: np.ndarray, 
    current_data: np.ndarray, 
    alpha: float = 0.05
) -> Tuple[float, float, bool]:
    """
    Calculates the Kolmogorov-Smirnov statistic to detect distribution drift.
    
    Args:
        reference_data: The baseline historical data distribution.
        current_data: The new incoming data distribution.
        alpha: Significance level (default 0.05).
        
    Returns:
        Tuple containing (statistic, p_value, is_drifted).
    """
    # Data validation
    ref_clean = _validate_input_data(reference_data, "reference_data")
    cur_clean = _validate_input_data(current_data, "current_data")
    
    # Perform KS test
    statistic, p_value = stats.ks_2samp(ref_clean, cur_clean)
    
    # Determine drift
    is_drifted = p_value < alpha
    
    logger.debug(f"KS Test: statistic={statistic:.4f}, p_value={p_value:.4f}, drift={is_drifted}")
    return statistic, p_value, is_drifted


class NodeDecayManager:
    """
    Manages the lifecycle and validity of equipment parameter nodes.
    
    This class monitors data streams against baseline node profiles. It detects
    data drift (environmental changes) and concept drift (performance decay),
    triggering specific relearning workflows.
    """

    def __init__(self, sensitivity: float = 0.05):
        """
        Initialize the NodeDecayManager.
        
        Args:
            sensitivity: The alpha value for statistical significance tests.
        """
        self.sensitivity = sensitivity
        self.managed_nodes: Dict[str, NodeProfile] = {}
        logger.info("NodeDecayManager initialized with sensitivity %.3f", sensitivity)

    def register_node(self, node: NodeProfile) -> None:
        """Register a new node profile to be monitored."""
        if not isinstance(node, NodeProfile):
            raise TypeError("Must register a NodeProfile object.")
        self.managed_nodes[node.node_id] = node
        logger.info("Node registered: %s (v%s)", node.node_id, node.version)

    def analyze_node_validity(
        self, 
        node_id: str, 
        current_data_window: Dict[str, np.ndarray], 
        current_performance: Optional[float] = None
    ) -> DriftReport:
        """
        Analyzes if a specific node is still valid given current data and performance.
        
        This function checks for:
        1. Data Drift: Has the input distribution changed? (using KS test)
        2. Performance Decay: Is the node's output quality degrading?
        
        Args:
            node_id: The ID of the node to check.
            current_data_window: Dictionary mapping feature names to current data arrays.
            current_performance: Optional float representing current operational efficiency.
            
        Returns:
            DriftReport: A detailed report on the node's status.
        """
        if node_id not in self.managed_nodes:
            logger.error("Node ID %s not found.", node_id)
            raise ValueError(f"Node ID {node_id} is not registered.")

        node = self.managed_nodes[node_id]
        logger.info("Analyzing node validity for: %s", node_id)

        # 1. Check Performance Decay (Concept Drift)
        if current_performance is not None:
            node.last_performance = current_performance
            if current_performance < node.performance_threshold:
                msg = (f"Performance decay detected: {current_performance:.3f} < "
                       f"{node.performance_threshold:.3f}")
                logger.warning(msg)
                return DriftReport(
                    status=DriftStatus.DRIFT_DETECTED,
                    p_value=0.0, # Not applicable
                    statistic=current_performance,
                    recommendation=RelearnAction.FULL_RETRAIN,
                    message=msg
                )

        # 2. Check Data Drift
        max_stat = 0.0
        min_p = 1.0
        drift_detected = False
        
        # Validate keys match
        missing_keys = set(node.baseline_features.keys()) - set(current_data_window.keys())
        if missing_keys:
            logger.warning("Missing features in current data window: %s", missing_keys)

        for feature_name, (ref_mean, ref_std) in node.baseline_features.items():
            if feature_name not in current_data_window:
                continue
                
            # Reconstruct reference data assumption or ideally, store a sample
            # Here we generate a synthetic reference for the demo, but in production
            # we would pass actual historical data buffers.
            # NOTE: For KS test, we need the raw data samples, not just mean/std.
            # In a real scenario, node.baseline_features should store a sample buffer.
            # For this demo, we simulate a reference distribution.
            synthetic_ref = np.random.normal(ref_mean, ref_std, 1000)
            
            current_data = current_data_window[feature_name]
            
            try:
                stat, p, is_drift = calculate_ks_drift_score(
                    synthetic_ref, current_data, self.sensitivity
                )
                if is_drift:
                    drift_detected = True
                    logger.info("Drift found in feature: %s (p=%.4f)", feature_name, p)
                
                if p < min_p: min_p = p
                if stat > max_stat: max_stat = stat
                
            except ValueError as e:
                logger.error("Error checking feature %s: %s", feature_name, e)
                continue

        # 3. Determine Action
        if drift_detected:
            status = DriftStatus.DRIFT_DETECTED
            # If drift is significant, fine-tune. If extreme, full retrain.
            # Logic: if p_value is extremely low (< 0.001), distribution shifted heavily
            action = RelearnAction.FINETUNE if min_p > 0.001 else RelearnAction.FULL_RETRAIN
            msg = f"Data drift detected in node {node_id}. Min p-value: {min_p:.5f}"
            logger.warning(msg)
        else:
            status = DriftStatus.STABLE
            action = RelearnAction.IGNORE
            msg = "Node is stable."
            logger.info(msg)

        return DriftReport(
            status=status,
            p_value=min_p,
            statistic=max_stat,
            recommendation=action,
            message=msg
        )

    def trigger_relearning_workflow(self, action: RelearnAction, node_id: str) -> bool:
        """
        Simulates the triggering of a sub-process to update the model parameters.
        
        Args:
            action: The type of relearning action required.
            node_id: The node to update.
            
        Returns:
            bool: True if workflow triggered successfully.
        """
        logger.info(">>> TRIGGERING WORKFLOW: Action=%s for Node=%s <<<", action.value, node_id)
        
        if action == RelearnAction.IGNORE:
            return False
            
        # Simulate updating the node version
        node = self.managed_nodes[node_id]
        current_ver = float(node.version.split('v')[-1])
        node.version = f"v{current_ver + 0.1}"
        
        # In a real AGI system, this would dispatch a task to a training cluster
        # or load a shadow model.
        return True


if __name__ == "__main__":
    # Example Usage
    
    # 1. Setup: Create a baseline node profile
    # Let's assume the sensor usually outputs temp ~20std 2.0, and pressure ~100std 5.0
    baseline_node = NodeProfile(
        node_id="pump_controller_v1",
        version="v1.0",
        baseline_features={
            "temperature": (20.0, 2.0),
            "pressure": (100.0, 5.0)
        },
        performance_threshold=0.80
    )
    
    manager = NodeDecayManager(sensitivity=0.05)
    manager.register_node(baseline_node)
    
    # 2. Scenario A: Normal Operations
    print("\n--- Scenario A: Normal Data ---")
    normal_data = {
        "temperature": np.random.normal(20.1, 2.1, 500),
        "pressure": np.random.normal(99.5, 5.2, 500)
    }
    report_a = manager.analyze_node_validity("pump_controller_v1", normal_data, current_performance=0.95)
    print(f"Result: {report_a.status.value}, Action: {report_a.recommendation.value}")
    
    # 3. Scenario B: Equipment Aging (Data Drift)
    # Temperature rises significantly due to wear
    print("\n--- Scenario B: Data Drift (Aging) ---")
    drifted_data = {
        "temperature": np.random.normal(25.0, 2.5, 500), # Shifted mean
        "pressure": np.random.normal(100.0, 5.0, 500)
    }
    report_b = manager.analyze_node_validity("pump_controller_v1", drifted_data, current_performance=0.82)
    print(f"Result: {report_b.status.value}, Action: {report_b.recommendation.value}")
    
    # 4. Scenario C: Performance Collapse (Concept Drift)
    print("\n--- Scenario C: Performance Collapse ---")
    # Data is normal, but efficiency drops (e.g., mechanical jam)
    normal_data_poor = {
        "temperature": np.random.normal(20.0, 2.0, 500),
        "pressure": np.random.normal(100.0, 5.0, 500)
    }
    report_c = manager.analyze_node_validity("pump_controller_v1", normal_data_poor, current_performance=0.65)
    print(f"Result: {report_c.status.value}, Action: {report_c.recommendation.value}")
    
    if report_c.recommendation != RelearnAction.IGNORE:
        manager.trigger_relearning_workflow(report_c.recommendation, "pump_controller_v1")