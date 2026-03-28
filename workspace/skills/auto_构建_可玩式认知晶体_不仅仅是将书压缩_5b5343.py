"""
Module: auto_构建_可玩式认知晶体_不仅仅是将书压缩_5b5343

This module implements the 'Playable Cognitive Crystal' generator.
It transforms complex systems theories (like Game Theory) into minimal,
interactive Micro-Games. Users can tweak parameters to observe emergent,
counter-intuitive conclusions in seconds, shifting from passive reading
to active model manipulation.

Author: AGI System
Version: 1.0.0
"""

import logging
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Strategy(Enum):
    """Enumeration of possible strategies in the game."""
    COOPERATE = "Cooperate"
    DEFECT = "Defect"

@dataclass
class PayoffMatrix:
    """
    Represents the payoff structure for a 2x2 game (e.g., Prisoner's Dilemma).
    
    Attributes:
        temptation (float): Reward for defecting when opponent cooperates (T).
        reward (float): Reward for mutual cooperation (R).
        punishment (float): Punishment for mutual defection (P).
        sucker (float): Punishment for cooperating when opponent defects (S).
    """
    temptation: float = 5.0   # T
    reward: float = 3.0       # R
    punishment: float = 1.0   # P
    sucker: float = 0.0       # S

    def validate(self) -> bool:
        """Validates the basic properties of a Prisoner's Dilemma matrix."""
        # Standard PD condition: T > R > P > S
        if not (self.temptation > self.reward > self.punishment > self.sucker):
            logger.warning("Payoff matrix does not strictly follow T > R > P > S hierarchy.")
            return False
        # Additional condition to prevent alternation exploitation
        if not (2 * self.reward > self.temptation + self.sucker):
            logger.warning("Payoff matrix may encourage alternating turns rather than cooperation.")
            return False
        return True

@dataclass
class GameResult:
    """Container for the outcome of a game round."""
    player_strategy: Strategy
    opponent_strategy: Strategy
    player_payoff: float
    opponent_payoff: float
    message: str

class CognitiveCrystalGame:
    """
    A minimal, interactive simulation of strategic conflict (e.g., Prisoner's Dilemma).
    
    This class serves as the 'Micro-Game' engine. It allows the user to act as a
    variable parameter (the opponent) to see how the system evolves.
    """

    def __init__(self, matrix: Optional[PayoffMatrix] = None):
        """
        Initialize the game engine with a specific payoff matrix.
        
        Args:
            matrix (PayoffMatrix, optional): The payoff structure. Defaults to standard PD.
        """
        self.matrix = matrix or PayoffMatrix()
        self.history: List[Dict[str, Any]] = []
        self._validate_environment()

    def _validate_environment(self) -> None:
        """Validates the game settings before starting."""
        if not self.matrix.validate():
            logger.error("Initialized with a non-standard or invalid payoff matrix.")
        logger.info("Game engine initialized with Matrix: T=%.1f, R=%.1f, P=%.1f, S=%.1f",
                    self.matrix.temptation, self.matrix.reward, 
                    self.matrix.punishment, self.matrix.sucker)

    def calculate_payoff(self, player_move: Strategy, opponent_move: Strategy) -> Tuple[float, float]:
        """
        Core logic: Calculate payoffs based on moves.
        
        Args:
            player_move (Strategy): The user's move.
            opponent_move (Strategy): The system/other player's move.
            
        Returns:
            Tuple[float, float]: (Player Score, Opponent Score)
        """
        if player_move == Strategy.COOPERATE and opponent_move == Strategy.COOPERATE:
            return self.matrix.reward, self.matrix.reward
        elif player_move == Strategy.COOPERATE and opponent_move == Strategy.DEFECT:
            return self.matrix.sucker, self.matrix.temptation
        elif player_move == Strategy.DEFECT and opponent_move == Strategy.COOPERATE:
            return self.matrix.temptation, self.matrix.sucker
        else: # Both Defect
            return self.matrix.punishment, self.matrix.punishment

    def play_round(self, player_move: Strategy, opponent_move: Strategy) -> GameResult:
        """
        Executes a single round of interaction.
        
        Args:
            player_move (Strategy): The decision made by the learner.
            opponent_move (Strategy): The decision made by the counterpart.
            
        Returns:
            GameResult: Detailed result of the interaction.
        """
        try:
            p_payoff, o_payoff = self.calculate_payoff(player_move, opponent_move)
            
            # Generate cognitive feedback (The 'Insight' generation)
            insight = self._generate_feedback(p_payoff)
            
            result = GameResult(
                player_strategy=player_move,
                opponent_strategy=opponent_move,
                player_payoff=p_payoff,
                opponent_payoff=o_payoff,
                message=insight
            )
            
            self.history.append(asdict(result))
            logger.debug(f"Round played: Player={player_move.value}, Opponent={opponent_move.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error during round execution: {e}")
            raise

    def _generate_feedback(self, payoff: float) -> str:
        """
        Auxiliary function: Generates cognitive feedback based on outcome.
        Helps the user understand the systemic implication of their choice.
        """
        if payoff == self.matrix.temptation:
            return "Exploitation successful. Short-term gain maximized, but is trust destroyed?"
        elif payoff == self.matrix.reward:
            return "Cooperation established. Collective optimal outcome achieved."
        elif payoff == self.matrix.punishment:
            return "Mutual destruction. The safety of defection leads to mediocrity."
        else: # Sucker
            return "Betrayal encountered. Altruism without enforcement is punished."

