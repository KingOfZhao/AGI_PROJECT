"""
Module: adaptive_node_evolution.py

This module implements an entropy-based decision tree for node lifecycle management
in Human-Computer Symbiosis systems. It specifically addresses how to process human
feedback to determine whether a node should be retained, archived, or retrained
based on the uncertainty (entropy) of the feedback.

Key Concepts:
- High Entropy: Feedback is polarized (controversial). The node may be context-dependent.
- Low Entropy (Negative): Feedback is consistently bad. The node is likely erroneous.
- Low Entropy (Positive): Feedback is consistently good. The node is robust.

Author: AGI System Core Team
Version: 1.0.0
"""

import math
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeAction(Enum):
    """Enumeration of possible actions to take on a node."""
    RETAIN = "RETAIN"                 # Node is performing well
    CONTEXTUALIZE = "CONTEXTUALIZE"   # High entropy, needs context binding
    RETRAIN = "RETRAIN"               # Low entropy negative, needs fixing
    TERMINATE = "TERMINATE"           # Irredeemable performance

@dataclass
class NodeFeedback:
    """
    Data structure representing feedback for a specific node.
    
    Attributes:
        node_id: Unique identifier for the node.
        positive_feedback: Count of positive interactions/ratings.
        negative_feedback: Count of negative interactions/ratings.
        total_interactions: Total number of interactions (for validation).
    """
    node_id: str
    positive_feedback: int
    negative_feedback: int
    total_interactions: int

    def __post_init__(self):
        """Validate data integrity after initialization."""
        if self.positive_feedback < 0 or self.negative_feedback < 0:
            raise ValueError("Feedback counts cannot be negative")
        if self.total_interactions != (self.positive_feedback + self.negative_feedback):
            logger.warning(f"Node {self.node_id}: Total interactions mismatch. "
                           f"Auto-correcting to sum of feedback.")
            self.total_interactions = self.positive_feedback + self.negative_feedback

class EntropyDecisionEngine:
    """
    Engine for calculating feedback entropy and determining node lifecycle actions.
    
    Uses Shannon Entropy to quantify the uncertainty in user feedback.
    """

    def __init__(self, 
                 high_entropy_threshold: float = 0.8, 
                 low_entropy_threshold: float = 0.3,
                 significance_level: int = 5):
        """
        Initialize the decision engine.
        
        Args:
            high_entropy_threshold: Threshold above which feedback is considered polarized.
            low_entropy_threshold: Threshold below which feedback is considered consistent.
            significance_level: Minimum number of interactions required to make a decision.
        """
        if not 0 <= low_entropy_threshold <= high_entropy_threshold <= 1:
            raise ValueError("Invalid threshold configuration.")
        
        self.high_entropy_threshold = high_entropy_threshold
        self.low_entropy_threshold = low_entropy_threshold
        self.significance_level = significance_level
        logger.info("EntropyDecisionEngine initialized with thresholds: "
                    f"High={high_entropy_threshold}, Low={low_entropy_threshold}")

    def _calculate_shannon_entropy(self, distribution: List[float]) -> float:
        """
        Calculate normalized Shannon Entropy.
        
        Helper function to calculate entropy of a probability distribution.
        Normalized to be between 0 and 1.
        
        Args:
            distribution: A list of probabilities summing to 1.
            
        Returns:
            float: The normalized entropy value.
        """
        entropy = 0.0
        for probability in distribution:
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize: Max entropy for binary distribution is log2(2) = 1
        # But for general cases, we assume binary feedback context here
        return entropy

    def compute_feedback_metrics(self, feedback: NodeFeedback) -> Tuple[float, float]:
        """
        Compute the entropy and approval rate of the feedback.
        
        Core Function 1.
        
        Args:
            feedback: The NodeFeedback data object.
            
        Returns:
            Tuple[float, float]: (Entropy Score, Approval Rate)
            
        Raises:
            ValueError: If total interactions is zero.
        """
        if feedback.total_interactions == 0:
            logger.error(f"Node {feedback.node_id}: Cannot compute metrics for zero interactions.")
            raise ValueError("Insufficient data for calculation")

        p_pos = feedback.positive_feedback / feedback.total_interactions
        p_neg = feedback.negative_feedback / feedback.total_interactions
        
        # Calculate Entropy
        entropy = self._calculate_shannon_entropy([p_pos, p_neg])
        
        logger.debug(f"Node {feedback.node_id}: Entropy={entropy:.4f}, "
                     f"Approval={p_pos:.2f}")
        
        return entropy, p_pos

    def decide_node_action(self, feedback: NodeFeedback) -> NodeAction:
        """
        Decide the lifecycle action for a node based on feedback entropy.
        
        Core Function 2.
        Implements the decision tree logic based on entropy and approval rates.
        
        Decision Logic:
        1. Check Sample Size: If too small -> RETAIN (insufficient data)
        2. Check Entropy:
           - HIGH (Polarized): Context-dependent -> CONTEXTUALIZE
           - LOW (Consistent):
             - If Approval High -> RETAIN
             - If Approval Low -> RETRAIN or TERMINATE
           - MEDIUM: Maintain status quo -> RETAIN
        
        Args:
            feedback: The feedback data for the node.
            
        Returns:
            NodeAction: The recommended action.
        """
        try:
            # Step 1: Sample Size Significance Check
            if feedback.total_interactions < self.significance_level:
                logger.info(f"Node {feedback.node_id}: Insufficient sample size. Action: RETAIN")
                return NodeAction.RETAIN

            entropy, approval_rate = self.compute_feedback_metrics(feedback)

            # Step 2: High Entropy Branch (Polarization)
            if entropy > self.high_entropy_threshold:
                logger.info(f"Node {feedback.node_id}: High Entropy detected ({entropy:.2f}). "
                            "Feedback is polarized. Action: CONTEXTUALIZE")
                return NodeAction.CONTEXTUALIZE

            # Step 3: Low Entropy Branch (Consensus)
            if entropy < self.low_entropy_threshold:
                if approval_rate > 0.7:
                    logger.info(f"Node {feedback.node_id}: Low Entropy, High Approval. Action: RETAIN")
                    return NodeAction.RETAIN
                
                if approval_rate < 0.3:
                    logger.warning(f"Node {feedback.node_id}: Low Entropy, Low Approval. "
                                   "Consensus on failure. Action: TERMINATE")
                    return NodeAction.TERMINATE
                
                # Moderate approval but consistent
                logger.info(f"Node {feedback.node_id}: Low Entropy, Medium Approval. Action: RETRAIN")
                return NodeAction.RETRAIN

            # Step 4: Medium Entropy (Uncertainty/Transition)
            logger.info(f"Node {feedback.node_id}: Medium Entropy. Action: RETAIN (Observe)")
            return NodeAction.RETAIN

        except Exception as e:
            logger.exception(f"Error processing node {feedback.node_id}: {str(e)}")
            # Fail-safe: Retain node if analysis crashes
            return NodeAction.RETAIN

