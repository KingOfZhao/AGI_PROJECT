"""
Module: auto_fuzzy_intent_interaction_layer.py
Description: Advanced AGI skill module for fusing fuzzy user intent (gestures) 
             with precise CAD logic. Translates loose screen interactions into 
             geometrically constrained engineering parameters.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
from typing import List, Tuple, Dict, Optional, Any, Union
from dataclasses import dataclass, field

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FuzzyIntentCAD")

# --- Data Structures ---

@dataclass
class GestureInput:
    """
    Represents raw input from the user gesture.
    
    Attributes:
        stroke_points: List of (x, y) coordinates representing the drawn path.
        bounding_box: Tuple of (min_x, min_y, max_x, max_y) defining the rough area.
        context_tags: Optional metadata (e.g., 'structural', 'electrical').
    """
    stroke_points: List[Tuple[float, float]]
    bounding_box: Tuple[float, float, float, float]
    context_tags: List[str] = field(default_factory=list)

@dataclass
class EngineeringParameter:
    """
    Represents the precise engineering output derived from intent.
    
    Attributes:
        primitive_type: Type of CAD primitive (e.g., 'line', 'circle', 'beam').
        coordinates: Precise start and end points or center/radius.
        constraints: List of applied geometric constraints (e.g., 'horizontal', 'tangent').
        metadata: Additional engineering properties.
    """
    primitive_type: str
    coordinates: Dict[str, Any]
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

# --- Custom Exceptions ---

class IntentProcessingError(Exception):
    """Custom exception for errors during intent analysis."""
    pass

class SolverFailureError(Exception):
    """Custom exception for geometric solver failures."""
    pass

# --- Helper Functions ---

def _validate_gesture_data(gesture: GestureInput) -> bool:
    """
    Validates the input gesture data integrity and boundaries.
    
    Args:
        gesture: The GestureInput object to validate.
        
    Returns:
        True if valid.
        
    Raises:
        ValueError: If data is malformed or empty.
    """
    if not gesture.stroke_points:
        raise ValueError("Stroke points cannot be empty.")
    
    if len(gesture.bounding_box) != 4:
        raise ValueError("Bounding box must contain 4 float values (x1, y1, x2, y2).")
        
    min_x, min_y, max_x, max_y = gesture.bounding_box
    if min_x > max_x or min_y > max_y:
        raise ValueError("Invalid bounding box coordinates: min cannot be greater than max.")
        
    logger.debug(f"Gesture data validated: {len(gesture.stroke_points)} points.")
    return True

def _calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# --- Core Functions ---

def analyze_fuzzy_intent(gesture: GestureInput, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Core Function 1: Analyzes the fuzzy gesture to predict user intent.
    Uses heuristics to determine if the user wants to draw a line, select an area, etc.
    
    Args:
        gesture: Validated GestureInput data.
        context: System context (existing objects on screen).
        
    Returns:
        A dictionary containing the classified intent and geometric features.
        
    Raises:
        IntentProcessingError: If intent cannot be determined.
    """
    _validate_gesture_data(gesture)
    logger.info("Analyzing fuzzy intent...")
    
    points = gesture.stroke_points
    start_point = points[0]
    end_point = points[-1]
    
    # Basic Heuristics for Intent Classification
    total_length = sum(
        _calculate_distance(points[i], points[i+1]) 
        for i in range(len(points)-1)
    )
    direct_dist = _calculate_distance(start_point, end_point)
    
    # Aspect ratio of bounding box
    min_x, min_y, max_x, max_y = gesture.bounding_box
    width = max_x - min_x
    height = max_y - min_y
    aspect_ratio = width / (height + 1e-5) # Avoid div by zero

    intent_data = {
        "raw_start": start_point,
        "raw_end": end_point,
        "centroid": ((min_x + max_x) / 2, (min_y + max_y) / 2),
        "features": {}
    }

    # Logic: If path is straight enough, intent is 'alignment' or 'line_creation'
    # If path is closed or circular, intent is 'area_selection' or 'hole'
    
    if direct_dist < 50 and total_length > 200:
        intent_data["type"] = "closed_shape"
        intent_data["features"]["estimated_center"] = intent_data["centroid"]
        logger.info("Intent classified: Closed Shape / Selection")
    else:
        intent_data["type"] = "alignment_or_path"
        intent_data["features"]["angle"] = math.atan2(
            end_point[1] - start_point[1], 
            end_point[0] - start_point[0]
        )
        logger.info("Intent classified: Alignment / Path")

    return intent_data

