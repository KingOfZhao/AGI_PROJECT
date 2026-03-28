"""
Module: semantic_digital_twin_bridge.py
Description: Implements the 'Semantic Digital Twin' logic layer. This module acts as a backend
             processor that ingests raw CAD PMI (Product Manufacturing Information) and
             transforms it into a structured, semantic format suitable for a Flutter frontend.
             
             It enables:
             1. Accessibility: Blind factory admins can perceive model structure via screen readers.
             2. AI Integration: AI inspectors can query structured tolerance data via API.
"""

import logging
import json
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass, asdict

# --- Configuration & Logging ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticDigitalTwin")

# --- Data Structures & Types ---

class PMIType(Enum):
    """Enumeration of standard PMI types."""
    DIMENSION = "DIMENSION"
    GEOMETRIC_TOLERANCE = "GEOMETRIC_TOLERANCE"
    SURFACE_FINISH = "SURFACE_FINISH"
    MATERIAL_SPEC = "MATERIAL_SPEC"
    ANNOTATION = "ANNOTATION"

class Severity(Enum):
    """Severity level for quality control."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

@dataclass
class ToleranceValue:
    """Represents a numerical tolerance range."""
    nominal: float
    upper: float
    lower: float
    unit: str

    def __post_init__(self):
        """Validate data integrity."""
        if self.upper < self.nominal or self.lower > self.nominal:
            raise ValueError(f"Invalid tolerance range: {self.lower} < {self.nominal} < {self.upper}")

@dataclass
class SemanticNode:
    """
    Represents a semantic node in the Digital Twin structure.
    This maps directly to a Semantics widget in Flutter.
    """
    node_id: str
    label: str
    hint: str
    value: Optional[Union[str, float, Dict]] = None
    pmi_type: Optional[PMIType] = None
    severity: Optional[Severity] = None
    children: List['SemanticNode'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

class FlutterSemanticsTree(TypedDict):
    """Output format compatible with Flutter Semantics JSON parsing."""
    id: str
    label: str
    hint: str
    value: str
    flags: Dict[str, bool]
    custom_attributes: Dict[str, str]
    children: List['FlutterSemanticsTree']

# --- Core Functions ---

def parse_raw_cad_data(raw_json: str) -> List[SemanticNode]:
    """
    Ingests raw JSON string from CAD systems (e.g., STEP AP242 or JT export).
    Validates and transforms raw geometry data into Semantic Nodes.

    Args:
        raw_json (str): A JSON string containing raw CAD feature data.

    Returns:
        List[SemanticNode]: A list of validated semantic nodes representing the model structure.
    
    Raises:
        ValueError: If input data is malformed or missing critical fields.
        TypeError: If input is not a string.
    """
    if not isinstance(raw_json, str):
        logger.error("Input must be a JSON string.")
        raise TypeError("Input data must be a string.")
    
    try:
        data = json.loads(raw_json)
        logger.info(f"Successfully parsed raw CAD data containing {len(data.get('features', []))} features.")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}")
        raise ValueError("Invalid JSON format.") from e

    semantic_nodes = []
    features = data.get("features", [])

    if not features:
        logger.warning("No features found in the provided CAD data.")

    for feature in features:
        try:
            # Validate required fields existence
            if 'name' not in feature or 'type' not in feature:
                logger.warning(f"Skipping malformed feature: {feature}")
                continue

            # Map raw type to internal PMI Enum
            try:
                pmi_type = PMIType[feature['type'].upper()]
            except KeyError:
                pmi_type = PMIType.ANNOTATION

            # Extract tolerance data if present
            tolerance_data = feature.get('tolerance')
            value_obj = None
            if tolerance_data:
                value_obj = ToleranceValue(
                    nominal=float(tolerance_data['nominal']),
                    upper=float(tolerance_data['upper']),
                    lower=float(tolerance_data['lower']),
                    unit=tolerance_data.get('unit', 'mm')
                )

            # Create Semantic Node
            node = SemanticNode(
                node_id=str(uuid.uuid4()),
                label=f"{feature['name']} ({pmi_type.value})",
                hint=_generate_accessibility_hint(pmi_type, value_obj),
                value=asdict(value_obj) if value_obj else feature.get('text_value'),
                pmi_type=pmi_type,
                severity=Severity[feature.get('severity', 'MINOR').upper()]
            )
            semantic_nodes.append(node)
            
        except (ValueError, KeyError) as ve:
            logger.warning(f"Skipping feature due to validation error: {ve}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing feature {feature.get('id')}: {e}")
            continue

    logger.info(f"Generated {len(semantic_nodes)} semantic nodes.")
    return semantic_nodes

def generate_flutter_semantics_tree(nodes: List[SemanticNode]) -> FlutterSemanticsTree:
    """
    Transforms internal Semantic Nodes into a Flutter-specific JSON structure.
    This structure is optimized for Flutter's SemanticsNode tree.

    Args:
        nodes (List[SemanticNode]): List of processed semantic nodes.

    Returns:
        FlutterSemanticsTree: A recursive dictionary structure ready for API consumption.
    """
    if not nodes:
        return {
            "id": "root_empty",
            "label": "Empty Model",
            "hint": "No data available",
            "value": "",
            "flags": {"isFocusable": False},
            "custom_attributes": {},
            "children": []
        }

    def _recursive_convert(node: SemanticNode) -> Dict[str, Any]:
        """Helper to convert node recursively."""
        # Format value for screen reader consumption (string representation)
        str_value = ""
        if isinstance(node.value, dict):
            str_value = f"{node.value.get('nominal', '')} {node.value.get('unit', '')}"
        elif node.value is not None:
            str_value = str(node.value)

        # Construct Flutter Semantics attributes
        flutter_node = {
            "id": node.node_id,
            "label": node.label,
            "hint": node.hint,
            "value": str_value,
            "flags": {
                "isFocusable": True,
                "isReadable": True
            },
            "custom_attributes": {
                "pmi_type": node.pmi_type.value if node.pmi_type else "UNKNOWN",
                "severity": node.severity.value if node.severity else "UNKNOWN",
                "raw_data_json": json.dumps(node.value) if node.value else "{}"
            },
            "children": [_recursive_convert(child) for child in node.children]
        }
        return flutter_node

    # Create a virtual root node
    root_tree = {
        "id": "virtual_root_3d_viewer",
        "label": "3D Model Semantic Root",
        "hint": "Double tap to explore model structure",
        "value": f"{len(nodes)} features",
        "flags": {"isFocusable": False},
        "custom_attributes": {"role": "container"},
        "children": [_recursive_convert(n) for n in nodes]
    }
    
    logger.info("Flutter Semantics Tree generated successfully.")
    return root_tree

# --- Helper Functions ---

def _generate_accessibility_hint(pmi_type: PMIType, value: Optional[ToleranceValue]) -> str:
    """
    Generates human-readable hints for screen readers (TalkBack/VoiceOver).
    This ensures the Semantic Digital Twin is accessible to blind administrators.
    """
    base_hint = f"Manufacturing attribute of type {pmi_type.value.replace('_', ' ')}."
    
    if value and isinstance(value, ToleranceValue):
        range_hint = (
            f"Target value {value.nominal} {value.unit}. "
            f"Acceptable range from {value.lower} to {value.upper} {value.unit}."
        )
        return f"{base_hint} {range_hint}"
    
    return base_hint

def validate_model_integrity(tree: FlutterSemanticsTree) -> bool:
    """
    Post-generation validation to ensure the tree structure is valid for the frontend.
    """
    if not tree.get("id"):
        return False
    
    def _check_children(node):
        if not isinstance(node.get('children'), list):
            return False
        for child in node['children']:
            if not _check_children(child):
                return False
        return True

    return _check_children(tree)

# --- Usage Example ---

if __name__ == "__main__":
    # Simulating input data from a CAD system export
    mock_cad_input = json.dumps({
        "features": [
            {
                "id": "feat_001",
                "name": "Hole_Diameter_A1",
                "type": "DIMENSION",
                "severity": "CRITICAL",
                "tolerance": {
                    "nominal": 10.5,
                    "upper": 10.55,
                    "lower": 10.45,
                    "unit": "mm"
                }
            },
            {
                "id": "feat_002",
                "name": "Surface_Roughness_B2",
                "type": "SURFACE_FINISH",
                "severity": "MINOR",
                "text_value": "Ra 1.6"
            }
        ]
    })

    try:
        # 1. Process Raw Data
        semantic_nodes = parse_raw_cad_data(mock_cad_input)
        
        # 2. Build Flutter Tree
        flutter_tree = generate_flutter_semantics_tree(semantic_nodes)
        
        # 3. Validate
        is_valid = validate_model_integrity(flutter_tree)
        
        if is_valid:
            print("\n--- Generated Flutter Semantics Tree (JSON) ---")
            print(json.dumps(flutter_tree, indent=2))
            print("\nSUCCESS: Semantic Digital Twin layer generated.")
        else:
            print("ERROR: Generated tree is invalid.")

    except Exception as e:
        print(f"Execution failed: {e}")