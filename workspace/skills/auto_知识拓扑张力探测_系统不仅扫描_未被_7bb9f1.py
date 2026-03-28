"""
Knowledge Topology Tension Detection System

This module implements a sophisticated knowledge topology analysis system that identifies
innovation opportunities by detecting "tension" between existing knowledge nodes.

The system goes beyond simple coverage scanning by calculating the structural tension
between nodes - situations where solutions to problem A and problem B exist but are
far apart in the knowledge graph without proper bridging concepts.

Key Features:
- Knowledge graph construction and analysis
- Tension calculation between distant nodes
- Innovation opportunity identification
- Human-readable gap analysis reports

Example Usage:
    >>> detector = KnowledgeTopologyDetector()
    >>> detector.add_node("python_basics", ["programming", "python"])
    >>> detector.add_node("machine_learning", ["ai", "ml"])
    >>> tensions = detector.detect_tensions()
    >>> for tension in tensions:
    ...     print(f"Tension between {tension.node_a} and {tension.node_b}")
    ...     print(f"  Suggested bridge: {tension.suggested_bridge}")
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import math
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge topology graph."""
    node_id: str
    attributes: Set[str]
    connections: Set[str] = None
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = set()
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary representation."""
        return {
            "node_id": self.node_id,
            "attributes": list(self.attributes),
            "connections": list(self.connections)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KnowledgeNode':
        """Create node from dictionary representation."""
        return cls(
            node_id=data["node_id"],
            attributes=set(data["attributes"]),
            connections=set(data.get("connections", []))
        )


@dataclass
class TensionResult:
    """Represents a detected tension between knowledge nodes."""
    node_a: str
    node_b: str
    distance: float
    shared_attributes: Set[str]
    unique_attributes_a: Set[str]
    unique_attributes_b: Set[str]
    suggested_bridge: str
    tension_score: float
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary representation."""
        return {
            "node_a": self.node_a,
            "node_b": self.node_b,
            "distance": self.distance,
            "shared_attributes": list(self.shared_attributes),
            "unique_attributes_a": list(self.unique_attributes_a),
            "unique_attributes_b": list(self.unique_attributes_b),
            "suggested_bridge": self.suggested_bridge,
            "tension_score": self.tension_score
        }


