"""
Module: cognitive_roi_manager.py
Description: Implements the 'Cognitive ROI' algorithm for AGI system optimization.
             It calculates the Return on Investment for memory nodes to determine
             their lifecycle (Active vs. Dormant), optimizing resource usage.

Design Logic:
    ROI Formula:
    $ ROI = \\frac{\\text{Frequency} \\times \\text{AvgValue}}{\\text{VectorDim} \\times \\text{DependencyCount}} $

    Nodes with ROI < System Average are candidates for 'Dormant' status (cold storage).
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveROI")

@dataclass
class CognitiveNode:
    """
    Represents a cognitive node in the AGI system.
    
    Attributes:
        id (str): Unique identifier for the node.
        vector_dim (int): Dimensionality of the node's vector (storage cost proxy).
        dependency_count (int): Number of other nodes depending on this one (maintenance cost).
        call_frequency (int): Number of times accessed in the evaluation window.
        avg_resolution_value (float): Average value generated per problem resolution.
        status (str): Current state ('ACTIVE', 'DORMANT').
    """
    id: str
    vector_dim: int
    dependency_count: int
    call_frequency: int = 0
    avg_resolution_value: float = 0.0
    status: str = 'ACTIVE'

    def __post_init__(self):
        """Data validation and boundary checks."""
        if self.vector_dim <= 0:
            raise ValueError(f"Node {self.id}: vector_dim must be > 0.")
        if self.dependency_count < 0:
            raise ValueError(f"Node {self.id}: dependency_count cannot be negative.")
        if self.avg_resolution_value < 0:
            raise ValueError(f"Node {self.id}: avg_resolution_value cannot be negative.")

class CognitiveROIManager:
    """
    Manages the lifecycle of cognitive nodes based on ROI calculations.
    """

    def __init__(self, dormant_threshold_factor: float = 1.0):
        """
        Initialize the manager.
        
        Args:
            dormant_threshold_factor (float): Multiplier for the average ROI threshold.
                                              Default 1.0 means < Average ROI triggers dormancy.
        """
        self.nodes: Dict[str, CognitiveNode] = {}
        self.dormant_threshold_factor = dormant_threshold_factor
        logger.info("CognitiveROIManager initialized.")

    def add_node(self, node: CognitiveNode) -> None:
        """Register a node to the system."""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        logger.debug(f"Node {node.id} added to system.")

    def _calculate_single_roi(self, node: CognitiveNode) -> float:
        """
        [Helper] Calculate ROI for a single node.
        
        Formula: (Freq * Value) / (Dim * Deps)
        
        Returns:
            float: The ROI score. Returns 0.0 if costs are 0 to avoid ZeroDivisionError 
                   (though validation prevents 0 dim).
        """
        # Boundary check: Prevent division by zero
        denominator = node.vector_dim * max(1, node.dependency_count)
        
        # Check for zero frequency or value to skip computation
        if node.call_frequency == 0 or node.avg_resolution_value == 0:
            return 0.0
            
        roi = (node.call_frequency * node.avg_resolution_value) / denominator
        return roi

    def evaluate_and_optimize(self) -> Dict[str, List[str]]:
        """
        [Core] Main algorithm execution.
        Calculates ROI for all nodes, determines system average,
        and transitions low-performing nodes to DORMANT state.
        
        Returns:
            Dict[str, List[str]]: Report of {'active': [ids], 'dormant': [ids], 'purge_candidates': [ids]}
        """
        logger.info("Starting ROI evaluation cycle...")
        
        if not self.nodes:
            logger.warning("No nodes to evaluate.")
            return {'active': [], 'dormant': []}

        # 1. Calculate all ROIs
        roi_scores = {}
        for node_id, node in self.nodes.items():
            if node.status == 'DORMANT':
                # Optional: Logic to potentially 'wake' dormant nodes could go here
                continue
            
            roi = self._calculate_single_roi(node)
            roi_scores[node_id] = roi

        # 2. Calculate System Average ROI
        if not roi_scores:
            return {'active': [], 'dormant': []}
            
        avg_roi = sum(roi_scores.values()) / len(roi_scores)
        threshold = avg_roi * self.dormant_threshold_factor
        logger.info(f"System Average ROI: {avg_roi:.4f} | Dormancy Threshold: {threshold:.4f}")

        # 3. Determine Node Fate
        report = {'active': [], 'dormant': [], 'purge_candidates': []}

        for node_id, node in self.nodes.items():
            if node.status == 'DORMANT':
                report['dormant'].append(node_id)
                continue

            current_roi = roi_scores.get(node_id, 0.0)

            if current_roi < threshold:
                # Trigger Dormancy
                self._transition_to_dormant(node)
                report['dormant'].append(node_id)
                logger.info(f"Node {node_id} transitioned to DORMANT (ROI: {current_roi:.4f} < {threshold:.4f})")
            else:
                # Keep Active
                report['active'].append(node_id)

        return report

    def _transition_to_dormant(self, node: CognitiveNode) -> None:
        """
        [Core] Handles the logic of moving a node to cold storage.
        In a real system, this would involve serialization and moving vector data to disk.
        """
        if node.status == 'DORMANT':
            return
        
        # Simulation of moving out of hot data layer
        node.status = 'DORMANT'
        # Reset frequency to ensure it doesn't affect next cycle unfairly without new usage
        node.call_frequency = 0 
        
        # Here you would add logic like:
        # vector_db.move_to_cold_storage(node.id)
        # cache.invalidate(node.id)

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Manager
    manager = CognitiveROIManager(dormant_threshold_factor=1.0)

    # 2. Create Nodes
    # High Value Node: Frequently used, high value
    node_vip = CognitiveNode(
        id="skill_python_coding",
        vector_dim=1536,
        dependency_count=5,
        call_frequency=100,
        avg_resolution_value=0.95
    )

    # Low Value Node: Rarely used, low value, high cost
    node_zombie = CognitiveNode(
        id="legacy_fact_1998",
        vector_dim=1536,
        dependency_count=2,
        call_frequency=1,
        avg_resolution_value=0.05
    )

    # Medium Node
    node_mid = CognitiveNode(
        id="context_general",
        vector_dim=512,
        dependency_count=10,
        call_frequency=50,
        avg_resolution_value=0.5
    )

    # 3. Add to Manager
    manager.add_node(node_vip)
    manager.add_node(node_zombie)
    manager.add_node(node_mid)

    # 4. Run Optimization
    print("--- Running Optimization ---")
    result = manager.evaluate_and_optimize()

    # 5. Verify Results
    print(f"Active Nodes: {result['active']}")
    print(f"Dormant Nodes: {result['dormant']}")
    
    # Expected: 'legacy_fact_1998' should be dormant because its ROI is significantly lower
    # than the average of the three nodes.