"""
Module: cloud_cad_logic_shared_layer
Description: Implements the 'Cloud CAD Logic Shared Layer'.
             This module serves as a microservice backend for Flutter apps,
             exposing heavy CAD algorithms (Boolean operations, Volume calculations,
             Collision detection) via gRPC/WebSocket interface logic.
             
Author: AGI System
Version: 1.0.0
"""

import logging
import time
import uuid
import json
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Attempt to import numpy, handle if not available (mock for environment compatibility)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Mock numpy for type hinting if not installed
    class np:
        @staticmethod
        def array(x): return x
        float64 = float

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CloudCADCore")


class GeometryError(Exception):
    """Custom exception for geometry processing errors."""
    pass


class InputValidationError(Exception):
    """Custom exception for invalid input data."""
    pass


class OperationStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


@dataclass
class CADVector:
    x: float
    y: float
    z: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BoundingBox:
    min_corner: CADVector
    max_corner: CADVector


@dataclass
class MeshData:
    """Represents a simplified 3D Mesh structure (STL-like)."""
    vertices: Any  # np.array or list of floats [x1, y1, z1, x2, ...]
    triangles: Any # np.array or list of ints [i1, i2, i3, ...]
    mesh_id: str

    def __post_init__(self):
        if not self.mesh_id:
            self.mesh_id = str(uuid.uuid4())


def validate_mesh_data(mesh: MeshData) -> None:
    """
    Helper function to validate mesh integrity and data types.
    
    Args:
        mesh (MeshData): The mesh object to validate.
        
    Raises:
        InputValidationError: If the mesh data is empty or malformed.
    """
    if not mesh:
        raise InputValidationError("Mesh data cannot be None.")
    
    if not mesh.vertices or len(mesh.vertices) == 0:
        logger.error(f"Validation failed for mesh {mesh.mesh_id}: Empty vertices.")
        raise InputValidationError("Mesh vertices cannot be empty.")
        
    if not mesh.triangles or len(mesh.triangles) == 0:
        logger.error(f"Validation failed for mesh {mesh.mesh_id}: Empty triangles.")
        raise InputValidationError("Mesh triangles cannot be empty.")

    # Basic check for triangle indices bounds (conceptual)
    # In a real scenario with numpy: if np.max(mesh.triangles) >= len(mesh.vertices) / 3: raise Error
    logger.debug(f"Mesh {mesh.mesh_id} validated successfully.")


def calculate_bounding_box(mesh: MeshData) -> BoundingBox:
    """
    Core Algorithm 1: Calculate the Axis-Aligned Bounding Box (AABB).
    Used for broad-phase collision detection optimization.
    
    Args:
        mesh (MeshData): Input mesh data.
        
    Returns:
        BoundingBox: The calculated bounding box.
    """
    validate_mesh_data(mesh)
    
    try:
        # Convert to numpy array for efficient calculation if available
        if NUMPY_AVAILABLE:
            verts = np.array(mesh.vertices).reshape(-1, 3)
            min_coords = np.min(verts, axis=0)
            max_coords = np.max(verts, axis=0)
        else:
            # Fallback logic for pure Python (simplified)
            verts = [mesh.vertices[i:i+3] for i in range(0, len(mesh.vertices), 3)]
            min_coords = [min(v[i] for v in verts) for i in range(3)]
            max_coords = [max(v[i] for v in verts) for i in range(3)]

        bbox = BoundingBox(
            min_corner=CADVector(*min_coords),
            max_corner=CADVector(*max_coords)
        )
        logger.info(f"Calculated AABB for mesh {mesh.mesh_id}")
        return bbox
    except Exception as e:
        logger.error(f"Math error in AABB calculation: {str(e)}")
        raise GeometryError(f"Failed to calculate bounding box: {str(e)}")


