"""
Responsive CAD Layout System

This module implements a responsive layout engine for CAD drawings by integrating
parametric constraint solving with layout algorithms. It enables CAD drawings to
adapt to different canvas sizes while maintaining engineering constraints.

Input Formats:
- Geometry: List of dictionaries with 'id', 'type', 'params', and 'constraints'
- Canvas: Dictionary with 'width', 'height', and 'unit'

Output Format:
- Dictionary containing 'adjusted_geometry', 'layout_metrics', and 'constraint_report'
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """Enumeration of CAD constraint types."""
    MIN_DISTANCE = "min_distance"
    FIXED_RATIO = "fixed_ratio"
    ALIGNMENT = "alignment"
    SYMMETRY = "symmetry"


@dataclass
class Canvas:
    """Represents the CAD canvas dimensions."""
    width: float
    height: float
    unit: str = "mm"
    
    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Canvas dimensions must be positive")
        if self.unit not in ["mm", "cm", "in"]:
            raise ValueError(f"Unsupported unit: {self.unit}")


@dataclass
class GeometryElement:
    """Represents a CAD geometry element."""
    id: str
    type: str
    params: Dict[str, float]
    constraints: List[Dict]
    
    def validate(self) -> bool:
        """Validate geometry element parameters."""
        if not self.id or not self.type:
            return False
        if self.type not in ["line", "circle", "arc", "polygon"]:
            logger.warning(f"Unknown geometry type: {self.type}")
            return False
        return True


class ConstraintSolver:
    """
    Parametric constraint solver for CAD elements.
    Implements iterative relaxation algorithm for constraint satisfaction.
    """
    
    def __init__(self, tolerance: float = 0.01, max_iterations: int = 100):
        """
        Initialize constraint solver.
        
        Args:
            tolerance: Convergence tolerance for constraint satisfaction
            max_iterations: Maximum iterations for solving
        """
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        logger.info(f"ConstraintSolver initialized with tolerance={tolerance}")
    
    def solve(
        self, 
        elements: List[GeometryElement], 
        canvas: Canvas
    ) -> Tuple[List[GeometryElement], Dict]:
        """
        Solve geometric constraints for responsive layout.
        
        Args:
            elements: List of geometry elements to adjust
            canvas: Target canvas dimensions
            
        Returns:
            Tuple of adjusted elements and constraint report
            
        Raises:
            ValueError: If elements or canvas are invalid
        """
        if not elements:
            raise ValueError("Empty elements list")
        
        if not all(elem.validate() for elem in elements):
            raise ValueError("Invalid geometry elements detected")
        
        logger.info(f"Solving constraints for {len(elements)} elements on {canvas.width}x{canvas.height}{canvas.unit} canvas")
        
        adjusted_elements = []
        constraint_report = {
            "satisfied": 0,
            "violated": 0,
            "iterations": 0,
            "details": []
        }
        
        try:
            # Calculate scaling factor based on canvas change
            scale_factor = self._calculate_scale_factor(elements, canvas)
            
            for iteration in range(self.max_iterations):
                all_satisfied = True
                constraint_report["iterations"] = iteration + 1
                
                for element in elements:
                    adjusted_element = self._apply_constraints(
                        element, scale_factor, canvas
                    )
                    adjusted_elements.append(adjusted_element)
                    
                    # Check constraint satisfaction
                    for constraint in element.constraints:
                        is_satisfied = self._check_constraint(
                            adjusted_element, constraint, canvas
                        )
                        
                        if is_satisfied:
                            constraint_report["satisfied"] += 1
                        else:
                            constraint_report["violated"] += 1
                            all_satisfied = False
                            
                        constraint_report["details"].append({
                            "element_id": element.id,
                            "constraint_type": constraint.get("type"),
                            "satisfied": is_satisfied
                        })
                
                if all_satisfied or iteration == self.max_iterations - 1:
                    logger.info(f"Constraint solving completed in {iteration + 1} iterations")
                    break
                    
                # Prepare for next iteration
                elements = adjusted_elements
                adjusted_elements = []
                
            return adjusted_elements, constraint_report
            
        except Exception as e:
            logger.error(f"Error during constraint solving: {str(e)}")
            raise RuntimeError(f"Constraint solving failed: {str(e)}") from e
    
    def _calculate_scale_factor(
        self, 
        elements: List[GeometryElement], 
        canvas: Canvas
    ) -> float:
        """
        Calculate optimal scale factor for responsive layout.
        
        Args:
            elements: List of geometry elements
            canvas: Target canvas dimensions
            
        Returns:
            Calculated scale factor
        """
        # This is a simplified calculation - real implementation would
        # consider bounding boxes and element distributions
        original_area = sum(
            self._estimate_element_area(elem) for elem in elements
        )
        target_area = canvas.width * canvas.height * 0.7  # Use 70% of canvas
        
        if original_area <= 0:
            return 1.0
            
        scale = math.sqrt(target_area / original_area)
        logger.debug(f"Calculated scale factor: {scale:.4f}")
        return max(0.1, min(scale, 10.0))  # Clamp scale factor
    
    def _estimate_element_area(self, element: GeometryElement) -> float:
        """Estimate the area of a geometry element."""
        if element.type == "circle":
            radius = element.params.get("radius", 1.0)
            return math.pi * radius ** 2
        elif element.type == "line":
            length = element.params.get("length", 1.0)
            return length * 0.1  # Arbitrary width for lines
        return 1.0  # Default area
    
    def _apply_constraints(
        self, 
        element: GeometryElement, 
        scale: float, 
        canvas: Canvas
    ) -> GeometryElement:
        """
        Apply constraints to a single geometry element.
        
        Args:
            element: Geometry element to adjust
            scale: Scale factor to apply
            canvas: Target canvas dimensions
            
        Returns:
            Adjusted geometry element
        """
        adjusted_params = element.params.copy()
        
        # Apply scaling based on element type
        if element.type == "circle":
            adjusted_params["radius"] *= scale
            adjusted_params["center_x"] = min(
                adjusted_params.get("center_x", 0) * scale,
                canvas.width - adjusted_params["radius"]
            )
            adjusted_params["center_y"] = min(
                adjusted_params.get("center_y", 0) * scale,
                canvas.height - adjusted_params["radius"]
            )
            
        elif element.type == "line":
            adjusted_params["length"] *= scale
            adjusted_params["start_x"] = min(
                adjusted_params.get("start_x", 0) * scale,
                canvas.width
            )
            adjusted_params["start_y"] = min(
                adjusted_params.get("start_y", 0) * scale,
                canvas.height
            )
            adjusted_params["end_x"] = min(
                adjusted_params.get("end_x", 0) * scale,
                canvas.width
            )
            adjusted_params["end_y"] = min(
                adjusted_params.get("end_y", 0) * scale,
                canvas.height
            )
            
        elif element.type == "arc":
            adjusted_params["radius"] *= scale
            adjusted_params["center_x"] = min(
                adjusted_params.get("center_x", 0) * scale,
                canvas.width
            )
            adjusted_params["center_y"] = min(
                adjusted_params.get("center_y", 0) * scale,
                canvas.height
            )
            
        return GeometryElement(
            id=element.id,
            type=element.type,
            params=adjusted_params,
            constraints=element.constraints
        )
    
    def _check_constraint(
        self, 
        element: GeometryElement, 
        constraint: Dict, 
        canvas: Canvas
    ) -> bool:
        """
        Check if a constraint is satisfied.
        
        Args:
            element: Geometry element to check
            constraint: Constraint specification
            canvas: Target canvas dimensions
            
        Returns:
            True if constraint is satisfied, False otherwise
        """
        constraint_type = constraint.get("type")
        
        if constraint_type == ConstraintType.MIN_DISTANCE.value:
            min_dist = constraint.get("value", 0)
            if element.type == "circle":
                center_x = element.params.get("center_x", 0)
                center_y = element.params.get("center_y", 0)
                radius = element.params.get("radius", 0)
                
                # Check distance from edges
                left_dist = center_x - radius
                right_dist = canvas.width - center_x - radius
                top_dist = center_y - radius
                bottom_dist = canvas.height - center_y - radius
                
                return all(d >= min_dist for d in [left_dist, right_dist, top_dist, bottom_dist])
                
        elif constraint_type == ConstraintType.FIXED_RATIO.value:
            ratio = constraint.get("value", 1.0)
            if element.type == "line":
                length = element.params.get("length", 0)
                expected = constraint.get("expected_length", 0)
                if expected > 0:
                    return abs(length / expected - ratio) < self.tolerance
                    
        return True  # Default to satisfied for unknown constraints


class ResponsiveCADLayout:
    """
    Main class for responsive CAD layout system.
    Integrates constraint solving with layout algorithms.
    """
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize responsive layout system.
        
        Args:
            tolerance: Constraint satisfaction tolerance
        """
        self.solver = ConstraintSolver(tolerance=tolerance)
        logger.info("ResponsiveCADLayout system initialized")
    
    def process_layout(
        self, 
        geometry_data: List[Dict], 
        canvas_data: Dict,
        output_format: str = "dict"
    ) -> Dict:
        """
        Process CAD layout for responsive adaptation.
        
        Args:
            geometry_data: List of geometry element dictionaries
            canvas_data: Canvas specification dictionary
            output_format: Output format ('dict' or 'geojson')
            
        Returns:
            Dictionary containing adjusted geometry and metrics
            
        Example:
            >>> layout_system = ResponsiveCADLayout()
            >>> geometry = [
            ...     {
            ...         "id": "hole_1",
            ...         "type": "circle",
            ...         "params": {"center_x": 50, "center_y": 50, "radius": 10},
            ...         "constraints": [{"type": "min_distance", "value": 5}]
            ...     }
            ... ]
            >>> canvas = {"width": 200, "height": 200, "unit": "mm"}
            >>> result = layout_system.process_layout(geometry, canvas)
        """
        # Validate input data
        if not isinstance(geometry_data, list) or not geometry_data:
            raise ValueError("geometry_data must be a non-empty list")
            
        if not isinstance(canvas_data, dict):
            raise ValueError("canvas_data must be a dictionary")
        
        try:
            # Convert input data to internal representation
            canvas = Canvas(**canvas_data)
            elements = [
                GeometryElement(
                    id=elem.get("id", ""),
                    type=elem.get("type", ""),
                    params=elem.get("params", {}),
                    constraints=elem.get("constraints", [])
                )
                for elem in geometry_data
            ]
            
            # Solve constraints
            adjusted_elements, constraint_report = self.solver.solve(elements, canvas)
            
            # Convert to output format
            adjusted_geometry = [
                {
                    "id": elem.id,
                    "type": elem.type,
                    "params": elem.params,
                    "constraints": elem.constraints
                }
                for elem in adjusted_elements
            ]
            
            # Calculate layout metrics
            layout_metrics = self._calculate_layout_metrics(
                adjusted_elements, canvas
            )
            
            result = {
                "adjusted_geometry": adjusted_geometry,
                "layout_metrics": layout_metrics,
                "constraint_report": constraint_report,
                "canvas_info": {
                    "width": canvas.width,
                    "height": canvas.height,
                    "unit": canvas.unit
                }
            }
            
            logger.info("Layout processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Layout processing failed: {str(e)}")
            raise RuntimeError(f"Layout processing failed: {str(e)}") from e
    
    def _calculate_layout_metrics(
        self, 
        elements: List[GeometryElement], 
        canvas: Canvas
    ) -> Dict:
        """
        Calculate layout quality metrics.
        
        Args:
            elements: List of adjusted geometry elements
            canvas: Target canvas dimensions
            
        Returns:
            Dictionary of layout metrics
        """
        total_area = sum(
            self.solver._estimate_element_area(elem) for elem in elements
        )
        canvas_area = canvas.width * canvas.height
        
        # Calculate utilization (percentage of canvas used)
        utilization = (total_area / canvas_area) * 100 if canvas_area > 0 else 0
        
        # Calculate density (elements per unit area)
        density = len(elements) / canvas_area if canvas_area > 0 else 0
        
        # Calculate bounding box coverage
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for elem in elements:
            if elem.type == "circle":
                cx = elem.params.get("center_x", 0)
                cy = elem.params.get("center_y", 0)
                r = elem.params.get("radius", 0)
                min_x = min(min_x, cx - r)
                max_x = max(max_x, cx + r)
                min_y = min(min_y, cy - r)
                max_y = max(max_y, cy + r)
            elif elem.type == "line":
                x1 = elem.params.get("start_x", 0)
                y1 = elem.params.get("start_y", 0)
                x2 = elem.params.get("end_x", 0)
                y2 = elem.params.get("end_y", 0)
                min_x = min(min_x, x1, x2)
                max_x = max(max_x, x1, x2)
                min_y = min(min_y, y1, y2)
                max_y = max(max_y, y1, y2)
        
        bbox_width = max_x - min_x if max_x > min_x else 0
        bbox_height = max_y - min_y if max_y > min_y else 0
        coverage = (bbox_width * bbox_height) / canvas_area * 100 if canvas_area > 0 else 0
        
        return {
            "utilization_percent": round(utilization, 2),
            "element_density": round(density, 6),
            "bounding_box_coverage": round(coverage, 2),
            "element_count": len(elements),
            "canvas_aspect_ratio": round(canvas.width / canvas.height, 2) if canvas.height > 0 else 0
        }


