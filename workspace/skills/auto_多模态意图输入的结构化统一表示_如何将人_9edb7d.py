"""
Module: multimodal_intent_unification.py

This module provides a robust framework for transforming fuzzy, multi-modal human inputs
(such as voice, sketches, or screenshots) into a unified, machine-executable Intermediate
Representation (IR). It addresses semantic ambiguity through normalization, validation,
and contextual slot filling.

Author: Advanced Python Engineer (AGI System Component)
Version: 1.0.0
License: MIT
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, TypedDict, Literal
from pydantic import BaseModel, Field, ValidationError, root_validator

# --- Configuration & Setup ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class ModalityInput(BaseModel):
    """Represents raw input from a specific modality."""
    type: Literal['text', 'voice', 'sketch', 'screenshot']
    content: Union[str, bytes]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    class Config:
        arbitrary_types_allowed = True

class SlotEntity(BaseModel):
    """Represents a extracted semantic entity/slot."""
    name: str
    value: Any
    source: str  # Which modality provided this
    confidence: float

class UnifiedIntentIR(BaseModel):
    """
    The Unified Intermediate Representation (IR).
    
    This schema defines the contract between the input perception layer
    and the execution/planning layer of the AGI system.
    """
    intent_id: str
    primary_action: str
    parameters: Dict[str, Any]
    resolved_slots: List[SlotEntity]
    ambiguity_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    raw_input_hash: str

# --- Helper Functions ---

def _normalize_text_input(text: str) -> str:
    """
    Helper function to clean and normalize raw text strings.
    
    Removes extra whitespace, converts to lowercase, and handles basic
    punctuation.
    
    Args:
        text (str): The raw input string.
        
    Returns:
        str: The normalized string.
    """
    if not isinstance(text, str):
        return ""
    
    # Remove special characters often resulting from ASR (Automatic Speech Recognition)
    cleaned = re.sub(r'[^\w\s.,!?]', '', text)
    # Normalize whitespace
    normalized = ' '.join(cleaned.split()).lower()
    logger.debug(f"Normalized text: '{text}' -> '{normalized}'")
    return normalized

def _hash_input_data(inputs: List[ModalityInput]) -> str:
    """
    Generates a deterministic hash for the input combination for tracking.
    """
    import hashlib
    data_string = "".join([f"{inp.type}:{inp.confidence}:" for inp in inputs])
    return hashlib.md5(data_string.encode()).hexdigest()

# --- Core Logic ---

class MultimodalIntegrator:
    """
    Core class responsible for fusing multiple input modalities and
    resolving semantic ambiguities into a structured IR.
    """

    def __init__(self):
        self.action_keywords = {
            'create': ['make', 'generate', 'create', 'draw', 'build'],
            'edit': ['change', 'modify', 'edit', 'update', 'resize'],
            'delete': ['remove', 'delete', 'erase', 'clear']
        }
        logger.info("MultimodalIntegrator initialized.")

    def extract_semantic_slots(self, inputs: List[ModalityInput]) -> List[SlotEntity]:
        """
        Core Function 1: Extracts semantic entities (slots) from various inputs.
        
        Analyzes text, voice transcripts, or visual labels to identify key
        parameters like color, size, object names, etc.
        
        Args:
            inputs (List[ModalityInput]): List of raw modality inputs.
            
        Returns:
            List[SlotEntity]: A list of extracted slots with confidence scores.
        
        Raises:
            ValueError: If inputs are empty or invalid.
        """
        if not inputs:
            raise ValueError("Input list cannot be empty.")

        extracted_slots = []
        
        for inp in inputs:
            if inp.type in ['text', 'voice']:
                # Assuming voice is transcribed to text in content
                content = _normalize_text_input(str(inp.content))
                
                # Simple keyword extraction logic (simulated NLP)
                if 'red' in content:
                    extracted_slots.append(SlotEntity(
                        name='color', value='red', source=inp.type, confidence=0.9
                    ))
                if 'blue' in content:
                    extracted_slots.append(SlotEntity(
                        name='color', value='blue', source=inp.type, confidence=0.9
                    ))
                
                # Number extraction
                numbers = re.findall(r'\b\d+\b', content)
                for num in numbers:
                    extracted_slots.append(SlotEntity(
                        name='quantity', value=int(num), source=inp.type, confidence=0.95
                    ))

            elif inp.type == 'sketch':
                # Simulated processing of sketch metadata
                # In a real scenario, this would call a CV model
                if 'bbox' in inp.metadata:
                    extracted_slots.append(SlotEntity(
                        name='spatial_reference', 
                        value=inp.metadata['bbox'], 
                        source='sketch', 
                        confidence=0.7
                    ))
        
        logger.info(f"Extracted {len(extracted_slots)} semantic slots.")
        return extracted_slots

    def generate_unified_ir(
        self, 
        inputs: List[ModalityInput], 
        context: Optional[Dict[str, Any]] = None
    ) -> UnifiedIntentIR:
        """
        Core Function 2: Generates the final Unified Intermediate Representation.
        
        Fuses the inputs and extracted slots to determine the primary action
        and resolve conflicts (e.g., text says "red" but sketch looks blue).
        
        Args:
            inputs (List[ModalityInput]): Raw inputs.
            context (Optional[Dict]): Contextual data (e.g., user history).
            
        Returns:
            UnifiedIntentIR: The structured intent object ready for execution.
        """
        logger.info("Starting IR generation process...")
        
        # 1. Validate inputs
        try:
            validated_inputs = [ModalityInput(**inp) for inp in inputs]
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise ValueError(f"Invalid input data format: {e}")

        # 2. Extract Slots
        slots = self.extract_semantic_slots(validated_inputs)
        
        # 3. Determine Primary Action
        # Prioritize explicit text/voice commands over implied sketch actions
        primary_action = "unknown"
        max_confidence = 0.0
        
        for inp in validated_inputs:
            if inp.type in ['text', 'voice']:
                content = _normalize_text_input(str(inp.content))
                for action, keywords in self.action_keywords.items():
                    if any(kw in content for kw in keywords):
                        # Simple heuristic: first match wins if confidence is high
                        if inp.confidence > max_confidence:
                            primary_action = action
                            max_confidence = inp.confidence

        # 4. Resolve Parameters (Conflict Resolution)
        # If multiple colors are mentioned, we pick the one with highest confidence
        params = {}
        color_slots = [s for s in slots if s.name == 'color']
        if color_slots:
            best_color = max(color_slots, key=lambda x: x.confidence)
            params['color'] = best_color.value
        
        spatial_slots = [s for s in slots if s.name == 'spatial_reference']
        if spatial_slots:
            params['location'] = spatial_slots[0].value

        # 5. Calculate Ambiguity Score
        # Higher score if action is unknown or conflicting slots exist
        ambiguity = 0.0
        if primary_action == "unknown":
            ambiguity = 0.9
        elif len(color_slots) > 1:
            ambiguity += 0.2 # Conflicting signals
        
        # 6. Construct IR
        ir = UnifiedIntentIR(
            intent_id=f"intent_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            primary_action=primary_action,
            parameters=params,
            resolved_slots=slots,
            ambiguity_score=ambiguity,
            raw_input_hash=_hash_input_data(validated_inputs)
        )
        
        logger.info(f"IR Generated: Action={primary_action}, Ambiguity={ambiguity}")
        return ir

# --- Main Execution (Example Usage) ---

if __name__ == "__main__":
    # Example Usage demonstrating mixed modality input (Voice + Sketch)
    
    print("--- Multimodal Intent Unification Example ---")
    
    # 1. Initialize the Integrator
    integrator = MultimodalIntegrator()
    
    # 2. Prepare raw inputs
    # User says: "Make this red" (Voice)
    # User draws: A circle on a canvas (Sketch)
    raw_inputs = [
        {
            "type": "voice",
            "content": "Make this red",  # Transcribed text
            "confidence": 0.88,
            "metadata": {"language": "en-US"}
        },
        {
            "type": "sketch",
            "content": b"<binary_stroke_data>", # Raw binary data
            "confidence": 0.95,
            "metadata": {
                "shape_type": "circle",
                "bbox": {"x": 100, "y": 150, "w": 50, "h": 50}
            }
        }
    ]
    
    # 3. Generate Unified IR
    try:
        unified_ir = integrator.generate_unified_ir(raw_inputs)
        
        # 4. Output the result (Formatted JSON)
        print("\nGenerated Unified Intermediate Representation (IR):")
        print(unified_ir.json(indent=2))
        
        print("\nExtracted Parameters:")
        for key, value in unified_ir.parameters.items():
            print(f" - {key}: {value}")
            
    except Exception as e:
        logger.error(f"Failed to process intent: {e}")