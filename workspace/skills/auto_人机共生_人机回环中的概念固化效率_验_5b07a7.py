"""
Module: auto_人机共生_人机回环中的概念固化效率_验_5b07a7

Description:
    This module implements a closed-loop system for Human-Computer Symbiosis (HCS).
    It focuses on the efficiency of "Concept Solidification" within the human-machine feedback loop.
    
    The process flow is:
    1.  Ingest unstructured human experience (e.g., a vague voice transcript).
    2.  Structure this information into a Standard Operating Procedure (SOP) using NLP heuristics.
    3.  Simulate/Accept human feedback on the generated SOP.
    4.  Solidify the final version into a persistent Skill Node (JSON format).
    
    Key Capabilities:
    -   Structuring fuzzy information.
    -   Integrating feedback loops.
    -   Persistent knowledge固化.

Domain: knowledge_management
Author: AGI System
Version: 1.0.0
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field

# --- Configuration & Setup ---

# Setting up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HCS_Concept_Solidification")

# --- Data Structures ---

@dataclass
class SOPNode:
    """
    Represents a Standard Operating Procedure (SOP) structure.
    """
    id: str
    title: str
    steps: List[str]
    version: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SOPValidationError(Exception):
    """Custom exception for SOP validation failures."""
    pass


class KnowledgeBaseError(Exception):
    """Custom exception for Knowledge Base I/O failures."""
    pass


# --- Core Functions ---

def ingest_unstructured_experience(raw_text: str) -> Dict[str, Any]:
    """
    Ingests and preprocesses raw, unstructured text input from a human.
    
    This function simulates the reception of fuzzy human logic (e.g., voice transcripts).
    It performs basic cleaning and sentiment/complexity analysis to determine 
    processing requirements.

    Args:
        raw_text (str): The raw input string.

    Returns:
        Dict[str, Any]: A dictionary containing processed tokens and metadata.

    Raises:
        ValueError: If input text is empty or too short to be meaningful.
    """
    logger.info("Ingesting unstructured experience...")
    
    # Data Validation
    if not raw_text or not isinstance(raw_text, str):
        logger.error("Input is empty or not a string.")
        raise ValueError("Input text must be a non-empty string.")
    
    stripped_text = raw_text.strip()
    if len(stripped_text) < 10:
        logger.warning(f"Input text too short: {len(stripped_text)} chars.")
        raise ValueError("Input text is too short to extract meaningful SOP.")

    # Preprocessing
    # Remove filler words (basic simulation of NLP cleaning)
    filler_words = r'\b(um|uh|like|basically|you know|so)\b'
    cleaned_text = re.sub(filler_words, '', stripped_text, flags=re.IGNORECASE)
    
    # Extract potential sentences
    sentences = re.split(r'[.!?\n]+', cleaned_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    metadata = {
        "original_length": len(raw_text),
        "cleaned_length": len(cleaned_text),
        "sentence_count": len(sentences),
        "complexity_score": len(set(cleaned_text.split())) / (len(cleaned_text.split()) + 1e-6)
    }

    logger.info(f"Ingestion complete. Found {len(sentences)} potential segments.")
    return {
        "cleaned_text": cleaned_text,
        "segments": sentences,
        "metadata": metadata
    }


def structure_into_sop(
    processed_data: Dict[str, Any], 
    skill_name: str = "Untitled_Skill"
) -> SOPNode:
    """
    Transforms processed text segments into a structured SOPNode object.
    
    This represents the AI's ability to organize chaos into order.

    Args:
        processed_data (Dict): Output from `ingest_unstructured_experience`.
        skill_name (str): The tentative name for the skill.

    Returns:
        SOPNode: The structured data object.
        
    Raises:
        KeyError: If processed_data lacks required keys.
    """
    logger.info(f"Structuring data into SOP for skill: {skill_name}")
    
    if "segments" not in processed_data:
        logger.error("Invalid processed data format.")
        raise KeyError("Missing 'segments' in processed data.")

    # Heuristic structuring logic
    # Filter out very short segments likely to be noise
    valid_steps = [s for s in processed_data["segments"] if len(s) > 5]
    
    # Auto-formatting steps
    formatted_steps = []
    for i, step in enumerate(valid_steps):
        # Ensure step starts with a capital letter
        step = step[0].upper() + step[1:] if len(step) > 1 else step.upper()
        formatted_steps.append(f"Step {i+1}: {step}")

    if not formatted_steps:
        formatted_steps = ["Step 1: Context analysis required (No clear steps detected)."]

    sop = SOPNode(
        id=f"skill_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title=skill_name.replace("_", " ").title(),
        steps=formatted_steps,
        version=1.0,
        metadata=processed_data.get("metadata", {})
    )

    logger.info(f"SOP Structured: {sop.id} with {len(sop.steps)} steps.")
    return sop


def solidify_skill_node(
    sop: SOPNode, 
    feedback: Optional[List[Tuple[int, str]]] = None,
    storage_path: str = "knowledge_base.json"
) -> bool:
    """
    Saves the SOP to the knowledge base, incorporating human feedback.
    
    This is the 'Solidification' phase. It merges feedback (corrections) 
    and persists the result.

    Args:
        sop (SOPNode): The SOP object to save.
        feedback (List[Tuple[int, str]], optional): A list of tuples where 
            (index, new_text) represents human corrections.
        storage_path (str): Path to the JSON file serving as the knowledge base.

    Returns:
        bool: True if successful, False otherwise.
    """
    logger.info("Initiating concept solidification...")
    
    # 1. Apply Feedback (The 'Loop' closure)
    if feedback:
        logger.info(f"Applying {len(feedback)} feedback items.")
        for index, new_text in feedback:
            if 0 <= index < len(sop.steps):
                # Validate new text
                if not isinstance(new_text, str) or not new_text.strip():
                    logger.warning(f"Invalid feedback text for index {index}. Skipping.")
                    continue
                
                # Overwrite step
                sop.steps[index] = f"Step {index+1}: {new_text.strip()}"
            else:
                logger.warning(f"Index {index} out of bounds for feedback. Skipping.")
        
        # Increment version due to modification
        sop.version = round(sop.version + 0.1, 1)
    
    # 2. Validate Final Structure
    try:
        validate_sop_integrity(sop)
    except SOPValidationError as e:
        logger.error(f"Solidification failed validation: {e}")
        return False

    # 3. Persist to Storage
    try:
        # Read existing DB
        kb_data = {}
        if Path(storage_path).exists():
            with open(storage_path, 'r', encoding='utf-8') as f:
                try:
                    kb_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Knowledge base corrupted or empty. Re-initializing.")
                    kb_data = {}
        
        # Update DB
        if "skills" not in kb_data:
            kb_data["skills"] = {}
            
        kb_data["skills"][sop.id] = sop.to_dict()
        
        # Write DB
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(kb_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Skill {sop.id} (v{sop.version}) solidified successfully.")
        return True

    except IOError as e:
        logger.error(f"File I/O error during solidification: {e}")
        raise KnowledgeBaseError("Failed to access knowledge base.")
    except Exception as e:
        logger.critical(f"Unexpected error during save: {e}")
        return False


# --- Helper Functions ---

def validate_sop_integrity(sop: SOPNode) -> None:
    """
    Validates the data integrity of an SOPNode before storage.
    
    Checks:
    - ID format
    - Presence of steps
    - Data types
    
    Args:
        sop (SOPNode): The object to validate.
        
    Raises:
        SOPValidationError: If validation fails.
    """
    if not isinstance(sop, SOPNode):
        raise SOPValidationError("Input is not an SOPNode instance.")
    
    if not sop.id or not isinstance(sop.id, str):
        raise SOPValidationError("Invalid ID.")
        
    if not sop.steps or len(sop.steps) == 0:
        raise SOPValidationError("SOP cannot be empty.")
        
    if sop.version < 1.0:
        raise SOPValidationError("Version must be at least 1.0.")

    logger.debug("SOP integrity check passed.")


# --- Main Execution / Example Usage ---

if __name__ == "__main__":
    # Scenario: A human expert describes a troubleshooting process vaguely.
    
    raw_human_input = """
    Um, okay, so first you gotta check the cables. 
    Make sure the red light is on, uh, blinking is bad.
    If it's solid, then you restart the service.
    Don't forget to log the time.
    """
    
    print("-" * 50)
    print(">>> STAGE 1: INGESTION")
    print("-" * 50)
    
    try:
        # 1. Ingest
        processed = ingest_unstructured_experience(raw_human_input)
        print(f"Extracted Segments: {processed['segments']}")
        
        print("-" * 50)
        print(">>> STAGE 2: STRUCTURING")
        print("-" * 50)
        
        # 2. Structure
        draft_sop = structure_into_sop(processed, skill_name="Hardware_Check")
        print(f"Generated SOP Draft:\n{json.dumps(draft_sop.to_dict(), indent=2)}")
        
        print("-" * 50)
        print(">>> STAGE 3: HUMAN FEEDBACK LOOP")
        print("-" * 50)
        
        # 3. Human Feedback (Simulated)
        # Human says: 
        # - Index 0 is fine.
        # - Index 1 is too vague, change to "Ensure Diode A pulses".
        # - Index 2 needs to specify which service.
        human_corrections = [
            (1, "Ensure Diode A pulses, red light is not enough."), 
            (2, "Restart the 'CoreService' daemon.")
        ]
        print(f"Applying Feedback: {human_corrections}")
        
        print("-" * 50)
        print(">>> STAGE 4: SOLIDIFICATION")
        print("-" * 50)
        
        # 4. Solidify
        success = solidify_skill_node(draft_sop, feedback=human_corrections)
        
        if success:
            print("SUCCESS: Concept solidified into Knowledge Base.")
            # Verify storage
            with open("knowledge_base.json", "r") as f:
                print(f.read())
        else:
            print("FAILURE: Solidification failed.")

    except Exception as e:
        logger.critical(f"System Crash: {e}")