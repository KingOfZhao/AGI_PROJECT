"""
Module: auto_skill_solidification.py
Description: 无监督语法树生成的代码技能固化模块。
             This module automates the extraction of executable logic from
             unstructured text logs or dialogues and generates a structured
             SKILL node (e.g., a Shell script) using NLP heuristics.
Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
MIN_TEXT_LENGTH = 20
MAX_TEXT_LENGTH = 5000
VALID_NODE_TYPES = ["shell_script", "python_function", "sql_query", "unknown"]
SKILL_REGISTRY_PATH = "./skill_registry/"

@dataclass
class SkillNode:
    """
    Represents a structured, executable skill node extracted from text.
    """
    node_id: str
    node_type: str
    name: str
    source_text: str
    generated_code: str
    created_at: str
    confidence_score: float
    dependencies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Converts the node to a dictionary for serialization."""
        return asdict(self)


class TextPreprocessor:
    """
    Helper class for cleaning and validating input text.
    """
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        Removes potentially harmful characters and normalizes whitespace.
        
        Args:
            text (str): Raw input text.
        
        Returns:
            str: Sanitized text.
        """
        if not text:
            return ""
        # Remove control characters except newlines
        sanitized = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Normalize multiple spaces to single space
        sanitized = re.sub(r' +', ' ', sanitized)
        return sanitized.strip()

    @staticmethod
    def validate_bounds(text: str) -> bool:
        """
        Checks if text length is within acceptable boundaries.
        """
        length = len(text)
        if length < MIN_TEXT_LENGTH:
            logger.warning(f"Input text too short: {length} chars.")
            return False
        if length > MAX_TEXT_LENGTH:
            logger.warning(f"Input text too long: {length} chars.")
            return False
        return True


class LogicExtractor:
    """
    Core logic for parsing unstructured text and generating syntax trees/code.
    """

    def __init__(self):
        # Regex patterns to identify potential code structures
        self._patterns = {
            "shell_script": [
                r"(sudo\s+)?(apt|yum|brew|pip|npm|systemctl|docker|kubectl)\s+[\w\-]+",
                r"rm\s+-rf\s+[/\w]",
                r"export\s+\w+=.*",
                r"chmod\s+[0-7]+"
            ],
            "sql_query": [
                r"SELECT\s+.+\s+FROM\s+\w+",
                r"UPDATE\s+\w+\s+SET\s+"
            ],
            "python_function": [
                r"def\s+\w+\s*\([^)]*\)\s*:",
                r"import\s+\w+"
            ]
        }

    def analyze_text(self, text: str) -> Tuple[str, float, str]:
        """
        Analyzes text to determine the most likely executable type.
        
        Args:
            text (str): The preprocessed text.
            
        Returns:
            Tuple[str, float, str]: (detected_type, confidence, extracted_logic_snippet)
        """
        scores = {k: 0 for k in VALID_NODE_TYPES if k != 'unknown'}
        
        for node_type, patterns in self._patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                scores[node_type] = scores.get(node_type, 0) + len(matches)
        
        if not any(scores.values()):
            return "unknown", 0.0, ""

        # Find the type with the highest score
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] * 0.2, 1.0) # Heuristic confidence calc
        
        # Extract the most relevant line (heuristic)
        lines = text.split('\n')
        best_line = lines[0] if lines else ""
        
        return best_type, confidence, best_line


class SkillSolidifier:
    """
    Main class to handle the end-to-end process of skill solidification.
    """

    def __init__(self, registry_path: str = SKILL_REGISTRY_PATH):
        self.preprocessor = TextPreprocessor()
        self.extractor = LogicExtractor()
        self.registry_path = registry_path
        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        """Ensures the directory for storing skills exists."""
        os.makedirs(self.registry_path, exist_ok=True)

    def _generate_code_block(self, logic_type: str, content: str) -> str:
        """
        Generates the actual executable code string based on extracted logic.
        (In a real AGI system, this would use an LLM or sophisticated parser).
        """
        if logic_type == "shell_script":
            return f"#!/bin/bash\n# Auto-generated skill\n{content}\necho 'Task completed.'"
        elif logic_type == "python_function":
            return f"# Auto-generated skill\n{content}\nprint('Task completed')"
        else:
            return f"# Could not parse executable logic for: {content}"

    def solidify_skill(self, raw_text: str, skill_name: Optional[str] = None) -> Optional[SkillNode]:
        """
        Processes raw text, extracts logic, and solidifies it into a SkillNode.
        
        Args:
            raw_text (str): Unstructured text containing process description.
            skill_name (Optional[str]): Optional name for the skill.
        
        Returns:
            Optional[SkillNode]: The generated skill node or None if failed.
        """
        logger.info("Starting skill solidification process...")
        
        # 1. Validation
        if not self.preprocessor.validate_bounds(raw_text):
            logger.error("Validation failed: Invalid input bounds.")
            return None

        # 2. Preprocessing
        clean_text = self.preprocessor.sanitize_input(raw_text)
        
        # 3. Analysis & Extraction
        detected_type, confidence, snippet = self.extractor.analyze_text(clean_text)
        
        if detected_type == "unknown" or confidence < 0.1:
            logger.warning(f"Extraction failed or low confidence: {confidence}")
            return None

        # 4. Node Generation
        node_id = f"skill_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().isoformat()
        
        # Generate Code
        generated_code = self._generate_code_block(detected_type, snippet)
        
        node = SkillNode(
            node_id=node_id,
            node_type=detected_type,
            name=skill_name or f"Auto_Extracted_{detected_type}",
            source_text=clean_text[:255], # Truncate for storage
            generated_code=generated_code,
            created_at=timestamp,
            confidence_score=confidence,
            dependencies=[] # Static analysis could populate this
        )
        
        logger.info(f"Successfully solidified node {node_id} with type {detected_type}")
        return node

    def save_node(self, node: SkillNode) -> bool:
        """
        Persists the skill node to the local registry.
        """
        try:
            file_path = os.path.join(self.registry_path, f"{node.node_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(node.to_dict(), f, indent=4)
            logger.info(f"Node saved to {file_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to save node {node.node_id}: {e}")
            return False


# --- Usage Example ---
if __name__ == "__main__":
    # Example input: Unstructured log describing a server maintenance task
    sample_log = """
    System Alert: Cache partition full.
    Manual Action Required:
    1. SSH into the server.
    2. Run 'sudo rm -rf /var/cache/tmp/*'
    3. Restart the service using 'systemctl restart myservice'.
    """
    
    print("--- Initializing Skill Solidifier ---")
    solidifier = SkillSolidifier()
    
    print("\n--- Processing Raw Text ---")
    skill_node = solidifier.solidify_skill(sample_log, skill_name="Clear_Server_Cache")
    
    if skill_node:
        print("\n--- Generated Skill Node ---")
        print(json.dumps(skill_node.to_dict(), indent=2))
        
        # Save to disk
        solidifier.save_node(skill_node)
    else:
        print("Failed to generate skill node.")