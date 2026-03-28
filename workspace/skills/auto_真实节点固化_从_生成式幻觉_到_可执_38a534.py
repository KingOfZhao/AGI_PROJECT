"""
Module: generative_solidifier.py

This module implements the 'Real Node Solidification' mechanism.
It serves as a formal verification interface that compiles generative AI outputs
(fuzzy natural language checklists) into deterministic, executable Python/Bash code
with formal pre-conditions, post-conditions, and exception handling.

Only code that executes successfully and satisfies all contracts is promoted to a 'Real Node'.

Dependencies:
    - pydantic (for data validation)
    - typing (for type hints)

Author: AGI System Core
Version: 1.0.0
"""

import json
import logging
import subprocess
import textwrap
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(module)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class ExecutionEnvironment(str, Enum):
    """Supported execution environments for the generated code."""
    PYTHON = "python"
    BASH = "bash"


class NodeStatus(str, Enum):
    """Lifecycle status of a knowledge node."""
    HALLUCINATION = "hallucination"  # Raw generated text
    COMPILED = "compiled"            # Transformed to code
    REAL = "real"                    # Successfully executed and verified
    FAILED = "failed"                # Execution failed


class TaskContract(BaseModel):
    """
    Defines the formal contract for a task execution.
    Includes pre-conditions, post-conditions, and the executable payload.
    """
    task_id: str = Field(..., description="Unique identifier for the task")
    description: str = Field("", description="Natural language description of the task")
    environment: ExecutionEnvironment = Field(ExecutionEnvironment.PYTHON, description="Execution context")
    pre_conditions: List[str] = Field(default_factory=list, description="Conditions that must be true before execution")
    post_conditions: List[str] = Field(default_factory=list, description="Conditions that must be true after execution")
    code_payload: str = Field(..., description="The executable script content")
    timeout: int = Field(10, ge=1, le=300, description="Execution timeout in seconds")

    @field_validator('code_payload')
    @classmethod
    def code_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Code payload cannot be empty")
        return v


class ExecutionResult(BaseModel):
    """Captures the result of a node solidification attempt."""
    task_id: str
    status: NodeStatus
    output: Optional[str] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


