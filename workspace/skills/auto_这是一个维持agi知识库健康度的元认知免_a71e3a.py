"""
AGI Meta-Cognitive Immune System Module.

This module implements a knowledge base health maintenance system mimicking biological 
metabolism. It manages the lifecycle of knowledge nodes through activity decay algorithms,
topological robustness analysis, and cognitive parasite detection.

Features:
- Dynamic knowledge node lifecycle management
- Activity decay calculation based on multiple factors
- Graph topology robustness analysis
- Cognitive parasite identification
- Automatic knowledge base pruning and optimization

Typical usage example:
    kb = KnowledgeBase()
    immune_system = MetaCognitiveImmuneSystem(kb)
    immune_system.run_maintenance_cycle()
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum, auto
import networkx as nx
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_ImmuneSystem")


class NodeHealth(Enum):
    """Enumeration of knowledge node health states."""
    HEALTHY = auto()
    DECAYING = auto()
    CRITICAL = auto()
    PARASITIC = auto()


@dataclass
class KnowledgeNode:
    """Represents a single unit of knowledge in the AGI system.
    
    Attributes:
        id: Unique identifier for the node
        content: The actual knowledge content
        created_at: Timestamp of node creation
        last_accessed: Timestamp of last access
        access_count: Number of times this node has been accessed
        verification_score: Score from practical verification (0-1)
        references: List of node IDs this node references
        metadata: Additional node metadata
    """
    id: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    verification_score: float = 0.5
    references: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate node data after initialization."""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Node ID must be a non-empty string")
        if self.verification_score < 0 or self.verification_score > 1:
            raise ValueError("Verification score must be between 0 and 1")


