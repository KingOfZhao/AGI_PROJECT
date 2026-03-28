"""
Module: adaptive_skill_engine.py
Description: Implements a dynamic skill execution system for AGI/Robotics.
             This module transforms static skill definitions into environment-adaptive
             behaviors by modulating sub-node parameters based on real-time
             sensory feedback (e.g., weight, friction).

Author: AGI System Core Team
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptiveSkillEngine")

# --- Constants and Limits ---
MAX_GRIP_FORCE_NEWTONS = 100.0
MAX_APPROACH_SPEED_MS = 2.0
MIN_FRICTION_COEFF = 0.05
MAX_OBJECT_WEIGHT_KG = 50.0

class SkillExecutionError(Exception):
    """Custom exception for skill execution failures."""
    pass

class ParameterValidationError(SkillExecutionError):
    """Exception for invalid input parameters."""
    pass

@dataclass
class EnvironmentContext:
    """
    Describes the current state of the operational environment.
    
    Attributes:
        target_mass_kg (float): Mass of the target object in kilograms.
        friction_coeff (float): Estimated friction coefficient (0.0 to 1.0+).
        object_fragility (float): Fragility score (0.0 robust to 1.0 fragile).
        is_slippery (bool): Flag for low-friction surfaces.
    """
    target_mass_kg: float
    friction_coeff: float
    object_fragility: float = 0.0
    is_slippery: bool = False

    def __post_init__(self):
        """Validate data after initialization."""
        if self.target_mass_kg < 0:
            raise ParameterValidationError("Mass cannot be negative.")
        if not (0 < self.friction_coeff <= 2.0):
            logger.warning(f"Unusual friction coefficient: {self.friction_coeff}")

@dataclass
class SubSkillNode:
    """
    Represents a dynamic sub-step within a skill.
    
    Attributes:
        name (str): Identifier for the sub-skill.
        base_weight (float): Default importance/weight of this node.
        params (Dict[str, Any]): Executable parameters (e.g., speed, force).
    """
    name: str
    base_weight: float
    params: Dict[str, Any] = field(default_factory=dict)
    dynamic_weight: float = 0.0  # Calculated at runtime

class AdaptiveSkill:
    """
    A skill node capable of modifying its internal behavior based on context.
    
    This class encapsulates the logic for 'One State, Many Forms' execution.
    It takes static definitions and morphs them using environmental data.
    """

    def __init__(self, skill_id: str, name: str, sub_nodes: List[SubSkillNode]):
        """
        Initialize the AdaptiveSkill.
        
        Args:
            skill_id (str): Unique identifier.
            name (str): Human-readable name.
            sub_nodes (List[SubSkillNode]): List of static sub-components.
        """
        self.skill_id = skill_id
        self.name = name
        self.sub_nodes = sub_nodes
        self._execution_log: List[str] = []
        logger.info(f"Skill '{name}' initialized with {len(sub_nodes)} sub-nodes.")

    def _calculate_adaptive_weights(self, context: EnvironmentContext) -> None:
        """
        Core internal logic: Adjust sub-node weights based on physics.
        
        Logic:
        - If friction is low, increase weight of 'Grip Force' and decrease 'Speed'.
        - If mass is high, increase 'Arm Stiffness'.
        """
        for node in self.sub_nodes:
            # Reset to base
            node.dynamic_weight = node.base_weight
            
            # Adaptive Logic: Friction Handling
            if context.friction_coeff < 0.4:  # Slippery
                if 'grip' in node.name.lower():
                    # Exponential increase in importance for grip
                    node.dynamic_weight *= (1.0 + (0.4 - context.friction_coeff) * 2.0)
                    node.params['force_multiplier'] = 1.5
                    logger.debug(f"Boosting grip weight for slippery surface: {node.name}")
                if 'move' in node.name.lower():
                    # Reduce speed importance to ensure stability
                    node.dynamic_weight *= 0.8
                    
            # Adaptive Logic: Weight Handling
            if context.target_mass_kg > 5.0:
                if 'lift' in node.name.lower():
                    node.dynamic_weight *= 1.2
                    node.params['torque_limit'] = min(1.0, context.target_mass_kg / 10.0)

            # Boundary check for weights
            node.dynamic_weight = max(0.0, min(5.0, node.dynamic_weight))

    def _validate_context(self, context: EnvironmentContext) -> bool:
        """
        Validates environment parameters against hardware limits.
        
        Returns:
            bool: True if execution is safe.
        
        Raises:
            ParameterValidationError: If limits are exceeded.
        """
        if context.target_mass_kg > MAX_OBJECT_WEIGHT_KG:
            raise ParameterValidationError(
                f"Object mass {context.target_mass_kg}kg exceeds max payload {MAX_OBJECT_WEIGHT_KG}kg."
            )
        return True

    def execute(self, context: EnvironmentContext) -> Dict[str, Any]:
        """
        Executes the skill using the provided environmental context.
        
        Args:
            context (EnvironmentContext): The current perception data.
            
        Returns:
            Dict[str, Any]: Execution report containing status and modified params.
        
        Raises:
            SkillExecutionError: If the skill chain fails.
        """
        logger.info(f"Executing Skill: {self.name}")
        self._execution_log = []
        
        try:
            self._validate_context(context)
            self._calculate_adaptive_weights(context)
            
            execution_report = {
                "skill_id": self.skill_id,
                "status": "success",
                "adaptations": [],
                "final_params": []
            }

            logger.info("--- Initiating Dynamic Sub-node Execution ---")
            
            # Sort nodes by dynamic weight (optional, for priority execution)
            # sorted_nodes = sorted(self.sub_nodes, key=lambda x: x.dynamic_weight, reverse=True)
            
            for node in self.sub_nodes:
                # In a real system, this would interface with hardware drivers
                # Here we simulate the parameter application
                final_params = self._apply_node_logic(node, context)
                
                report_entry = {
                    "node": node.name,
                    "weight_used": node.dynamic_weight,
                    "params": final_params
                }
                execution_report["final_params"].append(report_entry)
                
                if node.dynamic_weight != node.base_weight:
                    msg = f"Adapted '{node.name}': Weight {node.base_weight:.2f} -> {node.dynamic_weight:.2f}"
                    execution_report["adaptations"].append(msg)
                    logger.info(msg)

            return execution_report

        except ParameterValidationError as e:
            logger.error(f"Validation Failed: {e}")
            return {"skill_id": self.skill_id, "status": "failed", "error": str(e)}
        except Exception as e:
            logger.critical(f"Unexpected execution error: {e}", exc_info=True)
            raise SkillExecutionError(f"Runtime error in skill {self.name}") from e

    def _apply_node_logic(self, node: SubSkillNode, context: EnvironmentContext) -> Dict[str, Any]:
        """
        Helper function to finalize parameters before sending to actuators.
        Performs final boundary checks on calculated values.
        """
        calculated_params = node.params.copy()
        
        # Calculate specific force based on physics: F = mu * N (simplified)
        if 'force' in calculated_params:
            req_force = (context.target_mass_kg * 9.8) / max(MIN_FRICTION_COEFF, context.friction_coeff)
            # Apply safety margin
            req_force *= 1.2 
            calculated_params['calculated_force_n'] = min(req_force, MAX_GRIP_FORCE_NEWTONS)
            
        if 'speed' in calculated_params:
            # Reduce speed for fragile or heavy objects
            speed_factor = 1.0 - (context.object_fragility * 0.5) - (context.target_mass_kg / MAX_OBJECT_WEIGHT_KG * 0.3)
            calculated_params['speed'] = node.params['speed'] * max(0.1, speed_factor)
            calculated_params['speed'] = min(calculated_params['speed'], MAX_APPROACH_SPEED_MS)

        return calculated_params

# --- Factory / Setup Function ---
def create_grasp_skill() -> AdaptiveSkill:
    """
    Factory function to create a pre-configured 'Grasp' skill node.
    """
    # Define static base nodes
    nodes = [
        SubSkillNode(
            name="Visual_Servo_Align", 
            base_weight=1.0, 
            params={"speed": 0.5, "precision": "high"}
        ),
        SubSkillNode(
            name="Grip_Force_Control", 
            base_weight=1.0, 
            params={"force": 10.0, "force_multiplier": 1.0}
        ),
        SubSkillNode(
            name="Lift_Manipulator", 
            base_weight=1.0, 
            params={"speed": 0.8, "height": 0.2}
        )
    ]
    
    return AdaptiveSkill(skill_id="skill_grasp_001", name="Universal_Grasp", sub_nodes=nodes)

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Create the skill
    grasp_skill = create_grasp_skill()
    
    # 2. Define Scenario A: Heavy, Slippery Bottle
    print("\n[Scenario A: Heavy, Slippery Object]")
    ctx_slippery = EnvironmentContext(
        target_mass_kg=5.0, 
        friction_coeff=0.2, # Low friction
        object_fragility=0.1
    )
    result_a = grasp_skill.execute(ctx_slippery)
    print(f"Result Status: {result_a['status']}")
    print(f"Adaptations Made: {len(result_a['adaptations'])} changes.")
    
    # 3. Define Scenario B: Light, Robust Box
    print("\n[Scenario B: Light, Robust Object]")
    ctx_normal = EnvironmentContext(
        target_mass_kg=0.5, 
        friction_coeff=0.8, # High friction
        object_fragility=0.0
    )
    result_b = grasp_skill.execute(ctx_normal)
    
    # Compare parameters
    force_a = next((x for x in result_a['final_params'] if x['node'] == 'Grip_Force_Control'), None)
    force_b = next((x for x in result_b['final_params'] if x['node'] == 'Grip_Force_Control'), None)
    
    if force_a and force_b:
        print(f"Force Scenario A: {force_a['params'].get('calculated_force_n', 0):.2f}N")
        print(f"Force Scenario B: {force_b['params'].get('calculated_force_n', 0):.2f}N")