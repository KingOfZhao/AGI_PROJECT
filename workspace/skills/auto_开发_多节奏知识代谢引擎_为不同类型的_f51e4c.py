"""
Module: multi_rhythm_knowledge_metabolism_engine

This module implements the 'Multi-Rhythm Knowledge Metabolism Engine'.
It simulates a cognitive architecture where different types of knowledge
nodes follow different decay rhythms (metabolic rates), akin to musical
time signatures.

Knowledge Types:
- Sixteenth Note (API Parameters): High volatility, fast decay.
- Quarter Note (Best Practices): Medium volatility, moderate decay.
- Whole Note (Design Patterns): Low volatility, slow decay.

The engine acts as a conductor, orchestrating when specific knowledge
should be reviewed, consolidated, or pruned, preventing structural
amnesia caused by uniform forgetting policies.

Author: AGI System
Version: 1.0.0
"""

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MetabolismEngine")


class RhythmType(Enum):
    """Enumeration of supported knowledge rhythms (metabolic rates)."""
    SIXTEENTH = "sixteenth"  # Fast decay (e.g., volatile API params)
    QUARTER = "quarter"      # Medium decay (e.g., libraries, syntax)
    WHOLE = "whole"          # Slow decay (e.g., design patterns, core logic)


@dataclass
class MetabolicConfig:
    """Configuration for a specific rhythm type."""
    decay_rate: float       # Lambda for exponential decay
    review_threshold: float # Importance score below which review is triggered
    window_size: int        # Time window in seconds for a 'beat'


# Configuration mapping for rhythms
RHYTHM_CONFIGS: Dict[RhythmType, MetabolicConfig] = {
    RhythmType.SIXTEENTH: MetabolicConfig(
        decay_rate=0.1, review_threshold=0.5, window_size=60
    ),
    RhythmType.QUARTER: MetabolicConfig(
        decay_rate=0.05, review_threshold=0.6, window_size=3600
    ),
    RhythmType.WHOLE: MetabolicConfig(
        decay_rate=0.01, review_threshold=0.7, window_size=86400
    ),
}


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the graph.
    
    Attributes:
        id: Unique identifier.
        content: The actual knowledge data.
        rhythm: The assigned metabolic rhythm.
        base_importance: Intrinsic importance (0.0 to 1.0).
        last_accessed: Timestamp of last access or update.
        current_strength: Calculated strength based on decay.
    """
    id: str
    content: Any
    rhythm: RhythmType
    base_importance: float = 1.0
    last_accessed: float = field(default_factory=time.time)
    current_strength: float = 1.0

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Validate node attributes."""
        if not self.id:
            raise ValueError("Node ID cannot be empty.")
        if not 0.0 <= self.base_importance <= 1.0:
            raise ValueError("Base importance must be between 0.0 and 1.0.")


