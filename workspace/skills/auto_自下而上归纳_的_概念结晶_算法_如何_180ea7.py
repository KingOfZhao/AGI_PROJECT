"""
Module: auto_concept_crystallization_180ea7
Description: Implementation of the 'Concept Crystallization' algorithm for Bottom-Up Induction.
             This module extracts high-frequency patterns from fragmented logs and formalizes
             them into structured 'Real Nodes' with explicit input/output definitions.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
License: MIT
"""

import logging
import json
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field, asdict
from collections import Counter
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class PatternCandidate:
    """
    Represents a potential pattern found in the data.
    
    Attributes:
        pattern_text (str): The normalized text representing the pattern.
        frequency (int): How often this pattern appears in the dataset.
        source_ids (List[str]): IDs of the logs where this pattern was found.
        context_tags (List[str]): Tags extracted from context (e.g., intents).
    """
    pattern_text: str
    frequency: int = 0
    source_ids: List[str] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.frequency < 0:
            raise ValueError("Frequency cannot be negative")

@dataclass
class ConceptNode:
    """
    Represents a 'Crystallized' Concept (Real Node).
    
    Attributes:
        node_id (str): Unique identifier for the node.
        description (str): Human-readable description of the concept.
        trigger_patterns (List[str]): Regex patterns or keywords that trigger this concept.
        input_schema (Dict): JSON Schema defining expected inputs.
        output_schema (Dict): JSON Schema defining expected outputs.
        confidence_score (float): Reliability of this extraction (0.0 to 1.0).
        created_at (str): Timestamp of creation.
    """
    node_id: str
    description: str
    trigger_patterns: List[str]
    input_schema: Dict
    output_schema: Dict
    confidence_score: float
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        """Serializes the node to JSON for storage or verification."""
        return json.dumps(asdict(self), indent=2)

# --- Helper Functions ---