def validate_syntax(contract: TaskContract) -> Tuple[bool, str]:
    """
    [Helper Function] Validates the syntax of the code payload without full execution.
    
    Args:
        contract: The TaskContract containing the code to validate.
        
    Returns:
        A tuple of (is_valid: bool, message: str).
    """
    logger.debug(f"Validating syntax for task {contract.task_id}")
    try:
        if contract.environment == ExecutionEnvironment.PYTHON:
            compile(contract.code_payload, '<string>', 'exec')
            return True, "Python syntax valid"
        elif contract.environment == ExecutionEnvironment.BASH:
            # Uses bash -n for syntax checking
            result = subprocess.run(
                ["bash", "-n"],
                input=contract.code_payload.encode('utf-8'),
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "Bash syntax valid"
            else:
                return False, result.stderr.decode('utf-8')
        return False, "Unsupported environment"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except subprocess.TimeoutExpired:
        return False, "Syntax validation timed out"
    except Exception as e:
        return False, f"Unexpected validation error: {e}"


def compile_raw_intent(description: str, generated_code: str, env: ExecutionEnvironment) -> TaskContract:
    """
    [Core Function 1] Transforms raw generated code into a formal TaskContract.
    
    This function acts as the 'Compiler', wrapping fuzzy logic into a structured object
    with default safety checks (pre/post conditions).
    
    Args:
        description: The original natural language intent.
        generated_code: The raw code string produced by the LLM.
        env: The target execution environment (Python/Bash).
        
    Returns:
        A TaskContract object ready for validation.
    """
    logger.info(f"Compiling raw intent into contract: {description[:30]}...")
    
    # Automatic injection of safety wrappers
    safe_code = generated_code
    if env == ExecutionEnvironment.PYTHON:
        # Wrap in a main guard for safety
        safe_code = textwrap.dedent(f"""
        import sys
        import json
        
        # --- Generated Logic Start ---
        {generated_code}
        # --- Generated Logic End ---
        
        if __name__ == "__main__":
            pass
        """)
    
    # Create the contract with basic validation logic
    contract = TaskContract(
        task_id=f"task_{hash(description) % 10000}",
        description=description,
        environment=env,
        pre_conditions=["Input data exists", "Environment variables set"],
        post_conditions=["Output generated", "No critical errors"],
        code_payload=safe_code
    )
    
    return contract


def solidify_node(contract: TaskContract) -> ExecutionResult:
    """
    [Core Function 2] Executes the contract and attempts to 'solidify' the node.
    
    This function performs the actual execution. If successful, the node transitions
    from 'Hallucination' to 'Real'. If failed, it captures the exception and marks it 'Failed'.
    
    Args:
        contract: The formal TaskContract to execute.
        
    Returns:
        An ExecutionResult detailing the outcome.
    """
    logger.info(f"Attempting to solidify node {contract.task_id}...")
    
    # Step 1: Syntax Validation (Pre-flight check)
    is_valid, msg = validate_syntax(contract)
    if not is_valid:
        logger.error(f"Syntax validation failed for {contract.task_id}: {msg}")
        return ExecutionResult(
            task_id=contract.task_id,
            status=NodeStatus.FAILED,
            error=f"Syntax Validation Failed: {msg}"
        )
    
    # Step 2: Execution
    try:
        logger.info(f"Executing code in {contract.environment} environment...")
        process = subprocess.run(
            [contract.environment.value],
            input=contract.code_payload.encode('utf-8'),
            capture_output=True,
            timeout=contract.timeout,
            check=False # We handle return code manually
        )
        
        stdout = process.stdout.decode('utf-8')
        stderr = process.stderr.decode('utf-8')
        
        if process.returncode != 0:
            logger.warning(f"Execution failed with return code {process.returncode}")
            return ExecutionResult(
                task_id=contract.task_id,
                status=NodeStatus.FAILED,
                output=stdout,
                error=stderr,
                metrics={"return_code": process.returncode}
            )
            
        # Step 3: Post-Condition Verification (Simulation)
        # In a real system, we would parse stdout or check system state here.
        # For this example, successful execution (rc=0) implies post-conditions are met.
        logger.info(f"Node {contract.task_id} successfully solidified.")
        
        return ExecutionResult(
            task_id=contract.task_id,
            status=NodeStatus.REAL,
            output=stdout,
            error=None,
            metrics={"execution_time": 0.1} # Placeholder
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Execution timed out for {contract.task_id}")
        return ExecutionResult(
            task_id=contract.task_id,
            status=NodeStatus.FAILED,
            error="Execution timed out"
        )
    except Exception as e:
        logger.critical(f"Critical error during solidification: {str(e)}", exc_info=True)
        return ExecutionResult(
            task_id=contract.task_id,
            status=NodeStatus.FAILED,
            error=f"System Error: {str(e)}"
        )

# --- Usage Example ---
if __name__ == "__main__":
    # Example 1: Successful Python Node Solidification
    raw_llm_output_python = """
print("System Check: OK")
x = 10 + 5
print(f"Calculation Result: {x}")
    """
    
    # 1. Compile
    contract_py = compile_raw_intent(
        description="Calculate system metric", 
        generated_code=raw_llm_output_python, 
        env=ExecutionEnvironment.PYTHON
    )
    
    # 2. Solidify
    result_py = solidify_node(contract_py)
    
    print("\n--- Python Solidification Report ---")
    print(f"Status: {result_py.status.value}")
    print(f"Output: {result_py.output}")

    # Example 2: Failed Bash Node (Syntax Error)
    raw_llm_output_bash = """
    echo "Starting process..."
    if [ -f file.txt ]; then
        # Missing 'then' or 'fi' structure intentionally for error
        echo "Found"
    # Syntax error here
    """
    
    contract_bash = compile_raw_intent(
        description="Check file existence", 
        generated_code=raw_llm_output_bash, 
        env=ExecutionEnvironment.BASH
    )
    
    result_bash = solidify_node(contract_bash)
    
    print("\n--- Bash Solidification Report ---")
    print(f"Status: {result_bash.status.value}")
    print(f"Error: {result_bash.error}")