def run_simulation_scenarios(matrix: PayoffMatrix, rounds: int = 10) -> Dict[str, Any]:
    """
    Simulates an iterated environment to demonstrate emergence over time.
    
    This function represents the 'Variable Manipulation' aspect of the skill.
    It compares a 'Always Defect' strategy against a 'Tit-for-Tat' strategy
    to visualize how local interaction rules create global patterns.
    
    Args:
        matrix (PayoffMatrix): The rule set being tested.
        rounds (int): Number of iterations.
        
    Returns:
        Dict[str, Any]: Analysis of the simulation.
    """
    if rounds <= 0:
        raise ValueError("Rounds must be a positive integer")
        
    game = CognitiveCrystalGame(matrix)
    
    # Strategies
    def strategy_always_defect(history): return Strategy.DEFECT
    def strategy_tit_for_tat(history):
        if not history: return Strategy.COOPERATE
        return history[-1]['opponent_strategy']

    p1_score = 0.0
    p2_score = 0.0
    
    logger.info(f"Starting simulation: {rounds} rounds.")
    
    for i in range(rounds):
        # P1 is Always Defect, P2 is Tit-for-Tat
        move1 = strategy_always_defect(game.history)
        move2 = strategy_tit_for_tat(game.history)
        
        # Play round (P1 vs P2)
        result = game.play_round(move1, move2)
        p1_score += result.player_payoff
        p2_score += result.opponent_payoff

    analysis = {
        "config": asdict(matrix),
        "rounds": rounds,
        "player1_strategy": "Always Defect",
        "player2_strategy": "Tit-for-Tat",
        "final_scores": {
            "player1": p1_score,
            "player2": p2_score
        },
        "insight": "Even though Defect wins individual rounds, cooperative strategies (Tit-for-Tat) often survive better in iterated systems depending on matrix variables."
    }
    
    return analysis

# --- Usage Example & Demonstration ---
if __name__ == "__main__":
    # 1. Instantiate the 'Playable Cognitive Crystal' (The Micro-Game)
    print("--- Initializing Cognitive Crystal: The Prisoner's Dilemma Lab ---")
    
    # 2. Modify the 'Variables' (The Physics of the Social System)
    # Let's tweak the matrix to see how it changes behavior
    custom_matrix = PayoffMatrix(
        temptation=10.0,  # High temptation to defect
        reward=5.0,       # Good reward for cooperation
        punishment=1.0,   # Low punishment for mutual defection
        sucker=0.0        # Sucker's payoff
    )
    
    game_engine = CognitiveCrystalGame(matrix=custom_matrix)
    
    # 3. Interaction (The 'Play')
    print("\n[Scenario 1: Single Shot Interaction]")
    # User chooses to DEFECT, System chooses to COOPERATE
    result = game_engine.play_round(Strategy.DEFECT, Strategy.COOPERATE)
    print(f"Action: You Defected vs Opponent Cooperated")
    print(f"Result: Payoff={result.player_payoff}. Insight: {result.message}")
    
    # 4. Emergence Simulation (The 'Time' dimension)
    print("\n[Scenario 2: Systemic Evolution Simulation]")
    # We reduce the reward for cooperation to see if society collapses
    collapse_matrix = PayoffMatrix(temptation=10, reward=2, punishment=1, sucker=0)
    sim_results = run_simulation_scenarios(collapse_matrix, rounds=5)
    
    print(f"Simulation Results ({sim_results['rounds']} rounds):")
    print(f"P1 ({sim_results['player1_strategy']}): {sim_results['final_scores']['player1']}")
    print(f"P2 ({sim_results['player2_strategy']}): {sim_results['final_scores']['player2']}")
    print(f"Systemic Insight: {sim_results['insight']}")
    
    # 5. Data Export (Crystalized Knowledge)
    print("\n[Exporting Interaction Log]")
    print(json.dumps(game_engine.history, indent=2, default=str))