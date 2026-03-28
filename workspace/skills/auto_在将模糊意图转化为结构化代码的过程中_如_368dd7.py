"""
Module: intent_state_machine.py

This module implements a Context-Aware Intent State Machine designed to handle
the translation of fuzzy, evolving user intents into structured, logically
consistent code generation directives.

It addresses the challenge of 'Intent Amnesia' in long conversational sessions
by maintaining a hierarchical state, managing constraints (hard rules vs. soft
preferences), and resolving logical conflicts before generating code.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import hashlib
import json
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class ConstraintPriority(Enum):
    """Defines the weight of a constraint during conflict resolution."""
    LOW = 1        # Style preferences (e.g., variable naming styles)
    MEDIUM = 2     # Structural preferences (e.g., use classes over functions)
    HIGH = 3       # Functional requirements (e.g., must handle errors)
    CRITICAL = 4   # Non-negotiable (e.g., language version, security policies)


@dataclass
class Constraint:
    """Represents a single logical constraint or requirement."""
    key: str
    value: Any
    priority: ConstraintPriority
    source_turn: int  # Which conversation turn introduced this
    description: str = ""


@dataclass
class IntentSnapshot:
    """A snapshot of the user's intent at a specific conversation turn."""
    turn_id: int
    raw_input: str
    parsed_intent: str
    active_constraints: Dict[str, Constraint]
    generated_code_snippet: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class IntentInconsistencyError(Exception):
    """Raised when a new intent critically conflicts with existing locked constraints."""
    pass


# --- Core Component: Context State Machine ---