def run_symbiosis_cycle(feedback_data: List[Dict[str, Any]]) -> Dict[str, NodeAction]:
    """
    Helper function to process a batch of feedback data.
    
    Args:
        feedback_data: List of dictionaries containing raw feedback.
       
    Returns:
        Dict mapping node_ids to recommended actions.
    """
    engine = EntropyDecisionEngine()
    results = {}
    
    logger.info(f"Starting Symbiosis Cycle for {len(feedback_data)} nodes.")
    
    for raw_data in feedback_data:
        try:
            # Validate and Create Data Object
            node_fb = NodeFeedback(
                node_id=raw_data.get('id'),
                positive_feedback=raw_data.get('positive', 0),
                negative_feedback=raw_data.get('negative', 0),
                total_interactions=raw_data.get('total', 0)
            )
            
            # Get Decision
            action = engine.decide_node_action(node_fb)
            results[node_fb.node_id] = action
            
        except Exception as e:
            logger.error(f"Skipping invalid data entry {raw_data.get('id')}: {e}")
            
    return results

# --- Usage Example ---
if __name__ == "__main__":
    # Example Data representing different feedback scenarios
    sample_data = [
        {
            "id": "node_001", 
            "positive": 50, "negative": 50, "total": 100
            # High Entropy (max uncertainty) -> Should CONTEXTUALIZE
        },
        {
            "id": "node_002", 
            "positive": 95, "negative": 5, "total": 100
            # Low Entropy, High Approval -> Should RETAIN
        },
        {
            "id": "node_003", 
            "positive": 2, "negative": 98, "total": 100
            # Low Entropy, Low Approval -> Should TERMINATE
        },
        {
            "id": "node_004", 
            "positive": 1, "negative": 1, "total": 2
            # Insufficient Data -> Should RETAIN
        }
    ]

    print("--- Processing Feedback Batch ---")
    decisions = run_symbiosis_cycle(sample_data)
    
    for node_id, action in decisions.items():
        print(f"Node: {node_id:<10} | Decision: {action.value}")