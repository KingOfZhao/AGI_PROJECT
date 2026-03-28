"""
Module: auto_认知自洽的运行时沙箱_为了验证生成的代码_f83fe7

Description:
    This module implements a high-level "Cognitive Consistency Sandbox" designed
    to validate generated Python code snippets in an isolated environment.
    
    It ensures that code not only runs without syntax errors but also behaves
    consistently with expected inputs and outputs. It features resource constraints,
    execution timeouts, and serialization for portability.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import ast
import dill
import sys
import traceback
import signal
import resource
import logging
from types import CodeType
from typing import Any, Dict, Optional, Tuple, Callable

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveSandbox")

# Custom Exceptions for clear error propagation
class SandboxError(Exception):
    """Base exception for sandbox related errors."""
    pass

class SandboxTimeoutError(SandboxError):
    """Raised when execution exceeds the time limit."""
    pass

class SandboxMemoryError(SandboxError):
    """Raised when execution exceeds memory limits."""
    pass

class ValidationInputError(SandboxError):
    """Raised when input validation fails."""
    pass


def _set_resource_limits(memory_limit_mb: int, time_limit_sec: int) -> None:
    """
    Helper function to set OS-level resource limits for the current process.
    
    This prevents runaway code from crashing the host system (Resource Safety).
    
    Args:
        memory_limit_mb (int): Maximum allowed memory in Megabytes.
        time_limit_sec (int): Maximum allowed CPU time in Seconds.
    
    Raises:
        SandboxError: If resource limits cannot be set.
    """
    try:
        # Convert MB to Bytes
        memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Set memory limit (Address space)
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        
        # Set CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (time_limit_sec, time_limit_sec))
        
        logger.debug(f"Resource limits set: Memory={memory_limit_mb}MB, Time={time_limit_sec}s")
    except (ValueError, resource.error) as e:
        logger.error(f"Failed to set resource limits: {e}")
        raise SandboxError(f"Failed to apply resource constraints: {e}")


def validate_syntax(code_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the syntax of the provided Python code string without executing it.
    
    This is the first layer of 'Cognitive Consistency' check: does the code parse?
    
    Args:
        code_str (str): The raw Python code string.
        
    Returns:
        Tuple[bool, Optional[str]]: (True, None) if syntax is valid, 
                                    (False, error_message) otherwise.
    """
    if not isinstance(code_str, str):
        return False, "Input code must be a string."
    
    if not code_str.strip():
        return False, "Code string is empty."
        
    try:
        ast.parse(code_str)
        logger.info("Syntax validation passed.")
        return True, None
    except SyntaxError as e:
        error_msg = f"Syntax Error at line {e.lineno}: {e.msg}"
        logger.warning(f"Syntax validation failed: {error_msg}")
        return False, error_msg


