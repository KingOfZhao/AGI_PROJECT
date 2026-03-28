"""
Module: human_machine_symbiosis_loop.py

Description:
    This module implements a high-precision mechanism for establishing a "Human-Computer Symbiosis"
    interaction loop. It captures human modifications to generated code, parses the intent behind
    these modifications (via a Diff-to-Intent parser), and solidifies them as "Truth Nodes"
    (Verified Knowledge Units) within an AGI system.

    The core value is transforming transient human edits into persistent, structured knowledge
    that the system can reuse, ensuring the AI evolves with the user's specific coding style
    and requirements.

Key Components:
    - CodeChangeAnalysis: Data class representing the structured diff.
    - DiffToIntentParser: Core class for parsing code changes into semantic intents.
    - SymbiosisLoopManager: Manager class handling the registration and storage of knowledge.

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
"""

import difflib
import logging
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# --- Configuration & Setup ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanMachineSymbiosis")

class IntentCategory(Enum):
    """Enumeration of possible semantic intents derived from code changes."""
    VARIABLE_RENAME = "VARIABLE_RENAME"
    LOGIC_ADJUSTMENT = "LOGIC_ADJUSTMENT"
    REFACTOR_STRUCTURE = "REFACTOR_STRUCTURE"
    OPTIMIZATION = "OPTIMIZATION"
    UNKNOWN = "UNKNOWN"

@dataclass
class CodeChangeAnalysis:
    """
    Represents the structured result of parsing a code modification.
    
    Attributes:
        original_code: The code snippet before modification.
        modified_code: The code snippet after modification.
        intent_category: The classified intent of the change.
        confidence_score: A float between 0.0 and 1.0 representing parsing confidence.
        extracted_entities: Key-value pairs extracted (e.g., old_name -> new_name).
        raw_diff: The unified diff string.
    """
    original_code: str
    modified_code: str
    intent_category: IntentCategory
    confidence_score: float
    extracted_entities: Dict[str, str] = field(default_factory=dict)
    raw_diff: str = ""

    def __post_init__(self):
        """Validate data after initialization."""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")

@dataclass
class TruthNode:
    """
    Represents a solidified piece of knowledge derived from human interaction.
    """
    node_id: str
    intent: IntentCategory
    pattern: str
    description: str
    source_hash: str

# --- Core Classes ---

class DiffToIntentParser:
    """
    High-precision parser that analyzes code differences to determine user intent.
    
    Uses AST-like heuristics and pattern matching to distinguish between simple
    renaming, logic changes, and structural refactorings.
    """

    @staticmethod
    def _generate_unified_diff(original: str, modified: str) -> List[str]:
        """Helper to generate a unified diff."""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile='original',
            tofile='modified',
            n=3
        )
        return list(diff)

    def parse(self, original_code: str, modified_code: str) -> CodeChangeAnalysis:
        """
        Parses the difference between two code snippets into a semantic intent.
        
        Args:
            original_code: The source code string.
            modified_code: The modified code string.
            
        Returns:
            CodeChangeAnalysis: The structured analysis of the change.
            
        Raises:
            ValueError: If input strings are empty or identical.
        """
        if not original_code or not modified_code:
            logger.error("Input code strings cannot be empty.")
            raise ValueError("Input code strings cannot be empty.")
        
        if original_code.strip() == modified_code.strip():
            logger.warning("Original and modified code are identical.")
            # Return a low-confidence neutral analysis rather than crashing
            return CodeChangeAnalysis(
                original_code, modified_code, 
                IntentCategory.UNKNOWN, 0.0, {}, ""
            )

        # Generate diff for record keeping
        diff_lines = self._generate_unified_diff(original_code, modified_code)
        raw_diff = "".join(diff_lines)
        
        # 1. Analyze Variable Renaming
        rename_entity, rename_conf = self._detect_variable_rename(original_code, modified_code)
        
        # 2. Analyze Logic Changes (Simple heuristic: checking for operator changes or keyword swaps)
        logic_change, logic_conf = self._detect_logic_alteration(raw_diff)
        
        # Determine dominant intent
        if rename_conf > 0.8:
            intent = IntentCategory.VARIABLE_RENAME
            entities = rename_entity
            conf = rename_conf
        elif logic_conf > 0.6:
            intent = IntentCategory.LOGIC_ADJUSTMENT
            entities = logic_change
            conf = logic_conf
        else:
            intent = IntentCategory.REFACTOR_STRUCTURE
            entities = {"diff_summary": "Complex structural change"}
            conf = 0.5

        logger.info(f"Parsed intent: {intent.name} with confidence {conf:.2f}")
        
        return CodeChangeAnalysis(
            original_code=original_code,
            modified_code=modified_code,
            intent_category=intent,
            confidence_score=conf,
            extracted_entities=entities,
            raw_diff=raw_diff
        )

    def _detect_variable_rename(self, original: str, modified: str) -> Tuple[Dict[str, str], float]:
        """
        Heuristic to detect variable renaming.
        
        Returns:
            Tuple of (mapping_dict, confidence_score)
        """
        # Tokenize (simple split by non-alphanumeric for demo, production would use AST)
        token_pattern = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
        orig_tokens = set(token_pattern.findall(original))
        mod_tokens = set(token_pattern.findall(modified))
        
        # Find tokens removed and added
        removed = orig_tokens - mod_tokens
        added = mod_tokens - orig_tokens
        
        # Very basic heuristic: if counts match and context is similar
        if len(removed) == 1 and len(added) == 1:
            old_name = removed.pop()
            new_name = added.pop()
            
            # Avoid detecting keyword changes as renames
            keywords = set(['if', 'else', 'for', 'while', 'return', 'def', 'class'])
            if old_name not in keywords and new_name not in keywords:
                return {old_name: new_name}, 0.9
        
        return {}, 0.0

    def _detect_logic_alteration(self, diff_text: str) -> Tuple[Dict[str, str], float]:
        """Detects simple logic changes like binary operators."""
        # Regex to find changes like '==' to '!=', '>' to '<=', etc.
        logic_patterns = [
            (r'[-+]\s*if\s+.*==', r'[-+]\s*if\s+.*!=', "Equality to Inequality"),
            (r'[-+]\s*return\s+True', r'[-+]\s*return\s+False', "Boolean Flip")
        ]
        
        for p1, p2, desc in logic_patterns:
            if re.search(p1, diff_text) and re.search(p2, diff_text):
                return {"change_type": desc}, 0.85
                
        return {}, 0.0


