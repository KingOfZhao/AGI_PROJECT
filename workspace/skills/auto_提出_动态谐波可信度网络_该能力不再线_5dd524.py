"""
Module: dynamic_harmonic_credibility_network.py

Description:
    Implements the 'Dynamic Harmonic Credibility Network' (DHC-NET).
    This module moves beyond linear knowledge decay by employing a musical
    harmony-inspired tension model. It treats under-utilized knowledge not
    just as 'decaying', but as creating 'dissonance' that must be resolved.
    
    The lifecycle of a knowledge node follows a musical 'Cadence':
    1. Preparation (Preparation): Identifying long-unused nodes (Dissonance).
    2. Passing Tone (Verification): Generating active probes/test cases to verify validity.
    3. Resolution (Resolution): Updating weights, archiving, or accepting the new state.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum, auto

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DHC-NET")


class KnowledgeState(Enum):
    """Defines the current harmonic state of a knowledge node."""
    CONSONANT = auto()      # Stable, frequently used, trusted.
    DISSONANT = auto()      # Tension detected (long unused), pending resolution.
    RESOLVING = auto()      # Active verification (passing tone) in progress.
    RESOLVED = auto()       # Verification complete, state updated.


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the network.
    
    Attributes:
        id: Unique identifier.
        content: The actual knowledge payload (e.g., a solution script).
        weight: Current credibility/strength (0.0 to 1.0).
        last_called: Timestamp of the last successful usage.
        state: Current harmonic state.
        dissonance_score: Calculated tension based on time decay.
    """
    id: str
    content: Any
    weight: float = 1.0
    last_called: float = field(default_factory=time.time)
    state: KnowledgeState = KnowledgeState.CONSONANT
    dissonance_score: float = 0.0
    
    def update_usage(self):
        """Refreshes the node state upon successful usage."""
        self.last_called = time.time()
        self.dissonance_score = 0.0
        self.state = KnowledgeState.CONSONANT
        logger.info(f"Node {self.id} usage refreshed. State: CONSONANT.")


