"""
Module: meta_cognitive_falsification_engine
This module implements a meta-cognitive subsystem designed for top-down decomposition and falsification.
It generates stress tests and hallucination penetration scenarios to validate cognitive nodes.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MetaCognitiveFalsification")

class NodeState(Enum):
    """Enumeration of possible states for a cognitive node."""
    UNVERIFIED = 0
    VERIFIED = 1
    FALSIFIED = 2
    HALLUCINATED = 3

@dataclass
class CognitiveNode:
    """
    Represents a unit of knowledge or a plan in the cognitive network.
    
    Attributes:
        id: Unique identifier for the node.
        content: The core proposition or plan logic.
        state: Current verification state of the node.
        confidence: Internal confidence score (0.0 to 1.0).
        dependencies: List of child node IDs required for this node to be true.
    """
    id: str
    content: str
    state: NodeState = NodeState.UNVERIFIED
    confidence: float = 1.0
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

class FalsificationEngine:
    """
    Engine for top-down decomposition and falsification of cognitive structures.
    
    This engine attempts to disprove nodes by simulating edge cases, 
    resource constraints, and logical contradictions.
    """

    def __init__(self, initial_nodes: Optional[List[CognitiveNode]] = None):
        """
        Initialize the engine with an optional list of nodes.
        
        Args:
            initial_nodes: List of CognitiveNode objects to populate the network.
        """
        self.network: Dict[str, CognitiveNode] = {}
        self.falsification_log: List[Dict[str, Any]] = []
        if initial_nodes:
            for node in initial_nodes:
                self.add_node(node)
        logger.info("FalsificationEngine initialized.")

    def add_node(self, node: CognitiveNode) -> None:
        """Add a node to the cognitive network."""
        if not isinstance(node, CognitiveNode):
            raise TypeError("Only CognitiveNode objects can be added.")
        if node.id in self.network:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.network[node.id] = node
        logger.debug(f"Node {node.id} added to network.")

    def _generate_hallucination_test(self, node: CognitiveNode) -> Dict[str, Any]:
        """
        Internal helper to generate a 'Hallucination Penetration Test'.
        
        It creates a scenario designed to check if the node relies on non-existent
        assumptions or false premises.
        
        Args:
            node: The node to test.
            
        Returns:
            A dictionary containing the test scenario and expected outcome.
        """
        # Simulate generating a test case that targets the weakest link
        stress_factor = random.choice(["logical_contradiction", "resource_scarcity", "temporal_paradox"])
        
        test_scenario = {
            "target_node": node.id,
            "test_type": "HALLUCINATION_PENETRATION",
            "stress_factor": stress_factor,
            "description": f"Testing {node.content} against {stress_factor}",
            "pass_condition": "Consistency maintained"
        }
        logger.info(f"Generated hallucination test for node {node.id}: {stress_factor}")
        return test_scenario

    def _execute_pulse_feedback(self, node_id: str, failure_signal: bool) -> None:
        """
        Internal helper to propagate negative feedback through the network (Pulse Feedback).
        
        If a node is falsified, this reduces confidence in parent nodes immediately.
        
        Args:
            node_id: ID of the node where the failure occurred.
            failure_signal: Boolean indicating if a failure happened.
        """
        if not failure_signal:
            return

        logger.warning(f"PULSE FEEDBACK triggered by node {node_id}")
        
        # Find nodes that depend on the failed node (Reverse lookup simulation)
        for parent_id, parent_node in self.network.items():
            if node_id in parent_node.dependencies:
                # Apply penalty
                old_confidence = parent_node.confidence
                parent_node.confidence *= 0.5  # Sharp decay
                
                logger.info(
                    f"Confidence decay propagated to parent {parent_id}: "
                    f"{old_confidence:.2f} -> {parent_node.confidence:.2f}"
                )
                
                # If confidence drops too low, mark as falsified
                if parent_node.confidence < 0.2:
                    parent_node.state = NodeState.FALSIFIED
                    self.falsification_log.append({
                        "timestamp": time.time(),
                        "node": parent_id,
                        "reason": "Downstream failure propagation"
                    })

    def verify_node_integrity(self, node_id: str, simulation_depth: int = 2) -> Tuple[bool, str]:
        """
        Core Function 1: Verifies the integrity of a specific node via decomposition.
        
        It recursively checks dependencies and runs hallucination tests.
        
        Args:
            node_id: The ID of the node to verify.
            simulation_depth: How deep to check dependencies.
            
        Returns:
            A tuple (is_valid, message).
            
        Raises:
            ValueError: If node_id does not exist.
        """
        if node_id not in self.network:
            raise ValueError(f"Node {node_id} not found in network.")
            
        node = self.network[node_id]
        logger.info(f"Starting verification for node: {node_id}")
        
        # Step 1: Check dependencies (Top-down decomposition)
        if node.dependencies and simulation_depth > 0:
            for dep_id in node.dependencies:
                is_valid, _ = self.verify_node_integrity(dep_id, simulation_depth - 1)
                if not is_valid:
                    node.state = NodeState.FALSIFIED
                    msg = f"Dependency {dep_id} failed verification."
                    logger.error(msg)
                    return False, msg
        
        # Step 2: Generate and run hallucination tests
        test_case = self._generate_hallucination_test(node)
        
        # Mock execution logic: Randomly fail for simulation purposes
        # In a real AGI, this would query a world model or logic engine
        is_falsified = random.random() < 0.3  # 30% chance of catching a hallucination
        
        if is_falsified:
            node.state = NodeState.HALLUCINATED
            self._execute_pulse_feedback(node_id, True)
            return False, f"Node failed {test_case['stress_factor']} test."
        
        # If passed
        node.state = NodeState.VERIFIED
        return True, "Node verified successfully."

    def run_system_stress_test(self, resource_limit: float = 0.1) -> Dict[str, Any]:
        """
        Core Function 2: Runs a global stress test on the entire network.
        
        Simulates a resource-constrained environment to identify fragile nodes.
        
        Args:
            resource_limit: A factor (0.0-1.0) representing available resources.
            
        Returns:
            A report dictionary containing failed and survived nodes.
        """
        if not (0.0 < resource_limit < 1.0):
            raise ValueError("Resource limit must be a float between 0.0 and 1.0.")

        logger.info(f"Initiating system stress test with resource limit: {resource_limit}")
        
        report = {
            "total_nodes": len(self.network),
            "failed_nodes": [],
            "survived_nodes": [],
            "test_type": "BOUNDARY_PRESSURE"
        }
        
        for node_id, node in self.network.items():
            # Simulate processing cost
            cost = random.random()
            
            if cost > resource_limit:
                # Node cannot be sustained under resource constraint
                node.state = NodeState.FALSIFIED
                report["failed_nodes"].append(node_id)
                self._execute_pulse_feedback(node_id, True)
                logger.warning(f"Node {node_id} CRASHED under resource pressure (Cost: {cost:.2f}).")
            else:
                report["survived_nodes"].append(node_id)
                logger.debug(f"Node {node_id} survived (Cost: {cost:.2f}).")
                
        return report

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Setup sample nodes
    node_a = CognitiveNode(id="A", content="Acquire Resource X", confidence=0.9)
    node_b = CognitiveNode(id="B", content="Process Resource X", dependencies=["A"], confidence=0.8)
    node_c = CognitiveNode(id="C", content="Deliver Product Y", dependencies=["B"], confidence=0.95)
    
    # Initialize Engine
    engine = FalsificationEngine([node_a, node_b, node_c])
    
    print("\n--- Starting Verification ---")
    # Verify the top-level node
    is_valid, msg = engine.verify_node_integrity("C")
    print(f"Result for Node C: {is_valid} - {msg}")
    
    print("\n--- Starting Stress Test ---")
    # Run stress test
    stress_report = engine.run_system_stress_test(resource_limit=0.5)
    print(f"Stress Test Report: {stress_report}")
    
    print("\n--- Final Network State ---")
    for nid, n in engine.network.items():
        print(f"Node {nid}: State={n.state.name}, Confidence={n.confidence:.2f}")