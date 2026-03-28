"""
LOD (Level of Detail) Context-Aware Routing Framework.

This module implements a resource management system for application routing,
inspired by CAD (Computer-Aided Design) techniques like 'Frustum Culling' and
'LOD (Level of Detail)'. It is designed to prevent OOM (Out of Memory) errors
in applications with infinite navigation stack depth.

Core Concepts:
1.  **Frustum Culling Analogy**: When a user navigates deep into the app (e.g.,
    to a Product Detail page), parent pages (e.g., Home List) become "invisible"
    to the user's focus. This framework treats the active screen as the "View Frustum".
2.  **Resource Unloading**: Resources (heavy data, images, blobs) associated with
    pages outside the current focus are automatically downgraded or unloaded.
3.  **Restoration**: If the user navigates back, the framework attempts to restore
    the resources (from a cache or by flagging a reload).

Author: AGI System
Version: 1.0.0
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LODRouter")


class ResourceState(Enum):
    """Enumeration of possible states for a page's resources."""
    ACTIVE = auto()      # Fully loaded, currently visible.
    SUSPENDED = auto()   # Metadata kept, heavy resources released.
    PRUNED = auto()      # Removed from memory completely (pending reload).


class ResourceType(Enum):
    """Types of resources that can be managed."""
    IMAGE = auto()
    LARGE_BLOB = auto()
    DOM_TREE = auto()


@dataclass
class PageResource:
    """Represents a heavy resource associated with a page."""
    resource_id: str
    resource_type: ResourceType
    size_bytes: int
    payload: Optional[Any] = None  # The actual data (None if unloaded)
    is_loaded: bool = True


@dataclass
class RouteNode:
    """Represents a node in the navigation stack."""
    route_id: str
    path: str
    timestamp: float
    resources: Dict[str, PageResource] = field(default_factory=dict)
    state: ResourceState = ResourceState.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_total_size(self) -> int:
        """Calculates current memory footprint."""
        return sum(r.size_bytes for r in self.resources.values() if r.is_loaded)


