"""
Module: knowledge_half_life_decay.py

This module implements a dynamic weight adjustment system for AGI knowledge nodes.
It addresses the issue of static knowledge bases by introducing a 'Half-Life' decay
mechanism. Each node's weight decreases over time but can be reinforced by usage
(positive feedback) or penalized by falsification (negative feedback).

Designed for Time Series Analysis within Data Science contexts.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the AGI system.
    
    Attributes:
        id (str): Unique identifier for the knowledge node.
        content (str): The actual knowledge content (e.g., "Floppy disks store 1.44MB").
        initial_weight (float): The starting weight/importortance of the node (0.0 to 1.0).
        current_weight (float): The dynamic weight adjusted over time.
        half_life_seconds (float): Time in seconds for the weight to reduce by half without reinforcement.
        created_at (datetime): Timestamp of creation.
        last_accessed (datetime): Timestamp of the last access/update.
        access_count (int): Number of times the node was accessed/reinforced.
        falsification_count (int): Number of times the node was proven wrong.
    """
    id: str
    content: str
    initial_weight: float = 1.0
    current_weight: float = field(init=False)
    half_life_seconds: float = 2592000.0  # Default: 30 days
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    falsification_count: int = 0

    def __post_init__(self):
        """Initialize current_weight and validate inputs."""
        if not 0.0 <= self.initial_weight <= 1.0:
            raise ValueError(f"Initial weight must be between 0 and 1. Got {self.initial_weight}")
        if self.half_life_seconds <= 0:
            raise ValueError("Half-life must be positive.")
        
        self.current_weight = self.initial_weight
        logger.debug(f"Node created: {self.id} with weight {self.current_weight}")

# --- Core Functions ---

def calculate_decay_factor(
    time_delta_seconds: float, 
    half_life_seconds: float
) -> float:
    """
    Calculate the exponential decay factor based on elapsed time.
    
    Formula: factor = 2^(-t / T) where t is time elapsed and T is half-life.

    Args:
        time_delta_seconds (float): The time elapsed in seconds.
        half_life_seconds (float): The half-life period in seconds.

    Returns:
        float: The decay multiplier (0.0 to 1.0).
    """
    if time_delta_seconds < 0:
        logger.warning("Negative time delta detected, returning 1.0 factor.")
        return 1.0
    
    try:
        factor = math.exp(-0.693 * (time_delta_seconds / half_life_seconds))
        return max(0.0, min(1.0, factor))
    except (OverflowError, ZeroDivisionError) as e:
        logger.error(f"Math error in decay calculation: {e}")
        return 0.0

def update_node_weight(
    node: KnowledgeNode, 
    current_time: datetime, 
    reinforcement_factor: float = 0.0,
    falsification_penalty: float = 0.0
) -> float:
    """
    Updates the weight of a specific knowledge node based on time decay, 
    reinforcement (usage), and falsification (negative feedback).

    Logic:
    1. Calculate time since last access.
    2. Apply exponential decay.
    3. Apply reinforcement (increases weight towards 1.0).
    4. Apply falsification (decreases weight towards 0.0).
    5. Update metadata (last_accessed, counts).

    Args:
        node (KnowledgeNode): The knowledge node to update.
        current_time (datetime): The current timestamp.
        reinforcement_factor (float): Positive boost per access (0.0 to 1.0).
        falsification_penalty (float): Negative penalty per falsification (0.0 to 1.0).

    Returns:
        float: The updated weight of the node.
        
    Raises:
        ValueError: If input factors are out of bounds.
    """
    # Input Validation
    if not 0.0 <= reinforcement_factor <= 1.0:
        raise ValueError("Reinforcement factor must be between 0 and 1.")
    if not 0.0 <= falsification_penalty <= 1.0:
        raise ValueError("Falsification penalty must be between 0 and 1.")
        
    time_delta = (current_time - node.last_accessed).total_seconds()
    
    # 1. Calculate Time Decay
    decay_mult = calculate_decay_factor(time_delta, node.half_life_seconds)
    
    # 2. Apply Decay
    # Weight moves towards 0 based on decay
    decayed_weight = node.current_weight * decay_mult
    
    # 3. Apply Reinforcement (Logic: moves weight towards 1.0)
    if reinforcement_factor > 0:
        node.access_count += 1
        # Linear reinforcement towards 1.0
        boost = (1.0 - decayed_weight) * reinforcement_factor
        decayed_weight += boost
        logger.info(f"Node {node.id} reinforced. Boost: {boost:.4f}")

    # 4. Apply Falsification (Logic: moves weight towards 0.0)
    if falsification_penalty > 0:
        node.falsification_count += 1
        # Exponential penalty based on falsification count to ensure "bad" knowledge dies fast
        penalty_mult = math.pow(1.0 - falsification_penalty, node.falsification_count)
        decayed_weight *= penalty_mult
        logger.warning(f"Node {node.id} falsified. New weight factor: {penalty_mult:.4f}")

    # 5. Final Bounds Check
    node.current_weight = max(0.0001, min(1.0, decayed_weight)) # Floor at 0.0001 to keep it "alive" but negligible
    node.last_accessed = current_time
    
    return node.current_weight

