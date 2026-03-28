"""
Module: generative_validation_sandbox
This module implements a verification and defense system for generative content
(code, logic, schemas). It combines generative AI creativity with symbolic
rigor to build high-fidelity logical sandboxes.
"""

import logging
import re
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GenerativeSandbox")

class ContentType(Enum):
    """Enumeration of supported generative content types."""
    CODE = "code"
    LOGIC = "logic"
    SCHEMA = "schema"

class VerificationStatus(Enum):
    """Status of the verification process."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

@dataclass
class VerificationResult:
    """Container for verification results."""
    status: VerificationStatus
    confidence: float
    details: Dict[str, Any]
    execution_time: float

class GenerativeSandbox:
    """
    A high-fidelity logical sandbox for verifying generative AI outputs.
    """
    
    def __init__(self, content_type: ContentType, strict_mode: bool = True):
        """
        Initialize the sandbox for a specific content type.
        
        Args:
            content_type: The type of content to be verified.
            strict_mode: If True, applies stricter validation rules.
        """
        self.content_type = content_type
        self.strict_mode = strict_mode
        self._validators: Dict[ContentType, Callable] = {
            ContentType.CODE: self._validate_code,
            ContentType.LOGIC: self._validate_logic,
            ContentType.SCHEMA: self._validate_schema
        }
        logger.info(f"Initialized sandbox for {content_type.value} (Strict: {strict_mode})")

    def verify_content(
        self, 
        content: str, 
        test_cases: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Main entry point for content verification.
        
        Args:
            content: The generated content to verify.
            test_cases: Optional adversarial test cases.
            context: Additional context for validation.
            
        Returns:
            VerificationResult containing status and details.
            
        Example:
            >>> sandbox = GenerativeSandbox(ContentType.CODE)
            >>> code = "def add(a, b): return a + b"
            >>> result = sandbox.verify_content(code)
            >>> print(result.status)
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Input validation
            if not content or not isinstance(content, str):
                raise ValueError("Content must be a non-empty string")
            
            # Select appropriate validator
            validator = self._validators.get(self.content_type)
            if not validator:
                raise ValueError(f"Unsupported content type: {self.content_type}")
            
            # Run validation
            is_valid, details = validator(content, test_cases, context)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(is_valid, details)
            
            status = VerificationStatus.PASSED if is_valid else VerificationStatus.FAILED
            execution_time = time.time() - start_time
            
            logger.info(f"Verification completed with status: {status.value}")
            
            return VerificationResult(
                status=status,
                confidence=confidence,
                details=details,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return VerificationResult(
                status=VerificationStatus.ERROR,
                confidence=0.0,
                details={"error": str(e)},
                execution_time=time.time() - start_time
            )

    def _validate_code(
        self,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        context: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate generated code content.
        
        Args:
            code: The code string to validate.
            test_cases: Test cases for code validation.
            context: Additional context for validation.
            
        Returns:
            Tuple of (is_valid, details_dict)
        """
        details: Dict[str, Any] = {
            "syntax_check": False,
            "security_check": False,
            "functional_check": False,
            "issues": []
        }
        
        # 1. Syntax validation
        try:
            compile(code, "<string>", "exec")
            details["syntax_check"] = True
        except SyntaxError as e:
            details["issues"].append(f"Syntax error: {e}")
            return False, details
        
        # 2. Security validation (basic check for dangerous patterns)
        dangerous_patterns = [
            r"import\s+os", 
            r"import\s+subprocess",
            r"__import__",
            r"eval\s*\(",
            r"exec\s*\("
        ]
        
        security_issues = []
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                security_issues.append(f"Potentially dangerous pattern: {pattern}")
        
        if security_issues:
            details["security_check"] = False
            details["issues"].extend(security_issues)
            if self.strict_mode:
                return False, details
        else:
            details["security_check"] = True
        
        # 3. Functional validation (if test cases provided)
        if test_cases:
            functional_issues = self._run_code_tests(code, test_cases)
            if functional_issues:
                details["functional_check"] = False
                details["issues"].extend(functional_issues)
                return False, details
            details["functional_check"] = True
        else:
            details["functional_check"] = None  # Not applicable
        
        return True, details

    def _validate_logic(
        self,
        logic: str,
        test_cases: Optional[List[Dict[str, Any]]],
        context: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate logical expressions or rules.
        
        Args:
            logic: The logical content to validate.
            test_cases: Test cases for logic validation.
            context: Additional context for validation.
            
        Returns:
            Tuple of (is_valid, details_dict)
        """
        details: Dict[str, Any] = {
            "consistency_check": False,
            "entailment_check": False,
            "issues": []
        }
        
        # Basic consistency check (placeholder for actual logic validation)
        if "=>" in logic and "<=>" not in logic:
            details["consistency_check"] = True
        else:
            details["issues"].append("Potential logical inconsistency")
            return False, details
        
        # Entailment check (simplified)
        if test_cases:
            entailment_issues = self._check_logical_entailment(logic, test_cases)
            if entailment_issues:
                details["entailment_check"] = False
                details["issues"].extend(entailment_issues)
                return False, details
            details["entailment_check"] = True
        else:
            details["entailment_check"] = None
        
        return True, details

    def _validate_schema(
        self,
        schema: str,
        test_cases: Optional[List[Dict[str, Any]]],
        context: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate JSON schema or similar structured data.
        
        Args:
            schema: The schema content to validate.
            test_cases: Test cases for schema validation.
            context: Additional context for validation.
            
        Returns:
            Tuple of (is_valid, details_dict)
        """
        details: Dict[str, Any] = {
            "syntax_check": False,
            "structural_check": False,
            "issues": []
        }
        
        # Check JSON syntax
        try:
            parsed_schema = json.loads(schema)
            details["syntax_check"] = True
        except json.JSONDecodeError as e:
            details["issues"].append(f"JSON syntax error: {e}")
            return False, details
        
        # Basic structural validation
        required_keys = context.get("required_keys", [])
        missing_keys = [key for key in required_keys if key not in parsed_schema]
        
        if missing_keys:
            details["structural_check"] = False
            details["issues"].append(f"Missing required keys: {missing_keys}")
            return False, details
        
        details["structural_check"] = True
        return True, details

    def _calculate_confidence(self, is_valid: bool, details: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on validation results.
        
        Args:
            is_valid: Whether the content passed validation.
            details: Detailed validation results.
            
        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not is_valid:
            return 0.0
        
        base_score = 0.7
        
        # Add points for each passed check
        if details.get("syntax_check"):
            base_score += 0.1
        if details.get("security_check"):
            base_score += 0.1
        if details.get("functional_check"):
            base_score += 0.1
        
        # Penalize for issues
        if details.get("issues"):
            base_score -= 0.1 * len(details["issues"])
        
        return max(0.0, min(1.0, base_score))

    def _run_code_tests(
        self, 
        code: str, 
        test_cases: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Run functional tests on code content.
        
        Args:
            code: The code to test.
            test_cases: List of test cases with input/output pairs.
            
        Returns:
            List of error messages from failed tests.
        """
        issues = []
        local_vars: Dict[str, Any] = {}
        
        try:
            # Execute code in a controlled environment
            exec(code, {}, local_vars)
            
            # Find the main function (assuming first function is the one to test)
            main_func = None
            for name, obj in local_vars.items():
                if callable(obj) and not name.startswith("__"):
                    main_func = obj
                    break
            
            if not main_func:
                return ["No callable function found in the code"]
            
            # Run test cases
            for i, test in enumerate(test_cases, 1):
                try:
                    result = main_func(*test.get("input", []))
                    expected = test.get("output")
                    
                    if result != expected:
                        issues.append(
                            f"Test case {i} failed: "
                            f"Expected {expected}, got {result}"
                        )
                except Exception as e:
                    issues.append(f"Test case {i} raised exception: {str(e)}")
                    
        except Exception as e:
            issues.append(f"Code execution failed: {str(e)}")
        
        return issues

    def _check_logical_entailment(
        self, 
        logic: str, 
        test_cases: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check logical entailment for given test cases.
        
        Args:
            logic: The logical expression to test.
            test_cases: List of test cases with premises and conclusions.
            
        Returns:
            List of error messages from failed entailment checks.
        """
        issues = []
        # This is a simplified placeholder - actual implementation would use
        # a proper theorem prover or logical inference engine
        
        for i, test in enumerate(test_cases, 1):
            premises = test.get("premises", [])
            conclusion = test.get("conclusion")
            
            # Simplified check - in reality this would be much more complex
            if not all(p in logic for p in premises):
                issues.append(f"Test case {i}: Missing premise in logical expression")
            
            if conclusion and conclusion not in logic:
                issues.append(f"Test case {i}: Conclusion not entailed by logic")
        
        return issues


if __name__ == "__main__":
    # Example usage
    print("=== Code Validation Example ===")
    code_sandbox = GenerativeSandbox(ContentType.CODE)
    
    code = """
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
    """
    
    test_cases = [
        {"input": [[1, 2, 3]], "output": 2.0},
        {"input": [[10, 20, 30, 40]], "output": 25.0},
        {"input": [[]], "output": 0}
    ]
    
    result = code_sandbox.verify_content(code, test_cases)
    print(f"Status: {result.status.value}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Details: {json.dumps(result.details, indent=2)}")
    
    print("\n=== Logic Validation Example ===")
    logic_sandbox = GenerativeSandbox(ContentType.LOGIC)
    
    logic = "(A AND B) => C"
    logic_tests = [
        {"premises": ["A", "B"], "conclusion": "C"}
    ]
    
    result = logic_sandbox.verify_content(logic, logic_tests)
    print(f"Status: {result.status.value}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Details: {json.dumps(result.details, indent=2)}")