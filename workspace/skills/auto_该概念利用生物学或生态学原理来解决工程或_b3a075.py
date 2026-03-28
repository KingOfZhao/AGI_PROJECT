"""
Module: bio_inspired_structural_mapping
Description: This module implements a Bio-Inspired Structural Mapping Engine. It identifies
             isomorphic structures between a source domain (e.g., Biological Ecosystems) and
             a target domain (e.g., Network Routing or SQL Optimization). It uses graph
             theory and similarity metrics to map functional groups across domains to generate
             optimization strategies.

Author: AGI System
Version: 1.0.0
"""

import logging
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class DomainNode:
    """
    Represents a node in either the source or target domain graph.
    
    Attributes:
        id: Unique identifier for the node.
        type: Functional type (e.g., 'Predator', 'Index', 'Resource').
        attributes: Dictionary of key-value pairs describing the node.
    """
    id: str
    type: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, DomainNode):
            return self.id == other.id
        return False

@dataclass
class DomainEdge:
    """
    Represents a relationship between two nodes.
    
    Attributes:
        source: Source node ID.
        target: Target node ID.
        relation_type: Type of relationship (e.g., 'preys_on', 'joins_with').
        weight: Strength or cost of the relationship.
    """
    source: str
    target: str
    relation_type: str
    weight: float = 1.0

@dataclass
class IsomorphicMap:
    """
    Contains the mapping result between source and target domains.
    
    Attributes:
        node_mapping: Dictionary mapping Source Node ID -> Target Node ID.
        confidence_score: A float representing the structural similarity (0.0 to 1.0).
        strategy_metadata: Extracted high-level rules from the source to be applied to target.
    """
    node_mapping: Dict[str, str]
    confidence_score: float
    strategy_metadata: Dict[str, Any]

# --- Abstract Base Classes ---

class OptimizationStrategy(ABC):
    """Abstract base class for defining optimization strategies based on mappings."""
    
    @abstractmethod
    def apply(self, target_graph: 'DomainGraph', mapping: IsomorphicMap) -> List[str]:
        """Applies the strategy to the target graph based on the mapping."""
        pass

# --- Core Classes ---

class DomainGraph:
    """
    Represents a graph structure for a specific domain (Source or Target).
    
    Attributes:
        name: Name of the domain.
        nodes: Dictionary of node IDs to DomainNode objects.
        edges: List of DomainEdge objects.
    """
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, DomainNode] = {}
        self.edges: List[DomainEdge] = []
        self._adjacency: Dict[str, List[Tuple[str, float]]] = {}
        logger.info(f"Initialized DomainGraph for: {name}")

    def add_node(self, node: DomainNode) -> None:
        """Adds a node to the graph."""
        if not node.id:
            raise ValueError("Node ID cannot be empty")
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        logger.debug(f"Added node {node.id} to {self.name}")

    def add_edge(self, edge: DomainEdge) -> None:
        """Adds an edge to the graph with validation."""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge references non-existent nodes: {edge.source} -> {edge.target}")
        
        self.edges.append(edge)
        self._adjacency[edge.source].append((edge.target, edge.weight))
        # Assuming undirected or bidirectional for structural similarity context often,
        # but strictly following input direction here.
        logger.debug(f"Added edge {edge.source} -> {edge.target} ({edge.relation_type})")

    def get_node_degree(self, node_id: str) -> int:
        """Returns the degree of a node."""
        return len(self._adjacency.get(node_id, []))

    def get_node_types(self) -> Set[str]:
        """Returns a set of all unique node types in this domain."""
        return {node.type for node in self.nodes.values()}

