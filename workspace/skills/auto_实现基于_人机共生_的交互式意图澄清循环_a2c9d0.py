"""
Module: interactive_intent_clarification.py

Description:
    Implements a 'Human-Computer Symbiosis' based interactive intent clarification loop.
    When the confidence of a fuzzy intent is below a threshold, the system generates
    a 'Minimum Cost Falsification Question' to ask the human operator.

    The core challenge addressed herein is efficiently retrieving the key decision
    point capable of distinguishing the current intent branch from a large set of
    nodes (e.g., 3882 nodes) and presenting it in natural language rather than technical terms.

Domain: HCI / AGI Skill

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configurations ---
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
MINIMUM_NODES_FOR_SPLIT = 2
MAX_RETRRIEVAL_CANDIDATES = 50  # Limit search space for performance

class IntentNodeError(Exception):
    """Custom exception for errors related to intent node processing."""
    pass

class QueryGenerationError(Exception):
    """Custom exception for failures in generating natural language queries."""
    pass

@dataclass
class IntentNode:
    """
    Represents a node in the Intent Knowledge Graph.
    
    Attributes:
        id: Unique identifier for the node.
        description: Human-readable description of the intent.
        embedding: Vector representation of the intent (mocked for this skill).
        attributes: Key-value pairs used for distinguishing this intent (e.g., {'target': 'file', 'action': 'delete'}).
    """
    id: str
    description: str
    embedding: List[float] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not self.description:
            raise ValueError("Node ID and description cannot be empty.")

@dataclass
class ClarificationContext:
    """
    Maintains the state of the current interaction loop.
    
    Attributes:
        candidate_nodes: The current subset of nodes that potentially match the user's intent.
        history: Record of previous questions and answers to avoid repetition.
    """
    candidate_nodes: List[IntentNode]
    history: List[Tuple[str, bool]] = field(default_factory=list) # (Question, Answer)

def _calculate_attribute_entropy(
    nodes: List[IntentNode], 
    attribute_key: str
) -> float:
    """
    [Helper Function] Calculate the Shannon entropy of a specific attribute key across the node list.
    
    High entropy indicates that the attribute splits the nodes into roughly equal groups,
    making it an ideal candidate for a binary search question (Minimum Cost Falsification).
    
    Args:
        nodes: List of IntentNode objects.
        attribute_key: The key of the attribute to evaluate.
        
    Returns:
        float: The entropy value (0.0 to 1.0 for binary splits).
    """
    if not nodes:
        return 0.0
    
    # Count presence vs absence (or specific values)
    # For simplicity, we treat this as a binary split: Has Value vs No Value (or Value A vs Value B)
    # Here we implement a value-frequency entropy
    value_counts: Dict[Any, int] = {}
    
    for node in nodes:
        # Use .get() to handle missing keys, defaulting to a specific 'Undefined' token
        val = node.attributes.get(attribute_key, "__UNDEFINED__")
        value_counts[val] = value_counts.get(val, 0) + 1
        
    total_count = len(nodes)
    entropy = 0.0
    
    for count in value_counts.values():
        if count == 0: continue
        probability = count / total_count
        entropy -= probability * math.log2(probability)
        
    return entropy

def retrieve_discriminatory_attribute(
    context: ClarificationContext,
    current_user_input: str
) -> Tuple[str, List[Any]]:
    """
    [Core Function 1] Retrieves the optimal attribute to question the user about.
    
    This function simulates the 'Fast Retrieval' from a large node space by filtering
    the candidate set (which represents the local neighborhood of the search space).
    It selects the attribute with the highest information gain (entropy).
    
    Args:
        context: The current interaction context containing candidate nodes.
        current_user_input: The raw user input (used for context awareness, mocked here).
        
    Returns:
        A tuple containing:
        - The attribute key (str) to ask about.
        - A list of possible values for that attribute (for generating the question).
        
    Raises:
        IntentNodeError: If the candidate list is empty or too small to discriminate.
    """
    logger.info(f"Analyzing {len(context.candidate_nodes)} candidate nodes for discrimination.")
    
    if len(context.candidate_nodes) < MINIMUM_NODES_FOR_SPLIT:
        logger.warning("Insufficient nodes to generate a discriminatory question.")
        raise IntentNodeError("Intent clarified or node list exhausted.")

    # Step 1: Gather all potential attributes from the candidate nodes
    possible_keys = set()
    for node in context.candidate_nodes:
        possible_keys.update(node.attributes.keys())
    
    # Step 2: Filter keys that have already been asked in history
    asked_keys = {q.split("'")[1] for q, _ in context.history if "'" in q} # Simple parsing of history
    candidate_keys = possible_keys - asked_keys
    
    if not candidate_keys:
        logger.info("All attributes exhausted. Proceeding with best guess.")
        raise IntentNodeError("No more distinguishing attributes available.")

    # Step 3: Score attributes by Entropy (Information Gain)
    best_key = None
    max_entropy = -1.0
    
    # Optimization: If node count is huge, sample a subset for speed
    evaluation_nodes = context.candidate_nodes
    if len(evaluation_nodes) > MAX_RETRRIEVAL_CANDIDATES:
        evaluation_nodes = random.sample(evaluation_nodes, MAX_RETRRIEVAL_CANDIDATES)
        
    for key in candidate_keys:
        entropy = _calculate_attribute_entropy(evaluation_nodes, key)
        # We want the attribute that splits the group most evenly (closest to 1.0 for binary)
        if entropy > max_entropy:
            max_entropy = entropy
            best_key = key
            
    if best_key is None:
        # Fallback if entropy calculation fails (e.g., all attributes are identical)
        best_key = next(iter(candidate_keys))

    # Extract unique values for the best key
    unique_values = list(set(
        n.attributes.get(best_key) for n in context.candidate_nodes if n.attributes.get(best_key)
    ))
    
    logger.info(f"Selected discriminatory attribute: '{best_key}' with entropy {max_entropy:.4f}")
    return best_key, unique_values

def generate_human_readable_query(
    attribute_key: str, 
    possible_values: List[Any]
) -> str:
    """
    [Core Function 2] Converts a technical attribute key and values into a human-friendly question.
    
    Implements the 'Human-Computer Symbiosis' requirement by translating data-schema logic
    into natural language.
    
    Args:
        attribute_key: The technical key (e.g., 'target_type').
        possible_values: The list of values found in the cluster (e.g., ['file', 'directory']).
        
    Returns:
        A natural language question string.
        
    Raises:
        QueryGenerationError: If arguments are invalid.
    """
    if not attribute_key:
        raise QueryGenerationError("Attribute key cannot be empty.")

    # Mapping technical keys to natural language templates
    # In a real AGI system, this would use an LLM or a template engine
    templates = {
        "target_type": "Are you trying to interact with a specific type of entity, like {vals}?",
        "time_range": "Is this request related to a specific time frame, such as {vals}?",
        "action_scope": "Do you want to perform this operation on a {vals} scale?",
        "device_context": "Are you currently using the {vals} device?"
    }
    
    # Format values for display
    val_str = " or ".join(str(v) for v in possible_values[:3]) # Limit to 3 for brevity
    
    # Get template or default fallback
    question = templates.get(attribute_key)
    
    if question:
        return question.format(vals=val_str)
    else:
        # Heuristic formatting for unknown keys
        clean_key = attribute_key.replace("_", " ")
        return f"Regarding the {clean_key}, does the concept of '{val_str}' apply to your request?"

def run_clarification_loop(
    initial_candidates: List[IntentNode],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Optional[IntentNode]:
    """
    [Driver Function / Usage Example] Simulates the interaction loop.
    
    Note: In a real deployment, user input would be async. This simulates the logic flow.
    
    Args:
        initial_candidates: The list of potential intent nodes retrieved from vector search.
        confidence_threshold: The threshold below which we ask questions.
        
    Returns:
        The final IntentNode if identified, else None.
    """
    print(f"\n--- Starting Clarification Loop with {len(initial_candidates)} candidates ---")
    context = ClarificationContext(candidate_nodes=initial_candidates)
    
    # Mock loop iterations
    for iteration in range(3): # Max 3 questions to avoid user fatigue
        # 1. Check Confidence (Mock logic: if only 1 node left, confidence is high)
        if len(context.candidate_nodes) == 1:
            print(f"High confidence achieved. Selected: {context.candidate_nodes[0].id}")
            return context.candidate_nodes[0]
            
        try:
            # 2. Find the best attribute to split the remaining nodes
            key, values = retrieve_discriminatory_attribute(context, "mock_user_input")
            
            # 3. Generate Question
            question = generate_human_readable_query(key, values)
            print(f"\nSystem Question: {question}")
            
            # 4. Simulate User Response (Human-in-the-loop)
            # In this simulation, we randomly filter nodes to mimic a user saying "Yes, it's a file"
            # Real implementation would wait for API input.
            user_answer = random.choice(values) 
            print(f"User Answer (Simulated): Yes, it is related to '{user_answer}'")
            
            # 5. Filter Candidates
            new_candidates = [
                n for n in context.candidate_nodes 
                if n.attributes.get(key) == user_answer
            ]
            
            if not new_candidates:
                print("No matching intents found after filtering. Rolling back or stopping.")
                break
                
            context.candidate_nodes = new_candidates
            context.history.append((question, True))
            
        except IntentNodeError as e:
            logger.info(f"Loop terminated: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error in loop: {e}")
            break

    # Fallback
    return context.candidate_nodes[0] if context.candidate_nodes else None

# --- Data Definitions for Demonstration ---
def load_mock_data() -> List[IntentNode]:
    """Generates mock data resembling a subset of a 3882 node graph."""
    nodes = []
    actions = ["delete", "archive", "move", "copy"]
    targets = ["file", "folder", "disk", "network_share"]
    
    for i in range(50): # Creating 50 ambiguous nodes
        action = random.choice(actions)
        target = random.choice(targets)
        nodes.append(IntentNode(
            id=f"intent_{i}_{action}_{target}",
            description=f"User wants to {action} a {target}",
            attributes={"action_type": action, "target_type": target}
        ))
    return nodes

if __name__ == "__main__":
    # Example Usage
    mock_nodes = load_mock_data()
    final_intent = run_clarification_loop(mock_nodes)
    
    if final_intent:
        print(f"\n>>> Final Identified Intent: {final_intent.description}")
    else:
        print("\n>>> Failed to identify intent.")