class KnowledgeTopologyDetector:
    """
    Advanced knowledge topology analysis system that detects structural tensions
    between knowledge nodes to identify innovation opportunities.
    
    The system maintains a knowledge graph where:
    - Nodes represent capabilities, concepts or problem-solving approaches
    - Edges represent relationships or bridges between concepts
    - Tension is calculated when nodes are far apart but could benefit from connection
    
    Attributes:
        nodes (Dict[str, KnowledgeNode]): Dictionary of knowledge nodes
        attribute_index (Dict[str, Set[str]]): Reverse index from attributes to nodes
        tension_threshold (float): Minimum tension score to report
    """
    
    def __init__(self, tension_threshold: float = 0.6):
        """
        Initialize the knowledge topology detector.
        
        Args:
            tension_threshold: Minimum tension score (0.0-1.0) to consider significant
        """
        if not 0 <= tension_threshold <= 1:
            raise ValueError("Tension threshold must be between 0 and 1")
            
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.attribute_index: Dict[str, Set[str]] = defaultdict(set)
        self.tension_threshold = tension_threshold
        logger.info(f"Initialized KnowledgeTopologyDetector with threshold {tension_threshold}")
    
    def add_node(self, node_id: str, attributes: List[str], connections: Optional[List[str]] = None) -> None:
        """
        Add a new knowledge node to the topology.
        
        Args:
            node_id: Unique identifier for the node
            attributes: List of attributes/tags describing this node
            connections: Optional list of existing connected node IDs
            
        Raises:
            ValueError: If node_id already exists or is invalid
        """
        if not node_id or not isinstance(node_id, str):
            raise ValueError("Node ID must be a non-empty string")
            
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")
            
        if not attributes:
            logger.warning(f"Adding node {node_id} with no attributes")
        
        # Create node
        node = KnowledgeNode(
            node_id=node_id,
            attributes=set(attributes),
            connections=set(connections or [])
        )
        
        # Validate connections exist
        for conn in node.connections:
            if conn not in self.nodes:
                logger.warning(f"Connection target {conn} does not exist, skipping")
                node.connections.remove(conn)
        
        # Update indices
        self.nodes[node_id] = node
        for attr in node.attributes:
            self.attribute_index[attr].add(node_id)
            
        logger.info(f"Added knowledge node: {node_id} with {len(attributes)} attributes")
    
    def _calculate_attribute_similarity(self, attrs_a: Set[str], attrs_b: Set[str]) -> float:
        """
        Calculate Jaccard similarity between two attribute sets.
        
        Args:
            attrs_a: First attribute set
            attrs_b: Second attribute set
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not attrs_a or not attrs_b:
            return 0.0
            
        intersection = len(attrs_a & attrs_b)
        union = len(attrs_a | attrs_b)
        return intersection / union if union > 0 else 0.0
    
    def _calculate_graph_distance(self, node_a: str, node_b: str) -> float:
        """
        Calculate the shortest path distance between two nodes in the graph.
        
        Args:
            node_a: First node ID
            node_b: Second node ID
            
        Returns:
            Distance in number of hops (0 if same, infinity if disconnected)
        """
        if node_a == node_b:
            return 0.0
            
        if node_a not in self.nodes or node_b not in self.nodes:
            return float('inf')
            
        # BFS to find shortest path
        visited = set()
        queue = [(node_a, 0)]
        
        while queue:
            current, distance = queue.pop(0)
            
            if current == node_b:
                return float(distance)
                
            if current in visited:
                continue
                
            visited.add(current)
            
            for neighbor in self.nodes[current].connections:
                if neighbor not in visited:
                    queue.append((neighbor, distance + 1))
        
        # Nodes are not connected
        return float('inf')
    
    def _suggest_bridge(self, attrs_a: Set[str], attrs_b: Set[str]) -> str:
        """
        Generate a suggestion for bridging two knowledge domains.
        
        Args:
            attrs_a: Attributes from first node
            attrs_b: Attributes from second node
            
        Returns:
            Human-readable suggestion for bridging the gap
        """
        shared = attrs_a & attrs_b
        unique_a = attrs_a - attrs_b
        unique_b = attrs_b - attrs_a
        
        suggestions = []
        
        if shared:
            suggestions.append(f"build on shared concepts: {', '.join(shared)}")
        
        if unique_a and unique_b:
            suggestions.append(f"explore intersection of {', '.join(unique_a)} with {', '.join(unique_b)}")
        
        return " and ".join(suggestions) if suggestions else "explore fundamental connections"
    
    def detect_tensions(self, min_distance: int = 2) -> List[TensionResult]:
        """
        Analyze the knowledge topology to detect structural tensions.
        
        This is the core function that identifies innovation opportunities by
        finding pairs of nodes that are:
        1. Distant in the graph (min_distance or more hops apart)
        2. Have some attribute overlap (potential for synergy)
        3. Have significant unique attributes (innovation potential)
        
        Args:
            min_distance: Minimum graph distance to consider as "far apart"
            
        Returns:
            List of TensionResult objects sorted by tension_score descending
        """
        logger.info(f"Starting tension detection with min_distance={min_distance}")
        tensions = []
        node_ids = list(self.nodes.keys())
        
        for i, node_a_id in enumerate(node_ids):
            for node_b_id in node_ids[i+1:]:
                node_a = self.nodes[node_a_id]
                node_b = self.nodes[node_b_id]
                
                # Calculate metrics
                distance = self._calculate_graph_distance(node_a_id, node_b_id)
                if distance < min_distance:
                    continue
                    
                similarity = self._calculate_attribute_similarity(node_a.attributes, node.attributes)
                
                # Skip if too similar (no tension) or completely different (no synergy)
                if similarity > 0.7 or similarity < 0.1:
                    continue
                
                # Calculate tension score
                # Higher tension when: large distance, moderate similarity, many unique attrs
                unique_ratio = (len(node_a.attributes - node_b.attributes) + 
                               len(node_b.attributes - node_a.attributes)) / \
                              (len(node_a.attributes) + len(node_b.attributes))
                
                tension_score = (math.log1p(distance) * 0.5 + 
                               (1 - abs(similarity - 0.4)) * 0.3 + 
                               unique_ratio * 0.2)
                
                if tension_score < self.tension_threshold:
                    continue
                
                # Create tension result
                tension = TensionResult(
                    node_a=node_a_id,
                    node_b=node_b_id,
                    distance=distance,
                    shared_attributes=node_a.attributes & node_b.attributes,
                    unique_attributes_a=node_a.attributes - node_b.attributes,
                    unique_attributes_b=node_b.attributes - node_a.attributes,
                    suggested_bridge=self._suggest_bridge(node_a.attributes, node_b.attributes),
                    tension_score=round(tension_score, 3)
                )
                tensions.append(tension)
        
        # Sort by tension score descending
        tensions.sort(key=lambda x: x.tension_score, reverse=True)
        logger.info(f"Detected {len(tensions)} significant tensions")
        return tensions
    
    def generate_report(self, tensions: List[TensionResult]) -> str:
        """
        Generate a human-readable report of detected tensions.
        
        Args:
            tensions: List of TensionResult objects
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("KNOWLEDGE TOPOLOGY TENSION REPORT")
        report.append("=" * 50)
        report.append(f"Total nodes analyzed: {len(self.nodes)}")
        report.append(f"Significant tensions detected: {len(tensions)}\n")
        
        for i, tension in enumerate(tensions[:10], 1):  # Top 10
            report.append(f"\n{i}. TENSION BETWEEN '{tension.node_a}' AND '{tension.node_b}'")
            report.append(f"   Graph distance: {tension.distance} hops")
            report.append(f"   Tension score: {tension.tension_score:.2f}")
            report.append(f"   Shared attributes: {', '.join(tension.shared_attributes) or 'None'}")
            report.append(f"   Unique to {tension.node_a}: {', '.join(tension.unique_attributes_a)}")
            report.append(f"   Unique to {tension.node_b}: {', '.join(tension.unique_attributes_b)}")
            report.append(f"\n   SUGGESTION: {tension.suggested_bridge}")
        
        return "\n".join(report)
    
    def save_state(self, filepath: str) -> None:
        """
        Save current knowledge topology to a JSON file.
        
        Args:
            filepath: Path to save file
        """
        data = {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "tension_threshold": self.tension_threshold
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved knowledge topology to {filepath}")
        except IOError as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    @classmethod
    def load_state(cls, filepath: str) -> 'KnowledgeTopologyDetector':
        """
        Load knowledge topology from a JSON file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            KnowledgeTopologyDetector instance
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            detector = cls(tension_threshold=data["tension_threshold"])
            
            for node_data in data["nodes"]:
                detector.add_node(
                    node_id=node_data["node_id"],
                    attributes=node_data["attributes"],
                    connections=node_data["connections"]
                )
            
            logger.info(f"Loaded knowledge topology from {filepath}")
            return detector
            
        except (IOError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load state: {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Create detector
    detector = KnowledgeTopologyDetector(tension_threshold=0.5)
    
    # Add knowledge nodes
    detector.add_node("python_basics", ["programming", "python", "basics"])
    detector.add_node("data_analysis", ["python", "pandas", "statistics"])
    detector.add_node("machine_learning", ["ai", "ml", "algorithms"])
    detector.add_node("web_development", ["python", "django", "frontend"])
    detector.add_node("nlp", ["ai", "language", "text_processing"])
    
    # Add some connections
    detector.nodes["python_basics"].connections.add("data_analysis")
    detector.nodes["data_analysis"].connections.add("machine_learning")
    
    # Detect tensions
    tensions = detector.detect_tensions(min_distance=2)
    
    # Generate and print report
    print(detector.generate_report(tensions))
    
    # Save state
    detector.save_state("knowledge_topology.json")