"""
SKILL: auto_轻量级web端几何内核切片_不依赖重型w_a9a1ce
Description: A lightweight computational geometry backend module.
             This module calculates cross-sections and visualizations
             for a web-based CAD viewer without relying on heavy WebAssembly builds.
             It outputs vector graphics data (compatible with Flutter Canvas/Impeller).
"""

import logging
import math
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class GeometryType(Enum):
    """Enumeration for supported geometry types."""
    LINE = 1
    ARC = 2
    CIRCLE = 3
    POLYGON = 4

@dataclass
class Point3D:
    """Represents a point in 3D space."""
    x: float
    y: float
    z: float

    def __post_init__(self):
        if not all(isinstance(v, (float, int)) for v in [self.x, self.y, self.z]):
            raise ValueError("Coordinates must be numeric.")

@dataclass
class Triangle:
    """Represents a triangular face defined by three 3D points."""
    p1: Point3D
    p2: Point3D
    p3: Point3D

@dataclass
class VectorPath:
    """
    Represents a drawable vector path for Flutter Canvas.
    Attributes:
        commands: List of draw commands (e.g., moveTo, lineTo).
        color: RGBA hex string.
        thickness: Line width.
    """
    commands: List[Dict[str, Any]] = field(default_factory=list)
    color: str = "#000000"
    thickness: float = 1.0
    geometry_type: GeometryType = GeometryType.LINE

# --- Helper Functions ---

def _validate_mesh_integrity(triangles: List[Triangle]) -> bool:
    """
    Validates the mesh data structure.
    Ensures triangles are not degenerate (zero area).
    """
    if not triangles:
        logger.warning("Mesh validation failed: Empty mesh provided.")
        return False
    
    for i, tri in enumerate(triangles):
        # Check for degenerate triangles (collinear points or identical points)
        # Vector AB = B - A
        ab = Point3D(tri.p2.x - tri.p1.x, tri.p2.y - tri.p1.y, tri.p2.z - tri.p1.z)
        # Vector AC = C - A
        ac = Point3D(tri.p3.x - tri.p1.x, tri.p3.y - tri.p1.y, tri.p3.z - tri.p1.z)
        
        # Cross product components
        cross_x = ab.y * ac.z - ab.z * ac.y
        cross_y = ab.z * ac.x - ab.x * ac.z
        cross_z = ab.x * ac.y - ab.y * ac.x
        
        area_sq = cross_x**2 + cross_y**2 + cross_z**2
        
        if area_sq < 1e-10:
            logger.error(f"Degenerate triangle found at index {i}.")
            return False
            
    logger.info("Mesh validation passed.")
    return True

# --- Core Functions ---

def compute_planar_slice(
    triangles: List[Triangle], 
    plane_height: float = 0.0, 
    axis: str = 'z',
    tolerance: float = 1e-6
) -> VectorPath:
    """
    Computes the intersection of a triangular mesh with a horizontal or vertical plane.
    This function generates 2D vector paths suitable for rendering on Flutter Canvas.
    
    Args:
        triangles: A list of Triangle objects representing the 3D mesh.
        plane_height: The coordinate value of the slicing plane.
        axis: The axis perpendicular to the plane ('x', 'y', or 'z').
        tolerance: Precision for floating point comparisons.
        
    Returns:
        VectorPath: An object containing drawing commands for the intersection lines.
        
    Raises:
        ValueError: If axis is invalid or mesh is empty.
    """
    logger.info(f"Computing planar slice at {axis}={plane_height}")
    
    if not triangles:
        raise ValueError("Input mesh cannot be empty.")
    if axis not in ['x', 'y', 'z']:
        raise ValueError(f"Invalid axis {axis}. Must be 'x', 'y', or 'z'.")

    # Map axis to coordinate index
    axis_idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    
    segments = []
    
    for tri in triangles:
        points = [tri.p1, tri.p2, tri.p3]
        coords = [getattr(p, axis) for p in points]
        
        # Identify vertices above/below/on the plane
        # 1 = above, -1 = below, 0 = on
        sides = []
        for c in coords:
            if c > plane_height + tolerance:
                sides.append(1)
            elif c < plane_height - tolerance:
                sides.append(-1)
            else:
                sides.append(0)
        
        # We need exactly two intersection points if the plane cuts the triangle
        # Skip if all above or all below
        if all(s > 0 for s in sides) or all(s < 0 for s in sides):
            continue
            
        # Simple line segment intersection logic (ignoring vertex-on-plane edge cases for brevity)
        intersections = []
        edges = [(0, 1), (1, 2), (2, 0)]
        
        for i1, i2 in edges:
            p1, p2 = points[i1], points[i2]
            c1, c2 = coords[i1], coords[i2]
            
            # Check if edge crosses the plane
            if (c1 < plane_height and c2 > plane_height) or (c1 > plane_height and c2 < plane_height):
                # Linear interpolation
                t = (plane_height - c1) / (c2 - c1)
                ix = p1.x + t * (p2.x - p1.x)
                iy = p1.y + t * (p2.y - p1.y)
                iz = p1.z + t * (p2.z - p1.z)
                
                # Project to 2D based on slicing axis
                if axis == 'z':
                    intersections.append((ix, iy))
                elif axis == 'y':
                    intersections.append((ix, iz))
                else: # x
                    intersections.append((iy, iz))
                    
        if len(intersections) >= 2:
            segments.append(intersections[:2])

    # Convert segments to Flutter Canvas command format
    commands = []
    for p1, p2 in segments:
        commands.append({"action": "moveTo", "x": p1[0], "y": p1[1]})
        commands.append({"action": "lineTo", "x": p2[0], "y": p2[1]})
        
    logger.info(f"Slice generated with {len(commands) // 2} line segments.")
    
    return VectorPath(
        commands=commands, 
        color="#FF5722", 
        thickness=2.0, 
        geometry_type=GeometryType.LINE
    )

