"""
Time-Warp CAD Editor Core Logic
================================
This module implements the core logic for a 'Time-Warp CAD Editor'.
It bridges parametric CAD history with a state-management system inspired
by Flutter's Hot Reload and Widget tree.

Key Features:
- Interpolated transitions (Morphing) between design history states.
- Instant switching between design variants (States).
- Input/Output agnostic: Accepts JSON payloads, suitable for IPC with
  Flutter/Dart frontend or file-based storage.

Author: AGI System
Version: 1.0.0
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TimeWarpCADEditor")

class GeometryType(Enum):
    """Enumeration of supported CAD geometry types."""
    CUBE = "CUBE"
    SPHERE = "SPHERE"
    CYLINDER = "CYLINDER"
    MESH = "MESH"

@dataclass
class CADParameter:
    """Represents a single parameter in the CAD history tree."""
    name: str
    value: float
    min_val: float = -1e6
    max_val: float = 1e6
    
    def validate(self) -> bool:
        """Validate parameter boundaries."""
        if not (self.min_val <= self.value <= self.max_val):
            raise ValueError(f"Parameter {self.name} value {self.value} out of bounds [{self.min_val}, {self.max_val}]")
        return True

@dataclass
class CADNode:
    """Represents a node in the parametric history tree (Visual Git)."""
    node_id: str
    geo_type: GeometryType
    params: Dict[str, CADParameter] = field(default_factory=dict)
    children: List['CADNode'] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        """Serializes the node to a dictionary."""
        return {
            "node_id": self.node_id,
            "geo_type": self.geo_type.value,
            "params": {k: v.value for k, v in self.params.items()},
            "children": [c.to_dict() for c in self.children]
        }

class TimeWarpEngine:
    """
    Core engine for managing state, history, and interpolation.
    Acts as the backend logic for the 'Visual Git' system.
    """
    
    def __init__(self):
        self._history_stack: List[CADNode] = []
        self._current_state: Optional[CADNode] = None
        self._variant_cache: Dict[str, CADNode] = {}  # For instant switching
        
        logger.info("TimeWarpEngine initialized.")

    def load_design_tree(self, json_data: Dict[str, Any]) -> CADNode:
        """
        Reconstructs a CAD design tree from a dictionary (JSON) input.
        
        Args:
            json_data: Raw dictionary containing design data.
            
        Returns:
            CADNode: The root of the constructed design tree.
            
        Raises:
            ValueError: If data format is invalid.
        """
        try:
            root_data = json_data.get('root')
            if not root_data:
                raise ValueError("Input JSON must contain a 'root' node.")
            
            root_node = self._deserialize_node(root_data)
            self._current_state = root_node
            self._history_stack.append(root_node)
            
            logger.info(f"Design tree loaded successfully. Root ID: {root_node.node_id}")
            return root_node
        except Exception as e:
            logger.error(f"Failed to load design tree: {e}")
            raise

    def commit_change(self, new_params: Dict[str, float], description: str = "Update") -> bool:
        """
        Commits a parameter change, creating a new history entry (Git Commit equivalent).
        Performs a deep copy to preserve history immutability.
        
        Args:
            new_params: Dictionary of parameter names to new float values.
            description: Commit message.
            
        Returns:
            bool: True if commit was successful.
        """
        if not self._current_state:
            logger.warning("No state loaded to commit changes to.")
            return False

        try:
            # Create a mutable copy for the new state
            # In a real implementation, this would be a deep copy operation
            # Here we simulate by creating a new node based on current
            new_root = self._clone_tree(self._current_state)
            
            # Apply changes recursively (simplified for demo)
            self._apply_params(new_root, new_params)
            
            self._history_stack.append(new_root)
            self._current_state = new_root
            
            logger.info(f"Change committed: {description}")
            return True
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            return False

    def interpolate_history(
        self, 
        start_idx: int, 
        end_idx: int, 
        t: float
    ) -> Dict[str, Any]:
        """
        Generates an intermediate state between two history snapshots.
        This enables the 'Time-Warp' smooth transition effect.
        
        Args:
            start_idx: Index of the starting history state.
            end_idx: Index of the target history state.
            t: Interpolation factor (0.0 to 1.0).
            
        Returns:
            Dict: The interpolated geometry data ready for rendering.
        """
        # Boundary checks
        if not (0 <= start_idx < len(self._history_stack) and 
                0 <= end_idx < len(self._history_stack)):
            raise IndexError("History indices out of range.")
        
        if not (0.0 <= t <= 1.0):
            raise ValueError("Interpolation factor 't' must be between 0 and 1.")

        start_node = self._history_stack[start_idx]
        end_node = self._history_stack[end_idx]
        
        logger.debug(f"Interpolating states: {start_idx} -> {end_idx} at t={t:.2f}")
        
        # Recursively interpolate nodes
        interpolated_root = self._lerp_node(start_node, end_node, t)
        return interpolated_root.to_dict()

    def save_variant(self, variant_name: str) -> None:
        """
        Snapshots the current state into the variant cache (Flutter State preservation).
        Allows instant switching without re-calculation.
        """
        if self._current_state:
            # Deep copy simulation
            self._variant_cache[variant_name] = self._clone_tree(self._current_state)
            logger.info(f"Variant '{variant_name}' saved.")

    def load_variant(self, variant_name: str) -> Optional[Dict]:
        """
        Instantly loads a saved variant.
        """
        if variant_name in self._variant_cache:
            self._current_state = self._variant_cache[variant_name]
            logger.info(f"Switched to variant '{variant_name}' instantly.")
            return self._current_state.to_dict()
        logger.warning(f"Variant '{variant_name}' not found.")
        return None

    # ---------------- Helper Functions ---------------- #

    def _deserialize_node(self, data: Dict) -> CADNode:
        """Recursively parses dictionary data into CADNode objects."""
        params = {}
        for k, v in data.get('params', {}).items():
            # Basic assumption: params are floats
            params[k] = CADParameter(name=k, value=float(v))
            
        node = CADNode(
            node_id=data['node_id'],
            geo_type=GeometryType(data['geo_type']),
            params=params
        )
        
        for child_data in data.get('children', []):
            node.children.append(self._deserialize_node(child_data))
            
        return node

    def _clone_tree(self, node: CADNode) -> CADNode:
        """Creates a deep copy of a CADNode tree."""
        # Using to_dict and back for simple deep copy simulation
        # Production code would use copy.deepcopy or custom recursive clone
        return self._deserialize_node(node.to_dict())

    def _apply_params(self, node: CADNode, changes: Dict[str, float]) -> None:
        """Applies parameter changes to the node tree."""
        for key, val in changes.items():
            if key in node.params:
                node.params[key].value = val
                node.params[key].validate()
        
        # Propagate to children (simplified logic)
        for child in node.children:
            self._apply_params(child, changes)

    def _lerp_node(self, n1: CADNode, n2: CADNode, t: float) -> CADNode:
        """
        Core interpolation logic. 
        Calculates intermediate values for parameters.
        """
        # Start with structure of n1 (assuming isomorphic trees for morphing)
        new_params = {}
        
        all_keys = set(n1.params.keys()).union(set(n2.params.keys()))
        
        for key in all_keys:
            v1 = n1.params.get(key, CADParameter(key, 0.0)).value
            v2 = n2.params.get(key, CADParameter(key, 0.0)).value
            
            # Linear interpolation: v1 + (v2 - v1) * t
            # Using ease-in-out smoothing for visual appeal
            smooth_t = t * t * (3 - 2 * t) 
            interp_val = v1 + (v2 - v1) * smooth_t
            
            new_params[key] = CADParameter(name=key, value=interp_val)
            
        return CADNode(
            node_id=f"interp_{n1.node_id}_{n2.node_id}",
            geo_type=n1.geo_type,
            params=new_params
        )

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Initialize Engine
    engine = TimeWarpEngine()
    
    # 2. Define Input Data (e.g., a parametric Bracket)
    # Format: JSON compatible dict
    design_input = {
        "root": {
            "node_id": "bracket_base",
            "geo_type": "CUBE",
            "params": {"width": 100.0, "height": 20.0, "depth": 50.0},
            "children": [
                {
                    "node_id": "hole_1",
                    "geo_type": "CYLINDER",
                    "params": {"radius": 5.0, "height": 20.0},
                    "children": []
                }
            ]
        }
    }
    
    # 3. Load initial design
    try:
        root = engine.load_design_tree(design_input)
        print(f"Initial Model Loaded: {root.node_id}")
        
        # 4. Save initial state as a variant
        engine.save_variant("Design_V1")
        
        # 5. Modify parameters (Simulate user interaction)
        # Increasing width and hole radius
        engine.commit_change({"width": 150.0, "radius": 8.0}, description="Widened bracket")
        engine.save_variant("Design_V2_Wide")
        
        # 6. Time Warp interpolation
        print("\nSimulating Time Warp Morphing (0% -> 100%)...")
        for step in range(11):
            t_val = step / 10.0
            interpolated_state = engine.interpolate_history(0, 1, t_val)
            # In a real app, this dict is sent to the Flutter Viewport
            width = interpolated_state['params']['width']
            print(f"Step {step*10}%: Width = {width:.2f}mm")
            
        # 7. Instant Variant Switching
        print("\nSwitching back to V1 instantly...")
        v1_state = engine.load_variant("Design_V1")
        if v1_state:
            print(f"Current Width restored to: {v1_state['params']['width']}")

    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except Exception as e:
        print(f"System Error: {e}")