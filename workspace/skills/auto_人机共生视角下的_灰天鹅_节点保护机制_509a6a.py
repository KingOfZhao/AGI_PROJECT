"""
Module: auto_人机共生视角下的_灰天鹅_节点保护机制_509a6a

This module implements a protection mechanism for 'Gray Swan' nodes within an AGI system.
In the context of Human-Computer Symbiosis, these nodes represent capabilities that are
statistically insignificant during routine operations (low frequency) but are critically
vital during extreme, rare events (Black Swan events).

Standard optimization algorithms often prune these nodes due to low ROI in the short term.
This module introduces a 'Scenario Scarcity' vs 'Value Density' balancing function to
override statistical pruning, ensuring the system retains the ability to handle
rare, high-stakes scenarios.

Key Concepts:
- Gray Swan Node: Low call frequency, High criticality value.
- Scenario Scarcity: How rare the trigger condition is.
- Value Density: The utility provided when the trigger condition is met.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration Constants
DEFAULT_PRUNE_THRESHOLD = 0.1
SCARCITY_WEIGHT = 0.6
DENSITY_WEIGHT = 0.4
MIN_RETENTION_SCORE = 0.25


@dataclass
class NodeTelemetry:
    """
    Represents the telemetry data for a single AGI capability node.
    
    Attributes:
        node_id: Unique identifier for the node.
        total_invocations: Total number of times the node has been called.
        critical_successes: Number of successful executions in 'critical' scenarios.
        last_invocation_time: Timestamp of the last call.
        is_critical_infrastructure: Flag indicating if the node is vital for system integrity.
        decay_rate: How fast the node's activity history fades (gamma).
    """
    node_id: str
    total_invocations: int = 0
    critical_successes: int = 0
    last_invocation_time: Optional[datetime] = None
    is_critical_infrastructure: bool = False
    decay_rate: float = 0.05
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.total_invocations < 0:
            raise ValueError("total_invocations cannot be negative")
        if self.critical_successes < 0:
            raise ValueError("critical_successes cannot be negative")
        if self.critical_successes > self.total_invocations:
            logger.warning(f"Node {self.node_id}: Critical successes exceed total invocations. Data anomaly.")


@dataclass
class SystemState:
    """
    Represents the current global state of the AGI system.
    
    Attributes:
        total_system_uptime: Total active time of the system.
        global_node_count: Total number of active nodes.
        current_threat_level: Normalized score (0.0-1.0) of environmental volatility.
        nodes: Dictionary of NodeTelemetry objects.
    """
    total_system_uptime: timedelta
    global_node_count: int
    current_threat_level: float = 0.1
    nodes: Dict[str, NodeTelemetry] = field(default_factory=dict)


def calculate_temporal_scarcity(node: NodeTelemetry, current_time: datetime) -> float:
    """
    Auxiliary Function: Calculates the scarcity score based on invocation frequency.
    
    A node that is rarely called but exists in the system has high scarcity.
    Uses a logarithmic scale to prevent division by zero and normalize outliers.
    
    Args:
        node: The telemetry data of the node.
        current_time: The current timestamp for time delta calculation.
        
    Returns:
        float: A normalized scarcity score between 0.0 and 1.0.
    """
    if node.total_invocations == 0:
        return 1.0  # Maximum scarcity (Never used, potential latency risk but high rarity)
    
    # Calculate time since last seen
    if node.last_invocation_time:
        time_delta = (current_time - node.last_invocation_time).total_seconds()
    else:
        time_delta = 365 * 24 * 3600  # Default to 1 year if never seen

    # Scarcity function: Increases as frequency decreases and time since last call increases
    # S = 1 / (1 + log(1 + invocations)) * (1 - exp(-time * decay))
    freq_factor = 1 / (1 + math.log1p(node.total_invocations))
    recency_factor = 1 - math.exp(-time_delta / (3600 * 24)) # Normalized by day
    
    scarcity = freq_factor * 0.7 + recency_factor * 0.3
    return min(max(scarcity, 0.0), 1.0)


def calculate_value_density(node: NodeTelemetry) -> float:
    """
    Core Function 1: Calculates the value density of a node.
    
    Value Density is defined as the ratio of critical successes to total invocations,
    weighted by an importance factor. This captures the "Quality" of the node's output
    in extreme scenarios.
    
    Args:
        node: The telemetry data of the node.
        
    Returns:
        float: A value density score between 0.0 and 1.0.
    """
    if node.total_invocations == 0:
        return 0.5  # Neutral prior for unproven nodes

    success_rate = node.critical_successes / node.total_invocations
    
    # Apply sigmoid function to smooth the value curve
    # This emphasizes nodes that have very high success rates in critical moments
    smoothed_value = 1 / (1 + math.exp(-10 * (success_rate - 0.5)))
    
    if node.is_critical_infrastructure:
        smoothed_value = min(smoothed_value * 1.2, 1.0) # Boost critical infrastructure
        
    return smoothed_value


def gray_swan_protection_filter(system_state: SystemState) -> Tuple[List[str], List[str]]:
    """
    Core Function 2: Main algorithm to identify and protect Gray Swan nodes.
    
    This function iterates through all nodes, calculates a 'Survival Score' based on
    the balance between Scarcity and Value Density, and determines which nodes
    should be protected from standard statistical pruning (optimization).
    
    Args:
        system_state: The current state of the AGI system containing all node telemetries.
        
    Returns:
        Tuple[List[str], List[str]]: 
            - List 1: Node IDs identified as Gray Swans (To be Protected).
            - List 2: Node IDs identified as Obsolete (Safe to Prune).
            
    Raises:
        ValueError: If system_state contains invalid data.
    """
    if not system_state.nodes:
        logger.warning("System state contains no nodes to analyze.")
        return [], []

    protected_nodes = []
    obsolete_nodes = []
    current_time = datetime.now()
    
    logger.info(f"Starting Gray Swan analysis for {len(system_state.nodes)} nodes.")

    for node_id, telemetry in system_state.nodes.items():
        try:
            # 1. Data Validation & Sanitization
            if not isinstance(telemetry, NodeTelemetry):
                logger.error(f"Invalid telemetry type for node {node_id}")
                continue

            # 2. Calculate Metrics
            scarcity = calculate_temporal_scarcity(telemetry, current_time)
            density = calculate_value_density(telemetry)
            
            # 3. Survival Score Calculation (The Balancing Function)
            # Score = w1 * Scarcity + w2 * Density + (ThreatLevel * CriticalityBonus)
            survival_score = (SCARCITY_WEIGHT * scarcity) + (DENSITY_WEIGHT * density)
            
            # Add environmental context (if system is under high threat, rare nodes are more valuable)
            if system_state.current_threat_level > 0.5 and telemetry.is_critical_infrastructure:
                survival_score += 0.2 * system_state.current_threat_level
            
            # 4. Decision Logic
            # A node is a 'Gray Swan' if it has low frequency (implied by scarcity) 
            # but high survival score.
            is_gray_swan = (scarcity > 0.7 and survival_score > MIN_RETENTION_SCORE)
            
            if is_gray_swan:
                protected_nodes.append(node_id)
                logger.info(f"PROTECTING node {node_id}: Score {survival_score:.4f} (S:{scarcity:.2f}, D:{density:.2f})")
            else:
                # Standard logic for normal nodes
                if survival_score < DEFAULT_PRUNE_THRESHOLD and scarcity < 0.5:
                    obsolete_nodes.append(node_id)
                    logger.debug(f"Marking node {node_id} as obsolete. Score: {survival_score:.4f}")
                else:
                    # Active nodes or standard retention
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {str(e)}")
            continue

    logger.info(f"Analysis complete. Protected: {len(protected_nodes)}, Obsolete: {len(obsolete_nodes)}")
    return protected_nodes, obsolete_nodes


if __name__ == "__main__":
    # Example Usage
    print("--- Running Gray Swan Protection Mechanism Example ---")
    
    # 1. Setup Mock Data
    # Node A: High frequency, low criticality (Standard worker)
    node_a = NodeTelemetry(
        node_id="worker_01", 
        total_invocations=10000, 
        critical_successes=5,
        last_invocation_time=datetime.now() - timedelta(minutes=5)
    )
    
    # Node B: Low frequency, HIGH criticality (The Gray Swan - e.g., Nuclear Reactor SCRAM logic)
    node_b = NodeTelemetry(
        node_id="emergency_shutdown_01", 
        total_invocations=2, 
        critical_successes=2, # 100% success when it mattered
        last_invocation_time=datetime.now() - timedelta(days=365),
        is_critical_infrastructure=True
    )
    
    # Node C: Low frequency, Low value (Dead code)
    node_c = NodeTelemetry(
        node_id="legacy_test_func", 
        total_invocations=3, 
        critical_successes=0,
        last_invocation_time=datetime.now() - timedelta(days=180)
    )

    current_state = SystemState(
        total_system_uptime=timedelta(days=400),
        global_node_count=3,
        current_threat_level=0.8, # Simulating a high-risk environment
        nodes={
            "worker_01": node_a,
            "emergency_shutdown_01": node_b,
            "legacy_test_func": node_c
        }
    )
    
    # 2. Run Algorithm
    protected, obsolete = gray_swan_protection_filter(current_state)
    
    # 3. Display Results
    print(f"\nProtected Nodes (Gray Swans): {protected}")
    print(f"Obsolete Nodes (Safe to Prune): {obsolete}")
    
    assert "emergency_shutdown_01" in protected
    assert "legacy_test_func" not in protected # Should not protect useless code
    print("\nAssertion passed: Critical low-frequency node protected.")