"""
Module: evolutionary_knowledge_pruning_engine
Description: Implements an evolution-driven dynamic knowledge graph pruning engine.
             This engine manages knowledge nodes by simulating ecological metabolic
             pressures, distinguishing between 'bacteria-type' (simple, high-frequency)
             and 'apex-predator-type' (complex, high-value) nodes.

Author: Advanced Python Engineer for AGI System
Version: 1.0.0
License: MIT
"""

import logging
import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Classification of knowledge nodes based on ecological metaphors."""
    BACTERIA = "bacteria"  # Simple, high-frequency, low metabolic cost
    PREDATOR = "predator"  # Complex, high-value, high metabolic cost
    NEUTRAL = "neutral"    # Default or transitioning type


@dataclass(order=True)
class KnowledgeNode:
    """
    Represents a node in the knowledge graph with metabolic properties.
    
    Attributes:
        id (str): Unique identifier.
        complexity (float): Computational cost to maintain (Metabolic Rate).
        utility (float): Accumulated value from solving problems (Energy Intake).
        last_accessed (float): Timestamp of last successful usage.
        fitness_score (float): Calculated survival fitness (utility / complexity).
        type (NodeType): Ecological classification.
        is_archived (bool): Whether the node has been pruned/archived.
    """
    id: str
    complexity: float
    utility: float = 0.0
    last_accessed: float = field(default_factory=time.time)
    fitness_score: float = 0.0
    type: NodeType = NodeType.NEUTRAL
    is_archived: bool = False

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, KnowledgeNode):
            return self.id == other.id
        return False


class EvolutionaryPruningEngine:
    """
    Engine that applies evolutionary pressure to prune a knowledge graph.
    
    It simulates an ecosystem where nodes compete for computational resources.
    Nodes that consume high resources (complexity) but provide low value (utility)
    are subjected to metabolic stress and eventual archiving.
    """

    def __init__(self, carrying_capacity: int = 1000, stress_threshold: float = 0.05):
        """
        Initialize the engine.
        
        Args:
            carrying_capacity (int): Maximum number of active nodes before severe pressure applies.
            stress_threshold (float): The minimum fitness score required to survive a pruning cycle.
        """
        if carrying_capacity <= 0:
            raise ValueError("Carrying capacity must be positive.")
        
        self.graph: Dict[str, KnowledgeNode] = {}
        self.carrying_capacity = carrying_capacity
        self.stress_threshold = stress_threshold
        self._archived_ids: Set[str] = set()
        
        logger.info(
            f"Engine initialized with capacity {carrying_capacity}, "
            f"stress threshold {stress_threshold}"
        )

    def add_node(self, node_id: str, complexity: float, initial_utility: float = 0.0) -> None:
        """
        Add a new knowledge node to the ecosystem.
        
        Args:
            node_id: Unique ID for the node.
            complexity: Metabolic cost (computational expense).
            initial_utility: Starting utility value.
        
        Raises:
            ValueError: If inputs are invalid or node ID exists.
        """
        if not node_id or node_id in self.graph:
            raise ValueError(f"Invalid or duplicate node ID: {node_id}")
        
        if complexity <= 0:
            logger.warning(f"Complexity for {node_id} should ideally be > 0.")
            complexity = 0.1  # Prevent division by zero later

        new_node = KnowledgeNode(
            id=node_id,
            complexity=complexity,
            utility=initial_utility
        )
        self.graph[node_id] = new_node
        logger.debug(f"Node {node_id} added with complexity {complexity}.")

    def report_usage(self, node_id: str, information_gain: float) -> None:
        """
        Report that a node was used to solve a problem (Energy Intake).
        
        This increases the node's utility and updates its access time.
        
        Args:
            node_id: The ID of the used node.
            information_gain: The 'energy' acquired from this success (0.0 to 1.0).
        """
        if node_id not in self.graph:
            logger.error(f"Node {node_id} not found.")
            return
        
        if information_gain < 0:
            logger.warning("Information gain cannot be negative. Defaulting to 0.")
            information_gain = 0

        node = self.graph[node_id]
        node.utility += information_gain
        node.last_accessed = time.time()
        
        # Update fitness dynamically
        self._calculate_fitness(node)
        self._classify_node(node)
        
        logger.info(f"Node {node_id} used. Gain: {information_gain}. Total Utility: {node.utility}")

    def _calculate_fitness(self, node: KnowledgeNode) -> None:
        """
        [Internal] Calculate the evolutionary fitness of a node.
        Fitness = Utility / Complexity (Metabolic Efficiency).
        """
        # Add a small epsilon to complexity to avoid division by zero
        epsilon = 1e-6
        node.fitness_score = node.utility / (node.complexity + epsilon)

    def _classify_node(self, node: KnowledgeNode) -> None:
        """
        [Internal] Classify the node based on complexity and utility patterns.
        """
        # Simple heuristic for demonstration
        if node.complexity < 2.0 and node.fitness_score > 1.0:
            node.type = NodeType.BACTERIA
        elif node.complexity > 8.0 and node.utility > 10.0:
            node.type = NodeType.PREDATOR
        else:
            node.type = NodeType.NEUTRAL

    def apply_metabolic_pressure(self) -> Dict[str, Any]:
        """
        Core Cycle: Apply natural selection logic to the graph.
        
        1. Calculate carrying capacity pressure.
        2. Identify low-fitness nodes.
        3. Archive nodes that fail to meet metabolic requirements.
        
        Returns:
            A report dictionary containing 'survivors', 'archived', and 'stats'.
        """
        logger.info("--- Applying Metabolic Pressure ---")
        current_population = len(self.graph)
        
        if current_population == 0:
            return {"survivors": [], "archived": [], "stats": "Empty ecosystem"}

        # Determine how many need to be pruned if over capacity
        surplus = max(0, current_population - self.carrying_capacity)
        
        # Create a heap of nodes sorted by fitness (ascending) to find weakest
        # Heap elements: (fitness, last_accessed, node_id)
        candidates = [
            (n.fitness_score, n.last_accessed, n.id) 
            for n in self.graph.values()
        ]
        heapq.heapify(candidates)
        
        archived_count = 0
        archived_ids = []
        
        # 1. Prune explicit surplus (Starvation due to overpopulation)
        for _ in range(surplus):
            if not candidates: break
            fitness, _, nid = heapq.heappop(candidates)
            self._archive_node(nid)
            archived_ids.append(nid)
            archived_count += 1

        # 2. Prune based on metabolic stress (Fitness threshold)
        # Check remaining candidates
        remaining_candidates = []
        while candidates:
            fitness, _, nid = heapq.heappop(candidates)
            if fitness < self.stress_threshold:
                # Check if it's a 'Predator' with potential (protecting high-value complex nodes)
                node = self.graph.get(nid)
                if node and node.type == NodeType.PREDATOR and node.utility > 50.0:
                    # Apex predator exemption: High utility saves them despite low immediate fitness
                    remaining_candidates.append((fitness, _, nid))
                else:
                    self._archive_node(nid)
                    archived_ids.append(nid)
                    archived_count += 1
            else:
                remaining_candidates.append((fitness, _, nid))

        # Log results
        active_nodes = [n.id for n in self.graph.values() if not n.is_archived]
        report = {
            "survivors": active_nodes,
            "archived": archived_ids,
            "stats": {
                "initial_pop": current_population,
                "final_pop": len(active_nodes),
                "archived_count": archived_count
            }
        }
        
        logger.info(f"Cycle complete. Pruned {archived_count} nodes.")
        return report

    def _archive_node(self, node_id: str) -> None:
        """
        Helper: Mark a node as archived and remove it from active computation paths.
        """
        if node_id in self.graph:
            node = self.graph[node_id]
            node.is_archived = True
            self._archived_ids.add(node_id)
            logger.warning(f"NODE ARCHIVED: {node_id} (Fitness: {node.fitness_score:.4f})")

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Initialize the engine
    engine = EvolutionaryPruningEngine(carrying_capacity=5, stress_threshold=0.2)
    
    # Add nodes (Simulating different knowledge types)
    # Type 1: Simple, frequently used (Bacteria)
    engine.add_node("math_add", complexity=1.0)
    engine.add_node("text_tokenize", complexity=1.5)
    
    # Type 2: Complex, rarely used, low value (Dead weight)
    engine.add_node("legacy_cobol_parser", complexity=20.0)
    
    # Type 3: Complex, rarely used, but HIGH value when used (Apex Predator)
    engine.add_node("quantum_optimizer", complexity=50.0)
    
    # Type 4: Medium complexity, zero value (Failing)
    engine.add_node("deprecated_api_bridge", complexity=5.0)

    # Simulate Environment Interactions (Time passing)
    # Bacteria thrives
    for _ in range(10):
        engine.report_usage("math_add", 0.5)
        engine.report_usage("text_tokenize", 0.4)
    
    # Apex Predator solves a huge problem once
    engine.report_usage("quantum_optimizer", 100.0)
    
    # Legacy and Deprecated get nothing (Information Gain = 0)
    
    # Apply Evolutionary Pressure
    print("\n[Status Before Pruning]")
    for node in engine.graph.values():
        print(f"ID: {node.id:<20} | Fit: {node.fitness_score:.2f} | Type: {node.type.value}")

    report = engine.apply_metabolic_pressure()
    
    print("\n[Pruning Report]")
    print(f"Archived Nodes: {report['archived']}")
    print(f"Survivors: {report['survivors']}")