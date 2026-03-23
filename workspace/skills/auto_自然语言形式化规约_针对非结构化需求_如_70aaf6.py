"""
Module: auto_nl_formal_spec
A robust Python module designed to map unstructured natural language requirements
to formal, structured specifications (DSL/Schema).

This module acts as a bridge between human intent and machine-executable constraints,
specifically focusing on 'Implicit Knowledge Extraction' (e.g., mapping 'fast' to
specific numerical parameters).

Author: AGI System Core
Version: 1.0.0
"""

import logging
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum

# --- Configuration & Setup ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DomainContext(Enum):
    """Enumeration of supported domains for context-aware extraction."""
    GAME_DEV = "game_development"
    WEB_API = "web_api"
    DATA_PROCESSING = "data_processing"
    GENERIC = "generic"

@dataclass
class FormalSpecification:
    """
    Data structure representing the formal specification output.
    """
    intent: str
    constraints: Dict[str, Any]
    logic_schema: Dict[str, str]
    ambiguity_warnings: List[str]
    confidence_score: float

# --- Core Functions ---

def extract_implicit_constraints(
    raw_requirement: str, 
    domain: DomainContext = DomainContext.GENERIC,
    custom_mappings: Optional[Dict[str, Dict[str, Any]]] = None
) -> FormalSpecification:
    """
    Analyzes natural language to extract explicit parameters from implicit descriptions.

    This function simulates the LLM's reasoning process (Chain of Thought) where vague
    adjectives are mapped to specific technical parameters based on domain context.

    Args:
        raw_requirement (str): The unstructured user input (e.g., "Make a fast snake game").
        domain (DomainContext): The context domain to apply specific heuristic rules.
        custom_mappings (Optional[Dict]): Override or augment default mapping rules.

    Returns:
        FormalSpecification: A structured object containing constraints and logic.

    Raises:
        ValueError: If input is empty or not a string.

    Example:
        >>> spec = extract_implicit_constraints(
        ...     "Create a snake game that runs very fast", 
        ...     DomainContext.GAME_DEV
        ... )
        >>> print(spec.constraints['frame_rate'])
        60
    """
    # Input Validation
    if not raw_requirement or not isinstance(raw_requirement, str):
        logger.error("Invalid input provided: Input must be a non-empty string.")
        raise ValueError("Input requirement must be a non-empty string.")

    logger.info(f"Processing requirement for domain: {domain.value}")
    
    # Normalize text
    normalized_text = raw_requirement.lower().strip()
    
    # Initialize logic schema (pre-condition, post-condition, invariant)
    logic_schema = {
        "pre_condition": "System initialized",
        "post_condition": "Task completed successfully",
        "invariant": "System stability maintained"
    }
    
    constraints: Dict[str, Any] = {}
    warnings: List[str] = []
    confidence = 0.5 # Base confidence

    # Load Domain-Specific Heuristics (Simulating Retrieval Augmented Generation)
    mapping_rules = _load_domain_heuristics(domain)
    if custom_mappings:
        mapping_rules.update(custom_mappings)

    # --- NLP Extraction Logic (Simulated) ---
    
    # 1. Intent Extraction
    # In a real AGI system, this would be an embedding lookup or LLM generation.
    intent = "undefined_action"
    if "game" in normalized_text:
        intent = "create_game_instance"
        logic_schema["pre_condition"] = "Game engine loaded"
    
    # 2. Constraint Resolution (The core 'Formalization' step)
    # Mapping qualitative terms to quantitative values
    
    # Handle 'Speed/Performance' keywords
    if any(word in normalized_text for word in ["fast", "quick", "speedy", "rapid"]):
        if domain == DomainContext.GAME_DEV:
            constraints["frame_rate"] = 60  # Standard high-performance FPS
            constraints["speed_coefficient"] = 1.5
            logic_schema["invariant"] = "frame_delta_time < 0.017s"
            confidence += 0.2
            logger.debug("Mapped 'fast' to Game Dev constraints (60 FPS, 1.5x Speed).")
        elif domain == DomainContext.WEB_API:
            constraints["timeout_ms"] = 100
            constraints["caching_strategy"] = "redis_high_availability"
            confidence += 0.2
            logger.debug("Mapped 'fast' to Web API constraints (100ms timeout).")

    # Handle 'Safety/Stability' keywords
    elif any(word in normalized_text for word in ["stable", "safe", "robust"]):
        constraints["exception_handling"] = "strict"
        constraints["logging_level"] = "DEBUG"
        logic_schema["invariant"] = "transaction_atomicity = True"
        confidence += 0.2
    
    # Handle 'Scale/Volume' keywords
    if "big" in normalized_text or "large" in normalized_text:
        constraints["memory_allocation"] = "dynamic_high"
        warnings.append("Ambiguous term 'big' interpreted as high memory profile.")
    
    # 3. Boundary Checks & Validation
    if "frame_rate" in constraints:
        if constraints["frame_rate"] > 120:
            warnings.append("Frame rate > 120 may cause physics instability in some engines.")
            constraints["physics_substeps"] = 2 # Auto-correction

    # Final Confidence Calculation
    confidence = min(max(confidence, 0.0), 1.0) # Clamp 0-1
    
    return FormalSpecification(
        intent=intent,
        constraints=constraints,
        logic_schema=logic_schema,
        ambiguity_warnings=warnings,
        confidence_score=round(confidence, 2)
    )

