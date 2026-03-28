"""
AutoML-based Automated Code Node Unit Testing Module.

This module is designed to perform automated adversarial testing and stress
testing on a repository of SKILL nodes (executable code snippets). It leverages
program analysis to infer input types and constraints, automatically generating
'falsification cases' to probe boundary conditions and potential runtime errors.

The system simulates an AutoML-like process where it iteratively refines test
inputs based on code structure analysis to maximize code coverage and error detection.

Module Attributes:
    MAX_INPUT_GENERATION_ATTEMPTS (int): Limit for generating random inputs per parameter.
    SUPPORTED_TYPES (list): List of Python types supported for automatic generation.
"""

import ast
import inspect
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("AutoSKILLTester")

# Constants
MAX_INPUT_GENERATION_ATTEMPTS = 100
SUPPORTED_TYPES = [int, float, str, list, dict, bool, tuple]

@dataclass
class TestCaseResult:
    """Stores the result of a single test execution."""
    input_data: Dict[str, Any]
    output: Any = None
    exception: Optional[Exception] = None
    execution_time: float = 0.0
    passed: bool = False
    is_adversarial: bool = False

@dataclass
class CodeNode:
    """Represents a SKILL code node."""
    node_id: str
    func: Callable
    signature: inspect.Signature
    source_code: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

class InputGenerationStrategy:
    """
    Strategy class for generating inputs based on type hints and heuristics.
    Implements the 'AutoML' aspect of adaptive input generation.
    """

    def __init__(self):
        self._generators = {
            int: self._generate_int,
            float: self._generate_float,
            str: self._generate_str,
            bool: self._generate_bool,
            list: self._generate_list,
            dict: self._generate_dict,
        }

    def generate(self, param_name: str, param_type: type, is_adversarial: bool = False) -> Any:
        """
        Generates a value based on the type, optionally tailored for stress testing.
        
        Args:
            param_name: Name of the parameter (used for heuristics).
            param_type: The expected type of the parameter.
            is_adversarial: If True, focuses on boundary values.
        
        Returns:
            Generated value.
        """
        generator = self._generators.get(param_type, self._generate_default)
        value = generator(param_name, is_adversarial)
        
        # Post-generation validation
        if not isinstance(value, param_type) and param_type is not Any:
            try:
                # Attempt casting if possible (e.g. int to float)
                value = param_type(value)
            except (ValueError, TypeError):
                pass
        return value

    def _generate_int(self, name: str, adversarial: bool) -> int:
        if adversarial:
            # Boundary values for integers
            return random.choice([0, -1, 1, 2**31 - 1, -2**31, 1000000])
        return random.randint(-100, 100)

    def _generate_float(self, name: str, adversarial: bool) -> float:
        if adversarial:
            return random.choice([0.0, -0.0, 1e-10, 1e10, float('inf'), float('-inf'), float('nan')])
        return random.uniform(-100.0, 100.0)

    def _generate_str(self, name: str, adversarial: bool) -> str:
        if adversarial:
            choices = [
                "",  # Empty
                " ",  # Whitespace
                "A" * 10000,  # Long string
                "'; DROP TABLE users; --",  # SQL injection like
                "<script>alert(1)</script>",  # XSS like
                "🚀💡🔥",  # Unicode/Emoji
            ]
            return random.choice(choices)
        return "test_string"

    def _generate_bool(self, name: str, adversarial: bool) -> bool:
        return random.choice([True, False])

    def _generate_list(self, name: str, adversarial: bool) -> list:
        if adversarial:
            return [[], [1] * 1000, [None]]
        return [1, 2, 3]

    def _generate_dict(self, name: str, adversarial: bool) -> dict:
        if adversarial:
            return {k: v for k, v in zip(range(100), range(100))}
        return {"key": "value"}

    def _generate_default(self, name: str, adversarial: bool) -> Any:
        return None


