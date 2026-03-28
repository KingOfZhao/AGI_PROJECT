"""
Meta-Cognitive Layer for Handling Human Cognitive Chaos

This module implements a probabilistic state machine designed to parse ambiguous,
dynamic, and metaphorical human intent into structured Hierarchical Task Networks (HTN).
It features real-time intent drift detection and confidence-weighted state updates.

Key Features:
- Probabilistic state representation
- Intent drift detection via cosine similarity
- Interactive clarification loops
- Hierarchical Task Network generation

Data Formats:
- Input: Raw text string or pre-tokenized concept list
- Output: JSON-serializable dict containing HTN and confidence metrics
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MetaCognitiveChaosHandler")


class IntentState(Enum):
    """Enumeration of possible meta-cognitive states."""
    GROUNDED = auto()      # Intent is clear and stable
    DRIFTING = auto()      # Intent is shifting or ambiguous
    CONFLICT = auto()      # Multiple contradictory intents detected
    UNKNOWN = auto()       # Insufficient data to determine intent


@dataclass
class CognitiveState:
    """
    Represents the current probabilistic state of the system's understanding.
    
    Attributes:
        vector: A list of floats representing the semantic state.
        confidence: Current confidence level (0.0 to 1.0).
        history: List of past intent labels for drift detection.
        entropy: Measure of disorder in the current state.
    """
    vector: List[float] = field(default_factory=lambda: [0.0] * 8)
    confidence: float = 0.0
    history: List[str] = field(default_factory=list)
    entropy: float = 1.0

    def update_vector(self, new_vector: List[float]) -> None:
        """Updates the state vector and recalculates entropy."""
        if len(new_vector) != len(self.vector):
            raise ValueError("Vector dimension mismatch")
        self.vector = new_vector
        self.entropy = self._calculate_entropy(new_vector)

    @staticmethod
    def _calculate_entropy(vec: List[float]) -> float:
        """Calculates Shannon entropy of the vector (normalized)."""
        total = sum(abs(v) for v in vec) + 1e-9
        probs = [abs(v) / total for v in vec]
        return -sum(p * math.log(p + 1e-9) for p in probs if p > 0)


class ProbabilisticStateMachine:
    """
    Core engine for managing the meta-cognitive layer.
    Handles intent mapping, drift detection, and task decomposition.
    """

    def __init__(self, sensitivity_threshold: float = 0.75):
        """
        Initialize the state machine.
        
        Args:
            sensitivity_threshold: Threshold for intent drift detection.
        """
        self.sensitivity_threshold = sensitivity_threshold
        self.current_state = CognitiveState()
        self._vector_dim = 8
        logger.info("ProbabilisticStateMachine initialized with threshold %.2f", sensitivity_threshold)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Helper function to calculate cosine similarity between two vectors.
        
        Args:
            vec_a: First vector.
            vec_b: Second vector.
            
        Returns:
            Similarity score between -1.0 and 1.0.
        """
        if len(vec_a) != len(vec_b):
            logger.error("Vector dimension mismatch in similarity check")
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a)) + 1e-9
        norm_b = math.sqrt(sum(b * b for b in vec_b)) + 1e-9
        return dot_product / (norm_a * norm_b)

    def map_intent_to_vector(self, raw_input: str) -> List[float]:
        """
        Maps raw linguistic input to a probabilistic state vector.
        (Simulation of embedding processing)
        
        Args:
            raw_input: The raw user input string.
            
        Returns:
            A normalized probabilistic vector.
        """
        # In a real AGI system, this would interface with an LLM or embedding model.
        # Here we simulate vector generation based on string characteristics.
        seed = sum(ord(c) for c in raw_input)
        random.seed(seed)
        
        vec = [random.gauss(0, 1) for _ in range(self._vector_dim)]
        magnitude = math.sqrt(sum(x**2 for x in vec)) + 1e-9
        normalized = [x / magnitude for x in vec]
        
        logger.debug("Mapped input '%s' to vector (sample): %.4f...", raw_input[:10], normalized[0])
        return normalized

    def detect_intent_drift(self, new_vector: List[float]) -> Tuple[bool, float]:
        """
        Detects if the new intent vector significantly deviates from the current state.
        
        Args:
            new_vector: The incoming intent vector.
            
        Returns:
            Tuple of (is_drifting: bool, similarity_score: float)
        """
        similarity = self._cosine_similarity(self.current_state.vector, new_vector)
        is_drifting = similarity < self.sensitivity_threshold
        
        if is_drifting:
            logger.warning("Intent drift detected! Similarity: %.4f", similarity)
        
        return is_drifting, similarity

    def update_state(self, new_vector: List[float], label: str, is_drifting: bool) -> None:
        """
        Updates the cognitive state using a confidence-weighted interface.
        
        Args:
            new_vector: The incoming vector.
            label: The semantic label of the new intent.
            is_drifting: Whether drift was detected.
        """
        # Weighted average update (Kalman-like simplified)
        alpha = 0.3 if is_drifting else 0.7  # Faster adoption if grounded, slower if drifting
        
        updated_vec = [
            (alpha * new_val) + ((1 - alpha) * old_val)
            for new_val, old_val in zip(new_vector, self.current_state.vector)
        ]
        
        self.current_state.update_vector(updated_vec)
        self.current_state.history.append(label)
        
        # Adjust confidence
        if is_drifting:
            self.current_state.confidence = max(0.0, self.current_state.confidence - 0.1)
        else:
            self.current_state.confidence = min(1.0, self.current_state.confidence + 0.05)

    def generate_htn(self, intent_label: str) -> Dict:
        """
        Generates a Hierarchical Task Network (HTN) from the current state.
        
        Args:
            intent_label: The high-level label of the intent.
            
        Returns:
            A dictionary representing the HTN.
        """
        htn = {
            "root_task": intent_label,
            "subtasks": [],
            "status": "PENDING",
            "metadata": {
                "confidence": self.current_state.confidence,
                "entropy": self.current_state.entropy
            }
        }
        
        # Simulate decomposition based on entropy
        if self.current_state.entropy > 0.7:
            htn["subtasks"] = [
                {"task": "Clarify ambiguity", "priority": 1},
                {"task": "Resolve conflicting context", "priority": 2}
            ]
            htn["status"] = "CLARIFICATION_REQUIRED"
        else:
            htn["subtasks"] = [
                {"task": f"Execute {intent_label}", "priority": 1},
                {"task": "Verify results", "priority": 2}
            ]
            htn["status"] = "READY_FOR_EXECUTION"
            
        return htn

    def process_cycle(self, user_input: str) -> Dict:
        """
        Full processing cycle: Input -> Vector -> Drift Check -> State Update -> HTN.
        
        Args:
            user_input: The raw input string.
            
        Returns:
            The generated HTN and current state metadata.
        """
        if not user_input or not isinstance(user_input, str):
            raise ValueError("Input must be a non-empty string")

        logger.info(f"Processing cycle started for input: '{user_input}'")
        
        # 1. Map to vector space
        vector = self.map_intent_to_vector(user_input)
        
        # 2. Detect Drift
        drifting, score = self.detect_intent_drift(vector)
        
        # 3. Update State
        # Extract a dummy label for simulation
        label = f"Intent_{user_input.split()[0] if user_input else 'Empty'}"
        self.update_state(vector, label, drifting)
        
        # 4. Generate HTN
        htn = self.generate_htn(label)
        
        return {
            "htn": htn,
            "state": {
                "confidence": self.current_state.confidence,
                "last_similarity": score,
                "entropy": self.current_state.entropy
            }
        }


