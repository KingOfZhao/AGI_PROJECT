"""
Module: cognitive_collision_field.py

This module implements a dynamic 'Cognitive Collision Gravitational Field' algorithm.
It is designed to operate on a large-scale knowledge graph topology (e.g., 1487 nodes)
to automatically identify cross-domain associations and generate 'collision hypotheses'
for innovation discovery.

The core logic involves calculating a 'Conceptual Gravity' based on topological distance
and attribute similarity, specifically targeting nodes that are topologically distant
(cross-domain) but possess high latent correlation.

Author: Senior Python Engineer (AGI System Component)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Data Structures ---

# Gravitational Constant (Adjusted for conceptual space)
G_CONCEPTUAL = 0.5
# Threshold for considering a link a "Cross-Domain" discovery
CROSS_DOMAIN_HOP_THRESHOLD = 4.0

@dataclass
class Node:
    """
    Represents a node in the cognitive topology.
    
    Attributes:
        id: Unique identifier for the node.
        domain: The domain category (e.g., 'Biology', 'Computer Science').
        attributes: A vector or dictionary of features representing the node's concept.
        connections: Set of connected node IDs.
    """
    id: str
    domain: str
    attributes: Dict[str, float] = field(default_factory=dict)
    connections: Set[str] = field(default_factory=set)

@dataclass
class CollisionHypothesis:
    """
    Represents a potential innovation derived from a collision of two concepts.
    """
    source_id: str
    target_id: str
    gravitational_score: float
    cross_domain_factor: float
    hypothesis_description: str

class CognitiveCollisionField:
    """
    Algorithm class for generating a dynamic cognitive collision gravitational field.
    
    This class ingests a graph topology and calculates potential links between nodes
    that are far apart in graph distance but close in latent semantic space.
    """

    def __init__(self, nodes: Dict[str, Node], gravitational_constant: float = G_CONCEPTUAL):
        """
        Initialize the field with existing topology.
        
        Args:
            nodes: A dictionary mapping Node IDs to Node objects.
            gravitational_constant: The scaling factor for attraction.
        """
        self.nodes = nodes
        self.G = gravitational_constant
        self._distance_cache: Dict[Tuple[str, str], float] = {}
        logger.info(f"CognitiveCollisionField initialized with {len(nodes)} nodes.")

    def _calculate_euclidean_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Helper function to calculate similarity between two attribute vectors.
        Uses Euclidean distance converted to a similarity score (0 to 1).
        
        Args:
            vec1: Attribute dictionary of the first node.
            vec2: Attribute dictionary of the second node.
            
        Returns:
            A similarity score between 0.0 and 1.0.
        """
        if not vec1 or not vec2:
            return 0.0
        
        # Find common keys for fair comparison
        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0
            
        sum_sq = sum((vec1[k] - vec2[k]) ** 2 for k in common_keys)
        distance = math.sqrt(sum_sq)
        
        # Convert distance to similarity (using RBF kernel-like function)
        # Sigma (scale) is set to 1.0 for normalization purposes
        similarity = math.exp(-distance ** 2)
        return similarity

    def _get_topological_distance(self, source_id: str, target_id: str, max_depth: int = 10) -> float:
        """
        Helper function to estimate topological distance (shortest path).
        For performance on large graphs, this uses a bidirectional BFS or cached result.
        
        Note: In a production AGI system, this would query a graph database index.
              Here we implement a simplified BFS for the simulation.
        
        Args:
            source_id: Start node ID.
            target_id: End node ID.
            max_depth: Maximum search depth to prevent infinite loops.
            
        Returns:
            Float distance. Returns float('inf') if disconnected.
        """
        if source_id == target_id:
            return 0.0
            
        cache_key = tuple(sorted((source_id, target_id)))
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]

        # Simplified BFS (Not fully bidirectional for code brevity, but functional)
        visited: Set[str] = {source_id}
        queue: List[Tuple[str, int]] = [(source_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth > max_depth:
                self._distance_cache[cache_key] = float('inf')
                return float('inf')
                
            node = self.nodes.get(current_id)
            if not node:
                continue
                
            if target_id in node.connections:
                dist = float(depth + 1)
                self._distance_cache[cache_key] = dist
                return dist
            
            for neighbor_id in node.connections:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))
                    
        self._distance_cache[cache_key] = float('inf')
        return float('inf')

    def calculate_concept_gravity(self, n1: Node, n2: Node) -> float:
        """
        Core Function 1: Calculates the 'Conceptual Gravity' between two nodes.
        
        Formula: F = G * (Sim(n1, n2)) / (Dist(n1, n2) ^ 2 + epsilon)
        
        High gravity implies high semantic similarity but existing topological gap.
        
        Args:
            n1: First Node object.
            n2: Second Node object.
            
        Returns:
            Gravitational force score.
        """
        if n1.id == n2.id:
            return 0.0

        # 1. Semantic Mass (Similarity)
        semantic_mass = self._calculate_euclidean_similarity(n1.attributes, n2.attributes)
        
        # 2. Topological Distance
        topo_dist = self._get_topological_distance(n1.id, n2.id)
        
        if topo_dist == float('inf') or topo_dist == 0:
            return 0.0
            
        # 3. Calculate Force (Inverse Square Law modified)
        # We add a small epsilon to prevent division by zero for immediate neighbors
        # but we actually want to penalize immediate neighbors, so we treat dist < 1 differently.
        # For this algorithm, we want 'Long Range' forces.
        
        # If they are direct neighbors, they are 'known', not 'innovative'
        if topo_dist <= 1.5: 
            return 0.0 

        force = self.G * semantic_mass / (topo_dist ** 2)
        
        return force

    def detect_collision_candidates(self, top_k: int = 10) -> List[CollisionHypothesis]:
        """
        Core Function 2: Scans the topology to find high-potential collision candidates.
        
        It iterates through node pairs (sampling or optimized scan) to find those
        with the highest 'Innovation Score' (High Gravity + Cross-Domain).
        
        Args:
            top_k: Number of top hypotheses to return.
            
        Returns:
            List of CollisionHypothesis objects sorted by potential.
        """
        logger.info("Starting collision detection scan...")
        candidates: List[CollisionHypothesis] = []
        
        # In a real 1487-node scenario, O(N^2) is ~2M operations, feasible in Python.
        # We optimize by skipping pairs within the same domain early if desired,
        # but here we calculate gravity first to catch unexpected intra-domain gaps.
        
        node_ids = list(self.nodes.keys())
        total_pairs = len(node_ids) * (len(node_ids) - 1) // 2
        processed = 0
        
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                n1 = self.nodes[node_ids[i]]
                n2 = self.nodes[node_ids[j]]
                
                # Optimization: Skip if attributes are empty
                if not n1.attributes or not n2.attributes:
                    continue
                
                force = self.calculate_concept_gravity(n1, n2)
                
                # Filter: We want significant force
                if force > 0.01:
                    # Check for Cross-Domain nature
                    cross_domain_bonus = 1.0
                    if n1.domain != n2.domain:
                        cross_domain_bonus = 2.5 # Boost score for cross-domain
                    
                    final_score = force * cross_domain_bonus
                    
                    if final_score > 0.05:
                        dist = self._get_topological_distance(n1.id, n2.id)
                        hypothesis = CollisionHypothesis(
                            source_id=n1.id,
                            target_id=n2.id,
                            gravitational_score=final_score,
                            cross_domain_factor=dist,
                            hypothesis_description=f"Latent link between '{n1.domain}:{n1.id}' and '{n2.domain}:{n2.id}'"
                        )
                        candidates.append(hypothesis)
                
                processed += 1
        
        # Sort by score descending
        candidates.sort(key=lambda x: x.gravitational_score, reverse=True)
        logger.info(f"Scan complete. Found {len(candidates)} potential collisions.")
        
        return candidates[:top_k]

