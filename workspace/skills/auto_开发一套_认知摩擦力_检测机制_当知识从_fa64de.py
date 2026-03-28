"""
Module: cognitive_friction_detector.py

Description:
    Implements a 'Cognitive Friction' detection mechanism for AGI systems.
    
    This system detects semantic loss when knowledge is transposed from 
    domains of high mathematical logic (e.g., Quantum Mechanics) to domains 
    of high fuzzy logic (e.g., Art Creation). It calculates a friction score,
    estimates semantic loss, and generates 'Explanatory Bridge Nodes' to 
    facilitate knowledge transfer.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configurations ---
FRICTION_THRESHOLD_HIGH = 0.75
SEMANTIC_LOSS_CRITICAL = 0.6

@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge in the semantic graph.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge content (string or data).
        domain_type: 'logic' (math/physics) or 'fuzzy' (art/emotion).
        density: Information density (0.0 to 1.0). Logic domains usually have higher density.
        entropy: Uncertainty or ambiguity level (0.0 to 1.0).
    """
    id: str
    content: str
    domain_type: str  # 'logic' or 'fuzzy'
    density: float = 0.5
    entropy: float = 0.5

    def __post_init__(self):
        """Validate data after initialization."""
        if self.domain_type not in ['logic', 'fuzzy']:
            raise ValueError(f"Invalid domain type: {self.domain_type}")
        if not (0.0 <= self.density <= 1.0) or not (0.0 <= self.entropy <= 1.0):
            raise ValueError("Density and Entropy must be between 0.0 and 1.0")


@dataclass
class BridgeNode:
    """
    Represents an explanatory node generated to bridge cognitive gaps.
    """
    source_id: str
    target_id: str
    explanation: str
    friction_score: float
    semantic_loss_rate: float


