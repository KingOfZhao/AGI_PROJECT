"""
Module: adaptive_human_feedback_resolver
Description: Implements an active learning strategy to resolve ambiguities in human feedback
             by generating an optimized inquiry list that minimizes cognitive load.
Domain: HCI / Active Learning

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Enumeration for different types of feedback ambiguity."""
    UNCLEAR_INTENT = "unclear_intent"
    DATA_CONFLICT = "data_conflict"
    CONTEXT_MISSING = "context_missing"
    NOVEL_NODE = "novel_node"


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge graph or a data point requiring validation."""
    id: str
    content: str
    ambiguity_score: float  # 0.0 (clear) to 1.0 (highly ambiguous)
    cognitive_load_estimate: float  # Estimated effort for a human to verify
    feedback_type: FeedbackType
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0.0 <= self.ambiguity_score <= 1.0:
            raise ValueError(f"Invalid ambiguity score for node {self.id}. Must be between 0 and 1.")
        if self.cognitive_load_estimate < 0:
            raise ValueError("Cognitive load cannot be negative.")


@dataclass
class Inquiry:
    """Represents a generated question or inquiry task for the human."""
    target_node_id: str
    inquiry_text: str
    estimated_effort: float
    information_gain: float
    priority_score: float = 0.0


class CognitiveLoadManager:
    """
    Manages the selection of inquiries based on cognitive load theories.
    Ensures the total cognitive burden of the inquiry list remains within limits.
    """

    def __init__(self, max_cognitive_capacity: float = 1.0):
        self.max_cognitive_capacity = max_cognitive_capacity

    def calculate_inquiry_priority(self, node: KnowledgeNode) -> float:
        """
        Calculates the priority of inquiring about a specific node.
        Uses a heuristic balancing information gain (ambiguity resolution) vs cost (load).
        """
        # Prevent division by zero
        if node.cognitive_load_estimate == 0:
            return float('inf')
        
        # Higher ambiguity means higher potential gain, but we penalize high effort
        # Priority = (Ambiguity Score * Potential Info Gain Factor) / Cognitive Cost
        priority = (node.ambiguity_score * 10.0) / node.cognitive_load_estimate
        return priority


class ActiveFeedbackSystem:
    """
    Core system for resolving feedback ambiguity via active learning.
    Generates a minimal inquiry list to validate new nodes.
    """

    def __init__(self, cognitive_capacity_threshold: float = 0.75):
        """
        Initialize the system.
        
        Args:
            cognitive_capacity_threshold (float): The max cumulative cognitive load allowed 
                                                  in a single inquiry batch (0.0 to 1.0).
        """
        self.load_manager = CognitiveLoadManager()
        self.capacity_threshold = cognitive_capacity_threshold
        logger.info(f"System initialized with capacity threshold: {cognitive_capacity_threshold}")

    def _validate_node_batch(self, nodes: List[KnowledgeNode]) -> None:
        """Helper function to validate input data."""
        if not nodes:
            logger.warning("Input node list is empty.")
            return
        
        for node in nodes:
            if not isinstance(node, KnowledgeNode):
                raise TypeError(f"Invalid type in input list: {type(node)}")

    def _generate_inquiry_text(self, node: KnowledgeNode) -> str:
        """
        Generates natural language inquiry based on node content and type.
        (Mock implementation for demonstration)
        """
        if node.feedback_type == FeedbackType.NOVEL_NODE:
            return f"Is the concept '{node.content}' relevant and valid in this context?"
        elif node.feedback_type == FeedbackType.DATA_CONFLICT:
            return f"The data conflicts regarding '{node.content}'. Which source is correct?"
        else:
            return f"Please clarify the intent regarding '{node.content}'."

    def resolve_ambiguity(self, candidate_nodes: List[KnowledgeNode]) -> Tuple[List[Inquiry], float]:
        """
        Main strategy function. Selects the optimal set of inquiries to maximize 
        information gain while minimizing cognitive load.

        Args:
            candidate_nodes (List[KnowledgeNode]): List of new or ambiguous nodes detected.

        Returns:
            Tuple[List[Inquiry], float]: A list of optimized inquiries and the total 
                                         cognitive load used.
        
        Example:
            >>> system = ActiveFeedbackSystem()
            >>> nodes = [KnowledgeNode(...), KnowledgeNode(...)]
            >>> inquiries, load = system.resolve_ambiguity(nodes)
        """
        try:
            self._validate_node_batch(candidate_nodes)
        except TypeError as e:
            logger.error(f"Input validation failed: {e}")
            return [], 0.0

        logger.info(f"Processing {len(candidate_nodes)} candidate nodes for active learning.")

        # Calculate priority for all nodes
        prioritized_nodes = []
        for node in candidate_nodes:
            priority = self.load_manager.calculate_inquiry_priority(node)
            prioritized_nodes.append((node, priority))
        
        # Sort by priority (descending) to pick high-value, low-cost items first
        prioritized_nodes.sort(key=lambda x: x[1], reverse=True)

        selected_inquiries: List[Inquiry] = []
        current_load = 0.0

        # Knapsack-style selection (Greedy approach)
        for node, priority in prioritized_nodes:
            # Check if adding this inquiry exceeds cognitive capacity
            if (current_load + node.cognitive_load_estimate) <= self.capacity_threshold:
                inquiry_text = self._generate_inquiry_text(node)
                
                inquiry = Inquiry(
                    target_node_id=node.id,
                    inquiry_text=inquiry_text,
                    estimated_effort=node.cognitive_load_estimate,
                    information_gain=node.ambiguity_score,
                    priority_score=priority
                )
                
                selected_inquiries.append(inquiry)
                current_load += inquiry.estimated_effort
                logger.debug(f"Selected node {node.id} (Load: {inquiry.estimated_effort})")
            else:
                # If we skip a node, we continue checking smaller nodes due to sorting logic
                # or break if strictly strictly sorted by density and capacity is hard limit.
                continue

        logger.info(f"Generated {len(selected_inquiries)} inquiries. Total load: {current_load:.2f}")
        return selected_inquiries, current_load


# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    # 1. Simulate input data: New nodes detected by the AGI system with ambiguity
    node_A = KnowledgeNode(
        id="node_101",
        content="Quantum Entanglement",
        ambiguity_score=0.9,  # High ambiguity (needs verification)
        cognitive_load_estimate=0.6,  # Hard concept to verify
        feedback_type=FeedbackType.NOVEL_NODE
    )

    node_B = KnowledgeNode(
        id="node_102",
        content="User Preference: Dark Mode",
        ambiguity_score=0.4,
        cognitive_load_estimate=0.1,  # Easy to verify
        feedback_type=FeedbackType.UNCLEAR_INTENT
    )

    node_C = KnowledgeNode(
        id="node_103",
        content="Database Schema Update",
        ambiguity_score=0.8,
        cognitive_load_estimate=0.3,
        feedback_type=FeedbackType.DATA_CONFLICT
    )

    node_D = KnowledgeNode(
        id="node_104",
        content="Typo in variable name",
        ambiguity_score=0.1,
        cognitive_load_estimate=0.05,
        feedback_type=FeedbackType.NOVEL_NODE
    )

    raw_nodes = [node_A, node_B, node_C, node_D]

    # 2. Initialize System
    # Setting capacity to 0.7 means we prioritize efficiently
    resolver = ActiveFeedbackSystem(cognitive_capacity_threshold=0.7)

    # 3. Generate Inquiry List
    try:
        inquiries, total_load = resolver.resolve_ambiguity(raw_nodes)

        print("\n" + "="*30)
        print("Generated Inquiry List (Optimized for Cognitive Load)")
        print("="*30)
        
        for i, iq in enumerate(inquiries, 1):
            print(f"{i}. [Effort: {iq.estimated_effort}] {iq.inquiry_text}")
        
        print("-" * 30)
        print(f"Total Cognitive Load Used: {total_load:.2f} (Limit: 0.7)")
        print("="*30 + "\n")

    except Exception as e:
        logger.critical(f"System failure during execution: {e}", exc_info=True)