class LODNavigationManager:
    """
    Main manager for handling context-aware resource routing.
    
    Implements logic to suspend or prune pages based on the user's current location
    and memory pressure thresholds.
    """

    def __init__(self, memory_threshold_mb: int = 100):
        """
        Initialize the manager.
        
        Args:
            memory_threshold_mb: Memory limit in MB before triggering aggressive cleanup.
        """
        self._stack: List[RouteNode] = []
        self._memory_threshold_bytes = memory_threshold_mb * 1024 * 1024
        self._current_focus_index: int = -1
        logger.info(f"LODNavigationManager initialized with threshold: {memory_threshold_mb}MB")

    def _validate_input(self, path: str, resources: List[PageResource]) -> bool:
        """Validates input data before processing."""
        if not isinstance(path, str) or not path.startswith('/'):
            logger.error(f"Invalid path format: {path}")
            return False
        
        total_res_size = sum(r.size_bytes for r in resources)
        if total_res_size > self._memory_threshold_bytes * 0.8:
            logger.warning(f"Single page size {total_res_size} exceeds 80% of total threshold.")
        
        return True

    def push_route(self, path: str, resources: List[PageResource], metadata: Optional[Dict] = None) -> str:
        """
        Push a new route onto the stack (User navigates forward).
        
        Args:
            path: The route path (e.g., '/home/list/item/123').
            resources: List of resource objects attached to this page.
            metadata: Optional dictionary for page state.
            
        Returns:
            The ID of the newly created route node.
            
        Raises:
            ValueError: If input validation fails.
        """
        if not self._validate_input(path, resources):
            raise ValueError(f"Invalid route data for path {path}")

        route_id = f"route_{int(time.time() * 1000)}"
        new_node = RouteNode(
            route_id=route_id,
            path=path,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        for res in resources:
            new_node.resources[res.resource_id] = res

        self._stack.append(new_node)
        self._current_focus_index = len(self._stack) - 1
        
        logger.info(f"Pushed route: {path} (ID: {route_id})")
        
        # Trigger LOD logic after adding new content
        self._enforce_lod_policy()
        
        return route_id

    def pop_route(self) -> Optional[RouteNode]:
        """
        Pop the top route (User navigates back).
        
        Returns:
            The removed RouteNode or None if stack is empty.
        """
        if not self._stack:
            logger.warning("Attempted to pop from empty stack.")
            return None

        popped_node = self._stack.pop()
        self._current_focus_index = len(self._stack) - 1
        logger.info(f"Popped route: {popped_node.path}")
        
        # When going back, we might want to restore resources for the new top
        if self._current_focus_index >= 0:
            self._restore_suspended_resources(self._stack[self._current_focus_index])
            
        return popped_node

    def _enforce_lod_policy(self) -> None:
        """
        Core LOD Logic: Simulates 'Frustum Culling'.
        Checks memory usage and downgrades pages that are not currently in focus.
        """
        current_usage = self.get_current_memory_usage()
        logger.debug(f"Current memory usage: {current_usage / (1024*1024):.2f} MB")

        if current_usage > self._memory_threshold_bytes:
            logger.warning("Memory threshold exceeded. Starting LOD cleanup.")
            
            # Strategy 1: Suspend parent pages (Simulating distance fog/culling)
            # We iterate backwards from the root, leaving the immediate parent active
            # but suspending grand-parents and beyond.
            
            keep_alive_depth = 1 # How many layers back to keep active
            target_savings = current_usage - (self._memory_threshold_bytes * 0.7) # Aim for 70% capacity
            
            saved_bytes = 0
            
            # Iterate from oldest to newest, but skip the current focus and immediate history
            for i in range(len(self._stack) - (1 + keep_alive_depth)):
                if saved_bytes >= target_savings:
                    break
                
                node = self._stack[i]
                if node.state == ResourceState.ACTIVE:
                    saved_bytes += self._suspend_node_resources(node)

    def _suspend_node_resources(self, node: RouteNode) -> int:
        """
        Helper function to unload heavy resources from a node.
        
        Args:
            node: The RouteNode to suspend.
            
        Returns:
            The amount of memory freed in bytes.
        """
        freed_memory = 0
        for res_id, res in node.resources.items():
            if res.is_loaded and res.resource_type != ResourceType.DOM_TREE:
                # Simulate unloading image/blob data
                freed_memory += res.size_bytes
                res.payload = None
                res.is_loaded = False
                logger.debug(f"Unloaded resource {res_id} from {node.route_id}")
        
        if freed_memory > 0:
            node.state = ResourceState.SUSPENDED
            logger.info(f"Suspended node {node.route_id}. Freed: {freed_memory / 1024:.2f} KB")
            
        return freed_memory

    def _restore_suspended_resources(self, node: RouteNode) -> bool:
        """
        Helper function to attempt restoration of resources (placeholder for reload logic).
        
        Args:
            node: The node becoming active again.
        """
        if node.state == ResourceState.SUSPENDED:
            logger.info(f"Restoring resources for node {node.route_id}...")
            # In a real app, this would trigger async image fetching
            # Here we just simulate flagging them as needing reload
            for res in node.resources.values():
                if not res.is_loaded:
                    # Simulate reload (placeholder)
                    res.payload = f"Reloaded_Data_{res.resource_id}"
                    res.is_loaded = True
            
            node.state = ResourceState.ACTIVE
            return True
        return False

    def get_current_memory_usage(self) -> int:
        """Calculates total memory usage of all active resources in the stack."""
        return sum(node.get_total_size() for node in self._stack)

    def get_stack_status(self) -> List[Dict]:
        """Returns a summary of the current routing stack status."""
        return [
            {
                "path": node.path,
                "state": node.state.name,
                "size_kb": node.get_total_size() / 1024,
                "is_focused": (i == self._current_focus_index)
            }
            for i, node in enumerate(self._stack)
        ]

# Usage Example
if __name__ == "__main__":
    # Initialize manager with a low threshold for demonstration (10MB)
    manager = LODNavigationManager(memory_threshold_mb=10)
    
    # 1. Navigate to Home (Small payload)
    home_res = [PageResource("bg_img", ResourceType.IMAGE, 2 * 1024 * 1024, payload="binary_data")]
    manager.push_route("/home", home_res)
    
    # 2. Navigate to List (Medium payload)
    # Creating dummy data to simulate memory usage
    list_data = "x" * (4 * 1024 * 1024) # 4MB string
    list_res = [PageResource("list_data", ResourceType.LARGE_BLOB, 4 * 1024 * 1024, payload=list_data)]
    manager.push_route("/home/list", list_res)
    
    print("\n--- Status after pushing List ---")
    for s in manager.get_stack_status():
        print(s)
        
    # 3. Navigate to Detail (Large payload)
    # This push should trigger the threshold warning and suspend the Home page resources
    detail_res = [PageResource("hd_image", ResourceType.IMAGE, 5 * 1024 * 1024, payload="huge_binary_data")]
    manager.push_route("/home/list/detail/99", detail_res)
    
    print("\n--- Status after pushing Detail (Triggering LOD) ---")
    # Expected: Home is SUSPENDED, List is ACTIVE (immediate parent), Detail is ACTIVE
    for s in manager.get_stack_status():
        print(s)
        
    # 4. Navigate Back
    manager.pop_route()
    
    print("\n--- Status after popping back to List ---")
    for s in manager.get_stack_status():
        print(s)