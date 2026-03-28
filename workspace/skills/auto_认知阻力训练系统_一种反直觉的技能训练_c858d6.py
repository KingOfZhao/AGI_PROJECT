"""
Auto_Cognitive_Resistance_Training_System

A counter-intuitive skill training aid tool. It utilizes 'conflict detection algorithms' 
within AGI to calculate the 'cognitive resistance value' between the user's current 
action and mastered skills (or standard actions) during practice.

If the resistance value is too low (indicating the user is applying old habits to new skills),
the system actively increases resistance (simulated physical exoskeleton resistance or visual warnings),
forcing the brain to reconstruct actions via 'top-down deconstruction' rather than relying on inertia,
thereby accelerating skill internalization and the construction of correct 'real nodes'.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CognitiveResistanceTrainer")

@dataclass
class SkillVector:
    """
    Represents a skill as a high-dimensional vector.
    
    Attributes:
        id (str): Unique identifier for the skill.
        features (List[float]): Vector representation of the skill features.
        label (str): Human-readable name of the skill.
    """
    id: str
    features: List[float]
    label: str

    def __post_init__(self):
        if not self.features:
            raise ValueError("Feature vector cannot be empty.")
        if not all(isinstance(x, (int, float)) for x in self.features):
            raise TypeError("Features must be numeric.")

class ResistanceController:
    """
    Simulates the hardware/sensory interface for providing feedback.
    In a real AGI system, this would interface with haptic feedback suits or AR displays.
    """
    
    @staticmethod
    def apply_physical_resistance(level: float) -> bool:
        """
        Simulates increasing resistance on an exoskeleton or haptic device.
        
        Args:
            level (float): Resistance intensity (0.0 to 10.0).
            
        Returns:
            bool: True if application was successful.
        """
        if not (0.0 <= level <= 10.0):
            logger.error(f"Invalid resistance level requested: {level}")
            return False
            
        # Simulation logic
        if level > 0.1:
            logger.info(f"[ACTUATOR] Applying physical resistance: {level:.2f} units.")
            # Code to interface with hardware would go here
        else:
            logger.info("[ACTUATOR] Resistance neutral. Free movement allowed.")
        return True

    @staticmethod
    def trigger_visual_alert(message: str, severity: str = "WARNING"):
        """
        Triggers a visual warning in the user's AR/VR interface.
        
        Args:
            message (str): The warning content.
            severity (str): Level of alert (INFO, WARNING, DANGER).
        """
        logger.info(f"[VISUAL UI - {severity}]: {message}")
        return True

class CognitiveResistanceSystem:
    """
    Core AGI logic for calculating cognitive friction and managing training feedback loops.
    """
    
    def __init__(self, mastered_skills: List[SkillVector], resistance_threshold: float = 0.3):
        """
        Initialize the training system.
        
        Args:
            mastered_skills (List[SkillVector]): Database of skills the user has already internalized.
            resistance_threshold (float): The cosine similarity threshold below which resistance is triggered.
                                          Lower value = more different = less resistance initially.
                                          High similarity implies the user is using an old skill for a new problem.
        """
        self.mastered_skills = mastered_skills
        self.resistance_threshold = resistance_threshold
        self.controller = ResistanceController()
        logger.info(f"System initialized with {len(mastered_skills)} mastered skills patterns.")

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Helper function to calculate Cosine Similarity between two vectors.
        Measures the orientation difference, not magnitude.
        
        Args:
            vec_a (List[float]): Vector A
            vec_b (List[float]): Vector B
            
        Returns:
            float: Similarity score between -1 and 1.
        """
        if len(vec_a) != len(vec_b):
            raise ValueError("Vectors must be of the same dimension.")
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def analyze_cognitive_resistance(self, current_action: SkillVector, target_skill: SkillVector) -> Tuple[float, str]:
        """
        Core Algorithm: Calculates 'Cognitive Resistance'.
        
        Logic:
        1. Calculate similarity between Current Action and Target Skill.
           - If low similarity: User is doing it wrong (Error).
        2. Calculate similarity between Current Action and known Mastered Skills.
           - If high similarity: User is falling back on old habits (Habitual Inertia).
        
        The 'Resistance' is triggered when the user tries to solve a new problem using an old solution
        that looks similar but is fundamentally different (High Conflict).
        
        Args:
            current_action (SkillVector): The user's current movement/action vector.
            target_skill (SkillVector): The intended new skill to learn.
            
        Returns:
            Tuple[float, str]: (Resistance_Intensity, Diagnosis_Code)
        """
        logger.debug(f"Analyzing action {current_action.id} against target {target_skill.id}")
        
        # 1. Check proximity to target
        target_proximity = self._cosine_similarity(current_action.features, target_skill.features)
        
        # 2. Check for "Habitual Interference" - is the user just doing an old skill?
        max_habit_similarity = 0.0
        interfering_skill_label = "None"
        
        for skill in self.mastered_skills:
            sim = self._cosine_similarity(current_action.features, skill.features)
            if sim > max_habit_similarity:
                max_habit_similarity = sim
                interfering_skill_label = skill.label

        # 3. Calculate Resistance Logic
        # If the action is very similar to an old skill, BUT not similar enough to the target,
        # it means the user is "cheating" with muscle memory.
        # We apply resistance proportional to how much they rely on the old habit (max_habit_similarity)
        # but inversely proportional to how close they are to the actual target.
        
        resistance_intensity = 0.0
        diagnosis = "OPTIMAL_FLOW"
        
        # Boundary checks
        if target_proximity > 0.95:
            # Perfect execution
            diagnosis = "TARGET_ACQUIRED"
            resistance_intensity = 0.0
        elif max_habit_similarity > self.resistance_threshold and target_proximity < 0.7:
            # High conflict: User is using an old habit (high sim to mastered) but failing at new skill (low sim to target)
            # Formula: Intensity increases with habit reliance
            resistance_intensity = max_habit_similarity * 10.0 # Scale 0.0-1.0 to 0-10
            diagnosis = f"HABIT_INTERFERENCE_DETECTED:{interfering_skill_label}"
        elif target_proximity < 0.3:
            # Just wrong, random movement
            diagnosis = "RANDOM_NOISE"
            resistance_intensity = 2.0 # Light resistance to guide
        else:
            # Learning zone
            diagnosis = "LEARNING_ZONE"
            resistance_intensity = 0.0

        # Clamp values
        resistance_intensity = max(0.0, min(10.0, resistance_intensity))
        
        return resistance_intensity, diagnosis

    def execute_training_step(self, current_action: SkillVector, target_skill: SkillVector) -> Dict[str, str]:
        """
        Public interface to run a single training loop iteration.
        
        Args:
            current_action (SkillVector): Input from sensors.
            target_skill (SkillVector): The goal skill.
            
        Returns:
            Dict[str, str]: Status report of the training step.
        """
        try:
            intensity, diagnosis = self.analyze_cognitive_resistance(current_action, target_skill)
            
            if intensity > 0.1:
                self.controller.apply_physical_resistance(intensity)
                self.controller.trigger_visual_alert(
                    f"Warning: {diagnosis}. Stop relying on muscle memory. Deconstruct the movement.", 
                    "WARNING"
                )
            else:
                self.controller.apply_physical_resistance(0.0)
                if diagnosis == "TARGET_ACQUIRED":
                    self.controller.trigger_visual_alert("Perfect Repetition!", "SUCCESS")
            
            return {
                "status": "processed",
                "diagnosis": diagnosis,
                "resistance_applied": str(intensity)
            }
            
        except Exception as e:
            logger.error(f"Error during training step: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":
    # 1. Setup: Define Skills
    # Let's imagine a scenario: Learning a "Reverse Punch" in martial arts.
    # The user previously mastered "Standard Punch".
    
    standard_punch = SkillVector(
        id="skill_001", 
        features=[0.9, 0.1, 0.8, 0.2], # High forward momentum, standard rotation
        label="Standard Punch"
    )
    
    reverse_punch = SkillVector(
        id="skill_002",
        features=[0.1, 0.9, 0.2, 0.8], # Retracted momentum, reverse rotation
        label="Reverse Punch"
    )
    
    # User's attempt that looks too much like the old skill (The "Bad Habit")
    lazy_attempt = SkillVector(
        id="action_current",
        features=[0.85, 0.2, 0.75, 0.3], # Very similar to Standard Punch
        label="User Attempt"
    )
    
    # User's attempt that is actually trying the new skill
    good_attempt = SkillVector(
        id="action_current_2",
        features=[0.2, 0.85, 0.3, 0.75], # Very similar to Reverse Punch
        label="User Attempt"
    )

    # 2. Initialize System
    # The system knows the user knows 'Standard Punch'
    trainer = CognitiveResistanceSystem(
        mastered_skills=[standard_punch],
        resistance_threshold=0.3
    )
    
    print("\n--- SCENARIO 1: User falls back into old habit (Standard Punch) ---")
    result_1 = trainer.execute_training_step(lazy_attempt, reverse_punch)
    print(f"Result: {result_1}")
    # Expected: High resistance because cosine(lazy, standard) is high, but cosine(lazy, reverse) is low.
    
    print("\n--- SCENARIO 2: User performs the new skill correctly ---")
    result_2 = trainer.execute_training_step(good_attempt, reverse_punch)
    print(f"Result: {result_2}")
    # Expected: No resistance. System confirms target acquired.