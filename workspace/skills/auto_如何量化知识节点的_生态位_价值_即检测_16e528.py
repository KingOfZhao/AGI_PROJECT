"""
Module: auto_如何量化知识节点的_生态位_价值_即检测_16e528
Description: 
    This module provides algorithms to quantify the 'ecological niche' value of knowledge nodes 
    within a network. It focuses on detecting 'structural islands' (low connectivity) or 
    'excessive redundancy' (functional overlap). It calculates Betweenness Centrality and 
    Connection Density to assess node value.
    
    Crucially, it implements logic to evaluate maintenance costs versus network utility. 
    If a high-cost node persists in a low-connectivity/low-reference state, or is functionally 
    shadowed by a more efficient node, the system triggers automated merge or deletion protocols.

Domain: Network Science / AGI Knowledge Graph Management
"""

import networkx as nx
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeNode:
    """
    A data structure representing a node in the knowledge graph.
    """
    def __init__(self, node_id: str, maintenance_cost: float, efficiency_score: float, content_hash: Optional[str] = None):
        self.node_id = node_id
        self.maintenance_cost = maintenance_cost  # e.g., compute cost, manual review hours
        self.efficiency_score = efficiency_score  # 0.0 to 1.0 (latency, accuracy)
        self.content_hash = content_hash          # Used for functional overlap detection

class KnowledgeNetworkAnalyzer:
    """
    Analyzes the ecological value of nodes in a knowledge network.
    """
    
    def __init__(self, graph: nx.DiGraph):
        """
        Initialize with a NetworkX DiGraph.
        
        Args:
            graph (nx.DiGraph): The knowledge graph.
        """
        if not isinstance(graph, nx.DiGraph):
            raise TypeError("Input must be a networkx.DiGraph.")
        self.graph = graph
        logger.info(f"Initialized analyzer with {graph.number_of_nodes()} nodes.")

    def _validate_graph_state(self) -> bool:
        """Check if the graph is empty."""
        if self.graph.number_of_nodes() == 0:
            logger.warning("Graph is empty. No analysis performed.")
            return False
        return True

    def calculate_structural_metrics(self, normalized: bool = True) -> pd.DataFrame:
        """
        Calculates Betweenness Centrality and Connection Density for all nodes.
        
        Returns:
            pd.DataFrame: A dataframe containing node metrics.
        """
        if not self._validate_graph_state():
            return pd.DataFrame()

        logger.info("Calculating structural metrics: Betweenness Centrality...")
        try:
            # Betweenness Centrality: Identifies nodes that act as bridges
            betweenness = nx.betweenness_centrality(self.graph, normalized=normalized)
        except Exception as e:
            logger.error(f"Error calculating betweenness centrality: {e}")
            betweenness = {}

        logger.info("Calculating structural metrics: Degree Centrality (Connection Density proxy)...")
        try:
            # Degree Centrality: Sum of in/out connections normalized
            degree_centralities = nx.degree_centrality(self.graph)
        except Exception as e:
            logger.error(f"Error calculating degree centrality: {e}")
            degree_centralities = {}

        # Compile results
        data = []
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            # Extract cost and efficiency safely
            cost = node_data.get('maintenance_cost', 0.5)
            efficiency = node_data.get('efficiency_score', 0.5)
            
            # Calculate ROI (Return on Investment) - Higher is better
            # ROI = (Centrality * Efficiency) / Cost
            # Adding epsilon to cost to avoid division by zero
            safe_cost = max(cost, 0.0001)
            roi = (betweenness.get(node_id, 0) + degree_centralities.get(node_id, 0)) * efficiency / safe_cost

            data.append({
                'node_id': node_id,
                'betweenness': betweenness.get(node_id, 0.0),
                'connection_density': degree_centralities.get(node_id, 0.0),
                'maintenance_cost': cost,
                'efficiency_score': efficiency,
                'roi_score': roi,
                'content_hash': node_data.get('content_hash')
            })
        
        df = pd.DataFrame(data)
        logger.info("Structural metrics calculation complete.")
        return df

    def detect_redundancy(self, metrics_df: pd.DataFrame) -> List[Tuple[str, str]]:
        """
        Identifies redundant nodes based on content hash and efficiency.
        If two nodes share a content_hash (functional equivalence), 
        the one with lower efficiency or higher cost is flagged for merging.
        
        Args:
            metrics_df (pd.DataFrame): DataFrame from calculate_structural_metrics.
            
        Returns:
            List[Tuple[str, str]]: List of (redundant_node, keeper_node) pairs.
        """
        if metrics_df.empty:
            return []

        redundant_pairs = []
        # Group by content hash
        grouped = metrics_df.groupby('content_hash')
        
        for hash_val, group in grouped:
            if len(group) > 1 and hash_val is not None:
                # Sort by efficiency (desc) and cost (asc) to find the "dominant" node
                sorted_group = group.sort_values(by=['efficiency_score', 'maintenance_cost'], ascending=[False, True])
                keeper = sorted_group.iloc[0]
                
                for _, row in sorted_group.iloc[1:].iterrows():
                    logger.info(f"Redundancy detected: Node {row['node_id']} is shadowed by {keeper['node_id']}")
                    redundant_pairs.append((row['node_id'], keeper['node_id']))
                    
        return redundant_pairs

    def execute_ecological_assessment(
        self, 
        low_connectivity_threshold: float = 0.01, 
        low_roi_threshold: float = 0.05
    ) -> Dict[str, List[str]]:
        """
        Main workflow to detect structural islands and trigger optimization logic.
        
        Args:
            low_connectivity_threshold (float): Threshold for connection density to consider a node isolated.
            low_roi_threshold (float): Threshold for ROI to consider a node low-value.
            
        Returns:
            Dict: A report containing lists of nodes to 'delete', 'merge', or 'review'.
        """
        metrics_df = self.calculate_structural_metrics()
        if metrics_df.empty:
            return {"error": ["Empty graph or calculation failure."]}

        actions = {
            "delete": [],
            "merge": [],
            "review": []
        }

        # 1. Check for Structural Islands (Low Connectivity + High Cost)
        # Logic: If a node has very few connections and costs a lot to maintain, it's a candidate for deletion.
        # Exception: High efficiency might save it (requires review).
        structural_islands = metrics_df[
            (metrics_df['connection_density'] < low_connectivity_threshold) & 
            (metrics_df['maintenance_cost'] > 0.7) # Arbitrary high cost
        ]

        for _, node in structural_islands.iterrows():
            if node['roi_score'] < low_roi_threshold:
                actions['delete'].append(node['node_id'])
                logger.warning(f"Node {node['node_id']} flagged for DELETION (Structural Island).")
            else:
                actions['review'].append(node['node_id'])
                logger.info(f"Node {node['node_id']} flagged for REVIEW (Island but high potential ROI).")

        # 2. Check for Redundancy
        redundancies = self.detect_redundancy(metrics_df)
        for target, source in redundancies:
            actions['merge'].append(f"{target} -> {source}")

        return actions