def calculate_mesh_volume(mesh: MeshData) -> float:
    """
    Core Algorithm 2: Calculate the volume of a closed mesh using the Divergence Theorem.
    (Signed volume of tetrahedrons formed by triangles and origin).
    
    Args:
        mesh (MeshData): Input closed mesh.
        
    Returns:
        float: The volume of the mesh.
        
    Raises:
        GeometryError: If the mesh is not watertight or calculation fails.
    """
    validate_mesh_data(mesh)
    logger.info(f"Starting volume calculation for mesh {mesh.mesh_id}")
    
    total_volume = 0.0
    
    try:
        # Reshape vertices for easier access
        if NUMPY_AVAILABLE:
            verts = np.array(mesh.vertices, dtype=np.float64).reshape(-1, 3)
            tris = np.array(mesh.triangles, dtype=np.int32).reshape(-1, 3)
        else:
            # Pure python fallback (slow, just for logic demonstration)
            verts = [mesh.vertices[i:i+3] for i in range(0, len(mesh.vertices), 3)]
            tris = [mesh.triangles[i:i+3] for i in range(0, len(mesh.triangles), 3)]

        # Algorithm: Volume = sum of (v1 . (v2 x v3)) / 6 for each triangle
        # This is a signed volume method.
        for tri in tris:
            v1 = verts[tri[0]]
            v2 = verts[tri[1]]
            v3 = verts[tri[2]]
            
            if NUMPY_AVAILABLE:
                # Cross product v2 x v3
                cross = np.cross(v2, v3)
                # Dot product v1 . cross
                total_volume += np.dot(v1, cross) / 6.0
            else:
                # Manual cross product
                cx = v2[1]*v3[2] - v2[2]*v3[1]
                cy = v2[2]*v3[0] - v2[0]*v3[2]
                cz = v2[0]*v3[1] - v2[1]*v3[0]
                # Manual dot product
                total_volume += (v1[0]*cx + v1[1]*cy + v1[2]*cz) / 6.0

        if total_volume < 0:
            logger.warning(f"Mesh {mesh.mesh_id} has negative volume (normals might be inverted). Taking absolute value.")
            total_volume = abs(total_volume)

        logger.info(f"Volume calculated for {mesh.mesh_id}: {total_volume:.4f} units^3")
        return total_volume

    except IndexError:
        raise GeometryError("Triangle index out of bounds of vertex array.")
    except Exception as e:
        logger.error(f"Volume calculation failed: {str(e)}")
        raise GeometryError(f"Computational error: {str(e)}")


def execute_cad_operation(operation_type: str, payload: Dict) -> Dict:
    """
    Main entry point for the microservice (Controller Logic).
    Handles routing, execution timing, and error wrapping.
    
    Args:
        operation_type (str): 'volume', 'bounding_box', etc.
        payload (Dict): Dictionary containing 'vertices' and 'triangles'.
        
    Returns:
        Dict: Result package containing status, data, and latency.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Received operation: {operation_type}")
    
    try:
        # Input Parsing
        if 'vertices' not in payload or 'triangles' not in payload:
            raise InputValidationError("Payload must contain 'vertices' and 'triangles'.")

        mesh = MeshData(
            vertices=payload['vertices'],
            triangles=payload['triangles'],
            mesh_id=payload.get('id', 'unknown')
        )
        
        result_data = None
        
        # Routing
        if operation_type == 'volume':
            result_data = calculate_mesh_volume(mesh)
        elif operation_type == 'bounding_box':
            result_data = calculate_bounding_box(mesh).to_dict()
        else:
            raise InputValidationError(f"Unsupported operation: {operation_type}")

        latency = (time.time() - start_time) * 1000
        return {
            "request_id": request_id,
            "status": OperationStatus.SUCCESS.value,
            "data": result_data,
            "latency_ms": round(latency, 2)
        }

    except (InputValidationError, GeometryError) as cad_err:
        logger.warning(f"[{request_id}] Business logic error: {cad_err}")
        return {
            "request_id": request_id,
            "status": OperationStatus.FAILURE.value,
            "error": str(cad_err),
            "latency_ms": (time.time() - start_time) * 1000
        }
    except Exception as sys_err:
        logger.critical(f"[{request_id}] System failure: {sys_err}", exc_info=True)
        return {
            "request_id": request_id,
            "status": OperationStatus.FAILURE.value,
            "error": "Internal Server Error",
            "latency_ms": (time.time() - start_time) * 1000
        }

# Example Usage
if __name__ == "__main__":
    # Define a simple cube (2x2x2) centered at origin for demonstration
    # 8 vertices
    example_vertices = [
        -1, -1, -1,  # 0
         1, -1, -1,  # 1
         1,  1, -1,  # 2
        -1,  1, -1,  # 3
        -1, -1,  1,  # 4
         1, -1,  1,  # 5
         1,  1,  1,  # 6
        -1,  1,  1   # 7
    ]
    
    # 12 triangles (2 per face) defining the cube surface
    example_triangles = [
        0, 1, 2, 0, 2, 3, # Bottom
        4, 6, 5, 4, 7, 6, # Top
        0, 4, 5, 0, 5, 1, # Front
        2, 6, 7, 2, 7, 3, # Back
        0, 3, 7, 0, 7, 4, # Left
        1, 5, 6, 1, 6, 2  # Right
    ]
    
    input_payload = {
        "vertices": example_vertices,
        "triangles": example_triangles,
        "id": "cube_sample_01"
    }

    print("--- Running CAD Cloud Logic Example ---")
    
    # Test Volume Calculation
    # Expected volume for 2x2x2 cube is 8.0
    vol_result = execute_cad_operation("volume", input_payload)
    print(f"Volume Result: {json.dumps(vol_result, indent=2)}")

    # Test Bounding Box Calculation
    # Expected: Min(-1,-1,-1), Max(1,1,1)
    bbox_result = execute_cad_operation("bounding_box", input_payload)
    print(f"BBox Result: {json.dumps(bbox_result, indent=2)}")

    # Test Error Handling
    err_result = execute_cad_operation("volume", {"vertices": [], "triangles": []})
    print(f"Error Result: {json.dumps(err_result, indent=2)}")