class AutoSKILLTester:
    """
    Main class for automated unit testing of SKILL nodes.
    """

    def __init__(self):
        self.strategy = InputGenerationStrategy()
        logger.info("AutoSKILLTester initialized with AutoML strategies.")

    def _analyze_code_node(self, func: Callable) -> CodeNode:
        """
        Analyzes a function to extract metadata using AST and inspection.
        """
        try:
            sig = inspect.signature(func)
            source = inspect.getsource(func)
            
            # Parse AST to look for potential assertions or raises
            tree = ast.parse(source)
            
            params_meta = {}
            for name, param in sig.parameters.items():
                # Determine expected type (fallback to Any)
                p_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
                params_meta[name] = {
                    "type": p_type,
                    "default": param.default if param.default != inspect.Parameter.empty else None
                }
            
            node_id = f"node_{func.__name__}_{random.randint(1000, 9999)}"
            return CodeNode(
                node_id=node_id,
                func=func,
                signature=sig,
                source_code=source,
                parameters=params_meta
            )
        except Exception as e:
            logger.error(f"Failed to analyze function {func.__name__}: {e}")
            raise

    def _execute_test(self, node: CodeNode, inputs: Dict[str, Any]) -> TestCaseResult:
        """
        Safely executes the node with generated inputs.
        """
        start_time = time.time()
        result = TestCaseResult(input_data=inputs)
        
        try:
            logger.debug(f"Executing {node.node_id} with inputs: {inputs}")
            output = node.func(**inputs)
            result.output = output
            result.passed = True
        except Exception as e:
            result.exception = e
            result.passed = False
            logger.warning(f"Test case failed for {node.node_id}: {type(e).__name__} - {str(e)}")
        finally:
            result.execution_time = time.time() - start_time
            
        return result

    def generate_adversarial_inputs(self, node: CodeNode) -> List[Dict[str, Any]]:
        """
        Core AutoML function: Generates a set of inputs designed to 'falsify' the code.
        
        It combines boundary analysis and random mutations to create a diverse
        test suite.
        """
        test_suites = []
        
        # 1. Default values test (Happy path)
        happy_path_inputs = {}
        for name, meta in node.parameters.items():
            if meta["default"] is not None:
                happy_path_inputs[name] = meta["default"]
            else:
                happy_path_inputs[name] = self.strategy.generate(name, meta["type"], is_adversarial=False)
        test_suites.append(happy_path_inputs)

        # 2. Adversarial/Boundary tests
        # Try combinations of boundary values
        for _ in range(5): # Generate 5 adversarial cases
            adv_inputs = {}
            for name, meta in node.parameters.items():
                adv_inputs[name] = self.strategy.generate(name, meta["type"], is_adversarial=True)
            test_suites.append(adv_inputs)

        return test_suites

    def run_stress_test(self, skill_nodes: List[Callable], iterations: int = 10) -> Dict[str, List[TestCaseResult]]:
        """
        Runs the automated testing pipeline against a list of SKILL nodes.
        
        Args:
            skill_nodes: A list of callable Python functions (the SKILLs).
            iterations: Number of random test iterations per node.
            
        Returns:
            A dictionary mapping node IDs to their test results.
        """
        all_results = {}
        
        for func in skill_nodes:
            try:
                node = self._analyze_code_node(func)
                logger.info(f"Processing Node: {node.node_id}")
                
                node_results = []
                
                # Generate Adversarial Inputs
                adversarial_inputs = self.generate_adversarial_inputs(node)
                
                # Execute Adversarial Tests
                for inputs in adversarial_inputs:
                    res = self._execute_test(node, inputs)
                    res.is_adversarial = True
                    node_results.append(res)
                
                # Fuzzing / Random Tests
                for i in range(iterations):
                    random_inputs = {}
                    for name, meta in node.parameters.items():
                        random_inputs[name] = self.strategy.generate(name, meta["type"], is_adversarial=False)
                    
                    res = self._execute_test(node, random_inputs)
                    node_results.append(res)
                
                all_results[node.node_id] = node_results
                
                # Log summary for this node
                failures = sum(1 for r in node_results if not r.passed)
                logger.info(f"Node {node.node_id} completed. Total: {len(node_results)}, Failures: {failures}")
                
            except Exception as e:
                logger.error(f"Critical error testing node {getattr(func, '__name__', 'unknown')}: {e}")
                continue

        return all_results

# --- Example Usage and Mock Skills ---

def mock_skill_normalize_data(data: List[float], scale: float = 1.0) -> List[float]:
    """
    Example SKILL 1: Normalizes a list of numbers.
    Input: List[float], float
    Output: List[float]
    """
    if not isinstance(data, list):
        raise ValueError("Input data must be a list")
    if scale == 0:
        raise ZeroDivisionError("Scale cannot be zero")
    
    max_val = max(data) if data else 1.0
    return [x / (max_val / scale) for x in data]

def mock_skill_concat_strings(a: str, b: str) -> str:
    """
    Example SKILL 2: Concatenates strings.
    Input: str, str
    Output: str
    """
    # Vulnerable to memory issues with huge strings
    return a + b + "_processed"

def mock_skill_complex_calc(n: int) -> int:
    """
    Example SKILL 3: Recursive calculation (Fibonacci).
    Input: int
    Output: int
    """
    if n < 0:
        raise ValueError("Input must be non-negative")
    if n > 30:
        # Simulate a node that hangs or crashes on large inputs (recursion depth)
        raise RecursionError("Input too large for recursive implementation")
    
    if n <= 1:
        return n
    return mock_skill_complex_calc(n-1) + mock_skill_complex_calc(n-2)

if __name__ == "__main__":
    # Example Usage
    print("-" * 50)
    print("Starting AutoML-based SKILL Tester")
    print("-" * 50)
    
    # 1. Define/Load Skills
    skills_to_test = [
        mock_skill_normalize_data,
        mock_skill_concat_strings,
        mock_skill_complex_calc
    ]
    
    # 2. Initialize Tester
    tester = AutoSKILLTester()
    
    # 3. Run Tests
    results = tester.run_stress_test(skills_to_test, iterations=5)
    
    # 4. Display Results Summary
    print("\n\n--- TEST REPORT ---")
    for node_id, test_results in results.items():
        failures = [r for r in test_results if not r.passed]
        print(f"Node: {node_id}")
        print(f"  Total Tests: {len(test_results)}")
        print(f"  Success Rate: { (len(test_results) - len(failures)) / len(test_results) * 100:.2f}%")
        
        if failures:
            print("  Detected Errors:")
            for f in failures[:3]: # Show first 3 errors
                print(f"    - Input: {f.input_data}")
                print(f"      Error: {type(f.exception).__name__}: {f.exception}")
        print("-" * 30)