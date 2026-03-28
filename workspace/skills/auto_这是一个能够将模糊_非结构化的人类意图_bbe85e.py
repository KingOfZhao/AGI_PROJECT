"""
Module: intent_compiler.py
Description: A high-level cognitive system that translates vague, unstructured human intent
             (natural language, gestures) into structured, machine-executable instructions.
             It combines semantic graph anchoring, cognitive parsing, and semantic dynamics
             to map fuzzy modifiers (e.g., "gently", "slightly") to precise physical parameters.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
import math
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentCompiler")


class ConstraintViolationError(Exception):
    """Raised when the intent violates physical or logical constraints."""
    pass


class ParsingError(Exception):
    """Raised when the natural language intent cannot be parsed."""
    pass


class ActionType(Enum):
    """Enumeration of supported low-level machine actions."""
    MOVE_ABSOLUTE = "MOVE_ABSOLUTE"
    MOVE_RELATIVE = "MOVE_RELATIVE"
    ROTATE = "ROTATE"
    GRIPPER_ACTUATE = "GRIPPER_ACTUATE"
    WAIT = "WAIT"
    CUT = "CUT"


@dataclass
class SemanticContext:
    """Holds the current state and environmental context."""
    current_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    max_speed: float = 1.5  # m/s
    safe_zone_limits: Tuple[Tuple[float, float], 
                            Tuple[float, float], 
                            Tuple[float, float]] = (
        (-10.0, 10.0),  # X limits
        (-10.0, 10.0),  # Y limits
        (0.0, 5.0)      # Z limits
    )


@dataclass
class StructuredInstruction:
    """Represents a single, executable machine instruction."""
    action_type: ActionType
    parameters: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self):
        """Validate instruction integrity after initialization."""
        if not isinstance(self.action_type, ActionType):
            raise ValueError(f"Invalid action type: {self.action_type}")


class SemanticDynamicsEngine:
    """
    Handles the non-linear mapping of fuzzy adverbs to physical parameters.
    Implements the 'Semantic Dynamics' component of the system.
    """

    @staticmethod
    def map_adverb_to_modifier(adverb: Optional[str]) -> float:
        """
        Maps a linguistic adverb to a scalar modifier (0.0 to 1.0+).
        
        Args:
            adverb (str): The adverb found in the intent (e.g., "slightly", "quickly").
            
        Returns:
            float: A multiplier for physical parameters.
        """
        if not adverb:
            return 1.0  # Default neutral modifier

        adverb = adverb.lower().strip()
        mapping = {
            "slightly": 0.2,
            "gently": 0.3,
            "carefully": 0.4,
            "slowly": 0.5,
            "normally": 1.0,
            "quickly": 1.5,
            "rapidly": 2.0,
            "forcefully": 2.5
        }
        
        modifier = mapping.get(adverb)
        if modifier is None:
            logger.warning(f"Unknown adverb '{adverb}', defaulting to 1.0")
            return 1.0
        
        logger.debug(f"Mapped adverb '{adverb}' to modifier {modifier}")
        return modifier

    @staticmethod
    def calculate_kinematics(base_speed: float, modifier: float) -> Dict[str, float]:
        """
        Calculates velocity and acceleration based on semantic modifier.
        
        Args:
            base_speed (float): The standard operational speed.
            modifier (float): The semantic intensity modifier.
            
        Returns:
            Dict[str, float]: Kinematic parameters.
        """
        target_speed = base_speed * modifier
        # Simple non-linear acceleration mapping for safety
        acceleration = 2.0 * math.sqrt(modifier) if modifier > 0 else 0.1
        
        return {
            "velocity": round(target_speed, 3),
            "acceleration": round(acceleration, 3),
            "deceleration": round(acceleration * 1.2, 3)
        }


class IntentParser:
    """
    Core class for compiling natural language intent into structured instructions.
    """

    def __init__(self, context: SemanticContext):
        self.context = context
        self.dynamics_engine = SemanticDynamicsEngine()
        self._intent_vocabulary = self._build_vocabulary()

    def _build_vocabulary(self) -> Dict[str, Dict]:
        """Constructs the semantic graph anchor dictionary."""
        return {
            "move": {"action": ActionType.MOVE_ABSOLUTE, "requires_target": True},
            "shift": {"action": ActionType.MOVE_RELATIVE, "requires_target": True},
            "trim": {"action": ActionType.CUT, "requires_target": True},
            "cut": {"action": ActionType.CUT, "requires_target": True},
            "grab": {"action": ActionType.GRIPPER_ACTUATE, "state": "close"},
            "release": {"action": ActionType.GRIPPER_ACTUATE, "state": "open"},
            "wait": {"action": ActionType.WAIT}
        }

    def _extract_semantic_entities(self, text: str) -> Dict[str, Any]:
        """
        Helper function to extract verbs, adverbs, and coordinates from text.
        
        Args:
            text (str): Raw natural language string.
            
        Returns:
            Dict: Extracted entities.
        
        Raises:
            ParsingError: If no actionable verb is found.
        """
        text = text.lower().strip()
        
        # Adverb extraction (simplified regex for demonstration)
        adverb_match = re.search(r'\b(slightly|gently|quickly|rapidly)\b', text)
        adverb = adverb_match.group(0) if adverb_match else None
        
        # Coordinate extraction (e.g., "to 1, 2, 3" or "by 0.5, 0, 0")
        coord_match = re.search(r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)', text)
        target_coords = None
        if coord_match:
            target_coords = (
                float(coord_match.group(1)),
                float(coord_match.group(2)),
                float(coord_match.group(3))
            )

        # Identify main verb
        identified_action = None
        for verb, config in self._intent_vocabulary.items():
            if verb in text:
                identified_action = config
                break
        
        if not identified_action:
            raise ParsingError(f"No recognizable action verb found in intent: '{text}'")

        return {
            "adverb": adverb,
            "target_coords": target_coords,
            "action_config": identified_action
        }

    def compile_intent(self, natural_language_intent: str) -> List[StructuredInstruction]:
        """
        Core Function 1: Compiles a fuzzy human intent into a list of machine instructions.
        
        This function orchestrates the parsing, semantic mapping, and constraint checking.
        
        Args:
            natural_language_intent (str): The user input (e.g., "Gently move to 1, 2, 3").
            
        Returns:
            List[StructuredInstruction]: A sequence of executable commands.
            
        Example:
            >>> ctx = SemanticContext()
            >>> compiler = IntentParser(ctx)
            >>> instructions = compiler.compile_intent("Slightly trim the object at 0, 0, 0.5")
        """
        logger.info(f"Received intent: {natural_language_intent}")
        
        try:
            entities = self._extract_semantic_entities(natural_language_intent)
        except ParsingError as e:
            logger.error(e)
            return []

        # Semantic Dynamics processing
        modifier = self.dynamics_engine.map_adverb_to_modifier(entities["adverb"])
        kinematics = self.dynamics_engine.calculate_kinematics(self.context.max_speed, modifier)

        action_type = entities["action_config"]["action"]
        
        # Handle specific logic for different action types
        instructions = []

        if action_type in [ActionType.MOVE_ABSOLUTE, ActionType.MOVE_RELATIVE, ActionType.CUT]:
            if not entities["target_coords"]:
                raise ParsingError(f"Action {action_type.value} requires target coordinates.")

            target = entities["target_coords"]
            
            # Apply constraint checking
            self._validate_physical_constraints(target, action_type)

            # Construct parameters
            params = {
                "target_position": target,
                **kinematics
            }
            
            desc = f"Execute {action_type.value} with modifier {modifier}"
            instructions.append(StructuredInstruction(
                action_type=action_type,
                parameters=params,
                constraints={"safe_zone": True},
                description=desc
            ))

        elif action_type == ActionType.GRIPPER_ACTUATE:
            state = entities["action_config"].get("state", "toggle")
            instructions.append(StructuredInstruction(
                action_type=ActionType.GRIPPER_ACTUATE,
                parameters={"state": state, "force_modifier": modifier},
                description=f"Actuate gripper '{state}' with force modifier {modifier}"
            ))
        
        else:
             # Fallback or generic handler
            instructions.append(StructuredInstruction(
                action_type=action_type,
                parameters={"default": True},
                description="Generic action execution"
            ))

        logger.info(f"Compiled {len(instructions)} instructions.")
        return instructions

    def _validate_physical_constraints(self, 
                                      target: Tuple[float, float, float], 
                                      action: ActionType) -> bool:
        """
        Core Function 2: Validates the generated parameters against physical constraints.
        
        Checks boundary conditions and logical safety zones.
        
        Args:
            target (Tuple[float, float, float]): Target coordinates (x, y, z).
            action (ActionType): The type of action being performed.
            
        Returns:
            bool: True if safe.
            
        Raises:
            ConstraintViolationError: If the target is unreachable or unsafe.
        """
        x, y, z = target
        limits = self.context.safe_zone_limits
        
        # Boundary Check
        if not (limits[0][0] <= x <= limits[0][1] and
                limits[1][0] <= y <= limits[1][1] and
                limits[2][0] <= z <= limits[2][1]):
            raise ConstraintViolationError(
                f"Target {target} is outside safe operational zone limits {limits}"
            )

        # Floor Check (Z-axis safety)
        if action == ActionType.MOVE_RELATIVE:
            future_z = self.context.current_position[2] + z
            if future_z < 0:
                raise ConstraintViolationError(
                    f"Relative move results in Z collision (Z={future_z})"
                )

        logger.debug(f"Constraints validated for target {target}")
        return True


def format_output(instructions: List[StructuredInstruction]) -> str:
    """
    Auxiliary Function: Formats the list of instructions into a JSON-like 
    string for machine transmission.
    
    Args:
        instructions (List[StructuredInstruction]): List of compiled instructions.
        
    Returns:
        str: Formatted string representation.
    """
    if not instructions:
        return "[]"
    
    output_lines = ["["]
    for i, instr in enumerate(instructions):
        output_lines.append(f"  {{")
        output_lines.append(f"    'command': '{instr.action_type.value}',")
        output_lines.append(f"    'params': {instr.parameters},")
        output_lines.append(f"    'desc': '{instr.description}'")
        comma = "," if i < len(instructions) - 1 else ""
        output_lines.append(f"  }}{comma}")
    output_lines.append("]")
    return "\n".join(output_lines)


# Example Usage
if __name__ == "__main__":
    # Initialize Context
    ctx = SemanticContext(current_position=(0, 0, 1.0))
    compiler = IntentParser(ctx)

    print("-" * 60)
    print("AGI Intent Compiler Test")
    print("-" * 60)

    # Test Case 1: Fuzzy Movement
    intent_1 = "Quickly move to 5, 2, 1.5"
    try:
        result_1 = compiler.compile_intent(intent_1)
        print(f"Intent: '{intent_1}'")
        print(format_output(result_1))
    except Exception as e:
        print(f"Error: {e}")

    print("-" * 40)

    # Test Case 2: High Precision / Low Intensity
    intent_2 = "Slightly trim the edge at 0.1, 0.2, 0.5"
    try:
        result_2 = compiler.compile_intent(intent_2)
        print(f"Intent: '{intent_2}'")
        print(format_output(result_2))
    except Exception as e:
        print(f"Error: {e}")

    print("-" * 40)

    # Test Case 3: Constraint Violation (Example of error handling)
    intent_3 = "Forcefully move to 100, 0, 0"  # Outside limits
    try:
        result_3 = compiler.compile_intent(intent_3)
        print(format_output(result_3))
    except ConstraintViolationError as e:
        print(f"Intent: '{intent_3}'")
        print(f"System Safety Interception: {e}")

    print("-" * 60)