class MultiRhythmMetabolismEngine:
    """
    Engine that manages knowledge lifecycle based on rhythmic decay patterns.
    """

    def __init__(self):
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.conductor_time: float = time.time()
        logger.info("Multi-Rhythm Metabolism Engine initialized.")

    def _calculate_decay(self, node: KnowledgeNode, current_time: float) -> float:
        """
        Helper: Calculate current strength of a node using exponential decay.
        Formula: S(t) = Importance * e^(-lambda * t)
        """
        config = RHYTHM_CONFIGS[node.rhythm]
        elapsed_time = current_time - node.last_accessed
        
        # Prevent division by zero or negative time anomalies
        if elapsed_time < 0:
            elapsed_time = 0
            
        decay_factor = math.exp(-config.decay_rate * elapsed_time)
        return node.base_importance * decay_factor

    def add_knowledge(self, node: KnowledgeNode) -> bool:
        """
        Add a new knowledge node to the engine.
        
        Args:
            node: The KnowledgeNode object to add.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if node.id in self.knowledge_graph:
                logger.warning(f"Node {node.id} already exists. Updating instead.")
                self.update_knowledge(node.id)
                return True
            
            self.knowledge_graph[node.id] = node
            logger.info(f"Added knowledge node: {node.id} with rhythm {node.rhythm.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to add knowledge node: {e}")
            return False

    def update_knowledge(self, node_id: str) -> bool:
        """
        'Reinforce' a knowledge node (reset its decay timer).
        """
        if node_id not in self.knowledge_graph:
            logger.error(f"Node {node_id} not found for update.")
            return False
        
        node = self.knowledge_graph[node_id]
        node.last_accessed = time.time()
        node.current_strength = 1.0 # Reset strength on access
        logger.debug(f"Node {node_id} reinforced.")
        return True

    def conduct_cycle(self) -> Dict[str, List[str]]:
        """
        The main 'Conductor' loop. 
        1. Updates decay for all nodes.
        2. Identifies nodes needing review (weak beats).
        3. Identifies candidates for cross-domain collision (ensemble).
        
        Returns:
            A report containing 'review_candidates' and 'ensemble_candidates'.
        """
        current_time = time.time()
        self.conductor_time = current_time
        report = {
            "review_candidates": [],
            "ensemble_candidates": [],
            "pruned": []
        }

        logger.info("--- Starting Conducting Cycle ---")
        
        nodes_to_prune = []

        for node_id, node in self.knowledge_graph.items():
            # Update strength
            strength = self._calculate_decay(node, current_time)
            node.current_strength = strength
            config = RHYTHM_CONFIGS[node.rhythm]

            # Check for Review (Downbeat)
            if strength < config.review_threshold:
                report["review_candidates"].append(node_id)
                logger.info(f"WEAK BEAT detected: Node {node_id} needs review. Strength: {strength:.4f}")

            # Check for Ensemble (Cross-domain potential) - High strength Whole notes
            if node.rhythm == RhythmType.WHOLE and strength > 0.9:
                report["ensemble_candidates"].append(node_id)

            # Check for Pruning (Forgetting) - Critical failure
            if strength < 0.1:
                nodes_to_prune.append(node_id)

        # Execute Pruning
        for nid in nodes_to_prune:
            del self.knowledge_graph[nid]
            report["pruned"].append(nid)
            logger.warning(f"PRUNED knowledge node: {nid} (Strength decayed past threshold)")

        # Trigger Ensemble Logic if we have candidates
        if len(report["ensemble_candidates"]) >= 2:
            self._perform_ensemble(report["ensemble_candidates"])

        return report

    def _perform_ensemble(self, node_ids: List[str]) -> None:
        """
        Helper: Simulate a 'knowledge collision' or synthesis between strong nodes.
        """
        logger.info(f"ENSEMBLE ACTION: Synthesizing knowledge between {node_ids}")
        # In a real AGI system, this would generate new insights.
        # Here we just log the event.

    def get_node_state(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current state of a specific node."""
        if node_id not in self.knowledge_graph:
            return None
        
        node = self.knowledge_graph[node_id]
        return {
            "id": node.id,
            "rhythm": node.rhythm.value,
            "strength": node.current_strength,
            "last_accessed": node.last_accessed
        }

# Usage Example
if __name__ == "__main__":
    # Initialize Engine
    engine = MultiRhythmMetabolismEngine()

    # 1. Create diverse knowledge nodes
    # Volatile API Key (Fast rhythm)
    api_node = KnowledgeNode(
        id="api_key_123",
        content="AWS_SECRET_KEY",
        rhythm=RhythmType.SIXTEENTH,
        base_importance=0.9
    )

    # Stable Design Pattern (Slow rhythm)
    pattern_node = KnowledgeNode(
        id="singleton_pattern",
        content="Ensure a class only has one instance.",
        rhythm=RhythmType.WHOLE,
        base_importance=1.0
    )

    # 2. Add to engine
    engine.add_knowledge(api_node)
    engine.add_knowledge(pattern_node)

    # 3. Simulate time passing (manipulate timestamps for demo)
    # Simulate 5 seconds passing for API node (significant for fast rhythm)
    # Note: In real usage, time.time() handles this naturally
    engine.knowledge_graph["api_key_123"].last_accessed = time.time() - 100 
    
    # 4. Run a cycle
    print("\nRunning Metabolism Cycle...")
    cycle_report = engine.conduct_cycle()
    
    print("\nCycle Report:")
    print(f"Nodes needing review: {cycle_report['review_candidates']}")
    print(f"Nodes pruned: {cycle_report['pruned']}")
    
    # Check state
    state = engine.get_node_state("api_key_123")
    print(f"\nAPI Node State: {state}")