"""
Module: adaptive_narrative_simulator
A system for developing adaptive narrative scenario-based training, transforming static
case studies into interactive, movie-like role-playing experiences using generative AI.
"""

import logging
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("narrative_simulator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimulationError(Exception):
    """Custom exception for simulation errors."""
    pass

class DecisionType(Enum):
    """Enum representing different types of decisions a user can make."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    ETHICAL_CHOICE = "ethical_choice"

@dataclass
class Character:
    """
    Represents a character in the simulation (NPC or Player).
    
    Attributes:
        id: Unique identifier for the character.
        name: Name of the character.
        role: Role type (e.g., 'Manager', 'Employee', 'Historical Figure').
        personality_traits: List of traits defining the character's behavior.
        hidden_agenda: Optional secret goals the character tries to achieve.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unknown"
    role: str = "NPC"
    personality_traits: List[str] = field(default_factory=list)
    hidden_agenda: Optional[str] = None

    def validate(self) -> bool:
        """Validates character data."""
        if not self.name or not isinstance(self.name, str):
            logger.error("Invalid character name.")
            raise ValueError("Character name must be a non-empty string.")
        return True

@dataclass
class NarrativeState:
    """
    Represents the current state of the narrative simulation.
    
    Attributes:
        plot_id: ID of the current scenario.
        current_scene: Description of the current scene.
        history: List of past interactions and decisions.
        emotional_tone: Current emotional atmosphere (e.g., 'tense', 'empathetic').
    """
    plot_id: str
    current_scene: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    emotional_tone: float = 0.5  # Range 0.0 (negative) to 1.0 (positive)

    def add_event(self, actor: str, action: str, outcome: str):
        """Records an event in the narrative history."""
        event = {
            "timestamp": str(uuid.uuid4()),  # Using uuid as pseudo-timestamp for uniqueness
            "actor": actor,
            "action": action,
            "outcome": outcome
        }
        self.history.append(event)
        logger.info(f"Event recorded: {actor} performed {action}")

class GenerativeEngine:
    """
    Mock class representing the interface to a Generative AI model (e.g., LLM).
    In a real implementation, this would call APIs like OpenAI, Anthropic, or local models.
    """
    
    @staticmethod
    def generate_response(context: NarrativeState, npc: Character, user_input: str) -> str:
        """
        Simulates AI generation of NPC response based on context and personality.
        """
        # Simple logic simulation for demonstration
        mood_modifier = "polite" if context.emotional_tone > 0.5 else "defensive"
        response = (
            f"[{npc.name} ({npc.role}) responds with {mood_modifier} tone]: "
            f"I understand your point about '{user_input}', but as someone who is "
            f"{npc.personality_traits[0] if npc.personality_traits else 'neutral'}, "
            f"I must consider the consequences."
        )
        return response

    @staticmethod
    def update_plot(context: NarrativeState, decision: str) -> str:
        """
        Simulates dynamic plot progression based on user decision.
        """
        if "fire" in decision.lower() or "aggressive" in decision.lower():
            context.emotional_tone = max(0.0, context.emotional_tone - 0.2)
            return "The atmosphere in the room grows cold. The team looks anxious."
        elif "support" in decision.lower() or "empathy" in decision.lower():
            context.emotional_tone = min(1.0, context.emotional_tone + 0.2)
            return "Trust builds within the team. Productivity seems to increase."
        else:
            return "The situation remains unchanged, awaiting further action."

class AdaptiveNarrativeSystem:
    """
    Main class for the Adaptive Narrative Simulation System.
    
    This system manages the lifecycle of a role-playing training scenario,
    handling character interactions, state management, and narrative progression.
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        """
        Initializes the simulation system.
        
        Args:
            scenario_config: Dictionary containing initial scenario settings.
        
        Raises:
            SimulationError: If configuration is invalid.
        """
        try:
            self._validate_config(scenario_config)
            self.scenario_id = str(uuid.uuid4())
            self.state = NarrativeState(
                plot_id=scenario_config.get("plot_id", "default_plot"),
                current_scene=scenario_config.get("opening_scene", "The scene begins...")
            )
            self.characters: Dict[str, Character] = {}
            self.engine = GenerativeEngine()
            logger.info(f"Simulation {self.scenario_id} initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize simulation: {e}")
            raise SimulationError(f"Initialization failed: {e}")

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validates the input configuration dictionary."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary.")
        if "plot_id" not in config:
            logger.warning("No plot_id provided, using default.")
        return True

    def register_character(self, character_data: Dict[str, Any]) -> Character:
        """
        Creates and registers a character in the simulation.
        
        Args:
            character_data: Dictionary with keys 'name', 'role', 'traits', etc.
        
        Returns:
            The created Character object.
        """
        try:
            char = Character(
                name=character_data.get("name"),
                role=character_data.get("role"),
                personality_traits=character_data.get("traits", []),
                hidden_agenda=character_data.get("agenda")
            )
            char.validate()
            self.characters[char.id] = char
            logger.info(f"Character registered: {char.name} (ID: {char.id})")
            return char
        except Exception as e:
            logger.error(f"Failed to register character: {e}")
            raise SimulationError(f"Character registration failed: {e}")

    def process_user_turn(self, player_input: str, target_npc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes the student's (player's) turn.
        
        This method takes the player's input, updates the narrative state,
        generates NPC reactions, and determines the next scene.
        
        Args:
            player_input: The text or action code input by the student.
            target_npc_id: Optional ID of the NPC the player is interacting with.
        
        Returns:
            A dictionary containing the updated scene narrative and NPC responses.
        """
        if not player_input or not isinstance(player_input, str):
            raise ValueError("Player input must be a non-empty string.")

        logger.info(f"Processing player turn: {player_input[:50]}...")

        # 1. Update Plot based on decision
        next_scene_context = self.engine.update_plot(self.state, player_input)
        
        # 2. Generate NPC Reaction (if targeted)
        npc_response = None
        if target_npc_id and target_npc_id in self.characters:
            npc = self.characters[target_npc_id]
            npc_response = self.engine.generate_response(self.state, npc, player_input)
            self.state.add_event("Player", player_input, npc_response)
        else:
            self.state.add_event("Player", player_input, "Environment change")

        # 3. Update Scene Description
        self.state.current_scene = next_scene_context

        return {
            "status": "success",
            "current_scene": self.state.current_scene,
            "npc_response": npc_response,
            "emotional_tone": self.state.emotional_tone,
            "history_length": len(self.state.history)
        }

    def evaluate_performance(self) -> Dict[str, Union[float, str]]:
        """
        Analyzes the student's performance based on the narrative history.
        
        Returns:
            A report containing scores for empathy, logic, and risk-taking.
        """
        empathy_score = self.state.emotional_tone  # Simplified metric
        logic_score = 0.5  # Placeholder for complex logic analysis
        
        logger.info("Generating performance evaluation.")
        
        return {
            "student_id": "user_123", # In real system, tracked via session
            "empathy_index": round(empathy_score, 2),
            "decision_quality": "High" if empathy_score > 0.6 else "Needs Improvement",
            "feedback": "Demonstrated strong ethical reasoning in complex scenarios."
        }

# --- Usage Example ---
if __name__ == "__main__":
    # Configuration for a "Conflict Resolution" scenario
    config = {
        "plot_id": "conflict_res_01",
        "opening_scene": "You are a project manager. Two key team members are arguing about the project's architecture, delaying the deadline."
    }

    try:
        # Initialize System
        system = AdaptiveNarrativeSystem(config)
        
        # Setup NPCs
        npc_data = {
            "name": "Sarah (Lead Engineer)",
            "role": "Antagonist/Colleague",
            "traits": ["stubborn", "perfectionist", "loyal"],
            "agenda": "Wants to ensure code quality at all costs."
        }
        sarah = system.register_character(npc_data)

        # Simulation Loop (Turn 1)
        print("--- Scene 1 ---")
        print(f"Situation: {system.state.current_scene}")
        
        # Player makes a decision
        player_action = "I listen to both sides and propose a compromise focusing on MVP features first."
        
        result = system.process_user_turn(player_action, target_npc_id=sarah.id)
        
        print(f"\n> You: {player_action}")
        print(f"> System: {result['current_scene']}")
        if result['npc_response']:
            print(f"> {result['npc_response']}")
            
        # Final Evaluation
        print("\n--- Final Report ---")
        report = system.evaluate_performance()
        print(json.dumps(report, indent=2))

    except SimulationError as e:
        print(f"Simulation Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")