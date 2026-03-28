"""
Module: harmonic_forgetting_algorithm
Description: Implements a dynamic forgetting algorithm based on the Harmonic Overtone Series Tension Model.
             This module replaces traditional linear or exponential decay with an ADSR (Attack-Decay-Sustain-Release)
             envelope approach, simulating human auditory persistence and cognitive memory retention.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for default ADSR envelope (values are fractions of the total lifecycle or time in seconds)
DEFAULT_ATTACK = 0.1  # Immediate high tension
DEFAULT_DECAY = 0.2   # Rapid drop from peak
DEFAULT_SUSTAIN_LEVEL = 0.6  # Long-term retention level
DEFAULT_RELEASE = 0.1  # Rate of drop to background noise after sustain phase expires
BACKGROUND_NOISE_THRESHOLD = 0.05  # Weight below which memory is considered 'background noise'


@dataclass
class ADSREnvelope:
    """
    Represents the Attack-Decay-Sustain-Release envelope parameters for a memory node.
    """
    attack_time: float = 0.0  # Time to reach peak (seconds)
    decay_time: float = 60.0  # Time to fall from peak to sustain level (seconds)
    sustain_level: float = 0.7  # The stable weight level during sustain phase
    release_time: float = 3600.0  # Time to drop from sustain to 0 after 'active' phase (seconds)
    peak_weight: float = 1.0  # Maximum tension/weight at creation/access

    def __post_init__(self):
        """Validate envelope parameters."""
        if not (0.0 <= self.sustain_level <= 1.0):
            raise ValueError("Sustain level must be between 0.0 and 1.0")
        if self.decay_time < 0 or self.release_time < 0:
            raise ValueError("Time values cannot be negative")


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge/memory in the system.
    """
    node_id: str
    content: str
    creation_time: float = field(default_factory=time.time)
    last_access_time: float = field(default_factory=time.time)
    envelope: ADSREnvelope = field(default_factory=ADSREnvelope)
    current_weight: float = 1.0  # Initial tension

    def update_access(self):
        """Reset the envelope trigger upon access (reactivation)."""
        logger.debug(f"Node {self.node_id} accessed. Resetting envelope.")
        self.last_access_time = time.time()
        # Reactivation applies a new Attack burst
        self.current_weight = self.envelope.peak_weight


class HarmonicMemoryManager:
    """
    Manages knowledge nodes using a Harmonic Overtone Tension Model (ADSR-based forgetting).
    """

    def __init__(self, default_envelope: Optional[ADSREnvelope] = None):
        """
        Initialize the memory manager.

        Args:
            default_envelope (Optional[ADSREnvelope]): The default envelope for new nodes.
        """
        self.memory_store: Dict[str, KnowledgeNode] = {}
        self.default_envelope = default_envelope or ADSREnvelope()
        logger.info("HarmonicMemoryManager initialized.")

    def add_node(self, node_id: str, content: str, custom_envelope: Optional[ADSREnvelope] = None) -> None:
        """
        Add a new knowledge node to the memory system.

        Args:
            node_id (str): Unique identifier for the node.
            content (str): The data/content to store.
            custom_envelope (Optional[ADSREnvelope]): Custom ADSR settings for this specific node.
        """
        if node_id in self.memory_store:
            logger.warning(f"Node {node_id} already exists. Updating content and refreshing envelope.")
            self.memory_store[node_id].content = content
            self.memory_store[node_id].update_access()
            return

        envelope = custom_envelope if custom_envelope else self.default_envelope
        new_node = KnowledgeNode(
            node_id=node_id,
            content=content,
            envelope=envelope,
            current_weight=envelope.peak_weight
        )
        self.memory_store[node_id] = new_node
        logger.info(f"Created new node: {node_id} with peak tension {envelope.peak_weight}")

    def access_node(self, node_id: str) -> Optional[str]:
        """
        Access a node (recall memory). This triggers the 'Attack' phase again,
        reinforcing the memory.

        Args:
            node_id (str): The ID of the node to access.

        Returns:
            Optional[str]: The content of the node, or None if not found.
        """
        if node_id not in self.memory_store:
            logger.error(f"Access failed: Node {node_id} not found.")
            return None

        node = self.memory_store[node_id]
        node.update_access()
        return node.content

    def _calculate_adsr_weight(self, node: KnowledgeNode, current_time: float) -> float:
        """
        Core Algorithm: Calculate the dynamic weight based on the ADSR envelope.
        This simulates the 'Tension' of the memory trace over time.

        Time phases:
        1. Attack: Instantaneous in this implementation (weight set to peak on access).
        2. Decay: Non-linear drop from Peak to Sustain level.
        3. Sustain: Holds at Sustain level (simulating stable memory).
        4. Release: Non-linear drop from Sustain to 0 (Forgetting).

        Args:
            node (KnowledgeNode): The node to calculate weight for.
            current_time (float): The current timestamp.

        Returns:
            float: The calculated weight (tension).
        """
        delta_time = current_time - node.last_access_time
        env = node.envelope

        # Phase 1: Attack (Handled by update_access, but good to be aware)
        # Phase 2: Decay (Transition from Peak to Sustain)
        if delta_time < env.decay_time:
            # Using a cosine interpolation for smooth decay (simulating harmonic dissipation)
            # Progress goes from 0.0 to 1.0 over decay_time
            progress = delta_time / env.decay_time
            # Weight drops from peak to sustain
            decay_range = env.peak_weight - env.sustain_level
            # Non-linear decay: faster drop initially, slowing down as it approaches sustain
            calculated_weight = env.peak_weight - (decay_range * (1 - math.cos(progress * math.pi / 2)))
            return calculated_weight

        # Phase 3: Sustain
        # If we assume infinite sustain, it stays here. However, for a 'forgetting' algorithm,
        # we usually want a very long 'Release' phase after a certain implicit time,
        # or we treat Sustain as a plateau until a global 'system fatigue' kicks in.
        # For this implementation, we model Release as starting after Decay.
        # (Alternative model: Sustain lasts for X duration, then Release).
        # Let's implement: Decay -> Immediate Sustain Level -> Release begins immediately but slowly.

        # Time elapsed since decay finished
        release_delta = delta_time - env.decay_time
        
        # Phase 4: Release (The Forgetting Curve)
        if release_delta > 0:
            # Exponential decay relative to release time constant
            # Formula: Sustain * e^(-k * t)
            # To ensure it hits near-zero eventually, we use a decay factor
            release_factor = math.exp(-release_delta / env.release_time) if env.release_time > 0 else 0
            current_weight = env.sustain_level * release_factor
            
            # Floor the weight at background noise level
            if current_weight < BACKGROUND_NOISE_THRESHOLD:
                return BACKGROUND_NOISE_THRESHOLD
            return current_weight

        return env.sustain_level

    def update_memory_state(self) -> List[str]:
        """
        Update weights for all nodes and identify 'forgotten' nodes (background noise).
        This is the 'Dynamic Forgetting' step.

        Returns:
            List[str]: List of node IDs that have decayed to background noise level.
        """
        current_time = time.time()
        noise_nodes = []

        logger.info("Starting global memory state update...")
        
        for node_id, node in list(self.memory_store.items()):
            old_weight = node.current_weight
            node.current_weight = self._calculate_adsr_weight(node, current_time)
            
            # Check for transition to background noise
            if old_weight > BACKGROUND_NOISE_THRESHOLD and node.current_weight <= BACKGROUND_NOISE_THRESHOLD:
                logger.info(f"Node {node_id} has faded into background noise (Weight: {node.current_weight:.4f}).")
                noise_nodes.append(node_id)

        return noise_nodes

    def get_memory_snapshot(self) -> Dict[str, float]:
        """
        Returns a snapshot of current node weights.
        """
        return {nid: node.current_weight for nid, node in self.memory_store.items()}


