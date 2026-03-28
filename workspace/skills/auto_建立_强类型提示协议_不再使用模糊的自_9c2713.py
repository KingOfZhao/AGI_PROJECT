"""
Module: auto_strong_type_protocol.py

This module implements a 'Strong Typed Prompt Protocol' system designed to bring 
software engineering robustness to AI Agent development. Instead of relying on 
ambiguous natural language prompts, it enforces a strict 'Prompt Schema' (simulated 
here using Python's Pydantic, akin to Typescript/Zod).

Core Workflow:
1. Define strict Input and Output schemas.
2. Pre-validation: Validates user input against the Input Schema before LLM call.
3. Execution: Simulates LLM generation.
4. Post-validation: Validates LLM output against the Output Schema.
5. Self-Correction: If validation fails, triggers a 'Type Repair' mechanism 
   (simulated retry) instead of crashing or returning raw errors.

Author: Senior Python Engineer (AGI System Component)
"""

import logging
import json
from typing import Any, Dict, Generic, TypeVar, Optional, List
from pydantic import BaseModel, ValidationError, Field, validator
from datetime import datetime

# ---------------------------------------------------------------------------
# 1. Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StrongTypeProtocol")

# ---------------------------------------------------------------------------
# 2. Type Variables and Schemas
# ---------------------------------------------------------------------------

# Generic Type Variables for Input and Output schemas
InSchema = TypeVar("InSchema", bound=BaseModel)
OutSchema = TypeVar("OutSchema", bound=BaseModel)

class RepairAttemptLog(BaseModel):
    """Helper model to log repair attempts."""
    attempt: int
    error_msg: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ---------------------------------------------------------------------------
# 3. Core Classes and Functions
# ---------------------------------------------------------------------------

class AutoStrongTypeProtocol(Generic[InSchema, OutSchema]):
    """
    The core executor that enforces the Strong Typed Prompt Protocol.
    
    It handles schema validation, simulated LLM calls, and automatic self-correction
    loops when type mismatches occur.
    """
    
    def __init__(
        self, 
        input_model: type[InSchema], 
        output_model: type[OutSchema],
        max_repair_attempts: int = 3
    ):
        """
        Initialize the protocol handler.

        Args:
            input_model: Pydantic model for input validation.
            output_model: Pydantic model for output validation.
            max_repair_attempts: Maximum retries for self-correction.
        """
        self.input_model = input_model
        self.output_model = output_model
        self.max_repair_attempts = max_repair_attempts
        logger.info(f"Protocol initialized for {input_model.__name__} -> {output_model.__name__}")

    def _pre_validate(self, raw_input: Dict[str, Any]) -> InSchema:
        """
        (Internal) Validates input data against the defined Input Schema.
        This acts as the 'Compiler Layer' check before any LLM interaction.
        """
        logger.debug(f"Validating input: {raw_input}")
        try:
            return self.input_model(**raw_input)
        except ValidationError as e:
            logger.error(f"Input Pre-Validation Failed: {e}")
            raise ValueError(f"Input data does not match schema: {e}") from e

    def _post_validate(self, raw_output: Dict[str, Any]) -> OutSchema:
        """
        (Internal) Validates LLM output against the defined Output Schema.
        """
        logger.debug(f"Validating output: {raw_output}")
        try:
            return self.output_model(**raw_output)
        except ValidationError as e:
            logger.warning(f"Output Post-Validation Failed: {e}")
            # Return the error object or raise it to be caught by the repair loop
            raise e

    def _simulate_llm_generation(self, prompt_context: InSchema) -> Dict[str, Any]:
        """
        (Simulated) Calls the LLM API.
        In a real scenario, this would send a JSON request to OpenAI/Anthropic.
        Here we simulate a 'flaky' LLM that might return bad types initially.
        """
        # Simulation logic: returns valid data for this demo
        # In a real AGI system, this is the external API call.
        logger.info("Calling external LLM API...")
        
        # Simulating a response structure
        return {
            "status": "success",
            "data": {
                "user_id": prompt_context.user_id,
                "action": "processed",
                "confidence": 0.98
            },
            "message": "Action completed successfully."
        }

    def _self_repair_mechanism(
        self, 
        previous_output: Dict[str, Any], 
        error: ValidationError, 
        attempt: int
    ) -> Dict[str, Any]:
        """
        (Core Logic) Attempts to fix the output based on the validation error.
        In a real system, this would feed the error back to the LLM with a specific
        'Fix the JSON format' instruction.
        """
        logger.info(f"Activating Self-Repair Mechanism (Attempt {attempt})...")
        
        # Simulation of repair: We force the data into a valid state for demo purposes.
        # Real implementation: llm.repair(prompt, previous_output, error_schema)
        
        # Logic: If 'confidence' was missing or wrong type, we mock a correction.
        repaired_data = previous_output.copy()
        
        # Check specific error fields
        missing_fields = []
        for err in error.errors():
            if err['type'] == 'value_error.missing':
                missing_fields.append(err['loc'][0])
        
        if "confidence" in missing_fields:
            repaired_data["data"]["confidence"] = 0.0 # Default fallback
            
        # Ensure types are correct (simulated coercion)
        if "user_id" in repaired_data.get("data", {}):
            repaired_data["data"]["user_id"] = str(repaired_data["data"]["user_id"])
            
        logger.info("Repair logic applied. Re-submitting for validation.")
        return repaired_data

    def execute(self, raw_input: Dict[str, Any]) -> Optional[OutSchema]:
        """
        Main entry point. Orchestrates the validation -> execution -> repair flow.
        """
        try:
            # Step 1: Pre-validation (Input)
            valid_input = self._pre_validate(raw_input)
            
            # Step 2: LLM Generation
            raw_output = self._simulate_llm_generation(valid_input)
            
            # Step 3: Post-validation (Output) with Repair Loop
            current_attempt = 0
            while current_attempt <= self.max_repair_attempts:
                try:
                    validated_output = self._post_validate(raw_output)
                    logger.info("Process completed successfully with validated output.")
                    return validated_output
                except ValidationError as e:
                    if current_attempt == self.max_repair_attempts:
                        logger.critical("Max repair attempts reached. Failing.")
                        return None
                    
                    # Trigger repair
                    raw_output = self._self_repair_mechanism(raw_output, e, current_attempt + 1)
                    current_attempt += 1

        except ValueError as e:
            logger.critical(f"Execution halted due to invalid input: {e}")
            return None
        except Exception as e:
            logger.critical(f"Unexpected system error: {e}")
            return None

