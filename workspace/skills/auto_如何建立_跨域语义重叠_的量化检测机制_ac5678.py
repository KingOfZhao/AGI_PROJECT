"""
Module: auto_cross_domain_semantic_overlap_ac5678

Description:
    This module implements a quantitative detection mechanism for 'Cross-Domain Semantic Overlap'.
    It aims to identify latent cognitive isomorphism between nodes from different domains
    (e.g., 'Recursion in Programming' vs 'Hierarchical Feedback in Management') by analyzing
    their vector representations.

    The core algorithm calculates semantic similarity and isolates high-potential
    cross-domain connections, effectively linking isolated knowledge silos.

Key Features:
    - Vector-based semantic similarity calculation.
    - Domain isolation to ensure 'Cross-Domain' validity.
    - Configurable thresholding for overlap detection.
    - Robust error handling and logging.

Author: AGI System Core Engineering
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents a single node in the knowledge graph.
    
    Attributes:
        id (str): Unique identifier for the node.
        domain (str): The domain the node belongs to (e.g., 'cs', 'management').
        content (str): Textual description of the concept.
        embedding (Optional[np.ndarray]): Vector representation of the content.
    """
    id: str
    domain: str
    content: str
    embedding: Optional[np.ndarray] = None

@dataclass
class OverlapResult:
    """
    Represents a detected semantic overlap between two nodes.
    
    Attributes:
        source_id (str): ID of the source node.
        target_id (str): ID of the target node.
        score (float): The semantic similarity score (0.0 to 1.0).
        is_isomorphic (bool): True if score exceeds the threshold.
    """
    source_id: str
    target_id: str
    score: float
    is_isomorphic: bool

# --- Helper Functions ---

def _validate_embeddings(nodes: List[KnowledgeNode]) -> bool:
    """
    Validates that all nodes have valid, consistent embedding vectors.
    
    Args:
        nodes (List[KnowledgeNode]): List of nodes to validate.
        
    Returns:
        bool: True if validation passes.
        
    Raises:
        ValueError: If embeddings are missing or dimensions mismatch.
    """
    if not nodes:
        raise ValueError("Node list cannot be empty.")
    
    reference_dim = None
    for node in nodes:
        if node.embedding is None:
            logger.error(f"Node {node.id} is missing embedding data.")
            raise ValueError(f"Node {node.id} has no embedding.")
        
        if not isinstance(node.embedding, np.ndarray):
            logger.error(f"Node {node.id} embedding is not a numpy array.")
            raise TypeError(f"Embedding for {node.id} must be a numpy array.")
            
        if reference_dim is None:
            reference_dim = node.embedding.shape
        elif node.embedding.shape != reference_dim:
            logger.error(f"Dimension mismatch for node {node.id}.")
            raise ValueError("All node embeddings must have the same dimensions.")
            
    logger.info("Embedding validation successful.")
    return True

