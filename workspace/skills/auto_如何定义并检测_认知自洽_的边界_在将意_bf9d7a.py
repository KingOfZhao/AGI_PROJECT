"""
Module: cognitive_boundary_guardian.py

This module implements an advanced 'Uncertainty Estimator' for AGI systems.
It is designed to detect the boundaries of 'Cognitive Self-Consistency' and
prevent the generation of hallucinated code when user intent exceeds the
system's 'Real Node' knowledge coverage.

Core Functionality:
1.  Semantic Distance Measurement: Evaluates how far an intent is from
    the center of the known knowledge graph.
2.  Logical Contradiction Detection: Identifies internal conflicts within
    complex intents.
3.  Human-in-the-loop Triggering: Determines the necessity for human intervention
    based on uncertainty scores.

Author: Advanced Python Engineer
Version: 1.0.0
Domain: cognitive_science / AI_Safety
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Enums ---

class InterventionLevel(Enum):
    """Enumeration representing the level of intervention required."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    CRITICAL = 3

@dataclass
class KnowledgeNode:
    """
    Represents a 'Real Node' in the AGI's internal knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        vector: High-dimensional vector representation of the concept (embedding).
        constraints: A dictionary defining hard logical constraints (e.g., types, ranges).
    """
    id: str
    vector: np.ndarray
    constraints: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.vector, np.ndarray):
            raise TypeError("Vector must be a numpy array.")

@dataclass
class IntentProfile:
    """
    Represents the User Intent parsed into a structured profile.
    
    Attributes:
        raw_text: The original user input.
        embedding: The semantic vector of the intent.
        required_concepts: List of logical concepts required to fulfill the intent.
    """
    raw_text: str
    embedding: np.ndarray
    required_concepts: List[str]

@dataclass
class ConsistencyReport:
    """
    The output report detailing the cognitive boundary check.
    """
    is_consistent: bool
    uncertainty_score: float
    intervention_level: InterventionLevel
    message: str
    suggested_action: str

# --- Helper Functions ---

