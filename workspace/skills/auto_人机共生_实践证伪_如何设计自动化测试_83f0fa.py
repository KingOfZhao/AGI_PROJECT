"""
Automated Test Sandbox for Code Validation
========================================

This module provides a secure sandbox environment to execute and test generated code
against predefined test cases. It quantifies functional correctness and boundary compliance
through automated testing with error handling and detailed reporting.

Features:
- Secure code execution in restricted environment
- Quantified test results (pass/fail rates)
- Boundary condition testing
- Comprehensive error handling
- Detailed test case reporting

Usage:
    test_cases = [
        {'input': (1, 2), 'expected': 3, 'description': 'Basic addition'},
        {'input': ('a', 'b'), 'expected': 'ab', 'description': 'String concatenation'},
        {'input': (0, 0), 'expected': 0, 'description': 'Zero boundary case'}
    ]
    
    sandbox = AutomatedTestSandbox(test_cases)
    results = sandbox.run_tests(code_to_test)
    report = sandbox.generate_report(results)
"""

import sys
import traceback
from typing import List, Dict, Any, Tuple, Optional
import ast
import inspect

class AutomatedTestSandbox:
    """
    A secure sandbox environment for automated code testing.
    
    Attributes:
        test_cases (List[Dict]): List of test cases with inputs, expected outputs, and descriptions
        allowed_modules (List[str]): Whitelisted modules for safe imports
        max_recursion (int): Maximum recursion depth to prevent infinite loops
        timeout (int): Execution timeout in seconds
    """
    
    def __init__(
        self,
        test_cases: List[Dict[str, Any]],
        allowed_modules: Optional[List[str]] = None,
        max_recursion: int = 100,
        timeout: int = 5
    ):
        """
        Initialize the test sandbox.
        
        Args:
            test_cases: List of test cases in format:
                {
                    'input': (arg1, arg2, ...), 
                    'expected': expected_output,
                    'description': str
                }
            allowed_modules: Whitelisted modules (default: ['math', 'datetime'])
            max_recursion: Maximum recursion depth (default: 100)
            timeout: Execution timeout in seconds (default: 5)
        """
        self.test_cases = test_cases
        self.allowed_modules = allowed_modules or ['math', 'datetime']
        self.max_recursion = max_recursion
        self.timeout = timeout
        
        # Security restrictions
        self.restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'enumerate': enumerate,
                'zip': zip,
                'isinstance': isinstance,
                'type': type,
                'Exception': Exception,
                'ValueError': ValueError,
                'TypeError': TypeError,
                'IndexError': IndexError,
                'KeyError': KeyError,
                'AttributeError': AttributeError,
                'ZeroDivisionError': ZeroDivisionError,
            }
        }
        
        # Add allowed modules
        for module in self.allowed_modules:
            try:
                self.restricted_globals[module] = __import__(module)
            except ImportError:
                print(f"Warning: Module '{module}' not available")

    def _validate_code_syntax(self, code: str) -> bool:
        """
        Validate Python syntax of the provided code.
        
        Args:
            code: Python code string to validate
            
        Returns:
            bool: True if syntax is valid
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute code in restricted environment.
        
        Args:
            code: Python code string to execute
            
        Returns:
            Dict containing execution results:
            {
                'success': bool,
                'function': callable or None,
                'error': str or None
            }
        """
        if not self._validate_code_syntax(code):
            return {
                'success': False,
                'function': None,
                'error': "Syntax error in provided code"
            }
        
        try:
            # Set recursion limit
            original_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(self.max_recursion)
            
            # Execute code in restricted environment
            exec_globals = self.restricted_globals.copy()
            exec(code, exec_globals)
            
            # Find test function
            if 'target_function' not in exec_globals:
                return {
                    'success': False,
                    'function': None,
                    'error': "No 'target_function' defined in code"
                }
                
            return {
                'success': True,
                'function': exec_globals['target_function'],
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'function': None,
                'error': f"Execution error: {str(e)}"
            }
        finally:
            # Restore original recursion limit
            sys.setrecursionlimit(original_limit)

    def _run_test_case(
        self, 
        func: callable, 
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single test case.
        
        Args:
            func: Function to test
            test_case: Test case dictionary
            
        Returns:
            Dict containing test results:
            {
                'status': 'PASS' | 'FAIL',
                'output': actual_output,
                'expected': expected_output,
                'error': str or None,
                'description': str
            }
        """
        result = {
            'description': test_case['description'],
            'expected': test_case['expected'],
            'output': None,
            'status': 'FAIL',
            'error': None
        }
        
        try:
            # Prepare input arguments
            inputs = test_case['input']
            if not isinstance(inputs, tuple):
                inputs = (inputs,)
                
            # Execute function with timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Function execution timed out")
                
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout)
            
            try:
                output = func(*inputs)
                result['output'] = output
                result['status'] = 'PASS' if output == test_case['expected'] else 'FAIL'
            finally:
                signal.alarm(0)  # Cancel alarm
                
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'FAIL'
            
        return result

    def run_tests(self, code: str) -> List[Dict[str, Any]]:
        """
        Run all test cases against the provided code.
        
        Args:
            code: Python code string containing 'target_function'
            
        Returns:
            List of test result dictionaries
        """
        # Execute code in sandbox
        execution_result = self._execute_code(code)
        
        if not execution_result['success']:
            # Return failure for all test cases
            return [{
                'description': tc['description'],
                'expected': tc['expected'],
                'output': None,
                'status': 'FAIL',
                'error': execution_result['error']
            } for tc in self.test_cases]
            
        # Run test cases
        results = []
        for test_case in self.test_cases:
            result = self._run_test_case(execution_result['function'], test_case)
            results.append(result)
            
        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a comprehensive test report.
        
        Args:
            results: List of test result dictionaries
            
        Returns:
            Report dictionary with:
            {
                'total_tests': int,
                'passed': int,
                'failed': int,
                'pass_rate': float,
                'boundary_failures': int,
                'error_summary': Dict[str, int],
                'details': List[Dict]
            }
        """
        total = len(results)
        passed = sum(1 for r in results if r['status'] == 'PASS')
        failed = total - passed
        pass_rate = passed / total if total > 0 else 0
        
        # Count boundary failures (tests with edge cases)
        boundary_failures = sum(
            1 for r in results 
            if r['status'] == 'FAIL' and 'boundary' in r['description'].lower()
        )
        
        # Error summary
        error_types = {}
        for result in results:
            if result['status'] == 'FAIL' and result['error']:
                error_type = result['error'].split(':')[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate,
            'boundary_failures': boundary_failures,
            'error_summary': error_types,
            'details': results
        }

    def visualize_results(self, report: Dict[str, Any]) -> None:
        """
        Print a formatted visualization of test results.
        
        Args:
            report: Report dictionary from generate_report()
        """
        print("\n" + "="*60)
        print("AUTOMATED TEST RESULTS".center(60))
        print("="*60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed']} ({report['pass_rate']:.1%})")
        print(f"Failed: {report['failed']}")
        print(f"Boundary Failures: {report['boundary_failures']}")
        
        if report['error_summary']:
            print("\nError Summary:")
            for error, count in report['error_summary'].items():
                print(f"  {error}: {count}")
                
        print("\nDetailed Results:")
        for result in report['details']:
            status = "✓ PASS" if result['status'] == 'PASS' else "✗ FAIL"
            print(f"  {status} | {result['description']}")
            if result['status'] == 'FAIL':
                print(f"      Expected: {result['expected']}")
                print(f"      Received: {result['output']}")
                if result['error']:
                    print(f"      Error: {result['error']}")
        print("="*60 + "\n")


# Example Usage
if __name__ == "__main__":
    # Define test cases
    test_cases = [
        {
            'input': (1, 2),
            'expected': 3,
            'description': 'Basic addition'
        },
        {
            'input': ('a', 'b'),
            'expected': 'ab',
            'description': 'String concatenation'
        },
        {
            'input': (0, 0),
            'expected': 0,
            'description': 'Zero boundary case'
        },
        {
            'input': (10, -5),
            'expected': 5,
            'description': 'Negative number handling'
        },
        {
            'input': (1.5, 2.5),
            'expected': 4.0,
            'description': 'Float addition'
        }
    ]
    
    # Sample code to test
    sample_code = """
def target_function(a, b):
    \"\"\"Sample function for testing\"\"\"
    return a + b
"""
    
    # Create and run sandbox
    sandbox = AutomatedTestSandbox(test_cases)
    results = sandbox.run_tests(sample_code)
    report = sandbox.generate_report(results)
    sandbox.visualize_results(report)