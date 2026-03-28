"""
Module: cognitive_consistency_validator.py
Name: auto_设计_认知自洽性验证器_用于检测小摊贩_a5851c

Description:
    This module implements a Cognitive Consistency Validator designed to evaluate
    whether "closed-loop knowledge" (often found in informal sectors, e.g., street vendors)
    constitutes a "Real Node" in an AGI knowledge graph.

    It distinguishes between:
    1. Pseudo-knowledge: Logically self-consistent but impractical or deceptive (e.g., MLM pitches).
    2. Practical Knowledge: Logically rough but operationally effective (e.g., Street Smarts).

    The validation focuses on robustness under boundary conditions and external
    environmental coupling (reality anchoring).

Domain: Cognitive Science / AGI
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveValidator")


@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge to be validated.

    Attributes:
        id: Unique identifier for the knowledge node.
        internal_logic_score (float): Coherence of the internal narrative (0.0 to 1.0).
        boundary_robustness (float): How well it handles edge cases (0.0 to 1.0).
        reality_anchoring (float): Connection to physical constraints/resources (0.0 to 1.0).
        feedback_loop_exists (bool): Whether the system corrects itself based on results.
        tags: List of categorical tags (e.g., 'financial', 'survival', 'mlm').
    """
    id: str
    internal_logic_score: float = 0.0
    boundary_robustness: float = 0.0
    reality_anchoring: float = 0.0
    feedback_loop_exists: bool = False
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate data types and ranges after initialization."""
        if not isinstance(self.id, str):
            raise ValueError("ID must be a string.")
        
        for attr in ['internal_logic_score', 'boundary_robustness', 'reality_anchoring']:
            val = getattr(self, attr)
            if not isinstance(val, (float, int)) or not (0.0 <= val <= 1.0):
                raise ValueError(f"{attr} must be a float between 0.0 and 1.0.")


class ConsistencyValidator:
    """
    Core validator class for detecting the validity of knowledge nodes.
    """

    def __init__(self, strictness: float = 0.5):
        """
        Initialize the validator.

        Args:
            strictness (float): Threshold for validation (0.0 to 1.0).
        """
        self.strictness = strictness
        logger.info(f"ConsistencyValidator initialized with strictness: {strictness}")

    def _calculate_entropy(self, probability: float) -> float:
        """
        Helper function to calculate Shannon entropy for a binary event.
        Used to measure the uncertainty or 'roughness' of the knowledge.

        Args:
            probability (float): Probability of success/consistency (0.0 to 1.0).

        Returns:
            float: Entropy value.
        """
        if probability == 0 or probability == 1:
            return 0.0
        return - (probability * math.log2(probability) + (1 - probability) * math.log2(1 - probability))

    def _check_boundary_conditions(self, node: KnowledgeNode, stress_test: Optional[Dict] = None) -> float:
        """
        Auxiliary function to verify robustness under stress.
        Simulates boundary conditions (e.g., resource scarcity, rule changes).

        Args:
            node: The knowledge node.
            stress_test: Optional dictionary of simulated stress parameters.

        Returns:
            float: Adjusted robustness score.
        """
        logger.debug(f"Checking boundary conditions for node {node.id}")
        
        # If no external test provided, rely on the node's inherent score
        base_robustness = node.boundary_robustness
        
        if stress_test:
            # If we have stress data, simulate decay or resilience
            # Example: If logic is too rigid (high logic, low feedback), it crashes under stress
            rigidity = node.internal_logic_score * (0 if node.feedback_loop_exists else 1)
            resistance = base_robustness * (1 - rigidity * 0.5) # Rigid systems break easier
            return max(0.0, min(1.0, resistance))
        
        return base_robustness

    def validate_real_node(self, node: KnowledgeNode, environment_data: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Core Function 1: Determines if the node is a 'Real Node' or Pseudo-knowledge.

        Logic:
            - Pseudo-knowledge (Scam/MLM): High Internal Logic, Low Reality Anchoring, Low Robustness.
            - Street Smarts: Medium/Low Internal Logic, High Reality Anchoring, High Robustness.

        Args:
            node: The KnowledgeNode object to validate.
            environment_data: Contextual data for boundary checking.

        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        logger.info(f"Validating node: {node.id}")
        
        try:
            # 1. Check for "Utopian Loop" (Perfect logic, zero reality = Scam)
            if node.internal_logic_score > 0.95 and node.reality_anchoring < 0.1:
                reason = "Detected 'Utopian Loop': Logically perfect but detached from reality (Likely Pseudo-knowledge)."
                logger.warning(f"{node.id}: {reason}")
                return False, reason

            # 2. Check for "Street Smarts" (Rough logic, high survival value)
            # High entropy implies the logic is not rigid, which is good for chaotic environments
            entropy = self._calculate_entropy(node.internal_logic_score)
            
            # Use boundary checker
            robustness = self._check_boundary_conditions(node, environment_data)

            # Validity Calculation
            # We prioritize Reality Anchoring and Robustness over Internal Logic
            survival_score = (robustness * 0.5) + (node.reality_anchoring * 0.4) + (entropy * 0.1)
            
            # Feedback loops are critical for real nodes
            if node.feedback_loop_exists:
                survival_score += 0.15 # Bonus for adaptability

            if survival_score >= self.strictness:
                reason = f"Valid 'Real Node'. Survival Score: {survival_score:.2f}"
                logger.info(f"{node.id}: {reason}")
                return True, reason
            else:
                reason = f"Insufficient survival metrics. Score: {survival_score:.2f}"
                logger.info(f"{node.id}: {reason}")
                return False, reason

        except Exception as e:
            logger.error(f"Error validating node {node.id}: {e}")
            return False, f"Validation Error: {e}"

    def analyze_logical_roughness(self, node: KnowledgeNode) -> Dict[str, float]:
        """
        Core Function 2: Analyzes the 'Roughness' of the knowledge.
        Distinguishes between 'Broken Logic' and 'Heuristic Adaptability'.

        Args:
            node: The KnowledgeNode object.

        Returns:
            Dict containing analysis metrics.
        """
        logger.info(f"Analyzing logical roughness for node: {node.id}")
        
        # Roughness is defined as the gap between logic and reality
        gap = abs(node.internal_logic_score - node.reality_anchoring)
        
        # Calculate efficiency: How much robustness do we get per unit of logic?
        efficiency = 0.0
        if node.internal_logic_score > 0:
            efficiency = node.boundary_robustness / node.internal_logic_score
        
        analysis = {
            "logic_reality_gap": gap,
            "heuristic_efficiency": efficiency,
            "adaptability_index": 1.0 - abs(node.boundary_robustness - node.reality_anchoring)
        }

        # Interpretation
        if efficiency > 1.5 and node.internal_logic_score < 0.6:
            logger.info(f"{node.id} identified as High-Efficiency Heuristic (Street Smart).")
        elif gap < 0.1 and node.internal_logic_score < 0.5:
            logger.info(f"{node.id} identified as Low-Value Trivia.")
        
        return analysis

# --- Usage Example ---
if __name__ == "__main__":
    # Example 1: A typical "MLM/Pseudo-knowledge" node (High logic, low reality)
    mlm_node = KnowledgeNode(
        id="mlm_scheme_01",
        internal_logic_score=0.99,  # Internally perfect explanation
        boundary_robustness=0.1,    # Fails if market changes
        reality_anchoring=0.05,     # Ignores physical constraints
        feedback_loop_exists=False, # Ignores failure signals
        tags=["finance", "scam"]
    )

    # Example 2: A "Street Vendor" node (Rough logic, high reality)
    vendor_node = KnowledgeNode(
        id="street_vendor_tactics",
        internal_logic_score=0.6,   # "Buy low, sell high, dodge police" - simple logic
        boundary_robustness=0.85,   # Works in rain, shine, or police raids
        reality_anchoring=0.9,      # Heavily tied to physical goods and cash
        feedback_loop_exists=True,  # Immediate profit/loss feedback
        tags=["survival", "commerce"]
    )

    validator = ConsistencyValidator(strictness=0.6)

    print("--- Validation Results ---")
    
    # Validate MLM
    is_valid_mlm, reason_mlm = validator.validate_real_node(mlm_node)
    print(f"Node: {mlm_node.id} | Valid: {is_valid_mlm} | Reason: {reason_mlm}")

    # Validate Vendor
    is_valid_vendor, reason_vendor = validator.validate_real_node(vendor_node)
    print(f"Node: {vendor_node.id} | Valid: {is_valid_vendor} | Reason: {reason_vendor}")

    print("\n--- Roughness Analysis ---")
    analysis = validator.analyze_logical_roughness(vendor_node)
    print(f"Vendor Analysis: {analysis}")