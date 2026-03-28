"""
Module: auto_failure_consolidation.py

Description:
    This module implements the 'Failure Consolidation' skill for an AGI system.
    Its purpose is to analyze instances where AI-generated code fails (validated
    by human practice/execution), extract the underlying error pattern, and
    crystallize this into a persistent heuristic rule (a 'True Node').

    This process creates a feedback loop: Execution -> Error Analysis ->
    Pattern Extraction -> Rule Generation -> Future Avoidance.

    Domain: Cognitive Science / Machine Learning Engineering
"""

import logging
import re
import hashlib
from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime
from dataclasses import dataclass, field

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Failure_Consolidation")

class ErrorTrace(TypedDict):
    """Represents the input data structure for a failure event."""
    code_snippet: str
    error_type: str  # e.g., "UnicodeDecodeError"
    error_message: str  # Full stack trace or message
    context: Dict[str, Any]  # e.g., {"file_type": "csv", "library": "pandas"}
    user_feedback: Optional[str]

@dataclass
class HeuristicRule:
    """Represents a crystallized rule derived from past failures."""
    rule_id: str
    pattern_signature: str
    description: str
    mitigation_strategy: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 1.0  # Initial confidence

class FailureConsolidator:
    """
    Core class responsible for processing failures and generating heuristic rules.
    """

    def __init__(self):
        self.rule_database: Dict[str, HeuristicRule] = {}
        logger.info("FailureConsolidator initialized.")

    def _validate_input(self, error_data: ErrorTrace) -> bool:
        """
        Validate the input data structure.
        
        Args:
            error_data (ErrorTrace): The dictionary containing error details.
            
        Returns:
            bool: True if valid, raises ValueError otherwise.
        """
        if not isinstance(error_data, dict):
            raise TypeError("Input must be a dictionary (ErrorTrace).")
        
        required_keys = {"code_snippet", "error_type", "error_message", "context"}
        if not required_keys.issubset(error_data.keys()):
            missing = required_keys - set(error_data.keys())
            raise ValueError(f"Missing required keys in error data: {missing}")
            
        if not error_data['error_type']:
            logger.warning("Received empty error type, processing may be ambiguous.")
            
        return True

    def _extract_pattern_signature(self, error_data: ErrorTrace) -> str:
        """
        [Auxiliary Function] Generates a unique signature for the error context.
        
        Combines error type, specific error message patterns, and relevant context keys
        to create a unique identifier for this class of failure.
        
        Args:
            error_data (ErrorTrace): The error data.
            
        Returns:
            str: A unique hash signature representing the failure pattern.
        """
        # Normalize message: remove specific variable names or paths to generalize
        # e.g., "FileNotFoundError: 'data.csv'" -> "FileNotFoundError: FILE_PATH"
        normalized_msg = re.sub(r"'[^']*'", "'GENERIC_PATH'", error_data['error_message'])
        
        # Combine with context markers
        context_markers = "&".join(f"{k}={v}" for k, v in error_data['context'].items())
        
        signature_raw = f"{error_data['error_type']}::{normalized_msg}::{context_markers}"
        signature_hash = hashlib.md5(signature_raw.encode('utf-8')).hexdigest()
        
        logger.debug(f"Generated signature {signature_hash} for pattern.")
        return signature_hash

    def analyze_and_consolidate(self, error_data: ErrorTrace) -> Optional[HeuristicRule]:
        """
        [Core Function 1] Analyzes a failure event and creates a new rule.
        
        This function takes raw failure data, extracts the semantic pattern,
        checks if it already exists, and if not, creates a new HeuristicRule.
        
        Args:
            error_data (ErrorTrace): Validated error data.
            
        Returns:
            Optional[HeuristicRule]: The newly created rule, or None if consolidation failed.
        """
        try:
            self._validate_input(error_data)
        except (TypeError, ValueError) as e:
            logger.error(f"Input validation failed: {e}")
            return None

        signature = self._extract_pattern_signature(error_data)

        # Check if rule already exists
        if signature in self.rule_database:
            logger.info(f"Pattern {signature} already known. Reinforcing existing rule.")
            # In a real AGI system, we might update frequency or confidence here
            return self.rule_database[signature]

        # Semantic Analysis (Mock implementation of LLM/Cognitive extraction)
        # In a real scenario, this would call an LLM to summarize the error.
        # Here we use logic to simulate "Understanding".
        mitigation = self._generate_mitigation_strategy(error_data)
        description = f"Detected pattern: {error_data['error_type']} when {error_data['context'].get('operation', 'processing')}."

        new_rule = HeuristicRule(
            rule_id=f"rule_{signature[:8]}",
            pattern_signature=signature,
            description=description,
            mitigation_strategy=mitigation
        )

        self.rule_database[signature] = new_rule
        logger.info(f"NEW RULE CRystallized: {new_rule.rule_id} - {new_rule.description}")
        
        return new_rule

    def _generate_mitigation_strategy(self, error_data: ErrorTrace) -> str:
        """
        [Core Function 2] Determines the corrective action based on the error.
        
        This is the 'Learning' phase. It maps specific failure modes to code fixes.
        
        Args:
            error_data (ErrorTrace): The detailed error info.
            
        Returns:
            str: A natural language or pseudo-code instruction to fix the issue.
        """
        etype = error_data['error_type']
        context = error_data['context']
        
        # Logic for specific known patterns (The "Experience" Base)
        if "UnicodeDecodeError" in etype and "csv" in context.get("file_type", ""):
            return "Always check for BOM headers or use encoding='utf-8-sig' when reading CSVs."
        
        if "FileNotFoundError" in etype:
            return "Verify file existence using os.path.exists() before attempting to open."
            
        if "IndexError" in etype and "list" in error_data['error_message']:
            return "Validate list length before accessing specific indices."

        # Default generic strategy
        return f"Investigate {etype} and add try-except blocks around the failing operation."

    def check_code_against_rules(self, code_snippet: str, context: Dict[str, Any]) -> List[str]:
        """
        [Utility Function] Checks if a code snippet likely violates known rules.
        
        This is the application of the 'True Node' to prevent future errors.
        
        Args:
            code_snippet (str): The code to check.
            context (Dict): Context of the code generation.
            
        Returns:
            List[str]: List of warnings/mitigation strategies to apply.
        """
        warnings = []
        
        # Simple heuristics for checking (Mock implementation)
        # Real implementation might use AST parsing or semantic search
        if "csv" in context.get("file_type", "") and "utf-8-sig" not in code_snippet:
            # Check if we have a rule about CSV encoding
            for rule in self.rule_database.values():
                if "BOM" in rule.mitigation_strategy:
                    warnings.append(rule.mitigation_strategy)
                    break
                    
        return warnings

