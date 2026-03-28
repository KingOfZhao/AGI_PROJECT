"""
Module: auto_开发_空间自适应3d装配ui_在ar_ef81b8
Description: Implements spatial adaptive 3D assembly UI logic for AR/VR scenarios.
             Inspired by Flutter's layout algorithms (Wrap/Flow), this module provides
             collision detection and "smart snapping" to calculate optimal fit positions,
             reducing cognitive load during 3D model assembly.
Author: Senior Python Engineer (AGI System)
License: MIT
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Vector3:
    """Represents a point or direction in 3D space."""
    x: float
    y: float
    z: float

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def distance_to(self, other: 'Vector3') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

@dataclass
class BoundingBox:
    """Axis-Aligned Bounding Box (AABB) for a 3D object."""
    center: Vector3
    size: Vector3  # width, height, depth

    @property
    def min(self) -> Vector3:
        return Vector3(
            self.center.x - self.size.x / 2,
            self.center.y - self.size.y / 2,
            self.center.z - self.size.z / 2
        )

    @property
    def max(self) -> Vector3:
        return Vector3(
            self.center.x + self.size.x / 2,
            self.center.y + self.size.y / 2,
            self.center.z + self.size.z / 2
        )

@dataclass
class AssemblyPart:
    """Represents a 3D part in the assembly environment."""
    id: str
    position: Vector3
    bbox: BoundingBox
    is_static: bool = False

class SpatialAssemblyController:
    """
    Core logic for spatial adaptive UI in AR assembly.
    Handles spatial queries and calculates optimal snapping positions.
    """

    def __init__(self, snap_threshold: float = 0.5, alignment_gap: float = 0.05):
        """
        Initialize the controller.

        Args:
            snap_threshold (float): Maximum distance to trigger snapping logic.
            alignment_gap (float): Desired gap between parts after snapping (like margin in Flutter).
        """
        self.snap_threshold = snap_threshold
        self.alignment_gap = alignment_gap
        self._parts_registry: List[AssemblyPart] = []
        logger.info("SpatialAssemblyController initialized with threshold %.2f", snap_threshold)

    def register_part(self, part: AssemblyPart) -> None:
        """Register a part into the assembly environment."""
        if not isinstance(part, AssemblyPart):
            raise ValueError("Invalid part type provided.")
        self._parts_registry.append(part)
        logger.debug(f"Part {part.id} registered at {part.position}")

    def calculate_optimal_snap_position(self, moving_part: AssemblyPart) -> Optional[Vector3]:
        """
        Core Function 1: Calculates the 'best fit' position for the moving part
        based on surrounding static parts (Spatial Wrap Logic).

        Args:
            moving_part (AssemblyPart): The part currently being dragged.

        Returns:
            Optional[Vector3]: The calculated target position, or None if no snap is needed.

        Logic:
            Iterates through nearby static parts. If a part is within `snap_threshold`,
            it calculates a target position that aligns the bounding boxes with the
            specified gap, prioritizing the closest valid surface.
        """
        if not moving_part or moving_part.id not in [p.id for p in self._parts_registry]:
            logger.error("Moving part not found in registry.")
            return None

        best_target: Optional[Vector3] = None
        min_distance = float('inf')

        for target_part in self._parts_registry:
            if target_part.id == moving_part.id or not target_part.is_static:
                continue

            # Check rough distance between centers first for performance
            center_dist = moving_part.position.distance_to(target_part.position)
            max_reach = (
                max(moving_part.bbox.size.x, moving_part.bbox.size.y, moving_part.bbox.size.z) +
                max(target_part.bbox.size.x, target_part.bbox.size.y, target_part.bbox.size.z)
            ) / 2 + self.snap_threshold

            if center_dist > max_reach:
                continue

            # Determine potential snap directions (6 DOF)
            # We try to snap the moving part to the surfaces of the static part
            snap_candidates = self._get_surface_snap_offsets(moving_part.bbox, target_part.bbox)
            
            for offset in snap_candidates:
                potential_pos = target_part.position + offset
                dist = moving_part.position.distance_to(potential_pos)
                
                # Prioritize the closest valid snap point
                if dist < min_distance:
                    min_distance = dist
                    best_target = potential_pos

        if best_target and min_distance <= self.snap_threshold:
            logger.info(f"Snap candidate found for {moving_part.id} near target.")
            return best_target
        
        return None

    def _get_surface_snap_offsets(self, moving_bbox: BoundingBox, target_bbox: BoundingBox) -> List[Vector3]:
        """
        Helper Function: Calculates relative offsets to align `moving_bbox` 
        adjacent to `target_bbox` along X, Y, Z axes.

        Returns:
            List[Vector3]: List of possible relative positions (offsets) from the target center.
        """
        # Calculate required spacing (half sizes + gap)
        dx = (moving_bbox.size.x / 2) + (target_bbox.size.x / 2) + self.alignment_gap
        dy = (moving_bbox.size.y / 2) + (target_bbox.size.y / 2) + self.alignment_gap
        dz = (moving_bbox.size.z / 2) + (target_bbox.size.z / 2) + self.alignment_gap

        offsets = [
            Vector3(dx, 0, 0),  Vector3(-dx, 0, 0),  # X-axis alignment
            Vector3(0, dy, 0),  Vector3(0, -dy, 0),  # Y-axis alignment
            Vector3(0, 0, dz),  Vector3(0, 0, -dz)   # Z-axis alignment
        ]
        return offsets

    def detect_spatial_conflicts(self, proposed_position: Vector3, part_id: str) -> Tuple[bool, List[str]]:
        """
        Core Function 2: Collision Detection (AABB).
        Checks if placing a part at `proposed_position` overlaps with existing static parts.

        Args:
            proposed_position (Vector3): The potential new position.
            part_id (str): ID of the part being moved.

        Returns:
            Tuple[bool, List[str]]: (True if clear, False if collision), List of conflicting part IDs.
        """
        # Create a temporary bbox for the proposed position
        moving_part_data = next((p for p in self._parts_registry if p.id == part_id), None)
        if not moving_part_data:
            return False, ["Part not found"]

        # Create hypothetical box
        test_box = BoundingBox(center=proposed_position, size=moving_part_data.bbox.size)
        
        conflicts = []
        for part in self._parts_registry:
            if part.id == part_id:
                continue
            
            # AABB Intersection Test
            if self._check_aabb_intersection(test_box, part.bbox):
                conflicts.append(part.id)

        is_clear = len(conflicts) == 0
        if not is_clear:
            logger.warning(f"Conflict detected at {proposed_position} with parts: {conflicts}")
        
        return is_clear, conflicts

    def _check_aabb_intersection(self, box_a: BoundingBox, box_b: BoundingBox) -> bool:
        """
        Internal helper for AABB collision check.
        """
        return (
            abs(box_a.center.x - box_b.center.x) <= (box_a.size.x + box_b.size.x) / 2 and
            abs(box_a.center.y - box_b.center.y) <= (box_a.size.y + box_b.size.y) / 2 and
            abs(box_a.center.z - box_b.center.z) <= (box_a.size.z + box_b.size.z) / 2
        )

# Usage Example
if __name__ == "__main__":
    # 1. Setup Environment
    controller = SpatialAssemblyController(snap_threshold=1.0, alignment_gap=0.1)
    
    # 2. Define Parts (Simulating AR Scene Objects)
    # Static Engine Block
    engine_pos = Vector3(0, 0, 0)
    engine_size = Vector3(2.0, 1.5, 3.0)
    engine_part = AssemblyPart(
        id="engine_01", 
        position=engine_pos, 
        bbox=BoundingBox(engine_pos, engine_size), 
        is_static=True
    )
    controller.register_part(engine_part)

    # Moving Part (e.g., a Turbocharger)
    # Initially placed close to the engine, but not aligned
    turbo_pos = Vector3(1.8, 0.1, 0.0) 
    turbo_size = Vector3(0.8, 0.8, 0.8)
    turbo_part = AssemblyPart(
        id="turbo_01", 
        position=turbo_pos, 
        bbox=BoundingBox(turbo_pos, turbo_size), 
        is_static=False
    )
    controller.register_part(turbo_part)

    # 3. Simulate Drag Event
    # The system calculates where the turbo should go
    print("--- Calculating Snap ---")
    snap_target = controller.calculate_optimal_snap_position(turbo_part)

    if snap_target:
        print(f"Original Position: {turbo_pos.x}, {turbo_pos.y}, {turbo_pos.z}")
        # Expected: Aligned on X axis (Engine Width/2 + Turbo Width/2 + gap)
        # Engine X max = 1.0. Turbo half-width = 0.4. Gap = 0.1. Target X = 1.0 + 0.4 + 0.1 = 1.5
        print(f"Suggested Snap Position: {snap_target.x:.2f}, {snap_target.y:.2f}, {snap_target.z:.2f}")

        # 4. Validate the move
        is_clear, conflicts = controller.detect_spatial_conflicts(snap_target, "turbo_01")
        print(f"Is Move Valid? {is_clear}")
    else:
        print("No snap target found (too far away).")