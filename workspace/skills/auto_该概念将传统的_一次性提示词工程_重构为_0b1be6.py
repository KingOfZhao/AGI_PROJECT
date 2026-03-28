"""
Module: intent_compiler.py

This module implements the 'Intent Compiler' concept for AGI systems.
It refactors traditional one-shot prompt engineering into a structured
software engineering compilation process. Natural language inputs are
treated as source code, which is compiled into an Intermediate Representation (IR)
before collapsing into executable physical actions.
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentCompiler")

class IntentStatus(Enum):
    """Status of the Intent compilation process."""
    RAW = "RAW"
    COMPILED = "COMPILED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

@dataclass
class IntentIR:
    """
    Intermediate Representation of an Intent.
    This serves as the 'assembly language' of the cognitive process.
    """
    id: str
    source_text: str
    target_capability: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the IR to a dictionary."""
        return {
            "id": self.id,
            "source_text": self.source_text,
            "target_capability": self.target_capability,
            "parameters": self.parameters,
            "constraints": self.constraints,
            "dependencies": self.dependencies
        }

class IntentCompiler:
    """
    Compiles natural language prompts into structured Intent IRs.
    
    This class mimics a compiler pipeline: 
    1. Lexical/Semantic Analysis (Decomposition)
    2. IR Generation
    3. Isomorphism Verification (Type/Logic checking)
    4. Code Generation (Action execution simulation)
    """

    def __init__(self, capability_registry: Dict[str, Any]):
        """
        Initialize the compiler with a registry of known capabilities.
        
        Args:
            capability_registry (Dict): A dictionary defining valid capabilities and their schemas.
        """
        self.capability_registry = capability_registry
        logger.info("IntentCompiler initialized with %d capabilities.", len(capability_registry))

    def _generate_id(self) -> str:
        """Generates a unique identifier for an intent."""
        return f"intent_{uuid.uuid4().hex[:8]}"

    def _validate_parameters(self, schema: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """
        Validates parameters against a schema (Simulated).
        
        Args:
            schema: The expected parameter schema.
            params: The actual parameters provided.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        # Basic check: Ensure required keys exist
        required = schema.get("required", [])
        for key in required:
            if key not in params:
                logger.warning(f"Missing required parameter: {key}")
                return False
        return True

    def compile_prompt(self, natural_language_prompt: str) -> List[IntentIR]:
        """
        Core Function 1: Decomposes and compiles a prompt into Intent IRs.
        Implements 'Adaptive Granularity Decomposition'.
        
        Args:
            natural_language_prompt (str): The user's raw input.
            
        Returns:
            List[IntentIR]: A list of compiled intermediate representations.
        
        Raises:
            ValueError: If the prompt is empty or invalid.
        """
        if not natural_language_prompt or not isinstance(natural_language_prompt, str):
            logger.error("Invalid prompt input: Must be a non-empty string.")
            raise ValueError("Prompt must be a non-empty string.")

        logger.info(f"Compiling prompt: '{natural_language_prompt[:50]}...'")
        
        # Simulation of NLP decomposition logic
        # In a real AGI, this would involve semantic parsing
        raw_intents = self._mock_decompose(natural_language_prompt)
        compiled_irs = []

        for raw in raw_intents:
            cap_name = raw["capability"]
            if cap_name not in self.capability_registry:
                logger.warning(f"Unknown capability '{cap_name}' requested. Skipping.")
                continue
            
            schema = self.capability_registry[cap_name]
            if self._validate_parameters(schema, raw["parameters"]):
                ir = IntentIR(
                    id=self._generate_id(),
                    source_text=natural_language_prompt,
                    target_capability=cap_name,
                    parameters=raw["parameters"],
                    constraints=raw.get("constraints", {})
                )
                compiled_irs.append(ir)
                logger.debug(f"Successfully compiled IR: {ir.id}")
            else:
                logger.error(f"Parameter validation failed for capability {cap_name}")

        return compiled_irs

    def verify_isomorphism(self, ir_list: List[IntentIR]) -> Tuple[bool, List[IntentIR]]:
        """
        Core Function 2: Verifies 'Intent-Code Isomorphism'.
        Ensures the IR logic matches the semantic constraints and system state.
        
        Args:
            ir_list (List[IntentIR]): The list of IRs to verify.
            
        Returns:
            Tuple[bool, List[IntentIR]]: Verification status and filtered list of valid IRs.
        """
        verified_irs = []
        is_valid = True

        for ir in ir_list:
            # Check logical constraints (Simulated logic)
            # Example: If constraint 'max_items' is 5, but params request 10, fail.
            constraints = ir.constraints
            params = ir.parameters
            
            logic_check = True
            if "max_items" in constraints:
                if params.get("count", 0) > constraints["max_items"]:
                    logger.warning(f"IR {ir.id} failed isomorphism check: Count exceeds max_items.")
                    logic_check = False
            
            if logic_check:
                verified_irs.append(ir)
            else:
                is_valid = False

        if is_valid:
            logger.info("All IRs passed isomorphism verification.")
        else:
            logger.warning("Some IRs failed verification and were filtered.")
            
        return is_valid, verified_irs

    def collapse_to_execution(self, verified_irs: List[IntentIR]) -> List[Dict[str, Any]]:
        """
        Collapses the verified IRs into physical execution commands.
        This is the final 'machine code' generation step.
        
        Args:
            verified_irs (List[IntentIR]): Verified intents.
            
        Returns:
            List[Dict]: Executable command objects.
        """
        commands = []
        for ir in verified_irs:
            cmd = {
                "action_id": ir.id,
                "executor": ir.target_capability,
                "payload": ir.parameters,
                "metadata": {
                    "source": ir.source_text,
                    "timestamp": str(uuid.uuid1().time)
                }
            }
            commands.append(cmd)
            logger.info(f"Generated execution command for {ir.id}")
        return commands

    def _mock_decompose(self, text: str) -> List[Dict[str, Any]]:
        """
        Helper Function: Simulates the decomposition of NL into structured intent data.
        This acts as the 'Lexer/Parser' of the compiler.
        """
        # Mock logic for demonstration purposes
        if "database" in text.lower():
            return [
                {
                    "capability": "db_query",
                    "parameters": {"query": "SELECT * FROM users", "count": 10},
                    "constraints": {"max_items": 100}
                }
            ]
        elif "calculate" in text.lower():
            return [
                {
                    "capability": "math_op",
                    "parameters": {"operation": "add", "operands": [10, 20]},
                    "constraints": {}
                }
            ]
        else:
            return [
                {
                    "capability": "generic_response",
                    "parameters": {"input_text": text},
                    "constraints": {}
                }
            ]

# --- Usage Example ---

if __name__ == "__main__":
    # Define a mock capability registry
    registry = {
        "db_query": {
            "required": ["query"],
            "type": "data_retrieval"
        },
        "math_op": {
            "required": ["operation", "operands"],
            "type": "computation"
        },
        "generic_response": {
            "required": ["input_text"],
            "type": "communication"
        }
    }

    # Initialize the compiler
    compiler = IntentCompiler(registry)

    # Input Prompt
    user_prompt = "Please query the database for all users."

    try:
        # Step 1: Compile Prompt to IR
        logger.info("--- Starting Compilation ---")
        raw_irs = compiler.compile_prompt(user_prompt)

        # Step 2: Verify Isomorphism
        logger.info("--- Starting Verification ---")
        status, verified_irs = compiler.verify_isomorphism(raw_irs)

        # Step 3: Collapse to Execution (if valid)
        if status and verified_irs:
            logger.info("--- Collapsing Wavefunction ---")
            execution_plan = compiler.collapse_to_execution(verified_irs)
            print("\nFinal Execution Plan:")
            print(json.dumps(execution_plan, indent=2))
        else:
            print("Compilation failed verification checks.")

    except Exception as e:
        logger.error(f"System Error: {e}")