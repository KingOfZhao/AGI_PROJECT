"""
Module: auto_真实节点_最小可证伪单元_的粒度寻优_217d7e

Description:
    This module implements a dynamic granularity optimization mechanism for 'Real Nodes'
    (knowledge units) in an AGI system. It addresses the trade-off between 'Interpretability'
    (abstraction) and 'Executability' (actionable detail).
    
    The core concept is the 'Minimum Falsifiable Unit' (MFU) - a node granule that is
    specific enough to be tested/executed, yet abstract enough to be reusable.
    
    Key Features:
    - Analyzes node context and operational history.
    - Calculates an optimal granularity score.
    - Determines if a node should be split (refined) or merged (abstracted).

Author: Advanced Python Engineer
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
GRAIN_SCORE_MIN = 0.0
GRAIN_SCORE_MAX = 1.0
TARGET_GRANULARITY = 0.5  # The ideal balance point (heuristic)
PENALTY_WEIGHT_REUSE = 0.3
PENALTY_WEIGHT_EXECUTION = 0.3
PENALTY_WEIGHT_AMBIGUITY = 0.4


@dataclass
class KnowledgeNode:
    """
    Represents a knowledge node in the AGI system.
    
    Attributes:
        id: Unique identifier.
        label: Human-readable label (e.g., 'Macroeconomics', 'Screw Driving').
        depth: Current depth in the knowledge tree (0 = Root).
        usage_count: Number of times this node was accessed/referenced.
        actionability_score: Float (0-1). How directly can this node trigger a motor action?
        ambiguity_index: Float (0-1). How much confusion does this node cause in inference?
    """
    id: str
    label: str
    depth: int
    usage_count: int
    actionability_score: float  # 0.0 (Abstract) to 1.0 (Concrete)
    ambiguity_index: float      # 0.0 (Clear) to 1.0 (Vague)


def _validate_node_integrity(node: KnowledgeNode) -> bool:
    """
    Helper function to validate the data integrity of a KnowledgeNode.
    
    Args:
        node: The KnowledgeNode instance to validate.
        
    Returns:
        True if valid, raises ValueError otherwise.
        
    Raises:
        ValueError: If any numeric field is out of bounds or required fields are missing.
    """
    if not node.id or not node.label:
        logger.error(f"Node validation failed: Missing ID or Label for node {node.id}")
        raise ValueError("Node ID and Label must be non-empty.")
    
    if not (0.0 <= node.actionability_score <= 1.0):
        logger.error(f"Node {node.id}: actionability_score {node.actionability_score} out of range [0, 1]")
        raise ValueError("actionability_score must be between 0.0 and 1.0.")
        
    if not (0.0 <= node.ambiguity_index <= 1.0):
        logger.error(f"Node {node.id}: ambiguity_index {node.ambiguity_index} out of range [0, 1]")
        raise ValueError("ambiguity_index must be between 0.0 and 1.0.")
        
    if node.depth < 0 or node.usage_count < 0:
        logger.error(f"Node {node.id}: Negative depth or usage count detected.")
        raise ValueError("Depth and usage_count must be non-negative.")
        
    logger.debug(f"Node {node.id} passed integrity validation.")
    return True


def calculate_granularity_score(node: KnowledgeNode) -> float:
    """
    Core Function 1: Calculates the current granularity score of a node.
    
    The score represents the node's position on the spectrum from 
    Abstract (0.0) to Concrete (1.0). It combines intrinsic properties
    like depth and actionability.
    
    Formula Logic:
    Score = (Actionability * 0.6) + (Depth_Factor * 0.4)
    * Note: This is a heuristic simulation for the AGI logic.
    
    Args:
        node: The KnowledgeNode to evaluate.
        
    Returns:
        A float score between 0.0 and 1.0.
    """
    try:
        _validate_node_integrity(node)
    except ValueError as e:
        logger.warning(f"Skipping calculation for invalid node: {e}")
        return 0.0

    logger.info(f"Calculating granularity for Node: {node.label} ({node.id})")
    
    # Depth Factor: Deeper nodes are naturally more granular/concrete
    # Assuming max effective depth is 10 for normalization
    normalized_depth = min(node.depth / 10.0, 1.0)
    
    # Weighted calculation
    score = (node.actionability_score * 0.6) + (normalized_depth * 0.4)
    
    # Clamp result to ensure bounds
    score = max(GRAIN_SCORE_MIN, min(GRAIN_SCORE_MAX, score))
    
    logger.debug(f"Calculated Granularity Score: {score:.4f}")
    return score


def optimize_node_granularity(
    node: KnowledgeNode, 
    target_score: float = TARGET_GRANULARITY
) -> Tuple[str, float]:
    """
    Core Function 2: Determines the optimal adjustment strategy for the node.
    
    This function evaluates if the current granularity allows for 'Falsifiability'.
    - If too abstract (score low): It risks being non-falsifiable/unactionable.
    - If too concrete (score high): It risks being non-reusable/overfitted.
    
    Args:
        node: The target KnowledgeNode.
        target_score: The desired granularity balance (default 0.5).
        
    Returns:
        A tuple containing:
        - strategy (str): 'SPLIT', 'MERGE', or 'MAINTAIN'.
        - delta (float): The distance from the target score.
    """
    try:
        _validate_node_integrity(node)
    except ValueError as e:
        logger.error(f"Cannot optimize invalid node: {e}")
        return ("ERROR", 0.0)

    current_score = calculate_granularity_score(node)
    
    # Calculate deviation from optimal falsifiability
    deviation = current_score - target_score
    abs_deviation = abs(deviation)
    
    logger.info(f"Optimizing {node.label}: Current={current_score:.2f}, Target={target_score:.2f}")
    
    # Decision Logic with Hysteresis Threshold
    threshold = 0.15  # Dead zone to prevent oscillation
    
    if deviation > threshold:
        # Node is too concrete (over-optimized for action, low reuse)
        # Example: "Turning screw #452 on Tuesday"
        strategy = "MERGE" 
        logger.debug(f"Strategy: MERGE (Too concrete). Deviation: {deviation:.2f}")
        
    elif deviation < -threshold:
        # Node is too abstract (high reuse, low actionability)
        # Example: "Doing Work"
        strategy = "SPLIT"
        logger.debug(f"Strategy: SPLIT (Too abstract). Deviation: {deviation:.2f}")
        
    else:
        # Within optimal range
        strategy = "MAINTAIN"
        logger.debug(f"Strategy: MAINTAIN (Optimal). Deviation: {deviation:.2f}")
        
    return strategy, abs_deviation


def run_granularity_experiment(nodes: List[KnowledgeNode]) -> dict:
    """
    Main Workflow: Runs the optimization experiment on a list of nodes.
    
    Args:
        nodes: A list of KnowledgeNode objects.
        
    Returns:
        A summary dictionary of the experiment results.
    """
    results = {
        "processed": 0,
        "splits": 0,
        "merges": 0,
        "maintains": 0,
        "errors": 0
    }
    
    logger.info(f"Starting granularity experiment on {len(nodes)} nodes.")
    
    for node in nodes:
        try:
            strategy, _ = optimize_node_granularity(node)
            results["processed"] += 1
            
            if strategy == "SPLIT":
                results["splits"] += 1
            elif strategy == "MERGE":
                results["merges"] += 1
            elif strategy == "MAINTAIN":
                results["maintains"] += 1
            else:
                results["errors"] += 1
                
        except Exception as e:
            logger.exception(f"Critical error processing node {node.id}: {e}")
            results["errors"] += 1
            
    logger.info(f"Experiment Complete. Results: {results}")
    return results

# --- Usage Example ---
if __name__ == "__main__":
    # Create sample nodes representing different granularity levels
    sample_nodes = [
        # Case 1: Too Abstract (High Ambiguity, Low Actionability)
        KnowledgeNode(
            id="node_001", 
            label="Economics", 
            depth=1, 
            usage_count=500, 
            actionability_score=0.1, 
            ambiguity_index=0.9
        ),
        # Case 2: Too Concrete (Low Reuse, High Actionability)
        KnowledgeNode(
            id="node_002", 
            label="Breathing Air at 14:00 PM", 
            depth=8, 
            usage_count=1, 
            actionability_score=0.95, 
            ambiguity_index=0.05
        ),
        # Case 3: Optimal (Balanced)
        KnowledgeNode(
            id="node_003", 
            label="Adjust Interest Rates", 
            depth=4, 
            usage_count=50, 
            actionability_score=0.6, 
            ambiguity_index=0.2
        )
    ]

    # Run the experiment
    experiment_stats = run_granularity_experiment(sample_nodes)
    
    # Detailed check for one node
    print("\n--- Single Node Analysis ---")
    test_node = sample_nodes[0]
    current_g = calculate_granularity_score(test_node)
    decision, delta = optimize_node_granularity(test_node)
    
    print(f"Node: {test_node.label}")
    print(f"Granularity Score: {current_g:.4f}")
    print(f"Optimization Decision: {decision} (Delta: {delta:.4f})")