def run_interactive_calibration(psm: ProbabilisticStateMachine, inputs: List[str]) -> None:
    """
    Helper function to simulate an interactive calibration loop.
    Processes a list of inputs and logs the system's stabilization.
    
    Args:
        psm: An instance of the ProbabilisticStateMachine.
        inputs: A list of strings simulating a conversation history.
    """
    print("\n--- Starting Interactive Calibration Loop ---")
    for idx, text in enumerate(inputs):
        print(f"\n[Turn {idx+1}] User says: '{text}'")
        try:
            result = psm.process_cycle(text)
            status = result['htn']['status']
            conf = result['state']['confidence']
            print(f" -> System Status: {status} | Confidence: {conf:.2f}")
            
            if status == "CLARIFICATION_REQUIRED":
                print(" -> [System]: Could you please clarify your specific goal?")
            else:
                print(" -> [System]: Understood. Generating execution plan.")
                
        except Exception as e:
            logger.error(f"Error processing turn {idx+1}: {e}")
            print(" -> [System]: I encountered a processing error.")

    print("\n--- Calibration Loop Complete ---")


if __name__ == "__main__":
    # Example Usage
    
    # 1. Initialize the system
    meta_cog_system = ProbabilisticStateMachine(sensitivity_threshold=0.65)
    
    # 2. Simulate a chaotic conversation (Intent Drift -> Clarification -> Convergence)
    conversation_history = [
        "I want to build a website",             # Initial Intent
        "Actually, maybe a mobile app",          # Drift
        "Something with dark mode",              # Ambiguity (Entropy increase)
        "For iOS specifically",                  # Narrowing down
        "Using Swift",                           # Convergence
        "Using Swift"                            # Reinforcement
    ]
    
    # 3. Run the calibration
    run_interactive_calibration(meta_cog_system, conversation_history)
    
    # 4. Display final state
    final_state = meta_cog_system.current_state
    print(f"\nFinal System Entropy: {final_state.entropy:.4f}")
    print(f"Final Confidence: {final_state.confidence:.4f}")