class MetaCognitiveImmuneSystem:
    """Maintains knowledge base health through metabolic processes.
    
    This system implements:
    - Activity decay calculation for knowledge nodes
    - Graph topology analysis for structural integrity
    - Cognitive parasite detection
    - Automated knowledge base pruning
    
    Attributes:
        knowledge_base: The knowledge graph to maintain
        decay_rate: Base decay rate for knowledge nodes
        half_life_threshold: Threshold for node removal
        structural_protection: Set of protected structural nodes
    """
    
    def __init__(
        self,
        knowledge_base: nx.DiGraph,
        decay_rate: float = 0.1,
        half_life_threshold: float = 0.2
    ):
        """Initialize the immune system with a knowledge base.
        
        Args:
            knowledge_base: NetworkX DiGraph containing knowledge nodes
            decay_rate: Base decay rate per time unit (default: 0.1)
            half_life_threshold: Activity level below which nodes are removed
            
        Raises:
            ValueError: If parameters are out of valid range
        """
        if decay_rate <= 0 or decay_rate >= 1:
            raise ValueError("Decay rate must be between 0 and 1")
        if half_life_threshold <= 0 or half_life_threshold >= 1:
            raise ValueError("Half-life threshold must be between 0 and 1")
            
        self.knowledge_base = knowledge_base
        self.decay_rate = decay_rate
        self.half_life_threshold = half_life_threshold
        self.structural_protection: Set[str] = set()
        self._initialize_structural_nodes()
        
        logger.info(
            "Initialized MetaCognitiveImmuneSystem with decay_rate=%.2f, "
            "half_life_threshold=%.2f", decay_rate, half_life_threshold
        )
    
    def _initialize_structural_nodes(self) -> None:
        """Identify and protect structural hole nodes in the knowledge graph."""
        try:
            if len(self.knowledge_base) == 0:
                return
                
            # Calculate betweenness centrality to find structural holes
            centrality = nx.betweenness_centrality(self.knowledge_base)
            threshold = np.percentile(list(centrality.values()), 90)
            
            self.structural_protection = {
                node for node, cent in centrality.items() if cent >= threshold
            }
            
            logger.info(
                "Identified %d structural nodes for protection", 
                len(self.structural_protection)
            )
            
        except Exception as e:
            logger.error("Error initializing structural nodes: %s", str(e))
            raise
    
    def calculate_node_activity(
        self,
        node: KnowledgeNode,
        current_time: Optional[datetime] = None
    ) -> float:
        """Calculate the activity level of a knowledge node.
        
        The activity is calculated using an exponential decay function that considers:
        - Time since last access
        - Access frequency
        - Verification score
        
        Args:
            node: The knowledge node to evaluate
            current_time: Reference time for calculation (defaults to now)
            
        Returns:
            float: Activity level between 0 and 1
            
        Raises:
            ValueError: If node data is invalid
        """
        if current_time is None:
            current_time = datetime.now()
            
        try:
            # Time-based decay
            time_since_access = (current_time - node.last_accessed).total_seconds()
            time_factor = math.exp(-self.decay_rate * time_since_access / 86400)  # Daily decay
            
            # Access frequency factor (logarithmic scaling)
            frequency_factor = 1 - math.exp(-node.access_count / 10)
            
            # Verification confidence factor
            confidence_factor = node.verification_score
            
            # Combined activity score
            activity = (time_factor * 0.5) + (frequency_factor * 0.3) + (confidence_factor * 0.2)
            
            # Validate result
            activity = max(0.0, min(1.0, activity))
            
            logger.debug(
                "Calculated activity for node %s: %.3f "
                "(time=%.3f, freq=%.3f, conf=%.3f)",
                node.id, activity, time_factor, frequency_factor, confidence_factor
            )
            
            return activity
            
        except Exception as e:
            logger.error("Error calculating node activity: %s", str(e))
            raise
    
    def detect_cognitive_parasites(
        self,
        node: KnowledgeNode,
        min_references: int = 3,
        max_external_refs: float = 0.1
    ) -> bool:
        """Identify cognitive parasites - logically consistent but isolated nodes.
        
        Cognitive parasites are nodes that:
        1. Have high internal connectivity (many references)
        2. Have very few connections to external knowledge
        3. Are not grounded in practical verification
        
        Args:
            node: The knowledge node to evaluate
            min_references: Minimum references to consider as potential parasite
            max_external_refs: Maximum allowed ratio of external references
            
        Returns:
            bool: True if node is identified as a cognitive parasite
        """
        try:
            if len(node.references) < min_references:
                return False
                
            # Check external connectivity
            external_refs = 0
            for ref in node.references:
                if ref not in self.knowledge_base:
                    external_refs += 1
                    
            external_ratio = external_refs / len(node.references) if node.references else 0
            
            # Check if the node is isolated from practical verification
            is_parasite = (
                external_ratio < max_external_refs and
                node.verification_score < 0.3
            )
            
            if is_parasite:
                logger.warning(
                    "Detected cognitive parasite node %s: "
                    "external_ratio=%.2f, verification=%.2f",
                    node.id, external_ratio, node.verification_score
                )
                
            return is_parasite
            
        except Exception as e:
            logger.error("Error detecting cognitive parasites: %s", str(e))
            raise
    
    def _is_node_removable(self, node_id: str, activity: float) -> bool:
        """Determine if a node should be removed based on activity and protection status.
        
        Args:
            node_id: ID of the node to evaluate
            activity: Current activity level of the node
            
        Returns:
            bool: True if the node can be safely removed
        """
        return (
            activity < self.half_life_threshold and
            node_id not in self.structural_protection
        )
    
    def run_maintenance_cycle(
        self,
        nodes: Dict[str, KnowledgeNode],
        dry_run: bool = False
    ) -> Tuple[Dict[str, float], List[str]]:
        """Execute a complete maintenance cycle on the knowledge base.
        
        This process:
        1. Calculates activity for all nodes
        2. Identifies cognitive parasites
        3. Removes low-activity non-structural nodes
        4. Updates structural protection
        
        Args:
            nodes: Dictionary mapping node IDs to KnowledgeNode objects
            dry_run: If True, only simulate without making changes
            
        Returns:
            Tuple containing:
            - Dictionary of node activities
            - List of removed node IDs
            
        Raises:
            ValueError: If nodes dictionary is empty
        """
        if not nodes:
            raise ValueError("Nodes dictionary cannot be empty")
            
        logger.info(
            "Starting maintenance cycle on %d nodes (dry_run=%s)",
            len(nodes), dry_run
        )
        
        activities: Dict[str, float] = {}
        to_remove: List[str] = []
        parasites_found = 0
        
        try:
            # Phase 1: Analyze all nodes
            for node_id, node in nodes.items():
                activity = self.calculate_node_activity(node)
                activities[node_id] = activity
                
                if self.detect_cognitive_parasites(node):
                    parasites_found += 1
                    if not dry_run:
                        to_remove.append(node_id)
                        continue
                        
                if self._is_node_removable(node_id, activity):
                    to_remove.append(node_id)
            
            # Phase 2: Execute removal
            if not dry_run:
                for node_id in to_remove:
                    if node_id in nodes:
                        del nodes[node_id]
                    if self.knowledge_base.has_node(node_id):
                        self.knowledge_base.remove_node(node_id)
                        
                # Update structural protection after removals
                self._initialize_structural_nodes()
            
            logger.info(
                "Maintenance complete. Activities calculated: %d, "
                "Nodes removed: %d, Parasites found: %d",
                len(activities), len(to_remove), parasites_found
            )
            
            return activities, to_remove
            
        except Exception as e:
            logger.error("Error during maintenance cycle: %s", str(e))
            raise


# Example usage
if __name__ == "__main__":
    # Create a sample knowledge base
    kb_graph = nx.DiGraph()
    
    # Add some nodes and edges
    kb_graph.add_nodes_from(["A", "B", "C", "D", "E"])
    kb_graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "A")])
    
    # Create knowledge nodes
    nodes = {
        "A": KnowledgeNode(id="A", content="Core concept", verification_score=0.9, access_count=50),
        "B": KnowledgeNode(id="B", content="Secondary concept", verification_score=0.7, access_count=20),
        "C": KnowledgeNode(id="C", content="Outdated info", verification_score=0.2, access_count=5),
        "D": KnowledgeNode(id="D", content="Isolated theory", verification_score=0.1, access_count=3),
        "E": KnowledgeNode(id="E", content="Experimental", verification_score=0.4, access_count=8)
    }
    
    # Initialize the immune system
    immune_system = MetaCognitiveImmuneSystem(kb_graph, decay_rate=0.15, half_life_threshold=0.25)
    
    # Run a maintenance cycle
    activities, removed = immune_system.run_maintenance_cycle(nodes)
    
    print("\nMaintenance Results:")
    print(f"Node activities: {activities}")
    print(f"Nodes removed: {removed}")
    print(f"Protected structural nodes: {immune_system.structural_protection}")