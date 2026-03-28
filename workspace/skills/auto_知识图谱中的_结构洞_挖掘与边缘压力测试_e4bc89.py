"""
Advanced Knowledge Graph Structural Hole Mining & Edge Stress Testing Module.

This module implements algorithms to detect structural holes (weak connections)
in knowledge graphs and generate exploratory hypotheses for edge pressure testing.
Designed for AGI systems to validate knowledge network completeness.

Author: AGI Systems Engineer
Version: 1.0.0
"""

import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge graph with associated metadata."""
    node_id: str
    node_type: str
    description: str
    embedding: Optional[List[float]] = field(default=None)
    
    def __post_init__(self):
        """Validate node data after initialization."""
        if not self.node_id or not isinstance(self.node_id, str):
            raise ValueError("node_id must be a non-empty string")
        if not self.node_type:
            raise ValueError("node_type is required")


@dataclass
class ExploratoryHypothesis:
    """Represents a generated hypothesis for structural hole testing."""
    source_node: str
    target_node: str
    bridge_score: float
    hypothesis_text: str
    risk_level: str  # 'low', 'medium', 'high'
    expected_reward: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert hypothesis to dictionary format."""
        return {
            'source': self.source_node,
            'target': self.target_node,
            'bridge_score': self.bridge_score,
            'hypothesis': self.hypothesis_text,
            'risk': self.risk_level,
            'reward': self.expected_reward
        }


