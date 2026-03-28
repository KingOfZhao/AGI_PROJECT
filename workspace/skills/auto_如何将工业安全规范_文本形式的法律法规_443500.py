"""
Module: industrial_safety_guard
Description: Transforms industrial safety regulations into executable logic constraints.
             Acts as a pre-filter for AGI action planning to ensure safety compliance.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SafetyPriority(Enum):
    """Enumeration of safety priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class Action:
    """Data structure representing an AGI-generated action."""
    action_id: str
    action_type: str
    target_device: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]

@dataclass
class SafetyConstraint:
    """Data structure representing a safety constraint."""
    constraint_id: str
    description: str
    priority: SafetyPriority
    condition_logic: str  # Logical expression in string format
    violation_message: str

class IndustrialSafetyGuard:
    """
    Core class that enforces safety constraints on AGI actions.
    Parses textual regulations into executable logic and validates actions.
    """
    
    def __init__(self):
        self.constraints: Dict[str, SafetyConstraint] = {}
        self.device_states: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized IndustrialSafetyGuard")
    
    def parse_regulation_text(self, text: str) -> List[SafetyConstraint]:
        """
        Parse textual safety regulations into executable constraints.
        
        Args:
            text: Raw text containing safety regulations
            
        Returns:
            List of parsed SafetyConstraint objects
            
        Example:
            >>> guard = IndustrialSafetyGuard()
            >>> text = "When tank pressure > 5MPa, never close inlet valve."
            >>> constraints = guard.parse_regulation_text(text)
        """
        if not text or not isinstance(text, str):
            logger.error("Invalid regulation text input")
            raise ValueError("Regulation text must be a non-empty string")
        
        logger.info(f"Parsing regulation text of length {len(text)}")
        constraints = []
        
        # Pattern matching for safety rules (simplified example)
        patterns = [
            (r"When (.+), never (.+)\.", "IF {0} THEN NOT {1}"),
            (r"Always (.+) when (.+)\.", "IF {1} THEN {0}"),
            (r"(.+) is prohibited under (.+).", "IF {1} THEN NOT {0}")
        ]
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            for pattern, template in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    condition = match.group(1).strip()
                    action = match.group(2).strip()
                    
                    constraint = SafetyConstraint(
                        constraint_id=f"const_{len(self.constraints)+1}",
                        description=line,
                        priority=SafetyPriority.HIGH,
                        condition_logic=template.format(condition, action),
                        violation_message=f"Violation of safety rule: {line}"
                    )
                    constraints.append(constraint)
                    self.constraints[constraint.constraint_id] = constraint
                    logger.debug(f"Added constraint: {constraint.constraint_id}")
        
        logger.info(f"Parsed {len(constraints)} constraints from text")
        return constraints
    
    def validate_action(self, action: Action) -> Tuple[bool, Optional[str]]:
        """
        Validate an AGI action against all safety constraints.
        
        Args:
            action: The Action object to validate
            
        Returns:
            Tuple of (is_valid, violation_message)
            
        Example:
            >>> guard = IndustrialSafetyGuard()
            >>> action = Action("act1", "close_valve", "inlet_valve", {}, {})
            >>> is_valid, msg = guard.validate_action(action)
        """
        if not isinstance(action, Action):
            logger.error("Invalid action type provided")
            raise TypeError("Input must be an Action object")
            
        logger.info(f"Validating action {action.action_id} on {action.target_device}")
        
        # Check device state exists
        if action.target_device not in self.device_states:
            logger.warning(f"No state information for device {action.target_device}")
            # Proceed with validation assuming no state constraints
        
        for constraint in self.constraints.values():
            try:
                if self._evaluate_constraint(constraint, action):
                    logger.warning(
                        f"Action {action.action_id} violates constraint {constraint.constraint_id}"
                    )
                    return (False, constraint.violation_message)
            except Exception as e:
                logger.error(
                    f"Error evaluating constraint {constraint.constraint_id}: {str(e)}"
                )
                # Fail safe - assume constraint is violated
                return (False, f"Error evaluating safety constraint: {str(e)}")
        
        logger.info(f"Action {action.action_id} passed all safety checks")
        return (True, None)
    
    def _evaluate_constraint(
        self, 
        constraint: SafetyConstraint, 
        action: Action
    ) -> bool:
        """
        Helper function to evaluate if an action violates a constraint.
        
        Args:
            constraint: The safety constraint to evaluate
            action: The action being evaluated
            
        Returns:
            True if the action violates the constraint, False otherwise
        """
        # This is a simplified evaluation - in a real system this would
        # need to parse and evaluate complex logical expressions
        logic = constraint.condition_logic.lower()
        
        # Example evaluation for our sample constraint
        if "not" in logic and action.action_type in logic:
            condition_part = logic.split("if")[1].split("then")[0].strip()
            # In a real system, we'd evaluate the condition against device states
            # Here we're just doing simple pattern matching
            if "pressure >" in condition_part:
                # Check if pressure is high (mock implementation)
                pressure = self.device_states.get(
                    action.target_device, {}
                ).get("pressure", 0)
                
                # Extract threshold from condition (very simplified)
                try:
                    threshold = float(condition_part.split(">")[1].split()[0])
                except (IndexError, ValueError):
                    threshold = 5.0  # Default fallback
                
                if pressure > threshold:
                    return True
        
        return False
    
    def update_device_state(
        self, 
        device_id: str, 
        state: Dict[str, Any]
    ) -> None:
        """
        Update the state information for a device.
        
        Args:
            device_id: Unique identifier for the device
            state: Dictionary containing device state variables
            
        Example:
            >>> guard = IndustrialSafetyGuard()
            >>> guard.update_device_state("inlet_valve", {"pressure": 6.2, "status": "open"})
        """
        if not device_id or not isinstance(device_id, str):
            raise ValueError("device_id must be a non-empty string")
            
        if not state or not isinstance(state, dict):
            raise ValueError("state must be a non-empty dictionary")
            
        self.device_states[device_id] = state
        logger.debug(f"Updated state for device {device_id}")

# Example usage
if __name__ == "__main__":
    # Initialize the safety guard
    guard = IndustrialSafetyGuard()
    
    # Example regulation text
    regulations = """
    When tank pressure > 5MPa, never close inlet valve.
    Always verify ventilation before starting reactor.
    Operating machinery without safety gear is prohibited under all conditions.
    """
    
    # Parse regulations
    constraints = guard.parse_regulation_text(regulations)
    print(f"Parsed {len(constraints)} safety constraints")
    
    # Set up device states
    guard.update_device_state("inlet_valve", {"pressure": 6.2, "status": "open"})
    guard.update_device_state("reactor", {"status": "idle", "temperature": 25})
    
    # Test actions
    test_actions = [
        Action(
            action_id="act1",
            action_type="close_valve",
            target_device="inlet_valve",
            parameters={},
            context={}
        ),
        Action(
            action_id="act2",
            action_type="start",
            target_device="reactor",
            parameters={"ramp_up": "fast"},
            context={"safety_gear": False}
        )
    ]
    
    # Validate actions
    for action in test_actions:
        is_valid, message = guard.validate_action(action)
        print(f"Action {action.action_id}: {'VALID' if is_valid else 'INVALID'}")
        if not is_valid:
            print(f"  Reason: {message}")