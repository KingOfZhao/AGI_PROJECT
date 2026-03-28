"""
Module: auto_跨域迁移能力验证_给定一个全新的_未在_184895
Description: 【跨域迁移能力验证】AGI Skill for Complex Game Rule Synthesis and Execution.
             This module implements a logic engine for a complex, hypothetical card game
             'Quantum-Ops' based on natural language rules parsed into structured logic.
             It demonstrates the ability to map abstract text rules to concrete executable code.
"""

import logging
import random
import json
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class Suit(Enum):
    """Represents the suit of a card."""
    ALPHA = "Alpha"
    BETA = "Beta"
    GAMMA = "Gamma"
    DELTA = "Delta"

class ActionType(Enum):
    """Represents the type of action a player can take."""
    PLAY_CARD = "PLAY"
    DRAW_CARD = "DRAW"
    ACTIVATE_CORE = "ACTIVATE"

@dataclass
class Card:
    """Represents a game card with specific attributes."""
    card_id: str
    suit: Suit
    base_value: int
    is_stable: bool = True  # Quantum stability flag
    
    def __post_init__(self):
        """Validate card attributes after initialization."""
        if self.base_value < 1 or self.base_value > 13:
            raise ValueError(f"Invalid card value {self.base_value}. Must be 1-13.")
        if not isinstance(self.suit, Suit):
            raise TypeError(f"Invalid suit type: {type(self.suit)}")

@dataclass
class Player:
    """Represents a player in the game."""
    player_id: int
    hand: List[Card] = field(default_factory=list)
    score: int = 0
    is_protected: bool = False

    def add_card(self, card: Card) -> None:
        self.hand.append(card)
        logger.debug(f"Player {self.player_id} drew card {card.card_id}")

    def remove_card(self, card_id: str) -> Optional[Card]:
        for i, card in enumerate(self.hand):
            if card.card_id == card_id:
                return self.hand.pop(i)
        logger.warning(f"Card {card_id} not found in Player {self.player_id}'s hand")
        return None

# --- Core Game Logic Class ---

