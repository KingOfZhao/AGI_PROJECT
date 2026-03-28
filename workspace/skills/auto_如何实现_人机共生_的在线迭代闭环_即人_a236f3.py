"""
Module: human_machine_symbiosis_loop
Description: Implements an online iterative closed-loop system for 'Human-Machine Symbiosis'.
             This module translates unstructured human feedback (e.g., "feels stiff")
             into concrete physical parameter adjustments for AI simulation agents.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class SimulationParameters:
    """
    Represents the mutable physical parameters of the AI simulation agent.
    Boundaries ensure physical plausibility (e.g., friction > 0).
    """
    stiffness: float = 0.5      # Range [0.0, 1.0]
    damping: float = 0.3        # Range [0.0, 1.0]
    friction: float = 0.5       # Range [0.0, 1.0]
    elasticity: float = 0.2     # Range [0.0, 1.0]

    def validate(self) -> bool:
        """Validates that all parameters are within [0.0, 1.0]."""
        for attr in ['stiffness', 'damping', 'friction', 'elasticity']:
            val = getattr(self, attr)
            if not (0.0 <= val <= 1.0):
                logger.error(f"Validation failed: {attr} value {val} out of bounds.")
                return False
        return True

    def to_vector(self) -> List[float]:
        return [self.stiffness, self.damping, self.friction, self.elasticity]

@dataclass
class SymbioticLoop:
    """
    Manages the state of the iterative design loop.
    """
    current_params: SimulationParameters = field(default_factory=SimulationParameters)
    history: List[Dict] = field(default_factory=list)
    max_iterations: int = 10
    current_iteration: int = 0

# --- Core Functions ---

def parse_feedback_to_semantic_vector(feedback_text: str) -> Dict[str, float]:
    """
    Parses unstructured natural language feedback into a semantic adjustment vector.
    
    This simulates the behavior of an NLP model (like a fine-tuned BERT or LLM)
    extracting intent from qualitative descriptions.
    
    Args:
        feedback_text (str): Raw human input (e.g., "It moves too rigidly").
        
    Returns:
        Dict[str, float]: A dictionary mapping parameter names to adjustment deltas.
                          Positive values mean 'increase', negative mean 'decrease'.
    
    Example:
        >>> parse_feedback_to_semantic_vector("too stiff and slippery")
        {'stiffness': -0.2, 'friction': 0.2}
    """
    logger.info(f"Parsing feedback: '{feedback_text}'")
    feedback_text = feedback_text.lower().strip()
    adjustments = {}
    
    # Heuristic-based parsing logic (simulated NLP understanding)
    # In a production AGI system, this would interface with an LLM embedding layer.
    
    # Stiffness detection
    if "stiff" in feedback_text or "rigid" in feedback_text or "robotic" in feedback_text:
        adjustments['stiffness'] = -0.15 # Reduce stiffness
        adjustments['damping'] = -0.05   # Often associated
    elif "loose" in feedback_text or "wobbly" in feedback_text or "floppy" in feedback_text:
        adjustments['stiffness'] = 0.15
        adjustments['damping'] = 0.10

    # Friction detection
    if "slippery" in feedback_text or "slides" in feedback_text or "icy" in feedback_text:
        adjustments['friction'] = 0.2
    elif "rough" in feedback_text or "stuck" in feedback_text or "dragging" in feedback_text:
        adjustments['friction'] = -0.2
        
    # Bounce/Elasticity
    if "bouncy" in feedback_text or "rubber" in feedback_text:
        adjustments['elasticity'] = 0.2
        adjustments['damping'] = -0.1 # Less damping = more bounce
    elif "dead" in feedback_text or "heavy" in feedback_text:
        adjustments['elasticity'] = -0.1
        adjustments['damping'] = 0.1

    # Handle "Good" or "Stop" signals implicitly by returning empty dict or specific flag
    if not adjustments:
        if "perfect" in feedback_text or "good" in feedback_text or "stop" in feedback_text:
            logger.info("Positive termination signal detected in feedback.")
        else:
            logger.warning("Unrecognized feedback semantics.")

    return adjustments

def apply_parameter_adjustment(
    current_state: SimulationParameters, 
    adjustments: Dict[str, float],
    learning_rate: float = 1.0
) -> SimulationParameters:
    """
    Applies calculated adjustments to the simulation parameters with boundary checks.
    
    Args:
        current_state (SimulationParameters): The current physical params.
        adjustments (Dict[str, float]): The deltas to apply.
        learning_rate (float): A multiplier to control step size.
        
    Returns:
        SimulationParameters: Updated parameters.
        
    Raises:
        ValueError: If adjustment keys do not match existing parameters.
    """
    new_state = SimulationParameters(**current_state.__dict__) # Deep copy
    
    logger.info(f"Applying adjustments: {adjustments} with lr={learning_rate}")
    
    for param, delta in adjustments.items():
        if hasattr(new_state, param):
            current_val = getattr(new_state, param)
            new_val = current_val + (delta * learning_rate)
            
            # Boundary Clamping [0.0, 1.0]
            new_val = max(0.0, min(1.0, new_val))
            
            setattr(new_state, param, new_val)
            logger.debug(f"Updated {param}: {current_val:.3f} -> {new_val:.3f}")
        else:
            logger.error(f"Attempted to adjust non-existent parameter: {param}")
            # In a real system, might raise an error or handle gracefully
            continue
            
    if not new_state.validate():
        raise RuntimeError("Parameter validation failed after adjustment.")
        
    return new_state

# --- Helper Functions ---

def render_simulation_state(params: SimulationParameters) -> str:
    """
    Simulates the 'visualization' or 'rendering' of the AI agent's movement.
    In a real scenario, this drives a Unity/Unreal/PyBullet engine.
    
    Args:
        params (SimulationParameters): Parameters to render.
        
    Returns:
        str: A description of the movement style.
    """
    # Simple logic to describe the "feeling" of the parameters
    desc = []
    
    if params.stiffness > 0.8: desc.append("very rigid")
    elif params.stiffness < 0.2: desc.append("very loose")
    else: desc.append("balanced tension")
    
    if params.friction > 0.7: desc.append("high grip")
    elif params.friction < 0.3: desc.append("sliding")
    
    if params.elasticity > 0.6: desc.append("bouncy")
    
    return ", ".join(desc)

# --- AGI Skill Execution ---

def run_symbiotic_design_session(initial_params: Optional[SimulationParameters] = None):
    """
    Runs a simulated closed-loop session between Human and AI.
    This function demonstrates the full workflow.
    """
    print("\n--- Starting Human-Machine Symbiosis Session ---")
    
    loop_state = SymbioticLoop(
        current_params=initial_params or SimulationParameters()
    )
    
    # Simulated Human Feedback Queue (for demonstration)
    human_feedback_sequence = [
        "It feels a bit stiff.", 
        "Better, but it's sliding too much.", 
        "Perfect."
    ]
    
    print(f"Initial State: {loop_state.current_params}")
    
    while loop_state.current_iteration < loop_state.max_iterations:
        print(f"\n[Iteration {loop_state.current_iteration + 1}]")
        
        # 1. AI "Renders" or Simulates
        visual_desc = render_simulation_state(loop_state.current_params)
        print(f"AI Simulation: Performing action with style -> [{visual_desc}]")
        
        # 2. Get Human Input (Simulated by popping from list)
        if not human_feedback_sequence:
            break
            
        human_input = human_feedback_sequence.pop(0)
        print(f"Human Feedback: \"{human_input}\"")
        
        # 3. Process Feedback
        if "perfect" in human_input.lower() or "good" in human_input.lower():
            print(">>> Result: Human satisfied. Fixing 'Real Node'. <<<")
            break
            
        adjustments = parse_feedback_to_semantic_vector(human_input)
        
        # 4. Update State
        if adjustments:
            try:
                loop_state.current_params = apply_parameter_adjustment(
                    loop_state.current_params, 
                    adjustments
                )
                loop_state.history.append({
                    'iteration': loop_state.current_iteration,
                    'feedback': human_input,
                    'params': loop_state.current_params.to_vector()
                })
            except Exception as e:
                logger.error(f"Critical error during adjustment: {e}")
                break
        else:
            logger.info("No actionable adjustments found.")
            
        loop_state.current_iteration += 1

    print("\n--- Session Ended ---")
    print(f"Final Parameters: {loop_state.current_params}")
    return loop_state

if __name__ == "__main__":
    # Example Execution
    run_symbiotic_design_session()