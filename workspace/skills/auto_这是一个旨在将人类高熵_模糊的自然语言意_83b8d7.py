"""
Module: intent_entropy_reducer.py

This system is designed to transform high-entropy, ambiguous natural language
intentions into low-entropy, formalized machine-executable logic through
structured cognitive friction detection and iterative inquiry.

It serves as an ontological alignment layer, building 'explanatory bridge nodes'
to bridge the gap between high mathematical logic domains and high fuzzy logic domains.
"""

import logging
import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentEntropyReducer")

class IntentState(Enum):
    """Enumeration of the intent processing states."""
    RAW = "RAW"
    ANALYZED = "ANALYZED"
    CLARIFIED = "CLARIFIED"
    FORMALIZED = "FORMALIZED"
    ERROR = "ERROR"

@dataclass
class IntentContext:
    """
    Data structure to hold the context of the user's intent.
    
    Attributes:
        raw_input (str): The original natural language input.
        current_state (IntentState): The current processing state.
        extracted_entities (Dict[str, Any]): Key-value pairs extracted from text.
        ambiguity_score (float): A heuristic score (0.0 to 1.0) representing uncertainty.
        formal_logic (Optional[Dict]): The final structured output.
        history (List[str]): Log of processing steps and clarifications.
    """
    raw_input: str
    current_state: IntentState = IntentState.RAW
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    ambiguity_score: float = 1.0
    formal_logic: Optional[Dict] = None
    history: List[str] = field(default_factory=list)

