"""
Module: auto_基于人机共生闭环的_实践回响_量化评估_eb471a

This module provides a toolkit for quantifying 'Practical Resonance' within a 
Human-AGI symbiotic loop. It calculates node activity scores, identifies 
'Zombie Nodes' (high recommendation but low execution), and computes the 
Practice Transfer Rate (PTR).

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
EPSILON = 1e-6  # To prevent division by zero
DEFAULT_PTR_DECAY = 0.8  # Decay factor for time-sensitive relevance (conceptual)


@dataclass
class NodeStats:
    """
    Represents the statistical data for a single node in the checklist.
    
    Attributes:
        node_id: Unique identifier for the node.
        times_recommended: Total times the AI recommended this node.
        times_executed: Total times the user actually executed/completed the node.
        times_skipped: Total times the user explicitly skipped the node.
        times_deleted: Total times the user deleted the node from the active list.
        relevance_score: A base relevance score (0.0 to 1.0) indicating importance.
    """
    node_id: str
    times_recommended: int = 0
    times_executed: int = 0
    times_skipped: int = 0
    times_deleted: int = 0
    relevance_score: float = 1.0

    def __post_init__(self):
        """Validate data after initialization."""
        if self.times_recommended < 0 or self.times_executed < 0:
            raise ValueError("Counts cannot be negative.")
        if not (0.0 <= self.relevance_score <= 1.0):
            logger.warning(f"Relevance score {self.relevance_score} out of bounds for {self.node_id}. Clamping.")
            self.relevance_score = max(0.0, min(1.0, self.relevance_score))


@dataclass
class NodeMetrics:
    """
    Output data structure containing calculated metrics.
    """
    node_id: str
    activity_score: float
    ptr: float  # Practice Transfer Rate
    is_zombie: bool
    zombie_score: float  # Confidence score for being a zombie


def _safe_divide(numerator: float, denominator: float) -> float:
    """
    [Helper Function] Performs safe division, returning 0.0 if denominator is near zero.
    
    Args:
        numerator: The top part of the fraction.
        denominator: The bottom part of the fraction.
        
    Returns:
        The result of division or 0.0.
    """
    if abs(denominator) < EPSILON:
        return 0.0
    return numerator / denominator


def calculate_ptr(node: NodeStats) -> float:
    """
    [Core Function 1] Calculates the Practice Transfer Rate (PTR).
    
    PTR represents the efficiency of converting an AI recommendation into human action.
    Formula: PTR = (Executed) / (Recommended + Skipped + Deleted + Executed)
    Note: We normalize by total engagement events.
    
    Args:
        node: A NodeStats object containing raw interaction data.
        
    Returns:
        A float value between 0.0 and 1.0 representing the transfer rate.
    """
    logger.debug(f"Calculating PTR for node {node.node_id}")
    
    total_interactions = (
        node.times_executed + 
        node.times_skipped + 
        node.times_deleted
    )
    
    # If the node was never recommended or interacted with, PTR is undefined (0.0)
    if node.times_recommended == 0 or total_interactions == 0:
        return 0.0

    # Weighted PTR: Executions are positive, Skips/Deletes are negative implicit feedback
    # Standard calculation:
    ptr = _safe_divide(float(node.times_executed), float(node.times_recommended))
    
    # Apply relevance dampening if necessary (optional logic)
    # ptr *= node.relevance_score 
    
    return min(1.0, ptr)


def identify_zombie_nodes(
    nodes: List[NodeStats], 
    recommendation_threshold: int = 5,
    ptr_threshold: float = 0.2
) -> Dict[str, float]:
    """
    [Core Function 2] Identifies 'Zombie Nodes'.
    
    Zombie Nodes are defined as nodes that the AI frequently recommends, 
    but the user frequently ignores (skips or deletes).
    
    Args:
        nodes: List of NodeStats objects.
        recommendation_threshold: Minimum recommendations to be considered significant.
        ptr_threshold: Maximum PTR to be considered a 'zombie' (low conversion).
        
    Returns:
        A dictionary mapping node_id to a 'zombie_score' (0.0 to 1.0).
        Higher score means higher probability of being a zombie.
    """
    logger.info(f"Starting Zombie Node identification on {len(nodes)} nodes.")
    zombie_scores = {}

    for node in nodes:
        if node.times_recommended < recommendation_threshold:
            # Not enough data to decide
            continue

        ptr = calculate_ptr(node)
        
        # Calculate rejection ratio
        total_negative = node.times_skipped + node.times_deleted
        total_feedback = total_negative + node.times_executed
        
        rejection_rate = _safe_divide(float(total_negative), float(total_feedback))
        
        # Zombie Score Formula:
        # High recommendations (normalized) * High Rejection Rate
        # Logic: If PTR is low AND recommendations are high, it's a zombie.
        
        rec_weight = math.log10(node.times_recommended + 1) / 2.0 # Log scale to handle large numbers
        zombie_score = rec_weight * rejection_rate * (1.0 - ptr)
        
        if zombie_score > 0.5: # Arbitrary threshold for logging
            logger.warning(f"Potential Zombie Node detected: {node.node_id} (Score: {zombie_score:.4f})")
            
        if ptr < ptr_threshold and node.times_recommended >= recommendation_threshold:
            zombie_scores[node.node_id] = zombie_score

    return zombie_scores


def build_activity_score(node: NodeStats) -> float:
    """
    [Core Function 3 - Extended] Builds a composite Activity Score.
    
    Combines frequency, PTR, and relevance into a single metric for ranking.
    
    Args:
        node: NodeStats object.
        
    Returns:
        A composite score (float).
    """
    ptr = calculate_ptr(node)
    
    # Frequency Score: Logarithmic scaling of recommendations
    freq_score = math.log1p(node.times_recommended)
    
    # Interaction Score: Balance between execution and negative feedback
    total_interactions = node.times_executed + node.times_skipped + node.times_deleted
    interaction_intensity = math.log1p(total_interactions)
    
    # Final Formula:
    # Activity = (Frequency * 0.3) + (PTR * 0.5) + (Interaction * 0.2) * Relevance
    score = (
        (freq_score * 0.3) + 
        (ptr * 10 * 0.5) +  # Scale PTR up to balance with log values
        (interaction_intensity * 0.2)
    ) * node.relevance_score
    
    return round(score, 4)


def run_evaluation_pipeline(nodes_data: List[Dict[str, Any]]) -> List[NodeMetrics]:
    """
    Main pipeline to process raw data into structured metrics.
    
    Args:
        nodes_data: List of dictionaries containing raw node data.
        
    Returns:
        List of NodeMetrics objects.
        
    Raises:
        ValueError: If input data is malformed.
    """
    if not nodes_data:
        logger.error("Input data is empty.")
        return []

    processed_metrics: List[NodeMetrics] = []
    
    try:
        # Data Validation and Parsing
        valid_nodes = []
        for data in nodes_data:
            try:
                node = NodeStats(
                    node_id=data.get('id'),
                    times_recommended=data.get('recommended', 0),
                    times_executed=data.get('executed', 0),
                    times_skipped=data.get('skipped', 0),
                    times_deleted=data.get('deleted', 0),
                    relevance_score=data.get('relevance', 1.0)
                )
                valid_nodes.append(node)
            except Exception as e:
                logger.error(f"Skipping invalid node data {data.get('id')}: {e}")

        # Identify Zombies
        zombies = identify_zombie_nodes(valid_nodes)
        
        # Calculate Metrics
        for node in valid_nodes:
            score = build_activity_score(node)
            ptr = calculate_ptr(node)
            is_zombie = node.node_id in zombies
            
            metric = NodeMetrics(
                node_id=node.node_id,
                activity_score=score,
                ptr=ptr,
                is_zombie=is_zombie,
                zombie_score=zombies.get(node.node_id, 0.0)
            )
            processed_metrics.append(metric)
            
        logger.info(f"Successfully processed {len(processed_metrics)} nodes.")
        
    except Exception as e:
        logger.critical(f"Pipeline failed: {e}", exc_info=True)
        raise

    return processed_metrics

# --- Usage Example ---
if __name__ == "__main__":
    # Mock Data representing a Human-Machine Symbiosis Log
    mock_data = [
        {
            "id": "node_101", 
            "recommended": 100, 
            "executed": 5, 
            "skipped": 80, 
            "deleted": 15, 
            "relevance": 0.9
        }, # Likely Zombie
        {
            "id": "node_102", 
            "recommended": 50, 
            "executed": 45, 
            "skipped": 2, 
            "deleted": 0, 
            "relevance": 1.0
        }, # Healthy Node
        {
            "id": "node_103", 
            "recommended": 2, 
            "executed": 0, 
            "skipped": 1, 
            "deleted": 0, 
            "relevance": 0.5
        }, # New/Low Data Node
        {
            "id": "node_104", 
            "recommended": 20, 
            "executed": 1, 
            "skipped": 0, 
            "deleted": 19, 
            "relevance": 0.8
        } # Zombie (Deletion heavy)
    ]

    print("--- Starting Evaluation ---")
    results = run_evaluation_pipeline(mock_data)
    
    print("\n--- Results ---")
    for res in results:
        status = "ZOMBIE" if res.is_zombie else "ACTIVE"
        print(
            f"ID: {res.node_id} | "
            f"Score: {res.activity_score:.2f} | "
            f"PTR: {res.ptr:.2f} | "
            f"Status: {status}"
        )