"""
Module: semantic_feedback_tuner
This module implements a mechanism to translate fuzzy natural language feedback
from humans into precise system parameter adjustments. It acts as a bridge
between abstract human intuition (e.g., "this feels too aggressive") and
quantitative system configurations (e.g., reduce 'temperature' weight by 0.2).

The core workflow involves:
1. Parsing fuzzy feedback into structured 'Verification Nodes'.
2. Generating Minimum Viable Prompts (MVP) to confirm specific parameter mappings.
3. Applying validated adjustments to the knowledge network configuration.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackDomain(Enum):
    """Enumeration of possible domains for feedback."""
    COGNITION = "cognition"
    BEHAVIOR = "behavior"
    KNOWLEDGE = "knowledge"
    SYSTEM = "system"

@dataclass
class SystemParameter:
    """Represents a configurable parameter in the AGI system."""
    key: str
    current_value: float
    min_val: float = 0.0
    max_val: float = 1.0
    
    def update(self, delta: float) -> bool:
        """Updates the parameter value with boundary checks."""
        new_val = self.current_value + delta
        if self.min_val <= new_val <= self.max_val:
            self.current_value = round(new_val, 4)
            logger.info(f"Parameter '{self.key}' updated to {self.current_value}")
            return True
        logger.warning(f"Update for '{self.key}' failed: Boundary exceeded.")
        return False

@dataclass
class VerificationNode:
    """A structured representation of a potential system adjustment."""
    target_key: str
    suggested_delta: float
    confidence: float
    reason: str

class SemanticFeedbackTuner:
    """
    Translates fuzzy natural language feedback into precise system parameter adjustments.
    
    This class simulates the 'backpropagation' of human feedback into the system's
    configuration weight space.
    """

    def __init__(self, system_config: Dict[str, Any]):
        """
        Initializes the tuner with the current system configuration.
        
        Args:
            system_config: A dictionary representing the current system state.
        """
        self._raw_config = system_config
        self.parameters: Dict[str, SystemParameter] = self._load_parameters(system_config)
        logger.info(f"SemanticFeedbackTuner initialized with {len(self.parameters)} parameters.")

    def _load_parameters(self, config: Dict[str, Any]) -> Dict[str, SystemParameter]:
        """Extracts and validates parameters from the raw configuration."""
        params = {}
        # Simplified extraction logic for demonstration
        if "weights" in config:
            for k, v in config["weights"].items():
                if isinstance(v, (int, float)):
                    params[k] = SystemParameter(key=k, current_value=float(v))
        return params

    def parse_fuzzy_feedback(self, feedback_text: str) -> List[VerificationNode]:
        """
        Analyzes fuzzy text to generate potential system adjustments (Verification Nodes).
        
        Args:
            feedback_text: The raw natural language input from a human.
            
        Returns:
            A list of VerificationNodes representing potential changes.
            
        Raises:
            ValueError: If feedback_text is empty or invalid.
        """
        if not feedback_text or not isinstance(feedback_text, str):
            logger.error("Invalid feedback input: Empty or non-string.")
            raise ValueError("Feedback must be a non-empty string.")

        logger.info(f"Parsing feedback: '{feedback_text}'")
        nodes = []
        
        # Heuristic parsing logic (Simulated NLP understanding)
        text_lower = feedback_text.lower()
        
        # Rule 1: Intensity modifiers
        if "too aggressive" in text_lower or "too fast" in text_lower:
            if "response_speed" in self.parameters:
                nodes.append(VerificationNode(
                    target_key="response_speed",
                    suggested_delta=-0.15,
                    confidence=0.8,
                    reason="Detected negative intensity sentiment"
                ))
        
        # Rule 2: Precision modifiers
        if "not accurate" in text_lower or "hallucinating" in text_lower:
            if "creativity_weight" in self.parameters:
                nodes.append(VerificationNode(
                    target_key="creativity_weight",
                    suggested_delta=-0.25,
                    confidence=0.9,
                    reason="Detected accuracy concern"
                ))
            if "fact_verification_threshold" in self.parameters:
                nodes.append(VerificationNode(
                    target_key="fact_verification_threshold",
                    suggested_delta=0.1,
                    confidence=0.85,
                    reason="Increasing verification strictness"
                ))

        # Rule 3: Emotional tone
        if "more friendly" in text_lower:
            if "empathy_factor" in self.parameters:
                nodes.append(VerificationNode(
                    target_key="empathy_factor",
                    suggested_delta=0.2,
                    confidence=0.75,
                    reason="Detected request for warmer tone"
                ))

        if not nodes:
            logger.warning("No actionable nodes extracted from feedback.")
            
        return nodes

    def generate_mvp_questions(self, nodes: List[VerificationNode]) -> List[str]:
        """
        Generates Minimum Viable Prompt (MVP) questions to validate the nodes.
        
        Args:
            nodes: List of candidate adjustment nodes.
            
        Returns:
            A list of natural language questions for the human user.
        """
        questions = []
        for node in nodes:
            param = self.parameters.get(node.target_key)
            if not param:
                continue
                
            direction = "decrease" if node.suggested_delta < 0 else "increase"
            abs_delta = abs(node.suggested_delta)
            
            q = (f"System Analysis: You seem to want to {direction} the '{node.target_key}' "
                 f"(currently {param.current_value}) by {abs_delta:.2f}. "
                 f"Reason: {node.reason}. Confirm? (y/n)")
            questions.append(q)
            
        return questions

    def apply_validated_adjustments(self, nodes: List[VerificationNode], confirmations: List[bool]) -> Dict[str, float]:
        """
        Applies the validated changes to the system parameters.
        
        Args:
            nodes: The list of proposed verification nodes.
            confirmations: A list of booleans corresponding to user confirmation.
            
        Returns:
            A dictionary of updated parameters.
        """
        updated_params = {}
        if len(nodes) != len(confirmations):
            logger.error("Mismatch between nodes and confirmations length.")
            return updated_params

        for node, confirmed in zip(nodes, confirmations):
            if confirmed:
                param = self.parameters.get(node.target_key)
                if param and param.update(node.suggested_delta):
                    updated_params[node.target_key] = param.current_value
                else:
                    logger.warning(f"Failed to apply update for {node.target_key}")
        
        logger.info(f"Applied {len(updated_params)} adjustments.")
        return updated_params

# --- Utility Functions ---

def validate_system_config_schema(config: Dict[str, Any]) -> bool:
    """
    Validates the structure of the system configuration file.
    
    Args:
        config: The configuration dictionary to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(config, dict):
        return False
    if "weights" not in config:
        return False
    if not isinstance(config["weights"], dict):
        return False
    return True

