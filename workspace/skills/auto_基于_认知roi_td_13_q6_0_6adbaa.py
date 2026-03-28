"""
Module: auto_evolutionary_cognitive_roi.py

Description:
    AGI Skill module for system-level self-optimization.
    
    This module implements a lifecycle management system based on 'Cognitive ROI' (Return on Investment),
    an 'Induction Engine' for variation, and a 'Second Evolution Space' for simulation.
    
    It enables a process akin to natural selection:
    1. Variation: Strategies are mutated in a virtual space.
    2. Selection: Strategies are evaluated based on ROI in reality.
    3. Growth: High-value nodes are solidified.
    4. Apoptosis: Low-value nodes are discarded.

Key Components:
    - CognitiveNode: Represents a unit of strategy or logic.
    - EvolutionaryOrchestrator: Manages the lifecycle and evolution loop.

Author: AGI System
Version: 1.0.0
"""

import logging
import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EvolutionaryCognitiveROI")


class NodeState(Enum):
    """Enumeration of possible states for a Cognitive Node."""
    DORMANT = 0
    ACTIVE = 1
    EVOLVING = 2
    DEAD = 3


@dataclass
class CognitiveNode:
    """
    Represents a strategy node in the cognitive network.
    
    Attributes:
        id: Unique identifier for the node.
        strategy_vector: A list of floats representing the strategy parameters.
        roi_score: The calculated Return on Investment (performance metric).
        generation: The evolution generation this node belongs to.
        state: Current state of the node.
    """
    id: str
    strategy_vector: List[float]
    roi_score: float = 0.0
    generation: int = 0
    state: NodeState = NodeState.DORMANT

    def __post_init__(self):
        if not self.strategy_vector:
            raise ValueError("Strategy vector cannot be empty")

    def calculate_signature(self) -> str:
        """Generates a unique hash signature for the strategy vector."""
        data = "".join(map(str, self.strategy_vector))
        return hashlib.md5(data.encode()).hexdigest()


