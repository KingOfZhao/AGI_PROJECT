"""
Module: auto_cross_domain_structural_mapping_filter.py

Description:
    Implements a 'Structural Mapping' filter mechanism for Cross-Domain Transfer.
    This algorithm prioritizes deep structural similarity (isomorphism) over 
    surface semantic similarity to prevent invalid analogical transfers 
    (e.g., preventing 'left-right collisions' where concepts align incorrectly).
    
    Example Case:
        Source: Immune System (Identify -> Attack -> Memory)
        Target: Network Security (Detect -> Mitigate -> Log/Update)
        Mechanism: Matches the *process flow* rather than keyword overlap 
                   (e.g., 'Cell' vs 'Code').
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration for types of nodes in a knowledge graph."""
    ENTITY = 1
    PROCESS = 2
    ATTRIBUTE = 3

@dataclass
class Node:
    """Represents a node in the knowledge structure."""
    id: str
    type: NodeType
    attributes: Dict[str, str]

@dataclass
class Edge:
    """Represents a relationship between nodes."""
    source_id: str
    target_id: str
    relation: str

class KnowledgeGraph:
    """
    A simple representation of a domain structure using nodes and edges.
    """
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, List[Tuple[str, str]]] = {} # node_id -> [(neighbor_id, relation)]

    def add_node(self, id: str, type: NodeType, attributes: Dict[str, str] = None):
        if id in self.nodes:
            logger.warning(f"Node {id} already exists in graph {self.name}. Overwriting.")
        self.nodes[id] = Node(id, type, attributes or {})
        self._adjacency[id] = []

    def add_edge(self, source_id: str, target_id: str, relation: str):
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Source or Target node does not exist.")
        
        self.edges.append(Edge(source_id, target_id, relation))
        self._adjacency[source_id].append((target_id, relation))
        # Assuming directed graph for processes, but structural mapping might need undirected view
        # self._adjacency[target_id].append((source_id, f"reverse_{relation}"))

    def get_node_degree(self, node_id: str) -> int:
        return len(self._adjacency.get(node_id, []))

    def get_neighbors_by_relation(self, node_id: str, relation: str) -> List[str]:
        return [n for n, r in self._adjacency.get(node_id, []) if r == relation]

def _calculate_structural_vector(graph: KnowledgeGraph, node_id: str) -> Dict[str, int]:
    """
    Helper function: Generates a structural signature (vector) for a node.
    
    Analyzes connectivity patterns: degree count, specific relation counts, etc.
    This acts as a fingerprint for structural comparison.
    
    Args:
        graph: The knowledge graph containing the node.
        node_id: The ID of the node to analyze.
        
    Returns:
        A dictionary representing the structural features (e.g., {'degree': 3, 'causes': 1}).
    """
    if node_id not in graph.nodes:
        return {}

    neighbors = graph._adjacency.get(node_id, [])
    
    # Feature extraction
    degree = len(neighbors)
    relation_counts = {}
    for _, relation in neighbors:
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
    
    # Create a composite vector
    vector = {'degree': degree}
    vector.update(relation_counts)
    
    return vector

def retrieve_structural_matches(
    source_domain: KnowledgeGraph, 
    target_domain: KnowledgeGraph, 
    similarity_threshold: float = 0.6
) -> List[Tuple[str, str, float]]:
    """
    Core Function 1: Retrieves potential mappings between source and target domains 
    based on structural isomorphism.
    
    Algorithm:
    1. Iterate through all nodes in the source domain.
    2. Iterate through all nodes in the target domain.
    3. Calculate structural similarity (topology, relation types) rather than semantic similarity.
    4. Filter based on threshold.
    
    Args:
        source_domain: Graph representing the source knowledge.
        target_domain: Graph representing the target problem space.
        similarity_threshold: Minimum score (0.0 to 1.0) to accept a mapping.
        
    Returns:
        A list of tuples: (source_node_id, target_node_id, similarity_score).
    """
    logger.info(f"Starting structural mapping between {source_domain.name} and {target_domain.name}")
    
    if not source_domain.nodes or not target_domain.nodes:
        logger.error("One or both domains are empty.")
        return []

    candidates = []

    for s_id, s_node in source_domain.nodes.items():
        s_vector = _calculate_structural_vector(source_domain, s_id)
        
        for t_id, t_node in target_domain.nodes.items():
            # Phase 1: Type constraint (Optional, but good for pruning)
            if s_node.type != t_node.type:
                continue

            # Phase 2: Structural Vector Comparison
            t_vector = _calculate_structural_vector(target_domain, t_id)
            
            # Calculate Jaccard-like similarity on structural vectors
            # Keys are relation types (structural roles), values are counts
            all_keys = set(s_vector.keys()).union(set(t_vector.keys()))
            intersection_score = 0
            union_score = 0
            
            for key in all_keys:
                s_val = s_vector.get(key, 0)
                t_val = t_vector.get(key, 0)
                intersection_score += min(s_val, t_val)
                union_score += max(s_val, t_val)
            
            if union_score == 0:
                similarity = 0.0
            else:
                similarity = intersection_score / union_score
            
            if similarity >= similarity_threshold:
                candidates.append((s_id, t_id, similarity))
                logger.debug(f"Candidate found: {s_id} -> {t_id} (Score: {similarity:.2f})")

    logger.info(f"Found {len(candidates)} potential structural mappings.")
    return candidates

