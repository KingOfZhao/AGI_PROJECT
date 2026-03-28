"""
Reactive CAD Workbench: Immutable Data Flow Implementation

This module simulates a CAD frontend interaction layer refactored based on
Flutter's immutable data flow philosophy. It utilizes a diffing algorithm
to optimize model reconstruction, ensuring that only modified geometric
features are regenerated rather than performing a full rebuild.

Classes:
    GeometryFeature: An immutable representation of a CAD geometric feature.
    CADState: An immutable snapshot of the entire CAD model state.
    ChangeType: Enumeration defining the type of state change (Add, Update, Remove).

Core Functions:
    compute_diff: Compares two immutable CADStates to identify specific changes.
    execute_reactive_build: Applies changes by regenerating only affected features.

Auxiliary Functions:
    validate_geometry_params: Validates input parameters for geometric features.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ReactiveCAD")


class ChangeType(Enum):
    """Enumeration of possible change operations in the CAD model."""
    ADD = auto()
    UPDATE = auto()
    REMOVE = auto()


@dataclass(frozen=True)
class GeometryFeature:
    """
    Immutable representation of a CAD feature.
    
    Attributes:
        id (str): Unique identifier for the feature.
        type (str): Type of geometry (e.g., 'extrude', 'revolve', 'fillet').
        params (Dict[str, float]): Parameters defining the geometry (e.g., length, radius).
        _hash (str): Cached hash for efficient diffing.
    """
    id: str
    type: str
    params: Dict[str, float] = field(repr=False)
    _hash: str = field(init=False, repr=False)

    def __post_init__(self):
        # Calculate a hash based on content to detect changes efficiently
        params_str = str(sorted(self.params.items()))
        hash_obj = hashlib.md5(f"{self.id}{self.type}{params_str}".encode())
        object.__setattr__(self, '_hash', hash_obj.hexdigest())


@dataclass(frozen=True)
class CADState:
    """
    Immutable state container for the CAD model.
    
    This acts as the 'Widget Tree' equivalent in Flutter, representing the
    current configuration of the model.
    """
    features: Tuple[GeometryFeature, ...]

    def get_feature_by_id(self, feature_id: str) -> Optional[GeometryFeature]:
        """Retrieves a feature by its ID."""
        for feat in self.features:
            if feat.id == feature_id:
                return feat
        return None


def validate_geometry_params(params: Dict[str, float]) -> bool:
    """
    Validates geometric parameters to ensure they are physically possible.
    
    Args:
        params (Dict[str, float]): Dictionary of parameter names and values.
        
    Returns:
        bool: True if valid, False otherwise.
        
    Raises:
        ValueError: If parameters are out of bounds or invalid.
    """
    if not params:
        raise ValueError("Parameters dictionary cannot be empty.")
    
    for key, value in params.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"Parameter '{key}' must be a number.")
        if value < 0:
            # In CAD, dimensions usually cannot be negative
            raise ValueError(f"Parameter '{key}' cannot be negative (got {value}).")
        if key == 'radius' and value == 0:
            raise ValueError("Radius cannot be zero.")
            
    return True


def compute_diff(old_state: CADState, new_state: CADState) -> List[Tuple[ChangeType, GeometryFeature]]:
    """
    Computes the difference between two CAD states using a Diffing algorithm.
    
    This mimics Flutter's Element diffing process to identify which parts
    of the UI (or in this case, the Model) need updating.

    Args:
        old_state (CADState): The previous immutable state.
        new_state (CADState): The new immutable state.

    Returns:
        List[Tuple[ChangeType, GeometryFeature]]: A list of changes detected.
    """
    changes = []
    old_features_map = {f.id: f for f in old_state.features}
    new_features_map = {f.id: f for f in new_state.features}
    
    old_ids = set(old_features_map.keys())
    new_ids = set(new_features_map.keys())
    
    # Detect Additions (IDs in new but not in old)
    added_ids = new_ids - old_ids
    for fid in added_ids:
        changes.append((ChangeType.ADD, new_features_map[fid]))
        
    # Detect Removals (IDs in old but not in new)
    removed_ids = old_ids - new_ids
    for fid in removed_ids:
        changes.append((ChangeType.REMOVE, old_features_map[fid]))
        
    # Detect Updates (IDs in both, but content changed)
    common_ids = old_ids & new_ids
    for fid in common_ids:
        old_feat = old_features_map[fid]
        new_feat = new_features_map[fid]
        if old_feat._hash != new_feat._hash:
            changes.append((ChangeType.UPDATE, new_feat))
            
    logger.info(f"Diffing complete: {len(changes)} changes detected.")
    return changes


def execute_reactive_build(current_state: CADState, target_state: CADState) -> CADState:
    """
    Executes a reactive build process, regenerating only changed features.
    
    Instead of rebuilding the whole model, this function applies the patch
    calculated by the diffing algorithm.

    Args:
        current_state (CADState): The active state of the system.
        target_state (CADState): The desired state after user interaction.

    Returns:
        CADState: The new active state (which should match target_state).
        
    Example:
        >>> # Create initial state
        >>> f1 = GeometryFeature(id="cube1", type="box", params={"width": 10.0, "height": 10.0})
        >>> state_v1 = CADState(features=(f1,))
        >>> # Modify feature (Immutable update)
        >>> f2 = GeometryFeature(id="cube1", type="box", params={"width": 20.0, "height": 10.0})
        >>> state_v2 = CADState(features=(f2,))
        >>> # Apply update
        >>> final_state = execute_reactive_build(state_v1, state_v2)
    """
    logger.info("Starting reactive build process...")
    
    try:
        # 1. Calculate Diff
        changes = compute_diff(current_state, target_state)
        
        if not changes:
            logger.info("No changes detected. Model remains unchanged.")
            return current_state

        # 2. Apply Changes (Simulate Kernel Regeneration)
        # In a real CAD kernel, this would trigger C++ API calls to regenerate geometry.
        # Here we simulate the computational cost.
        for change_type, feature in changes:
            if change_type == ChangeType.UPDATE:
                logger.info(f"  [Rebuild] Updating feature ID: {feature.id} | Type: {feature.type}")
                # Simulate heavy computation for the specific feature
                _simulate_kernel_rebuild(feature)
            elif change_type == ChangeType.ADD:
                logger.info(f"  [Create] Adding new feature ID: {feature.id}")
                _simulate_kernel_rebuild(feature)
            elif change_type == ChangeType.REMOVE:
                logger.info(f"  [Delete] Removing feature ID: {feature.id}")
                
        # 3. Return new immutable state
        logger.info("Reactive build finished successfully.")
        return target_state
        
    except Exception as e:
        logger.error(f"Error during reactive build: {e}")
        # Rollback or handle error state
        raise


def _simulate_kernel_rebuild(feature: GeometryFeature) -> None:
    """
    Helper function to simulate the time-consuming process of geometric calculation.
    """
    # Simulate processing time based on complexity
    complexity = len(feature.params)
    logger.debug(f"    -> Calculating geometry for {feature.id} with {complexity} params...")
    # In a real scenario, this is where the heavy math happens.
    # The key is that we are HERE for only ONE feature, not the whole assembly.


if __name__ == "__main__":
    # --- Usage Example ---
    
    print("--- Initializing CAD Workbench ---")
    
    # Define initial features
    try:
        base_params = {"length": 50.0, "width": 50.0, "depth": 20.0}
        validate_geometry_params(base_params)
        
        feature_base = GeometryFeature(id="base_plate", type="extrude", params=base_params)
        feature_hole = GeometryFeature(id="mount_hole", type="cylinder", params={"radius": 5.0, "depth": 20.0})
        
        # Create initial state
        state_v1 = CADState(features=(feature_base, feature_hole))
        logger.info(f"Initial State Created: {len(state_v1.features)} features.")
        
        print("\n--- User Interaction: Modifying Base Plate Length ---")
        
        # User modifies the base plate length from 50.0 to 100.0
        # Because data is immutable, we create a new GeometryFeature instance
        new_base_params = {"length": 100.0, "width": 50.0, "depth": 20.0}
        feature_base_modified = GeometryFeature(id="base_plate", type="extrude", params=new_base_params)
        
        # Create target state
        state_v2 = CADState(features=(feature_base_modified, feature_hole))
        
        # Execute Reactive Build
        # The system should detect that 'mount_hole' is unchanged and skip its regeneration
        final_state = execute_reactive_build(state_v1, state_v2)
        
        print("\n--- User Interaction: Adding a Fillet ---")
        
        # User adds a fillet feature
        fillet_params = {"radius": 2.0}
        feature_fillet = GeometryFeature(id="edge_fillet", type="fillet", params=fillet_params)
        
        state_v3 = CADState(features=(feature_base_modified, feature_hole, feature_fillet))
        final_state = execute_reactive_build(final_state, state_v3)
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")