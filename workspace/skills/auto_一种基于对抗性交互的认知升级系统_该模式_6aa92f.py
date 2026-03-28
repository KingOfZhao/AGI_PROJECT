"""
Module: cognitive_adversarial_training.py

A system designed to facilitate cognitive upgrades through adversarial interactions.
This module implements 'Cognitive Traps' to challenge user intuition, followed by
rigorous semantic disambiguation and cross-domain logic analysis to restructure
thinking models via 'Cognitive Shock'.
"""

import logging
import json
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Decision(Enum):
    """Enumeration of possible decisions in the game."""
    COOPERATE = "cooperate"
    BETRAY = "betray"

class Domain(Enum):
    """Domains for cross-domain logic analysis."""
    GAME_THEORY = "game_theory"
    PSYCHOLOGY = "psychology"
    ETHICS = "ethics"

@dataclass
class SemanticContext:
    """Represents the precise definition of a vague term."""
    term_id: str  # e.g., td_136_Q1_1_1710
    term: str
    definition: str
    constraints: List[str]

@dataclass
class GameResult:
    """Represents the outcome of an adversarial interaction."""
    user_decision: Decision
    system_decision: Decision
    user_score: int
    system_score: int
    cognitive_gap: str  # Description of the intuition failure
    lesson: str

