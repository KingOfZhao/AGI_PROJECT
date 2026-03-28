"""
Module: human_in_loop_verification_cost_metric.py

This module implements an evaluation metric system for AGI/HCI contexts to manage
the cost of human verification. It introduces a "Verification Urgency" score to
prioritize knowledge nodes (concepts, functions, or data points) that require
human validation.

The core philosophy is to minimize human cognitive load by automating the
triage of verification tasks. It identifies nodes where AI confidence is
dropping despite frequent usage (high entropy/high impact) and assigns a
specific "Action Level" to guide the human operator.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class VerificationAction(Enum):
    """Enumeration of possible verification actions for human operators."""
    AUTO_CONFIRM = auto()       # High confidence, low risk -> Auto-validated or simple "OK"
    QUICK_REVIEW = auto()       # Medium risk -> Binary choice (Yes/No)
    DEEP_INSPECTION = auto()    # High risk -> Requires parameter tuning or logic check
    FULL_REWRITE = auto()       # Critical failure -> Requires code rewrite or concept redefinition

@dataclass
class KnowledgeNode:
    """
    Represents a node in the AGI knowledge graph or memory store.
    
    Attributes:
        node_id: Unique identifier for the node.
        content: The actual data/code/concept string.
        usage_count: How often this node is retrieved or executed.
        success_count: How many times the execution led to a positive outcome.
        cumulative_confidence: Aggregated confidence score from AI invocations.
        last_validated_ts: Timestamp of the last human check (unix epoch).
    """
    node_id: str
    content: str
    usage_count: int = 0
    success_count: int = 0
    cumulative_confidence: float = 0.0  # Range 0.0 to 1.0
    last_validated_ts: int = 0

    @property
    def average_confidence(self) -> float:
        """Calculates the average confidence score."""
        if self.usage_count == 0:
            return 0.0
        return self.cumulative_confidence / self.usage_count

@dataclass
class VerificationTask:
    """
    Represents a prioritized task for a human operator.
    """
    node_id: str
    urgency_score: float
    action_required: VerificationAction
    estimated_time_seconds: int
    reason: str

class VerificationCostEvaluator:
    """
    Evaluates the cost and urgency of verifying knowledge nodes in an AGI system.
    
    This class implements algorithms to calculate "Verification Urgency" based on
    usage frequency, confidence decay, and error rates. It categorizes tasks into
    different complexity levels to optimize human time (HITL optimization).
    """

    def __init__(self, 
                 weight_frequency: float = 0.4, 
                 weight_confidence: float = 0.4, 
                 weight_recency: float = 0.2,
                 confidence_threshold: float = 0.85):
        """
        Initialize the evaluator with weighting parameters.
        
        Args:
            weight_frequency: Weight for usage frequency in urgency calculation.
            weight_confidence: Weight for low confidence (inverse) in urgency calculation.
            weight_recency: Weight for how long since the last validation.
            confidence_threshold: Baseline for acceptable confidence.
        """
        if not (0 <= weight_frequency <= 1 and 0 <= weight_confidence <= 1):
            raise ValueError("Weights must be between 0 and 1.")
        
        self.weight_frequency = weight_frequency
        self.weight_confidence = weight_confidence
        self.weight_recency = weight_recency
        self.confidence_threshold = confidence_threshold
        logger.info("VerificationCostEvaluator initialized with weights: freq=%.2f, conf=%.2f", 
                    weight_frequency, weight_confidence)

    def calculate_verification_urgency(self, 
                                       node: KnowledgeNode, 
                                       current_time: int, 
                                       decay_rate: float = 0.05) -> float:
        """
        Calculates a normalized urgency score (0.0 to 1.0) for a specific node.
        
        Formula Logic:
        Urgency = (Norm_Frequency * W1) + ((1 - Confidence) * W2) + (Recency_Factor * W3)
        
        Args:
            node: The knowledge node to evaluate.
            current_time: Current timestamp to calculate staleness.
            decay_rate: Rate at which validation value decays over time.
            
        Returns:
            A float score between 0.0 (low urgency) and 1.0 (critical urgency).
        """
        if node.usage_count < 0:
            logger.error(f"Invalid usage count for node {node.node_id}")
            raise ValueError("Usage count cannot be negative")

        # 1. Frequency Score (Logarithmic scaling to handle large variances)
        # Adding 1 to avoid log(0)
        freq_score = math.log10(node.usage_count + 1) / 10.0 
        freq_score = min(max(freq_score, 0.0), 1.0) # Clamp to 0-1

        # 2. Confidence Deficit (Inverse of confidence)
        conf_deficit = 1.0 - node.average_confidence

        # 3. Recency Factor (Time since last validation)
        time_delta = current_time - node.last_validated_ts
        # Using exponential decay for staleness
        recency_factor = 1 - math.exp(-decay_rate * time_delta)

        # Weighted Sum
        urgency = (
            (freq_score * self.weight_frequency) +
            (conf_deficit * self.weight_confidence) +
            (recency_factor * self.weight_recency)
        )
        
        logger.debug(f"Node {node.node_id} Urgency: {urgency:.4f} (Freq: {freq_score:.2f}, Deficit: {conf_deficit:.2f})")
        return min(max(urgency, 0.0), 1.0)

    def determine_action_type(self, node: KnowledgeNode, urgency: float) -> VerificationAction:
        """
        Determines the type of human interaction required based on node state and urgency.
        
        Decision Logic:
        - If confidence is high but staleness is high -> QUICK_REVIEW (Sanity check)
        - If confidence is low and usage is high -> DEEP_INSPECTION
        - If error rate is extreme (success < 20%) -> FULL_REWRITE
        - Otherwise -> AUTO_CONFIRM
        """
        if node.usage_count == 0:
            return VerificationAction.AUTO_CONFIRM

        error_rate = 1.0 - (node.success_count / node.usage_count)

        # Critical Failures
        if error_rate > 0.8:
            return VerificationAction.FULL_REWRITE
        
        # High Urgency / Low Confidence
        if urgency > 0.7 and node.average_confidence < 0.5:
            return VerificationAction.DEEP_INSPECTION
        
        # Stale but potentially still valid
        if urgency > 0.5 and node.average_confidence >= self.confidence_threshold:
            return VerificationAction.QUICK_REVIEW
            
        # Low urgency
        return VerificationAction.AUTO_CONFIRM

    def generate_verification_queue(self, 
                                    nodes: List[KnowledgeNode], 
                                    current_time: int, 
                                    limit: int = 10) -> List[VerificationTask]:
        """
        Processes a list of nodes and returns a prioritized queue of verification tasks.
        
        This is the main entry point for the HITL system.
        
        Args:
            nodes: List of candidate nodes for verification.
            current_time: Current system time.
            limit: Maximum number of tasks to return (to cap human cost).
            
        Returns:
            A sorted list of VerificationTask objects.
        """
        tasks: List[VerificationTask] = []
        
        for node in nodes:
            try:
                urgency = self.calculate_verification_urgency(node, current_time)
                
                # Filter: Only queue if urgency is non-trivial
                if urgency < 0.1:
                    continue
                
                action = self.determine_action_type(node, urgency)
                
                # Estimate time cost based on action type
                time_cost = self._estimate_time_cost(action, len(node.content))
                
                reason = (f"Urgency: {urgency:.2f}. "
                          f"Confidence: {node.average_confidence:.2f}. "
                          f"Action: {action.name}")
                
                task = VerificationTask(
                    node_id=node.node_id,
                    urgency_score=urgency,
                    action_required=action,
                    estimated_time_seconds=time_cost,
                    reason=reason
                )
                tasks.append(task)
                
            except Exception as e:
                logger.error(f"Failed to process node {node.node_id}: {e}")
                continue

        # Sort by urgency descending
        tasks.sort(key=lambda x: x.urgency_score, reverse=True)
        
        logger.info(f"Generated {len(tasks)} tasks. Returning top {limit}.")
        return tasks[:limit]

    def _estimate_time_cost(self, action: VerificationAction, content_length: int) -> int:
        """
        Helper function to estimate human time cost in seconds.
        
        Args:
            action: The type of verification action.
            content_length: Length of the content string.
            
        Returns:
            Estimated seconds required.
        """
        base_reading_time = content_length / 10  # Approx 10 chars per second scanning
        
        if action == VerificationAction.AUTO_CONFIRM:
            return 2  # Instant click
        elif action == VerificationAction.QUICK_REVIEW:
            return max(5, int(base_reading_time * 0.5))
        elif action == VerificationAction.DEEP_INSPECTION:
            return max(60, int(base_reading_time * 2))
        elif action == VerificationAction.FULL_REWRITE:
            return max(300, int(content_length * 5)) # Writing takes time
        return 60

# --- Usage Example ---

if __name__ == "__main__":
    # Create dummy data
    current_timestamp = 1700000000
    
    # Node 1: Frequently used, high confidence (Low Urgency)
    node_a = KnowledgeNode(
        node_id="func_sum", 
        content="def sum(a, b): return a+b", 
        usage_count=1500, 
        cumulative_confidence=1450, # 0.96 conf
        success_count=1490,
        last_validated_ts=current_timestamp - 1000
    )
    
    # Node 2: Frequently used, dropping confidence (High Urgency)
    node_b = KnowledgeNode(
        node_id="func_complex_logic", 
        content="def process(x): ...complex logic...", 
        usage_count=500, 
        cumulative_confidence=200, # 0.4 conf
        success_count=300,
        last_validated_ts=current_timestamp - 50000
    )
    
    # Node 3: Never validated, very old (High Urgency)
    node_c = KnowledgeNode(
        node_id="legacy_data", 
        content="Key: Value", 
        usage_count=10, 
        cumulative_confidence=5,
        success_count=2,
        last_validated_ts=0 # Epoch
    )

    nodes_to_evaluate = [node_a, node_b, node_c]
    
    # Initialize Evaluator
    evaluator = VerificationCostEvaluator(
        weight_frequency=0.5, 
        weight_confidence=0.3, 
        weight_recency=0.2
    )
    
    # Generate Queue
    verification_queue = evaluator.generate_verification_queue(nodes_to_evaluate, current_timestamp)
    
    print("\n--- Human Verification Queue ---")
    for task in verification_queue:
        print(f"ID: {task.node_id}")
        print(f"  Urgency: {task.urgency_score:.4f}")
        print(f"  Action: {task.action_required.name}")
        print(f"  Est. Time: {task.estimated_time_seconds}s")
        print(f"  Reason: {task.reason}")
        print("-" * 30)