def format_feedback_report(updates: Dict[str, float], execution_time: float) -> str:
    """
    Formats the result of the tuning process into a readable report.
    
    Args:
        updates: Dictionary of parameter changes.
        execution_time: Time taken for the process.
        
    Returns:
        A formatted JSON string report.
    """
    report = {
        "status": "success",
        "timestamp": logging.Formatter.default_msec_format, # Placeholder logic
        "adjusted_params": updates,
        "processing_time_ms": execution_time
    }
    return json.dumps(report, indent=2)

# --- Usage Example ---

if __name__ == "__main__":
    # Mock System Configuration
    mock_config = {
        "weights": {
            "response_speed": 0.8,
            "creativity_weight": 0.5,
            "empathy_factor": 0.3,
            "fact_verification_threshold": 0.6
        },
        "metadata": {
            "version": "1.0"
        }
    }

    # 1. Validate Input
    if not validate_system_config_schema(mock_config):
        print("Invalid configuration provided.")
    else:
        # 2. Initialize Tuner
        tuner = SemanticFeedbackTuner(mock_config)
        
        # 3. Simulate Human Feedback
        human_feedback = "The system feels a bit too aggressive and is sometimes not accurate."
        
        try:
            # 4. Parse Feedback into Nodes
            verification_nodes = tuner.parse_fuzzy_feedback(human_feedback)
            
            # 5. Generate MVP Questions for the Human
            questions = tuner.generate_mvp_questions(verification_nodes)
            
            print("--- Interaction Log ---")
            print(f"Feedback Received: {human_feedback}")
            print("Generated MVP Questions:")
            for q in questions:
                print(f" - {q}")
            
            # 6. Simulate Human Confirmation (Auto-confirming for demo)
            # In a real scenario, this would come from a UI/UX interface
            user_confirmations = [True] * len(questions) 
            
            # 7. Apply Adjustments
            import time
            start_t = time.time()
            final_updates = tuner.apply_validated_adjustments(verification_nodes, user_confirmations)
            end_t = time.time()
            
            # 8. Output Report
            report = format_feedback_report(final_updates, (end_t - start_t) * 1000)
            print("\n--- Final Report ---")
            print(report)
            
        except ValueError as e:
            logger.error(f"Processing Error: {e}")
        except Exception as e:
            logger.critical(f"Unexpected System Failure: {e}")