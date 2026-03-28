"""
Module: interactive_clarification_protocol.py

This module implements an Interactive Clarification Protocol (ICP) designed for
Human-Computer Symbiosis (HCS) loops. It detects intent ambiguity or logical
conflicts within structured inputs and generates minimized guessing questions
(Multiple Choice) to help the system converge on the user's true intent.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import json
from enum import Enum
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Enumeration for types of logical conflicts or ambiguities."""
    INTENT_AMBIGUITY = "INTENT_AMBIGUITY"
    LOGICAL_CONFLICT = "LOGICAL_CONFLICT"
    MISSING_CONTEXT = "MISSING_CONTEXT"


@dataclass
class ClarificationChoice:
    """Represents a single choice in a multiple-choice question."""
    id: str
    content: str
    confidence_weight: float = 1.0  # Used for ranking or selection probability


@dataclass
class ClarificationRequest:
    """
    Structured object representing a request for human clarification.
    This is the output format of the protocol generation.
    """
    request_id: str
    conflict_type: ConflictType
    question_text: str
    choices: List[ClarificationChoice]
    timeout_seconds: int = 30

    def to_api_format(self) -> Dict[str, Any]:
        """Converts the request into a JSON-serializable dictionary for API transmission."""
        return {
            "request_id": self.request_id,
            "type": self.conflict_type.value,
            "interaction": {
                "prompt": self.question_text,
                "options": [
                    {"id": c.id, "label": c.content} for c in self.choices
                ]
            },
            "metadata": {
                "timeout": self.timeout_seconds
            }
        }


@dataclass
class UserIntentInput:
    """
    Input data structure containing the raw user input and analyzed metadata.
    """
    raw_text: str
    extracted_entities: Dict[str, Any]
    detected_intents: List[Dict[str, float]]  # List of {"intent": str, "score": float}
    context_tags: List[str] = field(default_factory=list)


class ClarificationProtocolEngine:
    """
    Core engine for generating interactive clarification protocols.
    
    This engine analyzes input data for ambiguities and generates structured
    multiple-choice questions to resolve them efficiently.
    """

    def __init__(self, ambiguity_threshold: float = 0.75, conflict_threshold: float = 0.2):
        """
        Initialize the engine with thresholds.

        Args:
            ambiguity_threshold (float): The minimum confidence score required to 
                                         avoid clarification (0.0 to 1.0).
            conflict_threshold (float): If secondary intent scores are within this 
                                        margin of the primary intent, it flags a conflict.
        """
        if not 0.0 <= ambiguity_threshold <= 1.0:
            raise ValueError("Ambiguity threshold must be between 0.0 and 1.0")
        
        self.ambiguity_threshold = ambiguity_threshold
        self.conflict_threshold = conflict_threshold
        logger.info("ClarificationProtocolEngine initialized with thresholds: Ambiguity=%.2f", ambiguity_threshold)

    def _validate_input(self, user_input: UserIntentInput) -> bool:
        """
        Validates the structure and content of the input data.

        Args:
            user_input (UserIntentInput): The input object to validate.

        Returns:
            bool: True if valid.

        Raises:
            ValueError: If critical data is missing or malformed.
        """
        if not user_input.raw_text:
            logger.error("Validation failed: Raw text is empty.")
            raise ValueError("Input raw text cannot be empty.")
        
        if not user_input.detected_intents:
            logger.warning("Validation warning: No intents detected in input.")
            
        return True

    def _detect_ambiguity(self, intents: List[Dict[str, float]]) -> Optional[Tuple[str, ConflictType]]:
        """
        Analyzes intent scores to detect ambiguity or conflict.

        Args:
            intents: List of intent dictionaries with scores.

        Returns:
            A tuple of (Description, ConflictType) if conflict found, else None.
        """
        if not intents:
            return ("Unable to determine specific action.", ConflictType.INTENT_AMBIGUITY)

        # Sort intents by score descending
        sorted_intents = sorted(intents, key=lambda x: x['score'], reverse=True)
        top_intent = sorted_intents[0]
        
        # Case 1: Low confidence even for top intent
        if top_intent['score'] < self.ambiguity_threshold:
            logger.debug("Detected low confidence ambiguity for intent: %s", top_intent['intent'])
            return ("Primary intent confidence is low.", ConflictType.INTENT_AMBIGUITY)

        # Case 2: Close competitors (Conflict)
        if len(sorted_intents) > 1:
            second_intent = sorted_intents[1]
            if (top_intent['score'] - second_intent['score']) < self.conflict_threshold:
                logger.debug("Detected logical conflict between %s and %s", top_intent['intent'], second_intent['intent'])
                return ("Multiple intents have similar confidence.", ConflictType.LOGICAL_CONFLICT)

        return None

    def generate_clarification_request(
        self, 
        user_input: UserIntentInput, 
        request_id: str
    ) -> Optional[ClarificationRequest]:
        """
        Main core function: Analyzes input and generates a clarification request if needed.

        Args:
            user_input (UserIntentInput): Structured input from the perception layer.
            request_id (str): Unique ID for tracking this interaction.

        Returns:
            ClarificationRequest: The generated question object, or None if intent is clear.
        """
        try:
            self._validate_input(user_input)
            
            # Check for logical conflicts or ambiguity
            conflict_info = self._detect_ambiguity(user_input.detected_intents)
            
            if not conflict_info:
                logger.info("Intent is clear. No clarification needed for request %s", request_id)
                return None

            description, conflict_type = conflict_info
            
            # Generate choices based on the top detected intents
            # We limit choices to top 3 for cognitive load minimization
            choices = self._generate_minimal_choices(user_input.detected_intents[:3])

            # Construct the question text
            question_text = self._construct_question_prompt(user_input.raw_text, conflict_type)

            request = ClarificationRequest(
                request_id=request_id,
                conflict_type=conflict_type,
                question_text=question_text,
                choices=choices
            )
            
            logger.info("Generated Clarification Request for ID %s", request_id)
            return request

        except Exception as e:
            logger.error("Error generating clarification request: %s", str(e), exc_info=True)
            raise

    def _generate_minimal_choices(self, candidate_intents: List[Dict[str, float]]) -> List[ClarificationChoice]:
        """
        Helper function to convert candidate intents into user-friendly choices.
        Ensures unique options and handles edge cases.
        """
        choices = []
        for idx, intent_data in enumerate(candidate_intents):
            # In a real system, we would map 'intent' strings to natural language templates
            choice_text = f"Execute action: {intent_data['intent'].replace('_', ' ').title()}"
            
            choices.append(ClarificationChoice(
                id=f"choice_{idx}",
                content=choice_text,
                confidence_weight=intent_data['score']
            ))
        
        # Add an "Other" option as a fallback
        choices.append(ClarificationChoice(
            id="choice_other",
            content="None of the above (Please specify)",
            confidence_weight=0.0
        ))
        
        return choices

    def _construct_question_prompt(self, raw_text: str, conflict_type: ConflictType) -> str:
        """
        Helper function to synthesize the natural language question.
        """
        if conflict_type == ConflictType.LOGICAL_CONFLICT:
            return f"I detected multiple possible instructions in your request: '{raw_text}'. Which one did you mean?"
        elif conflict_type == ConflictType.INTENT_AMBIGUITY:
            return f"I'm not quite sure what you mean by: '{raw_text}'. Could you clarify?"
        else:
            return "Please select the most appropriate action:"


