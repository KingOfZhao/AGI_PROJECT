"""
Module: auto_逻辑_执行一致性验证_针对已有节点中的_1f468a
Description: 
    This module implements a Logic-Execution Consistency Verification system.
    It is designed to validate whether AI-generated Python code (specifically 
    for algorithmic tasks) truly reflects the natural language logic explanation 
    provided alongside it.
    
    It utilizes Abstract Syntax Tree (AST) analysis to extract structural features 
    from the code (loops, conditionals, recursion) and compares them against 
    semantic parsing of the logic description. This serves as a rigorous test to 
    distinguish between "reasoned coding" and "probabilistic snippet stitching".

Author: AGI System Core
Version: 1.0.0
"""

import ast
import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConsistencyReport:
    """
    Data structure to hold the results of the consistency verification.
    """
    is_consistent: bool
    code_complexity_score: float
    logic_coverage_score: float
    missing_in_code: List[str] = field(default_factory=list)
    extra_in_code: List[str] = field(default_factory=list)
    details: str = ""

class LogicExecutionValidator:
    """
    A class to perform Logic-Execution Consistency Verification.
    
    Use Case:
        When an AGI system generates a skill (code + explanation), this tool 
        verifies if the code actually implements the explained logic steps.
        
    Example:
        >>> validator = LogicExecutionValidator()
        >>> code = "def fib(n):\\n    if n <= 1: return n\\n    return fib(n-1) + fib(n-2)"
        >>> desc = "Uses recursion with a base case."
        >>> report = validator.validate_consistency(code, desc)
        >>> print(report.is_consistent)
    """

    def __init__(self):
        self._ast_analyzer = ASTStructureAnalyzer()
        self._logic_parser = NaturalLogicParser()

    def validate_consistency(self, code_snippet: str, logic_description: str) -> ConsistencyReport:
        """
        Main entry point for verification. Compares code structure with logic text.
        
        Args:
            code_snippet (str): The Python source code to analyze.
            logic_description (str): The natural language description of the logic.
            
        Returns:
            ConsistencyReport: An object containing the verification results.
        """
        if not self._validate_input(code_snippet, logic_description):
            return ConsistencyReport(False, 0.0, 0.0, details="Invalid input data")

        try:
            # 1. Extract structural features from code (Reverse Engineering light)
            logger.info("Parsing AST for code structure...")
            code_structure = self._ast_analyzer.extract_features(code_snippet)
            
            # 2. Extract semantic features from text
            logger.info("Parsing natural language logic...")
            logic_features = self._logic_parser.extract_features(logic_description)

            # 3. Compare features
            report = self._compare_structures(code_structure, logic_features)
            
            logger.info(f"Verification complete. Consistent: {report.is_consistent}")
            return report

        except SyntaxError as e:
            logger.error(f"Code syntax error: {e}")
            return ConsistencyReport(False, 0.0, 0.0, details=f"Syntax Error in code: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during verification: {e}", exc_info=True)
            return ConsistencyReport(False, 0.0, 0.0, details=f"Internal error: {str(e)}")

    def _validate_input(self, code: str, desc: str) -> bool:
        """Validates that inputs are non-empty and within reasonable bounds."""
        if not code or not isinstance(code, str):
            logger.warning("Code snippet is empty or invalid.")
            return False
        if not desc or not isinstance(desc, str):
            logger.warning("Logic description is empty or invalid.")
            return False
        if len(code) > 100000: # Boundary check to prevent DoS on AST parsing
            logger.warning("Code snippet exceeds size limit.")
            return False
        return True

    def _compare_structures(self, code_struct: Dict, logic_struct: Dict) -> ConsistencyReport:
        """
        Core logic to map code features to logic features.
        Checks for presence of loops, conditionals, recursion, and data structures.
        """
        score = 0.0
        total_checks = 0
        missing = []
        
        # Define mappings between Logic Keywords and Code Features
        checks = [
            ("loops", ["for", "while", "iterate", "repeat", "traverse", "loop"]),
            ("conditionals", ["if", "else", "switch", "case", "condition", "check"]),
            ("recursion", ["recursive", "recursion", "call itself", "base case"]),
            ("data_structures", ["list", "array", "stack", "queue", "dictionary", "hash map"]),
            ("functions", ["function", "method", "def", "call", "invoke"])
        ]

        detected_code_features = set()
        
        # Normalize code structure keys
        for key, count in code_struct.items():
            if count > 0:
                detected_code_features.add(key)

        detected_logic_features = set()

        for feature_key, keywords in checks:
            total_checks += 1
            # Check if logic implies this feature
            logic_has_feature = any(kw in logic_struct.get("keywords", []) for kw in keywords)
            
            # Check if code has this feature
            code_has_feature = feature_key in detected_code_features
            
            if logic_has_feature:
                detected_logic_features.add(feature_key)
                if code_has_feature:
                    score += 1.0
                else:
                    missing.append(f"Logic mentions '{feature_key}', but code lacks it.")
            elif code_has_feature:
                # Code has feature not mentioned in logic (less critical, but noted)
                pass 

        # Calculate scores
        final_score = score / total_checks if total_checks > 0 else 0.0
        is_consistent = final_score >= 0.6 # Threshold for consistency

        return ConsistencyReport(
            is_consistent=is_consistent,
            code_complexity_score=sum(code_struct.values()) / 10.0, # Normalized
            logic_coverage_score=final_score,
            missing_in_code=missing,
            details="Alignment check completed."
        )