class IntentEntropyReducer:
    """
    A system to translate fuzzy human language into executable logic.
    
    It uses a loop of analysis and questioning to reduce semantic entropy.
    """

    def __init__(self, threshold: float = 0.25):
        """
        Initialize the reducer.
        
        Args:
            threshold (float): The maximum allowed ambiguity score to proceed 
                               without human clarification.
        """
        self.threshold = threshold
        self._validate_threshold()
        logger.info(f"IntentEntropyReducer initialized with threshold: {threshold}")

    def _validate_threshold(self) -> None:
        """Validate the ambiguity threshold boundary."""
        if not 0.0 <= self.threshold <= 1.0:
            logger.error("Threshold must be between 0.0 and 1.0")
            raise ValueError("Threshold must be between 0.0 and 1.0")

    def _calculate_entropy(self, text: str, entities: Dict) -> float:
        """
        [Helper] Calculate a heuristic ambiguity score based on linguistic markers.
        
        High entropy indicators: vague words (some, maybe, roughly), 
        lack of specific parameters, or conflicting entity types.
        
        Args:
            text (str): The input text.
            entities (Dict): Extracted entities.
            
        Returns:
            float: Ambiguity score between 0.0 (certain) and 1.0 (chaotic).
        """
        score = 0.0
        vague_markers = ['maybe', 'roughly', 'some', 'kind of', 'approximately', 'later']
        
        # Check for vague linguistic markers
        for marker in vague_markers:
            if marker in text.lower():
                score += 0.15
        
        # Check for missing critical entities (heuristic)
        if 'target' not in entities or 'action' not in entities:
            score += 0.4
            
        # Check for sentence complexity (very short or very long)
        word_count = len(text.split())
        if word_count < 3:
            score += 0.3
        
        return min(max(score, 0.0), 1.0)

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        [Core] Extracts structured entities from natural language.
        
        This is a simplified NLP parser mock. In production, this would 
        interface with an LLM or NLP pipeline.
        
        Args:
            text (str): Input text.
            
        Returns:
            Dict: Extracted entities.
        """
        entities = {}
        text_lower = text.lower()
        
        # Mock extraction logic
        if 'file' in text_lower or 'data' in text_lower:
            entities['target'] = 'file_system'
        if 'send' in text_lower or 'email' in text_lower:
            entities['action'] = 'communication'
        if 'analyze' in text_lower or 'check' in text_lower:
            entities['action'] = 'analysis'
            
        # Regex for specific parameters (e.g., numbers)
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            entities['parameters'] = [int(n) for n in numbers]
            
        return entities

    def process_intent(self, raw_input: str) -> IntentContext:
        """
        [Core] Main entry point to process raw natural language.
        
        It attempts to parse, check ambiguity, and formalize the input.
        
        Args:
            raw_input (str): The user's raw input string.
            
        Returns:
            IntentContext: The context object containing the formalized logic 
                           or requests for clarification.
        """
        if not isinstance(raw_input, str) or not raw_input.strip():
            logger.error("Invalid input provided.")
            return IntentContext(raw_input="", current_state=IntentState.ERROR)

        context = IntentContext(raw_input=raw_input)
        context.history.append(f"Received input: {raw_input}")
        
        try:
            # Step 1: Extraction
            context.extracted_entities = self._extract_entities(raw_input)
            context.ambiguity_score = self._calculate_entropy(raw_input, context.extracted_entities)
            context.current_state = IntentState.ANALYZED
            logger.info(f"Analysis complete. Entities: {context.extracted_entities}, Entropy: {context.ambiguity_score}")

            # Step 2: Entropy Check & Formalization
            if context.ambiguity_score <= self.threshold:
                context.formal_logic = self._formalize(context.extracted_entities)
                context.current_state = IntentState.FORMALIZED
                context.history.append("Formalization successful without clarification.")
                logger.info("Intent formalized successfully.")
            else:
                context.current_state = IntentState.CLARIFIED # Meaning 'Needs Clarification'
                context.history.append("High entropy detected. Clarification required.")
                logger.warning("Ambiguity detected, formalization paused.")
                
            return context

        except Exception as e:
            logger.exception("Critical error during intent processing.")
            context.current_state = IntentState.ERROR
            context.history.append(f"Error: {str(e)}")
            return context

    def _formalize(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Core] Converts extracted entities into a strict logic format.
        
        Args:
            entities (Dict): The verified entities.
            
        Returns:
            Dict: A structured command object.
        """
        logic_map = {
            "command": entities.get("action", "unknown"),
            "target": entities.get("target", "global"),
            "params": entities.get("parameters", []),
            "execution_mode": "sync",
            "confidence": 1.0
        }
        return logic_map

    def handle_clarification(self, context: IntentContext, user_response: str) -> IntentContext:
        """
        Handles the user's response to a clarification request.
        
        Args:
            context (IntentContext): The previous context.
            user_response (str): The user's additional input.
            
        Returns:
            IntentContext: Updated context.
        """
        if context.current_state != IntentState.CLARIFIED:
            logger.warning("handle_clarification called on invalid state.")
            return context

        # Merge new info
        new_entities = self._extract_entities(user_response)
        context.extracted_entities.update(new_entities)
        context.raw_input += f" [Clarified: {user_response}]"
        
        # Re-calculate entropy
        context.ambiguity_score = self._calculate_entropy(context.raw_input, context.extracted_entities)
        
        if context.ambiguity_score <= self.threshold:
            context.formal_logic = self._formalize(context.extracted_entities)
            context.current_state = IntentState.FORMALIZED
            logger.info("Intent recovered and formalized.")
        else:
            context.history.append("Clarification insufficient.")
            
        return context

# Example Usage
if __name__ == "__main__":
    # Initialize system
    reducer = IntentEntropyReducer(threshold=0.3)
    
    # Simulate a vague input
    vague_input = "maybe check that file roughly"
    result_context = reducer.process_intent(vague_input)
    
    print(f"State: {result_context.current_state.value}")
    print(f"Score: {result_context.ambiguity_score}")
    
    if result_context.current_state == IntentState.CLARIFIED:
        print("System requires clarification...")
        # Simulate user providing specific details
        result_context = reducer.handle_clarification(result_context, "Check file log.txt at 9pm")
        print(f"New State: {result_context.current_state.value}")
        
    if result_context.formal_logic:
        print("Final Executable Logic:")
        print(json.dumps(result_context.formal_logic, indent=2))