class CognitiveFrictionAnalyzer:
    """
    Core class for analyzing and bridging cognitive friction between knowledge domains.
    """

    def __init__(self, friction_threshold: float = FRICTION_THRESHOLD_HIGH):
        """
        Initialize the analyzer.

        Args:
            friction_threshold: The threshold above which intervention is required.
        """
        self.friction_threshold = friction_threshold
        logger.info("CognitiveFrictionAnalyzer initialized with threshold %.2f", friction_threshold)

    def _calculate_domain_distance(self, source: KnowledgeNode, target: KnowledgeNode) -> float:
        """
        Helper function to calculate the conceptual distance between domains.
        
        Args:
            source: The source knowledge node.
            target: The target knowledge node.
            
        Returns:
            A float representing distance (0.0 to 1.0).
        """
        # Logic -> Fuzzy implies high distance if entropy difference is large
        if source.domain_type == 'logic' and target.domain_type == 'fuzzy':
            # Distance increases with the difference in structure (density vs entropy)
            return min(1.0, abs(source.density - target.entropy) + 0.4)
        
        # Fuzzy -> Logic implies translation difficulty
        elif source.domain_type == 'fuzzy' and target.domain_type == 'logic':
            return min(1.0, abs(source.entropy - target.density) + 0.3)
            
        # Same domain transfer
        return max(0.0, abs(source.density - target.density) * 0.5)

    def detect_friction(self, source: KnowledgeNode, target: KnowledgeNode) -> Tuple[float, float]:
        """
        Calculates the cognitive friction score and estimated semantic loss rate.
        
        Cognitive Friction = (Domain Distance * Information Density Delta) + Entropy Barrier
        
        Args:
            source: Source knowledge node.
            target: Target knowledge node.
            
        Returns:
            Tuple[float, float]: (friction_score, semantic_loss_rate)
            
        Raises:
            ValueError: If nodes are invalid.
        """
        if not isinstance(source, KnowledgeNode) or not isinstance(target, KnowledgeNode):
            logger.error("Invalid input types for friction detection.")
            raise TypeError("Inputs must be KnowledgeNode instances")

        logger.debug(f"Analyzing friction between {source.id} and {target.id}")

        try:
            # 1. Calculate base domain distance
            distance = self._calculate_domain_distance(source, target)
            
            # 2. Calculate Information Density Delta
            # Moving from high density to low density might cause 'compression artifacts'
            density_delta = abs(source.density - target.density)
            
            # 3. Entropy Barrier (Trying to fit precise info into a chaotic system or vice versa)
            entropy_barrier = (source.entropy + target.entropy) / 2.0
            if source.domain_type == 'logic':
                entropy_barrier = 1.0 - source.entropy # Logic has low entropy, barrier is high if target is fuzzy

            # 4. Calculate Friction Score
            friction_score = (distance * 0.5) + (density_delta * 0.3) + (entropy_barrier * 0.2)
            
            # 5. Calculate Semantic Loss
            # Loss is probabilistic based on friction
            semantic_loss = math.tanh(friction_score * 1.5) # Non-linear scaling
            
            # Boundary checks
            friction_score = max(0.0, min(1.0, friction_score))
            semantic_loss = max(0.0, min(1.0, semantic_loss))
            
            logger.info(f"Result: Friction={friction_score:.3f}, Loss={semantic_loss:.3f}")
            return friction_score, semantic_loss

        except Exception as e:
            logger.exception("Error during friction calculation: ")
            raise RuntimeError("Failed to calculate cognitive friction") from e

    def generate_bridge_node(self, source: KnowledgeNode, target: KnowledgeNode) -> Optional[BridgeNode]:
        """
        Generates an explanatory bridge node if friction exceeds the threshold.
        
        Args:
            source: Source knowledge node.
            target: Target knowledge node.
            
        Returns:
            BridgeNode if intervention is needed, otherwise None.
        """
        friction, loss = self.detect_friction(source, target)

        if friction < self.friction_threshold:
            logger.info("Friction is within acceptable limits. No bridge needed.")
            return None

        logger.warning(f"High cognitive friction detected ({friction:.2f}). Generating bridge...")
        
        # Logic to generate explanation (Simulated)
        explanation = self._synthesize_bridge_explanation(source, target, loss)
        
        bridge = BridgeNode(
            source_id=source.id,
            target_id=target.id,
            explanation=explanation,
            friction_score=friction,
            semantic_loss_rate=loss
        )
        
        return bridge

    def _synthesize_bridge_explanation(self, source: KnowledgeNode, target: KnowledgeNode, loss: float) -> str:
        """
        Helper function to generate natural language explanation for the bridge.
        """
        if loss > SEMANTIC_LOSS_CRITICAL:
            return (f"CRITICAL WARNING: Transferring '{source.content}' ({source.domain_type}) "
                    f"to '{target.domain_type}' context risks {loss:.1%} semantic distortion. "
                    f"Recommended: Use metaphorical abstraction layer.")
        else:
            return (f"Advisory: Mapping precise concepts from '{source.content}' "
                    f"to the ambiguous domain of '{target.content}'. "
                    f"Expect {loss:.1%} interpretive variance.")

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize System
    analyzer = CognitiveFrictionAnalyzer(friction_threshold=0.7)

    # Define Knowledge Nodes
    # Case 1: Quantum Physics -> Abstract Art
    node_physics = KnowledgeNode(
        id="phys_01",
        content="Wave Function Collapse",
        domain_type="logic",
        density=0.95,  # Very high information density
        entropy=0.05   # Very low ambiguity
    )

    node_art = KnowledgeNode(
        id="art_99",
        content="Chaotic Brushstroke",
        domain_type="fuzzy",
        density=0.20,  # Low density
        entropy=0.90   # High ambiguity
    )

    print("-" * 60)
    print(f"Transferring knowledge from [{node_physics.content}] to [{node_art.content}]")
    
    # Detect and Bridge
    bridge = analyzer.generate_bridge_node(node_physics, node_art)

    if bridge:
        print("\n>>> BRIDGE NODE GENERATED <<<")
        print(f"Source: {bridge.source_id}")
        print(f"Target: {bridge.target_id}")
        print(f"Friction Score: {bridge.friction_score:.4f}")
        print(f"Semantic Loss:  {bridge.semantic_loss_rate:.2%}")
        print(f"Guidance: {bridge.explanation}")
    else:
        print("\nTransfer safe. Direct mapping applied.")

    # Case 2: Euclidean Geometry -> Architecture (Logic -> Logic/Light Fuzzy)
    node_geo = KnowledgeNode(
        id="geo_01", 
        content="Pythagorean Theorem", 
        domain_type="logic", 
        density=0.8, 
        entropy=0.1
    )
    node_arch = KnowledgeNode(
        id="arch_01", 
        content="Structural Integrity", 
        domain_type="logic", # Architecture can be logical
        density=0.7, 
        entropy=0.2
    )
    
    print("-" * 60)
    print(f"Transferring knowledge from [{node_geo.content}] to [{node_arch.content}]")
    bridge_2 = analyzer.generate_bridge_node(node_geo, node_arch)
    
    if bridge_2:
        print("\n>>> BRIDGE NODE GENERATED <<<")
        print(f"Guidance: {bridge_2.explanation}")
    else:
        print("\nTransfer safe. Direct mapping applied.")