# ---------------------------------------------------------------------------
# 4. Helper Functions and Usage Example
# ---------------------------------------------------------------------------

def setup_system_schemas():
    """
    Helper function to define the Input and Output schemas for this session.
    Demonstrates the definition of strong typing constraints.
    """
    class UserRequest(BaseModel):
        """Strict Input Schema."""
        user_id: str = Field(..., min_length=1, description="Unique User Identifier")
        query: str = Field(..., max_length=100, description="User search query")
        session_active: bool = True

    class AgentResponse(BaseModel):
        """Strict Output Schema."""
        status: str = Field(regex="^(success|failure)$")
        data: Dict[str, Any]
        confidence: float = Field(..., ge=0.0, le=1.0) # Must be between 0 and 1
        
        @validator('data')
        def check_data_keys(cls, v):
            if 'action' not in v:
                raise ValueError("'data' must contain 'action' key")
            return v

    return UserRequest, AgentResponse

def run_demo():
    """
    Usage Example Function.
    Demonstrates the workflow with valid and edge-case inputs.
    """
    print("\n--- Starting Strong Type Protocol Demo ---\n")
    
    # 1. Setup
    InputSchema, OutputSchema = setup_system_schemas()
    agent = AutoStrongTypeProtocol[InputSchema, OutputSchema](
        input_model=InputSchema,
        output_model=OutputSchema,
        max_repair_attempts=2
    )
    
    # 2. Test Case: Valid Input
    print("[Test 1] Processing valid input...")
    valid_input = {
        "user_id": "USR_998",
        "query": "Analyze financial report",
        "session_active": True
    }
    result = agent.execute(valid_input)
    if result:
        print(f"Result: {result.json(indent=2)}")
    
    # 3. Test Case: Invalid Input (Trigger Pre-Validation Failure)
    print("\n[Test 2] Processing invalid input (missing user_id)...")
    invalid_input = {
        "user_id": "",  # Fails min_length=1
        "query": "Hack the planet"
    }
    result = agent.execute(invalid_input)
    print(f"Result: {result}") # Should be None

if __name__ == "__main__":
    run_demo()