class SymbiosisLoopManager:
    """
    Manages the lifecycle of Truth Nodes.
    
    This class receives the analysis from the parser and "solidifies" it into
    the system's memory (simulated here as an in-memory registry).
    """

    def __init__(self):
        self._knowledge_base: Dict[str, TruthNode] = {}
        logger.info("SymbiosisLoopManager initialized.")

    def solidify_knowledge(self, analysis: CodeChangeAnalysis) -> Optional[TruthNode]:
        """
        Converts a transient CodeChangeAnalysis into a permanent TruthNode.
        
        Args:
            analysis: The analysis object from the parser.
            
        Returns:
            The created TruthNode, or None if confidence is too low.
        """
        # Boundary Check: Only solidify high-confidence insights
        if analysis.confidence_score < 0.7:
            logger.warning(f"Confidence {analysis.confidence_score} too low to solidify.")
            return None

        # Generate unique ID based on content hash
        content_hash = hashlib.sha256(analysis.raw_diff.encode()).hexdigest()[:16]
        node_id = f"node_{content_hash}"
        
        # Construct description based on intent
        if analysis.intent_category == IntentCategory.VARIABLE_RENAME:
            old_n = list(analysis.extracted_entities.keys())[0]
            new_n = analysis.extracted_entities[old_n]
            desc = f"User prefers '{new_n}' over '{old_n}' for variables."
            pattern = f"rename: {old_n} -> {new_n}"
        else:
            desc = f"User logic adjustment: {analysis.intent_category.name}"
            pattern = analysis.raw_diff[:100] # Truncate for storage

        node = TruthNode(
            node_id=node_id,
            intent=analysis.intent_category,
            pattern=pattern,
            description=desc,
            source_hash=content_hash
        )

        self._knowledge_base[node_id] = node
        logger.info(f"NEW TRUTH NODE CREATED: [{node.node_id}] {desc}")
        return node

    def get_active_context(self) -> List[TruthNode]:
        """Retrieves current active truth nodes to influence future generation."""
        return list(self._knowledge_base.values())

# --- Example Usage ---

def run_symbiosis_demo():
    """
    Demonstrates the full loop: parsing a change and creating a knowledge node.
    """
    # 1. Setup
    parser = DiffToIntentParser()
    manager = SymbiosisLoopManager()
    
    # 2. Define a code modification scenario
    original_code = """
def calculate_area(radius):
    val = 3.14 * radius * radius
    return val
"""
    
    # Human modifies 'val' to 'area' and changes logic slightly (simulated)
    modified_code = """
def calculate_area(radius):
    area = 3.14159 * radius * radius
    return area
"""

    print("--- Initiating Human-Computer Symbiosis Loop ---")
    
    try:
        # 3. Parse the intent
        analysis_result = parser.parse(original_code, modified_code)
        
        print(f"\n[Parser Output]")
        print(f"  Intent: {analysis_result.intent_category.name}")
        print(f"  Confidence: {analysis_result.confidence_score}")
        print(f"  Entities: {analysis_result.extracted_entities}")
        
        # 4. Solidify into Truth Node
        truth_node = manager.solidify_knowledge(analysis_result)
        
        if truth_node:
            print(f"\n[System Update]")
            print(f"  Knowledge Base Updated: {truth_node.description}")
        
    except Exception as e:
        logger.error(f"Error in symbiosis loop: {e}")

if __name__ == "__main__":
    run_symbiosis_demo()