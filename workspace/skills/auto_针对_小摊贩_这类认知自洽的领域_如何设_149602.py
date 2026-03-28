"""
Module: street_vendor_loop_detector
A robust workflow mining module designed to identify Minimum Viable Practice Loops (MVPL)
within unstructured text data, specifically tailored for cognitively self-consistent domains
like street vending.

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enumeration of possible node types in the workflow."""
    ACTION = "action"
    RESOURCE = "resource"
    SIGNAL = "signal"


@dataclass
class ActionNode:
    """
    Represents a fragmented action node extracted from text.
    
    Attributes:
        id: Unique identifier for the node.
        content: The text content describing the action.
        type: The classification of the node.
        preconditions: Resources or states required before this action.
        effects: Resources or states produced after this action.
    """
    id: str
    content: str
    type: NodeType
    preconditions: Set[str] = field(default_factory=set)
    effects: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self.id)


@dataclass
class RealNode:
    """
    Represents a consolidated 'Real Node' forming a closed loop.
    
    Attributes:
        name: The name of the identified skill/loop.
        input_defs: Required inputs to initiate the loop.
        output_defs: Expected outputs after loop completion.
        cycle_steps: The sequence of actions forming the loop.
        value_flow: Description of how value is generated/transferred.
    """
    name: str
    input_defs: List[str]
    output_defs: List[str]
    cycle_steps: List[str]
    value_flow: str


