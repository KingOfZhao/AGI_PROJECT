"""
Module: experience_compiler.py

This module implements a compiler service designed to transform unstructured
human practical experiences (e.g., street vending logs) into structured,
executable Python Skill nodes (functions).

It bridges the gap between natural language feedback and AGI system code,
enabling the system to evolve based on real-world physical interactions.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillNode:
    """
    Represents a compiled, executable Skill Node.
    
    Attributes:
        function_name (str): The canonical name of the function (snake_case).
        parameters (Dict[str, Any]): Key-value pairs of arguments.
        raw_intent (str): The original natural language description.
        confidence (float): Compilation confidence score (0.0 to 1.0).
    """
    function_name: str
    parameters: Dict[str, Any]
    raw_intent: str
    confidence: float = 0.0

    def to_code(self) -> str:
        """Generates executable Python code string."""
        params_str = ", ".join([f"{k}={v}" for k, v in self.parameters.items()])
        return f"{self.function_name}({params_str})"


class ExperienceCompiler:
    """
    Compiles unstructured text feedback into structured SkillNodes.
    
    This class acts as a domain-specific compiler. It uses pattern matching
    and keyword extraction to map natural language intents to function signatures.
    """

    def __init__(self, skill_library: Optional[Dict[str, Any]] = None):
        """
        Initialize the compiler with a library of known skills.
        
        Args:
            skill_library (dict): A dictionary mapping intents to function templates.
        """
        self.skill_library = skill_library or self._default_skill_library()
        self._pattern_cache: Dict[str, re.Pattern] = {}
        logger.info("ExperienceCompiler initialized with %d skill templates.", len(self.skill_library))

    def _default_skill_library(self) -> Dict[str, Any]:
        """Provides a default set of skills for the physical world domain."""
        return {
            "umbrella_control": {
                "keywords": ["umbrella", "umbrellas", "rain", "cover"],
                "function_template": "set_umbrella_angle",
                "param_mapping": {
                    "angle": r'(\d+)\s*(?:degree|deg|°)',
                    "state": r'(open|close|tilt)'
                }
            },
            "inventory_management": {
                "keywords": ["stock", "inventory", "goods", "items"],
                "function_template": "adjust_stock_level",
                "param_mapping": {
                    "count": r'(\d+)\s*(?:pieces|items|units)',
                    "item_id": r'item_id\s*[:=]?\s*(\w+)'
                }
            }
        }

    def _validate_input_text(self, text: str) -> str:
        """
        Cleans and validates the input text.
        
        Args:
            text (str): Raw input string.
            
        Returns:
            str: Cleaned string.
            
        Raises:
            ValueError: If input is empty or too short.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input must be a non-empty string.")
        
        cleaned = text.strip()
        if len(cleaned) < 5:
            raise ValueError("Input text is too short to contain meaningful instructions.")
            
        return cleaned

    def _extract_parameters(self, text: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Extracts specific parameters from text using regex patterns defined in the mapping.
        
        Args:
            text (str): The natural language text.
            mapping (dict): Dictionary of parameter_name -> regex_pattern.
            
        Returns:
            dict: Extracted parameters.
        """
        extracted = {}
        for param_name, pattern in mapping.items():
            # Compile regex for efficiency
            if pattern not in self._pattern_cache:
                self._pattern_cache[pattern] = re.compile(pattern, re.IGNORECASE)
            
            match = self._pattern_cache[pattern].search(text)
            if match:
                # Handle basic type conversion
                value = match.group(1)
                if value.isdigit():
                    value = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    value = float(value)
                extracted[param_name] = value
                
        return extracted

    def compile_intent(self, natural_language_feedback: str) -> Optional[SkillNode]:
        """
        Core Function 1: Compiles a single line of feedback into a SkillNode.
        
        This function analyzes the text, identifies the relevant skill category,
        extracts parameters, and constructs the node.
        
        Args:
            natural_language_feedback (str): e.g., "下雨天伞要倾斜45度"
            
        Returns:
            SkillNode: The compiled skill object, or None if no match found.
        """
        try:
            clean_text = self._validate_input_text(natural_language_feedback)
        except ValueError as e:
            logger.warning(f"Input validation failed: {e}")
            return None

        best_match: Optional[Dict[str, Any]] = None
        best_score = 0
        
        # NLP Step: Simple Keyword Matching (In production, replace with Embedding/LLM)
        text_lower = clean_text.lower()
        
        for skill_name, config in self.skill_library.items():
            score = sum(1 for kw in config["keywords"] if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = config

        if not best_match:
            logger.info(f"No matching skill found for text: {clean_text}")
            return None

        # Extract parameters using the matched template
        params = self._extract_parameters(clean_text, best_match["param_mapping"])
        
        # Calculate confidence based on keyword density and param extraction
        confidence = min(1.0, (best_score * 0.3) + (0.7 if params else 0.4))

        node = SkillNode(
            function_name=best_match["function_template"],
            parameters=params,
            raw_intent=clean_text,
            confidence=confidence
        )
        
        logger.info(f"Compiled intent '{clean_text}' -> {node.function_name} with params {params}")
        return node


class SkillDeployer:
    """
    Core Function 2: Handles the validation and simulation/deployment of compiled skills.
    """

    def validate_node(self, node: SkillNode) -> bool:
        """
        Validates the structural integrity and boundary checks of a SkillNode.
        
        Args:
            node (SkillNode): The node to validate.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        if not node.function_name or not isinstance(node.function_name, str):
            logger.error("Validation failed: Invalid function name.")
            return False

        # Boundary checks for specific functions
        if node.function_name == "set_umbrella_angle":
            angle = node.parameters.get("angle")
            if angle is not None:
                if not (0 <= int(angle) <= 90):
                    logger.error(f"Validation failed: Angle {angle} out of bounds (0-90).")
                    return False
        
        logger.debug(f"Node {node.function_name} passed validation.")
        return True

    def simulate_execution(self, node: SkillNode) -> bool:
        """
        Simulates the execution of the skill node (Dry Run).
        
        Args:
            node (SkillNode): The node to simulate.
            
        Returns:
            bool: True if simulation successful.
        """
        logger.info(f"SIMULATION: Executing {node.to_code()}")
        # In a real scenario, this would call a physics engine or sandbox
        return True

    def deploy_skill(self, node: SkillNode) -> bool:
        """
        Orchestrates the validation and deployment of a skill.
        """
        if not self.validate_node(node):
            return False
        
        if node.confidence < 0.6:
            logger.warning(f"Confidence {node.confidence} too low for auto-deployment. Requesting human approval.")
            return False

        return self.simulate_execution(node)


# --- Helper Functions ---

def format_feedback_batch(feedback_list: List[str]) -> List[str]:
    """
    Auxiliary Function: Pre-processes a batch of raw feedback strings.
    Removes special characters and standardizes encoding.
    """
    cleaned_list = []
    for item in feedback_list:
        # Remove non-ASCII characters for simplicity in this demo
        # Keep basic punctuation
        normalized = re.sub(r'[^\w\s.,]', '', item)
        if normalized:
            cleaned_list.append(normalized)
    return cleaned_list


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Initialize Compiler
    compiler = ExperienceCompiler()
    deployer = SkillDeployer()

    # 2. Define Raw Feedback (Simulating physical world input)
    raw_feedback = [
        "下雨天伞要倾斜45度 to prevent water pooling.",
        "Inventory check: We need 50 items of stock for the rush.",
        "This is irrelevant text that shouldn't compile."
    ]

    # 3. Pre-process
    processed_feedback = format_feedback_batch(raw_feedback)

    # 4. Compile and Deploy Loop
    compiled_skills: List[SkillNode] = []

    print(f"\n{'='*10} AGI Skill Compilation Log {'='*10}")
    for feedback in processed_feedback:
        node = compiler.compile_intent(feedback)
        
        if node:
            print(f"Original: {feedback}")
            print(f"Compiled Code: {node.to_code()}")
            print(f"Confidence: {node.confidence:.2f}")
            
            # Attempt Deployment
            success = deployer.deploy_skill(node)
            status = "Deployed" if success else "Held for Review"
            print(f"Status: {status}\n")
            compiled_skills.append(node)
        else:
            print(f"Skipped (No pattern match): {feedback}\n")

    print(f"Total Skills Compiled: {len(compiled_skills)}")