class ASTStructureAnalyzer:
    """
    Helper class to analyze Python code using AST (Abstract Syntax Tree).
    Performs 'Reverse Engineering' to identify control flow without executing code.
    """
    
    def extract_features(self, code: str) -> Dict[str, int]:
        """
        Parses code into AST and counts structural elements.
        
        Args:
            code (str): Python source code.
            
        Returns:
            Dict[str, int]: Counts of structural elements (loops, if, recursion, etc.).
        """
        tree = ast.parse(code)
        
        features = {
            "loops": 0,
            "conditionals": 0,
            "recursion": 0,
            "functions": 0,
            "data_structures": 0, # Heuristic based on list/dict literals
            "try_except": 0
        }
        
        # Custom Visitor to traverse AST
        class StructureVisitor(ast.NodeVisitor):
            def __init__(self, feats):
                self.feats = feats
                self.current_func_name = None

            def visit_For(self, node):
                self.feats["loops"] += 1
                self.generic_visit(node)

            def visit_While(self, node):
                self.feats["loops"] += 1
                self.generic_visit(node)
            
            def visit_If(self, node):
                self.feats["conditionals"] += 1
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                self.feats["functions"] += 1
                # Simple recursion detection heuristic
                # We check if the function calls itself inside its body
                self.current_func_name = node.name
                self.generic_visit(node)
                self.current_func_name = None

            def visit_Call(self, node):
                # Check for recursion
                if isinstance(node.func, ast.Name):
                    if node.func.id == self.current_func_name:
                        self.feats["recursion"] += 1
                
                # Check for data structure instantiation
                # (Very basic check for list(), dict(), etc.)
                if isinstance(node.func, ast.Name) and node.func.id in ('list', 'dict', 'set', 'tuple'):
                     self.feats["data_structures"] += 1
                self.generic_visit(node)

            def visit_List(self, node):
                self.feats["data_structures"] += 1
                self.generic_visit(node)
            
            def visit_Dict(self, node):
                self.feats["data_structures"] += 1
                self.generic_visit(node)

            def visit_Try(self, node):
                self.feats["try_except"] += 1
                self.generic_visit(node)

        visitor = StructureVisitor(features)
        visitor.visit(tree)
        
        logger.debug(f"Extracted AST features: {features}")
        return features

class NaturalLogicParser:
    """
    Helper class to extract semantic features from natural language descriptions.
    """
    
    def extract_features(self, text: str) -> Dict[str, List[str]]:
        """
        Extracts keywords and semantic markers from text.
        """
        # Basic preprocessing
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        return {
            "keywords": words,
            "length": len(words)
        }

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Example 1: Consistent Dynamic Programming (Fibonacci)
    consistent_code = """
def fibonacci(n):
    # Using dynamic programming
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
"""
    consistent_desc = """
This function calculates the nth Fibonacci number using dynamic programming.
It initializes a list (array) to store intermediate results.
It uses a loop to iterate from 2 to n, summing the previous two values.
It includes a base check for n <= 1.
"""

    # Example 2: Inconsistent Code (Logic says recursion, code uses loop)
    inconsistent_code = """
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""
    inconsistent_desc = """
This function calculates factorial using a recursive approach.
It calls itself with n-1 until the base case is reached.
"""

    validator = LogicExecutionValidator()

    print("--- Testing Consistent Example ---")
    report1 = validator.validate_consistency(consistent_code, consistent_desc)
    print(f"Result: {report1.is_consistent}")
    print(f"Coverage Score: {report1.logic_coverage_score:.2f}")
    print(f"Missing features: {report1.missing_in_code}")
    
    print("\n--- Testing Inconsistent Example ---")
    report2 = validator.validate_consistency(inconsistent_code, inconsistent_desc)
    print(f"Result: {report2.is_consistent}")
    print(f"Coverage Score: {report2.logic_coverage_score:.2f}")
    print(f"Missing features: {report2.missing_in_code}")