"""
Module: semantic_state_anchor.py

This module provides a robust interface for mapping ambiguous natural language
instructions (common in craftsmanship teaching) to concrete, high-dimensional
state-space vectors suitable for robotic control or simulation feedback.

It leverages a Large Language Model (LLM) to interpret qualitative descriptors
(e.g., "a bit thicker", "rougher texture") and projects them onto a normalized
state space vector.

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
Domain: nlp_cognitive
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from pydantic import BaseModel, Field, ValidationError, field_validator

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
DEFAULT_STATE_DIMENSION = 12  # Example: [x, y, z, rot, force, velocity, temp, viscosity, etc.]
VALID_STATE_KEYS = [
    "thickness", "pressure", "speed", "temperature", 
    "viscosity", "roughness", "humidity", "color_intensity"
]

class StateSpaceSchema(BaseModel):
    """Pydantic model for validating the state space definition."""
    dimension: int = Field(gt=0, description="Dimensionality of the state vector")
    bounds: List[Tuple[float, float]] = Field(..., description="Min/Max bounds for each dimension")

    @field_validator('bounds')
    @classmethod
    def check_bounds_length(cls, v, info):
        if 'dimension' in info.data and len(v) != info.data['dimension']:
            raise ValueError(f"Bounds list length {len(v)} must match dimension {info.data['dimension']}")
        return v

class SemanticInterpretation(BaseModel):
    """Structured output from the LLM parsing process."""
    intent: str = Field(..., description="The core intent identified, e.g., 'adjust_thickness'")
    target_state_delta: Dict[str, float] = Field(..., description="Relative changes to state parameters")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in the interpretation")
    ambiguity_detected: bool = Field(default=False)

class LLMInterface:
    """
    Mock Interface for Large Language Model interactions.
    In a production environment, this would call OpenAI, Anthropic, or a local model API.
    """
    
    def generate(self, prompt: str) -> str:
        """
        Simulates an LLM response. 
        In reality, this handles API calls, retries, and token limits.
        """
        # Simulation logic for the purpose of this module
        logger.debug("Sending prompt to LLM...")
        if "thicker" in prompt.lower():
            return json.dumps({
                "intent": "modify_geometry",
                "target_state_delta": {"thickness": 0.2, "pressure": 0.1},
                "confidence": 0.88,
                "ambiguity_detected": False
            })
        elif "feel" in prompt.lower() or "vibe" in prompt.lower():
            return json.dumps({
                "intent": "aesthetic_adjustment",
                "target_state_delta": {"roughness": -0.1, "color_intensity": 0.05},
                "confidence": 0.65,
                "ambiguity_detected": True
            })
        return json.dumps({
            "intent": "unknown",
            "target_state_delta": {},
            "confidence": 0.10,
            "ambiguity_detected": True
        })

def _construct_prompt(user_input: str, current_state: np.ndarray) -> str:
    """
    Helper function to construct a structured prompt for the LLM.
    
    Args:
        user_input (str): The raw natural language from the user.
        current_state (np.ndarray): The current system state vector (normalized).
        
    Returns:
        str: A formatted prompt string.
    """
    # Map current state indices to named parameters for better LLM understanding
    # (Simplified mapping for demonstration)
    state_desc = {
        "thickness": current_state[0] if len(current_state) > 0 else 0.0,
        "pressure": current_state[1] if len(current_state) > 1 else 0.0,
        "roughness": current_state[2] if len(current_state) > 2 else 0.0,
    }
    
    prompt = f"""
    You are an expert craftsmanship assistant. Analyze the user's instruction and map it to 
    physical state changes. The current state is: {json.dumps(state_desc)}.
    
    User Instruction: "{user_input}"
    
    Respond ONLY with valid JSON containing:
    1. "intent": string
    2. "target_state_delta": dict of parameter name to relative change (-1.0 to 1.0)
    3. "confidence": float
    4. "ambiguity_detected": boolean
    """
    return prompt.strip()

def parse_semantic_intent(
    user_input: str, 
    llm_client: LLMInterface
) -> SemanticInterpretation:
    """
    Core Function 1: Detects semantic references and intent in natural language.
    
    This function takes raw text and uses an LLM to extract structured intent 
    and proposed deltas for physical parameters.
    
    Args:
        user_input (str): The user's command (e.g., "Make it feel more organic").
        llm_client (LLMInterface): The interface to the language model.
        
    Returns:
        SemanticInterpretation: A validated data structure of the intent.
        
    Raises:
        ValueError: If user_input is empty.
        RuntimeError: If LLM output cannot be parsed.
    """
    if not user_input or not user_input.strip():
        logger.error("Received empty user input.")
        raise ValueError("User input cannot be empty.")
        
    logger.info(f"Parsing semantic intent for: '{user_input}'")
    
    try:
        # In a real scenario, we might pass current context/state to the prompt
        prompt = _construct_prompt(user_input, np.zeros(DEFAULT_STATE_DIMENSION))
        raw_response = llm_client.generate(prompt)
        
        # Clean and Parse JSON
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not json_match:
            raise RuntimeError("No JSON object found in LLM response")
            
        data = json.loads(json_match.group(0))
        interpretation = SemanticInterpretation(**data)
        
        logger.info(f"Intent parsed successfully: {interpretation.intent}")
        return interpretation
        
    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {e}")
        raise RuntimeError(f"Invalid LLM response structure: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}")
        raise RuntimeError(f"Failed to parse LLM JSON: {e}")

def anchor_to_state_vector(
    interpretation: SemanticInterpretation,
    current_state: np.ndarray,
    bounds: List[Tuple[float, float]]
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Core Function 2: Anchors the semantic intent to a concrete state-space vector.
    
    This maps the high-level intent (e.g., "thicker") to a specific vector delta,
    applies it to the current state, and enforces physical boundary constraints.
    
    Args:
        interpretation (SemanticInterpretation): The parsed intent object.
        current_state (np.ndarray): The current normalized state vector.
        bounds (List[Tuple[float, float]]): Min/Max constraints for each dimension.
        
    Returns:
        Tuple[np.ndarray, Dict]: 
            - The new calculated state vector.
            - A metadata dictionary containing execution details.
            
    Raises:
        ValueError: If state dimensions mismatch.
    """
    if len(current_state) != len(bounds):
        msg = f"Dimension mismatch: State has {len(current_state)}, Bounds have {len(bounds)}"
        logger.error(msg)
        raise ValueError(msg)
        
    logger.info("Anchoring semantic delta to state vector...")
    
    # Create a copy to avoid mutation
    new_state = current_state.copy()
    metadata = {
        "modifications_applied": {},
        "clamping_occurred": False,
        "success": True
    }
    
    # Mapping abstract keys to vector indices (Simplified logic)
    # In a real AGI system, this would use a dynamic config or embedding similarity
    key_to_index = {
        "thickness": 0, 
        "pressure": 1, 
        "roughness": 2,
        "speed": 3,
        "temperature": 4
    }
    
    deltas = interpretation.target_state_delta
    
    for key, delta in deltas.items():
        if key in key_to_index:
            idx = key_to_index[key]
            
            # Apply Scaling Factor based on Confidence
            # Lower confidence -> smaller changes (more cautious robot)
            scaled_delta = delta * interpretation.confidence
            
            original_value = new_state[idx]
            new_val = original_value + scaled_delta
            
            # Boundary Enforcement (Clamping)
            min_b, max_b = bounds[idx]
            if new_val < min_b or new_val > max_b:
                logger.warning(f"Clamping required for index {idx} ({key})")
                metadata["clamping_occurred"] = True
                
            clamped_val = np.clip(new_val, min_b, max_b)
            new_state[idx] = clamped_val
            
            metadata["modifications_applied"][key] = {
                "from": original_value,
                "delta_requested": delta,
                "delta_applied": clamped_val - original_value
            }
        else:
            logger.warning(f"Unknown state key '{key}' received from LLM. Ignoring.")
            
    return new_state, metadata

# --- Main Usage Example ---
if __name__ == "__main__":
    # Setup mock LLM and initial parameters
    llm = LLMInterface()
    initial_vector = np.array([0.5, 0.2, 0.1, 0.0, 0.5] + [0.0]*7) # 12 Dim vector
    state_bounds = [(0.0, 2.0)] * DEFAULT_STATE_DIMENSION # Generic bounds
    
    print("-" * 50)
    print("Scenario: User says 'Make it slightly thicker'")
    print("-" * 50)
    
    try:
        # Step 1: Semantic Parsing
        intent = parse_semantic_intent("Make it slightly thicker", llm)
        print(f"Parsed Intent: {intent}")
        
        # Step 2: State Anchoring
        new_vector, meta = anchor_to_state_vector(intent, initial_vector, state_bounds)
        
        print(f"\nOriginal State (first 5): {initial_vector[:5]}")
        print(f"New State (first 5):      {new_vector[:5]}")
        print(f"Metadata: {json.dumps(meta, indent=2)}")
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")