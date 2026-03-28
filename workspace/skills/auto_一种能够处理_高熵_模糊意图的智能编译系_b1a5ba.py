"""
Module: IntentCompiler
A high-level intelligent compilation system designed to resolve high-entropy, 
ambiguous human intents into low-entropy, machine-executable logic (IR).

This system introduces the concept of 'Cognitive Friction' detection and 
uses a structured interaction protocol to minimize entropy through user dialogue.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentCompiler")

# 2. Data Structures and Enums

class IntentEntropyLevel(Enum):
    """Categorization of intent ambiguity."""
    LOW = 1.0       # Clear, directly executable
    MEDIUM = 0.5    # Requires simple parameter filling
    HIGH = 0.1      # "Fuzzy Core" detected, requires structural disambiguation

@dataclass
class UserIntent:
    """Represents the raw or processed user intent."""
    raw_text: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    entropy_score: float = 1.0  # Default to high entropy (0.0 = low, 1.0 = max)

@dataclass
class IntermediateRepresentation:
    """The low-entropy, machine-executable logic structure."""
    action: str
    parameters: Dict[str, Any]
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize the IR to JSON for execution."""
        return json.dumps(self.__dict__, indent=2)

@dataclass
class ClarificationRequest:
    """Structured object to guide the user towards 'noise reduction'."""
    focus_area: str
    options: List[Tuple[str, str]]  # (Option ID, Description)
    question: str

class AmbiguityError(Exception):
    """Custom exception for unresolved ambiguities."""
    pass

# 3. Core System Class

class AutoCompiler:
    """
    The core compiler that transforms fuzzy natural language into structured IR.
    It simulates the 'Cognitive Friction' detection and interactive resolution process.
    """

    def __init__(self, knowledge_base: Optional[Dict] = None):
        """
        Initialize the compiler.
        
        Args:
            knowledge_base (Optional[Dict]): Domain knowledge for context awareness.
        """
        self.knowledge_base = knowledge_base if knowledge_base else {}
        logger.info("AutoCompiler initialized with Session ID: %s", uuid.uuid4())

    def _calculate_entropy(self, text: str) -> float:
        """
        [Helper] Analyzes text to determine the 'Fuzzy Core' magnitude.
        
        This is a heuristic simulation. In a real AGI system, this would involve
        semantic vector analysis or probabilistic parsing.
        
        Args:
            text (str): The input natural language.
            
        Returns:
            float: Entropy score between 0.0 (Clear) and 1.0 (Chaotic).
        """
        # Heuristic: Check for specific "vague" keywords
        vague_keywords = ["something", "maybe", "sort of", "fast", "nice", "good", "it"]
        
        entropy = 0.0
        if not text or len(text) < 5:
            entropy = 1.0
        else:
            # Simple keyword matching for simulation
            for kw in vague_keywords:
                if kw in text.lower():
                    entropy += 0.2
            
            # Penalize lack of specific nouns/verbs (very basic simulation)
            if len(text.split()) < 3:
                entropy += 0.4

        # Boundary Check
        return min(max(0.0, entropy), 1.0)

    def detect_fuzzy_core(self, intent: UserIntent) -> Tuple[IntentEntropyLevel, List[str]]:
        """
        [Core Function 1] Identifies the specific areas of cognitive friction.
        
        Args:
            intent (UserIntent): The user's raw intent object.
            
        Returns:
            Tuple[IntentEntropyLevel, List[str]]: The severity level and a list of missing/ambiguous slots.
        """
        logger.info(f"Analyzing intent entropy for: '{intent.raw_text}'")
        score = self._calculate_entropy(intent.raw_text)
        intent.entropy_score = score
        
        missing_slots = []
        
        if score > 0.7:
            level = IntentEntropyLevel.HIGH
            missing_slots = ["Core Action", "Target Object", "Context"]
            logger.warning("HIGH ENTROPY detected: Fuzzy core requires structural guidance.")
        elif score > 0.3:
            level = IntentEntropyLevel.MEDIUM
            missing_slots = ["Specific Parameter"]
            logger.info("MEDIUM ENTROPY: Need clarification on parameters.")
        else:
            level = IntentEntropyLevel.LOW
            logger.info("LOW ENTROPY: Intent is clear.")
            
        return level, missing_slots

    def generate_clarification_protocol(self, missing_slots: List[str]) -> ClarificationRequest:
        """
        [Core Function 2] Constructs an interactive protocol to reduce noise.
        
        Instead of guessing, it asks the user to refine the structure.
        
        Args:
            missing_slots (List[str]): The identified ambiguous elements.
            
        Returns:
            ClarificationRequest: A structured object to drive the UI interaction.
        """
        if "Core Action" in missing_slots:
            return ClarificationRequest(
                focus_area="Action",
                question="I detected a general desire, but what specific action do you want to perform?",
                options=[
                    ("A", "Analyze Data"),
                    ("B", "Generate Report"),
                    ("C", "Execute System Command")
                ]
            )
        elif "Specific Parameter" in missing_slots:
            return ClarificationRequest(
                focus_area="Parameters",
                question="Please specify the target for the operation.",
                options=[
                    ("A", "Current Directory"),
                    ("B", "Home Directory"),
                    ("C", "Custom Path")
                ]
            )
        
        # Fallback
        return ClarificationRequest(
            focus_area="General",
            question="Could you please rephrase that with more detail?",
            options=[]
        )

    def compile_to_ir(self, intent: UserIntent, user_selection: Optional[str] = None) -> IntermediateRepresentation:
        """
        [Core Function 3] Finalizes the compilation process.
        
        Transforms the clarified intent into a deterministic Intermediate Representation.
        
        Args:
            intent (UserIntent): The original intent.
            user_selection (Optional[str]): The ID of the option chosen by the user during interaction.
            
        Returns:
            IntermediateRepresentation: The executable logic object.
            
        Raises:
            AmbiguityError: If the intent remains high-entropy after interaction.
        """
        # Validation: If entropy is still high, reject compilation
        if intent.entropy_score > 0.6 and user_selection is None:
            logger.error("Compilation failed: Unresolved high entropy.")
            raise AmbiguityError("Intent remains ambiguous. Interaction required.")

        # Simulation of Logic Synthesis
        # In a real system, this maps the text + selection to a function call graph.
        
        action_map = {
            "A": "data.analyze",
            "B": "report.generate",
            "C": "system.exec"
        }
        
        # Default to 'generic.process' if no selection made but entropy was low
        final_action = action_map.get(user_selection, "generic.process")
        
        logger.info(f"Compiling to IR -> Action: {final_action}")
        
        return IntermediateRepresentation(
            action=final_action,
            parameters={
                "source_text": intent.raw_text,
                "timestamp": "2023-10-27T10:00:00Z" # Placeholder
            },
            confidence=1.0 - intent.entropy_score,
            context={"session": intent.session_id}
        )

