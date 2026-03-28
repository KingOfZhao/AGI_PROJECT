"""
Module: auto_语义_运动对齐_如何解决自然语言模糊性与_dc1c14
Description: Solves the mapping rupture between fuzzy natural language instructions
             and precise physical motion parameters using probabilistic distribution models.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InstructionType(Enum):
    """Enumeration for supported instruction types."""
    TEMPERATURE = "temperature"
    QUANTITY = "quantity"
    DURATION = "duration"
    FORCE = "force"

@dataclass
class FuzzyContext:
    """Contextual information that affects semantic interpretation."""
    cuisine_style: str = "general"  # e.g., 'sichuan' (hot), 'cantonese' (light)
    ingredient_type: str = "default" # e.g., 'meat', 'vegetable', 'soup'
    current_state: str = "raw"       # e.g., 'raw', 'heating', 'boiling'

@dataclass
class MotionParameter:
    """Represents the resolved physical motion parameters."""
    mean_value: float
    std_dev: float
    min_val: float
    max_val: float
    unit: str
    confidence_score: float
    distribution_type: str = "gaussian"  # or 'uniform'

class SemanticMotionAligner:
    """
    Core engine for aligning fuzzy semantics with precise motion parameters.
    
    Uses a hybrid approach of heuristic context mapping and probabilistic 
    distribution generation to translate natural language into executable instructions.
    """

    def __init__(self):
        self._knowledge_base = self._load_semantic_knowledge()
        logger.info("SemanticMotionAligner initialized successfully.")

    def _load_semantic_knowledge(self) -> Dict:
        """Helper: Loads predefined semantic mapping rules."""
        # In a real AGI system, this would connect to a Vector DB or Knowledge Graph
        return {
            InstructionType.TEMPERATURE: {
                "大火": {"mean": 220.0, "std": 20.0, "range": (180.0, 260.0)},
                "中火": {"mean": 160.0, "std": 15.0, "range": (130.0, 190.0)},
                "小火": {"mean": 100.0, "std": 10.0, "range": (80.0, 120.0)},
                "适中": {"mean": 150.0, "std": 20.0, "range": (120.0, 180.0)},
            },
            InstructionType.QUANTITY: {
                "少许": {"mean": 2.0, "std": 1.0, "range": (0.5, 5.0)},
                "适量": {"mean": 5.0, "std": 2.0, "range": (2.0, 10.0)},
                "大量": {"mean": 15.0, "std": 5.0, "range": (10.0, 30.0)},
            }
        }

    def _validate_input(self, text: str, instruction_type: InstructionType) -> None:
        """Helper: Validates input parameters."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Invalid input text: {text}")
        if not isinstance(instruction_type, InstructionType):
            raise TypeError(f"Invalid instruction type: {type(instruction_type)}")

    def resolve_fuzzy_instruction(
        self, 
        fuzzy_text: str, 
        target_type: InstructionType, 
        context: Optional[FuzzyContext] = None
    ) -> MotionParameter:
        """
        Core Function 1: Maps a fuzzy natural language phrase to a probabilistic motion parameter.
        
        Args:
            fuzzy_text (str): The natural language instruction (e.g., "少许盐").
            target_type (InstructionType): The physical dimension to map to.
            context (Optional[FuzzyContext]): Environmental context for disambiguation.
            
        Returns:
            MotionParameter: An object containing distribution details for execution.
            
        Raises:
            ValueError: If the input text is empty or mapping fails.
            KeyError: If the semantic concept is not found in knowledge base.
        """
        try:
            self._validate_input(fuzzy_text, target_type)
            logger.debug(f"Resolving '{fuzzy_text}' for type {target_type.value}")
            
            if context is None:
                context = FuzzyContext()

            # Retrieve base semantics
            base_params = self._knowledge_base.get(target_type, {}).get(fuzzy_text)
            if not base_params:
                # Fallback or dynamic inference would happen here in AGI
                logger.warning(f"Concept '{fuzzy_text}' not found in static KB. Using fallback.")
                base_params = {"mean": 0.0, "std": 0.0, "range": (0.0, 0.0)}

            # Contextual Adjustment (e.g., "少许" salt vs "少许" sugar might differ mass-wise)
            # This simulates the 'Strong Association' logic
            adjusted_mean = self._apply_contextual_bias(base_params["mean"], context, target_type)
            
            # Construct the probability distribution object
            motion_param = MotionParameter(
                mean_value=adjusted_mean,
                std_dev=base_params["std"],
                min_val=base_params["range"][0],
                max_val=base_params["range"][1],
                unit="grams" if target_type == InstructionType.QUANTITY else "celsius",
                confidence_score=0.85 if base_params["mean"] > 0 else 0.1,
                distribution_type="gaussian"
            )

            logger.info(f"Resolved '{fuzzy_text}' -> Mean: {motion_param.mean_value:.2f} {motion_param.unit}")
            return motion_param

        except Exception as e:
            logger.error(f"Failed to resolve instruction '{fuzzy_text}': {e}")
            raise

    def _apply_contextual_bias(self, base_value: float, context: FuzzyContext, target_type: InstructionType) -> float:
        """Helper: Adjusts values based on context."""
        # Example: Sichuan food might interpret "moderate heat" higher than Cantonese
        if target_type == InstructionType.TEMPERATURE:
            if context.cuisine_style == "sichuan":
                return base_value * 1.1 
            if context.cuisine_style == "cantonese":
                return base_value * 0.9
        return base_value

    def generate_executable_trajectory(
        self, 
        param: MotionParameter, 
        time_steps: int = 50,
        visual_feedback: Optional[np.ndarray] = None
    ) -> Dict[str, Union[np.ndarray, float]]:
        """
        Core Function 2: Generates a concrete trajectory and handles visual feedback loops.
        
        Takes the probability distribution and generates a concrete execution curve.
        If visual data (e.g., flame texture) is provided, it adjusts the trajectory.
        
        Args:
            param (MotionParameter): The resolved motion constraints.
            time_steps (int): Number of discrete execution steps.
            visual_feedback (Optional[np.ndarray]): Sensor data for closed-loop correction.
            
        Returns:
            Dict: Contains 'trajectory' (numpy array), 'expected_peak', and 'safety_margin'.
        """
        if time_steps <= 0:
            raise ValueError("time_steps must be positive integer.")

        logger.info(f"Generating trajectory for {param.unit} over {time_steps} steps.")

        # 1. Generate base trajectory using Gaussian Process simulation
        # We sample from the distribution to create a curve
        t = np.linspace(0, 1, time_steps)
        # Simulate a heating curve: sigmoid rise to mean value
        base_curve = param.mean_value / (1 + np.exp(-10 * (t - 0.3)))
        
        # Add noise based on std_dev to simulate probability distribution execution
        noise = np.random.normal(0, param.std_dev * 0.1, time_steps)
        trajectory = base_curve + noise

        # 2. Visual Data Alignment (The "Mapping Break" Fix)
        # If we have visual data (simulated here), we correct the curve
        if visual_feedback is not None:
            logger.debug("Applying visual feedback correction...")
            # Simulate extraction of physical value from visual data
            # e.g., detecting temperature from flame color
            estimated_state = self._extract_physics_from_visual(visual_feedback)
            
            # PID-like correction logic
            error = estimated_state - param.mean_value
            if abs(error) > param.std_dev:
                logger.warning(f"Visual alignment error detected: {error:.2f}. Adjusting trajectory.")
                # Slight adjustment towards the visual reality
                adjustment = error * 0.2
                trajectory -= adjustment

        # 3. Safety Clamping
        trajectory = np.clip(trajectory, param.min_val, param.max_val)

        return {
            "trajectory": trajectory,
            "target_value": param.mean_value,
            "variance": param.std_dev,
            "timestamp": np.arange(time_steps)
        }

    def _extract_physics_from_visual(self, visual_data: np.ndarray) -> float:
        """Helper: Simulates extracting physical parameters from visual tensors."""
        # In a real system, this uses CNNs or Vision Transformers
        # Here we just simulate a sensor reading
        return np.mean(visual_data)

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # Initialize System
    aligner = SemanticMotionAligner()
    
    # Scenario 1: Resolving "Medium Heat" (火候适中)
    try:
        print("\n--- Processing: '火候适中' (Medium Heat) ---")
        # 1. Resolve Semantic
        temp_instruction = aligner.resolve_fuzzy_instruction(
            fuzzy_text="中火",
            target_type=InstructionType.TEMPERATURE,
            context=FuzzyContext(cuisine_style="sichuan")
        )
        
        # 2. Generate Trajectory with simulated visual feedback (Flame color)
        # Simulating visual data: 50 frames of "flame" data (random values for demo)
        simulated_flame_visuals = np.random.normal(loc=165.0, scale=5.0, size=50)
        
        execution_plan = aligner.generate_executable_trajectory(
            param=temp_instruction,
            time_steps=50,
            visual_feedback=simulated_flame_visuals
        )
        
        print(f"Target Temp: {execution_plan['target_value']:.1f} C")
        print(f"Trajectory Mean (first 5 steps): {np.mean(execution_plan['trajectory'][:5]):.2f}")
        
    except Exception as e:
        print(f"Error in execution: {e}")

    # Scenario 2: Resolving "A little salt" (少许盐)
    try:
        print("\n--- Processing: '少许盐' (A little salt) ---")
        qty_instruction = aligner.resolve_fuzzy_instruction(
            fuzzy_text="少许",
            target_type=InstructionType.QUANTITY
        )
        
        # Execute without visual feedback (blind pour)
        salt_plan = aligner.generate_executable_trajectory(
            param=qty_instruction,
            time_steps=20,
            visual_feedback=None
        )
        
        print(f"Target Qty: {salt_plan['target_value']:.1f} g")
        print(f"Distribution Std Dev: {salt_plan['variance']:.2f}")
        
    except Exception as e:
        print(f"Error in execution: {e}")