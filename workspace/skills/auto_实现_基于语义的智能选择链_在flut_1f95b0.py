"""
Module: semantic_selection_chain

This module implements a high-level 'Semantic Smart Selection Chain' logic,
designed to bridge Flutter UI interactions with complex CAD/BIM model data.

In a real-world scenario, this Python backend service would receive hit-test
results from a Flutter frontend. It processes geometric click coordinates
against a spatial index (simulated here) and enriches the selection with
business logic (e.g., penetrating decoration layers to select structural walls)
and metadata retrieval.

Author: AGI System
Version: 1.0.0
"""

import logging
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElementType(Enum):
    """Enumeration of BIM element types for categorization."""
    STRUCTURAL_WALL = "structural_wall"
    DECORATION_LAYER = "decoration_layer"
    DOOR = "door"
    WINDOW = "window"
    FURNITURE = "furniture"
    UNKNOWN = "unknown"

@dataclass
class Point3D:
    """Represents a 3D coordinate in the model space."""
    x: float
    y: float
    z: float

    def __post_init__(self):
        """Validate coordinate data types."""
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.z]):
            raise ValueError("Coordinates must be numeric.")

@dataclass
class BIMElement:
    """
    Represents a semantic entity in the building model.
    
    Attributes:
        id: Unique identifier.
        type: The semantic type of the element.
        layer: The CAD layer name.
        properties: Dictionary of metadata (Material, Dimensions, etc.).
        geometry_bounds: Bounding box for spatial checks.
    """
    id: str
    type: ElementType
    layer: str
    properties: Dict[str, Any]
    geometry_bounds: Tuple[Point3D, Point3D]  # Min point, Max point

class SpatialIndexMock:
    """
    Mock class simulating a spatial index (like an R-Tree or Octree)
    used in CAD engines to find elements at specific coordinates.
    """
    def __init__(self, elements: List[BIMElement]):
        self._elements = elements
        logger.info(f"SpatialIndexMock initialized with {len(elements)} elements.")

    def query_by_point(self, point: Point3D) -> List[BIMElement]:
        """
        Finds elements that intersect with the given point.
        (Simplified logic: checks if point is within bounding box)
        """
        results = []
        for elem in self._elements:
            min_p, max_p = elem.geometry_bounds
            if (min_p.x <= point.x <= max_p.x and
                min_p.y <= point.y <= max_p.y and
                min_p.z <= point.z <= max_p.z):
                results.append(elem)
        return results