# Helper function for data preparation
def create_sample_knowledge_graph() -> nx.DiGraph:
    """
    Helper function to generate a mock knowledge graph for testing.
    
    Returns:
        nx.DiGraph: A sample graph with various node types.
    """
    G = nx.DiGraph()
    
    # Core Cluster (High value, high connectivity)
    G.add_node("Core_1", maintenance_cost=0.2, efficiency_score=0.9, content_hash="hash_A")
    G.add_node("Core_2", maintenance_cost=0.3, efficiency_score=0.8, content_hash="hash_B")
    
    # Redundant Nodes (Same function, different efficiency)
    G.add_node("Redundant_1", maintenance_cost=0.8, efficiency_score=0.4, content_hash="hash_A") # Same hash as Core_1
    
    # Structural Island (Low connectivity, high cost)
    G.add_node("Island_1", maintenance_cost=0.9, efficiency_score=0.2, content_hash="hash_C")
    
    # Healthy connections
    G.add_edges_from([("Core_1", "Core_2"), ("Core_2", "Core_1"), ("Core_1", "Redundant_1")])
    # Island has only one weak link
    G.add_edge("Core_2", "Island_1")
    
    return G

if __name__ == "__main__":
    # Example Usage
    print("--- Initializing Knowledge Network Analysis ---")
    
    # 1. Setup Data
    graph = create_sample_knowledge_graph()
    
    # 2. Initialize Analyzer
    analyzer = KnowledgeNetworkAnalyzer(graph)
    
    # 3. Run Assessment
    report = analyzer.execute_ecological_assessment(
        low_connectivity_threshold=0.05,
        low_roi_threshold=0.1
    )
    
    # 4. Output Results
    print("\n--- Ecological Assessment Report ---")
    for action, nodes in report.items():
        if nodes:
            print(f"Action [{action}]: {', '.join(map(str, nodes))}")
    
    print("\n--- Detailed Metrics ---")
    df = analyzer.calculate_structural_metrics()
    print(df[['node_id', 'connection_density', 'maintenance_cost', 'roi_score']].head())