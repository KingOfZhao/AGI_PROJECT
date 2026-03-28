"""
Module: auto_structural_isomorphism_engine
Description: This is the core engine for AGI to achieve creative leaps.
             It focuses on discovering 'structural isomorphisms' between
             disparate domains rather than surface-level linguistic similarities.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge in the vector space.
    
    Attributes:
        id: Unique identifier for the node.
        domain: The domain the node belongs to (e.g., 'biology', 'physics').
        vector: High-dimensional embedding representation of the concept.
        is_verified: Boolean indicating if this is 'executable knowledge' (Ground Truth).
        metadata: Additional properties or execution logic.
    """
    id: str
    domain: str
    vector: List[float]
    is_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.vector, list) or not all(isinstance(x, (float, int)) for x in self.vector):
            raise ValueError("Vector must be a list of numbers.")
        if len(self.vector) == 0:
            raise ValueError("Vector dimension cannot be zero.")


class StructuralIsomorphismEngine:
    """
    The core engine for discovering deep structural isomorphisms across domains.
    
    It identifies 'structurally adjacent' concepts—nodes that are semantically close 
    in vector space but separated by domain boundaries—to generate novel metaphors 
    and solutions.
    """

    def __init__(self, similarity_threshold: float = 0.85, domain_gap_weight: float = 1.5):
        """
        Initialize the engine.
        
        Args:
            similarity_threshold: Minimum cosine similarity to consider nodes related.
            domain_gap_weight: Heuristic weight to prioritize cross-domain pairs.
        """
        self.similarity_threshold = similarity_threshold
        self.domain_gap_weight = domain_gap_weight
        self.knowledge_base: List[KnowledgeNode] = []
        logger.info("StructuralIsomorphismEngine initialized.")

    def add_knowledge(self, nodes: List[KnowledgeNode]) -> None:
        """Loads nodes into the knowledge base."""
        if not nodes:
            logger.warning("Attempted to add empty node list.")
            return
        self.knowledge_base.extend(nodes)
        logger.info(f"Added {len(nodes)} nodes. Total knowledge size: {len(self.knowledge_base)}")

    def _validate_vector_dimensions(self, target_vector: List[float]) -> bool:
        """Checks if a vector matches the dimensionality of the knowledge base."""
        if not self.knowledge_base:
            return False
        base_dim = len(self.knowledge_base[0].vector)
        return len(target_vector) == base_dim

    def _calculate_structural_potential(self, node_a: KnowledgeNode, node_b: KnowledgeNode) -> float:
        """
        Calculates the potential for a creative leap between two nodes.
        High potential = High similarity + Different Domains + Verified Source.
        """
        if node_a.domain == node_b.domain:
            return 0.0  # We want cross-domain connections

        vec_a = np.array(node_a.vector).reshape(1, -1)
        vec_b = np.array(node_b.vector).reshape(1, -1)
        
        similarity = cosine_similarity(vec_a, vec_b)[0][0]
        
        # Heuristic: Amplify score if source is verified 'Real Node'
        verification_bonus = 1.2 if node_a.is_verified else 1.0
        
        return similarity * verification_bonus * self.domain_gap_weight

    def probe_latent_space(self, source_node: KnowledgeNode, top_k: int = 5) -> List[Tuple[KnowledgeNode, float]]:
        """
        Core Function 1: Probes the vector space to find 'Distance Near, Taxonomy Far' nodes.
        
        Args:
            source_node: The node from which to initiate the probe.
            top_k: Number of top candidates to return.
            
        Returns:
            A list of tuples containing the target node and the isomorphism score.
            
        Raises:
            ValueError: If vector dimensions do not match the existing knowledge base.
        """
        if not self._validate_vector_dimensions(source_node.vector):
            raise ValueError("Source node vector dimensions do not match knowledge base.")
        
        candidates = []
        
        for node in self.knowledge_base:
            if node.id == source_node.id:
                continue
            
            score = self._calculate_structural_potential(source_node, node)
            
            if score >= self.similarity_threshold:
                candidates.append((node, score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Probing completed. Found {len(candidates)} raw isomorphisms.")
        return candidates[:top_k]

    def verify_isomorphism_feasibility(self, source: KnowledgeNode, target: KnowledgeNode) -> bool:
        """
        Core Function 2: Validates if the isomorphism is 'Executable' or just 'Linguistic'.
        
        This acts as a filter to distinguish between poetic metaphors (linguistic) 
        and actionable innovations (physical/logic structural match).
        
        Args:
            source: The source node (must be verified).
            target: The target node.
            
        Returns:
            True if the mapping is structurally feasible, False otherwise.
        """
        # Rule 1: Source must be 'Real' (Verified)
        if not source.is_verified:
            logger.debug(f"Verification failed: Source {source.id} is not verified.")
            return False

        # Rule 2: Structural Key Match (Simulated)
        # In a real AGI, this would check knowledge graph relations or functional signatures.
        # Here we simulate by checking if specific 'structural keys' exist in metadata.
        source_keys = set(source.metadata.get("structural_keys", []))
        target_keys = set(target.metadata.get("structural_keys", []))
        
        overlap = source_keys.intersection(target_keys)
        
        # If they share specific structural properties, the mapping is feasible.
        if len(overlap) >= 1:
            logger.info(f"Feasibility confirmed: Structural overlap found {overlap} between {source.id} and {target.id}.")
            return True
        
        logger.debug("Feasibility failed: No structural overlap.")
        return False

    def generate_creative_leap(self, source: KnowledgeNode) -> Dict[str, Any]:
        """
        High-level orchestration function.
        Combines probing and verification to produce a final output.
        """
        if source not in self.knowledge_base:
             # Ensure we track it even if temporary
             self.knowledge_base.append(source)
             
        raw_candidates = self.probe_latent_space(source)
        validated_leaps = []
        
        for candidate, score in raw_candidates:
            if self.verify_isomorphism_feasibility(source, candidate):
                validated_leaps.append({
                    "target_id": candidate.id,
                    "target_domain": candidate.domain,
                    "confidence": score,
                    "insight": f"Applying logic of '{source.id}' to '{candidate.domain}' context."
                })
                
        return {
            "source_id": source.id,
            "discovered_leaps": validated_leaps,
            "status": "success" if validated_leaps else "no_viable_leaps"
        }


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Engine
    engine = StructuralIsomorphismEngine(similarity_threshold=0.75)
    
    # 2. Create Mock Knowledge Nodes
    # Node A: Verified knowledge about "Neural Networks pruning" (Computer Science)
    node_cs = KnowledgeNode(
        id="nn_pruning",
        domain="computer_science",
        vector=np.random.rand(128).tolist(), # Mock embedding
        is_verified=True,
        metadata={"structural_keys": ["hierarchy", "efficiency", "redundancy_reduction"]}
    )
    
    # Node B: Knowledge about "Brain Synaptic Pruning" (Biology) - High similarity, different domain
    # We construct a vector very close to Node A to simulate semantic closeness
    noise = np.random.normal(0, 0.01, 128) # Small noise
    vec_bio = np.array(node_cs.vector) + noise
    node_bio = KnowledgeNode(
        id="synaptic_pruning",
        domain="biology",
        vector=vec_bio.tolist(),
        is_verified=False, # Target doesn't need to be verified, but usually is known
        metadata={"structural_keys": ["hierarchy", "efficiency"]} # Partial overlap
    )
    
    # Node C: Knowledge about "Gardening" (Unrelated)
    node_garden = KnowledgeNode(
        id="tree_trimming",
        domain="agriculture",
        vector=np.random.rand(128).tolist(),
        is_verified=True,
        metadata={"structural_keys": ["aesthetic"]}
    )
    
    # 3. Load Data
    engine.add_knowledge([node_cs, node_bio, node_garden])
    
    # 4. Execute Creative Leap
    print("--- Generating Creative Leap ---")
    result = engine.generate_creative_leap(node_cs)
    
    print(f"Source: {result['source_id']}")
    print(f"Status: {result['status']}")
    for leap in result['discovered_leaps']:
        print(f"Found Leap to Domain: {leap['target_domain']}")
        print(f"Target Node: {leap['target_id']}")
        print(f"Insight: {leap['insight']}")