"""
Module: auto_构建_可视化逻辑编程系统_利用flut_3c9744
Description: This module provides the backend logic for a Visual Logic Programming System.
             It interprets a declarative JSON structure (representing Flutter-like Widgets)
             and compiles it into executable OpenSCAD code or a 3D geometry tree.
             
             The system treats CAD operations (Union, Difference, Intersection) as 
             Widget compositions, enabling a "What You See Is What You Get" approach 
             to procedural 3D modeling via code reconstruction.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class Vector3:
    """Represents a 3D vector for position, rotation, or scale."""
    x: float
    y: float
    z: float

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

@dataclass
class CadFeature:
    """
    Represents a single CAD feature node in the logic tree.
    Analogous to a Flutter Widget.
    """
    id: str
    type: str  # e.g., 'Cube', 'Sphere', 'Union', 'Difference'
    params: Dict[str, Any]
    children: List['CadFeature']

# --- Constants & Validation Rules ---

ALLOWED_PRIMITIVES = {'cube', 'sphere', 'cylinder'}
ALLOWED_BOOLEANS = {'union', 'difference', 'intersection'}
ALLOWED_TRANSFORMS = {'translate', 'rotate', 'scale'}

class ValidationError(Exception):
    """Custom exception for validation errors in the CAD tree."""
    pass

# --- Core Functions ---

def validate_and_parse_input(json_data: Dict[str, Any]) -> CadFeature:
    """
    Validates the incoming JSON structure (simulating Flutter Widget tree dump)
    and parses it into a CadFeature data structure.

    Args:
        json_data (Dict[str, Any]): The raw dictionary representing the widget tree.

    Returns:
        CadFeature: The root of the validated CAD feature tree.

    Raises:
        ValidationError: If the structure is invalid or parameters are out of bounds.
    """
    logger.info("Starting validation of input logic tree...")
    
    if not isinstance(json_data, dict):
        raise ValidationError("Input must be a dictionary.")

    def _recursive_parse(node: Dict[str, Any], depth: int = 0) -> CadFeature:
        if depth > 20:
            raise ValidationError("Maximum recursion depth exceeded (infinite loop detected in tree).")
        
        if 'type' not in node:
            raise ValidationError(f"Node missing 'type' field: {node}")

        node_type = node['type'].lower()
        params = node.get('params', {})
        raw_children = node.get('children', [])

        # Parameter Validation
        if node_type in ALLOWED_PRIMITIVES:
            if node_type == 'cube':
                if not (0 < params.get('size', 1.0) <= 1000.0):
                    raise ValidationError(f"Cube size out of bounds: {params.get('size')}")
            elif node_type == 'sphere':
                if not (0 < params.get('radius', 1.0) <= 500.0):
                    raise ValidationError(f"Sphere radius out of bounds: {params.get('radius')}")
        
        elif node_type in ALLOWED_BOOLEANS:
            if len(raw_children) < 2:
                logger.warning(f"Boolean operation '{node_type}' typically requires at least 2 children.")

        elif node_type in ALLOWED_TRANSFORMS:
            if 'vector' not in params:
                raise ValidationError(f"Transform '{node_type}' missing 'vector' parameter.")

        # Recursion
        children = [_recursive_parse(child, depth + 1) for child in raw_children]
        
        return CadFeature(
            id=node.get('id', 'unknown'),
            type=node_type,
            params=params,
            children=children
        )

    try:
        root = _recursive_parse(json_data)
        logger.info("Validation successful.")
        return root
    except KeyError as e:
        logger.error(f"Missing key during parsing: {e}")
        raise ValidationError(f"Missing key: {e}")


def generate_scad_code(feature_tree: CadFeature) -> str:
    """
    Transpiles the CadFeature tree into executable OpenSCAD code.
    This demonstrates the "Code Generation" aspect of the AGI skill.

    Args:
        feature_tree (CadFeature): The root node of the geometry tree.

    Returns:
        str: A string containing the generated OpenSCAD script.
    """
    logger.info(f"Generating SCAD code for tree root: {feature_tree.id}")
    
    def _compile_node(node: CadFeature, indent_level: int = 0) -> str:
        indent = "  " * indent_level
        code_lines = []
        
        # Handle Transforms
        if node.type == 'translate':
            vec = node.params.get('vector', [0,0,0])
            children_code = "".join([_compile_node(c, indent_level + 1) for c in node.children])
            code_lines.append(f"{indent}translate([{vec[0]}, {vec[1]}, {vec[2]}]) {{\n{children_code}{indent}}}\n")
        
        # Handle Boolean Operations
        elif node.type == 'union':
            children_code = "".join([_compile_node(c, indent_level + 1) for c in node.children])
            code_lines.append(f"{indent}union() {{\n{children_code}{indent}}}\n")
            
        elif node.type == 'difference':
            if not node.children:
                return ""
            base = _compile_node(node.children[0], indent_level + 1)
            cutters = "".join([_compile_node(c, indent_level + 1) for c in node.children[1:]])
            code_lines.append(f"{indent}difference() {{\n{base}{cutters}{indent}}}\n")

        # Handle Primitives
        elif node.type == 'cube':
            size = node.params.get('size', 1)
            code_lines.append(f"{indent}cube([{size}, {size}, {size}]);\n")
            
        elif node.type == 'sphere':
            r = node.params.get('radius', 1)
            code_lines.append(f"{indent}sphere(r={r});\n")
            
        else:
            logger.warning(f"Unsupported node type encountered: {node.type}")
            code_lines.append(f"{indent}// Unsupported type: {node.type}\n")

        return "".join(code_lines)

    scad_script = _compile_node(feature_tree)
    return scad_script

# --- Helper Functions ---

def vector3_to_openscad_string(vector: Union[List[float], Vector3]) -> str:
    """
    Helper to convert vector inputs to OpenSCAD format [x, y, z].
    
    Args:
        vector: List of floats or Vector3 object.
        
    Returns:
        str: Formatted string "[x, y, z]".
    """
    if isinstance(vector, Vector3):
        return str(vector.to_list()).replace(" ", "") # SCAD accepts [x,y,z]
    elif isinstance(vector, list) and len(vector) == 3:
        return f"[{vector[0]}, {vector[1]}, {vector[2]}]"
    else:
        logger.error("Invalid vector format")
        return "[0, 0, 0]"

# --- Main Execution Example ---

if __name__ == "__main__":
    # Simulating a JSON payload that might come from the Flutter Frontend
    # This represents a hollow box (Difference between two cubes)
    flutter_widget_dump = {
        "id": "root_node_1",
        "type": "Difference",
        "params": {},
        "children": [
            {
                "id": "outer_box",
                "type": "Cube",
                "params": {"size": 10},
                "children": []
            },
            {
                "id": "inner_cutout",
                "type": "Translate",
                "params": {"vector": [1, 1, 1]}, # Move cutter slightly
                "children": [
                    {
                        "id": "cutter_box",
                        "type": "Cube",
                        "params": {"size": 8},
                        "children": []
                    }
                ]
            }
        ]
    }

    print("-" * 40)
    print("Visual Logic Programming System Backend")
    print("-" * 40)

    try:
        # Step 1: Validate Input (Data Validation)
        parsed_tree = validate_and_parse_input(flutter_widget_dump)
        
        # Step 2: Generate Code (Logic Synthesis)
        generated_code = generate_scad_code(parsed_tree)
        
        print("\nGenerated OpenSCAD Code:")
        print(generated_code)
        
        # Step 3: Verify it's not empty
        assert len(generated_code) > 0
        assert "difference()" in generated_code
        
    except ValidationError as ve:
        logger.error(f"Validation Failed: {ve}")
    except Exception as e:
        logger.critical(f"System Error: {e}", exc_info=True)