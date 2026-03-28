"""
Module: sop_to_statemachine_translator
Description: Transforms industrial Standard Operating Procedures (SOPs) into
             parametric Finite State Machines (FSMs) for simulation agents.

This module addresses the challenge of mapping non-deterministic natural
language (e.g., "tighten moderately", "check temperature") found in SOPs
into deterministic, executable logic with defined physical constraints.
"""

import logging
import re
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of possible action types in an industrial context."""
    ROTARY_MOTION = auto()
    LINEAR_MOTION = auto()
    SENSOR_CHECK = auto()
    WAIT = auto()
    GRIP = auto()


class PhysicsConstraint:
    """Represents a physical boundary for a parameter."""
    def __init__(self, min_val: float, max_val: float, unit: str):
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit

    def validate(self, value: float) -> bool:
        """Check if value is within bounds."""
        return self.min_val <= value <= self.max_val


class SOPState:
    """
    Represents a single state in the generated State Machine.
    """
    def __init__(self, state_id: str, description: str, 
                 action_func: Callable, params: Dict[str, Any],
                 constraints: Dict[str, PhysicsConstraint],
                 transitions: Dict[str, str]):
        self.state_id = state_id
        self.description = description
        self.action_func = action_func
        self.params = params
        self.constraints = constraints
        self.transitions = transitions  # Map: condition -> next_state_id

    def __repr__(self) -> str:
        return f"<SOPState id={self.state_id} desc='{self.description}'>"


class LinguisticMapper:
    """
    Helper class to map fuzzy linguistic terms to precise numerical values.
    """
    
    # Knowledge Base for linguistic approximation
    LINGUISTIC_DB = {
        'moderately': {'factor': 0.6, 'variance': 0.1},
        'gently': {'factor': 0.3, 'variance': 0.05},
        'firmly': {'factor': 0.9, 'variance': 0.05},
        'high': {'factor': 0.8, 'variance': 0.1},
        'low': {'factor': 0.2, 'variance': 0.1},
        'room_temperature': {'value': 25.0, 'variance': 2.0, 'unit': 'celsius'},
        'ambient': {'value': 1.0, 'variance': 0.1, 'unit': 'atm'}
    }

    @staticmethod
    def resolve_term(term: str, base_value: Optional[float] = None) -> Dict[str, Any]:
        """
        Resolves a linguistic term to a target value.
        
        Args:
            term (str): The fuzzy term (e.g., "moderately").
            base_value (float, optional): The reference max value if term is relative.
        
        Returns:
            Dict containing resolved value and tolerance.
        """
        logger.debug(f"Resolving linguistic term: {term}")
        term = term.lower().strip()
        
        if term not in LinguisticMapper.LINGUISTIC_DB:
            raise ValueError(f"Unknown linguistic term: {term}")
            
        mapping = LinguisticMapper.LINGUISTIC_DB[term]
        
        if 'value' in mapping:
            # Absolute value
            return {
                'target': mapping['value'],
                'tolerance': mapping['variance'],
                'unit': mapping['unit']
            }
        elif 'factor' in mapping and base_value is not None:
            # Relative value
            target = base_value * mapping['factor']
            tol = base_value * mapping['variance']
            return {
                'target': target,
                'tolerance': tol
            }
        else:
            raise ValueError(f"Insufficient data to resolve term: {term}")


def parse_sop_text(raw_text: str) -> List[Dict[str, str]]:
    """
    Parses raw SOP text into structured step dictionaries.
    
    Input Format Example:
        "Step 1: Check if pressure is normal. If yes, proceed."
        
    Output Format:
        [{'step_id': '1', 'text': 'Check if pressure...', 'condition': 'pressure is normal'}]
    """
    logger.info("Parsing raw SOP text...")
    steps = []
    # Simplified regex for demonstration
    pattern = r"Step\s+(\d+):\s+(.*?)(?=\s*Step\s+\d+:|$)"
    matches = re.findall(pattern, raw_text, re.IGNORECASE | re.DOTALL)
    
    if not matches:
        logger.warning("No steps detected in SOP text.")
        return []

    for match in matches:
        step_id = match[0]
        text = match[1].strip()
        
        # Extract simple conditional logic (naive implementation)
        condition = "always"
        if "if" in text.lower():
            parts = text.lower().split("if", 1)
            text = parts[0].strip()
            condition = parts[1].strip()
            
        steps.append({
            'step_id': step_id,
            'text': text,
            'condition': condition
        })
        
    logger.info(f"Successfully parsed {len(steps)} steps.")
    return steps


def translate_to_state_machine(
    parsed_steps: List[Dict[str, str]], 
    equipment_specs: Dict[str, Dict[str, Any]]
) -> Dict[str, SOPState]:
    """
    Core function to translate parsed SOP steps into executable SOPState objects.
    
    Args:
        parsed_steps: Output from parse_sop_text.
        equipment_specs: Dictionary defining physical constraints of involved equipment.
                        e.g., {'valve_a': {'max_torque': 50, 'type': 'rotary'}}
    
    Returns:
        A dictionary mapping State IDs to SOPState objects.
    """
    logger.info("Translating steps to Parametric State Machine...")
    state_machine = {}
    
    for i, step in enumerate(parsed_steps):
        state_id = f"state_{step['step_id']}"
        raw_text = step['text']
        condition = step['condition']
        
        # Determine next state
        next_state_id = "END"
        if i < len(parsed_steps) - 1:
            next_state_id = f"state_{parsed_steps[i+1]['step_id']}"
            
        # Default params and constraints
        params: Dict[str, Any] = {}
        constraints: Dict[str, PhysicsConstraint] = {}
        transitions = {}
        action = ActionType.WAIT # Default dummy action
        
        # --- Heuristic Logic Mapping (The "AGI" reasoning part) ---
        
        # Case 1: Tightening / Rotational
        if "tighten" in raw_text.lower() or "rotate" in raw_text.lower():
            action = ActionType.ROTARY_MOTION
            # Extract equipment ID (simplified)
            equip_id = "default_valve"
            spec = equipment_specs.get(equip_id, {'max_torque': 100})
            
            # Extract fuzzy logic
            modifier = "moderately"
            for word in LinguisticMapper.LINGUISTIC_DB.keys():
                if word in raw_text.lower():
                    modifier = word
                    break
            
            # Calculate parameters
            resolved = LinguisticMapper.resolve_term(modifier, spec['max_torque'])
            params['target_torque'] = resolved['target']
            params['tolerance'] = resolved['tolerance']
            
            # Set constraints
            constraints['torque_limit'] = PhysicsConstraint(0, spec['max_torque'], 'Nm')
            transitions['torque_reached'] = next_state_id
            
        # Case 2: Observation / Sensing
        elif "observe" in raw_text.lower() or "check" in raw_text.lower():
            action = ActionType.SENSOR_CHECK
            
            # Map condition to transition
            if "normal" in condition:
                # Define what "normal" means based on specs
                params['target_temp'] = 25.0
                params['range'] = (20.0, 30.0)
                transitions['in_range'] = next_state_id
                transitions['out_of_range'] = "ERROR_STATE"
            else:
                transitions['success'] = next_state_id

        # Case 3: Default
        else:
            action = ActionType.LINEAR_MOTION
            transitions['complete'] = next_state_id

        # Create State
        new_state = SOPState(
            state_id=state_id,
            description=raw_text,
            action_func=lambda p=params: print(f"Executing action with params: {p}"), # Mock function
            params=params,
            constraints=constraints,
            transitions=transitions
        )
        
        state_machine[state_id] = new_state
        logger.debug(f"Generated state: {state_id}")
        
    return state_machine


def validate_state_machine(sm: Dict[str, SOPState]) -> bool:
    """
    Validates the integrity of the generated state machine.
    Checks:
    1. No deadlocks (states with no exit).
    2. Parameter bounds consistency.
    """
    logger.info("Validating State Machine integrity...")
    for state_id, state in sm.items():
        if not state.transitions and state_id != "END":
            logger.error(f"Validation Error: State {state_id} has no exit transitions (Deadlock).")
            return False
            
        # Check parameters against constraints
        for param_name, value in state.params.items():
            if param_name in state.constraints:
                constraint = state.constraints[param_name]
                if isinstance(value, (int, float)) and not constraint.validate(value):
                    logger.error(f"Validation Error: Param '{param_name}' value {value} out of bounds in {state_id}.")
                    return False
                    
    logger.info("State Machine validation successful.")
    return True


# Example Usage
if __name__ == "__main__":
    # Input Data
    sop_document = """
    Step 1: Observe pressure gauge. If pressure is normal, proceed.
    Step 2: Tighten valve moderately.
    Step 3: Check seal integrity.
    """
    
    equipment_configuration = {
        "default_valve": {"max_torque": 50.0, "type": "ball_valve"},
        "pressure_gauge": {"max_pressure": 100.0, "unit": "psi"}
    }

    print("--- Starting SOP Translation Process ---")
    
    # 1. Parse Text
    parsed_data = parse_sop_text(sop_document)
    
    # 2. Translate to Logic
    state_machine = translate_to_state_machine(parsed_data, equipment_configuration)
    
    # 3. Validate
    is_valid = validate_state_machine(state_machine)
    
    if is_valid:
        print("\n--- Generated State Machine Structure ---")
        for s_id, state in state_machine.items():
            print(f"ID: {s_id}")
            print(f"  Desc: {state.description}")
            print(f"  Action Params: {state.params}")
            print(f"  Constraints: {state.constraints}")
            print(f"  Transitions: {state.transitions}")
            print("-" * 40)