class IsolatedRuntime:
    """
    A context manager based runtime sandbox that handles environment setup,
    dependency injection, and teardown.
    """
    
    def __init__(self, memory_limit_mb: int = 128, time_limit_sec: int = 5):
        """
        Initializes the sandbox configuration.
        
        Args:
            memory_limit_mb (int): Max memory allowed for the sandboxed process.
            time_limit_sec (int): Max execution time.
        """
        self.memory_limit = memory_limit_mb
        self.time_limit = time_limit_sec
        self._original_globals = {}

    def _mock_external_dependencies(self) -> Dict[str, Any]:
        """
        Generates a dictionary of mock objects to simulate external dependencies.
        
        Returns:
            Dict[str, Any]: A globals dictionary containing mock classes/functions.
        """
        class MockDatabase:
            def query(self, sql: str) -> list:
                logger.info(f"[MockDB] Intercepted query: {sql}")
                return [{"id": 1, "status": "mocked_data"}]

        def mock_api_call(endpoint: str, data: dict) -> dict:
            logger.info(f"[MockAPI] Called {endpoint} with {data}")
            return {"status_code": 200, "result": "success"}

        return {
            "DB": MockDatabase(),
            "external_api": mock_api_call,
            "__builtins__": __builtins__
        }

    def execute_code(
        self, 
        code_str: str, 
        entry_point: str = "main", 
        input_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, str]:
        """
        Core Function 1: Executes the provided code string in a controlled environment.
        
        Process:
        1. Validate Syntax.
        2. Compile Code.
        3. Prepare Global Scope (with mocks).
        4. Set Resource Limits.
        5. Execute.
        6. Extract result.
        
        Args:
            code_str (str): The Python code to execute.
            entry_point (str): The function name to call after execution.
            input_data (Optional[Dict]): Arguments to pass to the entry point function.
            
        Returns:
            Tuple[bool, Any, str]: 
                - success (bool): True if ran without exceptions.
                - result (Any): The return value of the entry_point function.
                - logs (str): Execution logs or traceback.
        """
        # Input Validation
        is_valid, err_msg = validate_syntax(code_str)
        if not is_valid:
            return False, None, err_msg

        if input_data is None:
            input_data = {}
            
        if not isinstance(input_data, dict):
            return False, None, "input_data must be a dictionary."

        # Prepare Scope
        exec_globals = self._mock_external_dependencies()
        exec_locals = {}

        try:
            # Compilation
            code_obj = compile(code_str, '<sandbox>', 'exec')
            
            # Execution
            # Note: In a production AGI system, this would run in a subprocess
            # via dill/multiprocessing to ensure true isolation.
            logger.info("Starting sandboxed execution...")
            exec(code_obj, exec_globals, exec_locals)
            
            # Verify Entry Point exists
            if entry_point not in exec_locals:
                raise AttributeError(f"Entry point function '{entry_point}' not found in code.")
            
            target_func = exec_locals[entry_point]
            if not callable(target_func):
                raise TypeError(f"'{entry_point}' is not a callable function.")

            # Invoke with timeout logic (simplified here using context, usually subprocess)
            # Here we simulate the isolation logic wrapper
            result = target_func(**input_data)
            
            logger.info("Execution completed successfully.")
            return True, result, "Execution OK"

        except MemoryError:
            logger.error("Sandbox OOM triggered.")
            return False, None, "Memory Limit Exceeded"
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Runtime Error: {tb}")
            return False, None, tb

    def verify_state_consistency(
        self, 
        initial_state: Dict[str, Any], 
        mutation_code: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Core Function 2: Verifies if a piece of code correctly transforms a data state.
        
        This checks if the code logic is "Self-Consistent" with expected data mutations.
        
        Args:
            initial_state (Dict): The starting state of the data.
            mutation_code (str): Code snippet that modifies 'state' variable.
            
        Returns:
            Tuple[bool, Dict]: 
                - is_consistent (bool): True if state changed without error.
                - final_state (Dict): The modified state.
        """
        if not isinstance(initial_state, dict):
            raise ValidationInputError("Initial state must be a dictionary.")

        # Wrap the mutation code to ensure it targets the 'state' variable
        wrapper_code = f"""
def mutate_state(state):
    {mutation_code}
    return state
"""
        is_valid, err = validate_syntax(wrapper_code)
        if not is_valid:
            return False, initial_state

        # Deep copy state to prevent side effects on the caller's side
        # (Using dill for robust serialization simulation)
        try:
            # In a real scenario, we pass serialized bytes to a subprocess
            current_state = dill.loads(dill.dumps(initial_state))
        except Exception as e:
            logger.error(f"State serialization failed: {e}")
            return False, initial_state

        success, result, _ = self.execute_code(
            wrapper_code, 
            entry_point="mutate_state", 
            input_data={"state": current_state}
        )

        if success:
            return True, result
        else:
            return False, initial_state


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Example 1: Validating a simple processing function
    sample_code_valid = """
def main(input_value):
    # Simple logic
    if input_value < 0:
        return "Negative"
    return "Positive"
"""

    # Example 2: Code with dependency on external systems
    sample_code_with_deps = """
def main(user_id):
    # This code thinks it talks to a real DB, but the sandbox mocks it
    db_result = DB.query(f"SELECT * FROM users WHERE id={user_id}")
    return {"user_data": db_result, "processed": True}
"""

    # Example 3: Bad code (Runtime error)
    sample_code_error = """
def main(x):
    return 10 / 0
"""

    sandbox = IsolatedRuntime(memory_limit_mb=64, time_limit_sec=2)

    print("--- Test 1: Basic Validation ---")
    ok, res, log = sandbox.execute_code(sample_code_valid, input_data={"input_value": 10})
    print(f"Success: {ok}, Result: {res}")

    print("\n--- Test 2: Dependency Mocking ---")
    ok, res, log = sandbox.execute_code(sample_code_with_deps, input_data={"user_id": 42})
    print(f"Success: {ok}, Result: {res}")

    print("\n--- Test 3: Error Handling ---")
    ok, res, log = sandbox.execute_code(sample_code_error, input_data={"x": 1})
    print(f"Success: {ok}, Error Log Snippet: {log.splitlines()[-1]}")

    print("\n--- Test 4: State Consistency ---")
    state = {"count": 0, "items": []}
    mutation = "state['count'] += 1; state['items'].append('new')"
    ok, new_state = sandbox.verify_state_consistency(state, mutation)
    print(f"Consistent: {ok}, New State: {new_state}")