class SemanticSelector:
    """
    Core processor for handling semantic selection logic.
    """
    
    def __init__(self, spatial_index: SpatialIndexMock):
        self._index = spatial_index

    def _filter_by_layer_visibility(self, elements: List[BIMElement], visible_layers: List[str]) -> List[BIMElement]:
        """
        Helper function: Filters elements based on visibility settings.
        
        Args:
            elements: List of candidates.
            visible_layers: Layers currently active in the Flutter UI.
            
        Returns:
            Filtered list of elements.
        """
        if not visible_layers:
            return elements
            
        filtered = [e for e in elements if e.layer in visible_layers]
        logger.debug(f"Filtered {len(elements)} elements to {len(filtered)} based on layer visibility.")
        return filtered

    def _resolve_selection_priority(self, elements: List[BIMElement]) -> Optional[BIMElement]:
        """
        Core Algorithm: Smart Selection Chain.
        
        Logic:
        1. If empty, return None.
        2. Priority: Structural > Functional (Doors/Windows) > Decoration.
        3. This simulates 'penetrating' a decoration layer to select the structural wall.
        
        Args:
            elements: List of hit elements.
            
        Returns:
            The semantically 'best' target element.
        """
        if not elements:
            return None
            
        # Simple priority logic
        priority_map = {
            ElementType.STRUCTURAL_WALL: 10,
            ElementType.DOOR: 8,
            ElementType.WINDOW: 8,
            ElementType.FURNITURE: 5,
            ElementType.DECORATION_LAYER: 2,
            ElementType.UNKNOWN: 0
        }
        
        # Sort by priority descending
        sorted_elements = sorted(
            elements, 
            key=lambda e: priority_map.get(e.type, 0), 
            reverse=True
        )
        
        selected = sorted_elements[0]
        logger.info(f"Resolved selection conflict. Selected {selected.id} (Type: {selected.type.value}) among {len(elements)} candidates.")
        return selected

    def process_interaction(self, hit_point: Point3D, visible_layers: List[str]) -> Optional[Dict[str, Any]]:
        """
        Main entry point for the Flutter-triggered selection event.
        
        Args:
            hit_point (Point3D): The 3D coordinate clicked by the user.
            visible_layers (List[str]): List of layers currently visible.
            
        Returns:
            A dictionary containing the formatted payload for the Flutter Overlay,
            or None if no valid target is found.
            
        Example Usage:
            >>> selector = SemanticSelector(index)
            >>> point = Point3D(1.0, 2.5, 0.0)
            >>> result = selector.process_interaction(point, ['Architecture', 'Structural'])
            >>> print(result['element_id'])
        """
        try:
            # 1. Geometric Query
            candidates = self._index.query_by_point(hit_point)
            
            # 2. Visibility Filter
            visible_candidates = self._filter_by_layer_visibility(candidates, visible_layers)
            
            if not visible_candidates:
                logger.warning(f"No visible elements found at {hit_point}")
                return None

            # 3. Semantic Resolution
            target_element = self._resolve_selection_priority(visible_candidates)
            
            if target_element:
                # 4. Format Payload for Flutter
                return self._generate_overlay_payload(target_element)
                
            return None

        except Exception as e:
            logger.error(f"Error processing interaction at {hit_point}: {str(e)}", exc_info=True)
            return None

    def _generate_overlay_payload(self, element: BIMElement) -> Dict[str, Any]:
        """
        Formats the BIM data into a JSON-serializable dictionary suitable for
        a Flutter Overlay card display.
        """
        payload = {
            "element_id": element.id,
            "semantic_type": element.type.value,
            "display_title": f"{element.type.name.replace('_', ' ')} Detail",
            "attributes": element.properties,
            "ui_config": {
                "highlight_color": "#FF5722" if element.type == ElementType.STRUCTURAL_WALL else "#2196F3",
                "show_dimensions": True
            }
        }
        return payload

# --- Mock Data Setup and Execution Example ---

def initialize_demo_environment() -> SpatialIndexMock:
    """
    Sets up a mock environment with sample BIM elements for demonstration.
    """
    # A decoration layer (e.g., Wallpaper)
    decoration = BIMElement(
        id="wall_paper_01",
        type=ElementType.DECORATION_LAYER,
        layer="Interior_Decoration",
        properties={"Material": "Vinyl", "Color": "White"},
        geometry_bounds=(Point3D(0, 0, 0), Point3D(5, 3, 0.1))
    )
    
    # The structural wall behind the decoration
    structural = BIMElement(
        id="struct_wall_conc_01",
        type=ElementType.STRUCTURAL_WALL,
        layer="Structural_Concrete",
        properties={
            "Material": "C40 Concrete", 
            "Fire_Rating": "2 Hours", 
            "Load_Bearing": True,
            "Thickness": "200mm"
        },
        geometry_bounds=(Point3D(0, 0, -0.2), Point3D(5, 3, 0)) # Behind decoration
    )
    
    # A window on the wall
    window = BIMElement(
        id="window_01",
        type=ElementType.WINDOW,
        layer="Fenestration",
        properties={"Material": "Aluminum", "Glass_Type": "Double Glazing"},
        geometry_bounds=(Point3D(2, 1, 0), Point3D(3, 2, 0))
    )
    
    return SpatialIndexMock([decoration, structural, window])

if __name__ == "__main__":
    # 1. Setup
    index = initialize_demo_environment()
    selector = SemanticSelector(index)
    
    # 2. Simulate a user click on the wall (coordinates overlap both decoration and structural)
    click_location = Point3D(1.0, 1.5, 0.0) 
    
    # 3. Process selection
    print("-" * 60)
    print(f"Processing click at: {click_location}")
    result = selector.process_interaction(click_location, visible_layers=["Interior_Decoration", "Structural_Concrete"])
    
    # 4. Output result
    if result:
        print("Selection Result:")
        print(json.dumps(result, indent=2))
        print(f"Successfully selected: {result['element_id']}")
        print("Note: Even though click hit decoration, structural wall was selected due to priority.")
    else:
        print("No element selected.")