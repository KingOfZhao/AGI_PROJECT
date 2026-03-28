"""
Module: interactive_plc_view_generator
Description: Generates a configuration payload for an Interactive Product Lifecycle View.
             This module bridges CAD BOM structures with Flutter state management trees
             to enable bi-directional interaction between 3D models and deep data.

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MaterialType(Enum):
    """Enumeration of supported material types for the 3D model."""
    METAL = "metal"
    PLASTIC = "plastic"
    COMPOSITE = "composite"
    GLASS = "glass"

@dataclass
class BOMNode:
    """Represents a single node in the Bill of Materials."""
    node_id: str
    name: str
    quantity: int
    material: MaterialType
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['BOMNode'] = field(default_factory=list)

    def __post_init__(self):
        """Validate data after initialization."""
        if self.quantity < 0:
            raise ValueError(f"Quantity cannot be negative for node {self.node_id}")

@dataclass
class FlutterStateTree:
    """Represents the state tree structure for Flutter frontend."""
    widget_id: str
    widget_type: str
    bind_to_cad_guid: str
    properties: Dict[str, Any]
    children: List['FlutterStateTree'] = field(default_factory=list)

class BOMToFlutterMapper:
    """
    Core engine for mapping CAD BOM structures to Flutter State Trees.
    
    Handles the transformation logic, validation, and generation of the 
    interactive digital twin configuration.
    """

    def __init__(self, cad_metadata: Dict[str, Any]):
        """
        Initialize the mapper with CAD metadata.
        
        Args:
            cad_metadata (Dict[str, Any]): Metadata containing GUIDs and mesh references.
        """
        self.cad_metadata = cad_metadata
        self._node_cache: Dict[str, BOMNode] = {}
        logger.info("BOMToFlutterMapper initialized with %d metadata entries.", len(cad_metadata))

    def parse_bom_structure(self, raw_data: Dict[str, Any]) -> Optional[BOMNode]:
        """
        Parses raw JSON-like data into a validated BOMNode tree structure.
        
        Args:
            raw_data (Dict[str, Any]): Raw dictionary representing the root BOM.
            
        Returns:
            Optional[BOMNode]: The root of the validated BOM tree, or None if parsing fails.
        """
        try:
            root_node = self._recursive_parse(raw_data)
            self._build_cache(root_node)
            logger.info("Successfully parsed BOM structure with root ID: %s", root_node.node_id)
            return root_node
        except (KeyError, ValueError, TypeError) as e:
            logger.error("Failed to parse BOM structure: %s", str(e), exc_info=True)
            return None

    def generate_flutter_state_tree(self, bom_root: BOMNode) -> Optional[FlutterStateTree]:
        """
        Maps a BOMNode tree to a Flutter State Tree configuration.
        
        This creates the structural link for the frontend to render the PLC view.
        
        Args:
            bom_root (BOMNode): The root node of the BOM structure.
            
        Returns:
            Optional[FlutterStateTree]: The root of the generated Flutter state tree.
        """
        if not bom_root:
            logger.warning("Cannot generate Flutter tree from None BOM root.")
            return None
            
        logger.info("Generating Flutter State Tree for BOM: %s", bom_root.name)
        return self._recursive_map(bom_root)

    def update_material_linkage(self, node_id: str, new_material: MaterialType) -> Dict[str, Any]:
        """
        Simulates the bi-directional update: Modifies BOM and generates 3D update payload.
        
        Args:
            node_id (str): The ID of the node to update.
            new_material (MaterialType): The new material type.
            
        Returns:
            Dict[str, Any]: A command payload for the 3D engine to update the material sphere.
        """
        if node_id not in self._node_cache:
            logger.error("Node ID %s not found in cache.", node_id)
            return {"status": "error", "message": "Node not found"}

        node = self._node_cache[node_id]
        old_material = node.material
        node.material = new_material
        
        # Generate command for 3D engine
        command = {
            "target_guid": self.cad_metadata.get(node.node_id, {}).get("guid"),
            "action": "UPDATE_MATERIAL",
            "payload": {
                "shader_type": new_material.value,
                "properties": self._get_material_properties(new_material)
            }
        }
        
        logger.info("Updated node %s material from %s to %s", node_id, old_material.value, new_material.value)
        return command

    # ---------------- Private Helper Methods ----------------

    def _recursive_parse(self, data: Dict[str, Any]) -> BOMNode:
        """Recursively parses dictionary data into BOMNode objects."""
        # Data validation
        if not isinstance(data, dict):
            raise TypeError("BOM data must be a dictionary")
        
        node_id = data.get('id', str(uuid.uuid4()))
        
        # Handle material conversion safely
        try:
            material = MaterialType(data.get('material', 'metal').lower())
        except ValueError:
            logger.warning("Unknown material type '%s', defaulting to METAL.", data.get('material'))
            material = MaterialType.METAL

        node = BOMNode(
            node_id=node_id,
            name=data['name'],
            quantity=int(data.get('quantity', 1)),
            material=material,
            metadata=data.get('metadata', {})
        )

        children_data = data.get('children', [])
        if isinstance(children_data, list):
            for child in children_data:
                node.children.append(self._recursive_parse(child))
        
        return node

    def _recursive_map(self, bom_node: BOMNode) -> FlutterStateTree:
        """Recursively maps BOM nodes to Flutter State Tree nodes."""
        # Determine interaction logic based on metadata
        interaction_config = {
            "on_click": "SHOW_DETAIL_PANE",
            "on_hover": "HIGHLIGHT_MESH",
            "data_bindings": {
                "stock": bom_node.metadata.get('stock_level', 'N/A'),
                "process": bom_node.metadata.get('process_type', 'Unknown')
            }
        }

        flutter_node = FlutterStateTree(
            widget_id=f"flutter_{bom_node.node_id}",
            widget_type="PartWidget" if bom_node.children else "LeafPartWidget",
            bind_to_cad_guid=self.cad_metadata.get(bom_node.node_id, {}).get("guid", "unknown"),
            properties=interaction_config
        )

        for child in bom_node.children:
            flutter_node.children.append(self._recursive_map(child))

        return flutter_node

    def _build_cache(self, node: BOMNode) -> None:
        """Builds a flat cache of nodes for O(1) lookup."""
        self._node_cache[node.node_id] = node
        for child in node.children:
            self._build_cache(child)

    def _get_material_properties(self, material: MaterialType) -> Dict[str, Any]:
        """Returns rendering properties based on material type."""
        props = {
            MaterialType.METAL: {"roughness": 0.2, "metallic": 1.0, "color": "#A0A0A0"},
            MaterialType.PLASTIC: {"roughness": 0.8, "metallic": 0.0, "color": "#FF5500"},
            MaterialType.GLASS: {"roughness": 0.1, "metallic": 0.0, "transparency": 0.9},
            MaterialType.COMPOSITE: {"roughness": 0.5, "metallic": 0.2, "color": "#333333"}
        }
        return props.get(material, {})

def export_to_json(data: Union[BOMNode, FlutterStateTree], filename: str) -> None:
    """
    Helper function to export dataclasses to JSON files.
    
    Args:
        data: The dataclass instance to export.
        filename: The target filename.
    """
    def asdict_custom(obj):
        if isinstance(obj, Enum):
            return obj.value
        return asdict(obj)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(asdict_custom(data), f, indent=4, default=str)
        logger.info("Successfully exported data to %s", filename)
    except IOError as e:
        logger.error("Failed to write file %s: %s", filename, str(e))

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. Simulate input data from CAD system (BOM) and CAD Metadata (GUIDs)
    raw_bom_data = {
        "id": "root_001",
        "name": "Aero-Engine-Assembly",
        "quantity": 1,
        "material": "metal",
        "metadata": {"process_type": "Final Assembly"},
        "children": [
            {
                "id": "comp_101",
                "name": "Turbine-Blade-Set",
                "quantity": 24,
                "material": "composite",
                "metadata": {"stock_level": 120, "process_type": "Precision Casting"}
            },
            {
                "id": "comp_102",
                "name": "Outer-Casing",
                "quantity": 1,
                "material": "metal",
                "metadata": {"stock_level": 5}
            }
        ]
    }

    cad_meta = {
        "root_001": {"guid": "cad-uuid-9999", "mesh_file": "engine.obj"},
        "comp_101": {"guid": "cad-uuid-1010", "mesh_file": "blade.obj"},
        "comp_102": {"guid": "cad-uuid-1020", "mesh_file": "casing.obj"}
    }

    # 2. Initialize Mapper
    mapper = BOMToFlutterMapper(cad_meta)

    # 3. Parse BOM
    bom_root = mapper.parse_bom_structure(raw_bom_data)

    if bom_root:
        # 4. Generate Flutter View State
        flutter_tree = mapper.generate_flutter_state_tree(bom_root)
        
        # 5. Export configuration for the frontend
        if flutter_tree:
            export_to_json(flutter_tree, "plc_flutter_view_config.json")

        # 6. Simulate Bi-directional Update: User changes material in BOM
        update_cmd = mapper.update_material_linkage("comp_101", MaterialType.METAL)
        print("\n--- 3D Update Command ---")
        print(json.dumps(update_cmd, indent=2))