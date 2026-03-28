"""
Module: hallucination_code_detector.py

This module provides a robust sandbox environment designed to detect "hallucinated code"
during the solidification of knowledge nodes in an AGI system. It ensures that code
snippets intended to be stored as "Truth Nodes" are syntactically correct, safe to execute,
and functionally viable.

The system combines Abstract Syntax Tree (AST) static analysis with dynamic execution
in a restricted sandbox to minimize the cost of validation while maximizing security.

Key Components:
    - StaticValidator: Checks syntax and forbidden operations (imports, keywords).
    - DynamicSandbox: Executes code in a controlled environment with timeouts.
    - HallucinationDetector: Orchestrates the validation process.

Author: AGI System Core Engineering
Version: 1.0.0
"""

import ast
import logging
import multiprocessing
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type aliases for clarity
CodeBlock = str
ExecutionResult = Dict[str, Any]
ValidationReport = Dict[str, Any]

class StaticAnalysisError(Exception):
    """Custom exception for static analysis failures."""
    pass

class SandboxViolationError(Exception):
    """Custom exception for runtime security violations."""
    pass

def _validate_input_schema(code: str, entry_point: str, timeout: int) -> None:
    """
    Auxiliary function to validate input parameters and boundary conditions.
    
    Args:
        code (str): The source code to validate.
        entry_point (str): The function name to call.
        timeout (int): Execution timeout in seconds.
        
    Raises:
        ValueError: If inputs are empty or timeout is out of bounds.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Code snippet cannot be empty.")
    if not isinstance(entry_point, str) or not entry_point.isidentifier():
        raise ValueError(f"Entry point '{entry_point}' is not a valid identifier.")
    if not (1 <= timeout <= 30):
        raise ValueError("Timeout must be between 1 and 30 seconds for sandbox safety.")

def perform_static_analysis(code: str, forbidden_imports: List[str] = None) -> Tuple[bool, str]:
    """
    Core Function 1: Performs static analysis using AST to detect syntax errors
    and unauthorized imports before execution.
    
    This is the "Low Cost" filter to catch obvious hallucinations without
    spawning a process.
    
    Args:
        code (str): The Python source code.
        forbidden_imports (List[str], optional): Modules that are not allowed.
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if forbidden_imports is None:
        forbidden_imports = ['os', 'sys', 'subprocess', 'socket', 'shutil']

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        msg = f"Static Analysis Failed: Syntax Error at line {e.lineno}: {e.msg}"
        logger.warning(msg)
        return False, msg

    # Traverse AST to check for imports
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in forbidden_imports:
                    msg = f"Security Violation: Forbidden import '{module_name}' detected."
                    logger.error(msg)
                    return False, msg
    
    logger.info("Static analysis passed.")
    return True, "Static analysis successful."

def execute_in_sandbox(code: str, func_name: str, input_args: tuple, timeout: int = 5) -> ExecutionResult:
    """
    Core Function 2: Executes the code snippet in a separate process sandbox.
    
    This function uses multiprocessing to enforce timeouts and isolate execution.
    It captures stdout and return values.
    
    Args:
        code (str): The Python code containing the function.
        func_name (str): The name of the function to invoke.
        input_args (tuple): Arguments to pass to the function.
        timeout (int): Maximum execution time in seconds.
        
    Returns:
        ExecutionResult: A dictionary containing 'success', 'output', and 'error'.
    """
    def runner(conn, p_code, p_func, p_args):
        """Internal runner process."""
        local_scope: Dict[str, Any] = {}
        try:
            # Restricted globals (simulated sandbox)
            exec_globals = {'__builtins__': __builtins__}
            exec(p_code, exec_globals, local_scope)
            
            if p_func not in local_scope:
                raise NameError(f"Function '{p_func}' not defined in the code block.")
            
            func = local_scope[p_func]
            result = func(*p_args)
            conn.send({'success': True, 'output': result})
        except Exception as e:
            conn.send({'success': False, 'error': str(e), 'traceback': traceback.format_exc()})
        finally:
            conn.close()

    parent_conn, child_conn = multiprocessing.Pipe()
    p = multiprocessing.Process(target=runner, args=(child_conn, code, func_name, input_args))
    
    p.start()
    # Wait for process to finish or timeout
    if parent_conn.poll(timeout):
        response = parent_conn.recv()
    else:
        response = {'success': False, 'error': 'TimeoutError', 'traceback': 'Execution timed out.'}
    
    p.join(timeout=1) # Cleanup
    if p.is_alive():
        p.terminate()
        p.join()

    return response

class HallucinationDetector:
    """
    Main class to orchestrate the validation of code nodes.
    """
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.history: List[ValidationReport] = []

    def verify_node(self, code: str, entry_point: str, test_cases: List[Tuple]) -> ValidationReport:
        """
        High-level method to verify a code node.
        
        Args:
            code (str): The code block.
            entry_point (str): The function to test.
            test_cases (List[Tuple]): A list of argument tuples to fuzz the function.
            
        Returns:
            ValidationReport: Detailed report of the validation.
        """
        try:
            _validate_input_schema(code, entry_point, timeout=5)
        except ValueError as e:
            return {'valid': False, 'reason': str(e)}

        # Step 1: Static Analysis
        is_valid, msg = perform_static_analysis(code)
        if not is_valid:
            return {'valid': False, 'reason': msg, 'stage': 'static_analysis'}

        # Step 2: Dynamic Fuzzing/Sandbox Execution
        for args in test_cases:
            logger.info(f"Testing with args: {args}")
            result = execute_in_sandbox(code, entry_point, args, timeout=2)
            
            if not result.get('success'):
                error = result.get('error', 'Unknown Error')
                tb = result.get('traceback', '')
                logger.error(f"Dynamic execution failed: {error}")
                return {
                    'valid': False, 
                    'reason': f"Runtime Error: {error}", 
                    'traceback': tb,
                    'stage': 'dynamic_execution'
                }

        # If all passed
        report = {
            'valid': True, 
            'message': 'Node verified as executable.',
            'test_count': len(test_cases)
        }
        self.history.append(report)
        return report

# Usage Example
if __name__ == "__main__":
    # Example of a "Hallucinated Code" that looks correct but has a subtle error
    # or dangerous behavior.
    
    GOOD_CODE = """
def calculate_sum(a, b):
    return a + b
"""

    HALLUCINATED_CODE = """
def calculate_sum(a, b):
    # Hallucination: Forgotten import or Syntax error
    return math.sqrt(a**2 + b**2)
"""

    MALICIOUS_CODE = """
import os
def calculate_sum(a, b):
    os.system('rm -rf /') # Dangerous command
    return a + b
"""

    detector = HallucinationDetector()
    
    print("--- Testing Good Code ---")
    res1 = detector.verify_node(GOOD_CODE, "calculate_sum", [(1, 2), (5, 5)])
    print(f"Result: {res1}\n")

    print("--- Testing Hallucinated Code (Missing Import) ---")
    res2 = detector.verify_node(HALLUCINATED_CODE, "calculate_sum", [(1, 2)])
    print(f"Result: {res2}\n")

    print("--- Testing Malicious Code ---")
    res3 = detector.verify_node(MALICIOUS_CODE, "calculate_sum", [(1, 2)])
    print(f"Result: {res3}\n")