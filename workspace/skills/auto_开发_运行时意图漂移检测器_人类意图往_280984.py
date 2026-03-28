"""
Module: runtime_intent_drift_detector.py
Description: Detects real-time drift in user intent during AGI code execution.
             Distinguishes between noise and genuine intent changes to decide
             between rollback and incremental patching.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentDriftDetector")

class DriftAction(Enum):
    """Enumeration of possible actions in response to intent drift."""
    CONTINUE = "continue"
    ROLLBACK = "rollback"
    INCREMENTAL_PATCH = "incremental_patch"
    REQUEST_CLARIFICATION = "request_clarification"

@dataclass
class IntentState:
    """Represents the state of a user intent at a specific point in time."""
    vector: np.ndarray
    timestamp: datetime = field(default_factory=datetime.now)
    raw_text: str = ""
    confidence: float = 1.0

    def __post_init__(self):
        """Validate data after initialization."""
        if not isinstance(self.vector, np.ndarray):
            raise TypeError("Intent vector must be a numpy array.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0.")

class IntentDriftDetector:
    """
    Monitors user feedback and intent vectors to detect significant drift
    during an AGI task execution.
    
    Attributes:
        history (List[IntentState]): History of intent states.
        noise_threshold (float): Cosine similarity threshold below which 
                                 change is considered significant.
        stabilization_window (int): Number of past states to check for stabilization.
    """

    def __init__(
        self, 
        initial_intent: np.ndarray, 
        noise_threshold: float = 0.15, 
        stabilization_window: int = 3
    ):
        """
        Initialize the detector with the starting intent.
        
        Args:
            initial_intent (np.ndarray): The initial embedding vector of the user intent.
            noise_threshold (float): Threshold for cosine distance to trigger drift.
            stabilization_window (int): Window size to smooth out noise.
        """
        if not isinstance(initial_intent, np.ndarray):
            raise TypeError("Initial intent must be a numpy array.")
            
        self.history: List[IntentState] = [IntentState(vector=initial_intent)]
        self.noise_threshold = noise_threshold
        self.stabilization_window = stabilization_window
        logger.info("IntentDriftDetector initialized with threshold %.2f", noise_threshold)

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            v1: First vector.
            v2: Second vector.
            
        Returns:
            float: Cosine similarity score between -1 and 1.
        """
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def _is_noise(self, current_state: IntentState, previous_state: IntentState) -> bool:
        """
        Determine if the detected change is merely noise or a temporary fluctuation.
        Checks against the history window.
        
        Args:
            current_state: The latest detected state.
            previous_state: The immediately preceding state.
            
        Returns:
            bool: True if the change is considered noise, False otherwise.
        """
        # Check confidence levels
        if current_state.confidence < 0.6:
            logger.debug("Flagged as noise due to low confidence: %.2f", current_state.confidence)
            return True
            
        # Check rapid fluctuation against history
        if len(self.history) >= self.stabilization_window:
            recent_vectors = [s.vector for s in self.history[-self.stabilization_window:]]
            avg_similarity = np.mean([
                self._cosine_similarity(current_state.vector, v) for v in recent_vectors
            ])
            
            # If the current vector is somewhat similar to the average of recent history,
            # it might just be oscillation, not a permanent drift.
            if avg_similarity > (1.0 - self.noise_threshold / 2):
                logger.debug("Flagged as noise due to similarity with recent history window.")
                return True
                
        return False

    def update_state(self, new_intent_vector: np.ndarray, feedback_text: str = "") -> DriftAction:
        """
        Update the system with a new intent vector derived from user feedback or monitoring.
        
        Args:
            new_intent_vector (np.ndarray): The new embedding vector representing current context.
            feedback_text (str): Optional raw text feedback for logging context.
            
        Returns:
            DriftAction: The recommended action for the AGI system.
        """
        if not isinstance(new_intent_vector, np.ndarray):
            logger.error("Invalid input type for new_intent_vector.")
            raise TypeError("new_intent_vector must be a numpy array.")
            
        # Create new state
        new_state = IntentState(
            vector=new_intent_vector, 
            raw_text=feedback_text,
            confidence=0.9  # Placeholder for actual confidence logic
        )
        
        last_state = self.history[-1]
        similarity = self._cosine_similarity(new_state.vector, last_state.vector)
        distance = 1.0 - similarity
        
        logger.info(f"Intent Update: Similarity={similarity:.4f}, Distance={distance:.4f}")
        
        # Determine Action
        if distance < self.noise_threshold:
            logger.info("Change within noise threshold. Action: CONTINUE")
            self.history.append(new_state)
            return DriftAction.CONTINUE
            
        # Check if it's just noise
        if self._is_noise(new_state, last_state):
            logger.info("Detected fluctuation classified as noise. Action: CONTINUE")
            # We still append to history to track the noise pattern
            self.history.append(new_state)
            return DriftAction.CONTINUE
            
        # Significant Drift Detected
        logger.warning("Significant Intent Drift Detected!")
        self.history.append(new_state)
        
        # Decide between Rollback and Patch based on history length and magnitude
        if len(self.history) > 2 and distance > 0.5:
            logger.warning("Drift magnitude high. Recommending ROLLBACK.")
            return DriftAction.ROLLBACK
        else:
            logger.info("Drift magnitude moderate. Recommending INCREMENTAL_PATCH.")
            return DriftAction.INCREMENTAL_PATCH

def generate_mock_embedding(dim: int = 128) -> np.ndarray:
    """
    Helper function to generate random embedding vectors for demonstration.
    
    Args:
        dim (int): Dimension of the vector.
        
    Returns:
        np.ndarray: Normalized random vector.
    """
    vec = np.random.rand(dim)
    return vec / np.linalg.norm(vec)

def run_demo():
    """
    Example usage of the IntentDriftDetector.
    """
    print("--- Starting Runtime Intent Drift Detector Demo ---")
    
    # 1. Initialize
    initial_vec = generate_mock_embedding()
    detector = IntentDriftDetector(initial_intent=initial_vec)
    
    # 2. Simulate minor update (Noise)
    # Add small random noise to the vector
    noisy_vec = initial_vec + (np.random.rand(128) * 0.05)
    noisy_vec = noisy_vec / np.linalg.norm(noisy_vec)
    
    action = detector.update_state(noisy_vec, "User moved mouse slightly")
    print(f"Action taken: {action.value}")

    # 3. Simulate significant drift (Change of Mind)
    # Generate a completely different vector
    drifted_vec = generate_mock_embedding() 
    
    action = detector.update_state(drifted_vec, "User said: 'Actually, change the color to blue'")
    print(f"Action taken: {action.value}")

    # 4. Simulate massive drift (Contradiction)
    # Invert the vector (extreme change)
    inverted_vec = initial_vec * -1
    
    action = detector.update_state(inverted_vec, "User said: 'Cancel that, do the opposite'")
    print(f"Action taken: {action.value}")

if __name__ == "__main__":
    run_demo()