class StreetVendorLoopDetector:
    """
    Detects Minimum Viable Practice Loops in street vending scenarios.
    
    This class processes unstructured text fragments to identify cycles where 
    a resource is consumed, transformed, and value is realized (e.g., Money -> Goods -> Money').
    """

    def __init__(self, domain_keywords: Optional[Dict[str, List[str]]] = None):
        """
        Initialize the detector with domain-specific knowledge.
        
        Args:
            domain_keywords: A dictionary mapping resource types to keywords.
        """
        self.domain_keywords = domain_keywords or {
            "currency": ["money", "change", "cash", "payment", "fee", "yuan", "dollar"],
            "goods": ["food", "item", "product", "vegetable", "meal", "goods"],
            "service": ["delivery", "cooking", "wrapping", "service"]
        }
        logger.info("StreetVendorLoopDetector initialized with domain keywords.")

    def extract_fragment_nodes(self, raw_text: str) -> List[ActionNode]:
        """
        Extracts action nodes from unstructured text using rule-based parsing.
        
        Args:
            raw_text: Unstructured text describing the scenario.
            
        Returns:
            A list of ActionNode objects.
            
        Raises:
            ValueError: If raw_text is empty or invalid.
        """
        if not raw_text or not isinstance(raw_text, str):
            logger.error("Invalid input text provided.")
            raise ValueError("Input text must be a non-empty string.")

        logger.info("Starting node extraction...")
        # Simulated NLP extraction: Split by punctuation for demo
        sentences = re.split(r'[.!?\n]+', raw_text)
        nodes = []

        for idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 2:
                continue

            # Determine node type based on keywords (Heuristic)
            node_type = NodeType.ACTION
            preconds = set()
            effects = set()

            # Simple heuristic resource linkage
            if any(k in sentence for k in self.domain_keywords["currency"]):
                if "receive" in sentence or "find" in sentence or "change" in sentence:
                    effects.add("currency_held")
                elif "give" in sentence or "pay" in sentence:
                    preconds.add("currency_held")
            
            if any(k in sentence for k in self.domain_keywords["goods"]):
                if "hand" in sentence or "serve" in sentence:
                    effects.add("goods_transferred")
                elif "cook" in sentence or "prepare" in sentence:
                    effects.add("goods_ready")

            node = ActionNode(
                id=f"node_{idx}",
                content=sentence,
                type=node_type,
                preconditions=preconds,
                effects=effects
            )
            nodes.append(node)

        logger.info(f"Extracted {len(nodes)} potential nodes.")
        return nodes

    def _identify_loop_closure(self, nodes: List[ActionNode]) -> Optional[Tuple[str, str, List[ActionNode]]]:
        """
        Helper function to find a path where a resource transforms and returns to origin state.
        
        Args:
            nodes: List of action nodes to analyze.
            
        Returns:
            A tuple of (start_node_id, end_node_id, path) if loop found, else None.
        """
        # Simplified Cycle Detection: Look for currency start -> goods exchange -> currency end
        # In a real AGI system, this would use a Graph Neural Network or Dependency Graph
        currency_start_node = None
        currency_end_node = None
        goods_nodes = []

        for node in nodes:
            # Start: We need currency (input)
            if "currency_held" in node.effects and not node.preconditions:
                currency_start_node = node
            # Middle: We transfer goods
            elif "goods_transferred" in node.effects or "goods_ready" in node.effects:
                goods_nodes.append(node)
            # End: We receive currency (value realization)
            elif "currency_held" in node.effects and "goods_transferred" in node.preconditions:
                currency_end_node = node
        
        if currency_start_node and goods_nodes and currency_end_node:
            path = [currency_start_node] + goods_nodes + [currency_end_node]
            return (currency_start_node.id, currency_end_node.id, path)
        
        return None

    def detect_minimal_loops(self, nodes: List[ActionNode]) -> List[RealNode]:
        """
        Analyzes nodes to identify Minimum Viable Practice Loops (MVPL).
        
        Args:
            nodes: A list of ActionNodes.
            
        Returns:
            A list of consolidated RealNodes representing detected skills.
        """
        if not nodes:
            logger.warning("No nodes provided for loop detection.")
            return []

        logger.info("Analyzing nodes for minimal loops...")
        detected_loops = []

        # 1. Try to find the primary transaction loop
        loop_data = self._identify_loop_closure(nodes)
        
        if loop_data:
            start_id, end_id, path = loop_data
            logger.info(f"Closed loop detected: {' -> '.join([n.content for n in path])}")
            
            # 2. Consolidate into a RealNode
            inputs = list(path[0].preconditions) if path[0].preconditions else ["Implicit Context"]
            outputs = list(path[-1].effects)
            
            real_node = RealNode(
                name="TransactionLoop_CommodityExchange",
                input_defs=inputs,
                output_defs=outputs,
                cycle_steps=[n.content for n in path],
                value_flow="Currency converted to Goods, then converted back to Currency (with potential profit)."
            )
            detected_loops.append(real_node)
        
        return detected_loops

    def refine_real_node(self, real_node: RealNode) -> Dict:
        """
        Converts a RealNode object into a standardized, serializable format.
        
        Args:
            real_node: The RealNode to refine.
            
        Returns:
            A dictionary representing the refined skill definition.
        """
        if not isinstance(real_node, RealNode):
            raise TypeError("Input must be a RealNode instance.")

        return {
            "skill_name": real_node.name,
            "input_interface": real_node.input_defs,
            "output_interface": real_node.output_defs,
            "process_flow": real_node.cycle_steps,
            "validation_check": "Value flow confirmed: " + real_node.value_flow
        }


if __name__ == "__main__":
    # Example Usage
    sample_text = """
    The vendor sets up the stall. 
    A customer approaches and asks for a snack.
    The vendor receives 10 yuan from the customer.
    The vendor prepares the snack quickly.
    The vendor hands over the hot snack.
    The vendor gives back 2 yuan in change.
    The vendor shouts to attract more people.
    """

    detector = StreetVendorLoopDetector()
    
    try:
        # Step 1: Extract fragments
        fragments = detector.extract_fragment_nodes(sample_text)
        
        # Step 2: Detect loops
        loops = detector.detect_minimal_loops(fragments)
        
        # Step 3: Refine and Output
        for loop in loops:
            skill_def = detector.refine_real_node(loop)
            print("\n--- Detected Skill ---")
            for k, v in skill_def.items():
                print(f"{k}: {v}")
                
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}", exc_info=True)