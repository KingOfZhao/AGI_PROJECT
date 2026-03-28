"""
Module: cognitive_radioactive_decay.py

This module implements the 'Cognitive Radioactive Decay' algorithm for AGI systems.
It simulates the decay of node activity over time, where each node's activity
decays exponentially unless re-verified (re-activated) to reset its half-life.

Core Concepts:
- Node Activity: Represents the relevance or validity of a knowledge node.
- Decay: Activity decreases over time following an exponential decay model.
- Re-verification: Resetting the node's half-life to maintain its activity.

Dependencies:
- numpy: For numerical operations (optional, fallback to math if unavailable).
- logging: For logging events and errors.

Usage Example:
    >>> from cognitive_radioactive_decay import CognitiveDecayEngine
    >>> engine = CognitiveDecayEngine()
    >>> engine.add_node("concept_1", initial_activity=1.0, half_life=10.0)
    >>> engine.update_activity("concept_1", elapsed_time=5.0)
    >>> print(engine.get_activity("concept_1"))
    >>> engine.reverify_node("concept_1")  # Resets half-life

Input/Output:
- Input: Node identifiers (str), initial activity (float), half-life (float)
- Output: Current activity (float), decay status (bool)
"""

import logging
import math
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DecayNode:
    """Represents a node in the cognitive decay system."""
    node_id: str
    initial_activity: float
    half_life: float  # in arbitrary time units
    last_verified_time: float = 0.0  # timestamp of last verification
    current_activity: float = 1.0  # normalized activity (0.0 to 1.0)

    def __post_init__(self):
        """Validate node data after initialization."""
        if self.initial_activity <= 0:
            raise ValueError("Initial activity must be positive")
        if self.half_life <= 0:
            raise ValueError("Half-life must be positive")
        if not 0 <= self.current_activity <= 1.0:
            raise ValueError("Current activity must be between 0 and 1")


class CognitiveDecayEngine:
    """
    Manages the cognitive radioactive decay of knowledge nodes.
    
    Attributes:
        nodes (Dict[str, DecayNode]): Dictionary of active nodes
        time_scale (float): Scaling factor for time units
    """
    
    def __init__(self, time_scale: float = 1.0):
        """
        Initialize the decay engine.
        
        Args:
            time_scale: Multiplier for time units (default: 1.0)
        """
        self.nodes: Dict[str, DecayNode] = {}
        self.time_scale = time_scale
        logger.info("Initialized CognitiveDecayEngine with time_scale=%.2f", time_scale)

    def add_node(
        self,
        node_id: str,
        initial_activity: float,
        half_life: float,
        current_time: float = 0.0
    ) -> None:
        """
        Add a new node to the decay system.
        
        Args:
            node_id: Unique identifier for the node
            initial_activity: Initial activity value (must be > 0)
            half_life: Time for activity to reduce by half (must be > 0)
            current_time: Current time (default: 0.0)
            
        Raises:
            ValueError: If input parameters are invalid
            KeyError: If node already exists
        """
        if node_id in self.nodes:
            raise KeyError(f"Node {node_id} already exists")
            
        try:
            node = DecayNode(
                node_id=node_id,
                initial_activity=initial_activity,
                half_life=half_life,
                last_verified_time=current_time,
                current_activity=1.0  # Normalized initial activity
            )
            self.nodes[node_id] = node
            logger.debug("Added node %s with half_life=%.2f", node_id, half_life)
        except ValueError as e:
            logger.error("Failed to add node %s: %s", node_id, str(e))
            raise

    def update_activity(self, node_id: str, elapsed_time: float) -> float:
        """
        Update a node's activity based on elapsed time.
        
        Args:
            node_id: Identifier of the node to update
            elapsed_time: Time elapsed since last verification
            
        Returns:
            Current activity level (0.0 to 1.0)
            
        Raises:
            KeyError: If node doesn't exist
            ValueError: If elapsed_time is negative
        """
        if elapsed_time < 0:
            raise ValueError("Elapsed time cannot be negative")
            
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
            
        node = self.nodes[node_id]
        decay_factor = math.exp(-math.log(2) * elapsed_time / (node.half_life * self.time_scale))
        node.current_activity = max(0.0, min(1.0, decay_factor))
        
        logger.debug(
            "Updated node %s: activity=%.4f (elapsed_time=%.2f)",
            node_id, node.current_activity, elapsed_time
        )
        return node.current_activity

    def reverify_node(self, node_id: str, current_time: float) -> None:
        """
        Re-verify a node to reset its decay timer.
        
        Args:
            node_id: Identifier of the node to re-verify
            current_time: Current time for verification
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
            
        node = self.nodes[node_id]
        node.last_verified_time = current_time
        node.current_activity = 1.0  # Reset to full activity
        
        logger.info("Re-verified node %s at time %.2f", node_id, current_time)

    def get_activity(self, node_id: str) -> float:
        """
        Get the current activity level of a node.
        
        Args:
            node_id: Identifier of the node
            
        Returns:
            Current activity level (0.0 to 1.0)
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
        return self.nodes[node_id].current_activity

    def prune_inactive_nodes(self, threshold: float = 0.1) -> int:
        """
        Remove nodes with activity below threshold.
        
        Args:
            threshold: Activity threshold (default: 0.1)
            
        Returns:
            Number of nodes pruned
        """
        to_prune = [
            node_id for node_id, node in self.nodes.items()
            if node.current_activity < threshold
        ]
        
        for node_id in to_prune:
            del self.nodes[node_id]
            logger.debug("Pruned inactive node %s", node_id)
            
        return len(to_prune)


def calculate_decay_rate(half_life: float) -> float:
    """
    Calculate the decay constant for a given half-life.
    
    Args:
        half_life: Time for quantity to reduce by half
        
    Returns:
        Decay constant (lambda)
        
    Raises:
        ValueError: If half_life is not positive
    """
    if half_life <= 0:
        raise ValueError("Half-life must be positive")
    return math.log(2) / half_life


def demo_decay_engine():
    """Demonstrate the cognitive decay engine functionality."""
    engine = CognitiveDecayEngine(time_scale=1.0)
    
    # Add nodes with different half-lives
    engine.add_node("short_term", initial_activity=1.0, half_life=5.0)
    engine.add_node("long_term", initial_activity=1.0, half_life=20.0)
    
    # Simulate time passing
    for t in range(1, 31, 5):
        short_activity = engine.update_activity("short_term", elapsed_time=t)
        long_activity = engine.update_activity("long_term", elapsed_time=t)
        print(f"Time {t:2d}: Short={short_activity:.4f}, Long={long_activity:.4f}")
        
        # Re-verify short-term node every 10 time units
        if t % 10 == 0:
            engine.reverify_node("short_term", current_time=t)
            print(f"Re-verified short_term at time {t}")
    
    # Prune inactive nodes
    pruned = engine.prune_inactive_nodes(threshold=0.2)
    print(f"Pruned {pruned} inactive nodes")


if __name__ == "__main__":
    demo_decay_engine()