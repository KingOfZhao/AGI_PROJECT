"""
Module: genetic_knowledge_archiving.py

This module implements a Genetic Algorithm-Driven Knowledge Elimination Mechanism.
It is designed to manage the lifecycle of industrial knowledge nodes, combating
'knowledge entropy' (accumulation of outdated/redundant information) by simulating
biological evolution processes such as metabolism tracking, fitness evaluation,
apoptosis (archiving), and recombination (mutation).

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import json
import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("knowledge_evolution.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class KnowledgeStatus(Enum):
    """Enumeration of possible states for a Knowledge Node."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"  # Apoptosis state
    MUTATED = "MUTATED"    # New state after recombination


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the industrial knowledge base.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge data (e.g., rule, fact, procedure).
        metabolism_rate: Frequency of usage (0.0 to 1.0).
        fitness_score: Success rate in practical application (0.0 to 1.0).
        last_accessed: Timestamp of the last retrieval.
        status: Current lifecycle status.
        generation: Evolution generation counter.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metabolism_rate: float = 0.1
    fitness_score: float = 0.5  # Neutral start
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    generation: int = 1

    def to_dict(self) -> Dict:
        """Helper to convert node to dictionary for serialization."""
        return {
            **asdict(self),
            "status": self.status.value
        }


class GeneticKnowledgeSystem:
    """
    Core system managing the genetic evolution of the knowledge base.
    
    Implements selection, archiving (apoptosis), and recombination logic
    based on biological metaphors.
    """

    def __init__(self, 
                 metabolism_threshold: float = 0.05, 
                 fitness_threshold: float = 0.2,
                 archive_file: str = "knowledge_archive.json"):
        """
        Initialize the genetic knowledge system.
        
        Args:
            metabolism_threshold: Minimum usage rate to survive.
            fitness_threshold: Minimum success rate to survive.
            archive_file: Path to store archived/eliminated nodes.
        """
        self.metabolism_threshold = metabolism_threshold
        self.fitness_threshold = fitness_threshold
        self.archive_file = archive_file
        self.knowledge_base: Dict[str, KnowledgeNode] = {}
        
        # Boundary checks for configuration
        if not (0.0 <= metabolism_threshold <= 1.0):
            raise ValueError("Metabolism threshold must be between 0.0 and 1.0")
        if not (0.0 <= fitness_threshold <= 1.0):
            raise ValueError("Fitness threshold must be between 0.0 and 1.0")

        logger.info("GeneticKnowledgeSystem initialized with thresholds: Metabolism=%s, Fitness=%s",
                    self.metabolism_threshold, self.fitness_threshold)

    def add_knowledge(self, content: str) -> KnowledgeNode:
        """Inject a new knowledge node into the ecosystem."""
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string.")
            
        node = KnowledgeNode(content=content)
        self.knowledge_base[node.id] = node
        logger.debug("New knowledge node created: %s", node.id)
        return node

    def simulate_interaction(self, node_id: str, success: bool) -> None:
        """
        Simulate external interaction (usage) updating node vitals.
        
        Args:
            node_id: ID of the node accessed.
            success: Whether the knowledge proved useful/correct in this instance.
        """
        if node_id not in self.knowledge_base:
            logger.warning("Attempted to access non-existent node: %s", node_id)
            return

        node = self.knowledge_base[node_id]
        node.last_accessed = datetime.now().timestamp()
        
        # Update metabolic rate (exponential moving average)
        current_metabolism = node.metabolism_rate
        node.metabolism_rate = (current_metabolism * 0.8) + 0.2 # Boost on access
        
        # Update fitness score
        # Simple incremental update: (old * n + new) / (n + 1) approximated
        current_fitness = node.fitness_score
        val = 1.0 if success else 0.0
        node.fitness_score = (current_fitness * 0.9) + (val * 0.1)
        
        logger.info("Node %s updated. Fitness: %.2f, Metabolism: %.2f", 
                    node_id, node.fitness_score, node.metabolism_rate)

    def _apply_apoptosis(self) -> List[str]:
        """
        Internal mechanism: Identify and archive 'dead' knowledge nodes.
        
        Checks if metabolism (usage) or fitness (accuracy) falls below thresholds.
        This represents the 'Survival of the Fittest' filtering.
        
        Returns:
            List of IDs of archived nodes.
        """
        archived_ids = []
        nodes_to_remove = []

        for node_id, node in self.knowledge_base.items():
            if node.status != KnowledgeStatus.ACTIVE:
                continue

            # Check survival conditions
            is_zombie = node.metabolism_rate < self.metabolism_threshold
            is_harmful = node.fitness_score < self.fitness_threshold

            if is_zombie or is_harmful:
                reason = "Low Metabolism" if is_zombie else "Low Fitness"
                logger.warning("APOPTOSIS triggered for node %s. Reason: %s", node_id, reason)
                
                # Archive the node
                self._archive_node(node, reason)
                nodes_to_remove.append(node_id)
                archived_ids.append(node_id)

        # Remove from active population
        for nid in nodes_to_remove:
            del self.knowledge_base[nid]
            
        return archived_ids

    def _archive_node(self, node: KnowledgeNode, reason: str) -> None:
        """Write eliminated node to the history file."""
        node.status = KnowledgeStatus.ARCHIVED
        record = {
            "timestamp": datetime.now().isoformat(),
            "node_data": node.to_dict(),
            "elimination_reason": reason
        }
        try:
            with open(self.archive_file, 'a') as f:
                f.write(json.dumps(record) + "\n")
        except IOError as e:
            logger.error("Failed to write to archive: %s", e)

    def _recombine_knowledge(self) -> KnowledgeNode:
        """
        Internal mechanism: Crossover between high-fitness nodes to create new knowledge.
        
        Selects two distinct high-performing nodes and merges their content
        to create a 'mutated' offspring node.
        
        Returns:
            The newly created KnowledgeNode.
        """
        # Select parents (Roulette wheel selection simplified: Top fitness)
        active_nodes = [n for n in self.knowledge_base.values() if n.status == KnowledgeStatus.ACTIVE]
        if len(active_nodes) < 2:
            logger.info("Recombination skipped: Insufficient population.")
            return None

        # Sort by fitness and pick top 2 distinct parents
        sorted_nodes = sorted(active_nodes, key=lambda x: x.fitness_score, reverse=True)
        parent_a = sorted_nodes[0]
        parent_b = sorted_nodes[1]

        # Genetic Crossover: Merge content hashes or substrings
        # Here we simulate merging logic by combining hashes and substrings
        new_content_hash = hashlib.md5(
            (parent_a.content + parent_b.content).encode()
        ).hexdigest()[:8]
        
        new_content = f"Derived_Logic({parent_a.id[:4]}+{parent_b.id[:4]}):{new_content_hash}"
        
        offspring = KnowledgeNode(
            content=new_content,
            metabolism_rate=0.5, # Fresh metabolism
            fitness_score=(parent_a.fitness_score + parent_b.fitness_score) / 2, # Inherit average fitness
            generation=max(parent_a.generation, parent_b.generation) + 1,
            status=KnowledgeStatus.MUTATED
        )
        
        self.knowledge_base[offspring.id] = offspring
        logger.info("RECOMBINATION successful: New node %s created from parents %s and %s",
                    offspring.id, parent_a.id, parent_b.id)
        return offspring

    def run_evolution_cycle(self) -> Dict:
        """
        Main entry point to run one generation of the evolution process.
        
        1. Applies Apoptosis (removes weak nodes).
        2. Applies Recombination (generates new nodes from strong ones).
        
        Returns:
            A report of the evolution cycle results.
        """
        logger.info("--- Starting Evolution Cycle ---")
        
        population_before = len(self.knowledge_base)
        
        # Phase 1: Natural Selection
        archived = self._apply_apoptosis()
        
        # Phase 2: Mutation/Evolution
        offspring = self._recombine_knowledge()
        
        population_after = len(self.knowledge_base)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "population_before": population_before,
            "nodes_archived": len(archived),
            "new_offspring_id": offspring.id if offspring else None,
            "population_after": population_after,
            "current_avg_fitness": self._calculate_average_fitness()
        }
        
        logger.info("--- Cycle Complete. Population: %d -> %d ---", population_before, population_after)
        return report

    def _calculate_average_fitness(self) -> float:
        """Helper: Calculate mean fitness of active population."""
        active = [n.fitness_score for n in self.knowledge_base.values() if n.status == KnowledgeStatus.ACTIVE]
        if not active:
            return 0.0
        return sum(active) / len(active)


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize System
    gks = GeneticKnowledgeSystem(metabolism_threshold=0.1, fitness_threshold=0.3)

    # 2. Seed Initial Knowledge
    node1 = gks.add_knowledge("Rule: Temperature > 100 implies Overheat.")
    node2 = gks.add_knowledge("Rule: Pressure < 50 implies Leak.")
    node3 = gks.add_knowledge("Rule: Vibration > 10g implies Imbalance.")

    # 3. Simulate Time & Usage (Decay)
    # Node 3 is never accessed, so metabolism will decay/be low
    
    # Simulate Node 1 being successful and frequently used
    for _ in range(5):
        gks.simulate_interaction(node1.id, success=True)
    
    # Simulate Node 2 being used but often failing (false positives)
    for _ in range(5):
        gks.simulate_interaction(node2.id, success=False)

    # 4. Run Evolution Cycle
    print("\nRunning Evolution Cycle 1...")
    report = gks.run_evolution_cycle()
    print(json.dumps(report, indent=2))

    # Expected Outcome:
    # - Node 3 dies (Low Metabolism)
    # - Node 2 dies (Low Fitness)
    # - Node 1 survives
    # - A new node is created from Node 1 and Node 2 (before node 2 is removed or from remaining pool)