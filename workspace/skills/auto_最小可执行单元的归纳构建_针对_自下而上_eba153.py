"""
Module: auto_最小可执行单元的归纳构建_针对_自下而上_eba153

This module is designed to parse unstructured text contexts and extract 
executable 'Micro-Skills' (If-Then rules) for Bottom-Up Induction in AGI systems.
It distinguishes between declarative knowledge (descriptions) and procedural 
knowledge (instructions/causality) and compiles the latter into parameterized 
JSON SKILL nodes.

Author: Senior Python Engineer
Version: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeType(Enum):
    """Enumeration for classifying knowledge types."""
    DECLARATIVE = "declarative"  # What is it? (Facts, Descriptions)
    PROCEDURAL = "procedural"    # How to do it? (Instructions, Causality)


@dataclass
class SkillNode:
    """
    Represents a parameterized JSON SKILL node.
    
    Attributes:
        id (str): Unique identifier for the skill.
        trigger (str): The 'If' condition or trigger event.
        action (str): The 'Then' action or consequence.
        params (Dict[str, Any]): Extracted parameters required for execution.
        confidence (float): Confidence score of the extraction (0.0 to 1.0).
        raw_text (str): The original text segment from which the skill was extracted.
    """
    id: str
    trigger: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_text: str = ""

    def to_json(self) -> str:
        """Converts the node to a JSON string."""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


def _clean_text(text: str) -> str:
    """
    Helper function to clean and normalize text.
    Removes excessive whitespace and special characters.
    
    Args:
        text (str): Input text.
        
    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""
    # Remove multiple spaces and strip
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    return text


def classify_knowledge_segment(segment: str) -> KnowledgeType:
    """
    Classifies a text segment into Declarative or Procedural knowledge.
    
    This uses heuristics based on action verbs and causal connectors.
    
    Args:
        segment (str): A sentence or paragraph from the context.
        
    Returns:
        KnowledgeType: The classified type.
    """
    procedural_keywords = [
        "if", "then", "when", "should", "must", "ensure", "execute", 
        "run", "click", "press", "calculate", "result is", "leads to"
    ]
    declarative_keywords = [
        "is", "are", "was", "were", "consists of", "known as", "defined as"
    ]
    
    segment_lower = segment.lower()
    
    # Check for procedural patterns
    if any(re.search(rf'\b{kw}\b', segment_lower) for kw in procedural_keywords):
        return KnowledgeType.PROCEDURAL
        
    # Check for declarative patterns
    if any(re.search(rf'\b{kw}\b', segment_lower) for kw in declarative_keywords):
        return KnowledgeType.DECLARATIVE
        
    # Default fallback (could be enhanced with NLP models)
    return KnowledgeType.DECLARATIVE


def extract_causal_chains(text: str) -> List[Dict[str, str]]:
    """
    Core function to extract If-Then causal chains from text.
    
    It handles various patterns:
    1. Explicit: "If X, then Y."
    2. Implicit: "When X happens, do Y."
    3. Action-oriented: "To get X, perform Y."
    
    Args:
        text (str): The input unstructured text.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing 'trigger' and 'action'.
    """
    extracted_chains = []
    
    # Pattern 1: Explicit If-Then
    # Case-insensitive match for "If ... , then ..."
    pattern_if_then = re.compile(
        r"if\s+(?P<trigger>.*?)(?:,|\s+)\s*then\s+(?P<action>.*?)(?:\.|$)", 
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern 2: When-Do/Result
    pattern_when_do = re.compile(
        r"when\s+(?P<trigger>.*?)(?:,|\s+)\s*(?:you should|do|perform|the system will)\s+(?P<action>.*?)(?:\.|$)",
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern 3: Imperative/Process (starts with Verb, implies condition is context)
    # For this example, we focus on explicit causality
    patterns = [pattern_if_then, pattern_when_do]
    
    for pattern in patterns:
        matches = pattern.finditer(text)
        for match in matches:
            trigger = _clean_text(match.group('trigger'))
            action = _clean_text(match.group('action'))
            
            # Validation
            if trigger and action and len(trigger) > 2 and len(action) > 2:
                extracted_chains.append({
                    "trigger": trigger,
                    "action": action,
                    "raw": match.group(0)
                })
                
    return extracted_chains


def generate_skill_nodes(
    raw_text: str, 
    skill_prefix: str = "skill_auto"
) -> List[SkillNode]:
    """
    Main pipeline function that processes raw text and generates SkillNodes.
    
    Process:
    1. Segment text (simplified to sentence splitting for this demo).
    2. Filter for Procedural Knowledge.
    3. Extract Causal Chains.
    4. Parameterize the extraction into SkillNode objects.
    
    Args:
        raw_text (str): The full context text.
        skill_prefix (str): Prefix for generating skill IDs.
        
    Returns:
        List[SkillNode]: A list of validated skill nodes ready for execution.
        
    Raises:
        ValueError: If raw_text is empty or None.
    """
    if not raw_text:
        logger.error("Input text cannot be empty.")
        raise ValueError("Input text cannot be empty.")
        
    logger.info(f"Starting skill extraction on text of length: {len(raw_text)}")
    
    # 1. Segmentation (Split by sentence for analysis)
    # In a real AGI system, this would use advanced NLP sentence tokenization.
    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    
    skill_nodes = []
    
    for idx, sentence in enumerate(sentences):
        # 2. Filter Knowledge Type
        k_type = classify_knowledge_segment(sentence)
        
        if k_type == KnowledgeType.PROCEDURAL:
            # 3. Extract Chains
            chains = extract_causal_chains(sentence)
            
            for chain in chains:
                try:
                    # 4. Parameterize (Mock extraction of parameters)
                    # A real system would use Named Entity Recognition or Regex
                    # here to populate the 'params' dict.
                    params = {}
                    if "number" in chain['action'].lower():
                        params['input_type'] = 'numeric'
                    elif "file" in chain['action'].lower():
                        params['input_type'] = 'file_path'
                    else:
                        params['input_type'] = 'string'
                        
                    # Create the Node
                    node_id = f"{skill_prefix}_{idx}_{hash(chain['trigger']) % 10000}"
                    
                    node = SkillNode(
                        id=node_id,
                        trigger=chain['trigger'],
                        action=chain['action'],
                        params=params,
                        confidence=0.85,  # Static for demo, dynamic in production
                        raw_text=chain['raw']
                    )
                    
                    skill_nodes.append(node)
                    logger.info(f"Generated Skill Node: {node_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing chain in sentence {idx}: {e}")
                    continue
                    
    logger.info(f"Extraction complete. Total skills generated: {len(skill_nodes)}")
    return skill_nodes


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Sample unstructured text containing procedural knowledge
    sample_text = """
    The system is designed for high availability. 
    If the database connection fails, then retry the connection after 5 seconds. 
    To ensure data integrity, when a user submits a form, validate all input fields.
    If the validation passes, save the data to the database. 
    The architecture consists of microservices.
    When the load exceeds 80%, then scale out the cluster.
    """
    
    print("--- Starting Micro-Skill Extraction ---")
    
    try:
        # Generate Skills
        skills = generate_skill_nodes(sample_text, skill_prefix="ops_rule")
        
        # Output Results
        for skill in skills:
            print(f"\nSkill ID: {skill.id}")
            print(f"Trigger: {skill.trigger}")
            print(f"Action: {skill.action}")
            print(f"Params: {skill.params}")
            print("-" * 30)
            print(skill.to_json())
            
    except ValueError as ve:
        print(f"Validation Error: {ve}")
    except Exception as e:
        print(f"Unexpected Error: {e}")