class IntentContextStateMachine:
    """
    Manages the lifecycle of coding intents within a session.
    
    Uses a state machine approach to track the evolution of requirements and
    ensures logical self-consistency.
    
    Attributes:
        session_id (str): Unique identifier for the session.
        history (List[IntentSnapshot]): Log of all processed intents.
        current_constraints (Dict[str, Constraint]): The active set of requirements.
        locked_keys (Set[str]): Constraints that cannot be overridden by lower priorities.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: List[IntentSnapshot] = []
        self.current_constraints: Dict[str, Constraint] = {}
        self.locked_keys: Set[str] = set()
        self._turn_counter = 0
        
        # Internal State Machine States
        self._state = "INITIALIZED"
        logger.info(f"Session {self.session_id}: State Machine Initialized.")

    def _validate_input_payload(self, payload: Dict[str, Any]) -> bool:
        """Validates the structure of the incoming intent payload."""
        if not isinstance(payload, dict):
            raise ValueError("Input payload must be a dictionary.")
        if 'intent' not in payload:
            raise ValueError("Payload missing required key: 'intent'")
        return True

    def _resolve_conflicts(self, new_constraint: Constraint) -> Tuple[bool, str]:
        """
        Checks if the new constraint conflicts with existing ones.
        Logic:
        - If new priority >= existing priority: Override (Update).
        - If new priority < existing priority & existing is locked: Reject.
        - Else: Override with warning.
        """
        key = new_constraint.key
        if key in self.current_constraints:
            existing = self.current_constraints[key]
            
            # Logic: Higher or equal priority overrides
            if new_constraint.priority.value >= existing.priority.value:
                if key in self.locked_keys and new_constraint.priority.value < ConstraintPriority.CRITICAL.value:
                    msg = f"Constraint '{key}' is locked and cannot be changed by non-critical directives."
                    logger.warning(msg)
                    return False, msg
                
                logger.info(f"Overriding constraint '{key}' (Prio: {existing.priority.name} -> {new_constraint.priority.name})")
                return True, "Constraint Updated"
            else:
                msg = f"New constraint for '{key}' has lower priority ({new_constraint.priority.name}) than existing ({existing.priority.name}). Ignoring."
                logger.info(msg)
                return False, msg
        
        return True, "Constraint Added"

    def update_context(self, raw_input: str, intent_payload: Dict[str, Any]) -> IntentSnapshot:
        """
        Core Function 1: Updates the state machine with a new user intent.
        
        This method processes raw fuzzy input, extracts structured constraints,
        resolves logical conflicts, and advances the state.
        
        Args:
            raw_input (str): The user's raw natural language input.
            intent_payload (Dict): Structured data extracted by an upstream NLU module.
                                   Expected keys: 'intent', 'constraints' (list of dicts).
        
        Returns:
            IntentSnapshot: The state of the context after processing this turn.
        
        Raises:
            IntentInconsistencyError: If a critical logic violation occurs.
            ValueError: If payload format is invalid.
        """
        try:
            self._validate_input_payload(intent_payload)
            self._turn_counter += 1
            turn_id = self._turn_counter
            
            logger.info(f"[Turn {turn_id}] Processing intent: {intent_payload.get('intent')}")

            # Extract and process constraints
            incoming_constraints = intent_payload.get('constraints', [])
            valid_new_constraints: Dict[str, Constraint] = {}

            for c_data in incoming_constraints:
                if not all(k in c_data for k in ['key', 'value', 'priority']):
                    logger.warning(f"Skipping malformed constraint: {c_data}")
                    continue
                
                try:
                    priority = ConstraintPriority[c_data['priority'].upper()]
                except KeyError:
                    priority = ConstraintPriority.MEDIUM

                constraint = Constraint(
                    key=c_data['key'],
                    value=c_data['value'],
                    priority=priority,
                    source_turn=turn_id,
                    description=c_data.get('desc', '')
                )
                
                # Check for conflicts
                approved, msg = self._resolve_conflicts(constraint)
                if approved:
                    valid_new_constraints[constraint.key] = constraint
                    # Critical constraints are automatically locked
                    if priority == ConstraintPriority.CRITICAL:
                        self.locked_keys.add(constraint.key)
                else:
                    if priority == ConstraintPriority.CRITICAL:
                        # If a critical constraint is rejected due to locking, this is a hard error
                        raise IntentInconsistencyError(f"Critical conflict: {msg}")

            # Merge into current context
            self.current_constraints.update(valid_new_constraints)
            
            # Create Snapshot
            snapshot = IntentSnapshot(
                turn_id=turn_id,
                raw_input=raw_input,
                parsed_intent=intent_payload['intent'],
                active_constraints=dict(self.current_constraints) # Copy current state
            )
            self.history.append(snapshot)
            
            logger.info(f"[Turn {turn_id}] Context updated. Total constraints: {len(self.current_constraints)}")
            return snapshot

        except Exception as e:
            logger.error(f"Error updating context: {str(e)}")
            raise

    def generate_code_directive(self) -> Dict[str, Any]:
        """
        Core Function 2: Generates a structured directive for the Code Generator.
        
        It compiles the current state and constraints into a prompt or structure
        that ensures the generated code adheres to all accumulated logic.
        
        Returns:
            Dict[str, Any]: A structured JSON-serializable directive containing:
                            - 'instruction': The aggregated logical instruction.
                            - 'technical_requirements': Key-value pairs of constraints.
                            - 'context_hash': Hash of the current state for cache validation.
        """
        if not self.current_constraints:
            return {"instruction": "No specific constraints. Generate standard boilerplate.", "technical_requirements": {}}

        # Aggregate technical requirements
        tech_reqs = {
            k: {"value": v.value, "priority": v.priority.name}
            for k, v in self.current_constraints.items()
        }

        # Generate a summary instruction (Simulating an LLM prompt prep)
        # In a real AGI system, this would synthesize natural language instructions.
        instruction_block = [
            f"Ensure {v.description or k} is set to {v.value}."
            for k, v in self.current_constraints.items()
            if v.priority.value >= ConstraintPriority.MEDIUM.value
        ]
        
        # Calculate state hash for consistency checks
        state_hash = self._compute_state_hash()
        
        directive = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "instruction_block": instruction_block,
            "technical_requirements": tech_reqs,
            "context_hash": state_hash
        }
        
        logger.info(f"Generated Directive for turn {self._turn_counter}. Hash: {state_hash[:8]}")
        return directive

    def _compute_state_hash(self) -> str:
        """
        Helper Function: Computes a hash of the current context state.
        Useful for caching and verifying that the context hasn't drifted unexpectedly.
        """
        # Sort keys to ensure deterministic hash
        state_repr = json.dumps(
            {k: asdict(v) for k, v in sorted(self.current_constraints.items())},
            sort_keys=True
        )
        return hashlib.sha256(state_repr.encode()).hexdigest()


# --- Usage Example & Demonstration ---

if __name__ == "__main__":
    # Initialize the State Machine
    sm = IntentContextStateMachine(session_id="sess_8823_abc")
    
    print("--- Turn 1: Initial Request ---")
    # User wants a Python function to read files.
    turn1_payload = {
        "intent": "create_file_reader",
        "constraints": [
            {"key": "language", "value": "Python", "priority": "CRITICAL", "desc": "Target language"},
            {"key": "logging", "value": True, "priority": "HIGH", "desc": "Enable logging"}
        ]
    }
    
    try:
        snapshot1 = sm.update_context("I need a python script to read files.", turn1_payload)
        print(f"State after Turn 1: {len(snapshot1.active_constraints)} constraints.")
        
        # Generate directive for code generator
        directive1 = sm.generate_code_directive()
        print(f"Directive 1 Requirements: {list(directive1['technical_requirements'].keys())}")
        
    except (ValueError, IntentInconsistencyError) as e:
        print(f"Error: {e}")

    print("\n--- Turn 2: Evolving Intent (Refinement) ---")
    # User changes mind about logging level or adds specific library
    # Note: Trying to change 'language' to 'Java' (lower priority) should fail if CRITICAL is locked
    turn2_payload = {
        "intent": "refine_reader",
        "constraints": [
            {"key": "library", "value": "pandas", "priority": "MEDIUM", "desc": "Use pandas library"},
            {"key": "language", "value": "Java", "priority": "LOW", "desc": "User mentioned Java by mistake"}
        ]
    }
    
    try:
        snapshot2 = sm.update_context("Actually, use pandas. Maybe make it Java?", turn2_payload)
        # Check if language remained Python
        current_lang = sm.current_constraints['language'].value
        print(f"Language constraint check: {current_lang} (Should be Python)")
        print(f"Library constraint check: {sm.current_constraints.get('library')}")
        
        directive2 = sm.generate_code_directive()
        print(f"Directive 2 Hash: {directive2['context_hash'][:16]}...")
        
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Turn 3: Logical Conflict (Critical) ---")
    # User tries to force a change that violates a locked constraint logic
    # Assuming we lock language, trying to change it to CRITICAL might trigger logic
    # (Depends on implementation details of conflict resolution)
    
    print("State Machine processing completed.")