def validate_mapping_consistency(
    mappings: List[Tuple[str, str, float]], 
    source_domain: KnowledgeGraph, 
    target_domain: KnowledgeGraph
) -> List[Dict]:
    """
    Core Function 2: Validates the retrieved mappings by checking relational consistency.
    
    Ensures that if A -> B in Source maps to X -> Y in Target, the relationship 
    type between A->B is compatible with X->Y. This prevents 'Left-Right Collisions'.
    
    Args:
        mappings: List of candidate mappings from `retrieve_structural_matches`.
        source_domain: Source graph.
        target_domain: Target graph.
        
    Returns:
        A filtered list of valid mapping groups (contexts).
    """
    logger.info("Validating mapping consistency...")
    valid_groups = []
    
    # Convert mappings to a dict for quick lookup
    map_dict = {s: t for s, t, _ in mappings}
    
    for s_id, t_id, score in mappings:
        # Check outgoing edges
        s_neighbors = source_domain._adjacency.get(s_id, [])
        t_neighbors = target_domain._adjacency.get(t_id, [])
        
        matches = 0
        total_relations = len(s_neighbors)
        
        if total_relations == 0:
            continue
            
        for s_neighbor, s_relation in s_neighbors:
            # Does the mapped target node have a neighbor with the same relation type?
            if s_neighbor in map_dict:
                mapped_target_neighbor = map_dict[s_neighbor]
                
                # Check if this specific relation exists in target
                found = False
                for t_neighbor, t_relation in t_neighbors:
                    if t_neighbor == mapped_target_neighbor and t_relation == s_relation:
                        found = True
                        break
                
                if found:
                    matches += 1
        
        # Consistency score: How many relations in source are preserved in target structure?
        consistency = matches / total_relations if total_relations > 0 else 0
        
        if consistency >= 0.5: # Require at least 50% structural consistency
            valid_groups.append({
                "source_node": s_id,
                "target_node": t_id,
                "structural_similarity": score,
                "relation_consistency": consistency
            })
            
    logger.info(f"Validated {len(valid_groups)} consistent mapping groups.")
    return valid_groups

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Define Source Domain: Immune System
    immune_system = KnowledgeGraph("ImmuneSystem")
    immune_system.add_node("Pathogen", NodeType.ENTITY)
    immune_system.add_node("Macrophage", NodeType.ENTITY)
    immune_system.add_node("TCell", NodeType.ENTITY)
    immune_system.add_node("BCell", NodeType.ENTITY)
    immune_system.add_node("Antibody", NodeType.ENTITY)
    
    immune_system.add_edge("Macrophage", "TCell", "activates")
    immune_system.add_edge("TCell", "BCell", "stimulates")
    immune_system.add_edge("BCell", "Antibody", "produces")
    immune_system.add_edge("Antibody", "Pathogen", "neutralizes")
    
    # 2. Define Target Domain: Cyber Security
    # Note: Different vocabulary, but similar structure
    cyber_security = KnowledgeGraph("CyberSecurity")
    cyber_security.add_node("Malware", NodeType.ENTITY)
    cyber_security.add_node("IDS", NodeType.ENTITY) # Intrusion Detection System (Macrophage analog)
    cyber_security.add_node("Analyst", NodeType.ENTITY) # TCell analog
    cyber_security.add_node("Firewall", NodeType.ENTITY) # BCell/Antibody producer analog
    cyber_security.add_node("Patch", NodeType.ENTITY) # Antibody analog
    
    # Structure: Detect -> Alert -> Create Patch -> Neutralize
    cyber_security.add_edge("IDS", "Analyst", "activates")
    cyber_security.add_edge("Analyst", "Firewall", "stimulates")
    cyber_security.add_edge("Firewall", "Patch", "produces")
    cyber_security.add_edge("Patch", "Malware", "neutralizes")
    
    # Add some noise to make it harder
    cyber_security.add_node("User", NodeType.ENTITY)
    cyber_security.add_edge("User", "Malware", "downloads") # Different structure

    print("-" * 50)
    print("Executing Structural Mapping Filter...")
    print("-" * 50)

    # Step 1: Retrieve candidates based on topology
    candidates = retrieve_structural_matches(immune_system, cyber_security, similarity_threshold=0.5)
    
    # Step 2: Validate to ensure deep structure match
    final_mappings = validate_mapping_consistency(candidates, immune_system, cyber_security)
    
    print("\n--- Final Mappings (Deep Structure Match) ---")
    for m in final_mappings:
        print(f"Source: {m['source_node']:10} --> Target: {m['target_node']:10} "
              f"(Sim: {m['structural_similarity']:.2f}, Consistency: {m['relation_consistency']:.2f})")