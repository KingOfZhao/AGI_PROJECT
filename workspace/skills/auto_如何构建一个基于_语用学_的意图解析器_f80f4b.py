"""
Pragmatic Intent Parser Module.

This module implements a pragmatic intent parser designed to distinguish between
'stating facts' (assertives) and 'issuing commands' (directives) based on 
Pragmatics and Speech Act Theory. It combines NLP analysis with contextual 
modal logic to map natural language into system state change signals (Delta State).

Key Components:
- Modality Analysis: Determines the illocutionary force of the text.
- Context Integration: Uses environmental state (e.g., current temperature) to resolve ambiguity.
- State Delta Generation: Converts validated intent into executable system signals.
"""

import logging
import re
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple, Any

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PragmaticIntentParser")

class IntentCategory(Enum):
    """Enumeration of Speech Act categories relevant to AGI processing."""
    ASSERTIVE = auto()   # Stating facts (e.g., "The sky is blue")
    DIRECTIVE = auto()   # Commands or requests (e.g., "Open the door")
    COMMITMENT = auto()  # Promises (e.g., "I will do it")
    DECLARATION = auto() # Changing status by words (e.g., "I quit")
    UNKNOWN = auto()

class SystemSignal:
    """
    Represents a state change signal (Delta State) to be sent to the AGI core.
    """
    def __init__(self, action: str, parameters: Dict[str, Any], confidence: float):
        self.action = action
        self.parameters = parameters
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"<SystemSignal action={self.action} params={self.parameters} conf={self.confidence:.2f}>"

class ContextEnvironment:
    """
    Mock class representing the AGI's internal state and environmental sensors.
    """
    def __init__(self, current_temp: float = 24.0, ac_status: bool = False):
        self.current_temp = current_temp
        self.ac_status = ac_status # False = Off, True = On

    def get_state(self) -> Dict[str, Any]:
        return {
            "temperature": self.current_temp,
            "ac_active": self.ac_status
        }

