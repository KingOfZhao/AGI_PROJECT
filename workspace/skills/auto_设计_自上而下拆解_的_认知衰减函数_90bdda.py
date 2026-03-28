"""
Module: cognitive_decay_kernel.py

Description:
    Implements a 'Top-Down Decomposition' Cognitive Decay Function for AGI systems.
    
    This module addresses the 'human lifespan limitation' bias in knowledge graphs by 
    implementing a radioactive decay-like mechanism for knowledge nodes. It ensures that 
    'zombie nodes' (long-term unvalidated information) are systematically down-weighted 
    to prevent the system from being overwhelmed by obsolete data, while preserving 
    'ancient core wisdom' through high base-importance scores.

    The core logic relies on a modified exponential decay formula that considers:
    1. Time elapsed since last validation (proof).
    2. The inherent structural importance of the node (top-down weight).
    3. The node's connectivity (activation frequency).

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, TypedDict, Union
from dataclasses import dataclass, field

# Configure robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveDecayKernel")


class NodeValidationError(ValueError):
    """Custom exception for invalid node data structures."""
    pass


@dataclass
class KnowledgeNode:
    """
    Represents a cognitive node in the AGI knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        base_importance: Inherited importance from 'top-down' decomposition (0.0 to 1.0).
                         Higher values represent core axioms/ancient wisdom.
        last_validated_ts: Datetime when the node was last validated or proved.
        decay_rate_lambda: The base decay rate (lambda). Default corresponds to a 30-day half-life.
        connections: Number of connections to other active nodes (affects decay resistance).
        content: Optional payload of the node.
    """
    id: str
    base_importance: float
    last_validated_ts: datetime
    decay_rate_lambda: float = 0.0231  # Approx 30 days half-life (ln(2)/30)
    connections: int = 0
    content: Optional[str] = None

    def __post_init__(self):
        # Data Validation
        if not 0.0 <= self.base_importance <= 1.0:
            raise NodeValidationError(f"Node {self.id}: base_importance must be between 0.0 and 1.0.")
        if self.last_validated_ts.tzinfo is None:
            # Ensure timezone awareness for consistent calculations
            self.last_validated_ts = self.last_validated_ts.replace(tzinfo=timezone.utc)


class DecayCalculator:
    """
    Engine for calculating cognitive decay scores.
    
    Implements the logic to balance the forgetting of obsolete information 
    against the retention of foundational knowledge.
    """

    @staticmethod
    def calculate_half_life(days: int) -> float:
        """
        Helper function to convert days to decay constant (lambda).
        
        Formula: lambda = ln(2) / t_half
        
        Args:
            days: The half-life period in days.
            
        Returns:
            The decay constant lambda.
        """
        if days <= 0:
            logger.warning("Half-life days must be positive. Defaulting to 1 day.")
            days = 1
        return math.log(2) / days

    def compute_survival_score(
        self, 
        node: KnowledgeNode, 
        current_time: datetime,
        connectivity_factor: float = 0.1
    ) -> float:
        """
        Core Function 1: Computes the real-time survival score of a node.
        
        The formula extends standard radioactive decay:
        Score = Base_Importance * e ^ ( -lambda * adjusted_time )
        
        Where adjusted_time accounts for connectivity (highly connected nodes decay slower).
        
        Args:
            node: The KnowledgeNode to evaluate.
            current_time: The current timestamp for comparison.
            connectivity_factor: How much connectivity dampens decay.
            
        Returns:
            A float score between 0.0 and 1.0 representing the node's validity.
        """
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Calculate time delta in days
        delta = current_time - node.last_validated_ts
        days_elapsed = delta.total_seconds() / 86400.0
        
        if days_elapsed < 0:
            logger.error(f"Node {node.id} has future validation time. Check system clock.")
            days_elapsed = 0

        # Connectivity Buff: Highly connected concepts resist decay (semantic reinforcement)
        # effective_lambda = base_lambda / (1 + log(1 + connections) * factor)
        resistance = 1 + math.log(1 + node.connections) * connectivity_factor
        effective_lambda = node.decay_rate_lambda / resistance
        
        # Calculate decay factor
        decay_factor = math.exp(-effective_lambda * days_elapsed)
        
        # Final Score combines decay factor with inherent structural importance
        # The base_importance acts as a floor or anchor.
        final_score = node.base_importance * decay_factor
        
        logger.debug(f"Node {node.id}: Elapsed={days_elapsed:.2f}d, Score={final_score:.4f}")
        return final_score

    def analyze_node_vitality(
        self, 
        nodes: List[KnowledgeNode], 
        current_time: datetime,
        prune_threshold: float = 0.05
    ) -> Dict[str, Union[List[Dict], int]]:
        """
        Core Function 2: Batch analyzes a list of nodes to identify 'zombie' nodes.
        
        This facilitates 'Garbage Collection' in the cognitive graph.
        
        Args:
            nodes: List of KnowledgeNode objects.
            current_time: Reference time.
            prune_threshold: Score below which a node is considered 'Zombie'.
            
        Returns:
            A dictionary containing 'active_nodes', 'zombie_nodes', and stats.
        """
        if not nodes:
            return {"active": [], "zombies": [], "stats": {"total": 0}}

        active_results = []
        zombie_results = []
        
        for node in nodes:
            try:
                score = self.compute_survival_score(node, current_time)
                node_data = {
                    "id": node.id,
                    "score": score,
                    "last_seen": node.last_validated_ts.isoformat()
                }
                
                if score < prune_threshold:
                    zombie_results.append(node_data)
                else:
                    active_results.append(node_data)
                    
            except Exception as e:
                logger.error(f"Failed to process node {node.id}: {e}")
                continue

        return {
            "active": active_results,
            "zombies": zombie_results,
            "stats": {
                "total": len(nodes),
                "active_count": len(active_results),
                "zombie_count": len(zombie_results)
            }
        }


# --- Usage Example and Demonstration ---

def run_simulation():
    """
    Demonstrates the usage of the Cognitive Decay Kernel.
    """
    print("--- Initializing Cognitive Decay Simulation ---")
    
    # 1. Setup Calculator
    calculator = DecayCalculator()
    now = datetime.now(timezone.utc)
    
    # 2. Create Sample Nodes
    
    # Node A: Ancient Wisdom (High Base Importance, Old)
    # Even if not validated recently, its high base importance keeps it relevant.
    node_ancient = KnowledgeNode(
        id="axiom_001",
        base_importance=0.95, # Core truth
        last_validated_ts=now - timedelta(days=365), # 1 year ago
        content="Mathematical Axiom"
    )
    
    # Node B: Recent Trending Fact (Low Base Importance, Recent)
    # High relevance now, but will decay fast if not reinforced.
    node_trend = KnowledgeNode(
        id="fact_tech_09",
        base_importance=0.4,
        last_validated_ts=now - timedelta(days=1),
        connections=50, # Highly connected (trending)
        content="Latest JS Framework Info"
    )
    
    # Node C: Zombie Node (Low Importance, Old, Isolated)
    node_zombie = KnowledgeNode(
        id="temp_note_88",
        base_importance=0.2,
        last_validated_ts=now - timedelta(days=60),
        connections=0,
        content="Temporary configuration note"
    )
    
    # 3. Perform Analysis
    nodes_to_test = [node_ancient, node_trend, node_zombie]
    
    print("\n--- Calculating Individual Scores ---")
    for node in nodes_to_test:
        score = calculator.compute_survival_score(node, now)
        status = "ALIVE" if score > 0.1 else "ZOMBIE"
        print(f"Node: {node.id:<15} | Base: {node.base_importance:.2f} | Score: {score:.4f} | Status: {status}")

    print("\n--- Batch Analysis (Pruning Threshold: 0.1) ---")
    report = calculator.analyze_node_vitality(nodes_to_test, now, prune_threshold=0.1)
    print(f"Active Nodes: {report['stats']['active_count']}")
    print(f"Zombie Nodes: {report['stats']['zombie_count']}")
    print(f"Zombie IDs: {[z['id'] for z in report['zombies']]}")

if __name__ == "__main__":
    run_simulation()