"""
Module: logical_bubble_red_teamer.py

This module provides tools to detect and eliminate 'Logical Bubbles' (Local Optima)
within a cognitive network. It implements a 'Red Team' node strategy to challenge
high-confidence beliefs, thereby preventing the system from becoming overly
confident in potentially erroneous, self-reinforcing patterns (involution).

Classes:
    CognitiveNode: Represents a unit of belief or information.
    CognitiveNetwork: The graph structure holding the nodes.
    RedTeamAgent: The protagonist class that attacks high-confidence nodes.

Author: AGI System Core
Version: 1.0.0
"""

import logging
import hashlib
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime

# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CognitiveNode:
    """
    Represents a single node in the cognitive network.
    
    Attributes:
        id: Unique identifier for the node.
        content: The semantic content or belief (e.g., "Swans are white").
        confidence: A float between 0.0 and 1.0 representing certainty.
        is_active: Whether the node is currently active.
        metadata: Additional metadata.
    """
    id: str
    content: str
    confidence: float = 0.5
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate data after initialization."""
        self._validate()

    def _validate(self):
        """Ensure confidence is within bounds."""
        if not (0.0 <= self.confidence <= 1.0):
            logger.error(f"Invalid confidence value {self.confidence} for node {self.id}")
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def adjust_confidence(self, delta: float):
        """Adjust confidence safely."""
        self.confidence = max(0.0, min(1.0, self.confidence + delta))
        logger.debug(f"Node {self.id} confidence adjusted to {self.confidence}")


class CognitiveNetwork:
    """
    Represents the network of cognitive nodes.
    Simplified for this skill demonstration (adjacency list omitted for focus on nodes).
    """

    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}

    def add_node(self, node: CognitiveNode):
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        logger.info(f"Added node: {node.id}")

    def get_highest_confidence_node(self) -> Optional[CognitiveNode]:
        """Retrieves the node with the highest confidence (The potential bubble)."""
        if not self.nodes:
            return None
        
        # Sort nodes by confidence descending
        sorted_nodes = sorted(self.nodes.values(), key=lambda x: x.confidence, reverse=True)
        return sorted_nodes[0]


class RedTeamAgent:
    """
    Agent designed to attack high-confidence nodes to detect logical bubbles.
    
    This agent identifies nodes that are 'too confident' (potential local optima)
    and generates counter-arguments or 'falsification attempts'.
    """

    def __init__(self, aggression_level: float = 0.5):
        """
        Initialize the Red Team Agent.
        
        Args:
            aggression_level: How strongly the agent penalizes nodes upon successful attack (0.0 to 1.0).
        """
        self.aggression_level = aggression_level
        self.attack_history: List[Dict] = []
        logger.info(f"RedTeamAgent initialized with aggression {aggression_level}")

    def _validate_attack_input(self, target_node: CognitiveNode) -> bool:
        """Validate if the node is a valid target for red teaming."""
        if not isinstance(target_node, CognitiveNode):
            logger.error("Invalid target: Not a CognitiveNode instance.")
            return False
        if not target_node.is_active:
            logger.warning(f"Target node {target_node.id} is inactive. Skipping attack.")
            return False
        return True

    def _generate_counter_example(self, premise: str) -> Tuple[bool, str]:
        """
        Helper function to simulate the generation of a counter-example.
        
        In a real AGI system, this would query a knowledge base or run a simulation.
        Here, we simulate stochastic success based on content hash to ensure reproducibility
        in testing while appearing random.
        
        Args:
            premise: The content of the belief being attacked.
            
        Returns:
            A tuple (is_falsified, counter_argument).
        """
        # Simulation logic: deterministically 'random' based on content
        hash_val = int(hashlib.md5(premise.encode()).hexdigest(), 16)
        # If the hash is even, we simulate a successful counter-argument discovery
        falsification_success = (hash_val % 2 == 0) or (random.random() > 0.7)
        
        if falsification_success:
            counter = f"Discovered evidence contradicting: '{premise[:20]}...'"
            return True, counter
        else:
            return False, "No immediate counter-example found."

    def attack_node(self, target_node: CognitiveNode) -> Dict:
        """
        Core Function: Attacks a specific node to test its robustness.
        
        This simulates the 'Red Teaming' process.
        
        Args:
            target_node: The cognitive node to challenge.
            
        Returns:
            A report dictionary detailing the attack results.
        """
        if not self._validate_attack_input(target_node):
            return {"status": "skipped", "reason": "invalid_input"}

        logger.info(f"Attacking node {target_node.id} ('{target_node.content[:30]}...')")
        
        # Attempt to find a counter-example
        falsified, counter_arg = self._generate_counter_example(target_node.content)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_id": target_node.id,
            "original_confidence": target_node.confidence,
            "falsified": falsified,
            "counter_argument": counter_arg
        }

        if falsified:
            # Penalize the node (Popping the bubble)
            penalty = -0.2 * self.aggression_level
            target_node.adjust_confidence(penalty)
            report["new_confidence"] = target_node.confidence
            report["status"] = "success_bubble_popped"
            logger.warning(f"BUBBLE DETECTED: Node {target_node.id} falsified. Confidence reduced.")
        else:
            # Reinforce the node (It survived the attack)
            reward = 0.05 * (1.0 - self.aggression_level) # Small reward for resilience
            target_node.adjust_confidence(reward)
            report["new_confidence"] = target_node.confidence
            report["status"] = "failed_node_resilient"
            logger.info(f"Node {target_node.id} survived attack. Confidence boosted slightly.")

        self.attack_history.append(report)
        return report

    def scan_and_attack_network(self, network: CognitiveNetwork, threshold: float = 0.85) -> List[Dict]:
        """
        Core Function: Scans the network for high-confidence nodes and attacks the highest one.
        
        This prevents 'involution' by ensuring the system never gets too comfortable
        with a single unverified belief.
        
        Args:
            network: The cognitive network to scan.
            threshold: Confidence level above which a node is considered a potential bubble.
            
        Returns:
            List of attack reports.
        """
        target = network.get_highest_confidence_node()
        if not target:
            logger.info("Network is empty. No targets.")
            return []

        reports = []
        
        # Only attack if the node is suspiciously confident (Local Optima)
        if target.confidence >= threshold:
            logger.info(f"Targeting potential logical bubble: {target.id} (Conf: {target.confidence})")
            report = self.attack_node(target)
            reports.append(report)
        else:
            logger.info("No nodes exceed confidence threshold for red teaming.")
            
        return reports


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Network
    net = CognitiveNetwork()
    
    # 2. Create Nodes (Simulating a system building beliefs)
    # 'Swans are white' is a classic induction problem
    node_1 = CognitiveNode(id="b_001", content="All swans are white", confidence=0.95)
    # 'Water boils at 100C' (Robust belief)
    node_2 = CognitiveNode(id="b_002", content="Water boils at 100C at sea level", confidence=0.99)
    # 'Earth is flat' (Erroneous high confidence)
    node_3 = CognitiveNode(id="b_003", content="Earth is flat", confidence=0.90)
    
    net.add_node(node_1)
    net.add_node(node_2)
    net.add_node(node_3)
    
    # 3. Initialize Red Team
    # High aggression means we penalize confidence heavily when a bubble is found
    red_agent = RedTeamAgent(aggression_level=0.8)
    
    # 4. Run Scan
    # We scan for nodes with confidence > 0.8
    print("\n--- Starting Red Team Operation ---")
    attack_results = red_agent.scan_and_attack_network(net, threshold=0.8)
    
    print("\n--- Results ---")
    for res in attack_results:
        print(f"Target: {res['target_id']}")
        print(f"Status: {res['status']}")
        print(f"Confidence Change: {res['original_confidence']:.2f} -> {res['new_confidence']:.2f}")
        print("-" * 20)
        
    # Check final state
    print("\n--- Final Network State ---")
    for node in net.nodes.values():
        print(f"Node {node.id}: {node.confidence:.2f}")