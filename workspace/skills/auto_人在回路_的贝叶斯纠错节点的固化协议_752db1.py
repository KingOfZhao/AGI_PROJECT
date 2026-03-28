"""
Module: anti_node_solidification_protocol
Description: Implements the "Human-in-the-Loop Bayesian Error Correction Node Solidification Protocol".
             This module provides a standardized API to handle human feedback (counterexamples)
             by generating "Anti-Nodes" to suppress specific error patterns in an AGI system
             without causing catastrophic forgetting.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class CognitiveNode:
    """
    Represents a cognitive node in the AGI system's knowledge graph.
    
    Attributes:
        node_id (str): Unique identifier for the node.
        vector (np.ndarray): The embedding vector representing the knowledge/concept.
        label (str): The classification or output label associated with this node.
        is_frozen (bool): If True, the node is protected from standard gradient updates (safeguards against forgetting).
        creation_time (str): ISO format timestamp of creation.
    """
    node_id: str
    vector: np.ndarray
    label: str
    is_frozen: bool = False
    creation_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Helper to serialize node data excluding the heavy vector."""
        return {
            "node_id": self.node_id,
            "label": self.label,
            "is_frozen": self.is_frozen,
            "creation_time": self.creation_time
        }

@dataclass
class FeedbackPayload:
    """
    Input format for the human feedback API.
    
    Attributes:
        input_vector (List[float]): The input data that caused the error.
        predicted_label (str): The AI's incorrect prediction.
        correct_label (str): The ground truth provided by the human.
        context_metadata (Dict): Additional context (e.g., user ID, session ID).
    """
    input_vector: List[float]
    predicted_label: str
    correct_label: str
    context_metadata: Dict = field(default_factory=dict)

# --- Core Classes ---