# Example usage
if __name__ == "__main__":
    # Sample CAD geometry data
    sample_geometry = [
        {
            "id": "hole_1",
            "type": "circle",
            "params": {"center_x": 50, "center_y": 50, "radius": 10},
            "constraints": [{"type": "min_distance", "value": 5}]
        },
        {
            "id": "slot_1",
            "type": "line",
            "params": {"start_x": 20, "start_y": 100, "end_x": 80, "end_y": 100, "length": 60},
            "constraints": [{"type": "fixed_ratio", "value": 1.0, "expected_length": 60}]
        }
    ]
    
    # Target canvas (A4 to A3 change)
    sample_canvas = {"width": 420, "height": 297, "unit": "mm"}
    
    # Create and run layout system
    layout_system = ResponsiveCADLayout(tolerance=0.05)
    result = layout_system.process_layout(sample_geometry, sample_canvas)
    
    # Print results
    print("Adjusted Geometry:")
    for elem in result["adjusted_geometry"]:
        print(f"  {elem['id']}: {elem['params']}")
    
    print("\nLayout Metrics:")
    for key, value in result["layout_metrics"].items():
        print(f"  {key}: {value}")
    
    print("\nConstraint Report:")
    print(f"  Satisfied: {result['constraint_report']['satisfied']}")
    print(f"  Violated: {result['constraint_report']['violated']}")
    print(f"  Iterations: {result['constraint_report']['iterations']}")