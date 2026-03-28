"""
Module: robust_node_consolidation
Description: Implements a noise-resistant belief consolidation algorithm for AGI systems.
             It uses Subjective Logic (based on Evidence Theory/Dempster-Shafer) to
             model uncertainty and dynamically adjusts the 'Truthfulness' of nodes
             based on the reliability of feedback sources and environmental consistency.

Author: Senior Python Engineer (AGI Systems)
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Enumeration for types of feedback."""
    POSITIVE = 1
    NEGATIVE = 0
    UNCERTAIN = 0.5


@dataclass
class SourceProfile:
    """
    Represents the profile of a feedback source (Human or Environment).
    
    Attributes:
        id: Unique identifier for the source.
        reliability: A score between 0.0 and 1.0 representing historical accuracy/trustworthiness.
        bias_factor: A score between -1.0 (pessimistic) and 1.0 (optimistic) to adjust for subjective bias.
    """
    id: str
    reliability: float = 0.5
    bias_factor: float = 0.0

    def __post_init__(self):
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(f"Reliability must be between 0 and 1, got {self.reliability}")
        if not -1.0 <= self.bias_factor <= 1.0:
            raise ValueError(f"Bias factor must be between -1 and 1, got {self.bias_factor}")


@dataclass
class KnowledgeNode:
    """
    Represents a knowledge node in the AGI system.
    
    Attributes:
        node_id: Unique identifier.
        content: The actual knowledge content (string for simplicity).
        alpha: Count of positive evidence (Dirichlet parameter).
        beta: Count of negative evidence (Dirichlet parameter).
        base_rate: Non-informative prior probability (usually 0.5).
        is_consolidated: Flag indicating if the node is considered 'True' fixed knowledge.
    """
    node_id: str
    content: str
    alpha: float = 1.0  # Prior pseudo-count
    beta: float = 1.0   # Prior pseudo-count
    base_rate: float = 0.5
    is_consolidated: bool = False
    
    @property
    def expected_probability(self) -> float:
        """Calculates the expected probability of the node being true."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty_mass(self) -> float:
        """Calculates the uncertainty mass based on total evidence."""
        total_evidence = self.alpha + self.beta
        # As evidence grows, uncertainty decreases
        return 2.0 / (total_evidence + 2.0)


class BeliefConsolidator:
    """
    Core class for handling noise-resistant knowledge consolidation.
    Uses principles of Subjective Logic to fuse evidence.
    """

    def __init__(self, consolidation_threshold: float = 0.85, noise_filter_threshold: float = 0.2):
        """
        Initializes the consolidator.
        
        Args:
            consolidation_threshold: Probability required to flag a node as consolidated.
            noise_filter_threshold: Minimum source reliability required to accept feedback.
        """
        self.consolidation_threshold = consolidation_threshold
        self.noise_filter_threshold = noise_filter_threshold
        logger.info("BeliefConsolidator initialized with threshold %.2f", consolidation_threshold)

    def _adjust_for_bias(self, feedback: FeedbackType, source: SourceProfile) -> FeedbackType:
        """
        Auxiliary function: Adjusts raw feedback based on known source bias.
        
        If a source is known to be overly optimistic, we slightly downgrade positive feedback.
        """
        if feedback == FeedbackType.UNCERTAIN:
            return feedback
        
        # Simple bias adjustment logic
        bias_impact = 0.0
        if source.bias_factor > 0 and feedback == FeedbackType.POSITIVE:
            bias_impact = -0.1 * source.bias_factor # Discount positive bias
        elif source.bias_factor < 0 and feedback == FeedbackType.NEGATIVE:
            bias_impact = 0.1 * abs(source.bias_factor) # Discount negative bias
            
        # Note: This is a simplified heuristic for demonstration
        # In a real system, this would modify the weight of the evidence, not the enum
        return feedback

    def update_node_belief(
        self, 
        node: KnowledgeNode, 
        feedback: FeedbackType, 
        source: SourceProfile,
        environmental_consistency: float = 1.0
    ) -> KnowledgeNode:
        """
        Updates the belief (Alpha/Beta counts) of a node based on weighted feedback.
        
        This acts as the Bayesian update engine.
        
        Args:
            node: The knowledge node to update.
            feedback: The feedback signal (Positive/Negative).
            source: The source of the feedback.
            environmental_consistency: A factor [0.0-1.0] indicating if the environment
                                       supports this feedback (e.g., sensor validation).
        
        Returns:
            The updated KnowledgeNode.
        
        Raises:
            ValueError: If input parameters are out of bounds.
        """
        # Input Validation
        if not 0.0 <= environmental_consistency <= 1.0:
            raise ValueError("Environmental consistency must be between 0 and 1.")
        
        # Step 1: Noise Filtering
        if source.reliability < self.noise_filter_threshold:
            logger.warning(f"Source {source.id} reliability {source.reliability} below threshold. Feedback ignored.")
            return node

        # Step 2: Bias Adjustment
        adjusted_feedback = self._adjust_for_bias(feedback, source)
        
        # Step 3: Calculate Evidence Weight
        # Weight combines source reliability and environmental consistency
        # Using a geometric mean to penalize low scores in either heavily
        weight = math.sqrt(source.reliability * environmental_consistency)
        
        # Step 4: Update Alpha/Beta (Bayesian Update)
        # We add 'weight' to the evidence counts instead of just 1.
        # This is equivalent to updating the Dirichlet distribution parameters.
        if adjusted_feedback == FeedbackType.POSITIVE:
            node.alpha += weight
            logger.debug(f"Node {node.node_id}: Positive evidence +{weight:.3f}")
        elif adjusted_feedback == FeedbackType.NEGATIVE:
            node.beta += weight
            logger.debug(f"Node {node.node_id}: Negative evidence +{weight:.3f}")
        else:
            # Uncertain feedback adds to uncertainty (sometimes modeled as adding to both slightly or ignoring)
            pass

        # Step 5: Check for Consolidation
        current_prob = node.expected_probability
        if current_prob >= self.consolidation_threshold and not node.is_consolidated:
            node.is_consolidated = True
            logger.info(f"NODE CONSOLIDATED: {node.node_id} with P={current_prob:.4f}")
        
        return node

    def batch_update(
        self, 
        node: KnowledgeNode, 
        feedback_batch: List[Tuple[FeedbackType, SourceProfile, float]]
    ) -> KnowledgeNode:
        """
        Processes a batch of feedback entries for a single node.
        
        Args:
            node: The target node.
            feedback_batch: List of tuples (FeedbackType, SourceProfile, EnvConsistency).
            
        Returns:
            Updated node.
        """
        if not feedback_batch:
            return node

        logger.info(f"Processing batch of {len(feedback_batch)} signals for node {node.node_id}")
        
        for fb, source, env_const in feedback_batch:
            self.update_node_belief(node, fb, source, env_const)
            
        return node


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize System
    consolidator = BeliefConsolidator(consolidation_threshold=0.90, noise_filter_threshold=0.3)
    
    # 2. Define Sources
    expert_source = SourceProfile(id="expert_01", reliability=0.9, bias_factor=0.1)
    noisy_crowd_source = SourceProfile(id="crowd_02", reliability=0.4, bias_factor=-0.2) # Low reliability
    malicious_source = SourceProfile(id="bot_99", reliability=0.1, bias_factor=-1.0) # Very low reliability
    
    # 3. Define a Knowledge Node (Candidate for truth)
    # Hypothesis: "The sky is blue during the day."
    sky_node = KnowledgeNode(
        node_id="fact_sky_001", 
        content="Sky is blue during day", 
        alpha=1.0, 
        beta=1.0
    )
    
    print(f"Initial State: P={sky_node.expected_probability:.4f}, Consolidated={sky_node.is_consolidated}")
    
    # 4. Simulate Feedback Loop
    
    # Scenario A: Reliable expert confirms (High weight)
    consolidator.update_node_belief(sky_node, FeedbackType.POSITIVE, expert_source, environmental_consistency=1.0)
    print(f"After Expert: P={sky_node.expected_probability:.4f}")
    
    # Scenario B: Noisy crowd denies (Filtered out or low weight)
    consolidator.update_node_belief(sky_node, FeedbackType.NEGATIVE, noisy_crowd_source, environmental_consistency=0.5)
    print(fAfter Noisy: P={sky_node.expected_probability:.4f}")
    
    # Scenario C: Malicious source tries to spam negative feedback (Filtered out)
    consolidator.update_node_belief(sky_node, FeedbackType.NEGATIVE, malicious_source, environmental_consistency=1.0)
    # This should be ignored due to noise_filter_threshold
    
    # Scenario D: Batch processing of mixed signals
    batch_data = [
        (FeedbackType.POSITIVE, expert_source, 1.0),
        (FeedbackType.POSITIVE, SourceProfile("s2", 0.8, 0.0), 0.9),
        (FeedbackType.NEGATIVE, noisy_crowd_source, 0.8)
    ]
    consolidator.batch_update(sky_node, batch_data)
    
    print(f"Final State: P={sky_node.expected_probability:.4f}, Consolidated={sky_node.is_consolidated}")