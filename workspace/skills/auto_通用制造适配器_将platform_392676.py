"""
AGI Skill: Universal Manufacturing Adapter (UMA)

This module introduces a declarative DSL (Domain Specific Language) for CNC machine 
tool adaptation, inspired by Platform Channels concepts (similar to Flutter routing).
It decouples high-level manufacturing intents from low-level G-code generation, 
allowing users to configure machine behaviors via schemas rather than scripting.

Author: AGI System
Version: 1.0.0
Domain: cross_domain (CAD/CAM + Software Architecture)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UniversalManufacturingAdapter")

# --- Enums and Data Structures ---

class MachineBrand(Enum):
    """Supported machine tool brands."""
    FANUC = auto()
    SIEMENS = auto()
    HEIDENHAIN = auto()
    HAAS = auto()
    CUSTOM = auto()

class AxisType(Enum):
    """Axis definition types."""
    LINEAR = "linear"
    ROTARY = "rotary"

@dataclass
class AxisDefinition:
    """Defines a machine axis."""
    name: str
    axis_type: AxisType
    min_travel: float
    max_travel: float
    is_continuous: bool = False  # For rotary axes

    def __post_init__(self):
        if self.min_travel > self.max_travel:
            raise ValueError(f"Invalid travel range for axis {self.name}")

@dataclass
class MachineIntent:
    """
    High-level manufacturing intent.
    Input format for the adapter.
    """
    command: str  # e.g., 'rapid_move', 'linear_interpolation', 'spindle_on'
    parameters: Dict[str, Any]  # e.g., {'x': 100.0, 'y': 50.0, 'feed_rate': 1200}
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MachineChannel:
    """
    Represents a mapping channel between an Intent and machine-specific code.
    Similar to a 'Route' in web frameworks.
    """
    intent_key: str
    handler: Callable[[Dict[str, Any]], str]
    validator: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""

@dataclass
class GCodeResult:
    """
    Output format of the adapter.
    """
    success: bool
    code_blocks: List[str]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# --- Core Component: The Adapter ---

class UniversalManufacturingAdapter:
    """
    The central adapter class that holds the machine configuration (DSL)
    and dispatches intents to specific handlers.
    """

    def __init__(self, brand: MachineBrand, model_name: str):
        self.brand = brand
        self.model_name = model_name
        self._channels: Dict[str, MachineChannel] = {}
        self._axes: Dict[str, AxisDefinition] = {}
        self._state: Dict[str, Any] = {
            "current_pos": {},
            " coolant": False,
            "spindle_speed": 0
        }
        logger.info(f"Initialized Adapter for {brand.name} - {model_name}")

    def register_axis(self, axis: AxisDefinition) -> None:
        """Registers a physical axis to the machine configuration."""
        if axis.name in self._axes:
            logger.warning(f"Overwriting existing axis definition: {axis.name}")
        self._axes[axis.name.lower()] = axis
        logger.debug(f"Registered axis: {axis.name}")

    def register_channel(self, channel: MachineChannel) -> None:
        """
        Registers a processing channel (Intent -> G-Code mapping).
        """
        if channel.intent_key in self._channels:
            raise ValueError(f"Channel {channel.intent_key} is already registered.")
        self._channels[channel.intent_key] = channel
        logger.debug(f"Registered channel: {channel.intent_key}")

    def _validate_boundaries(self, params: Dict[str, Any]) -> List[str]:
        """Checks if target coordinates are within machine travel limits."""
        errors = []
        for axis_name, value in params.items():
            axis_def = self._axes.get(axis_name.lower())
            if axis_def:
                # Handle continuous rotary axes (no strict min/max check needed modulo 360)
                if axis_def.axis_type == AxisType.ROTARY and axis_def.is_continuous:
                    continue
                
                if not (axis_def.min_travel <= value <= axis_def.max_travel):
                    err_msg = (f"Axis {axis_name} value {value} out of bounds "
                               f"[{axis_def.min_travel}, {axis_def.max_travel}]")
                    errors.append(err_msg)
                    logger.error(err_msg)
        return errors

    def dispatch(self, intent: MachineIntent) -> GCodeResult:
        """
        Core function: Dispatches a high-level intent to the machine specific channel.
        
        Args:
            intent (MachineIntent): The manufacturing operation to perform.
            
        Returns:
            GCodeResult: The generated G-code and status.
        """
        logger.info(f"Dispatching intent: {intent.command}")
        
        # 1. Find Channel
        channel = self._channels.get(intent.command)
        if not channel:
            msg = f"No channel registered for intent: {intent.command}"
            logger.error(msg)
            return GCodeResult(success=False, code_blocks=[], errors=[msg])

        # 2. Validate Parameters (Schema Validation)
        if channel.validator and not channel.validator(intent.parameters):
            msg = f"Validation failed for intent {intent.command}"
            logger.error(msg)
            return GCodeResult(success=False, code_blocks=[], errors=[msg])

        # 3. Boundary Check (Physical Constraints)
        boundary_errors = self._validate_boundaries(intent.parameters)
        if boundary_errors:
            return GCodeResult(success=False, code_blocks=[], errors=boundary_errors)

        # 4. Execute Handler (Generate G-Code)
        try:
            generated_code = channel.handler(intent.parameters)
            
            # Simple formatting check
            if not isinstance(generated_code, str):
                raise TypeError("Handler must return a string (G-code block).")

            logger.debug(f"Generated code: {generated_code.strip()}")
            return GCodeResult(
                success=True, 
                code_blocks=[generated_code.strip()],
                warnings=[]
            )
        except Exception as e:
            logger.exception("Error during G-code generation")
            return GCodeResult(
                success=False, 
                code_blocks=[], 
                errors=[f"Generation Exception: {str(e)}"]
            )

# --- Helper Functions for Common Mappings ---

def create_standard_fanuc_mapping() -> Dict[str, MachineChannel]:
    """
    Helper function to generate a standard set of channels for Fanuc-style machines.
    This acts as a 'Configuration Preset'.
    """
    def rapid_handler(params: Dict[str, Any]) -> str:
        coords = " ".join([f"{k.upper()}{v:.3f}" for k, v in params.items()])
        return f"G00 {coords}"

    def linear_handler(params: Dict[str, Any]) -> str:
        feed = params.pop('feed_rate', 100.0)
        coords = " ".join([f"{k.upper()}{v:.3f}" for k, v in params.items() if k != 'feed_rate'])
        return f"G01 {coords} F{feed:.1f}"

    def spindle_handler(params: Dict[str, Any]) -> str:
        speed = params.get('speed', 0)
        direction = 3 if speed >= 0 else 4 # M3 CW, M4 CCW
        return f"M{direction} S{abs(speed)}"

    return {
        "rapid_move": MachineChannel(
            intent_key="rapid_move",
            handler=rapid_handler,
            description="Rapid positioning (G00)"
        ),
        "linear_move": MachineChannel(
            intent_key="linear_move",
            handler=linear_handler,
            description="Linear interpolation (G01)"
        ),
        "spindle_control": MachineChannel(
            intent_key="spindle_control",
            handler=spindle_handler,
            description="Spindle control"
        )
    }

# --- Main Execution Example ---

if __name__ == "__main__":
    # 1. Setup the Adapter (The DSL Configuration)
    adapter = UniversalManufacturingAdapter(
        brand=MachineBrand.FANUC, 
        model_name="VMC-750"
    )

    # 2. Define Machine Constraints (Boundary Checks)
    adapter.register_axis(AxisDefinition("X", AxisType.LINEAR, -500.0, 500.0))
    adapter.register_axis(AxisDefinition("Y", AxisType.LINEAR, -400.0, 400.0))
    adapter.register_axis(AxisDefinition("Z", AxisType.LINEAR, -300.0, 0.0))
    adapter.register_axis(AxisDefinition("C", AxisType.ROTARY, 0.0, 360.0, is_continuous=True))

    # 3. Load Preset Channels (Declarative Configuration)
    channels = create_standard_fanuc_mapping()
    for ch in channels.values():
        adapter.register_channel(ch)

    # 4. Create Intents (High-level abstraction)
    intent_rapid = MachineIntent(
        command="rapid_move",
        parameters={"x": 10.5, "y": 20.0, "z": -5.0}
    )

    intent_linear = MachineIntent(
        command="linear_move",
        parameters={"x": 50.0, "y": 50.0, "z": -10.0, "feed_rate": 800}
    )

    intent_error = MachineIntent(
        command="rapid_move",
        parameters={"x": 600.0, "y": 0.0} # X > 500 limit
    )

    # 5. Process and Output
    print("-" * 40)
    print("Processing Intent 1 (Rapid):")
    result1 = adapter.dispatch(intent_rapid)
    if result1.success:
        print(f"Code: {result1.code_blocks[0]}")
    
    print("-" * 40)
    print("Processing Intent 2 (Linear):")
    result2 = adapter.dispatch(intent_linear)
    if result2.success:
        print(f"Code: {result2.code_blocks[0]}")

    print("-" * 40)
    print("Processing Intent 3 (Boundary Error):")
    result3 = adapter.dispatch(intent_error)
    if not result3.success:
        print(f"Failed: {result3.errors}")