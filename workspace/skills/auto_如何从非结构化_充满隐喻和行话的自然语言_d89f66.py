"""
Module: abstract_constraint_parser.py
Description: A semantic parser module for AGI systems designed to translate abstract,
             metaphorical, and jargon-heavy natural language into quantifiable
             physical constraint parameters (e.g., kinematics, dynamics).

             It maps linguistic abstractions (e.g., "势如破竹", "行云流水") to
             structured mathematical boundaries (mean, variance, min, max).

Author: Senior Python Engineer (AGI Division)
License: MIT
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Configure Module-Level Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class ConstraintCategory(Enum):
    """Enumeration of physical constraint categories."""
    KINEMATICS = "kinematics"  # Movement characteristics
    DYNAMICS = "dynamics"      # Force characteristics
    SPATIAL = "spatial"        # Geometry characteristics

@dataclass
class PhysicalParameter:
    """Represents a quantifiable physical parameter with bounds."""
    name: str
    category: ConstraintCategory
    unit: str
    mean_target: float
    tolerance: float  # +/- from mean
    min_val: float
    max_val: float
    description: str

    def __post_init__(self):
        """Validate data integrity after initialization."""
        if self.min_val > self.max_val:
            raise ValueError(f"Min value {self.min_val} cannot exceed Max value {self.max_val}")
        if not (self.min_val <= self.mean_target <= self.max_val):
            logger.warning(f"Mean target {self.mean_target} is outside min/max bounds for {self.name}.")

@dataclass
class SemanticMapping:
    """Mapping between a semantic concept and physical parameters."""
    concept_key: str
    intensity_modifier: float  # 0.0 to 2.0 (normalized)
    parameters: List[PhysicalParameter]

# --- Knowledge Base (Mock Database) ---

KNOWLEDGE_BASE: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    # Concept -> {param_name: (mean, min, max)}
    "势如破竹": {
        "velocity": (8.5, 5.0, 15.0),  # High speed
        "momentum": (0.9, 0.8, 1.0),   # High continuity
        "resistance": (0.1, 0.0, 0.3)  # Low friction/resistance
    },
    "行云流水": {
        "velocity": (3.0, 1.0, 6.0),    # Moderate, consistent speed
        "jerk": (0.1, 0.0, 0.5),        # Low jerk (smoothness)
        "path_curvature": (0.8, 0.6, 1.0) # High fluidity in turns
    },
    "举重若轻": {
        "load_factor": (0.4, 0.1, 0.6), # Perceived weight
        "tremor": (0.05, 0.0, 0.1),     # Low vibration
        "precision": (0.95, 0.9, 1.0)   # High accuracy
    },
    "jittery": {
        "velocity": (0.2, 0.0, 0.8),
        "jerk": (5.0, 2.0, 10.0),       # High jerk
        "precision": (0.4, 0.1, 0.6)
    }
}

INTENSITY_KEYWORDS = {
    "非常": 1.5,
    "极其": 1.8,
    "略微": 0.6,
    "有点": 0.7,
    "super": 1.6,
    "slightly": 0.7
}

# --- Helper Functions ---

def _preprocess_text(text: str) -> Tuple[str, float]:
    """
    Cleans input text and extracts intensity modifiers.
    
    Args:
        text: Raw input string (e.g., "非常势如破竹").
        
    Returns:
        A tuple of (cleaned_concept_key, intensity_multiplier).
    """
    logger.debug(f"Preprocessing text: {text}")
    text = text.strip().lower()
    intensity = 1.0
    
    # Check for intensity modifiers
    for keyword, mult in INTENSITY_KEYWORDS.items():
        if text.startswith(keyword):
            intensity = mult
            text = text[len(keyword):].strip()
            logger.info(f"Detected intensity modifier '{keyword}' with factor {mult}")
            break
            
    # Simple punctuation removal
    text = re.sub(r'[^\w\s]', '', text)
    return text, intensity

def _scale_parameter(param_data: Tuple[float, float, float], intensity: float) -> PhysicalParameter:
    """
    Scales a parameter based on intensity and wraps it in a data object.
    
    Args:
        param_data: Tuple of (mean, min, max).
        intensity: Multiplier for the mean target.
        
    Returns:
        PhysicalParameter object.
    """
    mean_base, min_val, max_val = param_data
    
    # Calculate new target based on intensity, clamped by physical limits
    target = mean_base * intensity
    target = max(min_val, min(max_val, target))
    
    # Calculate tolerance (heuristic: 10% of range or based on intensity)
    tolerance = (max_val - min_val) * 0.1
    
    return PhysicalParameter(
        name="unknown", # Will be overwritten
        category=ConstraintCategory.KINEMATICS,
        unit="unitless",
        mean_target=target,
        tolerance=tolerance,
        min_val=min_val,
        max_val=max_val,
        description="Generated from abstract semantic mapping"
    )

# --- Core Functions ---

def extract_parameters_from_concept(concept_text: str) -> Optional[SemanticMapping]:
    """
    Core Function 1: Extracts physical constraints from a single abstract concept.
    
    Parses the text, looks up the semantic definition in the knowledge base,
    applies intensity modifiers, and returns a structured mapping.
    
    Args:
        concept_text: The natural language description (e.g., "势如破竹").
        
    Returns:
        SemanticMapping object if successful, None otherwise.
        
    Raises:
        ValueError: If input is empty or invalid.
    """
    if not concept_text or not isinstance(concept_text, str):
        logger.error("Invalid input: Input must be a non-empty string.")
        raise ValueError("Input must be a non-empty string.")

    clean_key, intensity = _preprocess_text(concept_text)
    
    logger.info(f"Looking up concept: '{clean_key}' with intensity {intensity}")
    
    if clean_key not in KNOWLEDGE_BASE:
        logger.warning(f"Concept '{clean_key}' not found in semantic knowledge base.")
        return None
        
    raw_params = KNOWLEDGE_BASE[clean_key]
    param_list: List[PhysicalParameter] = []
    
    for p_name, p_vals in raw_params.items():
        try:
            param = _scale_parameter(p_vals, intensity)
            param.name = p_name
            
            # Logic to assign units and categories based on name heuristics
            if "velocity" in p_name or "speed" in p_name:
                param.unit = "m/s"
                param.category = ConstraintCategory.KINEMATICS
            elif "jerk" in p_name or "tremor" in p_name:
                param.unit = "m/s^3"
                param.category = ConstraintCategory.KINEMATICS
            elif "precision" in p_name:
                param.unit = "score (0-1)"
                param.category = ConstraintCategory.SPATIAL
                
            param_list.append(param)
            logger.debug(f"Mapped parameter: {p_name} -> Target: {param.mean_target}")
            
        except Exception as e:
            logger.error(f"Error processing parameter {p_name}: {e}")
            continue

    return SemanticMapping(
        concept_key=clean_key,
        intensity_modifier=intensity,
        parameters=param_list
    )

def generate_control_constraints(
    mapping: SemanticMapping, 
    hard_limits: Dict[str, Tuple[float, float]]
) -> Dict[str, Dict[str, float]]:
    """
    Core Function 2: Converts semantic mapping into a finalized control dictionary.
    
    Merges the abstract constraints with system hard limits (safety boundaries)
    to produce a machine-readable constraint set.
    
    Args:
        mapping: The SemanticMapping object derived from text.
        hard_limits: System safety limits {param_name: (min, max)}.
        
    Returns:
        A dictionary structured for control systems:
        {
            "velocity": {"target": 8.0, "min": 5.0, "max": 10.0},
            ...
        }
    """
    if not mapping or not mapping.parameters:
        logger.warning("Empty mapping provided to constraint generator.")
        return {}

    final_constraints = {}
    
    for param in mapping.parameters:
        # Safety Check: Merge with Hard Limits
        sys_min, sys_max = hard_limits.get(param.name, (param.min_val, param.max_val))
        
        # Calculate final bounds: Intersection of Semantic and System bounds
        final_min = max(param.min_val, sys_min)
        final_max = min(param.max_val, sys_max)
        
        if final_min > final_max:
            logger.error(f"Safety conflict for {param.name}: Semantic bounds [{param.min_val}, {param.max_val}] "
                         f"conflict with System bounds [{sys_min}, {sys_max}]. Skipping parameter.")
            continue
            
        # Clamp target to final bounds
        final_target = max(final_min, min(final_max, param.mean_target))
        
        constraint_set = {
            "target": round(final_target, 4),
            "min": round(final_min, 4),
            "max": round(final_max, 4),
            "unit": param.unit,
            "priority": 1.0 if param.category == ConstraintCategory.SAFETY else 0.8
        }
        
        final_constraints[param.name] = constraint_set
        logger.info(f"Generated constraint for {param.name}: {constraint_set}")
        
    return final_constraints

# --- Main Execution Example ---

if __name__ == "__main__":
    # Setup basic logging for demo
    logging.basicConfig(level=logging.INFO)
    
    print("-" * 50)
    print("AGI Skill: Abstract Constraint Parser")
    print("-" * 50)

    # Example 1: Parsing a Chinese idiom
    input_text = "非常势如破竹" # "Very unstoppable/smashing bamboo"
    print(f"\nAnalyzing Input: '{input_text}'")
    
    try:
        # Step 1: Extract semantic mapping
        semantic_map = extract_parameters_from_concept(input_text)
        
        if semantic_map:
            print(f"Concept: {semantic_map.concept_key}")
            print(f"Intensity: {semantic_map.intensity_modifier}")
            
            # Step 2: Generate control constraints with safety limits
            # Hypothetical safety limits for the robot/agent
            system_safety_limits = {
                "velocity": (0.0, 12.0), # Cap velocity at 12 m/s for safety
                "momentum": (0.0, 0.95),
                "resistance": (0.0, 1.0)
            }
            
            control_params = generate_control_constraints(semantic_map, system_safety_limits)
            
            print("\nGenerated Control Parameters:")
            for k, v in control_params.items():
                print(f"  - {k}: {v}")
                
    except Exception as e:
        logger.exception(f"Execution failed: {e}")

    # Example 2: Parsing a jargon term
    input_text_2 = "slightly jittery"
    print(f"\nAnalyzing Input: '{input_text_2}'")
    
    map_2 = extract_parameters_from_concept(input_text_2)
    if map_2:
        constraints_2 = generate_control_constraints(map_2, {}) # No extra safety limits
        print("\nGenerated Control Parameters:")
        for k, v in constraints_2.items():
            print(f"  - {k}: {v}")