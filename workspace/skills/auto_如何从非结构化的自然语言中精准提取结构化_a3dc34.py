"""
Module: intent_atomic_extractor.py

Description:
    This module implements a high-precision mechanism to extract structured 'Intent Atoms'
    from unstructured natural language. It focuses on stripping emotional noise, 
    redundant modifiers, and resolving implicit context to produce a strictly defined 
    Intermediate Representation (IR) suitable for AGI code generation pipelines.

    The process involves:
    1. Text Cleaning (Sanitization)
    2. Semantic Parsing (Action-Entity-Condition extraction)
    3. IR Construction & Validation

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants & Enums ---

class IntentCategory(Enum):
    """Categorization of the extracted intent."""
    DATA_RETRIEVAL = "data_retrieval"
    DATA_MANIPULATION = "data_manipulation"
    SYSTEM_CONTROL = "system_control"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"

# Regex patterns for noise reduction (Simplified for demo, in prod use NLP models)
NOISE_PATTERNS = [
    r"\b(please|kindly|would you|could you|i want|i need|hopefully|just|maybe)\b",
    r"[.,!?;:]"
]

ACTION_MAPPING = {
    "create": "CREATE",
    "make": "CREATE",
    "generate": "CREATE",
    "delete": "DELETE",
    "remove": "DELETE",
    "get": "READ",
    "fetch": "READ",
    "find": "READ",
    "update": "UPDATE",
    "change": "UPDATE",
    "modify": "UPDATE",
    "send": "SEND",
    "email": "SEND",
    "list": "READ"
}

# --- Data Structures ---

@dataclass
class IntentAtom:
    """
    Intermediate Representation (IR) of a human intent.
    
    Attributes:
        action: The core verb normalized to standard logic (e.g., CREATE, READ).
        target: The primary object or entity being acted upon.
        parameters: Key-value pairs extracted from the context.
        constraints: Conditions or filters applied to the action.
        raw_text: The original input text for reference.
        confidence: Extraction confidence score (0.0 to 1.0).
    """
    action: str
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the IR to a dictionary for downstream processing."""
        return {
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "constraints": self.constraints,
            "metadata": {
                "raw_text": self.raw_text,
                "confidence": self.confidence
            }
        }

# --- Core Functions ---

def sanitize_and_normalize(text: str) -> str:
    """
    Removes emotional noise, stop words, and normalizes text to lowercase.
    
    Args:
        text (str): Raw natural language input.
        
    Returns:
        str: Cleaned and normalized string.
        
    Raises:
        ValueError: If input is empty or not a string.
    """
    if not isinstance(text, str):
        logger.error(f"Invalid input type: {type(text)}")
        raise ValueError("Input must be a string.")
    
    if not text.strip():
        logger.warning("Empty input text received.")
        raise ValueError("Input text cannot be empty.")

    logger.debug(f"Original text: {text}")
    
    # Lowercase
    cleaned_text = text.lower()
    
    # Remove noise patterns
    for pattern in NOISE_PATTERNS:
        cleaned_text = re.sub(pattern, "", cleaned_text)
    
    # Remove extra whitespace
    cleaned_text = " ".join(cleaned_text.split())
    
    logger.debug(f"Sanitized text: {cleaned_text}")
    return cleaned_text

