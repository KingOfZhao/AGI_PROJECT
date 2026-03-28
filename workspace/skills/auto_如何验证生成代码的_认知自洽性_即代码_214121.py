"""
Module: auto_如何验证生成代码的_认知自洽性_即代码_214121
Description: Advanced logic verification module for AGI systems to validate 
             'Cognitive Self-Consistency' in generated code execution results.
             
This module provides tools to detect logical paradoxes and verify closed-loop 
consistency in specific domains (e.g., financial balance, inventory management).

Author: Senior Python Engineer (AGI Division)
Version: 1.0.0
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cognitive_consistency.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConsistencyStatus(Enum):
    """Enumeration for consistency check results."""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    PARADOX_DETECTED = "paradox_detected"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ValidationResult:
    """Data class for validation results."""
    status: ConsistencyStatus
    score: float = 0.0
    message: str = ""
    details: Dict[str, Union[float, str, bool]] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "score": self.score,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class DomainContext:
    """Data class for domain-specific context."""
    domain_name: str
    expected_constraints: Dict[str, Tuple[float, float]]  # {param: (min, max)}
    balance_rules: Dict[str, str]  # e.g., {"income": "expenses + profit"}
    tolerance: float = 1e-6


class CognitiveConsistencyValidator:
    """
    Main class for validating cognitive self-consistency in generated code.
    
    This validator checks whether execution results form a logical closed-loop
    without contradictions or paradoxes in the specified domain.
    
    Attributes:
        domain_context (DomainContext): The context of the domain being validated.
        validation_history (List[ValidationResult]): History of validations performed.
        
    Example:
        >>> context = DomainContext(
        ...     domain_name="street_vendor_finance",
        ...     expected_constraints={"profit": (-1000, 10000)},
        ...     balance_rules={"revenue": "costs + profit"},
        ...     tolerance=0.01
        ... )
        >>> validator = CognitiveConsistencyValidator(context)
        >>> data = {"revenue": 100.0, "costs": 60.0, "profit": 40.0}
        >>> result = validator.validate_consistency(data)
        >>> print(result.status)
        ConsistencyStatus.CONSISTENT
    """
    
    def __init__(self, domain_context: DomainContext):
        """
        Initialize the validator with domain context.
        
        Args:
            domain_context: Context containing domain-specific rules and constraints.
        
        Raises:
            ValueError: If domain_context is invalid.
        """
        if not isinstance(domain_context, DomainContext):
            raise ValueError("domain_context must be an instance of DomainContext")
        
        self.domain_context = domain_context
        self.validation_history: List[ValidationResult] = []
        logger.info(f"Initialized CognitiveConsistencyValidator for domain: {domain_context.domain_name}")
    
    def _validate_input_data(self, data: Dict[str, Union[int, float]]) -> Tuple[bool, Optional[str]]:
        """
        Validate input data structure and types.
        
        Args:
            data: Dictionary containing numerical data to validate.
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Input data must be a dictionary"
        
        if not data:
            return False, "Input data cannot be empty"
        
        for key, value in data.items():
            if not isinstance(key, str):
                return False, f"Key '{key}' must be a string"
            if not isinstance(value, (int, float)):
                return False, f"Value for '{key}' must be numeric, got {type(value).__name__}"
        
        return True, None
    
    def _check_boundary_constraints(self, data: Dict[str, Union[int, float]]) -> Tuple[bool, List[str]]:
        """
        Check if values fall within expected boundary constraints.
        
        Args:
            data: Dictionary containing numerical data.
            
        Returns:
            Tuple of (all_within_bounds, list_of_violations)
        """
        violations = []
        all_within_bounds = True
        
        for param, (min_val, max_val) in self.domain_context.expected_constraints.items():
            if param in data:
                value = data[param]
                if not (min_val <= value <= max_val):
                    violations.append(
                        f"Parameter '{param}' value {value} outside bounds [{min_val}, {max_val}]"
                    )
                    all_within_bounds = False
                    logger.warning(f"Boundary violation: {param}={value}")
        
        return all_within_bounds, violations
    
    def _evaluate_balance_equation(self, equation: str, data: Dict[str, Union[int, float]]) -> Tuple[float, float]:
        """
        Evaluate a balance equation and return left and right side values.
        
        Args:
            equation: String equation in format "left = right".
            data: Dictionary containing variable values.
            
        Returns:
            Tuple of (left_value, right_value)
            
        Raises:
            ValueError: If equation format is invalid or variables missing.
        """
        if '=' not in equation:
            raise ValueError(f"Invalid equation format: {equation}")
        
        left_expr, right_expr = equation.split('=', 1)
        left_expr = left_expr.strip()
        right_expr = right_expr.strip()
        
        def safe_eval(expr: str, variables: Dict[str, Union[int, float]]) -> float:
            """Safely evaluate a mathematical expression."""
            allowed_chars = set('0123456789+-*/.() ')
            expr_chars = set(expr)
            
            # Check for invalid characters
            invalid_chars = expr_chars - allowed_chars - set(variables.keys())
            if invalid_chars:
                raise ValueError(f"Invalid characters in expression: {invalid_chars}")
            
            # Replace variable names with their values
            for var, val in variables.items():
                expr = expr.replace(var, str(float(val)))
            
            try:
                return eval(expr, {"__builtins__": None}, {})
            except Exception as e:
                logger.error(f"Expression evaluation failed: {expr}, Error: {e}")
                raise ValueError(f"Expression evaluation failed: {e}")
        
        left_value = safe_eval(left_expr, data)
        right_value = safe_eval(right_expr, data)
        
        return left_value, right_value
    
    def validate_consistency(
        self, 
        data: Dict[str, Union[int, float]],
        custom_rules: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Validate the cognitive self-consistency of execution results.
        
        This method performs comprehensive validation including:
        1. Input data validation
        2. Boundary constraint checking
        3. Balance equation verification
        4. Paradox detection
        
        Args:
            data: Dictionary containing execution results to validate.
            custom_rules: Optional custom balance rules to override domain defaults.
            
        Returns:
            ValidationResult object containing validation status and details.
            
        Example:
            >>> result = validator.validate_consistency(
            ...     {"revenue": 100, "costs": 60, "profit": 40}
            ... )
        """
        logger.info(f"Starting consistency validation for domain: {self.domain_context.domain_name}")
        
        # Step 1: Validate input data
        is_valid, error_msg = self._validate_input_data(data)
        if not is_valid:
            logger.error(f"Input validation failed: {error_msg}")
            result = ValidationResult(
                status=ConsistencyStatus.INSUFFICIENT_DATA,
                message=error_msg,
                details={"error_type": "input_validation"}
            )
            self.validation_history.append(result)
            return result
        
        # Step 2: Check boundary constraints
        within_bounds, violations = self._check_boundary_constraints(data)
        
        # Step 3: Validate balance equations
        balance_errors = []
        rules = custom_rules or self.domain_context.balance_rules
        
        for rule_name, equation in rules.items():
            try:
                left_val, right_val = self._evaluate_balance_equation(equation, data)
                difference = abs(left_val - right_val)
                
                if difference > self.domain_context.tolerance:
                    balance_errors.append({
                        "rule": rule_name,
                        "equation": equation,
                        "left_value": left_val,
                        "right_value": right_val,
                        "difference": difference
                    })
                    logger.warning(
                        f"Balance error in '{rule_name}': {left_val} != {right_val} "
                        f"(diff: {difference})"
                    )
            except ValueError as e:
                logger.error(f"Failed to evaluate rule '{rule_name}': {e}")
                balance_errors.append({
                    "rule": rule_name,
                    "error": str(e)
                })
        
        # Step 4: Determine overall consistency status
        if balance_errors:
            status = ConsistencyStatus.PARADOX_DETECTED
            score = 0.0
            message = "Logical paradox detected: balance equations not satisfied"
        elif violations:
            status = ConsistencyStatus.INCONSISTENT
            score = 0.5
            message = "Boundary constraints violated but no logical paradox"
        else:
            status = ConsistencyStatus.CONSISTENT
            score = 1.0
            message = "All consistency checks passed"
        
        result = ValidationResult(
            status=status,
            score=score,
            message=message,
            details={
                "boundary_violations": violations,
                "balance_errors": balance_errors,
                "rules_checked": list(rules.keys()),
                "data_keys": list(data.keys())
            }
        )
        
        self.validation_history.append(result)
        logger.info(f"Validation complete: {status.value} (score: {score})")
        
        return result
    
    def detect_circular_paradox(
        self, 
        data: Dict[str, Union[int, float]], 
        dependencies: Dict[str, List[str]]
    ) -> ValidationResult:
        """
        Detect circular dependencies that might cause logical paradoxes.
        
        Args:
            data: Dictionary containing execution results.
            dependencies: Dictionary mapping each variable to its dependencies.
                         e.g., {"A": ["B", "C"]} means A depends on B and C.
        
        Returns:
            ValidationResult indicating if circular paradox exists.
            
        Example:
            >>> deps = {"profit": ["revenue", "costs"], "revenue": ["profit"]}
            >>> result = validator.detect_circular_paradox(data, deps)
        """
        logger.info("Starting circular paradox detection")
        
        def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
            """Helper function to detect cycles using DFS."""
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited: set = set()
        rec_stack: set = set()
        cycle_detected = False
        
        for node in dependencies:
            if node not in visited:
                if has_cycle(node, visited, rec_stack):
                    cycle_detected = True
                    break
        
        if cycle_detected:
            status = ConsistencyStatus.PARADOX_DETECTED
            message = "Circular dependency paradox detected"
            score = 0.0
        else:
            status = ConsistencyStatus.CONSISTENT
            message = "No circular dependencies detected"
            score = 1.0
        
        result = ValidationResult(
            status=status,
            score=score,
            message=message,
            details={
                "dependencies": dependencies,
                "cycle_detected": cycle_detected
            }
        )
        
        self.validation_history.append(result)
        return result
    
    def get_validation_summary(self) -> Dict[str, Union[int, float, List[Dict]]]:
        """
        Generate a summary of all validations performed.
        
        Returns:
            Dictionary containing validation statistics and history.
        """
        if not self.validation_history:
            return {"total_validations": 0}
        
        status_counts = {}
        total_score = 0.0
        
        for result in self.validation_history:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_score += result.score
        
        avg_score = total_score / len(self.validation_history)
        
        return {
            "domain": self.domain_context.domain_name,
            "total_validations": len(self.validation_history),
            "status_distribution": status_counts,
            "average_score": round(avg_score, 4),
            "history": [r.to_dict() for r in self.validation_history[-10:]]  # Last 10 results
        }


# Standalone helper functions
def create_financial_validator() -> CognitiveConsistencyValidator:
    """
    Factory function to create a validator for financial domains.
    
    Returns:
        Configured CognitiveConsistencyValidator for financial data.
        
    Example:
        >>> validator = create_financial_validator()
        >>> data = {"revenue": 1000, "expenses": 600, "profit": 400}
        >>> result = validator.validate_consistency(data)
    """
    context = DomainContext(
        domain_name="finance",
        expected_constraints={
            "profit": (-1000000, 10000000),
            "revenue": (0, 100000000),
            "expenses": (0, 100000000)
        },
        balance_rules={
            "profit_equation": "revenue - expenses = profit",
            "margin_check": "profit / revenue = margin"
        },
        tolerance=0.01
    )
    return CognitiveConsistencyValidator(context)


def batch_validate(
    validator: CognitiveConsistencyValidator,
    data_list: List[Dict[str, Union[int, float]]]
) -> List[ValidationResult]:
    """
    Perform batch validation on multiple datasets.
    
    Args:
        validator: CognitiveConsistencyValidator instance.
        data_list: List of data dictionaries to validate.
        
    Returns:
        List of ValidationResult objects.
        
    Raises:
        ValueError: If input parameters are invalid.
    """
    if not isinstance(validator, CognitiveConsistencyValidator):
        raise ValueError("validator must be an instance of CognitiveConsistencyValidator")
    
    if not isinstance(data_list, list):
        raise ValueError("data_list must be a list")
    
    results = []
    for i, data in enumerate(data_list):
        try:
            logger.info(f"Batch validation {i+1}/{len(data_list)}")
            result = validator.validate_consistency(data)
            results.append(result)
        except Exception as e:
            logger.error(f"Batch validation failed for item {i}: {e}")
            results.append(ValidationResult(
                status=ConsistencyStatus.INSUFFICIENT_DATA,
                message=f"Validation failed: {str(e)}"
            ))
    
    return results


if __name__ == "__main__":
    # Example usage demonstration
    print("=" * 60)
    print("Cognitive Self-Consistency Validator Demonstration")
    print("=" * 60)
    
    # Create domain context for street vendor finance
    vendor_context = DomainContext(
        domain_name="street_vendor",
        expected_constraints={
            "daily_revenue": (0, 5000),
            "daily_costs": (0, 3000),
            "daily_profit": (-500, 4000)
        },
        balance_rules={
            "profit_check": "daily_revenue - daily_costs = daily_profit"
        },
        tolerance=0.01
    )
    
    # Initialize validator
    validator = CognitiveConsistencyValidator(vendor_context)
    
    # Test case 1: Consistent data
    print("\nTest Case 1: Consistent Data")
    consistent_data = {
        "daily_revenue": 500.0,
        "daily_costs": 300.0,
        "daily_profit": 200.0
    }
    result1 = validator.validate_consistency(consistent_data)
    print(f"Status: {result1.status.value}")
    print(f"Score: {result1.score}")
    print(f"Message: {result1.message}")
    
    # Test case 2: Inconsistent data (paradox)
    print("\nTest Case 2: Paradox Detection")
    paradox_data = {
        "daily_revenue": 500.0,
        "daily_costs": 300.0,
        "daily_profit": 250.0  # Should be 200, but is 250
    }
    result2 = validator.validate_consistency(paradox_data)
    print(f"Status: {result2.status.value}")
    print(f"Score: {result2.score}")
    print(f"Message: {result2.message}")
    print(f"Details: {json.dumps(result2.details['balance_errors'], indent=2)}")
    
    # Test case 3: Circular dependency detection
    print("\nTest Case 3: Circular Paradox Detection")
    dependencies = {
        "profit": ["revenue", "costs"],
        "revenue": ["sales", "returns"],
        "costs": ["materials", "labor"],
        "materials": ["profit"]  # Circular: materials depends on profit
    }
    result3 = validator.detect_circular_paradox({}, dependencies)
    print(f"Status: {result3.status.value}")
    print(f"Message: {result3.message}")
    
    # Print validation summary
    print("\nValidation Summary:")
    summary = validator.get_validation_summary()
    print(json.dumps(summary, indent=2, default=str))