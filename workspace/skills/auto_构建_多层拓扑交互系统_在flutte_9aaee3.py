"""
Module: multi_layer_topology_system_generator.py
Description: Generates configuration and logic layers for a Flutter-based CAD-level 
             Multi-layer Topology Interaction System. It handles穿透选择, 
             sub-element highlighting, and complex industrial interaction logic.
Author: Senior Python Engineer (AGI Skill)
Version: 1.0.0
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple, Union

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class BoundingBox:
    """Represents a 2D axis-aligned bounding box."""
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def contains_point(self, px: float, py: float) -> bool:
        """Check if a point is inside the bounding box."""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

@dataclass
class TopologyNode:
    """
    Represents a selectable element in the topology tree.
    Example: A data line, an axis, a grid line, or a legend item.
    """
    node_id: str
    node_type: str  # e.g., 'data_series', 'axis', 'grid', 'annotation'
    label: str
    bounding_box: BoundingBox
    meta_data: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    is_selectable: bool = True
    z_index: int = 0

    def to_json_serializable(self) -> Dict:
        obj = asdict(self)
        obj['bounding_box'] = self.bounding_box.to_dict()
        return obj

@dataclass
class InteractionConfig:
    """Configuration for the Flutter interaction engine."""
    enable_marquee_zoom: bool = True
    enable_inverse_selection: bool = True
    hit_tolerance: float = 5.0  # Pixels padding for hit testing
    max_selection_count: int = 100

# --- Core Logic Classes ---

class TopologyTree:
    """
    Manages the hierarchical structure of the graphical elements.
    Acts as the in-memory database for the topology.
    """
    def __init__(self):
        self._nodes: Dict[str, TopologyNode] = {}
        logger.info("TopologyTree initialized.")

    def add_node(self, node: TopologyNode) -> bool:
        """Adds a node to the topology tree."""
        if not isinstance(node, TopologyNode):
            logger.error("Invalid node type provided.")
            return False
        
        if node.node_id in self._nodes:
            logger.warning(f"Node {node.node_id} already exists. Overwriting.")
        
        self._nodes[node.node_id] = node
        logger.debug(f"Node added: {node.node_id} ({node.node_type})")
        return True

    def get_node(self, node_id: str) -> Optional[TopologyNode]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[TopologyNode]:
        return list(self._nodes.values())

    def clear(self):
        self._nodes.clear()
        logger.info("Topology tree cleared.")


class SelectionEngine:
    """
    Implements CAD-level selection logic (Point picking, Marquee selection).
    """
    def __init__(self, tree: TopologyTree, config: InteractionConfig):
        self.tree = tree
        self.config = config
        self._selection_set: set[str] = set()
        logger.info("SelectionEngine initialized with config.")

    def hit_test_point(self, x: float, y: float) -> List[str]:
        """
        Performs a point-based hit test (CAD Picking).
        Returns node IDs sorted by Z-Index (top-most first).
        """
        hits = []
        tolerance = self.config.hit_tolerance
        
        for node in self.tree.get_all_nodes():
            if not node.is_selectable:
                continue
            
            bb = node.bounding_box
            # Expand bounding box by tolerance for easier clicking
            if (bb.x - tolerance <= x <= bb.x + bb.width + tolerance and
                bb.y - tolerance <= y <= bb.y + bb.height + tolerance):
                hits.append(node)
        
        # Sort by Z-Index descending (Top elements first, like CAD layering)
        hits.sort(key=lambda n: n.z_index, reverse=True)
        return [n.node_id for n in hits]

    def perform_marquee_selection(self, rect: BoundingBox, 
                                  current_selection: List[str], 
                                  mode: str = 'new') -> List[str]:
        """
        Performs box/marquee selection.
        
        Args:
            rect (BoundingBox): The selection rectangle coordinates.
            current_selection (List[str]): Currently selected IDs.
            mode (str): 'new', 'add', 'remove' (inverse selection).
            
        Returns:
            List[str]: Updated list of selected IDs.
        """
        if not self.config.enable_marquee_zoom and mode != 'new':
            logger.warning("Marquee zoom disabled, defaulting to logic only.")

        newly_selected = set()
        
        # Find nodes intersecting the rectangle
        for node in self.tree.get_all_nodes():
            bb = node.bounding_box
            # Simple AABB intersection check
            intersects = not (bb.x > rect.x + rect.width or
                              bb.x + bb.width < rect.x or
                              bb.y > rect.y + rect.height or
                              bb.y + bb.height < rect.y)
            if intersects and node.is_selectable:
                newly_selected.add(node.node_id)

        current_set = set(current_selection)
        
        if mode == 'new':
            return list(newly_selected)
        elif mode == 'add':
            return list(current_set.union(newly_selected))
        elif mode == 'remove':
            # Inverse selection logic
            return list(current_set - newly_selected)
        
        return list(current_set)

# --- System Generator (Main API) ---

class TopologySystemBuilder:
    """
    Constructs the configuration and initial state for the Flutter Widget.
    """
    
    @staticmethod
    def build_system_spec(raw_data: List[Dict[str, Any]], 
                          config: Optional[InteractionConfig] = None) -> Dict[str, Any]:
        """
        Converts raw data into a structured topology system ready for Flutter consumption.
        
        Args:
            raw_data: List of graphical element definitions.
            config: Interaction settings.
            
        Returns:
            A dictionary containing 'topology_map', 'config', and 'initial_state'.
        """
        if config is None:
            config = InteractionConfig()
            
        tree = TopologyTree()
        
        # Process raw data into nodes
        for idx, item in enumerate(raw_data):
            try:
                # Validate input
                if 'type' not in item or 'bbox' not in item:
                    logger.warning(f"Skipping item {idx}: missing 'type' or 'bbox'")
                    continue
                
                bbox_data = item['bbox']
                bbox = BoundingBox(
                    x=float(bbox_data['x']),
                    y=float(bbox_data['y']),
                    width=float(bbox_data['w']),
                    height=float(bbox_data['h'])
                )
                
                node = TopologyNode(
                    node_id=item.get('id', str(uuid.uuid4())),
                    node_type=item['type'],
                    label=item.get('label', 'Unnamed'),
                    bounding_box=bbox,
                    z_index=item.get('z_index', 0),
                    meta_data=item.get('meta', {})
                )
                tree.add_node(node)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error processing item {idx}: {e}")
                continue

        # Serialize for output (simulating API response to Flutter)
        output_nodes = [node.to_json_serializable() for node in tree.get_all_nodes()]
        
        system_spec = {
            "system_id": f"sys_{uuid.uuid4().hex[:8]}",
            "config": asdict(config),
            "topology_nodes": output_nodes,
            "flutter_binding": {
                "widget": "InteractiveGraphView",
                "properties": {
                    "supports_pan": True,
                    "supports_zoom": True,
                    "selection_strategy": "cad_precision"
                }
            }
        }
        
        logger.info(f"System spec built with {len(output_nodes)} nodes.")
        return system_spec

# --- Helper Functions ---

def validate_coordinate_input(x: float, y: float) -> bool:
    """
    Validates if coordinates are within reasonable float boundaries.
    Helper function for API boundaries.
    """
    if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
        return False
    # Check for NaN or Infinity which might break geometry logic
    if not (-1e9 < x < 1e9 and -1e9 < y < 1e9):
        return False
    return True

def export_to_json(spec: Dict[str, Any], filepath: str) -> bool:
    """
    Helper to export the generated configuration to a file.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=4, ensure_ascii=False)
        logger.info(f"Spec exported to {filepath}")
        return True
    except IOError as e:
        logger.error(f"File write error: {e}")
        return False

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Prepare Mock Data (Simulating data from a charting library)
    mock_graph_elements = [
        {
            "id": "axis_x_1",
            "type": "axis",
            "label": "X-Axis",
            "bbox": {"x": 50, "y": 250, "w": 400, "h": 20},
            "z_index": 10
        },
        {
            "id": "line_series_1",
            "type": "data_line",
            "label": "Revenue 2023",
            "bbox": {"x": 50, "y": 50, "w": 400, "h": 200},
            "z_index": 50, # Higher Z-Index means on top
            "meta": {"color": "#FF0000", "points": 12}
        },
        {
            "id": "grid_bg",
            "type": "grid",
            "label": "Background Grid",
            "bbox": {"x": 50, "y": 50, "w": 400, "h": 200},
            "z_index": 5
        }
    ]

    # 2. Build the System Specification
    interaction_conf = InteractionConfig(
        enable_marquee_zoom=True,
        hit_tolerance=2.0
    )
    
    print("--- Building Topology System ---")
    system_spec = TopologySystemBuilder.build_system_spec(mock_graph_elements, interaction_conf)
    
    # 3. Display Partial Output
    print(f"System ID: {system_spec['system_id']}")
    print(f"Nodes generated: {len(system_spec['topology_nodes'])}")
    print("Node Types:", [n['node_type'] for n in system_spec['topology_nodes']])

    # 4. Demonstrate Logic (Simulation of Python Backend processing a Flutter event)
    print("\n--- Simulating Interaction ---")
    # Re-instantiate tree for local logic simulation
    local_tree = TopologyTree()
    for item in mock_graph_elements:
        bb = item['bbox']
        node = TopologyNode(
            node_id=item['id'],
            node_type=item['type'],
            label=item['label'],
            bounding_box=BoundingBox(bb['x'], bb['y'], bb['w'], bb['h']),
            z_index=item.get('z_index', 0)
        )
        local_tree.add_node(node)
        
    engine = SelectionEngine(local_tree, interaction_conf)
    
    # User clicks at (60, 60) -> Should hit both grid and line, but selects Line due to Z-Index
    hits = engine.hit_test_point(60, 60)
    print(f"Click at (60, 60) hits: {hits}") # Expected: ['line_series_1', 'grid_bg'] (sorted)
    
    # 5. Export
    export_to_json(system_spec, "topology_config.json")