class StructuralMapper:
    """
    Engine to identify isomorphic structures between a Source Domain (Bio/Eco)
    and a Target Domain (Engineering/Business).
    """

    def __init__(self, source_graph: DomainGraph, target_graph: DomainGraph):
        self.source = source_graph
        self.target = target_graph
        self._type_compatibility_map: Dict[str, str] = {}
        logger.info("StructuralMapper initialized.")

    def set_type_compatibility(self, mapping: Dict[str, str]) -> None:
        """
        Defines which source types map to which target types.
        Example: {'Predator': 'LoadBalancer', 'Prey': 'Server'}
        """
        self._type_compatibility_map = mapping
        logger.info(f"Type compatibility set: {mapping}")

    def _calculate_node_similarity(self, s_node: DomainNode, t_node: DomainNode) -> float:
        """
        Helper: Calculates similarity score between two nodes based on attributes and connectivity.
        Range: 0.0 to 1.0
        """
        score = 0.0
        
        # 1. Type Check
        if self._type_compatibility_map:
            if self._type_compatibility_map.get(s_node.type) != t_node.type:
                return 0.0
        elif s_node.type != t_node.type:
            # If no map provided, require exact match (stricter)
            return 0.0

        # 2. Connectivity Similarity (Degree ratio)
        s_degree = self.source.get_node_degree(s_node.id)
        t_degree = self.target.get_node_degree(t_node.id)
        
        if s_degree == 0 and t_degree == 0:
            conn_score = 1.0
        elif s_degree == 0 or t_degree == 0:
            conn_score = 0.0
        else:
            ratio = min(s_degree, t_degree) / max(s_degree, t_degree)
            conn_score = ratio
        
        # 3. Attribute Similarity (Simple intersection over union for keys)
        # More complex logic could compare values, but we keep it structural here.
        s_keys = set(s_node.attributes.keys())
        t_keys = set(t_node.attributes.keys())
        
        if not s_keys and not t_keys:
            attr_score = 1.0
        else:
            overlap = len(s_keys.intersection(t_keys))
            union = len(s_keys.union(t_keys))
            attr_score = overlap / union if union > 0 else 0.0

        # Weighted average
        score = (0.4 * conn_score) + (0.4 * attr_score) + (0.2) # Base 0.2 for type match
        return score

    def find_best_mapping(self) -> IsomorphicMap:
        """
        Core Algorithm: Identifies the best structural mapping using a greedy 
        heuristic based on node similarity and local graph topology.
        
        Returns:
            IsomorphicMap: The best mapping found.
        """
        logger.info("Starting structural mapping search...")
        if not self._type_compatibility_map:
            logger.warning("No type compatibility map set. Mapping may be inaccurate.")

        candidate_mappings: List[Tuple[float, str, str]] = [] # (score, source_id, target_id)
        
        # 1. Generate all potential node pairs with similarity > threshold
        for s_id, s_node in self.source.nodes.items():
            for t_id, t_node in self.target.nodes.items():
                similarity = self._calculate_node_similarity(s_node, t_node)
                if similarity > 0.5: # Threshold
                    heapq.heappush(candidate_mappings, (-similarity, s_id, t_id)) # Max heap
        
        # 2. Greedy selection (Simplified VF2-like approach)
        final_mapping: Dict[str, str] = {}
        used_target_nodes: Set[str] = set()
        total_score = 0.0
        
        # Sort by score descending
        sorted_candidates = sorted(candidate_mappings, key=lambda x: x[0])
        
        for neg_score, s_id, t_id in sorted_candidates:
            score = -neg_score
            if s_id not in final_mapping and t_id not in used_target_nodes:
                # Consistency check: Do the neighbors match?
                # (Skipping full recursive consistency check for performance in this example,
                # but checking immediate neighbors)
                is_consistent = self._check_edge_consistency(s_id, t_id, final_mapping)
                
                if is_consistent:
                    final_mapping[s_id] = t_id
                    used_target_nodes.add(t_id)
                    total_score += score
                    logger.debug(f"Mapped {s_id} -> {t_id} (Score: {score:.2f})")

        avg_score = total_score / len(final_mapping) if final_mapping else 0.0
        
        # 3. Extract Strategy
        strategy = self._extract_strategy(final_mapping)
        
        logger.info(f"Mapping complete. Mapped {len(final_mapping)} nodes. Confidence: {avg_score:.2f}")
        
        return IsomorphicMap(
            node_mapping=final_mapping,
            confidence_score=avg_score,
            strategy_metadata=strategy
        )

    def _check_edge_consistency(self, s_id: str, t_id: str, current_map: Dict[str, str]) -> bool:
        """Helper: Checks if mapping s_id->t_id violates existing edge mappings."""
        # Check outgoing edges from s_id
        for edge in self.source.edges:
            if edge.source == s_id:
                target_neighbor_id = current_map.get(edge.target)
                if target_neighbor_id:
                    # Check if target graph has corresponding edge
                    if not self._edge_exists(t_id, target_neighbor_id):
                        return False
        return True

    def _edge_exists(self, u: str, v: str) -> bool:
        """Helper: Check if edge exists in target graph."""
        for edge in self.target.edges:
            if edge.source == u and edge.target == v:
                return True
        return False

    def _extract_strategy(self, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Helper: Derives optimization rules based on the biological metaphor.
        Example: If 'Decomposer' maps to 'Garbage Collector', suggest 'Async Cleanup'.
        """
        strategies = {}
        for s_id, t_id in mapping.items():
            s_node = self.source.nodes[s_id]
            t_node = self.target.nodes[t_id]
            
            # Rule extraction logic based on source principles
            if s_node.type == "Decomposer" or "recycler" in s_node.attributes:
                strategies[t_id] = {
                    "action": "recycle_resources",
                    "priority": "low",
                    "logic": "Execute during low-load periods to reclaim memory."
                }
            elif s_node.type == "ApexPredator":
                strategies[t_id] = {
                    "action": "load_balancing",
                    "priority": "high",
                    "logic": "Aggressive resource allocation to handle peak spikes."
                }
        return strategies

# --- Strategy Implementation ---

class SystemOptimizationStrategy(OptimizationStrategy):
    """Applies biological strategies to technical systems."""
    
    def apply(self, target_graph: DomainGraph, mapping: IsomorphicMap) -> List[str]:
        logger.info(f"Applying strategy with confidence {mapping.confidence_score:.2f}...")
        actions_taken = []
        
        for t_id, rule in mapping.strategy_metadata.items():
            if t_id not in target_graph.nodes:
                logger.warning(f"Target node {t_id} not found in graph.")
                continue
            
            action = rule.get('action')
            logger.info(f"Applying action '{action}' to node {t_id}")
            # Simulate modifying the target system
            target_graph.nodes[t_id].attributes['optimization_status'] = 'optimized'
            target_graph.nodes[t_id].attributes['strategy_applied'] = action
            actions_taken.append(f"Node {t_id}: {action}")
            
        return actions_taken

# --- Usage Example ---

def main():
    """
    Example Usage: Mapping a 'Forest Ecosystem' to a 'Database Cluster'.
    Source: Forest (Trees, Deer, Wolves, Fungi)
    Target: DB Cluster (Data Nodes, Query Threads, Monitor, Garbage Collector)
    """
    print("--- Bio-Inspired Structural Mapping Example ---")
    
    # 1. Define Source Domain (Ecosystem)
    source = DomainGraph("ForestEcosystem")
    
    # Nodes
    source.add_node(DomainNode("T1", "Producer", {"energy": "solar", "biomass": 100}))
    source.add_node(DomainNode("D1", "Consumer", {"diet": "herbivore", "speed": "fast"}))
    source.add_node(DomainNode("W1", "Predator", {"diet": "carnivore", "territory": "large"}))
    source.add_node(DomainNode("F1", "Decomposer", {"function": "recycle"}))
    
    # Edges (Energy Flow)
    source.add_edge(DomainEdge("T1", "D1", "consumption"))
    source.add_edge(DomainEdge("D1", "W1", "consumption"))
    source.add_edge(DomainEdge("T1", "F1", "decay"))
    source.add_edge(DomainEdge("D1", "F1", "decay"))

    # 2. Define Target Domain (Database Cluster)
    target = DomainGraph("DatabaseCluster")
    
    # Nodes
    target.add_node(DomainNode("DB_DATA", "Storage", {"type": "SSD", "capacity": "1TB"}))
    target.add_node(DomainNode("DB_QUERY", "Worker", {"thread_count": 16}))
    target.add_node(DomainNode("DB_MONITOR", "Controller", {"cpu_limit": "80%"}))
    target.add_node(DomainNode("DB_GC", "Maintenance", {"schedule": "nightly"}))
    
    # Edges (Data Flow)
    target.add_edge(DomainEdge("DB_DATA", "DB_QUERY", "read"))
    target.add_edge(DomainEdge("DB_QUERY", "DB_MONITOR", "report"))
    target.add_edge(DomainEdge("DB_DATA", "DB_GC", "cleanup"))

    # 3. Configure Mapper
    mapper = StructuralMapper(source, target)
    
    # Map Biological Types to Technical Types
    type_map = {
        "Producer": "Storage",
        "Consumer": "Worker",
        "Predator": "Controller",
        "Decomposer": "Maintenance"
    }
    mapper.set_type_compatibility(type_map)

    # 4. Execute Mapping
    result = mapper.find_best_mapping()
    
    print(f"\nMapping Result (Confidence: {result.confidence_score:.2f}):")
    for s, t in result.node_mapping.items():
        print(f"  {source.name}::{s} ({source.nodes[s].type}) --> {target.name}::{t} ({target.nodes[t].type})")

    # 5. Apply Optimization
    strategy = SystemOptimizationStrategy()
    actions = strategy.apply(target, result)
    
    print("\nOptimization Actions:")
    for action in actions:
        print(f" - {action}")

if __name__ == "__main__":
    main()