def generate_stress_heatmap_data(
    triangles: List[Triangle],
    stress_values: List[float]
) -> Dict[str, Any]:
    """
    Generates vertex-colored geometry data for rendering a stress cloud map.
    Uses a simple linear interpolation for color mapping (Blue-Cyan-Green-Yellow-Red).
    
    Args:
        triangles: The mesh geometry.
        stress_values: A list of stress values corresponding to each triangle (or vertex).
                       Here we assume per-triangle scalar values for simplicity.
        
    Returns:
        A dictionary containing vertices, indices, and color arrays suitable for
        a Flutter Impeller shader or standard Canvas drawVertices call.
    """
    logger.info("Generating stress heatmap data...")
    
    if len(triangles) != len(stress_values):
        raise ValueError("Mismatch between triangle count and stress values count.")

    # Data validation
    if not stress_values:
        return {"vertices": [], "colors": [], "indices": []}

    min_stress = min(stress_values)
    max_stress = max(stress_values)
    range_stress = max_stress - min_stress if max_stress != min_stress else 1.0
    
    def get_color(value: float) -> str:
        """Maps 0.0-1.0 value to a heat color hex string."""
        # 0: Blue, 0.25: Cyan, 0.5: Green, 0.75: Yellow, 1: Red
        # Simplified logic for demonstration
        if value < 0.25:
            return "#0000FF"
        elif value < 0.5:
            return "#00FF00"
        elif value < 0.75:
            return "#FFFF00"
        else:
            return "#FF0000"

    output_vertices = []
    output_colors = []
    
    # Flatten triangles and assign colors
    # Note: In a real engine, we would use an index buffer to avoid duplicate vertices.
    # Here we duplicate vertices per triangle for simplicity of the JSON structure.
    
    for tri, stress in zip(triangles, stress_values):
        normalized = (stress - min_stress) / range_stress
        color_hex = get_color(normalized)
        
        # For each vertex in the triangle, add position and color
        for p in [tri.p1, tri.p2, tri.p3]:
            output_vertices.append({"x": p.x, "y": p.y, "z": p.z})
            output_colors.append(color_hex)
            
    logger.info(f"Generated heatmap for {len(triangles)} facets.")
    
    return {
        "format": "flutter_vertices",
        "vertex_mode": "triangles",
        "data": {
            "positions": output_vertices,
            "colors": output_colors
        }
    }

# --- Main Execution Example ---

if __name__ == "__main__":
    # Create a simple unit cube mesh (simplified for demo)
    # 12 triangles for a cube, here we just define a pyramid-like structure
    # centered at (0,0,0)
    demo_triangles = [
        Triangle(Point3D(0,0,0), Point3D(1,0,0), Point3D(0.5, 1, 0.5)), # Base 1
        Triangle(Point3D(1,0,0), Point3D(1,0,1), Point3D(0.5, 1, 0.5)), # Side 2
        Triangle(Point3D(1,0,1), Point3D(0,0,1), Point3D(0.5, 1, 0.5)), # Side 3
        Triangle(Point3D(0,0,1), Point3D(0,0,0), Point3D(0.5, 1, 0.5)), # Side 4
    ]
    
    # Add some stress values
    demo_stress = [10.0, 25.0, 50.0, 15.0]

    try:
        # 1. Validate Mesh
        if _validate_mesh_integrity(demo_triangles):
            # 2. Compute Slice at z=0.5
            slice_path = compute_planar_slice(demo_triangles, plane_height=0.5, axis='z')
            print(f"\nSlice Output (Commands count): {len(slice_path.commands)}")
            # print(slice_path.commands) # Uncomment to see raw commands

            # 3. Generate Heatmap
            heatmap_data = generate_stress_heatmap_data(demo_triangles, demo_stress)
            print(f"Heatmap Vertices: {len(heatmap_data['data']['positions'])}")
            
    except ValueError as e:
        logger.error(f"Processing Error: {e}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}", exc_info=True)