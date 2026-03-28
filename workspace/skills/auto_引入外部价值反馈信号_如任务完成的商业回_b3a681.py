"""
Module: auto_introduce_external_value_feedback_b3a681

This module implements a system to integrate external value feedback signals 
(e.g., commercial ROI, user satisfaction scores) into a node-based AGI architecture.
It constructs a Value-Sensitive weight system to prioritize nodes that contribute 
to higher external value.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class FeedbackSignal:
    """
    Represents a single external feedback signal.
    
    Attributes:
        source_id: Identifier for the node or action being rated.
        value_score: The external value metric (e.g., 0.0 to 1.0 for satisfaction, or $ amount).
        timestamp: When the feedback was received.
        confidence: Reliability of the signal (0.0 to 1.0).
    """
    source_id: str
    value_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0

    def __post_init__(self):
        if not (0.0 <= self.value_score <= 1.0):
            # Allowing normalization internally or strict check depending on design.
            # Here we clamp for safety but log a warning.
            logger.warning(f"Value score {self.value_score} out of [0,1] range for {self.source_id}. Clamping.")
            self.value_score = max(0.0, min(1.0, self.value_score))
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0. Got {self.confidence}")

@dataclass
class ValueNode:
    """
    Represents a node in the AGI system with value sensitivity.
    
    Attributes:
        node_id: Unique identifier.
        base_weight: The intrinsic weight before value feedback.
        current_value_weight: The adjusted weight based on external feedback.
        feedback_history: Historical record of received feedback signals.
    """
    node_id: str
    base_weight: float = 0.5
    current_value_weight: float = 0.5
    feedback_history: List[FeedbackSignal] = field(default_factory=list)

    def __post_init__(self):
        if self.base_weight < 0:
            raise ValueError("Base weight cannot be negative.")

# --- Core Functions ---

def calculate_decay_factor(timestamp: datetime, current_time: datetime, half_life_hours: float = 24.0) -> float:
    """
    Auxiliary Function: Calculate time-based decay factor.
    
    Uses exponential decay to reduce the influence of older feedback signals.
    
    Args:
        timestamp: The time the feedback was generated.
        current_time: The current reference time.
        half_life_hours: The period over which the signal value reduces by half.
        
    Returns:
        float: A decay multiplier between 0 and 1.
    """
    delta = (current_time - timestamp).total_seconds() / 3600.0
    if delta < 0:
        logger.warning("Feedback timestamp is in the future. Treating as instant.")
        return 1.0
    
    decay_lambda = math.log(2) / half_life_hours
    return math.exp(-decay_lambda * delta)

def process_external_feedback(
    nodes: Dict[str, ValueNode],
    feedback_signals: List[FeedbackSignal],
    learning_rate: float = 0.1,
    decay_enabled: bool = True
) -> Dict[str, ValueNode]:
    """
    Core Function 1: Ingest and process external feedback signals.
    
    Updates the `current_value_weight` of the nodes based on the received signals.
    It applies confidence weighting and temporal decay.
    
    Args:
        nodes: The current dictionary of system nodes.
        feedback_signals: A list of new external feedback signals to process.
        learning_rate: How strongly new feedback affects the weight (0.0 to 1.0).
        decay_enabled: Whether to apply time decay to signals.
        
    Returns:
        Dict[str, ValueNode]: The updated dictionary of nodes.
        
    Raises:
        ValueError: If inputs are malformed.
    """
    if not 0.0 < learning_rate <= 1.0:
        raise ValueError("Learning rate must be in (0, 1].")
    
    current_time = datetime.now()
    
    for signal in feedback_signals:
        if signal.source_id not in nodes:
            logger.error(f"Feedback received for unknown node ID: {signal.source_id}")
            continue
            
        node = nodes[signal.source_id]
        
        # Calculate effective signal strength
        decay = 1.0
        if decay_enabled:
            decay = calculate_decay_factor(signal.timestamp, current_time)
            
        effective_score = signal.value_score * signal.confidence * decay
        
        # Update logic: Smooth moving average approach
        # New_Weight = (1 - alpha) * Old_Weight + alpha * New_Signal
        delta = effective_score - node.current_value_weight
        node.current_value_weight += learning_rate * delta
        
        # Boundary Check
        node.current_value_weight = max(0.0, min(2.0, node.current_value_weight))
        
        node.feedback_history.append(signal)
        logger.info(f"Node {node.node_id} updated. Value Weight: {node.current_value_weight:.4f}")

    return nodes

def compute_system_value_distribution(nodes: Dict[str, ValueNode]) -> Dict[str, float]:
    """
    Core Function 2: Calculate the final normalized value distribution.
    
    Combines `base_weight` and `current_value_weight` to determine the final
    influence of each node in the system.
    
    Args:
        nodes: Dictionary of nodes containing base and value weights.
        
    Returns:
        Dict[str, float]: A dictionary mapping node_id to its normalized priority score (0.0 to 1.0).
    """
    raw_scores = {}
    
    for node_id, node in nodes.items():
        # Combine intrinsic value with learned external value
        # Formula: Priority = Base * (1 + Value_Sensitivity)
        combined_score = node.base_weight * (1.0 + node.current_value_weight)
        raw_scores[node_id] = combined_score
        
    total_score = sum(raw_scores.values())
    
    if total_score == 0:
        logger.warning("Total system value is zero. Returning uniform distribution.")
        uniform_val = 1.0 / len(nodes) if nodes else 0.0
        return {k: uniform_val for k in nodes}
    
    normalized_distribution = {
        k: v / total_score for k, v in raw_scores.items()
    }
    
    logger.debug(f"Value distribution calculated: {normalized_distribution}")
    return normalized_distribution

# --- Main Execution / Example ---

if __name__ == "__main__":
    # Initialize System Nodes
    system_nodes = {
        "search_engine": ValueNode(node_id="search_engine", base_weight=0.8),
        "code_generator": ValueNode(node_id="code_generator", base_weight=0.5),
        "casual_chat": ValueNode(node_id="casual_chat", base_weight=0.2)
    }
    
    logger.info("Initialized System Nodes.")
    
    # Simulate External Feedback (e.g., Commercial Task Completion)
    # Scenario: 'code_generator' brings high commercial value, 'casual_chat' low.
    incoming_signals = [
        FeedbackSignal(source_id="code_generator", value_score=0.9, confidence=0.95),
        FeedbackSignal(source_id="casual_chat", value_score=0.1, confidence=0.8),
        FeedbackSignal(source_id="search_engine", value_score=0.6, confidence=1.0),
        FeedbackSignal(source_id="code_generator", value_score=0.95, confidence=0.9),
    ]
    
    # Process Feedback
    logger.info("Processing external feedback signals...")
    try:
        updated_nodes = process_external_feedback(
            nodes=system_nodes,
            feedback_signals=incoming_signals,
            learning_rate=0.2
        )
        
        # Compute Final Distribution
        distribution = compute_system_value_distribution(updated_nodes)
        
        print("\n--- Final Value Distribution ---")
        for node_id, score in sorted(distribution.items(), key=lambda item: item[1], reverse=True):
            print(f"Node: {node_id:<15} | Priority Score: {score:.4f}")
            
    except Exception as e:
        logger.critical(f"System failed to process value feedback: {e}")