# 4. Usage Example
if __name__ == "__main__":
    # Initialize System
    compiler = AutoCompiler()

    # Scenario 1: High Entropy Input
    raw_input = "I want to do something with the files..."
    user_intent = UserIntent(raw_text=raw_input)

    print(f"\n>>> User Input: {raw_input}")

    # Step 1: Detect Fuzzy Core
    entropy_level, missing = compiler.detect_fuzzy_core(user_intent)

    # Step 2: Interactive Resolution (Simulated Loop)
    if entropy_level != IntentEntropyLevel.LOW:
        print(f"    [System] Detected {entropy_level.name} entropy.")
        clarification = compiler.generate_clarification_protocol(missing)
        
        print(f"    [System Question] {clarification.question}")
        for opt_id, desc in clarification.options:
            print(f"      [{opt_id}] {desc}")
            
        # Simulate User Choosing 'A'
        simulated_choice = 'A'
        print(f"    >>> User Selection: {simulated_choice}")
        
        # Step 3: Compile to IR
        try:
            ir = compiler.compile_to_ir(user_intent, user_selection=simulated_choice)
            print("\n>>> Compilation Successful. Generated IR:")
            print(ir.to_json())
        except AmbiguityError as e:
            print(f"Error: {e}")

    # Scenario 2: Low Entropy Input
    print("\n------------------------------------------------")
    raw_input_2 = "Delete the temporary logs immediately."
    user_intent_2 = UserIntent(raw_text=raw_input_2)
    print(f"\n>>> User Input: {raw_input_2}")
    
    level_2, _ = compiler.detect_fuzzy_core(user_intent_2)
    
    if level_2 == IntentEntropyLevel.LOW:
        ir_2 = compiler.compile_to_ir(user_intent_2)
        print("\n>>> Compilation Successful (Direct). Generated IR:")
        print(ir_2.to_json())