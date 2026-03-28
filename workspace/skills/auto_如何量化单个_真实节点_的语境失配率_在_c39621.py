"""
Module: auto_context_mismatch_quantifier
Name: auto_如何量化单个_真实节点_的语境失配率_在_c39621

Description:
This module implements an algorithm to quantify the "Context Mismatch Rate" for
a specific 'Real Node' within an AGI cognitive system.

It addresses the need to detect when a node is activated but its predefined
preconditions (temporal, spatial, object state) conflict with the current
environment. By comparing node metadata constraints against real-time
perception data, it calculates an 'Environment Viability Score'.

This score helps identify obsolete or rigid knowledge units that require
updates or deprecation.

Author: Senior Python Engineer (AGI Systems)
Domain: agi_cognition
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContextMismatchQuantifier")

class ConstraintType(Enum):
    """Enumeration of possible constraint types for a node."""
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    STATE = "state"

@dataclass
class NodeMetadata:
    """Represents the constraints and metadata of a cognitive node."""
    node_id: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    activation_count: int = 0
    mismatch_count: int = 0

@dataclass
class EnvironmentContext:
    """Represents the current real-time perception data."""
    timestamp: datetime
    location: Tuple[float, float]  # (latitude, longitude)
    detected_objects: Dict[str, Any]  # e.g., {'cup': 'full', 'door': 'open'}
    
class ContextMismatchError(Exception):
    """Custom exception for errors during mismatch calculation."""
    pass

def validate_inputs(node: NodeMetadata, context: EnvironmentContext) -> None:
    """
    Helper function to validate input data structures.
    
    Args:
        node: The node metadata object.
        context: The current environment context.
        
    Raises:
        ContextMismatchError: If inputs are invalid or malformed.
    """
    if not node.node_id:
        raise ContextMismatchError("Node ID cannot be empty.")
    if not isinstance(context.location, tuple) or len(context.location) != 2:
        raise ContextMismatchError("Location must be a tuple of (lat, lon).")
    if not isinstance(context.detected_objects, dict):
        raise ContextMismatchError("Detected objects must be a dictionary.")
    
    # Boundary checks for coordinates
    lat, lon = context.location
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ContextMismatchError(f"Invalid coordinates: {context.location}")

    logger.debug(f"Inputs validated for Node {node.node_id}")

def check_temporal_constraint(
    constraint_value: Dict[str, str], 
    current_time: datetime
) -> bool:
    """
    Checks if the current time falls within the allowed time window.
    
    Args:
        constraint_value: Dict with 'start' and 'end' keys in 'HH:MM' format.
        current_time: The current datetime object.
        
    Returns:
        True if the constraint is satisfied, False otherwise.
    """
    try:
        start_str = constraint_value.get("start")
        end_str = constraint_value.get("end")
        
        if not start_str or not end_str:
            return True # No valid constraint defined
            
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        current_t = current_time.time()
        
        if start_time < end_time:
            return start_time <= current_t <= end_time
        else: # Handles overnight time ranges e.g., 22:00 to 04:00
            return current_t >= start_time or current_t <= end_time
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid time format in constraint: {e}")
        return True # Fail open or closed depending on policy, here Fail Open

def check_spatial_constraint(
    constraint_value: Dict[str, float], 
    current_coords: Tuple[float, float]
) -> bool:
    """
    Checks if the current location is within the allowed radius.
    
    Args:
        constraint_value: Dict with 'lat', 'lon', and 'radius_km'.
        current_coords: Current (lat, lon).
        
    Returns:
        True if within radius, False otherwise.
    """
    # Using a simplified Euclidean approximation for distance for this logic snippet
    # In production, Haversine formula should be used for spherical distance
    try:
        target_lat = constraint_value["lat"]
        target_lon = constraint_value["lon"]
        radius = constraint_value["radius_km"]
        
        # Approx 111km per degree of latitude
        lat_diff = (current_coords[0] - target_lat) * 111
        # Cosine correction for longitude
        avg_lat = (current_coords[0] + target_lat) / 2
        lon_diff = (current_coords[1] - target_lon) * (111 * abs(abs(avg_lat) - 90) / 90)
        
        distance = (lat_diff**2 + lon_diff**2)**0.5
        
        return distance <= radius
    except KeyError:
        logger.warning("Spatial constraint missing required fields (lat, lon, radius_km)")
        return True

def calculate_environment_viability(
    node: NodeMetadata, 
    current_context: EnvironmentContext
) -> float:
    """
    Core Function: Calculates the real-time viability score of a node 
    based on current environment constraints.
    
    Algorithm:
    1. Iterate through all defined constraints in the node metadata.
    2. Compare against real-time context.
    3. Return a normalized score (0.0 to 1.0) representing the match ratio.
    
    Args:
        node: The cognitive node containing constraints.
        current_context: The real-time environmental data.
        
    Returns:
        float: A score between 0.0 (Total Mismatch) and 1.0 (Perfect Match).
    """
    try:
        validate_inputs(node, current_context)
    except ContextMismatchError as e:
        logger.error(f"Validation failed: {e}")
        return 0.0

    constraints = node.constraints
    if not constraints:
        return 1.0 # No constraints means always viable

    passed_checks = 0
    total_checks = 0
    
    for key, value in constraints.items():
        total_checks += 1
        is_satisfied = False
        
        try:
            if key.startswith("time_"):
                is_satisfied = check_temporal_constraint(value, current_context.timestamp)
            elif key.startswith("loc_"):
                is_satisfied = check_spatial_constraint(value, current_context.location)
            elif key.startswith("state_"):
                # Direct state comparison
                object_key = value.get("object")
                required_state = value.get("required_state")
                actual_state = current_context.detected_objects.get(object_key)
                is_satisfied = (actual_state == required_state)
            else:
                # Unknown constraint type, assume pass or handle specifically
                is_satisfied = True
                logger.info(f"Unknown constraint type encountered: {key}")
                
        except Exception as e:
            logger.error(f"Error checking constraint '{key}': {e}")
            is_satisfied = False # Treat errors as mismatches for safety

        if is_satisfied:
            passed_checks += 1

    viability = passed_checks / total_checks if total_checks > 0 else 1.0
    logger.info(f"Node {node.node_id} viability calculated: {viability:.2f}")
    return viability

def update_node_mismatch_stats(
    node: NodeMetadata, 
    viability_score: float, 
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Core Function: Updates the node's statistical records based on the viability score.
    
    If viability is below the threshold, it increments the mismatch count.
    It also updates the rolling mismatch rate.
    
    Args:
        node: The node object to update.
        viability_score: The score returned by calculate_environment_viability.
        threshold: The cutoff score for considering a node 'mismatched'.
        
    Returns:
        A summary dictionary containing the updated status.
    """
    node.activation_count += 1
    
    if viability_score < threshold:
        node.mismatch_count += 1
        logger.warning(f"Node {node.node_id} context mismatch detected! Score: {viability_score}")
    
    current_rate = node.mismatch_count / node.activation_count
    
    # Return a report structure
    report = {
        "node_id": node.node_id,
        "current_viability": viability_score,
        "total_activations": node.activation_count,
        "total_mismatches": node.mismatch_count,
        "cumulative_mismatch_rate": current_rate,
        "status": "obsolete" if current_rate > 0.8 else "active"
    }
    
    return report

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Node Metadata
    # Scenario: A node describing "Morning Coffee Routine"
    coffee_node = NodeMetadata(
        node_id="node_coffee_01",
        constraints={
            "time_window": {"start": "07:00", "end": "09:00"},
            "loc_kitchen": {"lat": 40.7128, "lon": -74.0060, "radius_km": 0.5}, # NYC
            "state_cup": {"object": "coffee_cup", "required_state": "clean"}
        }
    )

    # 2. Setup Contexts
    
    # Case A: Perfect Match (Morning, Kitchen, Clean Cup)
    context_match = EnvironmentContext(
        timestamp=datetime(2023, 1, 1, 8, 30),
        location=(40.7129, -74.0061), # Close to target
        detected_objects={"coffee_cup": "clean", "toaster": "off"}
    )

    # Case B: Mismatch (Afternoon)
    context_time_mismatch = EnvironmentContext(
        timestamp=datetime(2023, 1, 1, 14, 30), # Wrong time
        location=(40.7129, -74.0061),
        detected_objects={"coffee_cup": "clean"}
    )

    # Case C: Mismatch (Wrong State)
    context_state_mismatch = EnvironmentContext(
        timestamp=datetime(2023, 1, 1, 8, 30),
        location=(40.7129, -74.0061),
        detected_objects={"coffee_cup": "dirty"} # Wrong state
    )

    # 3. Execute Quantification
    
    print("--- Processing Case A (Expected: High Viability) ---")
    score_a = calculate_environment_viability(coffee_node, context_match)
    result_a = update_node_mismatch_stats(coffee_node, score_a)
    print(f"Result: {result_a}")

    print("\n--- Processing Case B (Expected: Low Viability) ---")
    score_b = calculate_environment_viability(coffee_node, context_time_mismatch)
    result_b = update_node_mismatch_stats(coffee_node, score_b)
    print(f"Result: {result_b}")
    
    print("\n--- Processing Case C (Expected: Partial Viability) ---")
    score_c = calculate_environment_viability(coffee_node, context_state_mismatch)
    result_c = update_node_mismatch_stats(coffee_node, score_c)
    print(f"Result: {result_c}")