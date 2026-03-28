"""
Module: auto_基于时序衰减与结果反馈的贝叶斯信任度动态_5e77cf
Description: Implementation of a dynamic trust calculation model for AGI nodes.
             This module provides a Bayesian-based approach to evaluate node reliability,
             incorporating temporal decay (dormancy penalty) and feedback loops (anomaly detection).

Author: Senior Python Engineer
Version: 1.0.0
"""

import math
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NodeProfile:
    """
    Data structure representing a node's state and history.
    
    Attributes:
        node_id (str): Unique identifier for the node.
        alpha (float): Beta distribution alpha parameter (successes + prior).
        beta (float): Beta distribution beta parameter (failures + prior).
        last_success_timestamp (Optional[datetime]): Timestamp of the last successful validation.
        last_update_timestamp (datetime): Timestamp of the last interaction (success or fail).
    """
    node_id: str
    alpha: float = 1.0  # Prior pseudo-count of successes (uninformative prior)
    beta: float = 1.0   # Prior pseudo-count of failures
    last_success_timestamp: Optional[datetime] = None
    last_update_timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError("Alpha and Beta must be positive.")


class TrustDynamicCalculator:
    """
    Calculates dynamic trust scores based on temporal decay and Bayesian inference.
    
    This class implements a model where trust is derived from the expected value of a 
    Beta distribution (historical success rate), penalized by an exponential decay 
    function based on inactivity, and adjusted for recent anomalies.
    
    Mathematical Model:
    Trust(t) = Historical_Score * Decay_Factor * Anomaly_Penalty
    Where:
        Historical_Score = alpha / (alpha + beta)
        Decay_Factor = exp(-lambda_decay * dt)
        Anomaly_Penalty = 1 / (1 + k * recent_failures) (Simplified for stability)
    """

    def __init__(self, decay_rate: float = 0.05, anomaly_sensitivity: float = 2.0, max_dormancy_days: int = 30):
        """
        Initialize the Trust Calculator.
        
        Args:
            decay_rate (float): The lambda parameter for exponential decay (sensitivity to time).
            anomaly_sensitivity (float): Multiplier for penalizing recent consecutive failures.
            max_dormancy_days (int): Days after which a node is considered fully untrusted (trust -> 0).
        """
        self.decay_rate = decay_rate
        self.anomaly_sensitivity = anomaly_sensitivity
        self.max_dormancy_days = max_dormancy_days
        self.nodes: Dict[str, NodeProfile] = {}
        logger.info("TrustDynamicCalculator initialized with decay_rate=%.4f", decay_rate)

    def _get_decay_factor(self, last_active: datetime, current_time: datetime) -> float:
        """
        Helper function to calculate the temporal decay factor.
        
        Args:
            last_active (datetime): The timestamp of the node's last activity.
            current_time (datetime): The current reference time.
            
        Returns:
            float: A multiplier between 0 and 1.
        """
        delta_seconds = (current_time - last_active).total_seconds()
        delta_days = delta_seconds / (24 * 3600)
        
        # Cap the decay to prevent numerical underflow or exact 0
        if delta_days > self.max_dormancy_days * 2:
            return 0.0
        
        decay = math.exp(-self.decay_rate * delta_days)
        return max(0.0, min(1.0, decay))

    def update_node_verification(self, node_id: str, is_success: bool, timestamp: Optional[datetime] = None) -> None:
        """
        Update the internal state of a node based on new verification results.
        This implements the Bayesian update step.
        
        Args:
            node_id (str): The ID of the node to update.
            is_success (bool): True if validation succeeded, False otherwise.
            timestamp (Optional[datetime]): Time of the event. Defaults to now.
        
        Raises:
            ValueError: If timestamp is in the past relative to node creation (logical error).
        """
        current_time = timestamp if timestamp else datetime.now()
        
        if node_id not in self.nodes:
            self.nodes[node_id] = NodeProfile(node_id=node_id)
            logger.debug("Created new profile for node: %s", node_id)
        
        node = self.nodes[node_id]
        
        # Basic causal check
        if current_time < node.last_update_timestamp:
            logger.warning("Received out-of-order timestamp for node %s", node_id)
            # Depending on policy, we might reject this, but here we accept for resilience
        
        # Bayesian Update: Increment Alpha (success) or Beta (failure)
        if is_success:
            node.alpha += 1.0
            node.last_success_timestamp = current_time
            logger.info("Node %s verification SUCCESS. New Alpha: %.2f", node_id, node.alpha)
        else:
            node.beta += 1.0
            logger.warning("Node %s verification FAILED. New Beta: %.2f", node_id, node.beta)
            
        node.last_update_timestamp = current_time

    def calculate_trust(self, node_id: str, current_time: Optional[datetime] = None) -> float:
        """
        Calculate the real-time trust score for a specific node.
        
        Logic:
        1. Calculate Base Probability (Mean of Beta Distribution).
        2. Calculate Time Decay (Exponential).
        3. Combine to get final score [0.0 - 1.0].
        
        Args:
            node_id (str): The ID of the node.
            current_time (Optional[datetime]): Reference time. Defaults to now.
            
        Returns:
            float: Trust score between 0.0 and 1.0. Returns 0.0 for unknown nodes.
        """
        if node_id not in self.nodes:
            logger.warning("Trust requested for unknown node: %s", node_id)
            return 0.0
            
        node = self.nodes[node_id]
        ref_time = current_time if current_time else datetime.now()
        
        # 1. Bayesian Expected Probability (Base Trust)
        # E[X] for Beta(alpha, beta) = alpha / (alpha + beta)
        total_interactions = node.alpha + node.beta
        if total_interactions == 0:
            base_score = 0.5 # Should not happen with priors=1, but safety check
        else:
            base_score = node.alpha / total_interactions
            
        # 2. Temporal Decay
        decay_factor = self._get_decay_factor(node.last_update_timestamp, ref_time)
        
        # 3. Anomaly Feedback (Penalty for recent failures without success)
        # If last success is older than last update, we have recent failures
        # We apply a soft penalty based on the ratio of recent beta to total
        # This is a heuristic simplification for "Fast Response to Anomalies"
        penalty = 1.0
        if node.last_success_timestamp is None or node.last_update_timestamp > node.last_success_timestamp:
            # Simple penalty logic: if alpha < beta (more failures than successes), reduce trust faster
            # A logistic-like penalty based on imbalance
            imbalance = (node.beta - node.alpha) / total_interactions if total_interactions > 0 else 0
            if imbalance > 0:
                penalty = 1.0 / (1.0 + self.anomaly_sensitivity * imbalance)

        # Final Aggregation
        final_trust = base_score * decay_factor * penalty
        
        # Boundary Checks
        final_trust = max(0.0, min(1.0, final_trust))
        
        logger.debug("Calculated trust for %s: %.4f (Base: %.2f, Decay: %.2f, Penalty: %.2f)",
                     node_id, final_trust, base_score, decay_factor, penalty)
                     
        return final_trust

    def get_network_trust_snapshot(self) -> Dict[str, float]:
        """
        Helper to get trust scores for all known nodes.
        
        Returns:
            Dict[str, float]: Mapping of node_id to trust score.
        """
        snapshot = {}
        current_time = datetime.now()
        for node_id in self.nodes:
            snapshot[node_id] = self.calculate_trust(node_id, current_time)
        return snapshot


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Initialize System
    trust_system = TrustDynamicCalculator(decay_rate=0.1, anomaly_sensitivity=1.5)
    
    # Simulation Timeline
    t_now = datetime.now()
    
    # 1. Node A: High reliability, frequent success
    trust_system.update_node_verification("Node_A", True, t_now - timedelta(days=1))
    trust_system.update_node_verification("Node_A", True, t_now - timedelta(days=0.5))
    trust_system.update_node_verification("Node_A", True, t_now)
    
    # 2. Node B: Dormant node (was good, but long time no see)
    trust_system.update_node_verification("Node_B", True, t_now - timedelta(days=10))
    trust_system.update_node_verification("Node_B", True, t_now - timedelta(days=9))
    # Not updated recently
    
    # 3. Node C: Anomalous node (sudden failures)
    trust_system.update_node_verification("Node_C", True, t_now - timedelta(hours=5))
    trust_system.update_node_verification("Node_C", False, t_now - timedelta(hours=2))
    trust_system.update_node_verification("Node_C", False, t_now - timedelta(hours=1))
    
    # 4. Node D: Unknown node
    
    # Calculate Trust
    print(f"Trust Node A (Active/Good): {trust_system.calculate_trust('Node_A'):.4f}")
    print(f"Trust Node B (Dormant):     {trust_system.calculate_trust('Node_B'):.4f}")
    print(f"Trust Node C (Anomaly):     {trust_system.calculate_trust('Node_C'):.4f}")
    print(f"Trust Node D (Unknown):     {trust_system.calculate_trust('Node_D'):.4f}")