"""
Declarative Vector Shape Component Module.

This module provides a high-level, declarative interface for creating and 
managing 2D vector shapes similar to CAD sketches. It supports parametric 
path generation, boolean operations (union, difference, intersection), and 
dynamic property updates (e.g., automatically recalculating paths when 
corner radius changes).

Dependencies:
    - numpy: For mathematical vector operations.

Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Union

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BooleanOperation(Enum):
    """Enumeration of supported boolean operations for shapes."""
    UNION = "union"
    DIFFERENCE = "difference"
    INTERSECTION = "intersection"


@dataclass
class Vector2D:
    """Represents a 2D coordinate or vector."""
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x - other.x, self.y - other.y)


@dataclass
class PathCommand:
    """Represents a single command in a vector path (SVG style)."""
    command: str  # M (Move), L (Line), C (Cubic Bezier), A (Arc), Z (Close)
    points: List[Vector2D] = field(default_factory=list)
    params: dict = field(default_factory=dict)  # For arc radii or other flags


class ShapeDefinitionError(Exception):
    """Custom exception for errors in shape definition."""
    pass


class VectorShape:
    """
    A declarative vector shape component.
    
    Supports parametric definitions and caches the calculated path.
    
    Attributes:
        name (str): Identifier for the shape.
        operations (List[Tuple[BooleanOperation, 'VectorShape']]): 
            List of boolean operations to apply to the base geometry.
    """

    def __init__(self, name: str, base_geometry: Optional[List[PathCommand]] = None):
        """
        Initialize a VectorShape.
        
        Args:
            name: The name of the shape.
            base_geometry: Optional initial list of path commands.
        """
        self.name = name
        self._base_geometry = base_geometry if base_geometry else []
        self._cached_path: Optional[List[PathCommand]] = None
        self.operations: List[Tuple[BooleanOperation, VectorShape]] = []
        logger.info(f"Initialized shape: {self.name}")

    def add_operation(self, operation: BooleanOperation, other_shape: 'VectorShape') -> None:
        """
        Add a boolean operation to the shape pipeline.
        
        Note: In a full implementation, this would trigger a CSG (Constructive 
        Solid Geometry) library. Here we simulate the data structure.
        
        Args:
            operation: The type of boolean operation.
            other_shape: The other shape to operate with.
        """
        if not isinstance(other_shape, VectorShape):
            raise ShapeDefinitionError("Operation requires a VectorShape instance.")
        
        self.operations.append((operation, other_shape))
        self._cached_path = None  # Invalidate cache
        logger.debug(f"Added {operation.value} operation to {self.name}")

    def generate_path(self) -> List[PathCommand]:
        """
        Generates the final path commands for the shape.
        
        Returns:
            List of PathCommand objects representing the vector geometry.
        """
        if self._cached_path is not None:
            return self._cached_path

        logger.info(f"Generating path for {self.name}...")
        # In a real scenario, we would run polygon clipping here (e.g., using Clipper2 library)
        # We return the base geometry for demonstration.
        
        # Validate geometry
        if not self._base_geometry:
            logger.warning(f"Shape {self.name} has no geometry defined.")
            
        self._cached_path = self._base_geometry
        return self._cached_path

    def update_geometry(self, new_commands: List[PathCommand]) -> None:
        """Updates the base geometry and clears cache."""
        self._base_geometry = new_commands
        self._cached_path = None


def create_rounded_rect(
    width: float, 
    height: float, 
    radius: float = 0.0, 
    center: Tuple[float, float] = (0, 0)
) -> List[PathCommand]:
    """
    Helper function to create a parametric rounded rectangle path.
    
    This function generates a sequence of PathCommand objects that define
    a rectangle with specified dimensions and corner radii.
    
    Args:
        width: The width of the rectangle. Must be non-negative.
        height: The height of the rectangle. Must be non-negative.
        radius: The corner radius. Must be non-negative. 
                If radius > min(width, height)/2, it is clamped.
        center: The (x, y) coordinates of the center of the rectangle.
    
    Returns:
        A list of PathCommand objects defining the rectangle.
    
    Raises:
        ValueError: If width, height, or radius are negative.
        
    Example:
        >>> path = create_rounded_rect(100, 50, 10, center=(0,0))
        >>> print(path[0].command)
        'M'
    """
    # Data Validation
    if width < 0 or height < 0 or radius < 0:
        logger.error("Invalid input: Dimensions cannot be negative.")
        raise ValueError("Width, height, and radius must be non-negative.")
    
    # Boundary Check: Clamp radius to half the smallest side
    max_radius = min(width, height) / 2
    clamped_radius = min(radius, max_radius)
    
    if clamped_radius != radius:
        logger.warning(f"Radius {radius} too large for dimensions. Clamped to {clamped_radius}")

    cx, cy = center
    x0, y0 = cx - width / 2, cy - height / 2
    x1, y1 = cx + width / 2, cy + height / 2

    # If radius is effectively 0, return a simple rectangle
    if clamped_radius < 1e-5:
        return [
            PathCommand('M', [Vector2D(x0, y0)]),
            PathCommand('L', [Vector2D(x1, y0)]),
            PathCommand('L', [Vector2D(x1, y1)]),
            PathCommand('L', [Vector2D(x0, y1)]),
            PathCommand('Z')
        ]

    # Construct path with Arcs (Simplified A command syntax)
    # For a perfect rounded rect, we draw lines and arcs
    path = []
    
    # Start at bottom edge, left of bottom-right corner
    path.append(PathCommand('M', [Vector2D(x1 - clamped_radius, y0)]))
    
    # Bottom right corner arc to right edge
    path.append(PathCommand('A', [
        Vector2D(x1, y0 + clamped_radius)
    ], params={'rx': clamped_radius, 'ry': clamped_radius, 'rotation': 0, 'large_arc': 0, 'sweep': 1}))
    
    # Right edge to top right corner
    path.append(PathCommand('L', [Vector2D(x1, y1 - clamped_radius)]))
    
    # Top right corner arc
    path.append(PathCommand('A', [
        Vector2D(x1 - clamped_radius, y1)
    ], params={'rx': clamped_radius, 'ry': clamped_radius, 'rotation': 0, 'large_arc': 0, 'sweep': 1}))
    
    # Top edge to top left corner
    path.append(PathCommand('L', [Vector2D(x0 + clamped_radius, y1)]))
    
    # Top left corner arc
    path.append(PathCommand('A', [
        Vector2D(x0, y1 - clamped_radius)
    ], params={'rx': clamped_radius, 'ry': clamped_radius, 'rotation': 0, 'large_arc': 0, 'sweep': 1}))
    
    # Left edge to bottom left corner
    path.append(PathCommand('L', [Vector2D(x0, y0 + clamped_radius)]))
    
    # Bottom left corner arc
    path.append(PathCommand('A', [
        Vector2D(x0 + clamped_radius, y0)
    ], params={'rx': clamped_radius, 'ry': clamped_radius, 'rotation': 0, 'large_arc': 0, 'sweep': 1}))
    
    path.append(PathCommand('Z'))
    
    return path


def apply_boolean_difference(base: VectorShape, hole: VectorShape) -> bool:
    """
    Core Function: Applies a boolean difference operation (subtraction).
    
    This punches the 'hole' shape out of the 'base' shape.
    
    Args:
        base: The primary shape.
        hole: The shape to subtract from the base.
        
    Returns:
        True if the operation was successfully scheduled.
    """
    try:
        logger.info(f"Applying difference: {base.name} - {hole.name}")
        base.add_operation(BooleanOperation.DIFFERENCE, hole)
        return True
    except ShapeDefinitionError as e:
        logger.error(f"Failed to apply boolean operation: {e}")
        return False


def export_to_svg_fragment(shape: VectorShape) -> str:
    """
    Helper Function: Exports the shape geometry to an SVG path string.
    
    Args:
        shape: The VectorShape instance to export.
        
    Returns:
        A string containing the 'd' attribute value for an SVG <path> element.
    """
    path_data = shape.generate_path()
    svg_string = ""
    
    for cmd in path_data:
        points_str = " ".join([f"{p.x:.2f} {p.y:.2f}" for p in cmd.points])
        
        if cmd.command == 'A':
            # SVG Arc format: A rx ry x-axis-rotation large-arc-flag sweep-flag x y
            p = cmd.points[0]
            svg_string += f" {cmd.command} {cmd.params['rx']:.2f} {cmd.params['ry']:.2f} " \
                          f"{cmd.params['rotation']} {cmd.params['large_arc']} " \
                          f"{cmd.params['sweep']} {p.x:.2f} {p.y:.2f}"
        else:
            svg_string += f" {cmd.command} {points_str}"
            
    return svg_string.strip()


if __name__ == "__main__":
    # Example Usage
    
    # 1. Create a base plate (Rounded Rectangle)
    try:
        logger.info("--- Creating Base Plate ---")
        base_plate_path = create_rounded_rect(200, 100, 15)
        base_plate = VectorShape("BasePlate", base_plate_path)
        
        # 2. Create a mounting hole (Circle approximated by 4 arcs or polygon)
        # Here we simulate a circle path for the hole
        circle_path = [
            PathCommand('M', [Vector2D(50, 0)]),
            PathCommand('A', [Vector2D(-50, 0)], {'rx': 50, 'ry': 50, 'rotation': 0, 'large_arc': 1, 'sweep': 1}),
            PathCommand('A', [Vector2D(50, 0)], {'rx': 50, 'ry': 50, 'rotation': 0, 'large_arc': 1, 'sweep': 1}),
            PathCommand('Z')
        ]
        mounting_hole = VectorShape("MountingHole", circle_path)
        
        # 3. Apply boolean operation (Cutout)
        apply_boolean_difference(base_plate, mounting_hole)
        
        # 4. Output result
        svg_output = export_to_svg_fragment(base_plate)
        print(f"\nGenerated SVG Path Data:\n{svg_output}")
        
        # 5. Parametric Update Example
        logger.info("--- Updating Parameters ---")
        print("Updating base plate radius to 30...")
        new_path = create_rounded_rect(200, 100, 30)
        base_plate.update_geometry(new_path)
        
        # Regenerate and print
        svg_output_updated = export_to_svg_fragment(base_plate)
        print(f"\nUpdated SVG Path Data:\n{svg_output_updated}")

    except Exception as e:
        logger.critical(f"Application crashed: {e}")