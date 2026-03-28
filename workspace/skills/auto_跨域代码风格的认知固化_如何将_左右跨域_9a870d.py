"""
Module: cross_domain_cognitive_solidification.py

This module implements an advanced AGI sub-system skill designed to convert 
implicit cross-domain programming style preferences (specifically applying 
Functional Programming concepts to UI development) into explicit, executable 
AST (Abstract Syntax Tree) constraints and Linter rules.

It addresses the challenge of "Cognitive Solidification" by translating 
high-level best practices into structural code checks, ensuring that 
generated code adheres to specific architectural patterns (e.g., pure 
components, immutability) regardless of the target syntax.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import ast
import logging
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union, Callable
from enum import Enum, auto

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossDomainCognitiveSolidifier")

# --- Data Structures ---

class ConstraintSeverity(Enum):
    """Defines the severity level of a constraint violation."""
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()

@dataclass
class ASTConstraint:
    """
    Represents a single structural constraint derived from a cognitive style preference.
    
    Attributes:
        rule_id: Unique identifier for the rule.
        description: Human-readable explanation of the rule.
        severity: The level of violation.
        node_type: The specific AST node type this constraint targets.
        validation_logic: A string representation of the logic (or lambda) to apply.
    """
    rule_id: str
    description: str
    severity: ConstraintSeverity
    node_type: ast.AST
    validation_logic: Callable[[ast.AST], bool] = field(repr=False)

@dataclass
class SolidificationResult:
    """
    Container for the results of the cognitive solidification process.
    
    Attributes:
        success: Whether the analysis/conversion was successful.
        constraints: List of generated AST constraints.
        linter_config: Dictionary configuration for an external linter engine.
        errors: List of error messages encountered.
    """
    success: bool
    constraints: List[ASTConstraint] = field(default_factory=list)
    linter_config: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

# --- Core Logic ---

class CrossDomainSolidifier:
    """
    Transforms implicit cross-domain style preferences into concrete AST constraints.
    
    This class specifically targets the intersection of Functional Programming (FP)
    and UI Development, identifying patterns that should be enforced (e.g., avoiding
    side effects in render methods, enforcing immutability).
    """

    def __init__(self, style_profile: Dict[str, Any]):
        """
        Initialize the solidifier with a user's style profile.
        
        Args:
            style_profile: A dictionary containing preferences like 
                           'immutability_level', 'pure_component_enforcement', etc.
        """
        self.style_profile = style_profile
        self._validate_profile()

    def _validate_profile(self) -> None:
        """Validates the input style profile to ensure required keys exist."""
        if 'domain_source' not in self.style_profile or 'domain_target' not in self.style_profile:
            error_msg = "Invalid profile: Must contain 'domain_source' and 'domain_target'."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info(f"Profile validated: Mapping from {self.style_profile['domain_source']} to {self.style_profile['domain_target']}")

    def _create_immutability_constraint(self) -> ASTConstraint:
        """
        Factory method: Creates a constraint enforcing immutability (no assignment to attributes).
        Context: FP concept applied to UI State objects.
        """
        def no_attr_assignment(node: ast.AST) -> bool:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        return False # Violation found
            return True

        return ASTConstraint(
            rule_id="FP-UI-001",
            description="Enforce immutability: Disallow direct attribute assignment in UI logic.",
            severity=ConstraintSeverity.ERROR,
            node_type=ast.Assign,
            validation_logic=no_attr_assignment
        )

    def _create_pure_function_constraint(self) -> ASTConstraint:
        """
        Factory method: Creates a constraint checking for side effects (no print/built-ins).
        Context: Pure Components in UI.
        """
        banned_calls = {'print', 'write', 'dump'}

        def no_side_effects(node: ast.AST) -> bool:
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in banned_calls:
                    return False
            return True

        return ASTConstraint(
            rule_id="FP-UI-002",
            description="Pure Component constraint: Disallow I/O side effects in render path.",
            severity=ConstraintSeverity.WARNING,
            node_type=ast.Call,
            validation_logic=no_side_effects
        )

    def generate_constraints(self) -> SolidificationResult:
        """
        Main execution method: Analyzes the style profile and generates a set of 
        executable constraints.
        
        Returns:
            SolidificationResult: The complete result set containing constraint objects.
        """
        logger.info("Starting cognitive solidification process...")
        result = SolidificationResult(success=True)
        
        try:
            preferences = self.style_profile.get("preferences", {})
            
            # Logic: If user prefers 'strict_immutability' from FP domain
            if preferences.get("strict_immutability", False):
                constraint = self._create_immutability_constraint()
                result.constraints.append(constraint)
                logger.debug(f"Generated constraint: {constraint.rule_id}")

            # Logic: If user prefers 'deterministic_ui' (Pure UI)
            if preferences.get("deterministic_rendering", False):
                constraint = self._create_pure_function_constraint()
                result.constraints.append(constraint)
                logger.debug(f"Generated constraint: {constraint.rule_id}")

            # Convert constraints to a linter configuration format (simulated)
            result.linter_config = self._export_to_linter_config(result.constraints)

        except Exception as e:
            logger.exception("Failed to generate constraints")
            result.success = False
            result.errors.append(str(e))
            
        return result

    def _export_to_linter_config(self, constraints: List[ASTConstraint]) -> Dict[str, Any]:
        """
        Helper: Serializes constraint objects into a generic linter configuration format.
        """
        config = {"rules": []}
        for c in constraints:
            config["rules"].append({
                "id": c.rule_id,
                "severity": c.severity.name,
                "description": c.description,
                "target_node": c.node_type.__name__
            })
        return config

# --- Execution Engine (Simulation) ---

def validate_code_against_constraints(
    code_snippet: str, 
    constraints: List[ASTConstraint]
) -> Dict[str, List[int]]:
    """
    Validates a snippet of Python code against generated AST constraints.
    
    This function parses the code into an AST and walks the tree, applying
    the validation logic of each constraint.
    
    Args:
        code_snippet: The source code string to validate.
        constraints: The list of ASTConstraint objects to apply.
        
    Returns:
        A dictionary mapping Rule IDs to lists of line numbers where violations occurred.
    """
    violations: Dict[str, List[int]] = {}
    try:
        tree = ast.parse(code_snippet)
    except SyntaxError as e:
        logger.error(f"Syntax error in input code: {e}")
        return {"SYNTAX_ERROR": [e.lineno if e.lineno else 0]}

    for node in ast.walk(tree):
        for constraint in constraints:
            # Check if the node type matches the constraint target
            if isinstance(node, constraint.node_type):
                # Execute the dynamic validation logic
                is_valid = constraint.validation_logic(node)
                if not is_valid:
                    if constraint.rule_id not in violations:
                        violations[constraint.rule_id] = []
                    violations[constraint.rule_id].append(node.lineno)
                    
    return violations

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define the User Intent / Style Profile (The "Cognitive" part)
    # User wants to apply Functional Programming strictness to UI components.
    user_profile = {
        "domain_source": "functional_programming",
        "domain_target": "ui_development",
        "preferences": {
            "strict_immutability": True,
            "deterministic_rendering": True
        }
    }

    # 2. Initialize Solidifier (The "Solidification" part)
    try:
        solidifier = CrossDomainSolidifier(user_profile)
        result = solidifier.generate_constraints()

        if result.success:
            print(f"Successfully generated {len(result.constraints)} constraints.")
            print("Linter Config JSON:")
            print(json.dumps(result.linter_config, indent=2))

            # 3. Test against code (The "Execution" part)
            # This code violates FP-UI-001 (attribute assignment) and FP-UI-002 (print call)
            bad_ui_code = """
class MyComponent:
    def render(self):
        self.data = "modified"  # Violation: Mutation
        print("Rendering...")   # Violation: Side effect
        return "UI"
            """

            print("\nValidating test code snippet...")
            found_violations = validate_code_against_constraints(bad_ui_code, result.constraints)
            
            if found_violations:
                print("Violations detected:")
                for rule_id, lines in found_violations.items():
                    print(f"- Rule {rule_id} violated at lines: {lines}")
            else:
                print("No violations found.")
                
    except ValueError as e:
        print(f"Initialization Error: {e}")