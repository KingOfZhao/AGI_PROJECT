"""
Module: auto_ecological_niche_value_1fe2b7
Description: [Left-Right Cross-Domain] Ecological Niche Value Assessment for 'API Call Chains'.
             Evaluates whether a SKILL node acts as a critical dependency for other nodes.
             It calculates a 'Reference Weight' (PageRank variant) to identify isolated leaf nodes
             or critical hub nodes.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
DAMPING_FACTOR = 0.85  # Standard PageRank damping factor
MAX_ITERATIONS = 100   # Maximum iterations for convergence
TOLERANCE = 1.0e-6     # Convergence tolerance
DEFAULT_WEIGHT = 1.0   # Initial weight for nodes

@dataclass
class SkillNode:
    """
    Represents a SKILL node in the ecosystem.
    
    Attributes:
        id: Unique identifier for the skill.
        description: Brief description of the skill.
        imports: List of other skill IDs this node depends on (Left/Called resources).
        exports: List of other skill IDs that depend on this node (Right/Consumers).
                 Note: In a graph analysis, 'exports' are usually derived from other nodes' imports.
        direct_usage_freq: Frequency of direct invocation by human/end-users (0.0 to 1.0).
    """
    id: str
    description: str = ""
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)  # Populated during graph building
    direct_usage_freq: float = 0.0

    def __post_init__(self):
        if not isinstance(self.id, str):
            raise ValueError("SkillNode id must be a string.")
        if not 0.0 <= self.direct_usage_freq <= 1.0:
            raise ValueError("direct_usage_freq must be between 0.0 and 1.0.")

@dataclass
class NicheAssessment:
    """
    Result object containing the ecological value assessment.
    """
    skill_id: str
    pagerank_score: float
    is_leaf: bool
    is_isolated: bool
    connectivity_score: float  # Combination of structure and usage
    verdict: str

def _validate_graph_inputs(nodes: List[SkillNode]) -> Dict[str, SkillNode]:
    """
    Helper function to validate inputs and build a lookup dictionary.
    
    Args:
        nodes: List of SkillNode objects.
        
    Returns:
        A dictionary mapping node ID to SkillNode.
        
    Raises:
        ValueError: If duplicate IDs are found.
    """
    logger.info(f"Validating {len(nodes)} skill nodes...")
    node_dict: Dict[str, SkillNode] = {}
    
    for node in nodes:
        if node.id in node_dict:
            logger.error(f"Duplicate node ID detected: {node.id}")
            raise ValueError(f"Duplicate node ID: {node.id}")
        node_dict[node.id] = node
        
    return node_dict

def build_dependency_graph(nodes: List[SkillNode]) -> Tuple[Dict[str, SkillNode], Dict[str, Set[str]]]:
    """
    Builds the reverse dependency graph (who calls whom).
    
    This function resolves 'imports' to populate the 'exports' (incoming links) 
    for PageRank calculation.
    
    Args:
        nodes: A list of SkillNode objects.
        
    Returns:
        A tuple containing:
        - The node dictionary.
        - An adjacency list (reverse dependencies) where key=callee, value=set(callers).
    """
    node_dict = _validate_graph_inputs(nodes)
    reverse_adj_list: Dict[str, Set[str]] = defaultdict(set)
    
    # Build connections
    for node in nodes:
        # Ensure every node exists in adjacency list even if it has no incoming links
        if node.id not in reverse_adj_list:
            reverse_adj_list[node.id] = set()
            
        for dep_id in node.imports:
            if dep_id in node_dict:
                # node (caller) -> dep_id (callee)
                # For PageRank, we need to know who links TO dep_id.
                # So we add 'node.id' to the list of nodes pointing to 'dep_id'
                reverse_adj_list[dep_id].add(node.id)
                # Update the object model for reference
                node_dict[dep_id].exports.append(node.id)
            else:
                logger.warning(f"Node {node.id} imports non-existent skill: {dep_id}")

    logger.info("Dependency graph constructed successfully.")
    return node_dict, reverse_adj_list

def calculate_ecological_value(
    nodes: List[SkillNode], 
    damping: float = DAMPING_FACTOR
) -> Dict[str, NicheAssessment]:
    """
    Core Algorithm: Calculates the ecological value (PageRank variant) for each SKILL node.
    
    Logic:
    1. Construct the graph based on 'imports'.
    2. Iterate to calculate PageRank (Reference Weight).
       - High Score = Hub/Utility node (critical dependency).
       - Low Score = Leaf/Isolated node.
    3. Assess 'Isolation':
       - Is it a leaf node? (No outgoing dependencies? Or no incoming? 
         Usually leaf in call chain means no one calls it, or it calls nothing.
         Here, 'Isolated' implies low PageRank + Low Direct Usage).
       
    Args:
        nodes: List of SkillNode objects.
        damping: Damping factor for PageRank.
        
    Returns:
        A dictionary mapping Skill ID to NicheAssessment.
        
    Example:
        >>> skills = [
        ...     SkillNode(id="A", imports=["B"], direct_usage_freq=0.1),
        ...     SkillNode(id="B", imports=[], direct_usage_freq=0.0),
        ...     SkillNode(id="C", imports=["B"], direct_usage_freq=0.9)
        ... ]
        >>> results = calculate_ecological_value(skills)
        >>> print(results["B"].verdict) # B should be high value as it supports A and C
    """
    try:
        node_dict, reverse_adj_list = build_dependency_graph(nodes)
        all_ids = list(node_dict.keys())
        n = len(all_ids)
        
        if n == 0:
            return {}

        # Initialize PageRank scores
        pr_scores: Dict[str, float] = {id_: (1.0 / n) for id_ in all_ids}
        
        logger.info(f"Starting PageRank calculation for {n} nodes...")
        
        # PageRank Iteration
        for i in range(MAX_ITERATIONS):
            new_pr_scores: Dict[str, float] = {}
            diff = 0.0
            
            for node_id in all_ids:
                # Get nodes that link to this node (callers)
                incoming_neighbors = reverse_adj_list[node_id]
                
                rank_sum = 0.0
                for neighbor_id in incoming_neighbors:
                    # Out-degree of neighbor = number of imports the neighbor has
                    out_degree = len(node_dict[neighbor_id].imports)
                    if out_degree > 0:
                        rank_sum += pr_scores[neighbor_id] / out_degree
                
                # PageRank formula
                random_jump = (1 - damping) / n
                new_rank = random_jump + (damping * rank_sum)
                
                new_pr_scores[node_id] = new_rank
                diff += abs(new_rank - pr_scores[node_id])
            
            pr_scores = new_pr_scores
            
            if diff < TOLERANCE:
                logger.info(f"Converged after {i+1} iterations.")
                break
        
        # Final Assessment Generation
        assessments: Dict[str, NicheAssessment] = {}
        
        # Normalize scores for easier interpretation (0-1 range roughly, or raw)
        # We will normalize based on max score found for relative value
        max_pr = max(pr_scores.values()) if pr_scores else 1.0
        if max_pr == 0: max_pr = 1.0 # Avoid division by zero

        for node_id, score in pr_scores.items():
            node = node_dict[node_id]
            
            # Determine Leaf/Isolated status
            # Is it a leaf? Definition: It calls no one (no imports) OR nobody calls it (sink).
            # In this context, strictly: "Nobody depends on it" (Sink in dependency graph)
            is_sink = len(reverse_adj_list[node_id]) == 0
            
            # Normalized relative value
            relative_value = score / max_pr
            
            # Isolation Logic:
            # If nobody references it (Sink) AND humans rarely use it directly -> Isolated
            is_isolated = is_sink and (node.direct_usage_freq < 0.1)
            
            # Connectivity Score: Hybrid of structural importance and direct usage
            # Formula: w1 * PR + w2 * DirectUsage
            conn_score = (0.7 * relative_value) + (0.3 * node.direct_usage_freq)
            
            # Verdict Generation
            if is_isolated:
                verdict = "Isolated/Dead Code Candidate"
            elif relative_value > 0.8:
                verdict = "Critical Infrastructure (Hub)"
            elif is_sink and node.direct_usage_freq > 0.5:
                verdict = "High-Value User Endpoint"
            else:
                verdict = "Standard Component"

            assessments[node_id] = NicheAssessment(
                skill_id=node_id,
                pagerank_score=score,
                is_leaf=is_sink,  # Using 'leaf' loosely as sink in dependency flow
                is_isolated=is_isolated,
                connectivity_score=conn_score,
                verdict=verdict
            )
            
        return assessments

    except Exception as e:
        logger.error(f"Error during ecological value calculation: {e}")
        raise

# --- Usage Example ---
if __name__ == "__main__":
    # Create a mock ecosystem
    # A -> B (A calls B)
    # C -> B (C calls B)
    # B -> D (B calls D)
    # E (Standalone, rarely used)
    
    mock_skills = [
        SkillNode(id="user_interface", imports=["auth_logic", "db_connector"], direct_usage_freq=0.9), # High direct use
        SkillNode(id="batch_processor", imports=["db_connector"], direct_usage_freq=0.1), # Background job
        SkillNode(id="auth_logic", imports=["db_connector", "hash_util"], direct_usage_freq=0.0), # Utility, not direct
        SkillNode(id="db_connector", imports=[], direct_usage_freq=0.0), # Core dependency
        SkillNode(id="hash_util", imports=[], direct_usage_freq=0.0), # Core dependency
        SkillNode(id="zombie_code", imports=[], direct_usage_freq=0.0), # Not used by anyone, not by humans
        SkillNode(id="unused_util", imports=["db_connector"], direct_usage_freq=0.0) # References core, but nobody calls it
    ]

    print("--- Running Ecological Niche Assessment ---")
    results = calculate_ecological_value(mock_skills)
    
    # Sort by connectivity score descending
    sorted_results = sorted(results.values(), key=lambda x: x.connectivity_score, reverse=True)
    
    for res in sorted_results:
        print(f"Skill: {res.skill_id:<20} | Score: {res.pagerank_score:.4f} | Verdict: {res.verdict}")