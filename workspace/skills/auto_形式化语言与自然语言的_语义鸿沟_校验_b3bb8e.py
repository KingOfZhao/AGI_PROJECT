"""
Module: semantic_gap_verifier
Description: AGI Skill for verifying the semantic consistency between natural language
             intents and executable code implementations. It detects logical or common-sense
             contradictions that syntax checkers miss.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticGapVerifier")

@dataclass
class VerificationResult:
    """Holds the result of the semantic verification process."""
    is_valid: bool
    score: float  # 0.0 to 1.0, where 1.0 is perfect alignment
    reason: str
    anomalies: List[str]

class SemanticRegistry:
    """
    A mock registry for semantic constraints and common-sense rules.
    In a full AGI system, this would interface with a Knowledge Graph or LLM.
    """
    def __init__(self):
        self._rules = {
            "age": lambda x: 0 <= x <= 120,
            "temperature_celsius": lambda x: -273.15 <= x <= 1000,
            "stock_price": lambda x: x >= 0,
            "sort_ascending": lambda x: all(x[i] <= x[i+1] for i in range(len(x)-1))
        }

    def check_constraint(self, key: str, value: Any) -> bool:
        if key in self._rules:
            try:
                return self._rules[key](value)
            except Exception:
                return False
        return True # No constraint found, assume valid for this mock

class SemanticValidator:
    """
    Core class to validate code execution results against natural language intents.
    """

    def __init__(self, registry: Optional[SemanticRegistry] = None):
        self.registry = registry or SemanticRegistry()
        logger.info("SemanticValidator initialized.")

    def _extract_intent_keywords(self, description: str) -> Dict[str, Any]:
        """
        Helper function: Extracts keywords and expected constraints from NL description.
        """
        constraints = {}
        desc_lower = description.lower()
        
        if "age" in desc_lower or "years old" in desc_lower:
            constraints["type"] = "numeric"
            constraints["constraint_key"] = "age"
        
        if "sort" in desc_lower and "ascending" in desc_lower:
            constraints["constraint_key"] = "sort_ascending"
            
        if "price" in desc_lower:
            constraints["constraint_key"] = "stock_price"
            
        return constraints

    def verify_intent_alignment(
        self, 
        nl_description: str, 
        code_output: Any, 
        source_code: Optional[str] = None
    ) -> VerificationResult:
        """
        Verifies if the code output aligns with the natural language intent.
        
        Args:
            nl_description (str): The natural language description of the task.
            code_output (Any): The actual result returned by the code execution.
            source_code (Optional[str]): The code that generated the output (for context).
            
        Returns:
            VerificationResult: Object containing validity status and reasoning.
        """
        if not nl_description:
            return VerificationResult(False, 0.0, "Empty description", ["Input validation failed"])

        logger.info(f"Verifying intent: '{nl_description}' against output: {code_output}")
        
        intent_data = self._extract_intent_keywords(nl_description)
        anomalies = []
        
        # 1. Type Checking (Basic Semantic Layer)
        # If intent implies numeric data but output is string, that's a semantic clash
        if intent_data.get("type") == "numeric" and not isinstance(code_output, (int, float)):
            anomalies.append(f"Type mismatch: Expected numeric for '{nl_description}', got {type(code_output)}")

        # 2. Common-sense / Business Logic Constraints
        constraint_key = intent_data.get("constraint_key")
        if constraint_key:
            if not self.registry.check_constraint(constraint_key, code_output):
                anomalies.append(f"Constraint violation: Value {code_output} violates common-sense for '{constraint_key}'")

        # 3. Logical Consistency Checks (Mock logic for specific keywords)
        if "sum" in nl_description.lower() and isinstance(code_output, (list, tuple)):
             # If user asked for a sum but code returned a list
             anomalies.append("Logical mismatch: Intent requested aggregation (sum), but received collection")

        # Calculate Score
        score = 1.0
        if anomalies:
            score = max(0.0, 1.0 - (0.5 * len(anomalies)))
        
        is_valid = len(anomalies) == 0
        reason = "Verification Passed" if is_valid else "Semantic inconsistencies detected."
        
        if not is_valid:
            logger.warning(f"Semantic drift detected: {anomalies}")
            
        return VerificationResult(is_valid, score, reason, anomalies)

class CodeExecutorBridge:
    """
    Auxiliary class to simulate the execution of code in a controlled environment.
    """
    
    @staticmethod
    def safe_execute(code_string: str, context: Optional[Dict] = None) -> Any:
        """
        Executes code string safely and returns the result.
        WARNING: In production, use a sandboxed environment (e.g., Docker, RestrictedPython).
        """
        if not code_string:
            logger.error("Attempted to execute empty code string.")
            return None
            
        logger.debug(f"Executing code: {code_string[:50]}...")
        try:
            # Define a safe execution scope
            exec_scope = {"__builtins__": {'print': print}}
            if context:
                exec_scope.update(context)
                
            exec(code_string, exec_scope)
            
            # Convention: The code must define a variable called 'result'
            if 'result' in exec_scope:
                return exec_scope['result']
            else:
                raise ValueError("Code executed but did not define a 'result' variable.")
                
        except SyntaxError as e:
            logger.error(f"Syntax Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Runtime Error: {e}")
            raise

def run_verification_pipeline(description: str, code: str) -> VerificationResult:
    """
    Main pipeline function: Executes code and verifies semantic alignment.
    
    Usage Example:
        >>> code = "result = 150 + 50" # Intended to calculate age
        >>> desc = "Calculate the user's age based on birth year"
        >>> res = run_verification_pipeline(desc, code)
        >>> print(res.is_valid) # Should be False as 200 is > 120
    """
    validator = SemanticValidator()
    
    try:
        # Step 1: Execute the code
        output = CodeExecutorBridge.safe_execute(code)
        logger.info(f"Execution successful. Output: {output}")
        
        # Step 2: Verify Semantic Gap
        result = validator.verify_intent_alignment(description, output, code)
        return result
        
    except Exception as e:
        logger.critical(f"Pipeline failed: {e}")
        return VerificationResult(False, 0.0, "Execution Failed", [str(e)])

if __name__ == "__main__":
    # Example 1: Valid Logic
    desc1 = "Calculate the average temperature in Celsius"
    code1 = "result = 25.5" 
    print(f"Test 1: {run_verification_pipeline(desc1, code1)}")

    # Example 2: Semantic Violation (Age > 120)
    desc2 = "Get the user's age"
    code2 = "result = 500" 
    res2 = run_verification_pipeline(desc2, code2)
    print(f"Test 2 (Expect Fail): Valid={res2.is_valid}, Anomalies={res2.anomalies}")

    # Example 3: Type Mismatch
    desc3 = "Calculate total price"
    code3 = "result = 'error'" 
    res3 = run_verification_pipeline(desc3, code3)
    print(f"Test 3 (Expect Fail): Valid={res3.is_valid}, Reason={res3.reason}")