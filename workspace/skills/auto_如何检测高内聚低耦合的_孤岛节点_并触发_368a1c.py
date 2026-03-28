"""
Module: auto_如何检测高内聚低耦合的_孤岛节点_并触发_368a1c
Description: Detection and handling of semantically redundant but structurally isolated nodes (Island Nodes).
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from pydantic import BaseModel, Field, ValidationError
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class Node(BaseModel):
    """Represents a node in the cognitive network."""
    id: str
    description: str
    embedding: Optional[List[float]] = None
    call_count: int = Field(default=0, ge=0)
    connections: Set[str] = Field(default_factory=set)

    def get_embedding_array(self) -> Optional[np.ndarray]:
        if self.embedding is None:
            return None
        return np.array(self.embedding, dtype=np.float32)

@dataclass
class OptimizationAction:
    """Represents an action to be taken on a node."""
    target_node_id: str
    action_type: str  # 'MERGE_INTO', 'DEPRECATE'
    related_node_id: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""

# --- Core Functions ---

def calculate_semantic_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec_a: First vector
        vec_b: Second vector
        
    Returns:
        Cosine similarity score between 0 and 1.
    """
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    dot_product = np.dot(vec_a, vec_b)
    return float(dot_product / (norm_a * norm_b))

def detect_island_nodes(
    nodes: List[Node], 
    semantic_threshold: float = 0.85, 
    structural_diff_threshold: float = 0.3
) -> List[OptimizationAction]:
    """
    Analyzes the graph to find semantically similar but structurally isolated nodes.
    
    High Cohesion/Low Coupling check:
    1. Semantic Similarity > threshold (Cohesive in meaning)
    2. Structural Overlap < threshold (Low coupling/Isolation)
    
    Args:
        nodes: List of Node objects.
        semantic_threshold: Threshold for cosine similarity to consider redundancy.
        structural_diff_threshold: Max Jaccard distance allowed to consider nodes 'isolated'.
        
    Returns:
        List of OptimizationAction objects.
    """
    if not nodes:
        logger.warning("Empty node list provided.")
        return []

    actions: List[OptimizationAction] = []
    node_dict = {n.id: n for n in nodes}
    
    logger.info(f"Starting island node detection on {len(nodes)} nodes.")
    
    # Filter nodes with embeddings
    valid_nodes = [n for n in nodes if n.embedding is not None]
    
    for i in range(len(valid_nodes)):
        for j in range(i + 1, len(valid_nodes)):
            node_a = valid_nodes[i]
            node_b = valid_nodes[j]
            
            # 1. Semantic Check
            vec_a = node_a.get_embedding_array()
            vec_b = node_b.get_embedding_array()
            
            if vec_a is None or vec_b is None:
                continue
                
            sim = calculate_semantic_similarity(vec_a, vec_b)
            
            if sim >= semantic_threshold:
                # 2. Structural Check (Jaccard Distance)
                # Low overlap implies they are structural islands relative to each other
                inter = len(node_a.connections.intersection(node_b.connections))
                union = len(node_a.connections.union(node_b.connections))
                jaccard_sim = inter / union if union > 0 else 0.0
                structural_distance = 1.0 - jaccard_sim
                
                if structural_distance >= structural_diff_threshold:
                    # Found a candidate pair
                    logger.debug(f"Island pair detected: {node_a.id} & {node_b.id} (Sim: {sim:.2f}, Dist: {structural_distance:.2f})")
                    
                    # Determine dominance based on Information Entropy (proxy: call_count)
                    # Higher count = Higher Entropy/Utility
                    survivor, victim = (node_a, node_b) if node_a.call_count >= node_b.call_count else (node_b, node_a)
                    
                    action = OptimizationAction(
                        target_node_id=victim.id,
                        action_type="MERGE_INTO",
                        related_node_id=survivor.id,
                        confidence=(sim + structural_distance) / 2,
                        reason=f"Semantic overlap {sim:.2f} with structural isolation {structural_distance:.2f}"
                    )
                    actions.append(action)

    logger.info(f"Detection complete. Generated {len(actions)} optimization actions.")
    return actions

# --- Helper / Trigger Functions ---

def execute_optimization_policy(
    graph_state: List[Node], 
    actions: List[OptimizationAction],
    min_confidence: float = 0.7
) -> Dict[str, int]:
    """
    Simulates the execution of optimization actions (Trigger phase).
    Filters actions by confidence and applies logic.
    
    Args:
        graph_state: Current list of nodes (mutable simulation).
        actions: List of proposed actions.
        min_confidence: Threshold to execute action.
        
    Returns:
        Summary statistics of execution.
    """
    stats = {"merged": 0, "deprecated": 0, "skipped": 0}
    node_map = {n.id: n for n in graph_state}
    
    for action in actions:
        if action.confidence < min_confidence:
            stats["skipped"] += 1
            continue
            
        if action.target_node_id not in node_map:
            continue

        if action.action_type == "MERGE_INTO":
            # In a real scenario, we would migrate connections
            logger.info(f"MERGING node {action.target_node_id} into {action.related_node_id}")
            stats["merged"] += 1
            
        elif action.action_type == "DEPRECATE":
            logger.info(f"DEPRECATING node {action.target_node_id}")
            stats["deprecated"] += 1
            
    return stats

# --- Usage Example ---

if __name__ == "__main__":
    # Mock Data Generation
    def generate_mock_embedding(dim=64):
        return list(np.random.randn(dim))

    # Node A: "Quick Sort" - High usage
    node_a = Node(
        id="skill_sort_01",
        description="Implementation of QuickSort algorithm",
        embedding=np.random.randn(64).tolist(), # Random but distinct
        call_count=100,
        connections={"lib_io", "lib_math"}
    )

    # Node B: "Partition Sort" - Low usage, similar context
    # Creating a vector close to A
    base_vec = np.array(node_a.embedding)
    noise = np.random.normal(0, 0.1, 64) # Small noise
    node_b = Node(
        id="skill_sort_02",
        description="Partition-based sorting method",
        embedding=(base_vec + noise).tolist(), # High semantic similarity
        call_count=5,
        connections={"lib_legacy"} # Completely different connections (Island)
    )

    # Node C: "Linear Regression" - Different concept
    node_c = Node(
        id="model_reg_01",
        description="Linear regression model",
        embedding=np.random.randn(64).tolist(),
        call_count=50,
        connections={"lib_math"}
    )

    current_graph = [node_a, node_b, node_c]

    print("--- Running Island Detection ---")
    detected_actions = detect_island_nodes(
        current_graph,
        semantic_threshold=0.8, # Lower threshold for demo
        structural_diff_threshold=0.5
    )

    print(f"Actions detected: {len(detected_actions)}")
    for act in detected_actions:
        print(f"Action: {act.action_type} {act.target_node_id} -> {act.related_node_id} (Conf: {act.confidence:.2f})")

    print("\n--- Executing Policy ---")
    results = execute_optimization_policy(current_graph, detected_actions)
    print(f"Results: {results}")