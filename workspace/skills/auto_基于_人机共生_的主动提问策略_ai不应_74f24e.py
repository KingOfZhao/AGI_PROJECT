"""
Module: active_inquiry_strategy.py

A high-quality skill module for an AGI system focusing on Human-Computer Symbiosis.
This module implements a strategy where the AI proactively identifies the 'weakest link'
(highest uncertainty/information entropy) in its current knowledge graph and generates
an optimal question to ask a human collaborator.

The core philosophy is to minimize human cognitive load (low answer cost) while
maximizing the information gain for the AI's internal modeling (entropy reduction).

Author: Senior Python Engineer
Version: 1.0.0
Domain: Human-Computer Interaction (HCI) / Active Learning
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enumeration of possible node types in the knowledge graph."""
    CONCEPT = "concept"
    ENTITY = "entity"
    RELATION = "relation"


@dataclass
class KnowledgeNode:
    """
    Represents a single node in the AI's knowledge structure.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual semantic content (e.g., "Object Permanence").
        entropy: Current uncertainty level (0.0 to 1.0). Higher means more uncertain.
        difficulty: Estimated complexity for a human to verify or explain (1-10).
        connections: List of connected node IDs.
        type: The type of knowledge node.
    """
    id: str
    content: str
    entropy: float = 0.5
    difficulty: float = 5.0
    connections: List[str] = field(default_factory=list)
    type: NodeType = NodeType.CONCEPT

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Validates data boundaries."""
        if not 0.0 <= self.entropy <= 1.0:
            raise ValueError(f"Entropy must be between 0 and 1. Got {self.entropy}")
        if not 1.0 <= self.difficulty <= 10.0:
            raise ValueError(f"Difficulty must be between 1 and 10. Got {self.difficulty}")


class ActiveInquiryEngine:
    """
    Engine for generating optimal questions based on information entropy and human cost.
    
    This engine analyzes a simulated knowledge graph to find areas of high uncertainty
    and formulates questions that balance information gain against the effort required
    for a human to answer.
    """

    def __init__(self, nodes: Optional[List[KnowledgeNode]] = None):
        """
        Initializes the engine with a set of knowledge nodes.
        
        Args:
            nodes: A list of KnowledgeNode objects representing the current state.
        """
        self.knowledge_base: Dict[str, KnowledgeNode] = {}
        if nodes:
            self.load_knowledge(nodes)

    def load_knowledge(self, nodes: List[KnowledgeNode]) -> None:
        """
        Loads or updates the internal knowledge base.
        
        Args:
            nodes: List of nodes to load.
        """
        logger.info(f"Loading {len(nodes)} nodes into knowledge base.")
        for node in nodes:
            if node.id in self.knowledge_base:
                logger.warning(f"Overwriting existing node: {node.id}")
            self.knowledge_base[node.id] = node

    def _calculate_question_cost(self, target_node: KnowledgeNode) -> float:
        """
        Helper function to calculate the 'cognitive cost' for a human to answer.
        
        Formula: Cost = Difficulty * (1 / Specificity)
        For this simulation, we assume specificity is inversely proportional to entropy
        (high entropy = vague concept = hard to answer specifically without context).
        
        Args:
            target_node: The node to evaluate.
            
        Returns:
            A float representing the estimated cost to the human.
        """
        # Avoid division by zero
        specificity = 1.1 - target_node.entropy  # Range approx 0.1 to 1.1
        cost = target_node.difficulty / specificity
        return cost

    def identify_optimal_inquiry_target(self) -> Tuple[Optional[KnowledgeNode], float]:
        """
        Identifies the 'weakest link' (shortest board) in the current knowledge structure.
        
        Strategy:
        1. Filter nodes with entropy above a threshold (we don't know enough about them).
        2. Calculate a 'Symbiotic Score' = (Information Gain Potential) / (Human Cost).
        3. Select the node with the highest score.
        
        Information Gain Potential is modeled here as High Entropy (uncertainty).
        We want to resolve high entropy, but we want to do it cheaply.
        
        Returns:
            A tuple containing the target KnowledgeNode and its calculated score.
            Returns (None, 0.0) if no suitable target is found.
        """
        if not self.knowledge_base:
            logger.error("Knowledge base is empty. Cannot identify target.")
            return None, 0.0

        best_node: Optional[KnowledgeNode] = None
        max_score: float = -1.0

        logger.debug("Scanning knowledge base for optimal inquiry target...")
        
        for node in self.knowledge_base.values():
            # Only consider nodes that are actually uncertain
            if node.entropy < 0.1:
                continue

            # Calculate Human Cost
            human_cost = self._calculate_question_cost(node)
            
            # Calculate Symbiotic Value (Value to AI / Cost to Human)
            # We prioritize high entropy (high potential gain) and low cost.
            # Score = Entropy^2 / Cost (Squared to emphasize high uncertainty)
            if human_cost > 0:
                score = (node.entropy ** 2) / human_cost
            else:
                score = float('inf')

            if score > max_score:
                max_score = score
                best_node = node

        if best_node:
            logger.info(f"Identified target: {best_node.id} (Entropy: {best_node.entropy:.2f}, Score: {max_score:.4f})")
        else:
            logger.info("No high-uncertainty targets found. System is stable.")
            
        return best_node, max_score

    def generate_question(self, target: KnowledgeNode) -> Dict[str, str]:
        """
        Generates a natural language question based on the target node's state.
        
        This function simulates the NLG (Natural Language Generation) component.
        It constructs a question designed to maximize information gain by asking
        for definitions or relationships depending on the node type.
        
        Args:
            target: The KnowledgeNode to formulate a question about.
            
        Returns:
            A dictionary containing the question and metadata.
            
        Raises:
            ValueError: If target node is invalid.
        """
        if not target or not isinstance(target, KnowledgeNode):
            raise ValueError("Invalid target node provided for question generation.")

        logger.debug(f"Generating question for node: {target.id}")
        
        # Simple template-based generation logic
        if target.entropy > 0.8:
            # Very uncertain -> Ask for basic definition
            question_text = (
                f" I am currently forming a concept for '{target.content}', "
                f"but my understanding is vague. Could you provide a concise definition "
                f"to clarify its core properties?"
            )
            intent = "definition_request"
        elif target.connections:
            # Moderately uncertain -> Ask for disambiguation/relationship verification
            related_id = random.choice(target.connections)
            related_content = "related concepts" # In a real system, look up related_id
            question_text = (
                f"Regarding '{target.content}', I see a connection to '{related_content}'. "
                f"Is this relationship causal or correlational? A simple distinction "
                f"would greatly refine my model."
            )
            intent = "relationship_verification"
        else:
            question_text = (
                f"Can you confirm if the concept '{target.content}' is relevant "
                f"to the current context?"
            )
            intent = "relevance_check"

        return {
            "target_node_id": target.id,
            "intent": intent,
            "question": question_text.strip(),
            "estimated_entropy_reduction": target.entropy * 0.5 # Simulated estimate
        }


def main():
    """
    Usage Example / Test Harness
    """
    # 1. Setup simulated knowledge state
    nodes = [
        KnowledgeNode(
            id="node_1", 
            content="Quantum Entanglement", 
            entropy=0.95, 
            difficulty=9.0, # Hard for human to explain simply
            type=NodeType.CONCEPT
        ),
        KnowledgeNode(
            id="node_2", 
            content="User Interface Button", 
            entropy=0.85, 
            difficulty=2.0, # Easy for human to explain
            type=NodeType.ENTITY
        ),
        KnowledgeNode(
            id="node_3", 
            content="Database Index", 
            entropy=0.6, 
            difficulty=4.0, 
            type=NodeType.CONCEPT
        ),
        KnowledgeNode(
            id="node_4",
            content="Coffee Machine",
            entropy=0.1, # Already known
            difficulty=1.0,
            type=NodeType.ENTITY
        )
    ]

    # 2. Initialize Engine
    engine = ActiveInquiryEngine(nodes=nodes)

    try:
        # 3. Identify the "Shortest Board" (Optimal Inquiry Target)
        target_node, score = engine.identify_optimal_inquiry_target()

        if target_node:
            # 4. Generate the Question
            result = engine.generate_question(target_node)
            
            print("\n" + "="*60)
            print("ACTIVE INQUIRY SYSTEM OUTPUT")
            print("="*60)
            print(f"Selected Target: {result['target_node_id']}")
            print(f"Symbiotic Score: {score:.4f}")
            print(f"Intent: {result['intent']}")
            print("-" * 60)
            print(f"Generated Question:\n{result['question']}")
            print("="*60 + "\n")
        else:
            print("No questions needed at this time.")

    except ValueError as ve:
        logger.error(f"Validation error during execution: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system failure: {e}", exc_info=True)


if __name__ == "__main__":
    main()