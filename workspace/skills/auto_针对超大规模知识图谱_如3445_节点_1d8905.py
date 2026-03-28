"""
Module: auto_kg_lifecycle_manager
Description: AGI Skill for self-maintenance and lifecycle management of ultra-large Knowledge Graphs.
             Integrates time-decay (freshness) and structural (bridge) analysis for automated
             graph metabolism.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
import datetime
import json
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

# Attempt to import networkx, provide fallback or instruction if missing
try:
    import networkx as nx
except ImportError:
    nx = None  # type: ignore

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KG_Auto_Lifecycle")


class KnowledgeGraphMetabolismManager:
    """
    Manages the lifecycle of nodes in a large-scale knowledge graph.
    
    This system evaluates nodes based on:
    1. Freshness (Time Dimension): Penalizes nodes based on access frequency and age (Half-life logic).
    2. Structural Importance (Structure Dimension): Identifies 'Bridge Nodes' connecting isolated clusters.
    3. Environment Sanity (Sandbox): Verifies if executable nodes have valid dependencies.
    
    Attributes:
        half_life (int): The period in days after which an unaccessed node's weight halves.
        decay_rate (float): Calculated decay rate based on half_life.
        bridge_threshold (float): Minimum betweenness centrality to consider a node a 'Bridge'.
        graph (nx.Graph): The internal graph representation.
    """

    def __init__(self, half_life_days: int = 30, bridge_threshold: float = 0.1):
        """
        Initialize the manager.

        Args:
            half_life_days (int): Days for knowledge freshness to decay by 50%.
            bridge_threshold (float): Threshold for structural hole detection (betweenness).
        """
        if nx is None:
            raise ImportError("NetworkX is required for this module. Please install it via 'pip install networkx'.")
        
        self.half_life = half_life_days
        self.decay_rate = math.log(2) / self.half_life
        self.bridge_threshold = bridge_threshold
        self.graph = nx.Graph()
        self.node_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Manager initialized with Half-Life: {half_life_days} days, Decay Rate: {self.decay_rate:.4f}")

    def load_graph_data(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """
        Load graph data into the system.

        Args:
            nodes (List[Dict]): List of node objects. 
                                Must contain 'id', 'type', 'created_at', 'last_accessed'.
            edges (List[Dict]): List of edge objects. Must contain 'source', 'target'.

        Raises:
            ValueError: If data format is invalid.
        """
        logger.info(f"Loading {len(nodes)} nodes and {len(edges)} edges...")
        
        # Data Validation
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("Inputs must be lists of dictionaries.")

        try:
            for node in nodes:
                if 'id' not in node:
                    raise ValueError("Node missing 'id' field.")
                
                node_id = node['id']
                self.graph.add_node(node_id)
                
                # Store metadata separately to keep graph object clean
                self.node_metadata[node_id] = {
                    'type': node.get('type', 'generic'),
                    'created_at': node.get('created_at', datetime.datetime.now()),
                    'last_accessed': node.get('last_accessed', datetime.datetime.now()),
                    'executable': node.get('executable', False),
                    'dependencies': node.get('dependencies', {})
                }

            for edge in edges:
                if 'source' not in edge or 'target' not in edge:
                    raise ValueError("Edge missing 'source' or 'target'.")
                self.graph.add_edge(edge['source'], edge['target'])
                
            logger.info("Graph data loaded successfully.")
            
        except Exception as e:
            logger.error(f"Failed to load graph data: {e}")
            raise

    def calculate_freshness_score(self, node_id: str) -> float:
        """
        Core Function 1: Calculate the freshness score of a node based on the Half-Life model.
        
        Formula: Score = e ^ (-decay_rate * days_since_access)
        
        Args:
            node_id (str): The ID of the node.

        Returns:
            float: A score between 0.0 (stale) and 1.0 (fresh).
        """
        if node_id not in self.node_metadata:
            logger.warning(f"Node {node_id} not found in metadata.")
            return 0.0

        metadata = self.node_metadata[node_id]
        last_accessed = metadata.get('last_accessed')
        
        if not isinstance(last_accessed, (datetime.datetime, str)):
            return 0.5  # Default neutral score if date is missing

        # Handle ISO format strings
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.datetime.fromisoformat(last_accessed)
            except ValueError:
                return 0.5

        delta = datetime.datetime.now() - last_accessed
        days_passed = delta.total_seconds() / (3600 * 24)
        
        score = math.exp(-self.decay_rate * days_passed)
        return max(0.0, min(1.0, score))

    def identify_structural_holes(self) -> Tuple[Set[str], Dict[str, float]]:
        """
        Core Function 2: Identify structural holes (Bridge Nodes).
        
        Uses Betweenness Centrality to find nodes that connect disparate parts of the graph.
        These nodes are critical for graph connectivity and should be 'reinforced'.

        Returns:
            Tuple[Set[str], Dict[str, float]]: A set of bridge node IDs and the full centrality dictionary.
        """
        logger.info("Calculating betweenness centrality (structural analysis)...")
        
        # sampling k nodes for approximation if graph is huge, but here we assume <5000 fits in memory
        # for exact calculation on 3445 nodes.
        if self.graph.number_of_nodes() == 0:
            return set(), {}

        try:
            # k=None means exact calculation. For >10,000 nodes, use k=100 approx.
            centrality = nx.betweenness_centrality(self.graph, normalized=True)
            
            bridge_nodes = {
                node for node, score in centrality.items() 
                if score >= self.bridge_threshold
            }
            
            logger.info(f"Identified {len(bridge_nodes)} structural bridge nodes.")
            return bridge_nodes, centrality

        except Exception as e:
            logger.error(f"Error calculating centrality: {e}")
            return set(), {}

    def _verify_environment_sandbox(self, node_id: str) -> bool:
        """
        Helper Function: Verify node dependencies in a simulated environment.
        
        Checks if required libraries or API versions are present.
        In a real AGI system, this would run in a Docker container.

        Args:
            node_id (str): The node to check.

        Returns:
            bool: True if dependencies are met, False otherwise.
        """
        metadata = self.node_metadata.get(node_id)
        if not metadata or not metadata.get('executable'):
            return True # Non-executable nodes always pass

        deps = metadata.get('dependencies', {})
        
        # Simulation: Check if 'requests' library version matches hypothetical requirement
        # In reality: use importlib.metadata or pkg_resources
        required_lib = deps.get('library')
        required_ver = deps.get('version')
        
        logger.debug(f"Sandbox check for {node_id}: Req {required_lib}=={required_ver}")
        
        # Mock logic for demonstration
        if required_lib == 'legacy_api':
            return False # Simulate a broken dependency
            
        return True

    def run_metabolism_cycle(self, freshness_threshold: float = 0.1) -> Dict[str, Any]:
        """
        Execute a full metabolism cycle: Evaluate, Prune, and Reinforce.
        
        Args:
            freshness_threshold (float): Nodes below this score are candidates for pruning.

        Returns:
            Dict[str, Any]: A report of actions taken.
        """
        logger.info("--- Starting Metabolism Cycle ---")
        
        report = {
            'pruned_nodes': [],
            'reinforced_bridges': [],
            'dep_failures': [],
            'timestamp': datetime.datetime.now().isoformat()
        }

        # 1. Structural Analysis
        bridge_nodes, _ = self.identify_structural_holes()

        # 2. Iterate and Evaluate
        nodes_to_remove = []
        
        for node_id, metadata in list(self.node_metadata.items()):
            if node_id not in self.graph:
                continue

            # Check Freshness
            fresh_score = self.calculate_freshness_score(node_id)
            
            # Check Environment
            env_ok = self._verify_environment_sandbox(node_id)
            if not env_ok:
                report['dep_failures'].append(node_id)
                # If environment is broken, we might force prune or flag for update
                # Here we force a 'warning' by lowering the threshold effectively
                fresh_score *= 0.5 

            # Decision Logic
            is_bridge = node_id in bridge_nodes
            
            # Metabolism Logic: 
            # If it's a bridge node, we protect it (lower threshold).
            # If it's a leaf node and stale, prune it.
            
            effective_threshold = freshness_threshold
            
            if is_bridge:
                # Reinforce: Log it and skip pruning regardless of score if critical
                report['reinforced_bridges'].append(node_id)
                # If it's really stale but structural, we might trigger a 'refresh' task
                if fresh_score < freshness_threshold:
                    logger.warning(f"Bridge Node {node_id} is stale but structurally critical. Maintenance required.")
                continue

            if fresh_score < effective_threshold:
                nodes_to_remove.append(node_id)

        # 3. Execution (Pruning)
        for node_id in nodes_to_remove:
            self.graph.remove_node(node_id)
            del self.node_metadata[node_id]
            report['pruned_nodes'].append(node_id)
            
        logger.info(f"Cycle Complete. Pruned: {len(report['pruned_nodes'])}, Reinforced: {len(report['reinforced_bridges'])}")
        return report

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup
    manager = KnowledgeGraphMetabolismManager(half_life_days=30, bridge_threshold=0.15)

    # 2. Mock Data (Simulating 3445+ nodes is verbose, creating a small structural example)
    # Node A is old, Node B is new, Node C connects two clusters (Bridge)
    mock_nodes = [
        {'id': 'A', 'type': 'data', 'last_accessed': datetime.datetime.now() - datetime.timedelta(days=60)}, # Stale
        {'id': 'B', 'type': 'data', 'last_accessed': datetime.datetime.now() - datetime.timedelta(days=1)},  # Fresh
        {'id': 'C', 'type': 'hub', 'last_accessed': datetime.datetime.now() - datetime.timedelta(days=60)},  # Stale but Bridge
        {'id': 'D', 'type': 'data', 'last_accessed': datetime.datetime.now() - datetime.timedelta(days=60)}, # Stale Leaf
        {'id': 'E', 'type': 'exec', 'last_accessed': datetime.datetime.now(), 'executable': True, 'dependencies': {'library': 'legacy_api'}}, # Broken Dep
    ]
    
    # C connects {A, B} to {D, E}
    mock_edges = [
        {'source': 'A', 'target': 'C'},
        {'source': 'B', 'target': 'C'},
        {'source': 'C', 'target': 'D'},
        {'source': 'C', 'target': 'E'},
        {'source': 'D', 'target': 'E'} # E and D connected
    ]

    manager.load_graph_data(mock_nodes, mock_edges)

    # 3. Run Cycle
    # Threshold 0.2 (Approx 25 days). A is 60 days (score ~0.25), D is 60 days.
    # C is 60 days but should be reinforced.
    # E has broken deps.
    result = manager.run_metabolism_cycle(freshness_threshold=0.3)

    print("\n--- System Report ---")
    print(json.dumps(result, indent=2, default=str))