# --- Utility Functions ---

def format_memory_report(memory_manager: HarmonicMemoryManager) -> str:
    """
    Generates a formatted string report of the current memory state.

    Args:
        memory_manager (HarmonicMemoryManager): The manager instance.

    Returns:
        str: A formatted report.
    """
    snapshot = memory_manager.get_memory_snapshot()
    if not snapshot:
        return "Memory is empty."
    
    report_lines = ["--- Memory Tension Report ---"]
    for nid, weight in sorted(snapshot.items(), key=lambda item: item[1], reverse=True):
        status = "ACTIVE" if weight > 0.6 else "SUSTAINING" if weight > 0.2 else "FADING" if weight > BACKGROUND_NOISE_THRESHOLD else "NOISE"
        bar = "#" * int(weight * 20)
        report_lines.append(f"{nid:<15} | {weight:.3f} | {status:<10} | {bar}")
    
    return "\n".join(report_lines)


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup the Memory Manager
    # Configure a specific envelope: Fast decay, long sustain, slow release
    custom_env = ADSREnvelope(
        attack_time=0.0,
        decay_time=5.0,     # Drops to sustain in 5 seconds (for demo purposes)
        sustain_level=0.8,  # High retention
        release_time=10.0   # Slowly forgets after sustain
    )
    
    manager = HarmonicMemoryManager(default_envelope=custom_env)

    # 2. Add Nodes (Knowledge Creation)
    manager.add_node("py_syntax", "Python basic syntax rules")
    manager.add_node("api_endpoint", "REST API authentication logic")
    
    print("\n[Initial State]")
    print(format_memory_report(manager))

    # 3. Simulate Time Passing (Partial Decay)
    print("\nWaiting 3 seconds (Decay Phase)...")
    time.sleep(3)
    manager.update_memory_state()
    print(format_memory_report(manager))

    # 4. Access a node (Reactivate Tension)
    print("\nAccessing 'py_syntax' to reinforce memory...")
    manager.access_node("py_syntax")
    manager.update_memory_state() # Update to see immediate effect
    print(format_memory_report(manager))

    # 5. Simulate Long Time Passing (Release/Forgetting)
    print("\nWaiting 10 seconds (Release Phase)...")
    time.sleep(10)
    manager.update_memory_state()
    print(format_memory_report(manager))