def process_user_feedback(feedback_json: str) -> Dict[str, Any]:
    """
    Simulates processing the user's response to the clarification request.
    
    Args:
        feedback_json (str): JSON string containing the user's selection.

    Returns:
        Dict: Processed result confirming the final intent.
    """
    try:
        data = json.loads(feedback_json)
        selected_id = data.get('selected_choice_id')
        request_id = data.get('request_id')
        
        if not selected_id:
            raise ValueError("Missing selected_choice_id in feedback")

        logger.info("Feedback received for request %s: Selected %s", request_id, selected_id)
        
        # Logic to update system state or trigger action would go here
        return {
            "status": "RESOLVED",
            "confirmed_action_id": selected_id,
            "message": "Intent successfully converged."
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON format received in feedback.")
        return {"status": "ERROR", "message": "Invalid feedback format"}
    except Exception as e:
        logger.error("Error processing feedback: %s", str(e))
        return {"status": "ERROR", "message": str(e)}


# ----------------------------
# Usage Example
# ----------------------------
if __name__ == "__main__":
    # 1. Setup the Engine
    engine = ClarificationProtocolEngine(ambiguity_threshold=0.80, conflict_threshold=0.15)

    # 2. Simulate ambiguous input (Two high scores close to each other)
    # User says "Book the ticket", but system detects 'Flight' and 'Movie' with similar scores
    ambiguous_input = UserIntentInput(
        raw_text="Book the ticket for tonight",
        extracted_entities={"time": "tonight"},
        detected_intents=[
            {"intent": "book_flight", "score": 0.82},
            {"intent": "book_movie", "score": 0.81},
            {"intent": "book_train", "score": 0.30}
        ]
    )

    print("--- Processing Input ---")
    try:
        # 3. Generate Protocol
        clarification = engine.generate_clarification_request(
            user_input=ambiguous_input, 
            request_id="req_1001"
        )

        if clarification:
            print("\n>>> SYSTEM GENERATED QUESTION <<<")
            print(f"Type: {clarification.conflict_type.value}")
            print(f"Q: {clarification.question_text}")
            print("Options:")
            for choice in clarification.choices:
                print(f"  [{choice.id}] {choice.content}")
            
            # 4. Simulate API Output
            print("\n>>> API JSON OUTPUT <<<")
            print(json.dumps(clarification.to_api_format(), indent=2))
        else:
            print("Intent clear. Proceeding with execution.")

    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except Exception as e:
        print(f"Unexpected Error: {e}")