class QuantumOpsEngine:
    """
    The core engine for the 'Quantum-Ops' game.
    This class manages game state, validates moves against rules, and handles the logic loop.
    """
    
    DECK_SIZE = 52
    
    def __init__(self, players: List[Player], rule_config: Optional[Dict] = None):
        """
        Initialize the game engine.
        
        Args:
            players: List of Player objects participating.
            rule_config: Optional dictionary to override standard rules (e.g., max_score).
        """
        if len(players) < 2:
            raise ValueError("Quantum-Ops requires at least 2 players.")
            
        self.players = players
        self.current_player_idx = 0
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.turn_count = 0
        self.rule_config = rule_config or {"winning_score": 100, "decay_rate": 0.1}
        self._initialize_deck()
        logger.info("QuantumOpsEngine initialized with new rule set.")

    def _initialize_deck(self) -> None:
        """Generates and shuffles the deck of cards."""
        self.deck = []
        card_count = 0
        for suit in Suit:
            for val in range(1, 14):
                # Create unique ID based on suit and value
                c_id = f"{suit.value[0]}{val:02d}"
                # Every 5th card is unstable (Quantum rule)
                is_stable = (val % 5 != 0)
                self.deck.append(Card(c_id, suit, val, is_stable))
                card_count += 1
        
        random.shuffle(self.deck)
        logger.info(f"Deck initialized with {card_count} cards.")

    def _validate_move(self, player: Player, action: ActionType, card: Optional[Card] = None) -> bool:
        """
        Validates if a move is legal according to the current game rules.
        
        Args:
            player: The player attempting the move.
            action: The type of action.
            card: The card involved (if playing).
            
        Returns:
            True if valid, False otherwise.
        """
        if action == ActionType.PLAY_CARD:
            if not card:
                logger.error("Validation failed: No card provided for PLAY action.")
                return False
            if card not in player.hand:
                logger.error(f"Validation failed: Player {player.player_id} does not hold card {card.card_id}")
                return False
            
            # Complex Rule: Unstable cards can only be played if score is odd
            if not card.is_stable and player.score % 2 == 0:
                logger.error(f"Validation failed: Cannot play Unstable card with even score.")
                return False
                
        return True

    def execute_turn(self, action_type: ActionType, card_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a full turn for the current player.
        
        Args:
            action_type: The action to perform.
            card_id: ID of the card to play (if applicable).
            
        Returns:
            A dictionary containing the result of the turn.
        
        Raises:
            ValueError: If the move is invalid or game state is corrupted.
        """
        current_player = self.players[self.current_player_idx]
        logger.info(f"Turn {self.turn_count}: Player {current_player.player_id} attempts {action_type.value}")
        
        selected_card = None
        if card_id:
            # Find card in hand
            selected_card = next((c for c in current_player.hand if c.card_id == card_id), None)
            if not selected_card:
                raise ValueError(f"Card ID {card_id} not found in hand.")

        if not self._validate_move(current_player, action_type, selected_card):
            raise ValueError("Invalid move detected by rule engine.")

        result_payload = {"success": False, "message": "", "state_update": {}}

        try:
            if action_type == ActionType.DRAW_CARD:
                if not self.deck:
                    self._recycle_discard_pile()
                
                drawn_card = self.deck.pop()
                current_player.add_card(drawn_card)
                result_payload["message"] = f"Drew card {drawn_card.card_id}"
                
            elif action_type == ActionType.PLAY_CARD and selected_card:
                current_player.remove_card(selected_card.card_id)
                self.discard_pile.append(selected_card)
                
                # Calculate score based on complex rules
                points = self._calculate_points(selected_card, current_player)
                current_player.score += points
                
                result_payload["message"] = f"Played {selected_card.card_id} for {points} points."
                result_payload["state_update"] = {"score": current_player.score}
            
            self._advance_turn()
            result_payload["success"] = True
            
        except IndexError:
            logger.critical("Deck is empty despite recycling attempt.")
            result_payload["message"] = "Game Over: No cards left."
        except Exception as e:
            logger.exception("Error during turn execution")
            raise

        return result_payload

    def _calculate_points(self, card: Card, player: Player) -> int:
        """
        Helper function to calculate points based on card stability and player state.
        
        Rules:
        1. Base points = card value.
        2. If card is Unstable: Points = Base * 1.5 (integer division).
        3. If Player is protected: +5 bonus.
        """
        points = card.base_value
        
        if not card.is_stable:
            points = int(points * 1.5)
            logger.debug(f"Applying unstable multiplier to card {card.card_id}")
            
        if player.is_protected:
            points += 5
            
        return points

    def _recycle_discard_pile(self) -> None:
        """Shuffles discard pile back into the deck."""
        if not self.discard_pile:
            raise RuntimeError("No cards to recycle.")
            
        logger.info("Recycling discard pile into deck.")
        self.deck = self.discard_pile
        self.discard_pile = []
        random.shuffle(self.deck)

    def _advance_turn(self) -> None:
        """Moves to the next player."""
        self.turn_count += 1
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def check_victory(self) -> Optional[int]:
        """Checks if any player has won."""
        target = self.rule_config.get("winning_score", 100)
        for p in self.players:
            if p.score >= target:
                return p.player_id
        return None

# --- Utility Functions ---

def generate_random_scenario(num_players: int = 2) -> Tuple[QuantumOpsEngine, Dict]:
    """
    Generates a randomized game setup for testing purposes.
    
    Args:
        num_players: Number of players to initialize.
        
    Returns:
        A tuple containing the initialized engine and the initial state dictionary.
    """
    players = [Player(i) for i in range(num_players)]
    engine = QuantumOpsEngine(players)
    
    # Deal initial hands
    for _ in range(5):
        for p in players:
            if engine.deck:
                p.hand.append(engine.deck.pop())
                
    logger.info(f"Generated scenario with {num_players} players.")
    return engine, {"hands_size": [len(p.hand) for p in players]}

def run_monte_carlo_simulation(engine: QuantumOpsEngine, iterations: int = 100) -> Dict[str, float]:
    """
    Runs a simulation of random moves to verify system stability.
    
    Args:
        engine: The game engine instance.
        iterations: Number of turns to simulate.
        
    Returns:
        Statistics about the simulation (avg score, errors encountered).
    """
    stats = {"total_points": 0, "errors": 0, "turns_played": 0}
    
    for i in range(iterations):
        current_p = engine.players[engine.current_player_idx]
        
        # Random decision: 70% play if has cards, 30% draw
        action = ActionType.PLAY_CARD if random.random() > 0.3 and current_p.hand else ActionType.DRAW_CARD
        
        try:
            card_target = None
            if action == ActionType.PLAY_CARD:
                card_target = random.choice(current_p.hand).card_id
                
            res = engine.execute_turn(action, card_target)
            stats["total_points"] += res["state_update"].get("score", 0)
            stats["turns_played"] += 1
            
            winner = engine.check_victory()
            if winner is not None:
                logger.info(f"Simulation ended early: Player {winner} wins.")
                break
                
        except ValueError as ve:
            # Catch logical invalid moves during random simulation (expected behavior)
            logger.debug(f"Simulated invalid move skipped: {ve}")
        except Exception as e:
            logger.error(f"Critical error during simulation: {e}")
            stats["errors"] += 1

    return stats

# --- Main Execution / Usage Example ---

if __name__ == "__main__":
    # 1. Setup game
    p1 = Player(1)
    p2 = Player(2)
    game_engine = QuantumOpsEngine([p1, p2])
    
    # 2. Deal cards manually for example
    for _ in range(4):
        p1.hand.append(game_engine.deck.pop())
        p2.hand.append(game_engine.deck.pop())
        
    print(f"Player 1 Hand: {[c.card_id for c in p1.hand]}")
    
    # 3. Execute a sequence of moves
    try:
        # Player 1 plays their first card
        card_to_play = p1.hand[0].card_id
        result = game_engine.execute_turn(ActionType.PLAY_CARD, card_to_play)
        print(f"Turn Result: {result['message']}")
        
        # Player 2 draws
        result = game_engine.execute_turn(ActionType.DRAW_CARD)
        print(f"Turn Result: {result['message']}")
        
    except Exception as e:
        print(f"Game Error: {e}")
        
    # 4. Run automated simulation test
    print("\nRunning Monte Carlo Simulation...")
    engine_test, _ = generate_random_scenario(3)
    sim_stats = run_monte_carlo_simulation(engine_test, iterations=50)
    print(f"Simulation Stats: {sim_stats}")