class HarmonicCredibilityNetwork:
    """
    The core network engine that manages knowledge nodes using musical harmony dynamics.
    """
    
    def __init__(self, dissonance_threshold_hours: float = 24.0, resolution_strategy: str = "auto"):
        """
        Initialize the network.
        
        Args:
            dissonance_threshold_hours: Time in hours before a node is considered 'dissonant'.
            resolution_strategy: Strategy for resolution ('auto' or 'manual').
        """
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.dissonance_threshold_sec = dissonance_threshold_hours * 3600
        self.resolution_strategy = resolution_strategy
        logger.info(f"Network initialized with threshold: {dissonance_threshold_hours}h")

    def add_node(self, node_id: str, content: Any) -> bool:
        """Adds a new knowledge node to the network."""
        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already exists.")
            return False
        
        if not content:
            raise ValueError("Node content cannot be empty.")
            
        new_node = KnowledgeNode(id=node_id, content=content)
        self.nodes[node_id] = new_node
        logger.info(f"New node added: {node_id}")
        return True

    def _calculate_dissonance(self, node: KnowledgeNode) -> float:
        """
        Helper: Calculate the 'musical tension' (dissonance) of a node.
        Dissonance grows non-linearly with time since last call.
        """
        current_time = time.time()
        time_delta = current_time - node.last_called
        
        # Non-linear tension: Sigmoid or Exponential growth
        # Here using a simplified parabolic growth relative to threshold
        if time_delta < self.dissonance_threshold_sec:
            return 0.0
            
        excess_time = time_delta - self.dissonance_threshold_sec
        # Tension increases sharply the longer it sits
        tension = min(1.0, (excess_time / self.dissonance_threshold_sec) ** 1.5)
        return tension

    def observe_interference(self) -> List[str]:
        """
        Core Function 1: Observe Interference (Scan for Dissonance).
        Iterates through nodes to find those creating 'harmonic tension' (staleness).
        Instead of simple linear decay, we flag them for 'Resolution'.
        
        Returns:
            List of node IDs identified as dissonant.
        """
        dissonant_ids = []
        logger.info("Scanning network for harmonic interference (stale knowledge)...")
        
        for node_id, node in self.nodes.items():
            if node.state == KnowledgeState.RESOLVING:
                continue
                
            tension = self._calculate_dissonance(node)
            node.dissonance_score = tension
            
            if tension > 0.7: # High tension threshold
                node.state = KnowledgeState.DISSONANT
                dissonant_ids.append(node_id)
                logger.warning(f"DISSONANCE detected in node {node_id} (Score: {tension:.2f})")
                
        return dissonant_ids

    def resolve_cadence(self, node_id: str, verification_func: Optional[Callable[[Any], bool]] = None) -> str:
        """
        Core Function 2: Resolve Cadence.
        Executes the transition from Dissonance -> Consonance via a 'Passing Tone' (Verification).
        
        Process:
        1. Check if node is valid for resolution.
        2. Perform 'Passing Tone' (Verification Test).
        3. 'Resolve' to new state (Lower weight or Refresh).
        
        Args:
            node_id: The ID of the node to resolve.
            verification_func: A callable that takes node content and returns True if valid.
                               If None, uses internal dummy test.
                               
        Returns:
            Status string: 'RESOLVED_VALID', 'RESOLVED_DEPRECATED', or 'ERROR'.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found.")
            return "ERROR_NOT_FOUND"
            
        node = self.nodes[node_id]
        if node.state != KnowledgeState.DISSONANT:
            logger.info(f"Node {node_id} is not in dissonance. No resolution needed.")
            return "SKIPPED"

        logger.info(f"Initiating Cadence Resolution for {node_id}...")
        node.state = KnowledgeState.RESOLVING

        try:
            # --- The Passing Tone (Active Verification) ---
            is_valid = False
            if verification_func:
                logger.info("Executing external verification logic (Passing Tone)...")
                is_valid = verification_func(node.content)
            else:
                # Internal fallback: Simulate a test case (e.g., syntax check or mock run)
                logger.info("Executing internal mock verification...")
                time.sleep(0.1) # Simulate processing
                # Randomly determine success for simulation purposes
                is_valid = random.choice([True, False])
            
            # --- The Resolution ---
            if is_valid:
                logger.info(f"Resolution: Node {node_id} verified VALID. Weight restored.")
                node.weight = min(1.0, node.weight + 0.2) # Reward for surviving
                node.update_usage() # Reset timer
                node.state = KnowledgeState.CONSONANT
                return "RESOLVED_VALID"
            else:
                logger.warning(f"Resolution: Node {node_id} FAILED verification. Applying decay.")
                node.weight *= 0.5 # Penalize
                if node.weight < 0.1:
                    logger.critical(f"Node {node_id} weight critical. Marking for archival.")
                    node.state = KnowledgeState.RESOLVED # But effectively dead
                else:
                    node.state = KnowledgeState.DISSONANT # Keep trying or manual fix
                return "RESOLVED_DEPRECATED"

        except Exception as e:
            logger.error(f"Error during resolution of {node_id}: {str(e)}")
            node.state = KnowledgeState.DISSONANT # Revert state
            return "ERROR"

# --- Usage Example & Demonstration ---

def mock_it_solution_verifier(solution: dict) -> bool:
    """
    Mock external verifier.
    Expects solution to be a dict with 'port' and 'protocol'.
    Returns False if port is 8080 (simulating an obsolete config).
    """
    logger.info(f"Verifying solution config: {solution}")
    if solution.get("port") == 8080:
        return False # Simulate failure (port blocked)
    return True

if __name__ == "__main__":
    # Initialize Network
    net = HarmonicCredibilityNetwork(dissonance_threshold_hours=0.0001) # Very short threshold for demo
    
    # Add Knowledge Nodes (e.g., IT Fix Scripts)
    # Node 1: A healthy SSH restart script
    net.add_node("fix_ssh", {"cmd": "systemctl restart sshd", "port": 22})
    
    # Node 2: An old HTTP proxy config (Potentially obsolete)
    net.add_node("fix_proxy", {"cmd": "service httpd restart", "port": 8080})
    
    # Simulate time passing by backdating the 'fix_proxy' node
    import datetime
    # Make it look like it was last called 1 year ago
    old_time = time.time() - (365 * 24 * 3600)
    net.nodes["fix_proxy"].last_called = old_time
    
    print("\n--- Step 1: Observing Interference ---")
    # Check for dissonance
    dissonant_nodes = net.observe_interference()
    print(f"Dissonant nodes found: {dissonant_nodes}")
    
    print("\n--- Step 2: Resolving Cadence ---")
    if "fix_proxy" in dissonant_nodes:
        print("Attempting to resolve 'fix_proxy'...")
        # Pass the mock verifier
        result = net.resolve_cadence("fix_proxy", verification_func=mock_it_solution_verifier)
        print(f"Resolution Result: {result}")
        
    print("\n--- Final Network State ---")
    for nid, node in net.nodes.items():
        print(f"Node: {nid} | State: {node.state.name} | Weight: {node.weight:.2f}")