"""
Module: active_questioning_strategy.py

This module implements a Human-Machine Symbiosis strategy for Active Learning.
It identifies 'Cognitive Boundaries' (nodes with high uncertainty and high importance)
and generates an optimized 'Minimal Question Set' for human experts.

The goal is to minimize human labeling effort while maximizing the reduction of
network entropy (uncertainty). Questions are structured as Yes/No or Multiple Choice.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
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


class QuestionType(Enum):
    """Enumeration for supported question types."""
    BINARY = "YES_NO"
    MULTI_CHOICE = "MULTI_CHOICE"


@dataclass
class CognitiveNode:
    """
    Represents a processing node in the AGI network.
    
    Attributes:
        id: Unique identifier for the node.
        uncertainty: Float between 0.0 and 1.0 representing model uncertainty (entropy).
        importance: Float between 0.0 and 1.0 representing the node's impact on the final output.
        options: Optional dictionary of possible choices for multi-select scenarios.
        content: The data or context associated with the node (e.g., text, image path).
    """
    id: str
    uncertainty: float
    importance: float
    content: Any
    options: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate data types and ranges after initialization."""
        if not isinstance(self.id, str):
            raise ValueError("Node ID must be a string.")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError(f"Uncertainty for node {self.id} must be between 0.0 and 1.0.")
        if not (0.0 <= self.importance <= 1.0):
            raise ValueError(f"Importance for node {self.id} must be between 0.0 and 1.0.")


@dataclass
class Question:
    """
    Represents a generated question for a human expert.
    
    Attributes:
        node_id: ID of the source node.
        question_text: The formatted question string.
        q_type: The type of question (BINARY or MULTI_CHOICE).
        expected_info_gain: Estimated reduction in entropy.
        choices: Available choices if applicable.
    """
    node_id: str
    question_text: str
    q_type: QuestionType
    expected_info_gain: float
    choices: Optional[List[str]] = None


def _calculate_symbiosis_score(
    node: CognitiveNode, 
    w_u: float = 0.6, 
    w_i: float = 0.4
) -> float:
    """
    [Helper Function] Calculate the priority score for a node.
    
    Strategy: In a human-machine symbiosis, we prioritize nodes that the machine
    is unsure about (high uncertainty) AND that matter significantly for the 
    final goal (high importance).
    
    Args:
        node: The CognitiveNode to evaluate.
        w_u: Weight for uncertainty (default 0.6).
        w_i: Weight for importance (default 0.4).
        
    Returns:
        A float score representing the criticality of clarifying this node.
    """
    if w_u + w_i == 0:
        return 0.0
    # Normalize weights just in case
    norm_w_u = w_u / (w_u + w_i)
    norm_w_i = w_i / (w_u + w_i)
    
    score = (node.uncertainty * norm_w_u) + (node.importance * norm_w_i)
    return score


def identify_cognitive_boundaries(
    nodes: List[CognitiveNode], 
    threshold: float = 0.75
) -> List[Tuple[CognitiveNode, float]]:
    """
    [Core Function 1] Filter and sort nodes based on their position relative to the Cognitive Boundary.
    
    Cognitive Boundaries are defined here as states where the system has high uncertainty
    regarding critical information. This function identifies where the machine needs
    human intervention to proceed effectively.
    
    Args:
        nodes: A list of CognitiveNode objects.
        threshold: The minimum symbiosis score (0.0-1.0) required to consider a node a boundary.
        
    Returns:
        A sorted list of tuples (Node, Score) requiring attention, descending by score.
        
    Raises:
        ValueError: If the input list is empty or threshold is invalid.
    """
    if not nodes:
        logger.warning("Input node list is empty.")
        return []
    
    if not (0.0 <= threshold <= 1.0):
        logger.error(f"Invalid threshold: {threshold}")
        raise ValueError("Threshold must be between 0.0 and 1.0")

    boundary_nodes = []
    
    logger.info(f"Scanning {len(nodes)} nodes for cognitive boundaries...")
    
    for node in nodes:
        try:
            score = _calculate_symbiosis_score(node)
            if score >= threshold:
                boundary_nodes.append((node, score))
                logger.debug(f"Node {node.id} identified as boundary with score {score:.4f}")
        except Exception as e:
            logger.error(f"Error processing node {node.id}: {e}")
            continue

    # Sort by score descending to prioritize the most critical ambiguities
    boundary_nodes.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Identified {len(boundary_nodes)} cognitive boundary nodes.")
    return boundary_nodes


