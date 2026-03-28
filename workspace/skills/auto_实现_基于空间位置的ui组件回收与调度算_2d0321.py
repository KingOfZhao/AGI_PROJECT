"""
Module: spatial_ui_recycler.py

This module implements a high-performance UI component recycling and scheduling algorithm
based on spatial positioning (2D Plane). It is designed for scenarios involving massive
UI interactions in map applications, infinite canvases, or large 2D charts.

The core logic treats UI components as spatial entities with bounding boxes. It utilizes
a Grid-based Spatial Hashing algorithm (a simplified CAD spatial index) to query
components intersecting with the current viewport (Camera). Only these components are
rendered or instantiated, drastically reducing the DOM/Canvas node count.

Author: AGI System
Version: 2.0.3
"""

import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class Rectangle:
    """
    Represents a 2D Axis-Aligned Bounding Box (AABB).
    
    Attributes:
        x (float): The x-coordinate of the top-left corner.
        y (float): The y-coordinate of the top-left corner.
        width (float): The width of the rectangle.
        height (float): The height of the rectangle.
    """
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def intersects(self, other: 'Rectangle') -> bool:
        """Checks if this rectangle intersects with another rectangle."""
        return not (
            self.right < other.x or
            self.x > other.right or
            self.bottom < other.y or
            self.y > other.bottom
        )

@dataclass
class UIComponent:
    """
    Represents a UI component with spatial properties.
    """
    id: str
    bounds: Rectangle
    data: Dict[str, Any] = field(default_factory=dict)
    is_visible: bool = False