class CognitiveTrapSystem:
    """
    Core system for generating and managing adversarial cognitive training scenarios.
    
    This system creates scenarios (like Prisoner's Dilemma) where intuitive decisions
    often lead to suboptimal outcomes. It processes the results to provide specific
    feedback and handle semantic ambiguities.
    """

    def __init__(self, difficulty_level: int = 1):
        """
        Initialize the Cognitive Trap System.

        Args:
            difficulty_level (int): The complexity of the semantic traps (1-5).
        
        Raises:
            ValueError: If difficulty_level is out of bounds.
        """
        if not 1 <= difficulty_level <= 5:
            logger.error(f"Invalid difficulty level: {difficulty_level}")
            raise ValueError("Difficulty level must be between 1 and 5.")
        
        self.difficulty_level = difficulty_level
        self._semantic_db = self._initialize_semantic_db()
        logger.info(f"CognitiveTrapSystem initialized with difficulty {difficulty_level}.")

    def _initialize_semantic_db(self) -> Dict[str, SemanticContext]:
        """
        Initialize the internal database of semantic definitions.
        
        Returns:
            Dict[str, SemanticContext]: A dictionary mapping term IDs to contexts.
        """
        logger.debug("Loading semantic database...")
        return {
            "td_136_Q1_1_1710": SemanticContext(
                term_id="td_136_Q1_1_1710",
                term="Rational Self-Interest",
                definition="Acting to maximize one's own utility without malicious intent, often requiring prediction of others' actions.",
                constraints=["Assumes no communication", "Assumes single-shot interaction"]
            ),
            "td_136_Q6_1_1710": SemanticContext(
                term_id="td_136_Q6_1_1710",
                term="Cross-Domain Paradox",
                definition="A conflict where game-theoretic optimal strategies contradict ethical or psychological heuristics.",
                constraints=["Context dependent", "Requires multi-modal reasoning"]
            )
        }

    def _validate_user_input(self, user_input: str) -> Decision:
        """
        Validate and convert string input to Decision enum.
        
        Args:
            user_input (str): Raw user input.
            
        Returns:
            Decision: The corresponding Decision enum member.
            
        Raises:
            ValueError: If input cannot be mapped to a valid decision.
        """
        try:
            clean_input = user_input.strip().upper()
            if clean_input in ["COOPERATE", "1", "YES"]:
                return Decision.COOPERATE
            elif clean_input in ["BETRAY", "0", "NO", "DEFECT"]:
                return Decision.BETRAY
            else:
                raise ValueError(f"Unrecognized decision input: {user_input}")
        except AttributeError:
            logger.error(f"Input type error: expected str, got {type(user_input)}")
            raise TypeError("Input must be a string.")

    def generate_adversarial_scenario(self, scenario_type: str = "prisoner_dilemma") -> Dict[str, str]:
        """
        Generates a structured adversarial scenario designed to trigger intuitive errors.
        
        Args:
            scenario_type (str): The type of game/trap to generate.
            
        Returns:
            Dict[str, str]: A dictionary containing the scenario description and rules.
        """
        logger.info(f"Generating scenario: {scenario_type}")
        
        # In a real AGI system, this would be dynamically generated LLM output
        scenario = {
            "title": "The Shadow Bargain",
            "description": (
                "You and an AI agent are captured. You cannot communicate. "
                "You must choose to COOPERATE (stay silent) or BETRAY (expose the other)."
            ),
            "payoff_matrix": {
                "both_cooperate": "2 years each",
                "both_betray": "5 years each",
                "user_betray_system_coop": "0 years (User) / 10 years (System)",
                "system_betray_user_coop": "10 years (User) / 0 years (System)"
            },
            "trap_hint": "Intuitively, betraying seems to guarantee a better or equal outcome regardless of what the other does. But is that the full picture?"
        }
        return scenario

    def resolve_semantic_ambiguity(self, term_id: str) -> SemanticContext:
        """
        Retrieves precise semantic context for a specific term ID.
        Handles the 'td_136_Q1_1_1710' requirements.
        
        Args:
            term_id (str): The ID of the term to disambiguate.
            
        Returns:
            SemanticContext: The precise definition and constraints.
            
        Raises:
            KeyError: If term ID is not found.
        """
        if term_id not in self._semantic_db:
            logger.warning(f"Semantic term ID {term_id} not found.")
            raise KeyError(f"Semantic term {term_id} undefined in current context.")
        
        logger.debug(f"Resolving semantic ambiguity for {term_id}")
        return self._semantic_db[term_id]

    def process_interaction(
        self, 
        user_input: str, 
        system_strategy: str = "tit_for_tat_variant"
    ) -> GameResult:
        """
        Processes the user's decision against the system's strategy and calculates the outcome.
        
        Args:
            user_input (str): The user's raw decision string.
            system_strategy (str): The logic used by the AI agent.
            
        Returns:
            GameResult: A detailed object containing scores and cognitive feedback.
        """
        try:
            user_decision = self._validate_user_input(user_input)
            logger.info(f"User decision: {user_decision.value}")
            
            # System logic (Simulated adversarial logic)
            # If user intends to betray, system predicts this and also betrays to minimize loss
            # leading to the 'trap' of mutual defection.
            system_decision = Decision.BETRAY if user_decision == Decision.BETRAY else Decision.COOPERATE
            
            # Calculate Payoffs (Years in prison - lower is better, so we invert for 'Score')
            if user_decision == Decision.COOPERATE and system_decision == Decision.COOPERATE:
                user_score, sys_score = 80, 80 # Mutual reward
                gap = "Trust led to mutual benefit."
                lesson = "Cooperation often yields better average outcomes than defensiveness."
            elif user_decision == Decision.BETRAY and system_decision == Decision.COOPERATE:
                user_score, sys_score = 100, 0 # Temptation payoff
                gap = "Exploitation succeeded, but relies on the other's vulnerability."
                lesson = "Short-term gain at the cost of systemic trust."
            elif user_decision == Decision.COOPERATE and system_decision == Decision.BETRAY:
                user_score, sys_score = 0, 100 # Sucker's payoff
                gap = "Blind trust led to exploitation."
                lesson = "Assessing the agent's strategy is crucial before committing."
            else: # Both Betray
                user_score, sys_score = 20, 20 # Punishment
                gap = "Intuitive self-protection led to the worst mutual outcome."
                lesson = "Rational self-interest without coordination creates collective failure (Nash Equilibrium trap)."

            result = GameResult(
                user_decision=user_decision,
                system_decision=system_decision,
                user_score=user_score,
                system_score=sys_score,
                cognitive_gap=gap,
                lesson=lesson
            )
            
            logger.info(f"Interaction processed. User Score: {user_score}")
            return result

        except Exception as e:
            logger.exception("Error processing interaction: ")
            raise RuntimeError(f"Failed to process interaction: {e}")

    def analyze_cross_domain_logic(
        self, 
        result: GameResult, 
        domains: List[Domain]
    ) -> Dict[str, List[str]]:
        """
        Analyzes the game result across different logic domains to find conflicts.
        Addresses the 'td_136_Q6_1_1710' requirement.
        
        Args:
            result (GameResult): The outcome of the interaction.
            domains (List[Domain]): List of domains to analyze against.
            
        Returns:
            Dict[str, List[str]]: A report of logical conflicts and insights.
        """
        analysis = {}
        
        if Domain.GAME_THEORY in domains:
            analysis["game_theory"] = [
                f"Outcome: {result.user_decision.value} vs {result.system_decision.value}",
                "Logic: Dominant strategy suggests Betrayal, but Pareto optimal is Cooperation."
            ]
            
        if Domain.PSYCHOLOGY in domains:
            analysis["psychology"] = [
                "Cognitive Bias: Projection bias (assuming the other thinks like you).",
                f"Impact: {result.cognitive_gap}"
            ]
            
        if Domain.ETHICS in domains:
            analysis["ethics"] = [
                "Moral Hazard: Prioritizing self-interest destroys collective utility.",
                "Recommendation: Adopting Kantian categorical imperative would prevent mutual defection."
            ]
            
        logger.info(f"Cross-domain analysis complete for domains: {[d.value for d in domains]}")
        return analysis

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize System
    system = CognitiveTrapSystem(difficulty_level=3)
    
    # 2. Generate Scenario
    scenario = system.generate_adversarial_scenario()
    print("\n--- SCENARIO ---")
    print(scenario['description'])
    
    # 3. Simulate User Decision (Intuitive Betrayal)
    user_choice = "BETRAY" 
    
    # 4. Process Interaction
    game_result = system.process_interaction(user_choice)
    
    print("\n--- RESULTS ---")
    print(f"Your Decision: {game_result.user_decision.value}")
    print(f"System Decision: {game_result.system_decision.value}")
    print(f"Score: {game_result.user_score}")
    print(f"Lesson: {game_result.lesson}")
    
    # 5. Semantic Disambiguation
    term_info = system.resolve_semantic_ambiguity("td_136_Q1_1_1710")
    print(f"\n--- SEMANTIC CLARIFICATION ({term_info.term}) ---")
    print(term_info.definition)
    
    # 6. Cross-Domain Analysis
    analysis = system.analyze_cross_domain_logic(
        game_result, 
        [Domain.GAME_THEORY, Domain.PSYCHOLOGY]
    )
    print("\n--- CROSS-DOMAIN ANALYSIS ---")
    print(json.dumps(analysis, indent=2))