class KnowledgeGraphMiner:
    """
    Main class for mining structural holes in knowledge graphs.
    
    Implements graph traversal algorithms to identify weak connection points
    and generate testable hypotheses for knowledge validation.
    
    Example:
        >>> miner = KnowledgeGraphMiner()
        >>> miner.load_graph("knowledge_db.json")
        >>> holes = miner.detect_structural_holes()
        >>> hypotheses = miner.generate_hypotheses(holes)
    """
    
    def __init__(self, min_bridge_score: float = 0.3, max_workers: int = 4):
        """
        Initialize the knowledge graph miner.
        
        Args:
            min_bridge_score: Minimum score threshold for structural holes
            max_workers: Number of parallel workers for computation
        """
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)
        self.min_bridge_score = min_bridge_score
        self.max_workers = max_workers
        self._node_embeddings: Dict[str, List[float]] = {}
        
        logger.info(f"Initialized KnowledgeGraphMiner with min_bridge_score={min_bridge_score}")
    
    def load_graph(self, graph_data: Dict) -> bool:
        """
        Load knowledge graph from dictionary data.
        
        Args:
            graph_data: Dictionary containing 'nodes' and 'edges' lists
            
        Returns:
            bool: True if loading successful
            
        Raises:
            ValueError: If data format is invalid
        """
        if not isinstance(graph_data, dict):
            raise ValueError("graph_data must be a dictionary")
        
        if 'nodes' not in graph_data or 'edges' not in graph_data:
            raise ValueError("graph_data must contain 'nodes' and 'edges' keys")
        
        try:
            # Load nodes
            for node_data in graph_data['nodes']:
                node = KnowledgeNode(**node_data)
                self.nodes[node.node_id] = node
                if node.embedding:
                    self._node_embeddings[node.node_id] = node.embedding
            
            # Load edges
            for edge in graph_data['edges']:
                if len(edge) != 2:
                    logger.warning(f"Invalid edge format: {edge}")
                    continue
                source, target = edge
                if source in self.nodes and target in self.nodes:
                    self.edges[source].add(target)
                    self.edges[target].add(source)  # Undirected graph
                else:
                    logger.warning(f"Edge contains unknown node: {edge}")
            
            logger.info(f"Loaded {len(self.nodes)} nodes and {sum(len(v) for v in self.edges.values())//2} edges")
            return True
            
        except Exception as e:
            logger.error(f"Error loading graph: {str(e)}")
            raise
    
    def detect_structural_holes(self, top_k: int = 10) -> List[Tuple[str, str, float]]:
        """
        Detect structural holes in the knowledge graph using bridge score analysis.
        
        This algorithm identifies node pairs that:
        1. Are not directly connected
        2. Share few common neighbors
        3. Have potential semantic similarity
        
        Args:
            top_k: Number of top structural holes to return
            
        Returns:
            List of tuples (source_id, target_id, bridge_score)
            
        Raises:
            RuntimeError: If graph is empty
        """
        if not self.nodes:
            raise RuntimeError("Graph is empty. Load data first.")
        
        logger.info("Starting structural hole detection...")
        structural_holes = []
        
        # Get all node pairs
        node_ids = list(self.nodes.keys())
        total_pairs = len(node_ids) * (len(node_ids) - 1) // 2
        processed = 0
        
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                node_a, node_b = node_ids[i], node_ids[j]
                
                # Skip if already connected
                if node_b in self.edges[node_a]:
                    processed += 1
                    continue
                
                # Calculate bridge score
                score = self._calculate_bridge_score(node_a, node_b)
                
                if score >= self.min_bridge_score:
                    structural_holes.append((node_a, node_b, score))
                
                processed += 1
                if processed % 1000 == 0:
                    logger.debug(f"Processed {processed}/{total_pairs} pairs")
        
        # Sort by score and return top_k
        structural_holes.sort(key=lambda x: x[2], reverse=True)
        result = structural_holes[:top_k]
        
        logger.info(f"Found {len(structural_holes)} structural holes, returning top {top_k}")
        return result
    
    def generate_hypotheses(
        self, 
        structural_holes: List[Tuple[str, str, float]],
        hypothesis_templates: Optional[List[str]] = None
    ) -> List[ExploratoryHypothesis]:
        """
        Generate exploratory hypotheses for detected structural holes.
        
        Args:
            structural_holes: List of structural holes from detect_structural_holes
            hypothesis_templates: Custom templates for hypothesis generation
            
        Returns:
            List of ExploratoryHypothesis objects
            
        Raises:
            ValueError: If structural_holes is empty
        """
        if not structural_holes:
            raise ValueError("structural_holes cannot be empty")
        
        default_templates = [
            "There exists an implicit relationship between {a} and {b} that is not captured in current knowledge",
            "The interaction between {a} and {b} may reveal emergent properties",
            "{a} could potentially influence {b} through indirect pathways",
            "Combining {a} with {b} might produce novel capabilities"
        ]
        
        templates = hypothesis_templates or default_templates
        hypotheses = []
        
        for source, target, score in structural_holes:
            # Determine risk level based on score
            if score > 0.8:
                risk = "high"
                reward = 0.9
            elif score > 0.5:
                risk = "medium"
                reward = 0.6
            else:
                risk = "low"
                reward = 0.3
            
            # Generate hypothesis text
            template = random.choice(templates)
            hypothesis_text = template.format(
                a=self.nodes[source].description,
                b=self.nodes[target].description
            )
            
            hypothesis = ExploratoryHypothesis(
                source_node=source,
                target_node=target,
                bridge_score=score,
                hypothesis_text=hypothesis_text,
                risk_level=risk,
                expected_reward=reward
            )
            
            hypotheses.append(hypothesis)
            logger.debug(f"Generated hypothesis: {hypothesis_text[:50]}...")
        
        logger.info(f"Generated {len(hypotheses)} exploratory hypotheses")
        return hypotheses
    
    def _calculate_bridge_score(self, node_a: str, node_b: str) -> float:
        """
        Calculate bridge score between two non-connected nodes.
        
        Bridge score is based on:
        1. Common neighbors ratio
        2. Path length (if exists)
        3. Semantic similarity (if embeddings available)
        
        Args:
            node_a: First node ID
            node_b: Second node ID
            
        Returns:
            float: Bridge score between 0 and 1
        """
        # Common neighbors component
        neighbors_a = self.edges[node_a]
        neighbors_b = self.edges[node_b]
        common = neighbors_a & neighbors_b
        union = neighbors_a | neighbors_b
        
        if not union:
            jaccard = 0.0
        else:
            jaccard = len(common) / len(union)
        
        # Shortest path component (BFS limited to depth 3)
        path_length = self._find_shortest_path_length(node_a, node_b, max_depth=3)
        path_score = 1.0 / (path_length + 1) if path_length > 0 else 0.0
        
        # Embedding similarity component
        emb_score = 0.0
        if self._node_embeddings:
            emb_a = self._node_embeddings.get(node_a)
            emb_b = self._node_embeddings.get(node_b)
            if emb_a and emb_b:
                emb_score = self._cosine_similarity(emb_a, emb_b)
        
        # Weighted combination
        bridge_score = 0.4 * jaccard + 0.3 * path_score + 0.3 * emb_score
        return round(bridge_score, 4)
    
    def _find_shortest_path_length(self, start: str, end: str, max_depth: int = 3) -> int:
        """
        Find shortest path length between two nodes using BFS.
        
        Args:
            start: Starting node ID
            end: Target node ID
            max_depth: Maximum search depth
            
        Returns:
            int: Path length or -1 if not found within max_depth
        """
        if start == end:
            return 0
        
        visited = {start}
        queue = [(start, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            for neighbor in self.edges[current]:
                if neighbor == end:
                    return depth + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        
        return -1
    
    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a ** 2 for a in vec_a) ** 0.5
        norm_b = sum(b ** 2 for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# Example usage
if __name__ == "__main__":
    # Sample knowledge graph data
    sample_graph = {
        "nodes": [
            {"node_id": "skill_1", "node_type": "skill", "description": "Natural Language Processing"},
            {"node_id": "skill_2", "node_type": "skill", "description": "Computer Vision"},
            {"node_id": "skill_3", "node_type": "skill", "description": "Reinforcement Learning"},
            {"node_id": "skill_4", "node_type": "skill", "description": "Knowledge Representation"},
            {"node_id": "skill_5", "node_type": "skill", "description": "Robotics"},
        ],
        "edges": [
            ["skill_1", "skill_3"],
            ["skill_2", "skill_3"],
            ["skill_4", "skill_1"],
            ["skill_5", "skill_2"],
            # Note: No direct connection between skill_1 and skill_2 (structural hole)
        ]
    }
    
    # Initialize miner and load graph
    miner = KnowledgeGraphMiner(min_bridge_score=0.2)
    miner.load_graph(sample_graph)
    
    # Detect structural holes
    holes = miner.detect_structural_holes(top_k=5)
    print(f"\nDetected {len(holes)} structural holes:")
    for src, tgt, score in holes:
        print(f"  {src} -> {tgt}: {score:.3f}")
    
    # Generate hypotheses
    hypotheses = miner.generate_hypotheses(holes)
    print("\nGenerated Hypotheses:")
    for hyp in hypotheses:
        print(f"[{hyp.risk_level.upper()}] {hyp.hypothesis_text}")
        print(f"  Expected reward: {hyp.expected_reward:.2f}\n")