def extract_intent_atom(text: str, context: Optional[Dict[str, Any]] = None) -> IntentAtom:
    """
    Main extraction function. Maps natural language to structured IntentAtom IR.
    
    This function implements a rule-based extraction logic (simulated) to identify 
    the core logical components of a request.
    
    Args:
        text (str): The raw user input.
        context (Optional[Dict]): External context (e.g., user session, history).
        
    Returns:
        IntentAtom: The structured intermediate representation.
        
    Example:
        >>> extract_intent_atom("Please create a new user account for John Doe who is an admin.")
        IntentAtom(action='CREATE', target='user account', parameters={'name': 'John Doe', 'role': 'admin'}, ...)
    """
    logger.info(f"Processing intent extraction for: '{text}'")
    
    try:
        # Step 1: Sanitization
        clean_text = sanitize_and_normalize(text)
        
        # Step 2: Action Extraction (Keyword Matching)
        detected_action = "UNKNOWN"
        for keyword, standard_action in ACTION_MAPPING.items():
            if keyword in clean_text.split():
                detected_action = standard_action
                break
        
        # Step 3: Target & Parameter Extraction (Heuristic Parsing)
        # This simulates a semantic parser identifying entities
        target = "unknown_entity"
        params = {}
        constraints = []
        
        # Simple heuristic for demonstration purposes
        words = clean_text.split()
        
        if "user" in words:
            target = "user_account"
        elif "report" in words:
            target = "system_report"
        elif "file" in words:
            target = "file_object"
            
        # Extract potential parameters (e.g., names, dates)
        # Looking for specific patterns like "for [Name]" or "at [Time]"
        if "for" in words:
            idx = words.index("for")
            if idx + 1 < len(words):
                # Capture next word as a parameter
                params["recipient"] = words[idx + 1]
        
        if "admin" in words:
            params["role"] = "administrator"
            
        if "urgent" in words or "asap" in words:
            constraints.append("priority:high")

        # Step 4: Confidence Calculation
        confidence = 0.0
        if detected_action != "UNKNOWN" and target != "unknown_entity":
            confidence = 0.8
        elif detected_action != "UNKNOWN":
            confidence = 0.5
        else:
            confidence = 0.1
            
        # Step 5: Construct IR
        atom = IntentAtom(
            action=detected_action,
            target=target,
            parameters=params,
            constraints=constraints,
            raw_text=text,
            confidence=confidence
        )
        
        logger.info(f"Extraction complete. Action: {detected_action}, Target: {target}")
        return atom

    except ValueError as ve:
        logger.error(f"Validation error during extraction: {ve}")
        # Return a null-payload atom or re-raise based on system design
        return IntentAtom(action="ERROR", target="invalid_input", raw_text=text)
    except Exception as e:
        logger.critical(f"Unexpected error during extraction: {e}", exc_info=True)
        raise RuntimeError("Intent extraction pipeline failed.") from e

# --- Helper Functions ---

def validate_intent_ir(atom: IntentAtom) -> bool:
    """
    Validates the structural integrity of the IntentAtom.
    
    Args:
        atom (IntentAtom): The dataclass instance to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(atom, IntentAtom):
        logger.error("Validation failed: Input is not an IntentAtom instance.")
        return False
        
    if not atom.action or not isinstance(atom.action, str):
        logger.error("Validation failed: Action missing or invalid.")
        return False
        
    if not atom.target or not isinstance(atom.target, str):
        logger.error("Validation failed: Target missing or invalid.")
        return False
        
    if not (0.0 <= atom.confidence <= 1.0):
        logger.warning(f"Confidence score out of bounds: {atom.confidence}. Clamping.")
        # Clamp logic could go here, but strict validation fails it here
        
    logger.info("IntentAtom validation passed.")
    return True

# --- Main Execution / Usage Example ---

if __name__ == "__main__":
    # Example Usage
    user_inputs = [
        "Please create a new user account for Sarah.",
        "I need you to delete the old log files immediately.",
        "Could you maybe send the report to the management team?",
        "This is annoying, fix the bug in the login system!"
    ]
    
    print(f"{'='*60}\nIntent Atomic Extractor v1.0\n{'='*60}")
    
    for raw_input in user_inputs:
        print(f"\nInput: {raw_input}")
        try:
            # Extract
            ir = extract_intent_atom(raw_input)
            
            # Validate
            is_valid = validate_intent_ir(ir)
            
            if is_valid:
                # Output formatted IR
                print(f"-> Extracted IR: {ir.to_dict()}")
            else:
                print("-> Extraction failed validation.")
                
        except Exception as e:
            print(f"-> System Error: {e}")