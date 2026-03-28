"""
Module: auto_natural_language_structural_mapping_be7c57
Description: A high-robustness semantic parser designed to convert unstructured,
             ambiguous Natural Language (NL) instructions into a structured
             Intermediate Representation (IR) / Abstract Syntax Tree (AST).
             It handles context dependency and intent disambiguation.
Author: AGI System Core
Version: 1.0.0
"""

import re
import json
import logging
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class IntentCategory(Enum):
    """Enumeration of recognized intent categories."""
    QUERY = "QUERY"
    COMMAND = "COMMAND"
    TRANSACTIONAL = "TRANSACTIONAL"
    UNKNOWN = "UNKNOWN"

class ConfidenceLevel(Enum):
    """Confidence level of the parsing result."""
    HIGH = 1.0
    MEDIUM = 0.7
    LOW = 0.4
    INVALID = 0.0

@dataclass
class SemanticAtom:
    """Represents a single extracted semantic unit (e.g., entity, action, target)."""
    token: str
    entity_type: str
    normalized_value: Any
    source_span: tuple  # (start_index, end_index)

@dataclass
class IntermediateRepresentation:
    """
    The structured output resembling an AST/IR.
    This serves as the bridge between NL and executable logic.
    """
    raw_input: str
    primary_intent: IntentCategory
    confidence: float
    entities: List[SemanticAtom] = field(default_factory=list)
    logic_tree: Dict[str, Any] = field(default_factory=dict)
    context_references: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Converts the IR to a serializable dictionary."""
        data = asdict(self)
        data['primary_intent'] = self.primary_intent.value
        data['entities'] = [
            {**e, 'source_span': list(e['source_span'])} 
            for e in data['entities']
        ]
        return data

# --- Custom Exceptions ---

class ParsingError(Exception):
    """Base exception for parsing failures."""
    pass

class InputValidationError(ParsingError):
    """Raised when input text is invalid or unsafe."""
    pass

class IntentDisambiguationError(ParsingError):
    """Raised when the intent cannot be reliably determined."""
    pass

# --- Core Logic ---

class RobustSemanticParser:
    """
    A robust parser that transforms natural language into structured IR.
    Implements validation, disambiguation, and context handling.
    """

    def __init__(self, context_memory: Optional[Dict[str, Any]] = None):
        """
        Initialize the parser.
        
        Args:
            context_memory: A dictionary holding previous context (e.g., user preferences, last query).
        """
        self._context = context_memory or {}
        # Regex patterns for simple entity extraction (mock logic for NER)
        self._patterns = {
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "DATE": re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
            "QUANTITY": re.compile(r'\b\d+\b'),
            "TARGET_OBJECT": re.compile(r'\b(file|user|database|record|image)s?\b', re.IGNORECASE)
        }
        logger.info("RobustSemanticParser initialized.")

    def _validate_input(self, text: str) -> str:
        """
        Validates and sanitizes input text.
        
        Args:
            text: Raw input string.
        
        Returns:
            Sanitized string.
        
        Raises:
            InputValidationError: If input is empty or exceeds safety limits.
        """
        if not text or not isinstance(text, str):
            raise InputValidationError("Input must be a non-empty string.")
        
        text = text.strip()
        
        # Boundary check: Prevent buffer overflow attacks or resource exhaustion
        if len(text) > 5000:
            logger.warning("Input text truncated to 5000 characters.")
            text = text[:5000]
            
        # Basic sanitization (preventing code injection in downstream tasks)
        # Note: In a real AGI system, this would be more sophisticated.
        dangerous_patterns = ["<script>", "rm -rf", "DROP TABLE"]
        for pat in dangerous_patterns:
            if pat in text:
                logger.error(f"Potentially malicious input detected: {pat}")
                raise InputValidationError("Input contains disallowed patterns.")
                
        return text

    def _extract_entities(self, text: str) -> List[SemanticAtom]:
        """
        Helper function to extract semantic atoms (entities) from text.
        
        Args:
            text: Validated input text.
            
        Returns:
            List of SemanticAtom objects.
        """
        atoms = []
        for entity_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                atom = SemanticAtom(
                    token=match.group(),
                    entity_type=entity_type,
                    normalized_value=match.group().lower() if entity_type == "TARGET_OBJECT" else match.group(),
                    source_span=(match.start(), match.end())
                )
                atoms.append(atom)
        return atoms

    def _map_intent_to_logic(self, text: str, entities: List[SemanticAtom]) -> Dict[str, Any]:
        """
        Core mapping logic: Transforms intent and entities into a logic tree (AST).
        
        Args:
            text: Input text.
            entities: Extracted entities.
            
        Returns:
            A dictionary representing the logical structure.
        """
        text_lower = text.lower()
        logic = {"action": "NOOP", "target": None, "conditions": []}
        
        # Intent mapping
        if "send" in text_lower or "email" in text_lower:
            logic["action"] = "SEND_MESSAGE"
        elif "find" in text_lower or "search" in text_lower:
            logic["action"] = "QUERY_DB"
        elif "delete" in text_lower or "remove" in text_lower:
            logic["action"] = "DELETE_RECORD"
        else:
            logic["action"] = "GENERIC_PROCESS"

        # Fill logic tree based on entities
        for atom in entities:
            if atom.entity_type == "TARGET_OBJECT":
                logic["target"] = atom.normalized_value
            elif atom.entity_type == "EMAIL":
                logic["target_recipient"] = atom.normalized_value
            elif atom.entity_type == "DATE":
                logic["conditions"].append({"field": "date", "op": "eq", "value": atom.normalized_value})

        # Context injection: If referencing previous context
        if "it" in text_lower.split() or "that" in text_lower.split():
            logic["context_ref"] = self._context.get("last_subject", "UNKNOWN")
            
        return logic

    def parse(self, text: str) -> IntermediateRepresentation:
        """
        Main entry point: Parses NL text into a structured IntermediateRepresentation.
        
        Args:
            text: The natural language input string.
            
        Returns:
            IntermediateRepresentation object.
            
        Raises:
            ParsingError: If parsing fails critically.
        """
        try:
            # Step 1: Validation
            clean_text = self._validate_input(text)
            logger.info(f"Processing input: '{clean_text[:50]}...'")

            # Step 2: Entity Extraction (NER)
            entities = self._extract_entities(clean_text)
            logger.debug(f"Extracted {len(entities)} entities.")

            # Step 3: Intent Classification (Heuristic/Symbolic for this module)
            # In a real AGI system, this would call an LLM or Classifier
            intent = IntentCategory.COMMAND if "please" in clean_text.lower() else IntentCategory.QUERY
            
            # Step 4: Logic Mapping (AST Construction)
            logic_tree = self._map_intent_to_logic(clean_text, entities)
            
            # Step 5: Confidence Calculation
            # Heuristic: Low confidence if no entities found for a complex sentence
            confidence = ConfidenceLevel.HIGH.value if entities else ConfidenceLevel.MEDIUM.value
            if logic_tree["action"] == "NOOP":
                confidence = ConfidenceLevel.LOW.value

            # Step 6: Construct IR
            ir = IntermediateRepresentation(
                raw_input=clean_text,
                primary_intent=intent,
                confidence=confidence,
                entities=entities,
                logic_tree=logic_tree
            )
            
            # Update context for future turns
            if logic_tree.get("target"):
                self._context["last_subject"] = logic_tree["target"]

            return ir

        except InputValidationError as ive:
            logger.error(f"Validation Error: {ive}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected parsing error: {e}")
            raise ParsingError(f"Failed to parse input: {e}") from e

# --- Usage Example ---

if __name__ == "__main__":
    # Initialize parser
    parser = RobustSemanticParser()
    
    # Example 1: Simple Command
    nl_input_1 = "Please find all users created on 2023-10-05"
    
    try:
        result_1 = parser.parse(nl_input_1)
        print("\n--- Parsed Result 1 ---")
        print(json.dumps(result_1.to_dict(), indent=2))
    except ParsingError as e:
        print(f"Error: {e}")

    # Example 2: Contextual Query with Ambiguity
    nl_input_2 = "Delete it permanently" 
    
    # Simulate context existence
    parser._context["last_subject"] = "file"
    
    try:
        result_2 = parser.parse(nl_input_2)
        print("\n--- Parsed Result 2 (Contextual) ---")
        print(json.dumps(result_2.to_dict(), indent=2))
    except ParsingError as e:
        print(f"Error: {e}")