# --- Usage Example ---

def generate_mock_topology(num_nodes: int = 1487) -> Dict[str, Node]:
    """
    Helper to generate a mock graph for demonstration.
    """
    nodes = {}
    domains = ["Physics", "Biology", "Sociology", "CS", "Art"]
    
    for i in range(num_nodes):
        node_id = f"node_{i}"
        domain = random.choice(domains)
        
        # Randomize attributes (semantic vector)
        attrs = {f"feat_{k}": random.random() for k in range(5)}
        
        nodes[node_id] = Node(id=node_id, domain=domain, attributes=attrs)
    
    # Create some edges (sparse graph)
    # Connect neighbors
    node_ids = list(nodes.keys())
    for i in range(len(node_ids) - 1):
        # Local connections
        nodes[node_ids[i]].connections.add(node_ids[i+1])
        if i < len(node_ids) - 2:
            nodes[node_ids[i]].connections.add(node_ids[i+2])
            
    # Create a specific "Cross Domain" hidden link for testing
    # Node 0 (Physics) and Node 1000 (Biology) have similar attributes but no graph connection
    nodes["node_0"].domain = "Physics"
    nodes["node_1000"].domain = "Biology"
    nodes["node_0"].attributes = {"feat_0": 0.9, "feat_1": 0.1}
    nodes["node_1000"].attributes = {"feat_0": 0.91, "feat_1": 0.11}
    # Ensure they are far apart in topology
    if "node_1000" in nodes["node_0"].connections:
        nodes["node_0"].connections.remove("node_1000")
        
    return nodes

if __name__ == "__main__":
    # 1. Setup
    logger.info("Generating mock data for 1487 nodes...")
    mock_nodes = generate_mock_topology(1487)
    
    # 2. Initialize Algorithm
    field_algo = CognitiveCollisionField(nodes=mock_nodes)
    
    # 3. Execute Detection
    top_hypotheses = field_algo.detect_collision_candidates(top_k=5)
    
    # 4. Display Results
    print("\n--- Top Cognitive Collision Hypotheses ---")
    for idx, hyp in enumerate(top_hypotheses):
        print(f"{idx+1}. Score: {hyp.gravitational_score:.4f} | Distance: {hyp.cross_domain_factor}")
        print(f"   Pair: {hyp.source_id} <-> {hyp.target_id}")
        print(f"   Desc: {hyp.hypothesis_description}")
        print("-" * 40)