"""
Module: auto_long_chain_integrity_validator
A robust validation system for testing AI's ability to maintain logical consistency
across multi-step business process generation tasks.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProcessStep(Enum):
    """Enumeration of all steps in the business process."""
    MARKET_RESEARCH = auto()
    LEGAL_COMPLIANCE = auto()
    SUPPLIER_SELECTION = auto()
    STOREFRONT_SETUP = auto()
    PAYMENT_INTEGRATION = auto()
    LOGISTICS_PLANNING = auto()
    MARKETING_STRATEGY = auto()
    CUSTOMER_SERVICE = auto()
    ANALYTICS_SETUP = auto()
    LAUNCH_PREPARATION = auto()

@dataclass
class ValidationResult:
    """Data structure for validation results."""
    step: ProcessStep
    is_valid: bool
    input_reference: bool
    logical_consistency: float
    error_messages: List[str]
    timestamp: str = datetime.now().isoformat()

class LongChainValidator:
    """
    Validates the integrity of multi-step business process generation.
    
    This class implements a comprehensive validation framework to ensure AI-generated
    business processes maintain logical consistency across all steps, with proper
    input-output references between consecutive steps.
    
    Attributes:
        min_consistency_score (float): Minimum acceptable consistency score (0-1)
        required_steps (int): Number of steps required in the process
        validation_results (List[ValidationResult]): Stores validation outcomes
    
    Example:
        >>> validator = LongChainValidator()
        >>> process_data = {
        ...     "steps": [
        ...         {"step": "MARKET_RESEARCH", "content": "...", "output": "..."},
        ...         {"step": "LEGAL_COMPLIANCE", "content": "...", "input": "..."},
        ...         # ... more steps
        ...     ]
        ... }
        >>> results = validator.validate_process(process_data)
    """
    
    def __init__(self, min_consistency_score: float = 0.8, required_steps: int = 10):
        """
        Initialize the validator with configuration parameters.
        
        Args:
            min_consistency_score: Minimum acceptable consistency score (default: 0.8)
            required_steps: Number of required steps in the process (default: 10)
            
        Raises:
            ValueError: If invalid parameters are provided
        """
        if not 0 <= min_consistency_score <= 1:
            raise ValueError("Consistency score must be between 0 and 1")
        if required_steps < 2:
            raise ValueError("Process must have at least 2 steps")
            
        self.min_consistency_score = min_consistency_score
        self.required_steps = required_steps
        self.validation_results: List[ValidationResult] = []
        logger.info("Initialized LongChainValidator with min_score=%.2f, steps=%d",
                    min_consistency_score, required_steps)

    def validate_process(self, process_data: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate an entire multi-step business process.
        
        This method performs comprehensive validation including:
        - Step count verification
        - Input-output reference checking
        - Logical consistency analysis
        - Cross-step dependency validation
        
        Args:
            process_data: Dictionary containing the process steps and metadata
                         Expected format: {
                             "steps": [
                                 {
                                     "step": str,
                                     "content": str,
                                     "input": Optional[str],
                                     "output": str
                                 },
                                 ...
                             ]
                         }
        
        Returns:
            Tuple containing:
            - Overall validation status (bool)
            - List of detailed validation results for each step
            
        Raises:
            KeyError: If required fields are missing in process_data
            ValueError: If process structure is invalid
        """
        if not process_data or "steps" not in process_data:
            raise ValueError("Invalid process data structure")
            
        steps = process_data["steps"]
        if len(steps) != self.required_steps:
            error_msg = f"Expected {self.required_steps} steps, got {len(steps)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.validation_results = []
        overall_valid = True
        previous_output = None
        
        for i, step_data in enumerate(steps):
            try:
                step_name = step_data["step"].upper()
                step_enum = ProcessStep[step_name]
                
                # Skip input validation for first step
                input_valid = True
                if i > 0:
                    input_valid = self._validate_input_reference(
                        step_data.get("input"),
                        previous_output,
                        step_name
                    )
                
                consistency_score = self._calculate_consistency_score(
                    step_data.get("content", ""),
                    step_data.get("output", "")
                )
                
                step_valid = (
                    input_valid and 
                    consistency_score >= self.min_consistency_score
                )
                
                result = ValidationResult(
                    step=step_enum,
                    is_valid=step_valid,
                    input_reference=input_valid,
                    logical_consistency=consistency_score,
                    error_messages=[] if step_valid else self._get_error_messages(
                        input_valid, consistency_score
                    )
                )
                
                self.validation_results.append(result)
                if not step_valid:
                    overall_valid = False
                    
                previous_output = step_data.get("output")
                
            except KeyError as e:
                logger.error("Missing required field in step %d: %s", i, str(e))
                raise
            except Exception as e:
                logger.exception("Unexpected error validating step %d", i)
                raise
                
        logger.info("Process validation completed. Overall status: %s", overall_valid)
        return overall_valid, self.validation_results

    def _validate_input_reference(
        self,
        current_input: Optional[str],
        previous_output: Optional[str],
        step_name: str
    ) -> bool:
        """
        Validate that current step's input references previous step's output.
        
        Args:
            current_input: Input field from current step
            previous_output: Output field from previous step
            step_name: Name of current step for logging
            
        Returns:
            bool: True if reference is valid, False otherwise
        """
        if not current_input or not previous_output:
            logger.warning("Missing input/output reference in step %s", step_name)
            return False
            
        # Simple reference check - can be enhanced with more sophisticated NLP
        reference_valid = (
            current_input.strip() == previous_output.strip() or
            previous_output.strip() in current_input
        )
        
        if not reference_valid:
            logger.warning(
                "Input reference mismatch in step %s. Expected to reference previous output.",
                step_name
            )
            
        return reference_valid

    def _calculate_consistency_score(self, content: str, output: str) -> float:
        """
        Calculate logical consistency score between content and output.
        
        This is a simplified implementation - in production this would use
        more sophisticated NLP techniques to evaluate semantic consistency.
        
        Args:
            content: The main content of the step
            output: The declared output of the step
            
        Returns:
            float: Consistency score between 0 and 1
        """
        if not content or not output:
            return 0.0
            
        # Basic keyword overlap check
        content_words = set(re.findall(r'\w+', content.lower()))
        output_words = set(re.findall(r'\w+', output.lower()))
        
        if not content_words or not output_words:
            return 0.0
            
        overlap = len(content_words & output_words)
        max_words = max(len(content_words), len(output_words))
        
        # Weighted score favoring output word coverage
        score = (overlap / max_words) * 0.7
        score += min(len(output_words)/20, 0.3)  # Bonus for comprehensive output
        
        return min(score, 1.0)

    def _get_error_messages(
        self,
        input_valid: bool,
        consistency_score: float
    ) -> List[str]:
        """
        Generate appropriate error messages based on validation failures.
        
        Args:
            input_valid: Whether input reference was valid
            consistency_score: The calculated consistency score
            
        Returns:
            List of error messages describing validation failures
        """
        messages = []
        if not input_valid:
            messages.append("Input does not properly reference previous step's output")
        if consistency_score < self.min_consistency_score:
            messages.append(
                f"Logical consistency score ({consistency_score:.2f}) "
                f"below minimum threshold ({self.min_consistency_score:.2f})"
            )
        return messages

    def generate_validation_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report.
        
        Returns:
            Dictionary containing:
            - overall_status: bool
            - total_steps: int
            - passed_steps: int
            - failed_steps: int
            - average_consistency: float
            - step_results: List of detailed results
        """
        if not self.validation_results:
            return {"status": "No validation results available"}
            
        passed = sum(1 for r in self.validation_results if r.is_valid)
        avg_consistency = (
            sum(r.logical_consistency for r in self.validation_results) / 
            len(self.validation_results)
        )
        
        return {
            "overall_status": all(r.is_valid for r in self.validation_results),
            "total_steps": len(self.validation_results),
            "passed_steps": passed,
            "failed_steps": len(self.validation_results) - passed,
            "average_consistency": avg_consistency,
            "step_results": [
                {
                    "step": r.step.name,
                    "is_valid": r.is_valid,
                    "input_reference": r.input_reference,
                    "consistency_score": r.logical_consistency,
                    "errors": r.error_messages,
                    "timestamp": r.timestamp
                }
                for r in self.validation_results
            ]
        }

# Example usage
if __name__ == "__main__":
    # Example process data (in a real scenario this would come from AI generation)
    example_process = {
        "steps": [
            {
                "step": "MARKET_RESEARCH",
                "content": "Conducted analysis of target markets for e-commerce...",
                "input": None,
                "output": "Target markets: US, EU, Japan"
            },
            {
                "step": "LEGAL_COMPLIANCE",
                "content": "Based on the target markets (US, EU, Japan), identified regulations...",
                "input": "Target markets: US, EU, Japan",
                "output": "Required certifications: GDPR, CCPA, JIS"
            },
            # ... (continue for all 10 steps)
        ]
    }
    
    # Initialize validator
    validator = LongChainValidator(min_consistency_score=0.75)
    
    try:
        # Validate process
        is_valid, results = validator.validate_process(example_process)
        
        # Generate and print report
        report = validator.generate_validation_report()
        print(json.dumps(report, indent=2))
        
    except Exception as e:
        logger.error("Validation failed: %s", str(e))