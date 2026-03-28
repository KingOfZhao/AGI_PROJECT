"""
Module: intuitive_collision_simulator
A rigorous teaching tool designed to 'break intuition' in Game Theory.
"""

import logging
import random
from enum import Enum
from typing import List, Tuple, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Decision(Enum):
    """Enumeration representing a player's decision."""
    COOPERATE = 1  # Stay Silent
    BETRAY = 2     # Betray Partner

class PrisonerDilemmaSimulator:
    """
    An AI-driven simulation of the Prisoner's Dilemma designed to 
    demonstrate the mathematical consequences of intuitive decision-making.
    
    This simulator acts as an AI opponent to induce decisions based on 
    trust or betrayal, providing harsh mathematical feedback (long-term 
    sentencing) to solidify learning through experience.
    
    Attributes:
        rounds (int): Total number of rounds to simulate.
        current_round (int): Current round index.
        player_score (int): Total years sentenced to the player (lower is better).
        ai_score (int): Total years sentenced to the AI (lower is better).
        history (List[Dict]): Record of all past interactions.
        learning_rate (float): Probability that AI makes a 'rational' vs 'random' move.
    
    Data Input:
        - rounds: Integer (default 10)
        - learning_rate: Float (0.0 to 1.0)
    
    Data Output:
        - Dict containing 'winner', 'player_total_sentence', 'ai_total_sentence', 'history'
    """

    def __init__(self, rounds: int = 10, learning_rate: float = 0.8):
        """
        Initialize the simulator.
        
        Args:
            rounds (int): Number of rounds to play. Must be > 0.
            learning_rate (float): AI sophistication level (0.0 to 1.0).
        
        Raises:
            ValueError: If input parameters are out of bounds.
        """
        if not isinstance(rounds, int) or rounds <= 0:
            logger.error("Invalid rounds input: %s", rounds)
            raise ValueError("Rounds must be a positive integer.")
        
        if not (0.0 <= learning_rate <= 1.0):
            logger.error("Invalid learning rate: %s", learning_rate)
            raise ValueError("Learning rate must be between 0.0 and 1.0.")

        self.rounds = rounds
        self.current_round = 0
        self.player_score = 0
        self.ai_score = 0
        self.history: List[Dict[str, str]] = []
        self.learning_rate = learning_rate
        logger.info("Simulator initialized with %d rounds and LR %.2f", rounds, learning_rate)

    def _calculate_sentence(self, player_move: Decision, ai_move: Decision) -> Tuple[int, int]:
        """
        Helper function to determine prison sentences based on moves.
        
        Scoring Matrix (Years in prison):
        - Both Cooperate: 1 year each (Reward)
        - Both Betray: 5 years each (Punishment)
        - One Betrays, One Cooperates: 0 for Betrayer (Temptation), 10 for Cooperator (Sucker)
        
        Args:
            player_move (Decision): The learner's choice.
            ai_move (Decision): The AI's choice.
            
        Returns:
            Tuple[int, int]: (player_sentence, ai_sentence)
        """
        if player_move == Decision.COOPERATE and ai_move == Decision.COOPERATE:
            return 1, 1  # Reward
        elif player_move == Decision.BETRAY and ai_move == Decision.BETRAY:
            return 5, 5  # Punishment
        elif player_move == Decision.BETRAY and ai_move == Decision.COOPERATE:
            return 0, 10 # Temptation vs Sucker
        else: # Player Coop, AI Betray
            return 10, 0

    def _ai_decision_engine(self, player_history: List[Decision]) -> Decision:
        """
        Core AI logic. Simulates an opponent that adapts or exploits.
        
        Strategy:
        1. High learning rate: Exploits patterns (Tit-for-Tat or ruthless Betrayal).
        2. Low learning rate: Random noise to test player's resilience.
        
        Args:
            player_history (List[Decision]): History of player's past moves.
            
        Returns:
            Decision: AI's calculated move.
        """
        # If random check fails, make a random move
        if random.random() > self.learning_rate:
            return random.choice([Decision.COOPERATE, Decision.BETRAY])
        
        # Rational Strategy: Tit-for-Tat (mostly)
        if not player_history:
            # First move: usually cooperate to probe
            return Decision.COOPERATE if random.random() > 0.3 else Decision.BETRAY
        
        last_move = player_history[-1]
        if last_move == Decision.BETRAY:
            # Punish betrayal
            return Decision.BETRAY
        else:
            # Exploit naivety with a probability of sudden betrayal
            return Decision.BETRAY if random.random() < 0.2 else Decision.COOPERATE

    def run_simulation(self, player_strategy_func) -> Dict[str, Optional[int]]:
        """
        Executes the full simulation loop.
        
        Args:
            player_strategy_func (callable): A function that takes (current_round, history) 
                                             and returns a Decision.
                                             
        Returns:
            Dict: Summary of the simulation results.
        """
        logger.info("Starting Intuitive Collision Simulation...")
        temp_player_history: List[Decision] = []

        for r in range(1, self.rounds + 1):
            self.current_round = r
            
            # 1. Get Player Decision
            try:
                player_move = player_strategy_func(r, self.history)
                if not isinstance(player_move, Decision):
                    raise TypeError("Player strategy must return a Decision Enum.")
            except Exception as e:
                logger.error("Error in player strategy function: %s", e)
                player_move = Decision.BETRAY # Default to betrayal on error
            
            # 2. Get AI Decision
            ai_move = self._ai_decision_engine(temp_player_history)
            
            # 3. Calculate Results
            p_time, ai_time = self._calculate_sentence(player_move, ai_move)
            self.player_score += p_time
            self.ai_score += ai_time
            
            # 4. Record History
            round_data = {
                "round": r,
                "player_move": player_move.name,
                "ai_move": ai_move.name,
                "player_sentence": p_time,
                "ai_sentence": ai_time
            }
            self.history.append(round_data)
            temp_player_history.append(player_move)
            
            logger.debug("Round %d: Player %s (%dy) vs AI %s (%dy)", 
                         r, player_move.name, p_time, ai_move.name, ai_time)

        winner = "Player" if self.player_score < self.ai_score else "AI" if self.ai_score < self.player_score else "Draw"
        logger.info("Simulation Complete. Winner: %s", winner)
        
        return {
            "winner": winner,
            "player_total_sentence": self.player_score,
            "ai_total_sentence": self.ai_score,
            "history": self.history
        }

# --- Usage Example ---
if __name__ == "__main__":
    # Example of a naive human strategy (Always Trust)
    def naive_trust_strategy(round_num, history):
        return Decision.COOPERATE

    # Example of a paranoid strategy (Always Betray)
    def paranoid_strategy(round_num, history):
        return Decision.BETRAY

    # 1. Test Naive Intuition (Expect heavy losses)
    print("--- Testing Intuition (Always Trust) ---")
    sim = PrisonerDilemmaSimulator(rounds=5, learning_rate=0.9)
    results = sim.run_simulation(naive_trust_strategy)
    print(f"Result: {results['winner']}")
    print(f"Player Sentence: {results['player_total_sentence']} years")
    
    # 2. Test Defensive Strategy
    print("\n--- Testing Defensive (Always Betray) ---")
    sim2 = PrisonerDilemmaSimulator(rounds=5, learning_rate=0.9)
    results2 = sim2.run_simulation(paranoid_strategy)
    print(f"Result: {results2['winner']}")
    print(f"Player Sentence: {results2['player_total_sentence']} years")