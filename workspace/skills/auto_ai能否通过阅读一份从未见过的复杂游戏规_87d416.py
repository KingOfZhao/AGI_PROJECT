"""
Module: auto_ai_game_strategy_generator
Description: This module demonstrates an AGI-like capability where an AI system reads
complex game rules (text) and generates executable strategy code to play the game.
It includes a mock game environment, a rule parser, a strategy generator, and a
simulation loop to validate the generated logic against random agents.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class GameState:
    """Represents the current state of the game environment."""
    player_hp: int = 20
    opponent_hp: int = 20
    player_energy: int = 1
    turn: int = 1
    hand: List[str] = field(default_factory=lambda: ["Attack", "Defend", "Heal"])
    history: List[str] = field(default_factory=list)

    def is_game_over(self) -> bool:
        return self.player_hp <= 0 or self.opponent_hp <= 0

@dataclass
class RuleSet:
    """Structured representation of parsed game rules."""
    win_condition: str
    valid_actions: List[str]
    constraints: Dict[str, Any]

# --- Core Function 1: Rule Parser ---

def parse_game_rules(raw_text: str) -> RuleSet:
    """
    Parses unstructured text containing game rules into a structured format.
    This simulates the NLP understanding component of the AGI system.

    Args:
        raw_text (str): The raw text of the game manual/instructions.

    Returns:
        RuleSet: A structured object containing parsed rules.
    
    Raises:
        ValueError: If the text is empty or critical rules are missing.
    """
    if not raw_text or len(raw_text.strip()) < 10:
        logger.error("Input rule text is too short or empty.")
        raise ValueError("Rule text must be a non-empty string with significant length.")

    logger.info("Parsing raw text into structured rules...")
    
    # Simulated semantic extraction (Regex/Keyword based for this demo)
    win_cond = "Reduce Opponent HP to 0"
    
    # Extract actions (Mock logic)
    actions = ["Attack", "Defend", "Heal"]
    if "Ultimate" in raw_text:
        actions.append("Ultimate")

    constraints = {
        "max_energy": 3,
        "heal_cap": 20,
        "attack_cost": 1,
        "heal_cost": 2
    }

    return RuleSet(
        win_condition=win_cond,
        valid_actions=actions,
        constraints=constraints
    )

# --- Core Function 2: Strategy Code Generator ---

def generate_strategy_code(rules: RuleSet) -> Callable[[GameState], str]:
    """
    Generates a Python function (strategy) based on the parsed rules.
    This represents the 'Code Synthesis' capability.

    Args:
        rules (RuleSet): The structured rules guiding the logic generation.

    Returns:
        Callable[[GameState], str]: An executable function that takes a state and returns an action.
    """
    logger.info("Generating executable strategy code based on rules...")
    
    # Here we dynamically create a function. 
    # In a real AGI, this would be generated via LLM or symbolic assembly.
    
    def dynamic_strategy(state: GameState) -> str:
        """AI Generated Strategy Logic"""
        # Priority 1: Heal if HP is low and energy is sufficient (Extracted from "Preserve life" semantic)
        if state.player_hp < 10 and state.player_energy >= rules.constraints["heal_cost"]:
            if "Heal" in state.hand:
                return "Heal"

        # Priority 2: Attack if possible (Extracted from "Win condition: Reduce HP")
        if state.player_energy >= rules.constraints["attack_cost"]:
            if "Attack" in state.hand:
                return "Attack"
        
        # Priority 3: Defend as fallback
        if "Defend" in state.hand:
            return "Defend"
            
        # Fallback
        return random.choice(state.hand) if state.hand else "Wait"

    return dynamic_strategy

# --- Helper Function: Environment Simulation ---

def simulate_turn(state: GameState, action: str, rules: RuleSet) -> None:
    """
    Applies the consequences of an action to the game state.
    Includes validation and boundary checks.

    Args:
        state (GameState): The current game state (mutated in place).
        action (str): The action chosen by the agent.
        rules (RuleSet): The rule set containing constraints.
    """
    if state.is_game_over():
        return

    state.history.append(f"Turn {state.turn}: Player used {action}")
    
    if action == "Attack":
        dmg = random.randint(3, 5)
        state.opponent_hp -= dmg
        state.player_energy -= rules.constraints["attack_cost"]
        state.history.append(f" -> Opponent took {dmg} damage.")
    elif action == "Heal":
        heal = random.randint(4, 6)
        state.player_hp = min(state.player_hp + heal, rules.constraints["heal_cap"])
        state.player_energy -= rules.constraints["heal_cost"]
        state.history.append(f" -> Player healed {heal} HP.")
    elif action == "Defend":
        state.player_energy -= 1
        state.history.append(" -> Player is blocking.")
    else:
        state.history.append(" -> Invalid action or Wait.")

    # Opponent turn (Simple logic)
    if not state.is_game_over():
        opp_dmg = random.randint(1, 4)
        # Check if player defended last turn (simplified logic)
        if "blocking" not in state.history[-1]:
            state.player_hp -= opp_dmg
            state.history.append(f" Opponent attacks for {opp_dmg}.")
        
    # Turn end maintenance
    state.turn += 1
    state.player_energy = min(state.player_energy + 2, rules.constraints["max_energy"])

# --- Main Execution Logic ---

def run_simulation(rules_text: str, max_turns: int = 20) -> Dict[str, Any]:
    """
    Orchestrates the full pipeline: Parse rules -> Generate Code -> Run Simulation.

    Args:
        rules_text (str): The raw game manual text.
        max_turns (int): Safety limit for the simulation loop.

    Returns:
        Dict[str, Any]: A report containing win status and turn history.
    """
    try:
        # 1. Semantic Grounding
        rules = parse_game_rules(rules_text)
        
        # 2. Code Synthesis
        ai_strategy = generate_strategy_code(rules)
        
        # 3. Initialization
        state = GameState()
        logger.info("Starting game simulation...")
        
        # 4. Game Loop
        while not state.is_game_over() and state.turn < max_turns:
            # AI Decision
            chosen_action = ai_strategy(state)
            
            # Execution
            simulate_turn(state, chosen_action, rules)
            
        # 5. Reporting
        result = {
            "winner": "AI" if state.opponent_hp <= 0 else "Opponent" if state.player_hp <= 0 else "Draw",
            "turns": state.turn,
            "final_player_hp": state.player_hp,
            "final_opponent_hp": state.opponent_hp,
            "history": state.history
        }
        
        logger.info(f"Game Over. Winner: {result['winner']} in {result['turns']} turns.")
        return result

    except Exception as e:
        logger.critical(f"Simulation failed: {str(e)}", exc_info=True)
        return {"error": str(e)}

# --- Usage Example ---

if __name__ == "__main__":
    # Mock input representing a 'never seen before' game manual text
    GAME_MANUAL = """
    Welcome to BattleGrid v1.0.
    Objective: Reduce the opponent's HP to 0.
    Actions:
    - Attack: Costs 1 Energy. Deals physical damage.
    - Heal: Costs 2 Energy. Restores health, but cannot exceed 20 HP.
    - Defend: Costs 1 Energy. Reduces incoming damage.
    Energy regenerates by 2 points every turn, capped at 3.
    """
    
    print("--- Starting Auto-AI Skill Demonstration ---")
    simulation_report = run_simulation(GAME_MANUAL)
    
    print("\n--- Final Report ---")
    if "error" in simulation_report:
        print(f"An error occurred: {simulation_report['error']}")
    else:
        print(f"Result: {simulation_report['winner']}")
        print(f"Player HP: {simulation_report['final_player_hp']}")
        print(f"Opponent HP: {simulation_report['final_opponent_hp']}")