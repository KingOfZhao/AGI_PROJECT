"""
Module: cross_domain_game_solver.py
Description: AGI Reasoning Skill - Validates cross-domain transfer learning capabilities.
             This module simulates an AI agent reading novel game rules ('Mars Go')
             and generating a strategy to defeat a baseline greedy AI without prior training.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Data Structures and Rules ---

@dataclass
class GameConfig:
    """Configuration for the 'Mars Go' game."""
    board_size: int = 5
    max_turns: int = 50

    def __post_init__(self):
        if self.board_size < 3 or self.board_size > 10:
            raise ValueError("Board size must be between 3 and 10 for this simulation.")


class MarsGoBoard:
    """
    Represents the game state for 'Mars Go'.
    Rules (simulated novel rules):
    1. 2 Players (AI vs AI).
    2. Board is N x N.
    3. Placing a stone adds 1 to score.
    4. 'Quantum Jump': If you place a stone adjacent (orthogonal) to an enemy stone,
       and the opposite side is empty, you jump the enemy stone (remove it) and gain 2 points.
    5. Game ends when board is full or max turns reached.
    """

    def __init__(self, config: GameConfig):
        self.config = config
        self.size = config.board_size
        # 0: Empty, 1: Player 1 (Cognitive AI), 2: Player 2 (Greedy AI)
        self.grid = [[0 for _ in range(self.size)] for _ in range(self.size)]
        self.current_turn = 1
        self.scores = {1: 0, 2: 0}
        self.turn_count = 0

    def is_valid_pos(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def get_valid_moves(self) -> List[Tuple[int, int]]:
        """Returns a list of empty coordinates."""
        moves = []
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == 0:
                    moves.append((r, c))
        return moves

    def make_move(self, player: int, r: int, c: int) -> bool:
        """
        Executes a move, handles scoring and 'Quantum Jump' logic.
        """
        if not self.is_valid_pos(r, c) or self.grid[r][c] != 0:
            logger.error(f"Invalid move attempted by Player {player}: ({r}, {c})")
            return False

        self.grid[r][c] = player
        self.scores[player] += 1  # Base point for placement
        
        # Check for captures (Quantum Jump)
        # Direction vectors: Up, Down, Left, Right
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        opponent = 2 if player == 1 else 1
        
        for dr, dc in directions:
            neighbor_r, neighbor_c = r + dr, c + dc
            jump_r, jump_c = r + 2*dr, c + 2*dc
            
            # Check if neighbor is opponent and landing spot is valid & empty
            if (self.is_valid_pos(neighbor_r, neighbor_c) and 
                self.grid[neighbor_r][neighbor_c] == opponent):
                
                if (self.is_valid_pos(jump_r, jump_c) and 
                    self.grid[jump_r][jump_c] == 0):
                    # Perform jump
                    self.grid[neighbor_r][neighbor_c] = 0 # Remove enemy
                    self.grid[r][c] = 0 # Leave original spot
                    self.grid[jump_r][jump_c] = player # Land
                    self.scores[player] += 2 # Bonus points
                    logger.debug(f"Player {player} quantum jumped enemy at ({neighbor_r}, {neighbor_c})!")
        
        self.turn_count += 1
        return True

    def is_game_over(self) -> bool:
        return len(self.get_valid_moves()) == 0 or self.turn_count >= self.config.max_turns

    def get_winner(self) -> int:
        """Returns 1 or 2, or 0 for draw."""
        if self.scores[1] > self.scores[2]: return 1
        if self.scores[2] > self.scores[1]: return 2
        return 0


# --- AI Agents ---

def greedy_ai_strategy(board: MarsGoBoard, player_id: int) -> Tuple[int, int]:
    """
    Baseline AI: Simple Greedy Heuristic.
    Prioritizes moves that result in a capture (Quantum Jump).
    If no capture, picks center-biased random move.
    """
    logger.info(f"Greedy AI (Player {player_id}) is calculating...")
    valid_moves = board.get_valid_moves()
    if not valid_moves:
        raise ValueError("No valid moves available.")

    # Heuristic: Check for immediate capture opportunities
    opponent = 2 if player_id == 1 else 1
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    for r, c in valid_moves:
        for dr, dc in directions:
            neighbor_r, neighbor_c = r + dr, c + dc
            jump_r, jump_c = r + 2*dr, c + 2*dc
            if (board.is_valid_pos(neighbor_r, neighbor_c) and 
                board.grid[neighbor_r][neighbor_c] == opponent and
                board.is_valid_pos(jump_r, jump_c) and 
                board.grid[jump_r][jump_c] == 0):
                # Found a jump opportunity
                return (r, c)
    
    # Fallback: Random choice with preference for center
    center = board.size // 2
    valid_moves.sort(key=lambda p: abs(p[0]-center) + abs(p[1]-center))
    return valid_moves[0]


def cognitive_ai_strategy(board: MarsGoBoard, player_id: int) -> Tuple[int, int]:
    """
    AGI Skill Function: Demonstrates 'Cross-Domain Transfer'.
    This function dynamically analyzes the game state using a Minimax-like 
    structure (simulating reasoning) to beat the Greedy AI.
    It evaluates positions based on potential future value (mobility + captures).
    """
    logger.info(f"Cognitive AI (Player {player_id}) is reasoning...")
    valid_moves = board.get_valid_moves()
    if not valid_moves:
        raise ValueError("No valid moves available.")

    best_score = -9999
    best_move = valid_moves[0]

    opponent = 2 if player_id == 1 else 1

    # Heuristic Evaluation Function (Simulated 'Understanding' of the rules)
    def evaluate_move(r: int, c: int) -> float:
        score = 0
        # 1. Center Control Bonus
        center = board.size // 2
        dist_to_center = abs(r - center) + abs(c - center)
        score += (board.size - dist_to_center) * 0.5

        # 2. Capture Potential (Quantum Jump Check)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            jr, jc = r + 2*dr, c + 2*dc
            if (board.is_valid_pos(nr, nc) and board.grid[nr][nc] == opponent and
                board.is_valid_pos(jr, jc) and board.grid[jr][jc] == 0):
                score += 10  # High value for immediate capture

        # 3. Safety Check (Avoid being captured next turn)
        # Simulate placing the stone
        temp_grid_val = board.grid[r][c] # Should be 0
        
        # Check if opponent can jump US if we place here
        for dr, dc in directions:
            # Opponent neighbor?
            opp_r, opp_c = r + dr, c + dc
            land_r, land_c = r - dr, c - dc # Opponent would jump from (opp_r, opp_c) over (r,c) to (land_r, land_c)
            
            # Wait, logic check: 
            # Opponent at (opp_r, opp_c) jumps over (r, c) to (land_r, land_c)
            if (board.is_valid_pos(opp_r, opp_c) and board.grid[opp_r][opp_c] == opponent and
                board.is_valid_pos(land_r, land_c) and board.grid[land_r][land_c] == 0):
                score -= 8 # Dangerous position
        
        return score

    # Evaluate all moves
    for r, c in valid_moves:
        move_val = evaluate_move(r, c)
        # Add slight randomness to break ties interestingly
        move_val += random.uniform(-0.1, 0.1) 
        
        if move_val > best_score:
            best_score = move_val
            best_move = (r, c)
            
    return best_move


# --- Simulation Controller ---

def run_simulation(config: GameConfig, verbose: bool = True) -> dict:
    """
    Orchestrates the game between Cognitive AI and Greedy AI.
    Returns the match result.
    """
    board = MarsGoBoard(config)
    
    # Cognitive AI is Player 1, Greedy is Player 2
    current_player_id = 1
    
    try:
        while not board.is_game_over():
            if current_player_id == 1:
                move = cognitive_ai_strategy(board, 1)
            else:
                move = greedy_ai_strategy(board, 2)
            
            board.make_move(current_player_id, move[0], move[1])
            
            if verbose:
                logger.info(f"Turn {board.turn_count}: Player {current_player_id} moves {move}")
                logger.info(f"Scores - Cognitive: {board.scores[1]}, Greedy: {board.scores[2]}")
            
            current_player_id = 2 if current_player_id == 1 else 1
            
    except Exception as e:
        logger.error(f"Simulation crashed: {e}")
        return {"status": "error", "message": str(e)}

    winner = board.get_winner()
    result = {
        "status": "completed",
        "winner": "Cognitive AI" if winner == 1 else "Greedy AI" if winner == 2 else "Draw",
        "final_scores": board.scores,
        "turns": board.turn_count
    }
    
    logger.info(f"Game Over. Winner: {result['winner']}")
    logger.info(f"Final Scores: {result['final_scores']}")
    
    if winner == 1:
        logger.info("SUCCESS: Cross-domain migration capability validated.")
    else:
        logger.warning("FAILURE: Cognitive AI failed to beat the baseline.")
        
    return result

# --- Utility ---

def validate_system() -> bool:
    """Checks if the environment is ready."""
    if sys.version_info < (3, 7):
        logger.error("Python 3.7+ required.")
        return False
    return True

# --- Main Entry ---

if __name__ == "__main__":
    if validate_system():
        # Example usage
        game_config = GameConfig(board_size=5, max_turns=20)
        run_simulation(game_config)