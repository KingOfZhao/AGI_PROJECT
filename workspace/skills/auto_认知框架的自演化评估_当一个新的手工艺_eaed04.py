"""
Module: auto_cognitive_framework_evolution_evaluator
Description: 【认知框架的自演化评估】
This module evaluates the 'collision effect' of a new skill node on an existing knowledge graph.
It assesses whether the integration of new knowledge leads to structural reorganization or fusion,
rather than merely incrementing the node count.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
import random
import time
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveEvaluator")


@dataclass
class SkillNode:
    """Represents a node in the cognitive skill graph."""
    node_id: str
    features: List[float]
    connections: Set[str] = field(default_factory=set)
    is_anchor: bool = False  # Anchor nodes represent stable, core knowledge


class GraphStructureError(Exception):
    """Custom exception for graph structure related errors."""
    pass


def validate_feature_vector(features: List[float], dimension: int = 128) -> bool:
    """
    Helper function to validate the integrity of a feature vector.
    
    Args:
        features (List[float]): The feature vector to validate.
        dimension (int): Expected dimension of the vector.
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If vector is None, empty, or wrong dimension.
    """
    if not features:
        raise ValueError("Feature vector cannot be empty.")
    if len(features) != dimension:
        raise ValueError(f"Feature vector dimension mismatch. Expected {dimension}, got {len(features)}.")
    return True


def calculate_semantic_drift(
    existing_graph: Dict[str, SkillNode], 
    node_id_a: str, 
    node_id_b: str
) -> float:
    """
    Calculate the semantic drift (distance) between two nodes based on cosine similarity.
    
    Args:
        existing_graph: The graph dictionary.
        node_id_a: ID of the first node.
        node_id_b: ID of the second node.
        
    Returns:
        float: A distance score (0.0 to 1.0, where 0 is identical).
    """
    node_a = existing_graph.get(node_id_a)
    node_b = existing_graph.get(node_id_b)
    
    if not node_a or not node_b:
        logger.warning(f"Calculation skipped: missing nodes {node_id_a} or {node_id_b}")
        return 1.0
        
    # Simple dot product for demo (Cosine Similarity logic)
    dot = sum(a * b for a, b in zip(node_a.features, node_b.features))
    norm_a = sum(a**2 for a in node_a.features) ** 0.5
    norm_b = sum(b**2 for b in node_b.features) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 1.0
        
    similarity = dot / (norm_a * norm_b)
    # Convert similarity (0-1) to distance (1-0)
    return 1.0 - max(0.0, min(1.0, similarity))


def evaluate_collision_effect(
    existing_graph: Dict[str, SkillNode], 
    new_node: SkillNode, 
    similarity_threshold: float = 0.85
) -> Dict[str, float]:
    """
    Core Function 1: Evaluates the immediate collision effect of a new node.
    
    This function checks how the new node connects to existing nodes and calculates
    a 'Fusion Index' and 'Disruption Score'.
    
    Args:
        existing_graph (Dict[str, SkillNode]): The current knowledge graph (mapping ID -> Node).
        new_node (SkillNode): The newly created skill node.
        similarity_threshold (float): Threshold to determine if a connection implies fusion.
        
    Returns:
        Dict[str, float]: A dictionary containing evaluation metrics:
            - 'fusion_index': Degree to which the new node merges with existing dense clusters.
            - 'disruption_score': How much the new node alters the semantic space of neighbors.
            - 'connectivity_gain': Increase in graph density relative to local area.
            
    Raises:
        GraphStructureError: If the graph is empty or node validation fails.
    """
    if not existing_graph:
        raise GraphStructureError("Existing graph cannot be empty for evaluation.")
    
    try:
        validate_feature_vector(new_node.features)
    except ValueError as e:
        logger.error(f"Invalid new node data: {e}")
        raise GraphStructureError(f"Node validation failed: {e}")

    logger.info(f"Starting collision evaluation for Node: {new_node.node_id}")
    
    fusion_count = 0
    total_drift = 0.0
    neighbor_count = len(new_node.connections)
    
    if neighbor_count == 0:
        return {'fusion_index': 0.0, 'disruption_score': 0.0, 'connectivity_gain': 0.0}

    # Analyze connections
    for neighbor_id in new_node.connections:
        if neighbor_id in existing_graph:
            drift = calculate_semantic_drift(existing_graph, new_node.node_id, neighbor_id)
            total_drift += drift
            
            # If drift is low (high similarity), it's a fusion event
            if drift < (1.0 - similarity_threshold):
                fusion_count += 1
                
    # Calculate Metrics
    fusion_index = fusion_count / neighbor_count
    avg_drift = total_drift / neighbor_count
    connectivity_gain = neighbor_count / len(existing_graph) # Relative connectivity
    
    results = {
        'fusion_index': round(fusion_index, 4),
        'disruption_score': round(avg_drift, 4), # Higher drift = higher disruption/change
        'connectivity_gain': round(connectivity_gain, 4)
    }
    
    logger.info(f"Evaluation Results: {results}")
    return results


def check_structural_reorganization(
    existing_graph: Dict[str, SkillNode], 
    new_node: SkillNode, 
    metrics: Dict[str, float]
) -> Tuple[bool, str]:
    """
    Core Function 2: Determines if the collision triggers a structural evolution.
    
    It analyzes the metrics from the collision to decide if the system has undergone
    a meaningful evolution (e.g., bridging two disconnected clusters or merging concepts).
    
    Args:
        existing_graph (Dict[str, SkillNode]): The current knowledge graph.
        new_node (SkillNode): The new node.
        metrics (Dict[str, float]): Metrics returned by `evaluate_collision_effect`.
        
    Returns:
        Tuple[bool, str]: (True if evolution occurred, Reason string).
    """
    is_evolution = False
    reason = "No significant structural change."
    
    # Logic: If the node has high connectivity and significant disruption, 
    # it implies it's forcing a re-routing of semantic paths.
    # Or if fusion is high, it's strengthening existing patterns.
    
    if metrics['fusion_index'] > 0.7:
        is_evolution = True
        reason = "High Fusion: Knowledge consolidation detected. Node acts as a keystone."
    elif metrics['disruption_score'] > 0.5 and metrics['connectivity_gain'] > 0.05:
        is_evolution = True
        reason = "High Disruption: Paradigm shift detected. Node creates new semantic bridges."
    elif metrics['connectivity_gain'] > 0.1:
         is_evolution = True
         reason = "High Connectivity: New central hub established."
         
    if is_evolution:
        logger.info(f"Structural Evolution Detected! Reason: {reason}")
    else:
        logger.info("Node added as isolated or peripheral knowledge.")
        
    return is_evolution, reason


# --- Usage Example and Simulation ---
if __name__ == "__main__":
    logger.info("Initializing Cognitive Graph Simulation...")
    
    # 1. Generate Mock Graph (Simulating existing 697 skills)
    DIM = 128
    mock_graph = {}
    for i in range(697):
        # Create nodes with random features and some random connections
        nid = f"skill_{i}"
        features = [random.gauss(0, 1) for _ in range(DIM)]
        # Normalize features
        norm = sum(x**2 for x in features) ** 0.5
        features = [x/norm for x in features]
        
        node = SkillNode(node_id=nid, features=features)
        # Add some existing connections
        if i > 0:
            node.connections.add(f"skill_{i-1}")
        mock_graph[nid] = node
        
    logger.info(f"Mock graph created with {len(mock_graph)} nodes.")
    
    # 2. Create a New Node (The new craft skill)
    # Let's make it somewhat similar to node 'skill_0' to trigger fusion
    base_features = mock_graph["skill_0"].features[:]
    noise = [random.gauss(0, 0.1) for _ in range(DIM)]
    new_features = [b + n for b, n in zip(base_features, noise)]
    norm = sum(x**2 for x in new_features) ** 0.5
    new_features = [x/norm for x in new_features]
    
    new_skill = SkillNode(node_id="craft_698", features=new_features)
    # Connect it to a few existing nodes
    new_skill.connections.update(["skill_0", "skill_1", "skill_2", "skill_400"])
    
    # 3. Run Evaluation
    try:
        collision_metrics = evaluate_collision_effect(mock_graph, new_skill)
        evolution_status, message = check_structural_reorganization(mock_graph, new_skill, collision_metrics)
        
        print("\n--- Final Report ---")
        print(f"New Node ID: {new_skill.node_id}")
        print(f"Metrics: {collision_metrics}")
        print(f"Evolution Status: {evolution_status}")
        print(f"Diagnosis: {message}")
        
    except GraphStructureError as e:
        logger.error(f"Simulation failed: {e}")