"""
 abyss_gaze_compression.py
 
 Implementation of the 'Abyss Gaze Compression' learning methodology.
 This module transforms static domain knowledge into interactive, high-friction
 cognitive challenges (Thought Boss Battles).
 
 Core Philosophy:
 1. Knowledge is not given; it is extracted through failure.
 2. Intuition is the enemy of deep understanding in counter-intuitive domains.
 3. High friction (failure) triggers the amygdala, strengthening synaptic connections
    for long-term memory retention (Flashbulb Memory effect).
 
 Author: AGI System
 Version: 1.0.0
 Domain: Cross-Domain (Game Theory, Logic, Strategy)
"""

import logging
import json
import random
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("abyss_gaze.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InteractionState(Enum):
    """Enumeration of the possible states in the learning cycle."""
    INITIALIZED = 0
    TRAP_SET = 1
    USER_FALLEN = 2  # The 'Death' state where learning happens
    KNOWLEDGE_ABSORBED = 3

@dataclass
class KnowledgeNode:
    """
    Represents a unit of knowledge to be compressed and transmitted.
    
    Attributes:
        topic: The specific subject matter (e.g., 'Nash Equilibrium').
        common_trap: The intuitive but wrong logic most users follow.
        correct_logic: The counter-intuitive truth.
        scenario: The text describing the interactive scenario.
        success_rate: Historical success rate of users (lower is better for learning).
    """
    topic: str
    common_trap: str
    correct_logic: str
    scenario: str
    options: Dict[str, str] = field(default_factory=dict)
    correct_key: str = ""
    success_rate: float = 0.0

class AbyssGazeSystem:
    """
    The Core Engine for the Abyss Gaze Compression Method.
    
    This system manages the state of the 'Cognitive Trap', validates user input,
    and orchestrates the feedback loop required for high-friction learning.
    """
    
    def __init__(self, domain_data: List[Dict]):
        """
        Initialize the system with raw domain data.
        
        Args:
            domain_data: A list of dictionaries containing raw knowledge facts.
        """
        self._validate_input_data(domain_data)
        self.knowledge_base: List[KnowledgeNode] = self._process_raw_data(domain_data)
        self.current_node: Optional[KnowledgeNode] = None
        self.state: InteractionState = InteractionState.INITIALIZED
        logger.info(f"Abyss Gaze System initialized with {len(self.knowledge_base)} nodes.")

    def _validate_input_data(self, data: List[Dict]) -> None:
        """Validates the structure of the input data."""
        if not isinstance(data, list):
            raise ValueError("Input must be a list of dictionaries.")
        required_keys = {"topic", "trap", "truth", "scenario"}
        for item in data:
            if not required_keys.issubset(item.keys()):
                raise ValueError(f"Missing keys in data item: {item}")

    def _process_raw_data(self, data: List[Dict]) -> List[KnowledgeNode]:
        """
        Transforms raw dictionaries into structured KnowledgeNode objects.
        This acts as a pre-compressor, organizing data for the trap mechanism.
        """
        nodes = []
        for item in data:
            # Simulating the generation of multiple choice options based on trap/truth
            options = {
                "A": item['trap'],  # The Trap (Intuitive)
                "B": item['truth'], # The Truth (Counter-intuitive)
                "C": "It depends on external factors.", # Vague safety
                "D": "Neither side benefits." # Pessimism
            }
            
            node = KnowledgeNode(
                topic=item['topic'],
                common_trap=item['trap'],
                correct_logic=item['truth'],
                scenario=item['scenario'],
                options=options,
                correct_key="B" # Assuming truth is the target
            )
            nodes.append(node)
        return nodes

    def load_cognitive_trap(self, difficulty: str = "medium") -> Dict[str, Union[str, Dict]]:
        """
        [Core Function 1]
        Constructs and presents the 'Trap' (The Scenario).
        
        The system selects a knowledge node and presents it as a game-like scenario
        without revealing the underlying theory. It invites the user to fail.
        
        Args:
            difficulty: Placeholder for future difficulty scaling.
            
        Returns:
            A dictionary containing the scenario text and choices.
        """
        if not self.knowledge_base:
            logger.error("Knowledge base is empty.")
            return {"error": "No scenarios available"}

        # Select a scenario (Simple selection logic, can be improved with RL)
        self.current_node = random.choice(self.knowledge_base)
        self.state = InteractionState.TRAP_SET
        
        logger.info(f"Trap set for topic: {self.current_node.topic}")
        
        return {
            "scenario": self.current_node.scenario,
            "options": self.current_node.options,
            "hint": "Trust your instincts... if you dare."
        }

    def evaluate_user_move(self, user_choice: str) -> Dict[str, Union[bool, str]]:
        """
        [Core Function 2]
        Evaluates the user's choice against the 'Abyss' (The Truth).
        
        If the user falls into the trap (Failure), the system provides the 
        'Enlightenment Feedback'. If they succeed, it validates mastery.
        
        Args:
            user_choice: The key (e.g., 'A') selected by the user.
            
        Returns:
            A feedback dictionary containing success status and the 'Core Logic'.
        """
        if self.state != InteractionState.TRAP_SET or not self.current_node:
            raise RuntimeError("No active trap found. Please load a scenario first.")
            
        if user_choice not in self.current_node.options:
            logger.warning(f"Invalid input: {user_choice}")
            return {"error": "Invalid choice", "valid_options": list(self.current_node.options.keys())}

        is_correct = (user_choice == self.current_node.correct_key)
        
        if not is_correct:
            # THE FRICTION POINT: User failed.
            self.state = InteractionState.USER_FALLEN
            logger.info(f"User fell into trap: {self.current_node.topic}")
            
            # The 'Resurrection' Logic - revealing the compressed knowledge
            feedback = (
                f"SYSTEM INTERRUPT: Cognitive Trap Triggered.\n"
                f"Your intuition chose: '{self.current_node.common_trap}'\n\n"
                f">>> CORE LOGIC UNLOCKED <<<\n"
                f"{self.current_node.correct_logic}\n\n"
                f"Memory anchored via high-friction event."
            )
            return {
                "success": False,
                "feedback": feedback,
                "knowledge_gained": self.current_node.topic
            }
        else:
            # MASTERY
            self.state = InteractionState.KNOWLEDGE_ABSORBED
            logger.info(f"User mastered: {self.current_node.topic}")
            return {
                "success": True,
                "feedback": "Impressive. You bypassed the intuitive trap.",
                "knowledge_gained": self.current_node.topic
            }

    def _get_system_status(self) -> Dict:
        """
        [Auxiliary Function]
        Returns the current internal state of the engine for debugging/UI.
        """
        return {
            "state": self.state.name,
            "current_topic": self.current_node.topic if self.current_node else None,
            "nodes_remaining": len(self.knowledge_base)
        }

# ==========================================
# Usage Example and Simulation
# ==========================================

if __name__ == "__main__":
    # Mock Data: Game Theory / Prisoner's Dilemma
    raw_knowledge = [
        {
            "topic": "Prisoner's Dilemma - Nash Equilibrium",
            "scenario": "You and an accomplice are arrested. You cannot communicate. "
                        "If you both stay silent, you get 1 year each. "
                        "If you betray (testify), you go free, and he gets 3 years (and vice versa). "
                        "If you BOTH betray, you both get 2 years. "
                        "To minimize YOUR time, what is the 'dominant strategy'?",
            "trap": "Stay Silent (Cooperate with accomplice to minimize total time).",
            "truth": "Betray (Defect). Regardless of what the other does, defecting yields a better individual outcome, leading to a suboptimal equilibrium."
        },
        {
            "topic": "Surivorship Bias",
            "scenario": "You examine the armor plating of bombers returning from war. "
                        "You see holes concentrated on the wing tips and tail. "
                        "Where should you add extra armor?",
            "trap": "Reinforce the wing tips and tail where the holes are.",
            "truth": "Reinforce the engine and cockpit. The planes you saw survived despite damage to wings. The planes hit in the engine didn't come back."
        }
    ]

    try:
        # 1. Initialize System
        print("--- Initializing Abyss Gaze System ---")
        abyss = AbyssGazeSystem(raw_knowledge)
        
        # 2. Load a Trap
        print("\n--- Loading Cognitive Trap ---")
        challenge = abyss.load_cognitive_trap()
        print(f"Scenario: {challenge['scenario']}")
        print("Options:")
        for k, v in challenge['options'].items():
            print(f"  [{k}]: {v}")
            
        # 3. Simulate User 'Failure' (The core of the method)
        print("\n--- Simulating Intuitive Choice (Failure) ---")
        # Intentionally choosing 'A' which is usually the trap in this setup
        result = abyss.evaluate_user_move("A") 
        
        if not result['success']:
            print("\n>>> FEEDBACK RECEIVED <<<")
            print(result['feedback'])
            print("\n>>> STATUS <<<")
            print(json.dumps(abyss._get_system_status(), indent=2))
            
    except ValueError as ve:
        logger.error(f"Data Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"System Crash: {e}", exc_info=True)