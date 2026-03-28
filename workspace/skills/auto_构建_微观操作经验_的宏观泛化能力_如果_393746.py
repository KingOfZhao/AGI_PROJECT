"""
Module: macro_generalization_from_micro_skills
Description: This module implements a structural node decomposition and synthesis engine
             for robotic skills. It demonstrates how an AGI system can decompose a learned
             skill (e.g., tightening a specific screw) into structural parameters (force, angle, material)
             and synthesize a new skill (e.g., tightening a different type of screw) via
             parameter mutation and constraint satisfaction.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class SkillParameter:
    """Represents a single parameter of a skill (a node in the decomposition graph)."""
    name: str
    value: float
    unit: str
    min_val: float
    max_val: float

    def __post_init__(self):
        if not (self.min_val <= self.value <= self.max_val):
            logger.warning(f"Value {self.value} for {self.name} is out of bounds [{self.min_val}, {self.max_val}]. Clamping.")
            self.value = max(self.min_val, min(self.max_val, self.value))

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "value": self.value, "unit": self.unit,
            "min": self.min_val, "max": self.max_val
        }

@dataclass
class ManipulationSkill:
    """Represents a complete robotic manipulation skill."""
    name: str
    description: str
    parameters: Dict[str, SkillParameter] = field(default_factory=dict)

    def get_parameter_vector(self) -> List[float]:
        return [p.value for p in self.parameters.values()]

    def __str__(self) -> str:
        params_str = "\n  ".join([f"{k}: {v.value} {v.unit}" for k, v in self.parameters.items()])
        return f"Skill: {self.name}\n  {self.description}\n  Parameters:\n  {params_str}"

# --- Custom Exceptions ---

class SkillSynthesisError(Exception):
    """Raised when skill synthesis fails due to constraint violations."""
    pass

class DecompositionError(Exception):
    """Raised when a skill cannot be decomposed into required nodes."""
    pass

# --- Core Functions ---

def decompose_skill_to_nodes(skill: ManipulationSkill, required_nodes: List[str]) -> Dict[str, SkillParameter]:
    """
    Extracts specific structural nodes (parameters) from a skill.
    
    Args:
        skill (ManipulationSkill): The source skill.
        required_nodes (List[str]): List of parameter names required for the abstraction.
    
    Returns:
        Dict[str, SkillParameter]: A dictionary of extracted parameters.
    
    Raises:
        DecompositionError: If a required node is missing in the source skill.
    """
    logger.info(f"Decomposing skill '{skill.name}' into nodes: {required_nodes}")
    extracted = {}
    
    for node_name in required_nodes:
        if node_name not in skill.parameters:
            logger.error(f"Missing node {node_name} in skill {skill.name}")
            raise DecompositionError(f"Source skill lacks required parameter node: {node_name}")
        
        extracted[node_name] = skill.parameters[node_name]
        
    logger.info("Decomposition successful.")
    return extracted

def synthesize_skill_from_abstract(
    base_nodes: Dict[str, SkillParameter], 
    target_config: Dict[str, float],
    new_skill_name: str
) -> ManipulationSkill:
    """
    Synthesizes a new skill by applying target configuration to abstract nodes.
    Handles the 'Generalization' aspect.
    
    Args:
        base_nodes (Dict[str, SkillParameter]): The abstract structure from the source.
        target_config (Dict[str, float]): New values for specific parameters (mutations).
        new_skill_name (str): Name of the generated skill.
    
    Returns:
        ManipulationSkill: The new, synthesized skill instance.
    """
    logger.info(f"Synthesizing new skill '{new_skill_name}'...")
    new_params = {}
    
    # Copy base structure and apply mutations
    for name, param in base_nodes.items():
        # Start with base value
        new_val = param.value
        
        # Apply mutation if specified
        if name in target_config:
            logger.debug(f"Mutating node '{name}': {param.value} -> {target_config[name]}")
            new_val = target_config[name]
            
        # Create new parameter object (validates bounds automatically via __post_init__)
        new_params[name] = SkillParameter(
            name=name,
            value=new_val,
            unit=param.unit,
            min_val=param.min_val,
            max_val=param.max_val
        )
        
    # Create new skill
    new_skill = ManipulationSkill(
        name=new_skill_name,
        description=f"Auto-generated skill derived from structural abstraction.",
        parameters=new_params
    )
    
    # Verify structural integrity (e.g., torque vs friction logic)
    if not _validate_physical_constraints(new_skill):
        raise SkillSynthesisError("Generated skill violates physical constraints.")
        
    return new_skill

# --- Helper Functions ---

def _validate_physical_constraints(skill: ManipulationSkill) -> bool:
    """
    Internal helper to validate if the synthesized parameters make physical sense.
    Example: High torque on soft material might cause damage.
    """
    logger.debug("Validating physical constraints...")
    
    # Boundary checks are handled by SkillParameter, this checks logic relations
    if "max_torque" in skill.parameters and "material_hardness" in skill.parameters:
        torque = skill.parameters["max_torque"].value
        hardness = skill.parameters["material_hardness"].value
        
        # Arbitrary rule: Torque > 10 on hardness < 3 is dangerous
        if torque > 10.0 and hardness < 3.0:
            logger.warning(f"Constraint violation: High torque ({torque}) on soft material ({hardness}).")
            return False
            
    return True

def calculate_dynamic_motion_profile(skill: ManipulationSkill) -> Tuple[List[float], List[float]]:
    """
    Generates a time-series profile for the robot controller based on skill parameters.
    Returns tuples of (time, position/force).
    """
    steps = 10
    time_profile = [i * 0.1 for i in range(steps)]
    
    # Simple linear interpolation example based on 'rotation_angle'
    target_angle = skill.parameters.get("rotation_angle")
    if not target_angle:
        return time_profile, [0.0] * steps
        
    motion_profile = [i * (target_angle.value / steps) for i in range(steps)]
    return time_profile, motion_profile

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define the 'Source Skill' (Micro Experience A)
    skill_screw_a = ManipulationSkill(
        name="Tighten_Steel_Screw_A",
        description="Standard phillips head steel screw tightening",
        parameters={
            "max_torque": SkillParameter("max_torque", 5.0, "Nm", 0.0, 50.0),
            "rotation_angle": SkillParameter("rotation_angle", 360.0, "degrees", 0.0, 1080.0),
            "material_hardness": SkillParameter("material_hardness", 8.0, "mohs", 1.0, 10.0),
            "approach_speed": SkillParameter("approach_speed", 0.5, "m/s", 0.1, 2.0)
        }
    )
    
    print(f"--- Source Skill ---\n{skill_screw_a}\n")

    try:
        # 2. Decompose into Abstract Nodes (Feature Extraction)
        required_abstraction = ["max_torque", "rotation_angle", "material_hardness"]
        abstract_nodes = decompose_skill_to_nodes(skill_screw_a, required_abstraction)

        # 3. Define Target Configuration (The 'B' Scenario)
        # Scenario: We need to tighten a softer, plastic screw that requires less rotation but same speed logic
        # We want to change: Material (softer), Torque (lower), Angle (less)
        target_mutations = {
            "max_torque": 1.5,          # Reduce torque for plastic
            "material_hardness": 2.0,   # Plastic is soft
            "rotation_angle": 180.0     # Only half turn needed
        }

        # 4. Synthesize New Skill
        skill_screw_b = synthesize_skill_from_abstract(
            base_nodes=abstract_nodes,
            target_config=target_mutations,
            new_skill_name="Tighten_Plastic_Screw_B"
        )

        print(f"--- Synthesized Skill (Generalized) ---\n{skill_screw_b}\n")

        # 5. Generate Motion Data
        t, y = calculate_dynamic_motion_profile(skill_screw_b)
        print(f"Motion Profile Generated: {len(t)} steps, final angle {y[-1]} deg.")

    except DecompositionError as de:
        logger.error(f"Failed to understand source skill: {de}")
    except SkillSynthesisError as se:
        logger.error(f"Failed to create new skill: {se}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")