class EvolutionaryOrchestrator:
    """
    Manages the evolutionary lifecycle of cognitive nodes.
    
    Implements the core logic for the 'Second Evolution Space' and 'Cognitive ROI' validation.
    """

    def __init__(self, roi_threshold: float = 0.75, mutation_rate: float = 0.1):
        """
        Initialize the orchestrator.
        
        Args:
            roi_threshold: The minimum ROI score required for a node to survive (Selection).
            mutation_rate: The intensity of random changes during variation.
        """
        self.roi_threshold = roi_threshold
        self.mutation_rate = mutation_rate
        self.population: List[CognitiveNode] = []
        self.history: Dict[str, float] = {}  # Track historical ROI for induction
        logger.info("EvolutionaryOrchestrator initialized with ROI threshold: %.2f", roi_threshold)

    def _validate_vector(self, vector: List[float]) -> bool:
        """Helper function to validate strategy vector boundaries."""
        if not isinstance(vector, list):
            return False
        if not all(-10.0 <= x <= 10.0 for x in vector):
            logger.warning("Vector values out of bounds [-10, 10]")
            return False
        return True

    def spawn_node(self, strategy_vector: List[float]) -> Optional[CognitiveNode]:
        """
        Creates a new cognitive node and adds it to the population.
        
        Args:
            strategy_vector: The initial strategy parameters.
            
        Returns:
            The created CognitiveNode or None if validation fails.
        """
        if not self._validate_vector(strategy_vector):
            logger.error("Invalid strategy vector provided for spawning.")
            return None

        node_id = f"node_{int(time.time() * 1000)}_{random.randint(0, 999)}"
        new_node = CognitiveNode(
            id=node_id,
            strategy_vector=strategy_vector,
            state=NodeState.ACTIVE
        )
        self.population.append(new_node)
        logger.debug("Spawned new node: %s", node_id)
        return new_node

    def _induction_engine(self, base_vector: List[float]) -> List[float]:
        """
        Secondary Evolution Space logic.
        Simulates variations (mutations) of a strategy to explore the solution space.
        
        Args:
            base_vector: The original strategy to mutate.
            
        Returns:
            A new, mutated strategy vector.
        """
        new_vector = base_vector.copy()
        for i in range(len(new_vector)):
            if random.random() < self.mutation_rate:
                # Apply gaussian noise as mutation
                mutation = random.gauss(0, 0.5)
                new_vector[i] += mutation
                # Clamp values
                new_vector[i] = max(min(new_vector[i], 10.0), -10.0)
        return new_vector

    def evaluate_roi(self, node: CognitiveNode, environment_feedback: float) -> float:
        """
        Calculates the Cognitive ROI based on environment feedback.
        
        Args:
            node: The node to evaluate.
            environment_feedback: A score representing real-world performance (0.0 to 1.0).
            
        Returns:
            The calculated ROI score.
        """
        if not (0.0 <= environment_feedback <= 1.0):
            raise ValueError("Environment feedback must be between 0.0 and 1.0")

        # Complex ROI logic could go here (e.g., cost vs benefit)
        # Simple implementation: weighted feedback
        complexity_cost = sum(abs(x) for x in node.strategy_vector) * 0.01
        roi = environment_feedback - complexity_cost
        
        node.roi_score = roi
        self.history[node.id] = roi
        logger.info("Node %s evaluated. ROI: %.4f", node.id, roi)
        return roi

    def run_evolution_cycle(self, feedback_map: Dict[str, float]) -> Dict[str, Any]:
        """
        Executes one full cycle of the evolutionary process:
        1. Evaluation (ROI Calculation)
        2. Selection (Apoptosis)
        3. Variation (Induction/Growth)
        
        Args:
            feedback_map: Dictionary mapping Node IDs to their real-world feedback scores.
            
        Returns:
            A summary report of the cycle.
        """
        start_time = time.time()
        culled_count = 0
        evolved_count = 0

        # 1. Evaluate and Select
        # We iterate over a copy of the list to allow modification
        for node in self.population[:]:
            feedback = feedback_map.get(node.id, 0.0)
            self.evaluate_roi(node, feedback)

            if node.roi_score < self.roi_threshold:
                # Apoptosis (Cell Death)
                node.state = NodeState.DEAD
                self.population.remove(node)
                culled_count += 1
                logger.info("Node %s culled due to low ROI (%.4f).", node.id, node.roi_score)
            else:
                # Growth & Variation
                # The node survives and spawns a mutated variant
                new_vector = self._induction_engine(node.strategy_vector)
                self.spawn_node(new_vector)
                evolved_count += 1

        duration = time.time() - start_time
        report = {
            "status": "cycle_complete",
            "population_size": len(self.population),
            "nodes_culled": culled_count,
            "nodes_evolved": evolved_count,
            "processing_time": duration
        }
        
        logger.info("Evolution cycle complete. Pop: %d, Culled: %d, Evolved: %d",
                    len(self.population), culled_count, evolved_count)
        return report


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize the Orchestrator
    system = EvolutionaryOrchestrator(roi_threshold=0.5, mutation_rate=0.2)
    
    # 2. Initial Population
    # Strategy vectors are abstract representations of behavior
    initial_strategies = [
        [1.0, 0.5, -0.2],
        [0.0, 0.0, 0.0],
        [5.0, -2.0, 1.5]
    ]
    
    for strat in initial_strategies:
        system.spawn_node(strat)

    # 3. Simulate an Environment Cycle
    # Mock feedback from the environment (Real-world validation)
    # Let's assume the first strategy performs well, the second poorly.
    mock_feedback = {
        system.population[0].id: 0.9,  # High ROI
        system.population[1].id: 0.1,  # Low ROI (will be culled)
        system.population[2].id: 0.6   # Medium ROI
    }

    # 4. Run Evolution
    report = system.run_evolution_cycle(mock_feedback)
    
    # 5. Output Results
    print("\n--- System Report ---")
    print(f"Population Size: {report['population_size']}")
    print(f"Nodes Culled: {report['nodes_culled']}")
    
    print("\n--- Surviving Nodes ---")
    for node in system.population:
        print(f"ID: {node.id[:15]}... | ROI: {node.roi_score:.4f} | State: {node.state.name}")