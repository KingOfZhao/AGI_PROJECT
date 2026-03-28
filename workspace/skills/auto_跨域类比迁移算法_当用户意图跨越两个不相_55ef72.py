"""
Cross-Domain Analogical Transfer Algorithm Module

This module implements a structural isomorphism detection algorithm for cross-domain
analogical reasoning. It enables the mapping of structural relationships between
conceptually unrelated domains (e.g., managing night market stalls → managing server queues).

Key Features:
- Graph-based representation of domain knowledge
- Structural similarity calculation using graph isomorphism principles
- Mapping validation with logical consistency checking
- Comprehensive error handling and logging

Author: AGI System
Version: 1.0.0
"""

import logging
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass
import numpy as np
import networkx as nx
from networkx.algorithms import isomorphism

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DomainNode:
    """Represents a node in a domain knowledge graph."""
    id: str
    name: str
    attributes: Dict[str, Any]
    role: str  # Functional role in the domain (e.g., 'manager', 'resource')

@dataclass
class DomainEdge:
    """Represents a relationship between nodes in a domain."""
    source: str
    target: str
    relationship: str
    weight: float = 1.0

class CrossDomainAnalogicalTransfer:
    """
    Implements cross-domain analogical transfer algorithm based on structural isomorphism.
    
    This class handles:
    1. Domain knowledge representation as graphs
    2. Structural similarity calculation
    3. Mapping generation and validation
    
    Example:
        >>> source_domain = {
        ...     'nodes': [
        ...         {'id': 's1', 'name': 'Stall Manager', 'attributes': {'capacity': 10}, 'role': 'manager'},
        ...         {'id': 's2', 'name': 'Food Stall', 'attributes': {'throughput': 5}, 'role': 'resource'}
        ...     ],
        ...     'edges': [
        ...         {'source': 's1', 'target': 's2', 'relationship': 'manages', 'weight': 0.8}
        ...     ]
        ... }
        >>> target_domain = {
        ...     'nodes': [
        ...         {'id': 't1', 'name': 'Server', 'attributes': {'cpu': 4}, 'role': 'resource'},
        ...         {'id': 't2', 'name': 'Load Balancer', 'attributes': {'connections': 100}, 'role': 'manager'}
        ...     ],
        ...     'edges': [
        ...         {'source': 't2', 'target': 't1', 'relationship': 'routes_to', 'weight': 0.9}
        ...     ]
        ... }
        >>> analogical_transfer = CrossDomainAnalogicalTransfer()
        >>> analogical_transfer.load_domain('night_market', source_domain)
        >>> analogical_transfer.load_domain('server_cluster', target_domain)
        >>> similarity = analogical_transfer.calculate_structural_similarity('night_market', 'server_cluster')
        >>> mappings = analogical_transfer.generate_mappings('night_market', 'server_cluster')
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize the analogical transfer system.
        
        Args:
            similarity_threshold: Minimum similarity score for valid mappings (0-1)
        """
        self.domains: Dict[str, nx.DiGraph] = {}
        self.similarity_threshold = similarity_threshold
        self._validate_similarity_threshold()
        
        logger.info("CrossDomainAnalogicalTransfer initialized with threshold %.2f", similarity_threshold)
    
    def _validate_similarity_threshold(self) -> None:
        """Validate the similarity threshold is within bounds."""
        if not 0 <= self.similarity_threshold <= 1:
            error_msg = f"Similarity threshold must be between 0 and 1, got {self.similarity_threshold}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _convert_to_graph(self, domain_data: Dict[str, List[Dict]]) -> nx.DiGraph:
        """
        Convert domain data dictionary to a NetworkX directed graph.
        
        Args:
            domain_data: Dictionary containing nodes and edges
            
        Returns:
            NetworkX DiGraph representation of the domain
            
        Raises:
            ValueError: If domain data is invalid or missing required fields
        """
        if not isinstance(domain_data, dict):
            error_msg = "Domain data must be a dictionary"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if 'nodes' not in domain_data or 'edges' not in domain_data:
            error_msg = "Domain data must contain 'nodes' and 'edges' keys"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        graph = nx.DiGraph()
        
        # Add nodes with attributes
        for node in domain_data['nodes']:
            if not all(key in node for key in ['id', 'name', 'attributes', 'role']):
                error_msg = f"Node missing required fields: {node}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            graph.add_node(
                node['id'],
                name=node['name'],
                attributes=node['attributes'],
                role=node['role']
            )
        
        # Add edges with attributes
        for edge in domain_data['edges']:
            if not all(key in edge for key in ['source', 'target', 'relationship']):
                error_msg = f"Edge missing required fields: {edge}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            graph.add_edge(
                edge['source'],
                edge['target'],
                relationship=edge['relationship'],
                weight=edge.get('weight', 1.0)
            )
        
        return graph
    
    def load_domain(self, domain_name: str, domain_data: Dict[str, List[Dict]]) -> None:
        """
        Load a domain into the system.
        
        Args:
            domain_name: Unique identifier for the domain
            domain_data: Dictionary containing nodes and edges
            
        Raises:
            ValueError: If domain data is invalid
        """
        if domain_name in self.domains:
            logger.warning("Overwriting existing domain: %s", domain_name)
            
        try:
            graph = self._convert_to_graph(domain_data)
            self.domains[domain_name] = graph
            logger.info("Successfully loaded domain: %s with %d nodes and %d edges",
                       domain_name, graph.number_of_nodes(), graph.number_of_edges())
        except Exception as e:
            error_msg = f"Failed to load domain {domain_name}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _node_match(self, node1: Dict, node2: Dict) -> bool:
        """
        Custom node matching function for isomorphism checking.
        
        Args:
            node1: First node attributes
            node2: Second node attributes
            
        Returns:
            bool: True if nodes match based on role and attribute similarity
        """
        # Match based on functional role (primary)
        if node1['role'] != node2['role']:
            return False
            
        # Calculate attribute similarity (secondary)
        attrs1 = node1['attributes']
        attrs2 = node2['attributes']
        
        common_keys = set(attrs1.keys()) & set(attrs2.keys())
        if not common_keys:
            return False
            
        # Simple attribute similarity: count matching keys
        similarity = len(common_keys) / max(len(attrs1), len(attrs2))
        return similarity >= self.similarity_threshold
    
    def _edge_match(self, edge1: Dict, edge2: Dict) -> bool:
        """
        Custom edge matching function for isomorphism checking.
        
        Args:
            edge1: First edge attributes
            edge2: Second edge attributes
            
        Returns:
            bool: True if edges match based on relationship type
        """
        # Match based on relationship type
        return edge1['relationship'] == edge2['relationship']
    
    def calculate_structural_similarity(self, source_domain: str, target_domain: str) -> float:
        """
        Calculate structural similarity between two domains.
        
        Args:
            source_domain: Name of the source domain
            target_domain: Name of the target domain
            
        Returns:
            float: Structural similarity score between 0 (no similarity) and 1 (perfect match)
            
        Raises:
            ValueError: If either domain is not loaded
        """
        self._validate_domains_exist(source_domain, target_domain)
        
        source_graph = self.domains[source_domain]
        target_graph = self.domains[target_domain]
        
        logger.info("Calculating structural similarity between %s and %s", source_domain, target_domain)
        
        # Calculate graph similarity using graph edit distance
        try:
            # For large graphs, this might be computationally expensive
            # In practice, we'd use approximate algorithms for production
            ged = nx.graph_edit_distance(
                source_graph,
                target_graph,
                node_match=self._node_match,
                edge_match=self._edge_match
            )
            
            # Normalize to 0-1 scale
            max_possible_ged = max(
                source_graph.number_of_nodes() + source_graph.number_of_edges(),
                target_graph.number_of_nodes() + target_graph.number_of_edges()
            )
            
            similarity = 1.0 - (ged / max_possible_ged) if max_possible_ged > 0 else 0.0
            similarity = max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
            logger.info("Structural similarity score: %.4f", similarity)
            return similarity
            
        except Exception as e:
            logger.error("Error calculating structural similarity: %s", str(e))
            return 0.0
    
    def _validate_domains_exist(self, *domain_names: str) -> None:
        """Validate that all specified domains exist."""
        missing_domains = [d for d in domain_names if d not in self.domains]
        if missing_domains:
            error_msg = f"Domains not found: {', '.join(missing_domains)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def generate_mappings(
        self,
        source_domain: str,
        target_domain: str,
        max_mappings: int = 5
    ) -> List[Dict[str, Dict[str, str]]]:
        """
        Generate possible node mappings between source and target domains.
        
        Args:
            source_domain: Name of the source domain
            target_domain: Name of the target domain
            max_mappings: Maximum number of mappings to return
            
        Returns:
            List of possible mappings, where each mapping is a dictionary:
            {
                'source_node_id': 'target_node_id',
                ...
            }
            
        Raises:
            ValueError: If either domain is not loaded
        """
        self._validate_domains_exist(source_domain, target_domain)
        
        source_graph = self.domains[source_domain]
        target_graph = self.domains[target_domain]
        
        logger.info("Generating mappings from %s to %s", source_domain, target_domain)
        
        # Use VF2 algorithm for graph isomorphism
        matcher = isomorphism.DiGraphMatcher(
            target_graph,
            source_graph,
            node_match=self._node_match,
            edge_match=self._edge_match
        )
        
        mappings = []
        for mapping in matcher.isomorphisms_iter():
            # Convert to more readable format
            readable_mapping = {
                target_node: source_node
                for source_node, target_node in mapping.items()
            }
            mappings.append(readable_mapping)
            
            if len(mappings) >= max_mappings:
                break
        
        logger.info("Generated %d possible mappings", len(mappings))
        return mappings
    
    def evaluate_mapping_consistency(
        self,
        source_domain: str,
        target_domain: str,
        mapping: Dict[str, str]
    ) -> Tuple[float, List[str]]:
        """
        Evaluate the logical consistency of a specific mapping.
        
        Args:
            source_domain: Name of the source domain
            target_domain: Name of the target domain
            mapping: Dictionary mapping source node IDs to target node IDs
            
        Returns:
            Tuple of (consistency_score, issues_list)
            consistency_score: 0 (inconsistent) to 1 (perfectly consistent)
            issues_list: List of consistency issues found
            
        Raises:
            ValueError: If domains or mapping are invalid
        """
        self._validate_domains_exist(source_domain, target_domain)
        
        if not mapping:
            error_msg = "Mapping cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        source_graph = self.domains[source_domain]
        target_graph = self.domains[target_domain]
        
        issues = []
        total_checks = 0
        passed_checks = 0
        
        # Check node role consistency
        for source_node, target_node in mapping.items():
            total_checks += 1
            source_role = source_graph.nodes[source_node]['role']
            target_role = target_graph.nodes[target_node]['role']
            
            if source_role != target_role:
                issues.append(
                    f"Role mismatch: {source_node}({source_role}) -> {target_node}({target_role})"
                )
            else:
                passed_checks += 1
        
        # Check relationship consistency
        for source_edge in source_graph.edges(data=True):
            source_u, source_v, data = source_edge
            if source_u in mapping and source_v in mapping:
                target_u = mapping[source_u]
                target_v = mapping[source_v]
                
                if target_graph.has_edge(target_u, target_v):
                    total_checks += 1
                    source_rel = data['relationship']
                    target_rel = target_graph.edges[target_u, target_v]['relationship']
                    
                    if source_rel != target_rel:
                        issues.append(
                            f"Relationship mismatch: {source_u}-{source_v}({source_rel}) -> "
                            f"{target_u}-{target_v}({target_rel})"
                        )
                    else:
                        passed_checks += 1
                else:
                    issues.append(
                        f"Missing relationship: {source_u}-{source_v} exists in source but "
                        f"{target_u}-{target_v} not found in target"
                    )
                    total_checks += 1
        
        consistency_score = passed_checks / total_checks if total_checks > 0 else 0.0
        logger.info("Mapping consistency score: %.4f with %d issues", consistency_score, len(issues))
        
        return consistency_score, issues

# Example usage in docstring is already provided above