class SpatialHashGrid:
    """
    A spatial partitioning data structure to efficiently query objects in a 2D space.
    This acts as the "CAD Spatial Index" for the UI components.
    """
    def __init__(self, cell_size: float = 256.0):
        """
        Initialize the grid.
        
        Args:
            cell_size (float): The size of each grid cell. Should be tuned based on
                               average component size vs viewport size.
        """
        if cell_size <= 0:
            raise ValueError("Cell size must be positive.")
        self.cell_size = cell_size
        self.grid: Dict[str, List[UIComponent]] = {}
        logger.info(f"SpatialHashGrid initialized with cell size: {cell_size}")

    def _get_cell_key(self, x: float, y: float) -> str:
        """Generates a unique key for the cell containing the point (x, y)."""
        cell_x = int(x // self.cell_size)
        cell_y = int(y // self.cell_size)
        return f"{cell_x}:{cell_y}"

    def insert(self, component: UIComponent) -> None:
        """
        Inserts a component into the spatial grid.
        The component is added to all cells its bounding box overlaps.
        """
        b = component.bounds
        
        # Data Validation
        if b.width < 0 or b.height < 0:
            logger.warning(f"Component {component.id} has negative dimensions. Skipping.")
            return

        # Determine range of cells
        start_x = int(b.x // self.cell_size)
        end_x = int(b.right // self.cell_size)
        start_y = int(b.y // self.cell_size)
        end_y = int(b.bottom // self.cell_size)

        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                key = f"{x}:{y}"
                if key not in self.grid:
                    self.grid[key] = []
                self.grid[key].append(component)

    def query(self, viewport: Rectangle) -> Set[UIComponent]:
        """
        Retrieves all components that potentially intersect with the viewport.
        """
        candidates: Set[UIComponent] = set()
        
        start_x = int(viewport.x // self.cell_size)
        end_x = int(viewport.right // self.cell_size)
        start_y = int(viewport.y // self.cell_size)
        end_y = int(viewport.bottom // self.cell_size)

        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                key = f"{x}:{y}"
                if key in self.grid:
                    candidates.update(self.grid[key])
                    
        return candidates

class UISpatialManager:
    """
    Main controller for managing UI component lifecycle based on spatial position.
    Handles the recycling, instantiation, and destruction logic.
    """
    def __init__(self, grid_cell_size: float = 500.0):
        self.spatial_index = SpatialHashGrid(cell_size=grid_cell_size)
        self.component_registry: Dict[str, UIComponent] = {}
        self.active_components: Set[str] = set()
        
    def register_component(self, id: str, x: float, y: float, w: float, h: float, **metadata) -> None:
        """
        Registers a static data source as a renderable UI component.
        
        Input Format:
            id: Unique identifier
            x, y: World coordinates
            w, h: Dimensions
            metadata: Arbitrary data payload
        """
        if id in self.component_registry:
            logger.warning(f"Duplicate component ID detected: {id}. Overwriting.")
            
        bounds = Rectangle(x, y, w, h)
        comp = UIComponent(id=id, bounds=bounds, data=metadata)
        
        self.component_registry[id] = comp
        self.spatial_index.insert(comp)
        logger.debug(f"Registered component {id} at ({x},{y})")

    def update_viewport(self, viewport_bounds: Rectangle) -> List[str]:
        """
        Core Scheduling Algorithm. Determines which components should be visible
        based on the current viewport.
        
        Args:
            viewport_bounds (Rectangle): The current visible area in world coordinates.
            
        Returns:
            List[str]: List of component IDs that are currently visible.
        
        Output Format:
            List of active IDs to be rendered by the UI layer.
        """
        # 1. Broad Phase: Query Spatial Index
        candidates = self.spatial_index.query(viewport_bounds)
        
        current_visible_ids: Set[str] = set()
        
        # 2. Narrow Phase: Exact Intersection Check
        for comp in candidates:
            if comp.bounds.intersects(viewport_bounds):
                current_visible_ids.add(comp.id)
                
                # Logic: Component just entered view
                if comp.id not in self.active_components:
                    self._on_component_enter(comp)
                    
        # 3. Logic: Components that left the view
        ids_to_remove = self.active_components - current_visible_ids
        for comp_id in ids_to_remove:
            comp = self.component_registry.get(comp_id)
            if comp:
                self._on_component_leave(comp)
                
        # Update state
        self.active_components = current_visible_ids
        
        return list(self.active_components)

    def _on_component_enter(self, component: UIComponent) -> None:
        """
        Helper function to handle component initialization/recycling.
        In a real engine, this would grab a node from the object pool.
        """
        component.is_visible = True
        # logger.info(f"Component {component.id} entered viewport. Rendering...")
        # Simulate rendering cost or pool retrieval here
        
    def _on_component_leave(self, component: UIComponent) -> None:
        """
        Helper function to handle component destruction/recycling.
        In a real engine, this would return the node to the object pool.
        """
        component.is_visible = False
        # logger.info(f"Component {component.id} left viewport. Recycling...")
        # Simulate cleanup here

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Initialize Manager
    manager = UISpatialManager(grid_cell_size=100.0)
    
    # 2. Generate massive amount of data (Simulating a Map or Infinite List)
    # Let's place 5000 items in a grid pattern from (0,0) to (10000, 10000)
    print("Registering 5000 components...")
    for i in range(5000):
        x = (i % 100) * 110.0
        y = (i // 100) * 110.0
        manager.register_component(f"item_{i}", x, y, 100.0, 100.0, label=f"Node {i}")
        
    # 3. Simulate Camera Movement
    # Viewport is looking at the top-left corner (0,0 to 800x600)
    viewport_1 = Rectangle(0, 0, 800, 600)
    print(f"\nUpdating viewport to: {viewport_1}")
    visible_items = manager.update_viewport(viewport_1)
    print(f"Visible components count: {len(visible_items)}") 
    # Expected: approx 30-40 items depending on grid alignment
    
    # 4. Simulate Camera Panning (Jump to center)
    viewport_2 = Rectangle(5000, 5000, 800, 600)
    print(f"\nUpdating viewport to: {viewport_2}")
    visible_items = manager.update_viewport(viewport_2)
    print(f"Visible components count: {len(visible_items)}")
    
    # 5. Boundary Check
    assert "item_0" not in visible_items, "Item 0 should not be visible in center view"
    print("Assertion passed: Item 0 is recycled.")