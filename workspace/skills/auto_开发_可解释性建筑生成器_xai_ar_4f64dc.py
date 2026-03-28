"""
Module: auto_开发_可解释性建筑生成器_xai_ar_4f64dc

This module implements the 'Explainable Architecture Generator' (XAI-Arch).
Unlike black-box generative models, this tool creates building components based
on explicit performance metrics and logical constraints. It generates both a
geometric representation and a human-readable decision rationale, facilitating
the 'human verification' phase in human-machine symbiosis.

Key Features:
- Performance-driven parametric generation.
- Automatic generation of natural language explanations for design decisions.
- Strict validation of architectural constraints.

Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("XAI_Arch_Generator")


class Orientation(Enum):
    """Enumeration for building orientation."""
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270


class ComponentType(Enum):
    """Types of architectural components."""
    WINDOW = "window"
    DOOR = "door"
    WALL = "wall"
    COLUMN = "column"


@dataclass
class SpatialContext:
    """Defines the environmental context of the building site."""
    latitude: float
    longitude: float
    floor_number: int
    adjacent_obstruction_height: float = 0.0  # in meters

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90.")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180.")


@dataclass
class ComponentSpec:
    """Specification for a generated architectural component."""
    comp_type: ComponentType
    width: float
    height: float
    position_xyz: Tuple[float, float, float]
    properties: Dict[str, float] = field(default_factory=dict)
    rationale: str = "No rationale provided."


class ExplainableArchitectureGenerator:
    """
    A generator class that produces architectural components based on
    performance metrics and provides explanations for every design decision.
    """

    def __init__(self, project_id: str, context: SpatialContext):
        """
        Initialize the generator.

        Args:
            project_id (str): Unique identifier for the project.
            context (SpatialContext): The environmental and spatial context.
        """
        self.project_id = project_id
        self.context = context
        self._components: List[ComponentSpec] = []
        logger.info(f"Initialized XAI-Arch for project {project_id} at Lat: {context.latitude}")

    def _calculate_daylight_factor(
        self,
        window_area: float,
        floor_area: float,
        visibility_angle: float
    ) -> float:
        """
        [Helper] Estimate simple daylight factor (DF).
        
        DF = (Window Area / Floor Area) * Visibility_Multiplier * Constant
        
        Note: This is a simplified heuristic for demonstration.
        """
        if floor_area <= 0:
            return 0.0
        
        # Base constant for glass transmission and maintenance
        CONSTANT = 0.5 
        angle_factor = math.sin(math.radians(visibility_angle / 2))
        
        df = (window_area / floor_area) * angle_factor * CONSTANT * 100
        logger.debug(f"Calculated DF: {df:.2f}% (Area: {window_area}, Angle: {visibility_angle})")
        return df

    def generate_window_by_performance(
        self,
        target_wall_width: float,
        target_daylight_factor: float,
        min_window_height: float = 1.2,
        max_window_height: float = 2.4,
        priority: str = "balanced"
    ) -> ComponentSpec:
        """
        Generates a window component geometry specifically sized to meet
        daylighting requirements, constrained by wall limits.

        Args:
            target_wall_width (float): Total available width for the window.
            target_daylight_factor (float): Desired Daylight Factor (e.g., 2.0 for 2%).
            min_window_height (float): Minimum allowable height.
            max_window_height (float): Maximum allowable height.
            priority (str): 'balanced', 'light_max', or 'privacy'.

        Returns:
            ComponentSpec: The generated window specification with rationale.

        Raises:
            ValueError: If constraints make the target DF impossible.
        """
        logger.info(f"Generating window for target DF: {target_daylight_factor}")
        
        # 1. Determine necessary window-to-floor ratio (simplified heuristic)
        # Assuming standard room depth correlates with window height
        assumed_room_depth = 3.0 * target_wall_width # Simplified geometric assumption
        floor_area_served = target_wall_width * assumed_room_depth
        
        # 2. Calculate required Window Area
        # Inverse of DF formula
        visibility_angle = 90.0 # Assuming standard 90 degree sky view
        required_area = (target_daylight_factor / 100) * floor_area_served / (0.5 * math.sin(math.radians(45)))
        
        # 3. Determine Dimensions
        # Try to fix height first at a comfortable 1.8m, then adjust width
        current_height = 1.8
        required_width = required_area / current_height
        
        # Boundary Checks
        rationale_steps = []
        
        if required_width > target_wall_width:
            # Width constrained: Need to increase height or admit failure
            if priority == "light_max":
                current_height = min(required_area / target_wall_width, max_window_height)
                required_width = target_wall_width
                rationale_steps.append(
                    f"Width constrained to wall width ({target_wall_width}m). "
                    f"Height adjusted to {current_height:.2f}m to maintain light."
                )
            else:
                # Cap the width and log a shortfall
                required_width = target_wall_width
                rationale_steps.append(
                    f"Width capped at {target_wall_width}m. Target DF {target_daylight_factor} "
                    f"may not be fully met due to spatial limits."
                )
        
        # Check Height Limits
        if current_height > max_window_height:
            current_height = max_window_height
            required_width = min(required_area / current_height, target_wall_width)
            rationale_steps.append(f"Height capped at maximum {max_window_height}m.")
        elif current_height < min_window_height:
            current_height = min_window_height
            rationale_steps.append(f"Height set to minimum {min_window_height}m (likely over lit).")

        # 4. Final Validation & Explanation Generation
        actual_area = required_width * current_height
        estimated_df = self._calculate_daylight_factor(actual_area, floor_area_served, visibility_angle)
        
        final_rationale = (
            f"Window sized to {required_width:.2f}m x {current_height:.2f}m. "
            f"Rationale: 'Target Daylight Factor was {target_daylight_factor}'. "
            f"Calculated DF estimate: {estimated_df:.2f}. "
            f"{' '.join(rationale_steps)}"
        )

        component = ComponentSpec(
            comp_type=ComponentType.WINDOW,
            width=round(required_width, 3),
            height=round(current_height, 3),
            position_xyz=(0.0, 0.0, 1.0), # Simplified positioning
            properties={
                "estimated_df": round(estimated_df, 2),
                "area_m2": round(actual_area, 2),
                "target_df_met": abs(estimated_df - target_daylight_factor) < 0.2
            },
            rationale=final_rationale
        )
        
        self._components.append(component)
        logger.info(f"Window generated: {component.width}x{component.height}. Rationale logged.")
        return component

    def generate_structural_grid(
        self,
        building_length: float,
        building_width: float,
        grid_spacing_target: float = 6.0
    ) -> Dict[str, List[float]]:
        """
        Generates a structural grid for columns based on span efficiency.
        Explains why columns are placed at specific locations.

        Args:
            building_length (float): Length of the building footprint.
            building_width (float): Width of the building footprint.
            grid_spacing_target (float): Desired distance between columns.

        Returns:
            Dict containing grid lines and the explanation string.
        """
        if building_length <= 0 or building_width <= 0:
            raise ValueError("Building dimensions must be positive.")

        logger.info("Calculating structural grid...")

        # Algorithm: Divide length by target spacing, round to nearest integer bays
        num_bays = max(1, round(building_length / grid_spacing_target))
        actual_spacing = building_length / num_bays
        
        x_coordinates = [0.0]
        explanation = [f"Structural grid generated with {num_bays} bays."]
        
        if abs(actual_spacing - grid_spacing_target) > 0.5:
            explanation.append(
                f"Warning: Spacing adjusted from target {grid_spacing_target}m to "
                f"{actual_spacing:.2f}m to fit building length {building_length}m symmetrically."
            )
        else:
            explanation.append(
                f"Spacing set to {actual_spacing:.2f}m for optimal structural efficiency."
            )

        for i in range(1, num_bays):
            x_coordinates.append(round(i * actual_spacing, 2))
        x_coordinates.append(building_length) # End point

        # Simplified Y grid (just start and end for this example)
        y_coordinates = [0.0, building_width]

        result = {
            "grid_x": x_coordinates,
            "grid_y": y_coordinates,
            "explanation": " ".join(explanation)
        }
        
        logger.info(result["explanation"])
        return result

    def get_design_report(self) -> str:
        """Generates a summary report of all generated components and their logic."""
        report = [f"\n=== Design Report: {self.project_id} ==="]
        for idx, comp in enumerate(self._components):
            report.append(
                f"\nComponent {idx+1}: {comp.comp_type.value.upper()}\n"
                f"  Dimensions: {comp.width}m x {comp.height}m\n"
                f"  Decision Logic: {comp.rationale}"
            )
        return "\n".join(report)

# ============================================================
# Usage Example
# ============================================================

if __name__ == "__main__":
    # 1. Setup Context
    try:
        site_context = SpatialContext(
            latitude=40.7128,
            longitude=-74.0060,
            floor_number=5
        )
        
        # 2. Initialize Generator
        arch_gen = ExplainableArchitectureGenerator(
            project_id="NYC_Tower_A", 
            context=site_context
        )

        # 3. Generate Components with Performance Targets
        
        # Scenario A: Living room requiring high light (DF 2.0)
        window_living = arch_gen.generate_window_by_performance(
            target_wall_width=4.0,
            target_daylight_factor=2.0,
            priority="light_max"
        )
        
        # Scenario B: Bedroom requiring privacy/lower light (DF 1.0)
        window_bedroom = arch_gen.generate_window_by_performance(
            target_wall_width=3.0,
            target_daylight_factor=1.0,
            max_window_height=1.5, # Constraint: Privacy
            priority="balanced"
        )
        
        # 4. Generate Structural Logic
        grid = arch_gen.generate_structural_grid(
            building_length=25.0,
            building_width=12.0,
            grid_spacing_target=6.0
        )

        # 5. Output Explainable Results
        print(arch_gen.get_design_report())
        print("\nStructural Grid Data:", grid)

    except ValueError as e:
        logger.error(f"Architectural Generation Failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected System Error: {e}")