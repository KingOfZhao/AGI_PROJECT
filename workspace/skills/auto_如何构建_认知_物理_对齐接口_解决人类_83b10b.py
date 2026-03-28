"""
Module: cognitive_physical_alignment.py

This module provides a robust interface for aligning human cognitive inputs (fuzzy language)
with physical system parameters (precise execution parameters). It acts as a semantic
translation layer, resolving the ambiguity of human instructions into machine-executable
ranges based on specific contexts.

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
Domain: Human-Computer Interaction (HCI)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class PhysicalParameter:
    """
    Represents a precise physical parameter range or value.
    
    Attributes:
        min_val (float): Minimum bound of the parameter.
        max_val (float): Maximum bound of the parameter.
        unit (str): The unit of measurement (e.g., 'celsius', 'rpm').
    """
    min_val: float
    max_val: float
    unit: str

    def __post_init__(self):
        if self.min_val > self.max_val:
            raise ValueError(f"Min value {self.min_val} cannot exceed Max value {self.max_val}")

@dataclass
class SemanticMapping:
    """
    Represents a mapping entry from a fuzzy concept to a physical parameter.
    Supports context-specific overrides.
    """
    concept: str
    default_range: Tuple[float, float]
    unit: str
    context_overrides: Dict[str, Tuple[float, float]] = field(default_factory=dict)

# --- Core Classes ---

class CognitivePhysicalInterface:
    """
    The core interface for translating fuzzy human instructions into precise physical parameters.
    
    This class maintains a dynamic dictionary (knowledge base) of semantic mappings and
    handles the resolution logic based on the provided context.
    """

    def __init__(self):
        self._knowledge_base: Dict[str, SemanticMapping] = {}
        self._load_default_knowledge()
        logger.info("Cognitive-Physical Interface initialized.")

    def _load_default_knowledge(self) -> None:
        """Preloads the system with common sense mappings (The 'Dynamic Dictionary')."""
        # Cooking Context
        self.add_mapping(
            concept="大火",
            default_range=(200.0, 250.0),
            unit="celsius",
            context_overrides={"烤箱": (220.0, 250.0), "炒菜": (1800, 2200)}
        )
        self.add_mapping(
            concept="小火",
            default_range=(80.0, 120.0),
            unit="celsius",
            context_overrides={"烤箱": (100.0, 150.0), "炖煮": (500, 800)}
        )
        
        # Mechanical Context
        self.add_mapping(
            concept="高转速",
            default_range=(3000, 5000),
            unit="rpm"
        )
        self.add_mapping(
            concept="一点点",
            default_range=(0.1, 10.0),
            unit="grams"
        )
        logger.debug(f"Loaded {len(self._knowledge_base)} default semantic mappings.")

    def add_mapping(
        self, 
        concept: str, 
        default_range: Tuple[float, float], 
        unit: str, 
        context_overrides: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> None:
        """
        Adds or updates a semantic mapping in the knowledge base.
        
        Args:
            concept: The fuzzy keyword (e.g., '火候大一点').
            default_range: The default (min, max) tuple.
            unit: The physical unit.
            context_overrides: Optional dictionary mapping specific contexts to different ranges.
        """
        if not concept or not unit:
            raise ValueError("Concept and Unit cannot be empty.")
        
        if len(default_range) != 2 or default_range[0] > default_range[1]:
            raise ValueError("Default range must be a tuple (min, max) where min <= max.")

        self._knowledge_base[concept] = SemanticMapping(
            concept=concept,
            default_range=default_range,
            unit=unit,
            context_overrides=context_overrides or {}
        )
        logger.info(f"Updated mapping for concept: '{concept}'")

    def translate(
        self, 
        fuzzy_input: str, 
        current_context: Optional[str] = None
    ) -> PhysicalParameter:
        """
        Core Function 1: Translates fuzzy natural language into a PhysicalParameter object.
        
        This method performs the lookup, handles context resolution, and ensures data validity.
        
        Args:
            fuzzy_input: The raw human input string.
            current_context: The current operating context (e.g., '烤箱', '汽车').
            
        Returns:
            PhysicalParameter: The precise machine instruction.
            
        Raises:
            ValueError: If the input cannot be mapped to a known concept.
        """
        if not isinstance(fuzzy_input, str):
            raise TypeError(f"Expected string input, got {type(fuzzy_input)}")

        # Normalize input
        clean_input = self._preprocess_text(fuzzy_input)
        
        # 1. Semantic Matching (Simple matching for demo, AGI would use embeddings)
        matched_mapping = None
        for concept, mapping in self._knowledge_base.items():
            if concept in clean_input:
                matched_mapping = mapping
                break
        
        if not matched_mapping:
            logger.warning(f"Unrecognized cognitive concept: '{fuzzy_input}'")
            raise ValueError(f"无法识别的认知概念: '{fuzzy_input}'")

        # 2. Context Resolution
        final_range = matched_mapping.default_range
        
        if current_context and current_context in matched_mapping.context_overrides:
            override = matched_mapping.context_overrides[current_context]
            final_range = override
            logger.debug(f"Context '{current_context}' applied. Range updated to {final_range}")
        
        # 3. Boundary Check & Safety Validation
        min_val, max_val = final_range
        if not self._validate_safety_bounds(matched_mapping.unit, min_val, max_val):
             logger.error(f"Safety boundary violation for {fuzzy_input} in context {current_context}")
             raise ValueError("Calculated parameters exceed safety limits.")

        return PhysicalParameter(
            min_val=min_val,
            max_val=max_val,
            unit=matched_mapping.unit
        )

    def _preprocess_text(self, text: str) -> str:
        """
        Helper Function: Cleans and normalizes input text.
        Removes punctuation and converts to lowercase for better matching.
        """
        # Remove special characters, keep spaces and alphanumeric
        cleaned = re.sub(r'[^\w\s]', '', text)
        return cleaned.lower().strip()

    def _validate_safety_bounds(self, unit: str, min_val: float, max_val: float) -> bool:
        """
        Core Function 2: Validates parameters against physical safety limits.
        
        Prevents the system from generating dangerous parameters (e.g., Temperature > 1000C).
        
        Args:
            unit: The unit of measurement.
            min_val: Proposed min value.
            max_val: Proposed max value.
            
        Returns:
            bool: True if safe, False otherwise.
        """
        # Hard limits for safety
        SAFETY_LIMITS = {
            "celsius": (-50.0, 500.0), # General cooking/electronic limits
            "rpm": (0.0, 10000.0),
            "watts": (0.0, 3000.0)
        }

        if unit in SAFETY_LIMITS:
            sys_min, sys_max = SAFETY_LIMITS[unit]
            if min_val < sys_min or max_val > sys_max:
                logger.error(f"Safety Check Failed: {min_val}-{max_val} {unit} exceeds system limits ({sys_min}-{sys_max}).")
                return False
        
        return True

# --- Usage Example ---

if __name__ == "__main__":
    # Initialize the interface
    interface = CognitivePhysicalInterface()
    
    print("--- AGI Cognitive-Physical Alignment Test ---")
    
    # Scenario 1: Cooking with Oven
    fuzzy_cmd_1 = "请把火调大一点" # "Make the fire bigger"
    context_1 = "烤箱" # Oven
    
    try:
        param_1 = interface.translate(fuzzy_cmd_1, context_1)
        print(f"\nInput: '{fuzzy_cmd_1}' (Context: {context_1})")
        print(f"Output: {param_1.min_val} - {param_1.max_val} {param_1.unit}")
    except ValueError as e:
        print(f"Error: {e}")

    # Scenario 2: Cooking with Stove (Different Context)
    fuzzy_cmd_2 = "大火" # "Big Fire"
    context_2 = "炒菜" # Stir fry
    
    try:
        param_2 = interface.translate(fuzzy_cmd_2, context_2)
        print(f"\nInput: '{fuzzy_cmd_2}' (Context: {context_2})")
        # Note: The mapping for '大火' in '炒菜' context is defined as (1800, 2200) Watts/RPM equivalent
        print(f"Output: {param_2.min_val} - {param_2.max_val} {param_2.unit}")
    except ValueError as e:
        print(f"Error: {e}")

    # Scenario 3: Ambiguous input without context
    fuzzy_cmd_3 = "小火"
    
    try:
        param_3 = interface.translate(fuzzy_cmd_3, current_context=None)
        print(f"\nInput: '{fuzzy_cmd_3}' (Context: Default)")
        print(f"Output: {param_3.min_val} - {param_3.max_val} {param_3.unit}")
    except ValueError as e:
        print(f"Error: {e}")

    # Scenario 4: Dynamic Learning - Adding a new skill
    print("\n[Dynamic Learning] Adding '飞速' for electric drills...")
    interface.add_mapping("飞速", (2400, 3000), "rpm")
    
    param_4 = interface.translate("拧得飞速", "电钻")
    print(f"New Skill Output: {param_4.min_val} - {param_4.max_val} {param_4.unit}")