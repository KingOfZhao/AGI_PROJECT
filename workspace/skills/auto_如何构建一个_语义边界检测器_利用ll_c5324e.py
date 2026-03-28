"""
Module: semantic_boundary_detector.py
Description: AGI Skill - Detects semantic boundaries in vague user intents.
             Transforms unstructured natural language into a structured tri-tuple
             (Explicit Constraints, Implicit Assumptions, Pending Variables).
Author: Senior Python Engineer
Version: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Any

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class IntentComplexity(Enum):
    """Enumeration for intent complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"

@dataclass
class StructuredIntent:
    """
    Represents the semi-structured output of the Semantic Boundary Detector.
    
    Attributes:
        raw_intent (str): The original user input.
        explicit_constraints (Dict[str, Any]): Clearly defined requirements extracted from text.
        implicit_assumptions (List[str]): Logical inferences made by the LLM to fill gaps.
        pending_variables (List[Dict[str, str]]): Missing parameters that must be confirmed 
                                                  before code generation to prevent hallucination.
        complexity (IntentComplexity): Estimated complexity of the intent.
    """
    raw_intent: str
    explicit_constraints: Dict[str, Any]
    implicit_assumptions: List[str]
    pending_variables: List[Dict[str, str]]
    complexity: IntentComplexity

    def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass to a dictionary for JSON serialization."""
        data = asdict(self)
        data['complexity'] = self.complexity.value
        return data

# --- Custom Exceptions ---

class LLMSyntaxError(Exception):
    """Raised when the LLM response cannot be parsed."""
    pass

class IntentValidationError(Exception):
    """Raised when the input intent violates safety or format checks."""
    pass

# --- Core Logic ---

class SemanticBoundaryDetector:
    """
    Analyzes vague intents using an LLM interface to separate facts from assumptions
    and identify missing information.
    """

    def __init__(self, llm_interface: Any, max_retries: int = 2):
        """
        Initialize the detector.
        
        Args:
            llm_interface (Any): An object that implements a `generate(prompt: str) -> str` method.
            max_retries (int): Number of retries for LLM calls.
        """
        self.llm = llm_interface
        self.max_retries = max_retries
        logger.info("SemanticBoundaryDetector initialized.")

    def _construct_system_prompt(self, user_intent: str) -> str:
        """
        Constructs the prompt engineering template for the LLM.
        
        Args:
            user_intent (str): The raw user input.
            
        Returns:
            str: The formatted prompt.
        """
        prompt = f"""
        You are a Semantic Boundary Detector for an AGI coding system.
        Your goal is to analyze the following vague user intent and decompose it into a structured JSON format.
        Do NOT generate code. Identify what is missing.
        
        User Intent: "{user_intent}"
        
        Analyze the intent and output a valid JSON object with the following keys:
        1. "explicit_constraints": (Dict) Facts explicitly stated in the prompt (e.g., platform, language, specific features).
        2. "implicit_assumptions": (List) Logical guesses you had to make to understand the request (e.g., "User implies mobile app", "Default language is Python").
        3. "pending_variables": (List of Dicts) Critical missing information needed to proceed. Format: [{{"var_name": "...", "reason": "...", "suggestion": "..."}}].
        4. "complexity": (String) One of ["simple", "moderate", "complex", "ambiguous"].
        
        JSON Output:
        """
        return prompt

    def _validate_and_parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Validates and parses the LLM response string into a JSON dictionary.
        
        Args:
            raw_response (str): The raw string output from the LLM.
            
        Returns:
            Dict[str, Any]: Parsed JSON data.
            
        Raises:
            LLMSyntaxError: If JSON is invalid or missing required keys.
        """
        try:
            # Basic extraction for markdown code blocks if present
            if "