class PragmaticIntentParser:
    """
    Parses natural language inputs into structured intents based on pragmatic context.
    
    This parser uses a hybrid approach:
    1. Syntactic analysis (keyword/heuristic patterns).
    2. Pragmatic validation (checking context fit).
    
    Attributes:
        context (ContextEnvironment): The current environmental state.
    """

    def __init__(self, context: Optional[ContextEnvironment] = None):
        """Initialize the parser with a specific context or a default one."""
        self.context = context if context else ContextEnvironment()
        logger.info("PragmaticIntentParser initialized with context: %s", self.context.get_state())

    def _analyze_modality(self, text: str) -> Tuple[IntentCategory, float]:
        """
        Internal helper to determine the base modality of the text using heuristics.
        
        In a full AGI system, this would use an LLM or a fine-tuned transformer.
        
        Args:
            text (str): The input utterance.
            
        Returns:
            Tuple[IntentCategory, float]: The detected category and initial confidence.
        """
        text = text.lower().strip()
        
        # Heuristic patterns for Directives
        directive_patterns = [
            r"^(please|pls|kindly)\s",
            r"\b(turn|set|make|open|close|delete|create|stop|start)\b.*\b(to|down|up|on|off)\b",
            r"^(can you|could you|would you)", # Interrogative directives
            r"^go\sahead"
        ]
        
        # Heuristic patterns for Assertives
        assertive_patterns = [
            r"^it is\s",
            r"^i am\s",
            r"^the\s\w+\sis\s",
            r"\b(weather|temperature|status)\s(is|looks)\b"
        ]

        for pattern in directive_patterns:
            if re.search(pattern, text):
                return IntentCategory.DIRECTIVE, 0.7

        for pattern in assertive_patterns:
            if re.search(pattern, text):
                return IntentCategory.ASSERTIVE, 0.8

        # Fallback heuristic: Imperative verbs usually come first
        # (Simplified check for this demonstration)
        first_word = text.split()[0] if text else ""
        imperative_verbs = ["put", "take", "bring", "call", "fix", "change"]
        if first_word in imperative_verbs:
            return IntentCategory.DIRECTIVE, 0.6

        return IntentCategory.UNKNOWN, 0.1

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """
        Helper to extract entities (slots) from text.
        """
        params = {}
        # Regex for temperature detection
        temp_match = re.search(r"(\d+(\.\d+)?)\s*(degrees|celsius|c)?", text.lower())
        if temp_match:
            params['target_value'] = float(temp_match.group(1))
            
        # Regex for device state
        if re.search(r"\b(on|start)\b", text):
            params['power'] = True
        elif re.search(r"\b(off|stop)\b", text):
            params['power'] = False
            
        # Directional adjustment
        if re.search(r"\b(lower|down|decrease|cooler)\b", text):
            params['direction'] = -1
        elif re.search(r"\b(higher|up|increase|warmer)\b", text):
            params['direction'] = 1
            
        return params

    def parse_to_signal(self, user_input: str) -> Optional[SystemSignal]:
        """
        Core function: Parses raw text into a SystemSignal (Delta State).
        
        This function orchestrates the parsing pipeline:
        1. Modality Analysis (Syntactic/Semantic).
        2. Contextual Pragmatic Filtering.
        3. Signal Generation.
        
        Args:
            user_input (str): The raw natural language string.
            
        Returns:
            Optional[SystemSignal]: A structured signal object if actionable, else None.
            
        Raises:
            ValueError: If input is empty or invalid type.
        """
        if not isinstance(user_input, str) or not user_input.strip():
            logger.error("Invalid input received: Input must be a non-empty string.")
            raise ValueError("Input must be a non-empty string.")

        logger.info(f"Parsing input: '{user_input}'")
        
        # Step 1: Base Modality Analysis
        category, confidence = self._analyze_modality(user_input)
        logger.debug(f"Initial Modality: {category.name} (Conf: {confidence})")

        # Step 2: Pragmatic Context Integration
        # Example: "It is hot" (Assertive) -> Context Check -> Convert to Directive (Turn on AC)
        # This simulates "Implicit Intent" recognition.
        
        current_context = self.context.get_state()
        params = self._extract_parameters(user_input)
        
        # Pragmatic Logic:
        # If the user states a fact about the environment that deviates from comfort norms,
        # and the system has the capability to fix it, treat as an Implicit Directive.
        if category == IntentCategory.ASSERTIVE:
            if "hot" in user_input.lower() and current_context['temperature'] > 25:
                logger.info("Pragmatic shift: Assertive 'Hot' interpreted as Directive 'Cool down'.")
                category = IntentCategory.DIRECTIVE
                params['direction'] = -1 # Implicit direction
                confidence = 0.65 # Lower confidence than explicit command
            elif "cold" in user_input.lower() and current_context['temperature'] < 20:
                logger.info("Pragmatic shift: Assertive 'Cold' interpreted as Directive 'Warm up'.")
                category = IntentCategory.DIRECTIVE
                params['direction'] = 1
                confidence = 0.65

        # Step 3: Signal Generation (only for Directives)
        if category != IntentCategory.DIRECTIVE:
            logger.info(f"Input categorized as {category.name}. No system signal generated.")
            return None

        # Validation of Parameters
        if not params:
            logger.warning("Directive detected, but no actionable parameters found.")
            # In a real system, this might trigger a clarification request sub-signal
            return None

        # Construct the Delta State
        action_type = "ADJUST_ENVIRONMENT"
        
        # Refine Parameters based on Context (Boundary Check)
        # If user says "Turn down AC" but AC is already off, signal might differ
        if params.get('direction') and not current_context['ac_active']:
            logger.warning("AC is off. Implicitly including 'Power On' in signal.")
            params['power'] = True

        return SystemSignal(
            action=action_type,
            parameters=params,
            confidence=confidence
        )

def run_diagnostics():
    """
    Standalone function to demonstrate module usage and capabilities.
    """
    print("--- Initializing Pragmatic Intent Parser ---")
    # Setup a specific context: It's currently 28 degrees (Hot)
    env = ContextEnvironment(current_temp=28.0, ac_status=False)
    parser = PragmaticIntentParser(context=env)

    test_cases = [
        "今天天气很热",             # Assertive, should trigger Implicit Directive due to context
        "把空调调低",               # Explicit Directive
        "Please turn the AC to 24", # Explicit Directive with Parameter
        "The sky is blue",          # Pure Assertive, no action
        "",                         # Error handling case
    ]

    print("\n--- Processing Test Cases ---")
    for text in test_cases:
        try:
            print(f"\nInput: {text}")
            signal = parser.parse_to_signal(text)
            if signal:
                print(f"Result: {signal}")
            else:
                print("Result: No actionable signal (Informational only)")
        except ValueError as ve:
            print(f"Result: Error - {ve}")
        except Exception as e:
            logger.exception("Unexpected error during parsing.")

if __name__ == "__main__":
    run_diagnostics()