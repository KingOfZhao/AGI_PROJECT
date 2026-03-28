"""
Module: implicit_negative_feedback_channel.py

Description:
    Implements a 'Negative Feedback Weighting' channel for Human-Computer Symbiosis.
    
    In human-AI interaction, explicit rejections are rare. Users often 'skip' or 
    remain 'silent' regarding AI suggestions. This module treats such implicit 
    behaviors as weak negative signals (soft rejections). 
    
    It provides algorithms to convert these implicit signals into penalty weights, 
    updating a Knowledge Graph (or Recommendation Matrix) to suppress the recall 
    probability of irrelevant nodes, thereby preventing the solidification of 
    incorrect knowledge due to user inertia.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import math
from typing import Dict, List, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type Aliases for clarity
NodeId = str
Weight = float
FeedbackSignal = Union[str, bool]  # e.g., 'skip', 'ignore', False
Timestamp = float


class FeedbackConfig:
    """Configuration constants for the feedback loop."""
    
    # Decay factor for time sensitivity (older signals have less impact)
    TIME_DECAY_LAMBDA: float = 0.05
    
    # Default penalty weight for implicit negative signals
    IMPLICIT_PENALTY: float = -0.25
    
    # Threshold below which a node is considered 'suppressed'
    SUPPRESSION_THRESHOLD: float = 0.1
    
    # Minimum weight floor (prevent negative infinity)
    WEIGHT_FLOOR: float = 0.01


def _calculate_time_decay(
    event_timestamp: Timestamp, 
    current_timestamp: Optional[Timestamp] = None
) -> float:
    """
    [Helper Function] Calculates the time decay factor for a signal.
    
    Recent signals should have more weight than older signals. Uses exponential decay.
    
    Args:
        event_timestamp (float): The unix timestamp when the event occurred.
        current_timestamp (Optional[float]): The current time. Defaults to now.
        
    Returns:
        float: A decay factor between 0 and 1.
        
    Raises:
        ValueError: If event_timestamp is in the future.
    """
    if current_timestamp is None:
        current_timestamp = datetime.now().timestamp()
        
    if event_timestamp > current_timestamp:
        logger.error(f"Future timestamp detected: {event_timestamp}")
        raise ValueError("Event timestamp cannot be in the future.")
        
    delta_time = current_timestamp - event_timestamp
    # Exponential decay: e^(-lambda * t)
    decay = math.exp(-FeedbackConfig.TIME_DECAY_LAMBDA * delta_time)
    return decay


def process_implicit_signal(
    user_action: FeedbackSignal,
    dwell_time_seconds: float = 0.0
) -> Optional[float]:
    """
    [Core Function 1] Translates user behavior into a delta weight value.
    
    Logic:
    1. Explicit rejection ('reject', False) -> Strong negative signal.
    2. Implicit rejection ('skip', 'silence', 'ignore') -> Weak negative signal,
       further adjusted by dwell time (quick skip = stronger rejection).
    3. Positive action -> None (handled by positive feedback loop).
    
    Args:
        user_action (FeedbackSignal): The detected user action.
        dwell_time_seconds (float): Time spent on the item before action.
        
    Returns:
        Optional[float]: The weight delta (negative value) or None if not a negative signal.
        
    Example:
        >>> process_implicit_signal('skip', dwell_time_seconds=1.5)
        -0.325
    """
    logger.debug(f"Processing signal: {user_action}, dwell: {dwell_time_seconds}")
    
    # Normalize input
    action_str = str(user_action).lower().strip()
    
    # Signal Classification
    if action_str in ['reject', 'dislike', 'false']:
        logger.info("Detected explicit negative signal.")
        return -0.8  # Strong penalty
    
    elif action_str in ['skip', 'ignore', 'silence', 'pass']:
        logger.info("Detected implicit negative signal (weak rejection).")
        
        # If user skipped very quickly, it's a stronger negative signal than lingering skip
        # This is a heuristic for "quality of attention".
        speed_factor = 1.0
        if dwell_time_seconds < 2.0:
            speed_factor = 1.2  # Fast skip = "Get this away from me"
        elif dwell_time_seconds > 10.0:
            speed_factor = 0.8  # Slow skip = "Maybe interesting, but not now"
            
        penalty = FeedbackConfig.IMPLICIT_PENALTY * speed_factor
        return penalty
        
    elif action_str in ['click', 'accept', 'save', 'true']:
        logger.debug("Positive signal detected. Ignoring in negative channel.")
        return None
        
    else:
        logger.warning(f"Unknown action type: {user_action}. Defaulting to weak negative.")
        return FeedbackConfig.IMPLICIT_PENALTY * 0.5


def update_knowledge_weights(
    graph_state: Dict[NodeId, Weight],
    feedback_log: List[Dict[str, Union[NodeId, FeedbackSignal, Timestamp, float]]],
    current_time: Optional[Timestamp] = None
) -> Dict[NodeId, Weight]:
    """
    [Core Function 2] Updates the knowledge graph weights based on accumulated feedback.
    
    This function applies the calculated penalties back to the specific nodes,
    applying time decay so that old feedback matters less.
    
    Args:
        graph_state (Dict[NodeId, Weight]): Current state of node weights (0.0 to 1.0).
        feedback_log (List[Dict]): A list of feedback events to process.
            Expected format: [{'node_id': str, 'action': str, 'timestamp': float, 'dwell_time': float}, ...]
        current_time (Optional[Timestamp]): Current time for decay calculation.
        
    Returns:
        Dict[NodeId, Weight]: The updated graph state.
        
    Input Format:
        graph_state: {'node_A': 0.9, 'node_B': 0.5}
        feedback_log: [{'node_id': 'node_A', 'action': 'skip', 'timestamp': 1678900000, 'dwell_time': 1.2}]
        
    Output Format:
        {'node_A': 0.65, 'node_B': 0.5} (node_A reduced)
    """
    if not isinstance(graph_state, dict) or not isinstance(feedback_log, list):
        logger.error("Invalid input types for update_knowledge_weights.")
        raise TypeError("graph_state must be a dict and feedback_log a list.")

    if current_time is None:
        current_time = datetime.now().timestamp()

    # Create a copy to avoid mutating the original state during processing
    updated_state = graph_state.copy()
    
    suppressed_count = 0

    for entry in feedback_log:
        # Data Validation
        if not all(k in entry for k in ['node_id', 'action', 'timestamp']):
            logger.warning(f"Malformed log entry skipped: {entry}")
            continue
            
        node_id = entry['node_id']
        
        if node_id not in updated_state:
            logger.warning(f"Node {node_id} not found in graph state. Skipping.")
            continue
            
        # 1. Calculate Base Signal Strength
        dwell = entry.get('dwell_time', 0.0)
        raw_delta = process_implicit_signal(entry['action'], dwell)
        
        if raw_delta is None:
            continue  # Not a negative signal
            
        # 2. Apply Time Decay
        try:
            decay_factor = _calculate_time_decay(entry['timestamp'], current_time)
        except ValueError:
            continue # Skip invalid time entries
            
        final_delta = raw_delta * decay_factor
        
        # 3. Apply Update
        old_weight = updated_state[node_id]
        new_weight = old_weight + final_delta
        
        # 4. Boundary Checks (Hard limits)
        new_weight = max(FeedbackConfig.WEIGHT_FLOOR, new_weight)
        updated_state[node_id] = new_weight
        
        log_msg = (
            f"Node {node_id} updated: {old_weight:.3f} -> {new_weight:.3f} "
            f"(Delta: {final_delta:.3f}, Decay: {decay_factor:.2f})"
        )
        logger.info(log_msg)
        
        if new_weight < FeedbackConfig.SUPPRESSION_THRESHOLD:
            suppressed_count += 1

    logger.info(f"Update complete. Total nodes suppressed: {suppressed_count}")
    return updated_state


if __name__ == "__main__":
    # --- Usage Example ---
    
    # 1. Simulate a Knowledge Base / Recommendation State
    knowledge_base = {
        "concept_pyramid": 0.95,      # Highly recommended
        "concept_monolith": 0.80,     # Recommended
        "concept_legacy": 0.60,       # Moderately recommended
        "concept_obsolete": 0.40      # Low confidence
    }
    
    # 2. Simulate collected user behavior logs
    # Scenario: User skipped the 'Monolith' suggestion quickly (Strong Implicit Negative)
    # Scenario: User ignored 'Legacy' suggestion after reading for a while (Weak Implicit Negative)
    # Scenario: User saw 'Pyramid' but did nothing (Neutral/Positive context not handled here)
    
    now = datetime.now().timestamp()
    
    interaction_logs = [
        {
            "node_id": "concept_monolith",
            "action": "skip",
            "timestamp": now - 100,  # 100 seconds ago
            "dwell_time": 0.5        # Very fast skip
        },
        {
            "node_id": "concept_legacy",
            "action": "silence",     # User just scrolled past
            "timestamp": now - 50,
            "dwell_time": 12.0       # Looked at it for a while, then ignored
        },
        {
            "node_id": "concept_obsolete",
            "action": "reject",      # Explicit rejection
            "timestamp": now - 10,
            "dwell_time": 0.0
        }
    ]
    
    print("--- Initial State ---")
    print(knowledge_base)
    
    # 3. Run the Negative Feedback Channel Algorithm
    print("\nProcessing Negative Feedback Channel...")
    updated_knowledge = update_knowledge_weights(knowledge_base, interaction_logs)
    
    print("\n--- Updated State ---")
    for k, v in updated_knowledge.items():
        print(f"{k}: {v:.4f}")
        
    # Expected outcome:
    # concept_monolith: Decreased significantly (fast skip)
    # concept_legacy: Decreased slightly (slow skip/ignore)
    # concept_obsolete: Decreased heavily (explicit reject)