def generate_minimal_question_set(
    boundary_nodes: List[Tuple[CognitiveNode, float]], 
    max_questions: int = 5
) -> List[Question]:
    """
    [Core Function 2] Generate a minimal set of questions to maximize entropy reduction.
    
    This function converts high-priority nodes into structured queries (Yes/No or Multi-choice).
    It limits the number of questions to avoid overloading the human expert, adhering to the
    'minimal human cost' principle.
    
    Args:
        boundary_nodes: List of tuples containing nodes and their scores.
        max_questions: Maximum number of questions to generate (human attention budget).
        
    Returns:
        A list of Question objects ready to be presented to a human.
    """
    if not boundary_nodes:
        logger.info("No boundary nodes provided for question generation.")
        return []

    question_set = []
    
    # Limit the iteration to the budget
    limit = min(len(boundary_nodes), max_questions)
    
    logger.info(f"Generating minimal question set (Max: {limit})...")
    
    for i in range(limit):
        node, score = boundary_nodes[i]
        
        try:
            # Determine Question Type based on available data
            if node.options and len(node.options) > 1:
                q_type = QuestionType.MULTI_CHOICE
                # Format options into a list
                choices = [f"{k}: {v}" for k, v in node.options.items()]
                text = f"Context: {node.content}\nWhich classification is correct?"
                
            else:
                q_type = QuestionType.BINARY
                # Generate a binary confirmation question
                # In a real AGI system, this would formulate a hypothesis
                text = f"Context: {node.content}\nIs this concept relevant or positive?"
                choices = ["Yes", "No"]
            
            # Estimate information gain (simplified as score * uncertainty factor)
            info_gain = score * node.uncertainty
            
            new_question = Question(
                node_id=node.id,
                question_text=text,
                q_type=q_type,
                expected_info_gain=info_gain,
                choices=choices
            )
            question_set.append(new_question)
            
        except Exception as e:
            logger.error(f"Failed to generate question for node {node.id}: {e}")
    
    logger.info(f"Generated {len(question_set)} questions.")
    return question_set


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Simulate a stream of cognitive nodes from an AGI system
    # Some nodes are certain (background processing), some are important but uncertain (boundaries)
    sample_nodes = [
        CognitiveNode(id="n_001", uncertainty=0.1, importance=0.2, content="User logged in."), # Low priority
        CognitiveNode(id="n_002", uncertainty=0.95, importance=0.9, content="Ambiguous command: 'Open the bank'", 
                      options={"A": "River bank", "B": "Financial institution", "C": "Blood bank"}), # High priority
        CognitiveNode(id="n_003", uncertainty=0.85, importance=0.5, content="Detecting object in fog"), # Medium priority
        CognitiveNode(id="n_004", uncertainty=0.99, importance=0.99, content="Ethical dilemma: Autonomous braking decision"), # Critical priority
        CognitiveNode(id="n_005", uncertainty=0.05, importance=0.9, content="System core heartbeat"), # Certain, High importance (No need to ask)
    ]

    try:
        print("--- Active Learning Strategy: Human-Machine Symbiosis ---")
        
        # 2. Identify Cognitive Boundaries (Where do we need help?)
        # We look for high uncertainty AND high importance
        boundaries = identify_cognitive_boundaries(sample_nodes, threshold=0.6)
        
        # 3. Generate the Minimal Question Set (Ask the human efficiently)
        questions = generate_minimal_question_set(boundaries, max_questions=3)
        
        # 4. Display the questions
        print(f"\nGenerated {len(questions)} Questions for Human Expert:\n")
        for idx, q in enumerate(questions, 1):
            print(f"[{idx}] Node: {q.node_id} | Expected Info Gain: {q.expected_info_gain:.3f}")
            print(f"    Type: {q.q_type.value}")
            print(f"    Question: {q.question_text}")
            if q.choices:
                print(f"    Choices: {q.choices}")
            print("-" * 40)
            
    except ValueError as ve:
        logger.critical(f"Validation Error in Main Execution: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}")