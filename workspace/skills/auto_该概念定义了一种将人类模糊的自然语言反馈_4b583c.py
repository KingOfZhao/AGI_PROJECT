"""
Module: intent_compiler.py
Description: A semantic compilation engine that translates abstract human feedback
             into structured system parameters. It serves as a bridge between
             fuzzy natural language and precise executable configurations.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackCategory(Enum):
    """Enumeration for categorized feedback types."""
    UNCLEAR = "unclear"
    PARAM_ADJUSTMENT = "param_adjustment"
    STYLE_CHANGE = "style_change"
    STRUCTURAL_CHANGE = "structural_change"

@dataclass
class SystemParameter:
    """Represents a structured system parameter."""
    key: str
    value: Any
    min_bound: Optional[float] = None
    max_bound: Optional[float] = None
    value_type: type = float

    def validate(self) -> bool:
        """Validates the parameter value against bounds and type."""
        if not isinstance(self.value, self.value_type):
            try:
                # Attempt type coercion
                self.value = self.value_type(self.value)
            except (ValueError, TypeError):
                logger.error(f"Type mismatch for {self.key}: expected {self.value_type}, got {type(self.value)}")
                return False

        if self.min_bound is not None and self.value < self.min_bound:
            logger.warning(f"Value {self.value} for {self.key} below min bound {self.min_bound}. Clamping.")
            self.value = self.min_bound
        if self.max_bound is not None and self.value > self.max_bound:
            logger.warning(f"Value {self.value} for {self.key} above max bound {self.max_bound}. Clamping.")
            self.value = self.max_bound
        
        return True

@dataclass
class MVPQuestion:
    """Minimum Viable Product Question for Human Feedback Loop."""
    question_id: str
    content: str
    suggested_options: List[str]
    target_parameter: str

class IntentCompiler:
    """
    Translates fuzzy natural language feedback into precise system parameters.
    
    This class acts as a semantic compiler, parsing abstract concepts (like 'more entropy')
    and mapping them to concrete configuration changes. It also generates MVP (Minimum
    Viable Product) questions to disambiguate complex requests.
    """

    def __init__(self, config_schema: Dict[str, Dict[str, Any]]):
        """
        Initialize the compiler with a parameter schema.
        
        Args:
            config_schema: Dictionary defining valid parameters, their types, and bounds.
                           Example: {'temperature': {'type': float, 'min': 0.0, 'max': 1.0}}
        """
        self._schema = config_schema
        self._feedback_history: List[Dict[str, Any]] = []
        logger.info("IntentCompiler initialized with schema.")

    def parse_fuzzy_feedback(self, feedback_text: str, current_state: Dict[str, Any]) -> Tuple[FeedbackCategory, Dict[str, Any]]:
        """
        Core Function 1: Analyzes natural language to determine intent and category.
        
        Args:
            feedback_text: The raw natural language input from the user.
            current_state: The current system configuration context.
            
        Returns:
            A tuple containing the detected category and a dictionary of extracted entities.
            
        Raises:
            ValueError: If feedback_text is empty.
        """
        if not feedback_text or not feedback_text.strip():
            logger.error("Empty feedback received.")
            raise ValueError("Feedback text cannot be empty.")

        logger.info(f"Parsing feedback: '{feedback_text}'")
        
        # Basic semantic analysis (mock logic for demonstration)
        feedback_lower = feedback_text.lower()
        entities: Dict[str, Any] = {}
        category = FeedbackCategory.UNCLEAR

        # Pattern matching for intents
        if "increase" in feedback_lower or "more" in feedback_lower:
            direction = 1.0
        elif "decrease" in feedback_lower or "less" in feedback_lower:
            direction = -1.0
        else:
            direction = 0.0

        # Mapping abstract concepts to parameters
        if "creative" in feedback_lower or "random" in feedback_lower:
            entities['target_param'] = 'temperature'
            entities['adjustment'] = direction * 0.1
            category = FeedbackCategory.PARAM_ADJUSTMENT
        elif "precise" in feedback_lower or "strict" in feedback_lower:
            entities['target_param'] = 'temperature'
            entities['adjustment'] = direction * 0.1 # direction would be negative here usually
            category = FeedbackCategory.PARAM_ADJUSTMENT
        elif "simpler" in feedback_lower:
            entities['target_param'] = 'complexity_depth'
            entities['adjustment'] = -1
            category = FeedbackCategory.STRUCTURAL_CHANGE
        else:
            category = FeedbackCategory.UNCLEAR
            entities['raw_text'] = feedback_text

        # Log the parsing result
        self._feedback_history.append({
            'input': feedback_text,
            'category': category,
            'extracted': entities
        })

        return category, entities

    def compile_to_parameters(self, category: FeedbackCategory, entities: Dict[str, Any]) -> List[SystemParameter]:
        """
        Core Function 2: Converts parsed intent into validated SystemParameter objects.
        
        Args:
            category: The categorized intent.
            entities: Extracted information from the parse phase.
            
        Returns:
            A list of SystemParameter objects ready for system application.
        """
        compiled_params: List[SystemParameter] = []
        
        if category == FeedbackCategory.UNCLEAR:
            logger.warning("Cannot compile unclear feedback to parameters.")
            return []

        target_key = entities.get('target_param')
        adjustment = entities.get('adjustment', 0)
        
        if target_key and target_key in self._schema:
            schema_def = self._schema[target_key]
            
            # In a real system, we would fetch the current value from the system state
            # Here we simulate a base value for calculation
            current_val = 0.5  # Mock current value
            
            new_val = current_val + adjustment
            
            param = SystemParameter(
                key=target_key,
                value=new_val,
                min_bound=schema_def.get('min'),
                max_bound=schema_def.get('max'),
                value_type=schema_def.get('type', float)
            )
            
            if param.validate():
                compiled_params.append(param)
                logger.info(f"Compiled parameter: {param.key} = {param.value}")
            else:
                logger.error(f"Validation failed for parameter {target_key}")
        else:
            logger.warning(f"Target parameter '{target_key}' not found in schema.")

        return compiled_params

    def generate_mvp_question(self, unclear_text: str) -> MVPQuestion:
        """
        Auxiliary Function: Generates a clarifying question (MVP) for ambiguous input.
        
        Args:
            unclear_text: The text that failed to parse into concrete parameters.
            
        Returns:
            An MVPQuestion object to prompt the user.
        """
        logger.info(f"Generating MVP question for: {unclear_text}")
        
        # Simple heuristic to suggest options based on keywords
        options = ["Adjust Logic", "Modify Output Format", "Change Tone", "Cancel"]
        
        return MVPQuestion(
            question_id=f"mvp_{len(self._feedback_history)}",
            content=f"I didn't quite understand '{unclear_text}'. Did you mean to:",
            suggested_options=options,
            target_parameter="user_intent_clarification"
        )

    def apply_parameters(self, params: List[SystemParameter]) -> Dict[str, Any]:
        """
        Simulates applying the parameters to the system.
        
        Returns:
            A dictionary representing the delta state.
        """
        state_update = {}
        for p in params:
            state_update[p.key] = p.value
        logger.info(f"System state updated with: {state_update}")
        return state_update

# --- Usage Example and Demonstration ---

def main():
    """Demonstration of the IntentCompiler workflow."""
    
    # 1. Define the system schema
    system_schema = {
        'temperature': {'type': float, 'min': 0.0, 'max': 1.0},
        'complexity_depth': {'type': int, 'min': 1, 'max': 10},
        'output_format': {'type': str}
    }

    # 2. Initialize Compiler
    compiler = IntentCompiler(system_schema)

    # Case A: Clear Intent
    print("\n--- Processing Clear Intent ---")
    feedback_a = "I need the output to be much more creative."
    cat_a, ent_a = compiler.parse_fuzzy_feedback(feedback_a, {})
    params_a = compiler.compile_to_parameters(cat_a, ent_a)
    
    if params_a:
        compiler.apply_parameters(params_a)
    else:
        print("No parameters compiled.")

    # Case B: Ambiguous Intent requiring MVP
    print("\n--- Processing Ambiguous Intent ---")
    feedback_b = "This feels weird." # Very ambiguous
    cat_b, ent_b = compiler.parse_fuzzy_feedback(feedback_b, {})
    
    if cat_b == FeedbackCategory.UNCLEAR:
        mvp = compiler.generate_mvp_question(feedback_b)
        print(f"System Question: {mvp.content}")
        print(f"Options: {mvp.suggested_options}")

if __name__ == "__main__":
    main()