def generate_dsl_representation(spec: FormalSpecification, dsl_type: str = "json") -> str:
    """
    Converts the internal FormalSpecification object into a specific
    Domain Specific Language (DSL) format or schema representation.

    Args:
        spec (FormalSpecification): The specification object derived from NL.
        dsl_type (str): Target format ('json', 'yaml', 'z_schema').

    Returns:
        str: The formatted specification string.
    
    Example:
        >>> spec = extract_implicit_constraints("fast api", DomainContext.WEB_API)
        >>> dsl = generate_dsl_representation(spec, "json")
        >>> print(dsl)
        {"spec": {...}}
    """
    logger.info(f"Generating DSL representation: {dsl_type}")
    
    if not isinstance(spec, FormalSpecification):
        raise TypeError("Input must be a FormalSpecification instance")

    if dsl_type == "json":
        return json.dumps(asdict(spec), indent=2)
    
    elif dsl_type == "z_schema":
        # Simulating a Z-Notation style schema output
        schema_lines = [
            f"┌──────────────────────────────────────┐",
            f"│ Schema: {spec.intent.upper():<26} │",
            f"├──────────────────────────────────────┤",
            f"│ Constraints:                         │",
        ]
        for k, v in spec.constraints.items():
            schema_lines.append(f"│   {k:<15}: {str(v):<15} │")
        
        schema_lines.append(f"├──────────────────────────────────────┤")
        schema_lines.append(f"│ Invariant: {spec.logic_schema.get('invariant', 'N/A'):<23} │")
        schema_lines.append(f"└──────────────────────────────────────┘")
        return "\n".join(schema_lines)
    
    else:
        logger.warning(f"Unsupported DSL type: {dsl_type}")
        return str(asdict(spec))

# --- Helper Functions ---

def _load_domain_heuristics(domain: DomainContext) -> Dict[str, Any]:
    """
    Helper function to retrieve domain-specific configuration maps.
    In a production environment, this would query a Vector DB or Config service.
    """
    base_map = {
        DomainContext.GAME_DEV: {
            "default_frame_rate": 30,
            "render_engine": "opengl"
        },
        DomainContext.WEB_API: {
            "default_timeout": 3000,
            "protocol": "https"
        },
        DomainContext.DATA_PROCESSING: {
            "batch_size": 1000,
            "format": "parquet"
        }
    }
    return base_map.get(domain, {})

def validate_spec_integrity(spec: FormalSpecification) -> Tuple[bool, List[str]]:
    """
    Post-generation validation to ensure the specification is logically consistent
    and technically feasible.

    Args:
        spec: The specification object to validate.

    Returns:
        A tuple containing (is_valid, list_of_errors).
    """
    errors = []
    
    # Check 1: Intent definition
    if spec.intent == "undefined_action":
        errors.append("Critical: Intent could not be derived from input.")
    
    # Check 2: Constraint Range (Example logic)
    if "frame_rate" in spec.constraints:
        if not (0 < spec.constraints["frame_rate"] <= 240):
            errors.append(f"Invalid frame_rate: {spec.constraints['frame_rate']}")

    # Check 3: Confidence Threshold
    if spec.confidence_score < 0.6:
        errors.append("Low confidence score requires human review.")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.warning(f"Spec validation failed: {errors}")
        
    return is_valid, errors

# --- Main Execution Block ---

if __name__ == "__main__":
    # Example Usage: Simulating an AGI processing a user request
    
    user_request = "帮我做一个贪吃蛇游戏，速度要快"  # "Help me make a snake game, speed must be fast"
    
    print(f"--- Processing Request: '{user_request}' ---")
    
    try:
        # Step 1: Extraction
        formal_spec = extract_implicit_constraints(
            raw_requirement=user_request,
            domain=DomainContext.GAME_DEV
        )
        
        # Step 2: Validation
        is_valid, validation_errors = validate_spec_integrity(formal_spec)
        
        if not is_valid:
            print(f"Validation Warnings: {validation_errors}")
        
        # Step 3: DSL Generation (Z-Schema style)
        dsl_output = generate_dsl_representation(formal_spec, dsl_type="z_schema")
        print("\nGenerated Formal Specification (Z-Style):")
        print(dsl_output)
        
        # Step 4: JSON Export for Machine consumption
        json_output = generate_dsl_representation(formal_spec, dsl_type="json")
        print("\nJSON Output for Downstream Systems:")
        print(json_output)

    except ValueError as ve:
        logger.error(f"Processing Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}", exc_info=True)