"""
Module: semantic_overlap_detector.py

This module implements a high-level semantic overlap detection algorithm
designed for heterogeneous cross-domain nodes. It facilitates "Left-Right
Cross-Domain Overlap" for computational creativity.

The core capability involves aligning nodes from vastly different domains
(e.g., 'Street Vendor Inventory' and 'JIT Lean Manufacturing') in a shared
vector space, identifying structural similarities in abstract dimensions
(e.g., 'Resource Turnover'), and generating novel concept connections
(e.g., 'Micro-JIT') rather than simple keyword matches.

Dependencies:
    - numpy
    - sklearn
    - logging (standard)
    - dataclasses (standard)
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticOverlapDetector")


@dataclass
class SemanticNode:
    """
    Represents a heterogeneous node in the knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        domain: The domain the node belongs to (e.g., 'Retail', 'Manufacturing').
        content: The text or raw content of the node.
        embedding: High-dimensional vector representation of the content.
        structured_features: Dictionary of numerical features representing
                             abstract dimensions (e.g., {'turnover_rate': 0.9}).
    """
    id: str
    domain: str
    content: str
    embedding: Optional[np.ndarray] = None
    structured_features: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConceptConnection:
    """
    Represents a newly generated connection between two nodes.
    """
    source_id: str
    target_id: str
    similarity_score: float
    overlap_dimensions: List[str]
    generated_concept: str
    reasoning: str


class VectorSpaceAligner:
    """
    Handles the alignment of heterogeneous nodes into a unified vector space.
    """
    
    def __init__(self, feature_dims: List[str]):
        """
        Initialize the aligner.
        
        Args:
            feature_dims: A list of feature keys expected in the structured features.
        """
        self.feature_dims = feature_dims
        self.scaler = StandardScaler()
        self._is_fitted = False
        logger.info(f"VectorSpaceAligner initialized for dimensions: {feature_dims}")

    def _validate_node(self, node: SemanticNode) -> bool:
        """Validates that the node contains the required structured features."""
        if not isinstance(node, SemanticNode):
            raise TypeError(f"Expected SemanticNode, got {type(node)}")
        
        missing_dims = [d for d in self.feature_dims if d not in node.structured_features]
        if missing_dims:
            logger.warning(f"Node {node.id} missing dimensions: {missing_dims}")
            return False
        return True

    def fit_transform(self, nodes: List[SemanticNode]) -> np.ndarray:
        """
        Extracts, validates, and normalizes structured features to create
        a domain-agnostic structural matrix.
        
        Args:
            nodes: List of SemanticNodes.
            
        Returns:
            A normalized numpy matrix of shape (n_nodes, n_features).
        """
        logger.info(f"Aligning vector space for {len(nodes)} nodes...")
        
        valid_nodes = [n for n in nodes if self._validate_node(n)]
        if len(valid_nodes) < len(nodes):
            logger.warning(f"Skipped {len(nodes) - len(valid_nodes)} invalid nodes.")

        if not valid_nodes:
            raise ValueError("No valid nodes provided for alignment.")

        # Extract feature matrix
        feature_matrix = np.array([
            [n.structured_features[d] for d in self.feature_dims] 
            for n in valid_nodes
        ])
        
        # Handle NaN values
        if np.isnan(feature_matrix).any():
            logger.warning("NaN values detected in features. Imputing with column means.")
            col_means = np.nanmean(feature_matrix, axis=0)
            nan_indices = np.where(np.isnan(feature_matrix))
            feature_matrix[nan_indices] = np.take(col_means, nan_indices[1])

        normalized_matrix = self.scaler.fit_transform(feature_matrix)
        self._is_fitted = True
        logger.info("Vector space alignment complete.")
        
        return normalized_matrix


def generate_novel_concept(node_a: SemanticNode, node_b: SemanticNode, dim: str) -> str:
    """
    Helper function to generate a creative concept name based on overlap.
    (In a real AGI system, this would call an LLM).
    
    Args:
        node_a: First node.
        node_b: Second node.
        dim: The dimension of overlap.
        
    Returns:
        A generated concept string.
    """
    # Simulated logic for creative naming
    prefix = node_a.content.split()[0] # Simplified extraction
    suffix = "".join(node_b.content.split()[1:]) # Simplified extraction
    
    # Logic to simulate 'Micro-JIT' generation
    if "small" in node_a.content.lower() or "vendor" in node_a.content.lower():
        prefix = "Micro"
    if "jit" in node_b.content.lower() or "lean" in node_b.content.lower():
        suffix = "JIT"
        
    return f"{prefix}-{suffix} ({dim} synergy)"


class CrossDomainDetector:
    """
    Main class for detecting semantic overlaps and generating concept connections.
    """

    def __init__(self, aligner: VectorSpaceAligner, similarity_threshold: float = 0.85):
        """
        Initialize the detector.
        
        Args:
            aligner: An instance of VectorSpaceAligner.
            similarity_threshold: Threshold for considering two nodes semantically overlapped.
        """
        if not isinstance(aligner, VectorSpaceAligner):
            raise TypeError("Invalid aligner provided.")
            
        self.aligner = aligner
        self.threshold = similarity_threshold
        logger.info(f"CrossDomainDetector initialized with threshold {similarity_threshold}")

    def detect_overlap(self, nodes: List[SemanticNode]) -> List[ConceptConnection]:
        """
        Executes the semantic overlap detection algorithm.
        
        Steps:
        1. Align nodes in vector space.
        2. Compute pairwise cosine similarity.
        3. Identify cross-domain pairs exceeding the threshold.
        4. Generate novel concept connections.
        
        Args:
            nodes: List of SemanticNodes to process.
            
        Returns:
            A list of ConceptConnection objects.
        """
        if len(nodes) < 2:
            logger.error("Insufficient nodes for comparison.")
            return []

        # 1. Structural Alignment
        try:
            struct_matrix = self.aligner.fit_transform(nodes)
        except ValueError as e:
            logger.error(f"Alignment failed: {e}")
            return []

        # 2. Semantic Similarity Calculation (using structural vectors)
        # Here we focus on structural similarity which reveals deep functional overlaps
        sim_matrix = cosine_similarity(struct_matrix)
        
        connections = []
        
        # 3. Find Pairs
        # Iterate upper triangle of similarity matrix
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                node_a = nodes[i]
                node_b = nodes[j]
                score = sim_matrix[i, j]
                
                # Ensure Cross-Domain (Heterogeneous)
                if node_a.domain == node_b.domain:
                    continue
                    
                if score >= self.threshold:
                    logger.info(f"Overlap detected: '{node_a.content}' <-> '{node_b.content}' (Score: {score:.4f})")
                    
                    # Find contributing dimensions (simplified logic)
                    overlap_dims = self._identify_overlap_dimensions(node_a, node_b)
                    
                    # 4. Generate Connection
                    concept = generate_novel_concept(node_a, node_b, overlap_dims[0])
                    
                    connection = ConceptConnection(
                        source_id=node_a.id,
                        target_id=node_b.id,
                        similarity_score=float(score),
                        overlap_dimensions=overlap_dims,
                        generated_concept=concept,
                        reasoning=f"Structural alignment in dimensions {overlap_dims} suggests functional equivalence."
                    )
                    connections.append(connection)
                    
        return connections

    def _identify_overlap_dimensions(self, node_a: SemanticNode, node_b: SemanticNode) -> List[str]:
        """
        Identifies which specific dimensions contribute most to the similarity.
        """
        overlaps = []
        for dim in self.aligner.feature_dims:
            val_a = node_a.structured_features.get(dim, 0)
            val_b = node_b.structured_features.get(dim, 0)
            
            # Simple relative difference check
            if val_a != 0 and val_b != 0:
                diff = abs(val_a - val_b) / max(abs(val_a), abs(val_b))
                if diff < 0.2: # Within 20% difference
                    overlaps.append(dim)
        return overlaps if overlaps else ["general"]


# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Define the structural dimensions we care about
    dimensions = ["turnover_rate", "inventory_volatility", "resource_efficiency", "responsiveness"]
    
    # 2. Create Heterogeneous Nodes
    # Node A: Street Vendor (High volatility, High turnover)
    vendor_node = SemanticNode(
        id="node_001",
        domain="Micro_Retail",
        content="Small Street Vendor Inventory",
        embedding=np.random.rand(768), # Placeholder for semantic embedding
        structured_features={
            "turnover_rate": 0.95,      # Very high (daily)
            "inventory_volatility": 0.9, # Unpredictable demand
            "resource_efficiency": 0.6,  # Low tech
            "responsiveness": 0.99       # Immediate customer feedback
        }
    )
    
    # Node B: Toyota-style JIT (High efficiency, High turnover)
    jit_node = SemanticNode(
        id="node_002",
        domain="Manufacturing",
        content="JIT Lean Production System",
        embedding=np.random.rand(768),
        structured_features={
            "turnover_rate": 0.90,      # High (reduced holding)
            "inventory_volatility": 0.1, # Controlled/Kanban
            "resource_efficiency": 0.95, # Optimized
            "responsiveness": 0.85       # Pull system
        }
    )
    
    # Node C: Bulk Warehouse (Low turnover, different logic)
    warehouse_node = SemanticNode(
        id="node_003",
        domain="Logistics",
        content="Bulk Warehousing",
        embedding=np.random.rand(768),
        structured_features={
            "turnover_rate": 0.2,
            "inventory_volatility": 0.3,
            "resource_efficiency": 0.7,
            "responsiveness": 0.4
        }
    )

    nodes_list = [vendor_node, jit_node, warehouse_node]
    
    # 3. Initialize System
    aligner = VectorSpaceAligner(feature_dims=dimensions)
    detector = CrossDomainDetector(aligner, similarity_threshold=0.8)
    
    # 4. Run Detection
    logger.info("Starting Semantic Overlap Detection...")
    results = detector.detect_overlap(nodes_list)
    
    # 5. Output Results
    print("\n" + "="*50)
    print(f"Detected {len(results)} Novel Connections:")
    print("="*50)
    
    for conn in results:
        print(f"Source: {conn.source_id} | Target: {conn.target_id}")
        print(f"Score: {conn.similarity_score:.4f}")
        print(f"Overlaps: {conn.overlap_dimensions}")
        print(f"New Concept: {conn.generated_concept}")
        print(f"Reasoning: {conn.reasoning}")
        print("-" * 30)