def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculates the cosine similarity between two vectors.
    Range: [-1, 1]. 1 indicates perfect alignment.
    
    Args:
        vec_a (np.ndarray): First vector.
        vec_b (np.ndarray): Second vector.
        
    Returns:
        float: Cosine similarity score.
    """
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

# --- Core Functions ---

def generate_cross_domain_pairs(
    nodes: List[KnowledgeNode], 
    target_domain_filter: Optional[List[str]] = None
) -> List[Tuple[KnowledgeNode, KnowledgeNode]]:
    """
    Generates candidate pairs of nodes belonging to different domains.
    
    Args:
        nodes (List[KnowledgeNode]): The complete list of knowledge nodes.
        target_domain_filter (Optional[List[str]]): If provided, only pairs where 
            the target node is in these domains will be generated.
            
    Returns:
        List[Tuple[KnowledgeNode, KnowledgeNode]]: A list of candidate node pairs.
    """
    pairs = []
    logger.info(f"Generating pairs for {len(nodes)} nodes...")
    
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i+1:]:
            # Ensure strict cross-domain comparison
            if node_a.domain != node_b.domain:
                # Apply filter if present
                if target_domain_filter:
                    if node_b.domain not in target_domain_filter and node_a.domain not in target_domain_filter:
                        continue
                        
                pairs.append((node_a, node_b))
                
    logger.info(f"Generated {len(pairs)} cross-domain candidate pairs.")
    return pairs

def calculate_semantic_overlaps(
    nodes: List[KnowledgeNode],
    threshold: float = 0.75,
    target_domains: Optional[List[str]] = None
) -> List[OverlapResult]:
    """
    Main detection mechanism. Computes semantic overlap scores for cross-domain nodes
    and identifies cognitive isomorphisms based on the threshold.
    
    Args:
        nodes (List[KnowledgeNode]): List of nodes with embeddings.
        threshold (float): The similarity score above which nodes are considered 
                           cognitively isomorphic (default: 0.75).
        target_domains (Optional[List[str]]): Domains to specifically target for overlap.
        
    Returns:
        List[OverlapResult]: A list of detected overlaps.
        
    Example:
        >>> nodes = [
        ...     KnowledgeNode("1", "cs", "Recursion", np.array([0.9, 0.1])),
        ...     KnowledgeNode("2", "mgmt", "Feedback Loop", np.array([0.85, 0.15]))
        ... ]
        >>> results = calculate_semantic_overlaps(nodes, threshold=0.8)
    """
    try:
        # 1. Data Validation
        logger.info("Starting Cross-Domain Semantic Overlap Detection...")
        _validate_embeddings(nodes)
        
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0.")

        # 2. Candidate Generation
        candidate_pairs = generate_cross_domain_pairs(nodes, target_domains)
        
        if not candidate_pairs:
            logger.warning("No cross-domain pairs found to analyze.")
            return []

        # 3. Quantification & Detection
        results = []
        for node_a, node_b in candidate_pairs:
            score = _cosine_similarity(node_a.embedding, node_b.embedding)
            
            # Logical check for isomorphism
            is_iso = score >= threshold
            
            if is_iso:
                logger.debug(f"Isomorphism detected: {node_a.id} <-> {node_b.id} (Score: {score:.4f})")
            
            result = OverlapResult(
                source_id=node_a.id,
                target_id=node_b.id,
                score=score,
                is_isomorphic=is_iso
            )
            results.append(result)
            
        logger.info(f"Detection complete. Found {sum(1 for r in results if r.is_isomorphic)} isomorphic pairs.")
        return results

    except Exception as e:
        logger.exception(f"Critical failure in overlap calculation: {e}")
        raise

# --- Main Execution (Example) ---

if __name__ == "__main__":
    # Mock Data Setup for Demonstration
    # Simulating a subset of the 2704 nodes system
    mock_nodes = [
        KnowledgeNode(
            id="cs_101", 
            domain="programming", 
            content="Recursion: A function calling itself.", 
            embedding=np.array([0.8, 0.2, 0.1])
        ),
        KnowledgeNode(
            id="math_202", 
            domain="mathematics", 
            content="Fractals: Self-similarity at different scales.", 
            embedding=np.array([0.75, 0.25, 0.1]) # High similarity
        ),
        KnowledgeNode(
            id="mgmt_305", 
            domain="management", 
            content="Hierarchical Feedback: Layers of reporting.", 
            embedding=np.array([0.78, 0.22, 0.15]) # High similarity
        ),
        KnowledgeNode(
            id="bio_404", 
            domain="biology", 
            content="Cellular Mitosis: Cell division.", 
            embedding=np.array([0.1, 0.9, 0.3]) # Low similarity
        )
    ]

    print("-" * 60)
    print("Executing Cross-Domain Semantic Overlap Detection")
    print("-" * 60)

    try:
        # Run the detection mechanism with a 0.7 threshold
        overlap_results = calculate_semantic_overlaps(
            nodes=mock_nodes, 
            threshold=0.7
        )

        print(f"\n{'Source':<10} | {'Target':<10} | {'Score':<6} | {'Isomorphic'}")
        print("-" * 50)
        
        for res in overlap_results:
            print(f"{res.source_id:<10} | {res.target_id:<10} | {res.score:.4f} | {res.is_isomorphic}")
            
    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except Exception as e:
        print(f"Unexpected Error: {e}")