def _normalize_text(text: str) -> str:
    """
    Normalizes text for pattern matching.
    Removes extra whitespace, lowercases, and strips punctuation.
    
    Args:
        text (str): Raw input text.
        
    Returns:
        str: Normalized text.
    """
    if not isinstance(text, str):
        logger.warning(f"Invalid text type received: {type(text)}. Converting to string.")
        text = str(text)
    
    # Basic normalization: lowercase, remove special chars, collapse whitespace
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _validate_log_entry(entry: Dict) -> bool:
    """
    Validates the structure of a single log entry.
    
    Args:
        entry (Dict): A log dictionary.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    required_keys = {"log_id", "content"}
    if not isinstance(entry, dict):
        return False
    if not required_keys.issubset(entry.keys()):
        logger.error(f"Validation Error: Log entry missing required keys {required_keys}. ID: {entry.get('id', 'Unknown')}")
        return False
    return True

# --- Core Functions ---

def extract_frequent_patterns(
    logs: List[Dict], 
    min_support: int = 5, 
    ngram_range: Tuple[int, int] = (3, 5)
) -> List[PatternCandidate]:
    """
    Analyzes a list of logs to find frequent n-gram patterns (Bottom-Up extraction).
    
    Args:
        logs (List[Dict]): List of log entries. Each must contain 'log_id' and 'content'.
        min_support (int): Minimum frequency to be considered a pattern.
        ngram_range (Tuple[int, int]): Range of n-grams to consider (min_n, max_n).
        
    Returns:
        List[PatternCandidate]: List of extracted pattern candidates.
        
    Raises:
        ValueError: If logs list is empty or invalid.
    """
    logger.info(f"Starting pattern extraction on {len(logs)} logs.")
    
    # Data Validation
    valid_logs = [log for log in logs if _validate_log_entry(log)]
    if len(valid_logs) < min_support:
        logger.warning("Insufficient valid data for pattern extraction.")
        return []

    ngram_counter = Counter()
    pattern_sources: Dict[str, Set[str]] = {}
    
    corpus = [_normalize_text(log['content']) for log in valid_logs]
    log_ids = [log['log_id'] for log in valid_logs]

    for idx, text in enumerate(corpus):
        tokens = text.split()
        current_log_id = log_ids[idx]
        
        # Generate n-grams
        for n in range(ngram_range[0], ngram_range[1] + 1):
            for i in range(len(tokens) - n + 1):
                ngram = " ".join(tokens[i:i+n])
                ngram_counter[ngram] += 1
                
                if ngram not in pattern_sources:
                    pattern_sources[ngram] = set()
                pattern_sources[ngram].add(current_log_id)

    # Filter by support threshold
    candidates = []
    for pattern, count in ngram_counter.items():
        if count >= min_support:
            candidate = PatternCandidate(
                pattern_text=pattern,
                frequency=count,
                source_ids=list(pattern_sources[pattern])
            )
            candidates.append(candidate)
            
    logger.info(f"Found {len(candidates)} potential patterns meeting support {min_support}.")
    # Sort by frequency
    candidates.sort(key=lambda x: x.frequency, reverse=True)
    return candidates

def crystallize_concept(
    pattern: PatternCandidate, 
    domain_context: Optional[str] = None
) -> Optional[ConceptNode]:
    """
    Formalizes a frequent pattern into a Concept Node with defined I/O.
    
    This function simulates the 'Crystallization' process. In a real AGI system,
    this would involve an LLM or an ontology mapper. Here, we use heuristic 
    templating to generate the I/O schema based on the pattern text.
    
    Args:
        pattern (PatternCandidate): The high-frequency pattern to formalize.
        domain_context (Optional[str]): Additional context (e.g., 'customer_support').
        
    Returns:
        Optional[ConceptNode]: The formalized node, or None if crystallization fails.
    """
    try:
        logger.info(f"Attempting to crystallize pattern: '{pattern.pattern_text}'")
        
        # Generate a unique ID for the concept
        node_id = f"concept_{hash(pattern.pattern_text) % 1000000}"
        
        # Heuristic Schema Generation
        # If the pattern looks like a question, output is 'answer', else 'confirmation'
        is_question = "?" in pattern.pattern_text or any(
            kw in pattern.pattern_text for kw in ["how to", "what is", "why"]
        )
        
        if is_question:
            input_schema = {
                "type": "object",
                "properties": {
                    "query_context": {"type": "string", "description": "Context surrounding the user query."}
                },
                "required": ["query_context"]
            }
            output_schema = {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "The synthesized answer to the question."},
                    "confidence": {"type": "number"}
                }
            }
            desc_prefix = "Knowledge Retrieval:"
        else:
            input_schema = {
                "type": "object",
                "properties": {
                    "action_params": {"type": "dict", "description": "Parameters extracted from the trigger."}
                }
            }
            output_schema = {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "failure"]},
                    "message": {"type": "string"}
                }
            }
            desc_prefix = "Action Routine:"

        # Calculate confidence based on frequency (simplified heuristic)
        confidence = min(1.0, pattern.frequency / 100.0 + 0.4)

        node = ConceptNode(
            node_id=node_id,
            description=f"{desc_prefix} Auto-generated concept for pattern '{pattern.pattern_text}'",
            trigger_patterns=[pattern.pattern_text],
            input_schema=input_schema,
            output_schema=output_schema,
            confidence_score=round(confidence, 2)
        )
        
        logger.info(f"Successfully crystallized Node: {node.node_id}")
        return node

    except Exception as e:
        logger.error(f"Failed to crystallize pattern {pattern.pattern_text}: {e}")
        return None

# --- Main Execution / Example ---

def run_crystallization_pipeline(raw_logs: List[Dict]) -> List[ConceptNode]:
    """
    Full pipeline execution.
    """
    # 1. Extract Patterns
    patterns = extract_frequent_patterns(raw_logs, min_support=2)
    
    # 2. Crystallize Nodes
    crystallized_nodes = []
    for p in patterns:
        node = crystallize_concept(p)
        if node:
            crystallized_nodes.append(node)
            
    return crystallized_nodes

if __name__ == "__main__":
    # Example Usage Data
    sample_logs = [
        {"log_id": "log_001", "content": "How do I reset my password?"},
        {"log_id": "log_002", "content": "I need to reset my password please."},
        {"log_id": "log_003", "content": "System check: reset password initiated."},
        {"log_id": "log_004", "content": "What is the weather like?"},
        {"log_id": "log_005", "content": "How do I reset my password?"},
        {"log_id": "log_006", "content": "Invalid data format detected."}, # Noise (low freq)
    ]

    print("--- Starting Concept Crystallization Pipeline ---")
    nodes = run_crystallization_pipeline(sample_logs)
    
    print(f"\n--- Generated {len(nodes)} Nodes ---")
    for n in nodes:
        print(n.to_json())
        print("-" * 40)