class AntiNodeManager:
    """
    Manages the lifecycle of Cognitive Nodes and Anti-Nodes.
    Implements the logic to process negative feedback and validate system performance.
    """

    def __init__(self, vector_dim: int = 128, similarity_threshold: float = 0.85):
        """
        Initialize the manager.
        
        Args:
            vector_dim (int): Dimensionality of the embedding space.
            similarity_threshold (float): Cosine similarity threshold to trigger error correction.
        """
        self.vector_dim = vector_dim
        self.similarity_threshold = similarity_threshold
        self.knowledge_base: Dict[str, CognitiveNode] = {}
        logger.info(f"AntiNodeManager initialized with dimension {vector_dim}")

    def _generate_node_id(self, vector: np.ndarray, label: str, prefix: str = "node") -> str:
        """
        Helper function to generate a deterministic unique ID based on content hash.
        
        Args:
            vector (np.ndarray): The node vector.
            label (str): The node label.
            prefix (str): Prefix for the ID (e.g., 'anti').
            
        Returns:
            str: A unique hash ID.
        """
        # Create a byte representation of the vector and label
        vec_bytes = vector.tobytes()
        label_bytes = label.encode('utf-8')
        hash_digest = hashlib.sha256(vec_bytes + label_bytes).hexdigest()[:12]
        return f"{prefix}_{hash_digest}"

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Helper function to calculate cosine similarity between two vectors.
        
        Args:
            vec_a (np.ndarray): Vector A.
            vec_b (np.ndarray): Vector B.
            
        Returns:
            float: Similarity score between -1 and 1.
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_b == 0 or norm_a == 0:
            return 0.0
        return np.dot(vec_a, vec_b) / (norm_a * norm_b)

    def process_negative_feedback(self, feedback: FeedbackPayload) -> CognitiveNode:
        """
        Core Function 1: Processes human feedback to generate an Anti-Node.
        
        This function takes a counterexample provided by a human. Instead of simply
        adjusting weights (which might affect global knowledge), it instantiates a
        specific "Anti-Node" that suppresses the activation of the incorrect concept
        for this specific input cluster.
        
        Args:
            feedback (FeedbackPayload): The feedback data structure.
            
        Returns:
            CognitiveNode: The newly created Anti-Node.
            
        Raises:
            ValueError: If input vector dimensions do not match system configuration.
        """
        # 1. Data Validation
        if len(feedback.input_vector) != self.vector_dim:
            msg = f"Vector dimension mismatch. Expected {self.vector_dim}, got {len(feedback.input_vector)}"
            logger.error(msg)
            raise ValueError(msg)

        input_vec = np.array(feedback.input_vector, dtype=np.float32)

        # 2. Check for Catastrophic Forgetting risks
        # We check if the input is too similar to an existing, FROZEN "Core" concept.
        # If so, we log a warning rather than blindly creating a contradictory node.
        for node in self.knowledge_base.values():
            if node.is_frozen:
                sim = self._cosine_similarity(input_vec, node.vector)
                if sim > 0.95 and node.label != feedback.predicted_label:
                    logger.warning(
                        f"Potential conflict detected. Input highly similar to frozen node {node.node_id}. "
                        "Proceeding with caution."
                    )

        # 3. Generate Anti-Node
        # An Anti-Node represents a specific "boundary" case where the predicted_label
        # is explicitly forbidden. The vector is stored to serve as a repeller.
        anti_node_id = self._generate_node_id(input_vec, feedback.predicted_label, prefix="anti")
        
        anti_node = CognitiveNode(
            node_id=anti_node_id,
            vector=input_vec,
            label=f"NOT_{feedback.predicted_label}", # Semantic marker
            is_frozen=True # Anti-nodes are固化 (solidified) immediately
        )

        # 4. Storage
        self.knowledge_base[anti_node_id] = anti_node
        logger.info(
            f"Anti-Node created and solidified. ID: {anti_node_id}. "
            f"Suppressed Label: {feedback.predicted_label}. "
            f"Correct Label Context: {feedback.correct_label}"
        )
        
        return anti_node

    def infer_with_rejection(self, input_vector: List[float]) -> Tuple[str, float, bool]:
        """
        Core Function 2: Performs inference using the Anti-Node logic.
        
        This simulates the AGI system's inference mechanism. It checks the input
        against existing Anti-Nodes. If the input is semantically close to an Anti-Node,
        the system rejects the original prediction or lowers confidence significantly.
        
        Args:
            input_vector (List[float]): The input data to classify.
            
        Returns:
            Tuple[str, float, bool]: 
                - predicted_label (str): The final system output.
                - confidence (float): The adjusted confidence score.
                - rejected (bool): True if an Anti-Node blocked a prediction.
        """
        if len(input_vector) != self.vector_dim:
            raise ValueError("Input vector dimension mismatch.")

        input_vec = np.array(input_vector, dtype=np.float32)
        
        # Step A: Standard Inference Simulation
        # In a real system, this would query a neural network. 
        # Here we simulate by finding the closest non-anti node.
        best_label = "Unknown"
        best_score = 0.0
        
        # Step B: Anti-Node Interference Check
        rejection_triggered = False
        for node in self.knowledge_base.values():
            sim = self._cosine_similarity(input_vec, node.vector)
            
            if node.node_id.startswith("anti_"):
                # If input matches an Anti-Node, we trigger suppression logic
                if sim > self.similarity_threshold:
                    logger.warning(f"Rejection triggered by Anti-Node {node.node_id} (Sim: {sim:.4f})")
                    rejection_triggered = True
                    # We don't return immediately, we might just lower confidence
                    # or force a re-ranking.
            else:
                # Standard retrieval logic
                if sim > best_score:
                    best_score = sim
                    best_label = node.label

        # Step C: Final Decision Logic
        if rejection_triggered:
            # Simple heuristic: If rejected, confidence drops to near zero for this path
            # or we return a specific "Review Needed" token.
            final_label = best_label # We keep the label to show *what* was almost predicted
            final_confidence = 0.05  # Drastically reduced
            logger.info(f"Inference overridden for input due to Anti-Node proximity.")
        else:
            final_label = best_label
            final_confidence = best_score

        return final_label, final_confidence, rejection_triggered

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup
    DIM = 64
    manager = AntiNodeManager(vector_dim=DIM, similarity_threshold=0.8)
    
    # 2. Simulate existing knowledge (Positive Nodes)
    # Let's imagine a node representing the concept of "Cat"
    cat_vec = np.random.rand(DIM).astype(np.float32) # In reality, this would be an embedding
    cat_node = CognitiveNode(
        node_id="node_cat_001", 
        vector=cat_vec, 
        label="Cat", 
        is_frozen=True
    )
    manager.knowledge_base[cat_node.node_id] = cat_node
    
    print(f"System initialized with concept: {cat_node.label}")

    # 3. Simulate a specific input that the AI incorrectly classifies as "Cat"
    # This is an "Edge Case" (e.g., a very small dog that looks like a cat)
    edge_case_input = cat_vec + (np.random.rand(DIM) * 0.1) # Slightly noisy vector
    edge_case_input = edge_case_input.astype(np.float32).tolist()

    # 3a. Initial Inference (Before Feedback)
    label, conf, rejected = manager.infer_with_rejection(edge_case_input)
    print(f"\nInitial Inference: {label} (Conf: {conf:.2f}, Rejected: {rejected})")
    # Expected: "Cat" with high confidence

    # 4. Human Feedback: "This is NOT a Cat, it is a Dog"
    feedback = FeedbackPayload(
        input_vector=edge_case_input,
        predicted_label="Cat", # What the AI thought
        correct_label="Dog"    # The truth
    )

    print("\nProcessing Human Feedback (Generating Anti-Node)...")
    anti_node = manager.process_negative_feedback(feedback)

    # 5. Post-Feedback Inference (Verification)
    # We feed the exact same input back into the system
    label_new, conf_new, rejected_new = manager.infer_with_rejection(edge_case_input)
    
    print(f"\nPost-Feedback Inference: {label_new} (Conf: {conf_new:.2f}, Rejected: {rejected_new})")
    
    # Verification of "Catastrophic Forgetting" prevention
    # The original "Cat" node should still exist and be healthy
    print(f"\nOriginal Knowledge Check: {manager.knowledge_base.get('node_cat_001').label} is still preserved.")