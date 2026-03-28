"""
Module: auto_基于知识图谱拓扑结构的_孤岛节点_与_冗_95cbe8
Description: Implementation of graph topology analysis for identifying isolated and redundant nodes
Author: AGI System
Version: 1.0.0
"""

import logging
from typing import Dict, List, Tuple, Set, Optional, Union
import numpy as np
import networkx as nx
from dataclasses import dataclass
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeAnalysisResult:
    """Container for node analysis results"""
    node_id: str
    pagerank: float
    semantic_density: float
    is_isolated: bool
    is_redundant: bool
    similarity_score: float

class KnowledgeGraphAnalyzer:
    """
    Analyzes knowledge graph topology to identify isolated and redundant nodes.
    
    This class implements algorithms to:
    1. Calculate PageRank values for nodes
    2. Compute semantic density based on node relationships
    3. Identify isolated nodes (low connectivity)
    4. Detect redundant nodes (high semantic overlap)
    
    Attributes:
        graph (nx.DiGraph): Directed graph representing the knowledge graph
        node_embeddings (Dict[str, np.ndarray]): Optional node embeddings for semantic analysis
        alpha (float): Damping factor for PageRank calculation
        similarity_threshold (float): Threshold for considering nodes redundant
    """
    
    def __init__(
        self,
        graph: Optional[nx.DiGraph] = None,
        node_embeddings: Optional[Dict[str, np.ndarray]] = None,
        alpha: float = 0.85,
        similarity_threshold: float = 0.9
    ) -> None:
        """
        Initialize the KnowledgeGraphAnalyzer.
        
        Args:
            graph: NetworkX directed graph representing the knowledge graph
            node_embeddings: Dictionary mapping node IDs to embedding vectors
            alpha: Damping factor for PageRank (default: 0.85)
            similarity_threshold: Threshold for redundancy detection (default: 0.9)
        """
        self.graph = graph if graph is not None else nx.DiGraph()
        self.node_embeddings = node_embeddings if node_embeddings is not None else {}
        self.alpha = alpha
        self.similarity_threshold = similarity_threshold
        
        # Validate inputs
        self._validate_inputs()
        
        logger.info(f"Initialized KnowledgeGraphAnalyzer with {len(self.graph.nodes)} nodes")
    
    def _validate_inputs(self) -> None:
        """Validate input parameters and graph structure."""
        if not isinstance(self.graph, nx.DiGraph):
            raise ValueError("Graph must be a NetworkX DiGraph")
            
        if not 0 < self.alpha < 1:
            raise ValueError("Alpha must be between 0 and 1")
            
        if not 0 < self.similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
            
        if self.node_embeddings:
            missing_nodes = set(self.graph.nodes) - set(self.node_embeddings.keys())
            if missing_nodes:
                logger.warning(f"Missing embeddings for {len(missing_nodes)} nodes")
    
    def calculate_pagerank(
        self,
        max_iter: int = 100,
        tol: float = 1e-6
    ) -> Dict[str, float]:
        """
        Calculate PageRank values for all nodes in the graph.
        
        Args:
            max_iter: Maximum number of iterations for PageRank calculation
            tol: Tolerance for convergence
            
        Returns:
            Dictionary mapping node IDs to PageRank values
            
        Raises:
            ValueError: If graph is empty or has no edges
        """
        if len(self.graph) == 0:
            raise ValueError("Cannot calculate PageRank on empty graph")
            
        if len(self.graph.edges) == 0:
            logger.warning("Graph has no edges, all PageRank values will be equal")
            return {node: 1/len(self.graph) for node in self.graph.nodes}
        
        try:
            pagerank = nx.pagerank(
                self.graph,
                alpha=self.alpha,
                max_iter=max_iter,
                tol=tol
            )
            logger.info("Successfully calculated PageRank values")
            return pagerank
        except nx.PowerIterationFailedConvergence as e:
            logger.error(f"PageRank failed to converge: {str(e)}")
            raise RuntimeError("PageRank calculation failed to converge") from e
    
    def compute_semantic_density(self) -> Dict[str, float]:
        """
        Compute semantic density for each node based on its neighborhood.
        
        Semantic density is calculated as the average cosine similarity between
        a node's embedding and its neighbors' embeddings.
        
        Returns:
            Dictionary mapping node IDs to semantic density scores
            
        Note:
            Nodes without embeddings will have density 0.0
        """
        if not self.node_embeddings:
            logger.warning("No node embeddings provided, returning 0 density for all nodes")
            return {node: 0.0 for node in self.graph.nodes}
        
        density_scores = {}
        
        for node in self.graph.nodes:
            if node not in self.node_embeddings:
                density_scores[node] = 0.0
                continue
                
            neighbors = set(self.graph.predecessors(node)) | set(self.graph.successors(node))
            if not neighbors:
                density_scores[node] = 0.0
                continue
                
            node_embedding = self.node_embeddings[node]
            similarities = []
            
            for neighbor in neighbors:
                if neighbor in self.node_embeddings:
                    neighbor_embedding = self.node_embeddings[neighbor]
                    similarity = self._cosine_similarity(node_embedding, neighbor_embedding)
                    similarities.append(similarity)
            
            density_scores[node] = np.mean(similarities) if similarities else 0.0
        
        logger.info("Calculated semantic density for all nodes")
        return density_scores
    
    def _cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        if vec1.shape != vec2.shape:
            raise ValueError("Vectors must have the same dimension")
            
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def identify_isolated_nodes(
        self,
        pagerank_threshold: float = 0.0001
    ) -> Set[str]:
        """
        Identify isolated nodes based on PageRank and connectivity.
        
        Args:
            pagerank_threshold: Minimum PageRank value to consider a node non-isolated
            
        Returns:
            Set of node IDs identified as isolated
        """
        if len(self.graph) == 0:
            return set()
            
        pagerank = self.calculate_pagerank()
        isolated_nodes = set()
        
        for node, score in pagerank.items():
            in_degree = self.graph.in_degree(node)
            out_degree = self.graph.out_degree(node)
            
            if (score < pagerank_threshold and 
                in_degree == 0 and 
                out_degree == 0):
                isolated_nodes.add(node)
        
        logger.info(f"Identified {len(isolated_nodes)} isolated nodes")
        return isolated_nodes
    
    def identify_redundant_nodes(
        self,
        density_threshold: float = 0.85
    ) -> Set[str]:
        """
        Identify redundant nodes based on semantic density and similarity.
        
        Args:
            density_threshold: Minimum semantic density to consider a node redundant
            
        Returns:
            Set of node IDs identified as redundant
        """
        if not self.node_embeddings:
            logger.warning("Cannot identify redundant nodes without embeddings")
            return set()
            
        density = self.compute_semantic_density()
        redundant_nodes = set()
        
        # Group nodes by high density
        high_density_nodes = [
            node for node, score in density.items() 
            if score > density_threshold
        ]
        
        # Check pairwise similarity within high density nodes
        for i, node1 in enumerate(high_density_nodes):
            if node1 in redundant_nodes:
                continue
                
            for node2 in high_density_nodes[i+1:]:
                if node2 in redundant_nodes:
                    continue
                    
                similarity = self._cosine_similarity(
                    self.node_embeddings[node1],
                    self.node_embeddings[node2]
                )
                
                if similarity > self.similarity_threshold:
                    # Mark the node with lower PageRank as redundant
                    pr1 = self.graph.nodes[node1].get('pagerank', 0)
                    pr2 = self.graph.nodes[node2].get('pagerank', 0)
                    redundant_nodes.add(node1 if pr1 < pr2 else node2)
        
        logger.info(f"Identified {len(redundant_nodes)} redundant nodes")
        return redundant_nodes
    
    def analyze_graph(
        self,
        pagerank_threshold: float = 0.0001,
        density_threshold: float = 0.85
    ) -> Dict[str, NodeAnalysisResult]:
        """
        Perform complete graph analysis to identify isolated and redundant nodes.
        
        Args:
            pagerank_threshold: Threshold for isolated node detection
            density_threshold: Threshold for redundant node detection
            
        Returns:
            Dictionary mapping node IDs to their analysis results
        """
        if len(self.graph) == 0:
            logger.warning("Analyzing empty graph")
            return {}
        
        # Calculate metrics
        pagerank = self.calculate_pagerank()
        density = self.compute_semantic_density()
        isolated_nodes = self.identify_isolated_nodes(pagerank_threshold)
        redundant_nodes = self.identify_redundant_nodes(density_threshold)
        
        # Compile results
        results = {}
        for node in self.graph.nodes:
            results[node] = NodeAnalysisResult(
                node_id=node,
                pagerank=pagerank.get(node, 0.0),
                semantic_density=density.get(node, 0.0),
                is_isolated=node in isolated_nodes,
                is_redundant=node in redundant_nodes,
                similarity_score=0.0  # Will be populated if redundant
            )
        
        # Add similarity scores for redundant nodes
        for node in redundant_nodes:
            neighbors = set(self.graph.predecessors(node)) | set(self.graph.successors(node))
            if neighbors:
                similarities = [
                    self._cosine_similarity(
                        self.node_embeddings[node],
                        self.node_embeddings[n]
                    )
                    for n in neighbors
                    if n in self.node_embeddings
                ]
                results[node].similarity_score = np.max(similarities) if similarities else 0.0
        
        logger.info("Completed full graph analysis")
        return results