# Example Usage
if __name__ == "__main__":
    # 1. Simulate a human-provided failure event
    failure_event: ErrorTrace = {
        "code_snippet": "import pandas as pd\ndf = pd.read_csv('data.csv')",
        "error_type": "UnicodeDecodeError",
        "error_message": "'utf-8' codec can't decode byte 0xff in position 0: invalid start bit",
        "context": {
            "file_type": "csv",
            "library": "pandas",
            "operation": "reading file"
        },
        "user_feedback": "This failed because the CSV had a BOM header."
    }

    # 2. Initialize the Cognitive Consilidator
    consolidator = FailureConsolidator()

    # 3. Process the failure
    print("--- Processing Failure ---")
    new_rule = consolidator.analyze_and_consolidate(failure_event)
    
    if new_rule:
        print(f"Rule Created: {new_rule.rule_id}")
        print(f"Mitigation: {new_rule.mitigation_strategy}")

    # 4. Simulate checking future code (Collision Prevention)
    print("\n--- Checking Future Code ---")
    future_code = "import pandas as pd\ndf = pd.read_csv('new_data.csv')"
    checks = consolidator.check_code_against_rules(future_code, {"file_type": "csv"})
    
    if checks:
        print("WARNING: Potential collision detected!")
        for warning in checks:
            print(f"- Suggestion: {warning}")
    else:
        print("Code passed heuristic checks.")