def geometric_constraint_solver(
    intent_data: Dict[str, Any], 
    tolerance: float = 0.1
) -> EngineeringParameter:
    """
    Core Function 2: Converts fuzzy intent into precise CAD parameters.
    Simulates a constraint solver (like SketchSolve or OpenCASCADE adapter).
    
    Args:
        intent_data: The output from analyze_fuzzy_intent.
        tolerance: Geometric tolerance for snapping.
        
    Returns:
        An EngineeringParameter object with precise coordinates.
        
    Raises:
        SolverFailureError: If constraints are unsolvable.
    """
    logger.info(f"Invoking Geometric Solver with tolerance {tolerance}...")
    
    try:
        intent_type = intent_data.get("type", "unknown")
        raw_start = intent_data["raw_start"]
        raw_end = intent_data["raw_end"]
        
        if intent_type == "alignment_or_path":
            # Auto-Snap Logic: Snap to nearest 5 units or grid
            snapped_start = (
                round(raw_start[0] / 5) * 5,
                round(raw_start[1] / 5) * 5
            )
            snapped_end = (
                round(raw_end[0] / 5) * 5,
                round(raw_end[1] / 5) * 5
            )
            
            # Auto-Constraint Logic: Force Horizontal or Vertical if close enough
            constraints = []
            dx = abs(snapped_end[0] - snapped_start[0])
            dy = abs(snapped_end[1] - snapped_start[1])
            
            if dx > dy * 2:
                snapped_end = (snapped_end[0], snapped_start[1]) # Flatten Y
                constraints.append("horizontal")
                logger.debug("Applied constraint: Horizontal")
            elif dy > dx * 2:
                snapped_end = (snapped_start[0], snapped_end[1]) # Flatten X
                constraints.append("vertical")
                logger.debug("Applied constraint: Vertical")
            else:
                constraints.append("fixed_angle")

            return EngineeringParameter(
                primitive_type="line_segment",
                coordinates={"start": snapped_start, "end": snapped_end},
                constraints=constraints,
                metadata={"source": "fuzzy_gesture"}
            )
            
        elif intent_type == "closed_shape":
            # Simplify to a bounding box or circle
            center = intent_data["features"]["estimated_center"]
            radius = _calculate_distance(raw_start, raw_end) / 2
            
            return EngineeringParameter(
                primitive_type="circle",
                coordinates={"center": center, "radius": radius},
                constraints=["fixed_center"],
                metadata={"source": "fuzzy_gesture"}
            )
        else:
            raise SolverFailureError("Unknown intent type for solver.")

    except KeyError as e:
        logger.error(f"Missing key in intent data: {e}")
        raise SolverFailureError(f"Invalid input data structure: {e}")
    except Exception as e:
        logger.critical(f"Unexpected solver error: {e}")
        raise SolverFailureError("Solver crashed.")

# --- Main Orchestration ---

def process_gesture_to_cad(gesture: GestureInput) -> EngineeringParameter:
    """
    Orchestrates the flow from raw gesture to precise parameter.
    """
    try:
        # Step 1: Validation
        _validate_gesture_data(gesture)
        
        # Step 2: Intent Analysis
        intent = analyze_fuzzy_intent(gesture)
        
        # Step 3: Solver & Parameterization
        params = geometric_constraint_solver(intent)
        
        logger.info("Successfully generated CAD parameters from fuzzy gesture.")
        return params
    except (ValueError, IntentProcessingError, SolverFailureError) as e:
        logger.warning(f"Failed to process gesture: {e}")
        # Return a null object or re-raise depending on system design
        raise

# --- Usage Example ---

if __name__ == "__main__":
    # Example: User draws a sloppy line roughly horizontally
    sloppy_stroke = [(10, 10), (15, 11), (50, 9), (100, 12)]
    bbox = (10, 9, 100, 12) # minx, miny, maxx, maxy
    
    user_input = GestureInput(
        stroke_points=sloppy_stroke, 
        bounding_box=bbox
    )
    
    try:
        print("-" * 30)
        print("Processing User Gesture...")
        result = process_gesture_to_cad(user_input)
        
        print("-" * 30)
        print("Resulting Engineering Parameter:")
        print(f"Type: {result.primitive_type}")
        print(f"Coords: {result.coordinates}")
        print(f"Constraints: {result.constraints}")
        
    except Exception as e:
        print(f"Error: {e}")