def example_usage():
    """
    Example usage of the KnowledgeGraphAnalyzer.
    
    This example demonstrates:
    1. Creating a sample knowledge graph
    2. Initializing the analyzer
    3. Performing graph analysis
    4. Accessing the results
    """
    # Create a sample knowledge graph
    graph = nx.DiGraph()
    graph.add_nodes_from(range(1, 28))  # 27 nodes for demonstration
    
    # Add some edges (representing citation relationships)
    edges = [
        (1, 2), (2, 3), (3, 4), (4, 5),  # Chain
        (1, 6), (6, 7), (7, 8),  # Branch
        (9, 10), (10, 11), (11, 9),  # Cycle
        (12, 13), (13, 14), (14, 15), (15, 16),  # Another chain
        (17, 18), (18, 19), (19, 20),  # Small chain
        (21, 22), (22, 23), (23, 24), (24, 25), (25, 26), (26, 27),  # Long chain
        (5, 9), (8, 12), (11, 17), (16, 21)  # Cross connections
    ]
    graph.add_edges_from(edges)
    
    # Add some isolated nodes
    graph.add_nodes_from([28, 29, 30])
    
    # Create random embeddings for demonstration
    node_embeddings = {
        str(node): np.random.rand(128) for node in graph.nodes
    }
    
    # Make some nodes very similar to demonstrate redundancy
    node_embeddings['2'] = node_embeddings['3'] * 0.95 + np.random.rand(128) * 0.05
    node_embeddings['4'] = node_embeddings['5'] * 0.92 + np.random.rand(128) * 0.08
    
    # Initialize analyzer
    analyzer = KnowledgeGraphAnalyzer(
        graph=graph,
        node_embeddings=node_embeddings,
        alpha=0.85,
        similarity_threshold=0.9
    )
    
    # Perform analysis
    results = analyzer.analyze_graph()
    
    # Print some results
    print("\nAnalysis Results:")
    print(f"{'Node':<6} {'PageRank':<10} {'Density':<8} {'Isolated':<8} {'Redundant':<8} {'Similarity':<8}")
    for node, result in results.items():
        print(f"{node:<6} {result.pagerank:.6f}  {result.semantic_density:.4f}  "
              f"{str(result.is_isolated):<8} {str(result.is_redundant):<8} "
              f"{result.similarity_score:.4f}")

if __name__ == "__main__":
    example_usage()