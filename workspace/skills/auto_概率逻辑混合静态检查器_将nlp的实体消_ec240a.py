"""
Module: auto_概率逻辑混合静态检查器_将nlp的实体消_ec240a
Description: A hybrid static checker that combines probabilistic logic with NLP entity resolution.
             It detects semantic-level bugs by analyzing variable naming conventions against usage
             patterns and verifying consistency between code logic and natural language comments.
             It also employs data-flow analysis techniques to track entity states across contexts.
Domain: cross_domain
Author: Senior Python Engineer
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticStaticChecker")


class SeverityLevel(Enum):
    """Enumeration for issue severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class SemanticIssue:
    """Data class representing a semantic issue found in the code."""
    line_no: int
    column_no: int
    severity: SeverityLevel
    message: str
    entity_name: str
    confidence_score: float  # 0.0 to 1.0
    suggested_fix: Optional[str] = None


class SemanticStaticAnalyzer(ast.NodeVisitor):
    """
    A hybrid static analyzer that uses NLP heuristics and AST analysis to find semantic bugs.
    """

    def __init__(self, source_code: str):
        """
        Initialize the analyzer with source code.
        
        Args:
            source_code (str): The Python source code to analyze.
        """
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.issues: List[SemanticIssue] = []
        self.entity_context: Dict[str, Dict[str, Any]] = {}  # Simulating register/memory management for entities
        self._current_scope = []

    def analyze(self) -> List[SemanticIssue]:
        """
        Main entry point to perform the analysis.
        
        Returns:
            List[SemanticIssue]: A list of detected semantic issues.
        """
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError as e:
            logger.error(f"Syntax error in source code: {e}")
            return [SemanticIssue(
                line_no=e.lineno or 0,
                column_no=e.offset or 0,
                severity=SeverityLevel.ERROR,
                message="Syntax error prevents analysis",
                entity_name="N/A",
                confidence_score=1.0
            )]
        
        logger.info(f"Analysis complete. Found {len(self.issues)} potential issues.")
        return self.issues

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to manage scope and check docstrings."""
        self._current_scope.append(node.name)
        # Check comment/docstring logic consistency
        self._check_comment_logic_consistency(node)
        self.generic_visit(node)
        self._current_scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment nodes to track entity types."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                entity_name = target.id
                inferred_type = self._infer_type_from_value(node.value)
                
                # Register entity (Data Flow Analysis simulation)
                self.entity_context[entity_name] = {
                    "type": inferred_type,
                    "line": node.lineno,
                    "usage_count": 0
                }
                
                # Core Function 1: Check Naming Convention vs Usage
                self._check_variable_naming_convention(entity_name, inferred_type, node)
        
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript operations (e.g., var['key'] or var[0])."""
        if isinstance(node.value, ast.Name):
            entity_name = node.value.id
            if entity_name in self.entity_context:
                self.entity_context[entity_name]["usage_count"] += 1
                
                # Detect access type: String key (Dict-like) vs Index (List-like)
                access_type = "dict_access" if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str) else "list_access"
                
                # Check for semantic mismatch
                stored_type_hint = self.entity_context[entity_name].get("type_hint_nlp", "")
                if stored_type_hint:
                    self._validate_access_pattern(entity_name, stored_type_hint, access_type, node)
        
        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # Core Functions
    # -------------------------------------------------------------------------

    def _check_variable_naming_convention(self, name: str, inferred_type: str, node: ast.Assign) -> None:
        """
        Core Function 1: Checks if variable names imply a structure that contradicts the assigned value.
        Uses simple NLP heuristics (regex) on the variable name.
        """
        name_lower = name.lower()
        
        # NLP Heuristics: Detect keywords in variable names
        is_list_name = bool(re.search(r'(list|arr|seq|items|rows)', name_lower))
        is_dict_name = bool(re.search(r'(dict|map|hash|keyval|lookup)', name_lower))
        
        issue = None
        confidence = 0.8

        if is_list_name and inferred_type == "dict":
            issue = SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.WARNING,
                message=f"Variable name '{name}' suggests a List, but assigned a Dictionary.",
                entity_name=name,
                confidence_score=confidence,
                suggested_fix=f"Rename to '{name.replace('list', 'dict')}' or change assignment type."
            )
        elif is_dict_name and inferred_type == "list":
            issue = SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.WARNING,
                message=f"Variable name '{name}' suggests a Dictionary, but assigned a List.",
                entity_name=name,
                confidence_score=confidence,
                suggested_fix=f"Rename to '{name.replace('dict', 'list')}' or change assignment type."
            )

        if issue:
            self.issues.append(issue)
            # Store the NLP hint for later access validation
            if name in self.entity_context:
                self.entity_context[name]["type_hint_nlp"] = "list" if is_list_name else "dict"

    def _check_comment_logic_consistency(self, node: ast.FunctionDef) -> None:
        """
        Core Function 2: Verifies consistency between natural language comments/docstrings and code logic.
        """
        docstring = ast.get_docstring(node)
        if not docstring:
            return

        docstring_lower = docstring.lower()
        
        # Simple NLP extraction of intent
        intent_sum = "sum" in docstring_lower or "total" in docstring_lower or "add" in docstring_lower
        intent_max = "max" in docstring_lower or "highest" in docstring_lower or "largest" in docstring_lower
        
        # Analyze function body for return logic
        logic_sum_found = False
        logic_max_found = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == "sum":
                        logic_sum_found = True
                    elif child.func.id == "max":
                        logic_max_found = True

        # Contradiction Detection
        if intent_sum and logic_max_found and not logic_sum_found:
            self.issues.append(SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.ERROR,
                message="Docstring describes a summation operation, but code logic uses max().",
                entity_name=node.name,
                confidence_score=0.9,
                suggested_fix="Update docstring or logic."
            ))
        elif intent_max and logic_sum_found and not logic_max_found:
            self.issues.append(SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.ERROR,
                message="Docstring describes finding a maximum, but code logic uses sum().",
                entity_name=node.name,
                confidence_score=0.9,
                suggested_fix="Update docstring or logic."
            ))

    # -------------------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------------------

    def _infer_type_from_value(self, node: ast.AST) -> str:
        """
        Helper Function: Infers basic type from AST node.
        """
        if isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id # e.g., dict(), list()
        return "unknown"

    def _validate_access_pattern(self, name: str, name_hint: str, access_type: str, node: ast.Subscript) -> None:
        """
        Validates if the access pattern matches the semantic hint from the variable name.
        This acts as the 'Entity Resolution' part, tracking if an entity 'list' is treated as a 'dict'.
        """
        if name_hint == "list" and access_type == "dict_access":
            self.issues.append(SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.WARNING,
                message=f"Entity '{name}' (named as list) is being accessed with a string key (dictionary behavior).",
                entity_name=name,
                confidence_score=0.75
            ))
        elif name_hint == "dict" and access_type == "list_access":
            self.issues.append(SemanticIssue(
                line_no=node.lineno,
                column_no=node.col_offset,
                severity=SeverityLevel.WARNING,
                message=f"Entity '{name}' (named as dict) is being accessed with an integer index (list behavior).",
                entity_name=name,
                confidence_score=0.75
            ))


# -------------------------------------------------------------------------
# Usage Example
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Input Data Format: Python source code string
    sample_code = """
def calculate_metrics(data_list):
    \"\"\"This function calculates the sum of the data.\"\"\"
    # Variable naming implies list, but assigned dict
    user_map = {"id": 1, "val": 10} 
    
    # Logic contradiction: Docstring says sum, code uses max
    return max(data_list)

# Entity Resolution: 'list' in name, used as dict
my_list = {"a": 1, "b": 2}
print(my_list["a"])
"""

    print(f"--- Analyzing Code ---\n{sample_code}\n--- Results ---")
    
    analyzer = SemanticStaticAnalyzer(sample_code)
    issues = analyzer.analyze()

    for issue in issues:
        print(f"[{issue.severity.value}] Line {issue.line_no}: {issue.message} "
              f"(Confidence: {issue.confidence_score:.2f})")
        if issue.suggested_fix:
            print(f"   Suggestion: {issue.suggested_fix}")