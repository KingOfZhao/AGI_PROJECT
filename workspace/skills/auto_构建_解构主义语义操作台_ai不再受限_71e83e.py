"""
Module: auto_构建_解构主义语义操作台_ai不再受限_71e83e
Description: Constructs a 'Deconstructivist Semantic Operating Platform'.
             This module enables AGI systems to transcend the 'literal meaning' of tools
             (affordances) by analyzing their atomic physical properties. It allows for
             creative recombination of tool functionalities in emergency situations
             (e.g., using a wrench as a hammer) based on a 'Functional Semantic' layer.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Constants and Enums
class PhysicalProperty(Enum):
    """Enumeration of atomic physical properties relevant to tool use."""
    HARDNESS = "hardness"          # Ability to withstand impact
    SHARPNESS = "sharpness"        # Ability to cut or pierce
    WEIGHT = "weight"             # Momentum generation capability
    LENGTH = "length"             # Reach capability
    GRIP = "grip"                 # Surface friction for holding
    CONDUCTIVITY = "conductivity" # Electrical/Thermal transmission

class UrgencyLevel(Enum):
    """Contextual urgency level influencing the matching tolerance."""
    LOW = 1       # Strict literal matching
    MEDIUM = 2    # Flexible matching
    HIGH = 3      # Emergency: Creative/Destructive matching allowed

# 3. Data Structures
@dataclass
class ToolProfile:
    """Represents the physical and semantic profile of a tool."""
    tool_id: str
    name: str
    literal_function: str
    # Properties mapped to a normalized 0.0-1.0 scale
    physical_properties: Dict[PhysicalProperty, float] 
    is_available: bool = True

    def __post_init__(self):
        if not self.validate_properties():
            raise ValueError(f"Invalid property values for tool {self.name}")

    def validate_properties(self) -> bool:
        """Ensure all physical properties are within [0.0, 1.0]."""
        for prop, value in self.physical_properties.items():
            if not (0.0 <= value <= 1.0):
                logger.error(f"Validation Error: Property {prop.value} out of range for {self.name}")
                return False
        return True

@dataclass
class TaskRequirement:
    """Defines the physical requirements of a task, independent of specific tools."""
    task_id: str
    description: str
    required_properties: Dict[PhysicalProperty, float]
    required_threshold: float = 0.7  # Minimum match score to consider a tool valid

# 4. Core Class
class DeconstructivistSemanticOS:
    """
    The core Operating System for the Deconstructivist Semantic Platform.
    Manages the library of tools and performs atomic recombination logic.
    """

    def __init__(self):
        self._tool_registry: Dict[str, ToolProfile] = {}
        logger.info("Deconstructivist Semantic Operating Platform Initialized.")

    def register_tool(self, tool: ToolProfile) -> bool:
        """Registers a tool profile into the system."""
        if not isinstance(tool, ToolProfile):
            logger.error("Invalid object type provided for registration.")
            return False
        
        self._tool_registry[tool.tool_id] = tool
        logger.info(f"Tool Registered: {tool.name} (ID: {tool.tool_id})")
        return True

    def decompose_tool_semantics(self, tool_id: str) -> Optional[Dict[str, float]]:
        """
        Core Function 1: Semantic Decomposition.
        Breaks down a tool's identity into its atomic physical vector.
        
        Args:
            tool_id (str): The unique identifier of the tool.
            
        Returns:
            Optional[Dict[str, float]]: A dictionary of property strengths, or None if not found.
        """
        tool = self._tool_registry.get(tool_id)
        if not tool:
            logger.warning(f"Tool ID {tool_id} not found in registry.")
            return None
        
        logger.debug(f"Decomposing semantics for {tool.name}: {tool.physical_properties}")
        return {prop.value: val for prop, val in tool.physical_properties.items()}

    def resolve_emergency_tool(
        self, 
        requirement: TaskRequirement, 
        urgency: UrgencyLevel
    ) -> Tuple[Optional[ToolProfile], float, str]:
        """
        Core Function 2: Cross-Domain Tool Resolution.
        Finds the best tool based on physical properties rather than name,
        allowing creative re-use in emergencies.
        
        Args:
            requirement (TaskRequirement): The physical requirements of the task.
            urgency (UrgencyLevel): The context urgency (affects tolerance).
            
        Returns:
            Tuple containing:
            - The best matching ToolProfile (or None).
            - The match confidence score (0.0-1.0).
            - A semantic reasoning string explaining the choice.
        """
        best_match: Optional[ToolProfile] = None
        highest_score = 0.0
        reasoning = ""

        # Dynamic threshold adjustment based on urgency
        threshold = requirement.required_threshold
        if urgency == UrgencyLevel.HIGH:
            threshold = max(0.4, threshold - 0.3) # Allow lower quality matches in emergencies
            logger.warning("EMERGENCY MODE: Lowering physical property constraints.")
        
        if urgency == UrgencyLevel.MEDIUM:
            threshold = max(0.5, threshold - 0.1)

        for tool in self._tool_registry.values():
            if not tool.is_available:
                continue
            
            score = self._calculate_semantic_similarity(
                tool.physical_properties, 
                requirement.required_properties
            )

            if score > highest_score:
                highest_score = score
                best_match = tool

        if best_match and highest_score >= threshold:
            # Generate reasoning
            if best_match.literal_function.lower() in requirement.description.lower():
                reasoning = f"Literal match found: Using {best_match.name} as intended."
            else:
                reasoning = (
                    f"CREATIVE RECOMBINATION: Using {best_match.name} (normally a {best_match.literal_function}) "
                    f"to satisfy task '{requirement.description}' via physical property overlap "
                    f"(Score: {highest_score:.2f})."
                )
            logger.info(f"Resolution Success: {reasoning}")
            return best_match, highest_score, reasoning
        
        logger.error("No suitable tool found even with relaxed constraints.")
        return None, 0.0, "Resolution Failed: Semantic gap too wide."

    # 5. Helper Functions
    def _calculate_semantic_similarity(
        self, 
        tool_props: Dict[PhysicalProperty, float], 
        req_props: Dict[PhysicalProperty, float]
    ) -> float:
        """
        Helper Function: Calculates the cosine similarity or weighted overlap
        between tool properties and task requirements.
        
        Note: For this skill, we use a weighted euclidean distance normalized to [0,1].
        """
        distance_sq = 0.0
        relevant_dims = 0
        
        for prop, req_val in req_props.items():
            tool_val = tool_props.get(prop, 0.0)
            # We penalize if tool is LESS capable than required, but reward if MORE capable
            # Here we use simple difference, but logic could be: if tool_val < req_val: penalty
            # For simplicity, treating it as vector proximity.
            diff = abs(tool_val - req_val)
            distance_sq += (diff ** 2)
            relevant_dims += 1
            
        if relevant_dims == 0:
            return 0.0
            
        # Normalize distance to similarity score (simple implementation)
        # Max possible distance per dimension is 1.0
        rmse = (distance_sq / relevant_dims) ** 0.5
        similarity = 1.0 - rmse
        
        return max(0.0, similarity)

# 6. Usage Example and Data Validation
def _run_demo():
    """
    Internal demonstration of the Deconstructivist Semantic Platform.
    """
    print("--- Starting System Demo ---")
    
    # Initialize OS
    os_platform = DeconstructivistSemanticOS()
    
    # Define Tools
    wrench = ToolProfile(
        tool_id=str(uuid.uuid4()),
        name="Heavy Wrench",
        literal_function="Fastening/Loosening Nuts",
        physical_properties={
            PhysicalProperty.HARDNESS: 0.9,
            PhysicalProperty.WEIGHT: 0.8,
            PhysicalProperty.GRIP: 0.9,
            PhysicalProperty.LENGTH: 0.4,
            PhysicalProperty.SHARPNESS: 0.1
        }
    )
    
    screwdriver = ToolProfile(
        tool_id=str(uuid.uuid4()),
        name="Flathead Screwdriver",
        literal_function="Driving Screws",
        physical_properties={
            PhysicalProperty.HARDNESS: 0.6,
            PhysicalProperty.WEIGHT: 0.2,
            PhysicalProperty.GRIP: 0.3,
            PhysicalProperty.LENGTH: 0.5,
            PhysicalProperty.SHARPNESS: 0.4 # Slightly sharp tip
        }
    )

    # Register Tools
    os_platform.register_tool(wrench)
    os_platform.register_tool(screwdriver)

    # Scenario 1: Standard Task (Tightening a screw)
    task_screw = TaskRequirement(
        task_id="task_001",
        description="Tighten a screw",
        required_properties={
            PhysicalProperty.GRIP: 0.8, # Need to hold it
            PhysicalProperty.HARDNESS: 0.5,
            PhysicalProperty.SHARPNESS: 0.0 # Need flat tip effectively
        }
    )
    
    # Scenario 2: Emergency Task (Hammering a nail, but no hammer available)
    task_hammer = TaskRequirement(
        task_id="task_002",
        description="Hammer a nail",
        required_properties={
            PhysicalProperty.HARDNESS: 0.8,
            PhysicalProperty.WEIGHT: 0.7, # Need mass
            PhysicalProperty.GRIP: 0.5
        }
    )

    print("\n[Scenario 1: Routine Task]")
    match, score, reason = os_platform.resolve_emergency_tool(task_screw, UrgencyLevel.LOW)
    if match:
        print(f"Selected Tool: {match.name}")
        print(f"Reasoning: {reason}")
        
    print("\n[Scenario 2: Emergency / Cross-Domain Task]")
    match, score, reason = os_platform.resolve_emergency_tool(task_hammer, UrgencyLevel.HIGH)
    if match:
        print(f"Selected Tool: {match.name}")
        print(f"Reasoning: {reason}")
        print(f"Confidence Score: {score:.2f}")

if __name__ == "__main__":
    _run_demo()