def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec_a: First vector.
        vec_b: Second vector.
        
    Returns:
        float: Similarity score between -1 and 1.
    """
    if vec_a.shape != vec_b.shape:
        logger.error(f"Shape mismatch in vector comparison: {vec_a.shape} vs {vec_b.shape}")
        raise ValueError("Vectors must have the same dimensions")
    
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

def _validate_inputs(intent: IntentProfile, nodes: List[KnowledgeNode]) -> None:
    """
    Validates the structure and integrity of inputs before processing.
    
    Args:
        intent: The intent profile to validate.
        nodes: The list of knowledge nodes to validate.
        
    Raises:
        ValueError: If inputs are empty or malformed.
    """
    if not nodes:
        raise ValueError("Knowledge base cannot be empty.")
    if intent.embedding is None or len(intent.embedding) == 0:
        raise ValueError("Intent embedding cannot be empty.")
    
    # Check dimension consistency
    expected_dim = nodes[0].vector.shape[0]
    if intent.embedding.shape[0] != expected_dim:
        raise ValueError(f"Dimension mismatch: Intent is {intent.embedding.shape[0]}-D, Nodes are {expected_dim}-D")

# --- Core Functions ---

class UncertaintyEstimator:
    """
    A class to estimate cognitive uncertainty and detect boundaries of self-consistency.
    """
    
    def __init__(self, consistency_threshold: float = 0.75, contradiction_tolerance: int = 1):
        """
        Initialize the estimator.
        
        Args:
            consistency_threshold: The minimum semantic similarity to consider a node 'covered'.
            contradiction_tolerance: The number of logical conflicts allowed before flagging.
        """
        self.consistency_threshold = consistency_threshold
        self.contradiction_tolerance = contradiction_tolerance
        logger.info("UncertaintyEstimator initialized with threshold %.2f", consistency_threshold)

    def calculate_semantic_drift(self, intent: IntentProfile, knowledge_nodes: List[KnowledgeNode]) -> Tuple[float, Optional[KnowledgeNode]]:
        """
        Calculates the semantic distance (drift) of the intent from the nearest known node.
        
        High drift indicates the intent is approaching the 'unknown' boundary of the AGI's knowledge.
        
        Args:
            intent: The user's intent profile.
            knowledge_nodes: Available 'Real Nodes' in the system.
            
        Returns:
            Tuple[float, Optional[KnowledgeNode]]: 
                - drift_score (0.0 to 1.0, where 1.0 is maximum drift).
                - The closest node found (or None).
        """
        _validate_inputs(intent, knowledge_nodes)
        
        max_similarity = -1.0
        closest_node = None
        
        for node in knowledge_nodes:
            sim = _cosine_similarity(intent.embedding, node.vector)
            if sim > max_similarity:
                max_similarity = sim
                closest_node = node
        
        # Drift is the inverse of similarity
        drift_score = 1.0 - max_similarity
        
        logger.debug(f"Max similarity: {max_similarity:.4f}, Calculated drift: {drift_score:.4f}")
        return drift_score, closest_node

    def detect_logical_paradox(self, intent: IntentProfile, closest_node: Optional[KnowledgeNode]) -> int:
        """
        Detects internal logical contradictions based on required concepts vs node constraints.
        
        This is a heuristic simulation of logic checking. It verifies if the intent requires
        concepts that violate the constraints of the closest known node.
        
        Args:
            intent: The user's intent profile.
            closest_node: The most semantically similar node in the knowledge base.
            
        Returns:
            int: Number of detected logical conflicts (paradox count).
        """
        if closest_node is None:
            return len(intent.required_concepts) # All concepts are unsupported
            
        conflicts = 0
        node_constraints = closest_node.constraints
        
        # Example Logic: If intent asks for 'mutable' operations but node is 'immutable'
        for concept in intent.required_concepts:
            if concept in node_constraints:
                # In a real AGI, this would be a logic solver.
                # Here we simulate by checking for explicit exclusion keys
                if node_constraints.get(concept) == "forbidden":
                    logger.warning(f"Logical conflict detected: Concept '{concept}' is forbidden in Node {closest_node.id}")
                    conflicts += 1
        
        return conflicts

    def evaluate_boundary(self, intent: IntentProfile, knowledge_nodes: List[KnowledgeNode]) -> ConsistencyReport:
        """
        Main entry point. Evaluates if the intent stays within the 'Cognitive Self-Consistency' boundary.
        
        Args:
            intent: The user's intent profile.
            knowledge_nodes: The system's current knowledge graph.
            
        Returns:
            ConsistencyReport: A detailed report on the decision.
        """
        try:
            # 1. Check Semantic Coverage
            drift, closest_node = self.calculate_semantic_drift(intent, knowledge_nodes)
            
            # 2. Check Logical Consistency
            paradox_count = self.detect_logical_paradox(intent, closest_node)
            
            # 3. Determine Uncertainty Score
            # Formula: Weighted sum of semantic drift and normalized paradox count
            # Normalize paradox count (assuming > 3 paradoxes is max failure)
            normalized_paradox = min(paradox_count / 3.0, 1.0)
            
            # We weight semantic drift higher (60%) than logic errors (40%) in this configuration
            uncertainty = (0.6 * drift) + (0.4 * normalized_paradox)
            
            # 4. Decide on Human-in-the-loop
            if uncertainty > 0.9:
                level = InterventionLevel.CRITICAL
                is_consistent = False
                action = "BLOCK_EXECUTION: Request Human Architect Review."
                msg = "Intent is outside cognitive boundary. High risk of hallucination."
            elif uncertainty > 0.6 or paradox_count > self.contradiction_tolerance:
                level = InterventionLevel.MEDIUM
                is_consistent = False
                action = "TRIGGER_HITL: Ask user for clarification or constraints."
                msg = "Logical ambiguity detected near knowledge boundary."
            else:
                level = InterventionLevel.LOW if uncertainty > 0.3 else InterventionLevel.NONE
                is_consistent = True
                action = "PROCEED_WITH_MONITORING"
                msg = "Intent is within cognitive boundary."
                
            logger.info(f"Evaluation Result: {msg} (Score: {uncertainty:.2f})")
            
            return ConsistencyReport(
                is_consistent=is_consistent,
                uncertainty_score=uncertainty,
                intervention_level=level,
                message=msg,
                suggested_action=action
            )
            
        except Exception as e:
            logger.error(f"Critical error during boundary evaluation: {str(e)}")
            return ConsistencyReport(
                is_consistent=False,
                uncertainty_score=1.0,
                intervention_level=InterventionLevel.CRITICAL,
                message=f"System Error: {str(e)}",
                suggested_action="SYSTEM_HALT"
            )

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Mock Data (Simulating Embeddings)
    # Dimension of semantic space
    DIM = 128
    
    # Define Knowledge Nodes (What the AI 'knows')
    # Node 1: Python File Handling
    node_python_io = KnowledgeNode(
        id="python_io_v1",
        vector=np.random.normal(loc=0.0, scale=0.1, size=DIM), # Random vector representing the concept
        constraints={"mode": "allowed", "network": "forbidden"}
    )
    
    # Node 2: Basic Math
    node_math = KnowledgeNode(
        id="math_basic",
        vector=np.random.normal(loc=5.0, scale=0.1, size=DIM),
        constraints={"recursive": "allowed"}
    )
    
    knowledge_base = [node_python_io, node_math]
    
    # 2. Initialize Estimator
    estimator = UncertaintyEstimator(consistency_threshold=0.7)
    
    # 3. Case 1: Valid Intent (Close to python_io)
    # We simulate an intent vector close to the python_io node
    valid_intent_vector = node_python_io.vector + np.random.normal(loc=0.0, scale=0.05, size=DIM)
    user_intent_valid = IntentProfile(
        raw_text="Read a local CSV file",
        embedding=valid_intent_vector,
        required_concepts=["mode"]
    )
    
    report_valid = estimator.evaluate_boundary(user_intent_valid, knowledge_base)
    print(f"\n[Valid Intent Check]\n - Action: {report_valid.suggested_action}\n - Score: {report_valid.uncertainty_score:.3f}")
    
    # 4. Case 2: Invalid/Drifting Intent (Far from any node, contradictory constraints)
    # Vector is distant (loc=0.0 vs loc=5.0) and asks for 'network' which is forbidden in python_io
    drifting_vector = np.full(DIM, 10.0) # Very far away conceptually
    user_intent_drift = IntentProfile(
        raw_text="Access remote database to modify system kernel",
        embedding=drifting_vector,
        required_concepts=["network", "kernel"] # 'network' is forbidden in closest node
    )
    
    report_drift = estimator.evaluate_boundary(user_intent_drift, knowledge_base)
    print(f"\n[Drift Intent Check]\n - Action: {report_drift.suggested_action}\n - Score: {report_drift.uncertainty_score:.3f}")