# --- Helper Functions ---

def filter_active_nodes(
    nodes: List[KnowledgeNode], 
    threshold: float = 0.1
) -> List[KnowledgeNode]:
    """
    Filters a list of nodes, returning only those with weight above a threshold.
    This is used to retrieve knowledge relevant for decision making, ignoring
    'sunken' knowledge like obsolete tech skills.

    Args:
        nodes (List[KnowledgeNode]): List of knowledge nodes.
        threshold (float): Minimum weight to be considered active.

    Returns:
        List[KnowledgeNode]: Sorted list of active nodes (descending weight).
    """
    if not isinstance(nodes, list):
        logger.error("Input must be a list of KnowledgeNodes.")
        return []
        
    active = [n for n in nodes if n.current_weight >= threshold]
    
    # Sort by weight (descending) so AGI prioritizes strongest knowledge
    active.sort(key=lambda x: x.current_weight, reverse=True)
    
    logger.info(f"Filtered {len(nodes)} nodes to {len(active)} active nodes.")
    return active

# --- Main Execution / Example ---

if __name__ == "__main__":
    # Simulation of the Skill usage
    
    print("--- Knowledge Half-Life Decay Simulation ---")
    
    # 1. Create Nodes
    node_floppy = KnowledgeNode(
        id="storage_001", 
        content="Use floppy disks for data backup", 
        initial_weight=0.9,
        half_life_seconds=3600 * 24 * 365 # 1 year half life (ages slowly if not touched)
    )
    
    node_cloud = KnowledgeNode(
        id="storage_002", 
        content="Use AWS S3 for data backup", 
        initial_weight=0.5,
        half_life_seconds=3600 * 24 * 30 # 1 month half life (needs frequent use)
    )
    
    knowledge_base = [node_floppy, node_cloud]
    
    # 2. Simulate Time Passing (5 years)
    future_time = datetime.utcnow() + timedelta(days=5*365)
    
    print(f"\nSimulating 5 years passing...")
    
    # 3. Update Weights
    # Floppy disk is NOT accessed (reinforcement=0)
    update_node_weight(node_floppy, future_time, reinforcement_factor=0.0)
    
    # Cloud storage IS accessed frequently (reinforcement=0.2)
    update_node_weight(node_cloud, future_time, reinforcement_factor=0.2)
    
    # 4. Simulate Falsification
    # Let's say someone explicitly marked the floppy node as "obsolete"
    update_node_weight(node_floppy, future_time, falsification_penalty=0.5)
    
    print(f"\nNode: {node_floppy.id}")
    print(f"Content: {node_floppy.content}")
    print(f"Final Weight: {node_floppy.current_weight:.6f} (Status: Obsolete/Sunken)")
    
    print(f"\nNode: {node_cloud.id}")
    print(f"Content: {node_cloud.content}")
    print(f"Final Weight: {node_cloud.current_weight:.6f} (Status: Active/Reinforced)")
    
    # 5. Filter for Decision Making
    active_knowledge = filter_active_nodes(knowledge_base, threshold=0.1)
    
    print("\n--- Active Knowledge for Decision Making ---")
    for node in active_knowledge:
        print(f"[{node.current_weight:.2f}] {node.content}")
        
    # Expected Output:
    # Floppy weight should be very low (decayed + falsified).
    # Cloud weight should be high (reinforced).
    # Only Cloud should appear in active list.