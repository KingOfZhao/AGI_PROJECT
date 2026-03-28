"""
Module: implicit_negation_mining.py

This module implements the 'Implicit Negation Mining Algorithm' designed for 
Human-Computer Symbiosis (HCS) systems. It quantifies user silence as a falsification 
signal, distinguishing between 'Not Yet Practiced', 'Forgetting', and 'Implicit Falsification'.

The core logic calculates a decayed utility score based on time-series interaction data
to automatically downweight inefficient AI suggestion nodes.

Author: AGI System
Version: 1.0.0
Domain: behavioral_psychology / human_computer_interaction
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ImplicitNegationMining")


class SilenceType(Enum):
    """Classification of user silence regarding an AI suggestion."""
    NOT_YET_PRACTICED = auto()   # Suggestion is new or user hasn't had time
    FORGETTING = auto()          # User saw it but likely forgot (benign neglect)
    IMPLICIT_FALSIFICATION = auto() # User ignored it because it was tried and failed (active rejection)
    ENGAGED = auto()             # Not silent, currently active


@dataclass
class InteractionEvent:
    """Represents a single interaction data point."""
    timestamp: datetime
    event_type: str  # 'impression', 'explicit_success', 'explicit_failure', 'engagement'


@dataclass
class SuggestionNode:
    """Represents an AI suggestion node in the knowledge graph."""
    node_id: str
    created_at: datetime
    last_interaction: datetime
    weight: float = 1.0
    explicit_negations: int = 0
    history: List[InteractionEvent] = field(default_factory=list)

    def add_event(self, event: InteractionEvent):
        self.history.append(event)
        self.last_interaction = event.timestamp


def _validate_time_consistency(history: List[InteractionEvent]) -> bool:
    """
    [Helper] Validates that interaction history is chronologically sorted.
    
    Args:
        history: List of interaction events.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if len(history) < 2:
        return True
    for i in range(len(history) - 1):
        if history[i].timestamp > history[i+1].timestamp:
            logger.error(f"Timestamp consistency error at index {i}")
            return False
    return True


def calculate_silence_score(
    node: SuggestionNode, 
    current_time: datetime, 
    decay_rate: float = 0.1
) -> Tuple[SilenceType, float]:
    """
    [Core] Analyzes the silence of a specific node to classify its state.
    
    This function distinguishes why a user is silent based on time deltas and 
    interaction patterns.
    
    Args:
        node (SuggestionNode): The AI suggestion node to analyze.
        current_time (datetime): The current timestamp for comparison.
        decay_rate (float): Lambda for exponential decay calculation.
        
    Returns:
        Tuple[SilenceType, float]: The classified silence type and a calculated 
                                   'Falsification Probability' (0.0 to 1.0).
    
    Raises:
        ValueError: If current_time precedes node creation time.
    """
    if current_time < node.created_at:
        logger.error(f"Temporal paradox detected: Current time {current_time} < Creation {node.created_at}")
        raise ValueError("Current time cannot be before node creation time.")

    # 1. Check for Recent Activity (Not Silent)
    delta_last_active = (current_time - node.last_interaction).total_seconds()
    
    # Thresholds (in seconds for simplicity, usually configurable)
    ENGAGEMENT_WINDOW = 300  # 5 minutes
    IMPLICIT_THRESHOLD = 7 * 24 * 3600  # 7 days
    
    if delta_last_active < ENGAGEMENT_WINDOW:
        return SilenceType.ENGAGED, 0.0

    # 2. Classify Silence
    age_of_node = (current_time - node.created_at).total_seconds()
    
    # Case A: Not Yet Practiced (Node is young, no significant history)
    if age_of_node < 24 * 3600 and not node.history:
        logger.debug(f"Node {node.node_id} classified as NOT_YET_PRACTICED")
        return SilenceType.NOT_YET_PRACTICED, 0.0

    # Case B: Implicit Falsification
    # Heuristic: If the user was active on OTHER nodes (implied by system context not shown here)
    # OR if the node was presented (impression) but immediately dropped despite user activity elsewhere.
    # Simplified Logic: If the node is old enough, has impressions, but no follow-up, and explicit negations exist.
    has_impressions = any(e.event_type == 'impression' for e in node.history)
    
    if age_of_node > IMPLICIT_THRESHOLD and has_impressions:
        # If there were impressions but no 'explicit_success' and time has passed, 
        # assume the user tried it mentally or briefly and rejected it.
        
        # Calculate probability based on decay of attention
        raw_score = 1.0 - math.exp(-decay_rate * (delta_last_active / (24 * 3600)))
        
        # If there were explicit failures previously, boost the falsification score
        if node.explicit_negations > 0:
            raw_score = min(1.0, raw_score + 0.4)
            
        logger.info(f"Node {node.node_id} identified as IMPLICIT_FALSIFICATION with score {raw_score:.2f}")
        return SilenceType.IMPLICIT_FALSIFICATION, raw_score

    # Case C: Forgetting (Default for silent nodes that don't fit A or B)
    # It's been a while, but not long enough to assume rejection, or no impressions recently.
    logger.debug(f"Node {node.node_id} classified as FORGETTING")
    return SilenceType.FORGETTING, 0.0


def update_node_weights(
    nodes: Dict[str, SuggestionNode], 
    current_time: datetime,
    penalty_factor: float = 0.85
) -> Dict[str, float]:
    """
    [Core] Updates the weights of a dictionary of nodes based on implicit negation mining.
    
    Iterates through nodes, identifies implicit falsification, and applies penalties.
    
    Args:
        nodes (Dict[str, SuggestionNode]): Map of node IDs to node objects.
        current_time (datetime): Current time for analysis.
        penalty_factor (float): Multiplier applied to nodes identified as implicitly falsified.
        
    Returns:
        Dict[str, float]: A dictionary of updated weights {node_id: new_weight}.
    """
    if not isinstance(nodes, dict):
        logger.error("Input nodes must be a dictionary.")
        raise TypeError("nodes must be a dictionary")

    updated_weights = {}
    
    for node_id, node in nodes.items():
        if not isinstance(node, SuggestionNode):
            logger.warning(f"Skipping invalid node type for ID: {node_id}")
            continue
            
        try:
            s_type, prob = calculate_silence_score(node, current_time)
            
            if s_type == SilenceType.IMPLICIT_FALSIFICATION:
                # Apply penalty proportional to probability
                reduction = 1.0 - (prob * (1.0 - penalty_factor))
                new_weight = node.weight * reduction
                node.weight = max(0.01, new_weight) # Floor at 0.01 to allow potential recovery
                logger.info(f"Penalizing node {node_id}. Old Weight: {node.weight:.2f}, New: {new_weight:.2f}")
            
            updated_weights[node_id] = node.weight
            
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")
            continue

    return updated_weights


if __name__ == "__main__":
    # Example Usage
    
    # 1. Setup mock data
    now = datetime.now()
    node_a_id = "sugg_001"
    node_b_id = "sugg_002"
    
    # Node A: Old node, viewed but ignored -> Implicit Falsification
    node_a = SuggestionNode(
        node_id=node_a_id,
        created_at=now - timedelta(days=14),
        last_interaction=now - timedelta(days=10),
        weight=1.0,
        history=[InteractionEvent(now - timedelta(days=13), 'impression')]
    )
    
    # Node B: Fresh node -> Not Yet Practiced
    node_b = SuggestionNode(
        node_id=node_b_id,
        created_at=now - timedelta(hours=1),
        last_interaction=now - timedelta(hours=1),
        weight=1.0
    )
    
    nodes_map = {
        node_a_id: node_a,
        node_b_id: node_b
    }
    
    # 2. Run the update algorithm
    print("Running Implicit Negation Mining Algorithm...")
    final_weights = update_node_weights(nodes_map, now)
    
    # 3. Output results
    for nid, weight in final_weights.items():
        print(f"Node: {nid} | Final Weight: {weight:.4f}")
        
    # Expected: Node A weight decreases, Node B weight stays 1.0